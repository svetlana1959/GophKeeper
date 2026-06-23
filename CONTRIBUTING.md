# Contributing to GophKeeper

Thanks for contributing. This guide covers commit signing, branching, and the
architectural boundaries the project relies on. Please read it before opening a
pull request.

## Getting Started

The repository holds two independent programs: the **CLI client** (Go, in `cli/`)
and the **Backend API** (Python, in `backend/`). They share a git history and
nothing else.

To build and test the CLI:

```bash
cd cli
make build      # build ./bin/goph
make test
make vet
```

`make vet` and `make test` must pass before you open a pull request.

## Commit Signing

All commits must be signed. We use SSH signing (Git 2.34+), which does not
require a separate GPG keyring. Unsigned commits will not be merged.

### 1. Generate an Ed25519 key (if you don't have one)

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

### 2. Configure Git

```bash
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
git config --global commit.gpgsign true
git config --global tag.gpgsign true
```

### 3. Register the key as a Signing Key on GitHub

GitHub treats authentication keys and signing keys as separate roles. A key
added for authentication will not verify signatures — add it again as a signing
key, or your commits will show as "Unverified".

1. Go to **Settings → SSH and GPG keys → New SSH key**.
2. Set **Key type** to **Signing Key**.
3. Paste the contents of `~/.ssh/id_ed25519.pub` and save.

After this, commits should show a "Verified" badge on GitHub.

## Branching Model

We use GitFlow.

- `main` — production-ready releases only.
- `dev` — integration branch; all work branches from and merges back into `dev`.
- `feature/*` — new features. Branch from `dev`, merge into `dev`.
- `hotfix/*` — urgent production fixes. Branch from `main`, merge into `main` and `dev`.
- `docs/*` — documentation. Branch from `dev`, merge into `dev`.

### Workflow

```bash
git switch dev
git pull origin dev
git switch -c feature/implement-secret-repository
# ... commits ...
git push origin feature/implement-secret-repository
```

Write commit messages in the imperative mood
(e.g. `feat: add upsert to SecretRepository using ON CONFLICT`). Open pull
requests against `dev`, never `main`. Link the issue the PR resolves, and keep
PRs small enough to review. At least one approval is required before merge.

## Architecture

### Directory Structure

```text
.
├── backend             # Backend API service (Python)
├── cli                 # CLI client (Go)
│   ├── main.go         # Entry point
│   └── internal        # Private packages (not importable outside cli/)
│       ├── commands    # CLI commands, flags, user I/O
│       ├── domain      # Models, behavior, and repository interfaces (ports)
│       ├── crypto      # age key generation and the DEK envelope
│       ├── config      # Client configuration
│       ├── vault       # Local SQLite store (implements domain ports)
│       └── remote      # HTTP client for the backend
├── docs                # Documentation
└── shared              # Wire-contract DTOs shared between CLI and backend
```

### Dependency Rule

`domain` defines the model and the interfaces (ports) it requires. It depends
only on the standard library - never on age, SQLite, or HTTP. The other
packages (`crypto`, `config`, `vault`, `remote`, `commands`) implement those
interfaces and depend on `domain`, not the reverse. 

```go
var _ domain.SecretRepository = (*SecretRepo)(nil)
```

### Cross-Boundary Rule

Code in `cli/` must never import from `backend/`, and vice versa. They are
isolated systems that happen to share a repository; their only contract is the
network API.
