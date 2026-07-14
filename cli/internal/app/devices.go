package app

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/svetlana1959/GophKeeper/cli/internal/remote"
	"github.com/svetlana1959/GophKeeper/cli/internal/syncstate"
	"github.com/svetlana1959/GophKeeper/cli/internal/trust"
)

// ErrAlreadyLinked is returned by Link when this device is already bound to an
// account.
var ErrAlreadyLinked = errors.New("this device is already linked to an account")

// ErrNotLinked is returned by read-only account operations on a device that has
// never synced or linked, so they don't silently bootstrap a fresh account.
var ErrNotLinked = errors.New(
	"this device isn't linked to an account yet; run 'goph sync' or 'goph link <code>' first",
)

// Invite is a pairing code for linking a new device, shown once.
type Invite struct {
	Code      string
	ExpiresAt time.Time
}

// DeviceInfo is one device in an account, as shown to the user.
type DeviceInfo struct {
	ID        string
	Name      string
	PublicKey string
	Status    string
	This      bool // true for the local device
}

// CreateInvite mints a pairing code another device can use to join this account.
// The code is generated locally and never sent to the server: only its hash and
// a roster of this device's trusted devices (each MAC'd under the code) are
// uploaded, so the joiner can verify the roster and adopt those devices as trust
// anchors. The invite is remembered locally until redeemed, so this device can
// verify the join proof and vouch for the joiner on a later sync.
func (s *Session) CreateInvite(ctx context.Context, pin string) (Invite, error) {
	client, _, _, _, err := s.connect(ctx, pin)
	if err != nil {
		return Invite{}, err
	}
	code, err := trust.GenerateInviteCode()
	if err != nil {
		return Invite{}, err
	}
	trusted, err := s.trustedSet(ctx, client)
	if err != nil {
		return Invite{}, err
	}
	inv, err := client.CreateInvite(ctx, trust.HashCode(code), trust.BuildRoster(code, trustedSlice(trusted)))
	if err != nil {
		return Invite{}, err
	}
	if err := s.db.PendingInvites().Save(trust.PendingInvite{InviteID: inv.ID, Code: code}); err != nil {
		return Invite{}, err
	}
	return Invite{Code: code, ExpiresAt: inv.ExpiresAt}, nil
}

// trustedSlice flattens a trusted set into a stable-free slice for roster building.
func trustedSlice(m map[string]trust.TrustedDevice) []trust.TrustedDevice {
	out := make([]trust.TrustedDevice, 0, len(m))
	for _, d := range m {
		out = append(out, d)
	}
	return out
}

// RevokeDevice publishes a signed revoke cert for targetID. It takes effect only
// if this device is an ancestor of the target in the vouch graph (it introduced
// it, directly or transitively) or revokes itself — the trust computation on
// every device enforces that, and drops the target's subtree along with it. On
// the next sync, reshare rotates secrets so the revoked device loses access to
// future ciphertext.
func (s *Session) RevokeDevice(ctx context.Context, pin, targetID string) error {
	client, _, state, _, err := s.connect(ctx, pin)
	if err != nil {
		return err
	}
	signPriv, err := s.unlockSigning(pin)
	if err != nil {
		return err
	}
	if signPriv == "" {
		return fmt.Errorf("app: this device has no signing key; re-init to manage trust")
	}
	resolvedID, err := s.resolveDeviceID(ctx, client, targetID)
	if err != nil {
		return err
	}
	certs, _, err := client.TrustChanges(ctx, 0)
	if err != nil {
		return fmt.Errorf("app: pull trust log: %w", err)
	}
	nextSeq, prevHash := chainHead(certs, state.DeviceID)
	cert, err := trust.Sign(trust.Cert{
		Kind: trust.KindRevoke, AccountID: state.AccountID, IssuerID: state.DeviceID,
		Seq: nextSeq, PrevHash: prevHash, TargetID: resolvedID, IssuedAt: time.Now().Unix(),
	}, signPriv)
	if err != nil {
		return err
	}
	return client.PublishCert(ctx, cert)
}

// resolveDeviceID maps a user-supplied target — a device id or a device name — to
// a device id, using the account's device list. An exact id match wins; a name is
// resolved if it is unambiguous.
func (s *Session) resolveDeviceID(
	ctx context.Context, client *remote.Client, target string,
) (string, error) {
	devices, err := client.ListDevices(ctx)
	if err != nil {
		return "", fmt.Errorf("app: list devices: %w", err)
	}
	var byName []remote.Device
	for _, d := range devices {
		if d.ID == target {
			return d.ID, nil
		}
		if d.Name == target {
			byName = append(byName, d)
		}
	}
	switch len(byName) {
	case 0:
		return "", fmt.Errorf("app: no device with id or name %q", target)
	case 1:
		return byName[0].ID, nil
	default:
		return "", fmt.Errorf("app: name %q is ambiguous (%d devices); use the id", target, len(byName))
	}
}

// ListDevices returns the account's devices, flagging the local one. It never
// creates an account: a device that has not linked/synced yet gets ErrNotLinked
// rather than silently registering just to satisfy a read.
func (s *Session) ListDevices(ctx context.Context, pin string) ([]DeviceInfo, error) {
	if _, err := s.db.Sync().GetState(); errors.Is(err, syncstate.ErrNoState) {
		return nil, ErrNotLinked
	} else if err != nil {
		return nil, err
	}
	client, _, _, _, err := s.connect(ctx, pin)
	if err != nil {
		return nil, err
	}
	devices, err := client.ListDevices(ctx)
	if err != nil {
		return nil, err
	}
	out := make([]DeviceInfo, 0, len(devices))
	for _, d := range devices {
		out = append(out, DeviceInfo{
			ID:        d.ID,
			Name:      d.Name,
			PublicKey: d.PublicKey,
			Status:    d.Status,
			This:      d.PublicKey == s.localPub,
		})
	}
	return out, nil
}

// Link binds this device to an existing account using a pairing code. The
// account's secrets arrive once a key-holding device reshares them on its next
// sync; run `goph sync` afterwards to pull them.
func (s *Session) Link(ctx context.Context, code string) error {
	if s.cfg.Remote == "" {
		// The pairing code does not yet carry the server URL (see design §5.4),
		// so the remote must already be configured on this device.
		return fmt.Errorf("%w: run 'goph init --remote <url>' on this device first", ErrNoRemote)
	}
	st := s.db.Sync()
	if _, err := st.GetState(); err == nil {
		return ErrAlreadyLinked
	} else if !errors.Is(err, syncstate.ErrNoState) {
		return err
	}

	client := remote.New(s.cfg.Remote)
	joinMAC := trust.JoinMAC(code, s.localPub, s.localSignPub)
	dev, roster, err := client.Join(
		ctx, trust.HashCode(code), s.cfg.DeviceName, s.localPub, s.localSignPub, joinMAC,
	)
	if err != nil {
		return fmt.Errorf("app: link: %w", err)
	}
	// This device trusts itself: anchor its own keys under the server-assigned id
	// so the trust graph has a root to grow from.
	if err := s.db.Anchors().Save(trust.Anchor{
		DeviceID: dev.ID, EncPub: s.localPub, SignPub: s.localSignPub,
	}); err != nil {
		return err
	}
	// Adopt the inviter's devices as anchors, but only the roster entries whose
	// MAC verifies under the code — a server-tampered or injected entry is dropped.
	// (A web-minted invite carries an empty roster; the first device just
	// self-anchors.)
	for _, a := range trust.VerifiedAnchors(code, roster) {
		if err := s.db.Anchors().Save(a); err != nil {
			return err
		}
	}
	return st.SaveState(&syncstate.State{AccountID: dev.AccountID, DeviceID: dev.ID})
}
