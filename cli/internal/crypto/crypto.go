package crypto

import (
	"bytes"
	"crypto/rand"
	"errors"
	"fmt"
	"io"

	"filippo.io/age"
	"golang.org/x/crypto/chacha20poly1305"
)
// ------------------------- Key generation -------------------------

// GenerateIdentity создаёт новую age X25519-личность (приватный ключ).
func GenerateIdentity() (age.Identity, error) {
	return age.GenerateX25519Identity()
}

// IdentityToRecipient извлекает получателя (публичный ключ) из идентичности.
func IdentityToRecipient(id age.Identity) (age.Recipient, error) {
	xid, ok := id.(*age.X25519Identity)
	if !ok {
		return nil, errors.New("cryptocore: identity is not an X25519 identity")
	}
	return xid.Recipient(), nil
}

// ------------------------- DEK & Symmetric Encryption -------------------------

// NewDEK генерирует случайный 32-байтный ключ (Data Encryption Key).
func NewDEK() ([]byte, error) {
	dek := make([]byte, chacha20poly1305.KeySize)
	if _, err := io.ReadFull(rand.Reader, dek); err != nil {
		return nil, fmt.Errorf("cryptocore: failed to generate DEK: %w", err)
	}
	return dek, nil
}

// EncryptPayload шифрует открытый текст с помощью ChaCha20-Poly1305.
// Возвращает (ciphertext, nonce, error). Nonce нужен для расшифровки.
func EncryptPayload(key, plaintext []byte) (ciphertext, nonce []byte, err error) {
	aead, err := chacha20poly1305.New(key)
	if err != nil {
		return nil, nil, fmt.Errorf("cryptocore: bad key length: %w", err)
	}
	nonce = make([]byte, aead.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, nil, fmt.Errorf("cryptocore: failed to generate nonce: %w", err)
	}
	// Seal дописывает authentication tag к шифротексту.
	ciphertext = aead.Seal(nil, nonce, plaintext, nil)
	return ciphertext, nonce, nil
}

// DecryptPayload расшифровывает ciphertext с ключом и nonce.
// При неверном ключе, nonce или повреждении возвращает ошибку аутентификации.
func DecryptPayload(key, ciphertext, nonce []byte) ([]byte, error) {
	aead, err := chacha20poly1305.New(key)
	if err != nil {
		return nil, fmt.Errorf("cryptocore: bad key length: %w", err)
	}
	plain, err := aead.Open(nil, nonce, ciphertext, nil)
	if err != nil {
		return nil, fmt.Errorf("cryptocore: decryption failed (wrong key/nonce/tampered data): %w", err)
	}
	return plain, nil
}

// ------------------------- Упаковка DEK (age) -------------------------

// WrapDEK шифрует DEK для списка age-получателей. Возвращает срез зашифрованных блобов (по одному на получателя).
func WrapDEK(dek []byte, recipients ...age.Recipient) ([][]byte, error) {
	if len(recipients) == 0 {
		return nil, errors.New("cryptocore: at least one recipient required")
	}
	var blobs [][]byte
	for _, rec := range recipients {
		var buf bytes.Buffer
		w, err := age.Encrypt(&buf, rec)
		if err != nil {
			return nil, fmt.Errorf("cryptocore: wrap failed: %w", err)
		}
		if _, err := w.Write(dek); err != nil {
			return nil, fmt.Errorf("cryptocore: wrap write: %w", err)
		}
		if err := w.Close(); err != nil {
			return nil, fmt.Errorf("cryptocore: wrap close: %w", err)
		}
		blobs = append(blobs, buf.Bytes())
	}
	return blobs, nil
}

// UnwrapDEK расшифровывает один age-блоб с помощью личного ключа и возвращает DEK.
func UnwrapDEK(encryptedDEK []byte, id age.Identity) ([]byte, error) {
	r := bytes.NewReader(encryptedDEK)
	rr, err := age.Decrypt(r, id)
	if err != nil {
		return nil, fmt.Errorf("cryptocore: unwrap failed (wrong identity?): %w", err)
	}
	dek, err := io.ReadAll(rr)
	if err != nil {
		return nil, fmt.Errorf("cryptocore: reading DEK: %w", err)
	}
	if len(dek) != chacha20poly1305.KeySize {
		return nil, errors.New("cryptocore: unwrapped DEK has wrong length")
	}
	return dek, nil
}

// ------------------------- Операции с секретом -------------------------

// Secret хранит всё необходимое для расшифровки и пере‑обёртывания.
type Secret struct {
	EncryptedDEKs [][]byte // age‑бобы с завёрнутым DEK (по одному на получателя)
	Ciphertext    []byte   // открытые данные, зашифрованные DEK
	Nonce         []byte   // nonce для ChaCha20-Poly1305
}

// NewSecret создаёт новый секрет: генерирует DEK, шифрует payload, заворачивает DEK для получателей.
func NewSecret(plaintext []byte, recipients ...age.Recipient) (*Secret, error) {
	dek, err := NewDEK()
	if err != nil {
		return nil, err
	}
	ciphertext, nonce, err := EncryptPayload(dek, plaintext)
	if err != nil {
		return nil, err
	}
	encDEKs, err := WrapDEK(dek, recipients...)
	if err != nil {
		return nil, err
	}
	return &Secret{
		EncryptedDEKs: encDEKs,
		Ciphertext:    ciphertext,
		Nonce:         nonce,
	}, nil
}

// Decrypt разворачивает DEK с помощью identity и расшифровывает payload.
func (s *Secret) Decrypt(id age.Identity) ([]byte, error) {
	dek, err := s.unwrapAny(id)
	if err != nil {
		return nil, err
	}
	return DecryptPayload(dek, s.Ciphertext, s.Nonce)
}

// AddRecipient добавляет нового получателя, не перешифровывая payload.
// newRecipient – публичный ключ нового получателя, identity – наш ключ для расшифровки одного из существующих блобов.
// Возвращает новый срез EncryptedDEKs (старый не меняется).
func (s *Secret) AddRecipient(newRecipient age.Recipient, identity age.Identity) ([][]byte, error) {
	dek, err := s.unwrapAny(identity)
	if err != nil {
		return nil, err
	}
	newBlobs, err := WrapDEK(dek, newRecipient)
	if err != nil {
		return nil, err
	}
	updated := make([][]byte, 0, len(s.EncryptedDEKs)+len(newBlobs))
	updated = append(updated, s.EncryptedDEKs...)
	updated = append(updated, newBlobs...)
	return updated, nil
}

// unwrapAny пробует развернуть DEK, перебирая все EncryptedDEKs с переданной identity.
func (s *Secret) unwrapAny(id age.Identity) ([]byte, error) {
	var lastErr error
	for _, blob := range s.EncryptedDEKs {
		dek, err := UnwrapDEK(blob, id)
		if err == nil {
			return dek, nil
		}
		lastErr = err
	}
	if lastErr == nil {
		return nil, errors.New("cryptocore: no DEK blob available")
	}
	return nil, fmt.Errorf("cryptocore: cannot unwrap DEK with this identity: %w", lastErr)
}