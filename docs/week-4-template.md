# Sprint 4 Report

## Project Information

### Track

Industrial

### Project

GophKeeper — a distributed zero-knowledge secret management system designed for secure storage, synchronization, and management of sensitive information across trusted devices.

### Sprint

Week 4

---

# Team Members and Contributions

| Team Member | Role | Contribution | commits/PRs/Issues |
|-------------|------|--------------|--------------------|
| Svetlana Maltseva | Team Lead, Product Manager | Project planning, backlog management, sprint coordination, requirements analysis, sprint documentation | Issues: #100, #104 |
| Elina Akhmetzyanova | Design, Documentation | Dark theme design, sprint template documentation | Issues: #101, #102 |
| Arseny Lashkevich | DevOps Engineer | | |
| Aleksander Goncharov | CLI Engineer | | |
| Emil Nabiullin | Frontend Developer | | |
| Malik Nurullin | Backend Developer | | |

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

---

## Integration Tests

### API Testing

| Endpoint | Test Status | Notes |
|-----------|------------|--------|
| | | |
| | | |

---

## End-to-End Testing

### Tested Flows

- Secret creation
- Secret synchronization
- Device management

---

## Test Results

### Summary

| Test Type | Total | Passed | Failed |
|------------|--------|--------|--------|
| Unit Tests | | | |
| Integration Tests | | | |

---

## Evidence

### Test Screenshots


### CI Logs

---

# CI/CD Pipeline

## Continuous Integration
### Automated Check

---

## Continuous Deployment

### Deployment Flow

---

## Workflow Files

### GitHub Actions

Link:

---

## Evidence

---

# VM Environment Setup

## Infrastructure Overview

### VM Configuration

| Component | Details |
|------------|---------|
| Provider | |
| OS | |
| CPU | |
| Memory | |
| Storage | |

---

## Installed Services

---

## Environment Variables

---

## Networking

---

# Deployment

## Deployment Process

---

## Application Availability

### Live UR

---

## Deployment Evidence

---

# User Feedback Collection

## Feedback Strategy

### Methods

---

## Feedback Collected

### Positive Feedback

### Improvement Suggestions

### Issues Identified

---

## Key Findings

---

# Internal Review

## Demo Summary

---

## Feedback from Team

---

# Industrial Track Contribution

## Product Stakeholder Feedback

---

## Updated Measurements

| Metric | Previous Sprint | Current Sprint |
|----------|---------|---------|
| | | |
| | | |

---

## Progress Against Baseline

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

---

## 30 June 2026

---

# Relevant Links
Figma - https://www.figma.com/design/e9yJfGqSkREVk5sjPocKHN/Untitled?node-id=0-1&t=edpuYY4hWFmTym6q-1



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

## CI/CD Configuration

---

## Live Application

---

# Updated Backlog
Project backlog and sprint planning are managed using GitHub Projects.
Link: https://github.com/orgs/svetlana1959/projects/4/views/1 and https://github.com/orgs/svetlana1959/projects/6/views/1

## Completed
### Issue: #102, #100, #101, 

## In Progress
### Issue: #109,

## Planned for Sprint 5

* Analyze stakeholder and user feedback collected during Week 4.
* Prioritize new backlog items based on the feedback received.
* Implement UI/UX improvements and fix reported issues.
* Improve application stability and error handling.
* Complete remaining planned functionality.
* Update project documentation and API documentation.
* Deploy the improved application to the VM and validate changes.


