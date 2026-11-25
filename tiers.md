# Tiers

The tiers of v1.0: what they ask for, what they hold, and how far two humans agree on them. The definitions are those of the [specification](specification.md) (§3, §4).

## The ladder

An item's tier is the lowest one whose caps it meets on every column. `naa cut` computes it, and `naa validate` fails if a stored tier disagrees.

| Tier | Name | Main added difficulty | Max D | Max R | Speakers | Max words |
| --- | --- | --- | --- | --- | --- | --- |
| T0 | Distractors only | False positives: no gold segment at all | — | — | 0 | 600 |
| T1 | Explicit direct | Baseline | D1 | R1 | 1 | 60 |
| T2 | Explicit indirect | Paraphrase and mixed speech; short name forms | D2 | R2 | 1 | 80 |
| T3 | Several named speakers | Telling explicit speakers apart | D2 | R2 | ≤ 3 | 150 |
| T4 | Local coreference | Pronouns; cue-less continuation segments | D3 | R3 | ≤ 3 | 250 |
| T5 | Beliefs and descriptors | Private states, non-verbal cues; role descriptors | D4 | R4 | ≤ 4 | 350 |
| T6 | Ambiguous or distant reference | Competing compatible candidates; distant antecedents | D4 | R5 | any | 600 |
| T7 | Implicit and discontinuous | No-mention speakers; distant cues; segments crossing paragraphs | D5 | R6 | any | 600 |

**T6 holds two kinds of difficulty:** a reference across a paragraph break, which most of its items have, and competing candidates, which few have.

**T7 holds one of its three difficulties:** segments that cross a paragraph or have no cue nearby. No segment has a speaker without any mention (R6).

## What each tier holds

| Tier | Dev items | Dev segments | Test items | Test segments | Items with a distractor | Adapted items |
| --- | --- | --- | --- | --- | --- | --- |
| T0 | 14 | 0 | 59 | 0 | 73 | 0 |
| T1 | 9 | 10 | 41 | 44 | 7 | 23 |
| T2 | 13 | 17 | 47 | 62 | 19 | 2 |
| T3 | 7 | 12 | 25 | 54 | 11 | 2 |
| T4 | 17 | 28 | 52 | 106 | 15 | 0 |
| T5 | 5 | 9 | 25 | 45 | 13 | 0 |
| T6 | 5 | 13 | 18 | 50 | 8 | 0 |
| T7 | 5 | 7 | 30 | 40 | 18 | 0 |

## Segments by level

| | D1 | D2 | D3 | D4 | D5 | R1 | R2 | R3 | R4 | R5 | R6 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| All | 178 | 180 | 60 | 40 | 39 | 374 | 24 | 51 | 5 | 43 | 0 |
| Test | 143 | 148 | 43 | 35 | 32 | 297 | 18 | 47 | 5 | 34 | 0 |

## Human agreement

Between the gold and a second annotator, on their first pass ([`agreement/`](agreement/)). It is the ceiling of each tier: a system scoring above it is not better than a human there.

| Tier | Items | Gold segments | Detection F1 | Speaker accuracy | Joint F1 |
| --- | --- | --- | --- | --- | --- |
| T1 | 10 | 10 | 1.00 | 1.00 | 1.00 |
| T2 | 12 | 14 | 0.96 | 1.00 | 0.96 |
| T3 | 7 | 14 | 0.89 | 1.00 | 0.89 |
| T4 | 15 | 30 | 0.95 | 1.00 | 0.95 |
| T5 | 6 | 12 | 0.86 | 0.98 | 0.76 |
| T6 | 5 | 11 | 0.95 | 1.00 | 0.95 |
| T7 | 7 | 11 | 1.00 | 0.91 | 0.90 |

T0: the second annotator marked something in 9 of 18 items. Five of those were dropped afterwards. The samples are small: the 95% interval is 0.71–1.00 for T5's detection F1, and 0.65–1.00 for T7's speaker accuracy.

## Detection levels

| Level | Definition | Example (invented; the tagged segment in bold) |
| --- | --- | --- |
| D1 | Direct quote with its own cue (speech or writing verb) in the same sentence | “**The lab reopens in March**,” said Anna Berg. |
| D2 | Indirect or mixed speech with its own speech or writing verb cue in the same sentence | Berg said **the lab would reopen “if the funding holds”**. |
| D3 | Cue in the adjacent sentence, not the same one: a continuation after the actor's cue, or a quote introduced by a lead-in ending in a colon ("Berg writes:"), including a block quote in the next paragraph | “The equipment is ready,” she said. “**We only need permits**.” |
| D4 | Private state or non-verbal cue: belief, fear, intention, "in X's view", "according to X", nominal cue ("his warning that…") | In his view, **permits could take a year**. |
| D5 | No cue in the same or the adjacent sentence (the nearest cue for this actor lies beyond narration or another paragraph), or the segment crosses a paragraph boundary (such as a block quote of several paragraphs) | “Permits are the bottleneck,” Holm said. [narration paragraph] “**Nobody wants to fund paperwork**.” |

## Reference levels

| Level | Definition | Example (invented) |
| --- | --- | --- |
| R1 | Canonical name in the same sentence | …said Anna Berg. |
| R2 | Short form of the canonical name (surname, first name) in the same sentence, unique in the item | …said Berg. |
| R3 | Pronoun whose antecedent is within the previous 2 sentences, in the same paragraph, and is the only compatible candidate | …she said. |
| R4 | Role or title descriptor ("the director", "the agency") within 2 sentences, unambiguous | The director fears the funding will be cut. |
| R5 | Distant antecedent (more than 2 sentences back or in an earlier paragraph), or two or more compatible candidates in the window, resolved by the content. A pronoun cue right after a paragraph break, whose antecedent ends the paragraph before, is distant: R5. For a block quote, the mention is the one in its lead-in. | Berg wants a March reopening; Lise Kanto has doubts. […] She thinks March is unrealistic. |
| R6 | No mention marks the actor as the speaker: the speaker is inferred from discourse structure, such as the answer in an exchange | Berg asked Holm when the lab would reopen. “Not before March.” (Holm is named, but only as the one asked) |
