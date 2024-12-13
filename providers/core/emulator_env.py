import os
import json
import uuid
import random
import subprocess
import time
import base64
from typing import Dict, Any, Optional

import logging
logger = logging.getLogger(__name__)

from utils import config_loader
from core import provisioner

class EmulatorConnectionError(Exception):
    pass

class EmulatorInstallError(Exception):
    pass

class EmulatorRunError(Exception):
    pass

class EmulatorEnv:
    def __init__(self):
        """
        Initialize EmulatorEnv by loading configuration and preparing for use.
        We do not provision immediately here; provisioning happens in init_device() if needed.
        """
        self.config = config_loader.load_config("config.yaml")
        emulator_config = self.config.get("emulator", {})
        self.timeout = emulator_config.get("timeout_seconds", 60)
        self.max_retries = emulator_config.get("max_retries", 2)
        self.vnc_url_template = emulator_config.get("vnc_url_template", "vnc://{host}:{port}")
        self.default_vnc_port = emulator_config.get("default_vnc_port", 5900)

        self.endpoints = []
        self.task_map: Dict[str, Dict[str,Any]] = {}
        self.app_package_cache: Dict[str, str] = {}  # Maps app_ref to pkg_name

    def _run_adb_command(self, cmd_list, timeout=None, check=True, retries=3, delay=5):
        """
        Run an adb command with optional retries.
        Logs output and errors.
        """
        for attempt in range(retries):
            logger.debug(f"Running ADB command (attempt {attempt+1}/{retries}): {' '.join(cmd_list)}")
            try:
                result = subprocess.run(cmd_list, capture_output=True, text=True, timeout=timeout or self.timeout, check=check)
                logger.debug(f"ADB command output: {result.stdout.strip()}")
                return result.stdout.strip()
            except subprocess.CalledProcessError as e:
                logger.warning(f"ADB command failed (attempt {attempt+1}): {e.stderr}")
                if attempt == retries - 1 and check:
                    raise
                time.sleep(delay)
            except subprocess.TimeoutExpired as e:
                logger.error(f"ADB command timed out (attempt {attempt+1}): {e}")
                if attempt == retries - 1:
                    raise EmulatorConnectionError(f"ADB command timed out: {cmd_list}")
                time.sleep(delay)
        raise EmulatorConnectionError("ADB command failed after all retries")

    def _reload_endpoints(self):
        """
        Reload endpoints from instances.json after provisioning.
        """
        instances_path = "instances.json"
        if os.path.exists(instances_path):
            with open(instances_path, "r") as f:
                instances_data = json.load(f)
                self.endpoints = instances_data.get("emulator", [])
        if not self.endpoints:
            raise ValueError("No emulator endpoints available after provisioning.")

    def _wait_for_device(self, host_port: str):
        """
        Wait until the device is fully booted and ready.
        """
        logger.info(f"Waiting for device {host_port} to be ready...")
        wait_cmd = ["adb", "-s", host_port, "wait-for-device"]
        self._run_adb_command(wait_cmd, check=True, retries=5, delay=10)

        # Check sys.boot_completed
        for _ in range(10):
            prop_cmd = ["adb", "-s", host_port, "shell", "getprop", "sys.boot_completed"]
            res = self._run_adb_command(prop_cmd, check=False, retries=3, delay=5)
            if res.strip() == "1":
                logger.info("Device boot completed.")
                return
            logger.info("Device not fully booted yet, retrying...")
            time.sleep(5)
        raise EmulatorConnectionError("Device not booted after waiting.")

    def _get_installed_packages(self, host_port: str) -> list:
        cmd = ["adb", "-s", host_port, "shell", "pm", "list", "packages", "-f"]
        output = self._run_adb_command(cmd, check=True)
        return output.splitlines()

    def _detect_new_package(self, before_list: list, after_list: list) -> str:
        """
        Given the packages before and after installation,
        detect which package line is newly added and extract the package name.

        Strategy:
        - `pm list packages -f` lines often look like:
        package:/data/app/~~xyzID/.../base.apk=com.example.myapp
        - Some lines may have complex paths or unusual prefixes, but `base.apk=` 
        reliably marks where the package name begins.
        - We'll find the substring 'base.apk=' and take everything after it as the package name.
        """
        before_set = set(before_list)
        after_set = set(after_list)
        new_lines = after_set - before_set
        if not new_lines:
            logger.error("No new package found after installation.")
            raise ValueError("Failed to detect newly installed package. No new packages found.")

        # We assume one new package line
        new_line = new_lines.pop().strip()
        logger.debug(f"New package line detected: {new_line}")

        # Locate 'base.apk=' in the line
        marker = 'base.apk='
        idx = new_line.find(marker)
        if idx == -1:
            logger.error(f"Cannot find 'base.apk=' in package line: {new_line}")
            raise ValueError("Cannot parse package name, 'base.apk=' not found.")

        # Extract the package name after 'base.apk='
        pkg_name = new_line[idx + len(marker):].strip()
        if not pkg_name:
            logger.error(f"Empty package name after parsing line: {new_line}")
            raise ValueError("Package name is empty after parsing.")

        logger.info(f"Detected package name: {pkg_name}")
        return pkg_name

    def _attempt_launch_app(self, host_port: str, pkg_name: str):
        """
        Attempt to launch app using monkey. If fails, try am start.
        """
        monkey_cmd = ["adb", "-s", host_port, "shell", "monkey", "-v", "-p", pkg_name, "1"]
        monkey_res = self._run_adb_command(monkey_cmd, check=False)
        if "injecting event" not in monkey_res.lower():
            logger.warning(f"Monkey failed to launch {pkg_name}, trying `am start` fallback...")
            # Try a generic known activity (Unity or Main)
            # This might need customization per app type:
            start_cmd = ["adb", "-s", host_port, "shell", "am", "start", "-n", f"{pkg_name}/com.unity3d.player.UnityPlayerActivity"]
            start_res = self._run_adb_command(start_cmd, check=False)
            if "Starting:" not in start_res:
                logger.error(f"Failed to launch app with am start: {start_res}")
                raise EmulatorRunError(f"Failed to run app {pkg_name}")

    def init_device(self):
        """
        Ensure we have a fresh new emulator instance.
        Provision if needed, wait for device readiness.
        """
        logger.info("init_device: Ensuring a fresh emulator instance.")
        # Remove instances.json to force provisioning each time if desired
        instances_path = "instances.json"
        if os.path.exists(instances_path):
            os.remove(instances_path)

        self.app_package_cache = {}

        logger.info("Provisioning new emulator(s) via Terraform...")
        provisioner.provision_emulators()
        time.sleep(20)  # Wait a bit for containers to come up
        self._reload_endpoints()

        if not self.endpoints:
            raise EmulatorConnectionError("No emulator endpoints after provisioning.")

        # Choose an endpoint and wait for device to be ready
        endpoint = random.choice(self.endpoints)
        host_port = endpoint.split("//")[-1]
        # self._wait_for_device(host_port)

        # Connect is more stable for some reason. 
        # TODO: Investigate why.
        parts = host_port.split(":")
        if len(parts) < 2:
            raise ValueError(f"Cannot parse host:port from endpoint: {endpoint}")
        host, port = parts[0], parts[1]

        connect_cmd = ["adb", "connect", f"{host}:{port}"]
        connect_res = self._run_adb_command(connect_cmd, check=False)
        # If connect fails, maybe device was already connected
        logger.info(f"ADB connect result: {connect_res}")
        logger.info(f"init_device: Device {host_port} is ready.")

    def install_app(self, app_ref: str) -> str:
        """
        Install the given app_ref (APK path) on the emulator and detect its package name.
        Uses cached package name if previously installed.
        """
        app_ref = app_ref.strip()
        if not app_ref:
            raise ValueError("app_ref must not be empty in install_app.")

        if not self.endpoints:
            raise EmulatorConnectionError("No emulator endpoints to install app.")

        logger.info(f"Installing app {app_ref} on emulator...")

        endpoint = random.choice(self.endpoints)
        host_port = endpoint.split("//")[-1]
        parts = host_port.split(":")
        if len(parts) < 2:
            raise ValueError("Cannot parse host:port from endpoint")

        # If we have it cached
        if app_ref in self.app_package_cache:
            pkg_name = self.app_package_cache[app_ref]
            logger.info(f"Using cached package name {pkg_name} for {app_ref}")
            return pkg_name

        before_list = self._get_installed_packages(host_port)

        install_cmd = ["adb", "-s", host_port, "install", f"{app_ref}"]
        install_res = self._run_adb_command(install_cmd, check=False)
        if "Success" not in install_res:
            raise EmulatorInstallError(f"Failed to install app {app_ref}, output: {install_res}")

        after_list = self._get_installed_packages(host_port)
        pkg_name = self._detect_new_package(before_list, after_list)
        self.app_package_cache[app_ref] = pkg_name
        return pkg_name

    def run_app(self, app_ref: str) -> Dict[str, Any]:
        """
        Run the previously installed app by pkg_name.
        Attempt to launch and then take a screenshot.
        Returns: {"visuals":{...}, "events": [...], "task_id": ...}
        """
        if not self.endpoints:
            raise EmulatorConnectionError("No emulator endpoints to run app.")

        endpoint = random.choice(self.endpoints)
        host_port = endpoint.split("//")[-1]
        pkg_name = self.app_package_cache[app_ref]
        logger.info(f"run_app: Launching app {app_ref} (package name {pkg_name}) on {host_port}")

        self._attempt_launch_app(host_port, pkg_name)

        # Capture screenshot
        screenshot_cmd = ["adb", "-s", host_port, "exec-out", "screencap", "-p"]
        sc_res = subprocess.run(screenshot_cmd, capture_output=True, timeout=self.timeout)
        if sc_res.returncode != 0:
            raise EmulatorRunError(f"Failed to capture screenshot: {sc_res.stderr}")

        png_data = sc_res.stdout
        screenshot_b64 = base64.b64encode(png_data).decode('utf-8')
        events = ["tap", "scroll", "launch"]
        task_id = str(uuid.uuid4())
        self.task_map[task_id] = {"endpoint": endpoint, "app_ref": pkg_name}
        logger.info(f"App run successful. Task ID: {task_id}")

        return {"visuals": {"screenshot": screenshot_b64}, "events": events, "task_id": task_id}

    def control_app(self, host_port: str, action: str, **params):
        """
        Perform a control action on the emulator device specified by host_port.

        Supported actions:
        - "screenshot": captures current screen and returns image data as base64 (no params)
        - "tap": requires x,y params (int)
        - "type": requires text param (str)
        - "swipe": requires x1,y1,x2,y2 params (int)
        - "back": no params
        - "home": no params

        Raises:
            ValueError if unknown action or missing parameters.
            EmulatorConnectionError, etc. if adb command fails.
        """
        logger.info(f"control_app: Performing {action} with params={params} on {host_port}")

        if action == "screenshot":
            # We will capture a screenshot by using the standard adb screencap command
            # and then pulling it locally.

            screenshot_cmd = ["adb", "-s", host_port, "exec-out", "screencap", "-p"]
            sc_res = subprocess.run(screenshot_cmd, capture_output=True, timeout=self.timeout)
            if sc_res.returncode != 0:
                raise EmulatorRunError(f"Failed to capture screenshot: {sc_res.stderr}")

            png_data = sc_res.stdout
            screenshot_b64 = base64.b64encode(png_data).decode('utf-8')
            logger.info("control_app: screenshot taken and converted to base64.")
            return screenshot_b64

        elif action == "tap":
            x = params.get("x")
            y = params.get("y")
            if x is None or y is None:
                raise ValueError("tap action requires x,y params")
            cmd = ["adb","-s",host_port,"shell","input","tap",str(x),str(y)]
            self._run_adb_command(cmd)
            logger.info("control_app: tap executed.")
            return "Tap done"

        elif action == "type":
            text = params.get("text")
            if text is None:
                raise ValueError("type action requires text param")
            # We'll type character by character.
            # Special handling for space, underscore, etc.
            for char in text:
                if char == ' ':
                    cmd = ["adb","-s",host_port,"shell","input","text","%s"]
                elif char == '_':
                    cmd = ["adb","-s",host_port,"shell","input","keyevent","66"]
                elif char.isalnum() or char in '-.,!?@\'°/:;()':
                    cmd = ["adb","-s",host_port,"shell","input","text",char]
                else:
                    # For other special characters, use broadcast
                    cmd = ["adb","-s",host_port,"shell","am","broadcast","-a","ADB_INPUT_TEXT","--es","msg",char]
                self._run_adb_command(cmd, check=False)
            logger.info(f"control_app: typed text: {text}")
            return f"Typed {text}"

        elif action == "swipe":
            x1 = params.get("x1")
            y1 = params.get("y1")
            x2 = params.get("x2")
            y2 = params.get("y2")
            if None in [x1,y1,x2,y2]:
                raise ValueError("swipe action requires x1,y1,x2,y2 params")
            cmd = ["adb","-s",host_port,"shell","input","swipe",str(x1),str(y1),str(x2),str(y2),"500"]
            self._run_adb_command(cmd)
            logger.info("control_app: swipe executed.")
            return "Swipe done"

        elif action == "back":
            cmd = ["adb","-s",host_port,"shell","input","keyevent","4"]
            self._run_adb_command(cmd)
            logger.info("control_app: back executed.")
            return "Back done"

        elif action == "home":
            cmd = ["adb","-s",host_port,"shell","am","start","-a","android.intent.action.MAIN","-c","android.intent.category.HOME"]
            self._run_adb_command(cmd)
            logger.info("control_app: home executed.")
            return "Home done"

        else:
            raise ValueError(f"Unknown action: {action}")


    def get_vnc_url(self, task_id: str) -> str:
        if task_id not in self.task_map:
            raise KeyError(f"No known emulator instance for task_id: {task_id}")

        info = self.task_map[task_id]
        endpoint = info["endpoint"]
        host_port = endpoint.split("//")[-1]
        parts = host_port.split(":")
        if len(parts) < 1:
            raise ValueError(f"Cannot parse host from endpoint: {endpoint}")
        host = parts[0]

        vnc_url = self.vnc_url_template.format(host=host, port=self.default_vnc_port)
        return vnc_url
