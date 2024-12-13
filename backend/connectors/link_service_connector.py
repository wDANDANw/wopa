import logging
import httpx
from core.config_loader import get_env

###############################################################################
# connectors/link_service_connector.py
#
# Purpose:
# analyze_link(url: str, visual_verify: bool)
# Calls LINK_SERVICE_URL endpoint, possibly POST /analyze/link with {"url":..., "visual_verify":...}
#
# Returns a task_id on success.
###############################################################################

logger = logging.getLogger(__name__)

def analyze_link(url_str: str, visual_verify: bool) -> str:
    link_url = get_env("LINK_SERVICE_URL")
    payload = {"url": url_str, "visual_verify": visual_verify}

    try:
        response = httpx.post(f"{link_url}/analyze/link", json=payload)
        response.raise_for_status()
        data = response.json()
        task_id = data.get("task_id")
        if not task_id:
            logger.error("No task_id in link service response.")
            raise Exception("Invalid response from link service")
        return task_id
    except Exception as e:
        logger.error(f"Failed to analyze link: {e}")
        raise
