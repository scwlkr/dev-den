# Den of Devs

A technical decision council grounded in developers' own published reasoning. Prepare advisor knowledge first, then convene five to seven relevant advisors to examine a shared decision brief and reach an opinionated, cited outcome.

The product specification is [GitHub issue #2](https://github.com/scwlkr/dev-den/issues/2). The initial collection expansion is recorded in [#4](https://github.com/scwlkr/dev-den/issues/4), and continuation from existing credits in [#5](https://github.com/scwlkr/dev-den/issues/5).

## Source collection and advisor knowledge

- [Collection instructions](collection/README.md): Terra setup, the current $51.50 cumulative allocation, resumption and evidence checks.
- [Full-roster report](collection/FULL-REPORT.md): actual source depth, compilation depth, costs and coverage gaps.
- [Advisor knowledge](knowledge/): eight Markdown files per advisor, following roast-room's structure.
- [Roster configuration](collection/roster.json): all 13 initial developers and their source focus.

The current collection has 13 rebuilt advisor packs, 7.31 million scoped source words and seven advisors meeting both deep-source thresholds. The report lists 1,100 per-advisor work counts, the estimated $49.13 cumulative API usage, and the remaining coverage gaps. Collection and knowledge preparation are the implemented scope so far.

Read an advisor's `_hot.md` first, then the relevant frameworks, principles, positions and cases. `sources.md` locates the underlying evidence; full source text and passage records remain local in the ignored `.collection/pilot/` directory. Applied recommendations must distinguish documented positions from inferred reasoning.

The depth benchmark comes from [roast-room's advisor-building workflow](https://github.com/nateherkai/roast-room/blob/main/.claude/skills/newroaster/SKILL.md) and [brain specification](https://github.com/nateherkai/roast-room/blob/main/.claude/skills/newroaster/references/brain-spec.md). Actual coverage is reported explicitly; a complete file structure alone does not establish a deep source collection.

## Development

```sh
python3 -B -m unittest discover -s tests -v
python3 -B -m collection.deepen
python3 -B -m collection.audit
```

[GLOSSARY.md](GLOSSARY.md) defines the domain terms. Decisions live in [docs/adr/](docs/adr/).
