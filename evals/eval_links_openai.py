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
OUTPUT_DIR = "./outputs_link_openai"

# Set this to the row index you want to resume from. If 0, start fresh.
RESUME_FROM_INDEX = 251  # For example, start from row 250
CHOSEN_END_INDEX = 501

###############################################################################
# JSON Schemas (same as before)
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

def process_link(url: str) -> dict:
    steps_data = {
        "Step1_Page_Accessibility": [],
        "Step2_Content_Analysis": [],
        "Step3_LLM_Link_Suspiciousness": []
    }

    w_page = 0.3
    w_main_html = 0.3
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

    script_contents = []
    if main_page_fetched:
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

    main_html_text = main_html if main_html else "No main HTML."
    mh = analyze_content(main_html_text, "main_html")
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
        sr = analyze_content(stext, src_name)
        steps_data["Step2_Content_Analysis"].append({
            "check_id":"check_2_script_llm",
            "analysis_agent":"LLM_script_analyzer",
            "weight":script_llm_weight,
            "risk_level":sr["risk_level"],
            "confidence":sr["confidence"],
            "explanation":sr["reason"]
        })

    # Step 3: Direct LLM Link Suspiciousness
    link_susp_res = analyze_link_suspiciousness(url)
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

    final_res = call_model(aggregator_prompt, AGGREGATOR_SCHEMA)

    return {"status":"completed","result":final_res}


def ensure_output_dir(directory=OUTPUT_DIR):
    if not os.path.exists(directory):
        os.makedirs(directory)

def load_partial_results(start_index: int):
    """
    Attempt to load partial results from the last batch CSV that was saved before start_index.
    Adjust counters accordingly.
    This is a simplistic example: you would need logic to find which batch CSV covers rows < start_index.
    For simplicity, we assume start_index aligns with a batch boundary or you know exactly which CSV to load.
    """
    # Example: If you saved results every 5%, and start_index=250 means after batch 5 ended,
    # load 'link_out_batch5.csv'.
    # This will depend on your actual saving logic.

    # If you do not have a perfect alignment, you need to find the highest batch file that covers rows < start_index.

    # For demonstration, let's assume start_index=250 means we have processed exactly 250 rows in a previous run
    # and have a file 'link_out_batchX.csv' that contains at least that many rows.
    # We'll just try to find the largest batch file covering processed<start_index.

    files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("link_out_batch") and f.endswith(".csv")]
    if not files:
        return None, None

    # Sort by batch number
    batch_nums = []
    for f in files:
        # parse batch number from filename: link_out_batch{num}.csv
        match = re.search(r'link_out_batch(\d+)\.csv', f)
        if match:
            batch_num = int(match.group(1))
            batch_nums.append(batch_num)
    batch_nums.sort()

    # We'll pick the last batch file that processed less than start_index rows
    # Since each batch CSV logs how many rows processed, we can just open them and check length
    chosen_file = None
    chosen_df = None
    for b in batch_nums:
        path = os.path.join(OUTPUT_DIR, f"link_out_batch{b}.csv")
        df = pd.read_csv(path)
        # if len(df) < start_index means this batch ended before start_index
        if len(df) < start_index:
            chosen_file = path
            chosen_df = df
        elif len(df) >= start_index:
            # This batch covers or surpasses the start_index, so we stop
            break

    return chosen_file, chosen_df

def run_batch_test():
    df = pd.read_csv(DATASET_FILE)
    if 'URL' not in df.columns or 'label' not in df.columns:
        print("Dataset must have 'URL' and 'label' columns. 'label'=1 legit, 0 phishing.")
        return

    total = len(df)
    if total == 0:
        print("No data to process.")
        return

    ensure_output_dir(OUTPUT_DIR)

    batch_interval = max(1, total // 20)
    next_batch = batch_interval
    batch_number = 0

    results = []  # (label, URL, suspicious, outcome, time)
    success = 0
    fail = 0
    error_count = 0
    total_time = 0.0

    start_time = time.time()

    # If RESUME_FROM_INDEX > 0, try loading partial
    start_index = RESUME_FROM_INDEX
    total = CHOSEN_END_INDEX if CHOSEN_END_INDEX else total
    if start_index > 0:
        print(f"[INFO] Attempting to resume from index {start_index}...")
        # Load partial results
        chosen_file, chosen_df = load_partial_results(start_index)
        if chosen_file and chosen_df is not None:
            # Use chosen_df to restore results
            # all rows in chosen_df have columns [label, URL, suspicious, outcome, time]
            # Reconstruct counters
            processed = len(chosen_df)
            print(f"[INFO] Loaded partial results from {chosen_file}. Processed={processed}")
            results = chosen_df.values.tolist()

            # Recount success/fail/error
            # success: outcome=success, fail=fail, error=error_status or error_exception
            for row in results:
                outcome = row[3]
                if outcome == "success":
                    success += 1
                elif outcome == "fail":
                    fail += 1
                elif outcome.startswith("error"):
                    error_count += 1
                # sum times
                total_time += row[4]
            print(f"[INFO] Loaded partial results from {chosen_file}. Processed={processed}, success={success}, fail={fail}, error={error_count}")
        else:
            print("[WARN] No suitable partial results found. Will attempt to start from scratch at start_index anyway.")
            processed = start_index
    else:
        processed = 0

    start_dt = datetime.fromtimestamp(start_time)
    print(f"Starting link analysis test at {start_dt.isoformat()} with {total} URLs...")

    general_log_path = os.path.join(OUTPUT_DIR, "general_log.csv")
    if not os.path.exists(general_log_path):
        with open(general_log_path, "w") as gf:
            gf.write("timestamp,batch,processed,total,success,fail,error,accuracy,avg_time\n")

    def save_partial(processed_now, final=False):
        nonlocal batch_number, success, fail, error_count, total_time
        accuracy = (success / processed_now) * 100 if processed_now > 0 else 0.0
        avg_time = total_time / processed_now if processed_now > 0 else 0.0

        batch_number += 1
        batch_csv = os.path.join(OUTPUT_DIR, f"link_out_batch{batch_number}.csv")
        batch_df = pd.DataFrame(results, columns=["label","URL","suspicious","outcome","time"])
        batch_df.to_csv(batch_csv, index=False)

        with open(general_log_path, "a") as gf:
            ts = datetime.now().isoformat()
            gf.write(f"{ts},{batch_number},{processed_now},{total},{success},{fail},{error_count},{accuracy:.2f},{avg_time:.4f}\n")

        run_log_path = os.path.join(OUTPUT_DIR, f"run_log_batch{batch_number}.log")
        with open(run_log_path, "w") as lf:
            lf.write(f"Batch {batch_number} processed {processed_now}/{total}\n")
            lf.write(f"Success: {success}, Fail: {fail}, Error: {error_count}\n")
            lf.write(f"Accuracy: {accuracy:.2f}%\n")
            lf.write(f"Avg Time: {avg_time:.4f}s\n")

        if final:
            print(f"\nFinal Results Saved to {batch_csv}")
        else:
            print(f"\nPartial Results Saved to {batch_csv}")

    try:
        # Start loop from start_index
        for i in range(processed, total):
            row = df.iloc[i]
            label = row['label']  # 1=legit, 0=phishing
            url = row['URL']

            print(f"[INFO] Processing URL {i+1}/{total}: {url}")
            req_start = time.time()
            try:
                result = process_link(url)
                req_end = time.time()
                elapsed = req_end - req_start
                total_time += elapsed

                if result["status"] != "completed":
                    print("[ERROR] LLM processing not completed successfully.")
                    error_count += 1
                    outcome = "error_status"
                    suspicious = None
                else:
                    final = result["result"]
                    final_risk = final.get("risk_level","low")
                    suspicious = "yes" if final_risk == "high" else "no"

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
                processed = i
                save_partial(processed, final=True)
                print("[WARN] Keyboard interrupt detected. Exiting gracefully.")
                sys.exit(0)
            except Exception as e:
                print(f"[ERROR] Exception: {e}")
                error_count += 1
                outcome = "error_exception"
                suspicious = None
                elapsed = time.time() - req_start
                total_time += elapsed

            results.append([label, url, suspicious, outcome, elapsed])
            processed = i + 1

            percent = (processed / total) * 100
            bar_length = 50
            completed = int((processed / total) * bar_length)
            bar = '*' * completed + '.' * (bar_length - completed)

            elapsed_so_far = time.time() - start_time
            avg_per_req = elapsed_so_far / processed if processed > 0 else 0.0
            remaining = total - processed
            remaining_time = avg_per_req * remaining
            estimated_end = datetime.fromtimestamp(time.time() + remaining_time).isoformat()

            progress_str = (f"[{percent:3.0f}%]{bar} [Processed:{processed}/{total}] [ETA:{estimated_end}]")
            print(progress_str, end='\r', flush=True)

            if processed >= next_batch and processed < total:
                save_partial(processed)
                next_batch += batch_interval

        save_partial(total, final=True)
        end_time = time.time()
        end_dt = datetime.fromtimestamp(end_time)
        print(f"\nFinished link analysis at {end_dt.isoformat()}.")

        if total > 0:
            accuracy = (success / total) * 100
            avg_time = total_time / total
            print(f"Total: {total}, Success: {success}, Fail: {fail}, Error: {error_count}")
            print(f"Accuracy: {accuracy:.2f}%")
            print(f"Average request time: {avg_time:.4f}s")
        else:
            print("No data processed.")

    except KeyboardInterrupt:
        processed_len = len(results)
        save_partial(processed_len, final=True)
        print("[WARN] Keyboard interrupt detected outside loop. Exiting gracefully.")
        sys.exit(0)


if __name__ == "__main__":
    run_batch_test()
