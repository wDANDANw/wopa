from fastapi import APIRouter, HTTPException
from data_models.schemas import AppRequest
import requests

###############################################################################
# File: api/routes_app.py
#
# Purpose:
# POST /api/analyze/app -> calls http://services:8001/analyze_app
#
# Steps:
# 1) Validate AppRequest
# 2) requests.post(...) to services:8001/analyze_app
# 3) Return services JSON
###############################################################################

app_router = APIRouter()

@app_router.post("/app", summary="Analyze a suspicious app")
async def analyze_app(request: AppRequest):
    url = "http://services:8001/analyze_app"
    payload = {"app_ref": request.app, "instructions": request.instructions}

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
