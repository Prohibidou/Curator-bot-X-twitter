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
- Never open more than the focused volume. Claude (the brain) counts its own actions during the run and must stop once it reaches `Config.action_budget` — the Python toolkit does not track or enforce this itself.
- If unsure what's on screen, screenshot again rather than guessing a click.
