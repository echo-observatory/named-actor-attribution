# Changelog

Versions of the dataset. Any change to the items, the gold or the evaluator makes a new version, and scores are only compared within one (spec §9).

## 1.1.0

The evaluator strips more titles and roles from names before comparing them (spec §8.1), as spec §2 says canonical names do. The items and the gold are unchanged.

- **Added to the list:** "doctor" (the spelled-out form of "Dr"); "psychologist", "sociologist", "environmentalist", "co-founder"; "leader", "expedition leader", "majority leader" and "senate majority leader". All of them stand before a speaker's name in the items' text, e.g. "said Doctor Susanne Sorensen", so a system that keeps them in a name was wrongly scored as naming another actor. Found by the first evaluation of Karaage, where "Doctor Susanne Sorensen" didn't match "Susanne Sorensen".
- **Not stripped:** affiliations and descriptions that aren't titles, such as "Google Co-founder Larry Page" or "Lyndon of Scraps of Moscow". Naming an actor so is still wrong.
- **Scores change** only for systems that put these words before a name. No gold name starts with one, so gold-against-gold and the agreement figures recorded for 1.0.0 are unchanged.
- **Compare scores within one version only:** a system's 1.0.0 and 1.1.0 scores can differ.

## 1.0.0

The first version: 372 items and 497 gold segments, in 8 tiers, from 59 documents.
