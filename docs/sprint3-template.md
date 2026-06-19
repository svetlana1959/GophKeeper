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
| Arseny Lashkevich | DevOps Engineer |  |
| Aleksander Goncharov | CLI Engineer | |
| Emil Nabiullin | Frontend Developer | Frontend layout implementation, UI integration, web page development based on approved mockups |
| Malik Nurullin | Backend Developer | |


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
The application now allows authenticated users to create and securely store secrets. Before being stored locally, secret data is encrypted to ensure confidentiality. The system validates required fields and provides feedback on successful or failed operations.

### (2) Secret Management
Users can now view all secrets available to them. displays secret names and contents, supports empty states when no secrets exist, and ensures that users can only access secrets they own or are authorized to view.

Users can also update existing secrets. Changes are validated before being saved, invalid updates are rejected, and users may cancel modifications without affecting stored data.


### (3) Multi-Device Access
Support for trusted devices has been added. Users can access their encrypted secrets from multiple approved devices. Synchronization ensures that data remains consistent across devices, while untrusted devices are denied access.


### Digital Inheritance (Planned Feature)
A new digital inheritance feature is planned for future releases. During registration, users will be able to designate a trusted beneficiary who may receive access to selected secrets in exceptional circumstances.

The system will periodically verify the activity of the account owner. If prolonged inactivity is detected, additional verification requests will be sent to confirm that the owner is still active. If verification attempts remain unanswered for a predefined period, access to designated secrets may be transferred to the trusted beneficiary according to the user's predefined settings.

This feature aims to provide secure digital legacy management while preserving user privacy and preventing unauthorized access.
---

## Frontend Updates

---

## Backend Updates


---

## Database Update

---

## Infrastructure Updates


---

# Screenshots / GIFs

---

# Architecture / Technical Decisions

## Decisions Made

---

## Challenges Encountered

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

Summary of the Sprint 2 state.

---

## Improvements Added

| Area | Sprint 2 | Sprint 3 |
|--------|--------|--------|
| Authentication | | |
| Secret Management | | |
| Synchronization | | |
| Infrastructure | | |
| Web Application | | |

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

- Issue #XX
- Issue #XX
- Issue #XX

---

## Pull Requests

- PR #XX
- PR #XX
- PR #XX

---

# Updated Backlog

## Completed
---

## In Progress

---

## Planned for Sprint 4

---

# Next Steps

## Sprint 4 Priorities


# Appendix
