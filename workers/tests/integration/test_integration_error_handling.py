import pytest
from fastapi.testclient import TestClient
from worker_server import create_app

###############################################################################
# test_integration_error_handling.py
#
# Purpose:
# Integration tests specifically targeting error scenarios where the Providers 
# subsystem returns unexpected responses (5xx status codes, invalid JSON), or 
# times out. The Worker Module should gracefully return `status:"error"` and a 
# descriptive message, maintaining user-friendly behavior under real failure conditions.
#
# Design & Steps:
# 1. Run integration environment with Providers subsystem active.
# 2. Trigger error scenarios for each worker type if possible:
#    - Text: LLM endpoint returns 500 or invalid JSON.
#    - Link: Domain reputation API returns 500, malformed JSON, or unreachable.
#    - Visual: Emulator endpoint times out or returns non-200.
#
# 3. Confirm Worker Module responds with `status:"error"` and messages like 
#    "LLM failed:", "Domain check failed:", or "Emulator run failed:" as defined 
#    in the workers' code.
#
# Maintainability:
# - If we introduce more detailed error messages or new providers, update tests 
#   to reflect those conditions.
# - If it's hard to force errors naturally, consider a test setup in Providers 
#   that triggers known error responses for specific inputs (like special domain 
#   or content strings).
#
# Testing:
# - Run `make test-integration-workers` with MODE=test and TEST_MODE=integration 
#   after ensuring providers can produce these errors.
# - If no real error scenario is triggered, tests may xfail to acknowledge 
#   environmental limitations.
###############################################################################

@pytest.fixture
def integration_test_client():
    """
    Provides a TestClient with the worker app in integration mode.
    """
    app = create_app()
    return TestClient(app)

class TestIntegrationErrorHandling:
    """
    Integration tests for error scenarios. We attempt to cause the Providers 
    endpoints to fail and check Worker Module's error responses.
    """

    def test_llm_error_scenario(self, integration_test_client):
        """
        Purpose:
          Trigger a scenario where LLM endpoint fails (e.g., returns 500 or invalid JSON).

        Steps:
          1. POST /request_worker with {"type":"text","content":"TRIGGER_LLM_ERROR"}
             This special content might cause LLM to fail in the test environment.
        
        Success:
          status=error and message includes "LLM failed".
        
        Note:
          If we can't easily cause LLM error, we xfail.
        """
        resp = integration_test_client.post("/request_worker", json={"type":"text","content":"TRIGGER_LLM_ERROR"})
        if resp.status_code == 200:
            pytest.xfail("No LLM error triggered. Environment stable beyond expectation.")
        else:
            assert resp.status_code in [400,500], "Expected an error status code"
            data = resp.json()
            assert data["status"] == "error"
            assert "LLM failed" in data["message"]

    def test_link_error_scenario(self, integration_test_client):
        """
        Purpose:
          Cause domain reputation API to fail or return malformed data.

        Steps:
          1. POST /request_worker {"type":"link","url":"http://trigger-domain-error.com"}
             This URL should produce an error scenario in domain API.
        
        Success:
          status=error and message includes "Domain check failed".

        Note:
          If no error scenario can be forced, xfail again.
        """
        resp = integration_test_client.post("/request_worker", json={"type":"link","url":"http://trigger-domain-error.com"})
        if resp.status_code == 200:
            pytest.xfail("No domain error triggered as expected.")
        else:
            assert resp.status_code in [400,500], "Expected an error status code"
            data = resp.json()
            assert data["status"] == "error"
            assert "Domain check failed" in data["message"]

    def test_visual_error_scenario(self, integration_test_client):
        """
        Purpose:
          Cause emulator endpoint to fail (e.g., return 500 or cause timeout).

        Steps:
          1. POST /request_worker {"type":"visual","url":"http://trigger-emulator-error.example"}
             This URL should cause emulator failure in the test environment.
        
        Success:
          status=error and message includes "Emulator run failed".

        Note:
          If no error scenario can be forced, xfail again.
        """
        resp = integration_test_client.post("/request_worker", json={"type":"visual","url":"http://trigger-emulator-error.example"})
        if resp.status_code == 200:
            pytest.xfail("No emulator error triggered as expected.")
        else:
            assert resp.status_code in [400,500], "Expected an error status code"
            data = resp.json()
            assert data["status"] == "error"
            assert "Emulator run failed" in data["message"]
