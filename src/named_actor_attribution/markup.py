"""The working markup format: one annotated source document per file (see docs/markup.md).

Offsets are in Unicode code points, which is what Python string indices count.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

SPEAKER_TYPES = ("person", "organization")
DETECTION_LEVELS = ("D1", "D2", "D3", "D4", "D5")
REFERENCE_LEVELS = ("R1", "R2", "R3", "R4", "R5", "R6")
DISTRACTOR_TYPES = (
    "named_no_attribution",
    "unnamed_source",
    "document_source",
    "author_voice",
    "non_statement",
    "negated_speech",
    "quoted_title_or_scare_quote",
)
STATUSES = ("blank", "drafted", "reviewed")
# Why a stretch of text keeps any item that contains it out of the dataset (spec §5.1, §5.2).
EXCLUSION_REASONS = (
    "joint",          # attributed to several actors at once
    "nested",         # an attribution inside another one
    "unresolved",     # the speaker can't be resolved, or has no canonical name (a handle only)
    "non-english",    # a sentence or quote in another language
    "boilerplate",    # a caption, photo credit, editorial note or headline: removed from items
)

DOCUMENT_ATTRS = {"id", "source", "source-id", "text-sha256", "status", "annotator", "drafted-by", "miss-check-by"}
SPEAKER_ATTRS = {"id", "name", "type"}
SEG_ATTRS = {"speaker", "d", "r", "note"}
DIS_ATTRS = {"type", "note"}
EXCLUDE_ATTRS = {"reason", "note"}

# Quotation marks that open or close a quote; a segment never starts or ends with one (spec §2).
QUOTE_MARKS = "\"'“”‘’«»„‟‹›"


class MarkupError(ValueError):
    """The file is not a valid markup document; nothing can be read from it."""


@dataclass
class Speaker:
    id: str
    name: str
    type: str


@dataclass
class Segment:
    speaker: str
    start: int
    end: int
    d: str | None = None
    r: str | None = None
    note: str | None = None


@dataclass
class Distractor:
    type: str
    start: int
    end: int
    note: str | None = None


@dataclass
class Exclusion:
    reason: str
    start: int
    end: int
    note: str | None = None


@dataclass
class Document:
    id: str
    text: str
    source: str | None = None
    source_id: str | None = None
    text_sha256: str | None = None
    status: str = "blank"
    annotator: str | None = None
    drafted_by: str | None = None
    miss_check_by: str | None = None
    speakers: list[Speaker] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    distractors: list[Distractor] = field(default_factory=list)
    exclusions: list[Exclusion] = field(default_factory=list)
    notes: str | None = None


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --- Reading -----------------------------------------------------------------


def parse(markup: str) -> Document:
    """Read a markup document. Raises MarkupError when the structure is wrong.

    Content problems that still leave a readable document (an unknown speaker, a bad level)
    are reported by check(), not here.
    """
    root = _root(markup)
    if root.tag != "document":
        raise MarkupError(f"the root element is <{root.tag}>, not <document>")
    return _parse_document(root)


def parse_many(markup: str) -> list[Document]:
    """Read a single document, or a bundle: <documents> holding several (the annotation page's "Save all")."""
    root = _root(markup)
    if root.tag == "document":
        return [_parse_document(root)]
    if root.tag != "documents":
        raise MarkupError(f"the root element is <{root.tag}>, not <document> or <documents>")
    docs = []
    for child in root:
        if child.tag != "document":
            raise MarkupError(f"unexpected element <{child.tag}> in <documents>")
        docs.append(_parse_document(child))
    return docs


def _root(markup: str) -> ET.Element:
    try:
        return ET.fromstring(markup)
    except ET.ParseError as e:
        raise MarkupError(f"not well-formed XML: {e}") from None


def _parse_document(root: ET.Element) -> Document:
    _no_unknown_attrs(root, DOCUMENT_ATTRS)
    if not root.get("id"):
        raise MarkupError("<document> has no id")

    children = list(root)
    tags = [c.tag for c in children]
    for tag in tags:
        if tag not in ("speakers", "text", "notes"):
            raise MarkupError(f"unexpected element <{tag}> in <document>")
        if tags.count(tag) > 1:
            raise MarkupError(f"<{tag}> appears more than once")
    if "text" not in tags:
        raise MarkupError("<document> has no <text>")

    doc = Document(
        id=root.get("id"),
        text="",
        source=root.get("source"),
        source_id=root.get("source-id"),
        text_sha256=root.get("text-sha256"),
        status=root.get("status", "blank"),
        annotator=root.get("annotator"),
        drafted_by=root.get("drafted-by"),
        miss_check_by=root.get("miss-check-by"),
    )
    for child in children:
        if child.tag == "speakers":
            for sp in child:
                if sp.tag != "speaker":
                    raise MarkupError(f"unexpected element <{sp.tag}> in <speakers>")
                _no_unknown_attrs(sp, SPEAKER_ATTRS)
                doc.speakers.append(Speaker(id=sp.get("id", ""), name=sp.get("name", ""), type=sp.get("type", "")))
        elif child.tag == "notes":
            doc.notes = child.text or ""
        elif child.tag == "text":
            _read_text(child, doc)
    return doc


def _read_text(el: ET.Element, doc: Document) -> None:
    parts = [el.text or ""]
    pos = len(parts[0])
    for span in el:
        if span.tag not in ("seg", "dis", "exclude"):
            raise MarkupError(f"unexpected element <{span.tag}> in <text>: only <seg>, <dis> and <exclude> are allowed")
        if len(span):
            raise MarkupError(f"<{span.tag}> at character {pos} contains <{span[0].tag}>: spans cannot nest")
        inner = span.text or ""
        start, end = pos, pos + len(inner)
        if span.tag == "seg":
            _no_unknown_attrs(span, SEG_ATTRS)
            doc.segments.append(Segment(speaker=span.get("speaker", ""), start=start, end=end,
                                        d=span.get("d"), r=span.get("r"), note=span.get("note")))
        elif span.tag == "dis":
            _no_unknown_attrs(span, DIS_ATTRS)
            doc.distractors.append(Distractor(type=span.get("type", ""), start=start, end=end, note=span.get("note")))
        else:
            _no_unknown_attrs(span, EXCLUDE_ATTRS)
            doc.exclusions.append(Exclusion(reason=span.get("reason", ""), start=start, end=end, note=span.get("note")))
        tail = span.tail or ""
        parts += [inner, tail]
        pos = end + len(tail)
    doc.text = "".join(parts)


def _no_unknown_attrs(el: ET.Element, allowed: set[str]) -> None:
    unknown = sorted(set(el.attrib) - allowed)
    if unknown:
        raise MarkupError(f"<{el.tag}> has unknown attribute(s): {', '.join(unknown)}")


# --- Checking ----------------------------------------------------------------


@dataclass
class Problem:
    level: str  # "error" or "warning"
    message: str

    def __str__(self) -> str:
        return f"{self.level}: {self.message}"


def check(doc: Document) -> list[Problem]:
    """Content checks on a parsed document. Errors must be fixed; warnings are worth a look."""
    out: list[Problem] = []

    def err(msg: str) -> None:
        out.append(Problem("error", msg))

    def warn(msg: str) -> None:
        out.append(Problem("warning", msg))

    if doc.text_sha256 is None:
        err("<document> has no text-sha256, so changes to the text can't be detected")
    elif doc.text_sha256 != text_sha256(doc.text):
        err("the text differs from the one this document was created with (text-sha256); "
            "if the change is deliberate, run `naa rehash`")
    if doc.status not in STATUSES:
        err(f"status {doc.status!r} is not one of {', '.join(STATUSES)}")

    ids = [s.id for s in doc.speakers]
    for sp in doc.speakers:
        if not sp.id:
            err(f"speaker {sp.name!r} has no id")
        elif ids.count(sp.id) > 1:
            err(f"speaker id {sp.id} is used more than once")
        if not sp.name.strip():
            err(f"speaker {sp.id} has no name")
        if sp.type not in SPEAKER_TYPES:
            err(f"speaker {sp.id} has type {sp.type!r}, not one of {', '.join(SPEAKER_TYPES)}")
    names = [normalize_name(s.name) for s in doc.speakers]
    for name in sorted({n for n in names if names.count(n) > 1}):
        err(f"several speakers have the name {name!r}")
    for sp in doc.speakers:
        if sp.name.strip() and not name_occurs(sp.name, doc.text):
            warn(f"the name of speaker {sp.id} ({sp.name!r}) does not occur in the text")

    used = {s.speaker for s in doc.segments}
    for sp in doc.speakers:
        if sp.id and sp.id not in used:
            warn(f"speaker {sp.id} ({sp.name}) has no segment")

    for seg in doc.segments:
        where = f"segment at {seg.start}–{seg.end} ({_excerpt(doc.text, seg.start, seg.end)})"
        if seg.speaker not in ids:
            err(f"{where} has speaker {seg.speaker!r}, which is not declared")
        if seg.d is not None and seg.d not in DETECTION_LEVELS:
            err(f"{where} has detection level {seg.d!r}")
        if seg.r is not None and seg.r not in REFERENCE_LEVELS:
            err(f"{where} has reference level {seg.r!r}")
        if doc.status == "reviewed" and (seg.d is None or seg.r is None):
            warn(f"{where} has no {'D' if seg.d is None else 'R'} level")
        inner = doc.text[seg.start:seg.end]
        if not trim(inner):
            err(f"{where} is empty once whitespace and punctuation are trimmed")
        elif inner[0].isspace() or inner[-1].isspace() or edge_quote(inner):
            warn(f"{where} starts or ends with whitespace or a quotation mark")

    for dis in doc.distractors:
        if dis.type not in DISTRACTOR_TYPES:
            err(f"distractor at {dis.start}–{dis.end} has type {dis.type!r}")
        if not doc.text[dis.start:dis.end].strip():
            err(f"distractor at {dis.start}–{dis.end} is empty")

    for ex in doc.exclusions:
        if ex.reason not in EXCLUSION_REASONS:
            err(f"exclusion at {ex.start}–{ex.end} has reason {ex.reason!r}, not one of {', '.join(EXCLUSION_REASONS)}")
        if not doc.text[ex.start:ex.end].strip():
            err(f"exclusion at {ex.start}–{ex.end} is empty")

    segs = sorted(doc.segments, key=lambda s: s.start)
    for a, b in zip(segs, segs[1:]):
        if a.speaker == b.speaker and not trim(doc.text[a.end:b.start]):
            warn(f"segments at {a.start} and {b.start} have the same speaker and only whitespace or "
                 "punctuation between them: merge them (a gold segment is a maximal run, spec §2)")
    return out


def edge_quote(s: str) -> bool:
    """A segment starts with a quotation mark, or ends with one that closes nothing inside it.

    Mixed speech may end with a quoted fragment (`would reopen “if the funding holds”`): that is fine.
    """
    if s[0] in QUOTE_MARKS:
        return True
    return s[-1] in QUOTE_MARKS and not any(c in QUOTE_MARKS for c in s[:-1])


def _excerpt(text: str, start: int, end: int, width: int = 40) -> str:
    s = text[start:end]
    return repr(s if len(s) <= width else s[: width - 1] + "…")


def trim(s: str) -> str:
    """Strip leading and trailing whitespace and punctuation, as the scoring does (spec §8.1)."""
    i, j = 0, len(s)
    while i < j and _is_trimmed(s[i]):
        i += 1
    while j > i and _is_trimmed(s[j - 1]):
        j -= 1
    return s[i:j]


def _is_trimmed(ch: str) -> bool:
    return ch.isspace() or unicodedata.category(ch).startswith("P")


def normalize_name(name: str) -> str:
    return " ".join(name.lower().split())


def name_occurs(name: str, text: str) -> bool:
    """The canonical name occurs verbatim, or with only a quoted or bracketed nickname inside it (spec §2)."""
    words = name.split()
    if not words:
        return False
    nickname = r"(?:\s+(?:[\"'“‘(\[][^\"'”’)\]]{1,40}[\"'”’)\]]))?"
    pattern = (nickname + r"\s+").join(re.escape(w) for w in words)
    return re.search(pattern, text) is not None


# --- Writing -----------------------------------------------------------------


def serialize(doc: Document) -> str:
    """Write a document as markup. parse(serialize(doc)) gives the same document back."""
    attrs = [("id", doc.id), ("source", doc.source), ("source-id", doc.source_id),
             ("text-sha256", doc.text_sha256), ("status", doc.status), ("annotator", doc.annotator),
             ("drafted-by", doc.drafted_by), ("miss-check-by", doc.miss_check_by)]
    lines = [f"<document{_attrs(attrs)}>", "<speakers>"]
    for sp in doc.speakers:
        lines.append(f"  <speaker{_attrs([('id', sp.id), ('name', sp.name), ('type', sp.type)])}/>")
    lines.append("</speakers>")
    lines.append(f"<text>{_text_with_spans(doc)}</text>")
    if doc.notes is not None:
        lines.append(f"<notes>{_escape(doc.notes)}</notes>")
    lines.append("</document>")
    return "\n".join(lines) + "\n"


def _text_with_spans(doc: Document) -> str:
    spans = [(s.start, s.end, "seg", [("speaker", s.speaker), ("d", s.d), ("r", s.r), ("note", s.note)])
             for s in doc.segments]
    spans += [(d.start, d.end, "dis", [("type", d.type), ("note", d.note)]) for d in doc.distractors]
    spans += [(x.start, x.end, "exclude", [("reason", x.reason), ("note", x.note)]) for x in doc.exclusions]
    spans.sort(key=lambda x: (x[0], x[1]))
    out, pos = [], 0
    for start, end, tag, attrs in spans:
        if start < pos:
            raise ValueError(f"spans overlap at character {start}")
        out.append(_escape(doc.text[pos:start]))
        out.append(f"<{tag}{_attrs(attrs)}>{_escape(doc.text[start:end])}</{tag}>")
        pos = end
    out.append(_escape(doc.text[pos:]))
    return "".join(out)


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _attrs(pairs: list[tuple[str, str | None]]) -> str:
    out = []
    for k, v in pairs:
        if v is None:
            continue
        v = (_escape(v).replace('"', "&quot;")
             .replace("\n", "&#10;").replace("\r", "&#13;").replace("\t", "&#9;"))
        out.append(f' {k}="{v}"')
    return "".join(out)


def blank(doc_id: str, text: str, source: str | None = None, source_id: str | None = None) -> Document:
    """A new document with no annotation, ready to draft."""
    return Document(id=doc_id, text=text, source=source, source_id=source_id, text_sha256=text_sha256(text))


def stripped(doc: Document) -> Document:
    """The same document with its annotation removed, for annotating from scratch."""
    return Document(id=doc.id, text=doc.text, source=doc.source, source_id=doc.source_id, text_sha256=doc.text_sha256)


def rehash(markup: str) -> str:
    """Set text-sha256 to the current text, changing nothing else in the file."""
    doc = parse(markup)
    new = text_sha256(doc.text)
    root_tag = re.match(r"\s*(<document\b[^>]*>)", markup)
    if root_tag is None:
        raise MarkupError("can't find the <document> tag")
    tag = root_tag.group(1)
    if 'text-sha256="' in tag:
        new_tag = re.sub(r'text-sha256="[^"]*"', f'text-sha256="{new}"', tag)
    else:
        new_tag = tag[:-1].rstrip("/") + f' text-sha256="{new}">'
    return markup[: root_tag.start(1)] + new_tag + markup[root_tag.end(1):]


# --- Drafts ------------------------------------------------------------------


def apply_draft(doc: Document, draft: dict) -> tuple[Document, list[str]]:
    """Annotate a document from a draft that quotes each span's text (see docs/drafting.md).

    Returns the annotated document and the problems found (a text not found, or found several
    times without saying which). Existing speakers and spans are replaced.
    """
    out = Document(**{**doc.__dict__, "speakers": [], "segments": [], "distractors": [], "exclusions": []})
    out.status = draft.get("status", "drafted")
    if "drafted_by" in draft:
        out.drafted_by = draft["drafted_by"]
    if "notes" in draft:
        out.notes = draft["notes"]
    out.speakers = [Speaker(i, n, t) for i, n, t in draft.get("speakers", [])]
    problems = []
    for entry in draft.get("spans", []):
        kind, value, text, *rest = entry
        opts = rest[0] if rest else {}
        hits, i = [], out.text.find(text)
        while i >= 0:
            hits.append(i)
            i = out.text.find(text, i + 1)
        n = opts.get("n")
        if not hits:
            problems.append(f"not found: {text[:60]!r}")
            continue
        if n is None and len(hits) > 1:
            problems.append(f"found {len(hits)} times, say which with n: {text[:60]!r}")
            continue
        if n is not None and not 1 <= n <= len(hits):
            problems.append(f"n={n}, but found {len(hits)} times: {text[:60]!r}")
            continue
        start = hits[(n or 1) - 1]
        end = start + len(text)
        if "to" in opts:
            j = out.text.find(opts["to"], start)
            if j < 0:
                problems.append(f"end not found after {text[:30]!r}: {opts['to'][:60]!r}")
                continue
            end = j + len(opts["to"])
        if kind == "seg":
            out.segments.append(Segment(value, start, end, opts.get("d"), opts.get("r"), opts.get("note")))
        elif kind == "dis":
            out.distractors.append(Distractor(value, start, end, opts.get("note")))
        elif kind == "exclude":
            out.exclusions.append(Exclusion(value, start, end, opts.get("note")))
        else:
            problems.append(f"unknown kind {kind!r}")
    return out, problems


# --- Records -----------------------------------------------------------------


def to_record(doc: Document) -> dict:
    """The document as a JSON-ready record with offsets, close to the item format of spec §6."""
    names = {s.id: s.name for s in doc.speakers}
    segs = sorted(doc.segments, key=lambda s: s.start)
    return {
        "doc_id": doc.id,
        "source": doc.source,
        "source_id": doc.source_id,
        "status": doc.status,
        "annotator": doc.annotator,
        "drafted_by": doc.drafted_by,
        "miss_check_by": doc.miss_check_by,
        "text": doc.text,
        "speakers": [{"speaker_id": s.id, "canonical_name": s.name, "type": s.type} for s in doc.speakers],
        "segments": [
            {"segment_id": f"G{i}", "speaker_id": s.speaker, "speaker": names.get(s.speaker),
             "start": s.start, "end": s.end, "text": doc.text[s.start:s.end],
             "detection_level": s.d, "reference_level": s.r, "note": s.note}
            for i, s in enumerate(segs, 1)
        ],
        "distractors": [
            {"type": d.type, "spans": [[d.start, d.end]], "text": doc.text[d.start:d.end], "note": d.note}
            for d in sorted(doc.distractors, key=lambda d: d.start)
        ],
        "exclusions": [
            {"reason": x.reason, "start": x.start, "end": x.end, "text": doc.text[x.start:x.end], "note": x.note}
            for x in sorted(doc.exclusions, key=lambda x: x.start)
        ],
        "notes": doc.notes,
    }
