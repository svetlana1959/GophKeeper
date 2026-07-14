package app

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/google/uuid"

	"github.com/svetlana1959/GophKeeper/cli/internal/device"
	"github.com/svetlana1959/GophKeeper/cli/internal/remote"
	"github.com/svetlana1959/GophKeeper/cli/internal/secret"
	"github.com/svetlana1959/GophKeeper/cli/internal/syncstate"
	"github.com/svetlana1959/GophKeeper/cli/internal/trust"
)

// ErrNoRemote is returned by Sync when no backend URL is configured.
var ErrNoRemote = errors.New("no remote configured; set 'remote' in config to sync")

// SyncResult summarizes one synchronization run.
type SyncResult struct {
	Pulled    int
	Pushed    int
	Reshared  int
	Conflicts int
}

// Sync reconciles this device's vault with the server: it registers on first
// run, authenticates, pulls the remote delta, then pushes local changes. pin is
// used only to unlock the private key for the auth challenge — the secret
// payloads themselves move as opaque ciphertext and are never decrypted here.
func (s *Session) Sync(ctx context.Context, pin string) (SyncResult, error) {
	var res SyncResult

	client, st, state, priv, err := s.connect(ctx, pin)
	if err != nil {
		return res, err
	}

	// Pull before push, so local edits are pushed against the latest server state.
	pulled, pullConflicts, pullCursor, err := s.applyPull(ctx, client, st, state.Cursor, priv)
	if err != nil {
		return res, err
	}
	res.Pulled = pulled
	res.Conflicts = pullConflicts

	// Reshare secrets to any account devices not yet sealed in (e.g. a newly
	// linked one). Reshared secrets become dirty and push below.
	reshared, err := s.applyReshare(ctx, client, priv)
	if err != nil {
		return res, err
	}
	res.Reshared = reshared

	pushed, pushConflicts, err := s.applyPush(ctx, client, st)
	if err != nil {
		return res, err
	}
	res.Pushed = pushed
	res.Conflicts += pushConflicts

	// The cursor tracks only what we pulled and applied — never our own pushes.
	// Folding a push seq in here would advance the cursor past a concurrent
	// change committed by another device between our pull and our push, and that
	// change would then never be returned by a future `since=cursor` pull. Our
	// own pushed secrets are harmlessly re-pulled next time (apply is idempotent).
	if pullCursor > state.Cursor {
		state.Cursor = pullCursor
		if err := st.SaveState(state); err != nil {
			return res, err
		}
	}
	return res, nil
}

// connect prepares an authenticated remote session: it unlocks the key, builds
// the client, ensures the device is bound to an account (registering on first
// run), and authenticates. It returns the client, the sync-state repo, the
// current state, and the unlocked private key.
func (s *Session) connect(
	ctx context.Context, pin string,
) (*remote.Client, syncstate.Repository, *syncstate.State, string, error) {
	if s.cfg.Remote == "" {
		return nil, nil, nil, "", ErrNoRemote
	}
	priv, err := s.unlock(pin)
	if err != nil {
		return nil, nil, nil, "", err
	}

	client := remote.New(s.cfg.Remote)
	st := s.db.Sync()
	// This device must already be linked to an account. Onboarding is
	// link-only (`goph link <code>` with a code from the web or another
	// device); the CLI never creates an account.
	state, err := st.GetState()
	if errors.Is(err, syncstate.ErrNoState) {
		return nil, nil, nil, "", ErrNotLinked
	} else if err != nil {
		return nil, nil, nil, "", err
	}

	decrypt := func(ciphertext []byte) ([]byte, error) {
		return s.cipher.Open(ciphertext, priv)
	}
	if err := client.Authenticate(ctx, s.localPub, decrypt); err != nil {
		return nil, nil, nil, "", fmt.Errorf("app: authenticate: %w", err)
	}
	return client, st, state, priv, nil
}

// applyPull fetches the server delta and applies it locally, returning how many
// secrets were applied, how many concurrent-edit conflicts were forked into
// conflict copies, and the server's authoritative cursor (the high-water to
// persist). priv decrypts payloads to recover the secret's name/folder (and
// confirms this device is a recipient).
func (s *Session) applyPull(
	ctx context.Context, client *remote.Client, st syncstate.Repository, since int64, priv string,
) (applied, conflicts int, cursor int64, err error) {
	changes, cursor, err := client.Pull(ctx, since)
	if err != nil {
		return 0, 0, since, fmt.Errorf("app: pull: %w", err)
	}

	dirty, err := st.ListDirty()
	if err != nil {
		return 0, 0, cursor, err
	}
	dirtyBase := make(map[string]int, len(dirty))
	for _, d := range dirty {
		dirtyBase[d.SecretID] = d.ServerVersion // the server version our edit is based on
	}

	for _, cs := range changes {
		local, gerr := s.secrets.Get(cs.ID)
		isNew := errors.Is(gerr, secret.ErrNotFound)
		if isNew {
			local = &secret.Secret{ID: cs.ID, Name: cs.ID} // placeholder name; refined below
		} else if gerr != nil {
			return applied, conflicts, cursor, gerr
		} else if base, isDirty := dirtyBase[cs.ID]; isDirty {
			// We hold an unpushed local edit. If the server hasn't moved past the
			// version we based it on, keep our edit as-is (push will land it) and
			// don't clobber. If the server did move on, this is a genuine
			// concurrent edit: preserve our version as a conflict copy rather than
			// silently overwriting it, then take the server's winner below.
			if cs.Version == base {
				continue
			}
			if err := s.forkConflictCopy(st, local); err != nil {
				return applied, conflicts, cursor, err
			}
			conflicts++
		} else if local.Version == cs.Version && local.Deleted == cs.Deleted {
			// Clean and already at this version — nothing to apply. The common
			// case when a device re-pulls its own just-pushed secrets (the cursor
			// deliberately doesn't advance past our own writes).
			continue
		}

		local.Payload = cs.Ciphertext
		local.Version = cs.Version
		local.Deleted = cs.Deleted
		local.UpdatedAt = time.Now().UTC()

		// If we can decrypt it, recover the real name/folder from the payload.
		// Only seed recipients for a brand-new secret (to this device alone, as a
		// placeholder reshare expands); for an existing one keep the recipient set
		// already loaded from the vault, or pull would clobber it and reshare
		// would ping-pong forever.
		if meta, ok := s.metaFromPayload(cs.Ciphertext, priv); ok {
			local.Name = meta.Name
			local.FolderID = meta.Folder
			if isNew {
				local.Recipients = []string{s.localPub}
			}
		}

		if err := s.secrets.Save(local); err != nil {
			return applied, conflicts, cursor, err
		}
		if err := st.MarkSynced(cs.ID, cs.Version); err != nil {
			return applied, conflicts, cursor, err
		}
		applied++
	}
	return applied, conflicts, cursor, nil
}

// forkConflictCopy preserves an unpushed local edit as a new, independent secret
// before the server's winning version overwrites the original. The copy keeps
// the local ciphertext (already sealed to the local recipients) under a
// name-suffixed, collision-free id, and is marked dirty so it pushes as a fresh
// create on this same run. This is the design's conflict-copy rule: a genuine
// concurrent edit is never silently lost.
func (s *Session) forkConflictCopy(st syncstate.Repository, local *secret.Secret) error {
	copyID := uuid.NewString()
	dup := &secret.Secret{
		ID:         copyID,
		Name:       fmt.Sprintf("%s (conflict %s)", local.Name, copyID[:8]),
		FolderID:   local.FolderID,
		Payload:    local.Payload,
		Recipients: local.Recipients,
		Version:    1,
		UpdatedAt:  time.Now().UTC(),
	}
	if err := s.secrets.Save(dup); err != nil {
		return err
	}
	return st.MarkDirty(dup.ID)
}

// metaFromPayload decrypts a payload to recover a secret's name and folder. It
// returns ok=false when this device is not a recipient or the payload predates
// names-in-payload.
func (s *Session) metaFromPayload(ciphertext []byte, priv string) (content, bool) {
	plain, err := s.cipher.Open(ciphertext, priv)
	if err != nil {
		return content{}, false
	}
	var c content
	if json.Unmarshal(plain, &c) != nil || c.Name == "" {
		return content{}, false
	}
	return c, true
}

// applyReshare ensures every secret this device can decrypt is sealed to the
// account's trusted devices. Trust is computed locally from the signed cert log
// and this device's anchors (never from the server's device list, which a
// malicious server could pad with a rogue recipient — see docs/sync_design.md
// §11). Trusted devices are mirrored into the local set so recipient keys
// resolve; any secret whose recipient set differs is re-encrypted and marked
// dirty to push.
func (s *Session) applyReshare(
	ctx context.Context, client *remote.Client, priv string,
) (int, error) {
	certs, _, err := client.TrustChanges(ctx, 0)
	if err != nil {
		return 0, fmt.Errorf("app: pull trust log: %w", err)
	}
	anchors, err := s.db.Anchors().List()
	if err != nil {
		return 0, err
	}
	trusted := trust.ComputeTrusted(certs, anchors)

	desired := make([]string, 0, len(trusted)+1)
	for _, d := range trusted {
		desired = append(desired, d.EncPub)
		if err := s.rememberTrusted(d); err != nil {
			return 0, err
		}
	}

	// The account's recovery key is a standing recipient of every secret, so its
	// offline private key can decrypt them if all devices are lost. It is a key,
	// not a device (it never pulls), so the server drops it from the recipient
	// mirror; we still seal the ciphertext to it. Empty until the web mints one.
	acc, err := client.Account(ctx)
	if err != nil {
		return 0, fmt.Errorf("app: fetch account: %w", err)
	}
	if acc.RecoveryPubkey != "" {
		if err := s.rememberRecoveryKey(acc.RecoveryPubkey); err != nil {
			return 0, err
		}
		desired = append(desired, acc.RecoveryPubkey)
	}

	secs, err := s.secrets.List(false) // active secrets only; tombstones carry no payload
	if err != nil {
		return 0, err
	}

	reshared := 0
	for _, sec := range secs {
		if sameSet(sec.Recipients, desired) {
			continue
		}
		// Reshare rotates the key to the new recipient set (the tested path that
		// guarantees a removed recipient loses access). It fails for a secret we
		// can't decrypt — i.e. one we're not a recipient of — which we simply skip.
		payload, err := s.cipher.Reshare(sec.Payload, priv, desired)
		if err != nil {
			continue
		}
		sec.Reseal(payload, time.Now().UTC())
		sec.Recipients = desired
		if err := s.secrets.Save(sec); err != nil {
			return reshared, err
		}
		if err := s.db.Sync().MarkDirty(sec.ID); err != nil {
			return reshared, err
		}
		reshared++
	}
	return reshared, nil
}

// rememberTrusted mirrors a trusted device into the local trusted_devices table
// if its key is not already known, so secret recipients resolve when saving.
// Names are cosmetic here (the id stands in); `device ls` shows real names from
// the server. The self row saved at init already carries this device's key, so
// it is left untouched.
func (s *Session) rememberTrusted(d trust.TrustedDevice) error {
	_, err := s.db.Devices().FindByPublicKey(d.EncPub)
	if err == nil {
		return nil
	}
	if !errors.Is(err, device.ErrNotFound) {
		return err
	}
	return s.db.Devices().Save(&device.Device{
		ID: d.DeviceID, Name: d.DeviceID, PublicKey: d.EncPub, SignPublicKey: d.SignPub,
		Active: true, UpdatedAt: time.Now().UTC(),
	})
}

// recoveryKeyID is the stable local id for the account recovery key. It is not a
// real device (never a UUID, never pulls); mirroring it as a trusted recipient
// just lets the vault resolve it when a secret is sealed to it.
const recoveryKeyID = "recovery-key"

// rememberRecoveryKey mirrors the account recovery public key into the local
// trusted set so secrets can be sealed to it.
func (s *Session) rememberRecoveryKey(pub string) error {
	if _, err := s.db.Devices().FindByPublicKey(pub); err == nil {
		return nil
	} else if !errors.Is(err, device.ErrNotFound) {
		return err
	}
	return s.db.Devices().Save(&device.Device{
		ID: recoveryKeyID, Name: "recovery", PublicKey: pub, Active: true, UpdatedAt: time.Now().UTC(),
	})
}

// sameSet reports whether two recipient lists contain the same keys.
func sameSet(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	counts := make(map[string]int, len(a))
	for _, x := range a {
		counts[x]++
	}
	for _, x := range b {
		counts[x]--
		if counts[x] < 0 {
			return false
		}
	}
	return true
}

// applyPush uploads dirty secrets and records the outcome. A conflicting item is
// left dirty so the next sync pulls the winner and reconciles.
func (s *Session) applyPush(
	ctx context.Context, client *remote.Client, st syncstate.Repository,
) (pushed, conflicts int, err error) {
	dirty, err := st.ListDirty()
	if err != nil {
		return 0, 0, err
	}
	if len(dirty) == 0 {
		return 0, 0, nil
	}

	items := make([]remote.PushItem, 0, len(dirty))
	for _, d := range dirty {
		sec, gerr := s.secrets.Get(d.SecretID)
		if gerr != nil {
			return pushed, conflicts, gerr
		}
		items = append(items, remote.PushItem{
			ID:          sec.ID,
			Ciphertext:  sec.Payload,
			BaseVersion: d.ServerVersion,
			Deleted:     sec.Deleted,
			Recipients:  sec.Recipients,
		})
	}

	results, err := client.Push(ctx, items)
	if err != nil {
		return pushed, conflicts, fmt.Errorf("app: push: %w", err)
	}

	for _, r := range results {
		if r.Status == "applied" {
			if err := st.MarkSynced(r.ID, r.Version); err != nil {
				return pushed, conflicts, err
			}
			pushed++
			continue
		}
		conflicts++
	}
	return pushed, conflicts, nil
}
