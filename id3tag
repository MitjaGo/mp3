# ===========================================
# streamlit_mp3_editor.py
# ===========================================
import streamlit as st
import eyed3
from PIL import Image as PILImage
import io
import re
import zipfile
from datetime import datetime

# ===========================================
# Helper Functions
# ===========================================
def resize_jpeg(img_data, max_size=500):
    img = PILImage.open(io.BytesIO(img_data))
    img.thumbnail((max_size, max_size))
    out = io.BytesIO()
    img.convert("RGB").save(out, format='JPEG', quality=85)
    return out.getvalue()

def parse_filename(filename):
    """Extract Artist & Title from filename."""
    name = re.sub(r'\.\w+$', '', filename)  # remove extension
    parts = re.split(r'\s*-\s*', name)
    parts = [p.strip() for p in parts if p.strip()]
    artist, title = "", ""
    if len(parts) >= 3:
        artist = parts[1]
        title = " - ".join(parts[2:])
    elif len(parts) == 2:
        artist, title = parts
    else:
        title = parts[0] if parts else filename
    return artist, title

def embed_thumbnail(mp3_file, image_data):
    audiofile = eyed3.load(mp3_file)
    if audiofile.tag is None:
        audiofile.initTag()
    audiofile.tag.images.set(3, image_data, "image/jpeg", u"Cover")
    audiofile.tag.save(version=eyed3.id3.ID3_V2_3)

def clean_filename(filename):
    return re.sub(r"\s*\(\d+\)(?=\.\w+$)", "", filename)

# ===========================================
st.title("🎵 MP3 Tag & Thumbnail Editor")

# ===========================================
# Step 1: Upload default thumbnail
default_img_file = st.file_uploader("📸 Upload a default JPG/PNG thumbnail", type=["jpg", "jpeg", "png"])
if default_img_file:
    default_img_data = resize_jpeg(default_img_file.read())
    st.image(default_img_data, width=150, caption="Default Thumbnail Preview")

# ===========================================
# Step 2: Upload MP3 files
mp3_files = st.file_uploader("⬆️ Upload MP3 files (multiple allowed)", type=["mp3"], accept_multiple_files=True)
if mp3_files:
    st.success(f"✅ {len(mp3_files)} MP3 files uploaded")
    
    # Optional: Bulk album name
    bulk_album_name = st.text_input("Set Album for All MP3s (optional):")
    
    edited_files = []

    # ===========================================
    for uploaded_file in mp3_files:
        st.markdown(f"---\n**File:** {uploaded_file.name}")
        audiofile = eyed3.load(uploaded_file)
        if audiofile.tag is None:
            audiofile.initTag()
        
        # Parse filename if tags missing
        parsed_artist, parsed_title = parse_filename(uploaded_file.name)
        title_val = audiofile.tag.title or parsed_title or ""
        artist_val = audiofile.tag.artist or parsed_artist or ""
        album_val = audiofile.tag.album or bulk_album_name or ""
        
        # Editable fields
        title = st.text_input(f"Title - {uploaded_file.name}", value=title_val, key=f"title_{uploaded_file.name}")
        artist = st.text_input(f"Artist - {uploaded_file.name}", value=artist_val, key=f"artist_{uploaded_file.name}")
        album = st.text_input(f"Album - {uploaded_file.name}", value=album_val, key=f"album_{uploaded_file.name}")
        
        # Thumbnail per file
        img_file = st.file_uploader(f"Thumbnail for {uploaded_file.name} (optional)", type=["jpg","jpeg","png"], key=f"img_{uploaded_file.name}")
        if img_file:
            img_data = resize_jpeg(img_file.read())
        else:
            img_data = default_img_data
        
        st.image(img_data, width=100)
        
        edited_files.append({
            "uploaded_file": uploaded_file,
            "title": title,
            "artist": artist,
            "album": album,
            "img_data": img_data
        })
    
    # ===========================================
    # Save & download as ZIP
    if st.button("💾 Save All Tags & Download ZIP"):
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as z:
            for f in edited_files:
                # Load and update tags
                temp_file = f["uploaded_file"].read()
                with open(f["uploaded_file"].name, "wb") as temp_fp:
                    temp_fp.write(temp_file)
                audiofile = eyed3.load(f["uploaded_file"].name)
                if audiofile.tag is None:
                    audiofile.initTag()
                audiofile.tag.title = f["title"]
                audiofile.tag.artist = f["artist"]
                audiofile.tag.album = f["album"]
                audiofile.tag.images.set(3, f["img_data"], "image/jpeg", u"Cover")
                audiofile.tag.save(version=eyed3.id3.ID3_V2_3)
                
                # Add to ZIP
                z.write(f["uploaded_file"].name, arcname=clean_filename(f["uploaded_file"].name))
        st.download_button("⬇️ Download Edited MP3s ZIP", data=zip_buffer.getvalue(), file_name=f"edited_mp3s_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
