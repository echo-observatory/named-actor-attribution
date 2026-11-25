"""Command line: `naa new`, `naa apply`, `naa check`, `naa rehash`, `naa export`, `naa page`, `naa split`,
`naa runs`, `naa cut`, `naa adapt`, `naa misscheck`."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import items as items_mod
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

    p = sub.add_parser("runs", help="list documents' paragraphs with their words, segments and exclusions, to choose cuts")
    p.add_argument("files", nargs="+", type=Path)

    p = sub.add_parser("cut", help="build items from cut lists (docs/cutting.md), check them and report their tiers")
    p.add_argument("cuts", nargs="+", type=Path, help="cut lists, as JSON")
    p.add_argument("--documents", type=Path, default=Path("annotations"), help="folder of the documents (default: annotations/)")
    p.add_argument("--corpus", type=Path, action="append", default=[], help="corpus JSONL, for each item's source details (repeatable)")
    p.add_argument("--out", type=Path, help="write the items here, as JSONL")
    p.add_argument("--page", type=Path, help="also build an annotation page holding the items, to read them")
    p.add_argument("--splits", type=Path, help="the split of each source document (from assign-splits), to fill each item's split")

    p = sub.add_parser("assign-splits", help="assign source documents to dev or test at random, meeting the minimums of spec §9")
    p.add_argument("cuts", nargs="+", type=Path, help="cut lists, as JSON")
    p.add_argument("--documents", type=Path, default=Path("annotations"), help="folder of the documents (default: annotations/)")
    p.add_argument("--out", type=Path, default=Path("splits.json"), help="the file to write (default: splits.json)")
    p.add_argument("--dev-share", type=float, default=0.2, help="chance that a document goes to dev (default: 0.2)")

    p = sub.add_parser("agreement", help="draw the agreement sample (spec §7) and build a blank page of its items")
    p.add_argument("cuts", nargs="+", type=Path, help="cut lists, as JSON")
    p.add_argument("--documents", type=Path, default=Path("annotations"), help="folder of the documents (default: annotations/)")
    p.add_argument("--out", type=Path, default=Path("agreement.json"), help="the sample's item ids (default: agreement.json)")
    p.add_argument("--page", type=Path, required=True, help="the blank annotation page to build for the second annotator")
    p.add_argument("--share", type=float, default=0.2, help="share of each tier (default: 0.2)")
    p.add_argument("--minimum", type=int, default=5, help="items per tier at least (default: 5)")
    p.add_argument("--seed", type=int, default=0, help="seed of the draw (default: 0)")

    p = sub.add_parser("review", help="record the review of items saved from an item page, and put corrections back into their documents")
    p.add_argument("files", nargs="+", type=Path, help="item files or bundles saved from the page built by `naa cut --page`")
    p.add_argument("--documents", type=Path, default=Path("annotations"), help="folder of the documents (default: annotations/)")
    p.add_argument("--cuts", type=Path, default=Path("cuts"), help="folder of the cut lists (default: cuts/)")

    p = sub.add_parser("adapt", help="create an adapted passage as a document of its own (docs/cutting.md)")
    p.add_argument("draft", type=Path, help="the adaptation, as JSON")
    p.add_argument("--documents", type=Path, default=Path("annotations"), help="folder of the documents (default: annotations/)")
    p.add_argument("--force", action="store_true", help="overwrite the adapted document if it exists")

    p = sub.add_parser("misscheck", help="ask a second model for missed segments and doubts; flags go into the documents")
    p.add_argument("files", nargs="+", type=Path)
    p.add_argument("--model", default=None, help="OpenRouter model id (default: the one in misscheck.py)")
    p.add_argument("--force", action="store_true", help="check again a document that already has miss-check-by")

    args = parser.parse_args(argv)
    commands = {"misscheck": _misscheck, "runs": _runs, "cut": _cut, "assign-splits": _assign_splits, "agreement": _agreement, "review": _review, "adapt": _adapt, "new": _new, "apply": _apply, "check": _check, "rehash": _rehash, "export": _export, "page": _page, "split": _split}
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


def _runs(args) -> int:
    for path in args.files:
        doc = _read(path)
        print(f"== {doc.id}")
        excluded = [(x.start, x.end, x.reason) for x in doc.exclusions]
        for k, (a, b) in enumerate(items_mod.paragraphs(doc.text), 1):
            reasons = sorted({r for s, e, r in excluded if s < b and a < e})
            segs = [s for s in doc.segments if a <= s.start < b]
            levels = " ".join(f"{s.speaker}:{s.d or '?'}{s.r or '?'}" for s in segs)
            n_dis = sum(1 for x in doc.distractors if a <= x.start < b)
            flag = f"EXCLUDED({','.join(reasons)})" if reasons else ""
            text = " ".join(doc.text[a:b].split())
            print(f"{k:3} {items_mod.word_count(doc.text[a:b]):4}w {flag:24} {levels:30} dis={n_dis}  {text[:70]}")
    return 0


def _source_details(corpora: list[Path]) -> dict:
    out = {}
    for path in corpora:
        name = path.resolve().parent.name
        with path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    out[(name, str(r["id"]))] = {
                        "url": r.get("url"), "title": r.get("title"), "date": r.get("date"),
                        "license": r.get("license"), "attribution_line": _attribution(name, r)}
    return out


def _attribution(corpus: str, r: dict) -> str | None:
    """The credit line of an article: the corpus's own, or, for Wikinews, the one its README asks for."""
    if r.get("attribution"):
        return r["attribution"]
    if corpus.startswith("wikinews"):
        return (f"“{r.get('title')}”, by Wikinews contributors ({r.get('date')}), licensed under {r.get('license')}: "
                f"{r.get('url')}. Converted to plain text.")
    return None


def _cut(args) -> int:
    details = _source_details(args.corpus)
    splits = json.loads(args.splits.read_text(encoding="utf-8"))["documents"] if args.splits else None
    all_items, failed, ranges, flags, stale = [], False, [], {}, []
    for path in args.cuts:
        spec = json.loads(path.read_text(encoding="utf-8"))
        doc = _read(args.documents / f"{spec['document']}.xml")
        for k, entry in enumerate(spec["items"], 1):
            cut, problems = items_mod.find_cut(doc, entry)
            item_id = f"{doc.id}-{k:02d}"
            if cut is None:
                print(f"{item_id}: error: {'; '.join(problems)}")
                failed = True
                continue
            ranges.append((*items_mod.source_range(doc, cut), item_id))
            item, more = items_mod.make_item(doc, cut, item_id, details.get((doc.source, doc.source_id)))
            for p in problems + more:
                print(f"{item_id}: error: {p}")
            failed |= bool(problems + more)
            item["annotation"]["notes"] = entry.get("note", "")
            if splits is not None:
                item["split"] = splits.get(item["source"]["document"])
                if item["split"] is None:
                    print(f"{item_id}: error: its document {item['source']['document']} has no split in {args.splits}")
                    failed = True
            if entry.get("review") and entry["review"].get("sha256") != items_mod.review_key(item):
                stale.append(item_id)
            flags[item_id] = [f for f in doc.flags if f.quote and f.quote in item["text"]]
            all_items.append(item)
            print(f"{item_id}: {item['tier'] or '—'} ({'+'.join(item['tier_breaks']) or 'base'}), "
                  f"{item['word_count']} words, {len(item['segments'])} segments, {len(item['speakers'])} speakers")
    for a, b in items_mod.overlaps(ranges):
        print(f"error: {a} and {b} take overlapping text from the same document")
        failed = True
    print()
    print(items_mod.yield_table(all_items))
    if splits is not None:
        print()
        print(items_mod.split_table(all_items))
        for p in items_mod.split_problems(all_items, splits):
            print(f"error: {p}")
            failed = True
    unreviewed = [i["item_id"] for i in all_items if not i["annotation"]["reviewed_by"]]
    print(f"\n{len(all_items) - len(unreviewed)} of {len(all_items)} items reviewed.")
    if stale:
        print(f"Changed since their review, to review again: {', '.join(stale)}")
    if args.out:
        args.out.write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in all_items), encoding="utf-8")
    if args.page:
        args.page.write_text(build_page([_item_document(i, flags.get(i["item_id"], [])) for i in all_items]), encoding="utf-8")
    return 1 if failed else 0


def _load_items(cut_paths: list[Path], documents: Path) -> list[dict]:
    """The items of the cut lists, without source details; refuses lists that don't cut cleanly."""
    out = []
    for path in cut_paths:
        spec = json.loads(path.read_text(encoding="utf-8"))
        doc = _read(documents / f"{spec['document']}.xml")
        for k, entry in enumerate(spec["items"], 1):
            cut, problems = items_mod.find_cut(doc, entry)
            if cut is None:
                raise SystemExit(f"{doc.id}-{k:02d}: error: {'; '.join(problems)} (run naa cut)")
            item, _ = items_mod.make_item(doc, cut, f"{doc.id}-{k:02d}")
            out.append(item)
    return out


def _assign_splits(args) -> int:
    all_items = _load_items(args.cuts, args.documents)
    seed, assignment = items_mod.assign_splits(all_items, dev_share=args.dev_share)
    if seed is None:
        print("error: no draw meets the minimums of spec §9; add items to the scarce tiers")
        return 1
    record = {
        "procedure": "Each source document goes to dev with probability dev_share, drawn with Python's random.Random(seed); "
                     "documents of the test_only corpora go to test. The seed is the first, from 0, whose draw meets "
                     "the per-tier, per-split minimums of spec §9.",
        "seed": seed, "dev_share": args.dev_share, "test_only": list(items_mod.BLIND_TEST_ONLY),
        "documents": dict(sorted(assignment.items())),
    }
    args.out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for i in all_items:
        i["split"] = assignment[i["source"]["document"]]
    print(f"seed {seed}: {sum(v == 'dev' for v in assignment.values())} documents to dev, "
          f"{sum(v == 'test' for v in assignment.values())} to test")
    print(items_mod.split_table(all_items))
    return 0


def _agreement(args) -> int:
    all_items = _load_items(args.cuts, args.documents)
    ids = items_mod.agreement_sample(all_items, args.share, args.minimum, args.seed)
    args.out.write_text(json.dumps({"seed": args.seed, "share": args.share, "minimum": args.minimum, "items": ids},
                                   indent=1) + "\n", encoding="utf-8")
    by_id = {i["item_id"]: i for i in all_items}
    args.page.write_text(build_page([markup.blank(i, by_id[i]["text"]) for i in ids]), encoding="utf-8")
    print(f"{len(ids)} items in the sample, in {args.page}")
    return 0


def _review(args) -> int:
    failed = False
    for path in args.files:
        for reviewed in markup.parse_many(path.read_text(encoding="utf-8")):
            item_id = reviewed.id
            if reviewed.status != "reviewed":
                print(f"{item_id}: not marked reviewed, left as it is")
                continue
            if not reviewed.annotator:
                print(f"{item_id}: error: reviewed, but no annotator")
                failed = True
                continue
            doc_id, _, number = item_id.rpartition("-")
            cuts_path, doc_path = args.cuts / f"{doc_id}.json", args.documents / f"{doc_id}.xml"
            if not number.isdigit() or not cuts_path.exists() or not doc_path.exists():
                print(f"{item_id}: error: no document and cut list for this item id")
                failed = True
                continue
            spec = json.loads(cuts_path.read_text(encoding="utf-8"))
            if not 1 <= int(number) <= len(spec["items"]):
                print(f"{item_id}: error: {cuts_path} has {len(spec['items'])} items")
                failed = True
                continue
            entry = spec["items"][int(number) - 1]
            doc = _read(doc_path)
            cut, problems = items_mod.find_cut(doc, entry)
            try:
                if cut is None:
                    raise ValueError("; ".join(problems))
                names, changes = items_mod.merge_review(doc, cut, reviewed)
            except ValueError as e:
                print(f"{item_id}: error: {e}")
                failed = True
                continue
            if changes:
                doc_path.write_text(markup.serialize(doc), encoding="utf-8")
            if names:
                entry["names"] = names
            else:
                entry.pop("names", None)
            cut, problems = items_mod.find_cut(doc, entry)
            item, _ = items_mod.make_item(doc, cut, item_id)
            entry["review"] = {"by": reviewed.annotator, "sha256": items_mod.review_key(item)}
            cuts_path.write_text(json.dumps(spec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(f"{item_id}: reviewed by {reviewed.annotator}" + ("" if changes else ", no change"))
            for c in changes + problems:
                print(f"  {c}")
    return 1 if failed else 0


def _adapt(args) -> int:
    spec = json.loads(args.draft.read_text(encoding="utf-8"))
    source = _read(args.documents / f"{spec['document']}.xml")
    cut, problems = items_mod.find_cut(source, spec)
    if cut is None:
        print(f"{args.draft}: error: {'; '.join(problems)}", file=sys.stderr)
        return 1
    doc = markup.adapted(source, cut.start, cut.end, spec["text"], spec["adaptation"], spec["id"])
    path = args.documents / f"{doc.id}.xml"
    if path.exists() and not args.force:
        print(f"{path} exists, left as it is (use --force to overwrite)", file=sys.stderr)
        return 1
    doc, problems = markup.apply_draft(doc, spec)
    for p in problems:
        print(f"{args.draft}: error: {p}", file=sys.stderr)
    if problems:
        return 1
    path.write_text(markup.serialize(doc), encoding="utf-8")
    for p in markup.check(doc):
        print(f"{path}: {p}")
    print(f"{path}: adapted from {source.id} [{cut.start}, {cut.end}), {len(doc.segments)} segments")
    return 0


def _misscheck(args) -> int:
    from . import misscheck
    model = args.model or misscheck.DEFAULT_MODEL
    try:
        key = misscheck.api_key()
    except misscheck.MissCheckError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    failed = False
    for path in args.files:
        doc = _read(path)
        if doc.miss_check_by and not args.force:
            print(f"{path}: already checked by {doc.miss_check_by}, skipped (use --force)")
            continue
        try:
            flags, info = misscheck.check_document(doc, model, key)
        except misscheck.MissCheckError as e:
            print(f"{path}: error: {e}", file=sys.stderr)
            failed = True
            continue
        doc.flags = flags
        doc.miss_check_by = model
        path.write_text(markup.serialize(doc), encoding="utf-8")
        missing = sum(1 for f in flags if f.quote not in doc.text)
        usage = info.get("usage") or {}
        print(f"{path}: {sum(f.kind == 'missed' for f in flags)} missed, {sum(f.kind == 'doubt' for f in flags)} doubts"
              f"{f', {missing} not found in the text' if missing else ''}"
              f" ({usage.get('prompt_tokens', '?')} + {usage.get('completion_tokens', '?')} tokens)")
    return 1 if failed else 0


def _item_document(item: dict, flags: list[markup.Flag] = ()) -> markup.Document:
    """An item as a markup document, to read or review it in the annotation page, with the miss-check
    flags of its document that fall inside it."""
    doc = markup.blank(item["item_id"], item["text"], item["source"].get("document"))
    reviewer = item["annotation"]["reviewed_by"]
    doc.status, doc.annotator = ("reviewed", reviewer) if reviewer else ("drafted", None)
    doc.drafted_by, doc.miss_check_by = item["annotation"]["drafted_by"], item["annotation"]["miss_check_by"]
    doc.flags = list(flags)
    doc.speakers = [markup.Speaker(s["speaker_id"], s["canonical_name"], s["type"]) for s in item["speakers"]]
    doc.segments = [markup.Segment(s["speaker_id"], s["start"], s["end"], s["detection_level"], s["reference_level"])
                    for s in item["segments"]]
    doc.distractors = [markup.Distractor(d["type"], *d["spans"][0], d.get("note")) for d in item["distractors"]]
    doc.notes = f"{item['tier']} ({'+'.join(item['tier_breaks']) or 'base'}). {item['annotation']['notes']}".strip()
    return doc


if __name__ == "__main__":
    sys.exit(main())
