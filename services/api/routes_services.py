###############################################################################
# routes_services.py
#
# Purpose:
# Defines endpoints related to initiating analyses. Now updated with more logging.
#
# Enhancements:
# - More logging at start/end of each endpoint.
# - If errors occur, we log them.
# - handle_manager_response() logs the final outcome.
#
# Steps:
# - /available_services: returns metadata from each service.
# - /analyze_message: now expects message_service to possibly return completed 
#   status immediately.
# - Other analyze endpoints remain as is, but now we add more logs.
#
# Error Handling:
# - If "status":"error", we log message before deciding HTTP code.
#
###############################################################################

import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger("services")

class MessageRequest(BaseModel):
    message: str

class LinkRequest(BaseModel):
    url: str

class FileRefRequest(BaseModel):
    file_ref: str

class AppReferenceRequest(BaseModel):
    app_ref: str
    instructions: str

@router.get("/available_services", summary="List all available services")
def available_services(request: Request):
    logger.info("GET /available_services called.")
    manager = request.app.state.manager
    service_map = request.app.state.service_map
    services_list = []
    for sname, service_instance in service_map.items():
        metadata = service_instance.get_metadata()
        metadata["service_name"] = sname
        services_list.append(metadata)
    logger.debug("GET /available_services returning: %s", services_list)
    return services_list

def handle_manager_response(resp: dict):
    status = resp.get("status")
    if status == "error":
        msg = resp.get("message","Unknown error")
        logger.warning("handle_manager_response: Task returned error: %s", msg)
        if any(word in msg.lower() for word in ["invalid","missing","required","bad input"]):
            raise HTTPException(status_code=400, detail=msg)
        else:
            raise HTTPException(status_code=500, detail=msg)
    else:
        # enqueued or completed
        logger.info("handle_manager_response: Returning success response: %s", resp)
        return resp

@router.post("/analyze_message", summary="Analyze a textual message")
def analyze_message(request: Request, body: MessageRequest):
    logger.info("POST /analyze_message called with body=%s", body.dict())
    manager = request.app.state.manager
    service_name = "message_analysis"
    resp = manager.process_task_now(service_name, body.dict())
    return handle_manager_response(resp)

@router.post("/analyze_link", summary="Analyze a URL")
def analyze_link(request: Request, body: LinkRequest):
    logger.info("POST /analyze_link called with body=%s", body.dict())
    manager = request.app.state.manager
    service_name = "link_analysis"
    resp = manager.process_task_now(service_name, body.dict())
    return handle_manager_response(resp)

@router.post("/analyze_file_static", summary="Perform static analysis on a file")
def analyze_file_static(request: Request, body: FileRefRequest):
    logger.info("POST /analyze_file_static called with body=%s", body.dict())
    manager = request.app.state.manager
    service_name = "file_static_analysis"
    resp = manager.process_task_now(service_name, body.dict())
    return handle_manager_response(resp)

@router.post("/analyze_file_dynamic", summary="Perform dynamic (sandbox) analysis on a file")
def analyze_file_dynamic(request: Request, body: FileRefRequest):
    logger.info("POST /analyze_file_dynamic called with body=%s", body.dict())
    manager = request.app.state.manager
    service_name = "file_dynamic_analysis"
    resp = manager.process_task_now(service_name, body.dict())
    return handle_manager_response(resp)

@router.post("/analyze_app", summary="Analyze an app (APK) behavior")
def analyze_app(request: Request, body: AppReferenceRequest):
    logger.info("POST /analyze_app called with body=%s", body.dict())
    manager = request.app.state.manager
    service_name = "app_analysis"
    resp = manager.process_task_now(service_name, body.dict())
    return handle_manager_response(resp)

###############################################################################
# Notes:
#
# Logging:
# - Each endpoint logs input at INFO level.
# - handle_manager_response logs final output or error.
# - message_service logs inside its process() steps.
#
# If aggregator or worker fails, message_service returns status=error with a message.
# handle_manager_response logs and returns suitable HTTP error code.
#
# This improved logging will help trace where "Unknown error" might come from.
# If aggregator is not reachable or returns invalid JSON, message_service logs that error.
#
###############################################################################
