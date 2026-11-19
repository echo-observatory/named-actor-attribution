# named-actor-attribution

Builds a small, frozen English eval dataset for one task: finding the text segments that express what a named actor said, wrote, believes or intends, and attributing each one to that actor.
The items are graded into 8 difficulty tiers, so that an eval shows where a system starts to fail, not only how well it does overall.
This is the task of Karaage's attribution step.

A side project, not a pipeline component: the dataset will be used later in evals in the [`evals`](https://github.com/echo-observatory/evals) repo, and possibly published in some form in `obs-test-datasets`.

Status: building. The markup format, its checks and the annotation page exist; drafting the pilot documents comes next.

## Contents

| Path | What it holds |
| --- | --- |
| [`guidelines.md`](guidelines.md) | The annotation guidelines, for the drafting model, reviewers and second annotators. |
| [`specification.md`](specification.md) | The dataset specification: task, difficulty levels and tiers, item construction, data format, annotation procedure, scoring, and deliverables. |
| [`docs/markup.md`](docs/markup.md) | The markup format: the working format of annotations, one source document per file, with spans marked in the text. |
| `annotations/` | Annotated documents in the markup format. Created with the first one. |
| [`annotator/annotator.html`](annotator/annotator.html) | The annotation page: a single HTML file with no dependencies (see [Annotation page](#annotation-page)). |
| [`src/named_actor_attribution/`](src/named_actor_attribution/), [`tests/`](tests/) | The `naa` command line, and its tests. |

## Plan

1. **Annotate whole source documents** in the [markup format](docs/markup.md): Claude drafts them, and a DeepSeek model on OpenRouter looks for missed segments (spec §7).
2. **Review in an annotation page:** a self-contained HTML page that opens a markup file, shows the segments highlighted by speaker, and lets a reviewer change boundaries, add segments, assign or rename speakers, and set levels and distractors. The same file can be sent to other annotators, who annotate from scratch and send back the file it saves. No account or server is needed.
3. **Cut items** from the reviewed documents by computed tier, adapting low-tier passages where needed (spec §5.1).
4. **Freeze** the dataset in this repo: validation, the agreement sample, splits, and a version (spec §9–§10).

## Inputs

Corpora of English texts whose license allows redistribution, from `obs-test-datasets`:
- [`global-voices-cheese-181`](https://github.com/echo-observatory/obs-test-datasets/tree/main/global-voices-cheese-181) (CC BY 3.0): mostly blog roundups, rich in block quotes and tweets, so it suits the higher tiers;
- possibly Wikinews, whose news style has more inline quotes ("…,” said X) for the low tiers.

No Retriever data: the dataset is meant to be published.

## Outputs

The deliverables listed in spec §10, mainly `items.jsonl`: one item per line, with its text, speakers, gold segments, difficulty levels and distractors (format in spec §6). Also an evaluator that scores a system's output against the gold (spec §8).

## Known limits

The dataset trades some of the messiness of real text for testability (spec §2, §5):
- items with joint attributions ("Berg and Holm said…") or nested ones ("A said that B told her…") are left out, though they are common in real text;
- each speaker has one canonical name per item, and reconciling actors across documents, social media handles included, is out of scope;
- items with non-English text are left out or adapted;
- some low-tier items are adapted from real text, so they are cleaner than real text.

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

# Check documents: exits 1 if any has an error
uv run naa check annotations/*.xml

# Accept a deliberate change to a document's text
uv run naa rehash annotations/global-voices-cheese-181-483946.xml

# Write documents as JSONL records with offsets
uv run naa export annotations/*.xml --out documents.jsonl

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
- **Annotators** get a copy built with `naa page`, with the documents inside it. Several documents open as a list; "Save all" downloads them as one file, to split with `naa split`.
