###############################################################################
# base_worker.py
#
# Purpose:
# This file defines the BaseWorker abstract class, serving as a blueprint for
# all worker classes (e.g., TextWorker, LinkWorker, StaticFileWorker, etc.) 
# in the `worker_definitions/` directory.
#
# The BaseWorker specifies two essential methods that all subclasses must implement:
# - validate_task(task_data: dict) -> dict or None:
#   Checks if `task_data` contains required fields and is logically consistent.
#   On success, return None or empty dict indicating no errors.
#   On failure, return {"error":"explanation"}.
#
# - process(task_data: dict) -> dict:
#   Executes the main logic for this worker type. Uses `config` and possibly providers.
#   Returns:
#     {"status":"completed","result":{...}} on success
#   or {"status":"error","message":"..."} on failure.
#
# Additionally, a `get_metadata()` method is defined as optional. It allows 
# subclasses to provide descriptive metadata about the worker (required fields, 
# description, capabilities, etc.). If not implemented, callers may fallback to 
# defaults. `get_metadata()` returns a dict describing this worker’s nature.
#
# Key Concepts:
# - worker_type: Identified at a higher level by `worker_server.py` and `WorkerManager`. 
#   Each subclass typically corresponds to one worker_type. The base class does not 
#   strictly enforce a `worker_type` attribute, but subclasses can define it as a class variable.
#
# - worker_id: Generated at runtime by WorkerManager, not handled here. 
#   BaseWorker does not manage worker_id or task_id. It only sees `task_data`.
#
# - mode (local/online) and providers_server_url: Provided via `config` at initialization.
#   Workers can use these config values to decide how to process data (e.g., calling local providers or external APIs).
#
# Maintainability:
# - If a new method is required of all workers, add it here. 
# - If we add a standard for metadata keys (like `required_fields`, `mode`, `capabilities`),
#   define them here so all workers can follow the pattern.
# - Keep docstrings updated as the system evolves.
#
# Testing:
# - Since BaseWorker is abstract, test it indirectly through subclasses.
# - Ensure each subclass’s validate_task and process methods handle errors correctly.
#
###############################################################################

from abc import ABC, abstractmethod

class BaseWorker(ABC):
    """
    BaseWorker:
    An abstract base class for all workers in the Workers subsystem.

    Each subclass represents a distinct worker_type (e.g., 'text', 'link', 'file'), 
    though the base class does not store worker_type directly. The relationship between 
    worker_type and subclass is conventional: one subclass per worker_type.

    Fields:
    - config: a dict of runtime configuration (mode, providers_server_url, etc.)
              passed at initialization from WorkerManager.

    Methods (abstract):
    - validate_task(task_data: dict) -> dict or None:
      Check if `task_data` is valid for this worker. If invalid, return {"error":"..."}.
      If valid, return None or empty dict.

    - process(task_data: dict) -> dict:
      Perform the core logic (LLM calls, sandbox checks, etc.) and return:
      {"status":"completed","result":{...}} or {"status":"error","message":"..."}.

    Methods (optional):
    - get_metadata() -> dict:
      Return a dictionary describing the worker.
      Recommended keys:
        "description": A short string explaining what this worker does.
        "required_fields": A list of strings naming fields needed in task_data.
        "mode": "local" or "online", based on config or worker design.
        "capabilities": A list of features this worker provides.
      If not implemented, the caller may fallback to defaults.
    """

    def __init__(self, config: dict):
        """
        __init__(config)
        Initialize the base worker with a given config dictionary.

        config keys may include:
          - "mode": "local" or "online"
          - "providers_server_url": URL for local providers if mode=local
          - other keys as added in future

        Subclasses can store config or parse keys for convenience.
        """
        self.config = config

    @abstractmethod
    def validate_task(self, task_data: dict):
        """
        validate_task(task_data)
        Check if `task_data` has required fields and logical consistency.
        Return None or empty dict if okay. 
        Return {"error":"..."} if something is missing or invalid.

        Example:
        For a text worker:
          - Check if "content" field is present and non-empty.
          If missing: return {"error":"content field is required"}

        For a link worker:
          - Check if "url" field is present and a valid URL.
          If invalid: return {"error":"invalid or missing url"}

        If no issues, just return None.
        """
        pass

    @abstractmethod
    def process(self, task_data: dict) -> dict:
        """
        process(task_data)
        Execute the main logic of this worker based on the data in task_data.

        Return a dict:
        - On success:
          {"status":"completed","result":{...}} 
          result keys vary by worker type.
        - On error:
          {"status":"error","message":"..."} explaining the error.

        Example:
        For a text worker in local mode:
          - Call local LLM provider at self.config["providers_server_url"] to analyze text.
          If success: return {"status":"completed","result":{"classification":"scam","confidence":0.95}}
          If failure: return {"status":"error","message":"LLM provider unreachable"}

        For a link worker in online mode:
          - Call external APIs for reputation checks.
          If API unreachable: return {"status":"error","message":"API call failed"}
        """
        pass

    def get_metadata(self) -> dict:
        """
        get_metadata()
        Optional method:
        Return a dictionary with metadata about this worker.

        Suggested keys:
          "description": Short explanation of worker's purpose.
          "required_fields": Which fields does this worker need in task_data?
          "mode": The mode this worker operates in, typically from config["mode"], "local" or "online".
          "capabilities": A list of strings describing what this worker can do (e.g., "text analysis", "sandbox analysis").

        If not overridden, this default returns a generic placeholder. Callers can fallback to other means.
        """
        # Default implementation (subclasses are encouraged to override):
        return {
            "description": "No metadata method implemented for this worker.",
            "required_fields": [],
            "mode": self.config.get("mode","local"),
            "capabilities": []
        }

###############################################################################
# Maintainability Notes:
#
# - If we add new standard fields (like a version number) to metadata, 
#   add them in get_metadata() here and ensure subclasses override or supplement.
#
# - If workers need common helper methods (like a method to call providers with 
#   standardized error handling), we could add them here, making them available 
#   to all workers.
#
# - If we introduce stateful logic (like caching results per worker instance), 
#   note that currently each request leads WorkerManager to create a new worker 
#   instance. Make sure not to rely on persistent state within a single worker instance.
#
###############################################################################
