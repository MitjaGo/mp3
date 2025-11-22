# streamlit_app.py

import streamlit as st
import os
import subprocess
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import zipfile

# --- App title ---
st.title("🎵 YouTube MP3 Downloader")
st.write("Upload a text file with one song title per line. The app will download MP3s from YouTube automatically.")

# Optional clickable link
st.markdown(
    '<a href="https://www.tunemymusic.com/transfer" target="_blank">🎵 Transfer your playlist with TuneMyMusic</a>',
    unsafe_allow_html=True
)

# --- Upload file ---
uploaded_file = st.file_uploader("Upload a .txt file", type="txt")

if uploaded_file is not None:
    raw_terms = [line.strip() for line in uploaded_file.getvalue().decode("utf-8").splitlines() if line.strip()]

    # --- Clean search terms ---
    def clean_term(term):
        term = re.sub(r'\(.*?\)', '', term)
        term = re.sub(r'\[.*?\]', '', term)
        return term.strip()

    search_terms = [clean_term(t) for t in raw_terms]
    st.success(f"🎶 Found {len(search_terms)} songs! Cleaned terms for better success rate.")

    # --- Prepare output folder ---
    output_dir = "mp3_downloads"
    os.makedirs(output_dir, exist_ok=True)

    # --- Define download function ---
    def download_song(term, max_retries=2):
        # Attempt to download and use the YouTube title as filename
        attempt = 0
        while attempt <= max_retries:
            cmd = [
                "yt-dlp",
                f"ytsearch1:{term}",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "-o", f"{output_dir}/%(title)s.%(ext)s",
                "--restrict-filenames",
                "--geo-bypass",
                "--cookies", "",
                "--no-warnings",
                "--quiet"
            ]
            try:
                subprocess.run(cmd, check=True)
                return (term, "success")
            except subprocess.CalledProcessError:
                attempt += 1
                time.sleep(1)
        return (term, "failed")

    # --- Run downloads in parallel ---
    if st.button("Start Download"):
        success, failed, skipped = [], [], []
        progress_bar = st.progress(0)
        status_text = st.empty()

        MAX_WORKERS = 4
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

        # --- Summary ---
        st.success("✅ Downloading complete!")
        st.write(f"📊 Summary:")
        st.write(f"✔️ Successful: {len(success)}")
        st.write(f"⏭️ Skipped: {len(skipped)}")
        st.write(f"❌ Failed: {len(failed)}")

        if failed:
            st.warning("⚠️ Could not download:")
            for f in failed:
                st.write(f"- {f}")

        # --- Zip results ---
        zip_path = "mp3_downloads.zip"
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, _, files in os.walk(output_dir):
                for file in files:
                    zipf.write(os.path.join(root, file), arcname=file)

        st.download_button(
            label="📦 Download All MP3s as ZIP",
            data=open(zip_path, "rb").read(),
            file_name="mp3_downloads.zip",
            mime="application/zip"
        )











st.write("""
by Micio
""")


