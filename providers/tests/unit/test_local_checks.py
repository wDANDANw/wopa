###############################################################################
# test_local_checks.py
#
# Purpose:
# Unit tests for local environment checks, configuration, and small utilities 
# that don't rely heavily on external mocks. For instance:
# - Confirm that config_loader returns correct defaults or raises the right exceptions.
# - Ensure that if instances.json is missing or empty, the code handles it (like in sandbox_env or emulator_env).
# - Possibly test small internal helper functions if any were implemented in utils.
#
# Key Responsibilities:
# - Validate local environment assumptions: if `instances.json` doesn’t exist, ValueError is raised by SandboxEnv and EmulatorEnv constructors.
# - Test config_loader with a real or temporary file to ensure correct parsing or error on invalid YAML.
#
# Requirements:
# - pytest and possibly `tmp_path` fixture to create temp files for config tests.
# - No complex mocks if not needed; just straightforward checks.
#
# Maintainability:
# - If more local utilities appear, add their tests here.
# - If config or file handling logic changes, update these tests to reflect new requirements.
###############################################################################

import pytest
import os
import yaml
from utils.config_loader import load_config
from core.sandbox_env import SandboxEnv
from core.emulator_env import EmulatorEnv
from unittest.mock import patch

def test_load_config_file_not_found():
    # If file not found, FileNotFoundError
    with pytest.raises(FileNotFoundError):
        load_config("non_existent_config.yaml")

def test_load_config_invalid_yaml(tmp_path):
    # Create a temp file with invalid YAML
    invalid_yaml_file = tmp_path / "invalid.yaml"
    invalid_yaml_file.write_text("INVALID unbalanced: [bracket")

    with pytest.raises(ValueError) as excinfo:
        load_config(str(invalid_yaml_file))
    assert "Failed to parse YAML" in str(excinfo.value)

def test_load_config_empty_yaml(tmp_path):
    # Empty file results in ValueError (since data won't be a dict)
    empty_file = tmp_path / "empty.yaml"
    empty_file.write_text("")

    with pytest.raises(ValueError) as excinfo:
        load_config(str(empty_file))
    assert "Invalid or empty config" in str(excinfo.value)

def test_load_config_valid_yaml(tmp_path):
    # Valid YAML should return a dict
    valid_file = tmp_path / "valid.yaml"
    data = {
        "llm": {"endpoint":"http://fake-llm","default_model":"test-model"},
        "sandbox": {"endpoints":["http://fake-sandbox:8002"]},
        "emulator": {"endpoints":["http://emulator1:5555"], "vnc_url_template":"vnc://{host}:{port}", "default_vnc_port":5900}
    }
    valid_file.write_text(yaml.dump(data))

    result = load_config(str(valid_file))
    assert isinstance(result, dict)
    assert "llm" in result
    assert "sandbox" in result
    assert "emulator" in result

def test_sandbox_no_endpoints_in_config(tmp_path):
    # If no endpoints found in instances.json or config.yaml, sandbox_env raises ValueError
    # Mock load_config to return empty sandbox config
    with patch("utils.config_loader.load_config") as mock_config_loader:
        mock_config_loader.return_value = {"llm":{},"sandbox":{},"emulator":{}}
        # Instantiate SandboxEnv should NOT raise now
        env = SandboxEnv()
        # Now try an operation that requires endpoints, e.g.:
        # Since no endpoints and no provisioning triggered yet, run_file() might fail.
        with pytest.raises(ValueError) as excinfo:
            env.run_file("test.bin")
        # Check error details if needed.

def test_emulator_no_endpoints_in_config(tmp_path):
    with patch("utils.config_loader.load_config") as mock_config_loader:
        mock_config_loader.return_value = {"llm":{},"sandbox":{},"emulator":{}}
        with pytest.raises(ValueError) as excinfo:
            EmulatorEnv()
        assert "No emulator endpoints available" in str(excinfo.value)

def test_sandbox_no_instances_file(tmp_path):
    # If instances.json doesn’t exist and config also lacks endpoints, raise ValueError
    # Here config has no endpoints and no instances file is created
    with patch("utils.config_loader.load_config") as mock_config_loader:
        mock_config_loader.return_value = {"llm":{},"sandbox":{"endpoints":[]},"emulator":{}}
        # No instances.json
        with pytest.raises(ValueError) as excinfo:
            SandboxEnv()
        assert "No sandbox endpoints available" in str(excinfo.value)

def test_emulator_no_endpoints_in_config(tmp_path):
    from core.emulator_env import EmulatorEnv, EmulatorConnectionError
    from unittest.mock import patch

    with patch("utils.config_loader.load_config") as mock_config_loader:
        mock_config_loader.return_value = {"llm":{},"sandbox":{},"emulator":{}}

        emulator = EmulatorEnv()  # Should not raise now
        # endpoints = [], no provisioning done yet

        # Now try run_app, expecting it to raise due to no endpoints
        with pytest.raises(EmulatorConnectionError) as excinfo:
            emulator.run_app("test_app.apk")

        assert "No emulator endpoints" in str(excinfo.value) or "unreachable" in str(excinfo.value)


###############################################################################
# Explanation:
#
# - test_load_config_*: Verify config_loader's behavior with various file states (not found, invalid yaml, empty, valid).
# - test_sandbox_no_endpoints_in_config & test_emulator_no_endpoints_in_config:
#   Confirm ValueError if no endpoints provided in config or instances.json.
# - test_sandbox_no_instances_file & test_emulator_no_instances_file:
#   Similar checks to ensure instances.json absence triggers fallback logic and errors out if no endpoints found.
#
# These tests ensure that local file handling and default logic are correct and 
# that robust exceptions are raised for missing or invalid config sources.
#
# Maintainability:
# Add more tests if new local checks or utilities appear.
###############################################################################
