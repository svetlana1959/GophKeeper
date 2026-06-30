package secret

// Cipher seals and opens secret payloads. It is the port consumed when storing
// and reading secrets; internal/crypto is the age-backed adapter. Keys are age
// strings ("age1…" recipients and "AGE-SECRET-KEY-1…" identities).
type Cipher interface {
	// Seal encrypts plaintext to every recipient. Any one recipient's private
	// key can Open the result.
	Seal(plaintext []byte, recipients []string) (ciphertext []byte, err error)
	// Open decrypts a sealed secret with the holder's private key.
	Open(ciphertext []byte, privateKey string) (plaintext []byte, err error)
	// Reshare re-encrypts a secret to a new recipient set, rotating the key so a
	// removed recipient loses access to the new ciphertext. privateKey must
	// currently be a recipient.
	Reshare(ciphertext []byte, privateKey string, recipients []string) ([]byte, error)
}
