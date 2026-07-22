import os
from PIL import Image


def save_png(data: bytes, path: str) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def crop_and_save(image_path: str, bbox, out: str) -> str:
    x, y, w, h = bbox
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    Image.open(image_path).crop((x, y, x + w, y + h)).save(out)
    return out
