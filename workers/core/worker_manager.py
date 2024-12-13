###############################################################################
# worker_manager.py
#
# Purpose:
# Now updated to include an automatic dequeue algorithm:
# - Adds a process_enqueued_tasks() method that scans for enqueued tasks and tries 
#   to process them automatically.
#
# Logic:
# - process_enqueued_tasks():
#   1. Iterate through tasks_storage.
#   2. For each task_id, iterate entries.
#   3. If an entry is "enqueued", attempt to process it by calling `process_enqueued_entry()`.
#   4. `process_enqueued_entry()` resembles `process_task()` logic but we do not need 
#      new data from outside, we already have `task_data` stored.
#
# - We modify `enqueue_task()` to store all necessary fields. We store worker_type and 
#   full task_data so we can re-run validation and processing at dequeue time.
#
# Triggering the automatic processing:
# - In `worker_server.py`, we could add a startup event that runs `manager.process_enqueued_tasks()` 
#   periodically or on-demand. One approach is to use a background task (e.g., `asyncio.create_task()`) 
#   or a separate thread or a schedule.
#
# Maintainability:
# - If we add logic to handle partial failures or retries, we can enhance process_enqueued_tasks.
# - If the number of tasks grows large, consider indexing or batching.
#
###############################################################################

import uuid
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class WorkerManager:
    """
    WorkerManager with automatic dequeue support.

    Fields:
    - config: dict with runtime config
    - worker_map: dict {worker_type: WorkerClass}
    - tasks_storage: {task_id: {"entries":[
        {"worker_id":"...","worker_type":"...","status":"enqueued"|"completed"|"error","task_data":...,"result":...,"message":...},
        ...
      ]}}

    Methods:
    - enqueue_task(task_data: dict) -> dict: Enqueues a worker request.
    - process_task(task_data: dict) -> dict: Immediately process a request (like request_worker).
    - list_all_tasks() -> list: List all tasks and their entries.
    - get_task_result(task_id: str) -> dict or None: Get details of a given task_id.
    - process_enqueued_tasks(): Automatically attempt to process all enqueued tasks.
    """

    def __init__(self, config: dict, worker_map: dict):
        self.config = config
        self.worker_map = worker_map
        self.tasks_storage = {}

    def _ensure_task_id_exists(self, task_id: str):
        if task_id not in self.tasks_storage:
            self.tasks_storage[task_id] = {"entries": []}

    def _find_worker_entry(self, task_id: str, worker_id: str):
        entries = self.tasks_storage[task_id]["entries"]
        for i, e in enumerate(entries):
            if e.get("worker_id") == worker_id:
                return e, i
        return None, -1

    def _generate_worker_id(self, worker_type: str) -> str:
        return f"{worker_type}-{uuid.uuid4()}"

    def enqueue_task(self, task_data: dict) -> dict:
        """
        enqueue_task(task_data)
        Adds a new "enqueued" worker request.

        Steps:
        - Extract worker_type
        - Determine task_id
        - Generate worker_id
        - Add entry with status="enqueued"

        Returns:
          {"task_id":task_id,"worker_id":worker_id,"status":"enqueued"}
        """
        worker_type = task_data.get("worker_type")
        if not worker_type or worker_type not in self.worker_map:
            raise ValueError("Invalid or missing worker_type.")

        if "task_id" in task_data:
            task_id = task_data["task_id"]
        else:
            task_id = str(uuid.uuid4())
            task_data["task_id"] = task_id

        self._ensure_task_id_exists(task_id)

        worker_id = self._generate_worker_id(worker_type)

        new_entry = {
            "worker_id": worker_id,
            "worker_type": worker_type,
            "status": "enqueued",
            "task_data": task_data
        }
        self.tasks_storage[task_id]["entries"].append(new_entry)
        logger.info(f"Enqueued worker_id={worker_id}, task_id={task_id}, worker_type={worker_type}.")
        return {"task_id": task_id, "worker_id": worker_id, "status":"enqueued"}

    def process_task(self, task_data: dict) -> dict:
        """
        process_task(task_data)
        Immediately process a worker request.

        Steps:
        - Extract worker_type
        - Determine task_id
        - Generate worker_id
        - Instantiate worker, validate, process
        - Return completed or error result
        """
        worker_type = task_data.get("worker_type")
        if not worker_type or worker_type not in self.worker_map:
            return {"status":"error","message":"Unknown or missing worker_type."}

        if "task_id" in task_data:
            task_id = task_data["task_id"]
        else:
            task_id = str(uuid.uuid4())
            task_data["task_id"] = task_id

        self._ensure_task_id_exists(task_id)
        worker_id = self._generate_worker_id(worker_type)

        WorkerClass = self.worker_map[worker_type]
        worker = WorkerClass(self.config)

        val_error = worker.validate_task(task_data)
        if val_error and "error" in val_error:
            # Store error entry
            self.tasks_storage[task_id]["entries"].append({
                "worker_id": worker_id,
                "worker_type": worker_type,
                "status":"error",
                "task_data":task_data,
                "message":val_error["error"]
            })
            return {"status":"error","message":val_error["error"]}

        try:
            result = worker.process(task_data)
            if result.get("status") == "completed":
                self.tasks_storage[task_id]["entries"].append({
                    "worker_id": worker_id,
                    "worker_type": worker_type,
                    "status":"completed",
                    "task_data":task_data,
                    "result": result.get("result")
                })
                logger.info(f"Task {task_id}, worker_id={worker_id}, worker_type={worker_type} completed.")
                return {
                    "status":"completed",
                    "result":result.get("result"),
                    "task_id":task_id,
                    "worker_id":worker_id
                }
            else:
                # Worker returned error
                msg = result.get("message","Unknown error")
                self.tasks_storage[task_id]["entries"].append({
                    "worker_id": worker_id,
                    "worker_type": worker_type,
                    "status":"error",
                    "task_data":task_data,
                    "message":msg
                })
                logger.warning(f"Worker {worker_id} type {worker_type} error task_id={task_id}: {msg}")
                return {"status":"error","message":msg}

        except Exception as e:
            # Unexpected exception
            error_msg = f"Worker error: {str(e)}"
            self.tasks_storage[task_id]["entries"].append({
                "worker_id": worker_id,
                "worker_type": worker_type,
                "status":"error",
                "task_data":task_data,
                "message":error_msg
            })
            logger.exception("Unexpected exception in worker.process")
            return {"status":"error","message":error_msg}

    def list_all_tasks(self) -> list:
        """
        list_all_tasks()
        Return a list of all tasks and their worker entries.

        Example:
        [
          {
            "task_id":"...",
            "entries":[
              {"worker_id":"...","worker_type":"...","status":"...","task_data":...,"result":...,"message":...},
              ...
            ]
          },
          ...
        ]
        """
        result_list = []
        for tid, data in self.tasks_storage.items():
            result_list.append({
                "task_id": tid,
                "entries": data["entries"]
            })
        return result_list

    def get_task_result(self, task_id: str):
        """
        get_task_result(task_id)
        Retrieve details for a given task_id.

        Returns: 
        {
          "entries":[
            {"worker_id":"...","worker_type":"...","status":"...","task_data":...,"result":...,"message":...},
            ...
          ]
        } or None if not found.
        """
        return self.tasks_storage.get(task_id, None)

    def process_enqueued_tasks(self):
        """
        process_enqueued_tasks()
        Automatic dequeue algorithm:
        Attempts to process all tasks that are currently enqueued.

        Steps:
        - Iterate over tasks_storage
        - For each entry that has status="enqueued", attempt to process it:
          1. Extract worker_type and task_data from the entry
          2. Call self._process_enqueued_entry(task_id, entry)
        - Keep track of how many tasks we processed this run. If needed, we can loop until no enqueued tasks remain,
          or just do one pass.

        Note: This is a synchronous method. If you want to run periodically, call it 
        from a background task in `worker_server.py`.
        
        Implementation detail:
        - We must call a method similar to process_task but we already have 
          all needed data (worker_type,task_data).
        - We'll create a helper _process_enqueued_entry to handle logic akin to process_task.

        Once done, all previously enqueued tasks (if valid) become completed or error.
        """

        processed_count = 0
        # We'll collect tasks and entries to process first, to avoid modifying dict while iterating
        to_process = []
        for tid, data in self.tasks_storage.items():
            for i, entry in enumerate(data["entries"]):
                if entry.get("status") == "enqueued":
                    # This entry needs processing
                    to_process.append((tid, i, entry))

        for (tid, i, entry) in to_process:
            # Double-check still enqueued:
            current_status = self.tasks_storage[tid]["entries"][i]["status"]
            if current_status == "enqueued":
                self._process_enqueued_entry(tid, i)
                processed_count += 1

        # logger.info(f"process_enqueued_tasks: Processed {processed_count} enqueued entries.")

    def _process_enqueued_entry(self, task_id: str, entry_index: int):
        """
        _process_enqueued_entry(task_id, entry_index)
        Helper method to process a single enqueued entry.

        Steps:
        - Extract worker_type, task_data from entry.
        - Instantiate worker and call validate_task, process.
        - Update the entry with completed or error status.

        Returns nothing. Modifies tasks_storage in-place.
        """
        entry = self.tasks_storage[task_id]["entries"][entry_index]
        worker_type = entry.get("worker_type")
        task_data = entry.get("task_data")

        if worker_type not in self.worker_map:
            # Unexpected scenario, mark error
            self.tasks_storage[task_id]["entries"][entry_index]["status"] = "error"
            self.tasks_storage[task_id]["entries"][entry_index]["message"] = f"Unknown worker_type {worker_type}"
            return

        WorkerClass = self.worker_map[worker_type]
        worker = WorkerClass(self.config)

        # Validate
        val_error = worker.validate_task(task_data)
        if val_error and "error" in val_error:
            self.tasks_storage[task_id]["entries"][entry_index]["status"] = "error"
            self.tasks_storage[task_id]["entries"][entry_index]["message"] = val_error["error"]
            return

        try:
            result = worker.process(task_data)
            if result.get("status") == "completed":
                self.tasks_storage[task_id]["entries"][entry_index]["status"] = "completed"
                self.tasks_storage[task_id]["entries"][entry_index]["result"] = result.get("result")
                logger.info(f"Automatically processed enqueued entry (worker_type={worker_type}) for task_id={task_id}, completed.")
            else:
                msg = result.get("message","Unknown error")
                self.tasks_storage[task_id]["entries"][entry_index]["status"] = "error"
                self.tasks_storage[task_id]["entries"][entry_index]["message"] = msg
                logger.warning(f"Automatically processed enqueued entry (worker_type={worker_type}) for task_id={task_id}, but worker returned error: {msg}")

        except Exception as e:
            error_msg = f"Worker error: {str(e)}"
            self.tasks_storage[task_id]["entries"][entry_index]["status"] = "error"
            self.tasks_storage[task_id]["entries"][entry_index]["message"] = error_msg
            logger.exception("Unexpected exception in auto processing worker.")

###############################################################################
# To integrate automatic dequeue:
#
# In worker_server.py, you might add:
#
# from fastapi_utils.tasks import repeat_every  # from fastapi-utils library
#
# @app.on_event("startup")
# @repeat_every(seconds=60)  # every 60 seconds
# async def auto_process_enqueued_tasks():
#     app.state.manager.process_enqueued_tasks()
#
# This way, every 60 seconds, enqueued tasks get processed automatically.
#
# If you don't want scheduling, you can call manager.process_enqueued_tasks() 
# manually from a triggered endpoint or event.
#
###############################################################################
