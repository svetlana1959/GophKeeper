# Secret Synchronization — Design

Status: proposal · Supersedes the device-access work in PR #112

This document describes how secrets are synchronized between a user's devices,
how new devices are linked, and how a lost or stolen device is removed — all
without the server ever holding a key or plaintext.

It is the spec the implementation milestones (end of this doc) build against.

---

## 1. Goals & non-goals

**Goals**

- Replicate one account's secrets across all of its trusted devices.
- Preserve the zero-knowledge guarantee: the server stores only opaque
  ciphertext plus non-secret metadata; it can never decrypt.
- Make linking a new device a two-command flow with no fingerprint chore.
- Make removing a lost/stolen device safe — a thief cannot lock the owner out.
- Stay local-first: the CLI keeps working offline; sync is opt-in.
- Leave a clean extension point for a later **read-only web dashboard** (device
  list, activity) that logs in with an account credential and never sees keys.

**Non-goals (for v1)**

- Web account login UX (email + password). The *account* entity and an auth
  abstraction exist now; the login front-end lands later.
- Selective per-secret / per-folder sharing. A linked device receives the whole
  account. Selective grants are a later extension.
- Real-time push. Sync is pull/push on demand (`goph sync`), not a live socket.

---

## 2. Two credential tiers

Authority is split so that no single stolen device can take over the account.

| Credential | Held by | Used for | Can decrypt? |
|---|---|---|---|
| **Device key** (age X25519) | each CLI / key-holding client | daily sync, self-revoke, completing a code-authorized link | yes |
| **Recovery key** (age X25519) | the user, stored **offline** | emergency: revoke a device you don't hold, full recovery | yes (it is a recipient) |
| **Account login** (email+pw) | *deferred* — future web | read-only metadata dashboard | no |

The device key is the everyday identity. The recovery key is the account's root
of authority — closer to a 2FA recovery code or Apple Recovery Key than to a
daily master password: it is **never** used for routine reads, syncs, or device
adds, only for the two rare emergencies. The account login, when it arrives, is
just a friendlier front-end to the same authority, restricted to plaintext
metadata.

### Authority matrix

| Action | Device key | Recovery key |
|---|---|---|
| Sync (push / pull) | ✅ | — |
| Add a device (via invite code) | ✅ | — |
| Self-revoke (retire *this* device) | ✅ | — |
| Revoke a **different** device | ❌ | ✅ |
| Recover with no devices left | — | ✅ |

The dangerous operations — revoking a device you are not physically holding, and
taking over an account — are the only ones behind the recovery key. That is also
exactly where friction is desirable.

---

## 3. Server data model (rewrite)

Everything here is plaintext metadata **except `secret.ciphertext`**. That one
column is the entire zero-knowledge surface. Names and folders never leave the
client.

```
account
  id              pk
  recovery_pubkey text          age1...  (public half only; private stays offline)
  created_at
  -- deferred web-login columns, nullable: email, password_hash, ...

device
  id              pk
  account_id      fk -> account
  name            text
  enc_pubkey      text          age1...  (identity + encryption + auth)
  status          text          pending | active | revoked
  created_at
  last_seen_at    nullable      bumped on each authenticated call

secret
  id              pk            client-generated UUID
  account_id      fk
  ciphertext      bytea         opaque age blob
  version         int           optimistic-concurrency token
  deleted         bool          tombstone
  updated_at
  seq             bigint        per-account monotonic; the sync cursor

secret_recipient
  secret_id       fk
  device_id       fk            one row per device the secret is sealed to
                                (authorization mirror of the age recipient set)

invite
  id              pk
  account_id      fk
  code_hash       text          hash of the single-use pairing code
  expires_at
  consumed_at     nullable

account_activity                append-only; feeds the future dashboard
  id              pk
  account_id      fk
  type            text          account.created | device.enroll_requested |
                                device.linked | device.revoked | account.recovered
  actor_device_id nullable
  target_id       nullable
  metadata        jsonb         non-secret context
  created_at
```

Kept from the existing backend: the blind-store `Secret` aggregate
(`update(base_version)` → `VersionConflict`, idempotent tombstone delete). It is
good; we build on it.

---

## 4. Authentication

`X-Device-Id` (unauthenticated, today's spoofable header) is replaced by a
**challenge-response that reuses the age key** — no second keypair, no secret
sent to the server:

1. Client requests a challenge for its `enc_pubkey`.
2. Server age-encrypts a random nonce **to that public key** and returns it.
3. Client decrypts (proving it holds the private key) and returns the nonce.
4. Server issues a short-lived session token used as a bearer thereafter.

The same mechanism authenticates the **recovery key** for emergency operations.

A request resolves to a `Principal` (today only `DevicePrincipal`, carrying
`account_id` + `device_id`; later `AccountPrincipal` for web). Every sync query
is scoped by the principal's `account_id`. TLS is mandatory regardless — it
protects tokens and metadata even though payloads are already E2E-encrypted.

---

## 5. Lifecycle flows

### 5.1 Local setup — `goph init`
Creates the local vault + device keypair only. **Nothing touches the server.**
Fully usable offline. No account exists yet, so there is no orphan/dead entity.

### 5.2 First sync = account creation
The first `goph sync` on a device with no account:
- creates the `account`, stores this device as `active`,
- mints the **recovery key**, shows the private half **once** ("store this
  offline; it is the only way to recover or revoke a lost device"), stores only
  the public half server-side, and adds it as a recipient,
- logs `account.created`.

### 5.3 Sync loop (steady state)
- **Pull** — `GET /sync/changes?since=<seq>` → every secret in the account the
  device is a recipient of with `seq > since`, **including tombstones**, plus the
  new high-water `seq`. Client applies, advances its cursor.
- **Push** — `POST /sync/push` → batch of locally changed secrets, each with
  `base_version`. Server upserts by UUID (idempotent — safe to retry), bumps
  `version` + `seq`, or returns `409 VersionConflict` on a stale write.

Cursor is the server-assigned `seq`, not timestamps (avoids clock skew).
Tombstones propagate as normal rows with `deleted=true`; clients keep them so a
delete cannot be silently resurrected.

**Conflict policy (version-LWW):** stale push → client pulls the winner; a no-op
edit fast-forwards, a genuine concurrent edit becomes a **conflict copy** (new
secret, name suffixed) rather than clobbering. Delete wins over a concurrent
edit. Conflicts are rare in practice (same secret edited on two devices before a
sync).

### 5.4 Linking a new device (two commands, no fingerprint chore)
The pairing code is a high-entropy single-use secret carried out-of-band from the
old device to the new one. The new device proves it knows the code (HMACs its
pubkey with it); the existing device verifies that proof — so the **code itself
defeats a server MITM**, and approval can be automatic.

```
# existing (key-holding) device
goph device invite
  → "Run on your new device (expires 10m):  goph link GK1-7QFM-3KD9-..."
    # code embeds server URL + account routing + the secret

# new device
goph link GK1-7QFM-3KD9-...
  → configures remote, generates keys, joins as 'pending', proves the code
  → "Linked. Secrets will appear once <existing-device> next syncs."
```

On its next sync, the existing device sees the valid pending device,
**reshares** the account's secrets to the new key (decrypt → re-encrypt to
recipients ∪ {new device} → push, via the existing `crypto.Reshare`), the server
inserts `secret_recipient` rows and flips the device to `active`, and logs
`device.linked`. No second human step.

Optional belt-and-suspenders: `goph device invite --confirm` makes the existing
device prompt and show the fingerprint before resharing, for users who don't
trust the code's transfer channel.

The server only relays and stores; it never re-encrypts and cannot insert itself
as a recipient.

> **As implemented in M1–M3 (differences from the target flow above):**
> - The pairing code is an opaque single-use secret but does **not** yet embed
>   the server URL/routing. The joining device must already have the remote
>   configured (`goph init --remote <url>`); otherwise `goph link` errors with
>   that guidance. Embedding routing in the code is deferred.
> - `goph link` admits the device as **`active` immediately** on a valid code —
>   the `pending` → reshare-gated → `active` handshake (and the `--confirm`
>   fingerprint step) lands in M4. The `pending` state and `Device.activate()`
>   exist and are guarded, but are not yet exercised.
> - Reshare currently derives its recipient set from the server's device list
>   (see the trust-boundary limitation in §9).

### 5.5 Retiring a device you still hold — self-revoke
`goph device revoke` run *on that device* marks it revoked using its own device
key. A remaining key-holder reshares to rotate keys. No recovery key needed.

### 5.6 Removing a lost / stolen device
Revoking a device you do **not** physically hold requires the recovery key — the
asymmetry that stops a thief from locking the owner out (a thief has a device
key but not the recovery key). Two phases:

1. **Membership revoke** (recovery-key authority, no crypto): server marks the
   device `revoked`; its tokens die immediately — locked out of the server.
2. **Reshare / key rotation** (a key-holder): reshare to an **explicit allow-list
   of recognized devices** — this both denies the stolen device future updates
   *and* purges any rogue device a thief may have quietly added (visible in
   `goph device ls` and the activity log).

Logs `device.revoked`.

### 5.7 Recovery (no devices left)
A fresh device + the recovery key bootstraps the account: the recovery key is an
age recipient, so it can decrypt; and it carries the authority to re-establish
devices. Without it, an all-devices-lost account is unrecoverable — inherent to
zero-knowledge, which is why the recovery key must be stored offline.

---

## 6. Security / threat model

Assume an honest-but-curious or actively malicious server.

| Threat | Outcome |
|---|---|
| Server reads secrets | Can't — only opaque age blobs, no keys |
| Server tampers ciphertext | age AEAD fails on decrypt |
| Server rolls back / withholds updates, resurrects a tombstone | Mitigated client-side (reject version regressions, keep tombstones). Full protection needs a signed log — **known residual risk** |
| Server forges a recipient grant | Harmless — blob isn't sealed to that device; can't decrypt |
| MITM at linking (pubkey substitution) | Defeated by the code-authenticated exchange |
| Spoofed device id (today's `X-Device-Id`) | Eliminated by age-challenge auth |
| Stolen device revokes the owner's devices | Eliminated — revoking another device needs the recovery key |
| Stolen *unlocked* device reads cached secrets | Can't be retracted (data already in hand); mitigated by PIN-at-rest + key rotation denying *future* updates and instant server lockout |
| Replay | Nonce + expiry in challenge; short-lived tokens; TLS |
| Metadata exposure | Server sees device names, fingerprints, timestamps, secret ids/sizes/counts, recipient sets — **never** secret names/folders/values |

Defense in depth: PIN-at-rest (age scrypt, already built), append-only activity
log + future notifications, rate-limiting on auth/enroll.

---

## 7. Code mapping

**Backend (rewrite on `feature/sync` off `dev`)**
- `account` aggregate (recovery_pubkey; nullable login columns).
- `device` with `status` + `enc_pubkey` + `last_seen_at`.
- age-challenge auth → `Principal`; drop `X-Device-Id`.
- `/sync/push` + `/sync/changes`; per-account `seq`.
- `invite` + code-authenticated linking; `secret_recipient`.
- recovery-key-gated revoke-other + recover.
- `account_activity` writer.
- keep the blind-store `Secret` aggregate already on `dev`.

**CLI**
- `internal/remote` — HTTP client behind a port (challenge auth, push, pull,
  invite, link, revoke, recover).
- app-layer sync use-case — reconcile remote ↔ vault (apply, detect conflicts,
  push, resolve).
- commands: `sync`, `device invite | link | ls | revoke`, `account recover`.
- recovery key minted at first sync; reuse `crypto.Reshare` for link/revoke.

### PR #112 → new mapping

| PR #112 | Becomes |
|---|---|
| `X-Device-Id` header | age-challenge auth → token → `Principal` |
| `access_requests` (PENDING/APPROVED/REJECTED) | `device.status` + code-authenticated `invite` |
| `approve` / `reject` endpoints | auto-reshare on valid code (manual-confirm optional) |
| `secret_access` | `secret_recipient` |
| per-id GET/PUT | `/sync/push` + `/sync/changes?since=seq` |
| (none) | `account`, recovery key, `account_activity` |

---

## 8. Milestones

Each is a vertically-sliced (backend + CLI) PR into `dev`, testable end-to-end.

- **M1 — Identity & auth.** `account` + `device` + age-challenge + `Principal`;
  CLI `internal/remote` auth + remote config. *A device registers and
  authenticates; account scoping works.*
- **M2 — Single-device sync.** `/sync/push` + `/sync/changes`, `seq`,
  `VersionConflict`, tombstones; CLI sync use-case + `goph sync`. *A vault
  round-trips to the server and back; conflicts and deletes handled.*
- **M3 — Multi-device.** invites, pending devices, `secret_recipient`, reshare;
  `goph device invite | link | ls`. *Two devices share secrets via two commands.*
- **M4 — Authority & recovery.** recovery key at setup, recovery-gated
  revoke-other + recover, self-revoke, allow-list reshare. *Stolen-device lockout
  + recovery.*
- **M5 — Activity & polish.** `account_activity` wired through, `last_seen_at`,
  `device ls` output, e2e tests, README / demo. *Data ready for the web
  dashboard; shippable.*

PR #112 stays open until M1–M3 land the replacement, then it is closed as
superseded.

## 9. Known limitations & deferred hardening (M1–M3)

These are conscious gaps, surfaced in review, to close in later milestones. They
are recorded here so they are decisions, not surprises.

- **Reshare trusts the server's device list (M4).** `applyReshare` seals secrets
  to the public keys returned by `GET /devices`. A malicious server could report
  a rogue device and the honest client would seal plaintext to it — weakening
  the zero-knowledge guarantee that §6 relies on. The mitigation is a
  client-owned trusted-device allow-list (populated only from confirmed
  invite/link provenance or an explicit fingerprint confirmation) that reshare
  seals to instead. Deferred to M4 with the recovery/authority work; until then,
  trust in the server for *recipient membership* (not for plaintext) is assumed.
- **Recovery key: CLI inclusion done, browser generation pending.** Reshare now
  seals every secret to `account.recovery_pubkey` when the server reports one (see
  §10), so the data-recovery half is wired and forward-compatible. What remains is
  the **browser generating** the recovery keypair at registration (other dev) and
  recovery-as-*authority* (revoke/recover with the recovery key) in M4.
- **Revocation is not enforceable end-to-end yet (M4).** The auth path now
  re-checks `Device.may_authenticate()` per request (so a revoked device is
  denied immediately once revoke exists), but there is no revoke endpoint/flow to
  set that state yet.
- **`seq` cursor assumes roughly in-order commit (scale).** The pull cursor is a
  single high-water over a global sequence. Under highly concurrent pushes, a
  lower `seq` can become visible after a client advanced past it (sequence values
  are allocated before commit). Acceptable at current scale; a commit-ordered
  append log or an `xmin`-gated watermark is the fix if it bites.
- **`secrets.account_id` is `TEXT`, not a `UUID` FK.** Everywhere else account id
  is a `UUID` with a foreign key; the pre-existing `secrets` table uses `TEXT`
  with no FK, forcing `str(...)` coercions at the sync seam. Migrating the column
  and adding the FK is deferred (it touches the older table).
- **Enrollment vocabulary is not unified.** The act of adding a device is spoken
  as *enroll* (context), *join* (backend method/endpoint), and *link* (CLI/user).
  "Invite" is consistent for the code itself. Reconciling on one verb (likely
  *link*) before the activity log hard-codes `device.linked` is a follow-up.

## 10. Web account plane & CLI onboarding

Account **registration moved off the CLI onto the web**. The web is a pure
*authority* plane: it authenticates a human and can act as the account, but holds
**no age key and can decrypt nothing**. Two credentials therefore coexist:

| Credential | Proof | Principal | Can decrypt? |
|---|---|---|---|
| Web session | email + password (argon2) | `AccountPrincipal(account_id)` | no |
| Device session | age challenge/response | `DevicePrincipal(device, account)` | yes (its own key) |

Auth methods are modeled for extension: `account_identities (provider,
identifier, secret)` — `password` today, OAuth later as a new provider with no
schema change.

**Endpoints**

- `POST /accounts` — register `{email, password, recovery_pubkey?}` → web session.
- `POST /accounts/login` — `{email, password}` → web session.
- `GET /accounts/me` — current account incl. `recovery_pubkey`; accepts a **web
  or device** token (the CLI reads its recovery key here).
- `POST /enroll/invite` — accepts a **web or device** principal (via
  `get_account_id`), so the browser can mint a CLI device's code.

**CLI onboarding — link, don't register.** Every device, including the first,
joins via an invite:

1. Web: register (browser mints the recovery keypair, sends only the pubkey,
   shows the private half once) → logged-in session.
2. Web "Link a device" → `POST /enroll/invite` → shows `goph link <code>`.
3. CLI: `goph link <code>` → `POST /enroll/join` → device enrolled (first device
   becomes the first key-holder).
4. CLI `goph sync` authenticates (age challenge) and, in reshare, reads
   `GET /accounts/me` and seals every secret to the devices **plus the recovery
   key** (mirrored locally as a trusted recipient; the server drops it from the
   pull mirror since it is a key, not a device).

**Linking handshake — path A (implemented) vs B (planned).** Today the web is
"an authority that mints an invite code" (path **A**), reusing the existing
invite/join machinery — the code is copied to the terminal. The nicer future UX
is path **B**, an OAuth 2.0 **Device Authorization Grant** (`gh auth login`
style): the CLI shows a `user_code` + URL, the user approves in the logged-in
browser, and the CLI polls to completion — no code pasting. B is deferred.

**Migration status.** The CLI's own account-bootstrap is removed — onboarding is
link-only (`goph link <code>`); an unlinked `goph sync` returns `ErrNotLinked`
rather than self-registering. Still pending: the browser recovery-keypair
generation (other dev).

## 11. Device trust graph (M4)

Closes the §9 gap "reshare trusts the server's device list." Reshare must seal
plaintext only to keys the *client* has verified belong to account devices —
never to whatever `GET /devices` returns, since a malicious server could inject a
rogue recipient and break the zero-knowledge guarantee of §6.

**Two orthogonal layers.**

- **Access = full mesh.** Every trusted device is a recipient of every
  mesh-scoped secret; a newly trusted device is resealed to by the whole mesh on
  the next sync. (Per-secret *recipient policies* — sharing a secret with only a
  subset of the mesh — are a future layer on top; the trust graph is unchanged by
  them.)
- **Trust = a provenance DAG**, rooted at an anchor. A device is trusted iff it
  is **reachable from the root through non-revoked vouches**. Revocation prunes
  by reachability.

**Device identity gains a signing key.** age keys are X25519 (encryption only),
so a device cannot *sign* an attestation. Each device therefore also holds an
**Ed25519 signing key**; identity becomes `(id, enc_pub, sign_pub)`, all three
registered at enroll and mirrored to peers. `enc_pub` is the age recipient;
`sign_pub` verifies the device's certs.

**Certs.** Two signed, published records, each with a per-issuer monotonic `seq`
and a `prev_hash` linking the issuer's previous cert (tamper-evident chain). The
signed bytes are a versioned, field-ordered canonical encoding — never map/JSON
key order.

- **Vouch** — `sign_issuer(account_id, issuer_id, seq, prev_hash, subject_id,
  subject_enc_pub, subject_sign_pub, issued_at)`: "issuer attests subject's keys
  and admits it." **Genesis** is a *self-vouch* (issuer == subject): the founding
  device anchors the tree.
- **Revoke** — `sign_issuer(account_id, issuer_id, seq, prev_hash, target_id,
  issued_at)`: "issuer revokes target." `target == issuer` is **self-revoke**.

**Trust computation (each device, locally, from the verified cert log).** Verify
every cert's signature against its issuer's `sign_pub` and its chain; then
`Trusted = { d : a non-revoked vouch path exists from Root to d }`. Reshare's
recipient set is `Trusted ∩ server-active` (the server still gates *availability*,
never *identity*), plus the recovery key.

**Roots & recovery.** Interim root = the **founding device** (its self-vouch).
The **recovery key is a bearer super-authority sitting *outside* the DAG** — not
a structural root: whoever holds it can issue vouches/revokes that are
authoritative regardless of graph position (revoke anyone, re-vouch, re-root).
This needs an Ed25519 **recovery signing** key (browser, other dev); until it
lands the founding device is the sole root and recovery is data-recovery only
(§10). A new device pins the root's (and recovery's) `sign_pub` through the
**invite-code channel** at link time, so it never trusts the server for the
anchor identity.

**Enrollment issues a vouch.** The invite code bootstraps *first contact* — the
inviter learns the joiner's real keys (join bound to the code) and the joiner
learns the anchor keys (roster authenticated by the code). The durable artifact
is the **inviter's vouch cert** over the joiner's keys, published to the log. No
per-pair invites: once vouched, the joiner is reachable from the root, so the
whole mesh reseals to it automatically.

**Revocation authority = the vouch tree.** `A` may revoke `B` iff `A` is an
**ancestor of `B`** in the DAG (A introduced B, directly or transitively), or `A`
holds the recovery key. Revoking `A` voids A's outgoing vouches, so any device
reachable *only* through `A` becomes unreachable and is dropped — the cascade.
Remaining devices then **rotate keys** (the tested reshare path guarantees a
removed recipient loses future access). Self-revoke is always permitted.

**Transport — dedicated trust log (option A).** `POST /trust/certs` publishes one
cert; `GET /trust/certs?since=<cursor>` returns new certs in order (same cursor
pattern as `/sync/changes`). Kept separate from `/devices` and `/sync` on
purpose: trust is a first-class, client-verified artifact, and re-entangling it
with the server's device list is the very bug being fixed. The server relays but
cannot forge (all certs signed). Integrity: per-issuer monotonic `seq` +
`prev_hash` chain detect drops/reorders *within* an issuer; a signed **log head**
(`issuer, latest_seq, latest_hash`) that peers refuse to roll back detects the
server hiding an issuer's *latest* certs (hardening, after the core).

**Forward secrecy only.** Rotation protects future ciphertext; a revoked device
keeps any plaintext it already pulled. Standard for key rotation, stated so it is
a decision.

**Implementation order (atomic commits).** signing keys at init/enroll → cert
format + sign/verify (crypto) → `/trust/certs` transport (backend + CLI client) →
trusted-set computation → reshare seals to it → vouch-on-enroll → revoke +
self-revoke + cascade → recovery-as-bearer (when the browser signing key lands).
