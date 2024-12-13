from fastapi import APIRouter, HTTPException
from core.request_handler import RequestHandler
from core.config_loader import get_env
import logging

###############################################################################
# File: api/routes_vnc.py
#
# Purpose:
# GET /api/task/{task_id}/vnc: For app tasks, retrieve a VNC session URL 
# from the emulator provider and redirect or return it.
#
# Steps:
# 1) Check if task_id is an app task type by checking its stored info from request_handler.
# 2) If not app type or no data, return 404.
# 3) Call emulator_provider_connector.get_vnc_session(app_ref) to get the VNC URL.
# 4) Return or redirect user to `provider_manager/{task_id}/vnc` or just return JSON with the URL.
#
# Maintanability:
# If we change how we present VNC (redirect vs JSON), update code here.
###############################################################################

vnc_router = APIRouter()
logger = logging.getLogger(__name__)

@vnc_router.get("/{task_id}/vnc", summary="Get VNC session link for app tasks")
async def get_vnc_link(task_id: str):
    rh = RequestHandler()
    data = rh.fetch_result(task_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check if this was an app task by re-fetching original data if needed.
    # We stored initial task data as "pending" but not the type in result. 
    # If we want type info, we must have stored it initially in the same key or 
    # we can store tasks somewhere else. For simplicity, let's assume we can 
    # guess from request_handler. If not stored, we must adapt.

    # Let's assume we stored initial task_data, or at least 'type' in the result initially.
    # If not, we must rely on guess: In the request_handler.enque_task we stored status & no type
    # For more correctness, let's store type along with initial_data in enqueue_task.
    # Update enqueue_task in request_handler to store type as well:
    #
    # initial_data = {
    #   "status": "pending",
    #   "result": None,
    #   "type": task_data["type"], # store type
    #   "content": task_data["content"]
    # }
    #
    # Now data contains type and content.
    task_type = data.get("type")
    if task_type != "app":
        raise HTTPException(status_code=400, detail="VNC endpoint applicable only for app tasks")

    app_ref = data.get("content")
    if not app_ref:
        raise HTTPException(status_code=500, detail="App reference missing in stored data")

    # Now call the emulator_provider_connector.get_vnc_session(app_ref)
    try:
        from connectors.emulator_provider_connector import get_vnc_session
        vnc_url = get_vnc_session(app_ref)
    except Exception as e:
        logger.error(f"Failed to retrieve VNC session for {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get VNC session")

    # Either redirect (if vnc_url is a complete URL), or return JSON with the link.
    # Let's return JSON for now:
    return {"vnc_url": vnc_url}
