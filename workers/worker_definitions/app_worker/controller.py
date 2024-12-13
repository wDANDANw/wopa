import os
import time
import base64
import requests
import re
import logging
from PIL import Image

logger = logging.getLogger(__name__)

def _action_error(message):
    # Simple helper if needed
    return {"status": "error", "message": message}

def _get_screenshot_for_task(base_url, task_id):
    try:
        resp = requests.get(f"{base_url}/emulator/screenshot", params={"task_id": task_id}, timeout=30)
        if resp.status_code != 200:
            return {"status":"error","message":f"screenshot {resp.status_code}"}
        data = resp.json()
        if data.get("status")!="ok":
            return {"status":"error","message":"screenshot not ok"}
        b64_str = data.get("screenshot","")
        if not b64_str:
            return {"status":"error","message":"No screenshot data"}
        screenshot_path = "./app_worker_screenshot.jpg"
        with open(screenshot_path,"wb") as f:
            f.write(base64.b64decode(b64_str))
        return {"status":"completed","screenshot_path":screenshot_path}
    except requests.RequestException as e:
        return {"status":"error","message":f"Net error screenshot: {str(e)}"}

def _perform_action_once(base_url, task_id, action_str):
    action_str = action_str.strip()
    action_str_lower = action_str.lower()
    params = {"task_id": task_id}

    try:
        if action_str_lower.startswith("tap("):
            coords = action_str.split("(")[-1].split(")")[0].split(",")
            if len(coords) != 2:
                return _action_error("Tap parse fail")
            x, y = coords
            logger.info(f"Performing tap action: {x},{y}")
            resp = requests.post(f"{base_url}/emulator/tap",
                                 json={"x": int(x.strip()), "y": int(y.strip())},
                                 params=params, timeout=30)

        elif action_str_lower.startswith("swipe("):
            # format: Swipe(x1,y1),(x2,y2)
            m = re.match(r"Swipe\s*\((\d+),(\d+)\)\s*,\s*\((\d+),(\d+)\)", action_str, re.IGNORECASE)
            if not m:
                return _action_error("Swipe parse fail")
            x1, y1, x2, y2 = m.groups()
            logger.info(f"Performing swipe action: {x1},{y1} -> {x2},{y2}")
            resp = requests.post(f"{base_url}/emulator/swipe",
                                 json={"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)},
                                 params=params, timeout=30)

        elif action_str_lower == "back":
            logger.info("Performing back action")
            resp = requests.post(f"{base_url}/emulator/back", params=params, timeout=30)

        elif action_str_lower == "home":
            logger.info("Performing home action")
            resp = requests.post(f"{base_url}/emulator/home", params=params, timeout=30)

        elif action_str_lower.startswith("type("):
            # Assuming an endpoint for typing text:
            # Action format: Type(text)
            text = action_str.split("(")[-1].split(")")[0]
            logger.info(f"Performing type action: {text}")
            resp = requests.post(f"{base_url}/emulator/type",
                                 json={"text": text},
                                 params=params, timeout=30)

        elif action_str_lower == "none":
            return {
                "check_id":"action_none",
                "analysis_agent":"emulator_action",
                "weight":0.0,
                "risk_level":"low",
                "confidence":0.8,
                "explanation":"No action chosen - success.",
                "status":"completed"
            }

        else:
            return _action_error("Unknown action")

        if resp.status_code != 200:
            return _action_error(f"action endpoint {resp.status_code}")
        data = resp.json()
        if data.get("status") == "ok":
            return {
                "check_id":"action_"+action_str_lower,
                "analysis_agent":"emulator_action",
                "weight":0.0,
                "risk_level":"low",
                "confidence":0.8,
                "explanation":f"Action {action_str} - success.",
                "status":"completed"
            }
        else:
            return _action_error("action not ok")

    except requests.RequestException as e:
        return _action_error(f"Network error action: {str(e)}")

def _perform_action_with_retry(base_url, task_id, action):
    # We'll try up to 2 times
    for i in range(2):
        res = _perform_action_once(base_url, task_id, action)
        if res["status"] == "completed":
            return res
        if i < 1:
            time.sleep(5)
    return res


# --------------------
# Rewritten functions
# --------------------

def get_screenshot(providers_url, task_id):
    # Uses _get_screenshot_for_task instead of adb commands
    result = _get_screenshot_for_task(providers_url, task_id)
    if result.get("status") == "completed":
        # The original code saved the final screenshot as ./screenshot/screenshot.jpg
        # Our code saved it as ./app_worker_screenshot.jpg
        # Let's ensure directories and rename to maintain original structure
        os.makedirs("./screenshot", exist_ok=True)
        src_path = result["screenshot_path"]
        dest_path = "./screenshot/screenshot.jpg"
        if os.path.exists(dest_path):
            os.remove(dest_path)
        os.rename(src_path, dest_path)
    else:
        logger.error("Failed to get screenshot: " + result.get("message", "Unknown error"))


def tap(providers_url, task_id, x, y):
    # Uses tap action
    action_str = f"Tap({x},{y})"
    result = _perform_action_with_retry(providers_url, task_id, action_str)
    if result.get("status") != "completed":
        logger.error("Tap action failed: " + result.get("message", ""))


def type(providers_url, task_id, text):
    # We'll assume we have a type endpoint:
    # Format the action as Type(text)
    # If needed, you can break it down by characters as original code, but here we do it in one go.
    action_str = f"Type({text})"
    result = _perform_action_with_retry(providers_url, task_id, action_str)
    if result.get("status") != "completed":
        logger.error("Type action failed: " + result.get("message", ""))


def slide(providers_url, task_id, x1, y1, x2, y2):
    # Uses swipe action
    action_str = f"Swipe({x1},{y1}),({x2},{y2})"
    result = _perform_action_with_retry(providers_url, task_id, action_str)
    if result.get("status") != "completed":
        logger.error("Slide action failed: " + result.get("message", ""))


def back(providers_url, task_id):
    # Uses back action
    action_str = "Back"
    result = _perform_action_with_retry(providers_url, task_id, action_str)
    if result.get("status") != "completed":
        logger.error("Back action failed: " + result.get("message", ""))


def home(providers_url, task_id):
    # Uses home action
    action_str = "Home"
    result = _perform_action_with_retry(providers_url, task_id, action_str)
    if result.get("status") != "completed":
        logger.error("Home action failed: " + result.get("message", ""))
