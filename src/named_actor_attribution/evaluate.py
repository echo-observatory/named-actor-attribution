"""Scoring a system's output against the gold (spec §8).

Predictions are one JSON object per item: {"item_id": …, "segments": [{"start", "end", "speaker"}]}.
The same scores, computed between two humans, give the agreement of each tier (spec §7, step 4).
"""

from __future__ import annotations

import random
import re
from collections import defaultdict
from dataclasses import dataclass, field

from . import markup

TIERS = tuple(f"T{k}" for k in range(8))
D_LEVELS = tuple(f"D{k}" for k in range(1, 6))
R_LEVELS = tuple(f"R{k}" for k in range(1, 7))
FOUND = 0.5  # a segment is found, or correct, from this share of its characters

# Titles, honorifics, roles and degrees that spec §2 strips from names. Longest first when matching.
LEADING = (
    "vice president", "prime minister", "deputy prime minister", "foreign minister", "foreign secretary",
    "secretary of state", "secretary general", "1st officer", "first officer", "supreme leader",
    "dr", "mr", "mrs", "ms", "miss", "mx", "prof", "professor", "sir", "dame", "lord", "lady", "rev", "reverend",
    "father", "sister", "brother", "bishop", "archbishop", "cardinal", "pope", "rabbi", "imam", "ayatollah", "sheikh",
    "president", "minister", "secretary", "senator", "sen", "representative", "rep", "congressman", "congresswoman",
    "councillor", "mayor", "governor", "gov", "chancellor", "ambassador", "judge", "justice", "director", "curator",
    "captain", "capt", "colonel", "col", "general", "gen", "major", "maj", "lieutenant", "lt", "sergeant", "sgt",
    "admiral", "commander", "king", "queen", "prince", "princess", "duke", "duchess",
)
TRAILING = ("phd", "ph.d", "md", "m.d", "dphil", "msc", "mba", "ma", "ba", "mp", "mep", "esq", "qc", "kc", "obe", "cbe", "mbe")


def normalize_speaker(name: str) -> str:
    """A speaker's name as compared (spec §8.1): lowercased, spaces collapsed, without a leading "the", titles or degrees."""
    s = " ".join(name.lower().split())
    while True:
        before = s
        s = re.sub(r"^the\s+", "", s)
        for title in sorted(LEADING, key=len, reverse=True):
            m = re.match(re.escape(title) + r"\.?\s+(?=\S)", s)
            if m:
                s = s[m.end():]
                break
        for degree in sorted(TRAILING, key=len, reverse=True):
            m = re.search(r"(?<=\S),?\s+" + re.escape(degree) + r"\.?$", s)
            if m:
                s = s[:m.start()]
                break
        if s == before:
            return s


@dataclass
class Span:
    start: int
    end: int
    speaker: str | None  # gold: the speaker's id; predicted: the id of the gold speaker it maps to, None if none
    d: str | None = None
    r: str | None = None

    @property
    def length(self) -> int:
        return self.end - self.start


def _trimmed(text: str, start: int, end: int) -> tuple[int, int] | None:
    """The range without leading and trailing whitespace and punctuation; None if nothing is left."""
    s = text[start:end]
    core = markup.trim(s)
    if not core:
        return None
    offset = 0
    while markup._is_trimmed(s[offset]):
        offset += 1
    return start + offset, start + offset + len(core)


def gold_spans(item: dict) -> list[Span]:
    out = []
    for s in item["segments"]:
        t = _trimmed(item["text"], s["start"], s["end"])
        if t:
            out.append(Span(*t, s["speaker_id"], s["detection_level"], s["reference_level"]))
    return out


def predicted_spans(item: dict, prediction: dict | None) -> tuple[list[Span], bool]:
    """The predicted segments, mapped to gold speakers; and whether the output is valid (spec §8.1, step 4)."""
    raw = (prediction or {}).get("segments", [])
    text = item["text"]
    ranges = []
    for s in raw:
        a, b = s.get("start"), s.get("end")
        if not isinstance(a, int) or not isinstance(b, int) or isinstance(a, bool) or isinstance(b, bool) \
                or not 0 <= a < b <= len(text) or not isinstance(s.get("speaker"), str):
            return [], False
        ranges.append((a, b))
    ranges.sort()
    if any(b1 > a2 for (_, b1), (a2, _) in zip(ranges, ranges[1:])):
        return [], False
    by_name = {normalize_speaker(s["canonical_name"]): s["speaker_id"] for s in item["speakers"]}
    out = []
    for s in raw:
        t = _trimmed(text, s["start"], s["end"])
        if t:
            out.append(Span(*t, by_name.get(normalize_speaker(s["speaker"]))))
    return out, True


def _overlap(a: Span, b: Span) -> int:
    return max(0, min(a.end, b.end) - max(a.start, b.start))


def _covered(span: Span, others: list[Span]) -> float:
    return sum(_overlap(span, o) for o in others) / span.length


@dataclass
class ItemScore:
    """One item's counts, pooled over a tier's items afterwards."""
    tier: str
    gold: list[Span] = field(default_factory=list)
    predicted: list[Span] = field(default_factory=list)
    found_joint: list[bool] = field(default_factory=list)      # per gold segment
    found: list[bool] = field(default_factory=list)
    correct_joint: list[bool] = field(default_factory=list)    # per predicted segment
    correct: list[bool] = field(default_factory=list)
    # per gold segment: characters also predicted, and those with the right speaker
    common: list[int] = field(default_factory=list)
    agreed: list[int] = field(default_factory=list)
    distractors: list[tuple[str, bool]] = field(default_factory=list)  # (type, hit)
    valid: bool = True


def score_item(item: dict, prediction: dict | None) -> ItemScore:
    gold, (pred, valid) = gold_spans(item), predicted_spans(item, prediction)
    s = ItemScore(item["tier"], gold, pred, valid=valid)
    for g in gold:
        same = [p for p in pred if p.speaker is not None and p.speaker == g.speaker]
        s.found_joint.append(_covered(g, same) >= FOUND)
        s.found.append(_covered(g, pred) >= FOUND)
        s.common.append(sum(_overlap(g, p) for p in pred))
        s.agreed.append(sum(_overlap(g, p) for p in same))
    for p in pred:
        s.correct_joint.append(p.speaker is not None and _covered(p, [g for g in gold if g.speaker == p.speaker]) >= FOUND)
        s.correct.append(_covered(p, gold) >= FOUND)
    for x in item["distractors"]:
        spans = [Span(a, b, None) for a, b in x["spans"]]
        hit = sum(_covered(y, pred) * y.length for y in spans) / sum(y.length for y in spans)
        s.distractors.append((x["type"], hit >= FOUND))
    return s


def _ratio(n: float, d: float) -> float | None:
    return n / d if d else None


def _f1(p: float | None, r: float | None) -> float | None:
    if p is None or r is None:
        return None
    return 2 * p * r / (p + r) if p + r else 0.0


def pool(scores: list[ItemScore]) -> dict:
    """The metrics of spec §8.2, over these items."""
    gold, pred = sum(len(s.gold) for s in scores), sum(len(s.predicted) for s in scores)
    out = {"items": len(scores), "gold_segments": gold, "predicted_segments": pred}
    for name, found, correct in (("joint", "found_joint", "correct_joint"), ("detection", "found", "correct")):
        r = _ratio(sum(sum(getattr(s, found)) for s in scores), gold)
        p = _ratio(sum(sum(getattr(s, correct)) for s in scores), pred)
        out |= {f"{name}_precision": p, f"{name}_recall": r, f"{name}_f1": _f1(p, r) if gold else None}
    out["speaker_accuracy"] = _ratio(sum(sum(s.agreed) for s in scores), sum(sum(s.common) for s in scores))
    t0 = [s for s in scores if s.tier == "T0"]
    out["t0_false_positives_per_item"] = _ratio(sum(len(s.predicted) for s in t0), len(t0))
    out["t0_clean_share"] = _ratio(sum(not s.predicted for s in t0), len(t0))
    out["invalid_rate"] = _ratio(sum(not s.valid for s in scores), len(scores))
    return out


def bootstrap(scores: list[ItemScore], metric: str, n: int = 1000, seed: int = 0) -> tuple[float, float] | None:
    """The 95% interval of a metric, by resampling items (spec §9)."""
    rng = random.Random(seed)
    values = sorted(v for v in (pool(rng.choices(scores, k=len(scores)))[metric] for _ in range(n)) if v is not None)
    return (values[int(0.025 * len(values))], values[min(len(values) - 1, int(0.975 * len(values)))]) if values else None


def score(items: list[dict], predictions: dict[str, dict]) -> list[ItemScore]:
    """Score each item; a missing prediction is an empty one."""
    return [score_item(i, predictions.get(i["item_id"])) for i in items]


def by_tier(scores: list[ItemScore]) -> dict[str, dict]:
    return {t: pool(its) for t in TIERS if (its := [s for s in scores if s.tier == t])}


def slices(scores: list[ItemScore]) -> list[dict]:
    """Segment recall and speaker accuracy by detection and by reference level, across all tiers."""
    out = []
    for attr, levels in (("d", D_LEVELS), ("r", R_LEVELS)):
        for level in levels:
            n = found_joint = found = common = agreed = 0
            for s in scores:
                for k, g in enumerate(s.gold):
                    if getattr(g, attr) == level:
                        n += 1
                        found_joint += s.found_joint[k]
                        found += s.found[k]
                        common += s.common[k]
                        agreed += s.agreed[k]
            out.append({"level": level, "gold_segments": n, "joint_recall": _ratio(found_joint, n),
                        "detection_recall": _ratio(found, n), "speaker_accuracy": _ratio(agreed, common)})
    return out


def distractor_hits(scores: list[ItemScore]) -> dict[str, tuple[int, int]]:
    """Distractors hit, and their number, by type."""
    out: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for s in scores:
        for kind, hit in s.distractors:
            out[kind][0] += hit
            out[kind][1] += 1
    return {k: (v[0], v[1]) for k, v in sorted(out.items())}


def document_prediction(doc: markup.Document) -> dict:
    """A document's annotation as a prediction, to score one annotator against another."""
    names = {s.id: s.name for s in doc.speakers}
    return {"item_id": doc.id,
            "segments": [{"start": s.start, "end": s.end, "speaker": names.get(s.speaker, "")} for s in doc.segments]}
