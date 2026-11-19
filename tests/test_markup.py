import json
from pathlib import Path

import pytest

from named_actor_attribution import cli, markup

FIXTURES = Path(__file__).parent / "fixtures"
LAB = FIXTURES / "invented-lab.xml"


def lab():
    return markup.parse(LAB.read_text(encoding="utf-8"))


def doc_with(text_markup: str, speakers: str = '<speaker id="S1" name="Anna Berg" type="person"/>',
             status: str = "drafted") -> markup.Document:
    """Parse a small document, with text-sha256 set to its text."""
    src = (f'<document id="t" status="{status}"><speakers>{speakers}</speakers>'
           f"<text>{text_markup}</text></document>")
    return markup.parse(markup.rehash(src))


def messages(doc, level=None):
    return [p.message for p in markup.check(doc) if level is None or p.level == level]


# --- Reading -----------------------------------------------------------------


def test_offsets_are_code_points_into_the_text_as_stored():
    doc = lab()
    seg = doc.segments
    assert [(s.start, s.end) for s in seg[:2]] == [(43, 65), (79, 103)]  # as in the spec's §6 example
    assert doc.text[seg[2].start:seg[2].end] == "the queue & the noise would be <manageable>"
    # The emoji (outside the BMP) and the combining accent each count as one code point,
    # and the text is not normalized.
    assert "🧀" in doc.text and "Pierré" in doc.text
    assert doc.text[seg[3].start:seg[3].end] == "Nobody wants to fund paperwork."


def test_whitespace_and_paragraphs_are_kept():
    doc = lab()
    assert "writes:\n\nNobody" in doc.text
    assert doc.text.startswith("Anna Berg") and doc.text.endswith("CC BY 2.0.")


def test_the_fixture_has_no_problems():
    assert markup.check(lab()) == []


@pytest.mark.parametrize("src, expected", [
    ("<document id='t'><text>a <b>x</b></text></document>", "only <seg>, <dis> and <exclude>"),
    ("<document id='t'><text><exclude reason='joint'>a <seg speaker='S1'>x</seg></exclude></text></document>", "cannot nest"),
    ("<document id='t'><text>a <seg speaker='S1'>x <dis type='author_voice'>y</dis></seg></text></document>", "cannot nest"),
    ("<document id='t'><speakers/></document>", "no <text>"),
    ("<document><text>a</text></document>", "no id"),
    ("<doc id='t'><text>a</text></doc>", "not <document>"),
    ("<document id='t'><text>a & b</text></document>", "not well-formed"),
    ("<document id='t'><text>a <seg speaker='S1' level='D1'>x</seg></text></document>", "unknown attribute"),
    ("<document id='t'><text>a</text><text>b</text></document>", "more than once"),
])
def test_structural_errors(src, expected):
    with pytest.raises(markup.MarkupError, match=expected):
        markup.parse(src)


# --- Checking ----------------------------------------------------------------


def test_a_change_to_the_text_is_detected():
    src = LAB.read_text(encoding="utf-8").replace("upbeat", "cheerful")
    assert any("text-sha256" in m for m in messages(markup.parse(src), "error"))
    assert messages(markup.parse(markup.rehash(src)), "error") == []


def test_unknown_speaker_and_bad_levels():
    doc = doc_with('Berg said <seg speaker="S9" d="D7" r="R1">it works</seg>.')
    errors = " | ".join(messages(doc, "error"))
    assert "not declared" in errors and "detection level 'D7'" in errors


def test_bad_types():
    doc = doc_with('<dis type="rumour">x</dis> <exclude reason="boring">y</exclude>',
                   speakers='<speaker id="S1" name="Anna Berg" type="blog"/>')
    errors = " | ".join(messages(doc, "error"))
    assert "type 'blog'" in errors and "type 'rumour'" in errors and "reason 'boring'" in errors


def test_duplicate_speakers():
    doc = doc_with("Anna Berg and anna  berg.", speakers=(
        '<speaker id="S1" name="Anna Berg" type="person"/><speaker id="S1" name="anna berg" type="person"/>'))
    errors = " | ".join(messages(doc, "error"))
    assert "used more than once" in errors and "several speakers have the name" in errors


def test_boundary_warnings():
    doc = doc_with('Anna Berg said: <seg speaker="S1">“It works.”</seg>')
    assert any("quotation mark" in m for m in messages(doc, "warning"))
    doc = doc_with('Anna Berg said <seg speaker="S1">it works “if the funding holds”</seg>.')
    assert not any("quotation mark" in m for m in messages(doc, "warning"))
    doc = doc_with('Anna Berg said <seg speaker="S1">“”</seg>.')
    assert any("empty once" in m for m in messages(doc, "error"))


def test_segments_that_should_be_merged():
    doc = doc_with('Anna Berg said <seg speaker="S1">it works</seg>, <seg speaker="S1">and it is cheap</seg>.')
    assert any("maximal run" in m for m in messages(doc, "warning"))
    doc = doc_with('Anna Berg said <seg speaker="S1">it works</seg> and added <seg speaker="S1">it is cheap</seg>.')
    assert not any("maximal run" in m for m in messages(doc))


def test_speaker_warnings():
    doc = doc_with("Nothing here.", speakers='<speaker id="S1" name="Anna Berg" type="person"/>')
    warnings = " | ".join(messages(doc, "warning"))
    assert "does not occur" in warnings and "has no segment" in warnings


def test_missing_levels_are_flagged_only_once_reviewed():
    text = 'Anna Berg said <seg speaker="S1">it works</seg>.'
    assert not any("level" in m for m in messages(doc_with(text, status="drafted")))
    assert any("has no D level" in m for m in messages(doc_with(text, status="reviewed")))


@pytest.mark.parametrize("name, text, expected", [
    ("Robert Smith", "Robert ‘Bob’ Smith said", True),
    ("Robert Smith", "Robert (Bob) Smith said", True),
    ("Robert Smith", "Robert Smith said", True),
    ("Robert Smith", "Robert J. Smith said", False),
    ("European Space Agency", "the European Space Agency said", True),
])
def test_name_occurs(name, text, expected):
    assert markup.name_occurs(name, text) is expected


def test_trim():
    assert markup.trim(" “It works.” ") == "It works"
    assert markup.trim("…") == ""


# --- Writing and round trips -------------------------------------------------


def test_serialize_round_trip():
    doc = lab()
    again = markup.parse(markup.serialize(doc))
    assert again == doc


def test_serialize_escapes_attributes():
    doc = lab()
    doc.segments[0].note = 'two lines\nand "quotes" & <tags>'
    assert markup.parse(markup.serialize(doc)).segments[0].note == doc.segments[0].note


def test_serialize_refuses_overlaps():
    doc = lab()
    doc.distractors[0].start = doc.segments[1].start
    with pytest.raises(ValueError, match="overlap"):
        markup.serialize(doc)


def test_rehash_changes_only_the_hash():
    src = LAB.read_text(encoding="utf-8")
    broken = src.replace(lab().text_sha256, "0" * 64)
    assert markup.rehash(broken) == src


def test_record():
    rec = markup.to_record(lab())
    assert rec["segments"][0] == {
        "segment_id": "G1", "speaker_id": "S1", "speaker": "Anna Berg", "start": 43, "end": 65,
        "text": "The equipment is ready", "detection_level": "D1", "reference_level": "R3", "note": None}
    assert rec["distractors"][0]["type"] == "unnamed_source"
    assert [x["reason"] for x in rec["exclusions"]] == ["joint", "boilerplate"]
    assert all(rec["text"][x["start"]:x["end"]] == x["text"] for x in rec["exclusions"])
    assert all(rec["text"][s["start"]:s["end"]] == s["text"] for s in rec["segments"])


# --- Command line ------------------------------------------------------------


def test_cli_new_check_export(tmp_path, capsys):
    text = "Anna Berg said it works. 🧀 & <done>\n\nThe end."
    corpus = tmp_path / "some-corpus" / "articles.jsonl"
    corpus.parent.mkdir()
    corpus.write_text(json.dumps({"id": "42", "text": text}) + "\n", encoding="utf-8")
    out = tmp_path / "annotations"

    assert cli.main(["new", str(corpus), "42", "--out", str(out)]) == 0
    path = out / "some-corpus-42.xml"
    doc = markup.parse(path.read_text(encoding="utf-8"))
    assert doc.text == text and doc.status == "blank" and doc.source_id == "42"

    assert cli.main(["check", str(path)]) == 0
    assert cli.main(["new", str(corpus), "43", "--out", str(out)]) == 1

    capsys.readouterr()
    assert cli.main(["export", str(LAB)]) == 0
    rec = json.loads(capsys.readouterr().out)
    assert rec["doc_id"] == "invented-lab" and len(rec["segments"]) == 4


def test_cli_check_fails_on_errors(tmp_path):
    bad = tmp_path / "bad.xml"
    bad.write_text("<document id='t'><text>a & b</text></document>", encoding="utf-8")
    assert cli.main(["check", str(bad)]) == 1


def test_apply_draft():
    doc = markup.blank("t", "Anna Berg said it works. “It works,” Berg said. The end.")
    draft = {"drafted_by": "model", "speakers": [["S1", "Anna Berg", "person"]], "spans": [
        ["seg", "S1", "it works", {"d": "D2", "r": "R1"}],
        ["seg", "S1", "It works", {"n": 1}],
        ["dis", "author_voice", "The", {"to": "end."}]]}
    out, problems = markup.apply_draft(doc, draft)
    assert problems == []
    assert [out.text[s.start:s.end] for s in out.segments] == ["it works", "It works"]
    assert out.text[out.distractors[0].start:out.distractors[0].end] == "The end."
    assert (out.status, out.drafted_by, doc.segments) == ("drafted", "model", [])
    _, problems = markup.apply_draft(doc, {"spans": [["seg", "S1", "missing"], ["seg", "S1", "works"]]})
    assert "not found" in problems[0] and "found 2 times" in problems[1]
