"""Command line: `naa new`, `naa check`, `naa rehash`, `naa export`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import markup


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="naa", description="Work with annotated documents in the markup format.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("new", help="create blank documents from a JSONL corpus, ready to annotate")
    p.add_argument("corpus", type=Path, help="JSONL file with one article per line, with `id` and `text` fields")
    p.add_argument("ids", nargs="+", help="ids of the articles to create documents for")
    p.add_argument("--out", type=Path, default=Path("annotations"), help="folder to write to (default: annotations/)")
    p.add_argument("--source", help="name of the corpus (default: the corpus file's folder name)")

    p = sub.add_parser("check", help="check documents; exit 1 if any has an error")
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--quiet", action="store_true", help="show errors only")

    p = sub.add_parser("rehash", help="accept a deliberate change to a document's text")
    p.add_argument("files", nargs="+", type=Path)

    p = sub.add_parser("export", help="write documents as JSONL records with offsets")
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--out", type=Path, help="output file (default: standard output)")

    args = parser.parse_args(argv)
    return {"new": _new, "check": _check, "rehash": _rehash, "export": _export}[args.command](args)


def _new(args) -> int:
    source = args.source or args.corpus.resolve().parent.name
    wanted = set(args.ids)
    found = {}
    with args.corpus.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                if str(rec["id"]) in wanted:
                    found[str(rec["id"])] = rec["text"]
    missing = wanted - found.keys()
    if missing:
        print(f"not in {args.corpus}: {', '.join(sorted(missing))}", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    for source_id in args.ids:
        doc_id = f"{source}-{source_id}"
        path = args.out / f"{doc_id}.xml"
        if path.exists():
            print(f"{path} exists, left as it is", file=sys.stderr)
            continue
        path.write_text(markup.serialize(markup.blank(doc_id, found[source_id], source, source_id)), encoding="utf-8")
        print(path)
    return 0


def _read(path: Path) -> markup.Document:
    return markup.parse(path.read_text(encoding="utf-8"))


def _check(args) -> int:
    failed = False
    for path in args.files:
        try:
            problems = markup.check(_read(path))
        except markup.MarkupError as e:
            problems = [markup.Problem("error", str(e))]
        if args.quiet:
            problems = [p for p in problems if p.level == "error"]
        failed |= any(p.level == "error" for p in problems)
        for p in problems:
            print(f"{path}: {p}")
    return 1 if failed else 0


def _rehash(args) -> int:
    for path in args.files:
        path.write_text(markup.rehash(path.read_text(encoding="utf-8")), encoding="utf-8")
    return 0


def _export(args) -> int:
    lines = []
    for path in args.files:
        try:
            doc = _read(path)
        except markup.MarkupError as e:
            print(f"{path}: error: {e}", file=sys.stderr)
            return 1
        lines.append(json.dumps(markup.to_record(doc), ensure_ascii=False))
    out = "\n".join(lines) + "\n"
    if args.out:
        args.out.write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
