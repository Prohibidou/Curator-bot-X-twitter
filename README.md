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
