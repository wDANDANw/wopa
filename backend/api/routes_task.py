from fastapi import APIRouter, HTTPException
from data_models.schemas import TaskStatusResponse, UpdateTaskStatusRequest
from core.request_handler import RequestHandler

###############################################################################
# File: api/routes_task.py
#
# Purpose:
# - GET /api/task/{task_id}: returns TaskStatusResponse (status/result)
# - POST /api/task/update_task_status/{task_id}: external services update task status
#
# Steps:
# GET: fetch_result from request_handler.
# POST: update_task_status with provided data.
#
# Maintainability:
# If task storage changes, we only update request_handler methods.
###############################################################################

task_router = APIRouter()

@task_router.get("/{task_id}", summary="Retrieve task status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    rh = RequestHandler()
    data = rh.fetch_result(task_id)
    if data is None:
        # No task found
        raise HTTPException(status_code=404, detail="Task not found")
    return data

@task_router.post("/update_task_status/{task_id}", summary="Update a task's status and result")
async def update_task_status(task_id: str, request: UpdateTaskStatusRequest):
    rh = RequestHandler()
    try:
        rh.update_task_status(task_id, request.status, request.result)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to update task status")
    return {"message":"Task status updated"}
