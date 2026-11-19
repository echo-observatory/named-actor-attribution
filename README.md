# named-actor-attribution

Builds a small, frozen English eval dataset for one task: finding the text segments that express what a named actor said, wrote, believes or intends, and attributing each one to that actor.
The items are graded into 8 difficulty tiers, so that an eval shows where a system starts to fail, not only how well it does overall.
This is the task of Karaage's attribution step.

A side project, not a pipeline component: the dataset will be used later in evals in the [`evals`](https://github.com/echo-observatory/evals) repo, and possibly published in some form in `obs-test-datasets`.

Status: specification only. Nothing is built yet.

## Contents

| Path | What it holds |
| --- | --- |
| [`specification.md`](specification.md) | The dataset specification: task, difficulty levels and tiers, item construction, data format, annotation procedure, scoring, and deliverables. |

## Plan

1. **Source passages** from shareable corpora (see Inputs). Low tiers (T0–T3) may use passages adapted to be simpler (spec §5.1).
2. **Draft** the annotations with a model, then run a second model to look for missed segments (spec §7).
3. **Review in a labelling page:** a small local Python server (standard library only) that serves an HTML page and writes the labels back to the JSONL file. The page shows each item's text with its segments highlighted by speaker. A reviewer can check who speaks, change segment boundaries and speakers, and set the levels and distractors. Reading and editing labels on the rendered text is much easier than editing JSON.
4. **Freeze** the dataset in this repo: tiers computed by script, validation, splits, and a version (spec §9–§10).

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

Nothing to install yet.
