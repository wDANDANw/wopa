###############################################################################
# worker_server.py
#
# Purpose:
# This file sets up the main FastAPI application for the Workers subsystem of WOPA.
# It loads configuration, initializes workers and the WorkerManager, and includes
# routers from the `api/` directory that define endpoints for tasks and workers.
#
# Clarified Concepts:
# - worker_type: A known category of worker (e.g. "text", "link", "static_file"). 
#   Listed by /available_workers. These types are known at startup.
#
# - worker_id: A unique identifier generated at runtime when we enqueue or process 
#   a task for a given worker_type. The WorkerManager returns this `worker_id`.
#   This `worker_id` identifies a specific worker instance created for that request.
#   `worker_server.py` does not handle worker_id creation; it just sets up infrastructure.
#
# - task_id: A global identifier for a user (upstream) request. Given by upstream 
#   or generated if missing. Multiple workers can be associated with the same task_id.
#
# Endpoints (from included routers):
# - Tasks related (routes_tasks):
#   - GET /tasks: list all tasks and their workers
#   - POST /enqueue_task: enqueue a worker request (returns task_id, worker_id, status)
#   - POST /request_worker: immediately process a worker request (returns completed or error result)
#   - GET /get_workers_in_task: get details about all worker instances under a given task_id
#
# - Workers related (routes_workers):
#   - GET /available_workers: list known worker_types
#   - GET /get_worker_by_id: get metadata about a specific worker instance by worker_id
#
# No main() function defined, `uvicorn worker_server:app` is used to run the server.
#
# Maintainability:
# - To add a new worker type, implement it in `worker_definitions/` and add an instance to `worker_map` in create_app().
# - To add a new endpoint, create a new router in `api/` and include it here.
# - If logic or naming conventions change, update docstrings and comments accordingly.
#
# Testing:
# - Unit tests can mock worker_manager and workers.
# - Integration tests use actual providers if configured.
#
###############################################################################

import logging
from fastapi import FastAPI
from utils.config_loader import load_config

# Import worker classes (these represent worker_types)
from worker_definitions.text_worker import TextWorker
from worker_definitions.link_worker import LinkWorker
# from worker_definitions.static_file_worker import StaticFileWorker
# from worker_definitions.dynamic_file_worker import DynamicFileWorker
# from worker_definitions.syslog_worker import SyslogWorker
from worker_definitions.app_worker_openai import AppWorker

from core.worker_manager import WorkerManager

# Import routers from api/ directory
#   routes_tasks: for task-related endpoints
#   routes_workers: for worker-related endpoints
from api import routes_tasks, routes_workers

###############################################################################
# Logging Configuration
###############################################################################
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S"
)
logger = logging.getLogger("workers")

###############################################################################
# create_app function
#
# Steps:
# 1. Load config (includes mode: local or online, providers_server_url, etc.)
# 2. Initialize worker instances. Each worker_type gets a WorkerClass instance.
# 3. Create a worker_map {worker_type: worker_instance}
# 4. Create WorkerManager with config and worker_map.
# 5. Include routers for tasks and workers.
###############################################################################
def create_app() -> FastAPI:
    config = load_config()

    # Initialize workers (one instance per worker_type)
    # These instances represent the baseline configuration for that worker type.
    # If desired, we could store classes instead of instances, but currently we 
    # create one instance. Each call to process/enqueue doesn't necessarily need a 
    # new instance if workers are stateless, but if stateless, reusing is fine. 
    # If stateful per request is needed, we can change approach in WorkerManager.
    #
    # Considering previous clarifications, it might be better if worker_map stores
    # WorkerClasses, and WorkerManager instantiates a new worker each time. 
    # However, previous code used worker instances directly. Let's do what's simplest:
    # We'll keep them as instances now. If WorkerManager needs a fresh worker each time,
    # we can store classes. We'll store classes here for clarity:
    #
    # Actually, user clarified we must re-instantiate worker each time in process_task?
    # Let's store classes instead of instances:
    # worker_map = { "text": TextWorker, "link":LinkWorker, ...}
    # Then WorkerManager does worker = WorkerClass(config)
    #
    # Let's do that now to align with final logic.

    worker_map = {
        "text": TextWorker,
        "link": LinkWorker,
        # "static_file": StaticFileWorker,
        # "dynamic_file": DynamicFileWorker,
        # "syslog": SyslogWorker,
        "app": AppWorker
    }

    manager = WorkerManager(config=config, worker_map=worker_map)

    # Create the FastAPI app
    app = FastAPI(
        title="WOPA Workers Subsystem",
        description=(
            "The Workers subsystem processes various tasks such as text analysis, link verification, "
            "file analysis (static & dynamic), syslog analysis, and app behavior via emulator. "
            "It integrates multiple workers and a WorkerManager to handle enqueued tasks and "
            "immediate task processing. Worker_id is generated per request, task_id from upstream."
        ),
        version="1.0.0"
    )

    # Store references in app.state for routers to use if needed
    app.state.manager = manager
    app.state.worker_map = worker_map
    app.state.config = config

    # Include the routers
    # Routes:
    # /tasks, /enqueue_task, /request_worker, /get_workers_in_task from routes_tasks
    # /available_workers, /get_worker_by_id from routes_workers
    app.include_router(routes_tasks.router, tags=["Tasks"])
    app.include_router(routes_workers.router, tags=["Workers"])

    @app.on_event("startup")
    async def startup_event():
        logger.info("Workers subsystem starting up...")

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Workers subsystem shutting down...")

    from fastapi_utils.tasks import repeat_every

    @app.on_event("startup")
    @repeat_every(seconds=60)  # every 60 seconds
    async def auto_process_enqueued_tasks():
        app.state.manager.process_enqueued_tasks()

    return app

###############################################################################
# Create the app instance
#
# uvicorn worker_server:app --host 0.0.0.0 --port 8002
# No main() function needed as requested.
###############################################################################
app = create_app()

###############################################################################
# Notes:
#
# - By storing worker_map as {worker_type: WorkerClass}, WorkerManager can instantiate
#   a fresh worker each time it's needed (in process_task), ensuring isolation per request.
#
# - If we need to adjust naming or add more worker_types, update worker_map and 
#   worker_definitions accordingly.
#
# - The endpoints and logic have been aligned so that:
#   - /available_workers returns worker_types (keys of worker_map).
#   - /enqueue_task and /request_worker expect worker_type, not worker_id.
#   - Manager generates worker_id at runtime.
#   - /get_worker_by_id searches tasks to find worker_id and then deduce worker_type.
#
# - If advanced features like automatic processing of enqueued tasks, or persistent storage 
#   are required, we would update WorkerManager and possibly add new endpoints.
#
###############################################################################
