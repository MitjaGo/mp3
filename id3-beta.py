# 🎧 Streamlit MP3 Tag Editor (Mutagen Version - Guaranteed Cover Replacement)
# ============================================================================
import streamlit as st
from PIL import Image as PILImage
import io
import tempfile
import zipfile
import re
from datetime import datetime
import unicodedata
import os
import shutil
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TRCK, TDRC, ID3NoHeaderError

# ---------------------------------------
# Streamlit setup
# ---------------------------------------
st.set_page_config(page_title="MP3 Tag Editor", page_icon="🎵", layout="centered")
st.title("🎧 MP3 Metadata & Thumbnail Editor (Mutagen)")

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

    # Save uploaded MP3 to temp
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp.write(mp3_file.getvalue())
    tmp_path = tmp.name
    tmp.close()

    # Try to read existing tags
    try:
        audio = MP3(tmp_path, ID3=ID3)
    except ID3NoHeaderError:
        audio = MP3(tmp_path)
        audio.add_tags()

    title_val = audio.tags.get('TIT2').text[0] if 'TIT2' in audio.tags else title_guess
    artist_val = audio.tags.get('TPE1').text[0] if 'TPE1' in audio.tags else artist_guess
    album_val = audio.tags.get('TALB').text[0] if 'TALB' in audio.tags else ""

    # Input fields
    cols = st.columns(3)
    with cols[0]:
        title = st.text_input("Title", value=title_val or "", key=f"title_{i}")
    with cols[1]:
        artist = st.text_input("Artist", value=artist_val or "", key=f"artist_{i}")
    with cols[2]:
        album = st.text_input("Album", value=bulk_album or album_val or "", key=f"album_{i}")

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
        "tmp_path": tmp_path
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
            tmp_path = track["tmp_path"]
            audio = MP3(tmp_path, ID3=ID3)

            # Delete all old tags
            try:
                audio.delete()
                audio.add_tags()
            except Exception:
                audio.add_tags()

            # Write new metadata
            audio.tags.add(TIT2(encoding=3, text=normalize_text(track["title"])))
            audio.tags.add(TPE1(encoding=3, text=normalize_text(track["artist"])))
            audio.tags.add(TALB(encoding=3, text=normalize_text(track["album"])))
            audio.tags.add(TRCK(encoding=3, text=f"{idx+1}/{len(edited_tracks)}"))
            audio.tags.add(TDRC(encoding=3, text=str(bulk_year)))

            # Add cover art
            audio.tags.add(
                APIC(
                    encoding=3,
                    mime='image/jpeg',
                    type=3,
                    desc='Cover',
                    data=track["image"]
                )
            )

            # Save tags
            audio.save(v2_version=3)

            # Add MP3 to ZIP
            zf.write(tmp_path, arcname=track["file"].name)
            progress.progress((idx + 1) / len(edited_tracks))

    # Read ZIP & cleanup
    with open(zip_path, "rb") as f:
        zip_bytes = f.read()
    for track in edited_tracks:
        try:
            os.remove(track["tmp_path"])
        except:
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












