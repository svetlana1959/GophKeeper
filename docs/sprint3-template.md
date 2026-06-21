# Sprint 3 Report

## Project Information

### Track

Industrial

### Project

GophKeeper — a distributed zero-knowledge secret management system designed for secure storage, synchronization, and management of sensitive information across trusted devices.

### Sprint

Week 3


## Team Members and Contributions

# Team Members and Contributions

| Team Member | Role | Contribution |
|-------------|------|-------------|
| Svetlana Maltseva | Team Lead, Product Manager | Project planning, backlog management, sprint coordination, requirements analysis, sprint documentation |
| Elina Akhmetzyanova | Design, Documentation | Landing page design, UI mockups, sprint documentation |
| Arseny Lashkevich | DevOps Engineer | Configured CI for backend unit and integration tests, implemented automated build pipelines, and set up deployment to the VM |
| Aleksander Goncharov | CLI Engineer | |
| Emil Nabiullin | Frontend Developer | Frontend layout implementation, UI integration, web page development based on approved mockups |
| Malik Nurullin | Backend Developer | Completed API endpoints implementation and fixed UUID and database connection issues that were causing test failures, started working on multi-device synchronization |


---

## Sprint Goal

Expand the MVP by implementing the next-priority features, improving system usability, strengthening integration between components, and delivering a more complete version of the product for internal review and testing.


## Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| Limited development time| High | High | Prioritize MVP features, maintain weekly sprint reviews, postpone non-critical functionality |
| Integration issues between CLI, backend, and web application | Medium | Medium | Define API contracts and continuously test integration during development |
| Team member illness or absence | Medium | High | Reassign unfinished tasks to available team members, adjust sprint scope if necessary, and maintain regular progress tracking |
| Incorrect estimation of task complexity | Medium | Medium | Break large tasks into smaller issues and review estimates weekly |
| Delays in code review process | Low | Medium | Assign reviewers in advance and monitor pull request status |
| The customer is not interested in the project | High | Medium |Collect feedback from potential users and stakeholders outside the customer organization to validate product decisions and usability | 
| Cross-language protocol mismatch (FastAPI doesn't talk Go) | Low | High | Lock contract early; validate http schemas, add contract tests to CI |
| Test coverage below 80% requirement | Medium | High | Monitor coverage reports in CI/CD, include tests in the Definition of Done, and prioritize writing tests for all newly implemented functionality |



---

# Features Implemented

## New Functionality

### (1) Secret Creation
- The application now allows authenticated users to create and securely store secrets. Before being stored locally, secret data is encrypted to ensure confidentiality. The system validates required fields and provides feedback on successful or failed operations.

### (2) Secret Management
- Users can now view all secrets available to them. displays secret names and contents, supports empty states when no secrets exist, and ensures that users can only access secrets they own or are authorized to view.
- Users can also update existing secrets. Changes are validated before being saved, invalid updates are rejected, and users may cancel modifications without affecting stored data.


### (3) Multi-Device Access
- Support for trusted devices has been added. Users can access their encrypted secrets from multiple approved devices. Synchronization ensures that data remains consistent across devices, while untrusted devices are denied access.


### Digital Inheritance (Planned Feature)
 - A new digital inheritance feature is planned for future releases. During registration, users will be able to designate a trusted beneficiary who may receive access to selected secrets in exceptional circumstances.
 - The system will periodically verify the activity of the account owner. If prolonged inactivity is detected, additional verification requests will be sent to confirm that the owner is still active. If verification attempts remain unanswered for a predefined period, access to designated secrets may be transferred to the trusted beneficiary according to the user's predefined settings.
 - This feature aims to provide secure digital legacy management while preserving user privacy and preventing unauthorized access.
---

## Frontend Updates
- Implemented the initial frontend structure based on approved mockups
- Completed layout implementation for the web application
- Finished the Trusted Devices Management Page
- Finished the Account Statistics Page
---

## Backend Updates
- Completed implementation of the planned API endpoints
- Fixed issues related to UUID handling and database connectivity
- Resolved test failures caused by backend configuration problems
- Started implementation of multi-device synchronization functionality
---

## Database Update
- Configured database models and schema for users, devices, and secrets
- Improved database connectivity and fixed integration issues
- Verified backend interaction with the database through automated tests
---

## Infrastructure Updates
- Configured CI pipelines for backend unit and integration tests.
Implemented automated build pipelines
- Set up deployment workflow for the VM environment
- Improved project infrastructure and development automation

---

# Screenshots / GIFs

---
# Architecture & Technical Decisions

## 1. Core Architectural Paradign: Zero-Knowledge & Mono-Repo split
- **Decision**: Implementing a strict **Zero-Knowledge model** inside a unified **mono-repo** codebase, dividing the system into an isolated stateless server component and a stateful client binary.
- **Rationale**: 
    - The server is architected as a "blind" storage orchestrator. It never processes unencrypted private keys or raw payloads. By keeping the cryptographic burden entirely on the client, the backend remains lightweight, scale-ready, and legally/technically resilient against data leaks.\
    - A mono-repo approach ensures tight synchronization of network communication protocols and API contracts. It simplifies localized builds, artifact versioning, and developer experience while enforcing a strict boundary rule: the client application never imports anything from the backend and vice versa.

## 2. Backend API Stack Decisions

### High-Performance Asynchronous Framework: FastAPI
- **Decision**: Selected as the primary presentation layer framework for the server component.
- **Rationale**: It leverages native asynchronous concurrent request processing, delivering high-throughput performance with low latency overhead. Automated serialization and runtime validation of input/output data transfer objects (DTOs) heavily reduce development overhead and eliminate a common vector for data-injection bugs.

### Reactive Data Access: SQLAlchemy (Async) + asyncpg
- **Decision**: Utilizing an asynchronous Object-Relational Mapper coupled with a high-performance, native-protocol driver.
- **Rationale**: This ensures non-blocking database input/output execution paths across the entire service layer. The direct binary protocol mapping handles large-scale binary blocks (BYTEA) and connection pools effectively, preventing worker pool starvation under dense, high-load cryptographic storage operations.

### Core Database: PostgreSQL
- **Decision**: Adopted as the primary relational database system.
- **Rationale**: The architectural requirements dictate strict enterprise compliance, operational atomicity, and native support for advanced binary fields (`BYTEA`) and logical tracking flags (`BOOLEAN`). Furthermore, its capability to handle high-concurrency safe updates (`ON CONFLICT DO UPDATE`) allows for reliable, idempotent distributed registration and atomic version increment logic.

### Separate Database Migration Tooling: dbmate
- **Decision**: Using a dedicated, framework-agnostic lightweight migration runner.
- **Rationale**: Decoupling schema tracking from the application framework runtime ensures clean infrastructure deployments. It forces migrations to be written in native SQL, making them explicit, maintainable, easily testable via continuous integration pipelines, and safe against state corruption caused by application-level code mutations.

### Configuration Management: Dynaconf
- **Decision**: Layered configuration management for different deployment environments.
- **Rationale**: It dynamically isolates settings for development, testing, staging, and production environments without modifying the system logic. It supports secure, dynamic injection of production configuration overrides directly from secret storage solutions or deployment orchestration systems.

### Package and Workspace Tooling: Uvicorn
- **Decision**: Utilizing a high-speed, modern workspace compiler and environment runner.
- **Rationale**: This dramatically accelerates deployment assembly pipelines, minimizes artifact container footprints, and ensures reproducible, locked runtime environments across both development and distributed staging servers.

## 3. Client Binary Tooling: Go Language (Golang)
- **Decision**: Designing and building the client CLI entirely using Go.
- **Rationale**:
    - **Static Compilation & Zero Dependencies**: Compiles into a single, statically-linked binary executable. This guarantees immediate out-of-the-box local execution on user nodes without requiring pre-installed runtimes, specific shared libraries, or interpreter management tools.
    - **Cryptographic Capability & Security**: Offers excellent access to low-level cryptographic extensions and multi-platform native compiling. Memory safety features drastically mitigate local side-channel or memory-corruption vulnerabilities common during key management and envelope encryption procedures.
    - **Cross-Compilation**: Enables native compilation for multiple targets (Linux, macOS, Windows across different CPU architectures) from a single deployment script, ensuring seamless distribution for diverse operational environments.

## 4. Client CLI Storage & Configuration Strategy

### Local Relational Storage: SQLite
- **Decision**: Utilizing a local embedded relational database engine for client-state tracking, cryptographic metadata, and the local trust graph.
- **Rationale**: 
    - **Zero-Administration & Single File**: It runs entirely within the CLI process memory space and stores all data in a single, compact local file. This eliminates the need to manage a separate local daemon or server process on the user's machine.
    - **Relational Integrity for Trust Chains**: Tracking local devices, synchronization states, and complex trust graphs (e.g., verifying which local device identity signed which target node) requires a relational model with strict Foreign Key constraints and atomic transactions (ACID). This ensures the local state can never be partially written or corrupted during abrupt application termination.
    - **Secure Binary Storage**: It naturally handles binary large objects (BLOB), which is essential for storing encrypted payload blocks and local keys without requiring brittle text encoding schemes.

### User-Modifiable Settings: YAML Configuration
- **Decision**: Separating application state from user configuration by keeping human-editable parameters in a clear text-based format.
- **Rationale**: 
    - **Separation of Concerns**: Parameters that a user needs to modify (such as backend server endpoints, connection timeouts, log levels, or default profile names) are decoupled from the sensitive application state.
    - **Human-Readable Boundaries**: Storing these preferences in a readable layout prevents users from manually editing or inadvertently corrupting the internal database tables (`SQLite`). This acts as an operational boundary: the database is managed strictly via application logic, while the configuration file remains an exposed user interface.

---

## Challenges Encountered

* The backend team encountered issues with UUID handling, which caused several API requests and tests to fail. The issue was investigated and resolved.

* Database connectivity issues were discovered during integration and automated testing. Configuration changes were applied to ensure stable communication between the backend and the database.

* Docker configuration problems slowed down backend development and testing. The container setup was adjusted to resolve environment-related issues.

* Setting up CI pipelines required additional effort to ensure that automated unit and integration tests run correctly in the GitHub Actions environment.

---

# Daily Standups

## 17 June 2026

All team members attended the meeting.

The team reviewed the project requirements and MVP scope, discussed user stories and acceptance criteria, estimated task complexity and workload using Planning Poker, and prioritized the backlog. Responsibilities were assigned among team members, the sprint scope was defined, and the team agreed on the development workflow.

---

## 18 June 2026

The meeting was attended by Svetlana, Malik, and Arseny.

The team discussed current progress and blockers. Malik reported Docker-related issues affecting backend development, and possible solutions were discussed. Arseny started working on CLI tasks. 

---

## 19 June 2026

The team discussed current progress and blockers.
| Team Member    | Progress Update                                                                                                                                                |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Emil**       | Continued frontend development. Working on page layout implementation. Plans to finish the current UI tasks by Sunday                                          |
| **Elina**      | Continued work on UI/UX design. Preparing and refining page mockups                                                                                            |
| **Aleksander** | Did not attend the standup                                                                                                                                     |
| **Malik**      | Continued backend API implementation. Investigating and fixing Docker-related issues affecting the development environment                                     |
| **Arseny**     | Continued development of CLI functionality. Planning to deploy the current application version to the VM in the evening                                        |
| **Svetlana**   | Updated and improved the weekly report and project documentation. Searching for a potential end user who can provide feedback during Week 4 usability testing  |

---

## 22 June 2026

---

## 23 June 2026

---

# Internal Review

## Demo Summary


### Feedback

### Action Items

---

# Baseline Comparison

## Previous Baseline

During Sprint 2, the team completed the project planning phase. The MVP scope, system architecture, technology stack, user stories, acceptance criteria, backlog, risks, and milestones were defined. Initial UI mockups and user flow diagrams were prepared, and the first API endpoints and documentation were created.

---

## Improvements Added

| Area | Sprint 2 | Sprint 3 |
|--------|--------|--------|
| Authentication | User stories and requirements defined | Not implemented yet(implementation in the next sprint) |
| Secret Management | MVP scope and CRUD requirements prepared | |
| Synchronization | Architecture and synchronization workflow designed | |
| Infrastructure | Technology stack selected, VM and CI/CD planned | |
| Web Application | Wireframes and UI mockups created | |

---

## Industrial Track Contribution

This sprint expanded the contribution to the GophKeeper product through implementation of additional functionality, infrastructure improvements, and preparation for future synchronization and trusted-device workflows.

### Progress Against Baseline

---

# API Documentation

## New Endpoints

---

## Updated Endpoints

---

# Relevant Links
Figma - https://www.figma.com/design/e9yJfGqSkREVk5sjPocKHN/Untitled?node-id=0-1&t=edpuYY4hWFmTym6q-1


## Issues

- Issue #50 - Design Web Authentication and User Dashboard -
  https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=198034715&issue=svetlana1959%7CGophKeeper%7C50
- Issue #27 - Create /api/v1/store and /api/v1/device endpoints - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197206217&issue=svetlana1959%7CGophKeeper%7C27
- Issue #80 - Create Sprint 3 report template - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=202347580&issue=svetlana1959%7CGophKeeper%7C80
- Issue #79 - Write Sprint 3 report - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=202089085&issue=svetlana1959%7CGophKeeper%7C79
- Issue #36 - Implement set command (create a secret) - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197617813&issue=svetlana1959%7CGophKeeper%7C36
- Issue #74 - Implement set command (update a secret) - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=201369906&issue=svetlana1959%7CGophKeeper%7C74
- Issue #39 - Implement delete command (remove a secret) - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197619359&issue=svetlana1959%7CGophKeeper%7C39
- Issue #37 - Implement get command (read a secret) - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197618672&issue=svetlana1959%7CGophKeeper%7C37
- Issue #38 - Implement list command (list secrets) - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197618939&issue=svetlana1959%7CGophKeeper%7C38
- Issue #32 - Implement distributed crypto-engine - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197240876&issue=svetlana1959%7CGophKeeper%7C32
- Issue #23 - Create local configuration storage - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197205187&issue=svetlana1959%7CGophKeeper%7C23
- Issue #33 - Implement local secret database - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197263931&issue=svetlana1959%7CGophKeeper%7C33
- Issue #22 - Implement CLI init command - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197205031&issue=svetlana1959%7CGophKeeper%7C22
- Issue #75 - [feat]: Frontend landing preview - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=201384138&issue=svetlana1959%7CGophKeeper%7C75
- Issue #77 - Design Trusted Devices Management Page - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=202085670&issue=svetlana1959%7CGophKeeper%7C77
- Issue #78 - Design Account Statistics Page - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=202086325&issue=svetlana1959%7CGophKeeper%7C78
- Issue #92 - Document the feature: Digital Inheritance - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=202900266&issue=svetlana1959%7CGophKeeper%7C92
---

## Pull Requests

- PR #58 - feat: api endpoints -  https://github.com/svetlana1959/GophKeeper/pull/58
- PR #55 - feat: backend database setup - https://github.com/svetlana1959/GophKeeper/pull/55
- PR #XX

---

# Updated Backlog

Project backlog and sprint planning are managed using GitHub Projects.
Link: https://github.com/orgs/svetlana1959/projects/4/views/1 and https://github.com/orgs/svetlana1959/projects/6/views/1

## Completed
### Issue: #80, #79, #55, #92
---

## In Progress
### Issue: #50, #58, #27, #78, #77, #75, #22, #33, #23, $32, #38, #37, #39, #74, #36
---

## Planned for Sprint 4

Implemented user authorization and user database. Connected real user data to the dashboard. Collected initial user feedback

### User Registration: 
- Implement user registration endpoint
- Add user table to the database
- Validate registration data
- Store users in the database

  
### User Login: 
- Implement login endpoint
- Verify credentials
- Return JWT access token

### Dashboard:
- Create dashboard API endpoint
- Display user secrets count
- Display pending access requests
- Connect frontend dashboard to backend API

### View Secrets:
- Connect secrets list to real backend data
- Display user secrets on the overview page

### View Devices:
- Display trusted devices on the overview page
- Connect devices data to backend

### Initial User Feedback:
- Deploy a working version to the VM
- Prepare demo scenario
- Conduct usability testing with at least 2–3 potential users
- Collect structured feedback
- Create improvement tasks based on feedback
- Document key findings in the sprint report

### Additional Technical Tasks:
- Configure database migrations
- Create seed/test users
- Improve API validation and error handling
- Add unit tests for authentication
- Add integration tests for registration and login flows
- Update API documentation
---

## Sprint 4 Priorities


### (1) User Registration - #83 - https://github.com/orgs/svetlana1959/projects/6/views/1?pane=issue&itemId=202877320&issue=svetlana1959%7CGophKeeper%7C83

As a new user
I want to create an account
So that my secrets are private and tied only to me

Acceptance criteria:

- Given a new user provides valid registration data, when the user creates an account, then the account is created successfully.
- Given the email is not used by another account, when the user submits registration, then the email is accepted as unique.
- Given the email already exists in the system, when the user tries to register, then the account is not created and an error is displayed.
- Given the username is not used by another account, when the user submits registration, then the username is accepted as unique.
- Given the username already exists in the system, when the user tries to register, then the account is not created and an error is displayed.
- Given the registration data is valid, when the account is created, then the account is saved in the system.
- Given required fields are empty or invalid, when the user submits the form, then the system rejects the request and shows a clear validation message

### (2) User Login - #84 - https://github.com/orgs/svetlana1959/projects/6/views/1?pane=issue&itemId=202877456&issue=svetlana1959%7CGophKeeper%7C84

As a registered user
I want to log in to my account
So that I can access my encrypted secrets

Acceptance criteria:

- Given a registered user enters valid login information, when the user logs in, then access to the account is granted.
- Given the login is successful, when authentication is completed, then a token is issued.
- Given the login information is invalid, when the user tries to log in, then an error is displayed.
- Given the login information is missing or incomplete, when the user submits the login form, then the system rejects the request.
- Given a user is not authenticated, when the user tries to access encrypted secrets, then access is denied

 
### (3) View Devices - #85 - https://github.com/orgs/svetlana1959/projects/6/views/1?pane=issue&itemId=202877908&issue=svetlana1959%7CGophKeeper%7C85

As a secret owner
I want to see which devices have access to my secrets
So that I can control who can access my data

Acceptance criteria:

- Given devices have access to the account, when the user opens device management, then the user can see a list of devices.
- Given the device list is displayed, when the user views it, then only devices with access are displayed.
- Given there are no trusted devices except the current one, when the list is opened, then the system displays the available trusted device information.
- Given a device was revoked, when the device list is refreshed, then the revoked device is no longer shown as trusted.
- Given the user is not authenticated, when the user tries to view devices, then access is denied

 
### (4) Dashboard - #90 - https://github.com/orgs/svetlana1959/projects/6/views/1?pane=issue&itemId=202879314&issue=svetlana1959%7CGophKeeper%7C90

As an authenticated user
I want to view information about my secrets and requests
So that I can monitor the security of my account

Acceptance criteria:

- Given the user is authenticated, when the dashboard is opened, then the user can see their secrets and requests.
- Given information is available, when the dashboard loads, then the information is displayed correctly.
- Given data changes, when the dashboard is refreshed or reopened, then data is updated after changes.
- Given there are no requests, when the dashboard is opened, then the system displays an empty requests state.
- Given the user is not authenticated, when the dashboard is requested, then access is denied

