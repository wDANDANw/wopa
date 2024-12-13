###############################################################################
# app_service.py
#
# Purpose:
# The AppService class implements logic for analyzing an app (like an APK) 
# by interacting with the "app" worker and aggregator LLM.
#
# Steps:
# 1. Validate input: require "app_ref" (the app name or reference) and "instructions".
# 2. Call the app worker with {"worker_type":"app","app_ref":...,"instructions":...}.
# 3. If worker error, return error.
# 4. If worker completed with {"suspicious":"yes/no","analysis":"..."},
#    call aggregator LLM to produce final {"suspicious":"...","reason":"..."}.
# 5. Return completed with final result.
#
# Logging:
# - Detailed logs at DEBUG and INFO for validation, worker calls, aggregator calls.
#
# Testing:
# - Similar to message_service/link_service testing.
###############################################################################

import json
import re
import requests
import logging
from typing import Optional, Dict
from .base_service import BaseService

logger = logging.getLogger("services")

class AppService(BaseService):
    def __init__(self, config: dict):
        """
        Initialize AppService.

        Expects config:
        - WORKER_SERVER_URL (default http://workers:8001)
        - PROVIDER_SERVER_URL (default http://providers:8003)
        """
        self.config = config
        self.description = "Analyze an app (APK) by simulating instructions and detecting suspicious behavior."
        self.worker_server_url = self.config.get("WORKER_SERVER_URL","http://workers:8001")
        self.provider_server_url = self.config.get("PROVIDER_SERVER_URL","http://providers:8003")

    def validate_task(self, task_data: dict) -> Optional[dict]:
        logger.debug("AppService.validate_task: Validating input %s", task_data)
        if "app_ref" not in task_data:
            logger.debug("AppService.validate_task: Missing 'app_ref' field")
            return {"error":"Missing 'app_ref' field"}
        if not isinstance(task_data["app_ref"], str) or not task_data["app_ref"].strip():
            logger.debug("AppService.validate_task: 'app_ref' empty or non-string")
            return {"error":"app_ref cannot be empty or non-string"}

        if "instructions" not in task_data:
            logger.debug("AppService.validate_task: Missing 'instructions' field")
            return {"error":"Missing 'instructions' field"}
        if not isinstance(task_data["instructions"], str) or not task_data["instructions"].strip():
            logger.debug("AppService.validate_task: 'instructions' empty or non-string")
            return {"error":"instructions cannot be empty or non-string"}

        logger.debug("AppService.validate_task: Validation passed.")
        return None

    def process(self, task_data: dict) -> dict:
        """
        Process app analysis:
        Steps:
        - Validate input.
        - Call app worker: {"worker_type":"app","app_ref":...,"instructions":...}
        - If worker error, return error.
        - If worker completed, get suspicious & analysis from result.
        - Call aggregator LLM to get final JSON with suspicious/reason.
        - Return completed with final result.
        """
        logger.info("AppService.process: Starting process for app task_data=%s", task_data)
        val_error = self.validate_task(task_data)
        if val_error:
            logger.info("AppService.process: Validation failed %s", val_error)
            return {"status":"error","message":val_error["error"]}

        logger.info("AppService.process: Validation succeeded. Calling app worker now.")
        app_payload = {
            "worker_type":"app",
            "app_ref":task_data["app_ref"],
            "instructions":task_data["instructions"]
        }

        try:
            w_resp = requests.post(f"{self.worker_server_url}/request_worker", json=app_payload)
            logger.debug("AppService.process: App worker response code=%s body=%s", w_resp.status_code, w_resp.text)
            if w_resp.status_code != 200:
                logger.warning("AppService.process: App worker HTTP %d error", w_resp.status_code)
                return {"status":"error","message":f"App worker HTTP {w_resp.status_code}"}
            w_data = w_resp.json()
            if w_data.get("status") == "error":
                logger.warning("AppService.process: App worker returned error %s", w_data.get("message"))
                return {"status":"error","message":w_data.get("message","App worker error")}
            if w_data.get("status") != "completed":
                logger.warning("AppService.process: App worker not completed, status=%s", w_data.get("status"))
                return {"status":"error","message":"App worker did not return completed status"}

            worker_result = w_data.get("result")
            logger.debug("AppService.process: App worker completed. result=%s", worker_result)
            if not worker_result or "suspicious" not in worker_result or "analysis" not in worker_result:
                logger.warning("AppService.process: App worker result missing 'suspicious' or 'analysis'")
                return {"status":"error","message":"App worker result missing 'suspicious' or 'analysis'"}
        except requests.RequestException as e:
            logger.exception("AppService.process: Network error calling app worker")
            return {"status":"error","message":f"Net err calling app worker: {str(e)}"}

        # Call aggregator LLM
        prompt = f"Based on this app analysis: {worker_result['analysis']}.\nReturn JSON: {{\"suspicious\":\"yes/no\",\"reason\":\"explain reasoning\"}}"
        logger.info("AppService.process: Calling aggregator LLM with prompt.")
        llm_resp = self._call_llm_for_json(prompt, self.provider_server_url, ["suspicious","reason"])
        if llm_resp.get("status") == "error":
            logger.warning("AppService.process: Aggregator LLM error %s", llm_resp.get("message"))
            return {"status":"error","message":llm_resp.get("message","Aggregator LLM error")}

        final_result = llm_resp["result"]
        logger.info("AppService.process: Aggregator succeeded. final_result=%s", final_result)
        return {"status":"completed","result":final_result}

    def get_metadata(self) -> dict:
        """
        Return metadata for app analysis service.
        """
        return {
            "description": self.description,
            "required_fields":["app_ref","instructions"],
            "worker_types":["app_worker"],
            "example_input":{"app_ref":"test.apk","instructions":"Play this game to check suspicious content."}
        }

    def _call_llm_for_json(self, prompt, base_url, required_keys):
        """
        Similar aggregator call logic as message_service and link_service.
        """
        llm_endpoint = f"{base_url}/llm/chat_complete"
        try:
            logger.debug("AppService._call_llm_for_json: Sending prompt to LLM: %s", prompt)
            llm_resp = requests.post(llm_endpoint, json={"prompt": prompt}, timeout=40)
            logger.debug("AppService._call_llm_for_json: LLM response code=%s body=%s", llm_resp.status_code, llm_resp.text)
            if llm_resp.status_code != 200:
                logger.warning("LLM HTTP error code=%d", llm_resp.status_code)
                return {"status":"error","message":f"LLM HTTP {llm_resp.status_code}"}
            llm_data = llm_resp.json()
            if llm_data.get("status") != "success":
                logger.warning("LLM aggregator not success: %s", llm_data)
                return {"status":"error","message":"LLM aggregator not success"}
            raw = llm_data["response"].strip()
            parsed = self._strict_json_parse(raw, required_keys)
            return parsed
        except requests.RequestException as e:
            logger.exception("AppService._call_llm_for_json: Net error aggregator LLM")
            return {"status":"error","message":f"Net err aggregator LLM: {str(e)}"}

    def _strict_json_parse(self, raw_response, required_keys=[]):
        """
        Parse aggregator LLM response as JSON, fallback to regex if direct parse fails.
        """
        import json
        logger.debug("AppService._strict_json_parse: raw_response=%s", raw_response)
        try:
            parsed = json.loads(raw_response)
            if any(k not in parsed for k in required_keys):
                logger.warning("LLM JSON missing required keys in direct parse")
                return {"status":"error","message":"LLM JSON missing required keys"}
            return {"status":"completed","result":parsed}
        except json.JSONDecodeError:
            logger.debug("AppService._strict_json_parse: direct parse failed, try regex fallback")
            import re
            match = re.search(r'\{.*\}', raw_response, flags=re.DOTALL)
            if match:
                block = match.group(0).strip()
                try:
                    parsed = json.loads(block)
                    if any(k not in parsed for k in required_keys):
                        logger.warning("LLM JSON missing required keys in fallback block")
                        return {"status":"error","message":"LLM JSON missing keys in fallback"}
                    return {"status":"completed","result":parsed}
                except json.JSONDecodeError:
                    logger.warning("LLM fallback block not valid JSON")
                    return {"status":"error","message":"LLM response not valid JSON (fallback attempt)"}
            logger.warning("No valid JSON block found in LLM response.")
            return {"status":"error","message":"LLM response not valid JSON"}
