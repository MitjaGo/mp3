# ===========================================
# 🎧 Streamlit MP3 Tag Editor with Thumbnail & Bulk Album Support
# ===========================================
import streamlit as st
import eyed3
from PIL import Image as PILImage
import io
import tempfile
import zipfile
import re
from datetime import datetime

st.set_page_config(page_title="MP3 Tag Editor", page_icon="🎵", layout="centered")
st.title("🎧 MP3 Metadata & Thumbnail Editor")

# ===========================================
# 🧩 Helper Functions
# ===========================================
def resize_jpeg(img_data, max_size=500):
    """Resize and convert any image to JPEG bytes."""
    img = PILImage.open(io.BytesIO(img_data))
    img.thumbnail((max_size, max_size))
    out = io.BytesIO()
    img.convert("RGB").save(out, format='JPEG', quality=85)
    return out.getvalue()

def parse_filename(filename):
    """
    Extract artist and title from filenames like:
    '22 - Eros Ramazzotti - Difenderò (That's All I Need To Know).mp3'
    → artist='Eros Ramazzotti', title="Difenderò (That's All I Need To Know)"
    """
    name = re.sub(r'\.\w+$', '', filename)  # remove extension
    parts = re.split(r'\s*-\s*', name)
    parts = [p.strip() for p in parts if p.strip()]

    # If filename starts with a number like "22 - ", remove it
    if parts and re.match(r'^\d+$', parts[0]):
        parts = parts[1:]

    artist, title = "", ""
    if len(parts) >= 2:
        artist, title = parts[0], " - ".join(parts[1:])
    elif len(parts) == 1:
        title = parts[0]
    return artist.strip(), title.strip()

def save_temp_file(uploaded_file):
    """Save an uploaded file to a temporary path for eyed3 to read."""
    suffix = ".mp3"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name
    return tmp_path

# ===========================================
# 📸 Step 1: Upload Default Thumbnail
# ===========================================
st.header("📸 Upload a Default Thumbnail")
default_img_file = st.file_uploader("Upload a default JPG/PNG image", type=["jpg", "jpeg", "png"])

if default_img_file:
    default_img_data = resize_jpeg(default_img_file.getvalue())
    st.image(default_img_data, caption="Default Thumbnail", width=150)
else:
    st.warning("Please upload a default thumbnail to continue.")
    st.stop()

# ===========================================
# 🎵 Step 2: Upload MP3 Files
# ===========================================
st.header("🎵 Upload MP3 Files")
uploaded_mp3s = st.file_uploader("Upload up to 50 MP3s", type=["mp3"], accept_multiple_files=True)
if not uploaded_mp3s:
    st.info("Please upload MP3 files to begin editing.")
    st.stop()

# ===========================================
# 💿 Step 3: Bulk Album Editor
# ===========================================
st.header("💿 Bulk Album Editor")
bulk_album = st.text_input("Enter album name (applied to all tracks):", value="")

# ===========================================
# 📝 Step 4: Edit Metadata
# ===========================================
st.header("📝 Edit Tags for Each MP3")

edited_tracks = []

for mp3_file in uploaded_mp3s[:50]:
    st.subheader(f"🎵 {mp3_file.name}")

    # Try to extract artist and title from filename
    artist_guess, title_guess = parse_filename(mp3_file.name)

    # Save temporarily to disk for eyed3
    temp_path = save_temp_file(mp3_file)
    audiofile = eyed3.load(temp_path)

    if audiofile is None:
        st.error(f"⚠️ Could not read {mp3_file.name}")
        continue

    if audiofile.tag is None:
        audiofile.initTag()

    # Use tag data if available, else fallback to parsed data
    title = st.text_input(f"Title ({mp3_file.name})", value=audiofile.tag.title or title_guess or "")
    artist = st.text_input(f"Artist ({mp3_file.name})", value=audiofile.tag.artist or artist_guess or "")
    album = bulk_album or (audiofile.tag.album or "")

    img_upload = st.file_uploader(f"Replace thumbnail for {mp3_file.name}", type=["jpg", "jpeg", "png"], key=mp3_file.name)
    img_data = resize_jpeg(img_upload.getvalue()) if img_upload else default_img_data

    edited_tracks.append({
        "file": mp3_file,
        "temp_path": temp_path,
        "title": title.strip(),
        "artist": artist.strip(),
        "album": album.strip(),
        "image": img_data
    })

# ===========================================
# 💾 Step 5: Save and Download
# ===========================================
st.header("💾 Save & Download")

if st.button("💾 Save All and Download ZIP"):
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"edited_mp3s_{now}.zip"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_zip:
        with zipfile.ZipFile(tmp_zip.name, "w") as z:
            for track in edited_tracks:
                audiofile = eyed3.load(track["temp_path"])
                if audiofile.tag is None:
                    audiofile.initTag()
                audiofile.tag.title = track["title"]
                audiofile.tag.artist = track["artist"]
                audiofile.tag.album = track["album"]
                audiofile.tag.images.set(3, track["image"], "image/jpeg", u"Cover")
                audiofile.tag.save(version=eyed3.id3.ID3_V2_3)
                z.write(track["temp_path"], arcname=track["file"].name)

     st.success("✅ All tags and album art updated successfully!")


