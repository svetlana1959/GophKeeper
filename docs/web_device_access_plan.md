# Web device access — design plan

## Goal

**Make the web browser a real, trusted device.** That is the feature — a usable
web vault that decrypts client-side, justified on its own merits. Real stats
(secrets list, category counts, folders, storage) are a *byproduct* that falls
out once the browser holds keys; they are not the reason to build this.

Today the web is metadata-only (no crypto), so the Secrets page and category
stats are sample data — the server is zero-knowledge and can't produce them, and
the browser has no keys. Making the browser a device fixes that *without
weakening the server*: it decrypts locally and computes what it needs in memory.
The server still only ever sees ciphertext.

## The invariant that holds, and the boundary that moves

- **Preserved:** zero-knowledge *against the server*. The server never sees
  plaintext, names, folders, or categories. This is unchanged.
- **New:** the browser becomes a decryption endpoint for the session. The trust
  boundary now includes the browser runtime — its XSS surface, its dependencies,
  and (if a key persists) its local storage. This is the same trade every serious
  web password manager makes; it is real and must be designed for, not assumed
  away.

## Core model: the browser is a device

A browser device is an ordinary device in the existing model — its own age +
Ed25519 keypair, enrolled in the account, vouched for in the trust graph, a
recipient of resealed secrets. Nothing about the device *model* is browser-
specific (see "no `kind` field" below). What differs is its **lifecycle**
(short, self-expiring) and its **key storage** (browser, not a `0600` file).

## Enrollment

### Primary: approve from another device

The browser initiates; an existing device approves. No code copied by hand — the
web shows a short verification number, the user confirms it on a device they
already trust.

```
1. Web: generates its own keypair (private half never leaves the tab),
        self-enrolls as a PENDING device, shows a 4-digit code.
2. CLI: `goph device approve`
        Pending: browser "Chrome on Mac"  code 4821  fingerprint ab12·cd34
        Approve? [y/N] y
3. CLI: vouches (trust cert) AND immediately reshares the vault to the browser's
        key, then pushes — approve IS the whole action, no separate sync.
4. Web: polls; once resealed secrets arrive, decrypts in memory → unlocked.
```

The verification number defends against approving an attacker's browser. The
reshare (step 3) is why a browser can't self-serve: only a key-holder can hand
the vault over. **Critically, `approve` triggers the reshare itself** — it does
not leave the browser in a "waiting for you to run `goph sync`" dead state, which
would read as "I approved it, why is it broken?" If the reshare can't complete
(e.g. the CLI loses connectivity mid-way), the web shows a bounded, explained
wait — never an infinite spinner — and the reshare resumes idempotently (below).

### Break-glass: recovery key

When there is **no other device** to approve from (first web login on a fresh
account, or after total device loss), the recovery key is the only path — it is
a standing recipient of every secret, so it can decrypt everything alone. See
"Recovery restore" below. This is the sharpest-edged path (master key in the
browser) and is treated as last-resort, never the default.

## Key handling

- **Generation:** the browser device keypair is generated in-tab via Web Crypto
  (X25519 + Ed25519). The private half never leaves the browser.
- **At rest (persistent + PIN, default on):** the device key is stored in
  IndexedDB **encrypted under a PIN-derived key** (Argon2id). The PIN itself is
  never stored; a wrong PIN simply fails to decrypt. This mirrors the CLI's
  PIN-protected-key-at-rest model, so a returning session unlocks with a PIN — no
  re-approval, no reshare.
- **Opt-out (allowed, warned):** like the CLI, the user may store the key without
  a PIN. On the CLI a `0600` file gives OS protection; **the browser has no
  equivalent**, so an unprotected key in IndexedDB is readable by any script on
  the origin (any XSS) and anyone with local profile access. Opt-out is offered
  for parity but is genuinely more dangerous here; PIN-on is the web default and
  the toggle carries a plain-language warning.
- **In use:** the decrypted key lives only in memory and is wiped on lock.

## Two clocks (not three)

Two lifetimes, cleanly separable. The earlier "session token" clock was
redundant with the heartbeat and is dropped — a live heartbeat *is* a live
session.

| Clock | Protects | Alive while | Dies when |
|---|---|---|---|
| **Vault lock** (in-memory key) | decrypted secrets | you interact | idle ~15 min, tab hidden/closed, or "Lock now" |
| **Device enrollment** (`expires_at`) | the browser's standing key | the heartbeat renews it | `expires_at` passes → server revokes |

A single **activity-driven heartbeat** winds both: while unlocked, visible, and
recently interacted-with, the client pings ~every 60 s — bumping `last_seen_at`
and pushing `expires_at` forward (the same call carries the bearer token, so
server access lives exactly as long as the heartbeat does). Going idle, or hiding
the tab (Page Visibility API), stops the heartbeat on its own — no background
timer spinning forever. Lock fires fast (protects the key); enrollment winds down
after (device hygiene). One sentence explains any logout: *the heartbeat stopped.*

## Device lifecycle — one uniform rule, no browser detection

The server must **not** know a device is a browser. Instead, each device carries
a nullable **`expires_at`**:

- **CLI** enrolls with `expires_at = null` → never expires by inactivity.
- **Web** enrolls with `expires_at = now + N`, renewed by the heartbeat.

The server's rule is one line applied to *every* device identically: **past
`expires_at` → revoked** (lazily at next auth, plus a light periodic prune that
also drops the dead device's ciphertext recipient entries). No `kind` enum, no
per-class policy. `N` is chosen in web Settings (mandatory — the web UI won't
offer "never"; enforcement is the server honoring the timestamp).

### The 90-day universal sweep — recovery-key-aware

A second uniform rule for hygiene: **any device idle > 90 days is revoked**
(on `last_seen_at`, applies to CLI and web alike). Because zero-knowledge is
unforgiving, this rule is gated on the recovery escape hatch:

- **Recovery key set** → sweeping all devices is fully recoverable. Fine.
- **No recovery key** → revoking the account's **last** device is *permanent
  lockout* (server is blind, no device to re-enroll from). **Never** auto-revoke
  the last device without a recovery key.

Regardless, **warn before** — a notification ahead of the sweep ("devices will be
removed after inactivity; confirm you still have your recovery key"). This keeps
the hygiene feature from silently becoming a data-loss feature.

## Reshare & reseal — must be idempotent and resumable

Resharing the vault to a new device D (on approval, and on recovery) re-encrypts
every secret to include D. Done naively in the browser this is a data-loss risk:
a tab closed at secret 4,700 of 10,000 leaves the vault half-resealed. So the
operation is specified as **idempotent and resumable**, not "usually works":

- The unit of work is per-secret: *ensure this secret's recipient set includes D.*
- The worklist is exactly the secrets whose current recipient set (known
  server-side via `secret_recipients`) does **not** yet include D. A secret
  already sealed to D is skipped — so re-running never double-pushes and never
  bumps a version twice.
- Each reseal pushes with the secret's `base_version` (optimistic concurrency); a
  version conflict means someone else moved it — re-pull that one and retry.
- Interruption is safe: on resume, the worklist is recomputed (still-missing-D
  secrets), so it picks up exactly where it stopped. No checkpoint bookkeeping to
  corrupt — the recipient set *is* the progress marker.

This reuses the existing M4 reshare mechanism; the new part is driving it to
completion from the browser with the above guarantees and a progress indicator.

## Recovery restore (all devices gone)

Revoking devices deletes nothing — ciphertext stays on the server, still sealed
to the recovery key. Restore:

```
1. Log in (email/password) — the keyless account session always works.
2. Web sees ZERO active devices → shows a distinct "No trusted devices" screen
   (NOT "link a device" — there's nothing to approve from).
3. Paste recovery key. Before doing anything, the browser **validates it
   client-side**: derive its public half and check it equals the account's
   `recovery_pubkey`. Wrong key → instant, kind "that's not this account's
   recovery key" — never a silent failure after a doomed decrypt attempt.
4. On a valid key, client-side:
     - decrypts the vault with the recovery key,
     - generates a fresh browser device keypair,
     - reseals every secret to {new browser device, recovery key} (idempotent,
       resumable — see above), with a progress indicator,
     - enrolls the browser as a device,
     - wipes the recovery key from memory.
5. "Restored ✓" — back to normal; re-link other devices via the approve flow.
```

The recovery key is used transiently to bootstrap one healthy device, then goes
back offline.

**On possession, we do not pretend to guarantee what we can't.** We cannot know
whether a user actually kept their recovery key — only that one was *set*. So we
do not build possession-checking machinery; we make it **impossible to miss**:
recovery-key setup is forced/urged at onboarding, its "save this now, we can
never show it again" moment is the loudest screen in the product, and a standing
banner nags any account whose recovery key was set long ago with "confirm you
still have your recovery key." If a user ignores all of that and loses both their
devices and their key, that is permanent loss — the irreducible cost of
zero-knowledge. Our job is awareness, not a safety net that can't exist.

## Backend changes

- `devices.expires_at TIMESTAMPTZ NULL` + a reaper (lazy at auth + periodic
  prune of expired devices and their `secret_recipients` rows).
- The 90-day `last_seen_at` sweep, gated on `recovery_pubkey` for the last device.
- A **heartbeat endpoint** (or piggyback) that bumps `last_seen_at`, refreshes
  the token, and extends `expires_at`.
- An **account-scoped device list** endpoint (today `/devices` is device-token
  only) so the web can render "your devices" and the CLI-approve UI has the data.
- Surface a **pending device** (the browser's self-enrollment awaiting a vouch).

## CLI changes

- `goph device approve` — list pending devices with their verification code +
  fingerprint; on confirm, vouch (trust cert) and reshare on next sync.
- (Reshare-to-new-recipient already exists via M4.)

## Frontend changes

- Locked/unlocked vault state; IndexedDB key store; PIN set/verify (Argon2id);
  idle tracker (interaction events + Page Visibility); heartbeat; in-memory key.
- The approve flow UI (pending → code → waiting-for-reshare → unlocked).
- The recovery-restore flow, incl. bulk reseal with progress + resumability.
- Settings → Security: PIN (default on, opt-out warned), auto-lock, unenroll `N`.
- **Remove sample data** once real: `sample-secrets.ts`, `sample-devices.ts`, the
  hardcoded folders/sync-events/storage/trend numbers, the category stubs.

## What this unlocks

Client-side, with the server none the wiser: the real secrets list, real
category counts and the type donut, real folders, real storage — plus the
already-real device counts and activity. The metadata-only tabs keep working
while locked and light up further once unlocked.

## Security considerations

- **XSS / supply-chain is now the whole ballgame — this is go/no-go.** Client-side
  decryption means one injected script (ours or a transitive dependency's) reads
  live keys and plaintext. This is a hard commitment, not an aspiration:
  - a **strict, locked Content-Security-Policy** (no inline/`eval`, explicit
    source allowlist) shipped and CI-enforced;
  - **Subresource Integrity** on anything not self-hosted;
  - a **dependency budget** for the crypto/vault path — pinned, audited, minimal;
    prefer the age author's own vetted library over ad-hoc crypto;
  - the decryption key held as a **non-extractable Web Crypto key** where the age
    implementation allows, so even an XSS can't exfiltrate the raw key for offline
    use (it can still abuse the live session — but the blast radius shrinks).

  If we cannot commit to holding this line, this feature should not ship — a web
  vault that can't defend its own runtime is a decryption oracle with a login page.
- **Recovery-key-in-browser** is the sharpest edge: it puts the account master
  key in the tab. In-memory only, never persisted, explicit warning, last-resort.
- **PIN opt-out on web** is materially worse than on the CLI (no OS file perms).
  Offered for parity, defaulted **off** (PIN on), warned in plain language.
- **Vault reseal** must be idempotent and resumable (see the reseal section).

## UX principles (non-negotiable)

- **Approve must be smooth, or people route into the recovery key.** The recovery
  key is the *most* dangerous login and it's one tap away. Any friction in approve
  (see the no-dead-wait rule) pushes users into the foot-gun. Smooth approve is a
  security control, not a nicety.
- **The two locked states are visually unmistakable.** "This browser isn't a
  device" (→ approve) vs "this account has no devices" (→ recovery) get different
  layout, icon, and verb, so nobody hammers the impossible action.
- **Recovery is designed for panic.** Reassure first ("Your secrets are safe"),
  validate the pasted key instantly (client-side pubkey match), fail kindly.
- **Recovery-key awareness is the loudest thread in the product** — forced at
  onboarding, unmissable at creation, gently nagged thereafter. The whole graceful
  story collapses without it, and possession is the user's responsibility.
- **Don't make users reason about timers.** Strong defaults; PIN/auto-lock/`N`
  live under "Advanced." Most users never learn the word "unenroll."
- **A humane PIN default** (sensible auto-lock) so frustration doesn't drive people
  to disable the PIN or set an 8-hour timeout.
- **The device list stays legible** — good names ("Chrome on Mac"), last-seen, and
  a visible "browsers expire automatically" so a high count doesn't read as a breach.
- **The 90-day sweep reads as routine, not punishment** — reassuring copy, recovery
  as the hero of that screen.

## Phasing

1. **MVP:** browser-as-device via approve flow + recovery restore; in-memory key,
   basic idle lock; `expires_at` + reaper. Real secrets list appears.
2. **Hardening/polish:** PIN + at-rest key, Settings (lock/`N`), heartbeat
   refinement, the 90-day sweep + warnings, category stats, sample-data removal.
3. **Security pass:** CSP/SRI/dependency review; threat-model sign-off.

## Open questions

- Two-timer split (lock + `N`) confirmed vs a single timer.
- Should PIN opt-out exist on web at all, given no OS protection?
- Bulk-reseal performance/limits for large vaults.
- Do we cap `expires_at` server-side, or trust the honest client's Settings?
