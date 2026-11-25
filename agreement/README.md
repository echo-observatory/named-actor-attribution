# Agreement between two annotators

The agreement of spec §7, step 4. On 25 November 2026, a second annotator, Andreas, labelled 80 items from their plain text, with a short codebook: 20% of each tier, at least 5 items, listed in [`agreement.json`](../agreement.json).

| File | Content |
| --- | --- |
| `items.jsonl` | The gold of the 80 items, as it was when they were scored. Credits are in each item's `attribution_line` |
| `second-annotator.xml` | The second annotator's labels, unchanged |

```bash
uv run naa evaluate agreement/items.jsonl agreement/second-annotator.xml
```

## Results

Scored on the first pass, before any adjudication, with the metrics of spec §8. Later corrections to the gold don't change these numbers.

| Tier | Items | Gold segments | Detection F1 | Speaker accuracy | Joint F1 |
| --- | --- | --- | --- | --- | --- |
| T1 | 10 | 10 | 1.00 | 1.00 | 1.00 |
| T2 | 12 | 14 | 0.96 | 1.00 | 0.96 |
| T3 | 7 | 14 | 0.89 | 1.00 | 0.89 |
| T4 | 15 | 30 | 0.95 | 1.00 | 0.95 |
| T5 | 6 | 12 | 0.86 | 0.98 | 0.76 |
| T6 | 5 | 11 | 0.95 | 1.00 | 0.95 |
| T7 | 7 | 11 | 1.00 | 0.91 | 0.90 |

- Speaker accuracy is at least 0.90 in every tier, as spec §7 asks. It counts only text that both annotators marked.
- **T0:** the second annotator marked something in 9 of 18 items, 10 segments in all. In 4 of the 9, they marked an unnamed source as a speaker; the other 5 items were dropped in the adjudication.
- **The samples are small.** By resampling items, the 95% interval is 0.71–1.00 for T5's detection F1, and 0.65–1.00 for T7's speaker accuracy.

## Adjudication

20 items had a disagreement. 11 were settled by the codebook, in favour of the gold. 7 were dropped, as ambiguous or wrong: 2 held a nested attribution to a named actor. 2 turned on the name of the speaker: 1 was renamed as the text has it ("Iranian government"), 1 was kept. A sweep of all the items for the same patterns then dropped 12 more, cut 2 again and renamed 1 speaker. The cut lists give the reason of each dropped item, and the [guidelines](../guidelines.md) the rules decided.
