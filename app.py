import streamlit as st
import asyncio
import threading
import time
import sys
from io import StringIO
import os
import re
import pandas as pd
import traceback
import webbrowser  # for open‑folder link
import subprocess, os, glob

# --- Windows asyncio fix ---
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# === import your existing working script ===
import form_automation

# --- Page setup ---
st.set_page_config(page_title="Automated Form Tester", layout="wide")

# --- Custom CSS for small visual polish ---
st.markdown("""
<style>
    .block-container {padding-top: 1rem;}
    .stProgress > div > div > div:nth-child(1) {background-color: #4CAF50;}
</style>
""", unsafe_allow_html=True)

st.title("🌐 Automated Tracking link Form Tester")
st.write("Runs your existing Playwright automation and shows a live per‑URL table.")

# --- Sidebar ---
with st.sidebar:
    st.header("Configuration")
    dev_username = st.text_input("DEV Username", value=form_automation.DEV_USERNAME)
    dev_password = st.text_input("DEV Password", type="password", value=form_automation.DEV_PASSWORD)
    input_file = st.text_input("Input Excel file path", value=form_automation.INPUT_FILE)
    output_file = st.text_input("Output Excel file path", value=form_automation.OUTPUT_FILE)
    headless = st.checkbox("Run headless browser", value=True)
    show_all_logs = st.checkbox("Show full logs", value=True)
    run_btn = st.button("🚀 Run Automation")

# --- Apply runtime config ---
form_automation.DEV_USERNAME = dev_username
form_automation.DEV_PASSWORD = dev_password
form_automation.INPUT_FILE = input_file
form_automation.OUTPUT_FILE = output_file

# Placeholders for dynamic UI sections
status_box = st.empty()
progress_box = st.empty()
table_box = st.empty()
log_box = st.empty()

# Regex patterns for parsing log lines
row_pattern = re.compile(r"Row\s+(\d+)\s*->\s*(\S+)")
finish_pattern = re.compile(r"✅ Results saved", re.IGNORECASE)


# --- helper to run form_automation.main() in background thread ---
def run_async_main(log_stream):
    sys.stdout = log_stream
    sys.stderr = log_stream
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(form_automation.main())
    except Exception:
        traceback.print_exc()
    finally:
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__


# --- Run button pressed ---
if run_btn:
    if not os.path.exists(input_file):
        st.error(f"❌ Input file not found: {input_file}")
        st.stop()

    start_time = time.time()
    status_box.info("Starting automation... This may take a few minutes.")
    log_stream = StringIO()

    thread = threading.Thread(target=run_async_main, args=(log_stream,), daemon=True)
    thread.start()

    df = pd.DataFrame(columns=["Row", "URL", "Status"])

    # --- Loop while background automation runs ---
    while thread.is_alive():
        time.sleep(1)
        logs = log_stream.getvalue()

        # optionally trim logs for display
        if not show_all_logs:
            logs = "\n".join(logs.splitlines()[-100:])

        # Display logs and auto‑scroll
        log_box.markdown(f"```text\n{logs}\n```<script>window.scrollTo(0, document.body.scrollHeight);</script>",unsafe_allow_html=True)

        # extract rows
        for row, url in row_pattern.findall(logs):
            row_i = int(row)
            if row_i not in df["Row"].values:
                df.loc[len(df)] = [row_i, url, "Running"]

        # mark completed ones
        for i in range(len(df)):
            if f"Row {df.loc[i, 'Row']} ->" in logs and "Captured Response URL" in logs:
                df.at[i, "Status"] = "Done"

        # update UI summary table and progress bar
        table_box.dataframe(
            df.sort_values("Row").reset_index(drop=True),
            use_container_width=True,
        )

        processed = len(df)
        if len(df) > 0:
            progress_value = min(processed / max(1, df["Row"].max()), 1.0)
        else:
            progress_value = 0.0
        progress_box.progress(progress_value)
        status_box.info(f"Processing... {processed} URLs so far")

        # --- After run completes ---
    thread.join(timeout=2)
    elapsed = round(time.time() - start_time, 1)
    final_logs = log_stream.getvalue()

    st.text_area("📝 Final Logs", final_logs, height=400, key="final_logs")

    status_box.success(f"✅ Completed in {elapsed}s! Results saved at: {output_file}")

    # Download + open folder helper
    if os.path.exists(output_file):
        with open(output_file, "rb") as f:
            st.download_button(
                "⬇️ Download Results (Excel)",
                f,
                file_name=os.path.basename(output_file),
            )
        folder = os.path.dirname(output_file)
        st.markdown(f"[📂 Open results folder]({folder})")

