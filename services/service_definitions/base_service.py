###############################################################################
# base_service.py
#
# Purpose:
# Defines the BaseService abstract class that all concrete service classes 
# (message_analysis, link_analysis, file_static_analysis, file_dynamic_analysis, app_analysis)
# extend. This base class provides a common interface and shared logic for all 
# services, improving maintainability and consistency.
#
# Responsibilities:
# Each concrete service must implement:
# - validate_task(task_data: dict) -> Optional[dict]
# - process(task_data: dict) -> dict
# - get_metadata() -> dict
#
# Methods:
# 1. validate_task(task_data: dict) -> Optional[dict]:
#    Checks if the input data meets the service's requirements.
#    Returns None if valid, or {"error":"message"} if invalid.
#
# 2. process(task_data: dict) -> dict:
#    Performs initial processing steps for the analysis request.
#    - Typically calls validate_task() internally or the manager calls it first.
#    - If invalid, return {"status":"error","message":"..."} or let caller handle.
#    - Possibly starts worker tasks if needed.
#    - Returns a dict with at least "status", possibly "result" if completed immediately, or "message" if error.
#    - Does NOT include "task_id" since the manager will inject it before returning to the client.
#
# 3. get_metadata() -> dict:
#    Returns metadata about the service, such as:
#    - description: a short description of what this service does.
#    - required_fields: a list of input fields this service expects.
#    - worker_types: a list of worker_types this service may invoke.
#    - other optional info that helps clients or internal diagnostics.
#
#    This metadata can be displayed in `/available_services` or used for debugging.
#
# Design & Purposes:
# - By forcing all services to provide `validate_task`, `process`, and `get_metadata`,
#   we ensure consistency. For example, `/available_services` can call `get_metadata()` on each service
#   to produce a uniform description of capabilities.
#
# - The `validate_task()` method ensures that each service handles its input requirements
#   internally. If validation logic changes, only that service file changes.
#
# - The `process()` method standardizes how services start their analysis process. They can 
#   call worker subsystem endpoints if needed, or complete immediately if no workers required.
#   Returning a "status" field ensures a predictable structure for the manager and routes.
#
# - The `get_metadata()` method provides introspection. For maintainability, each service 
#   can detail what it does and what fields it requires, enabling the system (and possibly clients)
#   to understand the service capabilities without reading code.
#
# Maintainability:
# - If we add a new required method later (e.g. a method to compute partial results),
#   we can define it here and all services must implement it.
#
# Error Handling:
# - validate_task() returns {"error":"..."} if invalid input. The manager or routes handle turning this into a 400 response.
# - process() returns status="error" with a message if something goes wrong at start.
# - If process runs smoothly but workers fail later, manager updates task status to error at completion time.
#
# Testing:
# - Unit tests: mock or test a concrete service to ensure validate_task and process return expected structures.
# - Integration tests with workers: run actual services and confirm they start workers correctly.
#
###############################################################################

from abc import ABC, abstractmethod
from typing import Optional, Dict

class BaseService(ABC):
    """
    BaseService is an abstract class defining the interface all concrete services must implement.

    Required Abstract Methods:
    - validate_task(task_data: dict) -> Optional[dict]:
      Validate input data. Return None if valid, {"error":"..."} if invalid.

    - process(task_data: dict) -> dict:
      Perform initial steps for the analysis. Return a dict with at least "status".
      "status" can be "enqueued" (if workers started), "completed" (if done immediately),
      or "error" (if something failed at initiation).
      May also return "result" if completed or "message" if error.
      DOES NOT include "task_id" since manager adds that after calling process().

    - get_metadata() -> dict:
      Returns a dictionary with metadata about the service:
      e.g. {
        "description":"Analyze textual messages for phishing/spam",
        "required_fields":["message"],
        "worker_types":["text_worker"],
        "example_input":{"message":"Hello check this link"},
      }
      This helps endpoints like `/available_services` provide richer info.
    """

    @abstractmethod
    def validate_task(self, task_data: dict) -> Optional[dict]:
        """
        Validate the input task_data for required fields and correct formats.

        Args:
            task_data (dict): The input data from the user request.

        Returns:
            None if valid.
            {"error":"message"} if invalid input.

        Example:
          If analyzing a message, check "message" field is present and non-empty.
          If missing or empty, return {"error":"Missing 'message' field"}.
        """
        pass

    @abstractmethod
    def process(self, task_data: dict) -> dict:
        """
        Perform initial processing for the analysis request.

        Steps may include:
        - Internally call validate_task() or assume manager does so before calling process.
        - If invalid, return {"status":"error","message":"..."}.
        - Start workers if needed by calling worker subsystem endpoints (done in concrete service).
        - Return {"status":"enqueued"} if waiting for workers.
        - If it can complete instantly (no workers), return {"status":"completed","result":{...}}.
        - On errors, return {"status":"error","message":"..."}.

        Return:
            dict with keys:
             - "status": "enqueued"|"completed"|"error"
             - "result": { ... } optional if completed
             - "message": "..." optional if error

        The manager will later inject the "task_id" key into the returned dict 
        before sending to the client.
        """
        pass

    @abstractmethod
    def get_metadata(self) -> dict:
        """
        Return a dictionary describing this service's capabilities and requirements.

        Example:
        {
          "description": "Analyze textual messages for phishing/spam patterns.",
          "required_fields":["message"],
          "worker_types":["text_worker"],  # If it uses the text worker for analysis.
          "example_input":{"message":"Check out this scam link"},
        }

        This metadata helps endpoints like /available_services show a human-readable 
        description. It also helps maintainers and clients understand what each service does.

        Returns:
            dict with keys like:
              "description": str
              "required_fields": list of str
              "worker_types": list of str (optional, if it uses workers)
              "example_input": dict (optional)
              plus any other helpful metadata
        """
        pass
