from worker_definitions.base_worker import BaseWorker
import requests
import json
import re

class TextWorker(BaseWorker):
    ################################################################################
    # Purpose & High-Level Design:
    #
    # The TextWorker:
    # 1. Analyzes the message's overall trustworthiness (Step1_Message_Trust).
    # 2. Identifies links in the message (Step2_Link_Identification).
    # 3. For each found link, calls the link worker to analyze them (Step3_Links_Analysis).
    # 4. Aggregates all results via a final aggregator LLM call, producing a final JSON only 
    #    output with hierarchical 'reasons'.
    #
    # If LLM still fails to produce valid JSON, we have even stricter instructions and fallback parsing.
    #
    # Maintainability:
    # - If aggregator LLM still fails, try different prompt tactics or model features.
    #
    ################################################################################

    def validate_task(self, task_data: dict):
        message = task_data.get("message")
        if not message or not isinstance(message, str) or message.strip() == "":
            return {"error":"missing or empty 'message' field"}
        return None

    def process(self, task_data: dict) -> dict:
        message = task_data["message"]
        mode = self.config.get("mode","local")
        base_url = self.config.get("providers_server_url","http://providers:8003")

        steps_data = {
            "Step1_Message_Trust": [],
            "Step2_Link_Identification": [],
            "Step3_Links_Analysis": []
        }

        # Weights:
        w_message_trust = 0.4
        w_link_id = 0.1
        w_links_total = 0.5  # sum for all links

        ################################################################################
        # Step 1: Message Trust Analysis
        ################################################################################
        check_1_A = {
            "check_id":"check_1_A",
            "analysis_agent":"LLM_message_trust_analyzer",
            "weight":w_message_trust,
            "risk_level":"low",
            "confidence":0.5,
            "explanation":"Analyze overall message trust"
        }

        trust_res = self._call_llm_for_json(
            prompt=(
                "Analyze the entire message for trustworthiness. Return ONLY JSON:\n"
                "{\"risk_level\":\"high|low\",\"confidence\":float,\"reason\":\"...\"}\n"
                "No extra text.\n"
                f"Message:\n{message}"
            ),
            base_url=base_url,
            required_keys=["risk_level","confidence","reason"]
        )
        if trust_res["status"] == "error":
            return trust_res
        tr = trust_res["result"]
        check_1_A["risk_level"] = tr["risk_level"]
        check_1_A["confidence"] = tr["confidence"]
        check_1_A["explanation"] = tr["reason"]
        steps_data["Step1_Message_Trust"].append(check_1_A)

        ################################################################################
        # Step 2: Link Identification
        ################################################################################
        check_2_A = {
            "check_id":"check_2_A",
            "analysis_agent":"LLM_link_identifier",
            "weight":w_link_id,
            "risk_level":"low",
            "confidence":0.5,
            "explanation":"Identify links in message"
        }

        link_id_res = self._call_llm_for_json(
            prompt=(
                "Identify all links in the message. Return ONLY JSON:\n"
                "{\"links\":[\"http://...\"],\"reason\":\"...\"}\n"
                "No extra text. If no links, links=[].\n"
                f"Message:\n{message}"
            ),
            base_url=base_url,
            required_keys=["links","reason"]
        )
        if link_id_res["status"] == "error":
            return link_id_res
        li = link_id_res["result"]
        links_found = li["links"]
        check_2_A["risk_level"] = "low"
        check_2_A["confidence"] = 0.6 if links_found else 0.7
        check_2_A["explanation"] = li["reason"]
        steps_data["Step2_Link_Identification"].append(check_2_A)

        ################################################################################
        # Step 3: Links Analysis (if any links)
        ################################################################################
        if links_found:
            per_link_weight = w_links_total / len(links_found)
            for link_url in links_found:
                link_check_id = f"check_3_link_{link_url.replace('http','').replace('/','_')}"
                link_req_body = {"worker_type":"link","url":link_url}
                try:
                    lw_resp = requests.post("http://localhost:8002/request_worker", json=link_req_body, timeout=30)
                    if lw_resp.status_code != 200:
                        steps_data["Step3_Links_Analysis"].append({
                            "check_id":link_check_id,
                            "analysis_agent":"link_worker",
                            "weight":per_link_weight,
                            "risk_level":"high",
                            "confidence":1.0,
                            "explanation":f"Link worker returned {lw_resp.status_code}, suspicious."
                        })
                        continue
                    lw_data = lw_resp.json()
                    if lw_data.get("status") != "completed":
                        steps_data["Step3_Links_Analysis"].append({
                            "check_id":link_check_id,
                            "analysis_agent":"link_worker",
                            "weight":per_link_weight,
                            "risk_level":"high",
                            "confidence":1.0,
                            "explanation":f"Link worker not completed: {lw_data.get('message','unknown error')}"
                        })
                        continue
                    res = lw_data.get("result",{})
                    lrisk = res.get("risk_level","low")
                    lconf = float(res.get("confidence",0.5))
                    steps_data["Step3_Links_Analysis"].append({
                        "check_id":link_check_id,
                        "analysis_agent":"link_worker",
                        "weight":per_link_weight,
                        "risk_level":lrisk,
                        "confidence":lconf,
                        "explanation":f"Link worker final risk={lrisk}, conf={lconf}"
                    })
                except requests.RequestException as e:
                    steps_data["Step3_Links_Analysis"].append({
                        "check_id":link_check_id,
                        "analysis_agent":"link_worker",
                        "weight":per_link_weight,
                        "risk_level":"high",
                        "confidence":1.0,
                        "explanation":f"Network error calling link worker: {str(e)}"
                    })
        else:
            steps_data["Step3_Links_Analysis"].append({
                "check_id":"check_3_no_links",
                "analysis_agent":"link_analyzer",
                "weight":0.0,
                "risk_level":"low",
                "confidence":0.5,
                "explanation":"No links to analyze."
            })

        ################################################################################
        # Final Aggregator Call:
        #
        # Very strict instructions:
        # We use triple backticks and a final warning:
        # "If you add ANY extra text outside the JSON, or fail keys, we consider it invalid."
        ################################################################################

        aggregator_prompt = (
            "You have a hierarchical steps_data with checks. Produce final JSON ONLY:\n"
            "```\n"
            "{\n"
            "\"risk_level\":\"high|low\",\n"
            "\"confidence\":float,\n"
            "\"reasons\":{\n"
            "  \"Step1_Message_Trust\":[...],\n"
            "  \"Step2_Link_Identification\":[...],\n"
            "  \"Step3_Links_Analysis\":[...]\n"
            "}\n"
            "}\n"
            "```\n"
            "No extra text. If any word outside JSON braces, invalid.\n"
            "risk_level: high if any check high else low.\n"
            "confidence: weighted avg of all checks.\n"
            "Include all checks from steps_data unchanged inside 'reasons'.\n"
            f"{json.dumps(steps_data)}"
        )

        final_res = self._call_llm_for_json(aggregator_prompt, base_url, required_keys=["risk_level","confidence","reasons"])
        return final_res if final_res["status"] == "error" else {"status":"completed","result":final_res["result"]}

    def get_metadata(self) -> dict:
        return {
            "description": ("Analyzes a text message: message trust check, identifies links, "
                            "analyzes each link via link_worker, then aggregates final results "
                            "in a hierarchical JSON-only output."),
            "required_fields": ["message"],
            "mode": self.config.get("mode","local"),
            "capabilities": [
                "message trust analysis",
                "link identification",
                "link analysis integration",
                "final hierarchical aggregator with strict JSON"
            ]
        }

    ################################################################################
    # Helper Methods
    ################################################################################
    def _call_llm_for_json(self, prompt: str, base_url: str, required_keys: list) -> dict:
        llm_endpoint = f"{base_url}/llm/chat_complete"
        try:
            llm_resp = requests.post(llm_endpoint, json={"prompt":prompt}, timeout=20)
            if llm_resp.status_code != 200:
                return {"status":"error","message":f"LLM returned {llm_resp.status_code}"}
            llm_data = llm_resp.json()
            if llm_data.get("status") != "success":
                return {"status":"error","message":"LLM not success"}

            raw_response = llm_data["response"].strip()
            parsed = self._strict_json_parse(raw_response, required_keys=required_keys)
            return parsed
        except requests.RequestException as e:
            return {"status":"error","message":f"Network error calling LLM: {str(e)}"}

    def _strict_json_parse(self, raw_response: str, required_keys=[]) -> dict:
        """
        Attempt strict json parsing.
        If fail, try regex to find first {...} block.
        Check required keys.
        """
        try:
            parsed = json.loads(raw_response)
            if any(k not in parsed for k in required_keys):
                return {"status":"error","message":"LLM JSON missing keys"}
            return {"status":"completed","result":parsed}
        except json.JSONDecodeError:
            # fallback
            match = re.search(r'\{.*\}', raw_response, flags=re.DOTALL)
            if match:
                block = match.group(0).strip()
                try:
                    parsed = json.loads(block)
                    if any(k not in parsed for k in required_keys):
                        return {"status":"error","message":"LLM JSON missing keys"}
                    return {"status":"completed","result":parsed}
                except json.JSONDecodeError:
                    return {"status":"error","message":"LLM response not valid JSON (fallback failed)"}
            return {"status":"error","message":"LLM response not valid JSON"}

###############################################################################
# Example curl:
# curl -X POST -H "Content-Type: application/json" \
# -d '{"worker_type":"text","message":"Check this out! http://example.com/malicious"}' \
# http://localhost:8002/request_worker
#
# If aggregator fails or LLM returns invalid JSON, you see an error.
# If success, final JSON includes hierarchical reasons and final risk.
#
###############################################################################
