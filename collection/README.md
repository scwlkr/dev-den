# Source collection

The approved expansion covers all 13 developers using `gpt-6.1-terra` through the OpenAI Responses API. It reuses the original three-advisor pilot evidence and charges under the same cumulative $25 ceiling. It reads existing text and available captions; it does not buy transcription or download video.

Run from the repository root:

```sh
python3 -B -m unittest discover -s tests -v
python3 -B -m collection.expand
python3 -B -m collection.expand --report-only
python3 -B -m collection.audit
```

The API credential comes from the **Den of Devs Source Collection** 1Password Developer Environment, mounted at the repository's ignored `.env`. An existing `OPENAI_API_KEY` environment variable also works. Never commit or print its value.

The historical pilot runner is retained for its read-only report/preflight options and regression tests; use `collection.expand` for collection and compilation. A missing or empty ledger alongside a charged report blocks a new paid run rather than starting another allowance.

The collector uses Python's standard library and the already installed `pdftotext` and `yt-dlp` programs. No additional Python environment or model runtime is installed.

## Retained results

- `.collection/pilot/`: ignored source text, retrieval metadata, extracted passage evidence, model outputs, the budget ledger, and the machine-readable report.
- `knowledge/<developer>/`: portable Markdown knowledge in roast-room's eight-file structure.
- `collection/FULL-REPORT.md`: current all-roster coverage, compilation depth, cost and gaps.
- `collection/PILOT-REPORT.md`: historical initial pilot report.

Source text is normalized during extraction; its hash and extraction method are retained. Temporary PDF/caption files are removed immediately. No original video is downloaded. Do not delete the retained source text: it is the evidence needed to audit the resulting knowledge.

## Budget and resumption

The initial ceiling is **$25 total**. One process owns the collection lock; at most three independent advisors run concurrently. Budget reservations and returned charges are serialized under one shared ledger lock. A durable conservative reservation is recorded before each paid request, including worst-case tool context, cache writes and output; completed usage replaces it at the documented rates. A $6 margin is preserved for the all-roster compilation phase. Cached reads, ordinary input, and 30-minute or 12-hour cache writes are priced separately. Hosted web-search page opens and finds are conservatively included in tool-fee estimates; the original discovery charges are reconciled from retained responses rather than reset. The ledger is an estimate from returned token/tool usage, not an account invoice or a server-side spending limit.

**Accounting correction:** the completed run was initially reported as $23.724864, but the calculator omitted cache-write premiums. Applying documented rates to saved usage gives **$27.286261**, $2.286261 above the original ceiling. The corrected ledger preserves the previous per-request estimates. Further paid work is blocked; the allowance has not been increased. The corrected calculation and reconciliation have a regression test. Historical pilot figures predate this correction; use the full report for cumulative cost.

A timeout or missing usage leaves its reservation in place and blocks new paid work; already active requests finish and record their charges. No paid POST is automatically retried. Do not delete or edit the ledger to bypass a reservation: review the provider outcome first. A source or model-configuration change has a new cache key; unchanged completed requests are reused. Re-running the command resumes retained work.

Discovery fetches actual primary indexes, publisher media links and own-channel metadata, and uses Terra web search to identify works. Extraction batches stay within their own advisor/source/part identities. Source work prioritizes the least covered advisors. The eight-file knowledge structure follows roast-room, with separate writers for frameworks/principles/books, positions/stories, voice, and the working context.

The source-depth benchmark is roast-room’s deep tier: 80+ distinct works and 500,000+ words per advisor. Standard is 30–50 works and 250,000+ words; quick is 12–20 and 80,000+. Compilations pursue 12–25 frameworks, 15–30 principles, 20–40 positions, 10–20 stories, a 600–800-word working context, and substantial voice guidance. These targets never justify invented views, duplicated works or padded entries. Actual results and limitations are in the full report. The run stops before an unaffordable request.

After saving all 13 baseline compilations, a focused Stroustrup top-up used a $1.50 compilation margin within the same ledger and $25 ceiling. The default all-roster margin remains $6. Remaining allowance is not a reason to submit a request whose conservative reservation would exceed the cap.

Known Primeagen course indexes include their linked notes as one work, bounded to 40 pages and 3 MB of extracted text per course. Standalone technical tutorials can qualify from five minutes when their captions contain at least 800 words; shorter items are held out. Video search filters out clips and reactions before speaker/content verification. Direct chapter URLs remain attached to evidence. Code indentation is preserved. Available publication metadata and source dates accompany compilation; an absent date stays unknown.

## Evidence checks and limits

Sources and quotations are matched to their own advisor and source. Caption source files retain their timestamps; quotation checks use the exact normalized caption words with cue markers removed, and retain a timestamp link and a labeled prose offset. This removes formatting artifacts without accepting paraphrased or invented words. Fabricated quotation strings are rejected. Coauthored work remains identified as coauthored, and conversations require identifiable speakers. Compiled points must reference existing passage evidence; the compiler cannot introduce new direct quotations.

Audit retained evidence against its source hash, normalized passage offset and target speaker aliases before accepting a completed run. The Markdown source references include short verified excerpts and locations; the complete passages remain local.

Known alternate uploads, keynote parts and republications share a work identity. Their original snapshots and citations remain available, but coverage counts one work and its largest scoped word count; independent support also counts work identities. Explicit scopes exclude unrelated mailing-list messages and reader comments while preserving the full snapshots for audit. An interview's scoped word count still includes questions and other conversational context.

A literal quotation match does **not** establish correct speaker attribution or semantic support. Terra assesses eligibility, attribution and context; important claims still deserve source inspection. Automatic captions are labeled as unverified transcripts, and missing code/diagram context is a coverage limitation. These checks are not a certification of historical completeness or advisor quality.

New caption retrieval also checks the selected track's underlying language and rejects translated English tracks. Earlier retained caption snapshots did not save that track-level metadata, so their original-language provenance cannot be certified retrospectively from the local records. Their text membership remains auditable; they are not audio-verified quotations.

Public documentation used for configuration: [Terra](https://developers.openai.com/api/docs/models/gpt-6.1-terra), [web search](https://developers.openai.com/api/docs/guides/tools-web-search), [pricing](https://developers.openai.com/api/docs/pricing), and [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

## summarize evaluation

The owner suggested [summarize](https://summarize.sh/). Version 0.21.5 was already installed, so no new installation, repository clone or model download was needed. Five extraction-only tests ran without provider keys, paid transcription, media downloads or persistent caches. They covered two available Primeagen videos, one unavailable Primeagen reaction transcript, a Linus interview page, and a Stanford Dorsey talk page.

It recovered no additional original English source material: the long HTMX transcript matched the existing extraction; the apparent workflow-video gain was Arabic subtitles rather than original English; the reaction transcript remained unavailable; the interview extraction included reader comments; and the Stanford page yielded surrounding site text. No translated track was promoted into advisor evidence, and no API charges were added. The tool was not integrated. Its [documented transcript flow](https://summarize.sh/docs/transcript-provider-flow.html) could be reconsidered for a separately scoped transcription phase. Disposable evaluation outputs were removed; the existing installation was preserved.
