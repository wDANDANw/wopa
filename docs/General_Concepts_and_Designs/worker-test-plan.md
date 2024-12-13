# WOPA Worker Module - Finalized Test Plan

## 1. Introduction

### 1.1 Objectives

This test plan aims to ensure the **WOPA Worker Module** meets both functional and non-functional requirements before integration with other WOPA subsystems (notably the Providers subsystem) and eventual system-wide verification. The Worker Module is responsible for handling a variety of tasks—such as textual content analysis, link safety checks, and visual verification of app behaviors—by routing requests to appropriate workers and orchestrating their processing and result storage. These tasks depend on external provider endpoints (LLM inference, sandbox analysis, and emulator runs), which are mocked at the unit test level to maintain isolation.

The primary goals of the test plan are:

- Validate correctness and stability of Worker Module endpoints (`/configs`, `/workers`, `/enqueue_task`, `/request_worker`, `/tasks`, `/get_worker_results`, `/admin`).
- Confirm that the **WorkerManager** correctly manages task lifecycle (enqueuing, immediate processing, storing results, and retrieving statuses).
- Ensure each worker type (Text, Link, Visual) correctly validates inputs, processes tasks, handles provider failures gracefully, and returns structured results.
- Provide a clear roadmap for transitioning from unit testing with mocks to future integration testing with real Providers endpoints.
- Maintain a high degree of traceability, linking use cases to requirements, features, and test cases through a structured mapping.

This plan’s careful structuring and documentation support new team members in understanding the test approach, while allowing existing developers to quickly locate relevant tests and verify coverage.

### 1.2 Team Members

**Development and Testing Team:**

- **Shucheng Fang:** Developer/Tester - Focused on Worker Server endpoints and integration with WorkerManager.  
- **Yongcheng Liu:** DevOps/PM/Tester - Handles CI/CD, containerization, and ensures that Makefile, Docker, and Compose align with test needs.
- **Project Team Members:** Additional developers/testers who maintain worker logic, provider mocks, and adapt tests as requirements evolve.

Each team member can use this plan to understand testing scopes, responsibilities, and methods, ensuring collaborative and efficient verification processes.

---

## 2. Scope

The scope of this test plan covers **unit-level testing** of the Worker Module. The unit tests verify logic in isolation, relying on mock responses rather than actual external services. This approach ensures that logic errors, validation issues, and endpoint misconfigurations are caught early.

Key elements in scope include:

- **Worker Server Endpoints:**  
  Verifying that all REST endpoints respond with correct HTTP statuses, handle input validations, and return structured JSON according to the specification.
  
- **WorkerManager Logic:**  
  Confirming that tasks can be enqueued, processed immediately, stored, and retrieved as results. Ensuring that errors (e.g., missing fields, provider failures) are appropriately handled and reported.
  
- **Individual Worker Classes (Text, Link, Visual):**  
  Each worker’s validate_task and process methods are tested to ensure they produce correct outputs. Mocked external calls simulate LLM responses, domain reputation checks, and emulator outputs to verify correct handling and fallback logic.

**Not in Scope:**
- Actual integration testing with live Providers endpoints.
- Performance/load testing (beyond simple analysis).
- Security or penetration tests.
- Full end-to-end system tests involving Backend, Providers, and other subsystems simultaneously.

At this stage, we focus solely on correctness at a code-level and endpoint response level within the Worker Module, ensuring it is stable and ready for future integration steps.

---

## 3. Assumptions and Risks

### 3.1 Assumptions

- **Stable Configuration File:**  
  A well-formed `config.yaml` is assumed to be present under `workers/config/`. If missing or malformed, tests check default fallback behavior.
  
- **Mocked External Calls:**  
  All LLM, sandbox, and emulator provider interactions are mocked at the unit level. The exact schemas from Providers subsystem are assumed known and stable, or simple placeholders are used. If the Providers subsystem changes its endpoints or data formats, minor test adjustments would suffice.
  
- **Minimal Dependencies:**  
  The worker tests run in an isolated environment, depending only on Python, `pytest`, and mocks. Redis or queue functionalities are either mocked or simplified to in-memory structures for testing convenience.
  
- **Command-Line Triggers:**  
  The `make` targets (`make run-workers`, `make test-unit-workers`) and `docker-compose.yml` setup are assumed to run as intended. If issues arise, the team may add more documentation or adjust scripts.

### 3.2 Risks

- **Schema Changes in Providers:**  
  If Providers subsystem alters endpoints or response formats (e.g., LLM returns a different JSON structure), certain tests or worker logic might need updates to remain accurate.
  
- **Incomplete Coverage of Edge Cases:**  
  While we strive for comprehensive coverage, some rare edge cases or unusual input formats might emerge later. The team may add new tests as these are discovered.
  
- **Integration Surprises:**  
  Once integrated with real Providers endpoints, unexpected latency, network failures, or service downtime might occur, necessitating more robust fallback logic. At the unit level, we rely on mocks and can only anticipate such conditions, not fully reproduce them.

**Overall, given these assumptions and risks, the test plan remains flexible. The team stands ready to add or modify tests as new information emerges or Providers subsystem details change.**

## 4. Requirement Verification Matrix (RVM)

The Requirement Verification Matrix (RVM) provides a high-level overview linking each key requirement to the verification methods used to ensure compliance. This matrix helps developers, testers, and stakeholders quickly identify how each requirement is addressed, which methods are applied, and at which stage of the testing lifecycle the requirement is validated. This section focuses on unit testing (our current scope), with acknowledgment that future integration or system-level tests may employ additional verification methods.

### Verification Methods Defined

- **T (Test):**  
  Direct testing through automated unit tests. Each requirement marked with "T" corresponds to one or more automated test cases executed in the unit test environment. For the Worker Module, these tests use `pytest` and are designed to run in isolation, mocking external calls.

- **D (Demonstration):**  
  Running a scenario interactively, often in a development environment or using an admin UI (like the Gradio interface at `/admin`) to show that certain functionalities or error messages work as intended. While our plan primarily relies on automated tests, some "D" methods serve as sanity checks or developer demos to confirm system behavior.

- **A (Analysis):**  
  Leveraging theoretical models, performance boundaries, or resource usage analysis. At the current unit testing stage, we do not perform extensive performance or boundary analysis. Still, requirements that might later require performance analysis are noted.

- **I (Inspection):**  
  Reviewing code, logs, or configurations. Inspection ensures certain requirements (like existence of a config file or fields in JSON responses) are met through code reviews or log checks. Unit tests may implicitly include inspection steps (e.g., checking JSON keys in responses).

### RVM Table

| Requirement                                                                 | T | D | A | I | Notes                                                           |
|------------------------------------------------------------------------------|---|---|---|---|-----------------------------------------------------------------|
| System must load a valid config.yaml and provide defaults if missing.         | X |   |   | I | Unit tests (T) confirm `load_config` returns correct dict. Code inspection (I) verifies fallback logic. |
| System must list available workers at `/workers`.                            | X |   |   | I | A unit test checks that workers endpoint returns expected list. |
| System must enqueue tasks via `/enqueue_task`.                                | X |   |   | I | Tests verify enqueued tasks return `status:"enqueued"`.         |
| System must handle immediate processing via `/request_worker`.                | X |   |   | I | Tests ensure correct worker selected and result returned.       |
| System must retrieve tasks/results via `/tasks` and `/get_worker_results`.     | X |   |   | I | Tests ensure these endpoints return correct JSON structures.    |
| System must integrate with Providers endpoints (LLM, domain check, emulator)   | X |   |   | I | At unit level, mocked responses ensure workers handle normal and error scenarios. Code inspection ensures correct URL usage. |
| System must return user-friendly error messages on provider failures or invalid inputs. | X | D |   | I | Tests confirm JSON error responses. Demos show admin UI displaying errors gracefully. |
| System must validate input fields before worker processing.                  | X |   |   | I | Tests submit invalid payloads to endpoints and workers, checking returned errors. |
| System must show admin UI at `/admin` for quick oversight.                   | X | D |   | I | Tests ensure `/admin` returns 200 and expected HTML. Demonstration (D) can show the UI loaded. |
| System must store and retrieve final results for tasks.                      | X |   |   | I | Tests confirm that after processing, results persist and are fetched correctly. |

### Interpretation of the RVM

- **Most requirements are verified by Tests (T):**  
  As this is a unit test-focused stage, direct automated tests form the core verification method. They ensure endpoints, workers, and manager logic behave as specified.

- **Some rely on Demonstration (D):**  
  While not strictly required, demonstration of UI endpoints (like `/admin`) or error conditions through manual exploration can supplement confidence. For example, after running `make run-workers`, a developer may visit the `/admin` page to visually confirm data displays correctly.

- **Analysis (A) not yet applied:**  
  No performance or complex boundary analysis has been conducted at the unit stage. Such analysis might occur later when assessing scaling or performance under load.

- **Inspection (I) for correctness:**  
  Code and log inspection complement tests. If a test fails, developers inspect logs or code to understand root causes. Also, inspection ensures configuration and fallback logic match expectations.

Overall, the RVM ensures that each requirement is mapped to at least one verification method. The current focus on "T" (unit tests) aligns with our immediate goal of ensuring correctness at a code-level before integration testing.

## 5. UC-REQ-FEAT-TEST Mapping Table

This section provides a detailed mapping between Use Cases (UC), Requirements (REQ), implemented Features (FEAT), and the corresponding Test Cases (TEST). The table ensures that every use case identified is tied to concrete requirements, implemented as specific features, and ultimately validated by one or more test cases. By establishing these relationships, the team can quickly trace which tests validate which parts of the system, ensuring no requirement or use case goes untested.

### Definitions:

- **Use Case (UC):**  
  A high-level scenario or task that a user (admin, developer) or another subsystem (e.g., the backend) wants to accomplish. Examples: listing workers, requesting immediate worker processing, viewing task results.
  
- **Requirement (REQ):**  
  A specific capability or constraint that must be met. Requirements can be functional (e.g., must process text tasks) or non-functional (e.g., must provide user-friendly error messages).
  
- **Feature (FEAT):**  
  A concrete functionality or endpoint implemented in code that supports the requirement. For instance, the `/workers` endpoint is a feature that fulfills the requirement of listing worker types.
  
- **Test Case (TEST):**  
  One or more specific unit tests that verify the behavior of a feature under various conditions. Tests may involve valid and invalid inputs, mocked external calls, and error scenarios.

### UC-REQ-FEAT-TEST Mapping Table

| Use Case (UC)                               | Requirement (REQ)                                                   | Feature (FEAT)                                                           | Test Case IDs                                                  |
|---------------------------------------------|----------------------------------------------------------------------|--------------------------------------------------------------------------|----------------------------------------------------------------|
| UC: Admin views configs                      | System must show current config via `/configs`                       | `/configs` endpoint                                                      | T-Worker-Server-Config-001                                     |
| UC: Admin lists workers                      | Must list available worker types                                      | `/workers` endpoint                                                      | T-Worker-Server-Workers-001                                     |
| UC: Enqueue tasks for later processing       | Must enqueue tasks via `/enqueue_task`                                | `/enqueue_task` endpoint                                                  | T-Worker-Server-Enqueue-001                                     |
| UC: Request immediate worker run             | Must process tasks immediately via `/request_worker`                  | `/request_worker` endpoint, WorkerManager’s process logic                 | T-Worker-Server-Request-001, T-Worker-Server-Request-002        |
| UC: Retrieve ongoing/completed tasks & results | Must retrieve tasks and results via `/tasks` & `/get_worker_results` | `/tasks` & `/get_worker_results` endpoints                               | T-Worker-Server-Tasks-001, T-Worker-Server-Results-001          |
| UC: Use admin UI for oversight               | Must show admin UI at `/admin`                                        | Admin UI (Gradio integration)                                             | T-Worker-Server-UI-001                                          |
| UC: Validate task inputs before processing   | Must validate input fields before worker processing                   | Worker validate_task methods                                              | T-Worker-Text-Validate-001, T-Worker-Link-Validate-001, T-Worker-Visual-Validate-001 |
| UC: Correct worker selection & processing    | Must choose correct worker by task type and return results            | WorkerManager’s `process_task`, Worker classes’ `process` methods          | T-Worker-Manager-Process-001, T-Worker-Text-Process-001, T-Worker-Link-Process-001, T-Worker-Visual-Process-001 |
| UC: Error handling & fallback on provider failures | Must return error messages gracefully on failure                      | Error handling in workers & manager, JSON error responses                 | T-Worker-Manager-Error-001, T-Worker-Text-Error-001              |
| UC: Integration with Providers (LLM, link, emulator endpoints mocked) | Must handle provider responses & errors | Worker classes calling mocked external endpoints                         | Covered by T-Worker-Text-Process-001 (LLM), T-Worker-Link-Process-001 (Domain check), T-Worker-Visual-Process-001 (Emulator) |

### Analysis of the Table

- **Comprehensive Coverage:**  
  Every UC maps to at least one REQ, a corresponding FEAT, and is tested by at least one TEST case. This ensures no scenario described as a UC is left unverified.
  
- **Traceability for Maintenance:**  
  If a requirement changes (e.g., the format of `/request_worker` input), the team can quickly find which tests and features to update. Similarly, if a test fails, the team can see which UC and REQ are affected.
  
- **Clarity for New Team Members:**  
  By reading the UC-REQ-FEAT-TEST mapping, a newcomer can understand the system’s functionalities and find relevant tests that confirm these functionalities work as intended.
  
- **Support for Future Integration Tests:**  
  While these tests are unit-level and rely on mocks, the mapping mentions external provider endpoints. Once integration tests begin, new tests will be added to verify that these same UCs and REQs hold true when communicating with real Provider subsystem endpoints.

In summary, this UC-REQ-FEAT-TEST mapping offers a structured view of how each use case is realized by specific features and verified by well-defined tests, supporting maintainable, transparent, and flexible testing processes.

## 6. Endpoints and External Interfaces

This section details all the endpoints provided by the Worker Module, as well as the external endpoints it relies on (or mocks at the unit level). Clearly defining these endpoints ensures that testers, developers, and integration partners know exactly what interfaces exist, their input/output formats, and how they fit into the overall WOPA ecosystem.

### Overview

The Worker Module exposes a set of HTTP endpoints (via a FastAPI server) to manage tasks, request workers, retrieve configurations, list workers, and provide an admin UI. While unit tests will mock external dependencies, these interfaces reflect the final intended structure for integration tests and real deployments.

For external endpoints—those belonging to the Providers subsystem—this section identifies the expected request/response patterns. Since we are currently at the unit test stage, actual communication is replaced by mocks, but the given information will guide future integration tests and ensure consistent implementation when real integration occurs.

### 6.1 Worker Server Endpoints

The Worker Server runs behind a FastAPI application defined in `worker_server.py`. Each endpoint returns JSON (except `/admin`, which returns HTML for the Gradio UI). All responses must include appropriate HTTP status codes, and if an error occurs (e.g., invalid input), the endpoint returns a 4xx status and a JSON error message.

| Endpoint                 | Method | Description                                                          | Input Example                                            | Output Example                                                                                                                                       |
|--------------------------|--------|----------------------------------------------------------------------|----------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| `/configs`               | GET    | Returns current configuration in JSON.                               | None                                                     | `{"queue_host":"redis","worker_types":["text","link","visual"]}`                                                                                      |
| `/workers`               | GET    | Lists registered worker types loaded from config.                    | None                                                     | `["text","link","visual"]`                                                                                                                            |
| `/enqueue_task`          | POST   | Enqueues a task for later processing.                                | `{"type":"text","content":"Check this message"}`         | `{"task_id":"abc123","status":"enqueued"}`                                                                                                            |
| `/request_worker`        | POST   | Immediately processes a given task, selecting the correct worker.     | `{"type":"link","url":"http://example.com"}`             | `{"status":"completed","result":{"risk_level":"low"}}` or `{"status":"error","message":"Invalid input"}`                                               |
| `/tasks`                 | GET    | Shows all known tasks and their current statuses (pending/enqueued/completed/error). | None                                     | `[{"task_id":"xyz789","status":"completed","result":{"detail":"ok"}}]` or empty list if no tasks.                                                      |
| `/get_worker_results`    | GET    | Retrieves final results for a given `task_id`.                       | `?task_id=xyz789`                                        | `{"status":"completed","result":{"detail":"ok"}}` or `{"status":"error","message":"not found"}`                                                       |
| `/admin`                 | GET    | Admin UI (Gradio) to view configs, tasks, and refresh data.          | None                                                     | HTML/JS rendering the Gradio interface. UI elements display configs and tasks data fetched from other endpoints.                                       |

**Error Handling:**  
If an endpoint receives invalid input (e.g., missing `type` field), it returns `400 Bad Request` and a JSON error like `{"error":"missing type"}`. If processing fails (like a worker exception), it returns `{"status":"error","message":"..."}.`

**Admin UI Details:**  
The `/admin` endpoint shows a simple Gradio-based interface. Although difficult to fully test at the unit level, we verify it returns `200 OK` and some HTML content. Demonstrations (D) can be used by developers to ensure the UI works as expected in a running environment.

### 6.2 External Provider Endpoints

The Worker Module relies on external endpoints defined by the Providers subsystem to perform complex analysis:

- **LLM (Text) Endpoint:** `POST /llm/inference`  
  **Purpose:** The text worker (TextAnalysisWorker) posts a JSON payload like `{"prompt":"Is this phishing?"}` and expects a JSON response `{"classification":"phishing","confidence":0.95}`.  
  **At Unit Test Level:** Mocks simulate normal and error responses. For example, a mock returning `{"classification":"phishing","confidence":0.9}` tests normal behavior, while an exception simulates LLM failures, ensuring the worker returns `{"status":"error"}`.

- **Domain Reputation (Link) Endpoint:** `GET /domain/check?url=...`  
  **Purpose:** The link worker queries a given URL’s reputation. A safe domain returns something like `{"safe":true,"score":0.1}`, while a malicious domain might return `{"safe":false,"score":0.9}`.  
  **At Unit Test Level:** Mocks return controlled JSON responses. If `safe=true`, link worker returns `{"status":"completed","result":{"risk_level":"low"}}`. If `safe=false`, risk might be `high`. An HTTP error from the mock tests fallback logic.

- **Emulator (Visual) Endpoint:** `POST /emulator/run_app`  
  **Purpose:** The visual worker simulates app usage in an emulator and expects `{"observations":["fake login prompt"]}` or similar. Input might be `{"url":"http://app.example"}` or `{"app_reference":"com.app.example"}`.  
  **At Unit Test Level:** Mocks return a standard `observations` array. Error simulations check how the worker handles failures (returning `{"status":"error"}`).

**No Direct Integration Yet:**  
Currently, these external calls are not actually invoked at unit test time. Instead, `requests` calls are patched to return predefined responses. Future integration tests will remove these mocks, pointing the worker code at a running Providers subsystem instance to confirm real interactions.

### Data Formats and Schemas

- **LLM Endpoint Response:**  
  Typical: `{"classification":"phishing","confidence":0.95}`  
  The worker tests rely on this schema. If changed, test mocks or worker logic must update.

- **Domain Check Response:**  
  Example: `{"safe":true,"score":0.2}`  
  The link worker maps `safe:true` to low risk and `safe:false` to high risk.

- **Emulator Response:**  
  Example: `{"observations":["some suspicious UI element"]}`  
  The visual worker returns these observations directly in its `result`.

### Impact on Testing

Understanding these endpoints’ expected I/O simplifies creating test mocks. Developers can produce realistic responses that let unit tests cover normal and error conditions extensively. If Providers subsystem changes these endpoints, adjusting mocks in tests is straightforward. This approach maintains flexibility and reduces friction during future integration stages.

In summary, the Worker Server endpoints define how external clients interact with the Worker Module, while the external provider endpoints define how workers get the data they need (currently mocked at unit level). This clear separation ensures testability, maintainability, and preparedness for eventual integration tests.

## 7. Unit Test Plan and Test Cases

This section presents a detailed unit test plan, enumerating test categories, test coverage, strategies for mocking external dependencies, naming conventions, and examples of how specific tests verify corresponding functionalities. The goal is to ensure every requirement, feature, and endpoint discussed in previous sections is validated at the code level before integration testing.

### Objectives of Unit Testing

- **Isolate Logic:**  
  Each unit test runs in isolation, mocking external calls (to Providers endpoints like LLM, domain check, emulator). This ensures that failures are due to logic errors in the Worker Module, not due to external services.
  
- **Early Defect Detection:**  
  By focusing on workers, endpoints, and the manager logic, unit tests catch validation errors, incorrect status codes, and improper handling of provider responses early in the development process.
  
- **Maintainability and Scalability:**  
  Tests are structured and named to ease future expansions. If new workers are added (e.g., a FileAnalysisWorker), adopting the same pattern of tests allows rapid integration and consistent coverage.

### Test Categories

1. **Server Endpoint Tests (in `test_worker_server_endpoints.py`):**  
   Covers all exposed endpoints `/configs`, `/workers`, `/enqueue_task`, `/request_worker`, `/tasks`, `/get_worker_results`, and `/admin`.  
   - Ensures correct HTTP responses, JSON structures, status codes, and error handling.
   - Mocks `WorkerManager` and worker responses to simulate various conditions (valid/invalid input, provider failures).
   
2. **Manager and Worker Logic Tests (in `test_worker_manager_and_workers.py`):**  
   Focuses on `WorkerManager` and each worker class (Text, Link, Visual):  
   - Validates that `enqueue_task`, `process_task`, `store_result`, and retrieval methods handle task lifecycles correctly.
   - Verifies worker input validation: missing fields must return error dictionaries.
   - Confirms worker `process` methods handle normal results and error conditions from mocked provider calls.
   - Checks error handling (e.g., raising exceptions in a worker leads to a `{"status":"error"}` result).

### Mocking Strategies

- **Mocking External Providers:**  
  Each worker that makes requests to an external endpoint (LLM inference, domain check, emulator run) uses `unittest.mock.patch` to replace `requests.post` or `requests.get`.  
  - Normal Scenario Mock: Return a known good JSON response (e.g., `{"classification":"phishing","confidence":0.9}"` for LLM).  
  - Error Scenario Mock: Raise `requests.exceptions.RequestException` or return a 500-like response to test fallback/error logic.
  
- **Mocking WorkerManager Internals:**  
  For endpoint tests, `WorkerManager` methods (like `list_all_tasks`, `get_task_result`) may be mocked to return stable, predictable data. This isolates endpoint logic from storage complexity.  
  For logic tests in `test_worker_manager_and_workers.py`, WorkerManager can be tested more directly with real in-memory dictionaries or partial mocks.

- **Mocking Configuration:**  
  `load_config()` can be patched to return a predefined dictionary, ensuring consistent worker_types and endpoints without depending on an actual config file.

### Naming Conventions and Organization

- Test files are named to reflect their scope:
  - `test_worker_server_endpoints.py`: Server endpoints.
  - `test_worker_manager_and_workers.py`: Manager and worker logic.

- Individual test functions follow a pattern like `test_{feature or scenario}_{condition}`:
  - Example: `test_text_worker_validate_missing_content`
  - Example: `test_request_worker_invalid_input`
  - Example: `test_manager_error_handling`

- Comments within tests describe the purpose, steps, and expected outcomes, ensuring maintainability and clarity.

### Coverage Approach

- **Endpoints Coverage:**  
  Each endpoint is tested with multiple scenarios: valid input, invalid input, empty responses, error conditions, and a normal flow scenario. For `/request_worker`, tests cover choosing correct worker, validating input fields, and handling provider errors.
  
- **Worker Coverage:**  
  Each worker class (Text, Link, Visual) is tested for:
  - Validation errors (missing `content` or `url`, etc.).
  - Successful processing under normal conditions (mock returns safe or phishing classification, safe domain vs malicious domain, normal emulator observations).
  - Error scenarios where the provider mock simulates failures (timeout, bad JSON, HTTP errors).
  
- **Manager Logic Coverage:**  
  Manager tests ensure tasks can be enqueued and processed, that `process_task` picks the right worker, and `store_result`/`get_task_result` handle final outputs. Also covers what happens if the worker process method raises exceptions.

### Full Tests List

Below is a comprehensive list of all identified test cases, following the specified format. Each test case includes its purpose, strategy, tested objects, detailed steps, and success criteria. This list integrates all tests from the endpoint-related scenarios and the worker/manager logic scenarios defined in previous sections.

---

**Server Endpoint Tests**

**T-Worker-Server-Health-001: Sanity check of all endpoints**  
- Purpose:  
  Verify that all main endpoints (`/configs`, `/workers`, `/enqueue_task`, `/request_worker`, `/tasks`, `/get_worker_results`, `/admin`) respond with correct status and basic expected output.  
- Strategy:  
  Use FastAPI TestClient to call each endpoint once with mock dependencies and confirm they return HTTP 200 and a minimally correct response structure.  
- Tested Objects:  
  - `worker_server.py` endpoints  
  - Indirectly tests `WorkerManager` mocking, no direct provider calls since all are mocked.  
- Steps:  
  1. GET `/configs` → Expect 200 and a JSON with config keys.  
  2. GET `/workers` → Expect 200 and JSON list of workers.  
  3. POST `/enqueue_task` with a valid JSON → Expect `{"status":"enqueued"}`.  
  4. POST `/request_worker` with valid input → Expect `{"status":"completed" or "pending"}`.  
  5. GET `/tasks` → Expect 200 and JSON list of tasks.  
  6. GET `/get_worker_results?task_id=xyz` → Expect 200 and `{"status":"completed" or "error"}`.  
  7. GET `/admin` → Expect 200 and HTML (Gradio UI).  
- Success Criteria:  
  All endpoints return 200 on normal conditions and basic correct structure (or a well-defined error if simulated).

**T-Worker-Server-Config-001**  
- Purpose:  
  Confirm `/configs` endpoint returns the configuration dictionary as loaded from `config_loader`.  
- Strategy:  
  Patch `load_config` to return a known dict, call `/configs`, and assert JSON matches keys.  
- Tested Objects:  
  - `/configs` endpoint, `load_config` function.  
- Steps:  
  1. Mock `load_config()` to return `{"worker_types":["text","link","visual"]}`.  
  2. GET `/configs`.  
  3. Check status=200 and `worker_types` in response.  
- Success Criteria:  
  Response includes mocked keys exactly, ensuring endpoint reflects current config.

**T-Worker-Server-Workers-001**  
- Purpose:  
  Verify `/workers` lists available worker types.  
- Strategy:  
  Ensure `worker_map` includes `text`, `link`, and `visual` and endpoint returns them.  
- Tested Objects:  
  - `/workers` endpoint  
- Steps:  
  1. GET `/workers`.  
  2. Expect 200 and JSON array containing `"text","link","visual"`.  
- Success Criteria:  
  Returned list matches known worker_types.

**T-Worker-Server-Enqueue-001**  
- Purpose:  
  Check that `/enqueue_task` enqueues a given task and returns `status:"enqueued"`.  
- Strategy:  
  Mock `WorkerManager.enqueue_task` to return a stable task_id. Test with valid input (e.g. `{"type":"text","content":"hello"}`).  
- Tested Objects:  
  - `/enqueue_task` endpoint, `WorkerManager.enqueue_task`  
- Steps:  
  1. POST `{"type":"text","content":"hello"}` to `/enqueue_task`.  
  2. Expect 200 and `{"task_id":"some_id","status":"enqueued"}`.  
- Success Criteria:  
  Task is enqueued, correct JSON response returned.

**T-Worker-Server-Request-001**  
- Purpose:  
  Confirm `/request_worker` processes a valid task immediately and returns completed result.  
- Strategy:  
  Mock chosen worker’s process method to return `status:"completed"` and a result.  
- Tested Objects:  
  - `/request_worker` endpoint, `WorkerManager.process_task`, Worker classes.  
- Steps:  
  1. POST a valid link task: `{"type":"link","url":"http://example.com"}` to `/request_worker`.  
  2. Mock link worker’s `process` to return `{"status":"completed","result":{"risk_level":"low"}}`.  
  3. Check response = 200, status=completed and result present.  
- Success Criteria:  
  Returns `completed` and correct result for a known good input scenario.

**T-Worker-Server-Request-002**  
- Purpose:  
  Check `/request_worker` error behavior for invalid input.  
- Strategy:  
  Submit a POST with missing fields, expect 400 error and an error JSON.  
- Tested Objects:  
  - `/request_worker` endpoint’s validation logic  
- Steps:  
  1. POST `{"type":"text"}` (no content)  
  2. Expect 400 and `{"error":"missing content"}`.  
- Success Criteria:  
  Endpoint returns a clear error message and 400 status.

**T-Worker-Server-Tasks-001**  
- Purpose:  
  Confirm `/tasks` returns a list of known tasks and their statuses.  
- Strategy:  
  Mock `WorkerManager.list_all_tasks` to return a sample.  
- Tested Objects:  
  - `/tasks` endpoint, `WorkerManager.list_all_tasks`  
- Steps:  
  1. Mock returns `[{"task_id":"xyz","status":"completed"}]`.  
  2. GET `/tasks` → Expect that exact JSON list.  
- Success Criteria:  
  Returns the mocked list correctly.

**T-Worker-Server-Results-001**  
- Purpose:  
  Retrieve final results of a task via `/get_worker_results`.  
- Strategy:  
  Mock `WorkerManager.get_task_result` with a completed result.  
- Tested Objects:  
  - `/get_worker_results` endpoint, `WorkerManager.get_task_result`  
- Steps:  
  1. Mock returns `{"status":"completed","result":{"detail":"ok"}}`.  
  2. GET `/get_worker_results?task_id=abc` → Expect 200 and that JSON.  
- Success Criteria:  
  Correct final results returned for a known task_id.

**T-Worker-Server-UI-001**  
- Purpose:  
  Validate `/admin` returns Gradio UI.  
- Strategy:  
  GET `/admin` and check 200 status and that the response is HTML.  
- Tested Objects:  
  - `/admin` endpoint and UI rendering code.  
- Steps:  
  1. GET `/admin`.  
  2. Expect 200 and HTML content (just checking status and minimal content for unit test).  
- Success Criteria:  
  Endpoint serves HTML page successfully.

---

**Manager & Worker Tests**

**T-Worker-Config-Load-001**  
- Purpose:  
  Ensure `load_config` returns correct dictionary and handles fallback.  
- Strategy:  
  Patch `load_config()` to return known dict, assert keys.  
- Tested Objects:  
  - `utils/config_loader.py` load_config function  
- Steps:  
  1. Mock load_config to return `{"worker_types":["text","link"]}`  
  2. Call load_config, check returned dict.  
- Success Criteria:  
  Returns expected config keys.

**T-Worker-Manager-Process-001**  
- Purpose:  
  Check that `WorkerManager.process_task` selects correct worker and returns completed result.  
- Strategy:  
  Patch chosen worker’s `process` method to return completed result.  
- Tested Objects:  
  - `WorkerManager.process_task`, a worker’s `process`  
- Steps:  
  1. Create a link task_data `{"type":"link","url":"http://safe.com"}`  
  2. Patch link worker’s process → completed  
  3. Call manager.process_task(task_data), expect `{"status":"completed","result":{...}}`  
- Success Criteria:  
  Correct worker called, completed result returned.

**T-Worker-Manager-Error-001**  
- Purpose:  
  If a worker raises exception, manager returns `{"status":"error"}`.  
- Strategy:  
  Patch worker process to raise exception.  
- Tested Objects:  
  - `WorkerManager.process_task` error handling  
- Steps:  
  1. Patch text worker’s process to raise `Exception("LLM failed")`  
  2. manager.process_task({"type":"text","content":"fail"})  
  3. Expect `{"status":"error","message":"LLM failed"}`  
- Success Criteria:  
  Error status and message reflect worker failure.

**T-Worker-Manager-Store-001**  
- Purpose:  
  Confirm store_result and retrieval logic works.  
- Strategy:  
  manager.store_result(task_id, result) then manager.get_task_result(task_id)  
- Tested Objects:  
  - `WorkerManager.store_result`, `WorkerManager.get_task_result`  
- Steps:  
  1. manager.store_result("task_abc", {"status":"completed","result":{"detail":"ok"}})  
  2. result = manager.get_task_result("task_abc")  
  3. Check result matches stored data.  
- Success Criteria:  
  Stored and retrieved results match exactly.

**T-Worker-Text-Validate-001**  
- Purpose:  
  Text worker requires `content`.  
- Strategy:  
  Call text_worker.validate_task with missing `content`.  
- Tested Objects:  
  - `TextAnalysisWorker.validate_task`  
- Steps:  
  1. text_worker.validate_task({"type":"text"})  
  2. Expect `{"error":"missing content"}`  
- Success Criteria:  
  Returns error dict for missing field.

**T-Worker-Text-Process-001**  
- Purpose:  
  Normal text processing scenario (LLM call).  
- Strategy:  
  Mock LLM endpoint (requests.post) returns phishing classification.  
- Tested Objects:  
  - `TextAnalysisWorker.process`  
- Steps:  
  1. Mock LLM returns `{"classification":"phishing","confidence":0.95}`  
  2. text_worker.process({"type":"text","content":"test"})  
  3. Expect `{"status":"completed","result":{"classification":"phishing","confidence":0.95}}`  
- Success Criteria:  
  Completed with correct result.

**T-Worker-Text-Error-001**  
- Purpose:  
  If LLM fails (e.g., timeout), text worker returns `error`.  
- Strategy:  
  Mock LLM call to raise exception.  
- Tested Objects:  
  - `TextAnalysisWorker.process` error handling  
- Steps:  
  1. Mock requests.post to raise Exception("LLM failed")  
  2. text_worker.process({"type":"text","content":"fail scenario"})  
  3. Expect `{"status":"error","message":"LLM failed: ..."}`
- Success Criteria:  
  `status:error` and a helpful message.

**T-Worker-Link-Validate-001**  
- Purpose:  
  Link worker requires `url`.  
- Strategy:  
  call link_worker.validate_task({"type":"link"}) missing url  
- Tested Objects:  
  - `LinkAnalysisWorker.validate_task`  
- Steps:  
  1. link_worker.validate_task({"type":"link"})  
  2. Expect `{"error":"missing url"}`  
- Success Criteria:  
  Returns error dict for missing url.

**T-Worker-Link-Process-001**  
- Purpose:  
  Normal link scenario.  
- Strategy:  
  Mock domain reputation API returns `{"safe":true,"score":0.1}`, link worker → low risk.  
- Tested Objects:  
  - `LinkAnalysisWorker.process`  
- Steps:  
  1. Mock requests.get returns safe domain JSON  
  2. link_worker.process({"type":"link","url":"http://safe.com"})  
  3. Expect `{"status":"completed","result":{"risk_level":"low","score":0.1}}`  
- Success Criteria:  
  Completed with expected low risk result.

**T-Worker-Visual-Validate-001**  
- Purpose:  
  Visual worker requires `url` or `app_reference`.  
- Strategy:  
  call visual_worker.validate_task({"type":"visual"}) missing both  
- Tested Objects:  
  - `VisualVerificationWorker.validate_task`  
- Steps:  
  1. visual_worker.validate_task({"type":"visual"})  
  2. Expect `{"error":"missing url or app_reference"}`  
- Success Criteria:  
  Returns error dict for missing fields.

**T-Worker-Visual-Process-001**  
- Purpose:  
  Normal visual scenario with emulator.  
- Strategy:  
  Mock emulator endpoint returns `{"observations":["fake login prompt"]}`  
- Tested Objects:  
  - `VisualVerificationWorker.process`  
- Steps:  
  1. Mock requests.post to emulator returns observations  
  2. visual_worker.process({"type":"visual","url":"http://app.example"})  
  3. Expect `{"status":"completed","result":{"observations":["fake login prompt"]}}`  
- Success Criteria:  
  Completed with expected observations.

### Test Execution and Reporting

- Run unit tests via `make test-unit-workers`, which sets `MODE=unit-test` and invokes pytest inside the container.  
- Pytest generates output indicating passed/failed tests. A CI pipeline (if in place) can parse results to ensure no regressions occur.
- Developers can review logs and coverage reports to identify missing tests or flaky scenarios.

### Preparing for Integration Testing

While these unit tests rely on mocks, their careful design ensures minimal friction when integration testing begins. For integration tests, mocks will be replaced by a running Providers subsystem, and tests will verify the actual network calls and responses. The naming conventions, structured tests, and well-defined input/output checks serve as a solid foundation for that next step.

## 8. Integration Test Plan and Test Cases

With the Worker Module thoroughly tested at the unit level using mocked external calls, the next step involves **integration testing** to verify that the Worker Module interacts correctly with real Provider endpoints. Integration tests focus on the interplay between the Worker Module and the Providers subsystem (LLM, Sandbox, Emulator services), ensuring that requests sent by the workers produce the expected real-world responses, and that fallback/error-handling logic behaves correctly when actual network conditions, delays, or unexpected formats occur.

### Objectives of Integration Testing

- **Verify Actual Provider Communication:**  
  Integration tests replace the mocks used in unit tests with a running Providers subsystem instance. This checks that `TextAnalysisWorker` can truly connect to `http://PROVIDER_URL/llm/inference`, send prompts, and interpret real responses. Similarly, `LinkAnalysisWorker` must handle actual domain reputation checks, and `VisualVerificationWorker` must run apps in a real emulator environment.

- **Confirm End-to-End Flows:**  
  While unit tests confirm individual logic components, integration tests verify that from the moment `/request_worker` or `/enqueue_task` is called, the entire chain—from Worker Manager to Worker, from Worker to Provider, and back—operates correctly with real data. This ensures no schema mismatches, URL typos, or unexpected HTTP responses cause failures.

- **Assess Stability and Error Conditions:**  
  Integration tests can simulate provider downtime, invalid provider responses, or extended delays. Observing how the Worker Module returns `status:"error"` and meaningful messages under real conditions ensures robust error handling.

- **No Longer Just Mocks:**  
  While unit tests rely heavily on mocks, integration tests run with actual services up and running. For this, a `docker-compose` environment might bring up the Providers subsystem along with `workers` and `redis`. Integration tests then execute requests against a fully functional environment.

### Assumptions for Integration Tests

- The Providers subsystem is available and accessible at known URLs (e.g., `http://providers:9000/llm/inference` or similar).
- Real credentials or configuration may be required if Providers subsystem endpoints require authentication.
- Network conditions are stable enough for testing, or tests consider timeouts as part of error-handling validation.

If these assumptions fail, integration tests help discover integration issues early, prompting adjustments in configuration or error handling logic.

### Scope of Integration Tests

Integration tests focus on:
- Real calls to LLM endpoint: Providing actual prompts to verify classification (phishing vs. benign).
- Real calls to the domain reputation API: Checking a safe domain returns a safe score, and a known malicious domain returns a high-risk score.
- Real calls to the emulator endpoint: Running an app in a real emulator container, verifying that observations (e.g., screenshots, logs) match expectations.

They also revisit the endpoints tested by unit tests but now observe real provider responses rather than mocked JSON. This confirms that the schema expectations, field names, and formats align perfectly.

### Additional Setup for Integration Tests

- **docker-compose with Providers:**  
  The integration test environment might include a `docker-compose.integration.yml` that brings up:
  - `providers` container(s) running LLM service, sandbox environment, and emulator.
  - The `workers` container running normally.
  - `redis` for storage if needed.

- **Test Data and Known Inputs:**  
  Some integration tests may rely on known phishing texts, known safe/malicious domains, or a test Android app reference that the emulator can run. This ensures predictable results and makes verifying correctness easier.

### Test Strategies

1. **Happy Path Scenarios (Normal Conditions):**  
   - `TextAnalysisWorker` sends a prompt to the LLM, receives a valid classification, returns `status:"completed"`.
   - `LinkAnalysisWorker` queries a known safe domain and returns `low` risk.
   - `VisualVerificationWorker` runs a known test app and returns expected `observations`.

2. **Error Conditions:**
   - LLM endpoint returns unexpected JSON or a non-200 status. Worker must return `status:"error"` gracefully.
   - Domain reputation API unavailable or returns malformed JSON. Check if link worker falls back with an error message.
   - Emulator endpoint takes too long or returns unexpected data. Visual worker should handle timeouts or parse errors.

3. **Validation of Task Lifecycle with Real Providers:**
   - Enqueue a task via `/enqueue_task` and later trigger `/request_worker` to process it. Confirm that with real Providers calls, the results stored in `/tasks` and `/get_worker_results` match actual provider responses.

### Naming Conventions for Integration Tests

Integration tests might reside in a separate directory, like `workers/tests_integration/`, or in a different repository area. Test function names can mirror unit test naming but add a suffix like `_integration` to differentiate from unit tests. For example:

- `test_text_worker_process_real_llm_integration`
- `test_link_worker_real_domain_check_integration`
- `test_visual_worker_real_emulator_integration`

### Full Integration Test List

Below is a comprehensive list of integration tests for the Worker Module, using the same structured format as the unit tests. These tests assume a running environment where the Providers subsystem is available at configured endpoints, allowing the Worker Module to make real calls to LLM, domain reputation, and emulator services. Each test includes purpose, strategy, tested objects, detailed steps, and success criteria.

All test IDs begin with `T-Worker-Integration-` to differentiate from unit-level tests. The scenarios cover normal (happy path) conditions, error conditions, and more complex workflows involving task enqueueing, immediate requests, and retrieving results.

**T-Worker-Integration-LLM-001**  
- Purpose:  
  Validate that the `TextAnalysisWorker` integrates with the real LLM endpoint and handles a normal classification scenario successfully.
- Strategy:  
  Run the Worker Module in an environment where the LLM endpoint (`POST /llm/inference`) is live, provide a known prompt, and verify correct classification and result structure.
- Tested Objects:  
  - `/request_worker` endpoint with a `{"type":"text","content":"Is this phishing?"}` input
  - `TextAnalysisWorker` calling the real LLM
- Steps:  
  1. Ensure Providers subsystem LLM service is running and accessible at `http://providers:9000/llm/inference`.
  2. POST `{"type":"text","content":"Is this phishing?"}` to `/request_worker`.
  3. Expect real LLM endpoint returns `{"classification":"phishing","confidence":0.9}`.
  4. Check response from Worker Module: `{"status":"completed","result":{"classification":"phishing","confidence":0.9}}`.
- Success Criteria:  
  Actual LLM call succeeds, correct classification and confidence displayed, and no mock is used.

**T-Worker-Integration-LLM-Error-001**  
- Purpose:  
  Confirm that if LLM endpoint returns a server error or malformed JSON, the `TextAnalysisWorker` and Worker Module handle it gracefully by returning `status:"error"`.
- Strategy:  
  Cause the LLM endpoint to return 500 or invalid JSON and observe error behavior.
- Tested Objects:  
  - `/request_worker` endpoint, `TextAnalysisWorker`
- Steps:  
  1. Temporarily configure or simulate LLM service to return a 500 status on request.
  2. POST `{"type":"text","content":"fail scenario"}` to `/request_worker`.
  3. Expect Worker Module response: `{"status":"error","message":"LLM failed: ..."}`
- Success Criteria:  
  Worker returns a clean error message, verifying robust error handling in real conditions.

**T-Worker-Integration-Link-001**  
- Purpose:  
  Test `LinkAnalysisWorker` against a real domain reputation API to confirm safe domain results in `low` risk classification.
- Strategy:  
  Use a known safe domain. Providers’ domain check endpoint returns `{"safe":true,"score":0.1}`.
- Tested Objects:  
  - `/request_worker` endpoint with `type: link`
  - `LinkAnalysisWorker` calling real domain check API
- Steps:  
  1. POST `{"type":"link","url":"http://example-safe.com"}` to `/request_worker`.
  2. Domain API returns `{"safe":true,"score":0.1}`.
  3. Expect `{"status":"completed","result":{"risk_level":"low","score":0.1}}`.
- Success Criteria:  
  Actual domain API integration works, low risk returned.

**T-Worker-Integration-Link-Error-001**  
- Purpose:  
  Verify error handling if the domain reputation API is unavailable or returns unexpected data.
- Strategy:  
  Simulate domain API downtime or invalid JSON.
- Tested Objects:  
  - `/request_worker`, `LinkAnalysisWorker`
- Steps:  
  1. POST `{"type":"link","url":"http://malformed-domain.com"}` to `/request_worker`.
  2. Domain API returns 500 error or invalid JSON.
  3. Expect Worker Module: `{"status":"error","message":"Domain check failed: ..."}`
- Success Criteria:  
  Worker returns an error without crashing, ensuring fallback logic in real scenarios.

**T-Worker-Integration-Visual-001**  
- Purpose:  
  Confirm `VisualVerificationWorker` interacts with a real emulator endpoint and returns expected observations for a known test app.
- Strategy:  
  Provide a known test app that exhibits a known suspicious UI element.
- Tested Objects:  
  - `/request_worker`, `VisualVerificationWorker`
- Steps:  
  1. POST `{"type":"visual","url":"http://app.example"}` to `/request_worker`.
  2. Emulator endpoint returns `{"observations":["fake login prompt"]}`.
  3. Expect `{"status":"completed","result":{"observations":["fake login prompt"]}}`.
- Success Criteria:  
  Successful emulator call and correct parsing of observations.

**T-Worker-Integration-Visual-Error-001**  
- Purpose:  
  Test error handling if the emulator endpoint returns invalid data or is unreachable.
- Strategy:  
  Emu endpoint returns a 404 or invalid JSON.
- Tested Objects:  
  - `/request_worker`, `VisualVerificationWorker`
- Steps:  
  1. POST `{"type":"visual","app_reference":"com.app.unknown"}`  
  2. Emulator endpoint returns error (e.g., 404 Not Found).
  3. Expect `{"status":"error","message":"Emulator run failed: ..."}`
- Success Criteria:  
  Worker responds with a user-friendly error message.

**T-Worker-Integration-Tasks-LifeCycle-001**  
- Purpose:  
  Validate full lifecycle: enqueue a task, later retrieve and process it via `/request_worker`, and then confirm final results appear in `/tasks` and `/get_worker_results`.
- Strategy:  
  Use a text or link task, enqueue it first, then request processing after some waiting, verify stored results.
- Tested Objects:  
  - `/enqueue_task`, `/tasks`, `/get_worker_results`, `WorkerManager.store_result/get_task_result`
- Steps:  
  1. POST `{"type":"text","content":"Check this message"}` to `/enqueue_task` → `task_id=abc`
  2. POST `{"type":"text","content":"Check this message"}` to `/request_worker` or directly use `task_id` approach if defined. (If immediate processing from queue is allowed later.)
  3. After processing (LLM call real), `/tasks` should show `{"task_id":"abc","status":"completed","result":{...}}`.
  4. `GET /get_worker_results?task_id=abc` → should return completed result.
- Success Criteria:  
  Full cycle from enqueueing to retrieving final results with real Providers calls works seamlessly.

**T-Worker-Integration-Admin-UI-001**  
- Purpose:  
  Check that the `/admin` UI shows real-time configs and tasks data when Providers subsystem is running.
- Strategy:  
  Access `/admin` and manually refresh or run scenario tests. Although primarily demonstration-based, we can automate checks for returned HTML and possibly query known elements.
- Tested Objects:  
  - `/admin` endpoint, Gradio interface
- Steps:  
  1. GET `/admin`  
  2. Confirm 200 status and presence of Gradio UI HTML.
  3. Optionally, if testing automated, we can parse HTML or rely on known CSS selectors to confirm UI loads partial results or config from actual endpoints.
- Success Criteria:  
  Admin UI works in integration environment, no broken links or missing data fields.

**T-Worker-Integration-Fallback-Provider-001**  
- Purpose:  
  Confirm that if Providers endpoints are slow or return unexpected HTTP codes, worker returns error gracefully.
- Strategy:  
  Introduce artificial delays or errors in provider services (like LLM responding after a long timeout).
- Tested Objects:  
  - `/request_worker` endpoint, relevant worker process method
- Steps:  
  1. Configure LLM or domain API to respond slowly or return a 503 error.
  2. POST a valid request to `/request_worker`.
  3. Expect `{"status":"error","message":"LLM failed: timeout"}` or similar.
- Success Criteria:  
  Worker handles real network/timeouts gracefully.

This **Full Integration Test List** ensures that every worker scenario previously tested with mocks at the unit level is now validated with real Provider services. Each test case is crafted to confirm correctness, error handling, and fallback mechanisms under authentic conditions. The list covers normal, error, and lifecycle scenarios, providing a comprehensive blueprint for integration testing once the Providers subsystem and all necessary services are available in the testing environment.

### Executing Integration Tests

- Run a dedicated `docker-compose -f docker-compose.integration.yml up` that includes providers and workers.
- Possibly run `make test-integration-workers` or a similar command that triggers pytest with a `MODE=integration` environment, ensuring no mocks are applied.
- Monitor logs for any unexpected errors. If tests fail, logs from providers and workers help identify schema mismatches or endpoint issues.

### Summary of Integration Testing Approach

Integration tests ensure that everything proven correct in isolation still holds true when real Provider endpoints are involved. By following a similar pattern of test naming, structure, and clarity as unit tests, developers can quickly adapt tests to real conditions. Gradual introduction of integration tests—starting with basic happy paths and error conditions—provides confidence that the Worker Module is ready for real operational scenarios within WOPA.

This comprehensive integration testing strategy complements the unit tests, guiding the Worker Module toward full system integration with minimal surprises.


## 9. Test Environment and Tools

This section describes the environment, tooling, and setup needed to run the unit and integration tests defined in this plan. Ensuring a stable and reproducible test environment is critical for consistent results and efficient troubleshooting.

### Environment Setup

- **Containerized Services:**  
  Both unit and integration tests run inside Docker containers defined by `docker-compose.yml`.  
  - **Unit Tests Environment:**  
    Only `workers` and `redis` services need to be brought up. The `workers` container runs in `MODE=unit-test`, executing pytest with mocked external calls.
  
  - **Integration Tests Environment:**  
    An extended compose file (e.g., `docker-compose.integration.yml`) or additional services added to the same file can bring up `providers` along with `workers` and `redis`. This ensures the Worker Module interacts with real LLM, domain, and emulator endpoints.

- **Networking:**  
  A shared network (`wopa_network`) ensures that containers can reach each other (e.g., `workers` can call `providers` at a known hostname and port). Domain names like `providers:9000` must be consistent and documented.

### Tools

- **Python and Pytest:**  
  Pytest serves as the primary test runner. Simple fixtures, `unittest.mock.patch`, and parametrization help isolate tests and provide clean, readable code.
  
- **Docker and Docker Compose:**  
  Using Docker ensures the environment is uniform across machines. Docker Compose orchestrates containers—`workers`, `redis`, and `providers`—for integration tests.

- **Makefile Targets:**  
  `make run-workers` and `make test-unit-workers` are convenient commands. A future `make test-integration-workers` could trigger integration tests once Providers is ready.

### Logging and Monitoring

- **Logs:**  
  The worker server, WorkerManager, and workers log events at INFO or ERROR level. During integration tests, developers can `docker logs` each container to investigate failures.
  
- **Coverage:**  
  Pytest can be run with coverage tools to measure test completeness. While not mandatory, coverage reports help identify untested code paths.

By defining the environment, tools, and logging strategies upfront, the team ensures a predictable and maintainable testing setup. Any changes to services (like new dependencies or different ports) require updating these environment files and make targets accordingly.

---

## 10. Test Reporting

Test reporting outlines how results are recorded, shared, and analyzed. Clear reporting helps stakeholders understand progress, detect regressions, and ensure readiness for integration and release cycles.

### Reporting Approach

- **Console Output:**  
  Running `pytest` prints results to the console. For unit tests, quick iteration is enough. For CI pipelines, console logs can be archived for reference.

- **CI Integration:**  
  If integrated into a CI system (like GitHub Actions, GitLab CI, or Jenkins), test results can be published as artifacts or commented on PRs. The CI can fail builds if tests fail, enforcing quality gates.

- **JSON/XML Reports:**  
  Pytest can produce JUnit XML or JSON output. This enables better integration with dashboards, coverage tools, or test management systems if needed.

- **Coverage Reports:**  
  Coverage reports show which lines of code remain untested. Developers can act on these to improve test completeness.

### Communication of Results

- **Team Notifications:**  
  On test completion, CI can notify the team on Slack or email if critical tests fail. Regular reviews of test runs ensure ongoing quality.

- **Historical Trends:**  
  Storing test logs and coverage reports over time allows the team to track stability trends, ensuring continuous improvement and quick identification of when a regression first appeared.

### Decision Making Based on Results

- **Release Readiness:**  
  If critical tests fail, the release may be postponed until the issues are resolved. Good test coverage and passing integration tests provide confidence in moving forward.

- **Regression Handling:**  
  When a test that previously passed fails in a new commit, developers quickly inspect logs and coverage diff reports to pinpoint introduced regressions.

Test reporting ensures that test outcomes drive informed decisions, maintaining the reliability and progress of the WOPA worker subsystem.

---

## 11. Roles and Responsibilities

Clear assignment of roles ensures that everyone knows their part in the testing process, from writing tests to analyzing results and maintaining test infrastructure.

- **Developers:**  
  Implement and maintain unit tests for their respective worker classes and endpoints. They fix defects found by these tests and enhance tests as features evolve.

- **Test/QA Engineers:**  
  Focus on refining the test plan, ensuring completeness and relevance. They may add more complex scenarios, improve mocks, or set up integration tests when Providers subsystem is available.

- **DevOps/Infrastructure Team:**  
  Maintain Docker, Compose, and CI pipelines to ensure tests run consistently in all environments. They handle scaling integration environments, adding or updating Providers containers as needed.

- **Project Manager/Lead:**  
  Monitors test coverage and results, deciding when the subsystem is stable enough for integration testing or release. Guides the team in prioritizing critical tests and addressing long-standing issues.

### Accountability and Updates

If requirements or endpoints change, developers update the tests accordingly. Test failures assign action items to responsible parties, ensuring prompt fixes and maintaining a high-quality codebase. Regular test plan reviews keep this document aligned with evolving project requirements.

---

## 12. Schedule and Milestones

While exact dates depend on project timelines, the general milestones for testing the Worker Module might be:

- **Unit Testing Phase (Current):**  
  - Complete all unit tests defined in sections above.  
  - Achieve passing status on CI for `make test-unit-workers`.  
  - Ensure coverage meets internal thresholds (e.g., 90% line coverage).

- **Integration Testing Preparation:**  
  - Wait until the Providers subsystem is stable and ready to respond with real endpoints.  
  - Write initial integration tests (see Full Integration Test List) and run them once Providers are available.
  
- **Integration Testing Execution:**  
  - Stand up Providers and Workers together using `docker-compose.integration.yml`.  
  - Run `make test-integration-workers` and fix issues revealed by real provider calls.  
  - Achieve stable passing results.

- **Pre-Release Checks:**
  - After integration tests pass consistently, consider adding load tests or minimal performance checks if required.  
  - Confirm all critical use cases are covered at both unit and integration levels before moving to a broader system test.

### Flexibility in Scheduling

The team may adjust the schedule as Providers subsystem availability changes. If Providers are delayed, more unit test scenarios can be added to improve quality. Once available, integration tests commence immediately.

---

## 13. Conclusion and References

This test plan ensures the Worker Module’s quality through a structured set of unit and integration tests. By defining requirements, use cases, features, tests, and clear mappings between them, the team maintains transparency and alignment with project goals. The outlined environment, tools, reporting mechanisms, roles, and schedule support a smooth and predictable testing lifecycle.

**References:**

- WOPA Project Philosophy and Charter: [internal docs]  
- Providers Subsystem Overview: Provided by Providers team developer.  
- FastAPI, Pytest, Docker, Gradio, and Requests official documentation.

**Next Steps:**
- Complete unit tests and run them under CI to ensure no regressions.
- After Providers subsystem is stable, proceed with integration tests as listed.
- Continuously improve tests based on feedback, coverage reports, and evolving requirements.

By following this plan, the Worker Module moves forward confidently, providing a resilient foundation within the WOPA ecosystem.
