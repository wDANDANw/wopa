from fastapi import APIRouter, HTTPException
from data_models.schemas import LinkRequest
import requests

###############################################################################
# File: api/routes_link.py
#
# Purpose:
# POST /api/analyze/link -> calls http://services:8001/analyze_link
#
# Steps:
# 1) Validate LinkRequest
# 2) requests.post(...) to services:8001/analyze_link
# 3) Return services JSON
###############################################################################

link_router = APIRouter()

@link_router.post("/link", summary="Analyze a suspicious link")
async def analyze_link(request: LinkRequest):
    url = "http://services:8001/analyze_link"
    link_url = str(request.url).rstrip('/')
    payload = {"url": link_url, "visual_verify": request.visual_verify}

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
