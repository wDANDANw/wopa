###############################################################################
# test_integration_sandbox.py
#
# Purpose:
# Integration tests for the sandbox endpoint and logic. These tests attempt 
# to run the sandbox analysis on actual sample files (`safe_test.bin` and 
# `malware_test.bin`) and verify that the returned logs match expected patterns.
# 
# Prerequisites:
# - Running Sandbox environment accessible at endpoints defined in config.yaml.
# - The test data files (safe_test.bin, malware_test.bin) available in the container.
#
# Strategy:
# - Submit `safe_test.bin` and expect logs indicating no suspicious activity.
# - Submit `malware_test.bin` and expect suspicious or malicious indicators in logs.
# - If the sandbox is unreachable or not returning expected results, tests 
#   will fail, indicating an environment issue.
#
# Requirements:
# - pytest, real network access.
# - Ensure `config.yaml` and possibly `instances.json` have valid sandbox endpoints.
#
# Maintainability:
# - If sandbox detection patterns change, update assertions accordingly.
# - If more test samples appear, add more cases.
###############################################################################

import pytest
import requests
import os
import json
from utils.config_loader import load_config

config = load_config("config.yaml")
# Assume that sandbox endpoint might be discovered from config or instances.json
# If sandbox endpoint is not stable or requires discovering from instances.json, 
# code might need to parse instances.json here.

# For simplicity, we assume provider_server is running at http://localhost:8003
# and the endpoint for sandbox is /sandbox/run_file internally managing calls.
provider_url = "http://localhost:8003/sandbox/run_file"

# Check if sandbox endpoints exist in config
sandbox_endpoints = config.get("sandbox", {}).get("endpoints", [])
if not sandbox_endpoints:
    pytest.skip("No sandbox endpoints configured, skipping sandbox integration tests.", allow_module_level=True)

@pytest.mark.integration
def test_sandbox_safe_file():
    # safe_test.bin should return logs with no suspicious activity
    # Ensure safe_test.bin exists in test_data directory within container
    payload = {"file_ref":"safe_test.bin"}
    r = requests.post(provider_url, json=payload, timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}, body: {r.text}"
    data = r.json()
    assert data["status"] == "success"
    assert "logs" in data
    # Expect something indicating no suspicious activity
    assert any("no suspicious" in log.lower() for log in data["logs"]), f"Expected a log mentioning 'no suspicious', got: {data['logs']}"

@pytest.mark.integration
def test_sandbox_malware_file():
    # malware_test.bin should yield suspicious activity logs
    payload = {"file_ref":"malware_test.bin"}
    r = requests.post(provider_url, json=payload, timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}, body: {r.text}"
    data = r.json()
    assert data["status"] == "success"
    assert "logs" in data
    # Expect suspicious or malicious keywords
    suspicious_keywords = ["suspicious", "malware", "known bad signature"]
    assert any(any(kw in log.lower() for kw in suspicious_keywords) for log in data["logs"]), \
        f"Expected at least one suspicious keyword in logs: {data['logs']}"

@pytest.mark.integration
def test_sandbox_unreachable():
    # If we fake a scenario by providing a file_ref that triggers a known unreachable endpoint
    # Without mocking, might be tricky. If no known scenario, we can skip or just attempt 
    # a known unreachable route. If we have a second sandbox endpoint that doesn't exist, 
    # we could forcibly break it. Otherwise, just check if we handle timeouts gracefully.

    # For demonstration, assume if file_ref="unknown.bin" leads to no route to sandbox?
    # If not possible, skip this test or rely on manual test mode:
    if len(sandbox_endpoints) < 1:
        pytest.skip("Cannot test unreachable scenario without a second invalid endpoint.")
    # Let's assume normal scenario is tested above; unreachable scenario may require special setup.
    # Without that setup, we skip.
    pytest.skip("No known method to force unreachable sandbox endpoint at runtime. Skipping.")

###############################################################################
# Explanation:
#
# - test_sandbox_safe_file: Checks normal scenario with safe_test.bin. Expects logs indicating no suspicious activity.
# - test_sandbox_malware_file: Uses malware_test.bin and expects logs with suspicious/malware indicators.
# - test_sandbox_unreachable: A placeholder test for unreachable scenario. 
#   Without a controlled environment to simulate unreachable endpoints, we skip it.
#
# Integration means relying on actual sandbox responses. If sandbox isn't running 
# or doesn't produce expected strings, tests might fail.
#
# Maintainability:
# - Update suspicious keywords if sandbox detection patterns change.
# - If adding more test samples, replicate the pattern for additional checks.
###############################################################################
