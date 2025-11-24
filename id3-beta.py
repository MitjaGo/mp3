# id3-beta.py
# Streamlit MP3 Bulk Tag + Thumbnail Editor
# Save as id3-beta.py and run: streamlit run id3-beta.py

import streamlit as st
import eyed3
from PIL import Image, UnidentifiedImageError
import io
import re
import zipfile
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple

st.set_page_config(page_title="MP3 Bulk Tag Editor", layout="wide")
st.title("🎵 MP3 Bulk Tag + Thumbnail Editor (id3-beta)")

# ------------------------
# Helpers
# ------------------------

def resize_and_validate(img_bytes: bytes, max_size: int = 800) -> Optional[bytes]:
    """Return JPEG bytes resized, or None if invalid image."""
    try:
        img = Image.open(io.BytesIO(img_bytes))
        img = img.convert("RGB")
        img.thumbnail((max_size, max_size))
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=90)
        return out.getvalue()
    except UnidentifiedImageError:
        return None
    except Exception as e:
        st.error(f"Image processing error: {e}")
        return None

def parse_filename(fname: str) -> Tuple[str,str]:
    """
    Parse '01 - Artist - Title.mp3' or 'Artist - Title.mp3'
    Returns (artist, title)
    """
    name = re.sub(r'\.mp3$', '', fname, flags=re.IGNORECASE)
    parts = re.split(r'\s*-\s*', name)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= 3:
        return parts[1], " - ".join(parts[2:])
    elif len(parts) == 2:
        return parts[0], parts[1]
    else:
        return "", parts[0] if parts else fname

def safe_clear_images(audio):
    """Clear existing images in tag in a way compatible with different eyeD3 versions."""
    if audio is None:
        return
    if audio.tag is None:
        return
    try:
        # preferred: if remove_all exists
        if hasattr(audio.tag.images, "remove_all"):
            audio.tag.images.remove_all()
            return
    except Exception:
        pass

    # Fallback 1: clear private list (works in many eyeD3 versions)
    try:
        imgs = getattr(audio.tag.images, "_images", None)
        if isinstance(imgs, list):
            imgs.clear()
            return
    except Exception:
        pass

    # Fallback 2: iterate and remove by picture type (best-effort)
    try:
        # make a copy of images to avoid modifying while iterating
        current = list(audio.tag.images)
        for entry in current:
            try:
                # each entry typically has .picture_type attribute
                pic_type = getattr(entry, "picture_type", None)
                if pic_type is not None:
                    audio.tag.images.remove(pic_type)
            except Exception:
                # try removing by index: not guaranteed to exist
                try:
                    audio.tag.images.remove(entry)
                except Exception:
                    pass
    except Exception:
        # final fallback: attempt to set _images to empty list
        try:
            audio.tag.images._images = []
        except Exception:
            pass

def embed_cover(audio, cover_bytes: bytes):
    """Replace cover art with cover_bytes (JPEG bytes)."""
    if audio is None:
        return
    if audio.tag is None:
        audio.initTag()
    safe_clear_images(audio)
    try:
        audio.tag.images.set(3, cover_bytes, "image/jpeg", u"Cover")
    except Exception:
        # fallback to add without specifying picture type
        try:
            audio.tag.images.set(0x03, cover_bytes, "image/jpeg", u"Cover")
        except Exception as e:
            st.warning(f"Could not set cover for {getattr(audio, 'path', 'unknown')}: {e}")

def set_tags(path: str, title: Optional[str], artist: Optional[str], album: Optional[str], cover: Optional[bytes], track_num: Optional[int]=None):
    audio = eyed3.load(path)
    if audio is None:
        st.warning(f"Could not open: {path}")
        return
    if audio.tag is None:
        audio.initTag()

    if title is not None:
        audio.tag.title = title or None
    if artist is not None:
        audio.tag.artist = artist or None
    if album is not None:
        audio.tag.album = album or None
    if



