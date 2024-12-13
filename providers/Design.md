Design Decisions Outline
Note: The Design Decisions Outline previously mentioned consisted of four main sections. Here, we will focus on delivering Section 1 and Section 2 in a comprehensive, detailed, and user-friendly manner, ensuring that newcomers, even with minimal technical background, can understand the choices made and their reasoning. No extraneous philosophies or complexities—just clear explanations and a down-to-earth technical rationale.

1. Technology Choices
When building the Providers subsystem, we faced a number of technology options. Our primary goals were stability, local execution, and straightforward integration with the rest of the system. We wanted tools that would run well inside containers, be simple to scale, and not complicate our internal dataflows. Below are the main decisions:

a. Programming Language and Environment:

Python 3.10-slim:
We chose Python for its extensive ecosystem, readability, and ease of writing asynchronous and networked code. The slim variant of the Python image reduces unnecessary overhead, making images smaller and faster to build.
No Version Pinning in Dependencies:
We intentionally avoided pinning specific library versions in requirements.txt for this PoC (Proof-of-Concept). This makes setup simpler and more flexible. In a long-term production scenario, pinning might be added to improve reproducibility.
b. Core Frameworks and Libraries:

FastAPI:
The Providers subsystem uses FastAPI in provider_server.py to create internal endpoints (like /health). FastAPI’s speed, straightforward syntax, and data validation capabilities make it ideal for building small, internal APIs.
Requests / HTTPX:
To interact with external endpoints—like the Ollama LLM service or Cuckoo Sandbox APIs—we use HTTP clients (requests or httpx) that are well-known, stable, and easy to mock in tests.
Gradio:
For the admin UI panel, Gradio offers a quick way to build a minimal local web interface without needing heavy front-end code. This is ideal for a PoC, allowing developers to visualize provider health and endpoints in a few lines of Python.
c. Chosen Providers:

Ollama for LLM:
Ollama is a local language model solution that can run right on the same machine as the Providers subsystem. This reduces complexity, avoids depending on remote third-party APIs, and makes prompt-response cycles fast and self-contained.
Cuckoo Sandbox for File Analysis:
Cuckoo is a known name in malware analysis. Running it locally (in a container) gives us the power to analyze suspicious files in isolation. Since we plan for potential scaling with Terraform, this fits well—Cuckoo instances can be multiplied if needed.
docker-android for App Emulation:
Emulating Android devices inside containers is simplified by docker-android. It provides ADB (Android Debug Bridge) and VNC access, letting us script interactions and even visually inspect what’s happening inside the emulator without requiring separate hardware or complex setup.
d. Infrastructure & Provisioning Tools:

Terraform:
Chosen to manage the dynamic provisioning of additional sandbox or emulator instances. Terraform’s Infrastructure-as-Code approach means scaling and changes are tracked and reversible. Developers can easily define how many instances they want and run a single command to achieve the desired state.
Summary of Technology Choices:
We picked a tech stack that’s local, container-friendly, and easy to integrate and scale. Python + FastAPI + Terraform + local providers (Ollama, Cuckoo, docker-android) keep complexity low and adaptability high—perfect for a subsystem whose job is to serve internal requests only and evolve as our PoC grows.

2. Deployment & Containerization
The Providers subsystem is fully containerized. This ensures consistency and portability, allowing the entire environment to run identically on different machines. Newcomers can spin up the subsystem using simple commands without installing a host of local dependencies, and they can easily run tests or production modes by flipping an environment variable.

a. Docker and Docker Compose:

We use Docker to build images that encapsulate our Python environment, code, and dependencies.
docker-compose.yml orchestrates multiple services—like the providers container, plus optional local services such as local-llm or android-emulator containers if defined.
With Docker Compose, make run-providers can start everything at once. This is especially handy for a PoC, where simplicity matters and rapid iteration is needed.
b. The Providers Docker Image:

WORKDIR /providers:
The Dockerfile sets the working directory to /providers so that code, configs, and scripts remain neatly localized.
ENTRYPOINT and entrypoint.sh:
Instead of hardcoding a single command, we rely on an environment variable (MODE) and entrypoint.sh to decide whether to run uvicorn (for the provider_server) or pytest (for unit tests). This flexibility makes testing and running seamless.
No Complex Build Stages in PoC:
For a PoC, our Dockerfile remains straightforward: install dependencies, copy code, and run. If future optimizations are needed, multi-stage builds could be introduced.
c. Running the Subsystem:

Normal Mode (Production-like):
make run-providers sets MODE=run and starts uvicorn provider_server:create_internal_api. Now /health and other internal endpoints are live.
Test Mode (Unit Tests):
make test-unit-providers sets MODE=unit-test, causing entrypoint.sh to run pytest instead of uvicorn. This ensures that tests run inside the same container environment as production, eliminating “works on my machine” issues.
d. Additional Services:

If the PoC requires external tools (e.g., local-llm container or docker-android emulator containers), docker-compose.yml can define these as services. Starting the entire environment becomes as easy as docker compose up providers.
Terraform provisioning results in changes to infrastructure that can be integrated into the same network. The providers container can then see newly created containers on the same Docker network.
Summary of Deployment & Containerization: All code runs inside containers, ensuring uniformity. Switching between normal operation and testing is simple and fast—just change MODE. Dependency services like ollama, cuckoo, or android-emulator are run as separate containers, orchestrated by docker-compose.yml. Terraform can layer on top to add more instances dynamically. This approach gives newcomers a smooth and predictable environment to work in, removing friction and complexity.

3. Configuration & Extensibility
In a dynamic and evolving environment like this PoC subsystem, configuration and the ability to extend or modify functionality easily are key. We want new developers to be able to tweak settings, add features, or integrate new providers without wrestling a hydra of hidden defaults or rigid code structures.

a. Centralized Configuration via config.yaml:

The config/ directory includes a config.yaml file holding parameters like default LLM endpoint host/port, the number of default sandbox instances, emulator image names, or timeouts.
Instead of scattering these values throughout multiple Python files, we store them centrally. This ensures that changing a port number or enabling a fallback mechanism is as simple as editing a YAML value.
The utils/config_loader.py reads config.yaml and provides simple methods (get_config() and get_nested_config()) to fetch these values. This means no hardcoded constants in the main code paths—just a clean call to config_loader.py.
b. Constants for Shared Values:

utils/constants.py stores universal constants like DEFAULT_SANDBOX_TIMEOUT or DEFAULT_LLM_MODEL. This reduces duplication, allowing all parts of the codebase to rely on a single source of truth for these fundamental parameters.
If a developer decides that the LLM model name should change or timeouts need adjusting, they update it here. That single modification permeates the codebase immediately, making maintenance painless.
c. Adding or Changing Providers:

Suppose a future scenario where we need a second LLM provider or a different sandbox tool. With the current structure:
Create a new directory, say my_new_provider/, mimic the pattern of llm_provider/ or sandbox_provider/ by having a main class (e.g., my_new_provider_env.py).
Add provisioning logic in terraform/ for this new provider type if scaling is needed. Then update provisioner.py to handle those new terraform resources.
Adjust provider_server.py or the internal logic to reference the new provider’s endpoints or health checks.
By following established patterns, new providers can fit into the existing structure without tearing down what’s already built.
d. Adjusting Dataflows and Endpoints:

If we need a new internal endpoint in provider_server.py (e.g., /my_new_provider/status), just add a new FastAPI route. The code is already set up for this pattern, with each endpoint’s logic confined to a short function.
Since ui/gradio_app.py relies on these endpoints for display, if we add a new provider endpoint, we can also show it in the Gradio dashboard by simply calling that endpoint and formatting the results.
Summary for Configuration & Extensibility: All configuration is centralized and easily accessible. Constants are well-defined, and the code is modular enough that adding, removing, or altering providers can be done with minimal friction. New developers or maintainers can confidently join and modify the subsystem without deciphering a labyrinth of hidden settings or magical constants.

4. Testing
Testing is critical to ensure that each change or addition to the Providers subsystem doesn’t break existing functionality. Our approach is simple: thorough unit testing, clear mocking strategies, and environment-independent execution.

a. Unit Testing Only:

This PoC relies on unit tests because it’s focusing on verifying internal logic and ensuring that every provider can handle basic requests, return correct structures, and gracefully handle errors.
No integration tests with the main system or end-to-end tests are included here, as we assume this subsystem’s final integration testing happens at a higher-level system test stage.
b. Pytest & Mocking:

We use pytest as our testing framework. Its straightforward syntax and rich ecosystem of plugins and fixtures make writing and running tests easy.
External dependencies, like HTTP calls to Ollama or Cuckoo APIs, are mocked using unittest.mock. By simulating external responses, we can test logic without requiring a real LLM or sandbox service running.
Each test file focuses on a particular area:
test_llm_client.py checks LLM prompt handling.
test_sandbox_and_emulator.py ensures sandbox and emulator logic handle both success and error cases.
test_provider_server.py verifies that the internal API endpoints return expected responses.
c. Running Tests Inside the Container:

Because we containerized everything, make test-unit-providers runs tests inside the same environment that the code uses in production. This prevents discrepancies between a developer’s local machine and the deployment environment.
If a test fails, the developer can confidently start debugging knowing the conditions match real runtime scenarios.
d. Fail Fast, Report Clearly:

Pytest options like --maxfail=1 let us fail fast on the first error. This is beneficial in a PoC environment where quick iteration matters.
Clear test naming conventions (like test_interpret_success() for LLM) ensure that newcomers can guess what each test checks without reading extensive docs.
e. Future Testing Enhancements:

If the project grows beyond a PoC, we could add integration tests that stand up actual Ollama and Cuckoo containers, run real files, and confirm actual logs. But for now, our unit test approach, relying on mocks and stable interfaces, is both sufficient and efficient.
Summary for Testing: We rely on a focused unit testing approach with mocks, run tests inside containers for consistency, and keep test scenarios clear and representative of real use cases. This ensures developers can confidently change code and quickly catch regressions without guesswork or complicated setups.

