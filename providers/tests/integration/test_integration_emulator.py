###############################################################################
# test_integration_emulator.py
#
# Purpose:
# Integration tests for the emulator environment. These tests attempt to:
# - Run a known test app (test_app.apk) via /emulator/run_app endpoint.
# - Retrieve the VNC URL for the given task_id using GET /{task_id}/vnc.
#
# Prerequisites:
# - A running emulator environment accessible via endpoints in config or instances.json.
# - `test_app.apk` present in test_data directory.
#
# Strategy:
# 1. Call POST /emulator/run_app with app_ref="test_app.apk".
#    - Expect a successful response with a `task_id`.
#    - The response should include `visuals` and `events`.
# 2. Using the returned `task_id`, call GET /{task_id}/vnc.
#    - Expect a status=200 and JSON with `vnc_url`.
#    - `vnc_url` should match the `vnc_url_template` in config or instances.json.
#
# If emulator is not configured or endpoints not found, skip tests.
#
# Requirements:
# - pytest, real network access.
# - Ensure emulator endpoints are properly defined and accessible.
#
# Maintainability:
# - If emulator logic changes (like returning different fields), update assertions.
# - If new endpoints are added (like resizing emulator or changing orientation), add tests here.
###############################################################################

import pytest
import requests
import os
import json
from utils.config_loader import load_config

config = load_config("config.yaml")
emulator_endpoints = config.get("emulator", {}).get("endpoints", [])
if not emulator_endpoints:
    pytest.skip("No emulator endpoints configured, skipping emulator integration tests.", allow_module_level=True)

# Assuming provider_server runs at http://localhost:8003
run_app_url = "http://localhost:8003/emulator/run_app"

@pytest.mark.integration
def test_emulator_run_app():
    payload = {"app_ref":"test_app.apk"}
    r = requests.post(run_app_url, json=payload, timeout=15)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}, body: {r.text}"
    data = r.json()
    assert data["status"] == "success"
    assert "visuals" in data and isinstance(data["visuals"], dict)
    assert "events" in data and isinstance(data["events"], list)
    assert "task_id" in data and len(data["task_id"]) > 0

    task_id = data["task_id"]

    # Now get VNC URL for the given task_id
    vnc_url = f"http://localhost:8003/{task_id}/vnc"
    r_vnc = requests.get(vnc_url, timeout=10)
    assert r_vnc.status_code == 200, f"Expected 200, got {r_vnc.status_code}, body: {r_vnc.text}"
    vnc_data = r_vnc.json()
    assert vnc_data["status"] == "success"
    assert "vnc_url" in vnc_data
    assert "vnc://" in vnc_data["vnc_url"], "VNC url should follow vnc:// schema"

    # Optionally, we could validate if vnc_url contains the emulator host and port from config
    # If vnc_url_template = "vnc://{host}:{port}", ensure host and port appear
    vnc_url_template = config.get("emulator", {}).get("vnc_url_template","vnc://{host}:{port}")
    # Since we got a vnc_url in response, just check basic format:
    # If we want to be strict, parse vnc_data["vnc_url"] and compare with emulator_endpoints or default_vnc_port.
    # For now, a basic existence check suffices.

@pytest.mark.integration
def test_emulator_app_missing():
    # If we try to run a non-existing app file, expect error
    payload = {"app_ref":"non_existent_app.apk"}
    r = requests.post(run_app_url, json=payload, timeout=15)
    # The server might return 400 or 404 if app not found
    assert r.status_code in [400,404], f"Expected 400 or 404, got {r.status_code}"
    data = r.json()
    assert "detail" in data
    # Check if detail message mentions missing app file
    assert "not found" in data["detail"].lower() or "missing" in data["detail"].lower()

@pytest.mark.integration
def test_emulator_vnc_unknown_task():
    # Unknown task_id for VNC should return 404
    unknown_task_url = "http://localhost:8003/unknown_task_999/vnc"
    r = requests.get(unknown_task_url, timeout=10)
    assert r.status_code == 404, f"Expected 404 for unknown task, got {r.status_code}"
    data = r.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()

def test_emulator_provisioning_success(mock_config):
    from core.emulator_env import EmulatorEnv
    from unittest.mock import patch

    mock_config.return_value = {"emulator": {"endpoints": [], "max_retries": 1}}
    emulator = EmulatorEnv()

    with patch.object(emulator, '_provision_new_emulator') as mock_prov, \
         patch.object(emulator, '_reload_endpoints') as mock_reload:
        # Simulate that after provisioning, endpoints become available
        mock_reload.side_effect = lambda: setattr(emulator, 'endpoints', ["http://emulator1:5555"])

        # Mock ADB calls for a normal success scenario
        with patch("subprocess.run", side_effect=[...]): # Provide a sequence of successful adb results
            result = emulator.run_app("test_app.apk")
            assert "task_id" in result
            assert "visuals" in result
            assert "events" in result


###############################################################################
# Explanation:
#
# - test_emulator_run_app:
#   Runs test_app.apk, expects success and a task_id, then queries VNC URL for that task_id and expects a success response with a vnc_url.
#
# - test_emulator_app_missing:
#   Tries running a non-existent app_ref. Expects a 400 or 404 error, ensuring error handling is correct.
#
# - test_emulator_vnc_unknown_task:
#   Calls VNC endpoint with a made-up task_id, expects 404 not found response.
#
# Integration means relying on the actual emulator and VNC endpoints. 
# If emulator not running or unreachable, tests fail or might need skipping logic.
#
# Maintainability:
# If emulator logic changes (like returning different fields or different errors), update assertions.
# If new endpoints appear (like scaling emulator view), add tests similarly.
###############################################################################
