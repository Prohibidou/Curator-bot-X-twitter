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
                f"--remote-debugging-port={c.debug_port}",
                f"--user-data-dir={c.chrome_profile_dir}",
                f"--window-size={c.window_width},{c.window_height}",
                "https://x.com/home"]
        # NOTE: intentionally NO --enable-automation (keeps navigator.webdriver false).
        self.proc = subprocess.Popen(args)
        time.sleep(6)

    def ensure_logged_in(self):
        print("Confirm the opened Chrome is logged in to the target X account.")
        input("Press Enter once you can see the X home feed...")
