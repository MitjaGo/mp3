# --- STEP 0: Install dependencies ---
# pip install yt-dlp pydub tqdm streamlit

import os
import subprocess
import streamlit as st
from concurrent.futures import ThreadPoolExecutor, as_completed
import zipfile
import re
import time
import shutil

# --- STEP 1: Streamlit app UI ---
st.set_page_config(page_title="YouTube → MP3 (one per search, mp3 only)")
st.title("🎶 Batch YouTube → MP3 (one file per entry, MP3 only)")
st.write("""
Upload a text file with one **song title** or **YouTube URL** per line.
The app will attempt to produce exactly one MP3 per line and will not include non-MP3 files in the ZIP.
""")

# --- Check ffmpeg availability early (required for conversion) ---
def check_ffmpeg():
    return shutil.which("ffmpeg") is not None

if not check_ffmpeg():
    st.error("`ffmpeg` not found. ffmpeg is required for conversion to MP3.")
    st.markdown("**Install ffmpeg:**")
    st.code("sudo apt update && sudo apt install ffmpeg    # Debian/Ubuntu", language="bash")
    st.code("brew install ffmpeg                             # macOS (Homebrew)", language="bash")
    st.code("choco install ffmpeg -y                         # Windows (Chocolatey)", language="bash")
    st.stop()

uploaded_file = st.file_uploader("📄 Upload your text file", type=["txt"])

if not uploaded_file:
    st.info("Upload a .txt file with one song title or YouTube URL per line.")
    st.stop()

search_terms = [
    line.strip()
    for line in uploaded_file.read().decode("utf-8").splitlines()
    if line.strip()
]
st.write(f"Found **{len(search_terms)}** items to download.")

# --- Prepare output folder ---
timestamp = time.strftime("%Y%m%d_%H%M%S")
output_dir = f"mp3_downloads_{timestamp}"
os.makedirs(output_dir, exist_ok=True)

# Helper: detect YouTube URL
def is_youtube_url(text: str) -> bool:
    return bool(re.search(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/", text))

# Helper: list files snapshot
def snapshot_files():
    return set(os.listdir(output_dir))

# Download function
def download_song(term):
    # Create a safe short name for skip detection
    safe_name = re.sub(r"[^\w\d-]", "_", term)[:60]
    # If we've already downloaded something that matches, skip
    for f in os.listdir(output_dir):
        if safe_name.lower() in f.lower() and f.lower().endswith(".mp3"):
            return (term, "skipped", "")

    before_files = snapshot_files()

    # Use direct URL or single-search
    if is_youtube_url(term):
        query = term
    else:
        query = f"ytsearch1:{term}"

    cmd = [
        "yt-dlp",
        query,
        "-x",                        # extract audio
        "--audio-format", "mp3",     # convert to mp3
        "--audio-quality", "0",      # best
        "--no-playlist",             # avoid playlists
        "-o", f"{output_dir}/%(title)s.%(ext)s",
        "--restrict-filenames"
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired:
        # If yt-dlp times out, try to clean any new non-mp3 files and return failed
        after_files = snapshot_files()
        new_files = after_files - before_files
        for nf in new_files:
            if not nf.lower().endswith(".mp3"):
                try:
                    os.remove(os.path.join(output_dir, nf))
                except Exception:
                    pass
        return (term, "failed", "yt-dlp timed out")

    stderr = proc.stderr or ""
    stdout = proc.stdout or ""

    after_files = snapshot_files()
    new_files = after_files - before_files

    # If any new .mp3 file was produced, success
    produced_mp3s = [f for f in new_files if f.lower().endswith(".mp3")]
    if produced_mp3s:
        # Clean up any other leftover non-mp3 files from this run
        for nf in new_files:
            if not nf.lower().endswith(".mp3"):
                try:
                    os.remove(os.path.join(output_dir, nf))
                except Exception:
                    pass
        return (term, "success", "\n".join([stderr.strip(), stdout.strip()]).strip())

    # No mp3 created: remove any new non-mp3 files to avoid polluting ZIP
    for nf in new_files:
        try:
            os.remove(os.path.join(output_dir, nf))
        except Exception:
            pass

    # Return failure and include stderr to help troubleshooting
    combined = stderr.strip() or stdout.strip() or "No mp3 created (conversion failed)."
    return (term, "failed", combined)

# Run downloads with a progress bar
MAX_WORKERS = 2
success, failed, skipped = [], [], []
logs = {}  # store stderr/stdout per term

progress_bar = st.progress(0)
status_text = st.empty()
log_area = st.empty()

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {executor.submit(download_song, term): term for term in search_terms}
    total = len(search_terms)
    done = 0
    for future in as_completed(futures):
        term, status, log_text = future.result()
        done += 1
        if status == "success":
            success.append(term)
        elif status == "skipped":
            skipped.append(term)
        else:
            failed.append(term)
        logs[term] = log_text
        progress_bar.progress(done / total)
        status_text.text(f"Processing: {term} → {status}")

# Summary
st.success("✅ Operation complete")
st.write(f"✔️ Successful: {len(success)}")
st.write(f"⏭️ Skipped: {len(skipped)}")
st.write(f"❌ Failed: {len(failed)}")

if failed:
    st.warning("⚠️ Failed items and logs (first 500 chars):")
    for f in failed:
        txt = logs.get(f, "")[:500]
        st.write(f"**{f}**")
        st.code(txt if txt else "No stderr available.", language="bash")

# Zip only .mp3 files
zip_name = f"{output_dir}.zip"
with zipfile.ZipFile(zip_name, "w") as zipf:
    for root, dirs, files in os.walk(output_dir):
        for file in files:
            if file.lower().endswith(".mp3"):
                zipf.write(os.path.join(root, file), arcname=file)

# Provide download button and show (if any) non-mp3 files were removed
with open(zip_name, "rb") as f:
    st.download_button(
        label="📦 Download All MP3s",
        data=f.read(),
        file_name=zip_name,
        mime="application/zip"
    )

# Small tips
st.info("""
**Notes / Troubleshooting**
- This app requires `ffmpeg` to convert to MP3. If you see non-MP3 files in previous runs, install ffmpeg and re-run.
- If a specific item fails, check the log shown above (it includes yt-dlp stderr).
- You can paste full YouTube URLs or plain titles. For titles we use `ytsearch1:` so only one result is attempted.
""")


st.write("""
by Micio
""")


