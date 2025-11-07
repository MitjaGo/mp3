# --- STEP 0: Install dependencies ---
# Run this in your terminal or add to Streamlit's requirements.txt:
# pip install yt-dlp pydub tqdm streamlit

import os
import subprocess
import streamlit as st
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import zipfile
import re
import time

# --- STEP 1: Streamlit app UI ---
st.title("🎶 Batch YouTube to MP3 Downloader")
st.write("Upload a text file with one song title per line, and download them as MP3.")

uploaded_file = st.file_uploader("Upload text file", type=["txt"])

if uploaded_file:
    search_terms = [line.strip() for line in uploaded_file.read().decode("utf-8").splitlines() if line.strip()]
    st.write(f"Found {len(search_terms)} songs.")

    # --- STEP 2: Prepare output folder ---
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = f"mp3_downloads_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    # --- STEP 3: Define download function ---
    def download_song(term):
        safe_name = re.sub(r"[^\w\d-]", "_", term)[:60]
        existing_files = [f for f in os.listdir(output_dir) if safe_name.lower() in f.lower()]

        if existing_files:
            return (term, "skipped")

        cmd = [
            "yt-dlp",
            f"ytsearch1:{term}",
            "-x",  # extract audio
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "-o", f"{output_dir}/%(title)s.%(ext)s",
            "--restrict-filenames"
        ]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return (term, "success")
        except subprocess.CalledProcessError:
            return (term, "failed")

    # --- STEP 4: Run downloads with a progress bar ---
    MAX_WORKERS = min(4, os.cpu_count() or 1)
    success, failed, skipped = [], [], []

    progress_bar = st.progress(0)
    status_text = st.empty()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(download_song, term): term for term in search_terms}
        for i, future in enumerate(as_completed(futures)):
            term, status = future.result()
            if status == "success":
                success.append(term)
            elif status == "failed":
                failed.append(term)
            else:
                skipped.append(term)
            
            progress_bar.progress((i + 1) / len(search_terms))
            status_text.text(f"Processing: {term} → {status}")

    # --- STEP 5: Summary ---
    st.write("✅ Downloading complete!")
    st.write(f"✔️ Successful: {len(success)}")
    st.write(f"⏭️ Skipped: {len(skipped)}")
    st.write(f"❌ Failed: {len(failed)}")

    if failed:
        st.write("⚠️ Could not download:")
        for f in failed:
            st.write(f"   - {f}")

    # --- STEP 6: Zip results ---
    zip_name = f"{output_dir}.zip"
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                zipf.write(os.path.join(root, file), arcname=file)

    st.download_button(
        label="📦 Download All MP3s",
        data=open(zip_name, "rb").read(),
        file_name=zip_name,
        mime="application/zip"
    )
