###############################################################################
# routes_admin.py
#
# Purpose:
# Defines administrative or diagnostic endpoints for the Providers subsystem.
# These endpoints are not generally exposed to external end-users. Instead, 
# they help developers or admins:
# - List all known endpoints that the subsystem provides (for documentation or debugging).
# - Possibly return internal config details.
#
# Key Responsibilities:
# 1. A GET endpoint to return a list of available endpoints and their paths.
# 2. Optional: A GET endpoint to show current config.yaml values or instances.json data.
#
# Requirements:
# - Because this is admin-focused, consider adding basic auth or restricting access 
#   if in a production environment.
# - If listing endpoints, we can rely on FastAPI’s `app.routes` or a manual route registry.
#
# Maintainability:
# - If new endpoints are added, ensure they appear in the listed output.
# - If we add more admin features (like triggering a refresh of instances.json), 
#   add more routes here.
###############################################################################

from fastapi import APIRouter, Request
from pydantic import BaseModel
import os
import json

router = APIRouter()

class EndpointsListResponse(BaseModel):
    endpoints: list[str]

@router.get("/endpoints", response_model=EndpointsListResponse)
async def list_endpoints(request: Request):
    """
    GET /admin/endpoints

    Purpose:
    Return a list of known endpoints provided by the Providers subsystem. 
    This helps admin UI or developers know what routes are available.

    Steps:
    1. Access request.app.routes to get a list of registered routes.
    2. Extract path and method info, or just path if we want simple info.
    3. Return them as a JSON list.

    Future Enhancements:
    - Filter out admin endpoints themselves if we don’t want them listed.
    - Include HTTP methods or tags if needed.
    """
    app = request.app
    paths = []
    for route in app.routes:
        # route might be of type APIRoute or others
        # We filter by APIRoute and skip static or internal routes if any
        if hasattr(route, "path"):
            # route could have multiple methods
            # For simplicity, just list paths. Or we can do:
            # methods = getattr(route, "methods", ["UNKNOWN"])
            # For now, just paths:
            paths.append(route.path)

    # Remove duplicates by converting to a set then back to list if needed
    unique_paths = sorted(set(paths))
    return EndpointsListResponse(endpoints=unique_paths)

@router.get("/config")
async def show_config():
    """
    GET /admin/config

    Purpose:
    Return the current config.yaml and instances.json data for admin purposes.

    Steps:
    1. Read config.yaml and instances.json.
    2. Return as JSON.
    
    Security Consideration:
    - This might expose internal details. In production, consider auth.
    - For now, no auth. This is a PoC or internal tool.

    If config.yaml or instances.json doesn’t exist or can’t be read, return partial data.
    """
    response_data = {}
    # Attempt to read config.yaml
    config_path = "config.yaml"
    if os.path.exists(config_path):
        import yaml
        with open(config_path, "r") as f:
            try:
                config_data = yaml.safe_load(f)
                response_data["config"] = config_data
            except Exception as e:
                response_data["config_error"] = f"Failed to parse config.yaml: {e}"
    else:
        response_data["config_error"] = "config.yaml not found"

    # Attempt to read instances.json
    instances_path = "instances.json"
    if os.path.exists(instances_path):
        with open(instances_path, "r") as f:
            try:
                instances_data = json.load(f)
                response_data["instances"] = instances_data
            except Exception as e:
                response_data["instances_error"] = f"Failed to parse instances.json: {e}"
    else:
        response_data["instances_error"] = "instances.json not found"

    return response_data

# routes_admin.py (New code addition)


###############################################################################
# Explanation:
#
# - /admin/endpoints:
#   Lists all known routes (like /health, /llm/chat_complete, etc.).
#   Useful for admin UI to dynamically show what is available.
#
# - /admin/config:
#   Returns current config and instances.json data if available, aiding debugging.
#
# Security:
# Currently no authentication. For production, add auth or IP restrictions.
#
# Future Enhancements:
# - Add a POST endpoint to refresh instances.json or re-run terraform provisioning.
# - Add auth tokens or IP whitelisting to protect these admin endpoints.
###############################################################################
