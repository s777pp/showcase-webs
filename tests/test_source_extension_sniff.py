from smweb.jobs import _name_with_real_extension, _sniff_extension


def test_downloader_names_without_extension_use_the_file_bytes():
    # Klickpin names keep "Klickpin.com" and lose the real ".mp4" to length limits.
    mp4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 20
    assert _name_with_real_extension("From Klickpin.com- Beachy summer-p", mp4) == "From Klickpin_com- Beachy summer-p.mp4"
    assert _name_with_real_extension("From Klickpin.com- pic", b"\xff\xd8\xff\xe0" + b"\x00" * 20).endswith(".jpg")


def test_known_extensions_and_unknown_bytes_are_left_alone():
    assert _name_with_real_extension("clip.mp4", b"not really") == "clip.mp4"
    assert _name_with_real_extension("notes.txt", b"plain text") == "notes.txt"


def test_sniff_covers_supported_containers():
    assert _sniff_extension(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8) == ".png"
    assert _sniff_extension(b"GIF89a" + b"\x00" * 8) == ".gif"
    assert _sniff_extension(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == ".webp"
    assert _sniff_extension(b"\x1a\x45\xdf\xa3" + b"\x00" * 8) == ".webm"
    assert _sniff_extension(b"\x00\x00\x00\x14ftypqt  " + b"\x00" * 8) == ".mov"
