import os
import pytest
from fastapi.testclient import TestClient

# Import the create_app function from the backend server.
# This requires that backend_server.py is in the python path or same package.
from backend_server import create_app


###############################################################################
# Test File: test_backend_server.py
#
# This file focuses on testing the core initialization and health endpoints of 
# the backend. According to the test plan, it mainly addresses the following:
#
# - T-Backend-Health-001: Verifying the /api/health endpoint sanity.
#
# Additional Notes:
# - We assume all environment variables are set externally (e.g., docker-compose),
#   but for unit tests, we can mock or provide defaults if needed.
# - The tests here do not integrate with external services or Redis. They focus 
#   on basic endpoint functionality to ensure the server starts up and responds 
#   correctly.
#
# Philosophy:
# Testing here is primarily (T) (Test) type verification from the RVM:
# We directly stimulate the endpoint and measure the response. Minimal (I) 
# (Inspection) occurs if we print or observe logs.
#
# Maintainability:
# Clear docstrings, explicit naming, and isolation of test cases ensure that if 
# the code changes (e.g., the health endpoint response format), updates are 
# minimal and localized.
###############################################################################


@pytest.fixture(scope="module")
def test_client():
    """
    A pytest fixture to create a TestClient instance for the FastAPI app.
    This client is reused for all tests in this module.

    We create the FastAPI app using create_app(), assuming it sets up the 
    routers and endpoints correctly.
    """
    app = create_app()
    client = TestClient(app)
    return client


###############################################################################
# Test Case: T-Backend-Health-001
#
# Purpose:
# Verify that the /api/health endpoint returns a healthy status, indicating that 
# the backend is up and running. This is critical for continuous integration 
# checks (liveness probes) and ensures reliability (NFR2).
#
# Design: 
# - Make a GET request to /api/health and expect a 200 OK and a JSON response 
#   like {"status":"healthy"}.
# - If the format changes in the future, we update this test accordingly.
#
# Prerequisites:
# - The backend_server app must have the /api/health route included.
# - No special environment variables needed for this basic test.
#
# Tested Objects:
# - /api/health endpoint
# - Basic FastAPI app initialization and routing
#
# Test Plan Steps:
# Step 1: Send GET request to /api/health
# Step 2: Assert the response is HTTP 200.
# Step 3: Assert the JSON body includes "status":"healthy".
#
# Success Criteria:
# - HTTP 200 returned.
# - JSON response with "status":"healthy".
###############################################################################
def test_health_endpoint(test_client):
    """
    T-Backend-Health-001:
    Test the health endpoint to ensure the backend responds with a healthy status.
    """
    # Step 1: Send GET request to /api/health
    response = test_client.get("/api/health")

    # Step 2: Assert HTTP 200 OK
    assert response.status_code == 200, "Expected 200 OK from health endpoint."

    # Step 3: Check JSON body contains status "healthy"
    json_resp = response.json()
    assert "status" in json_resp, "Health response should contain 'status' field."
    assert json_resp["status"] == "healthy", "Expected status='healthy' in the response."


###############################################################################
# Additional Tests (If Needed)
#
# Although only T-Backend-Health-001 is mandatory here, we can add more tests 
# related to server initialization if desired:
#
# For example, T-Backend-Config-001 (from the previous mapping) could be tested 
# if config loading is accessible here. That would require mocking environment 
# variables and checking if the config_loader behaves as expected.
#
# Example (Optional):
#
# def test_config_loading(mocker):
#     # This is not requested explicitly but shown as an example template.
#     # Mock environment variables and verify config_loader results.
#     mocker.setenv("MESSAGE_SERVICE_URL", "http://fake-message-url")
#     from core.config_loader import get_env
#     val = get_env("MESSAGE_SERVICE_URL")
#     assert val == "http://fake-message-url"
#
# This test would confirm environment-based configuration works, fulfilling T-Backend-Config-001.
#
# Since user only requested the "first file", we won't fully implement all 
# test cases here. We'll stop at T-Backend-Health-001 as a demonstration.
###############################################################################
