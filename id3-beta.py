# 🎧 Streamlit MP3 Tag Editor (Final Stable Version - Thumbnail Override Enabled)
# =========================================================
import streamlit as st
import eyed3
from PIL import Image as PILImage
import io
import tempfile
import zipfile
import re
from datetime import datetime
import unicodedata
import os
import shutil

# ---------------------------------------
# Streamlit setup
# ---------------------------------------
st.set_page_config(page_title="MP3 Tag Editor", page_icon="🎵", layout="centered")
st.title("🎧 MP3 Metadata & Thumbnail Editor")

# ---------------------------------------
# Helpers
# ---------------------------------------
def resize_jpeg(img_data: bytes, max_size: int = 500) -> bytes:
    """Resize and convert any image to JPEG bytes."""
    img = PILImage.open(io.BytesIO(img_data))
    img.thumbnail((max_size, max_size))
    out = io.BytesIO()
    img.convert("RGB").save(out, format="JPEG", quality=85)
    return out.getvalue()

def parse_filename(filename: str):
    """Guess artist/title from filename."""
    name = re.sub(r"\.\w+$", "", filename)
    parts = re.split(r"\s*-\s*", name)
    parts = [p.strip() for p in parts if p.strip()]
    if parts and re.match(r"^\d+$", parts[0]):
        parts = parts[1:]
    artist, title = "", ""
    if len(parts) >= 2:
        artist, title = parts[0], " - ".join(parts[1:])
    elif len(parts) == 1:
        title = parts[0]
    return artist.strip(), title.strip()

def normalize_text(s: str) -> str:
    """Clean up text for ID3 tags."""
    if not s:
        return ""
    return unicodedata.normalize("NFC", s).replace("\x00", "").strip()

def safe_load_audio(file_bytes: bytes):
    """Load MP3 safely from bytes buffer."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp.write(file_bytes)
    tmp_path = tmp.name
    tmp.close()

    eyed3.log.setLevel("ERROR")

    try:
        audiofile = eyed3.load(tmp_path)
    except Exception:
        audiofile = None

    # Remove invalid genres that can break save
    if audiofile and audiofile.tag and getattr(audiofile.tag, "genre", None):
        try:
            if audiofile.tag.genre and audiofile.tag.genre.id >= 250:
                audiofile.tag.genre = None
        except Exception:
            audiofile.tag.genre = None

    return audiofile, tmp_path

# ---------------------------------------
# Step 1: Default Thumbnail
# ---------------------------------------
st.header("📸 Upload Default Thumbnail")

default_img_file = st.file_uploader(
    "Upload a default JPG/PNG image", type=["jpg", "jpeg", "png"]
)

if not default_img_file:
    st.warning("Please upload a default thumbnail to continue.")
    st.stop()

force_override = st.checkbox("Force override all existing thumbnails", value=True)

default_img_data = resize_jpeg(default_img_file.getvalue())
st.image(default_img_data, caption="Default Thumbnail", width=150)

# ---------------------------------------
# Step 2: MP3 Upload
# ---------------------------------------
st.header("🎵 Upload MP3 Files")

uploaded_mp3s = st.file_uploader(
    "Upload up to 50 MP3s",
    type=["mp3"],
    accept_multiple_files=True
)

if not uploaded_mp3s:
    st.info("Please upload MP3 files to begin editing.")
    st.stop()

# ---------------------------------------
# Step 3: Bulk Album Editor
# ---------------------------------------
st.header("💿 Bulk Album Editor")

bulk_album = st.text_input("Album name (applied to all tracks):", value="")
bulk_year = st.number_input(
    "Year",
    min_value=1900,
    max_value=2100,
    value=datetime.now().year
)

# ---------------------------------------
# Step 4: Edit
# ---------------------------------------
st.header("📝 Edit Tags")

edited_tracks = []

for i, mp3_file in enumerate(uploaded_mp3s[:50]):
    st.subheader(f"🎵 {mp3_file.name}")

    artist_gues_











