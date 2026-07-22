# Twitter Vision Curator Implementation Plan (v3 — CDP engine)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Refactor the toolkit so the agent controls **only Chrome** via the Chrome DevTools Protocol (CDP) instead of OS-level mouse/keyboard. Vision (screenshots) and Claude-as-brain are unchanged.

**Architecture:** Chrome is launched with `--remote-debugging-port`. The toolkit connects to that one browser over a WebSocket: screenshots via `Page.captureScreenshot`, input via `Input.dispatchMouseEvent`/`insertText`, URL via CDP metadata. The OS is never touched. A fixed device-metrics override (`deviceScaleFactor=1`) makes screenshot pixels equal click coordinates.

**Tech Stack:** Python 3.11+, `websocket-client`, `Pillow`, stdlib `urllib`, `pytest`.

## Global Constraints
- Python 3.11+ on Windows; Google Chrome.
- **Control ONLY Chrome, never the OS.** No `pyautogui`/`pygetwindow`/`mss`.
- **No APIs beyond Claude Code; no local model; no DOM/HTML parsing; no cloaking.**
- Chrome launched WITHOUT `--enable-automation` (keeps `navigator.webdriver` false).
- Report Spanish; code/tests English.
- Volume defaults `max_posts=18`, `max_replies=8`; relative top-N.
- Frequent commits; conventional messages; stage explicit files; keep `__pycache__` out.

**Unchanged from v2 (do NOT touch):** `models.py`, `humanize_math.py`, `ranker.py`,
`report.py` and their tests. **Changed/new below.**

---

### Task 1: Dependencies and config for CDP

**Files:** Modify `requirements.txt`, `src/curator/config.py`; Test `tests/test_config.py`.

**Interfaces:** `Config` gains `debug_port: int = 9222`; keeps `window_width`, `window_height`, `chrome_profile_dir`, `max_posts`, `max_replies`, `output_dir`, `action_budget`, `min_delay_s`, `max_delay_s`, `min_confidence`.

- [ ] **Step 1: Edit `requirements.txt` to exactly:**

```text
websocket-client==1.8.0
Pillow==10.4.0
pytest==8.3.3
```

- [ ] **Step 2: Edit `tests/test_config.py`** — replace the removed-fields test with:

```python
import dataclasses
from curator.config import Config


def test_defaults_present():
    c = Config.default()
    assert c.max_posts == 18
    assert c.max_replies == 8
    assert c.debug_port == 9222


def test_no_local_model_fields():
    names = {f.name for f in dataclasses.fields(Config)}
    assert "vision_model" not in names
    assert "text_model" not in names
```

- [ ] **Step 3: Run test — expect FAIL** (`debug_port` missing).
Run: `python -m pytest tests/test_config.py -v`

- [ ] **Step 4: Edit `src/curator/config.py`** — add `debug_port: int = 9222` field (keep every existing field).

- [ ] **Step 5: Run test — expect PASS (2 passed).**

- [ ] **Step 6: Commit**
```bash
git add requirements.txt src/curator/config.py tests/test_config.py
git commit -m "refactor: swap OS-input deps for websocket-client; add debug_port"
```

---

### Task 2: CDP client (`cdp.py`) — new

**Files:** Create `src/curator/cdp.py`; Test `tests/test_cdp.py`.

**Interfaces:**
- `select_target(targets: list[dict], prefer: str) -> dict` — pure: choose a `type=="page"` target whose `url` contains `prefer`, else the first page; raise `RuntimeError` if none.
- `CDP(ws)` with `send(method, params=None) -> dict` (matches response by incremental id, skips events, raises on `error`), and helpers `navigate(url)`, `screenshot() -> bytes`, `move(x,y)`, `click(x,y)`, `scroll(x,y,dy)`, `type_text(s)`, `press(key)`, `current_url() -> str`.
- `connect(port, cfg=None, prefer="x.com", ws_factory=None) -> CDP` — discover via HTTP `/json`, open WS, enable Page, set device metrics.
- `discover_ws_url(port, prefer="x.com", opener=None) -> tuple[str,str]` — returns `(ws_url, current_url)`.

- [ ] **Step 1: Write the failing test** `tests/test_cdp.py`

```python
import json
import pytest
from curator.cdp import select_target, CDP


def test_select_target_prefers_matching_url():
    targets = [{"type": "page", "url": "https://google.com", "webSocketDebuggerUrl": "ws://a"},
               {"type": "page", "url": "https://x.com/home", "webSocketDebuggerUrl": "ws://b"},
               {"type": "background_page", "url": "https://x.com/x", "webSocketDebuggerUrl": "ws://c"}]
    assert select_target(targets, "x.com")["webSocketDebuggerUrl"] == "ws://b"


def test_select_target_falls_back_to_first_page():
    targets = [{"type": "page", "url": "https://google.com", "webSocketDebuggerUrl": "ws://a"}]
    assert select_target(targets, "x.com")["webSocketDebuggerUrl"] == "ws://a"


def test_select_target_raises_when_no_page():
    with pytest.raises(RuntimeError):
        select_target([{"type": "background_page", "url": "x"}], "x.com")


class FakeWS:
    """Echoes a result for each command id; can queue events to skip."""
    def __init__(self, events=None):
        self.sent = []
        self._events = list(events or [])
        self._pending = None

    def send(self, raw):
        msg = json.loads(raw)
        self.sent.append(msg)
        self._pending = msg["id"]

    def recv(self):
        if self._events:
            return json.dumps(self._events.pop(0))  # an event (no id)
        return json.dumps({"id": self._pending, "result": {"ok": self._pending}})


def test_send_matches_id_and_skips_events():
    ws = FakeWS(events=[{"method": "Page.frameNavigated", "params": {}}])
    cdp = CDP(ws)
    result = cdp.send("Page.enable")
    assert result == {"ok": 1}
    assert ws.sent[0]["method"] == "Page.enable"
    assert ws.sent[0]["id"] == 1


def test_click_dispatches_press_and_release():
    ws = FakeWS()
    cdp = CDP(ws)
    cdp.click(10, 20)
    types = [m["params"].get("type") for m in ws.sent if m["method"] == "Input.dispatchMouseEvent"]
    assert types == ["mouseMoved", "mousePressed", "mouseReleased"]
    assert ws.sent[-1]["params"]["x"] == 10 and ws.sent[-1]["params"]["y"] == 20
```

- [ ] **Step 2: Run test — expect FAIL** (`ModuleNotFoundError`).
Run: `python -m pytest tests/test_cdp.py -v`

- [ ] **Step 3: Write `src/curator/cdp.py`**

```python
import base64
import json
import urllib.request


def select_target(targets, prefer):
    pages = [t for t in targets if t.get("type") == "page"]
    for t in pages:
        if prefer in (t.get("url") or ""):
            return t
    if pages:
        return pages[0]
    raise RuntimeError("no CDP page target found")


def discover_ws_url(port, prefer="x.com", opener=None):
    opener = opener or (lambda url: urllib.request.urlopen(url, timeout=5))
    with opener(f"http://localhost:{port}/json") as r:
        targets = json.loads(r.read().decode("utf-8"))
    t = select_target(targets, prefer)
    return t["webSocketDebuggerUrl"], t.get("url", "")


class CDP:
    def __init__(self, ws):
        self._ws = ws
        self._id = 0

    def send(self, method, params=None):
        self._id += 1
        self._ws.send(json.dumps({"id": self._id, "method": method,
                                  "params": params or {}}))
        while True:
            msg = json.loads(self._ws.recv())
            if msg.get("id") == self._id:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg.get("result", {})
            # otherwise it's an event or another id: keep reading

    def navigate(self, url):
        self.send("Page.navigate", {"url": url})

    def screenshot(self) -> bytes:
        res = self.send("Page.captureScreenshot", {"format": "png"})
        return base64.b64decode(res["data"])

    def move(self, x, y):
        self.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y})

    def click(self, x, y):
        self.move(x, y)
        for t in ("mousePressed", "mouseReleased"):
            self.send("Input.dispatchMouseEvent",
                      {"type": t, "x": x, "y": y, "button": "left", "clickCount": 1})

    def scroll(self, x, y, dy):
        self.send("Input.dispatchMouseEvent",
                  {"type": "mouseWheel", "x": x, "y": y, "deltaX": 0, "deltaY": dy})

    def type_text(self, s):
        self.send("Input.insertText", {"text": s})

    def press(self, key):
        for t in ("keyDown", "keyUp"):
            self.send("Input.dispatchKeyEvent", {"type": t, "key": key})

    def current_url(self) -> str:
        res = self.send("Page.getNavigationHistory")
        entries = res.get("entries", [])
        if not entries:
            return ""
        idx = res.get("currentIndex", len(entries) - 1)
        return entries[idx].get("url", "")


def connect(port, cfg=None, prefer="x.com", ws_factory=None):
    ws_url, _ = discover_ws_url(port, prefer)
    if ws_factory is None:
        import websocket
        ws_factory = lambda u: websocket.create_connection(u, timeout=30)
    cdp = CDP(ws_factory(ws_url))
    cdp.send("Page.enable")
    if cfg is not None:
        cdp.send("Emulation.setDeviceMetricsOverride",
                 {"width": cfg.window_width, "height": cfg.window_height,
                  "deviceScaleFactor": 1, "mobile": False})
    return cdp
```

- [ ] **Step 4: Run test — expect PASS (5 passed).**

- [ ] **Step 5: Commit**
```bash
git add src/curator/cdp.py tests/test_cdp.py
git commit -m "feat: minimal Chrome DevTools Protocol client"
```

---

### Task 3: Screenshots via bytes (`screenshots.py` rewrite)

**Files:** Overwrite `src/curator/screenshots.py`; overwrite `tests/test_screenshots.py`.

**Interfaces:** `save_png(data: bytes, path: str) -> str`; `crop_and_save(image_path, bbox, out) -> str`. Remove `set_dpi_aware`, `capture_screen`.

- [ ] **Step 1: Overwrite the test** `tests/test_screenshots.py`

```python
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
```

- [ ] **Step 2: Run test — expect FAIL** (`save_png` missing / old symbols).
Run: `python -m pytest tests/test_screenshots.py -v`

- [ ] **Step 3: Overwrite `src/curator/screenshots.py`**

```python
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
```

- [ ] **Step 4: Run test — expect PASS (2 passed).**

- [ ] **Step 5: Commit**
```bash
git add src/curator/screenshots.py tests/test_screenshots.py
git commit -m "refactor: screenshots save CDP PNG bytes (no OS capture)"
```

---

### Task 4: Human pacing over CDP (`humanize.py` rewrite)

**Files:** Overwrite `src/curator/humanize.py`; create `tests/test_humanize.py`.

**Interfaces:** `Human(cdp, cfg, rng=None)` with `pause()`, `dwell(text)`, `move_and_click(x, y)`, `scroll(clicks)`. Input is dispatched through the injected `cdp` object (which has `move`, `click`, `scroll`). Motion uses `humanize_math.bezier_path`; last cursor position starts at the viewport center.

- [ ] **Step 1: Write the failing test** `tests/test_humanize.py`

```python
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
```

- [ ] **Step 2: Run test — expect FAIL** (`ModuleNotFoundError` or old signature).
Run: `python -m pytest tests/test_humanize.py -v`

- [ ] **Step 3: Overwrite `src/curator/humanize.py`**

```python
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
```

- [ ] **Step 4: Run test — expect PASS (2 passed).**

- [ ] **Step 5: Commit**
```bash
git add src/curator/humanize.py tests/test_humanize.py
git commit -m "refactor: human pacing dispatches input through CDP"
```

---

### Task 5: Browser launch for CDP (`browser.py` rewrite)

**Files:** Overwrite `src/curator/browser.py`; keep `tests/test_browser.py` (the `search_url` test still applies — verify it passes).

**Interfaces:** `Browser(cfg)` with `search_url(topic) -> str` (unchanged), `launch()` (Chrome + `--remote-debugging-port`, profile, no `--enable-automation`), `ensure_logged_in()`. Removes `goto`, `read_current_url`, `focus`, `window_bounds` (navigation/URL now via CDP).

- [ ] **Step 1: Confirm the existing test** `tests/test_browser.py` still only asserts `search_url` (Top tab + encoding). If it references removed methods, trim it to just the `search_url` test:

```python
from curator.config import Config
from curator.browser import Browser


def test_search_url_top_tab_and_encoding():
    b = Browser(Config.default())
    url = b.search_url("mars rover")
    assert url.startswith("https://x.com/search?")
    assert "q=mars%20rover" in url or "q=mars+rover" in url
    assert "f=top" in url
```

- [ ] **Step 2: Run test — expect PASS** (search_url unchanged), then overwrite the module and re-run.
Run: `python -m pytest tests/test_browser.py -v`

- [ ] **Step 3: Overwrite `src/curator/browser.py`**

```python
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
```

- [ ] **Step 4: Run test — expect PASS (1 passed).**

- [ ] **Step 5: Commit**
```bash
git add src/curator/browser.py tests/test_browser.py
git commit -m "refactor: launch Chrome with debug port for CDP control"
```

---

### Task 6: CLI over CDP (`cli.py` rewrite)

**Files:** Overwrite `src/curator/cli.py`; overwrite `tests/test_cli.py`.

**Interfaces:**
- `build_parser()` — subcommands `launch`, `goto url`, `screenshot path`, `click x y`, `scroll clicks`, `read-url`, `crop img x y w h out`, `render-report records_json out_dir`.
- `load_run(dict) -> RunResult` (unchanged behavior).
- `dispatch(args, deps) -> int` — routes to `deps` callables. CDP-using commands call `deps["connect"]()` to get a cdp client, and `click`/`scroll` wrap it with `deps["human"](cdp)`.
- `_real_deps()` wires: `launch` (Browser), `connect` (cdp.connect with cfg+port), `human` (lambda cdp: Human(cdp,cfg)), `save_png`, `crop_and_save`, `write_outputs`.

- [ ] **Step 1: Overwrite the test** `tests/test_cli.py`

```python
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
```

- [ ] **Step 2: Run test — expect FAIL.**
Run: `python -m pytest tests/test_cli.py -v`

- [ ] **Step 3: Overwrite `src/curator/cli.py`**

```python
import argparse
import json
import sys
from curator.config import Config
from curator.models import Post, Reply, RunResult


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="curator")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("launch")
    g = sub.add_parser("goto"); g.add_argument("url")
    s = sub.add_parser("screenshot"); s.add_argument("path")
    c = sub.add_parser("click"); c.add_argument("x", type=int); c.add_argument("y", type=int)
    sc = sub.add_parser("scroll"); sc.add_argument("clicks", type=int)
    sub.add_parser("read-url")
    cr = sub.add_parser("crop")
    cr.add_argument("img"); cr.add_argument("x", type=int); cr.add_argument("y", type=int)
    cr.add_argument("w", type=int); cr.add_argument("h", type=int); cr.add_argument("out")
    rr = sub.add_parser("render-report")
    rr.add_argument("records_json"); rr.add_argument("out_dir")
    return p


def load_run(data: dict) -> RunResult:
    posts = []
    for pd in data.get("posts", []):
        replies = [Reply(**rd) for rd in pd.get("top_replies", [])]
        fields = {k: v for k, v in pd.items() if k != "top_replies"}
        posts.append(Post(top_replies=replies, **fields))
    return RunResult(topic=data["topic"], timestamp=data["timestamp"], posts=posts,
                     summary_text=data.get("summary_text", ""),
                     output_dir=data.get("output_dir", ""))


def dispatch(args, deps) -> int:
    cmd = args.cmd
    if cmd == "launch":
        deps["launch"](); return 0
    if cmd == "goto":
        deps["connect"]().navigate(args.url); return 0
    if cmd == "screenshot":
        data = deps["connect"]().screenshot(); deps["save_png"](data, args.path); return 0
    if cmd == "click":
        deps["human"](deps["connect"]()).move_and_click(args.x, args.y); return 0
    if cmd == "scroll":
        deps["human"](deps["connect"]()).scroll(args.clicks); return 0
    if cmd == "read-url":
        print(deps["connect"]().current_url()); return 0
    if cmd == "crop":
        deps["crop_and_save"](args.img, (args.x, args.y, args.w, args.h), args.out); return 0
    if cmd == "render-report":
        with open(args.records_json, encoding="utf-8") as fh:
            run = load_run(json.load(fh))
        deps["write_outputs"](run, args.out_dir); return 0
    return 1


def _real_deps():
    from curator import cdp as cdp_mod, screenshots, report
    from curator.browser import Browser
    from curator.humanize import Human
    cfg = Config.default()
    browser = Browser(cfg)
    return {
        "launch": browser.launch,
        "connect": lambda: cdp_mod.connect(cfg.debug_port, cfg),
        "human": lambda c: Human(c, cfg),
        "save_png": screenshots.save_png,
        "crop_and_save": screenshots.crop_and_save,
        "write_outputs": report.write_outputs,
    }


def main(argv=None) -> int:
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    return dispatch(args, _real_deps())


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run test — expect PASS (4 passed).**

- [ ] **Step 5: Run FULL suite — expect all pass.**
Run: `python -m pytest -v`

- [ ] **Step 6: Commit**
```bash
git add src/curator/cli.py tests/test_cli.py
git commit -m "refactor: CLI drives Chrome over CDP (screenshot/click/scroll/goto/read-url)"
```

---

### Task 7: Update runbook and README

**Files:** Overwrite `docs/AGENT_RUNBOOK.md`; edit `README.md`. No tests.

- [ ] **Step 1: Overwrite `docs/AGENT_RUNBOOK.md`**

````markdown
# Agent Runbook — how Claude drives a run (CDP engine)

Claude is the brain. `python -m curator.cli ...` are hands & eyes that control
ONLY Chrome via CDP. Coordinates are viewport pixels (device-metrics override,
scale 1) — a screenshot pixel equals a click coordinate. Pace like a human. Claude
counts its own actions and stops at `Config.action_budget`.

## Preconditions
- `pip install -r requirements.txt`; Chrome installed.
- The target account is logged in on the profile `Config.chrome_profile_dir`.
  To reuse the normal profile: fully close Chrome first, then `launch` points at
  that profile with the debug port so the existing X login carries over.

## Loop
1. `python -m curator.cli launch` — opens Chrome with the debug port.
2. Confirm the profile is logged in to the target account.
3. `python -m curator.cli goto "https://x.com/search?q=<enc>&f=top"`.
4. Until ~15–18 candidate posts (pace between steps):
   a. `screenshot shots/feed-<n>.png`; read it.
   b. Record each visible post: author, text, like/reply/repost counts, has-image, bbox.
   c. If a rate-limit / unusual-activity / login wall shows → STOP, keep data.
   d. `scroll 3`.
5. Rank; pick top posts by likes.
6. Per top post: `click` to open; `screenshot`; `read-url` for the permalink;
   `crop` the tweet + image bboxes; scroll replies, screenshot, record + rank
   replies, crop the top ones; append to `run.json`.
7. Write the Spanish `summary_text` yourself.
8. `render-report <records.json> output/<topic>-<date>`.

## Rules
- Screenshot again rather than guessing a click.
- Never exceed the focused volume / action budget.
- All control is confined to Chrome; nothing touches the OS.
````

- [ ] **Step 2: Edit `README.md`** — update the "How it works" and Setup sections to describe CDP control (only Chrome, not the OS), `websocket-client` dependency, and the debug-port note. Keep the ToS/risk WARNING block prominent and unchanged.

- [ ] **Step 3: Commit**
```bash
git add docs/AGENT_RUNBOOK.md README.md
git commit -m "docs: runbook and README for CDP (Chrome-only) engine"
```

---

## Notes for the implementer
- Delete nothing from `models.py`/`humanize_math.py`/`ranker.py`/`report.py`.
- After Task 6, the full offline suite must pass. Live CDP paths (`launch`, real
  `connect`, `screenshot`, `click`, `scroll`, `goto`, `read-url`) are validated in a
  guided live run, not pytest.
