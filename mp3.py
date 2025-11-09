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
st.title("🎶 Batch YouTube to MP3 Downloader (URLs + Search Supported)")
st.write("""
Upload a text file with one song title **or** YouTube URL per line.  
The app will download each as an MP3 file and bundle them into a ZIP.
""")

uploaded_file = st.file_uploader("📄 Upload text file", type=["txt"])

if uploaded_file:
    search_terms = [
        line.strip()
        for line in uploaded_file.read().decode("utf-8").splitlines()
        if line.strip()
    ]
    st.write(f"Found **{len(search_terms)}** items to download.")

    # --- STEP 2: Prepare output folder ---
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir = f"mp3_downloads_{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    # --- STEP 3: Helper to check if a line is a YouTube URL ---
    def is_youtube_url(text: str) -> bool:
        return bool(re.search(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/", text))

    # --- STEP 4: Download function ---
    def download_song(term):
        safe_name = re.sub(r"[^\w\d-]", "_", term)[:60]
        existing_files = [
            f for f in os.listdir(output_dir) if safe_name.lower() in f.lower()
        ]
        if existing_files:
            return (term, "skipped")

        # Detect if this is a direct URL or a search term
        if is_youtube_url(term):
            query = term
        else:
            query = f"ytsearch5:{term}"

        cmd = [
            "yt-dlp",
            query,
            "-x",  # extract audio
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "-o", f"{output_dir}/%(title)s.%(ext)s",
            "--restrict-filenames"
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return (term, "success")
            else:
                print(f"❌ Error downloading {term}:\n{result.stderr}")
                return (term, "failed")
        except Exception as e:
            print(f"⚠️ Exception while downloading {term}: {e}")
            return (term, "failed")

    # --- STEP 5: Run downloads with a progress bar ---
    MAX_WORKERS = 2  # safer: avoids rate-limits and connection issues
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

    # --- STEP 6: Summary ---
    st.success("✅ Downloading complete!")
    st.write(f"✔️ Successful: {len(success)}")
    st.write(f"⏭️ Skipped: {len(skipped)}")
    st.write(f"❌ Failed: {len(failed)}")

    if failed:
        st.warning("⚠️ Could not download:")
        for f in failed:
            st.write(f"   - {f}")

    # --- STEP 7: Zip results ---
    zip_name = f"{output_dir}.zip"
    with zipfile.ZipFile(zip_name, "w") as zipf:
        for root, dirs, files in os.walk(output_dir):
            for file in files:
                zipf.write(os.path.join(root, file), arcname=file)

    # --- STEP 8: Download button ---
    with open(zip_name, "rb") as f:
        st.download_button(
            label="📦 Download All MP3s",
            data=f.read(),
            file_name=zip_name,
            mime="application/zip"
        )

    # --- STEP 9: Tips ---
    st.info("""
💡 **Tips:**
- If a song fails, try adding its full YouTube URL in your text file.
- You can mix URLs and song titles — both will work.
- Reduce failures further by running fewer downloads at once.
""")

