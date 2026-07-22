import random
from curator.config import Config
from curator.humanize import Human


class FakeCDP:
    def __init__(self):
        self.moves = []
        self.clicks = []
        self.scrolls = []
    def move(self, x, y): self.moves.append((x, y))
    def click(self, x, y): self.clicks.append((x, y))
    def scroll(self, x, y, dy): self.scrolls.append((x, y, dy))


def test_move_and_click_walks_path_then_clicks():
    cdp = FakeCDP()
    h = Human(cdp, Config.default(), rng=random.Random(0))
    h.move_and_click(300, 400)
    assert len(cdp.moves) >= 5           # walked a path
    assert cdp.moves[-1] == (300, 400)   # ended on target
    assert cdp.clicks == [(300, 400)]    # clicked once at target


def test_scroll_issues_one_event_per_click():
    cdp = FakeCDP()
    h = Human(cdp, Config.default(), rng=random.Random(0))
    h.scroll(3)
    assert len(cdp.scrolls) == 3
    assert all(s[2] > 0 for s in cdp.scrolls)   # positive dy = scroll down
