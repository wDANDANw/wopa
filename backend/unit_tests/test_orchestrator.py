import pytest
from unittest.mock import patch

###############################################################################
# Test File: test_orchestrator.py
#
# Focus:
# - Unit testing the internal logic of core/orchestrator.py, specifically:
#   - T-Backend-Message-001 (indirect)
#   - T-Backend-Link-001 (indirect)
#   - T-Backend-File-001 (indirect)
#   - T-Backend-App-001 (indirect)
#
# Although we tested endpoints and request_handler separately, the orchestrator 
# is where task creation logic decides which connector to invoke based on task type.
# This is crucial to ensure that when a new AnalysisTask is created, the right 
# external service is contacted.
#
# Philosophy:
# (T)est-based verification. We'll mock connectors and ensure that given a 
# particular task type, the orchestrator calls the expected connector function.
#
# Maintainability:
# - Clear docstrings and step-by-step approach.
# - Each test scenario focuses on a single task type, making it easy to update 
#   if we add new task types or connectors.
#
# Prerequisites:
# - Orchestrator and AnalysisTask model from data_models or similar.
# - Connectors must be mocked so we don't do real network calls.
###############################################################################


@pytest.fixture
def orchestrator_instance(mocker):
    """
    Creates an instance of AnalysisOrchestrator with mocked environment or config.
    If orchestrator relies on config_loader.get_env, we mock them as needed.
    """
    mocker.patch("core.config_loader.get_env", side_effect=lambda k: "test-value")
    from core.orchestrator import AnalysisOrchestrator
    orchestrator = AnalysisOrchestrator()
    return orchestrator


@pytest.fixture
def mock_connectors(mocker):
    """
    Mock all connector methods that might be called by the orchestrator:
    - message_service_connector.analyze_message
    - link_service_connector.analyze_link
    - file_service_connector.analyze_file
    - app_service_connector.analyze_app

    Returns a dictionary with references to these mocks so we can assert calls.
    """
    mocks = {}
    mocks["msg"] = mocker.patch("connectors.message_service_connector.analyze_message", return_value="msg-task-ref")
    mocks["link"] = mocker.patch("connectors.link_service_connector.analyze_link", return_value="link-task-ref")
    mocks["file"] = mocker.patch("connectors.file_service_connector.analyze_file", return_value="file-task-ref")
    mocks["app"] = mocker.patch("connectors.app_service_connector.analyze_app", return_value="app-task-ref")
    return mocks


@pytest.fixture
def sample_tasks():
    """
    Provides sample AnalysisTask dicts for message, link, file, and app tasks.
    We assume AnalysisTask schema might look like:
    {
      "type": "message" or "link" or "file" or "app",
      "content": "some content",
      "timestamp": "2024-10-24T12:00:00Z"
    }
    """
    return {
        "message_task": {"type":"message", "content":"Suspicious text", "timestamp":"2024-10-24T12:00:00Z"},
        "link_task": {"type":"link", "content":"http://phish.url", "timestamp":"2024-10-24T12:00:00Z"},
        "file_task": {"type":"file", "content":"file_ref_id", "timestamp":"2024-10-24T12:00:00Z"},
        "app_task": {"type":"app", "content":"app_ref_id", "timestamp":"2024-10-24T12:00:00Z"}
    }


###############################################################################
# Test: T-Backend-Message-001 (Indirect via orchestrator)
#
# Purpose:
# When create_task is called with a message task, it should call 
# message_service_connector.analyze_message and return some reference/task_id.
#
# Steps:
# 1) create_task with a message_task
# 2) Check if message connector was called with correct content
# 3) Check returned task_id is from connector
#
# Success:
# - Connector called once with content = "Suspicious text"
# - create_task returns "msg-task-ref" or at least not empty
###############################################################################
def test_orchestrator_create_message_task(orchestrator_instance, mock_connectors, sample_tasks):
    msg_task_data = sample_tasks["message_task"]
    task_id = orchestrator_instance.create_task(msg_task_data)
    mock_connectors["msg"].assert_called_once_with("Suspicious text")
    assert task_id == "msg-task-ref", "Expected orchestrator to return connector’s ref"


###############################################################################
# T-Backend-Link-001 (Indirect)
#
# Purpose:
# For a link task, orchestrator calls link_service_connector.analyze_link.
#
# Steps:
# 1) create_task with link_task data
# 2) verify link connector called with (url, visual_verify)
#
# But we notice our link_task_data only has 'content' = "http://phish.url"
# The orchestrator might default visual_verify=False if not specified. 
# If visual_verify is required, we must ensure orchestrator sets a default.
#
# Success:
# - link_service_connector.analyze_link called with "http://phish.url" and False
# - returns "link-task-ref"
###############################################################################
def test_orchestrator_create_link_task(orchestrator_instance, mock_connectors, sample_tasks):
    link_task_data = sample_tasks["link_task"]
    # If orchestrator sets defaults, we trust that. If we must specify, we can add:
    # link_task_data["visual_verify"] = False if orchestrator expects it.
    # For now, assume orchestrator defaults visual_verify=False if absent.
    task_id = orchestrator_instance.create_task(link_task_data)
    mock_connectors["link"].assert_called_once_with("http://phish.url", False)
    assert task_id == "link-task-ref"


###############################################################################
# T-Backend-File-001 (Indirect)
#
# Purpose:
# For a file task, orchestrator calls file_service_connector.analyze_file.
#
# Steps:
# 1) create_task with file_task
# 2) verify file connector called with "file_ref_id"
#
# Success:
# - file connector called with "file_ref_id"
# - returns "file-task-ref"
###############################################################################
def test_orchestrator_create_file_task(orchestrator_instance, mock_connectors, sample_tasks):
    file_task_data = sample_tasks["file_task"]
    task_id = orchestrator_instance.create_task(file_task_data)
    mock_connectors["file"].assert_called_once_with("file_ref_id")
    assert task_id == "file-task-ref"


###############################################################################
# T-Backend-App-001 (Indirect)
#
# Purpose:
# For an app task, orchestrator calls app_service_connector.analyze_app.
#
# Steps:
# 1) create_task with app_task
# 2) verify app connector called with "app_ref_id"
#
# Success:
# - app connector called with "app_ref_id"
# - returns "app-task-ref"
###############################################################################
def test_orchestrator_create_app_task(orchestrator_instance, mock_connectors, sample_tasks):
    app_task_data = sample_tasks["app_task"]
    task_id = orchestrator_instance.create_task(app_task_data)
    mock_connectors["app"].assert_called_once_with("app_ref_id")
    assert task_id == "app-task-ref"


###############################################################################
# Additional Scenario:
#
# What if orchestrator receives an unknown task type?
# Let's add a negative test to ensure it handles it gracefully (maybe raises ValueError).
#
# This covers a robustness scenario. Not explicitly in the previous test plan,
# but good for maintainability.
###############################################################################
def test_orchestrator_unknown_task_type(orchestrator_instance, mock_connectors):
    unknown_task = {"type":"unknown","content":"data","timestamp":"..."}
    # Expect orchestrator to raise an exception or handle error.
    # We must know orchestrator's behavior. Assume it raises ValueError.
    with pytest.raises(ValueError, match="Unknown task type"):
        orchestrator_instance.create_task(unknown_task)

    # No connector should be called
    mock_connectors["msg"].assert_not_called()
    mock_connectors["link"].assert_not_called()
    mock_connectors["file"].assert_not_called()
    mock_connectors["app"].assert_not_called()


###############################################################################
# Logging and error handling in orchestrator:
#
# If we want, we can simulate connector raising an exception and see if 
# orchestrator logs or re-raises it. Similar to test_api_routes,
# but here we ensure orchestrator doesn't hide errors.
###############################################################################
def test_orchestrator_connector_failure(orchestrator_instance, mocker, sample_tasks, caplog):
    # Simulate failure in message connector
    mock_fail = mocker.patch("connectors.message_service_connector.analyze_message",
                             side_effect=Exception("Connector error"))
    with pytest.raises(Exception, match="Connector error"):
        orchestrator_instance.create_task(sample_tasks["message_task"])

    mock_fail.assert_called_once_with("Suspicious text")
    # If orchestrator logs errors, we can check caplog here. Otherwise, just confirmed exception re-raised.


###############################################################################
# Conclusion:
#
# This file tests orchestrator logic thoroughly:
# - Confirm correct connector calls for each task type.
# - Check handling of unknown task types.
# - Check behavior on connector failure.
#
# This should cover orchestrator's main responsibilities.
#
# Since user requested to be notified at the end, here it is:
#
# *** Notification: This is the last test file *** 
#
# After providing test_backend_server.py, test_api_routes.py, test_request_handler.py,
# and now test_orchestrator.py, we have shown a comprehensive approach.
#
# We can now proceed to the actual implementation phase as requested.
###############################################################################
