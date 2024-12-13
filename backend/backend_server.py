import os
import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    app = FastAPI(
        title="WOPA Backend",
        description="Backend server for WOPA: Intelligent Chat Safeguarder",
        version="0.1.0"
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],  # The frontend's origin
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include auth_router with no prefix, so /login is at root.
    from api.routes_auth import auth_router
    app.include_router(auth_router)  # => /login at root

    from api.routes_history import history_router
    app.include_router(history_router)

    from api import api_router
    app.include_router(api_router) # we can still do prefix="/api" here if we want all others at /api
    # Actually, we must define the prefix for api_router now:
    # If we do `app.include_router(api_router, prefix="/api")` then all api routes are at /api/*, 
    # but /login stays at root:
    app.include_router(api_router, prefix="/api")

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)}
        )

    from admin_ui.gradio_dashboard import create_admin_ui_app
    admin_ui_app = create_admin_ui_app()
    app.mount("/admin", admin_ui_app)

    return app

if __name__ == "__main__":
    uvicorn.run("backend_server:create_app", host="0.0.0.0", port=8000, factory=True)
