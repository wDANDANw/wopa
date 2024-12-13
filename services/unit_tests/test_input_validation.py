"""
test_input_validation.py

This test file corresponds to the T-Services-Input-Validation-002 test case and related checks.

**Test Case: T-Services-Input-Validation-002**

**Purpose:**
The purpose is to ensure that the /analyze/* endpoints strictly validate incoming request payloads 
(url, message, file_ref, app_reference) and reject malformed or missing inputs 
with a proper error response. This includes:
- Invalid or missing URL in /analyze/link
- Empty or missing message in /analyze/message
- Missing file_ref in /analyze/file
- Invalid or missing app_reference in /analyze/app

**Design & Approach:**
- We use pytest and fastapi.testclient again to simulate requests.
- Each endpoint’s input validation logic is presumably performed by the underlying service.
- As these are unit tests, we may assume the services are reachable. If needed, 
  we can mock the service layer, but let's first assume the validation is integrated 
  directly in the endpoint or a small wrapper that calls `validate_task()`.

- We'll send various invalid payloads to each endpoint and confirm:
  1. The response status code is 400 or another suitable client error code.
  2. The response body contains a JSON with an "error" key explaining what was wrong.

**Prerequisites:**
- Endpoints: /analyze/link, /analyze/message, /analyze/file, /analyze/app
- Validation rules known:
  - For /analyze/link: Must contain a "url" field starting with http
  - For /analyze/message: Must contain "message" (non-empty string)
  - For /analyze/file: Must contain "file_ref" (string referencing a file)
  - For /analyze/app: Must contain "app_reference" (valid string)
- The server should return proper JSON errors for invalid inputs.

**Maintainability Notes:**
- If validation rules change (e.g., new fields, stricter formats), update these tests.
- Keep test data minimal but representative. If "url" requires http/https, test a malformed URL.
- Document expected error messages so future maintainers can easily adjust checks.

**Success Criteria:**
- Each invalid input scenario returns an HTTP 400 and a JSON error message.
- Proper error handling ensures no unexpected 500s or unclear messages.

"""

import pytest
from fastapi.testclient import TestClient
from service_manager import app

@pytest.fixture(scope="module")
def test_client():
    """Fixture to provide a TestClient instance for sending requests to the app."""
    return TestClient(app)


def test_invalid_link_input_no_url(test_client):
    """
    T-Services-Input-Validation-002-PartA-1

    Purpose:
    Test /analyze/link endpoint with missing 'url' field.

    Steps:
    - POST /analyze/link with JSON body {} or without 'url'.
    - Expect 400 status and error message about missing 'url'.

    Success Criteria:
    Status code = 400
    response.json()["error"] contains "url"
    """
    response = test_client.post("/analyze/link", json={})
    assert response.status_code == 400, "Missing url should cause 400"
    data = response.json()
    assert "error" in data, "Error field expected"
    assert "url" in data["error"].lower(), "Expected mention of 'url' in error"


def test_invalid_link_input_malformed_url(test_client):
    """
    T-Services-Input-Validation-002-PartA-2

    Purpose:
    Test /analyze/link with a malformed URL (not starting with http).

    Steps:
    - POST /analyze/link with json={"url":"ftp://strange.com"}
    - Expect 400 and error message indicating invalid URL format.

    Success Criteria:
    Status code = 400
    'error' mentions invalid or missing 'url'.
    """
    payload = {"url": "ftp://strange.com"}  # Not http or https
    response = test_client.post("/analyze/link", json=payload)
    assert response.status_code == 400, "Invalid URL format should yield 400"
    data = response.json()
    assert "error" in data
    # The service presumably checks for "http" or "https"
    assert "url" in data["error"].lower() and "invalid" in data["error"].lower(), \
        "Should complain about invalid url format"


def test_invalid_message_input_empty_message(test_client):
    """
    T-Services-Input-Validation-002-PartB-1

    Purpose:
    Test /analyze/message with empty 'message' field.

    Steps:
    - POST /analyze/message with {"message":""}
    - Expect 400 and mention that message cannot be empty.

    Success Criteria:
    status code=400
    error includes 'message'
    """
    payload = {"message": ""}
    response = test_client.post("/analyze/message", json=payload)
    assert response.status_code == 400, "Empty message should fail validation"
    data = response.json()
    assert "error" in data
    assert "message" in data["error"].lower(), "Error should mention 'message'"


def test_invalid_message_input_missing_message(test_client):
    """
    T-Services-Input-Validation-002-PartB-2

    Purpose:
    Test /analyze/message with no 'message' field at all.

    Steps:
    - POST /analyze/message with {}
    - Expect 400 and error about missing message field.

    Success Criteria:
    400 status, 'error' mentions 'message'
    """
    response = test_client.post("/analyze/message", json={})
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "message" in data["error"].lower(), "Should mention missing message"


def test_invalid_file_input_missing_file_ref(test_client):
    """
    T-Services-Input-Validation-002-PartC-1

    Purpose:
    Test /analyze/file with missing 'file_ref'.

    Steps:
    - POST /analyze/file with {}
    - Expect 400 and error about missing file_ref.

    Success Criteria:
    400 status, error mentions 'file_ref'
    """
    response = test_client.post("/analyze/file", json={})
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "file_ref" in data["error"].lower(), "Should mention missing file_ref"


def test_invalid_app_input_missing_app_reference(test_client):
    """
    T-Services-Input-Validation-002-PartD-1

    Purpose:
    Test /analyze/app with missing 'app_reference'.

    Steps:
    - POST /analyze/app with {}
    - Expect 400 and error about missing app_reference.

    Success Criteria:
    400 status, error mentions 'app_reference'
    """
    response = test_client.post("/analyze/app", json={})
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "app_reference" in data["error"].lower(), "Should mention missing app_reference"


def test_invalid_app_input_invalid_app_reference_format(test_client):
    """
    T-Services-Input-Validation-002-PartD-2

    Purpose:
    If there's any stricter rule for app_reference (e.g., must be a non-empty string),
    test a malformed input (like number or empty string).

    Steps:
    - POST /analyze/app with {"app_reference": ""}
    - Expect 400 and appropriate error message.

    Success Criteria:
    400 status, error mentions 'app_reference' invalid
    """
    payload = {"app_reference": ""}
    response = test_client.post("/analyze/app", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    # For now we assume empty string is invalid:
    assert "app_reference" in data["error"].lower() and "invalid" in data["error"].lower(), \
        "Error should mention invalid app_reference"


"""
Additional Notes:

- We separated tests by endpoint and scenario for clarity.
- Each test includes a docstring detailing purpose, steps, and success criteria.
- If services logic changes, e.g., allow ftp URLs, update test accordingly.
- The approach is minimal: just send invalid inputs and check for error responses.
- Maintainability: clear docstrings, consistent naming, and minimal assumptions.

By passing all these tests, we confirm robust input validation in the services module.
"""
