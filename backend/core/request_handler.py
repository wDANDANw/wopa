import json
import logging
from typing import Optional, Dict, Any

from core.config_loader import get_redis_config
import redis

###############################################################################
# File: core/request_handler.py
#
# Purpose:
# The RequestHandler class provides an interface for:
# - enqueueing new analysis tasks,
# - retrieving results of completed tasks,
# - updating task statuses from external services/workers.
#
# It uses Redis as a backing store. We assume:
# - There's a queue_name for tasks if needed (though we have not fully implemented
#   the actual queue consumption by workers, we simulate or rely on external 
#   orchestrations).
# - Results are stored as JSON strings keyed by "result:{task_id}".
#
# Design & Philosophy:
# - Keep methods simple and focus on Redis get/set operations.
# - Raise exceptions or return None if data not found.
# - UpdateTaskStatus writes the final JSON (status & result) to Redis.
#
# Maintainability:
# - If we switch from Redis to another store, we just update this file.
# - The keys and data structure are stable and defined here.
#
# Testing:
# - We have unit tests in test_request_handler.py mocking redis.
# - No actual integration with Redis in unit tests, just mocks.
###############################################################################

logger = logging.getLogger(__name__)

class RequestHandler:
    def __init__(self):
        """
        Initialize the RequestHandler by connecting to Redis using 
        parameters from environment variables.

        Assumes:
        - REDIS_HOST and REDIS_PORT are set and valid.
        """
        host, port = get_redis_config()
        # Create a redis client. Using StrictRedis or Redis
        self.redis_client = redis.StrictRedis(host=host, port=port, decode_responses=True)

    def enqueue_task(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """
        Enqueue a new analysis task for workers to consume.
        
        However, from our design discussions, we focused on reading/writing results 
        rather than a full queue mechanism. If we wanted a queue mechanism, we might:
        
        - Use a list or stream in Redis to push tasks.
        - For now, let's assume we simply store the task initial data if needed or 
          rely on orchestrator and external triggers.
        
        If we do decide to store the initial task state as pending:
        - result:prefix can store at least status:"pending".
        
        For consistency, let's set initial status to "pending" and no result yet.
        """
        initial_data = {
            "status": "pending",
            "result": None,
            "type": task_data["type"],
            "content": task_data["content"]
        }
        # Store under "result:{task_id}"
        key = f"result:{task_id}"
        self.redis_client.set(key, json.dumps(initial_data))
        logger.info(f"Enqueued task {task_id} with pending status.")

    def fetch_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the current stored result/status for a given task_id.

        Returns:
            A dict like {"status":"...", "result":{...}} if found,
            or None if no data is found in Redis.

        If Redis fails or no key found, returns None.
        """
        key = f"result:{task_id}"
        data_str = None
        try:
            data_str = self.redis_client.get(key)
        except Exception as e:
            logger.error(f"Error fetching result for {task_id}: {e}")
            return None

        if data_str is None:
            # No entry found
            return None

        try:
            return json.loads(data_str)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON stored for {task_id}: {e}")
            return None

    def update_task_status(self, task_id: str, status: str, result: Optional[Dict[str, Any]]) -> None:
        """
        Update the task's status and (optionally) its result.
        This is used by external services/workers calling POST /api/task/update_task_status/{task_id}.

        Params:
            task_id (str): The task to update.
            status (str): New status, e.g., "completed", "in_progress", "error"
            result (dict or None): Additional result data if available.

        Steps:
        - Fetch the current data (optional, but we can directly overwrite as well).
        - Overwrite or set a new JSON with {status: ..., result: ...} in Redis.

        Raises:
            If redis fails, we could log error. For now, assume raising exceptions 
            is acceptable.
        """
        key = f"result:{task_id}"
        # Construct the final data
        updated_data = {
            "status": status
        }
        if result is not None:
            updated_data["result"] = result
        else:
            # If no result provided, we can omit or set to None
            updated_data["result"] = None

        try:
            self.redis_client.set(key, json.dumps(updated_data))
            logger.info(f"Updated task {task_id} with status={status}")
        except Exception as e:
            logger.error(f"Error updating task {task_id}: {e}")
            raise e


###############################################################################
# Future Extensions:
#
# If we introduce a real queue mechanism for tasks (e.g., RPUSH to a queue list),
# we can add methods like enqueue_to_queue and external workers can read from 
# that queue. For now, we only store status/result keys.
#
# Not the last file:
# We will proceed to implement more files (like orchestrator, api routes, 
# admin_ui, connectors). We will notify when we produce the last file.
###############################################################################
