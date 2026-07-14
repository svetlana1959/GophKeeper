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

### Command Reference

#### 1. Initialize Local Vault

Sets up the local SQLite storage and generates your device's unique `age` keypair. Fully functional offline.

```bash
goph init

```

#### 2. Link a New Device

To link a secondary device to your account, generate an invite on an **existing (active) device**:

```bash
goph device invite
# Output: Run on your new device (expires 10m): goph link <pairing-code>

```

Then run the generated command on the **new device**:

```bash
goph link <pairing-code>

```

#### 3. Synchronize Secrets

Pushes local modifications and pulls remote changes since your last synchronized sequence cursor:

```bash
goph sync

```

#### 4. Manage Devices & Revocation

List all registered devices and their status:

```bash
goph device ls

```

To self-revoke a device you are currently on:

```bash
goph device revoke

```

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

## 🔌 REST API Endpoints Overview

| Method | Endpoint | Description | Auth Required |
| --- | --- | --- | --- |
| **POST** | `/accounts` | Register a new account (stores `recovery_pubkey` only) | No |
| **POST** | `/auth/challenge` | Request an age-encrypted challenge nonce | No |
| **POST** | `/auth/verify` | Prove challenge decryption to receive session token | No |
| **GET** | `/sync/changes` | Pull changes since the last sequence ID (`?since=<seq>`) | **Yes** |
| **POST** | `/sync/push` | Batch-push locally updated or deleted secrets | **Yes** |
| **POST** | `/enroll/invite` | Generate a single-use pairing code | **Yes** |
| **POST** | `/enroll/join` | Consume pairing code to link a pending device | No (Code Verified) |

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
