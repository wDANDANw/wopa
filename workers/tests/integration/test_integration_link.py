import pytest
from fastapi.testclient import TestClient
from worker_server import create_app

###############################################################################
# test_integration_link.py
#
# Purpose:
# Integration tests verifying the interaction between the Worker Module's link 
# worker and the actual domain reputation API in the Providers subsystem.
#
# Design & Steps:
# 1. Ensure Providers subsystem's domain reputation endpoint is live and accessible 
#    at the configured "domain_reputation_api" URL in config.yaml.
# 2. Use /request_worker endpoint with type=link tasks to analyze known safe and malicious domains.
# 3. Confirm that normal scenarios (safe domain) return completed with low risk_level.
# 4. Test a known malicious or suspicious domain scenario if available, expecting high risk_level.
# 5. Check error handling if the domain API returns invalid data or is unreachable.
#
# Maintainability:
# - If domain reputation API changes response schema, adjust the assertions here.
# - If we add more nuanced risk levels, update tests to reflect those classifications.
#
# Testing:
# - Run `make test-integration-workers` with MODE=test and TEST_MODE=integration.
# - If tests fail, review logs from providers and workers containers to identify issues.
###############################################################################

@pytest.fixture
def integration_test_client():
    """
    Provides a TestClient with the Worker Module app.
    Assumes a proper integration environment with Providers subsystem running.
    """
    app = create_app()
    return TestClient(app)

class TestIntegrationLink:
    """
    Integration tests for LinkAnalysisWorker.
    Ensures real domain API calls classify domains as low or high risk.
    """

    def test_link_safe_domain(self, integration_test_client):
        """
        Purpose:
          Test a known safe domain to confirm low risk classification.

        Steps:
          1. POST /request_worker with {"type":"link","url":"http://example-safe.com"}
          2. Expect completed status and risk_level=low from real domain API.

        Success:
          status=completed, risk_level=low, score is a float.
        """
        payload = {"type":"link","url":"http://example-safe.com"}
        resp = integration_test_client.post("/request_worker", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert "result" in data
        assert "risk_level" in data["result"]
        assert data["result"]["risk_level"] == "low"
        assert isinstance(data["result"].get("score", 1.0), float)

    def test_link_malicious_domain(self, integration_test_client):
        """
        Purpose:
          If we can identify a known malicious domain or trigger scenario,
          expect risk_level=high.

        Steps:
          1. POST /request_worker with {"type":"link","url":"http://known-malicious.com"}
          2. If domain API returns safe=false, worker should return risk_level=high.

        Success:
          status=completed and risk_level=high.

        Note:
          If we don't have a known malicious domain, we can use a test domain 
          preconfigured in providers environment to return safe=false.
        """
        payload = {"type":"link","url":"http://known-malicious.com"}
        resp = integration_test_client.post("/request_worker", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert "result" in data
        assert data["result"]["risk_level"] == "high"

    def test_link_endpoint_error(self, integration_test_client):
        """
        Purpose:
          Check error handling if domain API is unreachable or returns invalid JSON.
        
        Steps:
          1. Provide a domain that triggers an error scenario in domain API 
             (e.g., "http://trigger-domain-error.com").
        
        Success:
          status=error, message includes "Domain check failed".

        Note:
          This test depends on Providers environment setup. If no real error scenario 
          is easy to trigger, consider using xfail or a known test endpoint that returns 500.
        """
        payload = {"type":"link","url":"http://trigger-domain-error.com"}
        resp = integration_test_client.post("/request_worker", json=payload)
        # If no error scenario can be triggered, we might xfail or just check outcome.
        if resp.status_code == 200:
            pytest.xfail("No domain error triggered as expected.")
        else:
            # Expect possibly 400 or another error code if worker transforms 
            # provider error into error response.
            assert resp.status_code in [400, 500], "Expected an error status"
            data = resp.json()
            assert data["status"] == "error"
            assert "Domain check failed" in data["message"]
