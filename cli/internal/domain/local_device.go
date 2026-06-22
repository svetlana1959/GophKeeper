package domain

import (
    "errors"
    "time"
)

type LocalDevice struct {
	DeviceID            string
	PrivateKeyEncrypted []byte
	CreatedAt           time.Time
}

type LocalDeviceRepository interface {
	Store(device *LocalDevice) error
	Get() (*LocalDevice, error)
	Delete() error
}

var ErrLocalDeviceNotFound = errors.New("local device not found")
