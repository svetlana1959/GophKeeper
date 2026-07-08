package app

import (
	"context"
	"errors"
	"fmt"
	"time"

	"github.com/svetlana1959/GophKeeper/cli/internal/remote"
	"github.com/svetlana1959/GophKeeper/cli/internal/syncstate"
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
	Name      string
	PublicKey string
	Status    string
	This      bool // true for the local device
}

// CreateInvite mints a pairing code another device can use to join this account.
func (s *Session) CreateInvite(ctx context.Context, pin string) (Invite, error) {
	client, _, _, _, err := s.connect(ctx, pin)
	if err != nil {
		return Invite{}, err
	}
	inv, err := client.CreateInvite(ctx)
	if err != nil {
		return Invite{}, err
	}
	return Invite{Code: inv.Code, ExpiresAt: inv.ExpiresAt}, nil
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
	dev, err := client.Join(ctx, code, s.cfg.DeviceName, s.localPub)
	if err != nil {
		return fmt.Errorf("app: link: %w", err)
	}
	return st.SaveState(&syncstate.State{AccountID: dev.AccountID, DeviceID: dev.ID})
}
