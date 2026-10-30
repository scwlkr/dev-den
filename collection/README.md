# Source collection pilot

The agreed pilot covers DHH, Dennis Ritchie, and The Primeagen using `gpt-6.1-terra` through the OpenAI Responses API. It starts with existing text and transcripts; it does not buy transcription or download video. All 13 developers remain in the initial product scope.

Run from the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 -m collection.pilot --preflight
python3 -m collection.pilot
```

The API credential comes from the **Den of Devs Source Collection** 1Password Developer Environment, mounted at the repository's ignored `.env`. An existing `OPENAI_API_KEY` environment variable also works. Never commit or print its value.

The collector uses Python's standard library and the already installed `pdftotext` and `yt-dlp` programs. No additional Python environment or model runtime is installed.

## Retained results

- `.collection/pilot/`: ignored source text, retrieval metadata, extracted passage evidence, model outputs, the budget ledger, and the machine-readable report.
- `knowledge/<developer>/`: portable Markdown knowledge in roast-room's eight-file structure.
- `collection/PILOT-REPORT.md`: the human-readable cost and coverage report.

Source text is normalized during extraction; its hash and extraction method are retained. Temporary PDF/caption files are removed immediately. No original video is downloaded. Do not delete the retained source text: it is the evidence needed to audit the resulting knowledge.

## Budget and resumption

The initial ceiling is **$25 total**. Requests run serially under a process lock. A durable conservative reservation is recorded before each paid request, including worst-case tool context and output; completed usage replaces it at the documented rates. The final three compilations get a reserved margin. Cached-token discounts are not assumed. The ledger is an estimate from returned token/tool usage, not an account invoice or a server-side spending limit.

A timeout or missing usage leaves its reservation in place and stops paid work. No paid POST is automatically retried. Do not delete or edit the ledger to bypass a reservation: review the provider outcome first. A source or model-configuration change has a new cache key; unchanged completed requests are reused. Re-running the command resumes retained work.

Discovery fetches seed indexes and uses Terra web search to choose individual first-hand works. Source work is round-robin across the three developers. Source-count targets are planning goals; insufficient evidence, inaccessible content and missing transcripts remain visible gaps. The run stops before an unaffordable request. Review the pilot report before further spending or expansion to the other ten developers.

Known Primeagen course indexes include their linked notes as one work, bounded to 40 pages and 3 MB of extracted text per course. Direct chapter URLs remain attached to evidence. Code indentation is preserved. Available publication metadata and source dates accompany compilation; an absent date stays unknown.

## Evidence checks and limits

Sources and quotations are matched to their own advisor and source. Fabricated quotation strings are rejected. Coauthored work remains identified as coauthored, and conversations require identifiable speakers. Compiled points must reference existing passage evidence; the compiler cannot introduce new direct quotations.

On resume, retained evidence is checked against its source hash and target speaker aliases. The Markdown source references include short verified excerpts and locations; the complete passages remain local.

A literal quotation match does **not** establish correct speaker attribution or semantic support. Terra assesses eligibility, attribution and context; important claims still deserve source inspection. Automatic captions are labeled as unverified transcripts, and missing code/diagram context is a coverage limitation. This pilot is not a certification of historical completeness or advisor quality.

Public documentation used for configuration: [Terra](https://developers.openai.com/api/docs/models/gpt-6.1-terra), [web search](https://developers.openai.com/api/docs/guides/tools-web-search), [pricing](https://developers.openai.com/api/docs/pricing), and [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
