###############################################################################
# routes_tasks.py
#
# Purpose:
# This file defines endpoints related to retrieving a list of all tasks and 
# checking/updating the status of a specific task within the Services subsystem.
#
# Background:
# - The Services subsystem assigns a unique task_id (like "message_analysis-<uuid>")
#   to each user request (analyze_message, analyze_link, etc.).
# - Tasks may involve multiple workers. Each worker invocation returns a worker_id 
#   from the worker subsystem.
# - The ServiceManager stores task_id → worker_ids mapping and tracks the task's 
#   overall status. Initially, tasks are often "enqueued".
# - Over time, as the worker subsystem completes its subtasks, the Services subsystem 
#   can update the task to "completed" and store aggregated results.
#
# Endpoints:
# - GET /tasks:
#   Lists all known tasks, showing task_id, status, and if completed, result.
#
# - GET /get_task_status?task_id=<task_id>:
#   Given a specific task_id, tries to update its status by querying each worker_id 
#   from the worker subsystem. If all workers are done and successful, sets status 
#   to "completed" and aggregates results. If any worker fails, sets "error".
#   If still ongoing, remains "enqueued".
#
# Design & Approach:
# - These endpoints rely on the ServiceManager (app.state.manager) to access 
#   `list_all_tasks()` and `update_and_get_task_status(task_id)`.
# - If `update_and_get_task_status` returns None, means no such task_id (404).
# - If `update_and_get_task_status` returns an error status, we return that as 500 or 400 accordingly (decided by logic in service_manager).
# - On success, we return the current status and possibly result or message.
#
# Error Handling:
# - If task_id not found: 404 Not Found.
# - If worker subsystem unreachable or returns unexpected data: 
#   `manager.update_and_get_task_status()` sets status=error and message. We return 
#   a 500 if it's an internal error scenario.
#
# Maintainability:
# - If we add features like "cancel a task" or "filter tasks by status", we add 
#   more endpoints here that interact with the manager.
# - If we change how tasks are stored (DB instead of in-memory), only manager code 
#   changes, not these endpoints.
# - Clear docstrings ensure future developers understand the logic quickly.
#
# Testing:
# - Unit tests can mock manager to return fake tasks and results, ensuring endpoints 
#   return correct HTTP codes and JSON.
# - Integration tests check actual interaction with worker subsystem and verify 
#   tasks reflect real progress.
#
###############################################################################

import logging
from fastapi import APIRouter, Request, HTTPException, Query

router = APIRouter()
logger = logging.getLogger("services")

###############################################################################
# GET /tasks
#
# Purpose:
# Lists all tasks known to the Services subsystem, along with their status and 
# optionally final results if completed.
#
# Steps:
# 1. manager = app.state.manager
# 2. tasks = manager.list_all_tasks() returns a list of dicts:
#    [
#      {"task_id":"...","status":"completed","result":{...}},
#      {"task_id":"...","status":"enqueued"}
#    ]
#
# If empty, returns [].
#
# Example Response:
# [
#   {"task_id":"message_analysis-1234abcd","status":"completed","result":{"risk_level":"high"}},
#   {"task_id":"link_analysis-5678efgh","status":"enqueued"}
# ]
#
###############################################################################

@router.get("/tasks", summary="List all tasks and their statuses")
def list_tasks(request: Request):
    manager = request.app.state.manager
    tasks = manager.list_all_tasks()
    # Return as-is. If no tasks, returns empty list.
    return tasks

###############################################################################
# GET /get_task_status?task_id=<task_id>
#
# Purpose:
# Given a specific task_id, update and retrieve its current status.
#
# Steps:
# 1. Extract task_id from query parameter.
# 2. Call manager.update_and_get_task_status(task_id):
#    - If no such task, returns None → 404 Not Found.
#    - If found, tries to update by querying each worker_id in Worker subsystem:
#      - If any worker still "enqueued", task remains enqueued.
#      - If any worker "error", task error.
#      - If all completed, aggregates results and sets "completed".
#    - Returns a dict:
#      {
#        "status":"enqueued"|"completed"|"error",
#        "result":{...} if completed,
#        "message":"..." if error
#      }
#
# Example calls:
# GET /get_task_status?task_id=message_analysis-abc123
#
# Possible responses:
# - If completed:
#   {"status":"completed","result":{...}}
#
# - If enqueued:
#   {"status":"enqueued"}
#
# - If error:
#   {"status":"error","message":"Failed to reach worker"}
#
# Error Handling:
# - If task_id not found: 404
# - If error due to validation or known user input error: 400
# - If unexpected worker issue or internal logic fail: 500
#
# The `manager.update_and_get_task_status()` sets "status":"error" with a message.
# We can decide 400 vs 500 from message content. If message implies a known user 
# error, do 400; else 500. This logic can remain simple if we trust manager 
# to produce suitable error messages.
#
###############################################################################

@router.get("/get_task_status", summary="Get and update the status of a specific task")
def get_task_status(request: Request, task_id: str = Query(..., description="The task_id to check")):
    manager = request.app.state.manager
    status_info = manager.update_and_get_task_status(task_id)
    if status_info is None:
        # task_id not found
        raise HTTPException(status_code=404, detail="Task not found")

    # status_info = {"status":"...", "result":...optional, "message":...optional}
    t_status = status_info.get("status")
    if t_status == "error":
        # Check if message suggests validation error or internal error.
        msg = status_info.get("message","Unknown error")
        # If message includes typical validation error words:
        if any(word in msg.lower() for word in ["invalid","missing","required","bad input"]):
            raise HTTPException(status_code=400, detail=msg)
        else:
            # Internal/worker error
            raise HTTPException(status_code=500, detail=msg)
    else:
        # "enqueued" or "completed"
        # Return as-is with 200 OK
        return status_info

###############################################################################
# Notes:
#
# With this design:
# - /tasks is simple: just returns whatever manager.list_all_tasks() provides.
# - /get_task_status attempts to refine the status by contacting workers 
#   through the manager.
#
# If we add more endpoints (like /cancel_task), we do similarly here.
#
# If we change how errors are handled (e.g., always return 500 for internal 
# errors, never 400), we just tweak the final decision logic.
#
# If we want to add filters to /tasks (like ?status=completed), we extend 
# manager.list_all_tasks() to accept filters or do filtering here.
#
# Maintainability:
# - The code is well-commented, explaining each step and error scenario.
# - If worker subsystem endpoints change, we only update `service_manager.py`.
# - If we add a DB, only `service_manager.py` changes, not these endpoints.
#
# Testing:
# - Unit tests: mock manager to return fake statuses for tasks, ensure correct 
#   HTTP codes and responses.
# - Integration tests: run real worker subsystem to confirm tasks move from 
#   enqueued to completed, and these endpoints reflect that accurately.
#
###############################################################################
