from PIL import Image
from curator.screenshots import crop_and_save


def test_crop_and_save(tmp_path):
    src = tmp_path / "src.png"
    Image.new("RGB", (200, 200), "white").save(src)
    out = crop_and_save(str(src), (10, 10, 50, 40), str(tmp_path / "c.png"))
    saved = Image.open(out)
    assert saved.size == (50, 40)
