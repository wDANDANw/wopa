###############################################################################
# service_manager.py
#
# Purpose:
# The ServiceManager class orchestrates the lifecycle and tracking of analysis 
# tasks requested by clients through the Services subsystem. Each request (e.g. 
# /analyze_message) is assigned a unique internal task_id that identifies the 
# analysis job. The manager:
# - Generates task_id by combining service_name and a UUID for clarity.
# - Stores and updates tasks in an in-memory `task_store`.
# - Invokes the appropriate service to process the request. The service handles 
#   validation, calling workers, aggregator LLM, etc.
# - After the service returns a status ("completed","enqueued","error"), the manager 
#   updates the task record accordingly.
# - When clients call /get_task_status, the manager queries any associated workers 
#   if necessary, updates final status, and aggregates results.
#
# Terminology:
# - task_id: a unique string "service_name-<uuid>", identifying this analysis request.
# - worker_ids: if services start workers, they get worker_ids from the Worker subsystem.
#   The manager can store these worker_ids and later query worker statuses.
#
# Data Structures:
# - task_store: { task_id: {
#     "service_name": str,
#     "status": "enqueued"|"completed"|"error",
#     "worker_ids": [str],
#     "input_data": dict,
#     "result": dict|None,
#     "message": str|None (for errors)
#   }}
#
# Logging & Debugging:
# - Extensive logging at INFO and DEBUG levels for each action:
#   * Task creation, storing, processing
#   * Worker queries and result aggregation
#   * Validation or network errors
#
# Maintainability:
# - If switching from in-memory to DB storage, only this file changes.
# - Adding new services or worker logic doesn't require changes here unless 
#   we add special aggregation rules per service.
#
# Testing:
# - Unit tests can mock services and worker calls to simulate various scenarios.
# - Integration tests check real interactions with services and workers.
#
###############################################################################

import uuid
import logging
import os
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger("services")

class ServiceManager:
    def __init__(self, config: dict, service_map: dict):
        """
        Initialize ServiceManager.

        Args:
            config (dict): Configuration including WORKER_SERVER_URL, PROVIDER_SERVER_URL, etc.
            service_map (dict): {service_name: service_instance} mapping.

        Sets up:
        - self.task_store: in-memory dict to track tasks.
        - worker_server_url from config or "http://workers:8001".
        - Optionally Redis if we want to implement async queueing (not mandatory now).

        If REDIS_HOST, REDIS_PORT env found, attempt Redis connection, else in-memory.
        """
        self.config = config
        self.service_map = service_map
        self.task_store: Dict[str, Dict[str, Any]] = {}
        self.worker_server_url = config.get("WORKER_SERVER_URL", "http://workers:8001")

        self.use_redis = False
        redis_host = os.environ.get("REDIS_HOST")
        redis_port = os.environ.get("REDIS_PORT")
        if redis_host and redis_port:
            try:
                import redis
                self.redis = redis.StrictRedis(host=redis_host, port=int(redis_port), db=0)
                self.use_redis = True
                logger.info("ServiceManager: Redis integration enabled for queueing.")
            except ImportError:
                logger.warning("ServiceManager: Redis module not installed. Using in-memory only.")
            except Exception as e:
                logger.error(f"ServiceManager: Failed to connect Redis: {e}. Using in-memory only.")
        else:
            logger.info("ServiceManager: Using in-memory storage only (no Redis env).")

    def create_task_id(self, service_name: str) -> str:
        """
        Generate a unique task_id combining service_name and a UUID.

        Returns a string like "message_analysis-<uuid>".
        """
        new_uuid = str(uuid.uuid4())
        task_id = f"{service_name}-{new_uuid}"
        logger.debug("ServiceManager.create_task_id: Generated task_id=%s for service_name=%s", task_id, service_name)
        return task_id

    def store_new_task(self, task_id: str, service_name: str, input_data: dict):
        """
        Store a new task with initial status 'enqueued'.

        This allows us to track from the start.
        """
        logger.debug("ServiceManager.store_new_task: Storing new task_id=%s, service_name=%s", task_id, service_name)
        self.task_store[task_id] = {
            "service_name": service_name,
            "status": "enqueued",
            "worker_ids": [],
            "input_data": input_data,
            "result": None
        }

    def add_worker_id_to_task(self, task_id: str, worker_id: str):
        """
        Associate a worker_id with an existing task.

        Raises KeyError if task not found.
        """
        if task_id not in self.task_store:
            logger.error("ServiceManager.add_worker_id_to_task: Task %s not found", task_id)
            raise KeyError(f"Task {task_id} not found")
        logger.debug("ServiceManager.add_worker_id_to_task: Adding worker_id=%s to task_id=%s", worker_id, task_id)
        self.task_store[task_id]["worker_ids"].append(worker_id)

    def list_all_tasks(self) -> List[Dict[str, Any]]:
        """
        Return a summary of all tasks.

        Each entry includes at least "task_id" and "status".
        If completed, includes "result".
        If error, includes "message".
        """
        logger.debug("ServiceManager.list_all_tasks: Listing all tasks.")
        tasks_summary = []
        for tid, data in self.task_store.items():
            t_info = {
                "task_id": tid,
                "status": data["status"]
            }
            if data["status"] == "completed" and data["result"] is not None:
                t_info["result"] = data["result"]
            if data["status"] == "error" and "message" in data:
                t_info["message"] = data["message"]
            tasks_summary.append(t_info)
        logger.debug("ServiceManager.list_all_tasks: Returning tasks summary=%s", tasks_summary)
        return tasks_summary

    def get_task_result(self, task_id: str) -> Optional[dict]:
        """
        Retrieve full details for a given task_id, including worker_ids, input_data,
        and possibly result or message.

        If not found, return None.
        """
        logger.debug("ServiceManager.get_task_result: Looking up task_id=%s", task_id)
        return self.task_store.get(task_id, None)

    def update_and_get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Update a task's status by querying associated workers if needed.
        
        Steps:
        - If task not found, return None.
        - If status is already completed or error, return as is.
        - If enqueued with worker_ids:
          * For each worker_id, call worker subsystem GET /get_worker?task_id=worker_id
          * If any worker enqueued, remain enqueued.
          * If any worker error, set task error.
          * If all completed, aggregate results and set task completed.
        
        Returns updated status dict or None if not found.
        """
        logger.debug("ServiceManager.update_and_get_task_status: Checking status for task_id=%s", task_id)
        if task_id not in self.task_store:
            logger.warning("ServiceManager.update_and_get_task_status: Task_id=%s not found", task_id)
            return None

        task = self.task_store[task_id]
        if task["status"] in ["completed","error"]:
            logger.debug("ServiceManager.update_and_get_task_status: Task_id=%s already final (%s)", task_id, task["status"])
            return self._build_status_response(task)

        worker_ids = task["worker_ids"]
        if not worker_ids:
            # No workers: maybe service completed instantly
            task["status"] = "completed"
            task["result"] = task["result"] or {}
            logger.debug("ServiceManager.update_and_get_task_status: Task_id=%s no workers, set completed", task_id)
            return self._build_status_response(task)

        all_completed = True
        aggregated_results = []
        for w_id in worker_ids:
            logger.debug("ServiceManager.update_and_get_task_status: Querying worker_id=%s for task_id=%s", w_id, task_id)
            try:
                r = requests.get(f"{self.worker_server_url}/get_worker", params={"task_id": w_id}, timeout=5)
                logger.debug("Worker_id=%s response code=%d body=%s", w_id, r.status_code, r.text)
                if r.status_code == 404:
                    task["status"] = "error"
                    task["message"] = f"Worker not found: {w_id}"
                    task["result"] = None
                    logger.warning("Worker not found w_id=%s for task_id=%s", w_id, task_id)
                    return self._build_status_response(task)
                elif r.status_code != 200:
                    task["status"] = "error"
                    task["message"] = f"Error contacting worker subsystem: {r.text}"
                    task["result"] = None
                    logger.warning("Error contacting worker subsystem w_id=%s, task_id=%s: %s", w_id, task_id, r.text)
                    return self._build_status_response(task)

                w_status = r.json()
                w_state = w_status.get("status")
                if w_state == "enqueued":
                    logger.debug("Worker_id=%s still enqueued for task_id=%s", w_id, task_id)
                    all_completed = False
                elif w_state == "error":
                    task["status"] = "error"
                    task["message"] = w_status.get("message","Worker error")
                    task["result"] = None
                    logger.warning("Worker_id=%s error for task_id=%s msg=%s", w_id, task_id, task["message"])
                    return self._build_status_response(task)
                elif w_state == "completed":
                    if "result" in w_status:
                        aggregated_results.append(w_status["result"])
                        logger.debug("Worker_id=%s completed task_id=%s result appended", w_id, task_id)
                else:
                    task["status"] = "error"
                    task["message"] = f"Unknown worker status {w_state}"
                    task["result"] = None
                    logger.warning("Unknown worker status=%s w_id=%s task_id=%s", w_state, w_id, task_id)
                    return self._build_status_response(task)

            except requests.RequestException as e:
                logger.exception("Network error contacting worker subsystem w_id=%s task_id=%s", w_id, task_id)
                task["status"] = "error"
                task["message"] = "Could not reach worker subsystem"
                task["result"] = None
                return self._build_status_response(task)

        if not all_completed:
            logger.debug("ServiceManager.update_and_get_task_status: task_id=%s remains enqueued, some workers not done", task_id)
            return self._build_status_response(task)

        # All workers completed
        final_result = self._aggregate_worker_results(aggregated_results)
        task["status"] = "completed"
        task["result"] = final_result
        logger.info("ServiceManager.update_and_get_task_status: task_id=%s all workers completed final_result=%s", task_id, final_result)
        return self._build_status_response(task)

    def _aggregate_worker_results(self, results: List[dict]) -> dict:
        """
        Aggregate multiple worker results.
        If single result, return it as is.
        If multiple, combine under "combined_results".

        This can be specialized per service in future if needed.
        """
        logger.debug("ServiceManager._aggregate_worker_results: Aggregating %d results", len(results))
        if len(results) == 1:
            return results[0]
        return {"combined_results": results}

    def _build_status_response(self, task_data: dict) -> dict:
        """
        Build a response dict from task_data status and optionally result or message.

        Example:
        if completed: {"status":"completed","result":{...}}
        if error: {"status":"error","message":"..."}
        if enqueued: {"status":"enqueued"}

        Does not add task_id here; caller can add if needed.
        """
        resp = {"status": task_data["status"]}
        if task_data["status"] == "completed" and task_data["result"] is not None:
            resp["result"] = task_data["result"]
        if task_data["status"] == "error" and "message" in task_data:
            resp["message"] = task_data["message"]
        logger.debug("ServiceManager._build_status_response: %s", resp)
        return resp

    def enqueue_task_for_later(self, service_name: str, input_data: dict) -> str:
        """
        If we choose to enqueue tasks for asynchronous processing, 
        store them and push to Redis queue if available.

        Steps:
        - create task_id
        - store_new_task with status enqueued
        - if Redis used, lpush task_id to "service_tasks_queue"

        Return:
         task_id for reference.
        """
        t_id = self.create_task_id(service_name)
        self.store_new_task(t_id, service_name, input_data)
        if self.use_redis:
            self.redis.lpush("service_tasks_queue", t_id)
            logger.info("ServiceManager.enqueue_task_for_later: Task_id=%s enqueued in Redis queue", t_id)
        else:
            logger.debug("ServiceManager.enqueue_task_for_later: Task_id=%s enqueued in-memory only", t_id)
        return t_id

    def process_task_now(self, service_name: str, input_data: dict) -> dict:
        """
        Synchronously process a task:
        - create task_id
        - store new task
        - validate & process with the corresponding service
        - update task store and return final response

        If service returns "error", store error and message in task.
        If "completed", store result.

        Returns final response dict with "task_id" added.
        """
        t_id = self.create_task_id(service_name)
        logger.info("ServiceManager.process_task_now: Processing now task_id=%s service=%s", t_id, service_name)
        self.store_new_task(t_id, service_name, input_data)
        service = self.service_map[service_name]

        logger.debug("ServiceManager.process_task_now: Validating input for task_id=%s", t_id)
        val_error = service.validate_task(input_data)
        if val_error and "error" in val_error:
            logger.info("ServiceManager.process_task_now: Validation error task_id=%s error=%s", t_id, val_error["error"])
            self.task_store[t_id]["status"] = "error"
            self.task_store[t_id]["message"] = val_error["error"]
            resp = self._build_status_response(self.task_store[t_id])
            resp["task_id"] = t_id
            return resp

        logger.debug("ServiceManager.process_task_now: Calling service.process() for task_id=%s", t_id)
        try:
            result = service.process(input_data)
            final_status = result.get("status","enqueued")
            self.task_store[t_id]["status"] = final_status
            if "result" in result:
                self.task_store[t_id]["result"] = result["result"]
            if final_status == "error" and "message" in result:
                self.task_store[t_id]["message"] = result["message"]

            resp = self._build_status_response(self.task_store[t_id])
            resp["task_id"] = t_id
            logger.info("ServiceManager.process_task_now: task_id=%s final response=%s", t_id, resp)
            return resp
        except Exception as e:
            logger.exception("ServiceManager.process_task_now: Unexpected error for task_id=%s", t_id)
            self.task_store[t_id]["status"] = "error"
            self.task_store[t_id]["message"] = "Internal error processing task"
            resp = self._build_status_response(self.task_store[t_id])
            resp["task_id"] = t_id
            return resp

###############################################################################
# Notes:
#
# - With extensive logging, we can trace at which step the error occurs.
# - If the aggregator LLM or worker calls fail, the service sets "status":"error","message":"...".
#   handle_manager_response (in routes) decides final HTTP code.
#
# - If we keep getting "Unknown error" from curl, check logs here to see if 
#   service.process() returned a known message. If not, a try/except block might have 
#   caught an exception and returned a generic "Internal error processing task".
#
# - If aggregator or worker calls are failing, logs with exception stack traces 
#   help identify network issues or invalid responses.
#
# This approach should provide enough insights to debug and maintain the system 
# more effectively.
#
###############################################################################
