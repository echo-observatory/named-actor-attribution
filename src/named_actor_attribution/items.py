"""Cutting reviewed documents into dataset items, and computing their tiers (spec §4–§6).

A cut list names, for one document, the passages to keep: each by its first and last words,
with the item's levels where they differ from the document's (see docs/cutting.md).
"""

from __future__ import annotations

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
TARGETS = {"test": {"items": 8, "segments": 40}, "dev": {"items": 5, "segments": 20}}
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
    starts_para = any(p[0] == start for p in paras)
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

    item = {
        "item_id": item_id,
        "tier": tier,
        "tier_breaks": breaks,
        "split": None,
        "text": text,
        "word_count": words,
        "source": {**(source or {}), "document": doc.id, "start_offset": start, "adapted": False, "adaptation": None},
        "speakers": speakers,
        "segments": segments,
        "distractors": distractors,
        "annotation": {"drafted_by": doc.drafted_by, "miss_check_by": doc.miss_check_by,
                       "reviewed_by": doc.annotator, "second_annotator": None, "nested_checked": True, "notes": ""},
    }
    return item, problems


def _short(s: str, n: int = 50) -> str:
    s = " ".join(s.split())
    return repr(s if len(s) <= n else s[: n - 1] + "…")


def find_cut(doc: markup.Document, entry: dict) -> tuple[Cut | None, list[str]]:
    """A cut-list entry: {"from": first words, "to": last words, "n": …, "levels": {seg start words: [D, R]},
    "names": {document speaker id: name in this item}}."""
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
    cut = Cut(start, j + len(last), names=dict(entry.get("names", {})))
    problems = [f"names: no speaker {sid} in the document" for sid in cut.names if sid not in {s.id for s in doc.speakers}]
    for words, (d, r) in entry.get("levels", {}).items():
        seg = [s for s in doc.segments if cut.start <= s.start < cut.end and doc.text[s.start:s.end].startswith(words)]
        if len(seg) != 1:
            problems.append(f"levels: {len(seg)} segments of the passage start with {words!r}")
            continue
        cut.levels[seg[0].start] = (d, r)
    return cut, problems


def overlapping_cuts(cuts: list[Cut]) -> list[tuple[int, int]]:
    ordered = sorted(range(len(cuts)), key=lambda i: cuts[i].start)
    return [(a, b) for a, b in zip(ordered, ordered[1:]) if cuts[b].start < cuts[a].end]


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
