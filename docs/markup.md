# Markup format

The working format for annotations: one source document per file, with its spans marked inside the text.
It is easy to read and edit by hand, models can draft it, and the annotation page reads and writes it.
It is temporary: the dataset's items and labels (spec §6) are generated from it.

## Example

```xml
<document id="invented-lab" source="invented" source-id="lab" text-sha256="…" status="drafted" drafted-by="claude-opus-5-5">
<speakers>
  <speaker id="S1" name="Anna Berg" type="person"/>
  <speaker id="S2" name="Barbados Free Press" type="organization"/>
</speakers>
<text>Anna Berg, who leads the lab, was upbeat. “<seg speaker="S1" d="D1" r="R3">The equipment is ready</seg>,” she said.

<dis type="unnamed_source">The lab will reopen in March, officials said.</dis> The blog Barbados Free Press writes:

<seg speaker="S2" d="D3" r="R1">Nobody wants to fund paperwork.</seg></text>
<notes>Free text, optional.</notes>
</document>
```

## Elements

**`<document>`**, the root, with these attributes:

| Attribute | Content |
| --- | --- |
| `id` | Required. `<source>-<source-id>` for documents made with `naa new`; also the file name, with `.xml`. |
| `source`, `source-id` | The corpus (e.g. `global-voices-cheese-181`) and the article's id in it. |
| `text-sha256` | SHA-256 of the text's UTF-8 bytes, set when the file is created. If the text changes, the check fails: this catches a model or an editor that changes the text while marking it up. A deliberate change (removing a caption, adapting a passage) is accepted with `naa rehash`. |
| `status` | `blank`, `drafted` or `reviewed`. |
| `annotator` | Who reviewed or annotated it. |
| `drafted-by`, `miss-check-by` | The models used, with versions. |

**`<speakers>`** lists the document's speakers: `<speaker id="S1" name="…" type="…"/>`, where `name` is the canonical name (spec §2) and `type` is `person` or `organization` (blogs and publications included). Renaming a speaker means changing one attribute.

**`<text>`** holds the document's text, exactly, with two kinds of spans inside it:

- `<seg speaker="S1" d="D1" r="R3">…</seg>`: an attributed segment. `speaker` is required. `d` and `r` are its detection and reference levels (spec §3): optional while drafting, expected once reviewed. A second annotator working from scratch doesn't need to set them.
- `<dis type="…">…</dis>`: a distractor (spec §5.3). One span per distractor.

Both may carry an optional `note`. Spans cannot nest or overlap.

There is no markup for cues or speaker mentions: levels are set by the annotator, and checked again on each item after cutting.

**`<notes>`**, optional: free text about the document.

## Text rules

- The text is everything between `<text>` and `</text>`, whitespace included: don't add a line break after `<text>` or before `</text>`. Paragraphs are separated by a blank line.
- Escape `&`, `<` and `>` as `&amp;`, `&lt;` and `&gt;`. Everything else is written as it is, in UTF-8.
- Offsets computed from the file are in Unicode code points into the text as stored, without normalization (spec §6).
- The file is XML: a parser refuses a file that is not well-formed, so a broken tag is never silently read.

## Checks

`naa check` reports errors, which must be fixed, and warnings, worth a look:

- **Errors:** malformed XML, unknown elements or attributes, nested spans, a changed text, an undeclared speaker, an invalid level or type, two speakers with the same name, an empty segment.
- **Warnings:**
  - a speaker's name that doesn't occur in the text (spec §2), or a speaker with no segment;
  - a segment that starts or ends with whitespace or a quotation mark;
  - two segments of the same speaker with only whitespace or punctuation between them, which should be merged (spec §2);
  - a reviewed segment without levels.
