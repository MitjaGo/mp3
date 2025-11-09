import streamlit as st
import os
import zipfile
import asyncio
import subprocess
from yt_dlp import YoutubeDL
from concurrent.futures import ThreadPoolExecutor
import glob

st.set_page_config(page_title="YouTube Best Audio MP3 Downloader", layout="wide")
st.title("YouTube Search Audio Downloader (Clean Temp Files) 🎵")
st.write("Upload a `.txt` file with search terms (one per line).")

# -------------------
# Cleanup temporary files on app reload
# -------------------
def cleanup_temp_files():
    temp_patterns = ["downloaded.*", "*.mp3", "youtube_best_audio.zip"]
    for pattern in temp_patterns:
        for file in glob.glob(pattern):
            try:
                os.remove(file)
            except Exception:
                pass

cleanup_temp_files()  # Run cleanup at startup

# -------------------
# User selects top N search results per term
# -------------------
top_n = st.number_input("Number of search results to check per term", min_value=1, max_value=10, value=5, step=1)

uploaded_file = st.file_uploader("Choose a .txt file", type="txt")

if uploaded_file is not None:
    search_terms = [line.strip() for line in uploaded_file.getvalue().decode("utf-8").splitlines() if line.strip()]
    st.write(f"Found {len(search_terms)} search terms")

    if search_terms:
        mp3_files = []
        skipped_terms = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_terms = len(search_terms)
        executor = ThreadPoolExecutor(max_workers=4)

        def sanitize_filename(title):
            return "".join(c for c in title if c.isalnum() or c in " _-").rstrip()

        async def search_download_best_audio(term, idx):
            try:
                loop = asyncio.get_event_loop()

                # Alternative queries
                queries = [
                    term,
                    f"{term} official audio",
                    f"{term} lyrics",
                    f"{term} audio"
                ]

                best_info = None
                best_abr = 0

                # Try each query
                for query in queries:
                    search_url = f"ytsearch{top_n}:{query}"
                    ydl_opts = {'format': 'bestaudio/best', 'quiet': True}

                    try:
                        info_dicts = await loop.run_in_executor(executor, lambda: YoutubeDL(ydl_opts).extract_info(search_url, download=False))
                        entries = info_dicts.get('entries', [info_dicts])

                        # Check each entry for availability
                        for entry in entries:
                            try:
                                formats = entry.get('formats', [])
                                for f in formats:
                                    abr = f.get('abr', 0)
                                    if abr and abr > best_abr:
                                        download_url = f"https://www.youtube.com/watch?v={entry['id']}"
                                        ydl_opts_check = {'format': 'bestaudio/best', 'quiet': True}
                                        await loop.run_in_executor(executor, lambda: YoutubeDL(ydl_opts_check).extract_info(download_url, download=False))
                                        best_abr = abr
                                        best_info = entry
                                if best_info:
                                    break
                            except Exception:
                                continue
                        if best_info:
                            break
                    except Exception:
                        continue

                if not best_info:
                    skipped_terms.append(term)
                    st.warning(f"{idx+1}/{total_terms} No available video found: {term}")
                    return

                video_title = best_info.get('title', 'audio')
                safe_title = sanitize_filename(video_title)
                mp3_filename = f"{safe_title}.mp3"

                # Skip if MP3 exists
                if os.path.exists(mp3_filename):
                    mp3_files.append(mp3_filename)
                    st.info(f"{idx+1}/{total_terms} Skipped (already exists): {mp3_filename}")
                    st.audio(mp3_filename, format="audio/mp3")
                    return

                # Download best audio
                download_url = f"https://www.youtube.com/watch?v={best_info['id']}"
                ydl_opts_download = {'format': 'bestaudio/best', 'outtmpl': 'downloaded.%(ext)s', 'quiet': True}
                info = await loop.run_in_executor(executor, lambda: YoutubeDL(ydl_opts_download).extract_info(download_url, download=True))
                downloaded_file = YoutubeDL(ydl_opts_download).prepare_filename(info)

                # Convert to MP3
                await loop.run_in_executor(executor, lambda: subprocess.run([
                    "ffmpeg", "-y", "-i", downloaded_file, mp3_filename
                ], check=True))

                os.remove(downloaded_file)
                mp3_files.append(mp3_filename)
                st.success(f"{idx+1}/{total_terms} Converted (Best Audio): {mp3_filename}")
                st.audio(mp3_filename, format="audio/mp3")

            except Exception as e:
                skipped_terms.append(term)
                st.error(f"{idx+1}/{total_terms} Error: {term} -> {e}")
            finally:
                progress_bar.progress(len(mp3_files)/total_terms)

        async def main():
            await asyncio.gather(*(search_download_best_audio(term, i) for i, term in enumerate(search_terms)))

        asyncio.run(main())

        # Package MP3s into ZIP
        if mp3_files:
            zip_filename = "youtube_best_audio.zip"
            with zipfile.ZipFile(zip_filename, "w") as zipf:
                for mp3 in mp3_files:
                    zipf.write(mp3)
                    os.remove(mp3)

            st.success(f"All MP3s packaged into {zip_filename} ✅")
            with open(zip_filename, "rb") as f:
                st.download_button(
                    label="Download All MP3s",
                    data=f,
                    file_name=zip_filename,
                    mime="application/zip"
                )

        # Display skipped search terms
        if skipped_terms:
            st.warning(f"{len(skipped_terms)} search term(s) could not be downloaded:")
            for term in skipped_terms:
                st.write(f"- {term}")

        status_text.text("Processing complete!")








st.write("""
by Micio
""")


