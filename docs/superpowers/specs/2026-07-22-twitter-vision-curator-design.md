# Twitter Vision Curator — Design Spec (v2)

**Date:** 2026-07-22
**Status:** Approved (design v2)
**Supersedes:** v1 (local-LLM engine). Changed because the user lacks GPU RAM for a
local vision model. The engine is now the live Claude Code session.

## 1. Purpose

A local desktop agent that, given a **topic string**, browses Twitter/X like a
human, finds the most popular posts and the most popular replies on those posts,
screenshots them (and their images), and produces a **Spanish-language narrative
report** ("script") of what is being discussed.

The agent perceives the screen with **vision only** (screenshots — never the
DOM/HTML) and controls a real browser with **real OS mouse/keyboard input**.

## 2. Engine architecture (v2)

- **Brain = the live Claude Code session.** Claude runs the perceive→decide→act
  loop: take a screenshot, *look at it*, decide the next human action, execute it
  via the toolkit, repeat. Claude also writes the final Spanish report. There is
  **no local model and no Ollama/Tesseract.**
- **Hands & eyes = a small Python toolkit** exposed as CLI subcommands that Claude
  calls: launch Chrome, move-mouse-and-click (human motion), scroll, screenshot,
  crop, read the current URL from the OS clipboard, render the report.
- **Consequence — honest scope:** this is **not** a walk-away standalone app. It is
  "autonomous within a Claude Code session" — Claude makes every decision without
  the user steering — but it only runs while a session is driving it. It also now
  relies on the Anthropic API behind Claude Code (the original "no APIs" no longer
  holds), though with no extra API key or per-run bill beyond Claude Code itself.

## 3. Scope

**In scope**
- On-demand, single-topic runs.
- Single logged-in session on a **throwaway/secondary** account (manual login).
- Focused volume: ~15–18 top posts, ~5–8 top replies each.
- Relative popularity ranking (top-N by engagement).
- Spanish report + screenshot files + a single self-contained HTML page +
  structured `run.json`.

**Out of scope (explicitly will not build)**
- Twitter/X API; DOM/HTML parsing.
- Any local model / Ollama / Tesseract.
- Active detection-evasion / cloaking (fingerprint or canvas/WebGL spoofing,
  stealth plugins, proxy or account rotation, CAPTCHA-solving).
- Continuous/large-scale scraping.

## 4. Honest constraints & risks (carried into the design)

- **ToS / account risk:** Automating a logged-in account violates X's Terms; the
  throwaway account may be suspended. Minimized only by human-scale behavior, not
  disguise. "Undetectable" is not a deliverable; the goal is *behaving like a real
  person at real-person scale so there is nothing abnormal to detect.*
- **Token/context cost:** Every screenshot Claude looks at consumes session
  context. Volume is kept focused; Claude may record data incrementally and
  summarize as it goes to stay within limits.
- **Coordinate/DPI correctness:** screenshots (physical pixels) and mouse input
  must share one coordinate system. The toolkit sets the Python process
  DPI-aware and captures the full primary screen so screenshot pixel = screen
  coordinate for `pyautogui`.
- **Reliability:** Claude's vision reads tweets and engagement numbers directly
  (more accurate than local OCR), but pure-vision navigation can still misclick;
  the loop is defensive, saves progress incrementally, and stops on any
  rate-limit / unusual-activity / login-wall screen (Claude judges this visually).

## 5. Components

### 5.1 Python toolkit (`src/curator/`)
- **`models.py`** — dataclasses `Post`, `Reply`, `RunResult` (already built).
- **`config.py`** — `Config` dataclass with defaults (already built; trimmed of
  local-model fields).
- **`screenshots.py`** — `set_dpi_aware()`, `capture_screen(path)` (full primary
  monitor → PNG), `crop_and_save(image_path, bbox, out)`.
- **`humanize_math.py`** — `bezier_path`, `jittered_delay`, `dwell_seconds` (pure).
- **`humanize.py`** — `Human`: `move_and_click`, `scroll`, `pause`, `dwell`,
  `spend_action`/`budget_remaining` (real OS input via `pyautogui`).
- **`browser.py`** — `Browser`: `search_url` (pure), `launch`, `goto`,
  `read_current_url` (clipboard), `ensure_logged_in`, `window_bounds`.
- **`ranker.py`** — `top_posts`, `top_replies` (pure, relative ranking).
- **`report.py`** — `render_markdown`, `render_html`, `write_outputs` (pure;
  the Spanish `summary_text` is written by Claude and passed in).
- **`cli.py`** — argparse subcommands wiring the above so Claude can call them
  from the shell: `launch`, `goto`, `screenshot`, `click`, `scroll`, `read-url`,
  `crop`, `render-report`.

### 5.2 Brain (`docs/AGENT_RUNBOOK.md`)
A runbook Claude follows to drive a run: launch + ensure login → search the Top
tab → screenshot/scroll to gather candidate posts → record each with its like
count → rank → for each top post: open it, capture permalink, screenshot the
tweet region and image regions, scroll replies, record + rank replies, screenshot
top replies → save `run.json` incrementally → write the Spanish report → render
Markdown + HTML. Includes human pacing between actions and the visual
circuit-breaker.

## 6. Data model
- **Post:** author_handle, author_name, text, likes, replies, reposts, timestamp,
  permalink, has_image, screenshot_path, image_screenshot_paths,
  engagement_confidence, top_replies.
- **Reply:** author_handle, author_name, text, likes, timestamp, screenshot_path,
  engagement_confidence, parent_post_permalink.
- **RunResult:** topic, timestamp, posts, summary_text, output_dir.

## 7. Data flow
```
topic
 -> cli launch ; ensure manual login
 -> cli goto <search Top-tab URL>
 -> loop: cli screenshot -> Claude LOOKS -> record posts+likes -> cli scroll   (until enough)
 -> ranker.top_posts -> top ~15-18
    -> per post: cli click(open) -> cli read-url (permalink)
                 cli screenshot -> Claude picks tweet + image bboxes -> cli crop (screenshots)
                 loop: cli scroll -> cli screenshot -> Claude records replies
                 ranker.top_replies -> top ~5-8 -> cli crop each
                 write run.json (incremental)
 -> Claude writes Spanish summary_text
 -> report.write_outputs -> output/<topic>-<date>/ : report.md, report.html, run.json, screenshots/
```

## 8. Error handling
- **Perception failure:** re-screenshot after a human pause; if still unclear, skip
  that item and continue.
- **Circuit-breaker:** Claude visually detects a rate-limit / unusual-activity /
  login wall → stop and keep collected data.
- **Crash-safety:** `run.json` written incrementally.

## 9. Testing strategy
- **Unit (TDD):** `humanize_math`, `ranker`, `report` rendering, `screenshots.crop`,
  `browser.search_url`, `cli` argument routing (against a fake toolkit).
- **Manual/integration:** live browser driving (`launch`, `goto`, `click`,
  `scroll`, real `screenshot`) and the full Claude-driven loop are validated in a
  guided live run with the throwaway account.

## 10. Configuration
`max_posts` (18), `max_replies` (8), `output_dir`, `action_budget`, delay range,
window geometry, `chrome_profile_dir`, `min_confidence`.

## 11. Prerequisites / setup
- Python 3.11+ on Windows; Google Chrome.
- `pip install -r requirements.txt` (pyautogui, pygetwindow, mss, Pillow, pytest).
- Windows display scaling ideally 100% (toolkit is DPI-aware regardless).
- A throwaway/secondary X account (logged in by hand on first run).
- Runs while a Claude Code session drives it.

## 12. Deliverables
- The toolkit modules + `cli.py`.
- `docs/AGENT_RUNBOOK.md`.
- Unit tests.
- `README.md` with setup + the explicit ToS/risk notice.
