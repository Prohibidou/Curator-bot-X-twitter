import base64
import html
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
             "## Resumen", "", run.summary_text, "",
             "## Publicaciones destacadas", ""]
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
    parts = ["<!doctype html><html lang='es'><head><meta charset='utf-8'>",
             f"<title>Twitter: {html.escape(run.topic)}</title></head><body>",
             f"<h1>Twitter: {html.escape(run.topic)}</h1><p><em>{run.timestamp}</em></p>",
             "<h2>Resumen</h2>", f"<p>{html.escape(run.summary_text)}</p>",
             "<h2>Publicaciones destacadas</h2>"]
    for i, p in enumerate(run.posts, 1):
        parts.append(f"<h3>{i}. {html.escape(p.author_name)} ({html.escape(p.author_handle)}) — {p.likes} likes</h3>")
        parts.append(f"<p>{html.escape(p.text)}</p>")
        parts.append(_img_tag(p.screenshot_path))
        for img in p.image_screenshot_paths:
            parts.append(_img_tag(img))
        parts.append(f"<p>Enlace: <a href='{html.escape(p.permalink, quote=True)}'>{html.escape(p.permalink)}</a></p>")
        if p.top_replies:
            parts.append("<h4>Respuestas destacadas</h4><ul>")
            for r in p.top_replies:
                parts.append(f"<li>({r.likes} likes) {html.escape(r.author_handle)}: {html.escape(r.text)} "
                             f"{_img_tag(r.screenshot_path)}</li>")
            parts.append("</ul>")
    parts.append("</body></html>")
    return "".join(parts)


def write_outputs(run, base_dir: str) -> None:
    os.makedirs(base_dir, exist_ok=True)
    with open(os.path.join(base_dir, "report.md"), "w", encoding="utf-8") as fh:
        fh.write(render_markdown(run))
    with open(os.path.join(base_dir, "report.html"), "w", encoding="utf-8") as fh:
        fh.write(render_html(run))
    with open(os.path.join(base_dir, "run.json"), "w", encoding="utf-8") as fh:
        json.dump(asdict(run), fh, ensure_ascii=False, indent=2)
