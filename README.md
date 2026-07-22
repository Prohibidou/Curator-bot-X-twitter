# Twitter Vision Curator

A local agent that a live Claude Code session drives to browse X/Twitter by
vision only (screenshots) and Chrome DevTools Protocol (CDP) input, then
writes a Spanish report of the most popular posts/replies on a topic.

## WARNING
Automating a logged-in account violates X's Terms of Service. Use a throwaway
account you are willing to lose. This tool paces itself like a human to avoid
being blocked; it does NOT and cannot guarantee you won't be detected or
suspended. There is no fingerprint spoofing, proxy rotation, or CAPTCHA solving.

## How it works
- Python toolkit (`curator.cli`) = hands & eyes: launches Chrome with a
  remote-debugging port and drives it over CDP (`websocket-client`) —
  screenshot, click, scroll, crop, read URL, render report. Coordinates are
  viewport pixels, not screen pixels. Control is confined to the Chrome tab
  it opens; it does not move the OS mouse/keyboard and does not touch any
  other window.
- Claude Code = brain: looks at screenshots, decides actions, writes the
  Spanish report. See `docs/AGENT_RUNBOOK.md`.
- No Twitter API, no local model, no DOM scraping, no browser-automation
  framework (no Selenium/Playwright/pyautogui/mss) — just CDP over a
  localhost WebSocket.

## Setup
1. Install Python 3.11+ and Google Chrome.
2. `pip install -r requirements.txt` (pulls in `websocket-client`; no
   pyautogui/mss or OS-level input dependencies).
3. `launch` starts Chrome with `--remote-debugging-port` bound to localhost —
   only processes on this machine can attach to it. Fully close any existing
   Chrome first if you want the CLI to reuse your normal profile/login.
4. Have a throwaway X account; you log in by hand on first launch.

## Use
Ask Claude Code to run a topic; it follows `docs/AGENT_RUNBOOK.md`, driving
`python -m curator.cli ...` and looking at the screenshots.
