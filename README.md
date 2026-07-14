# GophKeeper Secret Manager (End-to-End Zero-Knowledge Sync)
![GitHub License](https://img.shields.io/github/license/svetlana1959/GophKeeper)
[![Go Version](https://img.shields.io/github/go-mod/go-version/svetlana1959/GophKeeper?filename=cli%2Fgo.mod)](https://go.dev/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)\
[![CI CLI](https://github.com/svetlana1959/GophKeeper/actions/workflows/ci-cli.yaml/badge.svg)](https://github.com/svetlana1959/GophKeeper/actions/workflows/ci-cli.yaml)
[![CI Backend](https://github.com/svetlana1959/GophKeeper/actions/workflows/ci-backend.yaml/badge.svg)](https://github.com/svetlana1959/GophKeeper/actions/workflows/ci-backend.yaml)
[![CI Frontend](https://github.com/svetlana1959/GophKeeper/actions/workflows/ci-frontend.yaml/badge.svg)](https://github.com/svetlana1959/GophKeeper/actions/workflows/ci-frontend.yaml)

A secure, local-first, end-to-end encrypted secret manager utilizing **age (X25519)** encryption. Designed under a strict **Zero-Knowledge model**, the server acts as a blind, stateless storage orchestrator that never processes or holds unencrypted payloads or private keys.

---

## 🌟 Features

* **Zero-Knowledge Architecture:** Payloads are encrypted client-side using `age` (X25519 AEAD) before transmission. The server only sees opaque binary blocks (`BYTEA`) and non-secret metadata.
* **Multi-Device Synchronization:** Declarative sync loop using monotonic sequence cursors (`seq`) preventing race conditions and clock skew.
* **Secure Device Linking:** Two-command pairing flow utilizing high-entropy single-use pairing codes to prevent Server MITM.
* **Dual-Tier Authority Model:** Standard operations use local device keys. Critical actions (revoking other devices, account recovery) require an offline **Recovery Key**.
* **Cryptographic Challenge-Response Auth:** Elimination of static tokens or passwords via `age`-encrypted nonce verification.
* **Local-First Design:** Fully functional offline CLI. Local secrets, device states, and trust graphs are stored in a local SQLite database.

---

## 🏗️ Tech Stack

### Client (CLI)
* **Language:** Go (Golang) — for static compilation, memory safety, and cross-platform native execution.
* **Storage:** **SQLite** — for offline transactional storage of local trust graphs and local metadata.
* **Configuration:** **YAML** — human-readable configuration file for user-modifiable settings (endpoints, logs).
* **Cryptography:** Modern `age` (X25519) encryption primitives.

### Server (Backend)
* **Framework:** **FastAPI** — high-performance asynchronous ASGI presentation layer.
* **ORM & Driver:** **SQLAlchemy (Async)** + **asyncpg** — non-blocking database queries.
* **Database:** **PostgreSQL** — native binary storage (`BYTEA`), logical flags (`BOOLEAN`), and concurrent conflict resolution (`ON CONFLICT`).
* **Package Management:** **uv** — lightning-fast workspace compiler.
* **Configuration:** **Dynaconf** — layered environment-specific configuration management.
* **Database Migrations:** **dbmate** — framework-agnostic, SQL-first migration runner.

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

## 🖥️ Backend Service: Local Spin-up

### Prerequisites

* Python 3.11+
* PostgreSQL 15+ or Docker
* `dbmate` migration tool installed locally

### Setup Instructions

1. **Clone & Configure Workspace:**
```bash
cd backend
# Install dependencies using uv
uv venv
source .venv/bin/activate
uv pip install -r pyproject.toml

```


2. **Environment Variables:**
Create a `.env` file in the `backend/` root directory:
```env
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/goph_db?sslmode=disable"
ENV_FOR_DYNACONF="development"

```


3. **Run Database Migrations:**
We use `dbmate` for keeping database schema tracks in pure SQL:
```bash
dbmate -u "postgresql://postgres:postgres@localhost:5432/goph_db?sslmode=disable" up

```


4. **Start Development Server:**
```bash
uvicorn src.main:app --reload --port 8000

```


Once started, interactive API Swagger documentation is available at `http://localhost:8000/docs`.

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
