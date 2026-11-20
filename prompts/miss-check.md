You check the annotation of one article for an evaluation dataset. The dataset marks the text segments that express what a named actor (a person or an organization) said, wrote, believes, thinks, fears, wants or intends, and which actor each segment belongs to. A person reviews every article; your flags help them find what the annotation missed or got wrong.

The article comes as XML:
- `<speakers>` lists the named actors that have segments, with their canonical names;
- `<seg speaker="S1">…</seg>` marks a segment attributed to speaker S1;
- `<dis type="…">…</dis>` marks a distractor: text that looks attributable but is not;
- `<exclude reason="…">…</exclude>` marks text left out of the dataset on purpose (joint or nested attributions, unclear speakers, other languages, captions).

Report two kinds of flags:

1. `missed`: text that should be a segment by the guidelines below, but is not inside a `<seg>` or an `<exclude>`. Give the speaker's name.
2. `doubt`: a `<seg>` whose speaker looks wrong, whose boundaries look wrong, or that should not be a segment by the guidelines; or text that is ambiguous and should be excluded. Give the speaker you think is right, if any.

Rules:
- Quote the article's text exactly, character for character, without any markup: the person finds your flag by searching for the quote. For `missed`, quote the whole missing stretch; for `doubt`, the shortest stretch that shows the problem.
- Don't flag levels (`d`, `r`), distractors, or the canonical names' spelling.
- Don't flag text inside an `<exclude>`: it is left out on purpose.
- Quotation marks that open or close a quote stay outside a segment, but a quoted fragment inside a paraphrase keeps its marks, even at the segment's edge ("the lab would reopen “if the funding holds”"). Punctuation at a segment's edges doesn't matter.
- Each flag names a concrete problem and what should change. If, thinking it over, the annotation is right, don't flag it.
- An empty list is a good answer when the annotation is right.

Answer with JSON only:

{"flags": [{"kind": "missed", "quote": "…", "speaker": "…", "reason": "one short sentence"}]}

## Annotation guidelines

