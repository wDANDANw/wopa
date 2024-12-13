import logging
import httpx
from core.config_loader import get_env

###############################################################################
# connectors/file_service_connector.py
#
# Purpose:
# analyze_file(file_ref: str)
# Calls FILE_SERVICE_URL endpoint to initiate file analysis.
#
# Assume POST /analyze/file with {"file":"file_ref"} returns {"task_id":"file-task-ref"}.
###############################################################################

logger = logging.getLogger(__name__)

def analyze_file(file_ref: str) -> str:
    file_url = get_env("FILE_SERVICE_URL")
    payload = {"file": file_ref}

    try:
        response = httpx.post(f"{file_url}/analyze/file", json=payload)
        response.raise_for_status()
        data = response.json()
        task_id = data.get("task_id")
        if not task_id:
            logger.error("No task_id in file service response.")
            raise Exception("Invalid response from file service")
        return task_id
    except Exception as e:
        logger.error(f"Failed to analyze file: {e}")
        raise
