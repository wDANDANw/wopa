"""
test_config_display.py

**Test File: T-Services-Config-005**

**Purpose:**
Ensure that the service subsystem correctly loads and displays its configuration via the /configs endpoint.  
Configuration is central to adaptability and maintainability, so verifying that the system can:
- Load `services_config.yaml` or equivalent from config_loader.py.
- Integrate these configs into `service_manager` so that /configs returns a JSON view.
- Reflect changes or mocks to config in responses.

**Context:**
- The config might contain endpoints for workers, thresholds, and other service-specific parameters.
- By testing /configs, we ensure that the system is transparent about its current operational parameters.

**Design & Approach:**
- Use `pytest` and `fastapi.testclient` to GET /configs.
- Check response code (200), data type (dict), and presence of expected keys.
- If needed, mock the `ConfigLoader` to return a known dictionary and confirm `/configs` returns exactly that.
- This ensures that from a unit perspective, if config loading logic or data changes, we detect discrepancies easily.

**Prerequisites:**
- `service_manager.py` sets up the `/configs` endpoint calling `service_manager.get_current_config()` or similar method.
- `config_loader.py` properly loads config into memory at startup.
- For unit tests, if external files are problematic, we can mock `ConfigLoader.get_config()` to return a predefined dict.

**Success Criteria:**
- `/configs` returns 200 and a JSON dict.
- The dict matches either a known minimal config or keys that we expect from a standard config scenario.
- If config_loader is mocked, the returned configs should match the mock exactly.

This is our last test file. After this, we shall start our implementation.

"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from service_manager import app

@pytest.fixture(scope="module")
def test_client():
    return TestClient(app)

def test_configs_endpoint_structure(test_client):
    """
    T-Services-Config-005-PartA

    Purpose:
    Check that /configs returns a well-formed JSON dict.

    Steps:
    - GET /configs without mocking anything initially
    - Expect HTTP 200
    - Expect JSON response to be a dict

    Even if empty or minimal, must be a dict.

    Success Criteria:
    200 status, data is a dict.
    """
    response = test_client.get("/configs")
    assert response.status_code == 200, "Should return 200 for /configs"
    data = response.json()
    assert isinstance(data, dict), "Expected configs endpoint to return a JSON dictionary"


@patch("utils.config_loader.ConfigLoader.get_config")
def test_configs_endpoint_with_mock(mock_get_config, test_client):
    """
    T-Services-Config-005-PartB

    Purpose:
    Mock the config loader to return a known dictionary and ensure /configs matches it.

    Steps:
    - Mock get_config to return a known config dict, e.g.:
      {
        "link_analyzer": {
          "text_worker":"http://text_worker:8000",
          "link_worker":"http://link_worker:8000",
          "sandbox_threshold": 0.8
        },
        "message_analyzer":{
          "text_worker":"http://text_worker:8000",
          "spam_threshold":0.7
        }
      }
    - GET /configs
    - Check response matches the mock exactly or at least contains these keys

    Success Criteria:
    The returned JSON includes these keys and values from the mock.
    """
    # Define a mock config:
    mock_config = {
        "link_analyzer": {
            "text_worker":"http://text_worker:8000",
            "link_worker":"http://link_worker:8000",
            "sandbox_threshold":0.8
        },
        "message_analyzer":{
            "text_worker":"http://text_worker:8000",
            "spam_threshold":0.7
        }
    }

    # Mock get_config method:
    # If the actual code calls get_config(service_name) repeatedly, we might need to handle that logic:
    # Let's assume service_manager aggregates configs from get_config calls per service_name.
    # Another approach: If get_config is used per service:
    # We can either:
    # 1. Mock get_config(service_name) to return sub-config
    # Or 2. If code is written differently, we adapt accordingly.
    #
    # For simplicity, let's assume service_manager uses something like:
    # configs = { "link_analyzer": cl.get_config("link_analyzer"), "message_analyzer": cl.get_config("message_analyzer") }
    #
    # In that case, each call to get_config(service_name) returns sub-config:
    # We'll handle this by side_effect based on input param:
    def mock_get_config_side_effect(service_name):
        return mock_config.get(service_name, {})

    mock_get_config.side_effect = mock_get_config_side_effect

    response = test_client.get("/configs")
    assert response.status_code == 200
    data = response.json()
    assert "link_analyzer" in data, "Expected 'link_analyzer' key in config"
    assert "message_analyzer" in data, "Expected 'message_analyzer' key in config"

    # Check nested keys:
    la = data["link_analyzer"]
    assert la["text_worker"] == "http://text_worker:8000"
    assert la["link_worker"] == "http://link_worker:8000"
    assert la["sandbox_threshold"] == 0.8

    ma = data["message_analyzer"]
    assert ma["text_worker"] == "http://text_worker:8000"
    assert ma["spam_threshold"] == 0.7

    # This confirms the endpoint reflects the mocked config.


@patch("utils.config_loader.ConfigLoader.get_config")
def test_configs_endpoint_empty_config(mock_get_config, test_client):
    """
    T-Services-Config-005-PartC

    Purpose:
    Test scenario where config returns empty dict (no services configured).

    Steps:
    - Mock get_config to return empty dict for any service_name.
    - The final configs might be empty or minimal.
    - Check response still 200 and dict (maybe empty).

    Success Criteria:
    /configs returns a dict (maybe empty). This shows system handles no-config scenario gracefully.
    """
    def empty_side_effect(service_name):
        return {}

    mock_get_config.side_effect = empty_side_effect

    response = test_client.get("/configs")
    assert response.status_code == 200
    data = response.json()
    # Data might be empty or have no keys.
    assert isinstance(data, dict), "Even if empty, must be a dict"
    # If the system attempts to load known services but returns empty, we may see empty or partial results.
    # Just ensure no crash and a dict returned.


def test_configs_endpoint_invalid_method(test_client):
    """
    T-Services-Config-005-PartD

    Purpose:
    Try a non-GET method like POST on /configs to ensure it's not allowed.

    Steps:
    - POST /configs
    - Expect method not allowed (405 or similar).

    Success Criteria:
    HTTP 405 (Method Not Allowed).
    """
    response = test_client.post("/configs", json={})
    # If not defined, typically returns 405
    assert response.status_code == 405, "Only GET should be allowed for /configs"


"""
Additional Notes:

- We have tested the /configs endpoint under normal conditions, with mocking, empty configs, and invalid HTTP methods.
- If the config structure or retrieval logic evolves, update these tests accordingly.
- The tests ensure that from a unit perspective, config loading and display is stable and understandable.

This is the last test file. After this, we can begin implementing the actual code and logic in the services subsystem.
"""
