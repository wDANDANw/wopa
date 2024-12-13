###############################################################################
# routes_emulator.py
#
# Purpose:
# Provides a set of endpoints to interact with and control the Android emulator,
# including:
# - Device initialization (provisioning)
# - App file upload
# - App installation
# - App launching (run_app)
# - Retrieving VNC URL for a running app session
# - UI interactions: tap, type, swipe, back, home
# - Taking screenshots
#
# New Changes:
# - `task_id` query parameter added to control endpoints (tap, type, swipe, back, home, screenshot)
#   so multiple emulators/endpoints can be distinguished.
# - If `task_id` is not found or not provided, we return an error.
#
# Maintainability:
# - If new actions or parameters are needed, just add a new endpoint or adjust existing ones.
# - If authentication or rate-limiting needed, add middleware or dependencies.
###############################################################################

import os
import hashlib
import logging
from fastapi import APIRouter, HTTPException, File, UploadFile, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any

from core.emulator_env import EmulatorEnv

router = APIRouter()
logger = logging.getLogger(__name__)

APKS_DIR = "/providers/apks"
os.makedirs(APKS_DIR, exist_ok=True)

###############################################################################
# Shared Schemas and Utilities
###############################################################################

class EmulatorRequest(BaseModel):
    app_ref: str  # local filename/path in APKS_DIR or absolute path

class EmulatorResponse(BaseModel):
    status: str
    visuals: dict        # {"screenshot":"base64..."}
    events: list[str]
    task_id: str

class InstallRequest(BaseModel):
    app_ref: str

class TapRequest(BaseModel):
    x: int
    y: int

class TypeRequest(BaseModel):
    text: str

class SwipeRequest(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int

# Emulator environment instance
emulator_env = EmulatorEnv()

def compute_sha256(file_path: str) -> str:
    """Compute SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def get_host_port_from_task_id(task_id: str) -> str:
    """
    Given a task_id, retrieve the host_port from emulator_env.task_map.
    Raises 404 if not found.
    """
    if task_id not in emulator_env.task_map:
        raise HTTPException(status_code=404, detail=f"No such task_id: {task_id}")
    endpoint = emulator_env.task_map[task_id]["endpoint"]
    host_port = endpoint.split("//")[-1]
    return host_port

###############################################################################
# Endpoints
###############################################################################

@router.post("/init_device")
async def init_device():
    """
    POST /emulator/init_device

    Trigger provisioning (or re-init) of the emulator device. 
    Returns {status:"ok"} if successful.

    Example:
    curl -X POST http://localhost:8003/emulator/init_device
    """
    try:
        logger.info("init_device: Initializing device.")
        emulator_env.init_device()
        return {"status": "ok", "message": "Device initialized"}
    except Exception as e:
        logger.exception("init_device failed.")
        raise HTTPException(status_code=500, detail=f"Initialization failed: {e}")

@router.post("/upload_app")
async def upload_app(file: UploadFile = File(...)):
    """
    POST /emulator/upload_app

    Upload an APK file into APKS_DIR.

    Example:
    curl -X POST -F file=@/path/to/app.apk http://localhost:8003/emulator/upload_app
    """
    filename = file.filename.strip()
    if not filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    local_path = os.path.join(APKS_DIR, filename)
    temp_path = local_path + ".tmp"
    try:
        with open(temp_path, "wb") as f_out:
            content = await file.read()
            f_out.write(content)
    except Exception as e:
        logger.error(f"Failed to store uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to store uploaded file.")

    new_checksum = compute_sha256(temp_path)

    if os.path.exists(local_path):
        existing_checksum = compute_sha256(local_path)
        if existing_checksum == new_checksum:
            os.remove(temp_path)
            return {"status":"ok","filename":filename,"message":"File already exists"}
        else:
            os.remove(temp_path)
            raise HTTPException(status_code=400, detail=f"Filename {filename} conflict with different file.")
    
    os.rename(temp_path, local_path)
    logger.info(f"Uploaded APK: {filename}")
    return {"status":"ok","filename":filename}

@router.post("/install_app")
async def install_app(request: InstallRequest):
    """
    POST /emulator/install_app

    Install an APK into the emulator device.

    Example:
    curl -X POST -H "Content-Type: application/json" \
      -d '{"app_ref":"app.apk"}' http://localhost:8003/emulator/install_app
    """
    app_ref = request.app_ref.strip()
    if not app_ref:
        raise HTTPException(status_code=400, detail="app_ref must not be empty.")

    if not os.path.isabs(app_ref):
        local_path = os.path.join(APKS_DIR, app_ref)
    else:
        local_path = app_ref

    if not os.path.exists(local_path):
        raise HTTPException(status_code=400, detail=f"APK file not found: {local_path}")

    try:
        emulator_env.install_app(local_path)
        return {"status":"ok","message":f"App {app_ref} installed."}
    except ConnectionError:
        raise HTTPException(status_code=503, detail="Emulator service unavailable.")
    except Exception as e:
        logger.exception("Failed to install app.")
        raise HTTPException(status_code=500, detail=f"Install error: {e}")

@router.post("/run_app", response_model=EmulatorResponse)
async def run_app_in_emulator(request: EmulatorRequest):
    """
    POST /emulator/run_app

    Launch and run an app from a given APK file (installs if not installed).

    Example:
    curl -X POST -H "Content-Type: application/json" -d '{"app_ref":"app.apk"}' \
         http://localhost:8003/emulator/run_app
    """
    app_ref = request.app_ref.strip()
    if not app_ref:
        raise HTTPException(status_code=400, detail="app_ref must not be empty.")

    if not os.path.isabs(app_ref):
        local_path = os.path.join(APKS_DIR, app_ref)
    else:
        local_path = app_ref

    if not os.path.exists(local_path):
        raise HTTPException(status_code=400, detail=f"APK file not found: {local_path}")

    try:
        result = emulator_env.run_app(local_path)
        visuals = result.get("visuals", {})
        events = result.get("events", [])
        task_id = result.get("task_id")
        if not task_id:
            raise HTTPException(status_code=500, detail="No task_id from run_app.")
        return EmulatorResponse(status="success", visuals=visuals, events=events, task_id=task_id)
    except ConnectionError:
        raise HTTPException(status_code=503, detail="Emulator service unavailable.")
    except Exception as e:
        logger.exception("Unexpected error running app.")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

@router.get("/get_vnc_url")
async def get_vnc_url(task_id: str = Query(..., description="Task ID returned by run_app")):
    """
    GET /emulator/get_vnc_url?task_id=...

    Return the VNC URL for a given task_id.

    Example:
    curl "http://localhost:8003/emulator/get_vnc_url?task_id=YOUR_TASK_ID"
    """
    try:
        vnc = emulator_env.get_vnc_url(task_id)
        return {"status":"ok","vnc_url":vnc}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"No such task_id: {task_id}")
    except Exception as e:
        logger.exception("Error getting VNC URL.")
        raise HTTPException(status_code=500, detail=f"Error: {e}")

@router.post("/tap")
async def tap_endpoint(request: TapRequest, task_id: str = Query(..., description="Task ID to identify which emulator to control")):
    """
    POST /emulator/tap?task_id=...

    Tap on the given coordinates (x,y).

    Example:
    curl -X POST -H "Content-Type: application/json" -d '{"x":100,"y":200}' \
         "http://localhost:8003/emulator/tap?task_id=YOUR_TASK_ID"
    """
    try:
        host_port = get_host_port_from_task_id(task_id)
        emulator_env.control_app(host_port, "tap", x=request.x, y=request.y)
        return {"status":"ok","message":"Tap done"}
    except Exception as e:
        logger.exception("Tap failed.")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/type")
async def type_endpoint(request: TypeRequest, task_id: str = Query(..., description="Task ID")):
    """
    POST /emulator/type?task_id=...

    Type the given text on the device.

    Example:
    curl -X POST -H "Content-Type: application/json" -d '{"text":"Hello"}' \
         "http://localhost:8003/emulator/type?task_id=YOUR_TASK_ID"
    """
    try:
        host_port = get_host_port_from_task_id(task_id)
        emulator_env.control_app(host_port, "type", text=request.text)
        return {"status":"ok","message":f"Typed {request.text}"}
    except Exception as e:
        logger.exception("Type failed.")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/swipe")
async def swipe_endpoint(request: SwipeRequest, task_id: str = Query(..., description="Task ID")):
    """
    POST /emulator/swipe?task_id=...

    Swipe from (x1,y1) to (x2,y2).

    Example:
    curl -X POST -H "Content-Type: application/json" \
      -d '{"x1":100,"y1":200,"x2":300,"y2":400}' \
      "http://localhost:8003/emulator/swipe?task_id=YOUR_TASK_ID"
    """
    try:
        host_port = get_host_port_from_task_id(task_id)
        emulator_env.control_app(host_port, "swipe", x1=request.x1, y1=request.y1, x2=request.x2, y2=request.y2)
        return {"status":"ok","message":"Swipe done"}
    except Exception as e:
        logger.exception("Swipe failed.")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/back")
async def back_endpoint(task_id: str = Query(..., description="Task ID")):
    """
    POST /emulator/back?task_id=...

    Press the back button.

    Example:
    curl -X POST "http://localhost:8003/emulator/back?task_id=YOUR_TASK_ID"
    """
    try:
        host_port = get_host_port_from_task_id(task_id)
        emulator_env.control_app(host_port, "back")
        return {"status":"ok","message":"Back done"}
    except Exception as e:
        logger.exception("Back failed.")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/home")
async def home_endpoint(task_id: str = Query(..., description="Task ID")):
    """
    POST /emulator/home?task_id=...

    Go to the device's home screen.

    Example:
    curl -X POST "http://localhost:8003/emulator/home?task_id=YOUR_TASK_ID"
    """
    try:
        host_port = get_host_port_from_task_id(task_id)
        emulator_env.control_app(host_port, "home")
        return {"status":"ok","message":"Home done"}
    except Exception as e:
        logger.exception("Home failed.")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/screenshot")
async def screenshot_endpoint(task_id: str = Query(..., description="Task ID")):
    """
    GET /emulator/screenshot?task_id=...

    Take a screenshot and return it as base64.

    Example:
    curl "http://localhost:8003/emulator/screenshot?task_id=YOUR_TASK_ID"
    """
    try:
        host_port = get_host_port_from_task_id(task_id)
        b64_data = emulator_env.control_app(host_port, "screenshot")
        return {"status":"ok","screenshot":b64_data}
    except Exception as e:
        logger.exception("Screenshot failed.")
        raise HTTPException(status_code=500, detail=str(e))

###############################################################################
# Ready to Test
#
# Example curl commands (assuming we already ran run_app and got a task_id):
#
# 1. Init device:
#    curl -X POST http://localhost:8003/emulator/init_device
#
# 2. Upload an APK:
# Note: Don't forget to include the `@` symbol before the file path.
#    curl -X POST http://localhost:8003/emulator/upload_app -F "file=@/path/to/app.apk" 
#
# 3. Install an app:
#    curl -X POST -H "Content-Type: application/json" -d '{"app_ref":"app.apk"}' \
#         http://localhost:8003/emulator/install_app
#
# 4. Run an app:
#    curl -X POST -H "Content-Type: application/json" -d '{"app_ref":"app.apk"}' \
#         http://localhost:8003/emulator/run_app
#   -> This returns a JSON with a task_id. Suppose task_id=abcd-1234
#
# 5. Get VNC URL:
#    curl "http://localhost:8003/emulator/get_vnc_url?task_id=abcd-1234"
#
# 6. Tap:
#    curl -X POST -H "Content-Type: application/json" -d '{"x":100,"y":200}' \
#         "http://localhost:8003/emulator/tap?task_id=abcd-1234"
#
# 7. Type:
#    curl -X POST -H "Content-Type: application/json" -d '{"text":"Hello"}' \
#         "http://localhost:8003/emulator/type?task_id=abcd-1234"
#
# 8. Swipe:
#    curl -X POST -H "Content-Type: application/json" \
#        -d '{"x1":100,"y1":200,"x2":300,"y2":400}' \
#        "http://localhost:8003/emulator/swipe?task_id=abcd-1234"
#
# 9. Back:
#    curl -X POST "http://localhost:8003/emulator/back?task_id=abcd-1234"
#
# 10. Home:
#     curl -X POST "http://localhost:8003/emulator/home?task_id=abcd-1234"
#
# 11. Screenshot:
#     curl "http://localhost:8003/emulator/screenshot?task_id=abcd-1234"
#
# This ensures we can control a specific emulator session identified by task_id.
###############################################################################
