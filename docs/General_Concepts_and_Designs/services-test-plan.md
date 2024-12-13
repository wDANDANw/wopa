# WOPA Services Module - Comprehensive Test Plan

## 1. Introduction

### 1.1 Objectives

The **WOPA Services Module** provides a front-facing interface for analyzing various inputs—messages, links, files, and apps—by leveraging underlying workers and aggregator logic. This module validates user inputs, routes tasks to the appropriate service logic (e.g., `message_service`, `link_service`, `file_static_service`, `file_dynamic_service`, `app_service`), and manages the lifecycle of analysis tasks from initiation to final results.

This test plan defines a thorough approach to ensure the Services Module meets both functional and non-functional requirements before moving to integration testing with other WOPA subsystems (notably the Worker and Provider subsystems) and final system-wide validation. The primary goals are:

- Confirm that each endpoint (`/available_services`, `/analyze_message`, `/analyze_link`, `/analyze_file_static`, `/analyze_file_dynamic`, `/analyze_app`, `/tasks`, `/get_task_status`) behaves as specified, handling valid and invalid inputs correctly.
- Verify that each service class (MessageService, LinkService, FileStaticService, FileDynamicService, AppService) properly validates inputs, calls workers, interacts with the aggregator LLM, and provides appropriate error handling.
- Ensure that `ServiceManager` orchestrates tasks correctly, storing results, updating statuses, and retrieving final aggregated outputs.
- Provide a blueprint for transitioning from unit tests (with mocks for external calls) to future integration tests using the real Worker and Provider endpoints.

### 1.2 Team Members

- **Developers (Services Focus):** Implement and maintain tests for service endpoints and logic.
- **Test/QA Engineers:** Enhance coverage, add complex scenarios, and document test cases for services and manager logic.
- **DevOps/Infra Team:** Ensure Docker/Compose and CI pipelines run these tests consistently in various environments.
- **Project Manager/Lead:** Reviews test coverage and stability, guiding readiness for integration and release milestones.

---

## 2. Scope

The scope includes **unit-level testing** of the Services Module. Tests rely on mocks for worker and aggregator endpoints to isolate service logic from external dependencies. Integration with the Worker and Provider modules will be tested later, once those services are stable and accessible in an integrated environment.

Key elements in scope:

- **Services Endpoints:**  
  Testing `/available_services`, `/analyze_message`, `/analyze_link`, `/analyze_file_static`, `/analyze_file_dynamic`, `/analyze_app` for correct HTTP responses, validation errors, and final aggregated results.
  
- **Service Classes (Message, Link, FileStatic, FileDynamic, App):**  
  Ensure each service validates inputs, calls mocked worker and aggregator endpoints properly, and returns comprehensive structured JSON responses or clear error messages.
  
- **ServiceManager:**  
  Confirm that tasks can be created with unique `task_id`, tracked, updated, and retrieved. Verify that after service calls workers and aggregator LLM, results are stored and retrievable via `/tasks` and `/get_task_status`.

**Not in Scope:**
- Integration with real Worker or Provider endpoints. Such integration will follow once Worker/Provider modules are stable.
- Performance/load testing beyond basic checks.
- Security or penetration testing at this stage.
- Full end-to-end system tests combining all WOPA modules.

---

## 3. Assumptions and Risks

### 3.1 Assumptions

- **Stable Worker and Provider Schemas (Mocked):**  
  Worker responses, aggregator outputs, and file references are stable and known. If Worker or Provider schemas change, test updates may be needed.
  
- **Configuration and Environment:**  
  A valid `config.yaml` or equivalent configuration is available, and defaults work if missing. If `WORKER_SERVER_URL` or `PROVIDER_SERVER_URL` differ, tests adapt accordingly.
  
- **Isolated Unit Tests:**  
  All external endpoints (workers, aggregator) are mocked. Actual network calls are replaced with controlled JSON responses or exceptions.

### 3.2 Risks

- **Provider Schema Changes:**  
  If aggregator LLM or Worker result formats change, tests or service logic must be updated promptly.
  
- **Limited Realistic Scenarios:**  
  Mocks simplify testing but may not reflect real complexity. Unexpected formats or latency issues only surface during integration tests.

**Conclusion:**
These assumptions and risks are manageable. The team stands ready to revise tests if external dependencies evolve.

---

## 4. Requirement Verification Matrix (RVM)

**Verification Methods:**
- **T (Test):** Automated unit tests using pytest and mocks.
- **D (Demonstration):** Optional, e.g., viewing `/tasks` or `/get_task_status` in a dev environment to confirm correct behavior visually.
- **A (Analysis):** Not applied at this stage; no complex performance analysis yet.
- **I (Inspection):** Code/log inspection complements test results.

| Requirement                                                  | T | D | A | I | Notes                                      |
|--------------------------------------------------------------|---|---|---|---|--------------------------------------------|
| Must list available services at `/available_services`.        | X |   |   | I | Unit tests ensure JSON array of service names. |
| Must validate and process message analysis tasks.            | X |   |   | I | Tests with `POST /analyze_message` check input validation & aggregator calls. |
| Must validate and process link analysis tasks.               | X |   |   | I | `POST /analyze_link` tests normal & error flows, aggregator results. |
| Must handle file static analysis tasks.                      | X |   |   | I | `POST /analyze_file_static` tests schema & aggregator. |
| Must handle file dynamic analysis tasks (sandbox).           | X |   |   | I | `POST /analyze_file_dynamic` tests mocking sandbox results. |
| Must handle app analysis tasks.                              | X |   |   | I | `POST /analyze_app` tests instructions & aggregator integration. |
| Must return task statuses via `/tasks` & `/get_task_status`. | X | D |   | I | Tests check results appear after processing. Demonstration may show how results accumulate. |
| Must display user-friendly error messages on invalid input or provider failures. | X |   |   | I | Tests submit malformed input or induce aggregator mock failures, verifying `{"status":"error","message":"..."}`. |
| Must store and retrieve aggregated results in `ServiceManager`. | X |   |   | I | Tests confirm that after service processing, results persist and are fetched correctly. |
| Must integrate (mocked at this stage) with aggregator and workers. | X |   |   | I | Tests patch requests to aggregator/worker URLs. On integration test phase, real calls verified. |

All functional requirements are tested (T) at the unit level. Inspection (I) and demonstration (D) support understanding or manual checks. Analysis (A) is deferred until performance concerns arise.

---

## 5. UC-REQ-FEAT-TEST Mapping

| Use Case (UC)                                | Requirement (REQ)                                                | Feature (FEAT)                                            | Test Cases                                                   |
|----------------------------------------------|-------------------------------------------------------------------|-----------------------------------------------------------|--------------------------------------------------------------|
| UC: List services                            | Must list available services at `/available_services`              | `/available_services` endpoint                            | T-Services-List-001                                          |
| UC: Analyze a message                        | Validate input, call text worker, aggregator, return final result  | `/analyze_message` & `MessageService`                     | T-Services-Message-001, T-Services-Message-Invalid-001, T-Services-Message-Agg-001 |
| UC: Analyze a link                           | Validate input, call link worker, aggregator, handle errors        | `/analyze_link` & `LinkService`                           | T-Services-Link-001, T-Services-Link-Error-001, T-Services-Link-Agg-001 |
| UC: Analyze a file statically                | Validate input, call file static worker & aggregator               | `/analyze_file_static` & `FileStaticService`             | T-Services-FileStatic-001, T-Services-FileStatic-Error-001 |
| UC: Analyze a file dynamically (sandbox)     | Similar to above but dynamic sandbox checks                        | `/analyze_file_dynamic` & `FileDynamicService`           | T-Services-FileDynamic-001, T-Services-FileDynamic-Error-001 |
| UC: Analyze an app (APK)                     | Validate `app_ref` & `instructions`, call app worker & aggregator  | `/analyze_app` & `AppService`                            | T-Services-App-001, T-Services-App-Error-001, T-Services-App-Agg-001 |
| UC: Retrieve task statuses & results         | `/tasks` & `/get_task_status` must return correct states & results | `/tasks`,`/get_task_status` & `ServiceManager`           | T-Services-Tasks-001, T-Services-Status-001                 |
| UC: Error handling                           | Must show error JSON if validation fails or aggregator fails       | All service endpoints with invalid input or mock errors   | T-Services-Common-Error-001 (generic for all services)       |

The UC-REQ-FEAT-TEST mapping confirms that each use case (UC) and requirement (REQ) is tied to a specific endpoint or service (FEAT), and corresponding test cases (TEST) ensure coverage.

---

## 6. Endpoints and External Interfaces

This section enumerates the Services Module endpoints and their interplay with mocked workers and aggregator:

**Services Module Endpoints:**

| Endpoint                 | Method | Purpose                                   | Input Example                                                   | Output Example                                                                |
|--------------------------|--------|-------------------------------------------|-----------------------------------------------------------------|-------------------------------------------------------------------------------|
| `/available_services`     | GET    | Lists service names and metadata          | None                                                            | `[{"service_name":"message_analysis","description":"..."}]`                  |
| `/analyze_message`        | POST   | Processes a message analysis request       | `{"message":"Check suspicious link..."}`                        | `{"task_id":"message_analysis-uuid","status":"completed","result":{...}}`    |
| `/analyze_link`           | POST   | Processes a link analysis request          | `{"url":"http://example.com"}`                                 | `{"task_id":"link_analysis-uuid","status":"completed","result":{...}}`       |
| `/analyze_file_static`    | POST   | File static analysis request               | `{"file_ref":"test.pdf"}`                                        | `{"task_id":"file_static_analysis-uuid","status":"completed","result":{...}}`|
| `/analyze_file_dynamic`   | POST   | File dynamic (sandbox) analysis request    | `{"file_ref":"susp.exe"}`                                        | `{"task_id":"file_dynamic_analysis-uuid","status":"completed","result":{...}}`|
| `/analyze_app`            | POST   | App behavior analysis request              | `{"app_ref":"test.apk","instructions":"Play this game..."}`      | `{"task_id":"app_analysis-uuid","status":"completed","result":{...}}`        |
| `/tasks`                  | GET    | Lists all tasks and their statuses         | None                                                            | `[{"task_id":"...","status":"completed"}]`                                   |
| `/get_task_status`        | GET    | Retrieves status/result for a given task_id| `?task_id=message_analysis-uuid`                                 | `{"status":"completed","result":{...}}` or `{"status":"error","message":"..."}`|

**External (Mocked) Endpoints:**
- Worker calls:  
  `POST {WORKER_SERVER_URL}/request_worker`  
  Mocks return completed or error results for text/link/file/app workers.
- Aggregator LLM calls:  
  `POST {PROVIDER_SERVER_URL}/llm/chat_complete`  
  Mocks return `{"status":"success","response":"{...json...}"}` or error codes to test fallback logic.

At the unit level, these worker and aggregator calls are all replaced with mocked `requests.post` or `requests.get`. Integration tests will remove mocks and verify actual networking.

---

## 7. Unit Test Plan and Test Cases

**Objectives of Unit Testing:**
- Confirm each endpoint validates inputs and handles success/error paths.
- Check each service class can parse worker results and aggregator responses correctly.
- Ensure `ServiceManager` properly stores, retrieves, and updates tasks.

**Test Categories:**
- **Endpoints Tests:**  
  Validate that `/analyze_message`, `/analyze_link`, `/analyze_file_static`, `/analyze_file_dynamic`, `/analyze_app` return correct JSON, handle invalid inputs, and process aggregator logic.
- **Service Classes Tests:**  
  Validate each `validate_task` and `process` method. Mocks simulate worker and aggregator.
- **Manager Tests:**  
  Test `ServiceManager` to confirm `process_task_now`, `update_and_get_task_status` handle various scenarios.

**Mocking Strategies:**
- Patch `requests.post`/`requests.get` calls to aggregator and worker endpoints to return predefined JSON or raise exceptions.

**Naming & Coverage:**
- `test_services_endpoints.py` for endpoint-level tests.
- `test_message_service.py`, `test_link_service.py`, etc., for each service class.
- `test_service_manager.py` for `ServiceManager` logic.

**Sample Test Cases:**
- **T-Services-Message-001:** Valid input for `/analyze_message` returns completed result.
- **T-Services-Message-Invalid-001:** Missing `message` field returns 400 error.
- **T-Services-Link-001:** Normal link scenario returns completed result from aggregator.
- **T-Services-Link-Error-001:** Aggregator returns invalid JSON, service returns `status:"error"`.
- **T-Services-App-001:** Valid `app_ref` and `instructions` produce completed result.
- **T-Services-Manager-001:** Manager stores and retrieves a completed task correctly.

These tests ensure each service scenario and manager behavior is validated before integration.

---

## 8. Integration Test Plan and Test Cases

After unit tests pass, integration tests will run with real Worker endpoints and aggregator services. Similar logic applies: remove mocks, deploy providers, and confirm that actual calls produce correct results. The integration testing approach mirrors that described in previous Worker Module test plans.

Until Providers subsystem is stable, integration tests remain on hold. The team will define them similarly to integration tests for Workers once ready.

---

## 9. Test Environment and Tools

- **Containers:**  
  Running `services` container plus mocks for workers and aggregator. For unit tests, no real providers needed; mocks suffice.
  
- **Tools:**  
  `pytest`, `unittest.mock`, `requests` library for mocking.  
  `make test-unit-services` for running tests inside container.

- **Logs & CI:**  
  Logs and coverage tools same as Worker Module. CI pipeline ensures no regressions.

---

## 10. Test Reporting

- **Console Output via pytest:**  
  Quick feedback on local runs.
  
- **CI Integration:**  
  JUnit XML or JSON format for results if desired. CI can halt merges if tests fail.

- **Coverage:**  
  Use `pytest-cov` to track coverage. Ensure all endpoints and service paths have near 100% coverage at unit level.

---

## 11. Roles and Responsibilities

- **Developers (Service Focus):**  
  Add/maintain tests for endpoints and services. Fix logic if tests fail.
  
- **Test/QA Engineers:**  
  Improve coverage, add complex aggregator error scenarios, ensure all use cases tested.

- **DevOps:**  
  Maintain `docker-compose` and `make` targets for easy test runs.

- **PM/Lead:**  
  Uses test results to judge readiness for integration and eventually release.

---

## 12. Schedule and Milestones

- **Unit Test Completion (Current Phase):**  
  All endpoints and services tested with mocks.
  
- **Integration Prep:**  
  Once Worker and Provider modules stable, add integration tests that remove mocks and call real endpoints.

- **Pre-Release Checks:**
  Achieve passing unit and integration tests, good coverage, stable results under multiple runs.

---

## 13. Conclusion and References

This test plan sets a strong foundation for verifying the Services Module. By detailing use cases, mapping them to requirements and features, and enumerating test cases, the plan ensures clarity, traceability, and maintainability. The approach—unit tests first with mocks, later integration tests with real dependencies—provides incremental confidence in system quality.

**References:**
- WOPA Project Charter and Philosophies
- Worker Module Test Plan (previously defined)
- Providers Subsystem Documentation
- FastAPI, Pytest official docs

**Next Steps:**
- Complete unit tests for all endpoints and services.
- Wait for Providers subsystem readiness, then add integration tests.
- Evaluate coverage, fix gaps, and prepare for final integration and system tests.

This comprehensive Services Module test plan enables the team to deliver robust, reliable features, confident that each endpoint and service class meets specifications and gracefully handles real-world complexities.
