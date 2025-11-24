# ---------------------------------------
# Step 4: Edit Tags (Title, Artist, Album, Cover) with live preview
# ---------------------------------------
st.header("📝 Edit Tags (Individual Album per Song)")
edited_tracks = []

for i, mp3_file in enumerate(uploaded_mp3s[:50]):
    st.subheader(f"🎵 {mp3_file.name}")
    
    # Smart filename parser
    artist_guess, title_guess = parse_filename_artist_title(mp3_file.name)
    
    # Show live preview
    st.markdown(f"**Filename Parsing Preview:** Artist: `{artist_guess}` | Title: `{title_guess}`")

    # Save uploaded MP3 to temp
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp.write(mp3_file.getvalue())
    tmp_path = tmp.name
    tmp.close()

    # Load existing ID3 tags
    try:
        audio_tags = ID3(tmp_path)
    except ID3NoHeaderError:
        audio_tags = ID3()

    # Use parsed values as default if ID3 empty
    title_val = audio_tags.get('TIT2').text[0] if 'TIT2' in audio_tags else title_guess
    artist_val = audio_tags.get('TPE1').text[0] if 'TPE1' in audio_tags else artist_guess
    album_val = audio_tags.get('TALB').text[0] if 'TALB' in audio_tags else ""

    # Input fields
    cols = st.columns(4)
    with cols[0]:
        title = st.text_input("Title", value=title_val or "", key=f"title_{i}")
    with cols[1]:
        artist = st.text_input("Artist", value=artist_val or "", key=f"artist_{i}")
    with cols[2]:
        album = st.text_input("Album (Individual)", value=album_val or "", key=f"album_{i}")
    with cols[3]:
        img_upload = st.file_uploader(f"Thumbnail ({mp3_file.name})", type=["jpg","jpeg","png"], key=f"img_{i}")

    img_data = resize_jpeg(img_upload.getvalue()) if img_upload else default_img_data
    st.image(img_data, width=100, caption="Cover Preview")

    # Decide final album: bulk_album overrides individual if filled
    final_album = bulk_album.strip() if bulk_album.strip() else album.strip()

    edited_tracks.append({
        "file": mp3_file,
        "title": title.strip(),
        "artist": artist.strip(),
        "album": final_album,
        "image": img_data,
        "tmp_path": tmp_path
    })



















