import random
import time
from curator.humanize_math import bezier_path, jittered_delay, dwell_seconds


class Human:
    def __init__(self, cfg, rng=None):
        self.cfg = cfg
        self.rng = rng or random.Random()
        self._budget = cfg.action_budget

    def pause(self):
        time.sleep(jittered_delay(self.cfg.min_delay_s, self.cfg.max_delay_s, self.rng))

    def dwell(self, text):
        time.sleep(dwell_seconds(text))

    def move_and_click(self, x, y):
        import pyautogui
        start = pyautogui.position()
        steps = self.rng.randint(18, 32)
        for px, py in bezier_path((start[0], start[1]), (x, y), steps, self.rng):
            pyautogui.moveTo(px, py, duration=0)
            time.sleep(0.005)
        self.pause()
        pyautogui.click()

    def scroll(self, clicks):
        import pyautogui
        step = -120 if clicks > 0 else 120
        for _ in range(abs(clicks)):
            pyautogui.scroll(step)
            time.sleep(jittered_delay(0.2, 0.8, self.rng))

    def spend_action(self) -> bool:
        if self._budget <= 0:
            return False
        self._budget -= 1
        return True

    def budget_remaining(self) -> int:
        return self._budget
