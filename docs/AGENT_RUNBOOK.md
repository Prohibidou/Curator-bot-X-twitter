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
