from fastapi import APIRouter
from .routes_message import message_router
from .routes_link import link_router
from .routes_file import file_router
from .routes_app import app_router
from .routes_task import task_router
from .routes_vnc import vnc_router
from .routes_health import health_router
from .routes_auth import auth_router
from .routes_history import history_router

api_router = APIRouter()

# The user wants /login without prefix. We have two main routers: api_router and directly attach auth_router to app.
# Let's attach auth_router to api_router with no prefix for now. 
# Actually, since api_router may have a prefix in backend_server, we must handle carefully.

# If in backend_server.py we do `app.include_router(api_router)` with no prefix, that means /login is available at /login if we do:
api_router.include_router(auth_router, tags=["login"])  # no prefix, so /login at /login
api_router.include_router(history_router, tags=["history"])
# If we do `app.include_router(api_router, prefix="/api")` in backend_server, this would put login at /api/login. 
# We must then NOT prefix api_router in backend_server for login to be at root.
# Alternatively, mount auth_router separately in backend_server.py.

# Let's mount auth_router separately in backend_server.py to ensure /login at root.

api_router.include_router(message_router, prefix="/api/analyze", tags=["analyze-message"])
api_router.include_router(link_router, prefix="/api/analyze", tags=["analyze-link"])
api_router.include_router(file_router, prefix="/api/analyze", tags=["analyze-file"])
api_router.include_router(app_router, prefix="/api/analyze", tags=["analyze-app"])
api_router.include_router(task_router, prefix="/api/task", tags=["task"])
api_router.include_router(vnc_router, prefix="/api/task", tags=["vnc"])
api_router.include_router(health_router, prefix="/api", tags=["health"])
