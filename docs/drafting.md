# Drafting

How documents get their first annotation, before a human reviews them (spec §7, step 1).

## Who drafts

Claude drafts the documents directly, following [`guidelines.md`](../guidelines.md). Each document records the model in `drafted-by`.

| Documents | Model | Guidelines | Date |
| --- | --- | --- | --- |
| The 6 pilot documents | `claude-opus-5-5` (Claude Opus 5.5, in Claude Code) | v0 | 2026-11-19 |

## Draft format

A draft quotes each span's text instead of giving offsets, so the drafting model never has to count characters or copy the article back. `naa apply` finds each quoted text in the document and inserts the spans; it refuses a text that is missing, or found several times without saying which.

```json
{
  "drafted_by": "claude-opus-5-5",
  "notes": "Optional notes on the document.",
  "speakers": [["S1", "Anna Berg", "person"], ["S2", "Barbados Free Press", "organization"]],
  "spans": [
    ["seg", "S1", "The equipment is ready", {"d": "D1", "r": "R3"}],
    ["seg", "S1", "We only need", {"to": "the permits", "d": "D3", "r": "R3"}],
    ["dis", "unnamed_source", "The lab will reopen in March, officials said."],
    ["exclude", "boilerplate", "Photo by Lise Kanto, CC BY 2.0."]
  ]
}
```

Each span is `[kind, value, text, options]`, where `value` is the speaker id, the distractor type or the exclusion reason. Options, all optional:

- `to`: the span runs from `text` to the end of the first `to` after it, for long spans;
- `n`: which occurrence of `text`, from 1, when it occurs more than once;
- `d`, `r`, `note`: as in the [markup format](markup.md).

```bash
uv run naa apply annotations/global-voices-cheese-181-61589.xml draft.json
```

`apply` replaces the document's speakers and spans, sets `status="drafted"`, then prints the result of `naa check`. Drafts are not kept: the markup file is the record.

## Miss check

A second model, of another family, reads each drafted document and lists what the draft may have missed, and the segments it doubts (spec §7, step 2). Reviewers catch wrong annotations far more easily than missing ones; this step is there for recall.

```bash
uv run naa misscheck annotations/global-voices-cheese-181-61589.xml
```

- The model is DeepSeek V4 Pro on OpenRouter (`deepseek/deepseek-v4-pro-0813`), with reasoning off: with it, DeepSeek's Flash model reasoned until it ran out of tokens. It needs an OpenRouter key in `NAA_API_KEY`, in the environment or in the repo's `.env`.
- The instructions are [`prompts/miss-check.md`](../prompts/miss-check.md), followed by the guidelines.
- Its flags go into the document, in `<flags>`, as the model gave them, and `miss-check-by` records the model. The annotation page lists them: clicking a flag selects its text, ready to make it a span; dismiss it once handled. `naa check` warns about flags left on a reviewed document, and about flags whose quote isn't in the text.
- Expect some noise: on the pilot, the model flagged one or two non-problems per document, and no missed segment.
