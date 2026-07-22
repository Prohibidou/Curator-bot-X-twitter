import random
import time
from curator.humanize_math import bezier_path, jittered_delay, dwell_seconds


class Human:
    def __init__(self, cdp, cfg, rng=None):
        self.cdp = cdp
        self.cfg = cfg
        self.rng = rng or random.Random()
        self._x = cfg.window_width // 2
        self._y = cfg.window_height // 2

    def pause(self):
        time.sleep(jittered_delay(self.cfg.min_delay_s, self.cfg.max_delay_s, self.rng))

    def dwell(self, text):
        time.sleep(dwell_seconds(text))

    def move_and_click(self, x, y):
        steps = self.rng.randint(18, 32)
        for px, py in bezier_path((self._x, self._y), (x, y), steps, self.rng):
            self.cdp.move(px, py)
            time.sleep(0.005)
        self._x, self._y = x, y
        self.pause()
        self.cdp.click(x, y)

    def scroll(self, clicks):
        cx, cy = self.cfg.window_width // 2, self.cfg.window_height // 2
        dy = 300 if clicks > 0 else -300
        for _ in range(abs(clicks)):
            self.cdp.scroll(cx, cy, dy)
            time.sleep(jittered_delay(0.2, 0.8, self.rng))
