## Project Information
**Project:** GophKeeper

**Track:** Industrial
GophKeeper is a distributed zero-knowledge secret management system designed for secure storage, synchronization, and management of sensitive information across trusted devices.

**Frozen commit**

Commit link: https://github.com/svetlana1959/GophKeeper/commit/2cbfa573ff106dcafc1add82a953558d98cf788a

Release link: https://github.com/svetlana1959/GophKeeper/releases/tag/v1.0.0

---

# 1. Final Product Preparation

## 1.1 Critical Fixes After Code Freeze

The commits merged in the run-up to the `v1.0.0` tag were primarily stabilization work rather than feature work: `a7aa6c3` "Lint fix", PR #159 "style/ruff-format" (`ruff format` cleanup across the backend), and PR #160 (final merge of the `dev` integration branch into `main`). These are the last verifiable changes before the freeze.

## 1.2 Final Build Status

- **Tag:** `v1.0.0`
- **Commit SHA:** `2cbfa573ff106dcafc1add82a953558d98cf788a`
- **Released:** 22.07.2026, 12:58
- **Signature:** GPG-signed, Verified badge on GitHub (key ID `B5690EEEBB952194`); tag itself SSH-signed by `arsenez2006` (Arseny Lashkevich)
- **CI pipelines configured for this build:** `ci-backend.yaml`, `ci-cli.yaml`, `ci-frontend.yaml`, `release-cli.yaml` (GoReleaser cross-compilation for CLI releases). Status badges for all three pipelines are published in the root `README.md`.
- **Release history:** `v0.1.0` (30.06.2026) → `v0.2.0` (08.07.2026) → `v1.0.0` (22.07.2026)

## 1.3 Final Product Verification

**CLI (`goph`):** unit tests across the `crypto`, `config`, `vault`, `remote`, `app`, and `commands` packages (including synchronization scenarios in `sync_test.go`), run through `make test` / `make vet` / `golangci-lint` in `ci-cli.yaml`. Coverage is enforced at a minimum of 80% via `go-test-coverage` (commit `0d777ad`) and was subsequently raised to 82% (PR #156 "feature/cli-coverage"), with a live coverage badge added in PR #157.

**Backend:** unit tests (`test_auth_service.py`, `test_account_auth_service.py`, `test_device_service.py`, `test_enrollment_service.py`, `test_secret.py`, `test_sync_service.py`, `test_tokens.py`) and integration tests (`test_device_repository.py`, `test_secret_repository.py`), run against a real PostgreSQL service container in CI, isolated per-transaction for safe parallelism (PR #154, `test(backend): isolate integration tests per-transaction for safe parallelism`). Quality gates: `ruff format --check`, `ruff check`. Test coverage was expanded specifically for the trust log and stats endpoints in PRs #143, #151, #155.

**Frontend:** ESLint (typescript-eslint, flat config) + Prettier (with the Tailwind plugin) + Vitest/Testing Library unit tests + Playwright end-to-end tests (login/register/bad-password flows verified in PR #148).

**Docker Compose:** per the Week 6 report, the backend and database services were successfully built and started using Docker Compose, and the `/health` endpoint confirmed the API was running correctly.


## 1.4 Full Product Functionality

**CLI (`goph`) — offline-first, Go:**

- `goph init` — creates the local SQLite vault and generates a native `age` (X25519) identity keypair; optional `--pin` to protect the private key at rest, optional `--key-file` to import an existing key.
- `goph set` / `goph get` / `goph list` / `goph delete` — create, read, list, and soft-delete (tombstone) secrets; payload resolution order is `--value` → `--file` → stdin → interactive prompt.
- `goph sync` — bidirectional sync: pulls remote changes (including tombstones), pushes local updates, handles automatic key resharing for newly authorized devices, flags concurrent-edit conflicts.
- `goph link <code>` — joins an existing account using a single-use pairing code.
- `goph device ls` / `invite` / `revoke` — device trust management from the CLI.
- All cryptography (encryption/decryption) happens client-side; plaintext never leaves the device.

**Backend — Python, FastAPI, stateless, "blind" storage:**

- Two-tier authentication: `age` challenge/response for devices (`POST /api/auth/challenge`, `POST /api/auth/verify`, `GET /api/auth/whoami`) and email + Argon2id password for the web dashboard (`POST /api/accounts`, `POST /api/accounts/login`).
- Zero-knowledge sync (`GET /api/sync/changes`, `POST /api/sync/push`) — the server orders and relays ciphertext but never decrypts it.
- Device enrollment via single-use, hashed, MAC-protected pairing codes (`POST /api/enroll/invite`, `POST /api/enroll/join`, `GET /api/enroll/invite/{invite_id}`).
- Device registry (`GET /api/devices`, `GET /api/devices/{device_id}`).
- Client-verified device trust graph — append-only log of signed vouch/revoke certificates (`POST /api/trust/certs`, `GET /api/trust/certs`); the server relays the log but cannot verify or forge it.
- Recovery key — a write-once account recovery public key (`PUT /api/accounts/me/recovery`, 409 if already set), separate from everyday device keys.
- Web dashboard statistics/telemetry (`GET /api/stats/overview`, `/activity`, `/security`) and `GET /api/health`.

**Web (React + Vite + TypeScript + TailwindCSS):** public landing page, registration/login (Argon2id-backed), authenticated dashboard (stat cards, trusted devices, pending access requests, recent activity — wired to `/stats/*`), devices page, statistics page (activity chart, secrets-by-type donut), settings (account, appearance/theme, security), secrets page (read-only, metadata-only per the zero-knowledge design — no plaintext ever reaches the browser), and an in-browser add-device flow that generates a recovery key using Web Crypto (X25519) and uploads only its public half.

## 1.5 Architecture

The system is a mono-repo hosting two independent programs — the CLI (Go, `cli/`) and the Backend API (Python, `backend/`) — plus a `shared/` directory reserved for wire-contract DTOs. Per `CONTRIBUTING.md`, the two programs "share a git history and nothing else": code in `cli/` must never import from `backend/` and vice versa; their only contract is the network API.

Both the CLI and the backend follow a hexagonal (ports-and-adapters) layering:

- CLI: `domain` (models + repository interfaces, standard-library only) ← `crypto`, `config`, `vault`, `remote`, `commands` (implementations, depend on `domain`, never the reverse).
- Backend: `domain` / `services` / `infrastructure` / `api` layers.

**Core architectural decision — Zero-Knowledge + mono-repo split:** the server is a "blind" storage orchestrator that never processes unencrypted private keys or raw payloads, keeping the entire cryptographic burden on the client.

**Tech stack:**

| Component | Stack |
|---|---|
| CLI (`goph`) | Go · Cobra · `age` (X25519) · SQLite (local vault) · golangci-lint |
| Backend | Python · FastAPI (async) · SQLAlchemy (async) + asyncpg · PostgreSQL · dbmate migrations · Dynaconf · Uvicorn · ruff |
| Frontend | React 19 · Vite · TypeScript · TailwindCSS v4 · Radix UI primitives · TanStack Query · Zod · React Hook Form · Playwright |
| CI/CD | GitHub Actions (`ci-backend.yaml`, `ci-cli.yaml`, `ci-frontend.yaml`, `release-cli.yaml`) · GoReleaser · Docker / GHCR |

Multi-device sync is implemented via a monotonic per-account sequence cursor (`secret_seq` DB sequence, `seq` column on `secrets`) — clients pull "changes since seq" rather than the whole dataset.

## 1.6 Competitor / Alternative Analysis and Differentiation

The Sprint 2 report established a baseline comparison against the closest existing products, split across the two market segments GophKeeper straddles: human password managers (Bitwarden, 1Password) and DevOps/infrastructure secrets managers (HashiCorp Vault, Infisical).

| Dimension | Bitwarden | 1Password | HashiCorp Vault | Infisical | GophKeeper |
|---|---|---|---|---|---|
| Primary use case | Human password management | Human password management | Machine/DevOps secrets | Machine/DevOps secrets | Distributed secret management for technical users |
| Zero-knowledge approach | Yes | Yes | No | Partial | Yes |
| Client-side encryption | Yes | Yes | No | Partial | Yes |
| Self-hosting | Yes | No | Yes | Yes | Planned (self-hosted deployment already used for the project VM) |
| DevOps-oriented workflow | Limited | Limited | Strong | Strong | CLI-first approach |
| Trusted-device synchronization | Limited | Limited | Not a core focus | Not a core focus | Core feature |

**Identified gap:** existing tools specialize in one segment or the other — Bitwarden/1Password give strong zero-knowledge guarantees but center on human password management; Vault/Infisical serve DevOps workflows but are not zero-knowledge across all scenarios. GophKeeper's differentiation is combining distributed, trusted-device secret management, full client-side encryption, and a CLI-first workflow for technical users in one product.

**Business-model differentiation** (per the team's business model concept document): a dual-licensing strategy (AGPLv3 or SSPL for the self-hosted core, plus a commercial license for Enterprise) targeting both a B2C freemium tier (device/secret limits, $2–4/mo Premium) and a B2B/DevOps tier (free self-hosted Community vs. paid Cloud Enterprise / Self-Hosted Enterprise with RBAC, audit logs, Kubernetes CSI driver, Terraform/OpenTofu integration, and dynamic secrets).

## 1.7 Team Workflow

Per `CONTRIBUTING.md`, the team follows **GitFlow**:

- `main` — production-ready releases only.
- `dev` — integration branch; all work branches from and merges back into `dev`.
- `feature/*` — new features, branched from `dev`.
- `hotfix/*` — urgent production fixes, branched from `main`, merged into both `main` and `dev`.
- `docs/*` — documentation changes.

**Process rules:** all commits must be SSH-signed (Git 2.34+, Ed25519) — unsigned commits are not merged. Pull requests are opened against `dev` (never `main`), must link the issue they resolve, must stay small enough to review, and require at least one approval before merge. Commit messages follow the imperative mood (`feat: add upsert to SecretRepository using ON CONFLICT`).

**Tooling supporting the workflow:** dedicated PR templates (`FEATURE.md`, `HOTFIX.md`) and issue templates (`backlog_task.yaml`, `bug_report.yaml`); backlog and sprint planning tracked on two GitHub Projects boards (`projects/4` — main board, `projects/6` — user stories board).

## 1.8 Research & Validation (Industrial Track)

**Baseline (Sprint 2):** no existing product — GophKeeper started from a blank mono-repo, with only requirements, user stories, mockups, and architectural decisions in place.

**Validation through usability testing (Sprints 4–5):** the team ran individual usability-testing sessions with **five stakeholders**, mixing experienced technical users, less-experienced users, and one international participant, each completing predefined usage scenarios.

Positive findings: the project was judged to address a real security problem; the combination of a CLI client with a zero-knowledge architecture was found technically convincing; the CLI and interface were rated intuitive; the feature set (secure secret storage, encrypted local vault, PIN protection, file-based workflows) was seen as already rich for its stage.

Improvement suggestions turned into backlog items: CLI aliases (`rm` for delete, `-f` for `--force`), a coverage badge/documentation in the README, consistent branch-naming conventions, warnings on recreating a deleted secret, idempotent soft-delete behavior.

**Quantified quality trend across sprints** (from each sprint's own test report):

- Week 4: 74 unit tests / 14 integration tests, all passing; backend coverage first crossed 80%.
- Week 5: 58 backend tests, 77% overall coverage (temporary dip during the account-based architecture redesign).
- Week 6–7: CLI coverage enforced at ≥80%, raised to 82%; backend test suite further expanded across PRs #143, #151, #154, #155 (trust log, stats endpoints, parallel-safe integration tests).

**Documented before/after impact (Week 6 report, Industrial Track Contribution):** *"Before: no existing product... After (this sprint): a working zero-knowledge CLI client with a local encrypted vault and multi-device sync against a hexagonal FastAPI backend; device-trust request/list/approve implemented and closed; a web client covering landing + auth, with a dashboard."* By `v1.0.0` this expanded further to include the client-verified device trust graph, device expiry/heartbeat, the recovery-key flow, and the full TypeScript/Tailwind dashboard.

## 1.9 Improvements Over Weeks 2–6

**Week 2 — Foundation.** Project scope, MVP architecture, user stories (Epics A–H, MoSCoW-prioritized), the competitor baseline comparison above, initial wireframes/mockups, and the first API endpoint stubs. No working functionality yet.

**Week 3 — First implementation pass.** Trusted Devices Management, Account Statistics, and Landing pages built; UUID support integrated across the backend; database connectivity issues resolved; CI pipelines stood up for frontend and backend. Multi-device synchronization was planned but postponed due to backend/infrastructure issues. Digital Inheritance was documented as a planned (not implemented) feature.

**Week 4 — Testing and deployment.** Cryptographic core and encrypted local database landed in the CLI; multi-device access and synchronization implemented on the backend; backend test coverage passed 80% (74 unit / 14 integration tests, all green); Docker images published to GHCR; VM deployment completed (`http://10.93.27.16/`); first round of stakeholder usability testing (5 stakeholders) run and documented.

**Week 5 — Architecture redesign.** The backend's device/secret model was redesigned from "secret belongs to one device" to "secret belongs to an account, devices are trusted members" with an explicit device lifecycle (pending/active/revoked) — enabling secure multi-device sync, safe device onboarding, and independent revocation. Registration and Login pages shipped; mobile UI designed for Registration/Login/Dashboard. Coverage temporarily dipped to 77% (58 tests) during the rewrite.

**Week 6 — Polish and freeze prep.** Multi-device secret synchronization finished end-to-end (PR #126); device-trust request/list/approve closed (issues #41–#43); final testing round (PRs #143, #151); code quality gates (`golangci-lint`, `make vet`/`make test`, `ruff format`/`ruff check`) enforced in CI; documentation finalized; code freeze target set for 22.07.2026.

**Week 6 → v1.0.0 (this report).** On top of the Week 6 state, the team shipped: a full frontend rewrite to TypeScript + Tailwind v4 + Radix + TanStack Query + Zod + Playwright (PR #148, six phases: scaffold → auth → dashboard → devices/landing → statistics/settings → secrets); the recovery-key flow with a write-once `PUT /api/accounts/me/recovery` endpoint (PR #147); the client-verified device trust graph closing the "reshare ZK gap" (PR #145, M4 milestone); device expiry with self-declared TTL, heartbeat, and an inactivity reaper; and the `/api` endpoint prefix migration. This work was tagged as `v1.0.0` on 22.07.2026.

## 1.10 Future Roadmap

Per the current `README.md` (verified against `v1.0.0`), the team's own stated roadmap is:

- Typed secret categories (passwords, cards, notes, files) — the CLI currently stores a generic secret type.
- Digital Inheritance — dead-man's-switch access transfer to a designated beneficiary (specified in `docs/feature_description.md` since Sprint 3; no code yet).
- Backup export / restore.
- Breach-database checks and stale-password alerts.
- Server-side revocation enforcement.
- Browser-based recovery keys.

---

## 1.11 Core Concept
 
**The pitch:** a cloud secret manager built on a Zero-Knowledge architecture — the server never has access to secret contents — using the `age` protocol (described in the concept doc as "an efficient and secure alternative to PGP") instead of a classic single-master-password scheme, combined with a model of distributed trust between a user's own devices, by analogy to how Git/sops handle multi-key encryption. Each device generates its own keypair; access to a shared secret store is granted by adding a new device's public key to the list of authorized recipients for specific secrets.
 
**Two architectural decisions from the concept carried straight into the shipped product:**
 
- **Atomic, per-secret encryption** — each secret (or logical folder) is encrypted as an independent object rather than one monolithic file, specifically to avoid sync "split-brain" conflicts when two devices update different secrets at once, and to allow fine-grained access control per secret/folder. This reasoning is echoed later in `docs/sync_design.md` and realized in the shipped `secret_seq`-based sync cursor (section 1.5).
- **Asynchronous key-exchange queue** — a new device leaves a request (with its public key) in the cloud without needing to be online at the same time as an already-trusted device; the trusted device picks up the request whenever it next comes online, decrypts, re-encrypts to the new device's key, and returns it. This is the same shape as the pairing-code/invite mechanism that shipped (`POST /api/enroll/invite`, `POST /api/enroll/join` — section 1.4), later extended into the client-verified device trust graph (PR #145).
**One open question the concept doc left for later, resolved differently in the shipped product:** the concept floated an optional "hybrid master-password" login — deriving a local master key from a strong password via Argon2id and storing an encrypted copy of that key on the server — explicitly flagged in the document itself as a trade-off ("reduces the overall Zero-Knowledge security level... introduces a classic brute-force vulnerability... if the cloud database is fully compromised"), with the decision left open. The shipped product did not take that trade-off; instead it ships a **separate recovery key** — an offline key independent of the password/device keys, with only its public half ever uploaded to the server (`PUT /api/accounts/me/recovery`, section 1.4) — avoiding the exact brute-force exposure the concept doc had flagged.
 
**Business framing** (`business_model_and_licensing.pdf`): the concept was pitched from the start as straddling two markets — B2C password management (positioned against Bitwarden/1Password) and B2B/DevOps secrets management (positioned against HashiCorp Vault/Infisical) — the same two-segment framing used in the competitor analysis in section 1.6, plus the dual-licensing (AGPLv3/SSPL + commercial) and freemium/tiered monetization model summarized there.
 
---

## 2.3 Video Structure
 
### 1. Problem Statement and Solution
Scene 1 — cold open (0:00–0:20): Malik is shown at his laptop, surrounded by scattered password notes and browser tabs, visibly desperate; the frame freezes on him in black-and-white. Voiceover (Emil): *"This is Malik. A backend developer. Keeper of 67 passwords. He remembers exactly one of them. Even he couldn't guess which service it was for."* ... *"And Malik isn't the only one."* Scene 2 (0:20–0:35): Arseny enters, sits next to Malik, looks into camera: *"Fortunately, we've already solved this. Meet GophKeeper."* Quick cut to the logo/landing page. Scene 3 — Title Card (0:35–0:40): project name + tagline, Industrial track, team names and roles on screen. Scene 4 — Problem Statement & Solution proper (0:40–1:05), voiceover Svetlana, over b-roll of scattered logins, a password list, and a data-breach headline: passwords live everywhere; existing password managers still require trusting the server; GophKeeper encrypts everything client-side and synchronizes only ciphertext between devices — "even we cannot read the secrets."
 
### 2. Target Audience
The scenario has no dedicated "Target Audience" scene or line of dialogue, so this is read off what Scenes 5 and 6 actually show rather than stated outright. Both scenes are built entirely around the CLI: the Key Features segment (Scene 5) is narrated over `init`/`set`/`get`/`list`/`delete`/`device`/`link`/`sync` and hexagonal-architecture terminology, and the core of the Live Demo (Scene 6) is a terminal walkthrough narrated by the CLI engineer, Arseny — signalling a technical, CLI-first audience (developers, DevOps engineers managing API keys and `.env`-style secrets). The only end-user-facing surface in the scenario is the brief web portion of Scene 6 (landing → registration → login → dashboard, voiced by Elina), which points to a secondary audience: people who want multi-device secret access without touching a terminal.
 
### 3. Industrial Track and Acceptance Criteria
Scene 3 (Title Card, 0:35–0:40) puts "track — Industrial" on screen alongside the project name and team roles, and the two scenes bracketing it carry the substance of an acceptance-criteria case even without a checklist graphic — Scene 4 (Problem Statement & Solution) states the gap being closed (server-side trust required by existing tools vs. GophKeeper's client-side-only encryption).

### 4. Key Features and Technology Stack
Scene 5 (1:05–1:45). Features, voiced by Arseny: client-side `age` encryption with a local SQLite vault (plaintext never leaves the device); the CLI surface (`init`, `set`, `get`, `list`, `delete`, `device`, `link`, `sync`); multi-device synchronization; the backend never decrypting anything, storing only version and timestamp metadata to resolve which copy is newest; the zero-knowledge device trust chain (enrollment/invites). Stack, voiced by Aleksander ("Саша"): CLI — Go, `age`, SQLite, hexagonal architecture; Backend — FastAPI, SQLAlchemy, PostgreSQL, dbmate migrations, Dynaconf; Frontend — React + Vite; CI/CD — GitHub Actions (separate cli/backend/frontend pipelines), GoReleaser; Docker for local/VM deployment.
 
### 5. Live Demo
Scene 6 (1:45–5:15). CLI demo — recorded and narrated by Arseny: `goph init` (device identity + local vault), `goph set github --value ****` (secret encrypted client-side on save), `goph get github` (decrypt and read), `goph list` (server sees only metadata) — then `goph device link` and `goph sync` across a second device, showing sync without any decrypted byte touching the server. Web portion — voiceover by Elina, showing the landing page, registration, login, and dashboard.
 
### 6. Industrial Track Highlight
Scene 7 (5:15–5:40), voiced by Malik over a before/after diagram. Before: secrets in text files, unencrypted environment variables, and messaging apps. After: a single zero-knowledge storage-and-sync system where even the server (and its owners) cannot read the secrets. 

 
### 8. Future Work
Scene 8 (5:40–6:00), voiced by Emil: optional features — integrations with various services, Digital Inheritance (access transfer to a trusted person on prolonged owner inactivity).
 
### 9. Team Contributions
Scene 9 (6:00–6:20), voiced by Svetlana over on-screen name/role cards: Svetlana — Team Lead (backlog prioritization, sprint/release coordination, reports, editing); Elina — design (Figma) and report documentation; Arseny — DevOps (CI/CD, releases, deployment); Aleksander — CLI (encryption, synchronization); Emil — Frontend (landing, auth, web client); Malik — Backend (domains, services, API).
 
**Beyond the nine required sections**, the scenario also has a Scene 10 (Outro, 6:20–6:40 — logo, repo QR code, "Thanks for watching") and a Scene 11 (Final Shot, 6:40–7:00) where Malik "unfreezes" from the cold open and delivers the payoff line: *"Out of 67 passwords, only one remains. The other 66 are now in GophKeeper."*
 
---
 
# 3. Video Production
 
| Team Member | Project Role | Narration / Video Section | Recording / Screen Capture / Editing Responsibility |
|---|---|---|---|
| Svetlana Maltseva | Team Lead, Product Manager | Problem Statement & Solution voiceover (Scene 4); Team Contributions voiceover (Scene 9) |
| Elina Akhmetzyanova | Design, Documentation | Live Demo — web-portion voiceover (Scene 6): landing, registration, login, dashboard | 
| Arseny Lashkevich | DevOps Engineer | On-camera pitch line (Scene 2); Key Features & Stack — features (Scene 5); Live Demo — CLI portion (Scene 6) | 
| Aleksander Goncharov | CLI Engineer | Key Features & Stack — tech stack (Scene 5)  |
| Emil Nabiullin | Frontend Developer | Cold-open voiceover (Scene 1); Future Roadmap voiceover (Scene 8) |
| Malik Nurullin | Backend Developer | On-camera, non-speaking, cold open (Scene 1); Industrial Track Highlight voiceover (Scene 7); delivers the closing line in the Final Shot (Scene 11)  |

---

# 4. Team Contributions

| Team Member | Role | Final Product Contribution | Final Video Contribution |
|---|---|---|---|
| Svetlana Maltseva | Team Lead, Product Manager | Sprint planning and backlog management across all sprints; final demo scenario; sprint/final reports (Issues #141, #138, and equivalents each sprint) | Problem Statement and Target Audience narration; Team Contributions segment; oversees final video assembly |
| Elina Akhmetzyanova | Design, Documentation |Responsible for UI/UX design and documentation. Designed the GophKeeper desktop and mobile interfaces in both light and dark themes, created the project landing page, prepared UI mockups for core application flows, and contributed to the project reports and documentation | Challenges & Lessons Learned narration; visual/title sequence |
| Arseny Lashkevich | DevOps Engineer | Owns and maintains all CI pipelines (`ci-backend`, `ci-cli`, `ci-frontend`, `release-cli`) and Docker builds for cli/backend/frontend; approved the device-trust/sync PR (#121); led the M4 device trust graph (PR #145); release manager — signed and published `v0.1.0`, `v0.2.0`, and `v1.0.0` | Cold-open pitch appearance; Track/Acceptance Criteria and architecture/DevOps narration |
| Aleksander Goncharov | CLI Engineer | Delivered multi-device secret synchronization (`app/sync.go`, PR #126) and the local vault/crypto/remote layers; drove CLI test coverage to 82% with an enforced 80% floor and a live coverage badge (PRs #156, #157) | Leads and narrates the CLI Live Demo segment |
| Emil Nabiullin | Frontend Developer | Shipped the original landing page, adaptive layout, and registration/authorization pages (PRs #116, #134, #136, Issue #109); the subsequent full TypeScript/Tailwind frontend rewrite and dashboard (PR #148) and the recovery-key/add-device flow (PR #147) were merged under the GitHub handle `Perchinka`, consistent with the Frontend Developer role | Cold-open voiceover; leads the Web Live Demo segment |
| Malik Nurullin | Backend Developer | Implemented the account/device/secret/sync services and repositories on FastAPI + SQLAlchemy (PR #121) | Cold-open "victim" role and its payoff shot; Industrial Track Highlight (before/after) narration |


---

# 5 Final Links

| Deliverable | Link |
|---|---|
| Final video | |
| Final Presentation| https://disk.yandex.ru/i/P3fEyvHSTdwPkw | 
| Final deployed version | http://10.93.27.16/ |
| Final codebase | https://github.com/svetlana1959/GophKeeper — frozen at https://github.com/svetlana1959/GophKeeper/commit/2cbfa573ff106dcafc1add82a953558d98cf788a (tag `v1.0.0`) |
| README | https://github.com/svetlana1959/GophKeeper/blob/main/README.md |
| API documentation | Swagger UI: `http://10.93.27.16/docs` (or `http://localhost:8080/docs` locally); OpenAPI schema: `/openapi.json` |
| Figma | https://www.figma.com/design/e9yJfGqSkREVk5sjPocKHN/Untitled?node-id=0-1&t=u4j6RSIVCZZWmd5j-1 |
| Other final documentation | `CONTRIBUTING.md`, `docs/technical_decisions.md`, `docs/sync_design.md`, `docs/user_stories.md`, `docs/feature_description.md` (all in the repository root `docs/`) |
