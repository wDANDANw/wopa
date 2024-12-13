import pytest
from unittest.mock import patch, MagicMock

# Assume we can import workers and worker_manager for direct testing
from core.worker_manager import WorkerManager
from text_analysis.text_analysis_worker import TextAnalysisWorker
from link_analysis.link_analysis_worker import LinkAnalysisWorker
from visual_verification.visual_verification_worker import VisualVerificationWorker

###############################################################################
# test_worker_manager_and_workers.py
#
# Purpose:
# This file tests WorkerManager logic and each worker class at the unit level.
# Focuses on:
# - WorkerManager's enqueue_task, process_task, store_result, list_all_tasks, get_task_result.
# - Worker validation and processing logic (Text, Link, Visual) with mocks for external calls.
#
# Design & Steps:
# 1. Create mock config and worker_map fixtures to pass into WorkerManager.
# 2. For each worker (Text, Link, Visual), test validate_task with missing fields.
# 3. Test process methods with normal and error scenarios by mocking requests calls.
# 4. Test WorkerManager process_task selecting correct worker and handling exceptions.
# 5. Ensure store_result and retrieval methods in WorkerManager work as expected.
#
# Maintainability:
# - If a new worker is added, add similar tests for validate and process logic.
# - If WorkerManager logic changes, update tests accordingly.
#
# Testing:
# - Run `make test-unit-workers` with MODE=unit-test inside container.
# - If tests fail, logs show which scenario broke.
###############################################################################

@pytest.fixture
def mock_config():
    """
    Fixture that returns a mocked config dictionary with endpoints and worker_types.
    Adjust this if new endpoints appear.
    """
    return {
        "worker_types": ["text","link","visual"],
        "llm_endpoint": "http://fake-llm",
        "domain_reputation_api": "http://fake-domain-api",
        "emulator_endpoint": "http://fake-emulator"
    }

@pytest.fixture
def workers_map(mock_config):
    """
    Creates instances of each worker with the mocked config.
    """
    text_worker = TextAnalysisWorker(mock_config)
    link_worker = LinkAnalysisWorker(mock_config)
    visual_worker = VisualVerificationWorker(mock_config)
    return {
        "text": text_worker,
        "link": link_worker,
        "visual": visual_worker
    }

@pytest.fixture
def manager(mock_config, workers_map):
    """
    Creates a WorkerManager instance for testing manager logic.
    """
    mgr = WorkerManager(config=mock_config, worker_map=workers_map)
    return mgr

class TestWorkerManagerAndWorkers:
    """
    Test suite for WorkerManager logic and individual worker classes.
    """

    # Testing validation logic of each worker:

    def test_text_worker_validate_missing_content(self, workers_map):
        """
        T-Worker-Text-Validate-001
        Purpose:
          Text worker requires 'content'.
        Steps:
          validate_task({"type":"text"}) → expect error dict
        Success:
          Returns {"error":"missing content ..."}
        """
        w = workers_map["text"]
        val = w.validate_task({"type":"text"})
        assert val is not None
        assert "error" in val
        assert "missing content" in val["error"]

    def test_text_worker_process_normal(self, workers_map):
        """
        T-Worker-Text-Process-001
        Purpose:
          Normal scenario for text worker with mocked LLM response.
        Steps:
          Mock requests.post to return classification "phishing".
          w.process({"type":"text","content":"Check this"}) → completed.
        Success:
          Returns completed with classification and confidence.
        """
        w = workers_map["text"]
        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"classification":"phishing","confidence":0.95}
            mock_post.return_value.raise_for_status = MagicMock()
            res = w.process({"type":"text","content":"Check this"})
            assert res["status"] == "completed"
            assert res["result"]["classification"] == "phishing"
            assert res["result"]["confidence"] == 0.95

    def test_text_worker_process_error(self, workers_map):
        """
        T-Worker-Text-Error-001
        Purpose:
          If LLM endpoint fails, return error.
        Steps:
          requests.post raises Exception("LLM failed")
          Expect status=error and message with 'LLM failed'.
        """
        w = workers_map["text"]
        with patch("requests.post", side_effect=Exception("LLM failed")):
            res = w.process({"type":"text","content":"fail scenario"})
            assert res["status"] == "error"
            assert "LLM failed" in res["message"]

    def test_link_worker_validate_missing_url(self, workers_map):
        """
        T-Worker-Link-Validate-001
        Purpose:
          Link worker requires 'url'.
        Steps:
          w.validate_task({"type":"link"}) no url → error
        """
        w = workers_map["link"]
        val = w.validate_task({"type":"link"})
        assert val is not None
        assert "error" in val
        assert "missing url" in val["error"]

    def test_link_worker_process_safe_domain(self, workers_map):
        """
        T-Worker-Link-Process-001
        Purpose:
          Normal scenario: safe domain returns low risk.
        Steps:
          Mock requests.get returns {"safe":true,"score":0.1}
          Expect completed with risk_level=low
        """
        w = workers_map["link"]
        with patch("requests.get") as mock_get:
            mock_get.return_value.json.return_value = {"safe":True,"score":0.1}
            mock_get.return_value.raise_for_status = MagicMock()
            res = w.process({"type":"link","url":"http://safe.com"})
            assert res["status"] == "completed"
            assert res["result"]["risk_level"] == "low"
            assert res["result"]["score"] == 0.1

    def test_link_worker_process_error(self, workers_map):
        """
        T-Worker-Link-Error-001
        Purpose:
          If domain API fails, return error.
        Steps:
          requests.get raises Exception("Domain check failed")
          Expect status=error and message containing "Domain check failed"
        """
        w = workers_map["link"]
        with patch("requests.get", side_effect=Exception("Domain failed")):
            res = w.process({"type":"link","url":"http://bad.com"})
            assert res["status"] == "error"
            assert "Domain check failed" in res["message"]

    def test_visual_worker_validate_missing_refs(self, workers_map):
        """
        T-Worker-Visual-Validate-001
        Purpose:
          Visual worker requires 'url' or 'app_reference'.
        Steps:
          validate_task({"type":"visual"}) no url/app → error
        """
        w = workers_map["visual"]
        val = w.validate_task({"type":"visual"})
        assert val is not None
        assert "error" in val
        assert "missing url or app_reference" in val["error"]

    def test_visual_worker_process_normal(self, workers_map):
        """
        T-Worker-Visual-Process-001
        Purpose:
          Normal scenario for visual worker.
        Steps:
          Mock requests.post returns {"observations":["fake login prompt"]}
          Expect completed with observations.
        """
        w = workers_map["visual"]
        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"observations":["fake login prompt"]}
            mock_post.return_value.raise_for_status = MagicMock()
            res = w.process({"type":"visual","url":"http://app.example"})
            assert res["status"] == "completed"
            assert "observations" in res["result"]
            assert "fake login prompt" in res["result"]["observations"]

    def test_visual_worker_process_error(self, workers_map):
        """
        T-Worker-Visual-Error-001
        Purpose:
          If emulator endpoint fails, return error.
        Steps:
          requests.post raises Exception
          Expect status=error and message containing "Emulator run failed"
        """
        w = workers_map["visual"]
        with patch("requests.post", side_effect=Exception("Emu failed")):
            res = w.process({"type":"visual","url":"http://bad-app.example"})
            assert res["status"] == "error"
            assert "Emulator run failed" in res["message"]

    # Testing WorkerManager logic:

    def test_manager_enqueue_task(self, manager):
        """
        Purpose:
          manager.enqueue_task creates a new task_id with status enqueued.
        Steps:
          call enqueue_task with sample task_data.
          Check returned task_id and storage entry.
        """
        t_id = manager.enqueue_task({"type":"text","content":"hello"})
        assert t_id in manager.tasks_storage
        assert manager.tasks_storage[t_id]["status"] == "enqueued"

    def test_manager_process_task_correct_worker(self, manager):
        """
        T-Worker-Manager-Process-001
        Purpose:
          process_task chooses correct worker and returns completed result.
        Steps:
          Patch text worker process to return completed
          call manager.process_task({"type":"text","content":"Check"})
        """
        text_worker = manager.worker_map["text"]
        with patch.object(text_worker, 'process', return_value={"status":"completed","result":{"classification":"phishing","confidence":0.95}}):
            result = manager.process_task({"type":"text","content":"Check"})
            assert result["status"] == "completed"
            assert "task_id" in result
            tid = result["task_id"]
            assert tid in manager.tasks_storage
            assert manager.tasks_storage[tid]["result"]["classification"] == "phishing"

    def test_manager_process_task_unknown_type(self, manager):
        """
        If worker type is unknown, return error.
        Steps:
          process_task({"type":"unknown"})
          Expect status=error
        """
        result = manager.process_task({"type":"unknown"})
        assert result["status"] == "error"
        assert "Unknown worker type" in result["message"]

    def test_manager_process_task_validation_error(self, manager):
        """
        If validation fails (e.g. text worker missing content), return error.
        Steps:
          Patch text worker validate_task to return error dict.
          process_task({"type":"text"}) → error
        """
        text_worker = manager.worker_map["text"]
        with patch.object(text_worker, 'validate_task', return_value={"error":"missing content"}):
            result = manager.process_task({"type":"text"})
            assert result["status"] == "error"
            assert "missing content" in result["message"]

    def test_manager_process_task_exception(self, manager):
        """
        If worker process raises an exception, manager returns error.
        Steps:
          Patch link worker process to raise Exception("LLM failed")
          process_task({"type":"link","url":"http://fail.com"})
          Expect status=error
        """
        link_worker = manager.worker_map["link"]
        with patch.object(link_worker, 'process', side_effect=Exception("LLM failed")):
            result = manager.process_task({"type":"link","url":"http://fail.com"})
            assert result["status"] == "error"
            assert "Worker error: LLM failed" in result["message"]

    def test_manager_store_and_retrieve_results(self, manager):
        """
        Purpose:
          store_result and get_task_result work as expected.
        Steps:
          store_result("abc", {"status":"completed","result":{"detail":"ok"}})
          get_task_result("abc") → should return same dict
        """
        manager.store_result("abc", {"status":"completed","result":{"detail":"ok"}})
        res = manager.get_task_result("abc")
        assert res["status"] == "completed"
        assert res["result"]["detail"] == "ok"
