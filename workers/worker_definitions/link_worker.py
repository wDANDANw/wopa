from worker_definitions.base_worker import BaseWorker
import requests
from bs4 import BeautifulSoup
import json
import re

class LinkWorker(BaseWorker):
    ################################################################################
    # Purpose & High-Level Design:
    #
    # This worker:
    #  - Fetches main page and scripts
    #  - Analyzes each content piece via LLM (JSON-only)
    #  - Sandbox analysis
    #  - Aggregator LLM call: produce final JSON with "risk_level","confidence","reasons"
    #
    # If aggregator returns missing keys, we now:
    #   1. Strict instructions with multiple examples and no extraneous text.
    #   2. If still fails, fallback attempt: regex search for a JSON block and parse again.
    #
    # Maintainability:
    # - If still failing, consider instructing LLM to use a special "role" or say "If you add extra text, you fail".
    #
    ################################################################################

    def validate_task(self, task_data: dict):
        url = task_data.get("url")
        if not url or not isinstance(url, str) or url.strip() == "":
            return {"error":"missing or empty 'url' field"}
        return None

    def process(self, task_data: dict) -> dict:
        url = task_data["url"]
        mode = self.config.get("mode","local")
        base_url = self.config.get("providers_server_url","http://providers:8003")

        steps_data = {
            "Step1_Page_Accessibility": [],
            "Step2_Content_Analysis": [],
            "Step3_Sandbox": []
        }

        w_page = 0.3
        w_main_html = 0.3
        # scripts total 0.2, sandbox 0.2

        main_html = None
        main_page_fetched = False

        ################################################################################
        # Step 1: Page Accessibility
        ################################################################################
        check_1_A = {
            "check_id":"check_1_A",
            "analysis_agent":"page_accessibility_checker",
            "weight":w_page,
            "risk_level":"low",
            "confidence":0.5,
            "explanation":"Attempt to fetch main page"
        }

        try:
            page_resp = requests.get(url, timeout=10)
            if page_resp.status_code == 200:
                main_html = page_resp.text
                main_page_fetched = True
                check_1_A["risk_level"] = "low"
                check_1_A["confidence"] = 0.7
                check_1_A["explanation"] += " - Page fetched (200)."
            else:
                check_1_A["risk_level"] = "high"
                check_1_A["confidence"] = 1.0
                check_1_A["explanation"] += f" - Failed status={page_resp.status_code}, suspicious."
        except requests.RequestException as e:
            check_1_A["risk_level"] = "high"
            check_1_A["confidence"] = 1.0
            check_1_A["explanation"] += f" - Network error: {str(e)}, suspicious."

        steps_data["Step1_Page_Accessibility"].append(check_1_A)

        ################################################################################
        # Step 2: Content Analysis (HTML & scripts)
        ################################################################################
        script_contents = []
        if main_page_fetched:
            from urllib.parse import urljoin
            soup = BeautifulSoup(main_html, 'html.parser')
            script_urls = [ urljoin(url, s['src']) for s in soup.find_all('script', src=True) ]

            for s_url in script_urls:
                try:
                    s_resp = requests.get(s_url, timeout=10)
                    if s_resp.status_code == 200:
                        script_contents.append((s_url, s_resp.text))
                    else:
                        steps_data["Step2_Content_Analysis"].append({
                            "check_id":"check_2_script_fetch",
                            "analysis_agent":"script_fetcher",
                            "weight":0.05,
                            "risk_level":"low",
                            "confidence":0.5,
                            "explanation":f"Script {s_url} fetch {s_resp.status_code}, ignored."
                        })
                except requests.RequestException:
                    steps_data["Step2_Content_Analysis"].append({
                        "check_id":"check_2_script_fetch",
                        "analysis_agent":"script_fetcher",
                        "weight":0.05,
                        "risk_level":"low",
                        "confidence":0.5,
                        "explanation":f"Network error fetching script {s_url}, ignored."
                    })
        else:
            steps_data["Step2_Content_Analysis"].append({
                "check_id":"check_2_no_main_html",
                "analysis_agent":"html_parser",
                "weight":0.1,
                "risk_level":"high",
                "confidence":0.6,
                "explanation":"No main HTML, can't parse scripts, suspicious."
            })

        def call_llm_analysis(content_text: str, source_name: str) -> dict:
            prompt = (
                "Analyze content and return ONLY valid JSON:\n"
                "{\"risk_level\":\"high|low\",\"confidence\":float,\"reason\":\"...\"}\n"
                "No extra text.\n"
                f"Source: {source_name}\n"
                f"Content:\n{content_text}\n"
            )
            llm_endpoint = f"{base_url}/llm/chat_complete"
            try:
                llm_resp = requests.post(llm_endpoint, json={"prompt":prompt}, timeout=20)
                if llm_resp.status_code != 200:
                    return {"status":"error","message":f"LLM returned {llm_resp.status_code}"}
                llm_data = llm_resp.json()
                if llm_data.get("status") != "success":
                    return {"status":"error","message":"LLM not success"}

                raw_response = llm_data["response"].strip()
                parsed = self._strict_json_parse(raw_response, required_keys=["risk_level","confidence","reason"])
                if parsed["status"] == "error":
                    return parsed
                return {"status":"completed","result":parsed["result"]}
            except requests.RequestException as e:
                return {"status":"error","message":f"Network error calling LLM: {str(e)}"}

        # main HTML analysis
        main_html_text = main_html if main_html else "No main HTML."
        main_res = call_llm_analysis(main_html_text, "main_html")
        if main_res["status"] == "error":
            return main_res
        mh = main_res["result"]
        steps_data["Step2_Content_Analysis"].append({
            "check_id":"check_2_main_html_llm",
            "analysis_agent":"LLM_html_analyzer",
            "weight":0.3,
            "risk_level":mh["risk_level"],
            "confidence":mh["confidence"],
            "explanation":mh["reason"]
        })

        script_llm_weight = 0.2 / (len(script_contents) if script_contents else 1)
        for (src_name, stext) in script_contents:
            sres = call_llm_analysis(stext, src_name)
            if sres["status"] == "error":
                return sres
            sr = sres["result"]
            steps_data["Step2_Content_Analysis"].append({
                "check_id":"check_2_script_llm",
                "analysis_agent":"LLM_script_analyzer",
                "weight":script_llm_weight,
                "risk_level":sr["risk_level"],
                "confidence":sr["confidence"],
                "explanation":sr["reason"]
            })

        ################################################################################
        # Step 3: Sandbox
        ################################################################################
        sandbox_endpoint = f"{base_url}/sandbox/analyze_link"
        try:
            sb_resp = requests.get(sandbox_endpoint, params={"url":url}, timeout=10)
            if sb_resp.status_code == 200:
                sb_data = sb_resp.json()
                sb_susp = sb_data.get("suspicious",False)
                steps_data["Step3_Sandbox"].append({
                    "check_id":"check_3_sandbox",
                    "analysis_agent":"sandbox_analyzer",
                    "weight":0.2,
                    "risk_level":"high" if sb_susp else "low",
                    "confidence":0.6 if sb_susp else 0.5,
                    "explanation": sb_data.get("details","No details")
                })
            else:
                steps_data["Step3_Sandbox"].append({
                    "check_id":"check_3_sandbox",
                    "analysis_agent":"sandbox_analyzer",
                    "weight":0.2,
                    "risk_level":"low",
                    "confidence":0.5,
                    "explanation": f"Sandbox returned {sb_resp.status_code}, ignoring."
                })
        except requests.RequestException:
            steps_data["Step3_Sandbox"].append({
                "check_id":"check_3_sandbox",
                "analysis_agent":"sandbox_analyzer",
                "weight":0.2,
                "risk_level":"low",
                "confidence":0.5,
                "explanation":"Sandbox call failed, ignoring."
            })

        ################################################################################
        # Final aggregator call
        ################################################################################
        def call_final_aggregator(steps_data):
            aggregator_prompt = (
                "You have a hierarchical set of analysis steps and checks for a URL.\n"
                "Produce final JSON ONLY, no extra text:\n"
                "{\"risk_level\":\"high|low\",\"confidence\":float,\"reasons\":{\"Step1_Page_Accessibility\":[...],\"Step2_Content_Analysis\":[...],\"Step3_Sandbox\":[...]}}\n"
                "No extra text outside JSON.\n"
                "Keys required: risk_level, confidence, reasons. reasons is exactly the steps_data structure.\n"
                "Decide final risk_level: if any check high, final=high else low.\n"
                "Compute confidence by weighted avg of all checks (sum of (confidence*weight))/sum(weights).\n"
                "Include all given checks in reasons unchanged.\n"
                "No mention 'Example', no extra commentary.\n"
                f"{json.dumps(steps_data)}"
            )

            llm_endpoint = f"{base_url}/llm/chat_complete"
            try:
                llm_resp = requests.post(llm_endpoint, json={"prompt":aggregator_prompt}, timeout=20)
                if llm_resp.status_code != 200:
                    return {"status":"error","message":f"Aggregator LLM {llm_resp.status_code}"}
                llm_data = llm_resp.json()
                if llm_data.get("status") != "success":
                    return {"status":"error","message":"Aggregator not success"}

                raw_response = llm_data["response"].strip()
                parsed = self._strict_json_parse(raw_response, required_keys=["risk_level","confidence","reasons"])
                return parsed
            except requests.RequestException as e:
                return {"status":"error","message":f"Network error calling aggregator LLM: {str(e)}"}

        final_res = call_final_aggregator(steps_data)
        if final_res["status"] == "error":
            return final_res

        return {
            "status":"completed",
            "result": final_res["result"]
        }

    def get_metadata(self) -> dict:
        return {
            "description": ("Analyzes URL with multiple steps, final aggregator LLM call for a structured hierarchical JSON result."),
            "required_fields": ["url"],
            "mode": self.config.get("mode","local"),
            "capabilities": [
                "multi-step analysis",
                "hierarchical reasons",
                "final aggregator llm call",
                "strict JSON-only responses"
            ]
        }

    def _strict_json_parse(self, raw_response: str, required_keys=[]) -> dict:
        """
        _strict_json_parse(raw_response, required_keys)
        Attempt to parse strictly as JSON. If fails, try regex to extract first {…} block.

        required_keys: keys that must exist in parsed JSON.

        Returns:
          {"status":"completed","result":parsed} on success
          {"status":"error","message":"..."} on failure
        """
        try:
            parsed = json.loads(raw_response)
            if any(k not in parsed for k in required_keys):
                return {"status":"error","message":"LLM JSON missing keys"}
            return {"status":"completed","result":parsed}
        except json.JSONDecodeError:
            # Try fallback: find first {...} block with regex
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
