###############################################################################
# routes_tasks.py
#
# Purpose:
# This module defines the FastAPI router handling task-related endpoints within 
# the Workers subsystem. The endpoints are:
# 1. GET /tasks: List all known tasks and their worker entries.
# 2. POST /enqueue_task: Enqueue a worker request under a given or new task_id.
#    The caller provides a worker_type and optional task_id. WorkerManager returns a
#    newly generated worker_id and sets status="enqueued".
# 3. POST /request_worker: Immediately process a task using a specified worker_type and
#    possibly a given task_id. WorkerManager runs the worker, returns a worker_id, and if completed,
#    status="completed" with results.
# 4. GET /get_workers_in_task: Retrieve information about all workers associated with a given task_id.
#
# Key Concepts:
# - task_id: Represents the upstream request or job. May be provided by upstream or generated if absent.
# - worker_type: Chosen by the caller from /available_workers.
# - worker_id: Generated by WorkerManager when a worker is enqueued or processed.
#   This worker_id is unique per worker instance handling that request and is returned 
#   in the response. The client can use it to track that specific worker.
#
# Interactions:
# - We rely on `app.state.manager` (a WorkerManager instance) and `app.state.worker_map` (mapping worker_type to worker classes).
# - The WorkerManager handles validation, storage, and calling the actual worker.
#
# Validation & Error Handling:
# - If `worker_type` not known, return 404.
# - If validation fails (worker.validate_task), return 400.
# - If `task_id` not found for retrieval, return 404.
# - Unexpected errors return 500.
#
# Maintainability:
# - If new endpoints related to tasks are needed (like canceling tasks), add them here.
# - If worker logic changes, we adapt these endpoints as needed, relying on WorkerManager.
#
###############################################################################

import logging
from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter()

###############################################################################
# Data Models for Requests
###############################################################################

class EnqueueTaskRequest(BaseModel):
    """
    Schema for enqueuing a task.
    Fields:
    - worker_type: str (e.g. "text", "link", "file", etc.)
    Additional fields depend on the chosen worker_type and are validated by the worker.

    The client can optionally provide "task_id" to group multiple workers under the 
    same overarching request. If not provided, WorkerManager will generate a new task_id.

    Example:
    {
      "worker_type": "text",
      "content": "Check this message",
      "task_id":"abc-123" // optional
    }
    """
    worker_type: str
    # Other fields are allowed (e.g. "content", "task_id") if the worker expects them.
    # We rely on extra fields. By default Pydantic would disallow them, 
    # but we can allow extra. If not, we can read raw JSON from request if needed.
    # For simplicity, assume these fields are allowed or we have a separate request reading.

class RequestWorkerRequest(BaseModel):
    """
    Schema for requesting immediate processing of a task.
    Similar to EnqueueTaskRequest but triggers processing immediately.

    Fields:
    - worker_type: str
    - optional "task_id" if caller wants to use a known task_id
    - other fields depending on worker

    Example:
    {
      "worker_type":"link",
      "url":"http://example.com/malicious",
      "task_id":"abc-123" // optional
    }
    """
    worker_type: str

###############################################################################
# Endpoints
###############################################################################

@router.get("/tasks", summary="List all tasks")
def list_tasks(request: Request):
    """
    GET /tasks
    Purpose:
      Return a list of all tasks known to the system, each with their associated worker entries.

    Each element:
    {
      "task_id":"...",
      "entries":[
        {"worker_id":"...","worker_type":"...","status":"...","result":...,"message":"...","task_data":...},
        ...
      ]
    }

    Steps:
      1. Access manager via request.app.state.manager
      2. manager.list_all_tasks() returns a list of tasks and their entries.
    Returns 200 OK with JSON array.
    """
    manager = request.app.state.manager
    tasks = manager.list_all_tasks()
    return tasks


@router.post("/enqueue_task", summary="Enqueue a new worker request for a task")
async def enqueue_task(request: Request):
    """
    POST /enqueue_task
    Purpose:
      Enqueue a worker request under a task_id (provided or new) with status="enqueued".

    Input JSON:
      {
        "worker_type":"text",
        "content":"Check this message",
        "task_id":"abc-123" // optional
      }

    Steps:
      1. Parse JSON. Extract worker_type.
      2. Check if worker_type is known. If not, 404.
      3. Validate task_data with worker's validate_task.
      4. manager.enqueue_task(task_data) returns {task_id, worker_id, status:"enqueued"}.
      5. Return this to caller.

    Returns:
      {
        "task_id":"...",
        "worker_id":"...",
        "status":"enqueued"
      }

    On validation error:
      400 with error message.
    On unknown worker_type:
      404 Not Found.
    """
    manager = request.app.state.manager
    worker_map = request.app.state.worker_map

    body = await request.json()
    worker_type = body.get("worker_type")
    if not worker_type:
        raise HTTPException(status_code=400, detail="No worker_type provided.")

    if worker_type not in worker_map:
        raise HTTPException(status_code=404, detail=f"Unknown worker_type: {worker_type}")

    # Validate task_data with a worker instance
    # Instantiate the worker class and call validate_task
    WorkerClass = worker_map[worker_type]
    worker = WorkerClass(manager.config)
    val_error = worker.validate_task(body)
    if val_error and "error" in val_error:
        raise HTTPException(status_code=400, detail=val_error["error"])

    # Enqueue task
    result = manager.enqueue_task(body) 
    # result = {"task_id":"...","worker_id":"...","status":"enqueued"}
    return result


@router.post("/request_worker", summary="Immediately process a worker request for a task")
async def request_worker_run(request: Request):
    """
    POST /request_worker
    Purpose:
      Immediately process a worker request, returning completed or error result.

    Input JSON:
      {
        "worker_type":"link",
        "url":"http://example.com/bad",
        "task_id":"abc-123" // optional
      }

    Steps:
      1. Extract worker_type, check if known.
      2. Validate task_data with worker.validate_task.
      3. manager.process_task(task_data):
         - returns {"status":"completed","result":...,"task_id":"...","worker_id":"..."} 
           or {"status":"error","message":"..."}.

    Returns on success:
      {
        "status":"completed",
        "result":{...},
        "task_id":"...",
        "worker_id":"..."
      }

    On error:
      400 or 500 depending on message.

    On unknown worker_type:
      404 Not Found.
    """
    manager = request.app.state.manager
    worker_map = request.app.state.worker_map

    body = await request.json()
    worker_type = body.get("worker_type")
    if not worker_type:
        raise HTTPException(status_code=400, detail="No worker_type provided.")

    if worker_type not in worker_map:
        raise HTTPException(status_code=404, detail=f"Unknown worker_type: {worker_type}")

    # Validate task_data
    WorkerClass = worker_map[worker_type]
    worker = WorkerClass(manager.config)
    val_error = worker.validate_task(body)
    if val_error and "error" in val_error:
        raise HTTPException(status_code=400, detail=val_error["error"])

    result = manager.process_task(body)
    if result.get("status") == "error":
        message = result.get("message","Unknown worker error")
        if "missing" in message.lower() or "invalid" in message.lower():
            raise HTTPException(status_code=400, detail=message)
        else:
            raise HTTPException(status_code=500, detail=message)

    # If completed:
    return result


@router.get("/get_workers_in_task", summary="Get info about all workers under a given task_id")
def get_workers_in_task(request: Request, task_id: str = Query(..., description="Task ID")):
    """
    GET /get_workers_in_task?task_id=...

    Purpose:
      Return all worker entries associated with the given task_id.

    Steps:
      1. manager.get_task_result(task_id)
      2. If not found, 404
      3. Return the full details as is.

    Returns:
    {
      "entries":[
        {"worker_id":"...","worker_type":"...","status":"...","task_data":{...},"result":{...optional},"message":...optional},
        ...
      ]
    }

    This shows all workers involved in the given task_id.
    If multiple workers were enqueued or processed under the same task_id, 
    we list them all.

    On not found task_id:
      404 error.
    """
    manager = request.app.state.manager
    res = manager.get_task_result(task_id)
    if not res:
        raise HTTPException(status_code=404, detail="Task not found")

    return res

###############################################################################
# Future Enhancements:
#
# - If we implement canceling tasks, add DELETE /tasks/{task_id} here.
# - If we need pagination for /tasks, add query params like limit, offset.
# - If multiple workers per task need special presentation (like aggregated status), 
#   transform the returned data from manager before responding.
#
###############################################################################