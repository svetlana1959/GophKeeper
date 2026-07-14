# GophKeeper Secret Manager (End-to-End Zero-Knowledge Sync)
![GitHub License](https://img.shields.io/github/license/svetlana1959/GophKeeper)
[![Go Version](https://img.shields.io/github/go-mod/go-version/svetlana1959/GophKeeper?filename=cli%2Fgo.mod)](https://go.dev/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)\
[![CI CLI](https://github.com/svetlana1959/GophKeeper/actions/workflows/ci-cli.yaml/badge.svg)](https://github.com/svetlana1959/GophKeeper/actions/workflows/ci-cli.yaml)
[![CI Backend](https://github.com/svetlana1959/GophKeeper/actions/workflows/ci-backend.yaml/badge.svg)](https://github.com/svetlana1959/GophKeeper/actions/workflows/ci-backend.yaml)
[![CI Frontend](https://github.com/svetlana1959/GophKeeper/actions/workflows/ci-frontend.yaml/badge.svg)](https://github.com/svetlana1959/GophKeeper/actions/workflows/ci-frontend.yaml)

A secure, local-first, end-to-end encrypted secret manager utilizing **age (X25519)** encryption. Designed under a strict **Zero-Knowledge model**, the server acts as a blind, stateless storage orchestrator that never processes or holds unencrypted payloads or private keys.

---

## Features

- **End-to-end encryption** — secrets are sealed client-side with `age` (X25519); the server sees only ciphertext.
- **Multi-device access** — secrets are sealed to multiple device keys at once, so any authorized device can open them.
- **Zero-knowledge sync** — push/pull with per-account cursors, idempotent batch upserts, and version-based conflict resolution.
- **Local-first CLI** — `goph` works fully offline; sync is opt-in. Set, get, list, and delete secrets from a single static binary.
- **Two-tier authentication** — age challenge/response for devices (no secret ever sent) and email + password (Argon2id) for the web dashboard.
- **Code-authenticated device linking** — invite/join flow that's MAC-protected against a server MITM.
- **Client-verified device trust** — a tamper-evident graph of signed vouch/revoke certificates; the server relays but never verifies them.
- **Device revocation** — revoke a device and its subtree, then rotate keys so it loses future access.
- **Recovery key** — an offline key separate from everyday device keys, so a stolen device can't lock you out.
- **Web dashboard** — metadata & management only; never handles secret plaintext or keys.

## Components

| Component | Stack |
|---|---|
| **Backend** | Python · FastAPI · PostgreSQL · Argon2id |
| **CLI** (`goph`) | Go · `age` · Ed25519 · SQLite vault |
| **Frontend** | React · Vite · TypeScript · TailwindCSS |

## Roadmap

- Typed secret categories (passwords, cards, notes, files) — CLI currently stores a generic secret type
- Digital inheritance (dead-man's-switch transfer to a beneficiary)
- Backup export / restore
- Breach-database checks and stale-password alerts
- Server-side revocation enforcement
- Browser-based recovery keys

---

## CLI Application: Guide & Usage

### Installation & Build

#### Linux / macOS

You can quickly install the pre-compiled binary using the official shell installer:

```bash
curl -sSL https://raw.githubusercontent.com/svetlana1959/GophKeeper/main/cli/install.sh | sh
```

The script installs the binary to `/usr/local/bin` (it will prompt for `sudo` only if write permissions are required). You can override the destination directory by passing `INSTALL_DIR`:

```bash
curl -sSL https://raw.githubusercontent.com/svetlana1959/GophKeeper/main/cli/install.sh | INSTALL_DIR="$HOME/.local/bin" sh
```

#### Windows (PowerShell)

For Windows users, use the automated PowerShell installer:

```powershell
irm https://raw.githubusercontent.com/svetlana1959/GophKeeper/main/cli/install.ps1 | iex
```

This installs the binary to `%LOCALAPPDATA%\Programs\goph` and automatically appends it to your user `PATH` (make sure to restart your terminal session afterwards). To override the default directory:

```powershell
$Env:InstallDir = "C:\Custom\Path"
irm https://raw.githubusercontent.com/svetlana1959/GophKeeper/main/cli/install.ps1 | iex
```

#### From a Release

1. Navigate to the [Releases Page](https://github.com/svetlana1959/GophKeeper/releases).
2. Download the packaged archive corresponding to your target operating system and CPU architecture.
3. Verify the binary integrity against the published `checksums.txt` file.
4. Extract the archive and move the `goph` executable into a directory listed in your system's `PATH`.

####  Building From Source

If you prefer to compile the CLI client manually, make sure you have **Go 1.26+** installed:

```bash
# Navigate to the CLI module, compile, and verify
cd cli
go build -o goph .
./goph --version
```

## CLI Command Reference
All command parameters, flags, and options are parsed using Cobra. If your local vault is PIN-protected, commands requiring your private key will securely prompt you for your PIN.

### Offline Local-First Commands
These commands operate entirely on your local machine and do not require any internet connection or backend interaction.

#### `goph init`
Set up the current device by creating a new local SQLite vault, configuring your remote, and generating a unique native `age` identity keypair.

* **Usage:** `goph init [flags]` 
    * **Flags:**
    * `--device-name <string>` — Custom name for this device (defaults to your machine's hostname).
    * `--remote <url>` — Optional backend URL to set up synchronization immediately.
    * `--key-file <path>` — Import an existing `age` private key from a file rather than generating a new one.
    * `--pin` — Protect your private key at rest inside the local vault using a master PIN.
    * `--force` — Overwrite any existing setup/vault on this machine.

#### `goph set`
Create a new secret or update an existing one in your local vault.

* **Usage:** `goph set <name> [flags]` 
* **Input Resolution Order:** The secret's raw payload is retrieved from `--value`, then `--file`, then piped `stdin`, or finally via a hidden interactive console prompt.
* **Flags:**
    * `--value <string>` — Provide the secret payload directly as a string.
    * `--file <path>` — Read the secret payload from a local file.
    * `--folder <string>` — Place the secret into a specific organizational folder.
    * `--description <string>` — Attach an optional non-secret description.

#### `goph get`
Read, decrypt, and display a stored secret.

* **Usage:** `goph get <name> [flags]` 
* **Flags:**
    * `--field <string>` — Extract and print only a single field from a JSON-structured secret (defaults to printing the raw payload).

#### `goph list`
List all secrets stored in your local database. Only outputs metadata; no cryptographic decryption is performed.

* **Usage:** `goph list [flags]` 
* **Flags:**
    * `--all` — Include soft-deleted secrets (tombstones) in the output.
    * `--folder <string>` — Filter the list of secrets by a specific folder.
    * `--json` — Format the output as a raw JSON array instead of a CLI table.

#### `goph delete`
Soft-delete an active secret by creating a tombstone. This tombstone will propagate to other devices on the next sync.

* **Usage:** `goph delete <name> [flags]` 
* **Flags:**
    * `--force` — Skip the interactive `[y/N]` deletion confirmation prompt.

---

### Online Synchronization & Trust Commands
These commands require a configured backend connection (`~/.goph/config.yaml`) and synchronize data or manage devices within your account's trust chain.

#### `goph sync`
Bidirectionally synchronize secrets with the remote server. This pulls changes (including tombstones), pushes local updates, handles automatic key resharing for newly authorized devices, and flags concurrent editing conflicts.

* **Usage:** `goph sync` 

#### `goph link`
Link your newly initialized device to your existing account using a high-entropy single-use pairing code generated by an active device.

* **Usage:** `goph link <code>` 

#### `goph device ls`
List all devices linked to your account, displaying their unique ID, descriptive name, authorization status (`pending` | `active` | `revoked`), and their trimmed public `age` key.

* **Usage:** `goph device ls` 

#### `goph device invite`
Generate a temporary, high-entropy pairing code to invite and link a new device to your account without exposing any keys to the server.

* **Usage:** `goph device invite` 
* **Output:** Displays the exact command (`goph link <code>`) to run on the new machine, alongside the pairing expiration timestamp.

#### `goph device revoke`

Revoke authorization for a specific device.

* **Usage:** `goph device revoke <device-id|name>` 
* *Note: Once revoked, you must run `goph sync` from an active device to rotate your cryptographic secrets and lock the revoked device out of future updates.*

---

## Backend Service & Infrastructure
The backend architecture consists of a stateless asynchronous **FastAPI** service, a stateful **PostgreSQL** storage instance, and **dbmate** for schema migration runner orchestration.

We provide a pre-configured `docker-compose.yaml` file under the `/backend` directory for instant local infrastructure spin-up.

### Running via Docker Compose (Recommended)
This is the fastest way to orchestrate the entire development environment, including automatic health checks, database volume mapping, and live reload for source modifications.

#### 1. Setup Environment Configuration
Before spinning up the containers, copy the template environment file and adjust your local credentials:
```bash
cd backend
cp .env.default .env
```

*(By default, `.env` includes development credentials `postgres/docker` for out-of-the-box local setup).*

#### 2. Spin Up the Infrastructure
Start the database and the backend app (with hot reload mounted in `/src` for rapid local development):

```bash
cd backend
docker compose up --build
```

* **Postgres Storage:** Available on the host machine at `localhost:5432`. Data is persisted locally inside the `./postgres-data` directory.
* **Stateless Backend:** Available at `http://localhost:8080`. API specification pages can be visited at `http://localhost:8080/docs`.
* *Note: Database migrations are applied **automatically** by the backend container upon startup.*

#### 3. Run Manual Database Migrations (Optional)

If you need to manually run, verify, or manage migrations without starting the full application server, you can use the dedicated `dbmate` container wrapper:

```bash
# Apply migrations manually using the companion tools profile
docker compose --profile tools run --rm migrations
```

---

### Alternative Manual Run (Host Machine)

If you prefer to run the FastAPI process bare-metal while keeping only the database inside Docker, follow these steps:

1. **Spin up Postgres only:**
```bash
docker compose up -d postgres
```

2. **Initialize Virtual Environment & Packages:**
Make sure you have [uv](https://github.com/astral-sh/uv) installed:
```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r pyproject.toml
```

3. **Run Migrations Locally (requires [dbmate](https://github.com/amacneil/dbmate) binary):**
```bash
dbmate -u "postgresql://postgres:docker@localhost:5432/gophkeeper?sslmode=disable" up
```

4. **Launch the App Server:**
Start the Uvicorn development server locally. We pass the `--env-file` flag so Uvicorn automatically loads your local database credentials and configuration:

```bash
uvicorn gophkeeper.main:app --host 127.0.0.1 --port 8080 --env-file .env --reload
```

---

## REST API Endpoints Overview

### Device Authentication (`auth`)

These endpoints are used by CLI devices to prove ownership of their private key via an **age challenge/response** mechanism without exposing keys to the network.

| Method | Endpoint | Description | Auth Required |
| --- | --- | --- | --- |
| **POST** | `/auth/challenge` | Start login: get base64 challenge ciphertext encrypted to the device's public key | No |
| **POST** | `/auth/verify` | Submit the decrypted challenge nonce to receive a session Bearer token | No |
| **GET** | `/auth/whoami` | Identify the account and device bound to the current session | **Yes** |

---

### Web Account Management (`accounts`)

Web-level credentials management (email/password). These sessions identify the account but hold no cryptographic keys.

| Method | Endpoint | Description | Auth Required |
| --- | --- | --- | --- |
| **POST** | `/accounts` | Register a new account (stores the browser-generated `recovery_pubkey` only) | No |
| **POST** | `/accounts/login` | Log in to an account with email & password to receive a web session token | No |
| **GET** | `/accounts/me` | Fetch the current account's details and its recovery public key | **Yes** |

---

### Zero-Knowledge Sync (`sync`)

Endpoints for pushing and pulling encrypted items. The server relays and orders changes but cannot decrypt payloads.

| Method | Endpoint | Description | Auth Required |
| --- | --- | --- | --- |
| **GET** | `/sync/changes` | Pull encrypted secrets modified since a cursor (`?since=<seq>`) | **Yes** |
| **POST** | `/sync/push` | Batch-push local creations, updates, or tombstones under optimistic concurrency | **Yes** |

---

### Device Enrollment (`enroll`)

Used to link new devices into an existing account utilizing temporary high-entropy pairing codes.

| Method | Endpoint | Description | Auth Required |
| --- | --- | --- | --- |
| **POST** | `/enroll/invite` | Register a client-generated pairing invite (stores code hash and MAC'd roster) | **Yes** |
| **POST** | `/enroll/join` | Consume an invite code to instantly register a new device under the account | No (Code Hash verified) |
| **GET** | `/enroll/invite/{invite_id}` | Poll an invite status to retrieve the join proof (the redeeming device and its join MAC) | **Yes** |

---

### Device Registry (`devices`)

Endpoints to view registered endpoints in the client's account.

| Method | Endpoint | Description | Auth Required |
| --- | --- | --- | --- |
| **GET** | `/devices` | List all devices linked to the caller's account | **Yes** |
| **GET** | `/devices/{device_id}` | Retrieve details of a specific device within the caller's account | **Yes** |

---

### Trust Graph Log (`trust`)

Manages the account's append-only trust log containing signed certificates.

| Method | Endpoint | Description | Auth Required |
| --- | --- | --- | --- |
| **POST** | `/trust/certs` | Publish a signed vouch or revoke certificate (`vouch` / `revoke` log chain) | **Yes (Issuer device)** |
| **GET** | `/trust/certs` | Pull all published trust log certificates since a sequence cursor (`?since=<seq>`) | **Yes** |

---

### Web Dashboard Statistics (`stats` & `health`)

Provides telemetry data for the web UI integration and deployment health probes.

| Method | Endpoint | Description | Auth Required |
| --- | --- | --- | --- |
| **GET** | `/stats/overview` | Fetch static dashboard card counts (passwords, notes, active/revoked devices) | No |
| **GET** | `/stats/activity` | Fetch chronological mock timeline series of events (`?period=[7d|30d|90d]`) | No |
| **GET** | `/stats/security` | Fetch mock aggregate security health, active alerts, and last sync time | No |
| **GET** | `/health` | Liveness check (returns `{"status": "ok"}`) | No |

---

## 🔗 Deployment

* **Production API Endpoint:** [https://api.goph.dev](https://www.google.com/search?q=https://api.goph.dev) *(Replace with actual URL)*
* **Web Dashboard UI:** [https://app.goph.dev](https://www.google.com/search?q=https://app.goph.dev) *(Deferred Stage 5 Web Portal)*

---

## 👥 Tracks & Contribution

### Project Development Track (GitFlow)

We use **GitFlow** branching model:

* Features are developed in isolated branches: `feature/*` -> Merge into `develop` via Pull Request templates.
* Production releases are tagged on `main`.

### Contribution Checklist

When submitting a Pull Request to `develop`, ensure you adhere to the repository standards:

1. **Boundary Separation:** Packages inside `cli/` must **never** import modules from `backend/`. They communicate solely over the network protocol.
2. **Symmetric Data Types:** PostgreSQL database fields must store raw binary `BYTEA` blocks. Base64 encoding/decoding is performed exclusively by the backend service layer.
3. **Commit Signing:** All Git commits must be cryptographically signed using your SSH key.
