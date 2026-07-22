import argparse
import json
import sys
from curator.config import Config
from curator.models import Post, Reply, RunResult


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="curator")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("launch")
    g = sub.add_parser("goto"); g.add_argument("url")
    s = sub.add_parser("screenshot"); s.add_argument("path")
    c = sub.add_parser("click"); c.add_argument("x", type=int); c.add_argument("y", type=int)
    sc = sub.add_parser("scroll"); sc.add_argument("clicks", type=int)
    sub.add_parser("read-url")
    cr = sub.add_parser("crop")
    cr.add_argument("img"); cr.add_argument("x", type=int); cr.add_argument("y", type=int)
    cr.add_argument("w", type=int); cr.add_argument("h", type=int); cr.add_argument("out")
    rr = sub.add_parser("render-report")
    rr.add_argument("records_json"); rr.add_argument("out_dir")
    return p


def load_run(data: dict) -> RunResult:
    posts = []
    for pd in data.get("posts", []):
        replies = [Reply(**rd) for rd in pd.get("top_replies", [])]
        fields = {k: v for k, v in pd.items() if k != "top_replies"}
        posts.append(Post(top_replies=replies, **fields))
    return RunResult(topic=data["topic"], timestamp=data["timestamp"], posts=posts,
                     summary_text=data.get("summary_text", ""),
                     output_dir=data.get("output_dir", ""))


def dispatch(args, deps) -> int:
    cmd = args.cmd
    if cmd == "launch":
        deps["launch"](); return 0
    if cmd == "goto":
        deps["connect"]().navigate(args.url); return 0
    if cmd == "screenshot":
        data = deps["connect"]().screenshot(); deps["save_png"](data, args.path); return 0
    if cmd == "click":
        deps["human"](deps["connect"]()).move_and_click(args.x, args.y); return 0
    if cmd == "scroll":
        deps["human"](deps["connect"]()).scroll(args.clicks); return 0
    if cmd == "read-url":
        print(deps["connect"]().current_url()); return 0
    if cmd == "crop":
        deps["crop_and_save"](args.img, (args.x, args.y, args.w, args.h), args.out); return 0
    if cmd == "render-report":
        with open(args.records_json, encoding="utf-8") as fh:
            run = load_run(json.load(fh))
        deps["write_outputs"](run, args.out_dir); return 0
    return 1


def _real_deps():
    from curator import cdp as cdp_mod, screenshots, report
    from curator.browser import Browser
    from curator.humanize import Human
    cfg = Config.default()
    browser = Browser(cfg)
    return {
        "launch": browser.launch,
        "connect": lambda: cdp_mod.connect(cfg.debug_port, cfg),
        "human": lambda c: Human(c, cfg),
        "save_png": screenshots.save_png,
        "crop_and_save": screenshots.crop_and_save,
        "write_outputs": report.write_outputs,
    }


def main(argv=None) -> int:
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    return dispatch(args, _real_deps())


if __name__ == "__main__":
    raise SystemExit(main())
