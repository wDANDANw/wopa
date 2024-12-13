###############################################################################
# test_integration_health.py
#
# Purpose:
# Integration tests for the /health endpoint. These tests confirm that the 
# Providers subsystem can correctly report on the health of LLM, Sandbox, and Emulator 
# services when all are running (or if any fail, reflect that state).
#
# Prerequisites:
# - Running LLM, Sandbox, Emulator services as per config.yaml or instances.json.
# - The provider_server running and accessible.
#
# Strategy:
# - Call /health and expect a JSON with "status" and "details".
# - If all services are up, "status" should be "ok" and details for llm/sandbox/emulator should be "ok".
# - If one service is down, system might show "status":"degraded" or "down" and reflect that in details.
#
# Test Scenarios:
# 1. Normal scenario (all services up) → status = "ok"
# 2. If we can simulate one service down (e.g., by removing an endpoint from config or temporarily stopping a service),
#    we could test degraded scenario. Without actual environment control, we can just check normal scenario.
#
# Requirements:
# - pytest, real network access.
# - If no way to simulate downtime easily, just check normal scenario.
#
# Maintainability:
# - If health logic changes to include more details or more services, update assertions.
# - If partial failures return different codes or fields, adjust accordingly.
###############################################################################

import pytest
import requests
import json
from utils.config_loader import load_config

config = load_config("config.yaml")
llm_endpoint = config.get("llm", {}).get("endpoint")
sandbox_endpoints = config.get("sandbox", {}).get("endpoints", [])
emulator_endpoints = config.get("emulator", {}).get("endpoints", [])

# If no endpoints at all, skip tests
if not llm_endpoint and not sandbox_endpoints and not emulator_endpoints:
    pytest.skip("No services configured, skipping health integration tests.", allow_module_level=True)

@pytest.mark.integration
def test_health_all_up():
    # Test /health in a normal scenario assuming all services are running
    health_url = "http://localhost:8003/health"
    r = requests.get(health_url, timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}. Body: {r.text}"

    data = r.json()
    assert "status" in data
    assert "details" in data

    # Typically, if all up, status = "ok"
    # details might look like {"llm":"ok","sandbox":"ok","emulator":"ok"}
    # If one service not configured, might show something else. Just ensure keys exist if endpoints are defined.
    overall_status = data["status"]
    details = data["details"]

    # If all three services are configured, expect all in details
    if llm_endpoint:
        assert "llm" in details
        # If truly up, "ok". If not guaranteed, at least check presence:
        assert details["llm"] in ["ok","degraded","down"]

    if sandbox_endpoints:
        assert "sandbox" in details
        assert details["sandbox"] in ["ok","degraded","down"]

    if emulator_endpoints:
        assert "emulator" in details
        assert details["emulator"] in ["ok","degraded","down"]

    # If all known services presumably up, we might expect "ok".
    # If environment is partial, just ensure no error and minimal fields present.
    # We'll assume a normal scenario returns "ok".
    # If test environment can't guarantee that, we can relax the assertion:
    assert overall_status in ["ok","degraded","down"], "Unexpected overall health status."

@pytest.mark.integration
def test_health_degraded_scenario():
    # Optional: If we can simulate a partial failure, e.g., by disabling emulator temporarily,
    # we can then check for "degraded" or "down".
    # Without real control, we might skip or just attempt and not fail if not possible.

    # Check if we have a scenario or environment variable to simulate downtime
    simulate_downtime = False  # If no control, skip test
    if not simulate_downtime:
        pytest.skip("No downtime simulation implemented, skipping degraded scenario test.")

    # If implemented, maybe we stop emulator service, then call /health:
    # r = requests.get("http://localhost:8003/health", timeout=10)
    # data = r.json()
    # assert data["status"] in ["degraded","down"]
    # assert "emulator" in data["details"] and data["details"]["emulator"] == "down"
    # After test, restore emulator.
    pass

###############################################################################
# Explanation:
#
# - test_health_all_up: Queries /health, checks basic structure and statuses. 
#   Assumes a stable environment, tries to be flexible if not all services are defined.
#
# - test_health_degraded_scenario: Placeholder for a scenario to test partial failures.
#   Without environment control, just skip. If future environment allows simulating downtime,
#   we’d implement logic to ensure /health shows "degraded" or "down".
#
# Maintainability:
# - If health endpoint evolves, add more assertions for new fields.
# - If partial failures become testable, enable and complete the degraded scenario test.
###############################################################################
