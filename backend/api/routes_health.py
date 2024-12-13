from fastapi import APIRouter
from fastapi.responses import JSONResponse

###############################################################################
# File: api/routes_health.py
#
# Purpose:
# Provide a simple /api/health endpoint for health checks.
#
# Design & Philosophy:
# - A simple GET endpoint returning {"status":"healthy"}.
# - Used by T-Backend-Health-001 test.
#
# Maintainability:
# - If health conditions become more complex, we can add checks here.
###############################################################################

health_router = APIRouter()

@health_router.get("/health", summary="Health check endpoint")
async def health_check():
    """
    Health check endpoint.
    Returns a JSON with {"status":"healthy"} to indicate server is up.
    """
    return JSONResponse({"status":"healthy"})
