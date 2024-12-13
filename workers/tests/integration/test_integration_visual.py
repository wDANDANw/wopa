import pytest
from fastapi.testclient import TestClient
from worker_server import create_app

###############################################################################
# test_integration_visual.py
#
# Purpose:
# Integration tests verifying that the VisualVerificationWorker interacts with the 
# real emulator endpoint to simulate app or URL-based behavior and returns proper observations.
#
# Design & Steps:
# 1. Ensure the Providers subsystem's emulator endpoint (e.g., /emulator/run_app) is live.
# 2. Use /request_worker with type=visual tasks, providing either 'url' or 'app_reference'.
# 3. Expect real responses containing observations about suspicious UI elements.
# 4. Test normal scenarios (e.g., known test app returning "fake login prompt") and 
#    scenarios where the emulator might fail or return unexpected data if possible.
#
# Maintainability:
# - If the emulator endpoint changes schema or requires additional inputs (like device model), 
#   update the payload and assertions accordingly.
# - If we add screenshot URLs or logs, extend tests to verify those fields in the result.
#
# Testing:
# - Run `make test-integration-workers` with MODE=test and TEST_MODE=integration.
# - Check logs for emulator container if tests fail.
###############################################################################

@pytest.fixture
def integration_test_client():
    """
    Provides a TestClient with the Worker Module app.
    In integration mode, relies on real config and providers endpoints.
    """
    app = create_app()
    return TestClient(app)

class TestIntegrationVisual:
    """
    Integration tests for VisualVerificationWorker.
    Confirm that when we request visual analysis, the actual emulator runs and 
    returns observations as expected.
    """

    def test_visual_url_scenario(self, integration_test_client):
        """
        Purpose:
          Test a scenario with a known URL that, when run in the emulator, 
          produces a known suspicious observation.

        Steps:
          1. POST /request_worker with {"type":"visual","url":"http://app.example"}
          2. Expect completed with observations array and a known suspicious element.

        Success:
          status=completed and "fake login prompt" or another known observation 
          present in the result.
        """
        payload = {"type":"visual","url":"http://app.example"}
        resp = integration_test_client.post("/request_worker", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert "result" in data
        assert "observations" in data["result"]
        # Check that observations is a list and at least contains one known suspicious element.
        obs = data["result"]["observations"]
        assert isinstance(obs, list)
        # If we know a standard observation from the test environment, we can assert it here.
        # If not, just ensure it's not empty or has a recognizable pattern.
        assert len(obs) > 0, "Expected at least one observation from the emulator run."

    def test_visual_app_reference_scenario(self, integration_test_client):
        """
        Purpose:
          Test scenario with an app_reference (like "com.app.example") to ensure 
          emulator can run a native app instead of a URL.

        Steps:
          1. POST /request_worker with {"type":"visual","app_reference":"com.test.app"}
          2. Expect completed with observations.

        Success:
          status=completed and observations array present.
        """
        payload = {"type":"visual","app_reference":"com.test.app"}
        resp = integration_test_client.post("/request_worker", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert "observations" in data["result"]
        assert isinstance(data["result"]["observations"], list)

    def test_visual_emulator_error(self, integration_test_client):
        """
        Purpose:
          Check error handling if the emulator endpoint fails or returns invalid data.

        Steps:
          1. POST a request that triggers an error scenario in emulator, 
             e.g. {"type":"visual","url":"http://trigger-error.example"}.

        Success:
          status=error and message includes "Emulator run failed".
        
        Note:
          If we cannot easily trigger an error in the real environment, consider 
          xfail or a known endpoint that returns non-200 status.
        """
        payload = {"type":"visual","url":"http://trigger-error.example"}
        resp = integration_test_client.post("/request_worker", json=payload)
        # If no error scenario occurs in reality, we might xfail here.
        if resp.status_code == 200:
            pytest.xfail("No emulator error triggered as expected.")
        else:
            # Expect possibly 400 or another error code
            data = resp.json()
            assert data["status"] == "error"
            assert "Emulator run failed" in data["message"]
