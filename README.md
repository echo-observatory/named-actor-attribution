# named-actor-attribution

Builds a small, frozen English eval dataset for one task: finding the text segments that express what a named actor said, wrote, believes or intends, and attributing each one to that actor.
The items are graded into 8 difficulty tiers, so that an eval shows where a system starts to fail, not only how well it does overall.
This is the task of Karaage's attribution step.

A side project, not a pipeline component: the dataset will be used later in evals in the [`evals`](https://github.com/echo-observatory/evals) repo, and possibly published in some form in `obs-test-datasets`.

Version 1.1.0: 372 items, 497 gold segments. [`items.jsonl`](items.jsonl) is the dataset; the [dataset card](#dataset-card) says what it is and isn't.

## Contents

| Path | What it holds |
| --- | --- |
| [`items.jsonl`](items.jsonl) | The dataset, one item per line, in the format of spec §6. |
| [`tiers.md`](tiers.md), [`prototypes.md`](prototypes.md) | The tiers, with their counts and human agreement, and five dev items per tier. |
| [`CHANGELOG.md`](CHANGELOG.md) | The versions of the dataset. |
| [`guidelines.md`](guidelines.md) | The annotation guidelines, for the drafting model, reviewers and second annotators. |
| [`specification.md`](specification.md) | The dataset specification: task, difficulty levels and tiers, item construction, data format, annotation procedure, scoring, and deliverables. |
| [`docs/markup.md`](docs/markup.md) | The markup format: the working format of annotations, one source document per file, with spans marked in the text. |
| [`annotations/`](annotations/) | Annotated documents in the markup format, with their licence and credits. |
| [`docs/drafting.md`](docs/drafting.md), [`prompts/`](prompts/) | How documents are drafted and miss-checked, the draft format that `naa apply` reads, and the miss-check prompt. |
| [`cuts/`](cuts/), [`docs/cutting.md`](docs/cutting.md) | The cut lists, which name the passages kept as items, and how cutting works. |
| [`splits.json`](splits.json) | The split, dev or test, of each source document, with the seed and procedure that drew it (spec §9). |
| [`agreement.json`](agreement.json), [`agreement/`](agreement/) | The items of the agreement sample (spec §7), and the record of it: the gold as it was, the second annotator's labels, and the results. |
| [`annotator/annotator.html`](annotator/annotator.html) | The annotation page: a single HTML file with no dependencies (see [Annotation page](#annotation-page)). |
| [`docs/evaluation.md`](docs/evaluation.md) | Scoring a system, or a second annotator, against the gold. |
| [`src/named_actor_attribution/`](src/named_actor_attribution/), [`tests/`](tests/) | The `naa` command line, and its tests. |

## Plan

1. **Annotate whole source documents** in the [markup format](docs/markup.md): Claude drafts them, and a DeepSeek model on OpenRouter looks for missed segments (spec §7).
2. **Cut items** from the documents by computed tier, adapting low-tier passages where needed (spec §5.1).
3. **Review the items in an annotation page:** a self-contained HTML page that shows the segments highlighted by speaker, and lets a reviewer change boundaries, add segments, assign or rename speakers, and set distractors. Corrections go back into the documents. The same page can be sent to other annotators, who annotate from scratch and send back the file it saves. No account or server is needed.
4. **Freeze** the dataset in this repo: validation, the agreement sample, splits, and a version (spec §9–§10).

## Inputs

Corpora of English texts whose license allows redistribution, from `obs-test-datasets`:
- [`global-voices-cheese-181`](https://github.com/echo-observatory/obs-test-datasets/tree/main/global-voices-cheese-181) (CC BY 3.0): mostly blog roundups, rich in block quotes and tweets, so it suits the higher tiers;
- [`wikinews-quote-rich-100`](https://github.com/echo-observatory/obs-test-datasets/tree/main/wikinews-quote-rich-100) (CC BY 2.5 or 4.0): news articles chosen for their quotes, mostly inline ("…,” said X), with several named speakers per article. Not `wikinews-piracy-30`, which is Karaage's development set.
- [`wikinews-repeated-claims-iran-nuclear-59`](https://github.com/echo-observatory/obs-test-datasets/tree/main/wikinews-repeated-claims-iran-nuclear-59) (CC BY 2.5 or 4.0): short news items on Iran's nuclear programme, with many officials and governments as speakers. Its items go to the `test` split only, since that set is meant to stay blind for repeated-claims evaluation.

No Retriever data: the dataset is meant to be published.

## Outputs

The deliverables listed in spec §10, mainly `items.jsonl`: one item per line, with its text, speakers, gold segments, difficulty levels and distractors (format in spec §6). Also an evaluator that scores a system's output against the gold (spec §8).

## Dataset card

### What it holds

372 items in 8 difficulty tiers, with 497 gold segments and 194 distractors: short passages of English news and blog roundups published between 2005 and 2025. [`tiers.md`](tiers.md) gives the counts per tier and split.

- **Splits:** 75 items in dev, 297 in test. Dev is free to use. Test is scored in aggregate only, and never inspected item by item (spec §9). Documents were drawn at random, and all the items of a document are in one split; [`splits.json`](splits.json) has the seed.
- **Sources and licences:** Global Voices, 156 items, CC BY 3.0; Wikinews, 216 items, CC BY 2.5 or 4.0. Each item has its licence, URL and credit line (`source`), and [`annotations/README.md`](annotations/README.md) credits every document. 27 items are adapted: they say so, with the edit.

### How it was made

1. **Drafted** by Claude Opus 5.5: segments, speakers, distractors, levels, and the choice of passages ([`prompts/drafting.md`](prompts/drafting.md)).
2. **Miss-checked** by DeepSeek V4 Pro, which flags what a draft may have missed.
3. **Reviewed** by one person, item by item: everything but the levels.
4. **Compared** with a second annotator, who labelled 80 items from plain text ([`agreement/`](agreement/)). Speaker accuracy was at least 0.90 in every tier. The gold was then corrected, and 24 items were dropped.

### Known limits

- **Cleaner than real text.** Ambiguous passages are left out on purpose, with joint attributions ("Berg and Holm said…"), nested ones ("A said that B told her…") and non-English text. Some low-tier items are adapted.
- **One canonical name per speaker and item.** Reconciling actors across documents is out of scope.
- **The gold may share its drafter's blind spots.** Reports should flag the scores of Claude-based systems. The reviewer corrected drafts rather than labelling from scratch, and the miss check flagged no real miss.
- **T5 and T0 are the least settled tiers.** T5 had the lowest agreement (joint F1 0.76), and the second annotator marked text in half of the T0 items. The agreement samples are small.
- **T6 measures two things:** references across a paragraph break, mostly, and competing candidates.
- **T7 measures detection, not reference.** All its items are there for a segment that crosses a paragraph or has no cue nearby, and 34 of its 47 segments name the speaker in the same sentence or in the lead-in. No segment is R6 (a speaker with no mention), and only 5 are R4 (a role or descriptor).
- **The order of the tiers is by rule, and untested.** Nothing yet shows that systems find T7 harder than T6.
- **Thin margins.** T7 test has exactly the 40 segments of the target, and T5, T6 and T7 dev have 5 items each.
- **Narrow sources.** Two publishers, and 80 test items from a corpus on Iran's nuclear programme. These are test-only, to keep another evaluation blind.
- **Public text.** The articles are on the web, so systems may have seen them in training, though not the labels.

## Setup

Requires Python 3.12 or later and [uv](https://docs.astral.sh/uv/). The command line has no dependencies beyond the standard library.

```bash
uv sync
uv run pytest
```

The tests of the annotation page run its self-test in headless Chrome or Chromium, and are skipped when neither is found. Set `CHROME` to the browser's path if it isn't found on its own.

## Commands

```bash
# Create blank documents from a corpus, ready to annotate (writes annotations/<source>-<id>.xml)
uv run naa new ../obs-test-datasets/global-voices-cheese-181/articles.jsonl 483946 766250

# Annotate a document from a draft that quotes each span (docs/drafting.md)
uv run naa apply annotations/global-voices-cheese-181-483946.xml draft.json

# Ask a second model for missed segments and doubts (docs/drafting.md); needs an OpenRouter key, NAA_API_KEY, in .env
uv run naa misscheck annotations/global-voices-cheese-181-483946.xml

# Check documents: exits 1 if any has an error
uv run naa check annotations/*.xml

# Accept a deliberate change to a document's text
uv run naa rehash annotations/global-voices-cheese-181-483946.xml

# Write documents as JSONL records with offsets
uv run naa export annotations/*.xml --out documents.jsonl

# Create an adapted passage, as a document of its own (docs/cutting.md)
uv run naa adapt adaptation.json

# List documents' paragraphs, to choose the passages to cut
uv run naa runs annotations/*.xml

# Build the items from the cut lists, check them, and report their tiers
uv run naa cut cuts/*.json --corpus ../obs-test-datasets/global-voices-cheese-181/articles.jsonl \
  --corpus ../obs-test-datasets/wikinews-quote-rich-100/articles.jsonl \
  --corpus ../obs-test-datasets/wikinews-repeated-claims-iran-nuclear-59/articles.jsonl --out items.jsonl --page items.html

# Record the review of items saved from that page; corrections go back into their documents
uv run naa review reviewed-items.xml

# Assign source documents to dev or test at random, meeting the per-tier minimums of spec §9;
# then fill each item's split when cutting
uv run naa assign-splits cuts/*.json
uv run naa cut cuts/*.json --splits splits.json --agreement agreement.json --out items.jsonl

# Run the acceptance checks of spec §10, and write the prototypes
uv run naa validate items.jsonl
uv run naa prototypes items.jsonl prototypes.json

# Draw the agreement sample, 20% of each tier, and build a blank page of its items for a second annotator
uv run naa agreement cuts/*.json --page agreement-blank.html

# Build a copy of the annotation page with documents built in, to send to an annotator;
# --blank removes the annotation, for annotating from scratch
uv run naa page annotations/a.xml annotations/b.xml --out to-send.html --blank

# Split a file saved with the page's "Save all" into one file per document
uv run naa split annotations-2026-11-20.xml --out second-annotator/
```

## Annotation page

[`annotator/annotator.html`](annotator/annotator.html) opens in any browser, offline. Nothing leaves the page: it reads and writes files on your computer.

- **Open** one or more markup files with Open…, or drop them on the page. In Chrome and Edge, Save writes back to the file you opened; in other browsers, it downloads the file.
- **Read:** segments are coloured by speaker, with the speaker's name before each and the levels after; distractors are dashed, exclusions hatched. Labels can be hidden. The Checks panel lists the problems `naa check` would report; click one to go to its span.
- **Edit:**
  - select text, then pick a speaker in the toolbar (or press `1`–`9`) to make it a segment, or make it a distractor or an exclusion. Selections snap to whole words and drop surrounding quotation marks; hold Alt while selecting for exact characters;
  - click a span to change its speaker, kind, levels, note or boundaries (◀ ▶ move an edge by a word, with Shift by a character), or delete it;
  - in Speakers: rename, change the type, merge a speaker into another, or add one. "Use … as speaker" in the toolbar adds a speaker named after the selected text;
  - set the document's status and your name in the header. Undo with Ctrl+Z.
- **Unsaved work** is kept in the browser while you work, and offered back when the same document is opened again.
- **Annotators** get a copy built with `naa page`, with the documents inside it. Several documents open as a list. "Save all" writes each document back to the file it was opened from, where the browser allows it (Chrome and Edge); documents built into the page, or opened in other browsers, are downloaded together as one file, to split with `naa split`.

## Licence

The annotations, the documentation and the code are under [CC BY 4.0](LICENSE). The texts keep their own licences: CC BY 3.0 for Global Voices, and CC BY 2.5 or 4.0 for Wikinews. Reusing an item means crediting its text too: its licence and its credit line are in `source`.
