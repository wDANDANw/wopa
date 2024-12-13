from fastapi import APIRouter, HTTPException, Body
from core.db import get_db_connection

auth_router = APIRouter()

@auth_router.post("/login")
def login(username: str = Body(...), password: str = Body(...)):
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM Accounts WHERE Username=%s AND Password=%s"
        cursor.execute(query, (username, password))
        user = cursor.fetchone()
        if user:
            account_id = user["AccountID"]
            return {
                "success": True,
                "message": "Login successful",
                "AccountID": account_id
            }
        else:
            return {
                "success": False,
                "message": "Invalid credentials"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Server error")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
