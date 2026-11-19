# named-actor-claim-attribution-dataset-sourcing

Builds a small, frozen English eval dataset for one task: finding the text segments that express what a named actor said, wrote, believes or intends, and attributing each one to that actor.
The items are graded into 8 difficulty tiers, so that an eval shows where a system starts to fail, not only how well it does overall.
In the pipeline, this is the task of Karaage's attribution step; the dataset is meant for the [`evals`](https://github.com/echo-observatory/evals) repo.
See the [`pipeline`](https://github.com/echo-observatory/pipeline) repo for how the components fit together.

Status: specification only. Nothing is built yet.

## Contents

| Path | What it holds |
| --- | --- |
| [`Specification.md`](Specification.md) | The dataset specification: task, difficulty levels and tiers, item construction, data format, annotation procedure, scoring, and deliverables. |

## Plan

1. **Source passages** from a shareable corpus (see Inputs).
2. **Draft** the annotations with a model, then run a second model to look for missed segments (spec §7).
3. **Review in a labelling page:** a local HTML page that shows each item's text with its segments highlighted by speaker. A reviewer can check who speaks, change segment boundaries and speakers, set the levels and distractors, and save the result. Reading and editing labels on the rendered text is much easier than editing JSON.
4. **Freeze** the dataset: tiers computed by script, validation, splits, and a version (spec §9–§10).

## Inputs

- A corpus of English texts whose license allows redistribution. The first candidate is [`global-voices-cheese-181`](https://github.com/echo-observatory/obs-test-datasets/tree/main/global-voices-cheese-181) from `obs-test-datasets` (CC BY 3.0).
- No Retriever data: the dataset is meant to be published.

## Outputs

The deliverables listed in spec §10, mainly `items.jsonl`: one item per line, with its text, speakers, gold segments, difficulty levels and distractors (format in spec §6). Also an evaluator that scores a system's output against the gold (spec §8).

## Known limits

The dataset trades some of the messiness of real text for testability (spec §2):
- items with joint attributions ("Berg and Holm said…") or nested ones ("A said that B told her…") are left out, though they are common in real text;
- each speaker has one canonical name per item, and reconciling actors across documents is out of scope.

## Setup

Nothing to install yet.
