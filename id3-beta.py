import streamlit as st
import eyed3
from PIL import Image, UnidentifiedImageError
import io
import re
import zipfile
import os
from datetime import datetime

st.set_page_config(page_title="MP3 Bulk Tag Editor", layout="wide")
st.title("🎵 MP3 Bulk Tag + Thumbnail Editor")

# ---------------------------------
# FUNCTIONS
# ---------------------------------

def resize_and_validate(img_data, max_size=800):
    try:
        img = Image.open(io.BytesIO(img_data))
        img = img.convert("RGB")
        img.thumbnail((max_size, max_size))

        out = io.BytesIO()
        img.save(out, format='JPEG', quality=90)
        return out.getvalue()

    except UnidentifiedImageError:
        return None


def parse_filename(filename):
    name = re.sub(r'\.mp3$', '', filename, flags=re.IGNORECASE)
    parts = re.split(r'\s*-\s*', name)

    if len(parts) >= 3:
        return parts[1], " - ".join(parts[2:])
    elif len(parts) == 2:
        return parts[0], parts[1]
    else:
        return "", name


def replace_cover(mp3_path, cover_data):
    audio = eyed3.load(mp3_path)
    if audio.tag is None:
        audio.initTag()

    audio.tag.images.remove_all()
    audio.tag.images.set(3, cover_data, "image/jpeg", u"Cover")
    audio.tag.save(version=eyed3.id3.ID3_V2_3)


def set_tags(mp3_path, title, artist, album, cover_data):
    audio = eyed3.load(mp3_path)
    if audio.tag is None:
        audio.initTag()

    audio.tag.title = title
    audio.tag.artist = artist
    audio.tag.album = album

    audio.tag.images.remove_all()
    audio.tag.images.set(3, cover_data, "image/jpeg", u"Cover")
    audio.tag.save(version=eyed3.id3.ID3_V2_3)


# ---------------------------------
# FILE UPLOADS
# ---------------------------------

st.sidebar.header("📤 Upload")

bulk_image = st.sidebar.file_uploader(
    "Upload BULK Thumbnail (jpg/png/webp)",
    type=["jpg", "jpeg", "png", "webp"]
)

mp3_files = st.sidebar.file_uploader(
    "Upload MP3 Files",
    type=["mp3"],
    accept_multiple_files=True
)

bulk_album = st.sidebar.text_input("Set Album for ALL")
apply_album = st.sidebar.button("Apply Album to All")

if not mp3_files:
    st.info("Upload MP3 files to get started")
    st.stop()

if bulk_image:
    bulk_img_bytes = resize_and_validate(bulk_image.read())

    if bulk_img_bytes is None:
        st.error("Invalid image file")
        st.stop()

    st.image(bulk_img_bytes, width=200)
else:
    st.warning("No bulk image uploaded yet")
    st.stop()


# ---------------------------------
# PREPARE FILES
# ---------------------------------

WORKDIR = "mp3_files"
os.makedirs(WORKDIR, exist_ok=True)

songs = []

for file in mp3_files:

    path = os.path.join(WORKDIR, file.name)
    with open(path, "wb") as f:
        f.write(file.read())

    artist, title = parse_filename(file.name)

    songs.append({
        "path": path,
        "filename": file.name,
        "artist": artist,
        "title": title,
        "album": ""
    })

# ---------------------------------
# BULK COVER APPLY
# ---------------------------------

if st.sidebar.button("🔁 APPLY BULK COVER TO ALL (REPLACE)"):
    for song in songs:
        replace_cover(song["path"], bulk_img_bytes)

    st.success("✅ Bulk cover added and old covers erased")


# ---------------------------------
# SONG EDITOR
# ---------------------------------

st.header("✏️ Edit Metadata")

for i, song in enumerate(songs):

    st.subheader(song["filename"])

    col1, col2, col3, col4 = st.columns([1, 2, 2, 2])

    with col1:
        st.image(bulk_img_bytes, width=100)

    with col2:
        title = st.text_input("Title", song["title"], key=f"title{i}")

    with col3:
        artist = st.text_input("Artist", song["artist"], key=f"artist{i}")

    with col4:
        album = st.text_input("Album", bulk_album if apply_album else song["album"], key=f"album{i}")

    song["title"]  = title
    song["artist"] = artist
    song["album"]  = album

    custom_image = st.file_uploader(
        f"Custom image for {song['filename']}",
        type=["jpg", "jpeg", "png", "webp"],
        key=f"img{i}"
    )

    if custom_image:
        custom_img_bytes = resize_and_validate(custom_image.read())
        if custom_img_bytes:
            song["cover"] = custom_img_bytes
            st.image(custom_img_bytes, width=100)
        else:
            st.warning("Invalid custom image")
    else:
        song["cover"] = bulk_img_bytes


# ---------------------------------
# SAVE BUTTON
# ---------------------------------

if st.button("💾 SAVE ALL TAGS"):

    for song in songs:
        set_tags(
            song["path"],
            song["title"],
            song["artist"],
            song["album"],
            song["cover"]
        )

    st.success("✅ All files saved with new metadata and covers")


# ---------------------------------
# ZIP DOWNLOAD
# ---------------------------------

if st.button("📦 DOWNLOAD ZIP"):

    zip_name = f"edited_mp3s_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"

    with zipfile.ZipFile(zip_name, "w") as z:
        for s in songs:
            z.write(s["path"], arcname=s["filename"])

    with open(zip_name, "rb") as f:
        st.download_button("⬇️ Download your ZIP", f, file_name=zip_name)


