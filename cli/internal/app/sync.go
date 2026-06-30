package app

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/svetlana1959/GophKeeper/cli/internal/remote"
	"github.com/svetlana1959/GophKeeper/cli/internal/secret"
	"github.com/svetlana1959/GophKeeper/cli/internal/syncstate"
)

// ErrNoRemote is returned by Sync when no backend URL is configured.
var ErrNoRemote = errors.New("no remote configured; set 'remote' in config to sync")

// SyncResult summarizes one synchronization run.
type SyncResult struct {
	Pulled    int
	Pushed    int
	Conflicts int
}

// Sync reconciles this device's vault with the server: it registers on first
// run, authenticates, pulls the remote delta, then pushes local changes. pin is
// used only to unlock the private key for the auth challenge — the secret
// payloads themselves move as opaque ciphertext and are never decrypted here.
func (s *Session) Sync(ctx context.Context, pin string) (SyncResult, error) {
	var res SyncResult
	if s.cfg.Remote == "" {
		return res, ErrNoRemote
	}

	priv, err := s.unlock(pin)
	if err != nil {
		return res, err
	}

	client := remote.New(s.cfg.Remote)
	st := s.db.Sync()

	state, err := s.ensureRegistered(ctx, client, st)
	if err != nil {
		return res, err
	}

	decrypt := func(ciphertext []byte) ([]byte, error) {
		return s.cipher.Open(ciphertext, priv)
	}
	if err := client.Authenticate(ctx, s.localPub, decrypt); err != nil {
		return res, fmt.Errorf("app: authenticate: %w", err)
	}

	// Pull before push, so local edits are pushed against the latest server state.
	pulled, pullSeq, err := s.applyPull(ctx, client, st, state.Cursor, priv)
	if err != nil {
		return res, err
	}
	res.Pulled = pulled

	pushed, conflicts, pushSeq, err := s.applyPush(ctx, client, st)
	if err != nil {
		return res, err
	}
	res.Pushed, res.Conflicts = pushed, conflicts

	cursor := max(state.Cursor, max(pullSeq, pushSeq))
	if cursor != state.Cursor {
		state.Cursor = cursor
		if err := st.SaveState(state); err != nil {
			return res, err
		}
	}
	return res, nil
}

// ensureRegistered loads the device's account binding, registering on first sync.
func (s *Session) ensureRegistered(
	ctx context.Context, client *remote.Client, st syncstate.Repository,
) (*syncstate.State, error) {
	state, err := st.GetState()
	if err == nil {
		return state, nil
	}
	if !errors.Is(err, syncstate.ErrNoState) {
		return nil, err
	}

	dev, err := client.Register(ctx, s.cfg.DeviceName, s.localPub)
	if err != nil {
		return nil, fmt.Errorf("app: register device: %w", err)
	}
	state = &syncstate.State{AccountID: dev.AccountID, DeviceID: dev.ID}
	if err := st.SaveState(state); err != nil {
		return nil, err
	}
	return state, nil
}

// applyPull fetches the server delta and applies it locally, returning how many
// secrets were applied and the highest seq seen. priv decrypts payloads to
// recover the secret's name/folder (and confirms this device is a recipient).
func (s *Session) applyPull(
	ctx context.Context, client *remote.Client, st syncstate.Repository, since int64, priv string,
) (applied int, maxSeq int64, err error) {
	changes, _, err := client.Pull(ctx, since)
	if err != nil {
		return 0, since, fmt.Errorf("app: pull: %w", err)
	}

	maxSeq = since
	for _, cs := range changes {
		if cs.Seq > maxSeq {
			maxSeq = cs.Seq
		}

		local, gerr := s.secrets.Get(cs.ID)
		isNew := errors.Is(gerr, secret.ErrNotFound)
		if isNew {
			local = &secret.Secret{ID: cs.ID, Name: cs.ID} // placeholder name; refined below
		} else if gerr != nil {
			return applied, maxSeq, gerr
		}

		local.Payload = cs.Ciphertext
		local.Version = cs.Version
		local.Deleted = cs.Deleted
		local.UpdatedAt = time.Now().UTC()

		// If we can decrypt it, recover the real name/folder from the payload and
		// record that this device is a recipient (so a later edit can re-seal).
		if meta, ok := s.metaFromPayload(cs.Ciphertext, priv); ok {
			local.Name = meta.Name
			local.FolderID = meta.Folder
			local.Recipients = []string{s.localPub}
		}

		if err := s.secrets.Save(local); err != nil {
			return applied, maxSeq, err
		}
		if err := st.MarkSynced(cs.ID, cs.Version); err != nil {
			return applied, maxSeq, err
		}
		applied++
	}
	return applied, maxSeq, nil
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

// applyPush uploads dirty secrets and records the outcome. A conflicting item is
// left dirty so the next sync pulls the winner and reconciles.
func (s *Session) applyPush(
	ctx context.Context, client *remote.Client, st syncstate.Repository,
) (pushed, conflicts int, maxSeq int64, err error) {
	dirty, err := st.ListDirty()
	if err != nil {
		return 0, 0, 0, err
	}
	if len(dirty) == 0 {
		return 0, 0, 0, nil
	}

	items := make([]remote.PushItem, 0, len(dirty))
	for _, d := range dirty {
		sec, gerr := s.secrets.Get(d.SecretID)
		if gerr != nil {
			return pushed, conflicts, maxSeq, gerr
		}
		items = append(items, remote.PushItem{
			ID:          sec.ID,
			Ciphertext:  sec.Payload,
			BaseVersion: d.ServerVersion,
			Deleted:     sec.Deleted,
		})
	}

	results, err := client.Push(ctx, items)
	if err != nil {
		return pushed, conflicts, maxSeq, fmt.Errorf("app: push: %w", err)
	}

	for _, r := range results {
		if r.Seq > maxSeq {
			maxSeq = r.Seq
		}
		if r.Status == "applied" {
			if err := st.MarkSynced(r.ID, r.Version); err != nil {
				return pushed, conflicts, maxSeq, err
			}
			pushed++
			continue
		}
		conflicts++
	}
	return pushed, conflicts, maxSeq, nil
}
