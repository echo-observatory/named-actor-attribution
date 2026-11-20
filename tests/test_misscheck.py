import json
from pathlib import Path

import pytest

from named_actor_attribution import cli, markup, misscheck

FIXTURES = Path(__file__).parent / "fixtures"
LAB = FIXTURES / "invented-lab.xml"


def test_parse_flags_keeps_what_the_model_says():
    flags = misscheck.parse_flags(json.dumps({"flags": [
        {"kind": "missed", "quote": "the queue", "speaker": "Robert Smith", "reason": "indirect speech"},
        {"kind": "odd", "quote": "nowhere", "speaker": None}]}))
    assert flags[0] == markup.Flag("missed", "the queue", "indirect speech", "Robert Smith")
    assert (flags[1].kind, flags[1].reason, flags[1].speaker) == ("odd", "", None)  # kept, and flagged by check
    with pytest.raises(misscheck.MissCheckError):
        misscheck.parse_flags("not json")
    with pytest.raises(misscheck.MissCheckError):
        misscheck.parse_flags('{"answer": []}')


def test_flags_in_documents():
    doc = markup.parse(LAB.read_text(encoding="utf-8"))
    doc.flags = [markup.Flag("missed", "Nobody wants", "a quote", "Barbados Free Press"),
                 markup.Flag("doubt", "not in the text", "")]
    again = markup.parse(markup.serialize(doc))
    assert again.flags == doc.flags
    messages = [p.message for p in markup.check(again)]
    assert any("not in the document" in m for m in messages)
    assert any("left on a reviewed document" in m for m in messages)
    assert "<flag" not in misscheck.document_for_model(doc)


def test_api_key(tmp_path, monkeypatch):
    for name in misscheck.KEY_NAMES:
        monkeypatch.delenv(name, raising=False)
    env = tmp_path / ".env"
    with pytest.raises(misscheck.MissCheckError):
        misscheck.api_key(env)
    env.write_text('OTHER=1\nKARAAGE_API_KEY="abc"\n', encoding="utf-8")
    assert misscheck.api_key(env) == "abc"
    monkeypatch.setenv("OPENROUTER_API_KEY", "xyz")
    assert misscheck.api_key(env) == "xyz"


def test_misscheck_command(tmp_path, monkeypatch, capsys):
    path = tmp_path / "doc.xml"
    path.write_text(LAB.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(misscheck, "api_key", lambda *a: "key")
    answer = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(
        {"flags": [{"kind": "missed", "quote": "Nobody wants", "speaker": "Barbados Free Press", "reason": "r"}]})}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
    seen = {}

    def fake_ask(model, system, user, key, **kw):
        seen.update(model=model, system=system, user=user)
        return answer

    monkeypatch.setattr(misscheck, "ask", fake_ask)
    assert cli.main(["misscheck", str(path)]) == 0
    doc = markup.parse(path.read_text(encoding="utf-8"))
    assert doc.miss_check_by == misscheck.DEFAULT_MODEL and doc.flags[0].quote == "Nobody wants"
    assert "Annotation guidelines" in seen["system"] and seen["user"].startswith("<document")
    assert cli.main(["misscheck", str(path)]) == 0
    assert "already checked" in capsys.readouterr().out
