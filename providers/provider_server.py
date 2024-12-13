###############################################################################
# provider_server.py
#
# Purpose:
# This file configures and launches the main FastAPI application for the Providers
# subsystem. It imports and includes routers for LLM, sandbox, emulator, health checks,
# admin endpoints, and VNC. Additionally, it mounts a Gradio-based admin UI under
# a subpath, providing a web interface for internal visibility and debugging.
#
# Key Responsibilities:
# 1. Create a FastAPI instance with metadata (title, version, description).
# 2. Include routers from the `api/` directory for each functionality:
#    - LLM endpoints (/llm)
#    - Sandbox endpoints (/sandbox)
#    - Emulator endpoints (/emulator)
#    - Health checks (/health)
#    - Admin endpoints (/admin)
#    - VNC endpoints for emulator sessions (e.g., /{task_id}/vnc)
# 3. Mount the admin UI (a Gradio ASGI app) at a chosen subpath (e.g., /admin/ui).
# 4. Define startup and shutdown events if needed, for logging or resource initialization.
#
# Integration with Other Components:
# - `emulator_env.py`, `sandbox_env.py`, and `llm_client.py` are not directly imported here,
#   but are likely used by the route handlers in `api/` modules. The routes handle
#   incoming requests, instantiate these classes, and return responses.
# - `provisioner.py` is used by the environment classes when needed to provision resources,
#   not necessarily directly used by `provider_server.py`.
#
# Maintainability:
# - If you add a new feature (e.g., a new provider), create a new router in `api/`
#   and just include it here with `app.include_router(...)`.
# - If the admin UI changes location or name, adjust the mount point or the import.
# - If authentication or CORS is needed, integrate appropriate middleware here.
#
# Running the Server:
# - Typically run via: `uvicorn provider_server:app --host 0.0.0.0 --port 8003`
# - Once running, endpoints like `/health` or `/llm/chat_complete` become available.
# - The admin UI is accessible at `http://localhost:8003/admin/ui` (if mounted that way).
#
# Future Enhancements:
# - Add global error handlers to return consistent JSON for exceptions.
# - Add logging middleware for request/response logs.
# - Add versioning to the API routes if needed.
#
###############################################################################

import logging
from fastapi import FastAPI
from utils import config_loader

# Import routers from the api subdirectory
from api import (
    routes_llm,
    routes_sandbox,
    routes_emulator,
    routes_health,
    routes_admin,
    routes_vnc
)

# Import the admin UI app from gradio_dashboard
# Adjust path if `gradio_dashboard.py` moves.
from admin_ui.gradio_dashboard import admin_asgi

###############################################################################
# Logging Configuration
#
# We configure basic logging. For more advanced setups, consider a logging config file,
# a structured logger (like structlog), or centralized log management.
###############################################################################
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S"
)
logger = logging.getLogger("providers")

###############################################################################
# Load Configuration if needed
#
# If any server-level config needed, load from config.yaml. Currently may not be strictly required.
###############################################################################
config = config_loader.load_config("config.yaml")

###############################################################################
# Create the FastAPI app
#
# Set title, version, and description. These appear in the OpenAPI docs.
###############################################################################
def create_app() -> FastAPI:
    app = FastAPI(
        title="WOPA Providers Subsystem",
        description=(
            "This subsystem provides LLM interpretation, sandbox file analysis, and "
            "emulator-based app behavior testing for the WOPA environment. "
            "It also includes admin endpoints and a graphical dashboard (Gradio UI) for inspection."
        ),
        version="0.1.0"
    )

    # Include various routers. Each router handles a specific area of functionality.
    app.include_router(routes_health.router, prefix="/health", tags=["health"])
    app.include_router(routes_llm.router, prefix="/llm", tags=["llm"])
    app.include_router(routes_sandbox.router, prefix="/sandbox", tags=["sandbox"])
    app.include_router(routes_emulator.router, prefix="/emulator", tags=["emulator"])
    app.include_router(routes_admin.router, prefix="/admin", tags=["admin"])
    app.include_router(routes_vnc.router, prefix="", tags=["vnc"])

    # If we need CORS or other middleware, add here:
    # from fastapi.middleware.cors import CORSMiddleware
    # app.add_middleware(
    #     CORSMiddleware,
    #     allow_origins=["*"],
    #     allow_credentials=True,
    #     allow_methods=["*"],
    #     allow_headers=["*"],
    # )

    # Startup event: Log that subsystem is starting
    @app.on_event("startup")
    async def startup_event():
        logger.info("Providers subsystem starting up...")
        # Could initialize connections, load models, or provision base resources if needed.

    # Shutdown event: Log that subsystem is shutting down
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Providers subsystem shutting down...")
        # Could close connections or release resources.

    # Mount the Gradio admin UI at /admin/ui:
    # We already have /admin routes from routes_admin. The admin UI is a separate ASGI app.
    # If we mount at /admin directly, it might conflict with admin endpoints.
    # So we choose /admin/ui or /admin/dashboard:
    app.mount("/admin", admin_asgi)

    # Now at http://localhost:8003/admin/ui we have the Gradio dashboard.
    # Admin endpoints like /admin/endpoints remain accessible.

    return app

###############################################################################
# Create the main app instance
###############################################################################
app = create_app()

###############################################################################
# Notes:
#
# - If we add a new service type (e.g., a new provider), just add a new router
#   after writing its routes. For example, if we create `routes_newservice.py`,
#   we do `app.include_router(routes_newservice.router, prefix="/newservice", tags=["newservice"])`.
#
# - If we decide to serve docs behind auth, add middleware or conditionally disable 
#   openapi_url and docs_url in FastAPI constructor arguments.
#
# - If performance metrics needed, integrate Prometheus or StatsD middleware here.
#
# - The admin UI is a static mount of gradio_dashboard; if we later change 
#   its code to reflect dynamic status from LLm, sandbox, emulator, we can add 
#   API calls or websockets for live updates.
#
###############################################################################
