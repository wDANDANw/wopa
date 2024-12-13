import logging
import httpx
from core.config_loader import get_env

###############################################################################
# connectors/app_service_connector.py
#
# Purpose:
# analyze_app(app_ref: str)
# Calls APP_SERVICE_URL endpoint to initiate app analysis.
#
# Assume POST /analyze/app with {"app":"app_ref"} returns {"task_id":"app-task-ref"}.
###############################################################################

logger = logging.getLogger(__name__)

def analyze_app(app_ref: str) -> str:
    app_url = get_env("APP_SERVICE_URL")
    payload = {"app": app_ref}

    try:
        response = httpx.post(f"{app_url}/analyze/app", json=payload)
        response.raise_for_status()
        data = response.json()
        task_id = data.get("task_id")
        if not task_id:
            logger.error("No task_id in app service response.")
            raise Exception("Invalid response from app service")
        return task_id
    except Exception as e:
        logger.error(f"Failed to analyze app: {e}")
        raise
