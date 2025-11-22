# streamlit_app.py

import streamlit as st
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pytube import YouTube, Search
from pydub import AudioSegment
import zipfile
import time

# --- App title ---
st.title("🎵 YouTube MP3 Downloader (pytube + retry)")
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
        term = re.sub(r'[^\x20-\x7E]+', '', term)  # remove invisible chars
        return term.strip()

    search_terms = [clean_term(t) for t in raw_terms]
    st.success(f"🎶 Found {len(search_terms)} songs! Cleaned terms for better success rate.")

    # --- Prepare output folder ---
    output_dir = "mp3_downloads"
    os.makedirs(output_dir, exist_ok=True)

    # --- Define download function with retries ---
    def download_song(term, max_retries=2):
        for attempt in range(max_retries + 1):
            try:
                # Search YouTube and get the first video
                results = Search(term).results
                if not results:
                    continue
                yt = results[0]

                # Use video title for filename
                title_safe = re.sub(r'[\\/*?:"<>|]', "", yt.title)
                mp3_path = os.path.join(output_dir, f"{title_safe}.mp3")

                if os.path.exists(mp3_path):
                    return (term, "skipped")

                # Download audio stream
                audio_stream = yt.streams.filter(only_audio=True).first()
                temp_file = audio_stream.download(output_path=output_dir, filename="temp_audio")

                # Convert to MP3 using pydub
                AudioSegment.from_file(temp_file).export(mp3_path, format="mp3")
                os.remove(temp_file)
                return (term, "success")
            except Exception:
                time.sleep(1)  # wait 1 second before retry
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


