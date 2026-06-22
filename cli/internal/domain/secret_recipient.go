package domain

import "errors"

type SecretRecipient struct {
	SecretID     string
	DeviceID     string
	EncryptedDEK []byte
}

type SecretRecipientRepository interface {
	Add(recipient *SecretRecipient) error
	Get(secretID, deviceID string) (*SecretRecipient, error)
	List(secretID string) ([]*SecretRecipient, error)
	Remove(secretID, deviceID string) error
}

var ErrSecretRecipientNotFound = errors.New("secret recipient not found")
