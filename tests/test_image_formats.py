import io

from PIL import Image

import processor
from tests.test_process_frames import _opts, _run


def _encoded(fmt, size=(256, 128), **params):
    buffer = io.BytesIO()
    Image.new("RGBA", size, (40, 90, 200, 255)).save(buffer, fmt, **params)
    return buffer.getvalue()


def test_other_still_formats_become_png():
    for name, data in (
        ("icon.ico", _encoded("ICO", size=(256, 256), sizes=[(16, 16), (64, 64), (256, 256)])),
        ("scan.tiff", _encoded("TIFF")),
        ("old.tga", _encoded("TGA")),
        ("new.avif", _encoded("AVIF")),
    ):
        new_name, png = processor.normalize_upload(name, data)
        assert new_name.endswith(".png"), name
        with Image.open(io.BytesIO(png)) as image:
            assert image.format == "PNG"
            if name.endswith(".ico"):
                assert image.size == (256, 256), "the largest icon size is used"


def test_native_and_unknown_files_are_left_alone():
    png = _encoded("PNG")
    assert processor.normalize_upload("art.png", png) == ("art.png", png)
    assert processor.normalize_upload("clip.mp4", b"not decoded") == ("clip.mp4", b"not decoded")
    assert processor.normalize_upload("notes.xyz", b"garbage") == ("notes.xyz", b"garbage")


def test_process_job_accepts_ico_and_tiff(tmp_path, monkeypatch):
    for index, (name, data) in enumerate((("logo.ico", _encoded("ICO", size=(256, 256), sizes=[(256, 256)])),
                                           ("scan.tif", _encoded("TIFF")))):
        folder = tmp_path / str(index)
        folder.mkdir()
        opts = _opts("solid")
        opts["outline_width"] = 0
        opts["outline_fx"] = None
        _, archive = _run(folder, monkeypatch, name, data, opts)
        parts = sorted(n for n in archive.namelist() if "/part_" in n)
        assert [n.rsplit("/", 1)[1] for n in parts] == [f"part_{i}.png" for i in range(1, 6)], name


def test_grade_is_normalized_and_neutral_is_none():
    assert processor.normalize_grade({}) is None
    assert processor.normalize_grade({"brightness": 100, "contrast": 100, "saturation": 100, "hue": 0}) is None
    grade = processor.normalize_grade({"brightness": 999, "hue": "-500", "saturation": "x"})
    assert grade["brightness"] == 150 and grade["hue"] == -180 and grade["saturation"] == 100


def test_grade_image_keeps_alpha_and_brightens():
    image = Image.new("RGBA", (8, 8), (80, 80, 80, 120))
    graded = processor.grade_image(image, processor.normalize_grade({"brightness": 140}))
    assert graded.getchannel("A").getextrema() == (120, 120)
    assert graded.getpixel((0, 0))[0] > 80


def test_graded_process_job_changes_output_colour(tmp_path, monkeypatch):
    def mean(grade, folder):
        folder.mkdir()
        opts = _opts("solid")
        opts.update(outline_width=0, outline_fx=None, grade=processor.normalize_grade(grade))
        _, archive = _run(folder, monkeypatch, "art.png", _encoded("PNG", size=(750, 300)), opts)
        part = next(n for n in archive.namelist() if n.endswith("part_1.png"))
        with Image.open(io.BytesIO(archive.read(part))) as image:
            return sum(image.convert("RGB").getpixel((75, 100)))
    assert mean({"brightness": 140}, tmp_path / "a") > mean({}, tmp_path / "b")


def test_graded_gif_job_still_produces_gifs(tmp_path, monkeypatch):
    frames = [Image.new("RGB", (750, 300), (60 + i * 30, 60, 90)) for i in range(4)]
    buffer = io.BytesIO()
    frames[0].save(buffer, "GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    opts = _opts("solid")
    opts.update(outline_width=0, outline_fx=None, grade=processor.normalize_grade({"saturation": 160, "hue": 40}))
    _, archive = _run(tmp_path, monkeypatch, "clip.gif", buffer.getvalue(), opts)
    parts = sorted(n.rsplit("/", 1)[1] for n in archive.namelist() if "/part_" in n)
    assert parts == [f"part_{i}.gif" for i in range(1, 6)]


def _heic() -> bytes:
    import pytest
    if not processor.HEIF_SUPPORTED:
        pytest.skip("pillow-heif is not installed")
    buffer = io.BytesIO()
    Image.new("RGB", (320, 160), (200, 80, 40)).save(buffer, "HEIF")
    return buffer.getvalue()


def test_heic_photo_becomes_png():
    name, png = processor.normalize_upload("IMG_0001.HEIC", _heic())
    assert name == "IMG_0001.png"
    with Image.open(io.BytesIO(png)) as image:
        assert image.format == "PNG" and image.size == (320, 160)


def test_heic_without_extension_is_not_mistaken_for_video():
    from smweb.jobs import _name_with_real_extension, _sniff_extension
    data = _heic()
    assert _sniff_extension(data) == ".heic"
    assert _name_with_real_extension("photo from chat", data).endswith(".heic")


def test_process_job_accepts_heic(tmp_path, monkeypatch):
    opts = _opts("solid")
    opts["outline_width"] = 0
    opts["outline_fx"] = None
    _, archive = _run(tmp_path, monkeypatch, "IMG_0002.heic", _heic(), opts)
    parts = sorted(n for n in archive.namelist() if "/part_" in n)
    assert len(parts) == 5
