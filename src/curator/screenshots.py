import os
from PIL import Image


def set_dpi_aware() -> None:
    """Make the process DPI-aware so screenshot pixels match pyautogui coords."""
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def capture_screen(path: str) -> str:
    import mss
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with mss.mss() as sct:
        # Assumes the primary monitor is at origin (0, 0), so screenshot pixel
        # coordinates line up 1:1 with pyautogui screen coordinates.
        mon = sct.monitors[1]  # primary monitor
        shot = sct.grab(mon)
        img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        img.save(path)
    return path


def crop_and_save(image_path: str, bbox, out: str) -> str:
    x, y, w, h = bbox
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    Image.open(image_path).crop((x, y, x + w, y + h)).save(out)
    return out
