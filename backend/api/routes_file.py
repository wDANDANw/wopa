from fastapi import APIRouter, HTTPException
from data_models.schemas import FileRequest
import requests

###############################################################################
# File: api/routes_file.py
#
# Purpose:
# POST /api/analyze/file -> calls http://services:8001/analyze_file
#
# Steps:
# 1) Validate FileRequest
# 2) requests.post(...) to services:8001/analyze_file
# 3) Return services JSON
###############################################################################

file_router = APIRouter()

@file_router.post("/file", summary="Analyze a suspicious file")
async def analyze_file(request: FileRequest):
    url = "http://services:8001/analyze_file"
    payload = {"file": request.file}

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
