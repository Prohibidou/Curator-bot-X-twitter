# Twitter Vision Curator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local, no-API desktop agent that browses Twitter/X purely by computer vision + real OS input, collects the most popular posts and replies on a given topic, screenshots them, and writes a Spanish narrative report.

**Architecture:** Plain Chrome is launched as an ordinary process (no automation framework) and driven by real mouse/keyboard input. Perception is 100% screenshot-based: qwen2.5vl (Ollama) for layout + Tesseract for exact text/numbers. Pure-logic modules (models, ranker, number parsing, humanize math, report rendering) are TDD-tested against fixtures; the browser/vision/agent glue is validated manually.

**Tech Stack:** Python 3.11+, Ollama (qwen2.5vl + a text model), Tesseract OCR, `pyautogui`, `pygetwindow`, `mss`, `Pillow`, `pytesseract`, `ollama` python client, `pytest`.

## Global Constraints

- Python 3.11+ on Windows. Google Chrome installed.
- **No APIs**: no Twitter/X API, no cloud LLM. Only local Ollama + Tesseract.
- **No DOM/HTML access** ever. All reading is from screenshots.
- **No automation framework** (no Playwright/Selenium/CDP) and **no cloaking** (no fingerprint/canvas spoofing, no proxy or account rotation, no CAPTCHA solving).
- Report language: **Spanish**. Code/tests/comments: English.
- Default volume: `max_posts=18`, `max_replies=8`. Ranking is relative (top-N by engagement).
- Human-scale pacing everywhere; a circuit-breaker stops on any rate-limit / unusual-activity / login-wall screen.
- Vision model default `qwen2.5vl`; configurable.
- Frequent commits; conventional commit messages.

---

### Task 1: Project scaffold, config, and data models

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `src/curator/__init__.py`
- Create: `src/curator/models.py`
- Create: `src/curator/config.py`
- Create: `tests/__init__.py`
- Create: `tests/test_models.py`
- Create: `README.md`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `models.Reply`, `models.Post`, `models.Element`, `models.ScreenModel`, `models.RunResult` (dataclasses, fields as below).
  - `config.Config` dataclass with `.default()` classmethod.

- [ ] **Step 1: Write `requirements.txt`**

```text
pyautogui==0.9.54
PyGetWindow==0.0.9
mss==9.0.1
Pillow==10.4.0
pytesseract==0.3.13
ollama==0.3.3
pytest==8.3.3
```

- [ ] **Step 2: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "twitter-vision-curator"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
```

- [ ] **Step 3: Write the failing test** `tests/test_models.py`

```python
from curator.models import Post, Reply, Element, ScreenModel, RunResult


def test_post_defaults():
    p = Post(author_handle="@a", author_name="A", text="hi",
             likes=10, replies=2, reposts=1)
    assert p.permalink == ""
    assert p.has_image is False
    assert p.top_replies == []
    assert p.engagement_confidence == 1.0


def test_reply_and_screenmodel():
    r = Reply(author_handle="@b", author_name="B", text="yo", likes=5)
    e = Element(kind="post", bbox=(0, 0, 100, 50), text="yo",
                numbers={"likes": (5, 0.9)})
    sm = ScreenModel(elements=[e])
    assert r.likes == 5
    assert sm.elements[0].numbers["likes"] == (5, 0.9)


def test_runresult():
    rr = RunResult(topic="x", timestamp="2026-07-22", posts=[], summary_text="",
                   output_dir="out")
    assert rr.posts == []
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'curator.models'`

- [ ] **Step 5: Write `src/curator/__init__.py`** (empty file) and `src/curator/models.py`

```python
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Reply:
    author_handle: str
    author_name: str
    text: str
    likes: int
    timestamp: str = ""
    screenshot_path: str = ""
    engagement_confidence: float = 1.0
    parent_post_permalink: str = ""


@dataclass
class Post:
    author_handle: str
    author_name: str
    text: str
    likes: int
    replies: int
    reposts: int
    timestamp: str = ""
    permalink: str = ""
    has_image: bool = False
    screenshot_path: str = ""
    image_screenshot_paths: list = field(default_factory=list)
    engagement_confidence: float = 1.0
    top_replies: list = field(default_factory=list)


@dataclass
class Element:
    kind: str            # 'post' | 'reply' | 'button' | 'image'
    bbox: tuple          # (x, y, w, h) in screen coordinates
    text: str = ""
    numbers: dict = field(default_factory=dict)   # {'likes': (int, confidence), ...}


@dataclass
class ScreenModel:
    elements: list = field(default_factory=list)  # list[Element]
    raw_screenshot_path: str = ""


@dataclass
class RunResult:
    topic: str
    timestamp: str
    posts: list = field(default_factory=list)     # list[Post]
    summary_text: str = ""
    output_dir: str = ""
```

- [ ] **Step 6: Write `src/curator/config.py`**

```python
from dataclasses import dataclass, field


@dataclass
class Config:
    max_posts: int = 18
    max_replies: int = 8
    vision_model: str = "qwen2.5vl"
    text_model: str = "qwen2.5:7b"
    output_dir: str = "output"
    action_budget: int = 300
    min_delay_s: float = 1.0
    max_delay_s: float = 5.0
    window_left: int = 0
    window_top: int = 0
    window_width: int = 1280
    window_height: int = 1000
    chrome_profile_dir: str = "chrome-profile"
    min_confidence: float = 0.4

    @classmethod
    def default(cls) -> "Config":
        return cls()
```

- [ ] **Step 7: Write `README.md`** with setup + risk notice

```markdown
# Twitter Vision Curator

Local, no-API agent that browses X/Twitter by computer vision only and writes a
Spanish report of the most popular posts/replies on a topic.

## WARNING
Automating a logged-in account violates X's Terms of Service. Use a throwaway
account you are willing to lose. This tool paces itself like a human to avoid
being blocked; it does NOT and cannot guarantee you won't be detected or
suspended.

## Setup
1. Install Python 3.11+ and Google Chrome.
2. `pip install -r requirements.txt`
3. Install Tesseract OCR and ensure `tesseract` is on PATH.
4. Install Ollama; `ollama pull qwen2.5vl` and `ollama pull qwen2.5:7b`.
5. First run opens Chrome — log in to your throwaway account by hand.

## Run
`python -m curator.main "your topic here"`
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `pytest tests/test_models.py -v`
Expected: PASS (3 passed)

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: project scaffold, config, and data models"
```

---

### Task 2: Engagement-count parsing (`parse_count`)

**Files:**
- Create: `src/curator/counts.py`
- Test: `tests/test_counts.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `counts.parse_count(text: str) -> tuple[int | None, float]` returning `(value, confidence)`. Confidence is `0.0` when unparseable, `0.9` for clean parses, `0.6` for noisy/ambiguous OCR text.

- [ ] **Step 1: Write the failing test** `tests/test_counts.py`

```python
from curator.counts import parse_count


def test_plain_integer():
    assert parse_count("1234") == (1234, 0.9)


def test_comma_grouped():
    assert parse_count("1,234") == (1234, 0.9)


def test_k_suffix():
    assert parse_count("12.4K") == (12400, 0.9)


def test_m_suffix():
    assert parse_count("3.2M") == (3200000, 0.9)


def test_empty_is_unparseable():
    assert parse_count("") == (None, 0.0)


def test_garbage_is_unparseable():
    assert parse_count("like") == (None, 0.0)


def test_noisy_but_recoverable_lower_confidence():
    # OCR noise around a number -> recoverable but less trusted
    value, conf = parse_count("~12K ")
    assert value == 12000
    assert conf == 0.6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_counts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'curator.counts'`

- [ ] **Step 3: Write `src/curator/counts.py`**

```python
import re

_CLEAN = re.compile(r"^\s*([0-9][0-9,\.]*)\s*([KkMm]?)\s*$")
_NOISY = re.compile(r"([0-9][0-9,\.]*)\s*([KkMm]?)")
_MULT = {"": 1, "k": 1_000, "m": 1_000_000}


def _to_int(num: str, suffix: str) -> int | None:
    num = num.replace(",", "")
    try:
        base = float(num)
    except ValueError:
        return None
    return int(round(base * _MULT[suffix.lower()]))


def parse_count(text: str) -> tuple[int | None, float]:
    """Parse an engagement count like '12.4K' -> (12400, confidence)."""
    if text is None:
        return (None, 0.0)
    m = _CLEAN.match(text)
    if m:
        value = _to_int(m.group(1), m.group(2))
        return (value, 0.9) if value is not None else (None, 0.0)
    m = _NOISY.search(text)
    if m:
        value = _to_int(m.group(1), m.group(2))
        return (value, 0.6) if value is not None else (None, 0.0)
    return (None, 0.0)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_counts.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: engagement-count parser with confidence"
```

---

### Task 3: Popularity ranking (`ranker`)

**Files:**
- Create: `src/curator/ranker.py`
- Test: `tests/test_ranker.py`

**Interfaces:**
- Consumes: `models.Post`, `models.Reply`, `config.Config.min_confidence`.
- Produces:
  - `ranker.top_posts(posts: list[Post], n: int, min_confidence: float = 0.4) -> list[Post]`
  - `ranker.top_replies(replies: list[Reply], m: int, min_confidence: float = 0.4) -> list[Reply]`
  - Ordering: descending by likes; posts tie-break by reposts then replies; entries whose `engagement_confidence < min_confidence` are dropped; entries with `likes is None`-equivalent (represented as `likes=-1`) are dropped.

- [ ] **Step 1: Write the failing test** `tests/test_ranker.py`

```python
from curator.models import Post, Reply
from curator.ranker import top_posts, top_replies


def _post(likes, reposts=0, replies=0, conf=1.0, handle="@a"):
    return Post(author_handle=handle, author_name="A", text="t",
                likes=likes, replies=replies, reposts=reposts,
                engagement_confidence=conf)


def test_top_posts_orders_by_likes_desc():
    posts = [_post(10), _post(100), _post(50)]
    result = top_posts(posts, 2)
    assert [p.likes for p in result] == [100, 50]


def test_top_posts_tie_breaks_by_reposts():
    posts = [_post(10, reposts=1), _post(10, reposts=9)]
    result = top_posts(posts, 2)
    assert [p.reposts for p in result] == [9, 1]


def test_top_posts_drops_low_confidence():
    posts = [_post(100, conf=0.2), _post(5, conf=0.9)]
    result = top_posts(posts, 5)
    assert [p.likes for p in result] == [5]


def test_top_posts_drops_unreadable_likes():
    posts = [_post(-1, conf=0.9), _post(5, conf=0.9)]
    result = top_posts(posts, 5)
    assert [p.likes for p in result] == [5]


def test_top_replies_orders_and_limits():
    replies = [Reply("@a", "A", "t", likes=3),
               Reply("@b", "B", "t", likes=30),
               Reply("@c", "C", "t", likes=15)]
    result = top_replies(replies, 2)
    assert [r.likes for r in result] == [30, 15]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_ranker.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'curator.ranker'`

- [ ] **Step 3: Write `src/curator/ranker.py`**

```python
from curator.models import Post, Reply


def _eligible(likes: int, confidence: float, min_confidence: float) -> bool:
    return likes is not None and likes >= 0 and confidence >= min_confidence


def top_posts(posts: list[Post], n: int, min_confidence: float = 0.4) -> list[Post]:
    eligible = [p for p in posts
                if _eligible(p.likes, p.engagement_confidence, min_confidence)]
    eligible.sort(key=lambda p: (p.likes, p.reposts, p.replies), reverse=True)
    return eligible[:n]


def top_replies(replies: list[Reply], m: int, min_confidence: float = 0.4) -> list[Reply]:
    eligible = [r for r in replies
                if _eligible(r.likes, r.engagement_confidence, min_confidence)]
    eligible.sort(key=lambda r: r.likes, reverse=True)
    return eligible[:m]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_ranker.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: relative popularity ranking for posts and replies"
```

---

### Task 4: Human-motion math (`humanize` pure functions)

**Files:**
- Create: `src/curator/humanize_math.py`
- Test: `tests/test_humanize_math.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `humanize_math.bezier_path(start: tuple[int,int], end: tuple[int,int], steps: int, rng) -> list[tuple[int,int]]` — quadratic Bézier with a randomized control point; first point == start, last == end, length == steps.
  - `humanize_math.jittered_delay(lo: float, hi: float, rng) -> float` — value in `[lo, hi]`.
  - `humanize_math.dwell_seconds(text: str, wps: float = 3.5) -> float` — reading time estimate, minimum 0.4s.
- Note: `rng` is a `random.Random` instance so tests can seed it.

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
    # A straight horizontal move would keep y == 0 throughout.
    assert any(p[1] != 0 for p in path)


def test_jittered_delay_within_bounds():
    rng = random.Random(3)
    for _ in range(100):
        d = jittered_delay(1.0, 5.0, rng)
        assert 1.0 <= d <= 5.0


def test_dwell_scales_with_length_and_has_minimum():
    assert dwell_seconds("") >= 0.4
    long = dwell_seconds("word " * 100)
    short = dwell_seconds("word")
    assert long > short
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_humanize_math.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'curator.humanize_math'`

- [ ] **Step 3: Write `src/curator/humanize_math.py`**

```python
def bezier_path(start, end, steps, rng):
    """Quadratic Bezier from start to end with a randomized control point."""
    (x0, y0), (x1, y1) = start, end
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    # Perpendicular-ish offset so the path bows off the straight line.
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
    """Non-uniform delay in [lo, hi] biased toward the low end (triangular)."""
    return rng.triangular(lo, hi, lo + (hi - lo) * 0.35)


def dwell_seconds(text, wps=3.5):
    """Estimated reading dwell time in seconds, minimum 0.4s."""
    words = len((text or "").split())
    return max(0.4, words / wps)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_humanize_math.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: human-motion math (bezier path, jittered delays, dwell)"
```

---

### Task 5: Report rendering (`report` pure functions)

**Files:**
- Create: `src/curator/report.py`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: `models.Post`, `models.Reply`, `models.RunResult`.
- Produces:
  - `report.render_markdown(run: RunResult) -> str`
  - `report.render_html(run: RunResult) -> str` (screenshots embedded as base64 when the file exists; otherwise the image is skipped)
  - `report.synthesize(run: RunResult, chat_fn) -> str` — builds a Spanish-language prompt from the collected text and calls `chat_fn(prompt: str) -> str`. `chat_fn` is injected so it can be tested without Ollama; the real caller passes an Ollama-backed function (Task 6).
  - `report.write_outputs(run: RunResult, base_dir: str) -> None` — writes `report.md`, `report.html`, `run.json`.

- [ ] **Step 1: Write the failing test** `tests/test_report.py`

```python
from curator.models import Post, Reply, RunResult
from curator.report import render_markdown, render_html, synthesize


def _run():
    reply = Reply("@r", "R", "great point", likes=42)
    post = Post("@a", "Alice", "hello world", likes=100, replies=3, reposts=5,
                permalink="https://x.com/a/status/1", top_replies=[reply])
    return RunResult(topic="mars", timestamp="2026-07-22",
                     posts=[post], summary_text="Resumen en español.")


def test_render_markdown_includes_topic_post_and_reply():
    md = render_markdown(_run())
    assert "mars" in md
    assert "hello world" in md
    assert "great point" in md
    assert "https://x.com/a/status/1" in md
    assert "Resumen en español." in md


def test_render_html_is_selfcontained_document():
    html = render_html(_run())
    assert "<html" in html.lower()
    assert "hello world" in html
    assert "Resumen en español." in html


def test_synthesize_builds_spanish_prompt_and_uses_chat_fn():
    captured = {}

    def fake_chat(prompt):
        captured["prompt"] = prompt
        return "SÍNTESIS"

    out = synthesize(_run(), fake_chat)
    assert out == "SÍNTESIS"
    # Prompt must instruct Spanish output and include collected text.
    assert "español" in captured["prompt"].lower()
    assert "hello world" in captured["prompt"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_report.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'curator.report'`

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
             "## Resumen", "", run.summary_text, "", "## Publicaciones destacadas", ""]
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
    parts = [f"<!doctype html><html lang='es'><head><meta charset='utf-8'>",
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


def synthesize(run, chat_fn) -> str:
    blocks = []
    for p in run.posts:
        blocks.append(f"[{p.likes} likes] {p.author_handle}: {p.text}")
        for r in p.top_replies:
            blocks.append(f"  respuesta [{r.likes} likes] {r.author_handle}: {r.text}")
    collected = "\n".join(blocks)
    prompt = (
        "Eres un analista de redes sociales. A partir de las publicaciones y "
        "respuestas más populares de Twitter/X sobre el tema "
        f"'{run.topic}', escribe en ESPAÑOL un resumen narrativo claro de todo "
        "lo más destacado que se está comentando: los temas principales, los "
        "puntos de vista y el tono general. No inventes datos.\n\n"
        f"Contenido recopilado:\n{collected}\n"
    )
    return chat_fn(prompt)


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

Run: `pytest tests/test_report.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: Spanish report synthesis and Markdown/HTML/JSON rendering"
```

---

### Task 6: Vision perception (`vision`)

**Files:**
- Create: `src/curator/vision.py`
- Create: `tests/fixtures/README.md` (explains how to add screenshot fixtures)
- Test: `tests/test_vision.py`

**Interfaces:**
- Consumes: `counts.parse_count`, `models.Element`, `models.ScreenModel`, `config.Config`.
- Produces:
  - `vision.ocr_words(image) -> list[dict]` — wraps `pytesseract.image_to_data`; each dict has `text`, `conf`, `left`, `top`, `width`, `height`. (Thin wrapper; the underlying pytesseract call is injected as `ocr_fn` for testing.)
  - `vision.build_screen_model(vision_json: dict, ocr_words: list[dict]) -> ScreenModel` — pure function combining the vision model's element boxes (JSON) with OCR words falling inside each box; parses engagement numbers via `parse_count`.
  - `vision.read_screen(image, cfg, vision_fn, ocr_fn) -> ScreenModel` — orchestrator; `vision_fn(image) -> dict` calls qwen2.5vl via Ollama, `ocr_fn(image) -> list[dict]` calls Tesseract. Both injected.
  - `vision.capture(bounds) -> PIL.Image` — screenshot via `mss`.
- **Test only the pure function `build_screen_model`** against a hand-written `vision_json` + `ocr_words`. The Ollama/Tesseract/mss calls are validated manually.

- [ ] **Step 1: Write the failing test** `tests/test_vision.py`

```python
from curator.vision import build_screen_model


def test_build_screen_model_assigns_ocr_and_parses_counts():
    vision_json = {
        "elements": [
            {"kind": "post", "bbox": [0, 0, 200, 100]},
            {"kind": "button", "bbox": [500, 500, 40, 20]},
        ]
    }
    ocr_words = [
        {"text": "hello", "conf": 95, "left": 10, "top": 10, "width": 40, "height": 12},
        {"text": "12.4K", "conf": 90, "left": 10, "top": 60, "width": 40, "height": 12},
        {"text": "offscreen", "conf": 88, "left": 900, "top": 900, "width": 40, "height": 12},
    ]
    sm = build_screen_model(vision_json, ocr_words)
    post = sm.elements[0]
    assert "hello" in post.text
    # The "12.4K" inside the post box becomes a candidate like-count.
    assert post.numbers["likes"][0] == 12400
    # A word outside every box is not attached.
    assert "offscreen" not in post.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_vision.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'curator.vision'`

- [ ] **Step 3: Write `src/curator/vision.py`**

```python
import json
import mss
from PIL import Image
from curator.counts import parse_count
from curator.models import Element, ScreenModel


def _inside(word, box) -> bool:
    x, y, w, h = box
    cx = word["left"] + word["width"] / 2
    cy = word["top"] + word["height"] / 2
    return x <= cx <= x + w and y <= cy <= y + h


def build_screen_model(vision_json: dict, ocr_words: list) -> ScreenModel:
    """Pure: merge vision element boxes with OCR words + parse counts."""
    elements = []
    for el in vision_json.get("elements", []):
        box = tuple(el["bbox"])
        words = [w for w in ocr_words if _inside(w, box)]
        text = " ".join(w["text"] for w in words).strip()
        numbers = {}
        # Highest number inside the box is treated as the like-count candidate.
        best = (None, 0.0)
        for w in words:
            value, conf = parse_count(w["text"])
            if value is not None and (best[0] is None or value > best[0]):
                best = (value, conf)
        if best[0] is not None:
            numbers["likes"] = best
        elements.append(Element(kind=el["kind"], bbox=box, text=text, numbers=numbers))
    return ScreenModel(elements=elements)


def ocr_words(image) -> list:
    import pytesseract
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    out = []
    for i, txt in enumerate(data["text"]):
        if txt.strip():
            out.append({"text": txt, "conf": data["conf"][i],
                        "left": data["left"][i], "top": data["top"][i],
                        "width": data["width"][i], "height": data["height"][i]})
    return out


def _default_vision_fn(image, model: str):
    import base64, io, ollama
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    prompt = (
        "Return ONLY JSON: {\"elements\":[{\"kind\":\"post|reply|button|image\","
        "\"bbox\":[x,y,w,h]}]} for every tweet, reply, like-button and image "
        "visible in this Twitter/X screenshot. Coordinates in pixels."
    )
    resp = ollama.chat(model=model, messages=[
        {"role": "user", "content": prompt, "images": [b64]}])
    content = resp["message"]["content"]
    start, end = content.find("{"), content.rfind("}")
    return json.loads(content[start:end + 1])


def read_screen(image, cfg, vision_fn=None, ocr_fn=None) -> ScreenModel:
    vision_fn = vision_fn or (lambda img: _default_vision_fn(img, cfg.vision_model))
    ocr_fn = ocr_fn or ocr_words
    return build_screen_model(vision_fn(image), ocr_fn(image))


def capture(bounds) -> Image.Image:
    """bounds = (left, top, width, height). Returns a PIL RGB image."""
    left, top, width, height = bounds
    with mss.mss() as sct:
        shot = sct.grab({"left": left, "top": top, "width": width, "height": height})
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_vision.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Write `tests/fixtures/README.md`**

```markdown
# Vision fixtures
To add a regression test: save a real X screenshot here as `<name>.png`, and a
hand-checked `<name>.expected.json` describing the elements you expect
`build_screen_model` to produce. Keep images small and free of private data.
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: pure-vision perception (screen model, OCR, qwen2.5vl)"
```

---

### Task 7: Browser lifecycle & OS navigation (`browser`)

**Files:**
- Create: `src/curator/browser.py`
- Test: `tests/test_browser.py`

**Interfaces:**
- Consumes: `config.Config`.
- Produces a `Browser` class:
  - `Browser(cfg)` — stores config.
  - `search_url(topic: str) -> str` — builds the X Top-tab search URL (pure; **this is the unit-tested part**).
  - `launch()` — starts plain Chrome via `subprocess` with `--user-data-dir` + window geometry flags.
  - `goto(url)` — focus address bar (`Ctrl+L`), type URL, Enter (via `pyautogui`).
  - `read_current_url() -> str` — `Ctrl+L`, `Ctrl+C`, read clipboard.
  - `ensure_logged_in()` — prints instructions and blocks until the user presses Enter after logging in manually.
  - `window_bounds() -> tuple` — locate the Chrome window via `pygetwindow`.
- Only `search_url` is unit-tested; the rest is manual.

- [ ] **Step 1: Write the failing test** `tests/test_browser.py`

```python
from curator.config import Config
from curator.browser import Browser


def test_search_url_uses_top_tab_and_encodes_topic():
    b = Browser(Config.default())
    url = b.search_url("mars rover")
    assert url.startswith("https://x.com/search?")
    assert "q=mars%20rover" in url or "q=mars+rover" in url
    assert "f=top" in url
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_browser.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'curator.browser'`

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
        # Common Windows install location fallback.
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

    def goto(self, url: str):
        import pyautogui
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.5)
        pyautogui.typewrite(url, interval=0.02)
        pyautogui.press("enter")
        time.sleep(4)

    def read_current_url(self) -> str:
        import pyautogui, subprocess as sp
        pyautogui.hotkey("ctrl", "l")
        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.3)
        # Windows clipboard via PowerShell to avoid extra deps.
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

Run: `pytest tests/test_browser.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: plain-Chrome launch and OS-input navigation"
```

---

### Task 8: Human-behavior actions (`humanize` actions)

**Files:**
- Create: `src/curator/humanize.py`
- Test: `tests/test_humanize.py`

**Interfaces:**
- Consumes: `humanize_math`, `config.Config`, `models.ScreenModel`.
- Produces a `Human` class:
  - `Human(cfg, rng=None)`.
  - `move_and_click(x, y)` — walk the Bézier path with `pyautogui.moveTo`, then click.
  - `scroll(clicks)` — several small `pyautogui.scroll` steps with jittered pauses.
  - `pause()` — `time.sleep(jittered_delay(...))`.
  - `dwell(text)` — sleep `dwell_seconds(text)`.
  - `spend_action() -> bool` / `budget_remaining() -> int` — decrement/report the action budget.
  - `check_circuit_breaker(sm: ScreenModel) -> bool` — returns True if any element text matches a stop phrase (`"unusual activity"`, `"rate limit"`, `"log in"`, `"try again later"`, case-insensitive). **This is the unit-tested part.**

- [ ] **Step 1: Write the failing test** `tests/test_humanize.py`

```python
from curator.config import Config
from curator.models import Element, ScreenModel
from curator.humanize import Human


def test_budget_decrements_and_blocks():
    cfg = Config.default()
    cfg.action_budget = 2
    h = Human(cfg)
    assert h.spend_action() is True
    assert h.spend_action() is True
    assert h.spend_action() is False
    assert h.budget_remaining() == 0


def test_circuit_breaker_trips_on_stop_phrase():
    h = Human(Config.default())
    sm = ScreenModel(elements=[Element(kind="button", bbox=(0, 0, 1, 1),
                                       text="Caution: unusual activity detected")])
    assert h.check_circuit_breaker(sm) is True


def test_circuit_breaker_ok_on_normal_screen():
    h = Human(Config.default())
    sm = ScreenModel(elements=[Element(kind="post", bbox=(0, 0, 1, 1),
                                       text="just a normal tweet")])
    assert h.check_circuit_breaker(sm) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_humanize.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'curator.humanize'`

- [ ] **Step 3: Write `src/curator/humanize.py`**

```python
import random
import time
from curator.humanize_math import bezier_path, jittered_delay, dwell_seconds

_STOP_PHRASES = ("unusual activity", "rate limit", "rate-limited",
                 "try again later", "log in", "sign in to continue",
                 "something went wrong")


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

    def check_circuit_breaker(self, sm) -> bool:
        blob = " ".join(e.text for e in sm.elements).lower()
        return any(phrase in blob for phrase in _STOP_PHRASES)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_humanize.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: human-behavior action layer with circuit-breaker"
```

---

### Task 9: Orchestration (`agent`) and CLI (`main`)

**Files:**
- Create: `src/curator/screenshots.py`
- Create: `src/curator/agent.py`
- Create: `src/curator/main.py`
- Test: `tests/test_agent.py`

**Interfaces:**
- Consumes: everything above.
- Produces:
  - `screenshots.crop_and_save(image, bbox, path) -> str` — crop a PIL image to bbox and save PNG (**unit-tested**).
  - `agent.collect_posts_from_screen(sm: ScreenModel) -> list[Post]` — convert post-kind elements to `Post` records using their parsed `likes` (**unit-tested**).
  - `agent.Agent(cfg, browser, human, ...)` with `run(topic) -> RunResult` — the perceive→decide→act loop (manual/integration).
  - `main.main(argv)` — parse the topic arg, wire real dependencies, run, write outputs.

- [ ] **Step 1: Write the failing test** `tests/test_agent.py`

```python
from PIL import Image
from curator.models import Element, ScreenModel
from curator.screenshots import crop_and_save
from curator.agent import collect_posts_from_screen


def test_crop_and_save(tmp_path):
    img = Image.new("RGB", (200, 200), "white")
    out = crop_and_save(img, (10, 10, 50, 40), str(tmp_path / "c.png"))
    saved = Image.open(out)
    assert saved.size == (50, 40)


def test_collect_posts_from_screen_builds_posts_with_likes():
    sm = ScreenModel(elements=[
        Element(kind="post", bbox=(0, 0, 100, 80), text="alpha",
                numbers={"likes": (500, 0.9)}),
        Element(kind="button", bbox=(0, 90, 20, 20), text="Like"),
    ])
    posts = collect_posts_from_screen(sm)
    assert len(posts) == 1
    assert posts[0].likes == 500
    assert posts[0].engagement_confidence == 0.9
    assert posts[0].text == "alpha"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_agent.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'curator.screenshots'`

- [ ] **Step 3: Write `src/curator/screenshots.py`**

```python
import os


def crop_and_save(image, bbox, path: str) -> str:
    x, y, w, h = bbox
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    image.crop((x, y, x + w, y + h)).save(path)
    return path
```

- [ ] **Step 4: Write `src/curator/agent.py`**

```python
import time
from curator.models import Post, RunResult
from curator.ranker import top_posts, top_replies
from curator import vision, screenshots


def collect_posts_from_screen(sm) -> list:
    posts = []
    for el in sm.elements:
        if el.kind != "post":
            continue
        likes, conf = el.numbers.get("likes", (-1, 0.0))
        posts.append(Post(author_handle="", author_name="", text=el.text,
                          likes=likes if likes is not None else -1,
                          replies=0, reposts=0, engagement_confidence=conf))
    return posts


class Agent:
    def __init__(self, cfg, browser, human, out_dir, timestamp,
                 read_screen=None, synth_fn=None):
        self.cfg = cfg
        self.browser = browser
        self.human = human
        self.out_dir = out_dir
        self.timestamp = timestamp
        self.read_screen = read_screen or (lambda img: vision.read_screen(img, cfg))
        self.synth_fn = synth_fn

    def _perceive(self):
        bounds = self.browser.window_bounds()
        img = vision.capture(bounds)
        sm = self.read_screen(img)
        return img, sm

    def run(self, topic) -> RunResult:
        from curator.report import synthesize, write_outputs
        self.browser.launch()
        self.browser.ensure_logged_in()
        self.browser.goto(self.browser.search_url(topic))
        self.human.pause()

        collected = []
        seen = set()
        # Gather posts by scrolling the search results.
        for _ in range(self.cfg.max_posts):
            if not self.human.spend_action():
                break
            img, sm = self._perceive()
            if self.human.check_circuit_breaker(sm):
                break
            for p in collect_posts_from_screen(sm):
                key = p.text[:60]
                if key and key not in seen:
                    seen.add(key)
                    collected.append(p)
            self.human.scroll(3)
            self.human.pause()

        ranked = top_posts(collected, self.cfg.max_posts, self.cfg.min_confidence)
        run = RunResult(topic=topic, timestamp=self.timestamp, posts=ranked,
                        output_dir=self.out_dir)
        # Incremental save before the (optional) summary.
        write_outputs(run, self.out_dir)

        if self.synth_fn:
            run.summary_text = synthesize(run, self.synth_fn)
            write_outputs(run, self.out_dir)
        return run
```

- [ ] **Step 5: Write `src/curator/main.py`**

```python
import sys
import time
import os
from curator.config import Config
from curator.browser import Browser
from curator.humanize import Human
from curator.agent import Agent


def _ollama_chat(model):
    import ollama
    def chat(prompt):
        resp = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
        return resp["message"]["content"]
    return chat


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print('Usage: python -m curator.main "topic"')
        return 1
    topic = argv[0]
    cfg = Config.default()
    stamp = time.strftime("%Y-%m-%d")
    safe = "".join(ch for ch in topic if ch.isalnum() or ch in " -_").strip().replace(" ", "-")
    out_dir = os.path.join(cfg.output_dir, f"{safe}-{stamp}")
    browser = Browser(cfg)
    human = Human(cfg)
    agent = Agent(cfg, browser, human, out_dir, stamp,
                  synth_fn=_ollama_chat(cfg.text_model))
    agent.run(topic)
    print(f"Done. Output in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_agent.py -v`
Expected: PASS (2 passed)

- [ ] **Step 7: Run the full suite**

Run: `pytest -v`
Expected: PASS (all tests from Tasks 1–9)

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: agent orchestration loop and CLI entrypoint"
```

---

## Notes for the implementer

- Tasks 1–6 and 8–9's unit tests are fully offline and must pass in CI. Tasks 7 and the live parts of 6/8/9 (`launch`, `goto`, `read_screen` with real Ollama, `Agent.run` end-to-end) require Chrome + Ollama + Tesseract and a manual login, so they are validated by a human run, not pytest.
- Reply collection per post mirrors post collection (open post → perceive → `collect` reply-kind elements → `top_replies` → screenshot). It is implemented inside `Agent.run` during the manual-integration phase; keep the same perceive/scroll/circuit-breaker pattern. This is intentionally left to the integration step because it cannot be unit-tested without the live site.
- Keep the ToS/risk notice in `README.md` prominent.
