# Evaluating against the gold

`naa evaluate` scores a system's output by the rules of spec §8.

```bash
uv run naa evaluate items.jsonl predictions.jsonl --split test --out metrics.csv
```

- `items.jsonl`: the gold, from `naa cut --out`.
- `predictions.jsonl`: one JSON object per item, in the format of spec §6. An item without a prediction is scored as an empty one.
- `--split` scores one split; `--only` scores the ids listed in a JSON file, such as `agreement.json`.

It prints, and with `--out` writes as CSV, one row per tier: joint precision, recall and F1 (the headline), detection precision, recall and F1, and speaker accuracy. It also prints T0 false positives, the rate of invalid outputs, recall and speaker accuracy by level, and the distractors hit by type. A score with nothing to measure, such as precision without predictions, is left empty.

Speaker names are compared after removing the titles, roles and degrees listed in [`evaluate.py`](../src/named_actor_attribution/evaluate.py).

## Agreement between two annotators

The same command scores a file saved from the annotation page, which gives the agreement of spec §7:

```bash
uv run naa evaluate items.jsonl second-annotator.xml --only agreement.json
```

It refuses an item whose text has changed since it was annotated. Report the agreement from the second annotator's first pass, before any adjudication: correcting the gold with their labels, then scoring it against them, would overstate it.

## Accepting a dataset

```bash
uv run naa cut cuts/*.json --splits splits.json --corpus … --out items.jsonl
uv run naa validate items.jsonl
```

`naa validate` runs the acceptance checks of spec §10 and exits with 1 if any fails. Two of them need people: that no item holds a nested or joint attribution (it only checks that `nested_checked` is set), and that no speaker's name forms conflict within an item.
