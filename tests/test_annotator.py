"""The annotation page: building it with documents built in, and its self-test in headless Chrome."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from named_actor_attribution import cli, markup

FIXTURES = Path(__file__).parent / "fixtures"
LAB = FIXTURES / "invented-lab.xml"


def embedded(page: str) -> list[str]:
    m = re.search(r'<script type="application/json" id="embedded-documents">(.*?)</script>', page, re.S)
    return json.loads(m.group(1))


def tricky_doc() -> markup.Document:
    """Text that would break the page if embedded carelessly."""
    text = "He wrote </script><script>alert(1)</script> and <!-- this --> in a post. 🧀"
    doc = markup.blank("tricky", text)
    doc.speakers.append(markup.Speaker("S1", "Anna Berg", "person"))
    doc.segments.append(markup.Segment("S1", 0, 2))
    return doc


def test_page_embeds_documents_safely(tmp_path):
    page = cli.build_page([markup.parse(LAB.read_text(encoding="utf-8")), tricky_doc()])
    assert page.count("</script>") == 2  # the two script elements of the template, nothing from the texts
    docs = embedded(page)
    assert docs[1] == markup.serialize(tricky_doc())
    assert markup.parse(docs[0]) == markup.parse(LAB.read_text(encoding="utf-8"))


def test_page_command_and_blank(tmp_path):
    out = tmp_path / "page.html"
    assert cli.main(["page", str(LAB), "--out", str(out), "--blank"]) == 0
    [doc] = [markup.parse(m) for m in embedded(out.read_text(encoding="utf-8"))]
    assert doc.text == markup.parse(LAB.read_text(encoding="utf-8")).text
    assert (doc.speakers, doc.segments, doc.distractors, doc.exclusions, doc.status) == ([], [], [], [], "blank")
    assert markup.check(doc) == []


def test_bundles_and_split(tmp_path):
    lab = markup.parse(LAB.read_text(encoding="utf-8"))
    bundle = "<documents>\n" + markup.serialize(lab) + markup.serialize(tricky_doc()) + "</documents>\n"
    assert [d.id for d in markup.parse_many(bundle)] == ["invented-lab", "tricky"]
    path = tmp_path / "bundle.xml"
    path.write_text(bundle, encoding="utf-8")
    out = tmp_path / "out"
    assert cli.main(["split", str(path), "--out", str(out)]) == 0
    assert markup.parse((out / "invented-lab.xml").read_text(encoding="utf-8")) == lab
    # A file that differs is kept, unless --force
    (out / "tricky.xml").write_text("changed", encoding="utf-8")
    assert cli.main(["split", str(path), "--out", str(out)]) == 1
    assert (out / "tricky.xml").read_text(encoding="utf-8") == "changed"
    assert cli.main(["split", str(path), "--out", str(out), "--force"]) == 0


def find_chrome() -> str | None:
    candidates = [os.environ.get("CHROME"), "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    for c in candidates:
        if c and (shutil.which(c) or Path(c).exists()):
            return shutil.which(c) or c
    return None


@pytest.mark.skipif(find_chrome() is None, reason="no Chrome or Chromium to run the page in")
def test_page_self_test_in_chrome(tmp_path):
    docs = [markup.parse(LAB.read_text(encoding="utf-8")), tricky_doc()]
    page = tmp_path / "page.html"
    page.write_text(cli.build_page(docs), encoding="utf-8")
    result = subprocess.run(
        [find_chrome(), "--headless=new", "--no-sandbox", "--disable-gpu", f"--user-data-dir={tmp_path / 'profile'}",
         "--dump-dom", page.as_uri() + "#selftest"],
        capture_output=True, text=True, timeout=60)
    m = re.search(r'<pre id="selftest">(.*?)</pre>', result.stdout, re.S)
    assert m, f"no self-test output; stderr: {result.stderr[-2000:]}"
    results = json.loads(m.group(1).replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&amp;", "&"))
    failed = [r for r in results if not r["ok"]]
    assert not failed, json.dumps(failed, indent=1, ensure_ascii=False)
    assert len(results) >= 15
