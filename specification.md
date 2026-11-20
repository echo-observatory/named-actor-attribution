# Spec: tiered eval dataset for attributing text segments to named actors

19 November 2026 · Mathieu Jacomy

## 1. Purpose

Build a small, frozen English eval dataset that tracks whether an AI system gets better or worse, version to version, at one task: finding the text segments that express what a named actor said, wrote, believes or intends, and attributing each segment to that actor. The dataset is split into **8 difficulty tiers (T0–T7)** so a report can tell apart a system that is weak everywhere from one that is good on easy cases and bad on hard ones.

The dataset is **not** for training, for large-scale benchmarking, or for evaluating alias detection. Sourcing the texts is out of scope of this spec; any source works if it meets §5 and the license rule in §6.

The tiers form a **cumulative ladder**: each tier allows everything the tier below allows, plus one main added difficulty. A score drop between tier N and tier N+1 therefore points to the difficulty added at N+1. The ladder does not triangulate every combination of difficulties, and the top tiers deliberately stack several; this is accepted and documented.

The headline output of an evaluation run is a **difficulty curve**: one joint score per tier (§8).

## 2. Task definition

**Input:** the plain text of one item (a passage of English prose, no markup, no headline; paragraphs separated by a blank line), and task instructions that state this definition and the canonical-name rule below, so the system knows to name each speaker by the fullest name the item gives. **Output:** a list of **non-overlapping character segments** `[start, end)`, each attributed to **exactly one** named actor by canonical name (rule below). Every character outside a segment carries the **default label: not attributed to a named actor**. The default covers narration, the author's own voice, unnamed sources and documents alike; it does not mean "claimed by the author".

**The unit is the attributed segment, not the claim.** The labelling has two levels only: text segments, and the actor each is attributed to. There is **no claim level in between**: the dataset does not assume that claims are distinct and countable, and nothing in it groups segments into claims. ("Claim" may be used informally in explanations; it has no role in the data or the scoring.)

An **attributed segment** is text expressing what a named actor said, wrote, believes, thinks, fears, wants or intends: direct quotes, indirect speech, mixed speech (paraphrase with quoted fragments) and private states ("in her view", "he fears that…"). A private state counts only when its content is a clause ("fears that the funding will be cut", "wants the lab to reopen"); a bare noun phrase ("fears further cuts", "wants reform") is not a segment.

- **Content only:** a segment never includes the speaker mention or the cue ("said", "according to"). Quotation marks that open or close a segment are excluded, like the cue; quotation marks inside it (the quoted fragments of mixed speech) stay.
- **Segmentation rule (gold):** a gold segment is a **maximal run** of text attributed to one actor. A paragraph break ends a run, unless the same quote continues across it (a block quote of several paragraphs). Gold segmentation should be deterministic; systems may segment differently, and scoring tolerates it (§8).
- **Not attributed:** reported questions, refusals and non-statements ("Berg declined to comment", "Berg asked whether…"); negated speech ("Berg did not say…"); titles of works; scare quotes with no speaker. A question inside a quote stays in the quote's segment: the run of quoted text is not split.

**Named actors in scope:** named persons and named organizations ("Anna Berg", "the European Space Agency"). Named blogs, publications and outlets ("Barbados Free Press") count as organizations. Out of scope, and used as distractors (§5.3): unnamed people and groups ("officials", "researchers"), documents and studies ("a report found"), and the article's author.

**One actor per segment.** Because each segment belongs to exactly one actor and segments cannot overlap, this dataset excludes (§5.2) **joint attributions to several actors** ("Berg and Holm said…", "the agency and its partners argue…") and nested attributions. Joint attributions are common in real text; they are left out here only because they are harder to score, and this limit must be stated in the README.

**Canonical-name rule.** Every speaker in an item has exactly one canonical name: its **normal name**, the form that would best identify the same actor across documents. In practice, this is the fullest proper name used for the actor in the item.

- **Persons:** given name(s) and family name, including middle names or initials when the item gives them ("Anna K. Berg"). Strip titles, honorifics, roles and degrees (Dr, Prof., Senator, PhD); keep generational suffixes (Jr., III). Drop nicknames given in quotes or brackets ("Robert ‘Bob’ Smith" → "Robert Smith"). If the item gives only one name for a person (a surname, a first name), that name is canonical.
- **Organizations** (blogs and publications included): the full name as given in the item, without a leading "the" ("European Space Agency", not "ESA"). If the item gives only an acronym or short form, that form is canonical.
- **Social media accounts:** the account's display name, as written, when it looks like a person's full name ("Ivan Kolpakov" for "Ivan Kolpakov (@kolpakov)"). A handle is an alias, not a canonical name: an account known only by a handle or a username that is not a full name ("A.S.T. (@All_Sin_Che)") has no canonical name, so its item is excluded (§5.2). Linking handles to actors is left to actor reconciliation, out of scope here.
- The canonical name must appear verbatim in the item, or with only a stripped nickname inside it ("Robert ‘Bob’ Smith" for "Robert Smith"). Stripped titles and a leading "the" sit outside the name, so they don't affect this. An actor never named in the item is not a named actor for that item.
- Canonical names are unique and not confusable within an item: two speakers called "Berg" → item excluded. The speaker test is on the canonical name only (§8.1), so each speaker needs one clear canonical name: if an item's name forms for one actor conflict ("Bob Smith" and "Robert Smith", or two different long forms), the item is excluded. The text itself may and should use other forms: short names, descriptors, pronouns.
- **Out of scope:** reconciling actors across documents (e.g. a middle name given in one article and not in another) and scoring alias lists. Real-world text is messier than this dataset; the dataset trades some messiness for testability, and its limits should be stated in the README.

## 3. Difficulty features (tagged per gold segment)

Every gold segment is tagged on two axes, by the drafting model on each item after cutting (§7): how hard it is to **detect** the segment, and how hard it is to **resolve its speaker**. Each axis is ordered easy → hard; a segment gets the highest level that applies. Item-level tiers (§4) are derived from these tags.

**Detection level (D)**

| Level | Definition | Example (invented; the tagged segment in bold) |
| --- | --- | --- |
| D1 | Direct quote with its own cue (speech or writing verb) in the same sentence | “**The lab reopens in March**,” said Anna Berg. |
| D2 | Indirect or mixed speech with its own speech or writing verb cue in the same sentence | Berg said **the lab would reopen “if the funding holds”**. |
| D3 | Cue in the adjacent sentence, not the same one: a continuation after the actor's cue, or a quote introduced by a lead-in ending in a colon ("Berg writes:"), including a block quote in the next paragraph | “The equipment is ready,” she said. “**We only need permits**.” |
| D4 | Private state or non-verbal cue: belief, fear, intention, "in X's view", "according to X", nominal cue ("his warning that…") | In his view, **permits could take a year**. |
| D5 | No cue in the same or the adjacent sentence (the nearest cue for this actor lies beyond narration or another paragraph), or the segment crosses a paragraph boundary (such as a block quote of several paragraphs) | “Permits are the bottleneck,” Holm said. [narration paragraph] “**Nobody wants to fund paperwork**.” |

**Speaker reference level (R)**, judged per segment: the mention attached to its cue, or, for a segment without a cue, the nearest mention that identifies its speaker.

| Level | Definition | Example (invented) |
| --- | --- | --- |
| R1 | Canonical name in the same sentence | …said Anna Berg. |
| R2 | Short form of the canonical name (surname, first name) in the same sentence, unique in the item | …said Berg. |
| R3 | Pronoun whose antecedent is within the previous 2 sentences and is the only compatible candidate | …she said. |
| R4 | Role or title descriptor ("the director", "the agency") within 2 sentences, unambiguous | The director fears the funding will be cut. |
| R5 | Distant antecedent (more than 2 sentences back or in an earlier paragraph), or two or more compatible candidates in the window, resolved by the content | Berg wants a March reopening; Lise Kanto has doubts. […] She thinks March is unrealistic. |
| R6 | No mention marks the actor as the speaker: the speaker is inferred from discourse structure, such as the answer in an exchange | Berg asked Holm when the lab would reopen. “Not before March.” (Holm is named, but only as the one asked) |

**Item-level features**, recorded per item: number of distinct speakers, word count, number of distractors (§5.3).

## 4. Tier ladder

An item's tier is the **lowest tier whose caps it meets on every column**. So a T4 item breaks at least one T3 cap. Caps apply to all gold segments in the item; distractors do not count toward D or R.

An item can land in a tier for a reason other than the tier's main added difficulty, for instance a D1/R1 item of 70 words in T2. To keep the ladder readable, **at least half of the items of each tier T2–T7 must break a cap of the tier below in a column of its main added difficulty**: D or R for T2 and T4–T7, speakers for T3. The script that computes tiers also reports which caps each item breaks.

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

T0 items must contain at least one distractor (§5.3). T1–T7 items must contain at least one gold segment.

**Prototypes.** The dataset documentation must give **5 prototypical examples per tier**, taken from the dataset's `dev` split, each shown as plain text and then as inline annotation. Until enough dev items are reviewed, the guidelines use invented examples instead. One invented illustration per tier, in the inline notation used throughout (`<seg speaker="…">`):

- **T0:** Anna Berg met the minister on Tuesday. The lab will reopen in March, officials said. → no gold segment; "officials" is unnamed.
- **T1:** “`<seg speaker="Anna Berg">`We will reopen the lab in March`</seg>`,” said Anna Berg.
- **T2:** Berg said `<seg speaker="Anna Berg">`the lab would reopen in March, “if the funding holds”`</seg>`. (the item names Anna Berg in full elsewhere)
- **T3:** Anna Berg said `<seg speaker="Anna Berg">`the lab would reopen in March`</seg>`. Tomas Holm, the university's director, said `<seg speaker="Tomas Holm">`no date had been set`</seg>`.
- **T4:** Anna Berg, who leads the lab, was upbeat. “`<seg speaker="Anna Berg">`The equipment is ready`</seg>`,” she said. “`<seg speaker="Anna Berg">`We only need the permits`</seg>`.” (two segments, split by the cue; the second has no cue of its own: D3)
- **T5:** Tomas Holm, the university's director, is less confident. In his view, `<seg speaker="Tomas Holm">`the permits could take a year`</seg>`. The director fears `<seg speaker="Tomas Holm">`the funding will be cut again`</seg>`. (private states: D4; a pronoun, then a descriptor: R3, R4)
- **T6:** Anna Berg wants `<seg speaker="Anna Berg">`the lab to reopen in March`</seg>`, but her deputy, Lise Kanto, has doubts. [two sentences on the budget] She thinks `<seg speaker="Lise Kanto">`March is unrealistic`</seg>`. (two compatible candidates, more than 2 sentences back: R5; the content resolves it, since Berg wants March. If nothing resolves it, the item is excluded, §5.2)
- **T7:** “`<seg speaker="Tomas Holm">`Permits are the bottleneck`</seg>`,” Tomas Holm said. [a paragraph on the budget] “`<seg speaker="Tomas Holm">`Nobody wants to fund paperwork`</seg>`.” (the second segment has no cue and a distant mention: D5, R5) Anna Berg asked Holm when the lab would reopen. “`<seg speaker="Tomas Holm">`Not before March`</seg>`.” (the answer in an exchange: R6)

## 5. Item construction

### 5.1 Units

- An item is a contiguous passage of **real English prose** (news by default), made of whole sentences, and from T3 up of whole paragraphs. Remove headlines, bylines, captions, photo credits, editorial notes and boilerplate.
- Do **not** trim the text around attributed segments to make an item cleaner. Ordinary narration is kept, because it carries the false-positive traps.
- **Adapted items.** Where unedited passages are too scarce for a low tier, an item in **T0–T3** may be adapted from real text to make it simpler: drop sentences or clauses, replace a pronoun or descriptor with the actor's name, or rewrite a lead-in and its block quote as an inline quote with its cue. Edits are minimal, keep the source's wording elsewhere, and never add content attributed to an actor. Items in T4–T7 are not adapted, except to remove non-English text (§5.2). An adapted item has `source.adapted` set to true and a one-line `source.adaptation` note, and its `attribution_line` says the text was adapted. Its tier is computed from the adapted text.
- Annotate **every** stretch of text attributable to a named actor in the item (exhaustive annotation). Precision is meaningless otherwise.
- Record the source document, the passage's character offset in it, and the text license.

### 5.2 Exclusions (drop the whole item)

- **Nested** or joint attributions anywhere in the item (joint = text attributed to several actors at once, "Berg and Holm said…", §2): "A said that B told her…", "according to A, B believes…", a quote inside a quote.
- A segment whose speaker cannot be resolved by a careful human reader from the item alone, or whose antecedent lies outside the item.
- More generally, any doubt the review can't settle, about a speaker, a segment's boundaries or whether text is attributed at all: the dataset keeps only unambiguous attributions, and ambiguous text is excluded rather than decided (guidelines, Principles).
- Two speakers with confusable names (§2), or a speaker without a canonical name in the item who would otherwise be a gold speaker.
- Gold disagreements that adjudication cannot settle (§7).
- Non-English text: a sentence or quote in another language, such as the original of a translated tweet. Single foreign words and names inside English sentences are fine. The item may instead be adapted to remove the non-English text (§5.1).

### 5.3 Distractors

A distractor is text that a careless system might attribute to a named actor, but that is not one. Each distractor is recorded with its type:

| Type | Example (invented) |
| --- | --- |
| `named_no_attribution` | Anna Berg met the minister on Tuesday. |
| `unnamed_source` | The lab will reopen in March, officials said. |
| `document_source` | A 2025 report found the coating cuts losses by a third. |
| `author_voice` | The decision is a worrying sign for open science. |
| `non_statement` | Berg declined to comment. / Berg asked whether the date would hold. |
| `negated_speech` | Holm did not say when the lab would reopen. |
| `quoted_title_or_scare_quote` | The so-called “fast track” has stalled. |

T0 items contain only distractors. In T1–T7, **at least 30% of items** contain at least one distractor, spread across the types.

Distractors need not be exhaustive: all text outside gold segments already carries the default label, and precision counts every false positive wherever it falls. Annotators record the clearest distractors, so that the hit rate can be broken down by type.

## 6. Data format

One JSON object per item, one item per line (`items.jsonl`). Character offsets are 0-based, end-exclusive, relative to `text`, and counted in Unicode code points (not UTF-16 code units, not bytes), as in Karaage. `text` is stored as it is, without Unicode normalization, and offsets point into it as stored. Paragraphs are separated by a blank line (`\n\n`). Gold segments never overlap and follow the segmentation rule of §2.

**Gold item**

```json
{
  "item_id": "t4-0012",
  "tier": "T4",
  "split": "dev",
  "text": "Anna Berg, who leads the lab, was upbeat. “The equipment is ready,” she said. “We only need the permits.”",
  "word_count": 19,
  "source": {"url": "https://…", "title": "…", "publisher": "…", "date": "2026-03-02", "start_offset": 1840, "adapted": false, "adaptation": null, "license": "CC BY 4.0", "attribution_line": "…"},
  "speakers": [
    {"speaker_id": "S1", "canonical_name": "Anna Berg", "type": "person"}
  ],
  "segments": [
    {"segment_id": "G1", "speaker_id": "S1", "start": 43, "end": 65, "text": "The equipment is ready",
     "detection_level": "D1", "reference_level": "R3"},
    {"segment_id": "G2", "speaker_id": "S1", "start": 79, "end": 103, "text": "We only need the permits",
     "detection_level": "D3", "reference_level": "R3"}
  ],
  "distractors": [],
  "annotation": {"drafted_by": "<model + version>", "miss_check_by": "<model + version>", "reviewed_by": "<human>", "second_annotator": null, "nested_checked": true, "notes": ""}
}
```

Field rules:

- `type` is `person` or `organization`. Per segment, the released item records only its boundaries, its speaker and its two levels. Cues and name mentions guide the annotators and the levels and are not part of the released item, but the working annotations may keep their spans (§7).
- `distractors` entries: `{"type": "<§5.3 type>", "spans": [[s, e]], "note": "…"}`.
- `source.license`: use texts whose license allows redistribution of the dataset (CC BY, CC0 or public domain), and fill `attribution_line` as the license requires.

**System output** (what the system under test must return per item; the system sees `text` and the task instructions of §2, nothing else from the item):

The system returns segments of the same kind as the gold segments, without the tags; scoring compares the two lists directly.

```json
{
  "item_id": "t4-0012",
  "segments": [
    {"start": 43, "end": 65, "speaker": "Anna Berg"},
    {"start": 79, "end": 103, "speaker": "Anna Berg"}
  ]
}
```

Segments are non-overlapping character ranges `[start, end)` into `text`, each with exactly one speaker string. Characters outside all segments carry the default label (not attributed to a named actor). Output with overlapping segments or offsets outside `text` is invalid (§8.1).

## 7. Annotation procedure and quality control

Gold is drafted by a model and fully reviewed by a human. Four steps, in order:

1. **Draft.** A strong model annotates speakers, segments, levels and distractors, following §2–§5. Record model and version. The gold is frozen while the systems under test change, so it can't always come from another family than theirs: the dataset card names the families used for the gold, and reports flag scores of systems from those families, since the gold may share their blind spots.
2. **Miss check.** A second model, from another family than the drafting model, reads the text and the draft and lists attributed text the draft missed, and drafts it doubts. Every flag goes to the reviewer. Reviewers catch wrong annotations far more easily than missing ones; this step exists for recall.
3. **Human review.** One reviewer checks every item in full: segments and their boundaries, speakers, canonical names, distractors, exclusions. Levels are not reviewed: they only decide the tier, and the drafting model sets them on each item after cutting. Before the full batch, time the review on 2 items per tier to plan effort.
4. **Agreement sample.** A second human independently annotates **20% of items per tier** (at least 5 items) from the plain text. Report per tier: segment detection F1 and speaker agreement, computed with the §8 metrics between the two humans. Disagreements are adjudicated; items that stay ambiguous are dropped (§5.2).

The per-tier human agreement is the **ceiling** for that tier. If the speaker accuracy (§8.2) between the two humans is below 0.90 in a tier, revise that tier's items or definitions before freezing; a model score above the human ceiling there is not meaningful.

The tier of each item is computed by script from the reviewed tags (§4), never assigned by hand. Write the annotation guidelines as a separate document (definition of attributed segments, segmentation and boundary rules, levels, distractor types, exclusions, with the 5 prototypes per tier) and give it to both drafting models and to humans.

**Recommended order:** an item's tier is only known once it is annotated, so annotate whole source documents once (draft, miss check, review), then cut items from them by computed tier, and check the levels of each item again after cutting, since distances to cues and mentions change. Working annotations may keep cue and mention spans for this: a script can then recompute most levels, and the labelling page can show which cue goes with which segment.

## 8. Evaluation

The headline numbers are **segment-level joint F1 and joint precision per tier**: a segment counts only if it is found and given the right speaker. Precision is a co-headline because false attribution is the main risk. Detection-only scores are reported beside them to show where errors come from.

### 8.1 Preparation (per item)

1. **Gold segments** = the item's gold segments (§6), each with its speaker. **Predicted segments** = the system output.
2. **Boundary trimming:** strip leading and trailing whitespace and punctuation (quotation marks included) from every gold and predicted segment; drop segments left empty. Punctuation inside a segment is kept and counts normally.
3. **Speaker check:** a predicted speaker string is right if, once normalized, it equals the normalized canonical name of the gold speaker. Normalization lowercases, collapses whitespace, and removes a leading "the" and the titles, honorifics, roles and degrees that §2 strips (Dr, Mr, Ms, Prof, Senator, PhD…), from one fixed list in `evaluate.py`. Any other form (short form, variant, pronoun, descriptor) is wrong. "Mapped to a speaker" below means passing this check.
4. **Invalid output** (overlapping segments, offsets outside `text`): the item is scored as an empty prediction and counted in the invalid-output rate.

### 8.2 Metrics (per tier, pooled over the tier's items)

| Metric | Definition |
| --- | --- |
| **Segment joint P / R / F1** (headline) | R: a gold segment is found if ≥ 50% of its characters are covered by predicted segments mapped to its speaker. P: a predicted segment is correct if ≥ 50% of its characters lie in gold segments of the speaker it maps to. |
| Segment detection P / R / F1 | As above, speakers ignored |
| Speaker accuracy | Among characters inside both a predicted and a gold segment, the share whose mapped speaker is the gold speaker |
| T0 false positives | Predicted segments per T0 item; share of T0 items with none |
| Distractor hit rate | Share of distractors with ≥ 50% of their characters covered by predicted segments, by distractor type, all tiers |
| Invalid-output rate | Share of items whose output is invalid |

Segment metrics count each segment equally, so a long quote does not outweigh a short one.

Diagnostic slices, for segment recall and speaker accuracy only (they have no precision): by detection level D1–D5 and by reference level R1–R6, across all tiers. Levels are those tagged on each gold segment (§3).

### 8.3 Running evaluations (recommendations, not binding)

The dataset fixes the output format, the scoring rules (§8.1) and the metrics (§8.2). How runs are organised and reported is up to the user. Two recommendations: report results as a difficulty curve (segment joint F1 and joint precision per tier, T1–T7, one line per system version, with T0 false positives shown separately), since that profile is what the dataset is designed to show; and because LLM-based systems vary between runs, compare versions over a few runs rather than one.

## 9. Size, splits, versioning

Target per tier: **test ≥ 40 gold segments and ≥ 8 items; dev ≥ 20 gold segments and ≥ 5 items** (5, so that the prototypes can come from dev). For T0: test ≥ 20 items, dev ≥ 10. With 40 independent segments, a tier score near 80% would have a 95% interval of roughly ±12 points. Segments of the same item are correlated, so the real interval is wider: compute it by bootstrap over items. That is enough to see large shifts, not small ones. Add items to a tier if finer tracking is needed.

This gives about 150–200 items and 400–500 gold segments in total; low tiers need many short items, high tiers few long ones.

- **Splits:** `dev` is used freely during development; `test` is run only at milestones and never inspected item by item. Assign items to splits at random, stratified by tier, before anyone runs a system on them. Keep items from the same source document in the same split.
- **Versioning:** the dataset is frozen per version (`v1.0`, `v1.1`…). Any change to items, gold or the evaluator bumps the version and is logged in a changelog. Scores are only compared within a dataset version.
- **Prototypes:** the 5 documentation prototypes per tier come from `dev`, never from `test`.

## 10. Deliverables and acceptance checklist

| Deliverable | Content |
| --- | --- |
| `items.jsonl` | All items in the gold format (§6), with `tier` and `split` |
| `guidelines.md` | Annotation guidelines (§7), with 5 prototypes per tier from `dev` |
| `tiers.md` | The tier table (§4) and level definitions (§3), with per-tier counts and human agreement |
| `assign_tiers.py` | Computes D/R-derived tiers from tags, and which caps of the tier below each item breaks; fails if a stored tier disagrees |
| `validate.py` | Runs every check below |
| `evaluate.py` | Implements §8: input = gold + system output files; output = metrics table per tier (CSV) |
| `prompts/` | Drafting and miss-check prompts, with model names and versions |
| `README.md` + `CHANGELOG.md` | Dataset card (sources, licenses, attribution lines, procedure, known limits) and version log |

The dataset is accepted when `validate.py` passes all of these:

- [ ] Every segment's offsets reproduce its `text` exactly; gold segments do not overlap and are maximal runs (§2): no two same-speaker gold segments are separated only by whitespace and punctuation; no segment is empty after boundary trimming (§8.1).
- [ ] Every speaker's `canonical_name` occurs in `text`, verbatim or with only a quoted or bracketed nickname inside it (§2); no two speakers have the same canonical name after normalization, and no speaker's name forms in the item conflict (§2).
- [ ] Every gold segment has a D and R level; every item's stored tier equals the computed tier; word counts respect the tier caps; in each tier T2–T7, at least half of the items break the tier below on its main added difficulty (§4).
- [ ] No item contains a nested or joint attribution (`annotation.nested_checked` is true on every item).
- [ ] Per-tier and per-split minimums of §9 are met; ≥ 30% of T1–T7 items have a distractor; all distractor types occur.
- [ ] Every item has a license allowing redistribution and an attribution line.
- [ ] Every item has `reviewed_by` filled; the agreement sample exists for every tier and its results are in `tiers.md`.
- [ ] `evaluate.py` scores the gold against itself at 1.0 on every metric, and an empty prediction file at 0 recall.
- [ ] Dev and test share no source document.
