import streamlit as st
from yt_dlp import YoutubeDL
from pydub import AudioSegment
import os
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed

st.title("YouTube Parallel Audio Downloader 🎵")
st.write("Upload a `.txt` file containing YouTube URLs (one per line).")

uploaded_file = st.file_uploader("Choose a .txt file", type="txt")

if uploaded_file is not None:
    urls = [line.strip() for line in uploaded_file.getvalue().decode("utf-8").splitlines() if line.strip()]
    st.write(f"Found {len(urls)} URLs")

    if urls:
        # Set pydub to use ffmpeg
        AudioSegment.converter = "ffmpeg"

        mp3_files = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        def download_and_convert(url):
            """Download a single YouTube URL and convert to MP3."""
            try:
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': 'downloaded.%(ext)s',
                    'quiet': True
                }

                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    video_title = info.get('title', 'audio')
                    downloaded_file = ydl.prepare_filename(info)

                audio = AudioSegment.from_file(downloaded_file)
                mp3_filename = f"{video_title}.mp3"
                audio.export(mp3_filename, format="mp3")

                # Clean up original file
                os.remove(downloaded_file)
                return mp3_filename, url, None
            except Exception as e:
                return None, url, str(e)

        # Use ThreadPoolExecutor for parallel downloads
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(download_and_convert, url): url for url in urls}
            for i, future in enumerate(as_completed(futures)):
                mp3_filename, url_processed, error = future.result()
                if error:
                    st.error(f"Error downloading {url_processed}: {error}")
                else:
                    mp3_files.append(mp3_filename)
                    st.success(f"Converted: {mp3_filename}")
                    st.audio(mp3_filename, format="audio/mp3")
                progress_bar.progress((i + 1) / len(urls))

        # Create ZIP if any MP3s were generated
        if mp3_files:
            zip_filename = "youtube_audios.zip"
            with zipfile.ZipFile(zip_filename, "w") as zipf:
                for mp3 in mp3_files:
                    zipf.write(mp3)
                    os.remove(mp3)  # Remove individual MP3 after adding to ZIP

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


