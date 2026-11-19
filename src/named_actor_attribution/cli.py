"""Command line: `naa new`, `naa apply`, `naa check`, `naa rehash`, `naa export`, `naa page`, `naa split`."""

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

    p = sub.add_parser("apply", help="annotate a document from a draft that quotes each span (docs/drafting.md)")
    p.add_argument("file", type=Path, help="the document to annotate; its speakers and spans are replaced")
    p.add_argument("draft", type=Path, help="the draft, as JSON")

    p = sub.add_parser("check", help="check documents; exit 1 if any has an error")
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--quiet", action="store_true", help="show errors only")

    p = sub.add_parser("rehash", help="accept a deliberate change to a document's text")
    p.add_argument("files", nargs="+", type=Path)

    p = sub.add_parser("export", help="write documents as JSONL records with offsets")
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--out", type=Path, help="output file (default: standard output)")

    p = sub.add_parser("page", help="build a copy of the annotation page with documents built in, to send to annotators")
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--out", type=Path, required=True, help="the HTML file to write")
    p.add_argument("--blank", action="store_true", help="remove the annotation, for annotating from scratch")

    p = sub.add_parser("split", help="split a file saved with the page's \"Save all\" into one file per document")
    p.add_argument("bundle", type=Path)
    p.add_argument("--out", type=Path, default=Path("annotations"), help="folder to write to (default: annotations/)")
    p.add_argument("--force", action="store_true", help="overwrite files that exist and differ")

    args = parser.parse_args(argv)
    commands = {"new": _new, "apply": _apply, "check": _check, "rehash": _rehash, "export": _export, "page": _page, "split": _split}
    return commands[args.command](args)


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


PAGE = Path(__file__).resolve().parents[2] / "annotator" / "annotator.html"
EMBED = '<script type="application/json" id="embedded-documents">[]</script>'


def build_page(docs: list[markup.Document], template: str | None = None) -> str:
    """The annotation page with these documents built in."""
    template = PAGE.read_text(encoding="utf-8") if template is None else template
    if template.count(EMBED) != 1:
        raise ValueError(f"the page template must contain {EMBED} exactly once")
    # Escaping "<" keeps "</script>" and "<!--" in a text from ending the script element.
    payload = json.dumps([markup.serialize(d) for d in docs], ensure_ascii=False).replace("<", "\\u003c")
    return template.replace(EMBED, EMBED.replace("[]", payload))


def _apply(args) -> int:
    doc = _read(args.file)
    draft = json.loads(args.draft.read_text(encoding="utf-8"))
    doc, problems = markup.apply_draft(doc, draft)
    for p in problems:
        print(f"{args.draft}: error: {p}", file=sys.stderr)
    if problems:
        return 1
    try:
        content = markup.serialize(doc)
    except ValueError as e:
        print(f"{args.draft}: error: {e}", file=sys.stderr)
        return 1
    args.file.write_text(content, encoding="utf-8")
    for p in markup.check(doc):
        print(f"{args.file}: {p}")
    print(f"{args.file}: {len(doc.segments)} segments, {len(doc.distractors)} distractors, {len(doc.exclusions)} exclusions")
    return 0


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


def _page(args) -> int:
    docs = []
    for path in args.files:
        try:
            docs += markup.parse_many(path.read_text(encoding="utf-8"))
        except markup.MarkupError as e:
            print(f"{path}: error: {e}", file=sys.stderr)
            return 1
    if args.blank:
        docs = [markup.stripped(d) for d in docs]
    args.out.write_text(build_page(docs), encoding="utf-8")
    print(f"{args.out}: {len(docs)} document{'s' if len(docs) != 1 else ''}")
    return 0


def _split(args) -> int:
    try:
        docs = markup.parse_many(args.bundle.read_text(encoding="utf-8"))
    except markup.MarkupError as e:
        print(f"{args.bundle}: error: {e}", file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    status = 0
    for doc in docs:
        path = args.out / f"{doc.id}.xml"
        content = markup.serialize(doc)
        if path.exists() and path.read_text(encoding="utf-8") != content and not args.force:
            print(f"{path} exists and differs, left as it is (use --force to overwrite)", file=sys.stderr)
            status = 1
            continue
        path.write_text(content, encoding="utf-8")
        print(path)
    return status


if __name__ == "__main__":
    sys.exit(main())
