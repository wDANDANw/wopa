###############################################################################
# routes_workers.py
#
# Purpose:
# This module defines the FastAPI router that handles worker-related endpoints
# in the Workers subsystem. It includes:
# 1. Listing all available worker types (/available_workers)
# 2. Retrieving metadata about a specific worker instance by worker_id (/get_worker_by_id)
#
# Clarified Concepts:
# - worker_type: A known category of worker defined at startup (e.g. "text", "link", "file").
#   The `/available_workers` endpoint returns these worker_types.
#
# - worker_id: A unique identifier generated per request (per worker instance) 
#   when we enqueue or process a worker request. This worker_id is returned by 
#   `enqueue_task` or `request_worker` calls.
#
#   Since worker_id is generated at runtime, it is not known beforehand. To retrieve 
#   metadata about that specific worker instance, we must find it in `tasks_storage`.
#
# Retrieving Worker Metadata by worker_id:
# - Because worker_id is created at request time and stored in tasks_storage, 
#   to serve `/get_worker_by_id`, we:
#   1. Iterate over all tasks in `tasks_storage` to find an entry with that worker_id.
#   2. Once found, get the worker_type from that entry.
#   3. Instantiate a worker using worker_map[worker_type], call `get_metadata()` if available.
#
# If worker_id not found in any tasks, return 404.
#
# Maintainability:
# - If we have a large number of tasks, searching might be slow. Consider indexing worker_ids in the future.
# - If workers must store more elaborate metadata, ensure each worker implements `get_metadata()`.
#
# Error Handling:
# - Unknown worker_id: 404.
# - If something unexpected happens, 500.
#
###############################################################################

import logging
from fastapi import APIRouter, HTTPException, Request, Query

logger = logging.getLogger(__name__)

router = APIRouter()

###############################################################################
# Endpoints
###############################################################################

@router.get("/available_workers", summary="List all available worker types")
def list_available_workers(request: Request):
    """
    GET /available_workers
    Purpose:
      Returns a list of all worker_types available in the system. 
      Worker types are known at startup and do not include worker_ids, since 
      worker_ids are generated at runtime per request.

    Steps:
      1. Access worker_map from request.app.state.worker_map
      2. Return list(worker_map.keys()), which represent worker_types.

    Returns:
      200 OK with JSON array of worker_types.
      Example:
      ["text","link","static_file","dynamic_file","syslog","app"]
    """
    worker_map = request.app.state.worker_map
    # worker_map keys represent worker_types in this updated design.
    return list(worker_map.keys())


@router.get("/get_worker_by_id", summary="Get metadata about a specific worker instance by worker_id")
def get_worker_by_id(request: Request, worker_id: str = Query(..., description="Worker ID assigned at runtime")):
    """
    GET /get_worker_by_id?worker_id=...

    Purpose:
      Retrieve detailed metadata about a specific worker instance identified by worker_id.
      Remember: worker_id is generated per request at enqueue_task or process_task time.

    Steps:
      1. Since worker_id is unique per worker instance and stored in tasks_storage entries,
         we must search through tasks_storage to find which entry holds this worker_id.
      2. Once found the matching entry:
         - Extract worker_type from the entry (as stored at request time).
         - Instantiate a worker using worker_map[worker_type].
         - Call worker.get_metadata() if available, else fallback metadata.
      3. Return metadata to caller.

    Returns:
      200 OK with JSON object containing worker metadata.
      Example:
      {
        "worker_id": "text-550e8400-e29b-41d4-a716-446655440000",
        "worker_type":"text",
        "description": "Analyzes text messages with LLM.",
        "required_fields":["content"],
        "mode":"local",
        "capabilities":["text analysis","LLM integration"]
      }

    Error Cases:
      - If no entry with worker_id found, 404 Not Found.
      - If unexpected error, 500.
    """

    worker_map = request.app.state.worker_map
    manager = request.app.state.manager

    # We have tasks_storage in manager. Need to search for worker_id:
    tasks_storage = manager.tasks_storage

    found_entry = None
    found_worker_type = None

    # Search all tasks:
    # This could be slow if many tasks. Consider indexing in future.
    for tid, data in tasks_storage.items():
        for entry in data["entries"]:
            if entry.get("worker_id") == worker_id:
                found_entry = entry
                found_worker_type = entry.get("worker_type")
                break
        if found_entry:
            break

    if not found_entry or not found_worker_type:
        # No such worker_id found
        raise HTTPException(status_code=404, detail=f"No such worker_id: {worker_id}")

    # found_worker_type gives us the type of the worker originally requested
    if found_worker_type not in worker_map:
        # This would be very unusual, means worker_type changed or lost:
        # Let's return error:
        raise HTTPException(status_code=500, detail=f"Inconsistent state: worker_type {found_worker_type} not in worker_map")

    WorkerClass = worker_map[found_worker_type]
    # Instantiate a worker to get metadata:
    worker = WorkerClass(manager.config)

    # Try get_metadata():
    if hasattr(worker, "get_metadata") and callable(worker.get_metadata):
        metadata = worker.get_metadata()
    else:
        # fallback metadata
        metadata = {
            "worker_id": worker_id,
            "worker_type": found_worker_type,
            "description": f"Worker {worker_id} of type {found_worker_type}, no metadata method.",
            "required_fields": ["unknown"],
            "mode": manager.config.get("mode","local"),
            "capabilities": []
        }

    # Since we know worker_id and worker_type, let's add them if not present:
    # Ensure metadata includes worker_id and worker_type:
    metadata["worker_id"] = worker_id
    if "worker_type" not in metadata:
        metadata["worker_type"] = found_worker_type

    return metadata

###############################################################################
# Future Enhancements:
#
# - Add endpoints like /worker_health or /worker_stats if needed.
# - If the system grows large, consider indexing workers by worker_id 
#   in manager for O(1) lookups instead of searching tasks.
# - If worker_type/worker_id concepts evolve, update logic accordingly.
#
###############################################################################
