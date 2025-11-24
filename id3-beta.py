# id3-beta.py
# Streamlit MP3 Bulk Tag + Thumbnail Editor
# Run: streamlit run id3-beta.py

import streamlit as st
import eyed3
from PIL import Image, UnidentifiedImageError
import io
import re
import zipfile
import os
from datetime import datetime
from pathlib import Path

st.set_page_config(page_title="MP3 Bulk Tag Editor", layout="wide")
st.title("🎵 MP3 Bulk Tag + Thumbnail Editor")

WORKDIR = Path("uploaded_mp3s")
WORKDIR.mkdir(exist_ok=True)


# ---------------------------- HELPERS ---------------------------------

def resize_and_validate(img_bytes, max_size=800):
    try:
        img = Image.open(io.BytesIO(img_bytes))
        img = img.convert("RGB")
        img.thumbnail((max_size, max_size))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=90)
        return out.getvalue()
    except UnidentifiedImageError:
        return None
    except:
        return None


def parse_filename(fname):
    name = re.sub(r'\.mp3$', '', fname, flags=re.I)
    parts = re.split(r'\s*-\s*', name)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) >= 3:
        return parts[1], " - ".join(parts[2:])
    elif len(parts) == 2:
        return parts[0], parts[1]
    else:
        return "", parts[0] if parts else fname


def safe_clear_images(audio):
    if audio is None or audio.tag is None:
        return

    # Method 1
    try:
        if hasattr(audio.tag.images, "remove_all"):
            audio.tag.images.remove_all()
            return
    except:
        pass

    # Method 2
    try:
        if hasattr(audio.tag.images, "_images"):
            audio.tag.images._images.clear()
            return
    except:
        pass

    # Method 3
    try:
        for img in list(audio.tag.images):
            try:
                ptype = getattr(img, "picture_type", None)
                if ptype is not None:
                    audio.tag.images.remove(ptype)
            except:
                pass
    except:
        pass


def embed_cover(audio, cover_bytes):
    if audio.tag is None:
        audio.initTag()

    safe_clear_images(audio)

    audio.tag.images.set(3, cover_bytes, "image/jpeg", u"Cover")


def set_tags(filepath, title, artist, album, cover, track=None):
    audio = eyed3.load(filepath)

    if audio is None:
        return

    if audio.tag is None:
        audio.initTag()

    audio.tag.title = title or None
    audio.tag.artist = artist or None
    audio.tag.album = album or None

    if track:
        audio.tag.track_num = (track, None)

    if cover:
        embed_cover(audio, cover)

    audio.tag.save(version=eyed3.id3.ID3_V2_3)


def save_files(uploaded):
    paths = []
    for f in uploaded:
        target = WORKDIR / f.name
        with open(target, "wb") as out:
            out.write(f.getvalue())
        paths.append(str(target))
    return paths


def clean_name(name):
    return re.sub(r"\s*\(\d+\)(?=\.\w+$)", "", name)


# ---------------------------- SIDEBAR ---------------------------------

st.sidebar.title("Upload")

mp3_upload = st.sidebar.file_uploader("Upload MP3(s)", type=["mp3"], accept_multiple_files=True)
zip_upload = st.sidebar.file_uploader("Upload ZIP", type=["zip"])
bulk_image = st.sidebar.file_uploader("Bulk Thumbnail", type=["jpg","jpeg","png","webp"])

auto_track = st.sidebar.checkbox("Auto track numbers")
apply_album_all = st.sidebar.text_input("Album for all")
apply_album_btn = st.sidebar.button("Apply Album To All")
apply_cover_btn = st.sidebar.button("Apply BULK COVER (REPLACE ALL)")


# unzip if zip uploaded
if zip_upload:
    zip_path = WORKDIR / zip_upload.name
    with open(zip_path, "wb") as f:
        f.write(zip_upload.getvalue())

    with zipfile.ZipFile(zip_path) as z:
        z.extractall(WORKDIR)

    zip_path.unlink()
    st.sidebar.success("ZIP extracted")


# save mp3 uploads
if mp3_upload:
    save_files(mp3_upload)


# get all mp3s in folder
mp3_files = sorted([str(p) for p in WORKDIR.glob("*.mp3")])

if not mp3_files:
    st.warning("Upload MP3 or ZIP to begin")
    st.stop()


# process bulk image
bulk_img_data = None
if bulk_image:
    bulk_img_data = resize_and_validate(bulk_image.getvalue())
    if bulk_img_data is None:
        st.sidebar.error("Invalid image file")


# Apply bulk cover immediately
if apply_cover_btn and bulk_img_data:
    for m in mp3_files:
        audio = eyed3.load(m)
        if audio:
            embed_cover(audio, bulk_img_data)
            audio.tag.save(version=eyed3.id3.ID3_V2_3)

    st.sidebar.success("Bulk cover applied to all files")


# ---------------------------- MAIN ---------------------------------

st.header("Edit MP3 Tags")

songs = []

for i, path in enumerate(mp3_files):
    filename = os.path.basename(path)
    default_artist, default_title = parse_filename(filename)

    audio = eyed3.load(path)

    if audio and audio.tag:
        title = audio.tag.title or default_title
        artist = audio.tag.artist or default_artist
        album = audio.tag.album or ""
    else:
        title = default_title
        artist = default_artist
        album = ""

    songs.append({
        "path": path,
        "filename": filename,
        "title": title,
        "artist": artist,
        "album": album
    })


for i, song in enumerate(songs):

    st.subheader(f"{i+1}. {song['filename']}")

    c1, c2, c3, c4, c5 = st.columns([3,3,3,2,2])

    with c1:
        song["title"] = st.text_input("Title", song["title"], key=f"t{i}")

    with c2:
        song["artist"] = st.text_input("Artist", song["artist"], key=f"a{i}")

    with c3:
        album_val = apply_album_all if apply_album_btn and apply_album_all else song["album"]
        song["album"] = st.text_input("Album", album_val, key=f"al{i}")

    with c4:
        track_val = i+1 if auto_track else ""
        song["track"] = st.text_input("Track #", track_val, key=f"tr{i}")

    with c5:
        custom = st.file_uploader("Cover", type=["jpg","png","jpeg","webp"], key=f"c{i}")
        song["custom_cover"] = None

        if custom:
            img = resize_and_validate(custom.getvalue())
            if img:
                song["custom_cover"] = img
                st.image(img, width=80)


# ---------------------------- ACTIONS ---------------------------------

if st.button("💾 SAVE ALL TAGS"):

    for i, song in enumerate(songs):
        cover = song["custom_cover"] or bulk_img_data

        try:
            track = int(song["track"]) if song["track"] else None
        except:
            track = None

        set_tags(
            song["path"],
            song["title"],
            song["artist"],
            song["album"],
            cover,
            track
        )

    st.success("All tags saved successfully ✅")


if st.button("📦 DOWNLOAD ZIP"):
    zip_name = f"edited_mp3s_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

    with zipfile.ZipFile(zip_name, "w") as z:
        for song in songs:
            arc = clean_name(song["filename"])
            z.write(song["path"], arc)

    with open(zip_name, "rb") as f:
        st.download_button("Download", f, file_name=zip_name)

    os.remove(zip_name)






