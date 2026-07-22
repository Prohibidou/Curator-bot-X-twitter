import io
from PIL import Image
from curator.screenshots import save_png, crop_and_save


def _png_bytes(size=(200, 200)):
    buf = io.BytesIO()
    Image.new("RGB", size, "white").save(buf, format="PNG")
    return buf.getvalue()


def test_save_png(tmp_path):
    out = save_png(_png_bytes(), str(tmp_path / "s.png"))
    assert Image.open(out).size == (200, 200)


def test_crop_and_save(tmp_path):
    src = tmp_path / "src.png"
    Image.new("RGB", (200, 200), "white").save(src)
    out = crop_and_save(str(src), (10, 10, 50, 40), str(tmp_path / "c.png"))
    assert Image.open(out).size == (50, 40)
