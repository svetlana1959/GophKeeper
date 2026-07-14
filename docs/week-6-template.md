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
| Svetlana Maltseva | Team Lead, Product Manager | Sprint planning and scope freeze for Week 6, final demo scenario, report Sprint 6 (Issues: #141, #138) |
| Elina Akhmetzyanova | Design, Documentation | report Sprint 6 template,  mobile/desktop design refinement (Issues: #142, #139) |
| Arseny Lashkevich | DevOps Engineer |  maintains the per-component CI pipelines (ci-backend, ci-cli, ci-frontend, release-cli) and Docker builds for cli/backend/frontend, wrote README (Issues: #14)|
| Aleksander Goncharov | CLI Engineer | Delivered multi-device secret synchronization (app/sync.go, PR #126) and the local vault/crypto/remote layers (PR #126)|
| Emil Nabiullin | Frontend Developer | Shipped the landing page, adaptive layout, and registration/authorization pages (PRs #116, #134, #136; Issues: #109) |
| Malik Nurullin | Backend Developer | Implemented the account/device/secret/sync services and repositories on FastAPI + SQLAlchemy; opened PR #121 to extend backend unit test coverage  |

---

# Sprint Goal

Finalize the project, freeze the scope, and prepare the application for release.

---

# Final Project Polish

## Completed Features

### High-Priority Features

Multi-device secret synchronization between the Go CLI and the FastAPI backend (PR #126) 
Core CLI workflow end-to-end: init, set, get, list, delete, device, link, sync, with client-side age encryption and a local SQLite vault — plaintext never leaves the device.
Backend zero-knowledge API: registration/login (auth_service, account_auth_service), device enrollment/invites, and secret CRUD, all behind hexagonal domain/service/infrastructure layers with 8 applied DB migrations.
Web authentication flow: registration and login pages, plus a redesigned landing page with adaptive layout (PRs #116, #134, #136)


### Bug Fixes


---

## Final Testing

### Testing Summary

CLI: unit tests exist across crypto, config, vault, remote, app (including a large sync_test.go), run via make test / make vet in CI (ci-cli.yaml).
Backend: unit tests cover account_auth_service, auth_service, device_service, enrollment_service, sync_service, tokens, secret; integration tests exist for device_repository and secret_repository, gated on TEST_DATABASE_URL so they don't block make test when no DB is present.

### Final Verification


---

## Code Quality

### Code Cleanup

Go side enforces golangci-lint (.golangci.yml) and make vet/make test as PR gates.
Backend enforces ruff format --check + ruff check via make lint.


### Comments and Refactoring

Go packages include doc.go files per package (crypto, vault, remote, config) documenting purpose, consistent with the Definition of Done's "every exported function/type/package documented."

---

## Code Freeze

### Freeze Date


### Notes

---

# Documentation Finalization

## README

### Final Updates

cli/README.md and backend/README.md are in good shape (install/usage, architecture, testing instructions)

Link: https://github.com/svetlana1959/GophKeeper/blob/main/README.md

---

## API Documentation

### Final Updates

FastAPI auto-generates interactive API docs (Swagger UI) at /docs once the backend is running (make up && make migrate), per backend/README.md. 

Link: 

---

## UI/UX Documentation

### Figma Design

Link: https://www.figma.com/design/e9yJfGqSkREVk5sjPocKHN/Untitled?node-id=0-1&t=u4j6RSIVCZZWmd5j-1

---

## Industrial Track Contribution

### Before / After Impact

Before: no existing product — GophKeeper started from a blank mono-repo (per CONTRIBUTING.md's architecture doc and docs/user_stories.md backlog).
After (this sprint): a working zero-knowledge CLI client with local encrypted vault and multi-device sync against a hexagonal FastAPI backend, plus the start of a web client (landing + auth).

---

# Release Readiness

## Deployment Verification

### VM Status


### Live Application

Link: http://10.93.27.16/

---

## Reproducibility

### Deployment Instructions

Backend: make up / make migrate (Docker Compose: Postgres + API + migrations), documented in backend/README.md.
CLI: cd cli && go build -o goph . or via install.sh / install.ps1.

### Docker Verification

---

## Final Validation Checklist

| Item | Status |
|------|--------|
| All planned features completed | |
| Critical bugs fixed | |
| README finalized | |
| API documentation completed | |
| Figma updated | |
| VM deployment verified | |
| Docker deployment verified | |
| Code freeze completed | |

---
# Final demo scenario
СЦЕНА 1 - Введение, прогрев) (0:00–0:20)
Малик сидит за ноутбуком, вокруг разбросаны бумажки/стикеры с паролями, куча вкладок в браузере, лицо — отчаяние. Камера медленно движется к Малику.
Малик стучит по клавиатуре, смотрит в потолок, руками берется за голову что очень отчаян. На пике отчаяния — кадр замирает в черно-белом фильтре.
Закадровый голос (Эмиль): "Это Малик. Backend-разработчик. Хранитель 67 паролей. Помнит из них — один. Угадать, от чего именно, не смог даже он сам."
Небольшая пауза, все еще только Малик в кадре
Эмиль: "И ведь Малик — не единственный"

СЦЕНА 2 — Появление решения (0:20–0:35)
Арсений заходит в комнату, садится рядом с Маликом, уверенно смотрит в камеру.
Арсений: "К счастью, мы уже это решили. Знакомьтесь — GophKeeper."
Быстрый переход на логотип или лендинг

СЦЕНА 3 — Title Card (0:35–0:40)
Название проекта + один слоган на экране, трек — Industrial, имена команды и роли

СЦЕНА 4 — Problem Statement & Solution (0:40–1:05)
Голос Светы на фоне: логины в разные сервисы, лист с паролями, скриншот новости про утечку

Пароли живут где попало: в заметках, файлах, голове
Готовые менеджеры паролей всё равно требуют доверять серверу — он теоретически видит расшифрованные данные
GophKeeper шифрует всё на стороне клиента и синхронизирует между устройствами только шифрованый текст. Прочитать секреты не можем даже мы.

СЦЕНА 5 — Key Features & Tech Stack (1:05–1:45)
Показывать на экране: фичи (каждая — 3–5 сек на экране):

Арсений:
Client-side шифрование через age, локальный SQLite vault — plaintext никогда не покидает устройство.
CLI: init, set, get, list, delete, device, link, sync. (про каждый кратко рассказать мб хз)
Мультиустройственная синхронизация.
Backend ничего не расшифровывает: получает от клиента уже зашифрованный блок данных и просто хранит его — вместе с версией и меткой времени, нужными только чтобы понять, какая копия свежее при синхронизации между устройствами.
Zero-knowledge trust chain между устройствами (enrollment/invites) - ...

Саша:
Стек (карточки/иконки):
CLI: Go, age, SQLite, гексагональная архитектура (domain/ports/adapters).
Backend: FastAPI, SQLAlchemy, PostgreSQL, dbmate-миграции, Dynaconf.
Frontend: React + Vite.
CI/CD: GitHub Actions (отдельные пайплайны под cli/backend/frontend), GoReleaser для релизов CLI.
Docker для локального/VM-деплоя.

СЦЕНА 6 — Live Demo (1:45–5:15) 
CLI-демо (записывает и рассказывает Арсений)
goph init                     # настройка устройства: identity + локальный vault
goph set github --value ****  # сохранить секрет
goph get github               # прочитать и расшифровать
goph list                     # список метаданных без расшифровки

Показать на экране терминала, комментируя вслух:
"Вот я инициализирую устройство — генерируется ключевая пара"
"Сохраняю секрет — он сразу шифруется на клиенте."
"Смотрю список — сервер видит только метаданные, не содержимое."

Затем — мультиустройственная синхронизация 
goph device link              # привязка нового доверенного устройства
goph sync                     # синхронизация секретов
"А теперь то же самое видно со второго устройства — без единого байта расшифрованных данных, прошедшего через сервер."

Элина:
Закадровый голос и показать: лендинг, регистрацию, логин, дашборд и тп

СЦЕНА 7 — Industrial Track Highlight: Before/After (5:15 - 5:40)
Закадровый голос на экране — диаграмма или таблица "было/ стало":
Малик:
До: секреты — в текстовых файлах, переменных окружения без шифрования, в мессенджерах
После: единая zero-knowledge система хранения и синхронизации с гарантией, что даже сервер (и его владельцы) не могут прочитать секреты

СЦЕНА 8 — Future Roadmap (5:40–6:00)
Эмиль закадровым голосом:
Опциональные фичи: интеграция с различными сервисами, Digital Inheritance (передача доступа доверенному лицу при неактивности владельца)

СЦЕНА 9 — Team Contributions (6:00–6:20)
Закадрово Света и на экране табличка или текст:

Светлана — Team Lead: приоритизация бэклога, координация спринтов и релизов, репорты, мотнаж 
Элина — дизайн (Figma) и документация репортов.
Арсений — DevOps: CI/CD, релизы, деплой.
Александр — CLI: шифрование, синхронизация.
Эмиль — Frontend: лендинг, авторизация, веб-клиент.
Малик — Backend: домены, сервисы, API.

СЦЕНА 10 — Outro (6:20 - 6:40)
логотип, ссылка на репозиторий куар кодом и надпись "Спасибо за просмотр" и можно еще фотошопом типо вокруг надписи мы показываем все жест ЛАЙК))

СЦЕНА 11 - Финалочка (6:40 - 7:00)
Кадр где Малик завис из первой сцены, типо отвисает, поворачивается и говорит: 
"Из 67 паролей остался один. Остальные 66 — теперь в GophKeeper" и показывает фирменный жест ЛАЙК

---

# Relevant Links

### Issues:
#139 - Write Sprint 6 template - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=211720319&issue=svetlana1959%7CGophKeeper%7C139
#138 - Write Sprint 6 report - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=211720245&issue=svetlana1959%7CGophKeeper%7C138
#109 - Implement Full Web Application Frontend - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=204189656&issue=svetlana1959%7CGophKeeper%7C109
#142 - Refining the design of the mobile and desktop versions of the application - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=212314778&issue=svetlana1959%7CGophKeeper%7C142
#14 - Create README structure - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=196725304&issue=svetlana1959%7CGophKeeper%7C14
#141 - Prepare the Final Project Demonstration Scenario - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=212303377&issue=svetlana1959%7CGophKeeper%7C141
#41 - Implement goph device request command - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197623524&issue=svetlana1959%7CGophKeeper%7C41
#43 - Implement device approve command - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197623533&issue=svetlana1959%7CGophKeeper%7C43
#42 - Implement goph device list-requests command - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197623530&issue=svetlana1959%7CGophKeeper%7C42
#44 - Implement goph device revoke command - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197623545&issue=svetlana1959%7CGophKeeper%7C44

## GitHub Repository

https://github.com/svetlana1959/GophKeeper
---

## Final Release
https://github.com/svetlana1959/GophKeeper/releases/tag/v0.2.0

---

## README
https://github.com/svetlana1959/GophKeeper/blob/main/README.md
---

## API Documentation


---

## Figma
https://www.figma.com/design/e9yJfGqSkREVk5sjPocKHN/Untitled?node-id=0-1&t=u4j6RSIVCZZWmd5j-1


---

Docker / Deployment


backend/docker-compose.yaml, backend/Dockerfile, cli/Dockerfile, frontend/Dockerfile — present in repo
VM host: 10.93.27.16
Live deployment link: http://10.93.27.16:80
