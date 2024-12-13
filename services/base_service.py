"""
base_service.py

**Purpose:**
Define the BaseService abstract class, specifying the interface and common behavior all services must implement.
This includes:
- Validation of input tasks.
- Processing workflow, calling workers in sequence.
- Worker registration/deregistration logic.
- Methods to call and validate worker outputs.
- Aggregation of final results.

Concrete services like LinkAnalyzerService or MessageAnalyzerService extend this class, implement `validate_task()` and `process()`, 
and configure workers in `__init__()`.

**Design:**
- BaseService is an ABC (abstract base class) from Python's `abc` module.
- It provides abstract methods `validate_task()` and `process()` that must be overridden.
- It provides default implementations of `register_worker()`, `deregister_worker()`, `_call_next_worker()`, `_validate_results()`, and `_aggregate_at_service_level()` that derived classes can use or override if needed.
- `workers` dictionary stores worker info (endpoints, schemas).

**Maintainability:**
- If worker logic changes (e.g., new schema validation), update `_validate_results()`.
- If result aggregation logic changes system-wide, could update `_aggregate_at_service_level()` here or let subclasses override.
- Clear docstrings and comments guide newcomers.

No direct I/O here; network calls to workers are usually done in `_call_next_worker()`, 
which will be patched or implemented in services (and tested with mocks).

"""

from abc import ABC, abstractmethod

class BaseService(ABC):
    def __init__(self):
        """
        Initialize a BaseService.
        Subclasses should set up `self.workers = {}` and then call `register_worker()` 
        for each worker needed.
        
        workers structure:
        {
          "worker_name": {
              "endpoint": "http://...",
              "input_schema": { ... },
              "output_schema": { ... }
          },
          ...
        }

        No direct code here in base, subclasses will handle.
        """
        self.workers = {}

    @abstractmethod
    def validate_task(self, task_data: dict):
        """
        Validate the incoming task_data. Return None if valid, or {"error":"..."} dict if invalid.
        Concrete services define their own validation logic (e.g. checking required fields).
        """
        pass

    @abstractmethod
    def process(self, task_data: dict) -> dict:
        """
        The main entry point for analysis. Given validated task_data, 
        call workers in sequence, validate results, and aggregate them.

        Concrete services implement the logic flow. 
        This method may:
          - Validate the task_data first (using validate_task()).
          - If invalid, return error directly.
          - Otherwise, call `_call_next_worker()` for each worker in order,
            `_validate_results()` each time, and finally `_aggregate_at_service_level()`.
        """
        pass

    def register_worker(self, name: str, endpoint: str, input_schema: dict, output_schema: dict):
        """
        Register a worker that this service will use.
        name: Unique worker name (e.g., "text_analysis")
        endpoint: The worker's endpoint URL.
        input_schema: Dict describing input keys and types expected by worker.
        output_schema: Dict describing output keys and their types.

        Example schema:
        input_schema = {"url":"string"}
        output_schema = {"confidence":"float","threat":"string"}

        This allows _validate_results() to confirm output correctness.
        """
        self.workers[name] = {
            "endpoint": endpoint,
            "input_schema": input_schema,
            "output_schema": output_schema
        }

    def deregister_worker(self, name: str):
        """
        Deregister a previously registered worker.
        If the worker is not present, no error is raised, just ignore.
        """
        if name in self.workers:
            del self.workers[name]

    def _call_next_worker(self, current_data: dict, worker_name: str) -> dict:
        """
        Call the specified worker with current_data as input.
        By default, this is not implemented fully here since we do not have actual network calls.
        Services or tests can mock/override this method.

        Expected behavior:
        - Validate `current_data` against `input_schema` of the worker if desired.
        - Send a request to the worker endpoint and get a response.
        - Return the response as a dict.

        If worker unavailable or endpoint fails, this might raise an exception or return None,
        triggering fallback scenarios in the calling logic.

        Maintainability:
        If we implement a real call, we can use `requests` or `httpx`.
        For now, NotImplementedError; subclasses or tests will patch this.
        """
        raise NotImplementedError("Subclasses or test mocks should implement this method.")

    def _validate_results(self, worker_name: str, result: dict) -> bool:
        """
        Check if `result` matches the output_schema defined for worker_name.
        By default, a simple schema check:
        - For each key in output_schema, ensure it's in result and type matches.

        output_schema might map keys to strings like "float","string","int" to keep it simple.

        Return True if passes, False if fails.
        
        If no worker with that name, return False.
        """
        worker_info = self.workers.get(worker_name)
        if not worker_info:
            return False
        schema = worker_info["output_schema"]
        for key, expected_type in schema.items():
            if key not in result:
                return False
            if expected_type == "float" and not isinstance(result[key], float):
                return False
            if expected_type == "string" and not isinstance(result[key], str):
                return False
            if expected_type == "int" and not isinstance(result[key], int):
                return False
        return True

    def _aggregate_at_service_level(self, results: list) -> dict:
        """
        Combine multiple worker outputs into a final result dictionary.
        
        This default implementation is simplistic: 
        It finds the max confidence and sets risk_level accordingly.
        If no results, return a default low-risk or completed status.

        Subclasses can override for custom logic.

        results is a list of dicts from each worker.
        
        Returns a dict like:
        {
          "status":"completed",
          "risk_level":"high"/"medium"/"low",
          "issues":[...]
        }

        If no results, maybe return something minimal or fallback scenario.

        Maintainability:
        If requirements for aggregation change, update logic or override in subclass.
        """
        if not results:
            return {"status":"completed","risk_level":"low","issues":[]}
        max_conf = 0.0
        final_threat = "none"
        for r in results:
            c = r.get("confidence",0.0)
            t = r.get("threat","none")
            if c > max_conf:
                max_conf = c
                final_threat = t
        risk_level = "high" if max_conf > 0.8 else ("medium" if max_conf > 0.5 else "low")
        issues = [] if final_threat == "none" else ["Detected:"+final_threat]
        return {"status":"completed","risk_level":risk_level,"issues":issues}

# Not last file yet. We will notify at the end of the final file.
