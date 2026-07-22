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
