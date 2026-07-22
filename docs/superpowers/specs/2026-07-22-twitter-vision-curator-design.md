# Twitter Vision Curator — Design Spec (v3)

**Date:** 2026-07-22
**Status:** Approved (design v3)
**Supersedes:**
- v1 (local-LLM engine) — dropped: user lacks GPU RAM for a local vision model.
- v2 (Claude engine driving OS-level mouse/keyboard via pyautogui) — dropped: the
  user does not want the agent controlling the whole operating system, only the
  Chrome browser. In practice v2 also grabbed the wrong window and fought the user
  for focus.

## 1. Purpose

A local agent that, given a **topic string**, browses Twitter/X like a human,
finds the most popular posts and the most popular replies on those posts,
screenshots them (and their images), and produces a **Spanish-language narrative
report** ("script") of what is being discussed.

The agent perceives with **vision only** (screenshots — never DOM/HTML parsing)
and controls **only the Chrome browser** (never the OS) via the Chrome DevTools
Protocol.

## 2. Engine architecture (v3)

- **Brain = the live Claude Code session.** Claude runs the perceive→decide→act
  loop: take a screenshot, *look at it*, decide the next human action, execute it
  via the toolkit, repeat. Claude also writes the final Spanish report. There is
  **no local model.**
- **Hands & eyes = a Python toolkit that speaks the Chrome DevTools Protocol
  (CDP).** Chrome is launched with `--remote-debugging-port`; the toolkit connects
  to that one browser over a WebSocket and:
  - captures screenshots with `Page.captureScreenshot` (vision; no DOM parsing);
  - injects human-paced input **into the page** with `Input.dispatchMouseEvent`
    (move/click/scroll) and `Input.insertText` / `Input.dispatchKeyEvent` (typing);
  - reads the current URL from CDP target metadata (no clipboard, no DOM).
- **Only Chrome is controlled.** The OS mouse/keyboard are never touched; the agent
  cannot act outside the browser, and the user can keep using the computer.
- **Coordinate safety:** on connect the toolkit sets a fixed device-metrics
  override (known width/height, `deviceScaleFactor=1`), so screenshot pixels equal
  click coordinates regardless of the display's scaling.
- **Stealth posture:** Chrome is launched WITHOUT `--enable-automation`, so
  `navigator.webdriver` stays `false` and there is no automation banner;
  CDP-injected events are `isTrusted=true`. The only added signal is a
  localhost-only debug port (not visible to X). This is at least as low-profile as
  v2, with no OS takeover.
- **Consequence — honest scope:** still **not** a walk-away standalone app — it runs
  only while a Claude Code session drives it, and relies on the Anthropic API behind
  Claude Code (no extra API key or per-run bill).

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
- **Coordinate correctness:** screenshots and injected clicks must share one
  coordinate system. The toolkit sets a fixed CDP device-metrics override
  (`deviceScaleFactor=1`, known width/height) so a screenshot pixel equals a click
  coordinate regardless of the OS display scaling.
- **Debug-port exposure:** the remote-debugging port is localhost-only; any local
  process could control the browser while it is open. Acceptable for a personal
  tool; the port is not reachable by X.
- **Reliability:** Claude's vision reads tweets and engagement numbers directly
  (more accurate than local OCR), but pure-vision navigation can still misclick;
  the loop is defensive, saves progress incrementally, and stops on any
  rate-limit / unusual-activity / login-wall screen (Claude judges this visually).

## 5. Components

### 5.1 Python toolkit (`src/curator/`)
- **`models.py`** — dataclasses `Post`, `Reply`, `RunResult` (unchanged).
- **`config.py`** — `Config` dataclass with defaults; adds `debug_port` (9222) and
  `chrome_profile_dir`; keeps window geometry (used for the device-metrics override).
- **`cdp.py`** *(new)* — minimal Chrome DevTools Protocol client: `connect(port)`
  discovers the page target over HTTP (`/json`, stdlib `urllib`) and opens a
  WebSocket (`websocket-client`); `send(method, params)`; helpers `navigate(url)`,
  `screenshot() -> bytes`, `move(x,y)`, `click(x,y)`, `scroll(x,y,dy)`,
  `type_text(s)`, `press(key)`, `current_url()`; sets `Page.enable` +
  device-metrics override on connect.
- **`screenshots.py`** — `save_png(data: bytes, path)` and
  `crop_and_save(image_path, bbox, out)` (Pillow). No OS capture, no DPI code.
- **`humanize_math.py`** — `bezier_path`, `jittered_delay`, `dwell_seconds` (pure; unchanged).
- **`humanize.py`** — `Human(cdp, cfg, rng=None)`: `move_and_click`, `scroll`,
  `pause`, `dwell` — human-paced input dispatched through the CDP client (no OS input).
- **`browser.py`** — `Browser`: `search_url` (pure), `launch` (Chrome with
  `--remote-debugging-port` + profile, no `--enable-automation`), `ensure_logged_in`.
- **`ranker.py`** — `top_posts`, `top_replies` (pure; unchanged).
- **`report.py`** — `render_markdown`, `render_html`, `write_outputs` (pure; unchanged;
  Spanish `summary_text` written by Claude and passed in).
- **`cli.py`** — argparse subcommands, each opening a short-lived CDP connection:
  `launch`, `goto`, `screenshot`, `click`, `scroll`, `read-url`, `crop`,
  `render-report`.

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
 -> cli launch (Chrome + debug port) ; confirm logged-in profile
 -> cli goto <search Top-tab URL>            (CDP Page.navigate)
 -> loop: cli screenshot -> Claude LOOKS -> record posts+likes -> cli scroll   (until enough)
 -> ranker.top_posts -> top ~15-18
    -> per post: cli click(open) -> cli read-url (CDP target URL = permalink)
                 cli screenshot -> Claude picks tweet + image bboxes -> cli crop
                 loop: cli scroll -> cli screenshot -> Claude records replies
                 ranker.top_replies -> top ~5-8 -> cli crop each
                 write run.json (incremental)
 -> Claude writes Spanish summary_text
 -> report.write_outputs -> output/<topic>-<date>/ : report.md, report.html, run.json, screenshots/
```
All clicks/scrolls/screenshots go through CDP into the one Chrome instance; the OS
is never touched.

## 8. Error handling
- **Perception failure:** re-screenshot after a human pause; if still unclear, skip
  that item and continue.
- **Circuit-breaker:** Claude visually detects a rate-limit / unusual-activity /
  login wall → stop and keep collected data.
- **Crash-safety:** `run.json` written incrementally.

## 9. Testing strategy
- **Unit (TDD):** `humanize_math`, `ranker`, `report` rendering, `screenshots`
  (`save_png`/`crop_and_save`), `browser.search_url`, `cdp` message
  framing/target-selection (against a fake socket), `humanize` pacing +
  input-dispatch order (against a fake CDP client), `cli` argument routing
  (against a fake toolkit).
- **Manual/integration:** live browser driving (`launch`, real CDP `goto`, `click`,
  `scroll`, `screenshot`, `read-url`) and the full Claude-driven loop are validated
  in a guided live run.

## 10. Configuration
`max_posts` (18), `max_replies` (8), `output_dir`, `action_budget`, delay range,
window geometry (device-metrics override), `chrome_profile_dir`, `debug_port`
(9222), `min_confidence`.

## 11. Prerequisites / setup
- Python 3.11+ on Windows; Google Chrome.
- `pip install -r requirements.txt` (websocket-client, Pillow, pytest).
- A logged-in Chrome profile for the account to use (ideally a throwaway); the tool
  relaunches Chrome on that profile with the debug port.
- Runs while a Claude Code session drives it.

## 12. Deliverables
- The toolkit modules + `cli.py`.
- `docs/AGENT_RUNBOOK.md`.
- Unit tests.
- `README.md` with setup + the explicit ToS/risk notice.
