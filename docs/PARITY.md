# Roast-room parity acceptance

Tracked in [issue #7](https://github.com/scwlkr/dev-den/issues/7). Starting implementation: `920dc50`. This checklist records verified behavior, not merely the existence of commands or green baseline tests. Upstream reference: `nateherkai/roast-room`, its council skill, scoring protocol, advisor-building skill and browser room.

## Required implementation

- [x] Normal, consult, quick (both ratification branches), selected and all modes complete through saved verdict and report.
- [x] Review mode survives provider execution and restart; existing accepted sessions retain their historical contents.
- [x] Quick escalation uses disagreement between advisors on the same option, plus material risk, rather than differences between option averages.
- [x] Saved default boards and ask/auto/default policy affect actual selection; explicit participants take precedence. Participant limits are explicit.
- [x] Weighted option fit, spread, council confidence and draft-resolution support are computed from accepted contributions.
- [x] Material risk cannot be averaged away; mitigation requires the relevant advisor's endorsement. Divided irreversible decisions require a test precondition.
- [x] Early unanimity triggers evaluation of the strongest neglected alternative without inventing disagreement.
- [x] Source-linked working context, frameworks, principles, positions, cases and voice inform advisor packets, with documented/inferred status preserved.
- [x] Retrieval covers the prepared corpus and can refine evidence for competing arguments without collecting new developer sources during reviews.
- [x] An advisor-building workflow discovers/imports lawful sources, resumes acquisition/extraction/compilation, verifies attribution, registers a validated advisor and tests a consultation. Its costs and actual depth remain explicit. Numeric-depth overrides require explicit acceptance; integrity cannot be waived.
- [x] Browser, portable CLI and installed skill expose the implemented modes, board settings and evidence workflow consistently.
- [x] Room portraits, active speakers, stage progress, errors, replay, mobile interaction and complete Markdown/JSON/PDF reports remain coherent.
- [x] Provider failures, uncertain costs, locks, pause/resume and existing ledger protections remain intact.
- [x] End-to-end and source-integrity tests pass; browser behavior and actual exported documents are checked; paid reasoning evaluation stays within verified authorization.

## External limits

Source depth is a quality measure, not a license to pad. Seven of thirteen advisors currently meet both deep-source targets. Source dates, attribution uncertainty, captions not checked against audio, and missing topics must remain visible. Finishing the creation capability does not establish exhaustive source coverage or usefulness on a real project.

The pixel treatment is provisional. No hosting, public release, credit purchase, automatic top-up or budget increase is authorized by this implementation task.

## Qualification (October 31, 2026)

- `npm test`: 49 behavioral checks, including complete nine-seat selected and small-roster all reviews; both quick branches; consult; saved policy affecting creation; strict schemas; old-session compatibility; risk ownership; divided irreversible decisions; packet budgets; evidence refinement; HTTP boundaries, costs and recovery. See `tests/parity.test.mjs`, `integration.test.mjs`, `evidence.test.mjs`, `retrieval-parity.test.mjs`, `room.test.mjs` and the original `review.test.mjs`.
- Python: 53 checks, including a complete independent build → extraction → compilation → registration → cited consultation, safe updates, default-board intent, and failed/corrupted publication protection. Tests use isolated temporary roots and no paid source calls.
- Source audit: all thirteen current compilations and retained passage integrity checks pass, 10,806 passages. Estimated collection usage remains $49.13114715.
- Bundled Chromium browser: real mode/board counts, complete consult and quick fixture reviews, source search/inspection, saved/default/ask/auto selection, explicit over-nine rejection, replay next/pause/speed, dialog keyboard dismissal, desktop and 390px mobile layouts, and Markdown/JSON/PDF downloads checked. Extracted PDF text includes recommendation, evidence, limits, costs and page numbering. Fresh browser console has no errors. Fixtures are explicitly labeled and isolated from the actual archive/ledger; temporary files are removed after verification.
- Live OpenAI/Terra quick review: `20261031163319-91027696`, hypothetical offline notes storage decision, four advisors, 11 calls, $0.18142550 additional estimated cost. The council selected Embedded SQLite, evaluated JSON as the neglected alternative, challenged concrete test assumptions, and specified a falsifiable recovery/search comparison. No ratification or dissent was invented when the quick branch converged. Existing normal review `20261031022041-849f7af5` remains intact. Runtime cumulative usage is $0.41892325 of $0.75; no unresolved reservations. Combined estimated source/runtime usage is $49.55007040 within the existing $51.50 allocation.

OpenCode was supervised through its existing CLI and configured free model. Its partial changes were reviewed and corrected; baseline tests and completion claims were not treated as proof. ADR 0010 records the final contracts. No push or deployment was performed.

## Remaining qualification limits

Functional parity does not mean identical advisor quality or exhaustive knowledge. Seven of thirteen advisors meet both 80-work/500,000-word deep targets. Ritchie, Primeagen, Linus, Carmack, Dorsey and Zuckerberg still have documented depth gaps. Prepared retrieval is local lexical ranking, not guaranteed semantic recall. Matching quotations proves membership and ownership checks, not semantic entailment, audio accuracy or factual truth. The live example was hypothetical and convergent, so usefulness and lively disagreement on the owner's real decisions remain to be established. Controlled tests cover disagreement/dissent mechanics. Only OpenAI/Terra was qualified live; other adapters were checked with controlled providers. Final art remains provisional.
