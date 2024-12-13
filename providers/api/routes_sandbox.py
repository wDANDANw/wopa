###############################################################################
# routes_sandbox.py
#
# Purpose:
# Defines FastAPI routes for submitting files to a sandbox environment for analysis.
# Clients (e.g., WOPA’s main system) can POST a file reference to this endpoint, 
# and this endpoint sends the file to a selected sandbox instance (using logic in 
# sandbox_env.py or directly calling the sandbox's API).
#
# Key Responsibilities:
# 1. Receive a file reference or identifier (not the actual file binary, 
#    assuming the Providers subsystem has secure means to access the file or 
#    the file is already known).
# 2. Forward the request to the sandbox environment (e.g., via sandbox_env’s run_file method).
# 3. Return the sandbox logs indicating benign or malicious activities.
#
# Requirements:
# - File reference could be a path in a shared volume, or a known ID that sandbox_env uses.
# - sandbox_env.py handles actual sandbox call (http POST or similar).
#
# Maintainability:
# - If sandbox endpoints or API keys change, update sandbox_env.py or config.yaml.
# - If input schema changes, adjust Pydantic models.
# - If multiple sandbox instances exist, sandbox_env.py chooses which one to use.
###############################################################################

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.sandbox_env import SandboxEnv

router = APIRouter()

class SandboxRequest(BaseModel):
    file_ref: str  # a reference (path or ID) to the suspicious file

class SandboxResponse(BaseModel):
    status: str
    logs: list[str]  # List of strings representing sandbox analysis logs (syscalls, etc.)

# Initialize sandbox environment handler
sandbox_env = SandboxEnv()

@router.post("/run_file", response_model=SandboxResponse)
async def run_file_in_sandbox(request: SandboxRequest):
    """
    POST /sandbox/run_file

    Purpose:
    Submit a suspicious file reference to the sandbox for analysis.

    Steps:
    1. Validate 'file_ref'.
    2. Call sandbox_env.run_file(file_ref) to get logs.
    3. Return {"status":"success","logs":[...]} on success.
    4. On sandbox errors (timeout, unreachable), return appropriate HTTPException.

    Error Cases:
    - If file_ref is empty: HTTP 400
    - If sandbox unreachable: HTTP 503
    - If logs returned are empty or suspicious: still status=success but logs might indicate no activity.
    """
    file_ref = request.file_ref.strip()
    if not file_ref:
        raise HTTPException(status_code=400, detail="file_ref must not be empty.")

    try:
        logs = sandbox_env.run_file(file_ref)  
        # run_file might return a list of log lines or raise exceptions.
        return SandboxResponse(status="success", logs=logs)
    except ConnectionError:
        # Sandbox service unreachable
        raise HTTPException(status_code=503, detail="Sandbox service unavailable.")
    except ValueError as ve:
        # If sandbox_env run_file returns ValueError for invalid file_ref
        raise HTTPException(status_code=400, detail=f"Invalid file_ref: {ve}")
    except Exception as e:
        # Unexpected errors
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

###############################################################################
# Explanation:
#
# - SandboxRequest: Client provides file_ref (string).
# - run_file_in_sandbox: Validates input, calls sandbox_env's run_file method.
# - On success: returns status=success and logs array.
# - On errors: raises HTTPExceptions with relevant status codes.
#
# If sandbox_env chooses which sandbox instance to use, it handles that logic internally.
#
# Future Enhancements:
# - Add more endpoints for retrieving historical sandbox runs or changing sandbox configs.
# - Add pagination if logs are huge, or store logs in a database.
###############################################################################
