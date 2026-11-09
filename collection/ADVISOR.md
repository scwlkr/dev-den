# Build or update an advisor

The builder is a preparation workflow, separate from a decision review. It reuses first-hand evidence validation and knowledge export. The host agent supplies discovery, extraction and compilation reasoning; this CLI makes no model API calls or changes to the original paid collection ledger. Network acquisition happens only when you explicitly import a URL without a local text file.

Run from the repository root. `node app/cli.mjs advisor ...` delegates to the same Python command and honors `DEN_PROJECT_ROOT`.

```sh
python3 -B -m collection.advisor prepare --id developer --name 'Full Name' --focus 'Technical domain' --depth standard
python3 -B -m collection.advisor import --id developer --url 'https://author.example/article'
# Or import explicitly supplied first-hand text; preserve provenance:
python3 -B -m collection.advisor import --id developer --url 'https://author.example/article' --text-file /path/to/article.txt --title 'Article' --author 'Full Name' --date 2026-01-01
python3 -B -m collection.advisor extraction-packet --id developer --source-id SOURCE_ID --part 1
# Read the complete packet/schema and write its grounded response:
python3 -B -m collection.advisor extraction-submit --id developer --source-id SOURCE_ID --part 1 --file /tmp/extraction.json
# Repeat for every part and eligible source.
python3 -B -m collection.advisor compilation-packet --id developer
python3 -B -m collection.advisor compilation-submit --id developer --file /tmp/compilation.json
python3 -B -m collection.advisor validate --id developer
python3 -B -m collection.advisor register --id developer
```

Use `--project /absolute/project` before the subcommand for an isolated fixture project. IDs are lowercase slugs. Supply aliases using repeated `--alias`; speaker identity is checked against aliases, not a loose name substring. The prepare response supplies a discovery task. Find personally authored material or identifiable original speech; record public lawful source URLs. Do not treat company posts, a reaction video's quoted author, or an interviewer as the target developer. Do not acquire gated material or download books/media without authorization.

Extraction packets include the actual JSON schema and source chunk. Do not invent evidence IDs or quotes: submission normalizes and verifies the attributed passage, assigns canonical IDs and offsets, and tracks source/chunk completion. Wrong speakers, foreign quotes, corruption and invalid source paths fail validation. Repeating an accepted part is idempotent. Source dates, authorship and extraction qualifications remain retained. Captions are text evidence, not audio verification.

Compilation packets supply verified evidence and the actual schema. Produce seven unique sections: `_hot`, `frameworks`, `principles`, `positions`, `stories`, `voice`, `books`, plus gaps. Every nonempty item needs its own evidence IDs and a `documented` or `inferred` basis. Direct quotations belong to evidence, not newly written compilation text. Leave unsupported sections explicitly empty; do not invent books, frameworks or positions to satisfy a file budget. Registration exports those seven Markdown files plus `sources.md` and the canonical local corpus used by the runtime.

Depth requires both distinct works and scoped source words:

| Depth | Works | Words |
| --- | ---: | ---: |
| Quick | 12 | 80,000 |
| Standard | 30 | 250,000 |
| Deep | 80 | 500,000 |

`validate --allow-gaps` and `register --allow-gaps` explicitly acknowledge a numeric shortfall. They never waive integrity checks. Actual coverage and gaps are retained; a registered thin advisor is not described as deep. Duplicate URLs/text are not independent works. Group known alternate representations of the same work rather than claiming corroboration from duplicates.

Registration validates retained text hashes, ownership, offsets, complete extraction, compilation references and snapshot identity again. It publishes staged corpus/knowledge under a lock, with the roster updated after valid data is ready. Existing destinations and failures must preserve prior data. `--default-board` on prepare records explicit intent to add the advisor to the default board; an over-nine board is rejected. Initial thirteen advisors cannot be replaced by an unrelated builder manifest.

For a builder-owned advisor, use `update --id developer` or `prepare ... --update` to resume its manifest, import new sources, extract them, compile the full combined evidence and `register --id developer --update`. New evidence invalidates the prior compilation. Historical source text and evidence identities must remain available. Do not replace a developer's identity, reset a ledger, or remove old sources to force an update through.

After successful registration, make a sample brief and run `node app/cli.mjs consult BRIEF.json developer`. Conduct its packet/submit workflow through a complete cited verdict, inspect the browser portrait fallback and report, and disclose limits. A prepared manifest or successful import alone is not consultation readiness. Changes to a source snapshot require a new decision review rather than silently altering a saved review's basis.
