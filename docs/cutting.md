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

Items are numbered in the order of the list: `<document id>-01`, `-02`…

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
- overlaps another item of the same document.

## Output

```bash
uv run naa cut cuts/*.json --corpus ../obs-test-datasets/global-voices-cheese-181/articles.jsonl \
  --out items.jsonl --page items.html
```

- For each item: its tier and the caps of the tier below that it breaks (`D`, `R`, `speakers`, `words`).
- A yield table: items and segments per tier against the targets of spec §9 (test and dev together), and how many items break the tier below on its main difficulty (spec §4: at least half should).
- `--out`: the items as JSONL, in the format of spec §6, with `tier_breaks` added and `split` left empty. `--corpus` fills each item's source details.
- `--page`: an annotation page holding the items, to read them as they will be scored.
