###############################################################################
# message_service.py
#
# Purpose:
# The MessageService class implements the logic for analyzing textual messages
# for phishing/spam patterns. It uses a text worker and then an aggregator LLM.
#
# Changes Made:
# - Adjusted the worker payload to use "message" instead of "content" to match 
#   the worker subsystem's expected input format.
#
# Steps (unchanged):
# 1. Validate input ("message").
# 2. Call the text worker with {"worker_type":"text","message":task_data["message"]}.
# 3. If worker returns completed status and a result, call aggregator LLM with a prompt.
# 4. Parse aggregator JSON for "suspicious" and "reason".
# 5. Return {"status":"completed","result":{"suspicious":"...","reason":"..."}} or {"status":"error","message":"..."}.
#
# Logging & Maintainability:
# - Log all steps for debugging.
# - If aggregator or worker fail, logs show where.
#
###############################################################################

import json
import re
import requests
import logging
from typing import Optional, Dict
from .base_service import BaseService

logger = logging.getLogger("services")

class MessageService(BaseService):
    def __init__(self, config: dict):
        """
        Initialize MessageService.
        
        Expects config with:
        - WORKER_SERVER_URL (default http://workers:8001)
        - PROVIDER_SERVER_URL (default http://providers:8003)
        """
        self.config = config
        self.description = "Analyze textual messages for phishing/spam patterns and produce a suspicious yes/no final result."
        self.worker_server_url = self.config.get("WORKER_SERVER_URL", "http://workers:8001")
        self.provider_server_url = self.config.get("PROVIDER_SERVER_URL", "http://providers:8003")

    def validate_task(self, task_data: dict) -> Optional[dict]:
        logger.info("MessageService.validate_task: Validating input %s", task_data)
        if "message" not in task_data:
            logger.info("MessageService.validate_task: Missing 'message' field")
            return {"error": "Missing 'message' field"}
        if not isinstance(task_data["message"], str) or not task_data["message"].strip():
            logger.info("MessageService.validate_task: 'message' is empty or non-string")
            return {"error": "message cannot be empty or non-string"}
        logger.info("MessageService.validate_task: Validation passed.")
        return None

    def process(self, task_data: dict) -> dict:
        """
        Perform message analysis:
        Steps:
        - Validate input.
        - Call text worker: {"worker_type":"text","message":task_data["message"]}.
        - If worker error, return error.
        - If completed, get worker_result {"suspicious":"yes/no","analysis":"..."}.
        - Call aggregator LLM to format final JSON with "suspicious" & "reason".
        - Return completed with final_result.
        """
        logger.info("MessageService.process: Starting process for message task_data=%s", task_data)
        val_error = self.validate_task(task_data)
        if val_error:
            logger.info("MessageService.process: Validation failed with error=%s", val_error)
            return {"status":"error","message": val_error["error"]}

        logger.info("MessageService.process: Validation succeeded. Calling text worker now.")
        # Call text worker with correct params
        text_payload = {"worker_type": "text", "message": task_data["message"]}
        try:
            w_resp = requests.post(f"{self.worker_server_url}/request_worker", json=text_payload, timeout=60)
            if w_resp.status_code != 200:
                logger.warning("MessageService.process: Text worker HTTP %d error", w_resp.status_code)
                return {"status":"error","message":f"Text worker HTTP {w_resp.status_code}"}
            w_data = w_resp.json()
            if w_data.get("status") == "error":
                logger.warning("MessageService.process: Text worker returned error %s", w_data.get("message"))
                return {"status":"error","message":w_data.get("message","Text worker error")}
            if w_data.get("status") != "completed":
                logger.warning("MessageService.process: Text worker not completed, status=%s", w_data.get("status"))
                return {"status":"error","message":"Text worker did not return completed status"}

            worker_result = w_data.get("result")

        except requests.RequestException as e:
            logger.exception("MessageService.process: Network error calling text worker")
            return {"status":"error","message":f"Net err calling text worker: {str(e)}"}

        # Call aggregator LLM:
        prompt = f"Based on this analysis: {worker_result}.\nReturn JSON: {{\"suspicious\":\"yes/no\",\"reason\":\"explain reasoning\"}}. Be Strict and carefully look at the content. No extra text. If any word outside JSON braces, invalid. Return ONLY JSON."
        logger.info("MessageService.process: Calling aggregator LLM with prompt.")
        llm_resp = self._call_llm_for_json(prompt, self.provider_server_url, ["suspicious","reason"])
        if llm_resp.get("status") == "error":
            logger.warning("MessageService.process: Aggregator LLM error %s", llm_resp.get("message"))
            return {"status":"error","message":llm_resp.get("message","Aggregator LLM error")}

        final_result = llm_resp["result"]
        final_result["worker_analysis"] = worker_result
        logger.info("MessageService.process: Aggregator succeeded. final_result=%s", final_result)
        # final_result: {"suspicious":"...","reason":"..."}
        return {"status":"completed","result":final_result}

    def get_metadata(self) -> dict:
        """
        Return metadata about this service.
        """
        return {
            "description": self.description,
            "required_fields": ["message"],
            "worker_types": ["text_worker"],
            "example_input": {"message": "Check out this suspicious link"}
        }

    def _call_llm_for_json(self, prompt, base_url, required_keys):
        """
        Call aggregator LLM endpoint with given prompt.

        On success: {"status":"completed","result":parsed_dict}
        On error: {"status":"error","message":"..."}
        """
        llm_endpoint = f"{base_url}/llm/chat_complete"
        json_max_retries = 3
        for i in range(json_max_retries):
            try:
                logger.info("MessageService._call_llm_for_json: Sending prompt to LLM: %s", prompt)
                llm_resp = requests.post(llm_endpoint, json={"prompt": prompt}, timeout=20)
                logger.info("MessageService._call_llm_for_json: LLM response code=%s body=%s", llm_resp.status_code, llm_resp.text)
                if llm_resp.status_code != 200:
                    logger.warning("LLM HTTP error code=%d", llm_resp.status_code)
                    return {"status":"error","message":f"LLM HTTP {llm_resp.status_code}"}
                llm_data = llm_resp.json()
                if llm_data.get("status") != "success":
                    logger.warning("LLM aggregator not success: %s", llm_data)
                    return {"status":"error","message":"LLM aggregator not success"}
                raw = llm_data["response"].strip()
                parsed = self._strict_json_parse(raw, required_keys)

                if "error" in parsed["status"]:
                    logger.warning("MessageService._call_llm_for_json: LLM error %s, retrying... (%d/%d)", parsed["message"], i+1, json_max_retries)
                    continue
                logger.debug("MessageService._call_llm_for_json: Successfully parsed JSON: %s", parsed)
                return parsed
            except requests.RequestException as e:
                if i < json_max_retries:
                    logger.info("MessageService._call_llm_for_json: Net error aggregator LLM, retrying... (%d/%d)", i+1, json_max_retries)
                    continue
                else:
                    logger.exception("MessageService._call_llm_for_json: Net error aggregator LLM")
                    return {"status":"error","message":f"Net err aggregator LLM: {str(e)}"}

    def _strict_json_parse(self, raw_response, required_keys=[]):
        """
        Parse raw_response as JSON. If fail, try regex block extraction.
        Check required keys.

        Return:
        {"status":"completed","result":parsed} or {"status":"error","message":"..."}
        """
        import json
        logger.info("MessageService._strict_json_parse: raw_response=%s", raw_response)
        try:
            parsed = json.loads(raw_response)
            if any(k not in parsed for k in required_keys):
                logger.warning("LLM JSON missing required keys in direct parse")
                return {"status":"error","message":"LLM JSON missing required keys"}
            return {"status":"completed","result":parsed}
        except json.JSONDecodeError:
            logger.info("MessageService._strict_json_parse: direct parse failed, try regex")
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
