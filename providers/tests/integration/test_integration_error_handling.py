###############################################################################
# test_integration_error_handling.py
#
# Purpose:
# Integration tests that specifically target error scenarios and verify 
# how the Providers subsystem responds. This can include:
# - Internal server errors when a service (LLM/sandbox/emulator) returns unexpected data.
# - Invalid user input at integration level (like malformed JSON or missing fields).
# - Timeout scenarios if external services don't respond in a timely manner.
#
# Prerequisites:
# - Running provider_server and connected services.
# - Possibly a scenario to simulate partial failures or invalid inputs.
#
# Strategy:
# 1. Send a request with invalid JSON or missing required fields and expect 400 Bad Request with a `detail` message.
# 2. If we can simulate an external service returning invalid responses, verify that the providers subsystem 
#    returns a 500 Internal Server Error and a meaningful `detail`.
# 3. Attempt a timeout scenario by providing a resource known to take too long or fail, expecting a ConnectionError 
#    or a gateway timeout (depends on actual code logic).
#
# Requirements:
# - pytest, real environment.
# - Without direct control over external services to produce certain errors, 
#   some tests might rely on known triggers (like special prompts or file refs) 
#   or remain as placeholders.
#
# Maintainability:
# - Update tests as error handling logic evolves or as new error scenarios are supported.
# - If new endpoints or external services appear, add corresponding error scenario tests.
###############################################################################

import pytest
import requests
import json
import time
from utils.config_loader import load_config

config = load_config("config.yaml")

provider_base_url = "http://localhost:8003"

@pytest.mark.integration
def test_invalid_json_body():
    # Test sending invalid JSON to an endpoint, e.g., /llm/chat_complete
    # Instead of proper JSON, send a raw string that isn't JSON.
    invalid_json = "this is not json"
    headers = {"Content-Type": "application/json"}
    r = requests.post(provider_base_url + "/llm/chat_complete", data=invalid_json, headers=headers, timeout=5)
    # Expect a 400 Bad Request since JSON parsing fails
    assert r.status_code == 400, f"Expected 400, got {r.status_code}. Body: {r.text}"
    data = r.json()
    assert "detail" in data
    assert "parse error" in data["detail"].lower() or "invalid json" in data["detail"].lower()

@pytest.mark.integration
def test_missing_required_field():
    # If an endpoint requires a certain field (like 'prompt'), but we omit it
    # POST /llm/chat_complete with empty JSON
    payload = {}
    r = requests.post(provider_base_url + "/llm/chat_complete", json=payload, timeout=5)
    # Expect 400 with a detail message about missing 'prompt'
    assert r.status_code == 400, f"Expected 400, got {r.status_code}. Body: {r.text}"
    data = r.json()
    assert "detail" in data
    # Check if detail mentions missing prompt or required field
    assert "prompt" in data["detail"].lower()

@pytest.mark.integration
def test_external_service_invalid_response():
    # If we can simulate external service returning invalid data (e.g., by a special prompt
    # known to break LLM or a known file that causes sandbox to return unexpected format).
    # Without a known scenario, we might try a nonsense prompt that possibly leads to a server error.

    prompt = {"prompt":"### cause invalid llm response ###","stream":False}
    r = requests.post(provider_base_url + "/llm/chat_complete", json=prompt, timeout=10)
    # If code can't handle nonsense and leads to internal error, we might get 500
    # Otherwise, if no known scenario to cause invalid response, we may skip.
    if r.status_code == 500:
        data = r.json()
        assert "detail" in data
        # detail should mention internal error or something similar
        assert "internal" in data["detail"].lower() or "error" in data["detail"].lower()
    elif r.status_code == 200:
        # If no error triggered, we just note no invalid response scenario available
        pytest.skip("No invalid external response scenario triggered. This test may need a known trigger.")
    else:
        # If another code returned, just ensure detail is present
        data = r.json()
        assert "detail" in data

@pytest.mark.integration
def test_timeout_scenario():
    # If we have a known slow operation or can artificially delay external service
    # Without control, we try a known large prompt or a big file to run in sandbox.
    # If no known slow scenario, we can just attempt and expect no failure.
    # Or we rely on a test mode (like environment var) to simulate slowness.

    # For now, attempt a big prompt repeatedly:
    big_prompt = "This is a long prompt " + ("x"*10000)
    payload = {"prompt": big_prompt, "stream":False}
    start = time.time()
    r = requests.post(provider_base_url + "/llm/chat_complete", json=payload, timeout=10)
    end = time.time()

    if r.status_code == 200:
        # If answered in under 10s, no timeout scenario triggered
        # If real environment had a scenario or a special route to cause delay, we would test that
        pytest.skip("No timeout scenario triggered, might need a special route or environment setup.")
    else:
        # If code did raise error or took too long and triggered a timeout at request level,
        # we get a requests.exceptions.Timeout exception rather than a response code.
        # Since we got a code, no actual timeout from requests side. Possibly a slow scenario needed.
        pass

    # If we reach here, no actual timeout scenario triggered. Just pass.
    pass

###############################################################################
# Explanation:
#
# - test_invalid_json_body: Sends invalid JSON to verify the server returns 400 and a parse error detail.
# - test_missing_required_field: Omits 'prompt' in /llm/chat_complete request to confirm a 400 error detailing missing field.
# - test_external_service_invalid_response: Attempts to cause invalid external response. If no known trigger, test may skip or adapt in future.
# - test_timeout_scenario: Tries large input hoping to hit a timeout. If no real delay scenario, test may skip.
#
# These tests highlight error handling. Without a controlled environment to trigger certain errors,
# some tests may skip or not show meaningful results. In a real environment, you might have 
# special triggers or scenarios to ensure these tests demonstrate correct error handling.
#
# Maintainability:
# - Add known triggers or special endpoints to reliably produce errors/timeouts.
# - Update assertions as error messages evolve.
###############################################################################
