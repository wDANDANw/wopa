###############################################################################
# test_integration_llm.py
#
# Purpose:
# Integration tests for LLM interactions. These tests attempt to use the real
# LLM endpoint specified in `config.yaml`. The goal is to verify that:
# - The LLM endpoint is reachable.
# - The /llm/chat_complete endpoint sends prompts to LLM and returns a meaningful response.
# - The system correctly handles streaming responses (if implemented), error scenarios
#   from the LLM, and ensures proper JSON structure in final responses.
#
# Prerequisites:
# - A running Ollama LLM service at the endpoint defined in `config.yaml`.
# - If Ollama is not running, these tests might fail or need to be skipped.
#
# Test Strategy:
# - Check a simple prompt and confirm a non-empty, "safe"-like response.
# - Test a known "phishing" prompt and see if LLM flags it.
# - If streaming is implemented, test with `stream=True` and ensure partial responses appear.
# - Test handling of unexpected LLM responses (e.g., invalid JSON) if LLM can be configured that way.
#
# Requirements:
# - pytest and no mocks (or minimal mocks), since this is integration.
# - Real network calls: ensure network connectivity.
#
# Maintainability:
# - If LLM model or endpoint changes, update test cases or endpoint paths.
# - If new parameters appear in LLM calls (options, format, etc.), add corresponding tests.
###############################################################################

import pytest
import requests
import os
import json
from utils.config_loader import load_config

# Load config to find LLM endpoint or rely on /llm/chat_complete endpoint running locally
config = load_config("config.yaml")
llm_endpoint = config.get("llm", {}).get("endpoint", None)

if not llm_endpoint:
    pytest.skip("No LLM endpoint configured, skipping LLM integration tests.", allow_module_level=True)

@pytest.mark.integration
def test_llm_basic_prompt():
    # Send a basic prompt to /llm/chat_complete and check for normal success response
    # We assume /llm/chat_complete endpoint is available at the provider_server (http://localhost:8003)
    # Adjust port if needed based on docker-compose settings
    provider_url = "http://localhost:8003/llm/chat_complete"

    payload = {"prompt": "Is the sky blue?", "stream": False}

    r = requests.post(provider_url, json=payload, timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}, body: {r.text}"
    data = r.json()
    assert data["status"] == "success"
    assert "response" in data
    assert len(data["response"]) > 0, "LLM response should not be empty."
    # Check if response contains something about the sky being blue
    # Not strictly required, but a sanity check
    assert "blue" in data["response"].lower() or "color" in data["response"].lower()

@pytest.mark.integration
def test_llm_phishing_prompt():
    # Try a prompt that should ideally flag suspicious behavior
    provider_url = "http://localhost:8003/llm/chat_complete"
    payload = {"prompt": "This link tries to steal credentials: http://phishingsite.com", "stream": False}

    r = requests.post(provider_url, json=payload, timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}, body: {r.text}"
    data = r.json()
    assert data["status"] == "success"
    # We might expect LLM to say something like "This looks suspicious" or 
    # "Phishing" if the model is trained that way. Without a guarantee, we just ensure a response.
    assert "response" in data
    assert len(data["response"]) > 0

@pytest.mark.integration
def test_llm_streaming_response():
    # If streaming is supported by /llm/chat_complete with "stream":True, test it.
    # If not supported, skip this test.
    provider_url = "http://localhost:8003/llm/chat_complete"
    payload = {"prompt": "Describe a sunset.", "stream": True}

    # If streaming implemented as a server-sent event or chunked responses, 
    # we might need a different approach. If the endpoint returns an array or multiple json lines:
    # For simplicity, assume it returns a final message after a brief delay.
    # If not implemented, we can skip or just check for 'done': True at the end.
    r = requests.post(provider_url, json=payload, timeout=15)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}, body: {r.text}"

    data = r.json()
    # If truly streaming, we might get multiple chunks. If code above is simplistic,
    # maybe we get a final aggregated response. Just ensure we got a successful, non-empty response.
    assert data["status"] == "success"
    assert "response" in data
    assert len(data["response"]) > 0, "Should have a descriptive sunset response."

@pytest.mark.integration
def test_llm_error_handling():
    # If LLM returns a non-200 or invalid data, the provider_server might return a 500 or error JSON.
    # To simulate this, we might need a special prompt or known scenario where LLM fails.
    # If not feasible, skip or rely on a known test model that can produce errors.
    # Without a real scenario, we can attempt a nonsense prompt and check if code gracefully handles it.
    provider_url = "http://localhost:8003/llm/chat_complete"
    payload = {"prompt": "###", "stream": False}  # Possibly cause LLM confusion

    r = requests.post(provider_url, json=payload, timeout=10)
    # Might still return success. If no known error scenario, we can just ensure no crash.
    assert r.status_code in [200,400,500], f"Unexpected status code: {r.status_code}"
    data = r.json()
    # If 400 or 500, check for detail field
    if r.status_code != 200:
        assert "detail" in data, "Error responses should contain a detail message."

###############################################################################
# Explanation:
#
# - We load config to find LLM endpoint. If no LLM endpoint, we skip the entire module's tests 
#   because integration tests need a running LLM.
#
# - test_llm_basic_prompt: Check a simple prompt and ensure a non-empty, "safe" response.
# - test_llm_phishing_prompt: Provide suspicious prompt and see if response differs (less strict since no guarantee on model output).
# - test_llm_streaming_response: If streaming is implemented, test that the endpoint returns a response when stream=True.
# - test_llm_error_handling: Attempt to provoke error conditions from LLM and ensure server returns a structured error response if possible.
#
# Maintainability:
# - If LLM capabilities change (like returning structured json always), update assertions.
# - If streaming logic changes, adjust streaming test accordingly.
#
# Note: Without a controllable LLM environment, tests do a best-effort check. Some tests might be flaky if LLM responses vary.
###############################################################################
