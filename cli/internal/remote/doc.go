// Package remote is the HTTP client for the GophKeeper backend.
//
// It is pure transport: it speaks the server's JSON API and knows nothing about
// key storage. Authentication is the age challenge/response — the server
// encrypts a nonce to the device's public key and the caller supplies a
// decrypt function (so the private key never enters this package). Sync
// (push/pull) and the enrollment mailbox build on this client in later
// milestones.
package remote
