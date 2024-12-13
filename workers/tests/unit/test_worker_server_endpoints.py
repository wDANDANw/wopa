import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Import the create_app function from worker_server
from worker_server import create_app

###############################################################################
# test_worker_server_endpoints.py
#
# Purpose:
# Tests all server endpoints defined in worker_server.py at the unit level.
# Focuses on verifying:
# - Correct HTTP status codes for normal and error conditions
# - JSON structures in responses
# - Validation errors on missing fields
# - Integration with mocked WorkerManager and workers (no real provider calls)
#
# Design & Steps:
# 1. Use pytest and FastAPI’s TestClient to simulate HTTP requests.
# 2. Mock `load_config()` to ensure stable config is always returned.
# 3. Patch WorkerManager methods and worker processing if needed, ensuring 
#    endpoints handle various scenarios correctly.
# 4. Check endpoints like /configs, /workers, /enqueue_task, /request_worker, 
#    /tasks, /get_worker_results, and /admin.
#
# Maintainability:
# - If new endpoints are added or changed, add or update tests accordingly.
# - If WorkerManager logic changes, update mocks to reflect new return values.
# - Keep test names descriptive: test_{endpoint}_{scenario}.
#
# Testing:
# - Run with `make test-unit-workers` using MODE=unit-test.
# - If tests fail, logs in CI output guide quick fixes.
###############################################################################

@pytest.fixture
def test_client():
    """
    Pytest fixture that creates a TestClient for the worker app.
    Mocks load_config to return a stable config.
    """
    with patch("utils.config_loader.load_config") as mock_config:
        mock_config.return_value = {
            "worker_types": ["text","link","visual"]
        }
        app = create_app()
        client = TestClient(app)
        yield client

class TestWorkerServerEndpoints:
    """
    Test suite for server endpoints.
    These tests ensure endpoints return expected responses for both valid 
    and invalid inputs and handle mocked WorkerManager interactions properly.
    """

    def test_configs_endpoint(self, test_client):
        """
        T-Worker-Server-Config-001
        Purpose:
          Check /configs returns the mocked config dictionary.
        Steps:
          1. GET /configs
          2. Expect 200 and a JSON with 'worker_types' key.
        Success:
          Worker_types present and matches mock return.
        """
        resp = test_client.get("/configs")
        assert resp.status_code == 200
        data = resp.json()
        assert "worker_types" in data
        assert data["worker_types"] == ["text","link","visual"]

    def test_workers_endpoint(self, test_client):
        """
        T-Worker-Server-Workers-001
        Purpose:
          Verify /workers lists worker types from config.
        Steps:
          1. GET /workers
          2. Expect 200 and ["text","link","visual"]
        Success:
          Matches known workers.
        """
        resp = test_client.get("/workers")
        assert resp.status_code == 200
        workers = resp.json()
        assert workers == ["text","link","visual"]

    @patch("core.worker_manager.WorkerManager.enqueue_task", return_value="abc123")
    def test_enqueue_task_valid(self, mock_enqueue, test_client):
        """
        T-Worker-Server-Enqueue-001
        Purpose:
          Check that /enqueue_task enqueues tasks correctly.
        Steps:
          1. POST a valid task: {"type":"text","content":"hello"}
          2. Expect 200 and {"task_id":"abc123","status":"enqueued"}
        Success:
          Task_id is returned and status = enqueued.
        """
        resp = test_client.post("/enqueue_task", json={"type":"text","content":"hello"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "enqueued"
        assert data["task_id"] == "abc123"

    def test_enqueue_task_missing_type(self, test_client):
        """
        Purpose:
          If 'type' field is missing, /enqueue_task should return 400 error.
        Steps:
          1. POST {} (no type)
          2. Expect 400 and error message
        Success:
          Endpoint returns an error JSON.
        """
        resp = test_client.post("/enqueue_task", json={})
        assert resp.status_code == 400
        data = resp.json()
        assert "detail" in data
        assert "Missing 'type' field" in data["detail"]

    @patch("core.worker_manager.WorkerManager.process_task")
    def test_request_worker_valid(self, mock_process, test_client):
        """
        T-Worker-Server-Request-001
        Purpose:
          Check /request_worker with a valid link task that returns completed result.
        Steps:
          1. Mock process_task to return completed result
          2. POST a link task {"type":"link","url":"http://example.com"}
          3. Expect 200 and completed result.
        Success:
          status=completed and result present.
        """
        mock_process.return_value = {
            "status": "completed",
            "result": {"risk_level":"low","score":0.1},
            "task_id":"xyz789"
        }
        resp = test_client.post("/request_worker", json={"type":"link","url":"http://example.com"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert "result" in data
        assert data["result"]["risk_level"] == "low"
        assert data["task_id"] == "xyz789"

    def test_request_worker_missing_type(self, test_client):
        """
        T-Worker-Server-Request-002
        Purpose:
          If 'type' is missing, return 400 error on /request_worker.
        Steps:
          1. POST with no 'type'
          2. Expect 400 error
        Success:
          Proper error detail returned.
        """
        resp = test_client.post("/request_worker", json={"url":"http://example.com"})
        assert resp.status_code == 422
        data = resp.json()
        assert "detail" in data
        assert "Missing 'type' field" in data["detail"]

    @patch("core.worker_manager.WorkerManager.list_all_tasks", return_value=[{"task_id":"t123","status":"completed"}])
    def test_tasks_endpoint(self, mock_list, test_client):
        """
        T-Worker-Server-Tasks-001
        Purpose:
          /tasks returns a list of tasks and statuses.
        Steps:
          1. Mock list_all_tasks return a sample list
          2. GET /tasks
          3. Expect 200 and the mocked list
        Success:
          Matches mocked tasks data.
        """
        resp = test_client.get("/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert any(t["task_id"]=="t123" for t in data)

    @patch("core.worker_manager.WorkerManager.get_task_result", return_value={"status":"completed","result":{"detail":"ok"}})
    def test_get_worker_results_valid(self, mock_get_result, test_client):
        """
        T-Worker-Server-Results-001
        Purpose:
          Confirm /get_worker_results returns final results for a known task.
        Steps:
          1. Mock get_task_result with completed result
          2. GET /get_worker_results?task_id=abc
          3. Expect 200 and completed result
        Success:
          Matches mocked completed result.
        """
        resp = test_client.get("/get_worker_results?task_id=abc")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert "result" in data
        assert data["result"]["detail"] == "ok"

    @patch("core.worker_manager.WorkerManager.get_task_result", return_value=None)
    def test_get_worker_results_not_found(self, mock_get_result, test_client):
        """
        Purpose:
          If no task found, /get_worker_results returns 404.
        Steps:
          1. Mock get_task_result returns None
          2. GET /get_worker_results?task_id=xyz
          3. Expect 404 and 'Task not found'
        Success:
          Proper not found error.
        """
        resp = test_client.get("/get_worker_results?task_id=xyz")
        assert resp.status_code == 404
        data = resp.json()
        assert "detail" in data
        assert "Task not found" in data["detail"]

    def test_admin_ui(self, test_client):
        """
        T-Worker-Server-UI-001
        Purpose:
          Check /admin returns the Gradio HTML UI.
        Steps:
          1. GET /admin
          2. Expect 200 and HTML (just check if content-type text/html or presence of <html>).
        Success:
          Returns 200 and some HTML structure.
        """
        resp = test_client.get("/admin")
        assert resp.status_code == 200
        # Check if response content likely HTML (just a minimal check)
        assert "<html" in resp.text.lower()

