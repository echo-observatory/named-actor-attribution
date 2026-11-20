# Cutting documents into items

Reviewed documents are cut into the dataset's items: short passages, each with its own labels, levels and tier (spec §4–§6). The model chooses the passages; a script builds and checks them.

## Cut lists

One JSON file per document, in [`cuts/`](../cuts/), names the passages to keep, each by its first and last words:

```json
{"document": "global-voices-cheese-181-705184", "items": [
  {"from": "In mid-March, Nexer", "to": "topped the list."},
  {"from": "Ashburne says he likes to vary", "to": "often without.",
   "names": {"S2": "Ashburne"}, "levels": {"he likes to vary": ["D2", "R1"]},
   "note": "Optional note on the item."}
]}
```

- `from`, `to`: the passage runs from the first occurrence of `from` (or the `n`-th, with `n`) to the end of the first `to` after it.
- `names`: the canonical name of a speaker in this item, when the item doesn't contain the document's (spec §2: the fullest name the item uses). By the document's speaker id.
- `levels`: the levels of a segment in this item, when they differ from the document's, by the segment's first words. Levels depend on where the passage starts and ends; the model sets them (guidelines, Principle 6).

An entry with no `from` (`{}`) takes the whole document: used for adapted passages.

Items are numbered in the order of the list: `<document id>-01`, `-02`…

## Adapted passages

Where the easy tiers lack items, a passage may be adapted to make it simpler (spec §5.1): drop sentences or clauses, replace a pronoun or descriptor with the actor's name, or rewrite a lead-in and its block quote as an inline quote with its cue. Edits are minimal and never add content attributed to an actor.

An adapted passage becomes a document of its own, `<document id>-a1.xml`, made with `naa adapt` from a JSON file in the [draft format](drafting.md), plus the source passage and the new text:

```json
{"document": "global-voices-cheese-181-95433", "id": "a1",
 "from": "Eyeris wonders why", "to": "nearby McD outlets? Hmmm",
 "text": "“There’s another restaurant … Hmmm,” writes Eyeris.",
 "adaptation": "Lead-in and block quote rewritten as an inline quote with its cue.",
 "speakers": [["S1", "Eyeris", "organization"]],
 "spans": [["seg", "S1", "There’s another restaurant", {"to": "Hmmm", "d": "D1", "r": "R1"}]]}
```

```bash
uv run naa adapt adaptation.json
```

The document records its source and the edit (`adapted-from`, `source-start`, `source-end`, `adaptation`), and is drafted like any other: a person reviews it, since its text changed. Its cut list takes it whole (`{"document": "…-a1", "items": [{}]}`), and its item is marked `adapted` with the edit, its credit line saying the text was adapted.

## Choosing passages

`naa runs` lists each document's paragraphs, with their words, segments (speaker and levels), distractors and exclusions, to choose from.

- Keep the scarce tiers in mind: a paragraph that could be one T7 item may give two T1 items instead.
- Leave out a passage whose speaker isn't clear from the passage alone (guidelines, Principle 1).
- Items of the same document don't overlap.

## Checks

`naa cut` refuses an item that:

- contains an exclusion, or cuts a segment or a distractor in two;
- doesn't start and end at a sentence, or, from T3 up, at a paragraph;
- has a speaker whose canonical name isn't in the passage;
- has no tier (over 600 words, a segment without levels), or is a T0 item without a distractor;
- overlaps another item taking text from the same document, adapted passages included;
- is adapted and lands above T3, or doesn't take the adapted document whole.

## Output

```bash
uv run naa cut cuts/*.json --corpus ../obs-test-datasets/global-voices-cheese-181/articles.jsonl \
  --out items.jsonl --page items.html
```

- For each item: its tier and the caps of the tier below that it breaks (`D`, `R`, `speakers`, `words`).
- A yield table: items and segments per tier against the targets of spec §9 (test and dev together), and how many items break the tier below on its main difficulty (spec §4: at least half should).
- `--out`: the items as JSONL, in the format of spec §6, with `tier_breaks` added and `split` left empty. `--corpus` fills each item's source details.
- `--page`: an annotation page holding the items, to read them as they will be scored.
