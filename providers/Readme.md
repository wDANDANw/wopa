# WOPA (Intelligent Chat Safeguarder) - Providers Subsystem

## Introduction

This repository hosts a subsystem of WOPA, an Intelligent Chat Safeguarder project designed to protect mobile environments and messaging ecosystems from malicious content. The **Providers Subsystem** specifically deals with bridging WOPA’s core logic to local and provisioned services:
- **LLM-Based Text Analysis (Ollama)**
- **Sandbox Environment for Suspicious Files (Cuckoo Sandbox)**
- **Android Emulator Integration (docker-android)**

By organizing these capabilities into a cohesive unit, the Providers Subsystem ensures that WOPA’s main backend can reliably and consistently leverage external resources to analyze URLs, detect malicious files, simulate app behaviors, and provide cultural synergy.

## Project Structure

```text
.
├─ providers/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  ├─ provider_server.py
│  ├─ entrypoint.sh
│  ├─ config.yaml
│  ├─ provisioner.py
│  ├─ instances.json
│  ├─ admin_ui/
│  │  ├─ __init__.py
│  │  ├─ gradio_dashboard.py
│  │  
│  ├─ api/
│  │  ├─ __init__.py
│  │  ├─ routes_llm.py
│  │  ├─ routes_sandbox.py
│  │  ├─ routes_emulator.py
│  │  ├─ routes_health.py
│  │  ├─ routes_admin.py
│  │  ├─ routes_vnc.py
│  │  
│  ├─ core/
│  │  ├─ __init__.py
│  │  ├─ llm_client.py
│  │  ├─ sandbox_env.py
│  │  ├─ emulator_env.py
│  │  └─ manager.py
│  │  
│  ├─ utils/
│  │  ├─ __init__.py
│  │  └─ config_loader.py
│  │  
│  ├─ test_data/
│  │  ├─ safe_test.bin
│  │  ├─ malware_test.bin
│  │  └─ test_app.apk
│  │  
│  ├─ unit_tests/
│  │  ├─ __init__.py
│  │  ├─ test_endpoints.py
│  │  ├─ test_manager_workers.py
│  │  ├─ test_validation_and_logging.py
│  │  └─ test_local_checks.py
│  │
│  └─ integration_tests/
│     ├─ __init__.py
│     ├─ test_integration_llm.py
│     ├─ test_integration_sandbox.py
│     ├─ test_integration_emulator.py
│     ├─ test_integration_scaling_fallback.py
│     ├─ test_integration_health.py
│     ├─ test_integration_error_handling.py
│     └─ test_integration_admin_ui.py
│  
└─ readme.md (this file)
Key Directories:

api/: Defines FastAPI endpoints for LLM, Sandbox, Emulator, Health checks, Admin, and VNC services.
core/: Houses logic for LLMClient (llm_client.py), sandbox integration (sandbox_env.py), emulator integration (emulator_env.py), and a manager orchestrator (manager.py).
utils/: Contains configuration loading utilities (config_loader.py) and package initializations.
test_data/: Binary test artifacts for sandbox and emulator integration tests.
unit_tests/ and integration_tests/: Organized test suites to verify correctness at different levels.
Prerequisites
Python 3.10+
FastAPI & Uvicorn: For running the provider_server.py.
Requests & PyYAML: For HTTP calls and configuration loading.
LLM (Ollama), Sandbox (Cuckoo), Emulator (docker-android): Properly installed, configured, and endpoints accessible.
Check requirements.txt for a full list of Python dependencies.

Setup & Configuration
Install dependencies:

bash
Copy code
pip install -r providers/requirements.txt
Prepare config.yaml and instances.json:

config.yaml: Provide llm.endpoint, sandbox.endpoints or rely on instances.json.
instances.json: Created or updated by provisioner.py after Terraform runs. It lists dynamically provisioned endpoints for sandbox and emulator.
Run the Provider Server:

bash
Copy code
cd providers
MODE=run uvicorn provider_server:app --host 0.0.0.0 --port 8001
Or using entrypoint.sh in a Docker container:

bash
Copy code
docker compose up providers
Accessing Endpoints: Check /admin/endpoints or /health to see what’s available and verify that LLM, sandbox, emulator services are reachable.

Testing
The project includes both unit and integration tests:

Unit Tests: Focus on isolated code logic with mocks, located in providers/unit_tests.

bash
Copy code
cd providers
MODE=test TEST_MODE=unit pytest --maxfail=1 --disable-warnings -q
Integration Tests: Validate end-to-end interactions with actual sandbox/emulator endpoints in providers/integration_tests.

bash
Copy code
cd providers
MODE=test TEST_MODE=integration pytest --maxfail=1 --disable-warnings -q tests/integration
Ensure that the LLM, sandbox, and emulator services are running or endpoints are available as expected. instances.json should reflect current provisioning.

Maintainers & Contributions
Maintaining Code:
Follow the architectural approach where core/ holds logic, api/ defines endpoints, and utils/ provides helpers. Keep test_data/ stable so tests remain consistent.

Contributions:
Ensure PRs pass all unit and integration tests. Update or add test samples in test_data/ if adding new scenarios. Document new endpoints in readme.md and admin/endpoints.

Logging & Error Handling:
Most logic raises exceptions on errors. Consider logging improvements or adding a global error handler in provider_server.py to standardize JSON error responses.

Future Directions
Scalability:
Add load balancing or health checks in manager.py or sandbox_env.py and emulator_env.py.
Security Enhancements:
Implement auth on /admin/ endpoints or secure instances.json and config.yaml if sensitive.
Conclusion
The Providers Subsystem integrates external services—LLM, sandbox, emulator—into WOPA’s environment. With robust configurations, clear endpoints, and comprehensive testing, it ensures that WOPA can reliably analyze content, detect threats, and simulate app behaviors. Use readme.md and the /admin/endpoints route to discover current capabilities and guide further development.