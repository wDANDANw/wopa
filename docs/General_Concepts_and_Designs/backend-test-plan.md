# WOPA Backend Module - Test Plan

## 1. Introduction

### 1.1 Objectives

This test plan aims to validate the **WOPA Backend Module**—the central coordination layer that orchestrates communication between the user-facing frontend, various worker modules, and external provider services. The Backend Module sits at the heart of WOPA’s architecture, receiving incoming requests from clients (e.g., the frontend or mobile app), dispatching tasks to workers, managing configurations, and providing admin interfaces for oversight and control.

**Primary Goals:**

- Confirm that all backend endpoints (`/api/analyze/message`, `/api/analyze/link`, `/api/analyze/file`, `/api/analyze/app`, `/api/task`, `/api/login`, `/api/search_history`, `/api/add_history`, and `/admin` UI) behave as per specifications.
- Validate input validations, error handling, response formatting, and integration with the worker subsystem and data stores (e.g., Redis and MySQL).
- Ensure that batch saving, partial result recording, logging, and responsiveness (progress bars, ETA estimates) are functioning correctly.
- Prepare for future integration tests with actual workers and providers, ensuring that the backend’s logic is sound and stable at the unit and integration levels.

This plan ensures that all functional and non-functional requirements associated with the Backend Module are thoroughly tested before larger-scale system or acceptance testing. It sets a robust foundation for ongoing quality assurance within the WOPA ecosystem.

### 1.2 Team Members

**Roles:**

- **Developers (Backend):** Implement and maintain backend endpoints and integration logic with workers and databases. They fix defects uncovered by tests.
- **Test/QA Engineers:** Design and enhance test coverage, add complex scenarios, maintain test data, and ensure results are well-documented.
- **DevOps/Infrastructure Team:** Manage Docker, Compose, and CI integration, ensuring a consistent and reproducible test environment.
- **Project Manager/Lead:** Monitors test progress, ensures that test coverage meets project standards, and decides on release readiness based on test outcomes.

All team members reference this plan for guidance on test coverage, requirements mapping, environment setup, and reporting processes.

---

## 2. Scope

This test plan focuses on **unit-level and partial integration-level** testing of the Backend Module, ensuring it operates correctly in isolation and with mocked worker and database interactions. The scope includes:

- **Endpoint-Level Testing:**  
  Ensuring each endpoint (e.g., `/api/analyze/message`) returns correct HTTP statuses, validates inputs, and provides structured responses.
  
- **Database and Redis Integration (Mocked or Partial):**  
  Confirming that queries to MySQL (for user history) and state tracking in Redis (for tasks) work as expected. Initial tests may mock databases or run them in Docker containers, verifying CRUD operations through standardized test data.
  
- **Authentication and Authorization Checks:**  
  Testing login and history retrieval endpoints ensures that authentication (e.g., `/api/login`) and data retrieval (`/api/search_history`, `/api/add_history`) conform to security and data integrity requirements.
  
- **Batch Saving and Logging Mechanics:**  
  Verifying that partial results are saved as CSV at certain intervals and that logs (e.g., `progress.log` or `general_log.csv`) are updated at the correct frequencies and formats.
  
- **Progress, ETA, and Admin UI Checks:**  
  Confirming that the backend can report progress (e.g., every 5%), produce ETAs, and display them. Also verifying that the admin UI (`/admin`) is accessible and stable.

**Not in Scope:**
- Full end-to-end system tests with real Providers and Workers. This plan focuses on the backend in isolation. Integration with real Worker results or Provider services is handled by separate integration test plans.

---

## 3. Assumptions and Risks

### 3.1 Assumptions

- **Stable Worker and Provider Interfaces (Mocked):**  
  The backend’s calls to Workers or Providers are initially mocked. Tests assume that once real integration begins, minimal changes are needed if endpoints remain stable.
  
- **Consistent Database Schema:**  
  The MySQL schema for Accounts and History tables (used by `/api/login`, `/api/search_history`, `/api/add_history`) is stable and matches test data files. If schemas change, test data and queries must be updated.
  
- **Environment Setup:**  
  Running `make test-unit-backend` or `make test-integration-backend` sets up a suitable Docker environment with mocked or real dependencies as needed.

### 3.2 Risks

- **Changing Requirements:**  
  If endpoints or data schemas change, test coverage must adapt quickly. The mapping of UC-REQ-FEAT-TEST ensures that any requirement changes are easily traceable.
  
- **Limited Real Integration at Unit Stage:**  
  Because we rely on mocks or partial Docker setups, some real-world issues (network latency, unexpected provider downtime) may not be fully replicated at this stage.
  
- **Data Volume or Performance Unknowns:**  
  While we may measure average request times and do partial load scenarios, comprehensive performance testing is deferred until after initial stability is proven.

By acknowledging these assumptions and risks, we maintain a flexible, maintainable test plan that can evolve as the project matures.

---

## 4. Requirement Verification Matrix (RVM)

| Requirement                                                        | T | D | A | I | Notes                                                                |
|--------------------------------------------------------------------|---|---|---|---|---------------------------------------------------------------------|
| Backend must handle `/api/analyze/message/link/file/app` endpoints | X |   |   | I | Unit tests confirm correct JSON responses & input validation.       |
| Backend must integrate with workers (mocked) to get analysis result | X |   |   | I | Tests mock Worker endpoints; correct results & error handling checked. |
| Backend must handle `/api/task` endpoints to retrieve tasks/results | X |   |   | I | Tests ensure tasks can be listed, partial results known.             |
| Backend must support `/api/login` and store/fetch histories in DB   | X | D |   | I | Unit tests with mocked DB confirm queries return expected JSON. D can show admin UI with login form. |
| Backend must save partial results every 5% & handle KeyboardInterrupt | X |   |   | I | Tests simulate partial processing & Ctrl+C, verifying CSV/log saved. |
| Backend must show admin UI (`/admin`) for oversight                 | X | D |   | I | Tests check `/admin` returns HTML; D to show admin accessing UI.     |
| Backend must return ETAs and progress bars in outputs/logs          | X | D |   | I | Unit tests confirm progress line formatting; D scenario to show admin. |

**Interpretation:**  
Mostly verified by Tests (T). Demonstration (D) can be used to visualize admin UI behavior. Inspection (I) ensures code and logs confirm compliance. Analysis (A) is minimal at this stage, as no complex performance modeling is done yet.

---

## 5. UC-REQ-FEAT-TEST Mapping

| Use Case (UC)                                              | Requirement (REQ)                                            | Feature (FEAT)                                                | Test Case IDs                                                 |
|------------------------------------------------------------|---------------------------------------------------------------|---------------------------------------------------------------|---------------------------------------------------------------|
| UC: User submits message for analysis                      | Must process `/api/analyze/message` input validation & results | `/api/analyze/message` endpoint calling workers                | T-Backend-Message-001, -002                                   |
| UC: User checks link analysis                              | Must process `/api/analyze/link` similarly                    | `/api/analyze/link` endpoint                                  | T-Backend-Link-001, -Error-001                                |
| UC: User logs in via `/api/login`                          | Must authenticate against MySQL users                         | `/api/login` endpoint, DB queries                             | T-Backend-Login-001, T-Backend-Login-Invalid-001              |
| UC: User retrieves search history via `/api/search_history`| Must query MySQL `Historys` table                             | `/api/search_history` endpoint, DB access                     | T-Backend-History-001, -002                                   |
| UC: User adds a history record `/api/add_history`          | Must insert into `Historys` table                             | `/api/add_history` endpoint, DB insert                        | T-Backend-AddHistory-001                                      |
| UC: Enqueue tasks & retrieve them                          | Must handle `/api/task` endpoints for listing/retrieving tasks | `/api/task` and related endpoints, WorkerManager integration   | T-Backend-Tasks-001, T-Backend-Results-001                    |
| UC: Partial result saving every 5%, handle Ctrl+C          | Must save CSV/log and exit gracefully on interrupt             | Internal logic triggered by processed count & signal handling  | T-Backend-BatchSave-001, -CtrlC-001                          |
| UC: Admin UI oversight at `/admin`                         | Must serve admin interface for config & task view             | `/admin` endpoint (Gradio UI)                                 | T-Backend-AdminUI-001                                        |
| UC: Progress & ETA in results/logs                         | Must compute & display ETA in progress lines                  | Updated progress print lines in code                           | T-Backend-Progress-001, -ETA-001                              |

This mapping ensures each UC is clearly tied to requirements, features, and test cases, providing traceability and simplifying maintenance.

---

## 6. Endpoints and External Interfaces

### Backend Endpoints

- **Analyze Endpoints:**  
  - `/api/analyze/message`, `/api/analyze/link`, `/api/analyze/file`, `/api/analyze/app`:
    Validate inputs, call workers (mocked), return final JSON (`status`, `result` or `error`).
- **Task Endpoints:**  
  `/api/task` and related query endpoints to list tasks, fetch partial or final results.
- **User & History Endpoints:**  
  `/api/login`, `/api/search_history`, `/api/add_history` connect to MySQL DB:
  - `login` verifies username/password from Accounts table.
  - `search_history` and `add_history` read/write to Historys table, return JSON.

- **Admin UI Endpoint:**  
  `/admin` shows the Gradio-based dashboard, enabling progress view, config display, and quick checks.

### External Dependencies (for now mocked at unit tests):

- **Workers Subsystem Endpoints:**  
  Worker results are mocked by patching calls that the backend would normally make.  
  Integration tests may later confirm real worker calls.

- **MySQL and Redis:**  
  At unit level, MySQL and Redis might be mocked or run as containers with test data.  
  The backend tests verify CRUD and retrieval logic from these stores.

By detailing endpoints and interfaces, the team can ensure that tests cover all expected communication paths.

---

## 7. Unit Test Plan and Test Cases

This section enumerates the planned unit tests that run under `MODE=unit-test`, using mocks for external dependencies:

**Categories:**

- **Endpoint Validation Tests:**  
  Check that each endpoint returns correct HTTP codes and JSON for various inputs.
- **Database Interaction Tests:**  
  Verify correct SQL queries to MySQL Accounts and Historys tables. With mocking or a test DB, confirm that inserts and queries produce expected results.
- **Task Lifecycle & Partial Saving Tests:**  
  Confirm that partial results are saved every 5%, CSV files appear in `./outputs`, and that on `KeyboardInterrupt`, final partial results are saved.

**Example Test Cases:**

- **T-Backend-Message-001:** `/api/analyze/message` with valid input returns `completed`  
- **T-Backend-Message-002:** `/api/analyze/message` with missing `content` returns `400 error`

- **T-Backend-Link-001:** `/api/analyze/link` with a safe link mock returns low risk  
- **T-Backend-Link-Error-001:** `/api/analyze/link` with domain check error returns `{"status":"error"}`

- **T-Backend-Login-001:** `/api/login` with correct credentials returns `{"success":True,...}`  
- **T-Backend-Login-Invalid-001:** `/api/login` invalid creds returns `{"success":False,...}`

- **T-Backend-History-001:** `/api/search_history?AccountID=...` returns expected JSON from mocked DB  
- **T-Backend-AddHistory-001:** `/api/add_history` inserts a record, confirm success JSON

- **T-Backend-Tasks-001:** `/api/task` lists tasks, `/api/get_worker_results` returns final results after mocking worker output.

- **T-Backend-BatchSave-001:** Process some tasks, after reaching 5%, confirm `message_out_batch1.csv` saved.  
- **T-Backend-CtrlC-001:** Simulate `KeyboardInterrupt` mid-run, confirm partial CSV/log output saved and script exits gracefully.

- **T-Backend-Progress-001:** Confirm that after each processed item, progress bar updates, and ETA is computed (mock time for stable results).

- **T-Backend-AdminUI-001:** `/admin` returns HTML page with expected placeholders or UI elements.

### Mocking Strategies for Backend Tests

- **Workers:**  
  Calls to workers are replaced by patches that return pre-defined JSON results for normal or error scenarios.
  
- **MySQL and Redis:**  
  Replace actual DB calls with in-memory mocks or a test container with known test data. Queries return fixed rows for login and history tests.

- **File System for Partial Results:**  
  Mock filesystem operations or write to a temporary directory. After test completion, check CSV files created.

### Test Execution

- Run `make test-unit-backend`:
  - Builds a Docker image with code and runs pytest inside, capturing output and any coverage reports.

- If all tests pass, we have confidence that the backend logic is correct, stable, and ready for integration tests.

---

## 8. Integration Test Plan and Test Cases

**Future Steps (Once Workers & Providers are real):**

Integration tests for the backend check if actual worker and provider responses integrate seamlessly. For now, the focus is on unit tests with mocks. When integration testing is possible, these tests confirm that no schema mismatches or endpoint naming issues appear, and that the backend can handle real latency or partial failures gracefully.

Key integration tests might include:

- **T-Backend-Integration-Worker-001:** `/api/analyze/message` calling a real text worker container.  
- **T-Backend-Integration-DB-001:** Using a real MySQL test DB with actual rows to verify login and history queries.  
- **T-Backend-Integration-Progress-001:** Running a large batch of tasks and checking CSVs in `./outputs` appear correctly in a real environment.

Such integration tests will run in a dedicated environment with `docker-compose.integration.yml` that includes real worker and DB containers.

---

## 9. Test Environment and Tools

Similar to the Worker Module test plan:

- **Python + Pytest:**  
  For unit and future integration tests.
  
- **Docker and Docker Compose:**  
  Spin up backend container with optional MySQL and Redis containers.  
  Use `make test-unit-backend` or `make test-integration-backend` as appropriate.

- **Logging and Monitoring:**  
  Backend logs at INFO/ERROR level help investigate test failures. Coverage reports identify untested code paths.

---

## 10. Test Reporting

- **Console Output & CI Artifacts:**  
  Pytest results displayed on console, CI pipeline to enforce quality gates.
  
- **JSON/XML Reports & Coverage:**  
  Optional JUnit XML or JSON can integrate with dashboards. Coverage reports highlight coverage over backend code.

- **Historical Trends:**  
  Storing test results over time can reveal if changes degrade stability or coverage.

Decisions such as release readiness or regression checks stem from analyzing these test reports.

---

## 11. Roles and Responsibilities

- **Developers:** Write and maintain tests for their implemented endpoints or DB logic. Fix defects as tests reveal them.
- **Test/QA Engineers:** Expand scenarios, refine mocks, and ensure coverage and clarity. Eventually integrate real providers for integration testing.
- **DevOps Team:** Maintain CI/CD for backend tests, ensure stable environments.
- **PM/Lead:** Review test coverage and decide readiness based on passing critical tests.

---

## 12. Schedule and Milestones

- **Unit Tests Completion:**  
  Achieve passing status for all planned unit tests before starting integration tests.
  
- **Integration Tests Start:**  
  Once real workers and providers are stable, begin integration tests. Initially run a subset of scenarios (e.g., a single analyze endpoint) before expanding coverage.

- **Pre-Release Checks:**  
  After both unit and integration tests consistently pass, the backend module can be integrated system-wide and eventually tested under staging or user acceptance conditions.

---

## 13. Conclusion and References

This Backend Module test plan provides a structured, comprehensive approach to verifying endpoint correctness, DB interactions, partial saving logic, and admin UI accessibility. By mapping requirements to use cases, features, and tests, the plan ensures transparent coverage, easy maintenance, and confidence in backend quality.

As the project evolves, integration tests will follow naturally, building on strong unit test foundations. Logs, coverage reports, and CI pipelines reinforce ongoing quality. This plan stands as a key reference document guiding all team members through the testing phases, from development to final release readiness.

**References:**
- WOPA Project Charter & Philosophies (internal)
- Backend Module Requirements and API Specs
- Worker Module and Providers Subsystem Documentation

This document ensures that every aspect of the backend’s logic, endpoints, and data handling is diligently tested before larger-scale integration and acceptance testing, contributing significantly to WOPA’s reliability and user trust.
