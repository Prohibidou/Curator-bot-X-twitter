import json
from curator.cli import build_parser, load_run, dispatch


def test_load_run_rebuilds_dataclasses():
    data = {"topic": "t", "timestamp": "2026-07-22", "summary_text": "s",
            "output_dir": "o",
            "posts": [{"author_handle": "@a", "author_name": "A", "text": "x",
                       "likes": 5, "replies": 0, "reposts": 0,
                       "top_replies": [{"author_handle": "@b", "author_name": "B",
                                        "text": "y", "likes": 1}]}]}
    run = load_run(data)
    assert run.topic == "t"
    assert run.posts[0].likes == 5
    assert run.posts[0].top_replies[0].author_handle == "@b"


def test_dispatch_routes_crop_to_dep():
    calls = {}
    deps = {"crop_and_save": lambda img, bbox, out: calls.setdefault("crop", (img, bbox, out))}
    parser = build_parser()
    args = parser.parse_args(["crop", "in.png", "1", "2", "3", "4", "out.png"])
    rc = dispatch(args, deps)
    assert rc == 0
    assert calls["crop"] == ("in.png", (1, 2, 3, 4), "out.png")


def test_dispatch_routes_render_report(tmp_path):
    data = {"topic": "t", "timestamp": "d", "summary_text": "s", "output_dir": "",
            "posts": []}
    p = tmp_path / "rec.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    written = {}
    deps = {"write_outputs": lambda run, out: written.setdefault("w", (run.topic, out))}
    args = build_parser().parse_args(["render-report", str(p), str(tmp_path / "out")])
    rc = dispatch(args, deps)
    assert rc == 0
    assert written["w"][0] == "t"
