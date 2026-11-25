"""Cutting reviewed documents into dataset items, and computing their tiers (spec §4–§6).

A cut list names, for one document, the passages to keep: each by its first and last words,
with the item's levels where they differ from the document's (see docs/cutting.md).
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from dataclasses import dataclass, field

from . import markup

# Spec §4: tier, max D, max R, max speakers (None: any), max words.
TIERS = [
    ("T0", None, None, 0, 600),
    ("T1", "D1", "R1", 1, 60),
    ("T2", "D2", "R2", 1, 80),
    ("T3", "D2", "R2", 3, 150),
    ("T4", "D3", "R3", 3, 250),
    ("T5", "D4", "R4", 4, 350),
    ("T6", "D4", "R5", None, 600),
    ("T7", "D5", "R6", None, 600),
]
# The column of each tier's main added difficulty (spec §4): at least half of a tier's items
# must break the tier below there.
MAIN_DIFFICULTY = {"T2": ("D", "R"), "T3": ("speakers",), "T4": ("D", "R"), "T5": ("D", "R"),
                   "T6": ("D", "R"), "T7": ("D", "R")}
# Spec §9: minimum items and segments per tier and split.
# Dev has no segment target: it needs examples (the prototypes), not statistical power.
TARGETS = {"test": {"items": 8, "segments": 40}, "dev": {"items": 5, "segments": 0}}
T0_TARGETS = {"test": 20, "dev": 10}

SENTENCE_END = re.compile(r"[.!?…][\"'”’)\]]*$")


@dataclass
class Cut:
    """A passage to keep: [start, end) in the document, and level overrides by segment start."""
    start: int
    end: int
    levels: dict[int, tuple[str | None, str | None]] = field(default_factory=dict)
    # The canonical name in this item, by the document's speaker id, when it differs from the
    # document's: the fullest name the item itself uses (spec §2), e.g. "Ashburne".
    names: dict[str, str] = field(default_factory=dict)
    # The item's human review, from the cut list: {"by": reviewer, "sha256": review_key of the item reviewed}.
    review: dict | None = None


def paragraphs(text: str) -> list[tuple[int, int]]:
    """The paragraphs of a text, as [start, end) ranges: separated by blank lines."""
    out, pos = [], 0
    for m in re.finditer(r"\n\s*\n", text):
        if text[pos:m.start()].strip():
            out.append((pos, m.start()))
        pos = m.end()
    if text[pos:].strip():
        out.append((pos, len(text)))
    return out


def word_count(text: str) -> int:
    return len(text.split())


def level_rank(level: str | None) -> int:
    return int(level[1:]) if level else 0


def compute_tier(segments: list[dict], n_speakers: int, words: int) -> tuple[str | None, list[str]]:
    """The item's tier, and the columns where it breaks the caps of the tier below.

    Returns (None, reasons) when no tier fits.
    """
    if not segments:
        return ("T0", []) if words <= 600 else (None, ["more than 600 words"])
    if any(s["detection_level"] is None or s["reference_level"] is None for s in segments):
        return None, ["a segment has no level"]
    d = max(level_rank(s["detection_level"]) for s in segments)
    r = max(level_rank(s["reference_level"]) for s in segments)

    def fits(row) -> bool:
        _, max_d, max_r, max_sp, max_w = row
        return (max_d is not None and d <= level_rank(max_d) and r <= level_rank(max_r)
                and (max_sp is None or n_speakers <= max_sp) and words <= max_w)

    for i, row in enumerate(TIERS[1:], 1):
        if fits(row):
            breaks = []
            if i > 1:
                _, bd, br, bsp, bw = TIERS[i - 1]
                if d > level_rank(bd):
                    breaks.append("D")
                if r > level_rank(br):
                    breaks.append("R")
                if bsp is not None and n_speakers > bsp:
                    breaks.append("speakers")
                if words > bw:
                    breaks.append("words")
            return row[0], breaks
    return None, ["more than 600 words"]


def make_item(doc: markup.Document, cut: Cut, item_id: str, source: dict | None = None) -> tuple[dict, list[str]]:
    """Build the item for one cut, in the format of spec §6, with the problems found."""
    problems: list[str] = []
    start, end = cut.start, cut.end
    text = doc.text[start:end]

    def inside(a: int, b: int) -> bool:
        return start <= a and b <= end

    def overlaps(a: int, b: int) -> bool:
        return a < end and start < b

    for x in doc.exclusions:
        if overlaps(x.start, x.end):
            problems.append(f"contains an exclusion ({x.reason}): {_short(doc.text[x.start:x.end])}")
    for kind, spans in (("segment", doc.segments), ("distractor", doc.distractors)):
        for s in spans:
            if overlaps(s.start, s.end) and not inside(s.start, s.end):
                problems.append(f"cuts a {kind} in two: {_short(doc.text[s.start:s.end])}")

    paras = paragraphs(doc.text)
    starts_para = any(p[0] == start for p in paras) or _after_excluded_line(doc, start)
    ends_para = any(p[1] == end for p in paras)
    before = doc.text[:start].rstrip()
    if not (starts_para or SENTENCE_END.search(before) or not before):
        problems.append(f"doesn't start at a sentence: {_short(text)}")
    if not (ends_para or SENTENCE_END.search(text.rstrip())):
        problems.append(f"doesn't end at a sentence: {_short(text[-40:])}")
    if text != text.strip():
        problems.append("starts or ends with whitespace")

    segs = sorted((s for s in doc.segments if inside(s.start, s.end)), key=lambda s: s.start)
    used = []
    for s in segs:
        if s.speaker not in used:
            used.append(s.speaker)
    by_id = {sp.id: sp for sp in doc.speakers}
    speakers = []
    for k, sid in enumerate(used, 1):
        sp = by_id.get(sid)
        if sp is None:
            problems.append(f"unknown speaker {sid}")
            continue
        name = cut.names.get(sid, sp.name)
        if not markup.name_occurs(name, text):
            problems.append(f"the name {name!r} is not in the passage")
        speakers.append({"speaker_id": f"S{k}", "canonical_name": name, "type": sp.type, "_doc_id": sid})
    new_id = {s["_doc_id"]: s["speaker_id"] for s in speakers}
    for s in speakers:
        del s["_doc_id"]

    segments = []
    for k, s in enumerate(segs, 1):
        d, r = cut.levels.get(s.start, (s.d, s.r))
        segments.append({
            "segment_id": f"G{k}", "speaker_id": new_id.get(s.speaker), "start": s.start - start, "end": s.end - start,
            "text": doc.text[s.start:s.end], "detection_level": d, "reference_level": r,
        })
    distractors = [
        {"type": x.type, "spans": [[x.start - start, x.end - start]], "note": x.note}
        for x in sorted(doc.distractors, key=lambda x: x.start) if inside(x.start, x.end)
    ]
    words = word_count(text)
    tier, breaks = compute_tier(segments, len(speakers), words)
    if tier is None:
        problems.append(f"no tier fits: {', '.join(breaks)}")
    elif tier == "T0" and not distractors:
        problems.append("a T0 item needs at least one distractor")
    elif tier not in ("T0", "T1", "T2") and not (starts_para and ends_para):
        problems.append(f"{tier} items are made of whole paragraphs")

    if doc.adapted_from is None:
        src = {**(source or {}), "document": doc.id, "start_offset": start, "adapted": False, "adaptation": None}
    else:
        if tier not in (None, "T0", "T1", "T2", "T3"):
            problems.append(f"an adapted item is {tier}: only T0–T3 items may be adapted (spec §5.1)")
        if (start, end) != (0, len(doc.text)):
            problems.append("an adapted document is one item: cut it whole")
        src = {**(source or {}), "document": doc.adapted_from, "start_offset": doc.source_start,
               "adapted": True, "adaptation": doc.adaptation}
        if src.get("attribution_line"):
            src["attribution_line"] += " Adapted for this dataset."

    item = {
        "item_id": item_id,
        "tier": tier,
        "tier_breaks": breaks,
        "split": None,
        "text": text,
        "word_count": words,
        "source": src,
        "speakers": speakers,
        "segments": segments,
        "distractors": distractors,
        "annotation": {"drafted_by": doc.drafted_by, "miss_check_by": doc.miss_check_by,
                       "reviewed_by": None, "second_annotator": None, "nested_checked": True, "notes": ""},
    }
    # Reviewed as an item, if the review matches what the item is now. An item without a review of its own
    # is reviewed with its document; one whose review is out of date is not reviewed, whatever the document is.
    if cut.review:
        if cut.review.get("sha256") == review_key(item):
            item["annotation"]["reviewed_by"] = cut.review.get("by")
    elif doc.status == "reviewed":
        item["annotation"]["reviewed_by"] = doc.annotator
    return item, problems


def review_key(item: dict) -> str:
    """A fingerprint of what a reviewer checks in an item: its text, speakers, segments and distractors, not levels."""
    payload = {
        "text": item["text"],
        "speakers": [[s["speaker_id"], s["canonical_name"], s["type"]] for s in item["speakers"]],
        "segments": [[s["speaker_id"], s["start"], s["end"]] for s in item["segments"]],
        "distractors": [[d["type"], d["spans"]] for d in item["distractors"]],
    }
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def merge_review(doc: markup.Document, cut: Cut, reviewed: markup.Document) -> tuple[dict[str, str], list[str]]:
    """Put the annotation of a reviewed item back into its document, which is changed in place.

    Returns the item's name overrides (the cut list's `names`) and the changes made. Levels are not
    reviewed: a segment the reviewer left as it was keeps its levels; a new or changed one has none.
    """
    start, end = cut.start, cut.end
    if doc.text[start:end] != reviewed.text:
        raise ValueError("the item's text is not its document's passage: was the cut list changed?")

    def inside(s) -> bool:
        return start <= s.start and s.end <= end

    used = []
    for s in sorted((s for s in doc.segments if inside(s)), key=lambda s: s.start):
        if s.speaker not in used:
            used.append(s.speaker)
    by_id = {sp.id: sp for sp in doc.speakers}
    names, changes, to_doc = dict(cut.names), [], {}
    for sp in reviewed.speakers:
        k = int(sp.id[1:]) if re.fullmatch(r"S\d+", sp.id) else 0
        if 1 <= k <= len(used):
            did = used[k - 1]
        else:  # a speaker the reviewer added: one of the document's, or a new one
            did = next((d.id for d in doc.speakers if sp.name in (d.name, names.get(d.id))), None)
            if did is None:
                did = f"S{max((int(d.id[1:]) for d in doc.speakers if d.id[1:].isdigit()), default=0) + 1}"
                doc.speakers.append(markup.Speaker(did, sp.name, sp.type))
                by_id[did] = doc.speakers[-1]
                changes.append(f"new speaker {sp.name!r}")
        to_doc[sp.id] = did
        doc_sp = by_id[did]
        if sp.name != names.get(did, doc_sp.name):
            changes.append(f"name in this item: {names.get(did, doc_sp.name)!r} → {sp.name!r}")
        if sp.name == doc_sp.name:
            names.pop(did, None)
        else:
            names[did] = sp.name
        if sp.type != doc_sp.type:
            changes.append(f"type of {doc_sp.name!r}: {doc_sp.type} → {sp.type}")
            doc_sp.type = sp.type

    old_segs = {(s.speaker, s.start, s.end): s for s in doc.segments if inside(s)}
    new_segs = []
    for s in reviewed.segments:
        key = (to_doc.get(s.speaker, s.speaker), s.start + start, s.end + start)
        kept = old_segs.get(key)
        new_segs.append(markup.Segment(key[0], key[1], key[2], kept.d if kept else None, kept.r if kept else None,
                                       kept.note if kept else s.note))
    for key in sorted(set(old_segs) - {(s.speaker, s.start, s.end) for s in new_segs}, key=lambda k: k[1]):
        changes.append(f"segment removed or changed: {_short(doc.text[key[1]:key[2]])}")
    for s in new_segs:
        if (s.speaker, s.start, s.end) not in old_segs:
            changes.append(f"segment added (needs levels): {_short(doc.text[s.start:s.end])}")
    doc.segments = sorted([s for s in doc.segments if not inside(s)] + new_segs, key=lambda s: s.start)

    old_dis = {(x.type, x.start, x.end) for x in doc.distractors if inside(x)}
    new_dis = [markup.Distractor(x.type, x.start + start, x.end + start, x.note) for x in reviewed.distractors]
    if old_dis != {(x.type, x.start, x.end) for x in new_dis}:
        changes.append("distractors changed")
    doc.distractors = sorted([x for x in doc.distractors if not inside(x)] + new_dis, key=lambda x: x.start)

    for x in reviewed.exclusions:
        doc.exclusions.append(markup.Exclusion(x.reason, x.start + start, x.end + start, x.note))
        changes.append(f"exclusion added ({x.reason}): {_short(doc.text[x.start + start:x.end + start])}")
    doc.exclusions.sort(key=lambda x: x.start)
    return names, changes


def _after_excluded_line(doc: markup.Document, pos: int) -> bool:
    """Whether pos starts a line whose previous line is excluded as boilerplate, such as a section
    heading on its own line at the top of a paragraph: the line after it starts the paragraph's text."""
    if pos == 0 or doc.text[pos - 1] != "\n":
        return False
    line_start = doc.text.rfind("\n", 0, pos - 1) + 1
    return any(x.reason == "boilerplate" and x.start <= line_start and pos - 1 <= x.end for x in doc.exclusions)


def _short(s: str, n: int = 50) -> str:
    s = " ".join(s.split())
    return repr(s if len(s) <= n else s[: n - 1] + "…")


def find_cut(doc: markup.Document, entry: dict) -> tuple[Cut | None, list[str]]:
    """A cut-list entry: {"from": first words, "to": last words, "n": …, "levels": {seg start words: [D, R]},
    "names": {document speaker id: name in this item}}."""
    if "from" not in entry:  # the whole document, e.g. an adapted passage
        return Cut(0, len(doc.text), names=dict(entry.get("names", {})), review=entry.get("review")), []
    first, last = entry["from"], entry["to"]
    hits = [m.start() for m in re.finditer(re.escape(first), doc.text)]
    n = entry.get("n")
    if not hits:
        return None, [f"not found: {first[:60]!r}"]
    if n is None and len(hits) > 1:
        return None, [f"found {len(hits)} times, say which with n: {first[:60]!r}"]
    start = hits[(n or 1) - 1]
    j = doc.text.find(last, start)
    if j < 0:
        return None, [f"end not found after {first[:30]!r}: {last[:60]!r}"]
    cut = Cut(start, j + len(last), names=dict(entry.get("names", {})), review=entry.get("review"))
    problems = [f"names: no speaker {sid} in the document" for sid in cut.names if sid not in {s.id for s in doc.speakers}]
    for words, (d, r) in entry.get("levels", {}).items():
        seg = [s for s in doc.segments if cut.start <= s.start < cut.end and doc.text[s.start:s.end].startswith(words)]
        if len(seg) != 1:
            problems.append(f"levels: {len(seg)} segments of the passage start with {words!r}")
            continue
        cut.levels[seg[0].start] = (d, r)
    return cut, problems


def source_range(doc: markup.Document, cut: Cut) -> tuple[str, int, int]:
    """The document and range an item takes its text from: for an adapted item, its source passage."""
    if doc.adapted_from is not None:
        return doc.adapted_from, doc.source_start, doc.source_end
    return doc.id, cut.start, cut.end


def overlaps(ranges: list[tuple[str, int, int, str]]) -> list[tuple[str, str]]:
    """Pairs of items that take overlapping text from the same document: (document, start, end, item id)."""
    out = []
    ordered = sorted(ranges)
    for i, (doc, start, end, item) in enumerate(ordered):
        for doc2, start2, _, item2 in ordered[i + 1:]:
            if doc2 != doc or start2 >= end:
                break
            out.append((item, item2))
    return out


def yield_table(items: list[dict]) -> str:
    """Items and gold segments per tier, against the targets of spec §9 for test + dev."""
    rows = ["| Tier | Items | Segments | Target items | Target segments | Breaks on its main difficulty |",
            "| --- | --- | --- | --- | --- | --- |"]
    for tier, *_ in TIERS:
        its = [i for i in items if i["tier"] == tier]
        segs = sum(len(i["segments"]) for i in its)
        if tier == "T0":
            target_items, target_segs = T0_TARGETS["test"] + T0_TARGETS["dev"], "–"
        else:
            target_items = TARGETS["test"]["items"] + TARGETS["dev"]["items"]
            target_segs = TARGETS["test"]["segments"] + TARGETS["dev"]["segments"]
        main = MAIN_DIFFICULTY.get(tier)
        on_main = (f"{sum(1 for i in its if set(i['tier_breaks']) & set(main))} of {len(its)}"
                   if main and its else "–")
        rows.append(f"| {tier} | {len(its)} | {segs} | {target_items} | {target_segs} | {on_main} |")
    return "\n".join(rows)


# Spec §9: corpora used blind by another evaluation, whose items go to test only.
BLIND_TEST_ONLY = ("wikinews-repeated-claims-iran-nuclear-59",)
SPLITS = ("dev", "test")


def split_problems(items: list[dict], assignment: dict[str, str], targets: dict = TARGETS,
                   t0_targets: dict = T0_TARGETS) -> list[str]:
    """Where the per-tier, per-split minimums of spec §9 are not met; assignment maps source documents to splits."""
    problems = []
    for tier, *_ in TIERS:
        for split in SPLITS:
            its = [i for i in items if i["tier"] == tier and assignment.get(i["source"]["document"]) == split]
            n, segs = len(its), sum(len(i["segments"]) for i in its)
            need_items, need_segs = (t0_targets[split], 0) if tier == "T0" else (targets[split]["items"], targets[split]["segments"])
            if n < need_items:
                problems.append(f"{tier} {split}: {n} items, needs {need_items}")
            if segs < need_segs:
                problems.append(f"{tier} {split}: {segs} segments, needs {need_segs}")
    return problems


def assign_splits(items: list[dict], dev_share: float = 0.2, test_only: tuple[str, ...] = BLIND_TEST_ONLY,
                  seeds=range(10000), **targets) -> tuple[int | None, dict[str, str]]:
    """Assign each source document to dev or test at random: all its items go together, adapted passages
    included (spec §9). Documents of a corpus in test_only go to test. Draws are made for seeds 0, 1, 2…;
    the first whose assignment meets the per-tier, per-split minimums is kept. Returns (seed, assignment)."""
    docs = sorted({i["source"]["document"] for i in items})
    forced = [d for d in docs if any(d.startswith(c + "-") for c in test_only)]
    free = [d for d in docs if d not in forced]
    for seed in seeds:
        rng = random.Random(seed)
        assignment = {d: "test" for d in forced}
        for d in free:
            assignment[d] = "dev" if rng.random() < dev_share else "test"
        if not split_problems(items, assignment, **targets):
            return seed, assignment
    return None, {}


def split_table(items: list[dict]) -> str:
    """Items and gold segments per tier and split, against the minimums of spec §9."""
    rows = ["| Tier | Dev items | Dev segments | Test items | Test segments | Minimum dev | Minimum test |",
            "| --- | --- | --- | --- | --- | --- | --- |"]
    for tier, *_ in TIERS:
        cell = {}
        for split in SPLITS:
            its = [i for i in items if i["tier"] == tier and i["split"] == split]
            cell[split] = (len(its), sum(len(i["segments"]) for i in its))
        if tier == "T0":
            mins = (f"{T0_TARGETS['dev']} items", f"{T0_TARGETS['test']} items")
        else:
            mins = (f"{TARGETS['dev']['items']} items",
                    f"{TARGETS['test']['items']} items, {TARGETS['test']['segments']} segments")
        rows.append(f"| {tier} | {cell['dev'][0]} | {cell['dev'][1]} | {cell['test'][0]} | {cell['test'][1]} | {mins[0]} | {mins[1]} |")
    return "\n".join(rows)


def agreement_sample(items: list[dict], share: float = 0.2, minimum: int = 5, seed: int = 0) -> list[str]:
    """The items a second annotator labels from plain text (spec §7, step 4): share of each tier, at
    least minimum (all of it, if the tier is smaller), drawn at random with a fixed seed."""
    rng = random.Random(seed)
    chosen = []
    for tier, *_ in TIERS:
        ids = sorted(i["item_id"] for i in items if i["tier"] == tier)
        k = min(len(ids), max(minimum, math.ceil(share * len(ids))))
        chosen += sorted(rng.sample(ids, k))
    return chosen
