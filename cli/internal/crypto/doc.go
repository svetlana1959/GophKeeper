// Package crypto is the age-backed adapter for sealing and opening secrets
// (#32): the implementation behind secret.Cipher. age already performs envelope
// encryption — a random file key, a ChaCha20-Poly1305 payload, and that key
// wrapped per recipient — so this package is a thin shell over filippo.io/age
// that adapts it to the domain port. Key generation lives here too.
package crypto
