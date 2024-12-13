import requests
import json
import re
import time
import os
import base64
import logging
from typing import List, Dict, Any, Optional

from worker_definitions.base_worker import BaseWorker

# Initialize logger for debugging and maintainability
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)

class AppWorker(BaseWorker):
    ################################################################################
    # Purpose & High-Level Design:
    #
    # The AppWorker integrates MobileAgent-like multi-step operation logic with
    # the providers subsystem. It:
    # 1. Prepares emulator: init_device, optionally upload app, install app.
    # 2. Runs the app on emulator.
    # 3. Explores the app for a configured duration:
    #    - Takes periodic screenshots.
    #    - Uses vision LLM to analyze suspicious elements & determine actions.
    #    - Performs actions (tap, swipe, back, home) if suggested.
    #    - Uses reflection to verify if operations match expectations.
    #    - Updates memory with discovered content.
    #    - Handles errors, limits (max errors), and stops early if too many errors.
    # 4. At the end, aggregates all steps data using aggregator LLM into a final JSON.
    #
    # If pre-run steps or run_app fail, return a minimal result (high risk).
    #
    # Configuration keys (defaults if missing):
    # - providers_server_url: str (default "http://providers:8003")
    # - reflection_switch: bool (default True)
    # - memory_switch: bool (default True)
    # - app_run_duration: int (minutes, default 5)
    # - app_check_interval: int (minutes, default 1)
    # - max_total_errors: int (default 15)
    # - max_consecutive_errors: int (default 3)
    #
    # This code attempts to replicate and integrate functionalities like memory,
    # reflection, and robust prompts from MobileAgent into AppWorker environment.
    ################################################################################

    def validate_task(self, task_data: dict):
        """
        Validate input fields 'app_ref' (mandatory) and 'instructions' (optional).
        """
        app_ref = task_data.get("app_ref")
        if not app_ref or not isinstance(app_ref, str) or app_ref.strip() == "":
            return {"error": "missing or empty 'app_ref' field"}
        # instructions optional
        return None

    def process(self, task_data: dict) -> dict:
        """
        Main workflow: pre-run, run app, exploration, aggregation.
        """
        instructions = task_data.get("instructions", "No specific instructions.")
        app_ref = task_data["app_ref"]
        base_url = self.config.get("providers_server_url", "http://providers:8003")
        run_duration = self.config.get("app_run_duration", 5)   # minutes
        interval = self.config.get("app_check_interval", 1)     # minutes
        max_total_errors = self.config.get("max_total_errors", 15)
        max_consecutive_errors = self.config.get("max_consecutive_errors", 3)

        self.reflection_enabled = self.config.get("reflection_switch", True)
        self.memory_enabled = self.config.get("memory_switch", True)

        # Data structure to store steps info
        steps_data = {
            "Step0_Emulator_Preparation": [],
            "Step1_App_Identification": [],
            "Step2_App_Exploration": []
        }

        # Initialize memory and insight
        self.memory = ""
        self.insight = ""

        # Pre-run steps
        init_res = self._init_emulator_device(base_url)
        steps_data["Step0_Emulator_Preparation"].append(init_res)
        if init_res["status"] == "error":
            return self._fail_no_analysis(steps_data, instructions)

        # If app_ref is local file, upload
        if os.path.exists(app_ref):
            upload_res = self._upload_app_if_needed(base_url, app_ref)
            steps_data["Step0_Emulator_Preparation"].append(upload_res)
            if upload_res["status"]=="error":
                return self._fail_no_analysis(steps_data, instructions)
            # If uploaded, update app_ref to the filename returned
            if "filename" in upload_res.get("data",{}):
                app_ref = upload_res["data"]["filename"]

        # install_app
        install_res = self._install_app(base_url, app_ref)
        steps_data["Step0_Emulator_Preparation"].append(install_res)
        if install_res["status"]=="error":
            return self._fail_no_analysis(steps_data, instructions)

        # run_app
        run_res = self._run_app(base_url, app_ref)
        steps_data["Step1_App_Identification"].append(run_res)
        if run_res["status"]=="error":
            return self._fail_no_analysis(steps_data, instructions)
        emulator_task_id = run_res["data"]["task_id"]

        # Take initial screenshot and vision analysis for identification
        shot_res = self._get_screenshot_for_task(base_url, emulator_task_id)
        screenshot_check = self._make_screenshot_check("check_1_initial_screenshot",0.0,shot_res,"Initial screenshot after run_app")
        steps_data["Step1_App_Identification"].append(screenshot_check)
        if shot_res["status"]=="error":
            return self._fail_no_analysis(steps_data, instructions)
        screenshot_path = shot_res["screenshot_path"]

        ident_prompt = (
            f"User instructions: {instructions}\n"
            "This is the just launched app. Identify the app type and suspicious UI.\n"
            "Return ONLY JSON:\n"
            "{\"risk_level\":\"high|low\",\"confidence\":float,\"reason\":\"...\"}"
        )
        ident_res = self._attempt_vision_llm_for_json(ident_prompt, screenshot_path, base_url, ["risk_level","confidence","reason"])
        ident_check = self._make_vision_check("check_1_ident_vision",0.0,ident_res,"Vision LLM app identify")
        steps_data["Step1_App_Identification"].append(ident_check)

        # Exploration
        explore_res = self._simulate_exploration(base_url, emulator_task_id, instructions, run_duration, interval, max_total_errors, max_consecutive_errors)
        # explore_res returns a dict with "exploration_steps" and "status".
        steps_data["Step2_App_Exploration"].extend(explore_res["exploration_steps"])

        # After exploration, final aggregator call
        final_res = self._final_aggregate_with_retry(steps_data, instructions, base_url, ["risk_level","confidence","reasons"])
        if final_res["status"]=="error":
            # if aggregator fail, return a minimal
            minimal = {
                "status":"completed",
                "result":{
                    "risk_level":"high",
                    "confidence":0.5,
                    "reasons":steps_data
                }
            }
            return minimal
        else:
            return final_res

    ################################################################################
    # Pre-run Methods
    ################################################################################

    def _init_emulator_device(self, base_url: str) -> dict:
        """
        Initialize emulator device with retries.
        """
        pre_run_retries = 3
        pre_run_timeout = 120
        init_dev_endpoint = f"{base_url}/emulator/init_device"

        def call():
            return requests.post(init_dev_endpoint, timeout=pre_run_timeout)

        result = self._retry_call(call, pre_run_retries, wait=30)
        return self._make_check_entry("check_0_init_device","emulator_device_init",0.0,result,"Initialize emulator device", pre_run=True)

    def _upload_app_if_needed(self, base_url: str, app_path: str) -> dict:
        """
        Upload the apk if local path. 3 retries.
        """
        pre_run_retries = 3
        pre_run_timeout = 120
        upload_endpoint = f"{base_url}/emulator/upload_app"

        def call():
            with open(app_path,'rb') as f:
                files={'file':(os.path.basename(app_path),f,'application/octet-stream')}
                return requests.post(upload_endpoint, files=files, timeout=pre_run_timeout)

        result = self._retry_call(call, pre_run_retries, wait=30)
        return self._make_check_entry("check_0_upload_app","emulator_upload_app",0.0,result,"Upload app apk", pre_run=True)

    def _install_app(self, base_url: str, app_ref: str) -> dict:
        """
        Install the app on emulator, 3 retries.
        """
        pre_run_retries = 3
        pre_run_timeout = 120
        install_endpoint = f"{base_url}/emulator/install_app"

        def call():
            return requests.post(install_endpoint, json={"app_ref":app_ref}, timeout=pre_run_timeout)

        result = self._retry_call(call, pre_run_retries, wait=30)
        return self._make_check_entry("check_0_install_app","emulator_install_app",0.0,result,"Install the app", pre_run=True)

    ################################################################################
    # Run App Method
    ################################################################################
    def _run_app(self, base_url: str, app_ref: str) -> dict:
        """
        Run the app, 2 retries
        """
        run_app_retries = 2
        run_app_timeout = 60
        run_app_endpoint = f"{base_url}/emulator/run_app"

        def call():
            return requests.post(run_app_endpoint, json={"app_ref":app_ref}, timeout=run_app_timeout)

        result = self._retry_call(call, run_app_retries, wait=60)
        return self._make_check_entry("check_1_run_app","emulator_run_app",0.0,result,"Run the app", pre_run=True)

    ################################################################################
    # Exploration Simulation
    ################################################################################
    def _simulate_exploration(self, base_url: str, emulator_task_id: str, instructions: str, run_duration: int, interval: int, max_total_errors: int, max_consecutive_errors: int) -> dict:
        """
        Runs the exploration loop for run_duration minutes.
        Every interval:
          - Screenshot
          - Vision analysis with a prompt: must return action + suspicious rating
          - Perform action if needed
          - Possibly reflect & update memory
        Stop early if too many errors.

        Returns {"exploration_steps":[...],"status":"completed" or "error"}
        """
        start_time = time.time()
        checks_count = 0
        total_errors = 0
        consecutive_errors = 0

        exploration_steps = []

        # The vision prompt at each step
        # Returns risk_level,confidence,reason,action
        # action: Tap(x,y),Swipe(...),Back,Home,None
        # We also incorporate reflection if enabled.
        # After performing action, we may reflect if changed or not.
        #
        # Additional complexity: memory. If memory_enabled, we might request memory update.

        while time.time() - start_time < run_duration*60:
            time.sleep(interval*60)
            checks_count += 1
            logger.info(f"Exploration: {checks_count}/{run_duration} steps")

            # Screenshot
            shot_res = self._get_screenshot_for_task(base_url, emulator_task_id)
            sc_check = self._make_screenshot_check(f"check_2_explore_shot_{checks_count}",0.0,shot_res,f"Exploration screenshot #{checks_count}")
            exploration_steps.append(sc_check)
            if shot_res["status"]=="error":
                total_errors+=1
                consecutive_errors+=1
                if total_errors>max_total_errors or consecutive_errors>max_consecutive_errors:
                    break
                continue
            else:
                consecutive_errors=0

            screenshot_path = shot_res["screenshot_path"]

            vision_prompt = (
                f"User instructions: {instructions}\n"
                f"We are analyzing this app for {run_duration} minutes, currently at minute {checks_count}/{run_duration}.\n"
                "You see a screenshot of the running app.\n"
                "Check suspicious UI.\n"
                "Possible actions: Tap(x,y), Swipe(x1,y1,x2,y2), Back, Home, None.\n"
                "Return ONLY JSON:\n"
                "{\"risk_level\":\"high|low\",\"confidence\":float,\"reason\":\"...\",\"action\":\"Tap(...)|Swipe(...)|Back|Home|None\"}"
            )

            vis_res = self._attempt_vision_llm_for_json(vision_prompt, screenshot_path, base_url, ["risk_level","confidence","reason","action"])
            vision_check = self._make_vision_check(f"check_2_explore_vision_{checks_count}",0.0,vis_res,f"Exploration vision analysis #{checks_count}")
            exploration_steps.append(vision_check)

            if vis_res["status"]=="error":
                total_errors+=1
                consecutive_errors+=1
                if total_errors>max_total_errors or consecutive_errors>max_consecutive_errors:
                    break
                continue
            else:
                consecutive_errors=0

            vr = vis_res["result"]
            action_str = vr["action"].strip()
            if action_str.lower()!="none":
                action_res = self._perform_action_with_retry(base_url, emulator_task_id, action_str)
                exploration_steps.append(action_res)
                if action_res["status"]=="error":
                    total_errors+=1
                    consecutive_errors+=1
                    if total_errors>max_total_errors or consecutive_errors>max_consecutive_errors:
                        break
                else:
                    consecutive_errors=0

            # Reflection phase (optional)
            if self.reflection_enabled:
                # We'll reflect only if we performed an action other than none.
                # Reflection requires the previous and current screenshot to see changes.
                # For reflection, we need last_screenshot saved, let's do a trick:
                # We will keep track of last_screenshot_path and last_info in class fields?
                # Let's store them in class for reflection.
                prev_screenshot_path = getattr(self, 'prev_screenshot_path', None)
                prev_info = getattr(self, 'prev_info', [])
                curr_info = "Some extracted info from screenshot if needed" # Simplify for now

                if prev_screenshot_path and action_str.lower()!="none":
                    # reflect
                    reflect_res = self._reflect_on_change(instructions, prev_screenshot_path, screenshot_path, prev_info, curr_info)
                    # Add reflect check
                    exploration_steps.append(reflect_res)
                    if reflect_res["status"]=="error":
                        total_errors+=1
                        consecutive_errors+=1
                        if total_errors>max_total_errors or consecutive_errors>max_consecutive_errors:
                            break
                    else:
                        consecutive_errors=0
                        # If reflection returns some insight:
                        if "insight" in reflect_res:
                            self._update_memory(reflect_res["insight"])

                # update prev_screenshot_path & prev_info
                self.prev_screenshot_path = screenshot_path
                self.prev_info = curr_info

            # Memory update: If memory_enabled and we have new insights
            if self.memory_enabled and "No suspicious" not in vr["reason"]:
                # Suppose we just add the reason to memory if suspicious patterns found:
                self._update_memory("Additional insight from vision: "+vr["reason"])

            # If suspicious high risk found multiple times, might stop early?
            # We'll rely on error logic for now.
            if total_errors>max_total_errors or consecutive_errors>max_consecutive_errors:
                break

        return {"exploration_steps":exploration_steps, "status":"completed"}

    ################################################################################
    # Aggregation
    ################################################################################
    def _final_aggregate_with_retry(self, steps_data: dict, instructions: str, base_url: str, required_keys: list) -> dict:
        for i in range(3):
            res = self._final_aggregate(steps_data, instructions, base_url, required_keys)
            if res["status"]=="completed":
                return res
            time.sleep(5)
        return {"status":"error","message":"Aggregator failed after 3 tries"}

    def _final_aggregate(self, steps_data: dict, instructions: str, base_url: str, required_keys: list) -> dict:
        aggregator_prompt=(
            f"User instructions: {instructions}\n"
            "You have steps_data:\n"
            "\"Step0_Emulator_Preparation\":[...],\n"
            "\"Step1_App_Identification\":[...],\n"
            "\"Step2_App_Exploration\":[...]\n"
            "Now produce final JSON ONLY:\n"
            "{\n"
            "\"risk_level\":\"high|low\",\n"
            "\"confidence\":float,\n"
            "\"reasons\":{\n"
            "  \"Step0_Emulator_Preparation\":[...],\n"
            "  \"Step1_App_Identification\":[...],\n"
            "  \"Step2_App_Exploration\":[...]\n"
            "}\n"
            "}\n"
            "No extra text.\n"
            "If suspicious patterns found, risk=high else low.\n"
            "Confidence = weighted avg.\n"
            f"{json.dumps(steps_data)}"
        )
        return self._call_llm_for_json(aggregator_prompt, base_url, required_keys)

    ################################################################################
    # Memory & Reflection Methods
    ################################################################################
    def _update_memory(self, insight: str):
        """
        If memory_enabled, add insight to memory if not redundant.
        """
        if not self.memory_enabled:
            return
        if insight.strip() and insight not in self.memory:
            self.memory += insight+"\n"
            logger.info(f"Memory updated with: {insight}")

    def _reflect_on_change(self, instructions: str, prev_shot: str, curr_shot: str, prev_info: Any, curr_info: Any) -> dict:
        """
        Use reflection to see if last action had the expected effect.
        For simplicity, we just ask LLM if the current state differs as expected.

        Return a JSON with maybe keys:
        {status:"completed", risk_level:"low",confidence:0.8,explanation:"reflection result",insight:"some content"} or error.
        """

        reflect_prompt = (
            f"User instructions: {instructions}\n"
            "We have two screenshots: before and after.\n"
            "Check if the last action met the expectation.\n"
            "Return ONLY JSON:\n"
            "{\"status\":\"completed\",\"risk_level\":\"low|high\",\"confidence\":float,\"explanation\":\"...\",\"insight\":\"...\"}"
        )

        # For reflection, we can treat prev_info/curr_info as normal text and call text llm.
        # If we had a special reflection route, we would call text LLM again:
        # We'll just call normal aggregator LLM:
        base_url = self.config.get("providers_server_url", "http://providers:8003")
        # incorporate prev_info, curr_info in prompt?
        reflect_prompt += f"\nBefore info: {prev_info}\nAfter info: {curr_info}\n"

        required_keys=["status","risk_level","confidence","explanation"]
        # insight optional, if missing no problem
        res = self._call_llm_for_json(reflect_prompt, base_url, required_keys)
        if res["status"]=="completed":
            # if optional "insight" missing, no problem
            if "insight" not in res["result"]:
                res["result"]["insight"]="No new insight"
            return {"status":"completed","risk_level":res["result"]["risk_level"],"confidence":res["result"]["confidence"],"explanation":res["result"]["explanation"],"insight":res["result"]["insight"]}
        else:
            return res

    ################################################################################
    # Vision & LLM Call Helpers
    ################################################################################
    def _attempt_vision_llm_for_json(self, prompt: str, image_path: str, base_url: str, required_keys: List[str]) -> dict:
        for i in range(3):
            res = self._call_vision_llm_for_json(prompt, image_path, base_url, required_keys)
            if res["status"]=="error":
                logger.info(f"Vision LLM attempt {i+1}/3 failed: {res['message']}")
                if i<2: time.sleep(5)
            else:
                return res
        return {"status":"error","message":"Vision LLM 3 attempts failed"}

    def _call_vision_llm_for_json(self, prompt: str, image_path: str, base_url: str, required_keys: List[str]) -> dict:
        llm_endpoint = f"{base_url}/llm/vision"
        try:
            with open(image_path,'rb') as f:
                b64_img = base64.b64encode(f.read()).decode('utf-8')
            body = {"prompt":prompt,"images":[b64_img]}
            llm_resp = requests.post(llm_endpoint,json=body,timeout=30)
            if llm_resp.status_code!=200:
                return {"status":"error","message":f"Vision LLM {llm_resp.status_code}"}
            llm_data = llm_resp.json()
            if llm_data.get("status")!="success":
                return {"status":"error","message":"Vision LLM not success"}
            raw = llm_data["response"].strip()
            parsed = self._strict_json_parse(raw, required_keys)
            return parsed
        except requests.RequestException as e:
            return {"status":"error","message":f"Net err Vision LLM: {str(e)}"}

    def _call_llm_for_json(self, prompt: str, base_url: str, required_keys: List[str]) -> dict:
        llm_endpoint = f"{base_url}/llm/chat_complete"
        try:
            llm_resp = requests.post(llm_endpoint, json={"prompt":prompt}, timeout=20)
            if llm_resp.status_code!=200:
                return {"status":"error","message":f"LLM {llm_resp.status_code}"}
            llm_data=llm_resp.json()
            if llm_data.get("status")!="success":
                return {"status":"error","message":"LLM aggregator not success"}
            raw=llm_data["response"].strip()
            parsed=self._strict_json_parse(raw, required_keys)
            return parsed
        except requests.RequestException as e:
            return {"status":"error","message":f"Net err aggregator LLM: {str(e)}"}

    def _strict_json_parse(self, raw_response: str, required_keys: List[str]=[]) -> dict:
        """
        Tries json.loads first, if fail tries regex.
        Ensures required_keys present.
        """
        try:
            parsed=json.loads(raw_response)
            if any(k not in parsed for k in required_keys):
                return {"status":"error","message":"LLM JSON missing keys"}
            return {"status":"completed","result":parsed}
        except json.JSONDecodeError:
            match=re.search(r'\{.*\}', raw_response, flags=re.DOTALL)
            if match:
                block=match.group(0).strip()
                try:
                    parsed=json.loads(block)
                    if any(k not in parsed for k in required_keys):
                        return {"status":"error","message":"LLM JSON missing keys"}
                    return {"status":"completed","result":parsed}
                except json.JSONDecodeError:
                    return {"status":"error","message":"LLM response not valid JSON (fallback)"}
            return {"status":"error","message":"LLM response not valid JSON"}

    ################################################################################
    # Action Execution Helpers
    ################################################################################
    def _perform_action_with_retry(self, base_url: str, task_id: str, action_str: str) -> dict:
        for i in range(2):
            res = self._perform_action_once(base_url, task_id, action_str)
            if res["status"]=="completed":
                return res
            if i<1:
                time.sleep(5)
        return res

    def _perform_action_once(self, base_url: str, task_id: str, action_str: str) -> dict:
        action_str = action_str.strip()
        action_str_lower = action_str.lower()
        params={"task_id":task_id}
        try:
            if action_str_lower.startswith("tap("):
                coords = action_str.split("(")[-1].split(")")[0].split(",")
                if len(coords)!=2:
                    return self._action_error("Tap parse fail")
                x,y = coords
                endpoint=f"{base_url}/emulator/tap"
                logger.info(f"Performing tap action: {x},{y}")
                resp=requests.post(endpoint,json={"x":int(x.strip()),"y":int(y.strip())},params=params,timeout=30)
            elif action_str_lower.startswith("swipe("):
                m = re.match(r"Swipe\s*\((\d+),(\d+)\)\s*,\s*\((\d+),(\d+)\)",action_str)
                if not m:
                    return self._action_error("Swipe parse fail")
                x1,y1,x2,y2=m.groups()
                endpoint=f"{base_url}/emulator/swipe"
                logger.info(f"Performing swipe action: {x1},{y1} -> {x2},{y2}")
                resp=requests.post(endpoint,json={"x1":int(x1),"y1":int(y1),"x2":int(x2),"y2":int(y2)},params=params,timeout=30)
            elif action_str_lower=="back":
                endpoint=f"{base_url}/emulator/back"
                logger.info("Performing back action")
                resp=requests.post(endpoint,params=params,timeout=30)
            elif action_str_lower=="home":
                endpoint=f"{base_url}/emulator/home"
                logger.info("Performing home action")
                resp=requests.post(endpoint,params=params,timeout=30)
            elif action_str_lower=="none":
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
                return self._action_error("Unknown action")

            if resp.status_code!=200:
                return self._action_error(f"action endpoint {resp.status_code}")
            data=resp.json()
            if data.get("status")=="ok":
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
                return self._action_error("action not ok")

        except requests.RequestException as e:
            return self._action_error(f"Network error action: {str(e)}")

    def _action_error(self, msg: str) -> dict:
        return {
            "check_id":"action_error",
            "analysis_agent":"emulator_action",
            "weight":0.0,
            "risk_level":"low",
            "confidence":0.5,
            "explanation":f"Action failed: {msg}",
            "status":"error"
        }

    ################################################################################
    # Retry and Error Handling Helpers
    ################################################################################
    def _retry_call(self, func, max_retries: int, wait: int=10) -> dict:
        """
        Calls func multiple times.
        func should return a requests.Response.
        Returns {status:"completed",data:...} or {status:"error",message:"..."}
        """
        for i in range(max_retries):
            try:
                resp = func()
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") in ["ok","success"]:
                        return {"status":"completed","data":data,"events":data.get("events",[]),"task_id":data.get("task_id")}
                    else:
                        # Not ok/success in json
                        pass
                else:
                    # non-200 code
                    pass
            except requests.RequestException as e:
                logger.warning(f"Network error: {e}")

            if i<max_retries-1:
                time.sleep(wait)

        return {"status":"error","message":"Max retries exceeded"}

    def _fail_no_analysis(self, steps_data: dict, instructions: str) -> dict:
        """
        If we fail pre-run or run steps, no analysis done => final minimal result.
        """
        minimal = {
            "status":"completed",
            "result":{
                "risk_level":"high",
                "confidence":0.5,
                "reasons":steps_data
            }
        }
        return minimal

    ################################################################################
    # Utility Check Entry Methods
    ################################################################################
    def _make_check_entry(self, check_id: str, agent: str, weight: float, result: dict, explanation: str, pre_run: bool=False) -> dict:
        # If pre_run or run steps fail => not suspicious, just fails workflow.
        # risk=low by default for pre-run steps.
        risk = "low"
        conf = 0.8 if result["status"] == "completed" else 0.5
        explan = explanation
        if result["status"] == "completed":
            explan += " - success."
        else:
            explan += f" - {result.get('message','failed')}"

        entry = {
            "check_id": check_id,
            "analysis_agent": agent,
            "weight": weight,
            "risk_level": risk,
            "confidence": conf,
            "explanation": explan,
            # Include status and message from result here
            "status": result["status"]
        }
        if "message" in result:
            entry["message"] = result["message"]
        if "data" in result:
            entry["data"] = result["data"]
        return entry

    def _make_screenshot_check(self, check_id: str, weight: float, result: dict, explanation: str) -> dict:
        if result["status"]=="error":
            return {
                "check_id":check_id,
                "analysis_agent":"emulator_screenshot",
                "weight":weight,
                "risk_level":"low",
                "confidence":0.5,
                "explanation":f"{explanation} - {result.get('message','no message')}"
            }
        else:
            return {
                "check_id":check_id,
                "analysis_agent":"emulator_screenshot",
                "weight":weight,
                "risk_level":"low",
                "confidence":0.7,
                "explanation":f"{explanation} - Screenshot taken."
            }

    def _make_vision_check(self, check_id: str, weight: float, result: dict, explanation: str) -> dict:
        if result["status"]=="error":
            return {
                "check_id":check_id,
                "analysis_agent":"vision_llm",
                "weight":weight,
                "risk_level":"low",
                "confidence":0.5,
                "explanation":f"{explanation} - Vision LLM error: {result.get('message')}"
            }
        else:
            vr = result["result"]
            return {
                "check_id":check_id,
                "analysis_agent":"vision_llm",
                "weight":weight,
                "risk_level":vr["risk_level"],
                "confidence":vr["confidence"],
                "explanation":f"{explanation} - {vr['reason']}"
            }

    ################################################################################
    # Screenshot Retrieval
    ################################################################################
    def _get_screenshot_for_task(self, base_url: str, task_id: str) -> dict:
        """
        GET /emulator/screenshot?task_id=...
        """
        shot_endpoint = f"{base_url}/emulator/screenshot"
        try:
            resp = requests.get(shot_endpoint, params={"task_id":task_id}, timeout=30)
            if resp.status_code!=200:
                return {"status":"error","message":f"screenshot {resp.status_code}"}
            data=resp.json()
            if data.get("status")!="ok":
                return {"status":"error","message":"screenshot not ok"}
            b64_str=data.get("screenshot","")
            if not b64_str:
                return {"status":"error","message":"No screenshot data"}
            screenshot_path="./app_worker_screenshot.jpg"
            with open(screenshot_path,"wb") as f:
                f.write(base64.b64decode(b64_str))
            return {"status":"completed","screenshot_path":screenshot_path}
        except requests.RequestException as e:
            return {"status":"error","message":f"Net error screenshot: {str(e)}"}
