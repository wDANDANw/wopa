###############################################################################
# gradio_dashboard.py
#
# Purpose:
# This file defines a Gradio-based admin UI for the Providers subsystem. Unlike a
# standalone dashboard that runs on a separate port, we design this code so it can 
# be integrated as a sub-application within the main FastAPI server. This allows the 
# Providers subsystem admin UI to be accessible via `/admin` on the same host/port 
# as other provider endpoints, simplifying deployment and testing.
#
# Key Responsibilities:
# 1. Present a dashboard that shows:
#    - Health status of the subsystem (LLM, Sandbox, Emulator) by calling the /health endpoint.
#    - A list of all available endpoints (from /admin/endpoints).
# 2. Provide a simple "Refresh" button to re-fetch data from the Providers subsystem.
#
# Integration with FastAPI:
# - Gradio (3.x and above) can produce an ASGI app that can be mounted on a FastAPI route.
# - We'll create a Gradio Blocks interface and then convert it into an ASGI app that
#   `provider_server.py` can mount at `/admin`. This ensures that when the user visits
#   `http://localhost:8003/admin` (assuming the main server is on 8003), they see this UI.
#
# Requirements:
# - Gradio installed.
# - The FastAPI main server running (provider_server.py).
# - Providers subsystem endpoints accessible (e.g., /health, /admin/endpoints) from inside 
#   the container or host environment where this code runs.
#
# Assumptions:
# - The Providers API is running at the same host and port as the main server, 
#   e.g., `http://localhost:8003`. If running inside Docker, ensure connectivity.
# - If running tests, make sure the integration test and actual running environment match.
#
# Maintainability:
# - If the Providers subsystem endpoints change location or require auth, update the 
#   request calls accordingly.
# - If we add more features (like logs, triggering tasks), we can add more Gradio components.
# - If layout changes or we need multiple pages, consider using Gradio Tabs or multiple Blocks.
#
# Design Notes:
# - The `get_health_info()` and `get_available_endpoints()` functions call Providers subsystem endpoints.
# - The `refresh_info()` function fetches both at once and returns them to be displayed in textboxes.
# - The UI consists of:
#   - A title and description.
#   - A "Refresh Info" button.
#   - Two textboxes: one for Health Information, one for Endpoint listing.
# - On startup, we load initial data for Health and Endpoints to show defaults.
#
# Future Enhancements:
# - Add more panels for showing emulator instances, sandbox logs, or LLM model info.
# - Add authentication if the admin UI should not be publicly accessible.
# - Add error handling UI if calls fail more gracefully.
###############################################################################

import requests
import gradio as gr
import os
import base64
import tempfile

# Configure the base URL of the Providers subsystem.
# We assume the main server runs on `http://localhost:8003` internally.
# Adjust if needed (e.g., use an environment variable).
PROVIDERS_BASE_URL = "http://localhost:8003"

def get_health_info():
    """
    Fetch health information from /health endpoint and format it nicely.
    
    Steps:
    1. GET /health
    2. If 200, parse JSON: 
       {
         "status":"ok","details":{"llm":"ok","sandbox":"ok","emulator":"ok"}
       }
    3. Extract status and details and build a user-friendly string.
    4. If non-200 or error, return an error message.
    """
    try:
        r = requests.get(f"{PROVIDERS_BASE_URL}/health", timeout=5)
        if r.status_code == 200:
            data = r.json()
            status = data.get("status", "unknown")
            details = data.get("details", {})
            detail_str = "\n".join([f"{k}: {v}" for k, v in details.items()])
            return f"Overall Status: {status}\n\nDetails:\n{detail_str}"
        else:
            return f"Health endpoint returned non-200 status: {r.status_code}"
    except Exception as e:
        return f"Error fetching health info: {e}"

def get_available_endpoints():
    """
    Fetch the list of all known endpoints from /admin/endpoints.
    
    Steps:
    1. GET /admin/endpoints
    2. If 200, parse JSON:
       {
         "endpoints":["/health/","/llm/chat_complete","/sandbox/run_file","/emulator/run_app","/admin/endpoints"]
       }
    3. Join them with newlines for display.
    4. If no endpoints or non-200, show an appropriate message.
    """
    try:
        r = requests.get(f"{PROVIDERS_BASE_URL}/admin/endpoints", timeout=5)
        if r.status_code == 200:
            data = r.json()
            eps = data.get("endpoints", [])
            if eps:
                return "Available Endpoints:\n" + "\n".join(eps)
            else:
                return "No endpoints returned by /admin/endpoints."
        else:
            return f"/admin/endpoints returned non-200 status: {r.status_code}"
    except Exception:
        return "Endpoints info not available. Perhaps /admin/endpoints not implemented or server unreachable."

def refresh_info():
    """
    Refresh data for both health and endpoints.
    Returns:
      (health_info_str, endpoints_info_str)
    """
    health = get_health_info()
    endpoints = get_available_endpoints()

    return health, endpoints

def upload_app_to_server(apk_file):
    """
    Upload the selected APK to /emulator/upload_app.
    Returns:
    - status and filename (and message) from server.
    """
    if apk_file is None:
        return "No APK selected.", "", ""
    url = f"{PROVIDERS_BASE_URL}/emulator/upload_app"
    with open(apk_file, "rb") as f:
        files = {"file": (os.path.basename(apk_file), f, "application/vnd.android.package-archive")}
        r = requests.post(url, files=files, timeout=60)
        if r.status_code != 200:
            return f"Error: {r.status_code} {r.text}", "", ""
        data = r.json()
        status = data.get("status","unknown")
        filename = data.get("filename","")
        message = data.get("message","")
        if not message and status == "ok":
            message = "Uploaded successfully."
        return f"Status: {status}", filename, message

def run_app_in_emulator(app_ref):
    """
    Calls /emulator/run_app with given app_ref (filename or full path).
    Returns status, events, task_id, screenshot image, and VNC info.
    """
    if not app_ref or not app_ref.strip():
        return "No app_ref provided.", "", "", None, ""
    run_app_url = f"{PROVIDERS_BASE_URL}/emulator/run_app"
    payload = {"app_ref": app_ref.strip()}
    try:
        r = requests.post(run_app_url, json=payload, timeout=60)
        if r.status_code != 200:
            return f"Error: {r.status_code} {r.text}", "", "", None, ""
        data = r.json()
        status = data.get("status","unknown")
        visuals = data.get("visuals",{})
        events = data.get("events",[])
        task_id = data.get("task_id","")
        screenshot_b64 = visuals.get("screenshot","")

        img_path = None
        if screenshot_b64:
            img_data = base64.b64decode(screenshot_b64)
            img_path = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
            with open(img_path,"wb") as imgf:
                imgf.write(img_data)

        events_str = "\n".join(events)
        vnc_info = "VNC: http://localhost:6080/?autoconnect=true"
        return f"Status: {status}", events_str, task_id, img_path, vnc_info
    except Exception as e:
        return f"Error calling run_app: {e}", "", "", None, ""

    
###############################################################################
# Build the Gradio Blocks UI
#
# Layout:
# - A title "Providers Admin Dashboard"
# - A description about what this UI shows.
# - A "Refresh Info" button to update the textboxes.
# - Two textboxes: one for Health Information, one for Endpoints.
#
# On start, we fetch initial data and populate the textboxes.
###############################################################################

with gr.Blocks() as admin_ui_blocks:
    gr.Markdown("# Providers Admin Dashboard")
    gr.Markdown("This UI shows system health/endpoints, allows APK upload, and runs an app on the emulator.\nUse 'Refresh Info' for health/endpoints updates.")

    # Section 1: Refresh Health/Endpoints
    refresh_button = gr.Button("Refresh Info")
    health_output = gr.Textbox(label="Health Information", interactive=False)
    endpoints_output = gr.Textbox(label="Endpoints", interactive=False)

    # Section 2: Upload an APK
    gr.Markdown("## Upload an APK")
    apk_upload = gr.File(label="Select APK File")
    upload_button = gr.Button("Upload APK")
    upload_status = gr.Textbox(label="Upload Status/Errors", interactive=False)
    uploaded_filename = gr.Textbox(label="Uploaded Filename", interactive=False)
    upload_message = gr.Textbox(label="Message", interactive=False)

    # Section 3: Run App
    gr.Markdown("## Run an App on Emulator (provide the filename from upload step)")
    app_ref_input = gr.Textbox(label="App Filename (from upload)", placeholder="e.g. myapp.apk")
    run_button = gr.Button("Run App")
    run_status = gr.Textbox(label="Run Status/Errors", interactive=False)
    run_events = gr.Textbox(label="Events", interactive=False)
    run_task_id = gr.Textbox(label="Task ID", interactive=False)
    run_screenshot = gr.Image(label="Screenshot")
    run_vnc_info = gr.Textbox(label="VNC Info", interactive=False)

    # Initial load
    refresh_button.click(fn=refresh_info, inputs=[], outputs=[health_output, endpoints_output])
    initial_health, initial_endpoints = refresh_info()
    health_output.value = initial_health
    endpoints_output.value = initial_endpoints

    # Upload and display results
    upload_button.click(fn=upload_app_to_server,
                        inputs=[apk_upload],
                        outputs=[upload_status, uploaded_filename, upload_message])

    # Run app after upload
    run_button.click(fn=run_app_in_emulator,
                     inputs=[app_ref_input],
                     outputs=[run_status, run_events, run_task_id, run_screenshot, run_vnc_info])


###############################################################################
# Exporting ASGI app
#
# After creating the admin_ui_blocks, we convert it into an ASGI-compatible app
# so that provider_server.py can mount it at /admin.
#
# `admin_ui_blocks.queue()` is often used to enable background tasks or concurrency,
# but if not needed, `admin_ui_blocks` alone might suffice. `queue()` returns a 
# Blocks instance with queue enabled, from which we can get the `.app` attribute.
#
# If you prefer no queue, just use `admin_ui_blocks.app` if supported by your gradio version.
#
# Let's assume `gradio>=3.9.0`, where `mount_gradio_app` is available in some versions:
# If not, we can do `admin_asgi = admin_ui_blocks.queue().app`
#
# We won't launch from here. provider_server.py will import this file and mount admin_asgi.
###############################################################################

admin_asgi = admin_ui_blocks.queue().app

# This file is not run standalone. The main server (provider_server.py) will:
# 1. Import `admin_asgi` from this file.
# 2. Mount it at path "/admin" using `app.mount("/admin", admin_asgi)`.
#
# So no __main__ block here.

###############################################################################
# Explanation:
#
# - We created a Gradio Blocks UI that shows health and endpoints info of Providers.
# - We handle refresh logic via a simple button.
# - The admin UI is exposed as a variable `admin_asgi` that provider_server.py can mount.
#
# Maintainability:
# - If /health or /admin/endpoints logic changes, update get_health_info or get_available_endpoints.
# - If we add more features (like scenario tests, direct calls to LLM or sandbox),
#   add more buttons or components.
# - If environment or base URL changes, adjust PROVIDERS_BASE_URL.
#
# Future Work:
# - Authentication: Add a login step before showing admin info.
# - More error handling: If endpoints fail, show a user-friendly message or retry logic.
###############################################################################
