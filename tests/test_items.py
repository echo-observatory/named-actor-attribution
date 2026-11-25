import json
from pathlib import Path

import pytest

from named_actor_attribution import cli, items, markup

FIXTURES = Path(__file__).parent / "fixtures"
LAB = FIXTURES / "invented-lab.xml"


def lab():
    return markup.parse(LAB.read_text(encoding="utf-8"))


def seg(d, r):
    return {"detection_level": d, "reference_level": r}


@pytest.mark.parametrize("segments, speakers, words, tier, breaks", [
    ([], 0, 50, "T0", []),
    ([seg("D1", "R1")], 1, 40, "T1", []),
    ([seg("D1", "R1")], 1, 70, "T2", ["words"]),
    ([seg("D2", "R1")], 1, 40, "T2", ["D"]),
    ([seg("D1", "R1"), seg("D2", "R2")], 2, 100, "T3", ["speakers", "words"]),
    ([seg("D3", "R1")], 1, 40, "T4", ["D"]),
    ([seg("D4", "R4")], 4, 300, "T5", ["D", "R", "speakers", "words"]),
    ([seg("D2", "R5")], 1, 40, "T6", ["R"]),
    ([seg("D5", "R1")], 1, 40, "T7", ["D"]),
])
def test_tiers(segments, speakers, words, tier, breaks):
    assert items.compute_tier(segments, speakers, words) == (tier, breaks)


def test_no_tier():
    assert items.compute_tier([seg("D1", "R1")], 1, 700)[0] is None
    assert items.compute_tier([seg(None, "R1")], 1, 40)[0] is None


def test_paragraphs():
    text = "One.\n\nTwo two.\n\n\nThree"
    assert [text[a:b] for a, b in items.paragraphs(text)] == ["One.", "Two two.", "Three"]


def cut(doc, first, last, **kw):
    c, problems = items.find_cut(doc, {"from": first, "to": last, **kw})
    assert problems == []
    return c


def test_an_item_with_offsets_relative_to_the_passage():
    doc = lab()
    item, problems = items.make_item(doc, cut(doc, "Anna Berg, who leads", "the permits.”"), "x-01")
    assert problems == []
    assert item["text"].startswith("Anna Berg") and item["text"].endswith("permits.”")
    assert [(s["start"], s["end"], s["text"]) for s in item["segments"]] == [
        (43, 65, "The equipment is ready"), (79, 103, "We only need the permits")]
    assert item["speakers"] == [{"speaker_id": "S1", "canonical_name": "Anna Berg", "type": "person"}]
    assert (item["tier"], item["tier_breaks"]) == ("T4", ["D", "R"])
    assert item["source"]["start_offset"] == 0 and item["source"]["document"] == "invented-lab"


def test_problems_of_a_cut():
    doc = lab()
    # An exclusion inside, and a whole-paragraph item from T3 up
    _, problems = items.make_item(doc, cut(doc, "The lab will reopen", "fund paperwork."), "x")
    assert any("exclusion (joint)" in p for p in problems)
    # A segment cut in two, and not starting at a sentence
    _, problems = items.make_item(doc, cut(doc, "equipment is ready", "permits.”"), "x")
    assert any("cuts a segment" in p for p in problems) and any("doesn't start at a sentence" in p for p in problems)
    # A speaker whose name is not in the passage
    _, problems = items.make_item(doc, cut(doc, "Nobody wants", "paperwork."), "x")
    assert any("'Barbados Free Press' is not in the passage" in p for p in problems)


def test_names_and_levels_set_for_one_item():
    doc = lab()
    c = cut(doc, "Robert ‘Bob’ Smith", "<manageable>.", names={"S2": "Smith"}, levels={"the queue": ["D2", "R2"]})
    item, problems = items.make_item(doc, c, "x")
    assert problems == []
    assert item["speakers"][0]["canonical_name"] == "Smith"
    assert (item["segments"][0]["detection_level"], item["segments"][0]["reference_level"]) == ("D2", "R2")
    _, problems = items.find_cut(doc, {"from": "Robert", "to": ".", "levels": {"nothing": ["D1", "R1"]}})
    assert "levels" in problems[0]


def test_t0_needs_a_distractor():
    doc = lab()
    item, problems = items.make_item(doc, cut(doc, "The lab will reopen", "officials said."), "x")
    assert item["tier"] == "T0" and problems == []
    doc.distractors = []
    _, problems = items.make_item(doc, cut(doc, "The lab will reopen", "officials said."), "x")
    assert any("needs at least one distractor" in p for p in problems)


def test_cut_command(tmp_path, capsys):
    docs = tmp_path / "annotations"
    docs.mkdir()
    (docs / "invented-lab.xml").write_text(LAB.read_text(encoding="utf-8"), encoding="utf-8")
    cuts = tmp_path / "cuts.json"
    cuts.write_text(json.dumps({"document": "invented-lab", "items": [
        {"from": "Anna Berg, who leads", "to": "the permits.”", "note": "two segments"},
        {"from": "The lab will reopen", "to": "officials said."}]}), encoding="utf-8")
    out, page = tmp_path / "items.jsonl", tmp_path / "page.html"
    assert cli.main(["cut", str(cuts), "--documents", str(docs), "--out", str(out), "--page", str(page)]) == 0
    got = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert [i["item_id"] for i in got] == ["invented-lab-01", "invented-lab-02"]
    assert got[0]["annotation"]["notes"] == "two segments"
    assert "| T4 | 1 | 2 |" in capsys.readouterr().out
    assert "invented-lab-02" in page.read_text(encoding="utf-8")
    # Overlapping items are refused
    cuts.write_text(json.dumps({"document": "invented-lab", "items": [
        {"from": "Anna Berg, who leads", "to": "the permits.”"}, {"from": "“We only", "to": "permits.”"}]}),
        encoding="utf-8")
    assert cli.main(["cut", str(cuts), "--documents", str(docs)]) == 1


def test_adapted_documents(tmp_path, capsys):
    docs = tmp_path / "annotations"
    docs.mkdir()
    (docs / "invented-lab.xml").write_text(LAB.read_text(encoding="utf-8"), encoding="utf-8")
    draft = tmp_path / "adapt.json"
    draft.write_text(json.dumps({
        "document": "invented-lab", "id": "a1", "from": "The blog Barbados Free Press writes:", "to": "fund paperwork.",
        "text": "“Nobody wants to fund paperwork,” the blog Barbados Free Press writes.",
        "adaptation": "Lead-in and block quote rewritten as an inline quote.",
        "speakers": [["S1", "Barbados Free Press", "organization"]],
        "spans": [["seg", "S1", "Nobody wants to fund paperwork", {"d": "D1", "r": "R1"}]]}), encoding="utf-8")
    assert cli.main(["adapt", str(draft), "--documents", str(docs)]) == 0
    doc = markup.parse((docs / "invented-lab-a1.xml").read_text(encoding="utf-8"))
    lab_doc = lab()
    assert doc.adapted_from == "invented-lab" and doc.adaptation.startswith("Lead-in")
    assert lab_doc.text[doc.source_start:doc.source_end].startswith("The blog Barbados Free Press writes:")
    assert markup.check(doc) == [] and markup.parse(markup.serialize(doc)) == doc
    assert cli.main(["adapt", str(draft), "--documents", str(docs)]) == 1  # exists

    cuts = tmp_path / "cuts.json"
    cuts.write_text(json.dumps({"document": "invented-lab-a1", "items": [{}]}), encoding="utf-8")
    out = tmp_path / "items.jsonl"
    assert cli.main(["cut", str(cuts), "--documents", str(docs), "--out", str(out)]) == 0
    item = json.loads(out.read_text(encoding="utf-8"))
    assert item["tier"] == "T1"
    assert item["source"]["adapted"] is True and item["source"]["document"] == "invented-lab"
    assert item["source"]["start_offset"] == doc.source_start

    # The same source text can't also be an item as it is
    source_cuts = tmp_path / "source.json"
    source_cuts.write_text(json.dumps({"document": "invented-lab", "items": [
        {"from": "The blog Barbados Free Press writes:", "to": "fund paperwork."}]}), encoding="utf-8")
    capsys.readouterr()
    assert cli.main(["cut", str(cuts), str(source_cuts), "--documents", str(docs)]) == 1
    assert "overlapping text" in capsys.readouterr().out


def test_adapted_items_stay_in_low_tiers():
    doc = markup.adapted(lab(), 0, 10, "Anna Berg said “it works.” She added “it is cheap.”", "invented", "a9")
    doc.speakers = [markup.Speaker("S1", "Anna Berg", "person")]
    t = doc.text
    doc.segments = [markup.Segment("S1", t.index("it works"), t.index("it works") + 8, "D1", "R1"),
                    markup.Segment("S1", t.index("it is cheap"), t.index("it is cheap") + 11, "D1", "R3")]
    item, problems = items.make_item(doc, items.Cut(0, len(doc.text)), "x")
    assert item["tier"] == "T4" and any("only T0–T3 items may be adapted" in p for p in problems)


def test_an_adapted_document_needs_its_source_range():
    doc = markup.adapted(lab(), 0, 10, "Some text.", "invented", "a9")
    doc.source_end = None
    assert any("needs source-start" in p.message for p in markup.check(doc))


def test_review_items_and_put_corrections_back(tmp_path, capsys):
    docs, cuts = tmp_path / "annotations", tmp_path / "cuts"
    docs.mkdir()
    cuts.mkdir()
    lab_doc = lab()
    lab_doc.status, lab_doc.annotator = "drafted", None  # reviewed as items only
    (docs / "invented-lab.xml").write_text(markup.serialize(lab_doc), encoding="utf-8")
    (cuts / "invented-lab.json").write_text(json.dumps({"document": "invented-lab", "items": [
        {"from": "Anna Berg, who leads", "to": "the permits.”"}]}), encoding="utf-8")
    out = tmp_path / "items.jsonl"

    def cut_items():
        assert cli.main(["cut", str(cuts / "invented-lab.json"), "--documents", str(docs), "--out", str(out)]) == 0
        return [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]

    def review(item_doc):
        saved = tmp_path / "saved.xml"
        saved.write_text(markup.serialize(item_doc), encoding="utf-8")
        capsys.readouterr()
        assert cli.main(["review", str(saved), "--documents", str(docs), "--cuts", str(cuts)]) == 0
        return capsys.readouterr().out

    [item] = cut_items()
    assert item["annotation"]["reviewed_by"] is None
    item_doc = cli._item_document(item)
    assert item_doc.status == "drafted"

    # Reviewed as it is: the document doesn't change, the cut list records the review
    item_doc.status, item_doc.annotator = "reviewed", "Tester"
    before = (docs / "invented-lab.xml").read_text(encoding="utf-8")
    assert "no change" in review(item_doc)
    assert (docs / "invented-lab.xml").read_text(encoding="utf-8") == before
    [item] = cut_items()
    assert item["annotation"]["reviewed_by"] == "Tester"

    # Corrected: the second segment removed, a distractor added; the first keeps its levels
    second = item_doc.segments.pop()
    item_doc.distractors.append(markup.Distractor("non_statement", second.start, second.end))
    printed = review(item_doc)
    assert "segment removed or changed" in printed and "distractors changed" in printed
    doc = markup.parse((docs / "invented-lab.xml").read_text(encoding="utf-8"))
    passage = [s for s in doc.segments if doc.text[s.start:s.end] in item["text"]]
    assert [doc.text[s.start:s.end] for s in passage] == ["The equipment is ready"]
    assert (passage[0].d, passage[0].r) == (lab_doc.segments[0].d, lab_doc.segments[0].r)
    [item] = cut_items()
    assert item["annotation"]["reviewed_by"] == "Tester" and len(item["segments"]) == 1

    # A later change to the document makes the review stale
    doc.distractors = [x for x in doc.distractors if doc.text[x.start:x.end] != "We only need the permits"]
    (docs / "invented-lab.xml").write_text(markup.serialize(doc), encoding="utf-8")
    capsys.readouterr()
    [item] = cut_items()
    assert item["annotation"]["reviewed_by"] is None
    assert "to review again: invented-lab-01" in capsys.readouterr().out


def test_source_details_credit_wikinews(tmp_path):
    corpus = tmp_path / "wikinews-test" / "articles.jsonl"
    corpus.parent.mkdir()
    corpus.write_text(json.dumps({"id": 7, "title": "A title", "date": "2008-01-02", "license": "CC BY 2.5",
                                  "url": "https://en.wikinews.org/wiki/A_title", "text": "x"}) + "\n", encoding="utf-8")
    line = cli._source_details([corpus])[("wikinews-test", "7")]["attribution_line"]
    assert line == ("“A title”, by Wikinews contributors (2008-01-02), licensed under CC BY 2.5: "
                    "https://en.wikinews.org/wiki/A_title. Converted to plain text.")


def test_an_item_may_start_after_an_excluded_heading_line():
    text = "Intro sentence.\n\nFunding woes\nAnna Berg said that the lab needs money.\n\nEnd."
    doc = markup.blank("heading", text)
    doc.speakers.append(markup.Speaker("S1", "Anna Berg", "person"))
    a = text.index("the lab"); doc.segments.append(markup.Segment("S1", a, a + len("the lab needs money"), "D2", "R1"))
    cut = items.Cut(text.index("Anna Berg"), text.index("money.") + len("money."))
    _, problems = items.make_item(doc, cut, "x")
    assert any("doesn't start at a sentence" in p for p in problems)
    h = text.index("Funding woes"); doc.exclusions.append(markup.Exclusion("boilerplate", h, h + len("Funding woes")))
    _, problems = items.make_item(doc, cut, "x")
    assert problems == []


def fake_item(item_id, doc, tier, n_segments=1):
    return {"item_id": item_id, "tier": tier, "segments": [{}] * n_segments, "source": {"document": doc}, "split": None}


def test_splits_keep_documents_together_and_blind_corpora_in_test():
    its = [fake_item(f"d{k}-{t}", f"c-{k}", tier) for k in range(20) for t, (tier, *_) in enumerate(items.TIERS)]
    its += [fake_item("b-01", "blind-1", "T1"), fake_item("b-02", "blind-1", "T2")]
    small = {"targets": {"test": {"items": 2, "segments": 2}, "dev": {"items": 2, "segments": 0}}, "t0_targets": {"test": 0, "dev": 0}}
    seed, a = items.assign_splits(its, dev_share=0.3, test_only=("blind",), **small)
    assert seed is not None and a["blind-1"] == "test" and set(a.values()) == {"dev", "test"}
    assert items.assign_splits(its, dev_share=0.3, test_only=("blind",), **small) == (seed, a)  # reproducible
    assert items.split_problems(its, a, **small) == []
    assert items.split_problems(its, {d: "test" for d in a}, **small)  # no dev at all


def test_agreement_sample_per_tier():
    its = [fake_item(f"a{k:02d}", f"c-{k}", "T1") for k in range(40)] + [fake_item(f"b{k}", f"c-{k}", "T2") for k in range(3)]
    ids = items.agreement_sample(its, share=0.2, minimum=5, seed=1)
    assert sum(i.startswith("a") for i in ids) == 8 and sum(i.startswith("b") for i in ids) == 3
    assert ids == items.agreement_sample(its, share=0.2, minimum=5, seed=1)


def test_dropped_items_keep_their_place(tmp_path, capsys):
    docs, cuts, out = tmp_path / "annotations", tmp_path / "cuts", tmp_path / "items.jsonl"
    docs.mkdir()
    cuts.mkdir()
    (docs / "invented-lab.xml").write_text(LAB.read_text(encoding="utf-8"), encoding="utf-8")
    path = cuts / "invented-lab.json"
    path.write_text(json.dumps({"document": "invented-lab", "items": [
        {"from": "no longer in the text", "to": "anywhere", "dropped": "a reason"},
        {"from": "Anna Berg, who leads", "to": "the permits.”"}]}), encoding="utf-8")
    assert cli.main(["cut", str(path), "--documents", str(docs), "--out", str(out)]) == 0
    assert [json.loads(line)["item_id"] for line in out.read_text(encoding="utf-8").splitlines()] == ["invented-lab-02"]
    assert "invented-lab-01: dropped (a reason)" in capsys.readouterr().out
    assert [i["item_id"] for i in cli._load_items([path], docs)] == ["invented-lab-02"]
    doc = markup.blank("invented-lab-01", "x")
    doc.status, doc.annotator = "reviewed", "T"
    (tmp_path / "saved.xml").write_text(markup.serialize(doc), encoding="utf-8")
    assert cli.main(["review", str(tmp_path / "saved.xml"), "--documents", str(docs), "--cuts", str(cuts)]) == 1
