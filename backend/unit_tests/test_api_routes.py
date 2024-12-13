import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend_server import create_app
from data_models.schemas import MessageRequest, LinkRequest

###############################################################################
# Test File: test_api_routes.py
#
# Focus:
# - Unit testing of various API endpoints related to task creation and input handling.
# - Covers several test cases from the plan:
#   - T-Backend-Message-001: Test message analysis endpoint.
#   - T-Backend-Link-001: Test link analysis endpoint.
#   - T-Backend-Validation-001: Check invalid inputs for link analysis.
#   - T-Backend-Error-001: Simulate external service failure for link analysis.
#
# Philosophy:
# We use (T)est approach: directly call endpoints and verify responses.
# Some (I)nspection is done by checking logs or mock calls.
# This file strictly uses unit tests with mocked connectors to avoid integration complexity.
#
# Maintainability:
# - Clear docstrings and test steps.
# - Each test function focuses on one scenario.
# - Mocking external connectors ensures consistent test results without depending on real services.
###############################################################################


@pytest.fixture(scope="module")
def test_client():
    """
    A pytest fixture to create a TestClient instance for the FastAPI app.
    This allows all tests in this module to share a single client.
    """
    app = create_app()
    client = TestClient(app)
    return client


###############################################################################
# Helper Mocks
#
# We'll define helper fixtures/mocks for connectors to avoid repetitive code.
# For instance, when testing message or link endpoints, we need to mock the
# respective connector's "analyze_message"/"analyze_link" functions to return
# controlled responses.
###############################################################################


@pytest.fixture
def mock_message_service(mocker):
    """
    Mock the message_service_connector.analyze_message method.
    By default, returns a dummy task reference: "msg-task-123".
    """
    return mocker.patch(
        "connectors.message_service_connector.analyze_message",
        return_value="msg-task-123"
    )


@pytest.fixture
def mock_link_service(mocker):
    """
    Mock the link_service_connector.analyze_link method.
    By default, returns a dummy task reference: "link-task-456".
    """
    return mocker.patch(
        "connectors.link_service_connector.analyze_link",
        return_value="link-task-456"
    )


###############################################################################
# T-Backend-Message-001
#
# Purpose:
# Test that POST /api/analyze/message creates a message analysis task and returns a task_id.
#
# Design: (T)
# Prerequisites:
# - Mocks in place for message connector.
#
# Tested Objects:
# - routes_message::analyze_message endpoint
# - orchestrator logic
#
# Steps:
# Step 1: POST /api/analyze/message with a valid MessageRequest {"message":"Suspicious text"}
# Step 2: Expect 200 response, JSON with task_id
# Step 3: Verify mock_message_service called once.
#
# Success Criteria:
# - status_code == 200
# - JSON has "task_id"
# - "msg-task-123" returned if no transformation done by backend
###############################################################################
def test_analyze_message_endpoint_success(test_client, mock_message_service):
    # Step 1:
    payload = {"message": "Suspicious text"}
    response = test_client.post("/api/analyze/message", json=payload)

    # Step 2:
    assert response.status_code == 200, "Expected 200 OK from /api/analyze/message"
    json_resp = response.json()
    assert "task_id" in json_resp, "Response should contain a task_id"
    # The returned task_id might differ if the backend enqueues tasks differently.
    # If the backend transforms "msg-task-123" into something else, adjust this check.
    # For now, we assume it returns a unique ID. Just check it's not empty.
    assert json_resp["task_id"] != "", "task_id should not be empty"

    # Step 3:
    mock_message_service.assert_called_once_with("Suspicious text")


###############################################################################
# T-Backend-Link-001
#
# Purpose:
# Test that POST /api/analyze/link creates a link analysis task.
#
# Design: (T)
# Prerequisites:
# - mock_link_service fixture
#
# Steps:
# Step 1: POST /api/analyze/link with {"url":"http://phish.url","visual_verify":false}
# Step 2: Expect 200, JSON with task_id
# Step 3: Check mock called once with given parameters
#
# Success Criteria:
# - status_code == 200
# - Contains task_id
###############################################################################
def test_analyze_link_endpoint_success(test_client, mock_link_service):
    payload = {"url": "http://phish.url", "visual_verify": False}
    response = test_client.post("/api/analyze/link", json=payload)
    assert response.status_code == 200, "Expected 200 OK from /api/analyze/link"
    json_resp = response.json()
    assert "task_id" in json_resp
    assert json_resp["task_id"] != ""

    # Check mock was called with correct args
    mock_link_service.assert_called_once_with("http://phish.url", False)


###############################################################################
# T-Backend-Validation-001
#
# Purpose:
# Submit invalid input to ensure validation handles it gracefully.
#
# Design: (T/I)
# Prerequisites:
# - No specific mocks required for basic validation. The endpoint should raise 422.
#
# Steps:
# Step 1: POST /api/analyze/link with invalid payload: {"url":"not_a_valid_url"}
# Step 2: Expect 422 Unprocessable Entity due to Pydantic validation
#
# Success Criteria:
# - HTTP 422 returned
###############################################################################
def test_analyze_link_endpoint_invalid_input(test_client):
    # "not_a_valid_url" doesn't match typical URL schema, 
    # expecting Pydantic HttpUrl validation error.
    payload = {"url": "not_a_valid_url", "visual_verify": False}
    response = test_client.post("/api/analyze/link", json=payload)
    # If pydantic validation fails, FastAPI returns 422.
    assert response.status_code == 422, "Expected 422 on invalid URL input"


###############################################################################
# T-Backend-Error-001
#
# Purpose:
# Simulate external API failure and verify that the endpoint handles it gracefully.
#
# Design: (T)
# Prerequisites:
# - mock_link_service but this time we raise an exception to simulate API failure.
#
# Steps:
# Step 1: mock_link_service raises an exception when called.
# Step 2: POST /api/analyze/link with a good URL
# Step 3: Expect the backend to handle the error, possibly returning a 500 or an error message.
#
# Success Criteria:
# - Backend returns a non-200 code (e.g., 500 or a defined error format).
# - Check logs if necessary (not mandatory here).
###############################################################################
def test_analyze_link_endpoint_external_api_failure(test_client, mocker):
    # We override the mock_link_service to raise an exception now.
    mock_fail = mocker.patch(
        "connectors.link_service_connector.analyze_link",
        side_effect=Exception("External API failure simulated")
    )

    payload = {"url": "http://normal.url", "visual_verify": True}
    response = test_client.post("/api/analyze/link", json=payload)

    # Since we haven't defined exact error handling in the previous doc, let's assume:
    # The backend might return a 500 Internal Server Error on such an exception.
    assert response.status_code == 500 or response.status_code == 502, (
        "Expected a server error status code due to external API failure."
    )

    # The exact response body might differ depending on error handling strategy.
    # We at least check if there's some error indication:
    json_resp = response.json()
    assert "error" in json_resp or "detail" in json_resp, "Response should indicate error scenario"

    mock_fail.assert_called_once_with("http://normal.url", True)


###############################################################################
# Additional Notes:
#
# Future tests could include T-Backend-File-001, T-Backend-App-001, and T-Backend-VNC-001
# in this same file or another file like test_api_routes_advanced.py. The pattern remains:
# - Mock the respective connectors (file or app).
# - POST the input to /api/analyze/file or /api/analyze/app.
# - Check for proper response and task_id.
#
# For T-Backend-VNC-001, we would mock emulator_provider_connector.get_vnc_session
# and verify GET /api/task/{task_id}/vnc returns a redirect or a link.
#
# Since only "next file" requested, this should suffice as a comprehensive example.
###############################################################################
