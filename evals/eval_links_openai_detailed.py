import os
import sys
import json
import re
import time
from datetime import datetime
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from openai import OpenAI

###############################################################################
# Configuration
###############################################################################
# Insert your OpenAI API key here
API_KEY = os.environ.get("OPENAI_API_KEY")
# Initialize the OpenAI client
client = OpenAI(api_key=API_KEY)

MODEL_NAME = "gpt-4o-mini"
DATASET_FILE = "phishing.csv"
OUTPUT_DIR = "./outputs_link_openai_detailed"

START_INDEX = 0
END_INDEX = 10

###############################################################################
# JSON Schemas
###############################################################################
CONTENT_ANALYSIS_SCHEMA = {
    "name": "content_analysis_schema",
    "schema": {
        "type": "object",
        "properties": {
            "risk_level": {"type": "string", "enum": ["high","low"]},
            "confidence": {"type": "number"},
            "reason": {"type": "string"}
        },
        "required": ["risk_level","confidence","reason"],
        "additionalProperties": False
    }
}

LINK_SUSPICIOUSNESS_SCHEMA = {
    "name": "link_susp_schema",
    "schema": {
        "type": "object",
        "properties": {
            "risk_level": {"type": "string", "enum":["high","low"]},
            "confidence": {"type":"number"},
            "reason": {"type":"string"}
        },
        "required":["risk_level","confidence","reason"],
        "additionalProperties":False
    }
}

AGGREGATOR_SCHEMA = {
    "name": "link_aggregator_schema",
    "schema": {
        "type":"object",
        "properties":{
            "risk_level":{"type":"string","enum":["high","low"]},
            "confidence":{"type":"number"},
            "reasons":{
                "type":"object",
                "properties":{
                    "Step1_Page_Accessibility":{
                        "type":"array",
                        "items":{"type":"object"}
                    },
                    "Step2_Content_Analysis":{
                        "type":"array",
                        "items":{"type":"object"}
                    },
                    "Step3_LLM_Link_Suspiciousness":{
                        "type":"array",
                        "items":{"type":"object"}
                    }
                },
                "required":["Step1_Page_Accessibility","Step2_Content_Analysis","Step3_LLM_Link_Suspiciousness"],
                "additionalProperties":False
            }
        },
        "required":["risk_level","confidence","reasons"],
        "additionalProperties":False
    }
}

###############################################################################
# Helper Functions
###############################################################################

def call_model(prompt: str, schema: dict):
    """
    Call the OpenAI model with given prompt and a JSON schema response_format.
    Returns a Python dict already validated.
    """

    MAX_TOKENS = 120000
    prompt_trim = prompt[:MAX_TOKENS]

    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a professional security expert. Return ONLY the requested JSON."},
            {"role":"user","content":prompt_trim}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": schema
        }
    )

    # The content should be directly valid JSON. Load it into Python dict.
    # response_format ensures the returned content is JSON and validated.
    # completion.choices[0].message.content is guaranteed to be JSON per schema.
    return json.loads(completion.choices[0].message.content)

def analyze_content(content_text: str, source_name: str) -> dict:
    prompt = (
        "Analyze the given content and return ONLY JSON:\n"
        "{\"risk_level\":\"high|low\",\"confidence\":float,\"reason\":\"...\"}\n"
        f"Source: {source_name}\n"
        f"Content:\n{content_text}\n"
        "No extra text."
    )
    return call_model(prompt, CONTENT_ANALYSIS_SCHEMA)

def analyze_link_suspiciousness(url: str) -> dict:
    prompt = (
        "Analyze the given URL for suspiciousness. Return ONLY JSON:\n"
        "{\"risk_level\":\"high|low\",\"confidence\":float,\"reason\":\"...\"}\n"
        f"URL:\n{url}\n"
        "No extra text."
    )
    return call_model(prompt, LINK_SUSPICIOUSNESS_SCHEMA)

def process_link(url: str, file_name: str) -> dict:

    log_path = os.path.join(OUTPUT_DIR, file_name)
    with open(log_path, "w", encoding="utf-8", errors='replace') as f:

        steps_data = {
            "Step1_Page_Accessibility": [],
            "Step2_Content_Analysis": [],
            "Step3_LLM_Link_Suspiciousness": []
        }

        w_page = 0.3
        # w_main_html = 0.3 (not explicitly needed here)
        # scripts total = 0.2
        # direct link suspiciousness step weight = 0.5

        check_1_A = {
            "check_id":"check_1_A",
            "analysis_agent":"page_accessibility_checker",
            "weight":w_page,
            "risk_level":"low",
            "confidence":0.5,
            "explanation":"Attempt to fetch main page"
        }

        main_html = None
        main_page_fetched = False

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
        f.write(f"[STEP 1] Page Accessibility Checker: {check_1_A}\n")
        f.write("\n\n************************************************\n\n")

        script_contents = []
        if main_page_fetched:
            soup = BeautifulSoup(main_html, 'html.parser')
            script_urls = [ urljoin(url, s['src']) for s in soup.find_all('script', src=True) ]

            f.write(f"[INFO] Found script URLs: {script_urls}\n")

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
                except requests.RequestException as e:
                    steps_data["Step2_Content_Analysis"].append({
                        "check_id":"check_2_script_fetch",
                        "analysis_agent":"script_fetcher",
                        "weight":0.05,
                        "risk_level":"low",
                        "confidence":0.5,
                        "explanation":f"Network error fetching script {s_url}, ignored. Err: {e}"
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

        main_html_text = main_html if main_html else "No main HTML."
        f.write(f"[STEP 2] Content Analysis - main_html:\n{main_html_text[:500]}\n")
        mh = analyze_content(main_html_text, "main_html")
        f.write(f"Main HTML Analysis Result: {mh}\n")
        f.write("\n\n************************************************\n\n")

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
            f.write(f"[STEP 2] Content Analysis - script {src_name}:\n{stext[:500]}\n")
            sr = analyze_content(stext, src_name)
            f.write(f"Script Analysis Result: {sr}\n")
            f.write("\n\n************************************************\n\n")

            steps_data["Step2_Content_Analysis"].append({
                "check_id":"check_2_script_llm",
                "analysis_agent":"LLM_script_analyzer",
                "weight":script_llm_weight,
                "risk_level":sr["risk_level"],
                "confidence":sr["confidence"],
                "explanation":sr["reason"]
            })

        f.write(f"[STEP 3] LLM Link Suspiciousness Analysis for: {url}\n")
        link_susp_res = analyze_link_suspiciousness(url)
        f.write(f"Link Suspiciousness Result: {link_susp_res}\n")
        f.write("\n\n************************************************\n\n")

        steps_data["Step3_LLM_Link_Suspiciousness"].append({
            "check_id":"check_3_link_suspiciousness",
            "analysis_agent":"LLM_link_suspiciousness",
            "weight":0.5,
            "risk_level":link_susp_res["risk_level"],
            "confidence":link_susp_res["confidence"],
            "explanation":link_susp_res["reason"]
        })

        aggregator_prompt = (
            "You have steps_data from URL analysis.\n"
            "Produce final JSON ONLY:\n"
            "{\n"
            "\"risk_level\":\"high|low\",\n"
            "\"confidence\":float,\n"
            "\"reasons\":{\n"
            "  \"Step1_Page_Accessibility\":[...],\n"
            "  \"Step2_Content_Analysis\":[...],\n"
            "  \"Step3_LLM_Link_Suspiciousness\":[...]\n"
            "}\n"
            "}\n"
            "No extra text outside JSON.\n"
            "risk_level=high if ANY check is high else low.\n"
            "confidence=weighted avg of all checks.\n"
            "Include all checks from steps_data unchanged.\n"
            f"{json.dumps(steps_data)}"
        )

        f.write(f"[STEP 4] Aggregator Prompt:\n{aggregator_prompt}\n")
        final_res = call_model(aggregator_prompt, AGGREGATOR_SCHEMA)
        f.write(f"Aggregator Final Result: {final_res}\n")
        f.write("\n\n************************************************\n\n")

        return {"status":"completed","result":final_res}


def ensure_output_dir(directory=OUTPUT_DIR):
    if not os.path.exists(directory):
        os.makedirs(directory)

def run_batch_test():
    df = pd.read_csv(DATASET_FILE, encoding='utf-8')
    if 'URL' not in df.columns or 'label' not in df.columns:
        print("Dataset must have 'URL' and 'label' columns. 'label'=1 legit, 0 phishing.")
        return

    # Only process from START_INDEX to END_INDEX
    df = df.iloc[START_INDEX:END_INDEX]
    total = len(df)
    if total == 0:
        print("No data to process (check START_INDEX, END_INDEX).")
        return

    ensure_output_dir(OUTPUT_DIR)

    results = []  # (label, URL, suspicious, outcome, time, final_json)
    success = 0
    fail = 0
    error_count = 0
    total_time = 0.0

    start_time = time.time()
    start_dt = datetime.fromtimestamp(start_time)
    print(f"Starting link analysis test at {start_dt.isoformat()} for {total} URLs...")

    try:
        for i, row in df.iterrows():
            label = row['label']  # 1=legit, 0=phishing
            url = row['URL']

            idx = i - START_INDEX  # zero-based index for these runs
            file_name = f"comprehensive_outputs_{idx+1}.log"
            print(f"[INFO] Processing URL {idx+1}/{total}: {url}")

            req_start = time.time()
            try:
                result = process_link(url, file_name)
                req_end = time.time()
                elapsed = req_end - req_start
                total_time += elapsed

                if result["status"] != "completed":
                    print("[ERROR] LLM processing not completed successfully.")
                    error_count += 1
                    outcome = "error_status"
                    suspicious = None
                    final_json = None
                else:
                    final = result["result"]
                    final_risk = final.get("risk_level","low")
                    suspicious = "yes" if final_risk == "high" else "no"
                    final_json = json.dumps(final)

                    # label=1 (legit) => suspicious=no => success
                    # label=0 (phishing) => suspicious=yes => success
                    if label == 1 and suspicious == "no":
                        success += 1
                        outcome = "success"
                    elif label == 0 and suspicious == "yes":
                        success += 1
                        outcome = "success"
                    else:
                        fail += 1
                        outcome = "fail"

            except KeyboardInterrupt:
                processed = idx
                print("Keyboard interrupt detected. Exiting gracefully.")
                sys.exit(0)
            except Exception as e:
                print(f"[ERROR] Exception: {e}")
                error_count += 1
                outcome = "error_exception"
                suspicious = None
                final_json = None
                elapsed = time.time() - req_start
                total_time += elapsed

            results.append([label, url, suspicious, outcome, elapsed, final_json])

        end_time = time.time()
        end_dt = datetime.fromtimestamp(end_time)
        print(f"\nFinished link analysis at {end_dt.isoformat()}.")

        processed = len(results)
        if processed > 0:
            accuracy = (success / processed) * 100
            avg_time = total_time / processed
            print(f"Processed: {processed}, Success: {success}, Fail: {fail}, Error: {error_count}")
            print(f"Accuracy: {accuracy:.2f}%")
            print(f"Average request time: {avg_time:.4f}s")
        else:
            print("No data processed.")

        # Save all results to a single CSV
        output_csv = os.path.join(OUTPUT_DIR, "link_analysis_10_tests.csv")
        df_out = pd.DataFrame(results, columns=["label","URL","suspicious","outcome","time","final_json"])
        df_out.to_csv(output_csv, index=False, encoding='utf-8', errors='replace')
        print(f"Results saved to {output_csv}")

    except KeyboardInterrupt:
        processed = len(results)
        print("Keyboard interrupt detected. Exiting gracefully.")
        output_csv = os.path.join(OUTPUT_DIR, "link_analysis_10_tests_partial.csv")
        df_out = pd.DataFrame(results, columns=["label","URL","suspicious","outcome","time","final_json"])
        df_out.to_csv(output_csv, index=False, encoding='utf-8', errors='replace')
        print(f"Partial Results saved to {output_csv}")
        sys.exit(0)


if __name__ == "__main__":
    run_batch_test()
