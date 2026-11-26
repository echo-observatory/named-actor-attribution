import csv
import json

import pytest

from named_actor_attribution import cli, markup
from named_actor_attribution import evaluate as ev

TEXT = "Anna Berg said “the lab is ready”. Tomas Holm fears the funding will be cut. Officials shrugged."


def seg(words, speaker, d="D1", r="R1"):
    a = TEXT.index(words)
    return {"segment_id": "G", "speaker_id": speaker, "start": a, "end": a + len(words), "text": words,
            "detection_level": d, "reference_level": r}


def item(tier="T3"):
    a = TEXT.index("Officials")
    return {"item_id": "x", "tier": tier, "text": TEXT,
            "speakers": [{"speaker_id": "S1", "canonical_name": "Anna Berg", "type": "person"},
                         {"speaker_id": "S2", "canonical_name": "Tomas Holm", "type": "person"}],
            "segments": [seg("the lab is ready", "S1"), seg("the funding will be cut", "S2", "D4")],
            "distractors": [{"type": "unnamed_source", "spans": [[a, len(TEXT)]], "note": None}]}


def pred(*segments):
    return {"item_id": "x", "segments": [{"start": TEXT.index(w), "end": TEXT.index(w) + len(w), "speaker": sp} for w, sp in segments]}


GOLD = pred(("the lab is ready", "Anna Berg"), ("the funding will be cut", "Tomas Holm"))


def test_gold_against_itself_and_an_empty_prediction():
    m = ev.pool([ev.score_item(item(), GOLD)])
    for k in ("joint_precision", "joint_recall", "joint_f1", "detection_f1", "speaker_accuracy"):
        assert m[k] == 1.0
    m = ev.pool([ev.score_item(item(), None)])
    assert m["joint_recall"] == 0 and m["joint_precision"] is None and m["speaker_accuracy"] is None and m["joint_f1"] is None


def test_wrong_speaker_is_detected_but_not_joint():
    m = ev.pool([ev.score_item(item(), pred(("the lab is ready", "Tomas Holm"), ("the funding will be cut", "Tomas Holm")))])
    assert (m["detection_f1"], m["joint_recall"], m["joint_precision"]) == (1.0, 0.5, 0.5)
    assert m["speaker_accuracy"] == pytest.approx(23 / 39)  # by characters


def test_a_short_form_or_an_unknown_name_is_wrong():
    for name in ("Berg", "she", "the director", "Anna K. Berg", ""):
        assert ev.pool([ev.score_item(item(), pred(("the lab is ready", name)))])["joint_precision"] == 0


@pytest.mark.parametrize("name", ["anna  berg", "Dr. Anna Berg", "Professor Anna Berg", "Anna Berg, PhD", "the Anna Berg", "Prof. Dr Anna Berg"])
def test_titles_and_case_dont_matter(name):
    assert ev.pool([ev.score_item(item(), pred(("the lab is ready", name)))])["joint_precision"] == 1.0


@pytest.mark.parametrize("name, gold", [
    ("Doctor Susanne Sorensen", "Susanne Sorensen"),        # the spelled-out form of Dr
    ("Psychologist Zarko Trebjesanin", "Zarko Trebjesanin"),
    ("Environmentalist Mark Lynas", "Mark Lynas"),
    ("Senate Majority Leader Harry Reid", "Harry Reid"),
    ("Expedition Leader Shane Rattenbury", "Shane Rattenbury"),
    ("Co-founder Larry Page", "Larry Page"),
])
def test_roles_found_in_the_items_are_stripped(name, gold):
    assert ev.normalize_speaker(name) == ev.normalize_speaker(gold)


def test_affiliations_are_not_stripped():
    # Not titles but part of what the text says of the actor: naming the actor so is wrong (spec §2).
    assert ev.normalize_speaker("Google Co-founder Larry Page") != ev.normalize_speaker("Larry Page")
    assert ev.normalize_speaker("Lyndon of Scraps of Moscow") != ev.normalize_speaker("Lyndon")


def test_normalizing_keeps_the_last_word_and_suffixes():
    assert ev.normalize_speaker("General") == "general"
    assert ev.normalize_speaker("Robert Smith Jr.") == "robert smith jr."
    assert ev.normalize_speaker("The Sunday Times") == "sunday times"


def test_half_of_the_characters_decides():
    a = TEXT.index("the lab is ready")  # 16 characters
    part = lambda n: {"item_id": "x", "segments": [{"start": a, "end": a + n, "speaker": "Anna Berg"}]}
    m = ev.pool([ev.score_item(item(), part(9))])
    assert m["joint_recall"] == 0.5 and m["joint_precision"] == 1.0
    assert ev.pool([ev.score_item(item(), part(7))])["joint_recall"] == 0


def test_a_segment_split_in_two_counts_each_part():
    m = ev.pool([ev.score_item(item(), pred(("the lab", "Anna Berg"), ("is ready", "Anna Berg")))])
    assert m["predicted_segments"] == 2 and m["joint_precision"] == 1.0 and m["joint_recall"] == 0.5


def test_edges_are_trimmed_and_empty_segments_dropped():
    m = ev.pool([ev.score_item(item(), pred(("“the lab is ready”. ", "Anna Berg"), ("the funding will be cut.", "Tomas Holm")))])
    assert m["joint_f1"] == 1.0
    a = TEXT.index("”. ")
    only_marks = {"item_id": "x", "segments": [{"start": a, "end": a + 3, "speaker": "Anna Berg"}]}
    assert ev.score_item(item(), only_marks).predicted == []


def test_invalid_output_is_an_empty_prediction():
    over = {"item_id": "x", "segments": [{"start": 0, "end": 10, "speaker": "a"}, {"start": 5, "end": 12, "speaker": "a"}]}
    out = {"item_id": "x", "segments": [{"start": 0, "end": len(TEXT) + 1, "speaker": "a"}]}
    for bad in (over, out, {"item_id": "x", "segments": [{"start": 5, "end": 5, "speaker": "a"}]}):
        s = ev.score_item(item(), bad)
        assert not s.valid and s.predicted == [] and ev.pool([s])["invalid_rate"] == 1.0
    touching = pred(("the lab", "Anna Berg"))
    touching["segments"].append({"start": touching["segments"][0]["end"], "end": touching["segments"][0]["end"] + 3, "speaker": "Anna Berg"})
    assert ev.score_item(item(), touching).valid


def test_distractors_t0_and_slices():
    it = item("T0") | {"segments": [], "speakers": []}
    s = ev.score_item(it, pred(("Officials shrugged.", "Officials")))
    assert ev.distractor_hits([s]) == {"unnamed_source": (1, 1)}
    m = ev.pool([s, ev.score_item(it, None)])
    assert m["t0_false_positives_per_item"] == 0.5 and m["t0_clean_share"] == 0.5
    rows = {r["level"]: r for r in ev.slices([ev.score_item(item(), pred(("the lab is ready", "Anna Berg")))])}
    assert rows["D1"]["joint_recall"] == 1.0 and rows["D4"]["joint_recall"] == 0 and rows["D2"]["joint_recall"] is None


def test_bootstrap_interval_is_reproducible():
    scores = [ev.score_item(item(), GOLD), ev.score_item(item(), None)] * 10
    lo, hi = ev.bootstrap(scores, "joint_recall", n=200)
    assert (lo, hi) == ev.bootstrap(scores, "joint_recall", n=200) and 0 < lo < 0.5 < hi < 1


def test_evaluate_command(tmp_path, capsys):
    items, preds, out = tmp_path / "items.jsonl", tmp_path / "p.jsonl", tmp_path / "m.csv"
    items.write_text(json.dumps(item() | {"split": "test"}) + "\n", encoding="utf-8")
    preds.write_text(json.dumps(GOLD) + "\n", encoding="utf-8")
    assert cli.main(["evaluate", str(items), str(preds), "--out", str(out)]) == 0
    [row] = list(csv.DictReader(out.open(encoding="utf-8")))
    assert row["tier"] == "T3" and float(row["joint_f1"]) == 1.0
    assert cli.main(["evaluate", str(items), str(preds), "--split", "dev"]) == 0
    preds.write_text(json.dumps(GOLD | {"item_id": "other"}) + "\n", encoding="utf-8")
    assert cli.main(["evaluate", str(items), str(preds)]) == 1
    # A second annotator's file, in the markup of the annotation page
    doc = markup.blank("x", TEXT)
    doc.speakers = [markup.Speaker("S1", "Anna Berg", "person")]
    a = TEXT.index("the lab is ready")
    doc.segments = [markup.Segment("S1", a, a + 16)]
    saved, only = tmp_path / "second.xml", tmp_path / "agreement.json"
    saved.write_text("<documents>\n" + markup.serialize(doc) + "</documents>\n", encoding="utf-8")
    only.write_text(json.dumps({"items": ["x"]}), encoding="utf-8")
    assert cli.main(["evaluate", str(items), str(saved), "--only", str(only), "--out", str(out)]) == 0
    [row] = list(csv.DictReader(out.open(encoding="utf-8")))
    assert float(row["joint_recall"]) == 0.5 and float(row["joint_precision"]) == 1.0
    # ... refused if the item's text has changed since
    items.write_text(json.dumps(item() | {"split": "test", "text": TEXT + " More."}) + "\n", encoding="utf-8")
    capsys.readouterr()
    assert cli.main(["evaluate", str(items), str(saved)]) == 1 and "cut again" in capsys.readouterr().out
