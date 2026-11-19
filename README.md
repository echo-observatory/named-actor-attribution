# named-actor-attribution

Builds a small, frozen English eval dataset for one task: finding the text segments that express what a named actor said, wrote, believes or intends, and attributing each one to that actor.
The items are graded into 8 difficulty tiers, so that an eval shows where a system starts to fail, not only how well it does overall.
This is the task of Karaage's attribution step.

A side project, not a pipeline component: the dataset will be used later in evals in the [`evals`](https://github.com/echo-observatory/evals) repo, and possibly published in some form in `obs-test-datasets`.

Status: building. The markup format and its checks exist; the annotation page comes next.

## Contents

| Path | What it holds |
| --- | --- |
| [`guidelines.md`](guidelines.md) | The annotation guidelines, for the drafting model, reviewers and second annotators. |
| [`specification.md`](specification.md) | The dataset specification: task, difficulty levels and tiers, item construction, data format, annotation procedure, scoring, and deliverables. |
| [`docs/markup.md`](docs/markup.md) | The markup format: the working format of annotations, one source document per file, with spans marked in the text. |
| `annotations/` | Annotated documents in the markup format. Created with the first one. |
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
```
