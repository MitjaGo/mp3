# 🎧 Streamlit MP3 Tag Editor (Stable Fixed Version - Safe Thumbnail)
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
    img = PILImage.open(io.BytesIO(img_data))
    img.thumbnail((max_size, max_size))
    out = io.BytesIO()
    img.convert("RGB").save(out, format="JPEG", quality=85)
    return out.getvalue()

def parse_filename(filename: str):
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
    if not s:
        return ""
    return unicodedata.normalize("NFC", s).replace("\x00", "").strip()

def safe_load_audio(file_bytes: bytes):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp.write(file_bytes)
    tmp_path = tmp.name
    tmp.close()
    eyed3.log.setLevel("ERROR")
    try:
        audiofile = eyed3.load(tmp_path)
    except Exception:
        audiofile = None
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
    "Upload up to 50 MP3s", type=["mp3"], accept_multiple_files=True
)
if not uploaded_mp3s:
    st.info("Please upload MP3 files to begin editing.")
    st.stop()

# ---------------------------------------
# Step 3: Bulk Album / Year Editor
# ---------------------------------------
st.header("💿 Bulk Album & Year Editor")
bulk_album = st.text_input("Album name (applied to all tracks):", value="")
bulk_year = st.number_input(
    "Year", min_value=1900, max_value=2100, value=datetime.now().year
)

# ---------------------------------------
# Step 4: Edit Tags
# ---------------------------------------
st.header("📝 Edit Tags")
edited_tracks = []

for i, mp3_file in enumerate(uploaded_mp3s[:50]):
    st.subheader(f"🎵 {mp3_file.name}")

    artist_guess, title_guess = parse_filename(mp3_file.name)

    audiofile, tmp_path = safe_load_audio(mp3_file.getvalue())
    if not audiofile:
        st.error(f"⚠️ Could not read {mp3_file.name}")
        continue
    if not audiofile.tag:
        audiofile.initTag()

    title_val = audiofile.tag.title or title_guess
    artist_val = audiofile.tag.artist or artist_guess
    album_val = bulk_album or (audiofile.tag.album or "")

    cols = st.columns(3)
    with cols[0]:
        title = st.text_input("Title", value=title_val or "", key=f"title_{i}")
    with cols[1]:
        artist = st.text_input("Artist", value=artist_val or "", key=f"artist_{i}")
    with cols[2]:
        album = st.text_input("Album", value=album_val or "", key=f"album_{i}")

    img_upload = st.file_uploader(
        f"Thumbnail ({mp3_file.name})", type=["jpg", "jpeg", "png"], key=f"img_{i}"
    )
    img_data = resize_jpeg(img_upload.getvalue()) if img_upload else default_img_data
    st.image(img_data, width=100, caption="Cover Preview")

    edited_tracks.append({
        "file": mp3_file,
        "title": title.strip(),
        "artist": artist.strip(),
        "album": album.strip(),
        "image": img_data,
        "tmp_path": tmp_path,
        "audiofile": audiofile
    })

# ---------------------------------------
# Step 5: Save & Download
# ---------------------------------------
st.header("💾 Save & Download")
if st.button("💾 Save All and Download ZIP"):
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"edited_mp3s_{now}.zip"

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, zip_filename)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        progress = st.progress(0)
        for idx, track in enumerate(edited_tracks):
            audiofile = track["audiofile"]
            if not audiofile.tag:
                audiofile.initTag()

            # Update tags
            audiofile.tag.title = normalize_text(track["title"])
            audiofile.tag.artist = normalize_text(track["artist"])
            album_name = normalize_text(bulk_album if bulk_album else track["album"])
            audiofile.tag.album = album_name
            audiofile.tag.recording_date = str(bulk_year)
            audiofile.tag.track_num = (idx + 1, len(edited_tracks))
            audiofile.tag.genre = None

            # Safe thumbnail override
            try:
                if force_override:
                    if hasattr(audiofile.tag, "images") and audiofile.tag.images:
                        audiofile.tag.images.remove_all()
            except Exception:
                pass

            # Always set new cover
            try:
                audiofile.tag.images.set(3, track["image"], "image/jpeg", u"Cover")
            except Exception:
                pass

            # Save tag safely
            try:
                audiofile.tag.save(version=eyed3.id3.ID3_V2_3, encoding="utf-8")
            except Exception:
                audiofile.tag.save(version=eyed3.id3.ID3_V2_3, encoding="utf-16")

            zf.write(track["tmp_path"], arcname=track["file"].name)
            progress.progress((idx + 1) / len(edited_tracks))

    # Read ZIP & cleanup
    with open(zip_path, "rb") as f:
        zip_bytes = f.read()
    for track in edited_tracks:
        try:
            os.remove(track["tmp_path"])
        except Exception:
            pass
    shutil.rmtree(temp_dir, ignore_errors=True)

    st.success("✅ All MP3s processed successfully!")
    st.download_button(
        label="⬇️ Download Edited MP3s as ZIP",
        data=zip_bytes,
        file_name=zip_filename,
        mime="application/zip"
    )

st.write("by Micio 🎵")











