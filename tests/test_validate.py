import json

import pytest

from named_actor_attribution import cli, items, markup, validate


def make(k=0, tier="T1", split="test", **changes):
    """A valid item of the tier: T0, or one direct quote padded by its tier's words."""
    text = "“The lab is ready,” said Anna Berg. Officials shrugged."
    a, o = text.index("The lab is ready"), text.index("Officials")
    d = {"type": markup.DISTRACTOR_TYPES[k % len(markup.DISTRACTOR_TYPES)], "spans": [[o, len(text)]], "note": None}
    level = {"T1": ("D1", "R1"), "T2": ("D2", "R1"), "T4": ("D3", "R1"), "T5": ("D4", "R1"), "T6": ("D1", "R5"), "T7": ("D5", "R1")}
    segs = [] if tier == "T0" else [{"segment_id": "G1", "speaker_id": "S1", "start": a, "end": a + 16, "text": "The lab is ready",
                                     "detection_level": level[tier][0], "reference_level": level[tier][1]}]
    return {"item_id": f"{tier}-{split}-{k}", "tier": tier, "split": split, "text": text, "word_count": len(text.split()),
            "source": {"document": f"c-{split}-{k}", "license": "CC BY 4.0", "attribution_line": "By X.", "adapted": False},
            "speakers": [] if tier == "T0" else [{"speaker_id": "S1", "canonical_name": "Anna Berg", "type": "person"}],
            "segments": segs, "distractors": [d],
            "annotation": {"reviewed_by": "M", "nested_checked": True}} | changes


def test_a_valid_item_has_no_problem():
    for tier in ("T0", "T1", "T2", "T4", "T5", "T6", "T7"):
        assert validate.check_item(make(tier=tier)) == []


def seg(item, **changes):
    item["segments"][0] |= changes
    return item


@pytest.mark.parametrize("item, message", [
    (seg(make(), end=10), "don't give its text"),
    (seg(make(), detection_level=None), "lacks a level"),
    (seg(make(), detection_level="D5"), "the tier computed"),
    (seg(make(), speaker_id="S9"), "no known speaker"),
    (make(speakers=[{"speaker_id": "S1", "canonical_name": "Lise Kanto", "type": "person"}]), "is not in the text"),
    (make(word_count=3), "word count"),
    (make(split=None), "no split"),
    (make(tier="T0", distractors=[]), "needs a distractor"),
    (make(annotation={"reviewed_by": None, "nested_checked": True}), "not reviewed"),
    (make(annotation={"reviewed_by": "M", "nested_checked": False}), "nested"),
    (make(source={"document": "c", "license": "CC BY 4.0", "attribution_line": None}), "no attribution_line"),
    (make(tier="T4", source={"document": "c", "license": "x", "attribution_line": "y", "adapted": True}), "adapted"),
    (make(distractors=[{"type": "author_voice", "spans": [[2, 8]], "note": None}]), "overlaps G1"),
])
def test_problems_of_an_item(item, message):
    assert any(message in p for p in validate.check_item(item)), validate.check_item(item)


def test_runs_to_merge_and_names_used_twice():
    item = make()
    g = item["segments"][0]
    item["segments"] = [g | {"end": g["start"] + 7, "text": "The lab"}, g | {"segment_id": "G2", "start": g["start"] + 8, "text": "is ready"}]
    assert any("one run" in p for p in validate.check_item(item))
    item = make()
    item["speakers"].append({"speaker_id": "S2", "canonical_name": "Dr Anna Berg", "type": "person"})
    assert any("two speakers" in p for p in validate.check_item(item))


def test_problems_of_a_dataset():
    its = [make(k) for k in range(8)]
    problems = validate.check_dataset(its, [its[0]["item_id"]])
    assert any(p.startswith("T5 test: 0 items") for p in problems)
    assert "no item of T0 in the agreement sample" in problems and "no item of T1 in the agreement sample" not in problems
    assert not any("scored against itself" in p or "some recall" in p or "distractor" in p for p in problems)
    its[0]["source"]["document"] = its[1]["source"]["document"] = "c-x"
    its[1]["split"] = "dev"
    assert "c-x is in several splits" in validate.check_dataset(its, [])
    its[2]["source"]["document"], its[2]["split"] = items.BLIND_TEST_ONLY[0] + "-1", "dev"
    assert any("for test only" in p for p in validate.check_dataset(its, []))
    assert any("used 2 times" in p for p in validate.check_dataset([its[3], its[3]], []))
    assert any("less than 30%" in p for p in validate.check_dataset([make(k, distractors=[]) for k in range(3)], []))
    assert any(p.startswith("T2: 0 of 1") for p in validate.check_dataset([seg(make(tier="T2"), detection_level="D1")], []))


def test_validate_command(tmp_path, capsys):
    path = tmp_path / "items.jsonl"
    path.write_text(json.dumps(make()) + "\n", encoding="utf-8")
    assert cli.main(["validate", str(path), "--agreement", str(tmp_path / "none.json")]) == 1
    out = capsys.readouterr().out
    assert "no agreement sample given" in out and "1 items" in out
