###############################################################################
# routes_vnc.py
#
# Purpose:
# Defines FastAPI routes for accessing or referencing VNC endpoints associated 
# with emulator instances. The idea is that after you run an app in the emulator,
# you might want to "see" the emulator screen. A VNC viewer can connect if we 
# provide a URL or instructions.
#
# Key Responsibilities:
# 1. Given a task_id (or app reference), return a VNC URL or instructions 
#    to connect to the emulator’s VNC port.
# 2. Possibly integrate with emulator_env.py or config.yaml/instances.json 
#    to find the correct emulator instance and its VNC port.
#
# Requirements:
# - The emulator environment or `emulator_env.py` should know which task_id 
#   maps to which emulator instance.
# - This endpoint might just return a string with the VNC URL template and port.
#
# Maintainability:
# - If the VNC mechanism changes (e.g., we use a web-based VNC proxy), update logic here.
# - If we store task_id→emulator mappings in a DB or in-memory store, adjust code.
###############################################################################

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
# Assuming emulator_env provides a method to map task_id to vnc url or host/port
from core.emulator_env import EmulatorEnv

router = APIRouter()

class VNCResponse(BaseModel):
    status: str
    vnc_url: Optional[str]

# Initialize emulator environment handler
emulator_env = EmulatorEnv()

@router.get("/{task_id}/vnc", response_model=VNCResponse)
async def get_vnc_url_for_task(task_id: str):
    """
    GET /{task_id}/vnc

    Purpose:
    Given a task_id that represents a previously run app in the emulator, 
    return a VNC URL or instructions to connect to the emulator screen.

    Steps:
    1. Validate task_id.
    2. Use emulator_env to find which emulator instance is associated with this task_id.
    3. Construct a VNC URL from host/port info in instances.json or config.yaml.
    4. Return {"status":"success", "vnc_url":"vnc://..."} on success.

    Error Cases:
    - If task_id not found or not associated with any emulator instance: 404.
    - If emulator unreachable or no VNC info: 503 or 500 depending on error type.
    """
    task_id = task_id.strip()
    if not task_id:
        raise HTTPException(status_code=400, detail="task_id must not be empty.")

    try:
        vnc_url = emulator_env.get_vnc_url(task_id)
        # get_vnc_url might return a string like "vnc://emulator1:5900" or raise exceptions.
        if not vnc_url:
            # If no URL returned, maybe task_id not found
            raise HTTPException(status_code=404, detail=f"No VNC info for task_id {task_id}")
        return VNCResponse(status="success", vnc_url=vnc_url)
    except KeyError:
        # If emulator_env says no such task_id mapped
        raise HTTPException(status_code=404, detail=f"task_id {task_id} not found.")
    except ConnectionError:
        # If emulator_env tries to contact emulator or read data and fails
        raise HTTPException(status_code=503, detail="Emulator VNC service unavailable.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

###############################################################################
# Explanation:
#
# - We assume emulator_env.get_vnc_url(task_id) provides the correct VNC URL.
# - If not found, return 404.
# - If unavailable, 503 or 500 depending on error cause.
#
# Future Enhancements:
# - Add more detail: if multiple VNC endpoints exist, return a list?
# - Add authentication if exposing VNC info is sensitive.
###############################################################################
