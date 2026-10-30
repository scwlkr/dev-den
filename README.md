# Den of Devs

A technical decision council grounded in developers' own published reasoning. Prepare advisor knowledge first, then convene five to seven relevant advisors to examine a shared decision brief and reach an opinionated, cited outcome.

The product specification is [GitHub issue #2](https://github.com/scwlkr/dev-den/issues/2). Collection expansion is tracked in [#4](https://github.com/scwlkr/dev-den/issues/4).

## Source collection and advisor knowledge

- [Collection instructions](collection/README.md): Terra setup, shared $25 budget, resumption and evidence checks.
- [Full-roster report](collection/FULL-REPORT.md): actual source depth, compilation depth, costs and coverage gaps.
- [Advisor knowledge](knowledge/): eight Markdown files per advisor, following roast-room's structure.
- [Roster configuration](collection/roster.json): all 13 initial developers and their source focus.

Read an advisor's `_hot.md` first, then the relevant frameworks, principles, positions and cases. `sources.md` locates the underlying evidence; full source text and passage records remain local in the ignored `.collection/pilot/` directory. Applied recommendations must distinguish documented positions from inferred reasoning.

The depth benchmark comes from [roast-room's advisor-building workflow](https://github.com/nateherkai/roast-room/blob/main/.claude/skills/newroaster/SKILL.md) and [brain specification](https://github.com/nateherkai/roast-room/blob/main/.claude/skills/newroaster/references/brain-spec.md). Actual coverage is reported explicitly; a complete file structure alone does not establish a deep source collection.

## Development

```sh
python3 -B -m unittest discover -s tests -v
python3 -B -m collection.expand
python3 -B -m collection.audit
```

[GLOSSARY.md](GLOSSARY.md) defines the domain terms. Decisions live in [docs/adr/](docs/adr/).
