# Twitter Vision Curator — Design Spec

**Date:** 2026-07-22
**Status:** Approved (design), pending spec review

## 1. Purpose

A local, fully autonomous desktop agent that, given a **topic string**, browses Twitter/X like a human, finds the most popular posts and the most popular replies on those posts, screenshots them (and their images), and produces a **Spanish-language narrative report** ("script") of what is being discussed on that topic.

Everything runs **locally, with no APIs** (no Twitter API, no cloud LLM). The agent perceives the screen with **computer vision only** — it never reads the page DOM/HTML — and controls a real browser with **real OS mouse/keyboard input**.

## 2. Scope

**In scope**
- On-demand, single-topic runs (occasional use).
- Single logged-in session on a **throwaway/secondary** account.
- Focused collection volume: ~15–20 top posts, ~5–10 top replies each.
- Relative popularity ranking (top-N by engagement), not fixed thresholds.
- Spanish report + screenshot files + a single self-contained HTML page + structured `run.json`.

**Out of scope (explicitly will not build)**
- Twitter/X API usage of any kind.
- Cloud LLMs / external APIs.
- DOM/HTML parsing.
- Active detection-evasion / cloaking: fingerprint or canvas/WebGL spoofing, stealth plugins, residential-proxy rotation, account rotation, CAPTCHA-solving services.
- Continuous/large-scale scraping or archiving across many topics.

## 3. Honest constraints & risks (carried into the design, not engineered away)

- **ToS / account risk:** Automating a logged-in account violates X's Terms of Service; the throwaway account may be suspended. The design minimizes this only through human-scale behavior, not disguise.
- **"Undetectable" is not a deliverable.** The goal is *"behaves like a real person at real-person scale, so there is nothing abnormal to detect,"* not concealment. This is achieved by: real Chrome with no automation framework, human pacing/volume, a real logged-in account, and a normal residential connection.
- **Pure-vision reliability:** Ranking accuracy depends on OCR reading engagement numbers correctly; occasional misreads are expected and flagged. Pure-vision navigation will occasionally misclick/misread; the loop is defensive and saves progress incrementally.
- **Speed:** Many model inferences per run make it slow (minutes to tens of minutes). This aligns with human pacing and is acceptable.

## 4. Key architectural decisions

1. **No automation framework.** Plain Chrome is launched as a normal process with a dedicated user profile; it is driven entirely by OS-level input and screenshots. Consequence: no `navigator.webdriver`, no CDP channel, nothing automated inside the browser for X to detect.
2. **Pure vision perception.** All reading is from screenshots via a local vision model (**qwen2.5vl** on Ollama) plus **Tesseract OCR**. The DOM is never accessed.
3. **Real OS input.** Mouse movement (curved, variable-speed paths) and keystrokes via `pyautogui`; window management via `pygetwindow`; screenshots via `mss`.
4. **Everything local.** Ollama (vision + text), Tesseract, screenshots, OS input. No network calls except the browser's own traffic to X.
5. **Permalinks without DOM.** After opening a tweet, the URL is captured via `Ctrl+L` → `Ctrl+C` → OS clipboard read (not DOM).

## 5. Components

Each module has one purpose, a defined interface, and is testable in isolation. Pure-logic modules (`ranker`, `report` rendering, `vision` parsing helpers) are unit-tested against fixtures; browser/OS-driving modules are validated manually.

### 5.1 `browser.py` — browser lifecycle & OS navigation
- **Does:** Launch plain Chrome with a dedicated `--user-data-dir`; position/resize the window to a known geometry; navigate to URLs via real keystrokes; detect logged-in vs logged-out state (visually) and, on first run, pause for **manual human login** (2FA/CAPTCHA solved by the user).
- **Depends on:** `pygetwindow`, `pyautogui`, OS Chrome install.
- **Interface:** `launch()`, `goto(url)`, `ensure_logged_in()`, `window_bounds()`, `read_address_bar_url()`.

### 5.2 `vision.py` — perception (screenshot → screen model)
- **Does:** Capture the browser region; run qwen2.5vl to locate posts, buttons, images, and layout; run Tesseract to read exact text and engagement numbers with bounding boxes; cross-check the two and attach a confidence flag to each number. Produces a **ScreenModel**.
- **Depends on:** `mss`, `PIL`, Ollama (qwen2.5vl), Tesseract.
- **Interface:** `capture(bounds) -> Image`, `read_screen(image) -> ScreenModel`.

### 5.3 `humanize.py` — human-like behavior layer
- **Does:** Curved, variable-speed mouse moves to a target; non-uniform delays with occasional long "distraction" pauses; natural variable-speed scrolling; reading dwell proportional to text length; a per-session **action budget**; a **circuit-breaker** that stops the run and saves progress on any rate-limit / "unusual activity" / login-wall screen.
- **Depends on:** `pyautogui`.
- **Interface:** `move_and_click(x, y)`, `scroll(amount)`, `dwell(text)`, `pause()`, `budget_remaining()`, `check_circuit_breaker(screen_model)`.

### 5.4 `agent.py` — orchestration (perceive → decide → act)
- **Does:** Runs the task plan: search the topic (Top tab) → collect visible posts by scrolling → rank → for each top post open it, screenshot the tweet region and image regions, capture permalink, scroll replies, collect and rank replies, screenshot top replies → persist incrementally → stop on budget/circuit-breaker.
- **Depends on:** all other modules.
- **Interface:** `run(topic) -> RunResult`.

### 5.5 `ranker.py` — popularity ranking (pure logic)
- **Does:** Given engagement records, rank relatively and select top-N posts / top-M replies; de-prioritize low-confidence numbers.
- **Interface:** `top_posts(posts, n)`, `top_replies(replies, m)`.

### 5.6 `report.py` — synthesis & output (pure logic + Ollama text)
- **Does:** Send collected text to a local Ollama model to write the **Spanish** narrative "script"; render `report.md`, a self-contained `report.html` (screenshots embedded as base64), and write/refresh `run.json`.
- **Interface:** `synthesize(records) -> str`, `render_markdown(...)`, `render_html(...)`, `write_run_json(...)`.

## 6. Data model

- **Post:** author_handle, author_name, text, likes, replies, reposts, timestamp, permalink, has_image, screenshot_path, image_screenshot_paths, engagement_confidence.
- **Reply:** author_handle, author_name, text, likes, timestamp, screenshot_path, engagement_confidence, parent_post_permalink.
- **ScreenModel:** list of on-screen elements with type (post/reply/button/image), bounding box, OCR text, detected numbers + confidence.
- **RunResult:** topic, timestamp, list[Post] (each with its top replies), summary_text, output_dir.

## 7. Data flow

```
topic string
  -> browser.goto(search Top tab for topic)
  -> loop: vision.read_screen -> collect posts -> humanize.scroll  (until enough)
  -> ranker.top_posts -> top ~15-20
     -> for each post:
          humanize.move_and_click(open) -> read_address_bar_url (permalink)
          vision.read_screen -> crop tweet region + image regions (screenshots)
          loop: scroll replies -> vision.read_screen -> collect replies
          ranker.top_replies -> top ~5-10 -> screenshot each
          persist to run.json (incremental)
  -> report.synthesize (Spanish, Ollama) -> render_markdown + render_html
  -> output/<topic>-<YYYY-MM-DD>/ : report.md, report.html, screenshots/, run.json
```

## 8. Error handling

- **Perception failure** (no posts found on screen): save the raw screenshot to a debug folder, retry once after a human-like pause, then move on / stop gracefully.
- **Circuit-breaker:** any rate-limit / "unusual activity" / unexpected login wall → stop immediately, keep collected data.
- **Crash-safety:** `run.json` written incrementally; a mid-run failure preserves everything gathered so far.
- **Low-confidence numbers:** kept but flagged; ranking treats them cautiously and the report notes uncertainty.

## 9. Testing strategy

- **Unit (TDD):** `ranker.py` (ranking/selection edge cases), `report.py` rendering (Markdown/HTML from sample records), `vision.py` parsing helpers (number/text extraction from saved screenshot fixtures), `humanize.py` math (path generation, delay distributions are within bounds).
- **Manual/integration:** the live browser-driving path (`browser.py`, `agent.py`) is validated by running against X with the throwaway account; not unit-tested against the live site.
- **Fixtures:** committed screenshot images + expected parsed output for `vision.py`.

## 10. Configuration

- `topic` (run input), `max_posts` (default 18), `max_replies` (default 8), `vision_model` (default `qwen2.5vl`), `text_model` (Ollama text model for the summary), `output_dir`, `action_budget`, delay ranges, window geometry.

## 11. Prerequisites / setup

- Python 3.11+ on Windows.
- Google Chrome installed.
- Ollama installed with `qwen2.5vl` (and a text model) pulled.
- Tesseract OCR installed.
- A throwaway/secondary X account (logged in manually on first run).

## 12. Deliverables

- The six modules above + a small CLI entrypoint (`main.py`) taking the topic.
- Unit tests + fixtures.
- A `README.md` with setup steps and the explicit ToS/risk notice.
