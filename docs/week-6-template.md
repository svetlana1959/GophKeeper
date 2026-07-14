# Sprint 6 Report
## Project Information
### Track
Industrial
### Project
GophKeeper — a distributed zero-knowledge secret management system designed for secure storage, synchronization, and management of sensitive information across trusted devices.
### Sprint
Week 6

---
# Team Members and Contributions
| Team Member | Role | Contribution |
|-------------|------|-------------|
| Svetlana Maltseva | Team Lead, Product Manager | Sprint planning Week 6, final demo scenario, Sprint 6 report (Issues: #141, #138) |
| Elina Akhmetzyanova | Design, Documentation | Sprint 6 report template, mobile/desktop design refinement (Issues: #142, #139) |
| Arseny Lashkevich | DevOps Engineer | Maintains the per-component CI pipelines (`ci-backend`, `ci-cli`, `ci-frontend`, `release-cli`) and Docker builds for cli/backend/frontend; approved the device-trust/sync PR (#121). Wrote README. (Issue #14) |
| Aleksander Goncharov | CLI Engineer | Delivered multi-device secret synchronization (`app/sync.go`, PR #126) and the local vault/crypto/remote layers (PR #126) |
| Emil Nabiullin | Frontend Developer | Shipped the landing page, adaptive layout, and registration/authorization pages (PRs: #116, #134, #136; Issue: #109) |
| Malik Nurullin | Backend Developer | Implemented the account/device/secret/sync services and repositories on FastAPI + SQLAlchemy; PR #121

---
# Sprint Goal
Finalize the project, freeze the scope, and prepare the application for release.

---
# Final Project Polish
## Completed Features
- Multi-device secret synchronization between the Go CLI and the FastAPI backend (PR #126).
- Core CLI workflow end-to-end: `init`, `set`, `чёget`, `list`, `delete`, `device`, `link`, `sync`, with client-side `age` encryption and a local SQLite vault — plaintext never leaves the device.
- Backend zero-knowledge API: registration/login (`auth_service`, `account_auth_service`), device enrollment/invites, and secret CRUD, all behind hexagonal domain/service/infrastructure layers with 8 applied DB migrations.
- Web authentication flow: registration and login pages, plus a redesigned landing page with adaptive layout (PRs #116, #134, #136).
- Device trust — request, list-requests, and approve are implemented and closed (Issues #41, #42, #43)
---
## Final Testing
### Testing Summary
- CLI: unit tests exist across `crypto`, `config`, `vault`, `remote`, `app` (including a large `sync_test.go`), run via `make test` / `make vet` in CI (`ci-cli.yaml`).
- Backend: PR #121 adds unit coverage for device, access-request, and API-schema/route logic, and reports backend coverage above 80% (`make lint` and `make test` passing per the PR description)

---
## Code Quality
### Code Cleanup
- Go side enforces `golangci-lint` (`.golangci.yml`) and `make vet`/`make test` as PR gates
- Backend enforces `ruff format --check` + `ruff check` via `make lint`; PR #121 includes a dedicated "style: apply ruff formatting" commit

### Comments and Refactoring
- Go packages include `doc.go` files per package (`crypto`, `vault`, `remote`, `config`) documenting purpose, consistent with the Definition of Done's "every exported function/type/package documented."

---
###  Code Freeze Date: 22.07.2026



---
# Documentation Finalization
## README
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

- The root `README.md`link: https://github.com/svetlana1959/GophKeeper/blob/main/README.md

---
## API Documentation
### Final Updates
# !МАЛИК ТУТ НАПИШИ!

---
## UI/UX Documentation
### Figma Design
Link: https://www.figma.com/design/e9yJfGqSkREVk5sjPocKHN/Untitled?node-id=0-1&t=u4j6RSIVCZZWmd5j-1

### Login Mobile
<img width="818" height="868" alt="login_mob" src="https://github.com/user-attachments/assets/51c37e0d-10bf-40a9-914e-b6a4ed1dda59" />

### Registration Mobile
<img width="832" height="880" alt="reg_mob" src="https://github.com/user-attachments/assets/6486b139-109f-4af8-bd16-fb40f96f2df1" />

### Dashboard Mobile
<img width="652" height="1200" alt="dash_mob" src="https://github.com/user-attachments/assets/0070704f-238a-47cc-a903-148659275d41" />

### Secret Mobile and Mobile Password
<img width="1186" height="800" alt="secret_mob_and_mob_passw" src="https://github.com/user-attachments/assets/d92cd13a-588b-4cd6-8c6c-2d94c7d0cc47" />

### Mobile Password Delete
<img width="1218" height="760" alt="mob_passw_delete" src="https://github.com/user-attachments/assets/07538dfd-4a58-4f16-89f8-6ab235b9b457" />

### Additional Mobile Details Design
<img width="1280" height="578" alt="addition" src="https://github.com/user-attachments/assets/d87ff3ea-2370-442a-870d-b17e79e9457f" />

### Password edit Desktop 
<img width="1192" height="886" alt="password_edit" src="https://github.com/user-attachments/assets/c29f7868-cb20-4cc7-9b80-5e09bf72a5f9" />


---
## Industrial Track Contribution
### Before / After Impact
- **Before:** no existing product — GophKeeper started from a blank mono-repo (per `CONTRIBUTING.md`'s architecture doc and `docs/user_stories.md` backlog).
- **After (this sprint):** a working zero-knowledge CLI client with a local encrypted vault and multi-device sync against a hexagonal FastAPI backend; device-trust request/list/approve implemented and closed; a web client covering landing + auth, with a dashboard. 

---
# Release Readiness
## Deployment Verification
### VM Status
VM host: `10.93.27.16`. This is a private/internal address — it responded when checked, but which build/commit is currently deployed there was not independently confirmed. DevOps (Arseny) to confirm the deployed version matches the state cited in this report before submission.

### Live Application
Link: http://10.93.27.16/

---
## Reproducibility
### Deployment Instructions
!АРСЕНИЙ ТУТ НАПИШИ!

### Docker Verification
!МАЛИК ТУТ ТОЖЕ НАПИШИ!

---
## Final Validation Checklist
| Item | Status |
|------|--------|
| README finalized | finished |
| API documentation completed | finished |
| Figma updated | Mobile screens for login, registration, dashboard, secret view, and password deletion are available |
| VM deployment verified | VM host known (`10.93.27.16`) |
| Docker deployment verified | Per-component Docker setups exist |
| Code freeze completed | Code freeae date: 22.07.2026 |

---
# Final demo scenario

## In English:

## SCENE 1 — Introduction/Warm-up (0:00–0:20)
Malik is sitting at his laptop; scraps of paper and sticky notes with passwords are scattered around, and there are dozens of browser tabs open. He looks utterly desperate. The camera slowly moves toward him. Malik types furiously, stares at the ceiling, and clutches his head in frustration. At the peak of his despair, the frame freezes in black and white.

**Voiceover (Emil):**
> "This is Malik. A backend developer. Keeper of 67 passwords. He remembers exactly one of them. Even he couldn't guess which service it was for."

*(brief pause; Malik remains the only one on screen)*

**Emil:**
> "And Malik isn't the only one."

---

## SCENE 2 — Introducing the Solution (0:20–0:35)
Arseniy enters the room, sits next to Malik, and looks confidently into the camera.

**Arseniy:**
> "Fortunately, we've already solved this. Meet GophKeeper."

Quick cut to the logo or landing page.

---

## SCENE 3 — Title Card (0:35–0:40)
Project name + tagline on screen; **Industrial**-style music plays; team names and roles are displayed.

---

## SCENE 4 — Problem Statement & Solution (0:40–1:05)
**Voiceover (Sveta)** plays over visuals: logins for various services, a password list, and a screenshot of a news story about a data breach.

- Passwords are scattered everywhere: in notes, files, and your head.
- Existing password managers still require you to trust the server—theoretically, it can see decrypted data.
- GophKeeper encrypts everything client-side and synchronizes only the encrypted text between devices. Even we cannot read the secrets.

---

## SCENE 5 — Key Features & Tech Stack (1:05–1:45)
On-screen display: features (3–5 seconds per feature).

**Arseniy:**
- Client-side encryption via `age`, local SQLite vault — plaintext never leaves the device.
- CLI: `init`, `set`, `get`, `list`, `delete`, `device`, `link`, `sync` *(briefly explain each if time permits)*.
- Multi-device synchronization.
- The backend performs no decryption: it receives an already encrypted data block from the client and simply stores it — along with a version and timestamp used solely to determine the most recent copy during device synchronization.
- Zero-knowledge trust chain between devices (enrollment/invites).

**Sasha** — stack (cards/icons):
- CLI: Go, `age`, SQLite, hexagonal architecture (domain/ports/adapters).
- Backend: FastAPI, SQLAlchemy, PostgreSQL, dbmate migrations, Dynaconf.
- Frontend: React + Vite.
- CI/CD: GitHub Actions (separate pipelines for CLI/backend/frontend), GoReleaser for CLI releases.
- Docker for local/VM deployment.

---

## SCENE 6 — Live Demo (1:45–5:15)
**CLI demo (Arseniy recording and narrating):**

```sh
goph init                     # device setup: identity + local vault
goph set github --value ****  # save secret
goph get github               # read and decrypt
goph list                     # list metadata without decryption
```

Show on the terminal screen while narrating:
- "Here I'm initializing the device—a key pair is generated."
- "I'm saving a secret—it gets encrypted on the client side immediately."
- "I'm viewing the list—the server sees only metadata, not the content."

Then — multi-device synchronization:

```sh
goph device link   # link a new trusted device
goph sync          # synchronize secrets
```

> "And now, the same thing is visible from the second device—without a single byte of decrypted data passing through the server."

**Elina** — voiceover; show: landing page, registration, login, dashboard, etc.

---

## SCENE 7 — Industrial Track Highlight: Before/After (5:15–5:40)
Voiceover; on-screen: "Before/After" diagram or table.

**Malik:**
- **Before:** secrets stored in text files, unencrypted environment variables, and messaging apps.
- **After:** a unified zero-knowledge storage and synchronization system, guaranteeing that even the server (and its owners) cannot read the secrets.

---

## SCENE 8 — Future Roadmap (5:40–6:00)
**Emil**, voiceover:
- Optional features: integration with various services, Digital Inheritance (transferring access to a trusted person in the event of owner inactivity).

---

## SCENE 9 — Team Contributions (6:00–6:20)
**Sveta** (voiceover), with a graphic or text displayed on screen:
- Svetlana — Team Lead: backlog prioritization, sprint and release coordination, reporting, video editing.
- Elina — Design (Figma) and report documentation.
- Arseniy — DevOps: CI/CD, releases, deployment.
- Alexander — CLI: encryption, synchronization.
- Emil — Frontend: landing page, authentication, web client.
- Malik — Backend: domains, services, API.

---

## SCENE 10 — Outro (6:20–6:40)
Logo, a QR code linking to the repository, and the text "Thanks for watching" — (optional: use Photoshop to add the team members surrounding the text giving a "thumbs-up" 👍).

---

## SCENE 11 — Final Shot (6:40–7:00)
The shot from the first scene where Malik was "frozen" — he unfreezes, turns around, and says:

**Malik:**
> "Out of 67 passwords, only one remains. The other 66 are now in GophKeeper."

*(gives the signature "thumbs-up" 👍)*

## In Russian:

# Final demo scenario

## СЦЕНА 1 — Введение, прогрев (0:00–0:20)
Малик сидит за ноутбуком, вокруг разбросаны бумажки/стикеры с паролями, куча вкладок в браузере, лицо — отчаяние. Камера медленно движется к Малику. Малик стучит по клавиатуре, смотрит в потолок, руками берётся за голову — очень отчаян. На пике отчаяния — кадр замирает в чёрно-белом фильтре.

**Закадровый голос (Эмиль):**
> "Это Малик. Backend-разработчик. Хранитель 67 паролей. Помнит из них — один. Угадать, от чего именно, не смог даже он сам."

*(небольшая пауза, всё ещё только Малик в кадре)*

**Эмиль:**
> "И ведь Малик — не единственный."

---

## СЦЕНА 2 — Появление решения (0:20–0:35)
Арсений заходит в комнату, садится рядом с Маликом, уверенно смотрит в камеру.

**Арсений:**
> "К счастью, мы уже это решили. Знакомьтесь — GophKeeper."

Быстрый переход на логотип или лендинг.

---

## СЦЕНА 3 — Title Card (0:35–0:40)
Название проекта + один слоган на экране, трек — **Industrial**, имена команды и роли.

---

## СЦЕНА 4 — Problem Statement & Solution (0:40–1:05)
**Голос (Света)** на фоне: логины в разные сервисы, лист с паролями, скриншот новости про утечку.

- Пароли живут где попало: в заметках, файлах, голове.
- Готовые менеджеры паролей всё равно требуют доверять серверу — он теоретически видит расшифрованные данные.
- GophKeeper шифрует всё на стороне клиента и синхронизирует между устройствами только зашифрованный текст. Прочитать секреты не можем даже мы.

---

## СЦЕНА 5 — Key Features & Tech Stack (1:05–1:45)
Показывать на экране: фичи (каждая — 3–5 сек на экране).

**Арсений:**
- Client-side шифрование через `age`, локальный SQLite vault — plaintext никогда не покидает устройство.
- CLI: `init`, `set`, `get`, `list`, `delete`, `device`, `link`, `sync` *(про каждый кратко рассказать, если будет время)*.
- Мультиустройственная синхронизация.
- Backend ничего не расшифровывает: получает от клиента уже зашифрованный блок данных и просто хранит его — вместе с версией и меткой времени, нужными только чтобы понять, какая копия свежее при синхронизации между устройствами.
- Zero-knowledge trust chain между устройствами (enrollment/invites).

**Саша** — стек (карточки/иконки):
- CLI: Go, `age`, SQLite, гексагональная архитектура (domain/ports/adapters).
- Backend: FastAPI, SQLAlchemy, PostgreSQL, dbmate-миграции, Dynaconf.
- Frontend: React + Vite.
- CI/CD: GitHub Actions (отдельные пайплайны под cli/backend/frontend), GoReleaser для релизов CLI.
- Docker для локального/VM-деплоя.

---

## СЦЕНА 6 — Live Demo (1:45–5:15)
**CLI-демо (записывает и рассказывает Арсений):**

```sh
goph init                     # настройка устройства: identity + локальный vault
goph set github --value ****  # сохранить секрет
goph get github               # прочитать и расшифровать
goph list                     # список метаданных без расшифровки
```

Показать на экране терминала, комментируя вслух:
- "Вот я инициализирую устройство — генерируется ключевая пара."
- "Сохраняю секрет — он сразу шифруется на клиенте."
- "Смотрю список — сервер видит только метаданные, не содержимое."

Затем — мультиустройственная синхронизация:

```sh
goph device link   # привязка нового доверенного устройства
goph sync          # синхронизация секретов
```

> "А теперь то же самое видно со второго устройства — без единого байта расшифрованных данных, прошедшего через сервер."

**Элина** — закадровый голос, показать: лендинг, регистрацию, логин, дашборд и т.п.

---

## СЦЕНА 7 — Industrial Track Highlight: Before/After (5:15–5:40)
Закадровый голос, на экране — диаграмма или таблица "было / стало".

**Малик:**
- **До:** секреты — в текстовых файлах, переменных окружения без шифрования, в мессенджерах.
- **После:** единая zero-knowledge система хранения и синхронизации с гарантией, что даже сервер (и его владельцы) не могут прочитать секреты.

---

## СЦЕНА 8 — Future Roadmap (5:40–6:00)
**Эмиль**, закадровым голосом:
- Опциональные фичи: интеграция с различными сервисами, Digital Inheritance (передача доступа доверенному лицу при неактивности владельца).

---

## СЦЕНА 9 — Team Contributions (6:00–6:20)
Закадрово **Света**, на экране табличка или текст:
- Светлана — Team Lead: приоритизация бэклога, координация спринтов и релизов, репорты, монтаж.
- Элина — дизайн (Figma) и документация репортов.
- Арсений — DevOps: CI/CD, релизы, деплой.
- Александр — CLI: шифрование, синхронизация.
- Эмиль — Frontend: лендинг, авторизация, веб-клиент.
- Малик — Backend: домены, сервисы, API.

---

## СЦЕНА 10 — Outro (6:20–6:40)
Логотип, ссылка на репозиторий QR-кодом и надпись "Спасибо за просмотр" — можно фотошопом добавить, что вокруг надписи все показывают жест ЛАЙК 👍.

---

## СЦЕНА 11 — Финалочка (6:40–7:00)
Кадр, где Малик "завис" из первой сцены — отвисает, поворачивается и говорит:

**Малик:**
> "Из 67 паролей остался один. Остальные 66 — теперь в GophKeeper."

*(показывает фирменный жест ЛАЙК 👍)*

---
# Relevant Links
### Issues:
- #139 - Write Sprint 6 template - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=211720319&issue=svetlana1959%7CGophKeeper%7C139
- #138 - Write Sprint 6 report - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=211720245&issue=svetlana1959%7CGophKeeper%7C138
- #109 - Implement Full Web Application Frontend (open) - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=204189656&issue=svetlana1959%7CGophKeeper%7C109
- #142 - Refining the design of the mobile and desktop versions of the application - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=212314778&issue=svetlana1959%7CGophKeeper%7C142
- #14 - Create README structure (open, assigned to Arseny) - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=196725304&issue=svetlana1959%7CGophKeeper%7C14
- #141 - Prepare the Final Project Demonstration Scenario - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=212303377&issue=svetlana1959%7CGophKeeper%7C141
- #41 - Implement goph device request command (closed/Done) - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197623524&issue=svetlana1959%7CGophKeeper%7C41
- #43 - Implement device approve command (closed/Done) - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197623533&issue=svetlana1959%7CGophKeeper%7C43
- #42 - Implement goph device list-requests command (closed/Done) - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197623530&issue=svetlana1959%7CGophKeeper%7C42
- #44 - Implement goph device revoke command (open — stretch/US-5) - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197623545&issue=svetlana1959%7CGophKeeper%7C44

## GitHub Repository
https://github.com/svetlana1959/GophKeeper

---
## Final Release
https://github.com/svetlana1959/GophKeeper/releases/tag/v0.2.0 
---
## README
https://github.com/svetlana1959/GophKeeper/blob/main/README.md 

---
## Figma
https://www.figma.com/design/e9yJfGqSkREVk5sjPocKHN/Untitled?node-id=0-1&t=u4j6RSIVCZZWmd5j-1

---
## Docker / Deployment
!МАЛИК ТУТ ТОЖЕ ДОПИШИ!
- VM host: `10.93.27.16`
- Live deployment link: http://10.93.27.16/


---
## Pre-freeze punch list:

- Finish frontend — fully port the Figma design
- Secret statistics and categorization (backend + client)
- Minimal mobile web version
- Analytics logging for recent activity, etc. 
- Manual end-to-end testing: account creation to adding several devices to working with secrets
