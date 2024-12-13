###############################################################################
# routes_health.py
#
# Purpose:
# Defines FastAPI endpoints for health checks of the Providers subsystem.
# Returns a simple JSON that reports the overall status ("ok", "degraded", "down")
# and detailed status of each critical component: LLM, Sandbox, Emulator.
#
# Key Responsibilities:
# 1. Provide a quick /health endpoint that returns:
#    - status: "ok" if all components healthy, otherwise "degraded" or "down".
#    - details: a dictionary with keys like "llm", "sandbox", "emulator" and their respective statuses.
#
# 2. The status of each component might be determined by calling 
#    corresponding `core/` classes (llm_client, sandbox_env, emulator_env) or 
#    checking config files. For now, we might simulate or do a minimal check.
#
# Requirements:
# - If detailed checks are implemented, this endpoint might attempt 
#   a quick request to LLM endpoint, one sandbox endpoint, and one emulator endpoint.
# - If any fails, mark component as "unreachable".
#
# Maintainability:
# - If new components are added (e.g., a new provider), add them to the details.
# - If checks become more complex (e.g., latency measurement), expand logic.
###############################################################################

from fastapi import APIRouter
from pydantic import BaseModel
import requests

router = APIRouter()

class HealthResponse(BaseModel):
    status: str
    details: dict

@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    GET /health

    Purpose:
    Returns the overall health and the health of each core service. Checks may include:
    - LLM: Check if LLM endpoint responds quickly.
    - Sandbox: Check if at least one sandbox endpoint is reachable.
    - Emulator: Check if at least one emulator endpoint is reachable.

    Steps:
    1. Attempt a minimal GET request to each component's known endpoint.
    2. If all respond positively, overall status = "ok".
    3. If some fail, overall status = "degraded".
    4. If all fail or a critical issue occurs, overall status = "down".
    5. Return JSON with status and details.

    Note:
    This is a simplified logic. Real checks might be more sophisticated or read 
    from `instances.json` and `config.yaml` to find endpoints.
    """

    # Default assumptions
    llm_status = "unknown"
    sandbox_status = "unknown"
    emulator_status = "unknown"

    overall_status = "ok"  # assume ok, then downgrade if issues found

    # Example checks:
    # LLM check:
    # Suppose LLM endpoint from config or known default (like http://localhost:11434)
    llm_endpoint = "http://localhost:11434/api/generate"  # Hypothetical endpoint to test LLM quickly
    try:
        r = requests.post(llm_endpoint, json={"model":"llama3.2","prompt":"hello","stream":False}, timeout=2)
        if r.status_code == 200:
            llm_status = "ok"
        else:
            llm_status = f"error: got {r.status_code}"
            overall_status = "degraded"
    except Exception as e:
        llm_status = f"unreachable: {e}"
        overall_status = "degraded"

    # Sandbox check:
    # Suppose we read one endpoint from config.yaml or instances.json
    # For simplicity, hardcode a test endpoint. In practice, parse instances.json.
    sandbox_endpoint = "http://sandbox1:8002/ping"  # Hypothetical ping endpoint
    try:
        r = requests.get(sandbox_endpoint, timeout=2)
        if r.status_code == 200:
            sandbox_status = "ok"
        else:
            sandbox_status = f"error: got {r.status_code}"
            overall_status = "degraded"
    except Exception as e:
        sandbox_status = f"unreachable: {e}"
        overall_status = "degraded"

    # Emulator check:
    # Similarly, pick a known emulator endpoint from instances.json or config.
    emulator_endpoint = "http://emulator1:5555/ping"  # Hypothetical ping endpoint
    try:
        r = requests.get(emulator_endpoint, timeout=2)
        if r.status_code == 200:
            emulator_status = "ok"
        else:
            emulator_status = f"error: got {r.status_code}"
            overall_status = "degraded"
    except Exception as e:
        emulator_status = f"unreachable: {e}"
        overall_status = "degraded"

    details = {
        "llm": llm_status,
        "sandbox": sandbox_status,
        "emulator": emulator_status
    }

    # If all unknown or unreachable, maybe mark overall as "down"
    if all(s not in ["ok"] for s in details.values()):
        overall_status = "down"

    return HealthResponse(status=overall_status, details=details)

###############################################################################
# Explanation:
#
# - health_check(): attempts to contact LLM, Sandbox, and Emulator endpoints.
# - If all ok: overall status = ok.
# - If one or more degraded: overall status = degraded.
# - If all fail: overall status = down.
#
# This logic can be refined depending on actual endpoints.
# For now, we rely on hypothetical /ping endpoints or known test requests.
#
# Future Enhancements:
# - Read actual endpoints from config.yaml or instances.json.
# - Implement a dedicated "ping" route in each service for consistent checks.
# - Add retries or caching results to avoid slow responses.
###############################################################################
