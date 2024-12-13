###############################################################################
# link_service.py
#
# Purpose:
# The LinkService class implements logic for analyzing URLs for malicious content.
# Similar to message_service, it:
# 1. Validates input ("url" field).
# 2. Calls the link worker with {"worker_type":"link","url":"..."}.
# 3. If worker returns error or non-200 HTTP, we set status=error.
# 4. If worker completes, we get {"suspicious":"yes/no","analysis":"..."} from worker_result.
# 5. Call aggregator LLM to produce a standardized final JSON:
#    {"suspicious":"yes/no","reason":"..."}
# 6. Return completed with that final result.
#
# Logging & Maintainability:
# - Extensive logs at each step for debugging.
# - If aggregator or worker logic changes, update fields and prompts here.
#
# Testing:
# - Similar to message_service testing. We'll provide instructions after the code.
###############################################################################

import json
import re
import requests
import logging
from typing import Optional, Dict
from .base_service import BaseService

logger = logging.getLogger("services")

class LinkService(BaseService):
    def __init__(self, config: dict):
        """
        Initialize LinkService.

        Expects config:
        - WORKER_SERVER_URL (default: http://workers:8001)
        - PROVIDER_SERVER_URL (default: http://providers:8003)
        """
        self.config = config
        self.description = "Analyze a URL for malicious behavior and produce suspicious yes/no result."
        self.worker_server_url = self.config.get("WORKER_SERVER_URL", "http://workers:8001")
        self.provider_server_url = self.config.get("PROVIDER_SERVER_URL", "http://providers:8003")

    def validate_task(self, task_data: dict) -> Optional[dict]:
        logger.debug("LinkService.validate_task: Validating input %s", task_data)
        if "url" not in task_data:
            logger.debug("LinkService.validate_task: Missing 'url' field")
            return {"error": "Missing 'url' field"}
        if not isinstance(task_data["url"], str) or not task_data["url"].strip():
            logger.debug("LinkService.validate_task: 'url' is empty or non-string")
            return {"error": "url cannot be empty or non-string"}
        # Optionally check if url starts with http:// or https://
        # if not (task_data["url"].startswith("http://") or task_data["url"].startswith("https://")):
        #     return {"error":"url must start with http:// or https://"}
        logger.debug("LinkService.validate_task: Validation passed.")
        return None

    def process(self, task_data: dict) -> dict:
        """
        Process link analysis:
        Steps:
        - Validate input
        - Call link worker: {"worker_type":"link","url":task_data["url"]}
        - If worker error, return error.
        - If success, get worker_result with suspicious & analysis.
        - Call aggregator LLM with a prompt to produce final JSON.
        - Return completed with final suspicious/reason.

        Returns:
        - {"status":"completed","result":{"suspicious":"...","reason":"..."}}
        or {"status":"error","message":"..."} if something fails.
        """
        logger.info("LinkService.process: Starting process for link task_data=%s", task_data)
        val_error = self.validate_task(task_data)
        if val_error:
            logger.info("LinkService.process: Validation failed %s", val_error)
            return {"status":"error","message":val_error["error"]}

        logger.info("LinkService.process: Validation succeeded. Calling link worker now.")
        link_payload = {"worker_type":"link","url":task_data["url"]}
        try:
            w_resp = requests.post(f"{self.worker_server_url}/request_worker", json=link_payload, timeout=10)
            logger.debug("LinkService.process: Link worker response code=%s body=%s", w_resp.status_code, w_resp.text)
            if w_resp.status_code != 200:
                logger.warning("LinkService.process: Link worker HTTP %d error", w_resp.status_code)
                return {"status":"error","message":f"Link worker HTTP {w_resp.status_code}"}
            w_data = w_resp.json()
            if w_data.get("status") == "error":
                logger.warning("LinkService.process: Link worker returned error %s", w_data.get("message"))
                return {"status":"error","message":w_data.get("message","Link worker error")}
            if w_data.get("status") != "completed":
                logger.warning("LinkService.process: Link worker not completed, status=%s", w_data.get("status"))
                return {"status":"error","message":"Link worker did not return completed status"}

            worker_result = w_data.get("result")

        except requests.RequestException as e:
            logger.exception("LinkService.process: Network error calling link worker")
            return {"status":"error","message":f"Net err calling link worker: {str(e)}"}

        # Call aggregator LLM:
        prompt = f"Based on this link analysis: {worker_result}.\nReturn JSON: {{\"suspicious\":\"yes/no\",\"reason\":\"explain reasoning\"}}. Be Strict and carefully look at the content. No extra text. If any word outside JSON braces, invalid. Return ONLY JSON."
        logger.info("LinkService.process: Calling aggregator LLM with prompt.")
        llm_resp = self._call_llm_for_json(prompt, self.provider_server_url, ["suspicious","reason"])
        if llm_resp.get("status") == "error":
            logger.warning("LinkService.process: Aggregator LLM error %s", llm_resp.get("message"))
            return {"status":"error","message":llm_resp.get("message","Aggregator LLM error")}

        final_result = llm_resp["result"]
        final_result["worker_analysis"] = worker_result
        logger.info("LinkService.process: Aggregator succeeded. final_result=%s", final_result)
        return {"status":"completed","result":final_result}

    def get_metadata(self) -> dict:
        """
        Return metadata for link analysis service.
        """
        return {
            "description": self.description,
            "required_fields": ["url"],
            "worker_types": ["link_worker"],
            "example_input": {"url":"http://example.com/malicious"}
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
                logger.info("LinkService._call_llm_for_json: Sending prompt to LLM: %s", prompt)
                llm_resp = requests.post(llm_endpoint, json={"prompt": prompt}, timeout=20)
                logger.info("LinkService._call_llm_for_json: LLM response code=%s body=%s", llm_resp.status_code, llm_resp.text)
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
                    logger.warning("LinkService._call_llm_for_json: LLM error %s, retrying... (%d/%d)", parsed["message"], i+1, json_max_retries)
                    continue
                logger.debug("LinkService._call_llm_for_json: Successfully parsed JSON: %s", parsed)
                return parsed
            except requests.RequestException as e:
                if i < json_max_retries:
                    logger.info("LinkService._call_llm_for_json: Net error aggregator LLM, retrying... (%d/%d)", i+1, json_max_retries)
                    continue
                else:
                    logger.exception("LinkService._call_llm_for_json: Net error aggregator LLM")
                    return {"status":"error","message":f"Net err aggregator LLM: {str(e)}"}
    def _strict_json_parse(self, raw_response, required_keys=[]):
        """
        Parse aggregator LLM response as JSON, fallback to regex block if direct parse fails.
        """
        import json
        logger.debug("LinkService._strict_json_parse: raw_response=%s", raw_response)
        try:
            parsed = json.loads(raw_response)
            if any(k not in parsed for k in required_keys):
                logger.warning("LLM JSON missing required keys in direct parse")
                return {"status":"error","message":"LLM JSON missing required keys"}
            return {"status":"completed","result":parsed}
        except json.JSONDecodeError:
            logger.debug("LinkService._strict_json_parse: direct parse failed, try regex fallback")
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
