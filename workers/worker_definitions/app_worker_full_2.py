from worker_definitions.base_worker import BaseWorker
import requests
import json
import re
import time
import os
import base64

import logging
logger = logging.getLogger(__name__)

class AppWorker(BaseWorker):
    ################################################################################
    # Purpose & High-Level Design:
    #
    # The AppWorker:
    # 1. Pre-run (Step0): init_device, upload_app (if local), install_app.
    #    - If fail at any step after 3 retries => cannot proceed. 
    #      Return final result with high risk (no analysis done).
    #
    # 2. run_app (Step1): 2 retries, if fail => no analysis => high risk final.
    #
    # 3. Exploration (Step2):
    #    - run for `run_duration` minutes, every `interval`:
    #      * screenshot
    #      * vision LLM with a prompt asking what action to take and suspiciousness.
    #      * If vision LLM fails to return proper JSON after 3 tries, count error.
    #      * If total errors > 15 or consecutive errors > 3, stop early.
    #      * If action != None, perform it and if fail => count error.
    #
    # 4. After exploration, call aggregator LLM with all recorded steps and checks.
    #    If aggregator fails, retry 3 times. If still fails, return error message.
    #
    # Pre-run and run steps do NOT affect suspicious rating, just whether we can proceed.
    # If we can't proceed, final = high risk (no analysis).
    #
    # If we complete exploration:
    #  - aggregator will incorporate all steps, suspicious rating from vision checks.
    #
    # Maintainability:
    # - Adjust run_duration, interval in config.
    # - If aggregator or vision logic changes, update prompts in methods.
    #
    ################################################################################

    def validate_task(self, task_data: dict):
        app_ref = task_data.get("app_ref")
        if not app_ref or not isinstance(app_ref, str) or app_ref.strip() == "":
            return {"error":"missing or empty 'app_ref' field"}
        return None

    def process(self, task_data: dict) -> dict:
        instructions = task_data.get("instructions","No instructions.")
        app_ref = task_data["app_ref"]
        base_url = self.config.get("providers_server_url","http://providers:8003")
        run_duration = self.config.get("app_run_duration", 5) # minutes
        interval = self.config.get("app_check_interval", 1)   # minutes

        steps_data = {
            "Step0_Emulator_Preparation": [],
            "Step1_App_Identification": [],
            "Step2_App_Exploration": []
        }

        # Retry configs
        pre_run_retries = 3
        pre_run_timeout = 120
        run_app_retries = 2
        run_app_timeout = 60

        # Error handling in exploration
        max_total_errors = 15
        max_consecutive_errors = 3
        total_errors = 0
        consecutive_errors = 0

        # Pre-run steps:
        # init_device
        init_result = self._retry_call(lambda: requests.post(f"{base_url}/emulator/init_device", timeout=pre_run_timeout), pre_run_retries, wait=30)
        steps_data["Step0_Emulator_Preparation"].append(self._make_check_entry("check_0_init_device", "emulator_device_init", 0.0, init_result, "Initialize emulator device", pre_run=True))
        if init_result["status"]=="error":
            return self._fail_no_analysis(steps_data, instructions, base_url)
        
        # Need to wait for 20 seconds for emulator to be ready
        logger.info(f"Waiting for 20 seconds for emulator to be ready...")
        time.sleep(20)

        # upload_app if local
        upload_needed = os.path.exists(app_ref)
        if upload_needed:
            def upload_call():
                with open(app_ref,'rb') as f:
                    files = {'file':(os.path.basename(app_ref), f,'application/octet-stream')}
                    return requests.post(f"{base_url}/emulator/upload_app", files=files, timeout=pre_run_timeout)
            upload_result = self._retry_call(upload_call, pre_run_retries, wait=30)
            logger.info(f"Upload result: {upload_result}")
            steps_data["Step0_Emulator_Preparation"].append(self._make_check_entry("check_0_upload_app","emulator_upload_app",0.0,upload_result,"Upload app apk", pre_run=True))
            if upload_result["status"]=="error":
                return self._fail_no_analysis(steps_data, instructions, base_url)
            if "filename" in upload_result.get("data",{}):
                app_ref = upload_result["data"]["filename"]

        # install_app
        def install_call():
            return requests.post(f"{base_url}/emulator/install_app", json={"app_ref":app_ref}, timeout=pre_run_timeout)
        install_result = self._retry_call(install_call, pre_run_retries, wait=30)
        steps_data["Step0_Emulator_Preparation"].append(self._make_check_entry("check_0_install_app","emulator_install_app",0.0,install_result,"Install the app", pre_run=True))
        if install_result["status"]=="error":
            return self._fail_no_analysis(steps_data, instructions, base_url)
        logger.info(f"Install result: {install_result}")


        # Need to wait for 5 seconds for app to be ready
        logger.info(f"Waiting for 5 seconds for app to be ready...")
        time.sleep(5)

        # run_app
        def run_app_call():
            return requests.post(f"{base_url}/emulator/run_app", json={"app_ref":app_ref}, timeout=run_app_timeout)
        run_app_result = self._retry_call(run_app_call, run_app_retries, wait=60)
        logger.info(f"Run app result: task_id: {run_app_result['data']['task_id']}, events: {run_app_result['data']['events']}, status: {run_app_result['data']['status']}")

        steps_data["Step1_App_Identification"].append(self._make_check_entry("check_1_run_app","emulator_run_app",0.0,run_app_result,"Run the app", pre_run=True))
        if run_app_result["status"]=="error":
            return self._fail_no_analysis(steps_data, instructions, base_url)

        emulator_task_id = run_app_result["data"].get("task_id")
        if not emulator_task_id:
            # no task_id means can't proceed
            return self._fail_no_analysis(steps_data, instructions, base_url)

        # initial screenshot
        shot_res = self._get_screenshot_for_task(base_url, emulator_task_id)
        steps_data["Step1_App_Identification"].append(self._make_screenshot_check("check_1_initial_screenshot",0.0,shot_res,"Initial screenshot after run_app"))
        if shot_res["status"]=="error":
            return self._fail_no_analysis(steps_data, instructions, base_url)

        screenshot_path = shot_res["screenshot_path"]

        # Vision analysis initial
        ident_prompt = (
            f"User instructions: {instructions}\n"
            "You see a screenshot of a just launched app. Identify app and suspicious UI.\n"
            "Return ONLY JSON:\n"
            "{\"risk_level\":\"high|low\",\"confidence\":float,\"reason\":\"...\"}"
        )
        # Attempt vision LLM 3 times if fail:
        ident_res = self._attempt_vision_llm_for_json(ident_prompt, screenshot_path, base_url, ["risk_level","confidence","reason"])
        steps_data["Step1_App_Identification"].append(self._make_vision_check("check_1_ident_vision",0.0,ident_res,"Vision LLM app identify"))

        if ident_res["status"]=="error":
            # This is a vision step. If fail here, not suspicious, just no info.
            total_errors += 1
            consecutive_errors += 1

        # Exploration
        # run for run_duration
        start_time = time.time()
        checks_count = 0

        # We'll store results from each exploration step
        # Vision prompt each time:
        # must return risk_level,confidence,reason,action
        # If fail 3 times in a row to parse vision LLM, count error.
        # If action != None and fail to perform action => error.

        # If total_errors>15 or consecutive_errors>3 => stop early.

        operation_counts = 0
        while time.time()-start_time < run_duration*60:
            operation_counts += 1
            time.sleep(interval*60)
            checks_count += 1
            # screenshot
            shot_res = self._get_screenshot_for_task(base_url, emulator_task_id)
            sc_check = self._make_screenshot_check(f"check_2_explore_shot_{checks_count}",0.0,shot_res,f"Exploration screenshot #{checks_count}")
            steps_data["Step2_App_Exploration"].append(sc_check)
            if shot_res["status"]=="error":
                total_errors+=1
                consecutive_errors+=1
                if total_errors>15 or consecutive_errors>3:
                    break
                continue
            else:
                consecutive_errors=0

            screenshot_path = shot_res["screenshot_path"]

            vision_prompt = (
                f"User instructions: {instructions}\n"
                f"We are analyzing this app for {run_duration} minutes, currently at minute {checks_count}/{run_duration}.\n"
                "You see a screenshot. Check suspicious UI.\n"
                "Actions: Tap(x,y),Swipe(x1,y1,x2,y2),Back,Home,None\n"
                "Return ONLY JSON:\n"
                "{\"risk_level\":\"high|low\",\"confidence\":float,\"reason\":\"...\",\"action\":\"Tap(...)|Swipe(...)|Back|Home|None\"}"
            )

            logger.info(f"[{(time.time() - start_time)/(run_duration*60)}%] Starting vision analysis #{operation_counts} at {time.time() - start_time} / {run_duration*60} seconds")

            step_vision_res = self._attempt_vision_llm_for_json(vision_prompt, screenshot_path, base_url, ["risk_level","confidence","reason","action"])
            steps_data["Step2_App_Exploration"].append(self._make_vision_check(f"check_2_explore_vision_{checks_count}",0.0,step_vision_res,f"Exploration vision analysis #{checks_count}"))
            if step_vision_res["status"]=="error":
                total_errors+=1
                consecutive_errors+=1
                logger.info(f"[{(time.time() - start_time)/(run_duration*60)}%] Vision analysis #{operation_counts} failed, attempt {consecutive_errors}")
                if total_errors>15 or consecutive_errors>3:
                    break
                continue
            else:
                consecutive_errors=0

            # Perform action
            vr = step_vision_res["result"]
            action = vr["action"].strip()

            logger.info(f"[{(time.time() - start_time)/(run_duration*60)}%] Got Result: {vr} - Performing action: {action}")

            if action.lower()!="none":
                action_res = self._perform_action_with_retry(base_url, emulator_task_id, action)
                steps_data["Step2_App_Exploration"].append(action_res)
                if action_res["risk_level"]=="low" and "success" in action_res["explanation"]:
                    consecutive_errors=0
                else:
                    total_errors+=1
                    consecutive_errors+=1
                    if total_errors>15 or consecutive_errors>3:
                        break

        # After exploration or early break:
        # Call aggregator LLM.
        return self._final_aggregate_with_retry(steps_data, instructions, base_url, ["risk_level","confidence","reasons"])

    def get_metadata(self):
        return {
            "description":"Run an app in emulator, use vision LLM to guide actions and check suspicious UI, aggregate final results.",
            "required_fields":["app_ref"],
            "mode":self.config.get("mode","local"),
            "capabilities":["emulator init/install/run","vision-based dynamic analysis","interactive actions","JSON aggregator"]
        }

    ################################################################################
    # Helper Methods
    ################################################################################

    def _fail_no_analysis(self, steps_data, instructions, base_url):
        # If we fail pre-run or run, no analysis done => final aggregator with minimal result?
        # Just produce a final minimal JSON: risk=high (unknown)
        # aggregator not needed
        minimal = {
            "status":"completed",
            "result":{
                "risk_level":"high",
                "confidence":0.5,
                "reasons":{
                    "Step0_Emulator_Preparation":steps_data["Step0_Emulator_Preparation"],
                    "Step1_App_Identification":steps_data["Step1_App_Identification"],
                    "Step2_App_Exploration":steps_data["Step2_App_Exploration"]
                }
            }
        }
        return minimal

    def _retry_call(self, func, max_retries, wait=10):
        for i in range(max_retries):
            try:
                resp = func()
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") in ["ok","success"]:
                        return {"status":"completed","data":data}
                    else:
                        # Not ok
                        pass
                else:
                    # non-200
                    pass
            except requests.RequestException:
                pass
            if i<max_retries-1:
                time.sleep(wait)
        return {"status":"error","message":"Max retries exceeded"}

    def _make_check_entry(self, check_id, agent, weight, result, explanation, pre_run=False):
        # If error in pre-run or run steps doesn't affect suspicious rating (no suspicious from these steps)
        risk = "low"
        conf = 0.8 if result["status"]=="completed" else 0.5
        explan = explanation
        if result["status"]=="completed":
            explan+=" - success."
        else:
            explan+=f" - {result.get('message','failed')}"
        return {
            "check_id":check_id,
            "analysis_agent":agent,
            "weight":weight,
            "risk_level":risk,
            "confidence":conf,
            "explanation":explan
        }

    def _make_screenshot_check(self, check_id, weight, result, explanation):
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

    def _make_vision_check(self, check_id, weight, result, explanation):
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

    def _get_screenshot_for_task(self, base_url, task_id):
        try:
            resp = requests.get(f"{base_url}/emulator/screenshot", params={"task_id":task_id}, timeout=30)
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

    def _attempt_vision_llm_for_json(self, prompt, image_path, base_url, required_keys):
        # try 3 times
        for i in range(3):
            res = self._call_vision_llm_for_json(prompt, image_path, base_url, required_keys)
            if res["status"]=="error":
                # retry
                if i<2: time.sleep(5)
            else:
                return res
        return {"status":"error","message":"Vision LLM 3 attempts failed"}

    def _call_vision_llm_for_json(self, prompt, image_path, base_url, required_keys):
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
            raw_response = llm_data["response"].strip()
            parsed = self._strict_json_parse(raw_response, required_keys)
            return parsed
        except requests.RequestException as e:
            return {"status":"error","message":f"Net err Vision LLM: {str(e)}"}
        except (json.JSONDecodeError,KeyError):
            return {"status":"error","message":"Invalid Vision LLM response"}

    def _perform_action_with_retry(self, base_url, task_id, action):
        # parse action: Tap(x,y), Swipe(...), Back, Home
        # 2 retries if fail?
        # Actually we can just 1 try. If fail => error action
        for i in range(2):
            res = self._perform_action_once(base_url, task_id, action)
            if res["status"]=="completed":
                return res
            if i<1: time.sleep(5)
        return res # last attempt result

    def _perform_action_once(self, base_url, task_id, action_str):
        action_str = action_str.strip()
        action_str_lower = action_str.lower()
        endpoint = None
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
                # format: Swipe(x1,y1),(x2,y2)
                m = re.match(r"Swipe\s*\((\d+),(\d+)\)\s*,\s*\((\d+),(\d+)\)",action_str)
                if not m:
                    return self._action_error("Swipe parse fail")
                x1,y1,x2,y2=m.groups()
                endpoint=f"{base_url}/emulator/swipe"
                logger.info(f"Performing swipe action: {x1},{y1} -> {x2},{y2}")
                resp=requests.post(endpoint,json={"x1":int(x1),"y1":int(y1),"x2":int(x2),"y2":int(y2)},params=params,timeout=30)
            elif action_str_lower=="back":
                endpoint=f"{base_url}/emulator/back"
                logger.info(f"Performing back action")
                resp=requests.post(endpoint,params=params,timeout=30)
            elif action_str_lower=="home":
                endpoint=f"{base_url}/emulator/home"
                logger.info(f"Performing home action")
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

    def _action_error(self, msg):
        return {
            "check_id":"action_error",
            "analysis_agent":"emulator_action",
            "weight":0.0,
            "risk_level":"low",
            "confidence":0.5,
            "explanation":f"Action failed: {msg}",
            "status":"error"
        }

    def _final_aggregate_with_retry(self, steps_data, instructions, base_url, required_keys):
        # aggregator might fail, retry 3 times
        for i in range(3):
            res = self._final_aggregate(steps_data, instructions, base_url, required_keys)
            if res["status"]=="completed":
                return res
            # else retry
            time.sleep(5)
        # if still fail
        return {"status":"error","message":"Aggregator failed after 3 tries"}

    def _final_aggregate(self, steps_data, instructions, base_url, required_keys):
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
            "If no suspicious from exploration steps, risk=low else high.\n"
            "Confidence = weighted avg of all relevant checks.\n"
            f"{json.dumps(steps_data)}"
        )
        return self._call_llm_for_json(aggregator_prompt, base_url, required_keys)

    def _call_llm_for_json(self, prompt, base_url, required_keys):
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

    def _strict_json_parse(self, raw_response, required_keys=[]):
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
