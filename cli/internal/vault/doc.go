// Package vault is the SQLite-backed local store: the adapter behind
// secret.Repository, device.Repository, and device.LocalRepository. It holds
// ciphertext only — plaintext never touches disk — and is the single place in
// the CLI that runs SQL. Open creates and migrates the database; the repository
// accessors hand out the domain ports.
package vault
