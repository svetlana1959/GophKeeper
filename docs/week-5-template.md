# Sprint 5 Report

## Project Information

### Track

Industrial

### Project

GophKeeper — a distributed zero-knowledge secret management system designed for secure storage, synchronization, and management of sensitive information across trusted devices.

### Sprint

Week 5

---

# Team Members and Contributions

| Team Member | Role | Contribution | PR/Issues |
|-------------|------|-------------|------|
| **Svetlana Maltseva** | Team Lead, Product Manager | Coordinated sprint activities, organized stakeholder interviews, analyzed collected feedback, updated the backlog, and prepared sprint documentation and reports | Issues: #127 |
| **Elina Akhmetzyanova** | Design, Documentation | Designed the mobile versions of the Registration, Login, and Dashboard screens. Created detailed interaction states for the desktop UI, including default, loading, success, and error scenarios for key user actions | Issues: #128, #103, #131|
| **Arseny Lashkevich** | DevOps Engineer | Improved the CI/CD infrastructure, worked on the recovery strategy for deployments, and refined GitHub Actions workflows | |
| **Aleksander Goncharov** | CLI Engineer | Was unable to contribute during most of the sprint due to hospitalization | |
| **Emil Nabiullin** | Frontend Developer | Implemented the Registration and Login pages, continued developing the landing page, and integrated frontend components based on the approved UI designs |  Issues: #109 |
| **Malik Nurullin** | Backend Developer | Adapted the backend to the new device and secret architecture, implemented the Device Revoke backend functionality with automated tests, fixed integration tests after database schema changes, resolved backend issues, and prepared the foundation for the remaining M4 backend tasks |  Issues: #16, #119, #112; PR: #133, #112, #119|

---

# Sprint Goal

Turn user feedback into prioritized improvements, implement refinements, fix issues, and improve the overall usability and quality of the product.

---

# Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| Limited development time| High | High | Prioritize MVP features, maintain weekly sprint reviews, postpone non-critical functionality |
| Team member illness or absence | High | High | Reassign unfinished tasks to available team members, adjust sprint scope if necessary, and maintain regular progress tracking |
| Major architectural changes during development | Medium | High | Regularly review the architecture, validate design decisions early, and allocate time for refactoring when requirements evolve |



# Feedback Analysis

Feedback was collected through individual usability testing sessions with five stakeholders. The group included both technical and non-technical users, as well as one international participant. Each stakeholder completed predefined usage scenarios and provided structured feedback on usability, functionality, and the overall user experience.

---

## Summary of Collected Feedback

| Source | Feedback | Priority |
|--------|----------|----------|
| Stakeholders | The overall concept and zero-knowledge architecture received very positive feedback | High |
| Stakeholders | Improve CLI usability by adding aliases (e.g., `rm`, `-f`) and simplifying installation commands | High |
| Stakeholders | Add test coverage documentation and a coverage badge to the README | Medium |
| Stakeholders | Improve project conventions (branch naming, issue references, commit messages) | Medium |
| Stakeholders | Improve secret deletion behavior and provide clearer warnings when restoring deleted secrets | Medium |

---

## Prioritized Improvements

| Improvement | Reason | Priority | Status |
|-------------|--------|----------|--------|
| Improve CLI usability (aliases, installation command) | Requested by multiple stakeholders | High | Planned |
| Improve secret deletion workflow | Prevent accidental data loss and improve UX | High | Planned |
| Refactor backend architecture for multi-device support | Support secure synchronization and trusted devices | High | In Progress |
| Improve project documentation and README | Simplify onboarding and development | Medium | Planned |
| Add test coverage report and documentation | Increase project transparency and code quality | Medium | Planned |
| Adopt consistent Git workflow conventions | Improve collaboration and repository organization | Low | Planned |


# Product Improvements

## Documentation Improvements

### API Documentation

The backend API is documented using automatically generated Swagger/OpenAPI documentation provided by FastAPI. It describes all available REST endpoints, request and response models, authentication requirements, and data schemas used by the system. The documentation also allows developers to test API endpoints directly from the browser. During this reporting period, the API documentation was updated to reflect the new multi-device synchronization architecture and the redesigned device management workflow.

<img width="959" height="884" alt="Снимок экрана 2026-07-07 234500" src="https://github.com/user-attachments/assets/b046b6c7-5aa9-42a7-a50a-c40716f3ada6" />


### Mobile UI

The mobile versions of the main application screens were designed to improve usability on smartphones.

#### Dash Mob Dark

#### LogIn Mob

#### Dash Mob

#### Reg Mob Dark

#### LogIn Mob Dark

#### Reg Mob

#### Registration Creating Account

#### Registration Creating

#### Registration Dark Creating Account Error

#### Registration Dark Creating Account

#### Registration Dark Creating

#### Registration Dark

#### Registration Success

#### Registration Creating Account Error

#### Login Dark Error

#### Login Dark Loading

#### Login Dark

#### Login Error

#### Login Loading

---

### Registration & Login Pages

The Registration and Login pages were fully implemented based on the approved UI designs. Their functionality and user interface are demonstrated in the accompanying video included in this report


## Bug Fixes

| Bug | Solution |
|------|----------|
| Integration tests relied on the deprecated `is_active` model after the device architecture redesign. | Updated the tests to use the new device lifecycle model (`pending`, `active`, `revoked`). |
| Integration tests created `Device` objects without the required fields introduced by the new architecture (`account_id`, `status`, etc.). | Updated test fixtures and device creation scenarios to match the new data model. |
| The database cleanup fixture used an outdated list of tables (`access_requests`, `secret_access`), which could leave stale data after schema changes. | Updated the cleanup procedure to reflect the current database schema. |
| Some integration tests still validated the old repository behavior (`list_active`) instead of the new account-based logic. | Adapted the tests to use the new `list_for_account` repository behavior. |
| There was no backend support for revoking the currently authenticated device. | Implemented the `POST /devices/self/revoke` endpoint and the corresponding backend service. |
| Revoked devices were still able to access protected endpoints until their session expired. | Added device lifecycle validation during authentication and verified the behavior with automated tests. |
| Repeated calls to `Device.revoke()` modified the `updated_at` timestamp, although the operation should be idempotent. | Fixed the revoke logic so repeated calls no longer modify the device state. |
| The synchronization result status (`PushResultResponse.status`) was represented as an unrestricted string. | Replaced it with a `StrEnum` to enforce valid values and improve the generated OpenAPI documentation. |
| No dedicated tests existed for the new self-revoke functionality. | Added unit tests for the service and router, along with repository persistence checks. |
| There was no verification that revoked devices were excluded from synchronization recipients. | Added tests confirming that revoked devices are not included in the recipients list. |
| The codebase still contained outdated comments and docstrings referring to the previous device architecture. | Updated comments, docstrings, and internal documentation to match the new architecture. |
| The README and internal documentation partially described the old backend architecture. | Updated the documentation to reflect the current project architecture. |

---

## Feature Enhancements

- Mobile UI design completed
- Desktop interaction states designed
- Improved user experience based on stakeholder feedback


### Architecture Improvements

During Sprint 5, the team redesigned the backend architecture to support multi-device access.

Initially, the system architecture assumed that each secret belonged to a single device. As multi-device support became a project requirement, this design introduced several limitations. It was difficult to securely synchronize secrets between devices, connect new devices to an existing account, or revoke access from lost or compromised devices without significantly changing the data model and authorization logic.

To address these issues, the architecture was redesigned. Secrets are now owned by a user account rather than an individual device, while devices are treated as trusted members of the account. Each device has its own lifecycle (registration, activation, and revocation), and access to encrypted secrets is managed through trusted recipients and the synchronization mechanism.

This redesign enables secure multi-device synchronization, safe onboarding of new devices, independent device revocation, and provides a solid foundation for future features such as account recovery, trusted device management, and maintaining the zero-knowledge security model where the server never has access to users' decrypted secrets.
---

## Error Handling Improvements

- Updated backend validation to support the new account-based device architecture
- Added validation for the new device lifecycle (`pending`, `active`, `revoked`)
- Added automated tests covering the new device lifecycle and self-revoke functionality

---

## Performance Improvements

The main focus of this sprint was the architectural redesign required for multi-device support

---

## Documentation Improvements

- Updated the backend documentation to reflect the new architecture
- Updated code comments and docstrings
- Updated the OpenAPI (Swagger) documentation


---

# Test Results

### Coverage Report

Backend automated tests currently include **58 passing tests** with **77% overall code coverage**.

<img width="1135" height="961" alt="Снимок экрана 2026-07-07 233142" src="https://github.com/user-attachments/assets/10f5359a-ac82-4040-b39e-94a2308a8f96" />

## Tests Summary

### Unit Tests

| File | What is tested |
|---|---|
| `test_secret.py` | Secret update, version conflicts, idempotent delete, invalid state validation. |
| `test_device.py` | Device lifecycle: activate, revoke, invalid status handling. |
| `test_device_service.py` | Account/device registration, fetching devices, self-revoke logic. |
| `test_device_router.py` | `POST /devices/self/revoke`, revoked token invalidation, 404 case. |
| `test_auth_service.py` | Challenge/verify auth flow, token validation, revoked device rejection. |
| `test_enrollment_service.py` | Invite/join flow, invalid/expired/used codes, duplicate public key. |
| `test_tokens.py` | Token signing, verification, tampering, expiration, malformed tokens. |
| `test_sync_schema.py` | Push result status enum validation and OpenAPI schema values. |
| `test_sync_service.py` | Push/pull sync, conflicts, tombstones, recipients, revoked device exclusion. |

### Integration Tests

| File | What is tested |
|---|---|
| `test_account_repository.py` | Saving and loading account recovery public key from real DB. |
| `test_device_repository.py` | Device save/fetch, revoked status persistence, rollback, account device listing. |
| `test_secret_repository.py` | Secret save/fetch round trip and rollback behavior in real DB. |


# Internal Review

## Demo Summary

The sprint results were presented to the team during the internal review meeting. The demonstration included the updated backend architecture, multi-device support, Device Revoke functionality, Swagger API documentation, the implemented Registration and Login pages, and the new mobile UI designs. The team also reviewed stakeholder feedback collected during usability testing and compared the completed work against the sprint goals.

---

## Team Feedback

The team agreed that redesigning the backend architecture was necessary to support secure multi-device synchronization and future account management features. The implemented UI improvements and API documentation were considered a significant step toward a production-ready system.
The team also identified several areas for future improvement, including completing the remaining frontend pages, enhancing CLI usability based on stakeholder feedback, and finalizing the new synchronization workflow.

---

## Follow-up Tasks

- Complete the remaining frontend pages (Dashboard and Trusted Devices)
- Finish the new multi-device synchronization workflow
- Implement the remaining CLI improvements requested during stakeholder interviews
- Continue improving project documentation and installation instructions

---

# Industrial Track Contribution

## Improvement Against Baseline
Compared to the previous sprint, the project underwent a significant architectural redesign to support secure multi-device access. The backend now follows an account-based model instead of binding secrets to individual devices, enabling secure synchronization, device revocation, and future account recovery features.
In addition, the team expanded the frontend with Registration and Login pages, designed mobile versions of the main screens, improved API documentation through Swagger/OpenAPI, fixed multiple backend issues, and incorporated stakeholder feedback into the product backlog. These improvements make the system more maintainable, scalable, and closer to a production-ready implementation.

# Updated Backlog
Project backlog and sprint planning are managed using GitHub Projects.
Link: https://github.com/orgs/svetlana1959/projects/4/views/1 and https://github.com/orgs/svetlana1959/projects/6/views/1

## Completed
### Issue: #16, #128, #127, #103, #131, #112


## In Review
### Issue: #119

## In Progress
### Issue: #109


## GitHub Issues

- #41 - Implement goph device request command -  https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197623524&issue=svetlana1959%7CGophKeeper%7C41
- #43 - Implement device approve command - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197623533&issue=svetlana1959%7CGophKeeper%7C43
- #42 - Implement goph device list-requests command - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197623530&issue=svetlana1959%7CGophKeeper%7C42
- #44 - Implement goph device revoke command - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=197623545&issue=svetlana1959%7CGophKeeper%7C44
- #16 - Write API documentation - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=196725437&issue=svetlana1959%7CGophKeeper%7C16
- #131 - Design Mobile Version of the Application - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=207113642&issue=svetlana1959%7CGophKeeper%7C131
- #109 - Implement Full Web Application Frontend - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=204189656&issue=svetlana1959%7CGophKeeper%7C109
- #128 - Write Sprint 5 template - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=207097892&issue=svetlana1959%7CGophKeeper%7C128
- #127 - Write Sprint 5 report - https://github.com/orgs/svetlana1959/projects/4/views/1?pane=issue&itemId=207097709&issue=svetlana1959%7CGophKeeper%7C127


---

## Pull Requests

- #119 - Feature/synchronization - https://github.com/svetlana1959/GophKeeper/pull/119
- #112 - Feature/69 multi device access - https://github.com/svetlana1959/GophKeeper/pull/112
- #133 - backend: add device self-revoke endpoint - https://github.com/svetlana1959/GophKeeper/pull/133

---

## Live Application

http://10.93.27.16/
---

# Plans for Sprint 6

- Complete the remaining high-priority features
- Fix critical bugs and perform final testing
- Finalize project documentation and API documentation
- Verify deployment and reproducibility on the project VM
- Prepare the project for release by freezing the codebase and completing the final review

