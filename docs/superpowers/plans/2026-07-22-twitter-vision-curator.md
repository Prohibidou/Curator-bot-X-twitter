# Twitter Vision Curator Implementation Plan (v2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Build a Python "hands & eyes" toolkit that a live Claude Code session drives to browse Twitter/X by vision + real OS input, collect the most popular posts/replies on a topic, screenshot them, and render a Spanish report Claude writes.

**Architecture:** The brain is the live Claude Code session (screenshot → look → decide → act loop). The toolkit is CLI subcommands: launch plain Chrome, human mouse/scroll, full-screen screenshot, crop, read-URL-from-clipboard, render report. No local model, no Ollama, no Tesseract, no automation framework, no DOM.

**Tech Stack:** Python 3.11+, `pyautogui`, `pygetwindow`, `mss`, `Pillow`, `pytest`.

## Global Constraints
- Python 3.11+ on Windows; Google Chrome installed.
- **No APIs beyond Claude Code itself; no local model; no DOM/HTML; no automation framework; no cloaking** (no fingerprint/canvas spoofing, no proxy/account rotation, no CAPTCHA solving).
- Report language **Spanish**; code/tests/comments English.
- Volume defaults `max_posts=18`, `max_replies=8`; relative top-N ranking.
- Toolkit sets the process **DPI-aware** and captures the **full primary screen**, so screenshot pixel == `pyautogui` screen coordinate.
- Human-scale pacing on every input action.
- Frequent commits; conventional messages; stage explicit files (never `git add -A`; keep `__pycache__` out).

**Status:** Task 1 (models, config) already complete on branch `feature/vision-curator` (commit 88c64e3). `models.py` provides dataclasses `Post`, `Reply`, `Element`, `ScreenModel`, `RunResult`; `config.py` provides `Config`. `Element`/`ScreenModel` are now unused (harmless; left in place).

---

### Task 2: Trim dependencies and config for the v2 engine

**Files:**
- Modify: `requirements.txt`
- Modify: `src/curator/config.py`
- Test: `tests/test_config.py` (create)

**Interfaces:**
- Consumes: existing `Config`.
- Produces: `Config` WITHOUT `vision_model` / `text_model` fields; all other fields unchanged.

- [ ] **Step 1: Write the failing test** `tests/test_config.py`

```python
import dataclasses
from curator.config import Config


def test_defaults_present():
    c = Config.default()
    assert c.max_posts == 18
    assert c.max_replies == 8
    assert c.output_dir == "output"
    assert c.action_budget == 300


def test_local_model_fields_removed():
    names = {f.name for f in dataclasses.fields(Config)}
    assert "vision_model" not in names
    assert "text_model" not in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL on `test_local_model_fields_removed` (fields still present).

- [ ] **Step 3: Edit `src/curator/config.py`** — remove the two lines `vision_model: str = "qwen2.5vl"` and `text_model: str = "qwen2.5:7b"`. Leave every other field.

- [ ] **Step 4: Edit `requirements.txt`** to exactly:

```text
pyautogui==0.9.54
PyGetWindow==0.0.9
mss==9.0.1
Pillow==10.4.0
pytest==8.3.3
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add requirements.txt src/curator/config.py tests/test_config.py
git commit -m "refactor: drop local-model deps and config fields for Claude-driven engine"
```

---

### Task 3: Screenshot capture and crop (`screenshots`)

**Files:**
- Create: `src/curator/screenshots.py`
- Test: `tests/test_screenshots.py`

**Interfaces:**
- Produces:
  - `screenshots.set_dpi_aware() -> None` — makes the process DPI-aware on Windows (no-op elsewhere / on failure).
  - `screenshots.capture_screen(path: str) -> str` — grab the full primary monitor to a PNG at `path`; return `path`.
  - `screenshots.crop_and_save(image_path: str, bbox: tuple[int,int,int,int], out: str) -> str` — crop `(x,y,w,h)` from the PNG and save to `out`; return `out`. **This is the unit-tested part.**

- [ ] **Step 1: Write the failing test** `tests/test_screenshots.py`

```python
from PIL import Image
from curator.screenshots import crop_and_save


def test_crop_and_save(tmp_path):
    src = tmp_path / "src.png"
    Image.new("RGB", (200, 200), "white").save(src)
    out = crop_and_save(str(src), (10, 10, 50, 40), str(tmp_path / "c.png"))
    saved = Image.open(out)
    assert saved.size == (50, 40)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_screenshots.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'curator.screenshots'`

- [ ] **Step 3: Write `src/curator/screenshots.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_screenshots.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/curator/screenshots.py tests/test_screenshots.py
git commit -m "feat: DPI-aware full-screen capture and crop"
```

---

### Task 4: Human-motion math (`humanize_math`)

**Files:**
- Create: `src/curator/humanize_math.py`
- Test: `tests/test_humanize_math.py`

**Interfaces:**
- Produces (`rng` is a `random.Random` so tests seed it):
  - `bezier_path(start, end, steps, rng) -> list[tuple[int,int]]` — first==start, last==end, len==steps, curved.
  - `jittered_delay(lo, hi, rng) -> float` — in `[lo,hi]`.
  - `dwell_seconds(text, wps=3.5) -> float` — reading time, min 0.4.

- [ ] **Step 1: Write the failing test** `tests/test_humanize_math.py`

```python
import random
from curator.humanize_math import bezier_path, jittered_delay, dwell_seconds


def test_bezier_endpoints_and_length():
    rng = random.Random(1)
    path = bezier_path((0, 0), (100, 50), steps=20, rng=rng)
    assert len(path) == 20
    assert path[0] == (0, 0)
    assert path[-1] == (100, 50)


def test_bezier_is_curved_not_straight():
    rng = random.Random(2)
    path = bezier_path((0, 0), (100, 0), steps=50, rng=rng)
    assert any(p[1] != 0 for p in path)


def test_jittered_delay_within_bounds():
    rng = random.Random(3)
    for _ in range(100):
        d = jittered_delay(1.0, 5.0, rng)
        assert 1.0 <= d <= 5.0


def test_dwell_scales_and_has_minimum():
    assert dwell_seconds("") >= 0.4
    assert dwell_seconds("word " * 100) > dwell_seconds("word")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_humanize_math.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `src/curator/humanize_math.py`**

```python
def bezier_path(start, end, steps, rng):
    """Quadratic Bezier from start to end with a randomized control point."""
    (x0, y0), (x1, y1) = start, end
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    offset = rng.uniform(-0.3, 0.3)
    cx = mx + (y1 - y0) * offset
    cy = my - (x1 - x0) * offset
    points = []
    for i in range(steps):
        t = i / (steps - 1) if steps > 1 else 1.0
        x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1
        y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1
        points.append((round(x), round(y)))
    points[0] = (x0, y0)
    points[-1] = (x1, y1)
    return points


def jittered_delay(lo, hi, rng):
    """Non-uniform delay in [lo, hi], biased toward the low end."""
    return rng.triangular(lo, hi, lo + (hi - lo) * 0.35)


def dwell_seconds(text, wps=3.5):
    """Estimated reading dwell time in seconds, minimum 0.4s."""
    words = len((text or "").split())
    return max(0.4, words / wps)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_humanize_math.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add src/curator/humanize_math.py tests/test_humanize_math.py
git commit -m "feat: human-motion math (bezier path, jittered delay, dwell)"
```

---

### Task 5: Human input actions (`humanize`)

**Files:**
- Create: `src/curator/humanize.py`
- Test: `tests/test_humanize.py`

**Interfaces:**
- Consumes: `humanize_math`, `config.Config`.
- Produces a `Human` class:
  - `Human(cfg, rng=None)`.
  - `pause()` / `dwell(text)` — sleep human delays.
  - `move_and_click(x, y)` — Bézier `pyautogui.moveTo` walk, then click.
  - `scroll(clicks)` — several small `pyautogui.scroll` steps with jittered pauses.
  - `spend_action() -> bool` / `budget_remaining() -> int` — action budget. **This is the unit-tested part.**

- [ ] **Step 1: Write the failing test** `tests/test_humanize.py`

```python
from curator.config import Config
from curator.humanize import Human


def test_budget_decrements_and_blocks():
    cfg = Config.default()
    cfg.action_budget = 2
    h = Human(cfg)
    assert h.spend_action() is True
    assert h.spend_action() is True
    assert h.spend_action() is False
    assert h.budget_remaining() == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_humanize.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `src/curator/humanize.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_humanize.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/curator/humanize.py tests/test_humanize.py
git commit -m "feat: human input action layer (move/click, scroll, budget)"
```

---

### Task 6: Browser lifecycle & OS navigation (`browser`)

**Files:**
- Create: `src/curator/browser.py`
- Test: `tests/test_browser.py`

**Interfaces:**
- Consumes: `config.Config`.
- Produces a `Browser` class:
  - `Browser(cfg)`.
  - `search_url(topic) -> str` — X Top-tab search URL (**unit-tested**).
  - `launch()` — plain Chrome via `subprocess` with `--user-data-dir` + geometry.
  - `focus()` — activate the Chrome window (`pygetwindow`).
  - `goto(url)` — focus, then `Ctrl+L`, type, Enter.
  - `read_current_url() -> str` — `Ctrl+L`, `Ctrl+C`, read clipboard (PowerShell `Get-Clipboard`).
  - `ensure_logged_in()` — print instructions; block on `input()`.
  - `window_bounds() -> tuple` — Chrome window bounds or config geometry.

- [ ] **Step 1: Write the failing test** `tests/test_browser.py`

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

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_browser.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `src/curator/browser.py`**

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_browser.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add src/curator/browser.py tests/test_browser.py
git commit -m "feat: plain-Chrome launch and OS-input navigation"
```

---

### Task 7: Popularity ranking (`ranker`)

**Files:**
- Create: `src/curator/ranker.py`
- Test: `tests/test_ranker.py`

**Interfaces:**
- Consumes: `models.Post`, `models.Reply`.
- Produces:
  - `top_posts(posts, n, min_confidence=0.4) -> list[Post]` — desc by likes; tie-break reposts then replies; drop `engagement_confidence < min_confidence` and `likes < 0`.
  - `top_replies(replies, m, min_confidence=0.4) -> list[Reply]` — desc by likes; same drops.

- [ ] **Step 1: Write the failing test** `tests/test_ranker.py`

```python
from curator.models import Post, Reply
from curator.ranker import top_posts, top_replies


def _post(likes, reposts=0, replies=0, conf=1.0):
    return Post(author_handle="@a", author_name="A", text="t",
                likes=likes, replies=replies, reposts=reposts,
                engagement_confidence=conf)


def test_orders_by_likes_desc():
    assert [p.likes for p in top_posts([_post(10), _post(100), _post(50)], 2)] == [100, 50]


def test_tie_breaks_by_reposts():
    assert [p.reposts for p in top_posts([_post(10, reposts=1), _post(10, reposts=9)], 2)] == [9, 1]


def test_drops_low_confidence():
    assert [p.likes for p in top_posts([_post(100, conf=0.2), _post(5, conf=0.9)], 5)] == [5]


def test_drops_unreadable_likes():
    assert [p.likes for p in top_posts([_post(-1), _post(5)], 5)] == [5]


def test_top_replies_orders_and_limits():
    reps = [Reply("@a", "A", "t", likes=3), Reply("@b", "B", "t", likes=30),
            Reply("@c", "C", "t", likes=15)]
    assert [r.likes for r in top_replies(reps, 2)] == [30, 15]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ranker.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `src/curator/ranker.py`**

```python
from curator.models import Post, Reply


def _eligible(likes, confidence, min_confidence) -> bool:
    return likes is not None and likes >= 0 and confidence >= min_confidence


def top_posts(posts, n, min_confidence=0.4):
    e = [p for p in posts if _eligible(p.likes, p.engagement_confidence, min_confidence)]
    e.sort(key=lambda p: (p.likes, p.reposts, p.replies), reverse=True)
    return e[:n]


def top_replies(replies, m, min_confidence=0.4):
    e = [r for r in replies if _eligible(r.likes, r.engagement_confidence, min_confidence)]
    e.sort(key=lambda r: r.likes, reverse=True)
    return e[:m]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ranker.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/curator/ranker.py tests/test_ranker.py
git commit -m "feat: relative popularity ranking for posts and replies"
```

---

### Task 8: Report rendering (`report`)

**Files:**
- Create: `src/curator/report.py`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `models.Post`, `models.Reply`, `models.RunResult`.
- Produces:
  - `render_markdown(run) -> str`
  - `render_html(run) -> str` (screenshots embedded as base64 when the file exists)
  - `write_outputs(run, base_dir) -> None` — writes `report.md`, `report.html`, `run.json`.
- NOTE: the Spanish `run.summary_text` is written by Claude and set before rendering; there is no `synthesize` function.

- [ ] **Step 1: Write the failing test** `tests/test_report.py`

```python
from curator.models import Post, Reply, RunResult
from curator.report import render_markdown, render_html, write_outputs


def _run():
    reply = Reply("@r", "R", "great point", likes=42)
    post = Post("@a", "Alice", "hello world", likes=100, replies=3, reposts=5,
                permalink="https://x.com/a/status/1", top_replies=[reply])
    return RunResult(topic="mars", timestamp="2026-07-22", posts=[post],
                     summary_text="Resumen en español.")


def test_markdown_includes_topic_post_reply_summary():
    md = render_markdown(_run())
    for s in ("mars", "hello world", "great point",
              "https://x.com/a/status/1", "Resumen en español."):
        assert s in md


def test_html_is_document():
    html = render_html(_run())
    assert "<html" in html.lower()
    assert "hello world" in html
    assert "Resumen en español." in html


def test_write_outputs(tmp_path):
    write_outputs(_run(), str(tmp_path))
    assert (tmp_path / "report.md").exists()
    assert (tmp_path / "report.html").exists()
    assert (tmp_path / "run.json").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_report.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `src/curator/report.py`**

```python
import base64
import json
import os
from dataclasses import asdict


def _img_tag(path: str) -> str:
    if not path or not os.path.exists(path):
        return ""
    with open(path, "rb") as fh:
        data = base64.b64encode(fh.read()).decode("ascii")
    return f'<img style="max-width:100%" src="data:image/png;base64,{data}"/>'


def render_markdown(run) -> str:
    lines = [f"# Twitter: {run.topic}", "", f"_{run.timestamp}_", "",
             "## Resumen", "", run.summary_text, "",
             "## Publicaciones destacadas", ""]
    for i, p in enumerate(run.posts, 1):
        lines += [f"### {i}. {p.author_name} ({p.author_handle}) — {p.likes} likes",
                  "", p.text, "", f"Enlace: {p.permalink}", ""]
        if p.top_replies:
            lines.append("**Respuestas destacadas:**")
            for r in p.top_replies:
                lines.append(f"- ({r.likes} likes) {r.author_handle}: {r.text}")
            lines.append("")
    return "\n".join(lines)


def render_html(run) -> str:
    parts = ["<!doctype html><html lang='es'><head><meta charset='utf-8'>",
             f"<title>Twitter: {run.topic}</title></head><body>",
             f"<h1>Twitter: {run.topic}</h1><p><em>{run.timestamp}</em></p>",
             "<h2>Resumen</h2>", f"<p>{run.summary_text}</p>",
             "<h2>Publicaciones destacadas</h2>"]
    for i, p in enumerate(run.posts, 1):
        parts.append(f"<h3>{i}. {p.author_name} ({p.author_handle}) — {p.likes} likes</h3>")
        parts.append(f"<p>{p.text}</p>")
        parts.append(_img_tag(p.screenshot_path))
        for img in p.image_screenshot_paths:
            parts.append(_img_tag(img))
        parts.append(f"<p>Enlace: <a href='{p.permalink}'>{p.permalink}</a></p>")
        if p.top_replies:
            parts.append("<h4>Respuestas destacadas</h4><ul>")
            for r in p.top_replies:
                parts.append(f"<li>({r.likes} likes) {r.author_handle}: {r.text} "
                             f"{_img_tag(r.screenshot_path)}</li>")
            parts.append("</ul>")
    parts.append("</body></html>")
    return "".join(parts)


def write_outputs(run, base_dir: str) -> None:
    os.makedirs(base_dir, exist_ok=True)
    with open(os.path.join(base_dir, "report.md"), "w", encoding="utf-8") as fh:
        fh.write(render_markdown(run))
    with open(os.path.join(base_dir, "report.html"), "w", encoding="utf-8") as fh:
        fh.write(render_html(run))
    with open(os.path.join(base_dir, "run.json"), "w", encoding="utf-8") as fh:
        json.dump(asdict(run), fh, ensure_ascii=False, indent=2)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_report.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add src/curator/report.py tests/test_report.py
git commit -m "feat: Markdown/HTML/JSON report rendering"
```

---

### Task 9: CLI toolkit (`cli`)

**Files:**
- Create: `src/curator/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: all modules above.
- Produces:
  - `cli.build_parser() -> argparse.ArgumentParser` with subcommands: `launch`, `goto url`, `screenshot path`, `click x y`, `scroll clicks`, `read-url`, `crop img x y w h out`, `render-report records_json out_dir`.
  - `cli.load_run(data: dict) -> RunResult` — rebuild `RunResult`/`Post`/`Reply` dataclasses from a plain dict (the JSON Claude writes).
  - `cli.dispatch(args, deps) -> int` — run the chosen subcommand; `deps` is a dict of callables so tests can inject fakes. Real `main()` supplies real deps and calls `screenshots.set_dpi_aware()` first.
- Both `load_run` and `dispatch` routing are **unit-tested** with fakes; real device commands are validated live.

- [ ] **Step 1: Write the failing test** `tests/test_cli.py`

```python
import json
from curator.cli import build_parser, load_run, dispatch


def test_load_run_rebuilds_dataclasses():
    data = {"topic": "t", "timestamp": "2026-07-22", "summary_text": "s",
            "output_dir": "o",
            "posts": [{"author_handle": "@a", "author_name": "A", "text": "x",
                       "likes": 5, "replies": 0, "reposts": 0,
                       "top_replies": [{"author_handle": "@b", "author_name": "B",
                                        "text": "y", "likes": 1}]}]}
    run = load_run(data)
    assert run.topic == "t"
    assert run.posts[0].likes == 5
    assert run.posts[0].top_replies[0].author_handle == "@b"


def test_dispatch_routes_crop_to_dep():
    calls = {}
    deps = {"crop_and_save": lambda img, bbox, out: calls.setdefault("crop", (img, bbox, out))}
    parser = build_parser()
    args = parser.parse_args(["crop", "in.png", "1", "2", "3", "4", "out.png"])
    rc = dispatch(args, deps)
    assert rc == 0
    assert calls["crop"] == ("in.png", (1, 2, 3, 4), "out.png")


def test_dispatch_routes_render_report(tmp_path):
    data = {"topic": "t", "timestamp": "d", "summary_text": "s", "output_dir": "",
            "posts": []}
    p = tmp_path / "rec.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    written = {}
    deps = {"write_outputs": lambda run, out: written.setdefault("w", (run.topic, out))}
    args = build_parser().parse_args(["render-report", str(p), str(tmp_path / "out")])
    rc = dispatch(args, deps)
    assert rc == 0
    assert written["w"][0] == "t"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `src/curator/cli.py`**

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
    return RunResult(topic=data["topic"], timestamp=data["timestamp"],
                     posts=posts, summary_text=data.get("summary_text", ""),
                     output_dir=data.get("output_dir", ""))


def dispatch(args, deps) -> int:
    cmd = args.cmd
    if cmd == "launch":
        deps["launch"](); return 0
    if cmd == "goto":
        deps["goto"](args.url); return 0
    if cmd == "screenshot":
        deps["capture_screen"](args.path); return 0
    if cmd == "click":
        deps["move_and_click"](args.x, args.y); return 0
    if cmd == "scroll":
        deps["scroll"](args.clicks); return 0
    if cmd == "read-url":
        print(deps["read_current_url"]()); return 0
    if cmd == "crop":
        deps["crop_and_save"](args.img, (args.x, args.y, args.w, args.h), args.out)
        return 0
    if cmd == "render-report":
        with open(args.records_json, encoding="utf-8") as fh:
            run = load_run(json.load(fh))
        deps["write_outputs"](run, args.out_dir); return 0
    return 1


def _real_deps():
    from curator import screenshots, report
    from curator.browser import Browser
    from curator.humanize import Human
    cfg = Config.default()
    browser = Browser(cfg)
    human = Human(cfg)
    return {
        "launch": browser.launch,
        "goto": browser.goto,
        "read_current_url": browser.read_current_url,
        "capture_screen": screenshots.capture_screen,
        "crop_and_save": screenshots.crop_and_save,
        "move_and_click": human.move_and_click,
        "scroll": human.scroll,
        "write_outputs": report.write_outputs,
    }


def main(argv=None) -> int:
    from curator import screenshots
    screenshots.set_dpi_aware()
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    return dispatch(args, _real_deps())


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -v`
Expected: PASS (all tests from Tasks 1–9).

- [ ] **Step 6: Commit**

```bash
git add src/curator/cli.py tests/test_cli.py
git commit -m "feat: CLI toolkit wiring launch/goto/screenshot/click/scroll/crop/render"
```

---

### Task 10: Agent runbook and README

**Files:**
- Create: `docs/AGENT_RUNBOOK.md`
- Modify: `README.md`

No tests (documentation). Deliverable is the runbook Claude follows to drive a live run, plus updated setup/risk docs.

- [ ] **Step 1: Write `docs/AGENT_RUNBOOK.md`**

````markdown
# Agent Runbook — how Claude drives a run

Claude is the brain. The Python CLI (`python -m curator.cli ...`) is hands & eyes.
All coordinates are full-screen pixels (process is DPI-aware). Pace like a human.

## Preconditions
- `pip install -r requirements.txt`; Chrome installed; throwaway X account ready.
- Ideally set Windows display scaling to 100%.

## Loop
1. `python -m curator.cli launch` — opens Chrome on the dedicated profile.
2. Tell the user to log in by hand; wait for confirmation.
3. `python -m curator.cli goto "<search Top-tab URL for the topic>"`.
   Build the URL with `Browser.search_url` semantics: `https://x.com/search?q=<enc>&f=top`.
4. Repeat until enough candidate posts (aim ~15–18), pacing between steps:
   a. `python -m curator.cli screenshot shots/feed-<n>.png`
   b. Read the PNG. Record each visible post: author, text, like/reply/repost
      counts, whether it has an image, and the on-screen bbox.
   c. If a rate-limit / unusual-activity / login wall is visible → STOP, keep data.
   d. `python -m curator.cli scroll 3`
5. Rank candidates (or call ranker); pick top posts by likes.
6. Per top post, pacing between steps:
   a. `click` its location to open it; `screenshot`; `read-url` for the permalink.
   b. Pick the tweet bbox and image bboxes; `crop` each into `shots/`.
   c. Scroll replies, `screenshot`, record replies + like counts.
   d. Rank replies; `crop` the top ones.
   e. Append to `run.json` (incremental).
7. Write the Spanish narrative `summary_text` yourself from the collected text.
8. Save the final records JSON and run
   `python -m curator.cli render-report <records.json> output/<topic>-<date>`.

## Rules
- Never rush: pause between actions; dwell on posts before moving on.
- Never open more than the focused volume; stop at the action budget.
- If unsure what's on screen, screenshot again rather than guessing a click.
````

- [ ] **Step 2: Overwrite `README.md`**

```markdown
# Twitter Vision Curator

A local agent that a live Claude Code session drives to browse X/Twitter by
vision only (screenshots) and real OS mouse/keyboard input, then writes a
Spanish report of the most popular posts/replies on a topic.

## WARNING
Automating a logged-in account violates X's Terms of Service. Use a throwaway
account you are willing to lose. This tool paces itself like a human to avoid
being blocked; it does NOT and cannot guarantee you won't be detected or
suspended. There is no fingerprint spoofing, proxy rotation, or CAPTCHA solving.

## How it works
- Python toolkit (`curator.cli`) = hands & eyes: launch Chrome, human
  mouse/scroll, screenshot, crop, read URL, render report.
- Claude Code = brain: looks at screenshots, decides human actions, writes the
  Spanish report. See `docs/AGENT_RUNBOOK.md`.
- No Twitter API, no local model, no DOM, no automation framework.

## Setup
1. Install Python 3.11+ and Google Chrome.
2. `pip install -r requirements.txt`
3. (Recommended) set Windows display scaling to 100%.
4. Have a throwaway X account; you log in by hand on first launch.

## Use
Ask Claude Code to run a topic; it follows `docs/AGENT_RUNBOOK.md`, driving
`python -m curator.cli ...` and looking at the screenshots.
```

- [ ] **Step 3: Commit**

```bash
git add docs/AGENT_RUNBOOK.md README.md
git commit -m "docs: agent runbook and README for Claude-driven engine"
```

---

## Notes for the implementer
- Tasks 2–9 unit tests are fully offline and must pass. Live device commands
  (`launch`, `goto`, `click`, `scroll`, real `screenshot`, `read-url`) and the
  full Claude-driven loop are validated in a guided live run, not pytest.
- Keep the ToS/risk notice prominent in `README.md`.
