import os
import sys
import json
import re
import time
from datetime import datetime
import requests
import pandas as pd

PHISHING_FILE = "phishing.csv"
BACKEND_URL = "http://localhost:8000"
OUTPUT_DIR = "./outputs_link"

# Set START_INDEX to the row index you want to start from (0-based).
START_INDEX = 0
END_INDEX = 250

def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def test_links():
    df = pd.read_csv(PHISHING_FILE)
    # Ensure 'URL' and 'label' columns:
    if 'URL' not in df.columns or 'label' not in df.columns:
        print("Dataset must have 'URL' and 'label' columns. 'label'=1 legit, 0 phishing.")
        return

    total = len(df)
    if total == 0:
        print("No data to process.")
        return

    if START_INDEX >= total:
        print(f"START_INDEX={START_INDEX} is beyond dataset size={total}. Nothing to process.")
        return

    ensure_output_dir()

    # We'll process from START_INDEX to END_INDEX (or end of dataset if smaller)
    end_index = min(END_INDEX, total - 1)
    to_process = end_index - START_INDEX + 1

    # 5% increments of the subset we are processing
    batch_interval = max(1, to_process // 20)
    next_batch = batch_interval
    batch_number = 0

    results = []  # (label, url, suspicious, outcome, time)
    success = 0
    fail = 0
    error = 0
    total_time = 0.0

    start_time = time.time()
    start_dt = datetime.fromtimestamp(start_time)
    print(f"Starting link analysis test at {start_dt.isoformat()} ...")
    print(f"Processing starting from index {START_INDEX} (0-based), up to {end_index}")

    general_log_path = os.path.join(OUTPUT_DIR, "general_log.csv")
    if not os.path.exists(general_log_path):
        with open(general_log_path, "w") as gf:
            gf.write("timestamp,batch,processed,total,success,fail,error,accuracy,avg_time\n")

    def save_partial(processed, final=False):
        nonlocal batch_number, success, fail, error, total_time
        accuracy = (success / processed) * 100 if processed > 0 else 0.0
        avg_time = total_time / processed if processed > 0 else 0.0

        batch_number += 1
        batch_csv = os.path.join(OUTPUT_DIR, f"link_out_batch{batch_number}.csv")
        batch_df = pd.DataFrame(results, columns=["label","url","suspicious","outcome","time"])
        batch_df.to_csv(batch_csv, index=False)

        with open(general_log_path, "a") as gf:
            ts = datetime.now().isoformat()
            gf.write(f"{ts},{batch_number},{processed},{to_process},{success},{fail},{error},{accuracy:.2f},{avg_time:.4f}\n")

        run_log_path = os.path.join(OUTPUT_DIR, f"run_log_batch{batch_number}.log")
        with open(run_log_path, "w") as lf:
            lf.write(f"Batch {batch_number} processed {processed}/{to_process}\n")
            lf.write(f"Success: {success}, Fail: {fail}, Error: {error}\n")
            lf.write(f"Accuracy: {accuracy:.2f}%\n")
            lf.write(f"Avg Time: {avg_time:.4f}s\n")

        if final:
            print(f"\nFinal Results Saved to {batch_csv}")
        else:
            print(f"\nPartial Results Saved to {batch_csv}")

    try:
        for i in range(START_INDEX, end_index + 1):
            row = df.iloc[i]
            label = row['label']  # 1=legit, 0=phishing
            url = row['URL']
            payload = {"url": url, "visual_verify": False}

            req_start = time.time()
            try:
                resp = requests.post(f"{BACKEND_URL}/api/analyze/link", json=payload, timeout=30)
                req_end = time.time()
                elapsed = req_end - req_start
                total_time += elapsed

                if resp.status_code != 200:
                    error += 1
                    outcome = "error_status"
                    suspicious = None
                else:
                    data = resp.json()
                    suspicious = data.get("result", {}).get("suspicious", "no")

                    # label=0 (phishing) & suspicious="yes" => success
                    # label=1 (legit) & suspicious="no" => success
                    if (label == 0 and suspicious == "yes") or (label == 1 and suspicious == "no"):
                        success += 1
                        outcome = "success"
                    else:
                        fail += 1
                        outcome = "fail"
            except KeyboardInterrupt:
                processed = i - START_INDEX
                save_partial(processed, final=True)
                print("Keyboard interrupt detected. Exiting gracefully.")
                sys.exit(0)
            except Exception:
                error += 1
                outcome = "error_exception"
                suspicious = None
                elapsed = time.time() - req_start
                total_time += elapsed

            results.append([label, url, suspicious, outcome, elapsed])

            processed = i - START_INDEX + 1
            percent = (processed / to_process) * 100
            bar_length = 50
            completed = int((processed / to_process) * bar_length)
            bar = '*' * completed + '.' * (bar_length - completed)

            elapsed_so_far = time.time() - start_time
            avg_per_req = elapsed_so_far / processed if processed > 0 else 0.0
            remaining = to_process - processed
            remaining_time = avg_per_req * remaining
            estimated_end = datetime.fromtimestamp(time.time() + remaining_time).isoformat()

            progress_str = (f"[{percent:3.0f}%]{bar} [Progress:{processed}/{to_process}][ETA:{estimated_end}]")
            print(progress_str, end='\r', flush=True)

            if processed == 1:
                # Recalculate batch_interval since we know to_process exactly
                batch_interval = max(1, to_process // 20)
                next_batch = batch_interval

            if processed >= next_batch and processed < to_process:
                save_partial(processed)
                next_batch += batch_interval

        # After the loop, save final
        processed = to_process
        save_partial(processed, final=True)
        end_time = time.time()
        end_dt = datetime.fromtimestamp(end_time)
        print(f"\nFinished link analysis test at {end_dt.isoformat()}.")

        # Print final stats
        accuracy = (success / processed) * 100 if processed > 0 else 0.0
        avg_time = total_time / processed if processed > 0 else 0.0
        print(f"Processed (from index {START_INDEX}): {processed}, Success: {success}, Fail: {fail}, Error: {error}")
        print(f"Accuracy: {accuracy:.2f}%")
        print(f"Average request time: {avg_time:.4f}s")

    except KeyboardInterrupt:
        processed = len(results)
        save_partial(processed, final=True)
        print("Keyboard interrupt detected outside loop. Exiting gracefully.")
        sys.exit(0)

if __name__ == "__main__":
    test_links()
