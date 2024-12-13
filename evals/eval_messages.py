import requests
import pandas as pd
import time
from datetime import datetime
import os
import sys

# File: test_messages.py
#
# Requirements:
# - Every 5% of dataset processed, save partial results to ./outputs/message_out_batchX.csv
# - Also maintain a general log (general_log.csv) and run log for each batch (run_log_batchX.log)
# - On KeyboardInterrupt, save what we have and exit gracefully
# - At end or interrupt, print final accuracy, error rate, avg time.
#
# Steps:
# 1) Load sms_spam.csv (label=ham/spam, message)
# 2) For each row, call /api/analyze/message
# 3) Store result (label, message, suspicious, success/fail/error, time)
# 4) Every 5% of total processed, write partial CSV and logs
# 5) If KeyboardInterrupt, save partial and exit
# 6) Print final stats

SMS_SPAM_FILE = "sms_spam.csv"
BACKEND_URL = "http://localhost:8000"
OUTPUT_DIR = "./outputs_message"

def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def test_messages():
    df = pd.read_csv(SMS_SPAM_FILE, encoding='latin-1')
    if 'v1' in df.columns and 'v2' in df.columns:
        df.rename(columns={'v1':'label','v2':'message'}, inplace=True)
    df = df[['label','message']]
    total = len(df)

    if total == 0:
        print("No data to process.")
        return

    ensure_output_dir()

    # Determine batch size: every 5%
    batch_interval = max(1, total // 20)  # 5% steps (20 batches per 100%)
    next_batch = batch_interval
    batch_number = 0

    results = []  # store per-request info: (label, message, suspicious, outcome, time)
    success = 0
    fail = 0
    error = 0
    total_time = 0.0

    start_time = time.time()
    start_dt = datetime.fromtimestamp(start_time)
    print(f"Starting message analysis test at {start_dt.isoformat()} ...")

    # Write a general log header if not exist
    general_log_path = os.path.join(OUTPUT_DIR, "general_log.csv")
    if not os.path.exists(general_log_path):
        with open(general_log_path, "w") as gf:
            gf.write("timestamp,batch,processed,total,success,fail,error,accuracy,avg_time\n")

    def save_partial(processed, final=False):
        nonlocal batch_number, success, fail, error, total_time
        # Calculate stats
        accuracy = 0.0
        if processed > 0:
            accuracy = (success / processed) * 100
        avg_time = total_time / processed if processed > 0 else 0.0

        # Save batch results
        batch_number += 1
        batch_csv = os.path.join(OUTPUT_DIR, f"message_out_batch{batch_number}.csv")
        batch_df = pd.DataFrame(results, columns=["label","message","suspicious","outcome","time"])
        batch_df.to_csv(batch_csv, index=False)

        # Update general log
        with open(general_log_path, "a") as gf:
            ts = datetime.now().isoformat()
            gf.write(f"{ts},{batch_number},{processed},{total},{success},{fail},{error},{accuracy:.2f},{avg_time:.4f}\n")

        # Run log for this batch
        run_log_path = os.path.join(OUTPUT_DIR, f"run_log_batch{batch_number}.log")
        with open(run_log_path, "w") as lf:
            lf.write(f"Batch {batch_number} processed {processed}/{total}\n")
            lf.write(f"Success: {success}, Fail: {fail}, Error: {error}\n")
            lf.write(f"Accuracy: {accuracy:.2f}%\n")
            lf.write(f"Avg Time: {avg_time:.4f}s\n")

        if final:
            print(f"\nFinal Results Saved to {batch_csv}")
        else:
            print(f"\nPartial Results Saved to {batch_csv}")

    try:
        for i, row in df.iterrows():
            label = row['label']
            msg = row['message']

            payload = {"message": msg}
            req_start = time.time()
            try:
                resp = requests.post(f"{BACKEND_URL}/api/analyze/message", json=payload, timeout=30)
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
                    # Determine success/fail
                    # spam + suspicious=yes => success
                    # ham + suspicious=no => success
                    # else fail
                    if label == "spam" and suspicious == "yes":
                        success += 1
                        outcome = "success"
                    elif label == "ham" and suspicious == "no":
                        success += 1
                        outcome = "success"
                    else:
                        fail += 1
                        outcome = "fail"
            except KeyboardInterrupt:
                # On Ctrl+C, save partial and exit
                processed = i
                save_partial(processed, final=True)
                print("Keyboard interrupt detected. Exiting gracefully.")
                sys.exit(0)
            except Exception:
                # Other exceptions
                error += 1
                outcome = "error_exception"
                suspicious = None
                elapsed = time.time() - req_start

            # Store result
            results.append([label, msg, suspicious, outcome, elapsed])

            processed = i + 1
            percent = (processed / total) * 100
            # Update progress on the same line
            # Recompute bar and ETA each iteration:
            bar_length = 50
            completed = int((processed / total) * bar_length)
            bar = '*' * completed + '.' * (bar_length - completed)

            elapsed_so_far = time.time() - start_time
            avg_per_req = elapsed_so_far / processed if processed > 0 else 0.0
            remaining = total - processed
            remaining_time = avg_per_req * remaining
            estimated_end = datetime.fromtimestamp(time.time() + remaining_time).isoformat()

            progress_str = (f"[{percent:3.0f}%]{bar} [Progress:{processed}/{total}]"
                            f"[ETA:{estimated_end}]")

            print(progress_str, end='\r', flush=True)


            # Every batch_interval (5%), save partial results
            if processed >= next_batch and processed < total:
                save_partial(processed)
                next_batch += batch_interval

        # End of loop
        save_partial(total, final=True)
        end_time = time.time()
        end_dt = datetime.fromtimestamp(end_time)
        print(f"Finished message analysis at {end_dt.isoformat()}.")

        # Print final stats
        if total > 0:
            accuracy = (success / total) * 100
            avg_time = total_time / total
            print(f"Total: {total}, Success: {success}, Fail: {fail}, Error: {error}")
            print(f"Accuracy: {accuracy:.2f}%")
            print(f"Average request time: {avg_time:.4f}s")
        else:
            print("No data processed.")

    except KeyboardInterrupt:
        # If Ctrl+C outside the request loop
        processed = len(results)
        save_partial(processed, final=True)
        print("Keyboard interrupt detected. Exiting gracefully.")
        sys.exit(0)

if __name__ == "__main__":
    test_messages()
