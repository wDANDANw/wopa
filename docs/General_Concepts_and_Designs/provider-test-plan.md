# Test Plan for Providers Subsystem (Finalized Version)

**Date:** 24 October 2024  
**Prepared by:** Project Team (CS 588 Cybersecurity Capstone)

---

## 1. Introduction

The Providers subsystem is an internal component of the WOPA environment designed to supply specialized services to other subsystems. It is not a standalone product and does not directly interface with external end-users. Instead, it serves as a “backroom” or “support” module that provides three key capabilities:

1. **LLM-based Text Analysis:**  
   This component interacts with a locally running Ollama LLM service (at `http://localhost:11434`) to process text prompts. Other WOPA modules rely on this functionality to interpret, classify, or summarize textual content. The Providers subsystem must ensure that prompts sent to the LLM are properly formatted, and that responses—whether successful or error-based—are structured and actionable.

2. **Sandbox File Analysis (Cuckoo):**  
   The subsystem can send suspicious files to one or multiple Cuckoo Sandbox instances. These sandboxes are not statically defined; they are dynamically provisioned via Terraform and can scale horizontally if demand increases. The subsystem must accurately map these sandbox instances, deliver files to them, and return structured logs indicating benign or malicious activities. This ensures WOPA’s main system can flag harmful files before they reach end-users or other critical parts of the environment.

3. **Android App Emulation (docker-android):**  
   Using Terraform-provisioned docker-android instances, the Providers subsystem can emulate mobile apps, simulate user interactions, record events, and capture screenshots. This enables the main system to detect suspicious or malicious app behavior without risking a real device. The subsystem must locate appropriate emulator endpoints, run apps, and return meaningful data to WOPA’s main logic.

**Role within WOPA:**  
The Providers subsystem never stands alone; it’s strictly internal. Its stable, well-defined endpoints (e.g., `/health`, `/llm/chat_complete`, `/sandbox/run_file`, `/emulator/run_app`, `/{task_id}/vnc`) and a Gradio-based admin UI provide introspection and operational status reports. The main WOPA backend and other modules rely on these endpoints to understand providers’ capabilities and states. The Providers subsystem must thus maintain high reliability, clear error reporting, and strong integration with provisioning tools (like Terraform) that dynamically alter the environment.

**Testing Context:**  
Since the Providers subsystem operates behind the scenes, the testing approach must account for both internal logic validation (unit testing) and real-world scenario verification (integration testing). Unit tests mock external dependencies to ensure internal methods (input validation, fallback logic, logging) are correct. Integration tests require a running Ollama instance and Terraform-provisioned sandbox/emulator instances to verify true end-to-end behavior.

---

## 2. Scope and Objectives

The testing strategy covers both **Functional** and **Non-Functional** requirements:

- **Functional Goals:**  
  - **LLM Interaction:** Ensure `/llm/chat_complete` returns either a correct, meaningful textual response or a well-structured error. This involves testing various prompt complexities, ensuring fallback on external API failure, and verifying proper JSON formatting.
  - **Sandbox Analysis:** Confirm `/sandbox/run_file` processes files and returns logs accurately. Unit tests mock sandbox responses, while integration tests use a real Cuckoo Sandbox instance. The subsystem must handle both safe and malicious sample files, invalid file references, and sandbox downtime gracefully.
  - **Emulator Operations:** Validate `/emulator/run_app` and `/{task_id}/vnc` endpoints to ensure the subsystem can actually run an app in an emulator and return correct visuals/events. Integration tests must confirm that real emulator instances, dynamically created by Terraform, work as expected.

- **Non-Functional Goals:**  
  - **Reliability & Health Checks:** The `/health` endpoint must correctly reflect LLM, sandbox, and emulator health states. Periodic checks or triggered tests must confirm stable and consistent behavior.
  - **Scalability & Provisioning:** Ensure that when Terraform provisions multiple sandbox/emulator instances, the Providers subsystem discovers and uses them correctly without code changes—just configuration and `provisioner.py` scripts.
  - **Error Messaging & Logging:** Check that invalid inputs, external failures, or missing dependencies yield user-friendly error messages, well-structured JSON responses, and comprehensive log entries for debugging.
  - **Admin UI Support:** The admin UI (Gradio) queries endpoints to show current status. Tests ensure UI endpoints (`/admin/endpoints`) and related data are correct and reflect reality, aiding internal monitoring.

**What’s In Scope:**
- All internal logic, endpoint handlers, input validation code, fallback and error routines, scaling logic integration.
- Communication with Ollama, sandbox, and emulator through mocked responses (unit tests) and real endpoints (integration tests).
- Verification that Terraform-provisioned resources are discovered and utilized by the Providers subsystem.

**What’s Out of Scope:**
- End-to-end WOPA system testing involving user-facing components. Those tests occur at a higher level.
- Detailed performance or stress testing, though basic reliability checks are included.
- Security penetration tests of sandbox or emulator containers (handled externally).

The main objective is to give developers and maintainers confidence that the Providers subsystem’s code and configuration changes do not break its essential functionalities, degrade reliability, or distort error reporting, whether tested in isolation or integrated with real instances.

---

## 3. Requirements Verification Matrix (RVM)

The matrix below maps each requirement to a suitable verification method (Test, Demonstration, Analysis, Inspection) and notes any special conditions.

**Verification Methods:**
- **T:** Test (execute code, compare output to expected results)
- **D:** Demonstration (manual or guided scenario testing)
- **A:** Analysis (use models or structured reasoning)
- **I:** Inspection (reviewing code, docs, configs)

| Requirement                                  | Verification (T/D/A/I) | Notes                                               |
|----------------------------------------------|-----------------------|-----------------------------------------------------|
| FR-LLM-Analysis: Interpret text with LLM      | T, I                  | Tests ensure `/llm/chat_complete` correctness.     |
| FR-Sandbox-Dynamic: Run files in sandbox      | T, I                  | Integration tests confirm real sandbox logs; unit mocks. |
| FR-Emulator-Visual: Emulate app & visuals     | T, I                  | Integration tests run actual apps on emulator; unit mocks. |
| FR-Input-Validation: Validate request inputs  | T, I                  | Unit tests with malformed JSON, check error outputs. |
| FR-Error-Messaging: Friendly error outputs     | T, I                  | Unit + integration tests with invalid states.        |
| FR-Fallback-ExternalAPI: Handle external fails| T, I                  | Kill Ollama or sandbox in integration test, see error. |
| NFR-Reliability: Stable health checks          | T, D                 | `/health` endpoint tested with all dependencies.    |
| NFR-Scalability: Terraform provisioning        | T, A                 | Integration tests after scaling resources, plus analysis of Terraform outputs. |
| NFR-Logging-Debugging: Comprehensive logs      | T, I                 | Induce errors, check logs in unit tests, partial integration log checks if possible. |
| NFR-Admin-UI: Admin endpoints & clarity        | T, D                 | Check `/admin/endpoints` and UI rendering.          |

This matrix ensures every requirement is anchored to at least one test-based verification method (T). Demonstrations (D) occur during development phases, for example, manually checking admin UI. Analysis (A) and Inspection (I) complement tests by reviewing logic, Terraform configs, and code structure to prevent misconfigurations.

## 4. UC-REQ-FEAT-TEST Mapping

This section creates a direct chain linking **Use Cases (UC)**—the primary functional scenarios the Providers subsystem must handle—to the **Requirements (REQ)** they realize, the **Features (FEAT)** implemented to meet those requirements, and finally to the **Test Cases (TEST)** that verify correct behavior. This mapping ensures no feature or test is floating without purpose, and no requirement goes untested.

**Key Concepts:**
- **Use Case (UC):** A scenario describing how the Providers subsystem serves the WOPA environment. For example, “LLM-based Text Analysis” is a UC describing the process of sending text prompts and receiving responses.
- **Requirement (REQ):** A specific statement that must be met. Functional requirements might say “The subsystem must interpret textual prompts using the LLM,” while non-functional requirements may say “The subsystem must return clear error messages.”
- **Feature (FEAT):** An implemented technical capability or endpoint. For example, the `POST /llm/chat_complete` endpoint is a feature enabling the LLM-based text analysis UC.
- **Test(s):** Each test case corresponds to unit or integration scenarios that confirm the feature works as intended under the given UC and requirement conditions.

Below is the comprehensive UC-REQ-FEAT-TEST table. Tests are split into **Unit** (U) and **Integration** (I) types. “Related” indicates multiple tests per scenario if necessary.

| Use Case (UC)                               | Requirement (REQ)                        | Feature (FEAT)                                                | Test(s)                                                                                                                                                 |
|---------------------------------------------|-------------------------------------------|---------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|
| Providers Health Check & Admin Visibility    | NFR-Reliability, NFR-Admin-UI             | `/health` endpoint, Admin UI (Gradio), periodic checks         | Unit: **T-Provider-Server-Health-001** (U) checks mocked dependencies. Integration: **T-Provider-Admin-UI-001** (I) runs with real Ollama/Sandbox/Emulator. |
| LLM-based Text Analysis (LLM UC)             | FR-LLM-Analysis, FR-Error-Messaging, FR-Fallback-ExternalAPI | `POST /llm/chat_complete` endpoint, LLMClient interpret method | Unit: **T-Provider-LLM-Interpret-001** (U) mocks LLM calls. Integration: **T-Provider-LLM-Integr-001** (I) uses real Ollama. Fallback tests: **T-Provider-Fallback-API-001** (U), **T-Provider-Fallback-Integr-001** (I). |
| Sandbox Execution for Files (Sandbox UC)     | FR-Sandbox-Dynamic, FR-Error-Messaging, FR-Fallback-ExternalAPI, FR-Input-Validation | `POST /sandbox/run_file` endpoint, SandboxEnv run_file logic  | Unit: **T-Provider-Sandbox-RunFile-001** (U) mocks sandbox responses. Integration: **T-Provider-Sandbox-Integr-001** (I) tests real sandbox instance. Errors tested by **T-Provider-Error-Msg-001**. Fallback: **T-Provider-Fallback-API-001** (I). |
| Android Emulator for App Analysis (Emulator UC)| FR-Emulator-Visual, FR-Error-Messaging, FR-Fallback-ExternalAPI | `POST /emulator/run_app`, `GET /{task_id}/vnc` endpoints, emulator_env logic | Unit: **T-Provider-Emu-RunApp-001**, **T-Provider-Emu-VNC-001** (U) mock emulator. Integration: **T-Provider-Emu-Integr-001** (I) runs real emulator instance. Errors & fallback tested similarly. |
| Input Validation & User-Friendly Errors      | FR-Input-Validation, FR-Error-Messaging   | Input parsing checks in endpoint handlers                     | Unit: **T-Provider-Input-Validation-001**, **T-Provider-Error-Msg-001** ensure malformed requests yield proper error JSON. Integration: **T-Provider-Error-Integr-001** tries invalid input with real environment. |
| Local Dependencies & Provisioning (Scaling UC)| NFR-Local-Dependencies, NFR-Scalability   | Terraform-managed instances, local tool checks (adb, sandbox bin) | Unit: **T-Provider-Local-Check-001** mocks checking for binaries. Integration: **T-Provider-Scaling-Integr-001** after `provisioner.py apply` checks multiple sandbox/emulator endpoints. |
| Logging & Reporting for Debugging (Logging UC) | NFR-Logging-Debugging                   | Logging statements on errors, fallback, unusual events         | Unit: **T-Provider-Logging-001** verifies logs on error induction. Integration: **T-Provider-Logging-Integr-001** triggers real endpoint errors and inspects logs (if accessible). |

**Detailed Explanation:**

1. **Health Check & Admin Visibility:**  
   - The `/health` endpoint ensures WOPA’s main system knows the Providers subsystem status. Unit tests mock LLM/sandbox/emulator states to confirm correct JSON. Integration tests run `/health` against actual Ollama and Terraform-provisioned resources, ensuring real conditions match expected statuses.
   - The admin UI queries `/admin/endpoints` or other endpoints. Unit tests confirm endpoint listings are correct; integration tests check the UI displays real data (like available sandbox instances after provisioning).

2. **LLM-based Text Analysis:**  
   - Requirements: Handle textual prompts, return well-structured responses or errors, fallback gracefully if Ollama is down.
   - Features: `POST /llm/chat_complete` calls LLMClient, which interacts with Ollama.
   - Tests: Unit mocks let us feed fake Ollama responses. Integration tests query the real Ollama endpoint at `http://localhost:11434` to confirm that a genuine LLM reply is returned. Error and fallback scenarios appear if Ollama stops mid-test.

3. **Sandbox Execution for Files:**
   - Requirements: Dynamically run files and get logs, handle errors if sandbox is unreachable.
   - Feature: `POST /sandbox/run_file` finds a sandbox instance (real endpoint discovered from Terraform outputs).
   - Tests: Unit tests mock logs as if sandbox always returns known data. Integration tests run a sample file on a real sandbox instance. If sandbox is down, integration tests confirm that fallback error messages are user-friendly.

4. **Android Emulator for App Analysis:**
   - Requirements: Emulate apps, produce visuals/events, get a VNC link.
   - Feature: `POST /emulator/run_app` and `GET /{task_id}/vnc`.
   - Tests: Unit tests mock emulator responses. Integration tests require real docker-android instances from Terraform. The test ensures that a real `app_ref` run yields an actual `vnc_url` and events.

5. **Input Validation & Errors:**
   - Requirements: Reject malformed inputs early, show friendly error messages.
   - Tests: Unit tests provide invalid JSON to each endpoint, expecting structured error JSON. Integration tests do the same but with the full environment running to confirm consistent behavior.

6. **Local Dependencies & Scalability:**
   - Requirements: Terraform provisioning must scale sandbox/emulator instances and these must be discoverable and usable without code changes.
   - Tests: Unit tests mock local checks (like `adb devices`). Integration tests run after `provisioner.py apply` has created multiple instances, ensuring that the providers subsystem’s code automatically adapts and uses them.

7. **Logging & Debugging:**
   - Requirements: Rich logs for error scenarios, enabling quick troubleshooting.
   - Tests: Unit tests ensure that induced errors call the logger correctly. Integration tests trigger actual endpoint errors (like removing an emulator instance) and verify logs are generated and can be analyzed (if we have a logging endpoint or external log collection).

This table and detailed explanation connect each use case back to specific requirements, the implemented features, and the corresponding test cases. By following this mapping, testers can be sure that every key scenario is covered, every requirement is verified, and that both unit and integration tests are aligned with the actual functionalities of the Providers subsystem.

## 5. Endpoints and External Interfaces

This section details the internal server endpoints provided by the Providers subsystem and the external interfaces it relies upon. It clarifies what internal WOPA modules can use (the Providers’ own endpoints) and which external services the Providers subsystem needs (Ollama, sandbox instances, emulator instances, backend task API).

### Server Endpoints (Internal)

These are the HTTP endpoints that other parts of WOPA (like the main backend or admin UI) invoke to interact with the Providers subsystem. They represent the main interface through which WOPA gains LLM analysis, sandbox logs, and emulator behaviors. Each endpoint’s purpose, input, and output formats are strictly defined and verified by tests.

| Endpoint              | Method | Purpose                                           | Input Example                     | Output Example                                              |
|-----------------------|--------|---------------------------------------------------|-----------------------------------|-------------------------------------------------------------|
| `/health`             | GET    | Check overall health of LLM, Sandbox, Emulator     | None                              | `{"status":"ok","details":{"llm":"ok","sandbox":"ok","emulator":"ok"}}` |
| `/llm/chat_complete`  | POST   | Interact with the LLM (Ollama) for text analysis   | `{"prompt":"Why is the sky blue?"}`| `{"status":"success","response":"Rayleigh scattering..."}`   |
| `/sandbox/run_file`   | POST   | Run a file in a Cuckoo Sandbox instance, get logs  | `{"file_ref":"malware.bin"}`      | `{"status":"success","logs":["suspicious syscall","net calls"]}`|
| `/emulator/run_app`   | POST   | Run an app in an emulator and simulate user actions | `{"app_ref":"test.apk"}`         | `{"status":"success","visuals":{"img":"base64..."},"events":["click","scroll"]}`|
| `/{task_id}/vnc`      | GET    | Return a VNC link to view emulator’s screen         | None                              | `{"status":"success","vnc_url":"vnc://HOST:5900"}`          |
| `/admin/endpoints`    | GET    | (Future) List all available provider endpoints      | None                              | `{"endpoints":["/llm/chat_complete","/sandbox/run_file","/emulator/run_app"]}`|

**Test Considerations:**
- **Unit Tests:** Mock responses from LLM/sandbox/emulator to ensure endpoints format JSON correctly, handle errors, and perform input validation.  
- **Integration Tests:** Use actual Ollama, real sandbox instances, and emulator instances provisioned by Terraform. Check that real responses (actual LLM text, actual sandbox logs, and emulator visuals/events) match the expected formats and that `/health` returns accurate states.

### External Endpoints / Interfaces the Providers Module Uses

The Providers subsystem does not live in isolation; it interacts with external services and tools:

| External Interface            | Tooling                            | Endpoint/Host Examples          | Usage                                                       |
|-------------------------------|------------------------------------|---------------------------------|-------------------------------------------------------------|
| Ollama LLM Service (Local)    | docker-compose at root              | `http://localhost:11434`        | Providers subsystem sends text prompts to Ollama. Integration tests ensure real LLM responses. |
| Sandbox (Cuckoo Sandbox)      | Terraform-provisioned (hypervisor/docker) | `http://sandbox1:8002`          | Providers picks a sandbox instance from registry and sends files for analysis. Integration tests require a running sandbox. |
| Emulator (docker-android)     | Terraform-provisioned (hypervisor/docker) | ADB at `http://emulatorX:444X`, VNC at `http://emulatorX:590X` | The subsystem queries emulators to run apps. Integration tests confirm real emulator interactions. |
| Backend Task API (External)   | External to Providers subsystem     | `http://BACKEND_URL/api/task/{task_id}` | Provides metadata for tasks if needed by admin UI. Not heavily tested in Providers subsystem unless integration requires it. |
| Terraform/Ansible (Provisioning)| Infra as Code                      | N/A                              | `provisioner.py` applies Terraform configurations to create multiple sandbox/emulator instances. Tests check that after provisioning, providers endpoints discover and use them seamlessly. |

**Test Considerations:**
- **Unit Tests:** Mocks replace calls to these external endpoints. No actual network requests are made.  
- **Integration Tests:** Require these external services to be live. For instance:
  - Ollama must be running (`docker compose up ollama`).
  - Sandbox/emulator instances created by running `provisioner.py apply`.
  - Integration tests attempt real requests and expect real responses from these services.

### Interaction and Assumptions

**Assumptions:**
- Ollama runs locally at `localhost:11434`, stable and accessible.
- Terraform scripts successfully provision sandbox and emulator instances. Once done, the Providers subsystem reads a registry (e.g., `instances.json`) to know which endpoints are active.
- If external endpoints fail (e.g., sandbox down, Ollama unreachable), the Providers subsystem must handle these gracefully, returning structured errors instead of crashing.

**Documentation and Versioning:**
- Endpoint documentation remains stable, so tests can rely on consistent input/output formats.
- Changes in Ollama’s endpoint port or sandbox/emulator scaling logic must be reflected in `config.yaml` and possibly test setups. The test plan assumes these changes are rare and well-communicated.

In short, these endpoints (internal and external) form the foundation of all testing scenarios. Without consistent endpoints, neither unit nor integration tests can validate functionalities. The thorough test coverage ensures that any shifts in these interfaces trigger corresponding test updates, keeping the subsystem robust and reliable.

## 6. Unit Test Plan and Test Cases

This section details the **Unit Test Plan** for the Providers subsystem, ensuring all critical functionalities are verified at a code level without reliance on actual external services. Unit tests run early in the development cycle, catching logic errors before integration testing. By mocking external dependencies, we isolate internal logic—validating input handling, error messaging, logging, fallback mechanisms, and endpoint response formatting.

### Objectives of Unit Testing

- **Isolate Internal Logic:**  
  Each unit test focuses on Providers subsystem code in strict isolation. All external endpoints (LLM, sandbox, emulator) are replaced with mocks to ensure test failures reflect Providers logic issues, not external systems.

- **Early Defect Detection:**  
  Unit tests verify proper input validation, structured JSON outputs, error handling, and fallback logic. By catching these issues early, we ensure stable foundations for subsequent integration tests and prevent regressions.

- **Maintainability and Scalability:**  
  By organizing tests into logical categories and using consistent naming conventions, it’s straightforward to add new tests as the subsystem grows. If a new worker or a new endpoint emerges, we can replicate the existing test patterns for rapid, consistent coverage.

### Test Categories

1. **Endpoint-Level Tests:**  
   These tests target each Providers endpoint (`/health`, `/llm/chat_complete`, `/sandbox/run_file`, `/emulator/run_app`, `/{task_id}/vnc`, and `/admin/endpoints`) individually.  
   - **Goal:** Ensure correct HTTP status codes, JSON structures, successful/erroneous scenarios, and user-friendly error messages.
   - **Approach:** Each endpoint test uses mock responses for external calls to simulate normal operation, partial failures (like a down LLM), and invalid inputs (like missing `prompt` or `file_ref`).

2. **Manager and Worker Logic Tests:**  
   Internal classes like `LLMClient`, `sandbox_env`, `emulator_env`, and any manager layers (if present) are tested here.  
   - **Goal:** Validate that worker classes correctly process inputs, handle normal and error mock responses, and generate expected results or fallback errors.
   - **Approach:** Mock all external APIs. For example, `llm_client.interpret()` returns a mock JSON response. `sandbox_env.run_file()` returns a mock log array. `emulator_env.run_app()` returns mock visuals/events. Tests check if the manager and workers react properly—storing results, raising errors, or logging correctly.

3. **Input Validation, Error Handling, and Logging Tests:**  
   Some tests specifically induce malformed requests or trigger exceptions in mock responses to confirm that:  
   - Input validation routines reject invalid inputs and return structured error JSON.  
   - Fallback logic gracefully recovers from external failures (like a mock LLM timeout) by returning a meaningful error message.  
   - Logging calls record error details at appropriate levels, providing clear debugging clues.

### Mocking Strategies

- **External Calls Mocking:**  
  All network requests to Ollama, sandbox instances, or emulator endpoints are replaced with `unittest.mock.patch` or similar tools. Mocks can return:
  - **Successful responses:** Confirm normal operation.
  - **Error responses:** Simulate unreachable LLM or sandbox server returning HTTP 500, triggering fallback logic.
  - **Empty or malformed responses:** Test how well the code handles unexpected data.

- **Local Dependencies Mocking:**  
  If local binaries (e.g., `adb`) or configuration loaders (`config_loader.py`) are involved, mocks return predetermined values, ensuring no dependency on actual filesystem or environment states.

- **Manager and Worker Internals Mocking:**  
  For endpoint tests, we can mock internal methods of the manager or workers to simulate desired states without testing the entire stack. Conversely, dedicated manager/worker logic tests may use fewer mocks to verify that logic stands alone.

### Naming Conventions and File Organization

- **Test Filenames:**  
  - `test_endpoints.py`: Contains endpoint-level tests.  
  - `test_manager_workers.py`: Contains manager and worker logic tests.  
  - `test_validation_and_logging.py`: Tests focusing on input validation, error handling, and logging.

- **Test Function Names:**
  Follow a `test_{feature}_{condition}` pattern:  
  - `test_llm_chat_complete_success`  
  - `test_sandbox_run_file_invalid_input`  
  - `test_emulator_run_app_fallback_on_error`
  
  This ensures clarity: readers can guess what scenario a test covers from its name.

- **Comments and Docstrings:**  
  Each test function includes brief docstrings or comments explaining its purpose, setup steps, expected results, and variations. This eases maintenance and onboarding of new team members.

### Coverage Approach

- **Endpoints Coverage:**  
  Each endpoint is tested with:
  - Valid input (happy path)
  - Invalid input (missing required fields, wrong data types)
  - Simulated external service errors (mock failures)
  - Boundary conditions (e.g., extremely long prompts for LLM, suspicious or safe files for sandbox)
  
  This ensures robust endpoint validation before integration tests.

- **Worker Classes Coverage:**  
  Each worker’s `process()` method is tested for:
  - Correct handling of normal mock responses (e.g., a “phishing” classification from LLM).
  - Graceful behavior on error mock responses (simulating timeouts, bad JSON, HTTP error codes).
  - Proper input validation at the worker level (missing `prompt`, `file_ref`, or `app_ref` fields).
  
- **Logging and Error Routes:**  
  Specific tests induce errors intentionally (e.g., mocking a raised exception in a worker) and confirm that:
  - The subsystem returns `{"status":"error","error":"message"}` in the response body.
  - Logging calls occur as expected, capturing error details at ERROR level logs.

- **Scalability and Fallback Checks:**  
  Although scaling logic is mostly integration-tested (since it requires Terraform provisioning), unit tests can still mock a scenario where multiple sandbox instances are “registered” in the manager. The manager’s selection logic can be tested by simulating different mock registry states. Fallback tests confirm that if one mock instance fails, the code tries another or returns an error gracefully.

## Full Unit Test Case Listing

Below is the comprehensive list of **unit test cases** for the Providers subsystem, following a consistent naming and formatting convention. Each test case includes purpose, strategy, tested objects, steps, and success criteria. These tests cover endpoints, worker logic, input validation, error handling, fallback scenarios, logging, and admin UI checks, all with mocked external dependencies.

**Note:** “Mock” indicates external provider calls (LLM, Sandbox, Emulator) are replaced by simulated responses.

### Server Health & Admin Visibility

**T-Provider-Server-Health-001: Basic Health Check**  
- **Purpose:**  
  Verify `/health` endpoint returns correct JSON status of LLM, sandbox, and emulator subsystems under normal conditions.  
- **Strategy:**  
  Mock LLM, sandbox, and emulator states as “healthy.” Call `/health` and check the returned JSON.  
- **Tested Objects:**  
  `/health` endpoint handler, health-check logic.  
- **Steps:**  
  1. Mock LLM check → returns `ok`  
  2. Mock sandbox check → returns `ok`  
  3. Mock emulator check → returns `ok`  
  4. GET `/health`  
  5. Expect `{"status":"ok","details":{"llm":"ok","sandbox":"ok","emulator":"ok"}}` and HTTP 200.  
- **Success Criteria:**  
  `/health` returns `status:"ok"` and all subsystems `"ok"` as mocked.

**T-Provider-Admin-UI-001: Admin Endpoints List**  
- **Purpose:**  
  Confirm `/admin/endpoints` (future endpoint) or `/admin` UI endpoint returns the expected list of provider endpoints.  
- **Strategy:**  
  Mock no external calls needed. Just ensure endpoint returns a stable JSON/HTML structure.  
- **Tested Objects:**  
  `/admin/endpoints` or `/admin` endpoint, endpoint listing logic.  
- **Steps:**  
  1. GET `/admin/endpoints`  
  2. Expect HTTP 200 and `{"endpoints":["/llm/chat_complete","/sandbox/run_file","/emulator/run_app"]}`  
- **Success Criteria:**  
  The known endpoints appear in the JSON. Admin UI can read and display them.

### LLM-Based Text Analysis Tests

**T-Provider-LLM-Interpret-001: Normal LLM Prompt Interpretation**  
- **Purpose:**  
  Check `/llm/chat_complete` with a valid prompt returns a mocked successful LLM response.  
- **Strategy:**  
  Mock `llm_client.interpret("Why is sky blue?")` → `{"status":"success","response":"Rayleigh scattering..."}`  
- **Tested Objects:**  
  `/llm/chat_complete` endpoint, `llm_client` logic.  
- **Steps:**  
  1. POST `{"prompt":"Why is sky blue?"}` to `/llm/chat_complete`.  
  2. Expect HTTP 200 and `{"status":"success","response":"Rayleigh scattering..."}`.  
- **Success Criteria:**  
  Returns correct success JSON as per mock LLM response.

**T-Provider-Fallback-API-001: LLM Failure Fallback**  
- **Purpose:**  
  Ensure that if LLM mock simulates a failure (e.g. timeout), endpoint returns a user-friendly error.  
- **Strategy:**  
  Mock `llm_client.interpret()` to raise a request exception.  
- **Tested Objects:**  
  `/llm/chat_complete` endpoint’s error/fallback handling.  
- **Steps:**  
  1. POST `{"prompt":"Check this URL"}` with LLM mock failing.  
  2. Expect HTTP 503 and `{"status":"error","error":"LLM service unavailable"}`.  
- **Success Criteria:**  
  Error scenario produces a graceful fallback message, not a crash.

### Sandbox File Analysis Tests

**T-Provider-Sandbox-RunFile-001: Safe File Analysis**  
- **Purpose:**  
  Check `/sandbox/run_file` with a safe file returns mocked benign logs.  
- **Strategy:**  
  Mock `sandbox_env.run_file("safe.bin")` → `{"logs":["no suspicious activity"]}`.  
- **Tested Objects:**  
  `/sandbox/run_file` endpoint, sandbox_env logic.  
- **Steps:**  
  1. POST `{"file_ref":"safe.bin"}` to `/sandbox/run_file`.  
  2. Expect HTTP 200 and `{"status":"success","logs":["no suspicious activity"]}`.  
- **Success Criteria:**  
  Correct JSON structure and logs from mock. No errors.

**T-Provider-Error-Msg-001 (Sandbox Variation):**  
- **Purpose:**  
  Induce an error in the sandbox mock to ensure friendly error message.  
- **Strategy:**  
  Mock `sandbox_env.run_file()` to throw an exception or return error.  
- **Tested Objects:**  
  `/sandbox/run_file` error handling.  
- **Steps:**  
  1. POST `{"file_ref":"malware.bin"}`  
  2. Sandbox mock returns error scenario.  
  3. Expect HTTP 500 or 503 with `{"status":"error","error":"Sandbox unavailable"}`.  
- **Success Criteria:**  
  Error JSON is user-friendly and structured.

### Emulator App Analysis Tests

**T-Provider-Emu-RunApp-001: Normal App Run**  
- **Purpose:**  
  Ensure `/emulator/run_app` returns visuals/events on valid input.  
- **Strategy:**  
  Mock `emulator_env.run_app("test.apk")` → `{"visuals":{"img":"base64..."},"events":["click"]}`  
- **Tested Objects:**  
  `/emulator/run_app` endpoint, emulator_env logic.  
- **Steps:**  
  1. POST `{"app_ref":"test.apk"}`  
  2. Expect HTTP 200 and `{"status":"success","visuals":{"img":"base64..."},"events":["click"]}`.  
- **Success Criteria:**  
  Endpoint returns correct success JSON as per mock data.

**T-Provider-Emu-VNC-001: VNC Link Retrieval**  
- **Purpose:**  
  Confirm `/{task_id}/vnc` returns a mocked VNC URL.  
- **Strategy:**  
  Mock `emulator_env.get_vnc_link(task_id)` → `{"vnc_url":"vnc://HOST:5900"}`.  
- **Tested Objects:**  
  `/{task_id}/vnc` endpoint.  
- **Steps:**  
  1. GET `/{task_id}/vnc` with task_id="abc"  
  2. Expect HTTP 200 and `{"status":"success","vnc_url":"vnc://HOST:5900"}`.  
- **Success Criteria:**  
  Correctly returns VNC link from mock.

### Input Validation & Error Handling Tests

**T-Provider-Input-Validation-001: Missing Prompt for LLM**  
- **Purpose:**  
  Send invalid input to `/llm/chat_complete` to confirm 400 error and descriptive error message.  
- **Strategy:**  
  POST `{}` (no prompt).  
- **Tested Objects:**  
  Input validation in `/llm/chat_complete` endpoint.  
- **Steps:**  
  1. POST `{}` to `/llm/chat_complete`.  
  2. Expect HTTP 400 and `{"status":"error","error":"Missing 'prompt' field"}`.  
- **Success Criteria:**  
  Proper 400 error and user-friendly error message.

**T-Provider-Error-Msg-001: Internal Logic Error**  
- **Purpose:**  
  Simulate an unexpected internal exception in sandbox worker to confirm a generic error response.  
- **Strategy:**  
  Mock `sandbox_env.run_file()` to raise an arbitrary exception.  
- **Tested Objects:**  
  Exception handling in `/sandbox/run_file`.  
- **Steps:**  
  1. POST `{"file_ref":"unknown.bin"}`  
  2. Mock raises exception.  
  3. Expect HTTP 500 and `{"status":"error","error":"Internal error occurred"}`.  
- **Success Criteria:**  
  Generic error message returned gracefully, no stack trace leaks.

### Local Dependencies & Provisioning Tests

**T-Provider-Local-Check-001: Missing Local Binary**  
- **Purpose:**  
  If `adb` or another local binary is expected, test how code responds if binary not found (mock check returns false).  
- **Strategy:**  
  Mock a method `check_local_binaries()` to return failure for `adb`.  
- **Tested Objects:**  
  Initialization logic or first emulator request.  
- **Steps:**  
  1. Simulate a call to `/emulator/run_app`  
  2. With `adb` missing, expect error JSON `{"status":"error","error":"ADB not found"}`.  
- **Success Criteria:**  
  Proper error message indicates missing dependency.

### Logging and Debugging Tests

**T-Provider-Logging-001: Logging on Error Scenario**  
- **Purpose:**  
  Check that inducing an error (e.g., LLM mock timeout) triggers appropriate logging calls.  
- **Strategy:**  
  Patch logger and ensure `logger.error()` is called with error details.  
- **Tested Objects:**  
  Logging statements inside error handling code paths.  
- **Steps:**  
  1. POST `{"prompt":"Hello"}` to `/llm/chat_complete` with LLM mock returning error.  
  2. Verify `logger.error()` called with "LLM service unavailable" or similar text.  
- **Success Criteria:**  
  Error is logged as expected, aiding future debugging.

### Preparation for Integration Tests

By thoroughly covering all logic paths here, we ensure that when integration tests run with real Ollama, real sandbox and emulator instances, most fundamental logic issues are already resolved. Integration tests will thus focus on verifying actual external interactions, performance, and stability under realistic conditions.

## 7. Integration Test Plan and Test Cases

While unit tests ensure the internal logic of the Providers subsystem is correct in isolation, **integration tests** validate the subsystem’s behavior under realistic conditions—interacting with actual external services and infrastructure provisioned by Terraform. These tests run later in the development cycle, once the environment can replicate production-like scenarios. By verifying that the Providers subsystem works correctly with a live Ollama LLM, real sandbox instances, and real emulator containers, integration tests confirm that all components harmonize as intended.

### Objectives of Integration Testing

1. **Realistic Interaction:**  
   Integration tests connect to a running Ollama LLM service (at `http://localhost:11434`) and to sandbox/emulator instances created by Terraform. This means no mocks for external calls—responses come from actual services.

2. **Full Data Flows:**  
   These tests ensure that requests sent to Providers endpoints (`/llm/chat_complete`, `/sandbox/run_file`, `/emulator/run_app`, etc.) not only reach the correct external services but that the returned data is processed correctly and reflected accurately in Providers’ JSON responses.

3. **Error Handling Under Real Conditions:**  
   Integration tests also simulate partial failures, like temporarily stopping Ollama or providing a known-bad file to the sandbox. The subsystem should handle these scenarios gracefully, returning structured fallback errors.

4. **Scalability & Provisioning Validation:**  
   When Terraform provisioning creates multiple sandbox or emulator instances, integration tests confirm the Providers subsystem can discover and utilize them without code changes—just by reading configuration or a registry of endpoints.

### Test Environment and Prerequisites

- **Ollama Service Running:**  
  `docker compose up ollama` at the project root must be running. Ollama should have models loaded or accessible so that LLM queries produce meaningful responses.

- **Terraform Provisioning Applied:**  
  `provisioner.py apply --sandboxes=N --emulators=M` must be run before tests. This ensures a known number of sandbox and emulator instances are available. The Providers subsystem reads their endpoints from a registry or config file output by `provisioner.py`.

- **Providers Container Running:**  
  `make run-providers` or an equivalent command starts the providers subsystem in normal mode (no mocks). The `/health` endpoint should reflect actual states of LLM/sandbox/emulator.

### Strategies

1. **No Mocks for External Calls:**  
   Integration tests rely on real endpoints. LLM prompts are actually sent to Ollama, files are actually posted to a real sandbox instance, and real emulator containers are instructed to run an app. If any external component is down, the test checks if the providers subsystem returns a graceful error.

2. **Varied Scenarios:**  
   Tests cover:
   - Normal operations with valid inputs.
   - Edge cases like large prompts, suspicious files, non-existent apps.
   - Failure scenarios where we stop Ollama or remove a sandbox instance mid-test and confirm fallback behavior.
   - Scaling scenarios with multiple sandbox/emulator instances, ensuring the subsystem can choose any available instance.

3. **Data Integrity Checks:**
   Integration tests verify that the returned JSON matches expected formats and that certain fields (like `response` from LLM, `logs` from sandbox, or `events`/`visuals` from emulator) look plausible. While exact responses might vary, tests can check for required fields (e.g., `response` key in LLM output, `logs` array for sandbox).

4. **Timing & Performance Considerations (Optional):**
   Though not a strict focus, if performance is a concern, integration tests might measure response times to ensure no severe delays in normal scenarios.

### Test Naming and File Organization

- **Test Filenames:**
  - `test_integration_llm.py` for LLM-related integration tests.
  - `test_integration_sandbox.py` for sandbox file analysis integration tests.
  - `test_integration_emulator.py` for emulator-based app tests.
  - `test_integration_scaling_fallback.py` for scenarios testing multiple instances and fallback.

- **Test Function Names:**
  Similar to unit tests, use `test_{scenario}_{condition}`. For example:
  - `test_llm_chat_complete_real_response`
  - `test_sandbox_run_file_malware_detected`
  - `test_emulator_run_app_real_visuals`
  - `test_llm_service_down_fallback_integration`

## Full Integration Test List

Below is the comprehensive list of **integration test cases** for the Providers subsystem. Each test case follows the format: T-... number, Purpose, Strategy, Tested Objects, Steps, and Success Criteria. These integration tests assume that external services (Ollama LLM, sandbox instances, emulator instances) are running and accessible, and that Terraform provisioning has been applied where necessary.

### LLM Integration Tests

**T-Provider-LLM-Integr-001: Real LLM Prompt Interpretation**  
- **Purpose:**  
  Verify `/llm/chat_complete` returns a meaningful response from a running Ollama instance (no mocks).  
- **Strategy:**  
  With Ollama up and loaded with models, send a real prompt and check if the response is plausible.  
- **Tested Objects:**  
  `/llm/chat_complete` endpoint, `llm_client` making real calls to Ollama.  
- **Steps:**  
  1. Ensure Ollama is running (`docker compose up ollama`).  
  2. POST `{"prompt":"Why is the sky blue?"}` to `/llm/chat_complete`.  
  3. Expect HTTP 200, `{"status":"success","response":"Rayleigh scattering..."}` or a similar natural language explanation.  
- **Success Criteria:**  
  The response includes a coherent, human-like explanation, proving real LLM interaction.

**T-Provider-LLM-Integr-002: LLM Failure Fallback**  
- **Purpose:**  
  Check fallback logic when Ollama is unreachable or stopped mid-test.  
- **Strategy:**  
  Temporarily stop Ollama or block its port, then send a request.  
- **Tested Objects:**  
  LLM fallback logic in `/llm/chat_complete`.  
- **Steps:**  
  1. Stop Ollama container.  
  2. POST `{"prompt":"hello"}` to `/llm/chat_complete`.  
  3. Expect HTTP 503, `{"status":"error","error":"LLM service unavailable"}`.  
- **Success Criteria:**  
  Returns a graceful error message consistent with fallback expectations.

### Sandbox Integration Tests

**T-Provider-Sandbox-Integr-001: Safe File Analysis**  
- **Purpose:**  
  Ensure `/sandbox/run_file` handles a benign file correctly with a real sandbox instance provisioned by Terraform.  
- **Strategy:**  
  Terraform creates `sandbox1`. Post a known safe file and confirm logs reflect no malicious actions.  
- **Tested Objects:**  
  `/sandbox/run_file` endpoint, actual sandbox connectivity.  
- **Steps:**  
  1. Confirm sandbox endpoint (e.g., `http://sandbox1:8002`) is reachable.  
  2. POST `{"file_ref":"safe_test.bin"}` to `/sandbox/run_file`.  
  3. Expect HTTP 200, `{"status":"success","logs":["no suspicious activity"]}`.  
- **Success Criteria:**  
  Logs show benign behavior, ensuring correct real sandbox interaction.

**T-Provider-Sandbox-Integr-002: Suspicious File Detection**  
- **Purpose:**  
  Test how `/sandbox/run_file` reacts to a known malicious file.  
- **Strategy:**  
  Provide a test file that triggers suspicious logs in the real sandbox.  
- **Tested Objects:**  
  `/sandbox/run_file` endpoint with actual sandbox.  
- **Steps:**  
  1. POST `{"file_ref":"malware_test.bin"}`.  
  2. Expect HTTP 200, `{"status":"success","logs":["suspicious syscall","..."]}` indicating malicious behavior.  
- **Success Criteria:**  
  Logs confirm malicious signs, proving correct real sandbox usage.

### Emulator Integration Tests

**T-Provider-Emu-Integr-001: Real Emulator App Run**  
- **Purpose:**  
  Validate `/emulator/run_app` can run a test app on a real Terraform-provisioned emulator.  
- **Strategy:**  
  After provisioning an emulator instance (e.g., `emulator1`), run a known app and expect actual events and visuals.  
- **Tested Objects:**  
  `/emulator/run_app` endpoint, `emulator_env` logic, real emulator instance.  
- **Steps:**  
  1. POST `{"app_ref":"test_app.apk"}` to `/emulator/run_app`.  
  2. Expect HTTP 200, `{"status":"success","visuals":{"img":"..."},"events":["click","scroll"]}`.  
- **Success Criteria:**  
  Real emulator returns plausible events and a screenshot, confirming functional emulator integration.

**T-Provider-Emu-Integr-002: VNC Link Check**  
- **Purpose:**  
  After running an app, `/{task_id}/vnc` should return a valid VNC URL for real emulator instance.  
- **Strategy:**  
  Reuse the `task_id` from T-Provider-Emu-Integr-001’s response and query VNC link.  
- **Tested Objects:**  
  `/{task_id}/vnc` endpoint with real emulator.  
- **Steps:**  
  1. From previous test, get `task_id`.  
  2. GET `/{task_id}/vnc`.  
  3. Expect HTTP 200 and `{"status":"success","vnc_url":"vnc://HOST:5900"}`.  
- **Success Criteria:**  
  VNC URL is returned, verifying correct emulator environment and Providers’ knowledge of emulator endpoints.

### Health, Scalability, and Error Handling Integration Tests

**T-Provider-Health-Integr-001: Health Check with Real Resources**  
- **Purpose:**  
  Confirm `/health` accurately reflects real LLM, sandbox, and emulator states.  
- **Strategy:**  
  All services running. Check `/health`.  
- **Tested Objects:**  
  `/health` endpoint with actual environment.  
- **Steps:**  
  1. Ensure Ollama, sandbox(es), emulator(s) are active.  
  2. GET `/health`.  
  3. Expect `{"status":"ok","details":{"llm":"ok","sandbox":"ok","emulator":"ok"}}` or show “error” if a resource is down.  
- **Success Criteria:**  
  Matches real states, no mocks, confirming environment-aware health checks.

**T-Provider-Scaling-Integr-001: Multiple Instances Scenario**  
- **Purpose:**  
  Validate that when multiple sandbox/emulator instances are provisioned, Providers subsystem can use any of them.  
- **Strategy:**  
  Terraform creates multiple instances. `/health` or a request to `/sandbox/run_file` and `/emulator/run_app` confirm it can pick any available instance automatically.  
- **Tested Objects:**  
  Instance selection logic, `/health` endpoint.  
- **Steps:**  
  1. Provision 2 sandboxes, 2 emulators.  
  2. GET `/health` shows multiple "ok" resources.  
  3. POST a file to `/sandbox/run_file`, check success from one instance.  
  4. POST an app request to `/emulator/run_app`, check success from one emulator.  
- **Success Criteria:**  
  Requests succeed, proving the subsystem uses provisioned instances without code changes.

**T-Provider-Error-Integr-001: Invalid Input in Real Environment**  
- **Purpose:**  
  Confirm input validation errors remain correct with real services running.  
- **Strategy:**  
  Send malformed JSON to `/llm/chat_complete` while Ollama is available.  
- **Tested Objects:**  
  Input validation with real environment.  
- **Steps:**  
  1. POST `{}` to `/llm/chat_complete` (missing `prompt`).  
  2. Expect HTTP 400, `{"status":"error","error":"Missing 'prompt' field"}`.  
- **Success Criteria:**  
  Error response consistent with unit tests, even in real environment.

**T-Provider-Fallback-Integr-001: External Service Down**  
- **Purpose:**  
  Simulate a sandbox/emulator downtime and confirm fallback error.  
- **Strategy:**  
  Stop or block one sandbox instance. Attempt `/sandbox/run_file`.  
- **Tested Objects:**  
  Fallback logic in a real scenario.  
- **Steps:**  
  1. Disable sandbox1 endpoint.  
  2. POST `{"file_ref":"safe.bin"}` to `/sandbox/run_file`.  
  3. Expect `{"status":"error","error":"Sandbox unavailable"}` and a suitable HTTP error code (503).  
- **Success Criteria:**  
  Graceful error message matches expectations from fallback tests at unit level.

This full list of integration test cases ensures that, once the Providers subsystem is deployed with real LLM, sandbox, and emulator resources, every critical scenario—normal operations, scaling, fallback, error handling, and input validation—works as intended. By running these integration tests after unit tests pass, we confirm that no fundamental logic issues remain and that the subsystem can handle realistic workloads and configurations.

### Additional Notes

- Integration tests may rely on environment variables or config files that store actual endpoints from Terraform outputs.
- If logs are accessible, advanced integration tests can check that certain errors appear in logs. Otherwise, confirm error JSON suffices.
- Integration tests should run after unit tests pass, ensuring stable internal logic before testing real scenarios.

By covering these integration tests in detail, we guarantee that once the Providers subsystem is deployed in a realistic environment, all functionalities perform as expected—even when faced with real data, real model responses, and scaled-out sandbox/emulator instances.

## 8. Test Execution and Environment Setup

This section describes how to set up the environment for executing the tests—both unit and integration—and the sequence in which tests should run. It also covers tools and configurations necessary to replicate these conditions reliably.

### Tools and Frameworks

- **Programming Language and Test Framework:**  
  Python with `pytest` is used for both unit and integration tests. `pytest`’s fixtures, markers, and parallelization options simplify test structure.
  
- **Mocking and Patching:**  
  `unittest.mock.patch` or `pytest`-based mocking tools replace external calls with simulated responses in unit tests.
  
- **HTTP Testing Utilities:**  
  FastAPI’s TestClient or `requests` library used to call endpoints. For integration tests, `requests` is employed against the deployed services.

- **Logging and Debugging:**  
  Python’s `logging` module to capture logs. Integration tests rely on environment logs or dedicated log endpoints if available.

### Environment Setup

1. **Unit Test Environment:**
   - No external dependencies required.  
   - Run `make test-unit-providers` or `pytest providers/unit_tests/` after installing dependencies from `requirements.txt`.
   - Mocks ensure stable, repeatable tests.

2. **Integration Test Environment:**
   - **Ollama LLM:** Start with `docker compose up ollama` at project root. Confirm it’s responding at `http://localhost:11434`.
   - **Terraform Provisioning:** Run `provisioner.py apply` to create sandbox and emulator instances. Confirm generated endpoints in a registry file (e.g., `instances.json`).
   - **Providers Service:** Start with `make run-providers` or `docker compose up providers` ensuring `/health` returns `ok` states once external services are ready.
   - Execute `pytest providers/integration_tests/` or `make test-providers` (if combined) after confirming all services are active.

### Execution Order and Dependencies

- **Recommended Order:**
  1. **Unit Tests First:** Validate internal logic in isolation. If unit tests fail, fix those issues before integration tests.
  2. **Integration Tests Next:** Once unit tests pass, start all external services and run integration tests to confirm end-to-end behavior.

- **Parallelization:**
  - Unit tests can run in parallel safely since they are isolated and mocked.
  - Integration tests may run sequentially if environment resources are limited. If parallelizing, ensure no race conditions (e.g., two tests modifying the same Terraform state).

### Test Data Management

- **Unit Tests:**  
  Mostly hardcoded or mock data. No persistent storage needed.
  
- **Integration Tests:**  
  May involve test files (like `safe_test.bin`, `malware_test.bin`), placed in a known directory accessible by `providers`.
  Ensure Terraformed resources do not contain sensitive data and are destroyed after tests if not needed.

**Success Criteria:**
A stable, repeatable testing environment that developers can spin up locally, run tests, and teardown without side effects. Pass rates and clear error messages guide debugging.

---

## 9. Reporting, Metrics, and Traceability

This section describes how test results are reported, what metrics are tracked, and how we maintain traceability from requirements to tests.

### Reporting

- **Command-Line Output:**  
  `pytest` outputs results to console. On CI/CD, logs are captured in build artifacts. Developers read pass/fail summaries, plus any error traceback.

- **HTML/JSON Reports:**  
  Optional `pytest` plugins (e.g., `pytest-html`, `pytest-json`) can generate HTML or JSON reports for easier sharing and archiving of results. This helps when comparing test runs over time.

- **CI/CD Integration:**
  If integrated with a CI system (e.g., GitHub Actions, GitLab CI), results can appear directly in pull requests or pipeline logs, ensuring quality checks before merging code.

### Metrics Tracked

- **Pass/Fail Rates:**  
  The number of passing vs. failing tests. Over time, stable pass rates indicate maturity and code stability.

- **Coverage Metrics (Optional):**  
  If using coverage tools, track percentage of code covered by unit tests. Aim for high coverage in critical logic areas.

- **Regression Counts:**  
  If a previously passing test fails after changes, it indicates a regression. Keeping track of regressions helps monitor code quality over time.

### Traceability

- **UC-REQ-FEAT-TEST Mapping:**  
  The tables established earlier serve as a traceability matrix. Each requirement and use case can be traced to specific test cases. If a requirement changes, we know which tests to update.

- **RVM and UC Mapping:**  
  The Requirements Verification Matrix and UC-REQ-FEAT-TEST mappings ensure no requirement goes untested. During reporting, if a test fails, we know which requirement might be at risk.

**Success Criteria:**
Clear and accessible test reports, coupled with coverage and regression metrics, provide stakeholders a transparent view of progress and quality. Perfect traceability from requirements to tests ensures changes are managed efficiently.

---

## 10. Risks, Contingencies, and Assumptions

Despite careful planning, certain risks may affect test execution or interpretation.

### Risks

1. **External Service Unavailability:**  
   If Ollama or Terraformed instances are down, integration tests fail. Mitigation: Run integration tests only after verifying services are ready. If needed, mock certain critical calls or re-run tests once services recover.

2. **Flaky Tests Due to Timing Issues:**  
   Network latencies or slow sandbox/emulator responses can cause intermittent test failures. Mitigation: Increase timeouts, add retries for known flaky endpoints, or monitor performance logs to adjust environment resources.

3. **Configuration Drift:**
   Changes in Terraform scripts or Ollama models could break integration tests. Mitigation: Keep test environment configs versioned and stable. Document any known good state for tests.

4. **Complex Error Diagnostics:**
   If a test fails at integration level, debugging can be hard due to multiple moving parts (LLM, sandbox, emulator). Mitigation: Good logging in code, separate logs from each service, and stepwise approach—start from unit tests upward.

### Contingencies

- If environment setup (Terraform apply) fails, skip integration tests and fix provisioning issues first.
- If Ollama lacks certain models needed, load a default model known to produce stable responses for tests.

### Assumptions

- Ollama models and sandbox/emulator test configurations are stable. No frequent changes to endpoints or responses that would break test expectations.
- Developers have permissions to run Terraform, Docker, and other tools on their machine.
- The test data (like test files for sandbox or app references for emulator) are known and unchanging.

**Success Criteria:**
Risk mitigation strategies in place. Document known flakiness and have fallback options. Assume stable baseline environment and re-check all assumptions if tests unexpectedly fail.

---

## 11. Maintenance and Future Enhancements

Tests are living artifacts that evolve with the codebase. When new features are added or requirements change, tests must adapt accordingly.

### Maintenance Strategies

- **Regular Review:**  
  Periodically review test cases to ensure relevance, remove outdated scenarios, and fill any new coverage gaps.
  
- **Refactoring Tests:**  
  If code structure changes, refactor tests to maintain clarity and reduce duplication. Utilize shared fixtures or utility functions for common test setups.

- **Continuous Integration:**
  Running tests on every commit or merge request ensures that defects are caught early, and no regression slips into production. This encourages a test-driven or at least test-first mentality for new features.

### Future Enhancements

- **Performance Testing:**  
  If non-functional requirements expand to performance or load testing, consider adding a separate suite of tests with realistic throughput scenarios.

- **Security and Penetration Testing:**
  If security requirements rise, add specific tests focusing on sandbox or emulator endpoints for potential vulnerabilities.

- **Broader Coverage on Scaling:**
  As WOPA grows, scaling tests may evolve into more complex scenarios (hundreds of sandbox/emulator instances). Consider automated scaling tests integrated with CI/CD pipelines.

**Success Criteria:**
A flexible testing infrastructure that easily incorporates new tests, updates existing ones, and keeps pace with product evolution, ensuring consistent high-quality delivery.

---

## 12. Conclusion

This test plan provides a comprehensive roadmap for ensuring that the Providers subsystem of the WOPA environment functions correctly, both in isolation (unit tests) and integrated with real external services (integration tests).

- We started by defining the subsystem’s purpose and key functionalities.
- Established clear traceability from requirements and use cases to test cases.
- Detailed unit tests to catch internal logic errors early.
- Prepared integration tests for end-to-end validation with actual LLM, sandbox, and emulator instances.
- Outlined tools, environment setups, reporting methods, risk mitigations, and maintenance strategies to keep tests effective and relevant over time.

By following this test plan, developers, QA engineers, and stakeholders gain confidence that the Providers subsystem meets WOPA’s standards for functionality, reliability, and scalability. Tests ensure immediate feedback on changes, support rapid iteration, and maintain overall system quality.

**End of Test Plan Document**
