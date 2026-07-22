import shutil
import subprocess
import time
import urllib.parse


class Browser:
    def __init__(self, cfg):
        self.cfg = cfg
        self.proc = None

    def search_url(self, topic: str) -> str:
        q = urllib.parse.quote(topic)
        return f"https://x.com/search?q={q}&f=top"

    def _chrome_path(self) -> str:
        for name in ("chrome", "google-chrome", "chrome.exe"):
            found = shutil.which(name)
            if found:
                return found
        return r"C:\Program Files\Google\Chrome\Application\chrome.exe"

    def launch(self):
        c = self.cfg
        args = [self._chrome_path(),
                f"--user-data-dir={c.chrome_profile_dir}",
                f"--window-position={c.window_left},{c.window_top}",
                f"--window-size={c.window_width},{c.window_height}",
                "--new-window", "https://x.com/home"]
        self.proc = subprocess.Popen(args)
        time.sleep(6)

    def focus(self):
        import pygetwindow as gw
        wins = [w for w in gw.getAllWindows() if "Chrome" in w.title]
        if wins:
            try:
                wins[0].activate()
            except Exception:
                pass
            time.sleep(0.5)

    def goto(self, url: str):
        import pyautogui
        self.focus()
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.5)
        pyautogui.typewrite(url, interval=0.02)
        pyautogui.press("enter")
        time.sleep(4)

    def read_current_url(self) -> str:
        import pyautogui, subprocess as sp
        self.focus()
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.3)
        out = sp.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                     capture_output=True, text=True)
        pyautogui.press("escape")
        return out.stdout.strip()

    def ensure_logged_in(self):
        print("Log in to your throwaway X account in the opened Chrome window.")
        input("Press Enter here once you are logged in and see your home feed...")

    def window_bounds(self):
        import pygetwindow as gw
        wins = [w for w in gw.getAllWindows() if "Chrome" in w.title]
        if not wins:
            c = self.cfg
            return (c.window_left, c.window_top, c.window_width, c.window_height)
        w = wins[0]
        return (w.left, w.top, w.width, w.height)
