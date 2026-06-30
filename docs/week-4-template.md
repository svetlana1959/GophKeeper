# Sprint 4 Report

## Project Information

### Track

Industrial

### Project

GophKeeper — a distributed zero-knowledge secret management system designed for secure storage, synchronization, and management of sensitive information across trusted devices.

### Sprint

Week 4

---

Вот как можно кратко и в одном стиле заполнить таблицу.

| Team Member              | Role                       | Contribution                                                                                                                                                                                                                             | commits/PRs/Issues |
| ------------------------ | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| **Svetlana Maltseva**    | Team Lead, Product Manager | Project planning, backlog management, sprint coordination, stakeholder communication, requirements analysis, sprint documentation, sprint retrospective preparation                                                                      | Issues: #100, #104 |
| **Elina Akhmetzyanova**  | Design, Documentation      | Designed the application dark theme, refined UI interaction flows, updated sprint documentation and templates                                                                                                                            | Issues: #101, #102 |
| **Arseny Lashkevich**    | DevOps Engineer            | Implemented CI/CD pipelines for frontend and backend, automated testing, coverage reporting, Docker image publishing to GHCR, VM deployment improvements, secured GitHub Actions workflows                                               | PRs: 94, 82        |
| **Aleksander Goncharov** | CLI Engineer               | Implemented the cryptographic core, added encrypted local database support, fixed review comments, improved local storage implementation                                             |                    |
| **Emil Nabiullin**       | Frontend Developer         | Implemented the landing page, responsive layout, authentication pages (Login and Registration), Dashboard layout, and integrated approved UI designs into the frontend                                                                   |                    |
| **Malik Nurullin**       | Backend Developer          | Implemented multi-device access and synchronization, added access request workflow and synchronization API, wrote unit and integration tests, increased backend test coverage above 80%, improved backend stability and passed CI checks |                    |

---

# Sprint Goal

Ensure quality through testing, automate builds and deployment to the VM, and begin collecting real user feedback from the deployed product.

---

# Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| Limited development time| High | High | Prioritize MVP features, maintain weekly sprint reviews, postpone non-critical functionality |
| Integration issues between CLI, backend, and web application | Medium | Medium | Define API contracts and continuously test integration during development |
| Team member illness or absence | Medium | High | Reassign unfinished tasks to available team members, adjust sprint scope if necessary, and maintain regular progress tracking |
| The customer is not interested in the project | High | Medium |Collect feedback from potential users and stakeholders outside the customer organization to validate product decisions and usability | 
| Cross-language protocol mismatch (FastAPI doesn't talk Go) | Low | High | Lock contract early; validate http schemas, add contract tests to CI |


# Testing

## Testing Strategy

### Goals

- Verify core functionality
- Validate API behavior
- Ensure deployment stability
- Reduce regression risks

---

## Unit Tests

Unit tests cover the core domain and service logic without using a real database.

Current unit test coverage includes:

- Device registration
- Duplicate device registration handling
- Device retrieval
- Secret update logic
- Version conflict handling
- Secret deletion
- Secret validation and invalid state handling

---

## Integration Tests

Integration tests verify repository behavior and database interaction using the real persistence layer.

### API Testing

| Component | Test Status | Notes |
|-----------|------------|--------|
| Device Repository | Implemented | Store, fetch, rollback, and list active devices |
| Secret Repository | Implemented | Store, fetch, and rollback secret persistence |

---

## End-to-End Testing

End-to-end testing is currently focused on the core user workflows and will be expanded as frontend-backend integration progresses.

Planned user flows include:

- Device registration
- Secret creation
- Secret retrieval
- Secret synchronization between trusted devices
  
### Tested Flows

- Secret creation
- Secret synchronization
- Device management

---

## Test Results

### Summary

| Test Type | Total | Passed | Failed |
|------------|------:|------:|------:|
| Unit Tests | 9 | 9 | 0 |
| Integration Tests | 5 | 5 | 0 |

---
## Evidence

- GitHub Actions workflows are configured for backend, frontend, and CLI.
- Backend CI runs automated tests with a PostgreSQL service container.
- Backend CI generates a coverage report and uploads it as an artifact.
- Frontend and backend Docker images are built in CI.
- Frontend and backend Docker images are published to GitHub Container Registry (GHCR) on `main` and `dev` branches.
- CLI CI runs formatting checks, `go vet`, linting, tests, and coverage summary.

### Test Screenshots



### CI Logs

The CI workflows generate logs for:

- Backend unit and integration tests
- Backend code coverage
- Frontend build
- Backend Docker image build
- Frontend Docker image build
- CLI formatting, linting, and tests
- Docker image publishing to GitHub Container Registry (GHCR)
---

# CI/CD Pipeline

## Continuous Integration

### Automated Checks

The project uses GitHub Actions to automatically validate every push and pull request

Implemented checks include:

- Backend unit tests
- Backend integration tests with PostgreSQL
- Backend code coverage reporting
- Backend linting
- Frontend linting
- Frontend Docker image build
- CLI formatting validation (gofmt)
- CLI static analysis (go vet)
- CLI linting (golangci-lint)
  
## Continuous Deployment

### Deployment Flow

The deployment pipeline is implemented using GitHub Actions

Deployment process:

1. Build the application Docker image
2. Publish the image to GitHub Container Registry (GHCR)
3. Images are published for the `main` and `dev` branches
4. The published images are ready to be deployed to the project VM
---

## Workflow Files

### GitHub Actions

- `ci-backend.yaml` – backend testing, code coverage, Docker build, and image publishing.
- `ci-frontend.yaml` – frontend build and image publishing.
- `ci-cli.yaml` – CLI linting, formatting, testing, and coverage.
- `release-cli.yaml` – automated CLI release pipeline.

---

# VM Environment Setup

## Installed Services

- Docker
- Docker Compose
- PostgreSQL
- Backend API (FastAPI)
- Frontend Web Application (React)

---

## Environment Variables

The backend and database configuration is managed through environment variables.

| Variable | Purpose |
|----------|---------|
| `POSTGRES_USER` | PostgreSQL username |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `POSTGRES_DB` | PostgreSQL database name |
| `DATABASE_URL` | Database connection string used by backend and migrations |
| `TEST_DATABASE_URL` | Database connection string used for integration tests |
| `ENV` | Application environment, for example `dev` |

The project also supports configuration overrides through the `GOPH_` environment variable prefix, for example `GOPH_DATABASE__PASSWORD`
---

## Networking

The application is deployed on the project VM and is accessible via HTTP at:

- **Application URL:** http://10.93.27.16/

The infrastructure is containerized using Docker Compose. The frontend, backend API, and PostgreSQL database communicate through an internal Docker network, while the frontend is exposed externally through the VM.

---

# Deployment

## Deployment Process

The application is deployed on the project VM using Docker Compose

Deployment process:

1. Pull the latest changes from the GitHub repository
2. Build Docker images for the frontend and backend services
3. Apply database migrations
4. Start or update all containers using Docker Compose
5. Verify that the frontend, backend API, and PostgreSQL services are running
6. Confirm that the application is accessible through the project VM

---

## Feedback Strategy

### Methods

User feedback was collected through usability testing sessions with **five stakeholders**. Individual meetings were conducted with each participant, allowing them to complete predefined usage scenarios and provide structured feedback.

The stakeholder group included both **experienced technical users and less experienced users**, enabling the team to evaluate the product from different perspectives. One of the stakeholders was **an international participant**, providing additional feedback on usability.

After each session, observations, comments, and improvement suggestions were documented and converted into backlog items for future development.

---

## Feedback Collected

### Positive Feedback

- The project is highly relevant and addresses a real security problem
- The combination of a CLI client and a zero-knowledge architecture makes the product technically convincing
- The interface and CLI are intuitive and easy to understand
- The application already provides a rich feature set, including secure secret storage, encrypted local vault, PIN protection, and file-based workflows
- The overall implementation appears practical and security-oriented
  
### Improvement Suggestions

- Add an alias to the installation command so users do not need to type `./`
- Use issue numbers consistently in branch names (e.g., `issue-111`)
- Add a test coverage report and describe how to generate it in the README
- Optionally add a coverage badge to the README
- Add `rm` as an alias for the `delete` command
- Add a short `-f` alias for the `--force` flag
- Refactor settings initialization to avoid global side effects
- Warn users when recreating a previously deleted secret
- Make repeated soft-delete operations idempotent

### Issues Identified
- Some branches do not reference their corresponding GitHub issues
- The project currently does not expose test coverage information in the documentation
- The CLI command naming could be more consistent with common Unix conventions
- Secret deletion behavior could be improved to provide a better user experience and avoid accidental data loss

---

## Key Findings

The stakeholder found the product easy to use and technically well designed. Most of the feedback focused on improving developer experience, CLI usability, and project documentation rather than changing the core functionality. These suggestions will be converted into backlog items and prioritized for future sprints.

---

# Internal Review

## Demo Summary
The team demonstrated the current version of the application, including the web interface, CLI client, backend API, encrypted local storage, trusted device support, and multi-device synchronization. The implemented functionality was reviewed against the sprint goals, and the received feedback was analyzed to identify improvements for the next iteration.

---

## Feedback from Team
- Continue improving CLI usability
- Increase visibility of automated test coverage
- Improve project documentation and installation instructions
- Refine secret deletion workflow and edge-case handling
- Convert stakeholder suggestions into backlog items for future sprints

---

# Industrial Track Contribution

## Product Stakeholder Feedback
The stakeholder confirmed that the project solves a relevant problem and provides a practical implementation of secure secret management. The overall architecture, security model, and CLI workflow received positive feedback. Several usability and developer-experience improvements were suggested and will be addressed in future sprints.

---

## Progress Against Baseline
Compared to the previous sprint, the project significantly expanded its functionality. Multi-device access and secret synchronization were implemented, backend test coverage exceeded 80%, CI/CD pipelines were extended to support backend, frontend, and CLI components, and deployment on the project VM was completed. Stakeholder feedback was collected and incorporated into the project backlog to guide future development.
---

# Daily Standups

## 24 June 2026

| Team Member  | Daily Update                                                                                                                                                       |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Arseny**   | Discussed the tasks planned for the current sprint and agreed on priorities for the week |
| **Svetlana** | Reviewed the sprint backlog, discussed new sprint rules and the workflow, and confirmed task priorities for the upcoming week |
|  **Elina**     | Did not attend the standup   |
| **Emil**      | Did not attend the standup   |
| **Aleksander**    | Did not attend the standup   |
| **Malik**   | Did not attend the standup   |

---

## 26 June 2026

| Team Member    | Daily Update    |
| -------------- | ------------------------------------------- |
| **Elina**      | Continued refining UI details and started designing the dark theme for the application  |
| **Emil**       | Landing page implementation is still in progress. Plans to complete the landing page, responsive layout, and frontend implementation of the Login, Registration, and Dashboard pages by the end of the weekend |
| **Malik**      | Completed the **Multi-Device Access** functionality. Started implementing synchronization between trusted devices and plans to complete backend tests                                                         |
| **Aleksander** | Continued studying Go and preparing for CLI development. Plans to implement all CLI tasks currently in the **To Do** column of the sprint backlog                                                              |
| **Svetlana**      | Did not attend the standup   |
| **Arseny**     | Did not attend the standup   |
---

## 29 June 2026

| Team Member    | Daily Update    |
| -------------- | ------------------------------------------- |
| **Elina**      | Continued refining UI details and the application dark theme design. |
| **Emil**       | Continued developing the landing page and adding new sections based on the approved design. |
| **Malik**      | Did not attend the standup                                                  |
| **Aleksander** | Completed the assigned CLI tasks and plans to finish the remaining review comments before being admitted to the hospital. |
| **Svetlana**      | Continued preparing the sprint report and organizing sprint deliverables |
| **Arseny**     | Continued improving the CI/CD pipelines, refining GitHub Actions workflows, and working on deployment automation  |
---

## 30 June 2026

### Only Arseny, Malik, and Svetlana attended the daily standup. The team discussed the current sprint progress, reviewed the remaining tasks, and then conducted usability testing sessions with five stakeholders. Feedback from all meetings was collected and documented, and the identified improvements will be added to the product backlog and prioritized for the next sprint.
---

# Relevant Links
Figma - https://www.figma.com/design/e9yJfGqSkREVk5sjPocKHN/Untitled?node-id=0-1&t=edpuYY4hWFmTym6q-1
Workflow - https://github.com/svetlana1959/GophKeeper/tree/main/.github/workflows




## Issues

- Issue #102 - Design Dark Theme - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=204164117&issue=svetlana1959%7CGophKeeper%7C102
- Issue #101 - Write Sprint 4 report template - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=204154413&issue=svetlana1959%7CGophKeeper%7C101
- Issue #100 - Write Sprint 4 report - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=204154121&issue=svetlana1959%7CGophKeeper%7C100
- Issue #104 - User Feedback - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=204167222&issue=svetlana1959%7CGophKeeper%7C104
- Issue #103 - Detail User Actions and Interaction Flows - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=204166686&issue=svetlana1959%7CGophKeeper%7C103
- Issue #36 - Implement set command (create a secret) - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197617813&issue=svetlana1959%7CGophKeeper%7C36
- Issue #74 - Implement set command (update a secret) - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=201369906&issue=svetlana1959%7CGophKeeper%7C74
- Issue #39 - Implement delete command (remove a secret) - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197619359&issue=svetlana1959%7CGophKeeper%7C39
- Issue #37 - Implement get command (read a secret) - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197618672&issue=svetlana1959%7CGophKeeper%7C37
- Issue #38 - Implement list command (list secrets) - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197618939&issue=svetlana1959%7CGophKeeper%7C38
- Issue #32 - Implement distributed crypto-engine - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197240876&issue=svetlana1959%7CGophKeeper%7C32
- Issue #23 - Create local configuration storage - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197205187&issue=svetlana1959%7CGophKeeper%7C23
- Issue #33 - Implement local secret database - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197263931&issue=svetlana1959%7CGophKeeper%7C33
- Issue #22 - Implement CLI init command - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197205031&issue=svetlana1959%7CGophKeeper%7C22
- Issue #109 - Implement Full Web Application Frontend - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=204189656&issue=svetlana1959%7CGophKeeper%7C109
- Issue #110 - Configure Continuous Integration (CI) - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=204195437&issue=svetlana1959%7CGophKeeper%7C110
- Issue #111 - Configure Continuous Deployment and Deploy Application - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=204196082&issue=svetlana1959%7CGophKeeper%7C111
  
## Pull Requests

- PR #
- 
---

# Updated Backlog
Project backlog and sprint planning are managed using GitHub Projects.
Link: https://github.com/orgs/svetlana1959/projects/4/views/1 and https://github.com/orgs/svetlana1959/projects/6/views/1

## Completed
### Issue: #102, #100, #101, 

## In Progress
### Issue: #109,

## Planned for Sprint 5

* Analyze stakeholder and user feedback collected during Week 4
* Prioritize new backlog items based on the feedback received
* Implement UI/UX improvements and fix reported issues
* Improve application stability and error handling
* Complete remaining planned functionality
* Update project documentation and API documentation
* Deploy the improved application to the VM and validate changes


