import logging
import httpx
from core.config_loader import get_env

###############################################################################
# connectors/emulator_provider_connector.py
#
# Purpose:
# get_vnc_session(app_ref: str)
# Calls EMULATOR_PROVIDER_URL to obtain a VNC session link for a given app.
#
# Assume GET /vnc?app=app_ref returns {"vnc_url":"http://provider_manager/{task_id}/vnc"}
#
###############################################################################

logger = logging.getLogger(__name__)

def get_vnc_session(app_ref: str) -> str:
    emulator_url = get_env("EMULATOR_PROVIDER_URL")
    # Suppose the emulator provider accepts a GET param app=app_ref
    try:
        response = httpx.get(f"{emulator_url}/vnc", params={"app":app_ref})
        response.raise_for_status()
        data = response.json()
        vnc_url = data.get("vnc_url")
        if not vnc_url:
            logger.error("No vnc_url in emulator provider response.")
            raise Exception("Invalid response from emulator provider")
        return vnc_url
    except Exception as e:
        logger.error(f"Failed to get vnc session: {e}")
        raise
