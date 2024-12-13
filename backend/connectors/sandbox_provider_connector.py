import logging
import httpx
from core.config_loader import get_env

###############################################################################
# connectors/sandbox_provider_connector.py
#
# Purpose:
# run_file_in_sandbox(file_ref: str)
# If needed by file service (though we decided orchestrator doesn't call it directly),
# the file service presumably uses it. However, we implement anyway for completeness.
#
# Suppose GET or POST to SANDBOX_PROVIDER_URL/run with {"file":file_ref} returns logs.
#
# For now, let's define a function that might be used by external services.
# Not directly called by orchestrator or routes. Just implemented for completeness.
###############################################################################

logger = logging.getLogger(__name__)

def run_file_in_sandbox(file_ref: str) -> dict:
    sandbox_url = get_env("SANDBOX_PROVIDER_URL")
    payload = {"file": file_ref}

    try:
        response = httpx.post(f"{sandbox_url}/run", json=payload)
        response.raise_for_status()
        data = response.json()
        # data might contain logs or analysis result
        return data
    except Exception as e:
        logger.error(f"Failed to run file in sandbox: {e}")
        raise
