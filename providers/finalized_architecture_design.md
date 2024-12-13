1. Introduction
Welcome to the Providers subsystem of this Proof-of-Concept (PoC) project, a small but crucial internal part of our larger system. Think of this subsystem as a friendly backstage crew working tirelessly to ensure that other parts of the show (like the main backend and user-facing interfaces) receive the specialized services they need. Here, we do not aim to run solo—this module is strictly for use within the parent system. No rogue standalone usage allowed!

The Providers subsystem supplies three major capabilities:

LLM Inference via a local model endpoint (Ollama), so that your texts can be quickly and intelligently analyzed.
Sandbox File Analysis using a local Cuckoo Sandbox, ensuring suspicious files are examined and any malicious behaviors detected.
Mobile App Emulation powered by docker-android, enabling dynamic, hands-on testing of mobile apps in a controlled environment to uncover sneaky app tricks.
Our focus is on clarity, minimal configuration fuss, and easy scalability. The files, directories, and tooling are arranged so that new contributors—whether seasoned developers or newcomers with only basic coding knowledge—can quickly understand what’s happening. By sticking to well-defined endpoints, straightforward scripts, and a uniform directory structure, maintainability and adaptability come naturally.

In short, this subsystem is the “private behind-the-scenes toolkit” of the larger architecture. No external adventures. Just good old internal service to help the main platform run smoothly and securely.

2. High-Level Components
At a high level, the Providers subsystem consists of three main provider types plus some supporting utilities. Each provider type handles a distinct class of tasks. All of them are neatly packaged under the providers/ directory, working cooperatively but never straying outside their role as an internal cog in the bigger machine.

Components:

LLM Provider (Ollama):
A local language model that takes text input and returns insightful responses. It’s like a smart textual assistant living right next door. The llm_provider/ directory holds a llm_client.py that sends prompts to a locally running Ollama service. This LLM provider does not depend on remote services, reducing latency and complexity.

Sandbox Provider (Cuckoo Sandbox):
A suspicious file arrives, we pass it into the Cuckoo Sandbox, and out comes a security report. The sandbox_provider/ directory, with its sandbox_env.py, defines how we talk to Cuckoo Sandbox instances. If we need more horsepower (i.e., more sandbox instances), provisioning steps are in place. The sandbox is all about analyzing files in isolation and logging their shady activities before they can do any harm.

Emulator Provider (docker-android):
Need to poke around a mobile app safely? The emulator environment—managed in emulator_provider/emulator_env.py—uses docker-android. We start and manage emulator instances to run and test apps in a secure, contained bubble. We can scale up by adding more emulator containers if demand grows. The emulator also offers a VNC viewer link, making it possible to see what’s happening inside that pretend mobile device.

Supporting Utilities and Configuration:

provider_server.py:
A FastAPI internal server offering /health and other internal endpoints. Think of it as the local control panel that exposes the health status of LLM, sandbox, and emulator. It does not serve external clients directly—just our own system.

ui/gradio_app.py:
A simple Gradio-based admin UI dashboard to visualize what’s going on. It shows which providers are up, what endpoints they offer, and helps developers get a quick snapshot of system status.

utils/ directory:
Houses config_loader.py and constants.py. They keep configuration access and fixed values organized, making it easy to tweak settings like timeouts or default ports without rummaging through multiple code files.

terraform/ directory and provisioner.py:
These handle scaling multiple sandbox or emulator instances through automated provisioning. If load spikes or more parallel analysis is needed, run a Terraform command via provisioner.py to spin up extra containers. It’s infrastructure automation to keep things flexible and future-proof.

All these pieces are arranged to ensure that the Providers subsystem remains neat, understandable, and ready for internal-only duties within the larger system. By separating responsibilities clearly and providing straightforward, localizable configuration and provisioning steps, newcomers can easily learn the ropes and contribute with minimal hassle.

3. Internal Architecture
This section zooms into the internal workings of the Providers subsystem, describing how each file and directory interacts, the logic flow within key classes and functions, and how newcomers can quickly navigate and adapt the code.

Core Principles:

Single Responsibility: Each directory and file focuses on a single area—LLM logic in llm_provider/, sandbox logic in sandbox_provider/, emulator logic in emulator_provider/, with overarching coordination and utilities placed in provider_server.py, ui/gradio_app.py, and utils/.
Clear Boundaries: Communication between providers and other parts of the system happens only through stable, well-defined internal endpoints and occasionally through provisioning logic. No hidden side-channels or unclear dependencies.
Easy Mocking & Testing: The code is structured so that external calls (e.g., to Ollama’s LLM endpoint, Cuckoo Sandbox’s APIs, or docker-android’s emulator) occur in isolated methods. This makes unit tests simpler, as these methods can be cleanly mocked.
Directory-by-Directory Internal Overview:

providers/ (Root of Subsystem):

provider_server.py:
Acts as the subsystem’s internal API gateway. It sets up a FastAPI application offering endpoints like /health and /{task_id}/vnc. Other modules (like ui/gradio_app.py or the main system’s backend) can query this server to get the status of LLM, sandbox, and emulator.
Internally, provider_server.py calls helper functions (like check_llm_health(), check_sandbox_health(), check_emulator_health()) that either return hardcoded statuses or query the actual providers. For the VNC endpoint, it may retrieve details from emulator provisioning data (via provisioner.py or a stored registry of instance endpoints).

ui/gradio_app.py:
Implements a small web-based admin dashboard using Gradio. This dashboard calls /health and other internal endpoints to display statuses and available endpoints on a user-friendly page. Internally, gradio_app.py defines functions like get_provider_health() and get_provider_endpoints() that perform requests.get() calls to provider_server.py endpoints, then formats the results for display. No complex logic here—just input/output formatting and a simple Gradio interface.

entrypoint.sh & requirements.txt, Dockerfile:
These files handle containerization and runtime mode selection. entrypoint.sh checks the MODE environment variable:

If MODE=run, it starts the uvicorn server from provider_server.py.
If MODE=unit-test, it runs pytest against unit_tests/.
requirements.txt lists dependencies (e.g., fastapi, pytest, requests, gradio), and Dockerfile builds an image with /providers as WORKDIR.
llm_provider/ directory (Ollama Integration):

llm_client.py:
Contains the LLMClient class. The interpret(prompt) method sends a POST request to the local Ollama LLM endpoint (e.g., http://localhost:9000) with a JSON payload containing the prompt and parameters like max_tokens and temperature.
On success, LLMClient returns a {"status":"success","response":"..."} dictionary. On error, it returns {"status":"error","error":"..."}. This class might include basic retry logic, handle empty prompts by returning an error immediately, and provide a central place to upgrade LLM logic later if needed.
sandbox_provider/ directory (Cuckoo Sandbox Integration):

sandbox_env.py:
Defines SandboxEnvironment class. Its run_file(file_ref) method orchestrates the process of submitting a file to the Cuckoo Sandbox for analysis. It may do the following steps:
Identify an available Cuckoo Sandbox instance from provisioning data.
Upload the file using Cuckoo’s POST /tasks/create/file endpoint.
Poll GET /tasks/view/<task_id> until results are ready.
Parse the returned JSON logs to find suspicious system calls or network actions.
The _execute_sandbox() helper might be replaced with actual Cuckoo API calls, and _parse_sandbox_output() might parse JSON output from Cuckoo’s APIs. For now, these methods are simplified and can be extended as needed.
emulator_provider/ directory (docker-android Integration):

emulator_env.py:
Defines EmulatorEnvironment class. Its run_app(app_reference) method simulates installing and running an Android app on a docker-android emulator instance. Steps may include:
Calling _start_emulator() to ensure the emulator container is running and healthy. If multiple emulators are provisioned, choose one from provisioner.py.
Calling _run_interactions(app_reference) which would ideally install the app via adb commands, simulate user actions, and capture screenshots or logs.
Return a dictionary with "status":"success","visuals":{...},"events":[] describing what happened inside the emulator.
Similar to the sandbox, this logic can be extended or replaced with real adb command calls and advanced test scripts later.
utils/ directory (Configuration & Constants):

config_loader.py:
A ConfigLoader class reads config/config.yaml and provides get_config(name) and get_nested_config() methods. For example, if config.yaml specifies default LLM port or emulator count, config_loader.py makes it easy to retrieve them without hardcoding.
constants.py:
Holds fixed values like DEFAULT_LLM_MODEL, DEFAULT_SANDBOX_TIMEOUT, DEFAULT_EMULATOR_TIMEOUT. This centralization ensures that if default timeouts or model names change, we modify them once here.
config/ directory (YAML Settings):

config.yaml:
Houses YAML configuration for providers. For instance:
yaml
Copy code
llm:
  host: "localhost"
  port: 9000
sandbox:
  default_instances: 1
emulator:
  default_instances: 1
The config_loader.py reads these values, allowing easy scaling and endpoint changes without rewriting code.
terraform/ directory and provisioner.py:

The terraform/ directory contains .tf files that define how to spin up additional sandbox containers or emulator instances. Adjusting variables (like number_of_sandboxes: 2) and running provisioner.py triggers terraform apply, retrieves outputs, and updates a local registry (JSON file or in-memory) of available instances.
provisioner.py might run shell commands like terraform init, terraform apply, and terraform output, parse the output to extract hostnames and ports, and store them so that sandbox_env.py or emulator_env.py can pick a free instance at runtime.
unit_tests/ directory:
Contains test files test_provider_server.py, test_llm_client.py, and test_sandbox_and_emulator.py. Each test file isolates a component, mocks external HTTP calls, and checks results. This directory ensures that as we refactor or add features, we can confidently run make test-unit-providers and see if anything broke.

Internal Communication Patterns:

provider_server.py ↔ llm_client.py, sandbox_env.py, emulator_env.py:
The server may call health check methods or provisioning lookups to answer /health queries or return VNC URLs.
gradio_app.py → provider_server.py:
The admin UI pulls data from the internal API to display in the dashboard.
sandbox_env.py and emulator_env.py ↔ provisioner.py:
Before starting an operation, these classes may invoke provisioner.py logic (or a simple helper function that reads terraform output results) to find an available sandbox/emulator instance.
Extendability:

Adding a new provider (e.g., a new language model or a different sandbox) involves creating a new directory with a similar pattern: a class that handles external API calls, a test file in unit_tests/, and possible Terraform configurations if scaling is required.
Changing an external service (e.g., replacing Ollama with another local model) only requires adjusting llm_client.py and possibly updating config files.
Overall, the internal architecture is straightforward and modular. Each provider type is neatly enclosed, the utilities are central and easy to adjust, and the provisioning is decoupled into Terraform plus a simple Python script. This ensures that even a relative newcomer, after a quick overview, can confidently dive in and start coding, testing, or expanding the functionalities without getting lost in a maze of code.

4. Provisioning and Scaling
This section describes how the Providers subsystem can dynamically expand its capacity for sandbox file analysis and app emulation. Because LLM (Ollama) can typically handle multiple requests at once, it usually doesn’t need multiple instances. However, Cuckoo Sandbox and docker-android emulators are more resource-intensive and may need to scale out.

Key Goals:

Allow running multiple sandbox instances in parallel if the volume of suspicious files grows.
Spin up more emulator containers to simultaneously run and analyze multiple mobile apps.
Simplify scaling operations so that developers can easily adjust capacity without diving into low-level container management.
Terraform & provisioner.py:

Inside providers/terraform/, we define Terraform configuration files (main.tf, variables.tf, outputs.tf) describing how to deploy multiple sandbox and emulator containers. Terraform uses the configuration to consistently create or destroy these resources.
provisioner.py is a Python script acting as a friendly frontend for these Terraform operations. Instead of manually typing terraform commands, one can run python provisioner.py apply --sandboxes=2 --emulators=3 or similar. This command would:
Run terraform init and terraform apply with the specified variables.
On success, run terraform output to retrieve newly assigned endpoints (like sandbox container IPs and ports, emulator ADB and VNC ports).
Store these endpoints, often in a local JSON file or a simple data structure, so that the provider classes (sandbox_env.py, emulator_env.py) can pick a free instance on-demand.
Scaling Process (Step-by-Step):

Adjust Variables: Suppose you need more sandbox instances. You change a variable (e.g., sandbox_count) in terraform/variables.tf or pass it as a command-line argument to provisioner.py.
Run Provisioner: provisioner.py calls terraform apply, which creates or destroys containers as needed.
Update Internal Registry: After apply completes, provisioner.py retrieves endpoints and updates a registry file (like instances.json) mapping each sandbox or emulator container to its unique URLs and ports.
Consume Updated Endpoints: Next time sandbox_env.py calls for a sandbox, it reads from this registry, picks a free sandbox instance endpoint, and interacts with it. The same logic applies for choosing an emulator instance.
Maintainability & Extensibility:

Adding another type of provider is straightforward: create new Terraform resources and add logic in provisioner.py to handle them.
Changing providers (e.g., switching from Cuckoo to another sandbox) involves updating Terraform configs and the relevant code in sandbox_env.py.
Terraform’s infrastructure-as-code approach ensures that scaling changes are versioned and consistent.
By keeping provisioning and scaling separate from the core logic of LLM, sandbox, and emulator classes, we make the system easier to evolve. Terraform handles resource creation, provisioner.py bridges the gap between Terraform and Python, and the provider classes focus solely on their domain tasks.

5. Dataflows (Renamed from previous section name)
Dataflows describe how information moves within the Providers subsystem and how these components interact with each other as well as with the rest of the system. While this subsystem is not designed for standalone use, understanding these flows helps new developers and testers visualize what’s happening under the hood.

High-Level Dataflows:

LLM Requests:

Input: A textual prompt, e.g., “Check this URL.”
Process: The llm_client.py sends a POST request with JSON payload { "prompt":"Check this URL" } to the Ollama endpoint (at http://localhost:9000). The LLM replies with structured JSON.
Output: The interpret() method returns a {"status":"success","response":"..."} or {"status":"error","error":"..."} dict to the caller (e.g., provider_server or a test script).
Sandbox File Analysis:

Input: A file reference (like “malware.bin”) from the main system.
Process: sandbox_env.py chooses an available Cuckoo Sandbox instance endpoint (from the registry updated by provisioner.py). It then:
POSTs the file to /tasks/create/file on Cuckoo’s API.
Polls /tasks/view/<task_id> until the analysis is ready.
Retrieves logs, parses them, and extracts suspicious calls.
Output: A dictionary like {"status":"success","logs":[... suspicious entries ...]} or {"status":"error","error":"..."} if something fails.
Emulator App Analysis:

Input: An app reference (e.g., “test.apk”).
Process: emulator_env.py:
Chooses an emulator instance from the registry (again updated by Terraform outputs).
Ensures the emulator is up and running (_start_emulator()).
Runs interactions (_run_interactions()) via adb commands to simulate user actions.
Captures screenshots and event logs.
Output: {"status":"success","visuals":{...},"events":[...]} or {"status":"error","error":"..."} if emulator fails.
Provider Server & Admin UI Dataflow:

Provider Server (provider_server.py):
Health Check: Calls simple health-check functions or tries basic interactions with providers. Returns JSON summarizing LLM, sandbox, and emulator status.
VNC Link: For /{task_id}/vnc, retrieves a known emulator instance’s VNC URL from the registry and returns it.

Admin UI (ui/gradio_app.py):
Pulls health info and endpoint lists from provider_server.py endpoints using requests.get(). Displays them in a Gradio interface. When a user clicks “Refresh,” the UI calls these endpoints again, updates the displayed info.

Provisioning Dataflow:

provisioner.py runs terraform apply, which communicates with Docker or cloud providers to spawn containers. After applying:
provisioner.py calls terraform output to list newly created instances.
It updates a local registry (in-memory or a JSON file) that sandbox_env.py and emulator_env.py can read at runtime.
This ensures that as soon as we have new sandbox or emulator containers, they become available to handle more tasks without changing code in the provider classes.

Visibility & Debugging:

If issues arise, developers can trace dataflows step-by-step:
Check provider_server.py logs if health endpoints return expected data.
If sandbox analysis fails, check sandbox_env.py logs and provisioner.py output to ensure correct endpoints.
If emulator interactions seem off, verify emulator_env.py steps and adb commands.
Because each step is well-defined and isolated, debugging usually involves checking a few method calls or endpoint responses rather than wading through tangled code paths.
By understanding these dataflows, new contributors can quickly answer questions like: “How does a file get from our main system into the sandbox, and back as a security report?” or “How do we scale up and ensure the emulator provider finds the new instances?” The structured approach and clear data pipelines make this subsystem’s internal logic transparent and approachable.

