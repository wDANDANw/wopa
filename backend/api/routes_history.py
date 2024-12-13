from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import Optional
from core.db import get_db_connection

###############################################################################
# File: api/routes_history.py
#
# Purpose:
# Implements:
# - GET /search_history?AccountID=... : Retrieve user’s history records
# - POST /add_history : Add a new history record
#
# Design & Philosophy:
# - Similar to the original Flask code given by the user, but now in FastAPI style.
# - If no records found, return 404.
# - On DB or server errors, return 500.
# - POST /add_history expects JSON with AccountID, isMalicious, analysisType, Report,
#   Confidence, and analysisContent.
#
# Maintainability:
# - If table schema changes, update the SQL queries.
###############################################################################

history_router = APIRouter()

@history_router.get("/search_history")
def search_history(AccountID: int = Query(..., description="AccountID to query history for")):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM Historys WHERE AccountID = %s"
        cursor.execute(query, (AccountID,))
        histories = cursor.fetchall()
        if not histories:
            # No history records found
            return {"success": False, "message": "No history records found for this AccountID"}, 404
        return {"success": True, "histories": histories}
    except Exception as e:
        # Log or raise an HTTPException(500)
        raise HTTPException(status_code=500, detail="Server error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


class AddHistoryRequest(BaseModel):
    AccountID: int = Field(..., description="The AccountID of the user")
    isMalicious: bool = Field(..., description="Is the analyzed content malicious?")
    analysisType: str = Field(..., description="One of 'URL', 'MSG', 'FILE'")
    Report: str = Field(..., description="Short report")
    Confidence: int = Field(..., description="Confidence score (0-100)")
    analysisContent: str = Field(..., description="Content analyzed, e.g. URL or message text")

@history_router.post("/add_history")
def add_history(payload: AddHistoryRequest):
    # Validate analysisType
    valid_types = ["URL", "MSG", "FILE"]
    if payload.analysisType not in valid_types:
        raise HTTPException(status_code=400, detail=f"analysisType must be one of {valid_types}")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
        INSERT INTO Historys (AccountID, isMalicious, analysisType, Report, Confidence, analysisContent)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            payload.AccountID,
            payload.isMalicious,
            payload.analysisType,
            payload.Report,
            payload.Confidence,
            payload.analysisContent
        ))
        conn.commit()
        return {"success": True, "message": "History added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Server error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
