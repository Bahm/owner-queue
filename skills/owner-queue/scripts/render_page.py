#!/usr/bin/env python3
import argparse
import html
import os
import re
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "owner-queue.html"
TOKEN = "__QUEUE_TITLE__"


def slug_of(title: str) -> str:
    return re.sub(r"[\W_]+", "-", title.lower()).strip("-") or "queue"


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the Owner Queue page for one queue.")
    parser.add_argument("title", help="The queue's name, e.g. 'Website Launch'")
    parser.add_argument("--out", type=Path, help="Defaults to ${XDG_CACHE_HOME:-~/.cache}/owner-queue/<slug>/page.html")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing page, e.g. to re-render a published queue")
    args = parser.parse_args()
    if not args.title.strip():
        parser.error("the title must not be empty")

    try:
        template = TEMPLATE.read_text(encoding="utf-8")
    except OSError as error:
        raise SystemExit(f"Can't read the template: {error}")
    if template.count(TOKEN) != 2:
        raise SystemExit(f"{TEMPLATE} must contain {TOKEN} exactly twice (<title> and <h1>)")
    cache_home = os.environ.get("XDG_CACHE_HOME", "")
    cache = Path(cache_home) if os.path.isabs(cache_home) else Path.home() / ".cache"
    out = args.out or cache / "owner-queue" / slug_of(args.title) / "page.html"
    if out.is_dir():
        raise SystemExit(f"--out must be a file path, not the folder {out}")
    if out.exists() and not args.force:
        raise SystemExit(f"{out} already exists. Pass --force to overwrite it.")
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(template.replace(TOKEN, html.escape(html.unescape(args.title))), encoding="utf-8")
    except OSError as error:
        raise SystemExit(f"Can't write the page: {error}")
    print(out)


if __name__ == "__main__":
    main()
