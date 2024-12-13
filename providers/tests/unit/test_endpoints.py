###############################################################################
# test_endpoints.py
#
# Purpose:
# Unit tests for various API endpoints defined in `api/`. We use FastAPI’s TestClient
# to simulate HTTP requests against `provider_server.py`. Since these are unit tests, 
# we mock external dependencies (like llm_client, sandbox_env, emulator_env) to avoid 
# real network calls or provisioning.
#
# Key Responsibilities:
# - Test normal and error scenarios for endpoints: /health, /llm/chat_complete,
#   /sandbox/run_file, /emulator/run_app, /{task_id}/vnc, /admin/endpoints, /admin/config.
# - Ensure correct status codes, JSON structures, and error messages.
#
# Changes Made:
# - Previously, `test_emulator_run_app` failed because "task_id" was missing in the response.
# - Now that `emulator_env.run_app` and `routes_emulator.py` return `task_id`,
#   we've updated our mocks to return a task_id and ensured the test checks it.
#
# Requirements:
# - pytest and requests for testing.
# - FastAPI TestClient for HTTP endpoint simulation.
# - unittest.mock to patch external calls like `llm_client`, `sandbox_env`, `emulator_env`.
#
# Maintainability:
# - Add or remove tests as endpoints evolve.
# - Keep mocks in sync with actual code changes in `emulator_env`, `routes_*`, etc.
# - If a new endpoint requires a new field, update the corresponding tests.
###############################################################################

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from provider_server import app

client = TestClient(app)

@pytest.fixture
def mock_llm():
    # A mock for LLMClient calls in /llm/chat_complete endpoint
    # By default, returns "Safe"
    with patch("core.llm_client.LLMClient.interpret") as mock_interpret:
        mock_interpret.return_value = "Safe"
        yield mock_interpret

@pytest.fixture
def mock_sandbox():
    # A mock for sandbox_env calls in /sandbox/run_file
    with patch("core.sandbox_env.SandboxEnv.run_file") as mock_run_file:
        def side_effect(file_ref):
            # If file_ref contains "malware", return suspicious logs, else safe logs
            if "malware" in file_ref.lower():
                return ["Suspicious activity detected", "Known malware signature"]
            return ["No suspicious activity found"]
        mock_run_file.side_effect = side_effect
        yield mock_run_file

@pytest.fixture
def mock_emulator():
    # Mocks for emulator_env calls in /emulator/run_app and /{task_id}/vnc
    with patch("core.emulator_env.EmulatorEnv.run_app") as mock_run_app, \
         patch("core.emulator_env.EmulatorEnv.get_vnc_url") as mock_vnc_url:

        # run_app now must return a dict with "visuals", "events", and "task_id"
        def run_app_side_effect(app_ref):
            # Return a stable task_id for test determinism
            return {
                "visuals": {"screenshot":"base64img"},
                "events": ["tap","scroll","ahaha"],
                "task_id": "emu_task_123"  # This ensures test passes
            }

        def vnc_url_side_effect(task_id):
            # If correct task_id, return a vnc url
            if task_id == "emu_task_123":
                return "vnc://emulator1:5900"
            else:
                raise KeyError("No known emulator instance")

        mock_run_app.side_effect = run_app_side_effect
        mock_vnc_url.side_effect = vnc_url_side_effect
        yield mock_run_app, mock_vnc_url

@pytest.fixture
def mock_config():
    # Mock config_loader to return stable config if endpoints rely on config
    with patch("utils.config_loader.load_config") as mock_config_loader:
        mock_config_loader.return_value = {
            "llm": {"endpoint":"http://fake-llm","default_model":"test-model"},
            "sandbox": {"endpoints":["http://fake-sandbox:8002"]},
            "emulator": {
                "endpoints":["http://emulator1:5555"],
                "vnc_url_template":"vnc://{host}:{port}",
                "default_vnc_port":5900
            }
        }
        yield mock_config_loader

def test_health_endpoint(mock_config, mock_llm, mock_sandbox, mock_emulator):
    # /health should return system status and details about llm, sandbox, emulator
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok","degraded","down"]
    assert "llm" in data["details"]
    assert "sandbox" in data["details"]
    assert "emulator" in data["details"]

def test_llm_endpoint_safe(mock_config, mock_llm):
    # /llm/chat_complete returns "Safe"
    response = client.post("/llm/chat_complete", json={"prompt":"Check this URL"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "Safe" in data["response"]

def test_llm_endpoint_error(mock_config, mock_llm):
    # If prompt empty, mock LLM raises ValueError
    mock_llm.side_effect = ValueError("Prompt field must not be empty")
    response = client.post("/llm/chat_complete", json={"prompt":""})
    assert response.status_code == 400
    data = response.json()
    assert "Prompt field must not be empty" in data["detail"]

def test_sandbox_run_file_safe(mock_config, mock_sandbox):
    # /sandbox/run_file with a safe file
    response = client.post("/sandbox/run_file", json={"file_ref":"safe_test.bin"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "logs" in data
    assert any("no suspicious" in log.lower() for log in data["logs"])

def test_sandbox_run_file_malware(mock_config, mock_sandbox):
    # /sandbox/run_file with a malware file
    response = client.post("/sandbox/run_file", json={"file_ref":"malware_test.bin"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "logs" in data
    assert any("suspicious" in log.lower() for log in data["logs"])

def test_emulator_run_app(mock_config, mock_emulator):
    # Test if /emulator/run_app returns task_id and other fields
    mock_run_app, _ = mock_emulator
    response = client.post("/emulator/run_app", json={"app_ref":"test_app.apk"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "visuals" in data
    assert "events" in data
    assert "task_id" in data   # This was previously missing, now it's present
    assert data["task_id"] == "emu_task_123"

def test_vnc_url(mock_config, mock_emulator):
    # First run an app to get a known task_id
    run_app_response = client.post("/emulator/run_app", json={"app_ref":"test_app.apk"})
    task_id = run_app_response.json()["task_id"]

    response = client.get(f"/{task_id}/vnc")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "vnc_url" in data
    assert "vnc://emulator1:5900" in data["vnc_url"]

def test_vnc_url_not_found(mock_config, mock_emulator):
    # unknown task_id
    response = client.get("/unknown_task_id_999/vnc")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()

def test_admin_endpoints(mock_config):
    # Check admin endpoints listing /admin/endpoints
    response = client.get("/admin/endpoints")
    assert response.status_code == 200
    data = response.json()
    assert "endpoints" in data
    # Ensure known endpoints are listed
    endpoints = data["endpoints"]
    assert "/health/" in endpoints
    assert "/llm/chat_complete" in endpoints
    assert "/sandbox/run_file" in endpoints

def test_admin_config(mock_config):
    # Check config endpoint: /admin/config
    response = client.get("/admin/config")
    assert response.status_code == 200
    data = response.json()
    # Mock config returns a dict with llm/sandbox/emulator keys
    assert "config" in data
    assert "llm" in data["config"]
    assert "emulator" in data["config"]
    assert "sandbox" in data["config"]
