# Sprint 2 Report

## Project Information

### Track

Industrial

### Project

GophKeeper - is a zero-knowledge secret management system designed to securely store, synchronize, and share sensitive information across trusted devices. The project focuses on client-side encryption, ensuring that secret contents are never accessible to the server.

### Team Members

- Elina Akhmetzyanova
- Svetlana Maltseva
- Arseny Lashkevich
- Aleksander Goncharov
- Emil Nabiullin
- Malik Nurullin

### Roles

| Team Member | Role |
|-------------|------|
| Svetlana Maltseva | Team Lead, Product Manager |
| Elina Akhmetzyanova | Design, Documentation |
| Arseny Lashkevich | DevOps Engineer |
| Aleksander Goncharov | CLI Engineer |
| Emil Nabiullin | Frontend Developer |
| Malik Nurullin | Backend Developer  |

### Sprint

Week 2

---

## Problem Statement

Most password managers and secret storage systems require users to trust the service provider with sensitive information or rely on a single master password.

The goal of GophKeeper is to develop a Zero-Knowledge cloud secret manager where the server never has access to the contents of user secrets.

The system should provide secure storage, synchronization, and sharing of secrets across trusted user devices.

---

## Industrial Track Justification

### Existing Product / Project

GophKeeper belongs to the Industrial Track and addresses the problem of secure secret management.

Similar products include Bitwarden, 1Password, HashiCorp Vault, and Infisical.

### Identified Gap

Existing solutions often rely on centralized trust models or provide complex key management workflows.

GophKeeper aims to simplify secure secret management by combining client-side encryption with trusted device synchronization.

### Planned Contribution

Develop a secure cloud secret manager that performs encryption on the client side and stores only encrypted data on the server.

### Expected Impact

Improve the security of secret storage while reducing the amount of trust required from users toward the service provider.

---

## Project Plan

### Week-by-Week Roadmap

The roadmap is based on our current understanding of the project and may change during development. As we start implementing specific features, some tasks may require more or less time than initially expected.

#### Week 1

- Team formation
- Project and track selection
- Initial project discussion

#### Week 2

- Project planning
- User stories preparation
- Backlog creation
- UI design
- Project documentation

#### Week 3

- Backend setup
- Database setup
- API design
- CLI structure preparation

#### Week 4

- Authentication implementation
- Secret storage implementation
- Encryption integration

#### Week 5

- Trusted device management
- Secret synchronization
- Access request workflow

#### Week 6

- Testing
- Bug fixing
- Documentation updates
- Final project preparation

### Milestones

- Project concept approved
- User stories completed

### Risks

- Limited development time
- Requirement changes during development
  
---

## Backlog

### GitHub Project Board

Project backlog and sprint planning are managed using GitHub Projects.

Link: https://github.com/orgs/svetlana1959/projects/4/views/1

---

## User Stories

### Epic A — Account & Authentication

#### A1. Create an Account

As a new user, I want to create an account, so that my secrets are private and tied only to me.

**Acceptance Criteria:**

- A user registers with a login and master password via the CLI.
- The master password is hashed (bcrypt/argon2), never stored in plaintext or recoverable.
- Duplicate logins are rejected with a clear message.

#### A2. Log In

As a registered user, I want to log in, so that only I can access my secrets.

**Acceptance Criteria:**

- Valid credentials authenticate the user against the server.
- Invalid credentials are rejected without revealing which field was wrong.

---

### Epic B — Zero-Knowledge Secret Storage

#### B1. Store a Login/Password Pair

As a user, I want to store a login and password with metadata, so that I do not have to remember it.

**Acceptance Criteria:**

- Payload is encrypted client-side with age before leaving the device.
- The server stores only ciphertext, never plaintext passwords.
- Arbitrary text metadata can be attached.

#### B2. Store Free Text

As a user, I want to store an arbitrary text note, so that I can keep secure notes alongside my passwords.

#### B3. Store Binary Data

As a user, I want to store an arbitrary file, so that I can keep keys, certificates, and documents safe.

**Acceptance Criteria:**

- Large payloads are handled correctly.
- Files are encrypted client-side before upload.
- Metadata distinguishes files from other secret types.

#### B4. Store Bank Card Data

As a user, I want to store bank card details, so that I have them available securely.

**Acceptance Criteria:**

- Card number, expiry date, CVV, and cardholder name are stored as encrypted fields.
- Input is validated before saving.

#### B5. Update a Secret

As a user, I want to update an existing secret, so that my stored information stays accurate.

#### B6. Delete a Secret

As a user, I want to delete a secret, so that I can remove information I no longer need.

#### B7. List All Secrets

As a user, I want to see all my secrets, so that I can find what I need.

**Acceptance Criteria:**

- Listing displays metadata such as secret name and type.
- Secret contents are not decrypted unless explicitly requested.

#### B8. Organize / Filter Secrets by Type

As a user with many secrets, I want to view my secrets grouped or filtered by type, so that I can manage different kinds of information efficiently.

**Acceptance Criteria for B1–B5:**

- Invalid input (empty required fields, malformed card numbers, etc.) is rejected with a clear error before anything is saved.

---

### Epic C — Multi-Device Trust & Sharing

#### C1. Request Access from a New Device

As a user on a new device, I want to request access to my vault, so that an already trusted device can grant it.

#### C2. View Pending Access Requests

As a user on a trusted device, I want to see pending access requests, so that I can review them before granting access.

#### C3. Approve an Access Request

As a user on a trusted device, I want to approve a request, so that the new device is added to the trust chain.

#### C4. First Sync After Approval

As a user on the newly approved device, I want my secrets to appear and decrypt, so that I can use the vault immediately.

#### C5. View Trusted Devices

As a user, I want to see which devices are in my trust chain, so that I can control who can read my data.

#### C6. Revoke Device Access

As a user, I want to revoke access for a device, so that a lost or retired device can no longer read my secrets.

---

### Epic D — Synchronization

#### D1. Automatic Sync Across Devices

As a user with more than one trusted device, I want my secrets to sync automatically, so that every device shows the latest version.

#### D2. Conflict Resolution

As a user who edited the same secret on two devices, I want the system to detect conflicts instead of silently overwriting changes, so that I never lose data.

**Acceptance Criteria:**

- Concurrent edits are detected.
- The second conflicting update is rejected.
- The client must pull the latest version before re-applying changes.
- Unrelated secrets remain unaffected.

#### D3. Synchronization Status

As a user, I want to know whether my last synchronization succeeded, so that I can trust my data is up to date.

---

### Epic E — Account Overview

#### E1. Account Overview

As a user, I want an overview of my secrets, trusted devices, and pending requests, so that I can quickly monitor my account.

**Acceptance Criteria:**

- Displays total secret count.
- Displays trusted devices.
- Displays pending access request count.
- Displays last synchronization time.

---

### Web Overview Application

As a user, I want a web page showing my account overview, so that I can check account status without using the CLI.

**Acceptance Criteria:**

- Displays secret count.
- Displays trusted devices.
- Displays pending requests.
- Displays last synchronization time.
- Displays metadata only and never exposes secret contents.

---

## MVP Scope

### In Scope

- Epic A — Account & Authentication
- Epic B — Zero-Knowledge Secret Storage
- Epic C — Multi-Device Trust & Sharing
- Epic D — Synchronization
- Epic E — Account Overview
- Web Overview Application

### Out of Scope

- Backup & Recovery
- Client Metadata
- Password Breach Monitoring
- Password Expiration Notifications
- OTP Support
- Secret Version History

---

## Tech Stack

### Frontend
CLI — GoLang + Cobra, a basic stack for developing the CLI service. The main advantage is the age library for file encryption, written by the algorithm's creator. It's written in Go and has active community support, which makes it probably the safest option out there - and it means we don't have to build anything from scratch on the algorithm side
WebApp — ReactJS with a Vite configuration + Gravity UI + Tailwind CSS for rapid web layout development and builds, plus React Hooks for fast request initialization.

### Backend
Python + FastAPI is the most suitable stack for a simple API and an MVP, since it's familiar to most of the team members

### Database
PostgreSQL with migrations for the global API, as it's designed to handle many users concurrently; and SQLite for local key storage, since in the CLI case we have only one user and therefore no need for a dedicated database server. SQLite stores the database in a local file, which can be easily encrypted

### Infrastructure
Main project "svetlana1959" (https://github.com/svetlana1959), which contains the Kanban board and the repositories, with branches for the production and development stages.

---

## Design Artifacts

### Wireframes

The following wireframes were prepared:

- Registration Screen
- Login Screen
- User Dashboard
- User Secrets List

### Mockups

Initial UI mockups were created in Figma.

### User Flow Diagrams

Currently under development.

---

## MVP Features

### Implemented Features

At this stage, the team has defined the project requirements, prepared user stories, identified the MVP scope, and started working on the UI design.

Core functionality implementation is planned for the next stages of the project.

### Functional User Journeys

User journeys are currently being developed based on the approved user stories and MVP requirements.

### Screenshots / GIFs

Initial wireframes and UI mockups have been created and will be expanded during the implementation phase.

---

## Baseline Comparison

### Baseline Product

The project was analyzed against several existing secret management solutions:

- Bitwarden
- 1Password
- HashiCorp Vault
- Infisical

### Initial Measurement

At the current stage of development, quantitative comparison is not yet available because the MVP implementation is still in progress.

---

## Sprint Goal

Establish the project foundation, define requirements, prepare project documentation, create initial user stories, and begin designing the user interface for the MVP.

---

## Relevant Links

### Issues

### Pull Requests

### API Documentation

---

## Next Steps

- Complete user stories
- Complete UI mockups
- Finalize MVP scope
- Begin backend implementation
- Prepare API design
