import streamlit as st
import os
import zipfile
import asyncio
import subprocess
from yt_dlp import YoutubeDL
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Async YouTube MP3 Downloader", layout="wide")
st.title("YouTube Batch Audio Downloader (FFmpeg, Async) 🎵")
st.write("Upload a `.txt` file with YouTube URLs (one per line).")

uploaded_file = st.file_uploader("Choose a .txt file", type="txt")

if uploaded_file is not None:
    urls = [line.strip() for line in uploaded_file.getvalue().decode("utf-8").splitlines() if line.strip()]
    st.write(f"Found {len(urls)} URLs")

    if urls:
        mp3_files = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        total_urls = len(urls)
        executor = ThreadPoolExecutor(max_workers=8)

        def sanitize_filename(title):
            return "".join(c for c in title if c.isalnum() or c in " _-").rstrip()

        async def download_convert(url, idx):
            try:
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': 'downloaded.%(ext)s',
                    'quiet': True
                }

                loop = asyncio.get_event_loop()
                # Download video
                info = await loop.run_in_executor(executor, lambda: YoutubeDL(ydl_opts).extract_info(url, download=True))
                video_title = info.get('title', 'audio')
                safe_title = sanitize_filename(video_title)
                mp3_filename = f"{safe_title}.mp3"

                # Skip if MP3 already exists
                if os.path.exists(mp3_filename):
                    mp3_files.append(mp3_filename)
                    st.info(f"{idx+1}/{total_urls} Skipped (already exists): {mp3_filename}")
                    st.audio(mp3_filename, format="audio/mp3")
                    return

                downloaded_file = YoutubeDL(ydl_opts).prepare_filename(info)

                # Convert to MP3 using ffmpeg subprocess
                await loop.run_in_executor(executor, lambda: subprocess.run([
                    "ffmpeg", "-y", "-i", downloaded_file, mp3_filename
                ], check=True))

                os.remove(downloaded_file)
                mp3_files.append(mp3_filename)
                st.success(f"{idx+1}/{total_urls} Converted: {mp3_filename}")
                st.audio(mp3_filename, format="audio/mp3")

            except Exception as e:
                st.error(f"{idx+1}/{total_urls} Error: {url} -> {e}")
            finally:
                progress_bar.progress(len(mp3_files)/total_urls)

        async def main():
            await asyncio.gather(*(download_convert(url, i) for i, url in enumerate(urls)))

        asyncio.run(main())

        # Package all MP3s into a ZIP
        if mp3_files:
            zip_filename = "youtube_audios.zip"
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

        status_text.text("Processing complete!")




st.write("""
by Micio
""")


