# Roast-room parity acceptance

Tracked in [issue #7](https://github.com/scwlkr/dev-den/issues/7). Starting implementation: `920dc50`. This checklist records verified behavior, not merely the existence of commands or green baseline tests. Upstream reference: `nateherkai/roast-room`, its council skill, scoring protocol, advisor-building skill and browser room.

## Required implementation

- [ ] Normal, consult, quick (both ratification branches), selected and all modes complete through saved verdict and report.
- [ ] Review mode survives provider execution and restart; existing accepted sessions retain their historical contents.
- [ ] Quick escalation uses disagreement between advisors on the same option, plus material risk, rather than differences between option averages.
- [ ] Saved default boards and ask/auto/default policy affect actual selection; explicit participants take precedence. Participant limits are explicit.
- [ ] Weighted option fit, spread, council confidence and draft-resolution support are computed from accepted contributions.
- [ ] Material risk cannot be averaged away; mitigation requires the relevant advisor's endorsement. Divided irreversible decisions require a test precondition.
- [ ] Early unanimity triggers evaluation of the strongest neglected alternative without inventing disagreement.
- [ ] Source-linked working context, frameworks, principles, positions, cases and voice inform advisor packets, with documented/inferred status preserved.
- [ ] Retrieval covers the prepared corpus and can refine evidence for competing arguments without collecting new developer sources during reviews.
- [ ] An advisor-building workflow discovers/imports lawful sources, resumes acquisition/extraction/compilation, verifies attribution, registers a validated advisor and tests a consultation. Its costs and actual depth remain explicit.
- [ ] Browser, portable CLI and installed skill expose the implemented modes, board settings and evidence workflow consistently.
- [ ] Room portraits, active speakers, stage progress, errors, replay, mobile interaction and complete Markdown/JSON/PDF reports remain coherent.
- [ ] Provider failures, uncertain costs, locks, pause/resume and existing ledger protections remain intact.
- [ ] End-to-end and source-integrity tests pass; browser behavior and actual exported documents are checked; paid reasoning evaluation stays within verified authorization.

## External limits

Source depth is a quality measure, not a license to pad. Seven of thirteen advisors currently meet both deep-source targets. Source dates, attribution uncertainty, captions not checked against audio, and missing topics must remain visible. Finishing the creation capability does not establish exhaustive source coverage or usefulness on a real project.

The pixel treatment is provisional. No hosting, public release, credit purchase, automatic top-up or budget increase is authorized by this implementation task.

## Reviewed milestones

- `8ba875b`: partial mode/persistence changes; not accepted as complete. The review found mandatory-ratification dereferences in consult, incorrect quick spread arithmetic and absent new mode tests. Follow-up implementation is in progress.
