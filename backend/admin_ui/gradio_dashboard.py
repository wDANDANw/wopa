import gradio as gr
import logging
from core.request_handler import RequestHandler

###############################################################################
# File: admin_ui/gradio_dashboard.py
#
# Purpose:
# This file defines the admin UI using Gradio. Instead of launching a separate
# server, it provides a function to create a Gradio Blocks application that can 
# be mounted as a sub-application in the main FastAPI server. This allows 
# administrators to access the admin UI at, for example, /admin on the same 
# backend URL.
#
# Design & Philosophy:
# - Previously, we had `launch_ui()` calling `demo.launch()` to run on port 7860.
#   Now we integrate the UI into the main FastAPI app:
#   - Provide create_admin_ui_app() that returns demo.app (ASGI app for Gradio).
#   - The backend_server.py can then `app.mount("/admin", admin_ui_app)` to 
#     serve this UI at /admin.
#
# Steps:
# 1) Provide a Textbox for admin to input `task_id`.
# 2) A "Load Task" button fetches and displays the task details:
#    - If the task is found, show type, status, result.
#    - If `type == "app"`, show a VNC link "/api/task/{task_id}/vnc".
#
# Maintainability:
# - If we add a task listing feature in the future, we can expand this UI.
# - The code is simple and easy to adapt if the request_handler or endpoints change.
#
###############################################################################

logger = logging.getLogger(__name__)


def load_task_data(task_id: str) -> str:
    """
    Given a task_id, fetch its data from request_handler and return a formatted string.

    If task_id is empty, prompt the user to enter a task_id.
    If the task is not found, return "Task not found".
    Otherwise, display:
    - Task ID
    - Type
    - Status
    - Result (if any)
    - For app tasks, show VNC link "/api/task/{task_id}/vnc".

    Returns:
        str: A human-readable multiline string with task info.
    """
    if not task_id:
        return "Please enter a task_id."

    rh = RequestHandler()
    data = rh.fetch_result(task_id)
    if data is None:
        return f"Task {task_id} not found."

    # Expected data format: {"status":..., "result":..., "type":..., "content":...}
    task_type = data.get("type", "unknown")
    status = data.get("status", "no-status")
    result = data.get("result", None)

    msg = f"Task ID: {task_id}\nType: {task_type}\nStatus: {status}\n"
    msg += f"Result: {result}\n" if result is not None else "Result: None\n"

    if task_type == "app":
        vnc_link = f"/api/task/{task_id}/vnc"
        msg += f"VNC Session (App Task): {vnc_link}\n"

    return msg


def create_admin_ui_app():
    """
    Creates and returns a Gradio Blocks application as a Starlette ASGI app.

    Instead of launching Gradio in standalone mode, we use the 'demo.app' attribute,
    which is a Starlette application that can be mounted into a FastAPI app.

    Returns:
        Starlette ASGI app (demo.app) representing the admin UI.
    """
    with gr.Blocks(title="WOPA Admin Dashboard") as demo:
        gr.Markdown("## WOPA Admin Dashboard\nEnter a Task ID to view its details and possibly a VNC link.")
        
        task_id_input = gr.Textbox(label="Task ID", placeholder="Enter task_id here...")
        load_button = gr.Button("Load Task")
        output_box = gr.Textbox(label="Task Details", interactive=False)

        load_button.click(fn=load_task_data, inputs=task_id_input, outputs=output_box)

    # Return the underlying Starlette ASGI app for integration with FastAPI
    return demo.app
