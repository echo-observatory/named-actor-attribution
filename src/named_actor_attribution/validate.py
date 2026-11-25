"""The acceptance checks of spec §10, on the items of a dataset."""

from __future__ import annotations

from collections import Counter

from . import evaluate as ev
from . import items as items_mod
from . import markup

DISTRACTOR_SHARE = 0.3  # spec §5.3: of T1–T7 items with at least one distractor


def check_item(item: dict) -> list[str]:
    """The checks of one item by itself."""
    out = []
    text, segs = item["text"], sorted(item["segments"], key=lambda s: s["start"])
    ids = {s["speaker_id"] for s in item["speakers"]}
    for s in segs:
        if text[s["start"]:s["end"]] != s["text"]:
            out.append(f"the offsets of {s['segment_id']} don't give its text")
        if not markup.trim(s["text"]):
            out.append(f"{s['segment_id']} is empty once trimmed")
        if s["speaker_id"] not in ids:
            out.append(f"{s['segment_id']} has no known speaker")
        if s["detection_level"] not in ev.D_LEVELS or s["reference_level"] not in ev.R_LEVELS:
            out.append(f"{s['segment_id']} lacks a level")
    for a, b in zip(segs, segs[1:]):
        gap = text[a["end"]:b["start"]]
        if b["start"] < a["end"]:
            out.append(f"{a['segment_id']} and {b['segment_id']} overlap")
        elif a["speaker_id"] == b["speaker_id"] and not markup.trim(gap) and "\n" not in gap:
            out.append(f"{a['segment_id']} and {b['segment_id']} are one run: merge them")
    names = Counter()
    for s in item["speakers"]:
        names[ev.normalize_speaker(s["canonical_name"])] += 1
        if not markup.name_occurs(s["canonical_name"], text):
            out.append(f"the name {s['canonical_name']!r} is not in the text")
        if not any(g["speaker_id"] == s["speaker_id"] for g in segs):
            out.append(f"the speaker {s['canonical_name']!r} has no segment")
    out += [f"two speakers are named {n!r}" for n, k in names.items() if k > 1]
    for d in item["distractors"]:
        if any(not 0 <= a < b <= len(text) for a, b in d["spans"]):
            out.append("a distractor lies outside the text")
        elif any(a < g["end"] and g["start"] < b for a, b in d["spans"] for g in segs):
            out.append(f"a distractor overlaps {next(g['segment_id'] for a, b in d['spans'] for g in segs if a < g['end'] and g['start'] < b)}")
    if item["word_count"] != items_mod.word_count(text):
        out.append(f"the word count is {items_mod.word_count(text)}, not {item['word_count']}")
    tier, breaks = items_mod.compute_tier(item["segments"], len(item["speakers"]), items_mod.word_count(text))
    if tier != item["tier"]:
        out.append(f"the tier computed from the levels is {tier}, not {item['tier']}")
    if item["tier"] == "T0" and not item["distractors"]:
        out.append("a T0 item needs a distractor")
    if item["source"].get("adapted") and item["tier"] not in ("T0", "T1", "T2", "T3"):
        out.append(f"an adapted item is {item['tier']}")
    if item["annotation"].get("nested_checked") is not True:
        out.append("not checked for nested and joint attributions")
    for key in ("license", "attribution_line"):
        if not item["source"].get(key):
            out.append(f"no {key}")
    if not item["annotation"].get("reviewed_by"):
        out.append("not reviewed")
    if item.get("split") not in items_mod.SPLITS:
        out.append("no split")
    return out


def check_dataset(items: list[dict], agreement_ids: list[str] | None = None) -> list[str]:
    """The checks on the items together; agreement_ids are those of the agreement sample."""
    out = [f"the id {k} is used {n} times" for k, n in Counter(i["item_id"] for i in items).items() if n > 1]
    for tier, columns in items_mod.MAIN_DIFFICULTY.items():
        its = [i for i in items if i["tier"] == tier]
        on_main = sum(bool(set(items_mod.compute_tier(i["segments"], len(i["speakers"]), i["word_count"])[1]) & set(columns)) for i in its)
        if 2 * on_main < len(its):
            out.append(f"{tier}: {on_main} of {len(its)} items break the tier below on its main difficulty, less than half")
    splits: dict[str, set] = {}
    for i in items:
        splits.setdefault(i["source"]["document"], set()).add(i.get("split"))
    out += [f"{d} is in several splits" for d, s in sorted(splits.items()) if len(s) > 1]
    out += [f"{d} belongs to a corpus for test only" for d, s in sorted(splits.items())
            if s != {"test"} and any(d.startswith(c + "-") for c in items_mod.BLIND_TEST_ONLY)]
    out += items_mod.split_problems(items, {i["source"]["document"]: i.get("split") for i in items})
    upper = [i for i in items if i["tier"] != "T0"]
    share = sum(bool(i["distractors"]) for i in upper) / len(upper) if upper else 0
    if share < DISTRACTOR_SHARE:
        out.append(f"{share:.0%} of the T1–T7 items have a distractor, less than {DISTRACTOR_SHARE:.0%}")
    types = {d["type"] for i in items for d in i["distractors"]}
    out += [f"no distractor of type {t}" for t in markup.DISTRACTOR_TYPES if t not in types]
    if agreement_ids is None:
        out.append("no agreement sample given")
    else:
        known = {i["item_id"]: i["tier"] for i in items}
        sampled = Counter(known[k] for k in agreement_ids if k in known)
        out += [f"no item of {t} in the agreement sample" for t in ev.TIERS if not sampled[t]]
    gold = {i["item_id"]: {"segments": [
        {"start": s["start"], "end": s["end"],
         "speaker": next((p["canonical_name"] for p in i["speakers"] if p["speaker_id"] == s["speaker_id"]), "")}
        for s in i["segments"]]} for i in items}
    own, empty = ev.pool(ev.score(items, gold)), ev.pool(ev.score(items, {}))
    out += [f"the gold scored against itself has {k} {own[k]}, not 1" for k in
            ("joint_precision", "joint_recall", "joint_f1", "detection_precision", "detection_recall", "detection_f1", "speaker_accuracy")
            if own[k] != 1]
    if own["invalid_rate"]:
        out.append("the gold is an invalid output for some items")
    if empty["joint_recall"] != 0 or empty["detection_recall"] != 0:
        out.append("an empty prediction has some recall")
    return out
