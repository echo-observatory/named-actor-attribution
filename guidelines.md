# Annotation guidelines

Version 0, 19 November 2026. For everyone who annotates: the drafting model, reviewers, and second annotators.
The rules come from the [specification](specification.md) (§2–§5); when the two disagree, the specification wins, and this file is fixed.
The examples are invented. They will be replaced by 5 examples per tier from the dataset's `dev` split.

## 1. The task

Mark every stretch of text that expresses what a **named actor** said, wrote, believes, thinks, fears, wants or intends, and say which actor it belongs to.
Everything you don't mark means "not attributed to a named actor": narration, the author's own voice, unnamed sources, documents.

Files are in the [markup format](docs/markup.md). You work with three spans and a speaker list:

- `<seg speaker="S1">…</seg>`: an attributed segment;
- `<dis type="…">…</dis>`: a distractor, text a careless system might attribute but shouldn't;
- `<exclude reason="…">…</exclude>`: text that makes a passage unusable;
- `<speaker id="S1" name="Anna Berg" type="person"/>`: one per actor with at least one segment.

**Reviewing a draft:** check every segment (its boundaries and its speaker), every speaker's name, the levels, distractors and exclusions. Then read the text once more, looking only for what the draft missed: missed segments are the error that is hardest to see. Set `status="reviewed"` and `annotator` when done.

**Annotating from scratch** (second annotators): you get short passages without any annotation. Mark segments and speakers only; levels, distractors and exclusions are not needed.

## 2. What is a segment

Mark:

- **direct quotes**: “`<seg>`The lab reopens in March`</seg>`,” said Anna Berg.
- **indirect speech**: Berg said `<seg>`the lab would reopen in March`</seg>`.
- **mixed speech**, a paraphrase with quoted fragments: Berg said `<seg>`the lab would reopen “if the funding holds”`</seg>`.
- **private states whose content is a clause**: In her view, `<seg>`the permits could take a year`</seg>`. Holm fears `<seg>`the funding will be cut again`</seg>`. Berg wants `<seg>`the lab to reopen in March`</seg>`.
- **writing and posting**: a blog post, a tweet, a letter, a statement by an organization.

Don't mark:

- a private state with a bare noun phrase: "Holm fears further cuts", "Berg wants reform";
- reported questions and refusals: "Berg asked whether the date would hold", "Berg declined to comment" (mark them as distractors, `non_statement`);
- negated speech: "Holm did not say when the lab would reopen" (`negated_speech`);
- titles of works, and scare quotes with no speaker (`quoted_title_or_scare_quote`);
- what unnamed people, groups or documents say: "officials said", "a report found" (`unnamed_source`, `document_source`);
- the author's own voice, including "I" and "we" of the article's author (`author_voice`).

Inside a quote, keep the whole run, questions included: in “Why fund paperwork? Nobody wants to,” the whole quote is one segment.

## 3. Boundaries

- **Content only.** The speaker mention and the cue ("said", "according to", "writes:") stay outside.
- **Quotation marks** that open or close the quote stay outside; quotation marks inside it (the fragments of mixed speech) stay in.
- **One segment per maximal run.** If the same actor's text continues and only the cue interrupts it, that makes two segments: “`<seg>`The equipment is ready`</seg>`,” she said, “`<seg>`and we only need permits`</seg>`.” If only whitespace or punctuation separates two pieces of the same actor's text, merge them into one segment.
- **A block quote of several paragraphs** is one segment, paragraph breaks included.
- **Punctuation at the edges** doesn't matter: the scoring trims it. Don't spend time on it.
- **Don't split by sentence or by claim.** The unit is the run of text, not the claim.

## 4. Speakers and their names

Every speaker gets one **canonical name**: the fullest proper name the document gives for that actor.

- **Persons:** given name(s) and family name, with middle names or initials when the document gives them ("Anna K. Berg"). Leave out titles, honorifics, roles and degrees (Dr, Prof., Senator, PhD); keep Jr. and III. Leave out nicknames in quotes or brackets ("Robert ‘Bob’ Smith" → "Robert Smith"). If the document gives only one name (a surname, a first name), that name is canonical.
- **Organizations**, blogs and publications included: the full name as given, without a leading "the" ("European Space Agency", not "ESA"). If the document gives only an acronym, use the acronym.
- **Social media accounts:** the display name, as written, when it looks like a person's full name ("Ivan Kolpakov" for "Ivan Kolpakov (@kolpakov)"). An account known only by a handle or a username has no canonical name: mark its text `<exclude reason="unresolved">`.
- The canonical name must appear in the text (apart from a nickname inside it). The text itself may use any other form: short names, descriptors, pronouns.
- If two speakers could be confused ("Berg" for two different people), or one actor's name forms conflict ("Bob Smith" and "Robert Smith"), note it in `<notes>`: those passages will be left out.

`type` is `person` or `organization`.

## 5. Distractors

Mark the clearest distractors, one span each, with their type. They don't need to be exhaustive: unmarked text is "not attributed" anyway.

| Type | Example |
| --- | --- |
| `named_no_attribution` | Anna Berg met the minister on Tuesday. |
| `unnamed_source` | The lab will reopen in March, officials said. |
| `document_source` | A 2025 report found the coating cuts losses by a third. |
| `author_voice` | The decision is a worrying sign for open science. |
| `non_statement` | Berg declined to comment. / Berg asked whether the date would hold. |
| `negated_speech` | Holm did not say when the lab would reopen. |
| `quoted_title_or_scare_quote` | The so-called “fast track” has stalled. |

## 6. Exclusions

Mark with `<exclude reason="…">` the text that would make any passage containing it unusable. Mark the smallest stretch that covers the problem, usually a sentence or a quote.

| Reason | Text |
| --- | --- |
| `joint` | Attributed to several actors at once: "Berg and Holm said…", "the agency and its partners argue…" |
| `nested` | An attribution inside another: "Berg said that Holm told her…", "according to Berg, Holm believes…", a quote inside a quote |
| `unresolved` | You can't tell who says it, or the actor has no canonical name (a handle only) |
| `non-english` | A sentence or quote in another language. Single foreign words inside English sentences are fine |
| `boilerplate` | Captions, photo credits, editorial notes ("[All links lead to Spanish-language pages.]"), headlines |

## 7. Levels (reviewers and the drafting model)

Each segment gets two levels: how hard it is to **detect** (`d`) and how hard it is to tell **who** says it (`r`). When several levels apply, use the highest.

| `d` | When |
| --- | --- |
| D1 | Direct quote with its own speech or writing verb in the same sentence |
| D2 | Indirect or mixed speech with its own speech or writing verb in the same sentence |
| D3 | The cue is in the adjacent sentence: a continuation after the cue, or a quote after a lead-in ending in a colon ("Berg writes:"), block quotes included |
| D4 | Private state or non-verbal cue: "believes", "fears", "in her view", "according to", "his warning that…" |
| D5 | No cue in the same or adjacent sentence, or the segment crosses a paragraph break |

| `r` | The mention that identifies the speaker (attached to the cue, or the nearest one) |
| --- | --- |
| R1 | The canonical name, in the same sentence |
| R2 | A short form of the name (surname, first name), in the same sentence |
| R3 | A pronoun whose antecedent is within the 2 previous sentences, with no other candidate |
| R4 | A role or descriptor ("the director", "the agency") within 2 sentences, unambiguous |
| R5 | An antecedent further back, or several candidates that fit, resolved by the content |
| R6 | No mention marks the actor as the speaker: inferred from the discourse, such as the answer in an exchange |

Levels are set on the whole document, and checked again on each passage cut from it.

## 8. Global Voices articles

Most articles of the first corpus are blog roundups, with their own habits:

- **Lead-in and block quote:** "Nora describes it as follows:" then one or more paragraphs quoted from her blog, without quotation marks (the original page had a block quote, which the plain text has lost). The quoted paragraphs are one segment: D3 for a single paragraph, D5 for several. Decide where the quote ends from the content: the author's voice usually comes back with a sentence about the blogger ("Before sharing the recipe, the blogger talked about…"). If you can't tell, add a `note` to the segment.
- **Tweets:** the tweet's text, then a signature line "— Name (@handle) date", then often an English translation. The original in another language: `<exclude reason="non-english">`. The translation: a segment of the tweet's author. The signature line is not part of the segment. Editorial insertions in brackets inside a quote ("[jellybeanMelih]") stay inside the segment.
- **Blogs as speakers:** "Barbados Free Press writes:" makes the blog the speaker, as an organization. When the text names the person behind the blog and attributes the post to them, the person is the speaker.
- **Captions and credits** ("Photo by …", "Image via …", "Screenshot from …"): `boilerplate`.

## 9. Examples, one per tier

The tier of a passage is computed from its levels, its speakers and its length (spec §4); you never set it. These examples show what each tier looks like, with speaker ids replaced by names for reading.

- **T0**, no segment: `<dis type="named_no_attribution">`Anna Berg met the minister on Tuesday.`</dis>` `<dis type="unnamed_source">`The lab will reopen in March, officials said.`</dis>`
- **T1**: “`<seg speaker="Anna Berg" d="D1" r="R1">`We will reopen the lab in March`</seg>`,” said Anna Berg.
- **T2**: Berg said `<seg speaker="Anna Berg" d="D2" r="R2">`the lab would reopen in March, “if the funding holds”`</seg>`. (Anna Berg is named in full elsewhere in the passage.)
- **T3**: Anna Berg said `<seg speaker="Anna Berg" d="D2" r="R1">`the lab would reopen in March`</seg>`. Tomas Holm, the university's director, said `<seg speaker="Tomas Holm" d="D2" r="R1">`no date had been set`</seg>`.
- **T4**: Anna Berg, who leads the lab, was upbeat. “`<seg speaker="Anna Berg" d="D1" r="R3">`The equipment is ready`</seg>`,” she said. “`<seg speaker="Anna Berg" d="D3" r="R3">`We only need the permits`</seg>`.”
- **T5**: Tomas Holm, the university's director, is less confident. In his view, `<seg speaker="Tomas Holm" d="D4" r="R3">`the permits could take a year`</seg>`. The director fears `<seg speaker="Tomas Holm" d="D4" r="R4">`the funding will be cut again`</seg>`.
- **T6**: Anna Berg wants `<seg speaker="Anna Berg" d="D4" r="R1">`the lab to reopen in March`</seg>`, but her deputy, Lise Kanto, has doubts. [two sentences on the budget] She thinks `<seg speaker="Lise Kanto" d="D4" r="R5">`March is unrealistic`</seg>`.
- **T7**: “`<seg speaker="Tomas Holm" d="D1" r="R1">`Permits are the bottleneck`</seg>`,” Tomas Holm said. [a paragraph on the budget] “`<seg speaker="Tomas Holm" d="D5" r="R5">`Nobody wants to fund paperwork`</seg>`.” Anna Berg asked Holm when the lab would reopen. “`<seg speaker="Tomas Holm" d="D5" r="R6">`Not before March`</seg>`.”

## 10. When in doubt

- Add a `note` to the span, or write in `<notes>`, rather than guessing silently.
- If a careful reader can't settle it, it's probably an `<exclude reason="unresolved">`.
- Run `uv run naa check` on the file: it catches broken markup, a changed text, unknown speakers and segments that should be merged.
