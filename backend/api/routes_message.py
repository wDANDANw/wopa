from fastapi import APIRouter, HTTPException
from data_models.schemas import MessageRequest
import requests

###############################################################################
# File: api/routes_message.py
#
# Purpose:
# POST /api/analyze/message -> calls http://services:8001/analyze_message
# and returns final JSON.
#
# Steps:
# 1) Validate MessageRequest
# 2) requests.post(...) to services:8001/analyze_message
# 3) Return services JSON
#
# Maintanability:
# - If services endpoint changes, just update the URL or payload.
###############################################################################

message_router = APIRouter()

@message_router.post("/message", summary="Analyze a suspicious message")
async def analyze_message(request: MessageRequest):
    content = request.message
    url = "http://services:8001/analyze_message"
    payload = {"message": content}

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
