import json
from curator.cli import build_parser, load_run, dispatch


class FakeCDP:
    def __init__(self): self.calls = []
    def navigate(self, url): self.calls.append(("navigate", url))
    def screenshot(self): self.calls.append(("screenshot",)); return b"PNGDATA"
    def current_url(self): return "https://x.com/u/status/9"


def test_load_run_rebuilds_dataclasses():
    data = {"topic": "t", "timestamp": "d", "summary_text": "s", "output_dir": "o",
            "posts": [{"author_handle": "@a", "author_name": "A", "text": "x",
                       "likes": 5, "replies": 0, "reposts": 0,
                       "top_replies": [{"author_handle": "@b", "author_name": "B",
                                        "text": "y", "likes": 1}]}]}
    run = load_run(data)
    assert run.posts[0].top_replies[0].author_handle == "@b"


def test_dispatch_screenshot_saves_bytes():
    cdp = FakeCDP()
    saved = {}
    deps = {"connect": lambda: cdp,
            "save_png": lambda data, path: saved.setdefault("s", (data, path))}
    args = build_parser().parse_args(["screenshot", "out.png"])
    assert dispatch(args, deps) == 0
    assert saved["s"] == (b"PNGDATA", "out.png")


def test_dispatch_click_uses_human_over_cdp():
    cdp = FakeCDP()
    clicked = {}
    class FakeHuman:
        def __init__(self, c): self.c = c
        def move_and_click(self, x, y): clicked["xy"] = (x, y)
    deps = {"connect": lambda: cdp, "human": lambda c: FakeHuman(c)}
    args = build_parser().parse_args(["click", "12", "34"])
    assert dispatch(args, deps) == 0
    assert clicked["xy"] == (12, 34)


def test_dispatch_read_url_prints(capsys):
    deps = {"connect": lambda: FakeCDP()}
    args = build_parser().parse_args(["read-url"])
    assert dispatch(args, deps) == 0
    assert "x.com/u/status/9" in capsys.readouterr().out
