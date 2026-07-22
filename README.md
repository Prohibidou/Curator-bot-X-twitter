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
