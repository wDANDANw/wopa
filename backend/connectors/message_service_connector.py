# import logging
# import httpx
# from core.config_loader import get_env

# ###############################################################################
# # connectors/message_service_connector.py
# #
# # Purpose:
# # Provides a function analyze_message(content: str) that calls MESSAGE_SERVICE_URL 
# # to initiate a message analysis.
# #
# # Assumptions:
# # - MESSAGE_SERVICE_URL env var set, e.g., "http://message-service:8080"
# # - POST /analyze/message (or similar) returns a JSON { "task_id": "msg-task-123" }
# #
# # If actual external API differs, adjust accordingly.
# ###############################################################################

# logger = logging.getLogger(__name__)

# def analyze_message(content: str) -> str:
#     url = get_env("MESSAGE_SERVICE_URL")
#     # Suppose external service expects JSON: {"message": content}
#     payload = {"message": content}

#     try:
#         response = httpx.post(f"{url}/analyze/message", json=payload)
#         response.raise_for_status()
#         data = response.json()
#         task_id = data.get("task_id")
#         if not task_id:
#             logger.error("No task_id in message service response.")
#             raise Exception("Invalid response from message service")
#         return task_id
#     except Exception as e:
#         logger.error(f"Failed to analyze message: {e}")
#         raise

import logging
import httpx

###############################################################################
# connectors/message_service_connector.py
#
# Purpose:
# Provides a function analyze_message_final(content: str) that calls services:8001/analyze_message
# and returns the final JSON result directly.
#
# The services server returns:
# {
#   "status": "completed",
#   "result": { ... },
#   "task_id": "message_analysis-..."
# }
#
# We'll return this entire JSON as is.
###############################################################################

import requests

def analyze_message(content: str) -> dict:
    url = "http://services:8001"
    payload = {"message": content}
    response = requests.post(f"{url}/analyze_message", json=payload, timeout=60)
    response.raise_for_status()
    return response.json()
