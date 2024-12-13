from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, Dict, Any
from datetime import datetime

###############################################################################
# File: data_models/schemas.py
#
# Purpose:
# This file defines the Pydantic data models (schemas) that describe the shapes 
# of requests and responses for the backend, as well as internal models for tasks.
#
# Why Pydantic?
# - Pydantic ensures data validation and provides automatic error responses 
#   when incoming JSON doesn't match the specified schema.
#
# Design & Philosophy:
# - Keep schemas simple and focused on their domain.
# - Separate request and response models clearly.
# - Include docstrings and Field(...) definitions for clarity.
#
# Maintainability:
# - If requirements change (e.g., we add new fields to the task or result), 
#   we only need to update these schemas. Tests should catch any mismatch.
#
# Schemas:
# 1. MessageRequest: for /api/analyze/message endpoint
# 2. LinkRequest: for /api/analyze/link endpoint (using HttpUrl validator)
# 3. FileRequest: for /api/analyze/file endpoint
# 4. AppRequest: for /api/analyze/app endpoint
# 5. TaskStatusResponse: returned by GET /api/task/{task_id} showing status/result
# 6. AnalysisTask: internal representation of a task in queue
# 7. AnalysisResult: represents stored result of a completed task
# 8. UpdateTaskStatusRequest: for POST /api/task/update_task_status/{task_id}
###############################################################################


class MessageRequest(BaseModel):
    """
    Represents the payload for analyzing a suspicious message.

    Example:
    {
      "message": "Suspicious message content"
    }
    """
    message: str = Field(..., description="The suspicious text message to analyze.")

    # No need for special validation here. Just a non-empty string.
    # If needed, we can add min_length=1 to ensure not empty.


class LinkRequest(BaseModel):
    """
    Represents the payload for analyzing a suspicious link.

    Example:
    {
      "url": "http://phish.url",
      "visual_verify": false
    }
    """
    url: HttpUrl = Field(..., description="A URL to be analyzed for phishing or malicious content.")
    visual_verify: bool = Field(False, description="Whether to perform visual-based verification.")


class FileRequest(BaseModel):
    """
    Represents the payload for analyzing a suspicious file.

    Since this is a backend, we might receive a file reference (e.g., a UUID or path).
    Actual file upload endpoints may differ; here we assume 'file' is a reference ID.

    Example:
    {
      "file": "file_reference_id"
    }
    """
    file: str = Field(..., description="A reference to the suspicious file to analyze.")


class AppRequest(BaseModel):
    """
    Represents the payload for analyzing a suspicious app (APK reference).

    This might be an app package reference to be analyzed by the external app service.
    
    Example:
    {
      "app": "app_package_ref"
    }
    """
    app: str = Field(..., description="A reference to the suspicious app to analyze.")


class TaskStatusResponse(BaseModel):
    """
    Represents the status response returned by GET /api/task/{task_id}.

    Fields:
    - status: 'pending', 'in_progress', 'completed', 'error', etc.
    - result: optional dict containing analysis results if completed.
    """
    status: str = Field(..., description="The current status of the task.")
    result: Optional[Dict[str, Any]] = Field(None, description="Analysis result if available.")


class AnalysisTask(BaseModel):
    """
    Internal model representing a task. This might be queued by request_handler.
    
    Fields:
    - type: 'message', 'link', 'file', 'app'
    - content: the actual string reference (message text, URL, file_id, app_id)
    - timestamp: when the task was created. Useful for logging and ordering.

    Example:
    {
      "type": "message",
      "content": "Suspicious text",
      "timestamp": "2024-10-24T12:00:00Z"
    }
    """
    type: str = Field(..., description="Type of the task: message, link, file, app.")
    content: str = Field(..., description="The content related to this task.")
    timestamp: datetime = Field(..., description="When the task was created or enqueued.")


class AnalysisResult(BaseModel):
    """
    Represents the stored result of a completed task.

    Fields:
    - status: e.g., 'completed', 'error'
    - result: a dictionary with detailed analysis info
    """
    status: str = Field(..., description="Status of the completed task.")
    result: Dict[str, Any] = Field(..., description="Detailed result from analysis.")


class UpdateTaskStatusRequest(BaseModel):
    """
    Payload for POST /api/task/update_task_status/{task_id}
    
    Allows external modules (services/workers/providers) to update the 
    task's status and optionally provide a result.

    Fields:
    - status: new status (e.g., completed, error)
    - result: optional dict containing updated result info.
    """
    status: str = Field(..., description="New status of the task.")
    result: Optional[Dict[str, Any]] = Field(None, description="Optional result data to store.")


###############################################################################
# Future changes:
#
# - If new task types emerge, we can add an enum or validation logic in AnalysisTask.
# - If result structure changes often, we might break down 'result' into more 
#   specific models for each task type. For now, a flexible Dict[str,Any] is used.
#
# This concludes the schemas. Next files (like config_loader, orchestrator, request_handler,
# routes, connectors) will use these schemas.
#
# Not the last file yet:
# We will proceed to implement other files (core/config_loader.py, core/request_handler.py, 
# etc.) similarly. We'll notify at the end when we reach the last implementation file.
###############################################################################
