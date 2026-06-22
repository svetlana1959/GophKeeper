package domain

import (
    "errors"
    "time"
)

type TrustedDevice struct {
	ID        string
	DeviceName string
	PublicKey  string
	IsActive   bool
	UpdatedAt  time.Time
}

type TrustedDeviceRepository interface {
	Create(device *TrustedDevice) error
	Get(id string) (*TrustedDevice, error)
	List(activeOnly bool) ([]*TrustedDevice, error)
	Update(device *TrustedDevice) error
	Activate(id string) error
	Deactivate(id string) error
}

var ErrTrustedDeviceNotFound = errors.New("trusted device not found")
