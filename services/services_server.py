###############################################################################
# services_server.py
#
# Purpose:
# This file sets up the main FastAPI application for the Services subsystem of WOPA.
# The Services subsystem provides endpoints to analyze different types of content
# (message, link, file static/dynamic, and app) using underlying workers and aggregator services.
#
# Architecture:
# - Clients call endpoints like /analyze_message with input data.
# - The chosen service (e.g. message_service) validates input and may call 
#   workers (through WORKER_SERVER_URL) and aggregator LLM (PROVIDER_SERVER_URL).
# - A task_id is assigned internally by the manager, ensuring we can track the analysis request.
# - The manager or service sets initial "enqueued" or "completed" status.
# - Clients can query /get_task_status with the returned task_id to monitor progress.
#
# Configuration:
# - Loaded via load_config() from "config/services_config.yaml" and environment variables.
# - WORKER_SERVER_URL and PROVIDER_SERVER_URL may be overridden by env vars.
#
# Service Integration:
# - Each service class (like MessageService) extends BaseService.
# - This file's role is just to create the FastAPI app, load config, instantiate services, 
#   create ServiceManager, and mount routers for endpoints.
#
# Logging & Maintainability:
# - Logging at INFO level for startup/shutdown, configuration loading, and service map printing.
# - If something fails at request time, routes and services have their own logs.
# - Adding a new service means creating it in service_definitions/ and adding it to service_map here.
#
# Testing:
# - Unit tests: mock manager and services.
# - Integration tests: run with real worker subsystem and aggregator.
#
###############################################################################

import os
import logging
from fastapi import FastAPI

from utils.config_loader import load_config

# Import service classes
from service_definitions.base_service import BaseService
from service_definitions.message_service import MessageService
# In a final solution, we would also import LinkService, FileStaticService, etc.
# but user scenario focusing on message_service now.
from service_definitions.link_service import LinkService
# from service_definitions.file_static_service import FileStaticService
# from service_definitions.file_dynamic_service import FileDynamicService
from service_definitions.app_service import AppService

from service_manager import ServiceManager

# Import routers
from api import routes_services, routes_tasks

###############################################################################
# Logging Configuration
#
# Set a basic logging configuration. In production, consider using structured logs.
###############################################################################
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S"
)
logger = logging.getLogger("services")

def create_app() -> FastAPI:
    """
    create_app():
    Initializes and returns the FastAPI application for the Services subsystem.

    Steps:
    1. Load configuration using load_config().
    2. Override WORKER_SERVER_URL and PROVIDER_SERVER_URL if env vars are set.
    3. Instantiate services:
       - Currently only message_service for demonstration.
       - In a full solution, link_service, file_static_service, file_dynamic_service, and app_service are also instantiated.
    4. Build a service_map: { "service_name": service_instance }.
    5. Create a ServiceManager to orchestrate tasks and integrate with services.
    6. Create a FastAPI app, store manager, config, and service_map in app.state.
    7. Include routers for services and tasks endpoints.
    8. Add startup/shutdown events for logging.
    9. Return the app instance.

    Returns:
        FastAPI app ready for uvicorn to run.
    """
    logger.info("create_app: Loading configuration...")
    config = load_config()

    # Check environment overrides:
    worker_server_url = os.environ.get("WORKER_SERVER_URL", config.get("WORKER_SERVER_URL","http://workers:8001"))
    provider_server_url = os.environ.get("PROVIDER_SERVER_URL", config.get("PROVIDER_SERVER_URL","http://providers:8003"))
    config["WORKER_SERVER_URL"] = worker_server_url
    config["PROVIDER_SERVER_URL"] = provider_server_url

    logger.debug("create_app: Final WORKER_SERVER_URL=%s", worker_server_url)
    logger.debug("create_app: Final PROVIDER_SERVER_URL=%s", provider_server_url)

    # Instantiate services
    # Just message_service for now as per current focus:
    message_service = MessageService(config)
    link_service = LinkService(config)
    # file_static_service = FileStaticService(config)
    # file_dynamic_service = FileDynamicService(config)
    app_service = AppService(config)

    # Build service_map
    service_map = {
        "message_analysis": message_service,
        "link_analysis": link_service,
        # "file_static_analysis": file_static_service,
        # "file_dynamic_analysis": file_dynamic_service,
        "app_analysis": app_service
    }

    logger.debug("create_app: service_map keys=%s", list(service_map.keys()))

    # Create ServiceManager
    manager = ServiceManager(config=config, service_map=service_map)

    # Create FastAPI app
    app = FastAPI(
        title="WOPA Services Subsystem",
        description=(
            "The Services subsystem initiates analyses of messages, links, files, and apps, "
            "coordinating with worker and aggregator subsystems. It returns task_ids and "
            "manages statuses until results are finalized."
        ),
        version="1.0.0"
    )

    # Store references in app.state
    app.state.manager = manager
    app.state.config = config
    app.state.service_map = service_map

    # Include routers
    logger.debug("create_app: Including routers for services and tasks.")
    app.include_router(routes_services.router, tags=["Services"])
    app.include_router(routes_tasks.router, tags=["Tasks"])

    @app.on_event("startup")
    async def startup_event():
        logger.info("Services subsystem starting up...")
        logger.info("Configuration loaded: %s", config)
        logger.info("Service map: %s", ", ".join(service_map.keys()))

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Services subsystem shutting down...")

    return app

# Create the app instance
app = create_app()

###############################################################################
# Notes:
#
# If we continue to get "Unknown error" from curl:
# - Check message_service logging for aggregator or worker call failures.
# - Check if aggregator and worker endpoints are actually running.
#
# The "Unknown error" means service.process() returned {"status":"error","message":"..."} 
# without known validation keywords. Check aggregator/worker availability.
#
# More debugging:
# - Set logging to DEBUG (done with `logger.debug()` calls)
# - Inspect logs for steps message_service took. 
#
# If aggregator or worker not up:
# - message_service logs network error as "Net err calling text worker" or aggregator.
#
# If that happens, handle_manager_response sees "status":"error" and "message":"Net err..." 
# If "net err" doesn't contain "invalid","missing", the endpoint returns 500 with detail "Net err..."
#
###############################################################################
