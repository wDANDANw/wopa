###############################################################################
# test_integration_scaling_fallback.py
#
# Purpose:
# Integration tests checking how the system behaves under load or when endpoints 
# become unreachable, and whether fallback/scaling logic kicks in.
#
# Prerequisites:
# - A scenario where Terraform can spin up additional emulator/sandbox instances 
#   if load is high.
# - Possibly require `provisioner.py` and proper configuration in `config.yaml`.
#
# Strategy:
# - Simulate multiple requests in quick succession to emulator or sandbox endpoints,
#   expecting that if capacity is exceeded, the system either returns a clear error
#   or triggers provisioning logic.
# - If fallback is implemented, for example, when LLM or sandbox endpoints fail,
#   the code may attempt a secondary endpoint or return a defined fallback response.
#
# Requirements:
# - pytest, real environment setup with Terraform and second endpoints prepared.
# - If no scaling or fallback logic is implemented, tests might be placeholders or skipped.
#
# Maintainability:
# - Update tests if new fallback mechanisms appear (like reading from `instances.json` 
#   to find extra endpoints).
# - If we add metrics or logs for scaling events, we could verify them here.
###############################################################################

import pytest
import requests
import os
import json
import time
from utils.config_loader import load_config

config = load_config("config.yaml")

# Check if multiple endpoints or scaling logic is defined. If not, skip.
sandbox_endpoints = config.get("sandbox", {}).get("endpoints", [])
emulator_endpoints = config.get("emulator", {}).get("endpoints", [])
# Suppose we need at least 2 endpoints in sandbox or emulator to test scaling/fallback
if len(sandbox_endpoints) < 2 and len(emulator_endpoints) < 2:
    pytest.skip("No multiple endpoints or scaling logic found, skipping scaling/fallback integration tests.", allow_module_level=True)

provider_url_emulator = "http://localhost:8003/emulator/run_app"
provider_url_sandbox = "http://localhost:8003/sandbox/run_file"

@pytest.mark.integration
def test_emulator_scaling():
    # If scaling logic is implemented, we can try sending multiple requests rapidly
    # and see if responses remain stable or if fallback logic triggers.
    # Without actual scaling code, this test may be a placeholder.

    # Attempt to run multiple apps in parallel (just sequential calls here)
    successes = 0
    for i in range(5):
        payload = {"app_ref":"test_app.apk"}
        r = requests.post(provider_url_emulator, json=payload, timeout=15)
        # If scaling: we might expect all requests to succeed, or the system to stand up new endpoints.
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "success":
                successes += 1
        else:
            # If fallback logic is implemented, maybe we get a defined fallback response
            # If no fallback, just note the failure
            pass

    assert successes >= 3, "At least 3 out of 5 emulator run attempts should succeed if scaling works."

@pytest.mark.integration
def test_sandbox_fallback_on_failure():
    # Simulate a scenario where first sandbox endpoint fails (e.g., by removing it from config or timing it out).
    # If fallback is implemented, the system might try a second endpoint.
    # Without control over endpoints, we can try a slow test:
    
    # Let's try sending a suspicious file repeatedly. If the first sandbox is overloaded or unreachable,
    # the system might try a second sandbox endpoint or return a fallback response.
    
    # This test may be mostly placeholder if no fallback logic is actually implemented.
    attempts = 3
    suspicious_found = 0
    for _ in range(attempts):
        payload = {"file_ref":"malware_test.bin"}
        r = requests.post(provider_url_sandbox, json=payload, timeout=10)
        if r.status_code == 200:
            data = r.json()
            logs = data.get("logs", [])
            # If fallback worked, we still see suspicious logs from the second endpoint
            if any("suspicious" in log.lower() for log in logs):
                suspicious_found += 1
        else:
            # If fails, maybe fallback not implemented or environment not correct
            pass

    # Expect at least one success indicating fallback or multiple endpoints usage
    assert suspicious_found >= 1, "At least one sandbox attempt should yield suspicious logs if fallback/scaling works."

@pytest.mark.integration
def test_llm_fallback_if_main_endpoint_down():
    # If main LLM endpoint is down, fallback logic might try a secondary endpoint or return cached responses.
    # Without second LLM endpoint defined, skip or just attempt and see what happens.
    llm_endpoints = config.get("llm",{}).get("extra_endpoints", [])
    if not llm_endpoints:
        pytest.skip("No extra LLM endpoints for fallback, skipping this test.")

    # If we have extra_endpoints, let's assume main is down. We can't easily simulate downtime here.
    # Just send a prompt and see if we get a result. If main down scenario can't be forced, 
    # this test might be placeholder or require manual environment setup.

    prompt = {"prompt":"Test fallback scenario","stream":False}
    r = requests.post("http://localhost:8003/llm/chat_complete", json=prompt, timeout=10)
    # If fallback works, we get a success anyway
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "response" in data and len(data["response"]) > 0

###############################################################################
# Explanation:
#
# - test_emulator_scaling: Sends multiple requests to /emulator/run_app to check if 
#   multiple endpoints or scaling logic handle load. Without real scaling, 
#   sets a minimal success criterion.
#
# - test_sandbox_fallback_on_failure: Tries suspicious files repeatedly, expecting 
#   at least one successful suspicious detection if fallback to second sandbox endpoint 
#   or scaling logic is in place.
#
# - test_llm_fallback_if_main_endpoint_down: Attempts a scenario for LLM fallback 
#   if extra endpoints are defined. If main is down, code might use extra_endpoints. 
#   Without control, this is a placeholder expecting success.
#
# These tests might be placeholders if actual scaling/fallback logic isn’t implemented. 
# If real logic exists, these tests help ensure reliability under load or failure conditions.
#
# Maintainability:
# - If new fallback routes, scaling policies, or infrastructure changes occur, 
#   update tests to reflect real expected behaviors.
###############################################################################
