# Running the Den

Node 22+ is the only runtime dependency. The advisor source corpus must already exist in `.collection/pilot/`; the app checks retained source hashes, passage offsets, attribution scopes, and advisor ownership before creating a review. A fresh clone includes compiled Markdown knowledge but not the private raw corpus or saved reviews. Complete the documented collection workflow on another machine before running there.

```sh
npm start
# http://127.0.0.1:4731
```

Create a brief, select a review mode and advisors with relevance weights, and convene. A normal review uses 5–7 advisors. Preparation is free. Use `$dev-den` in Codex to conduct the review through the current agent, or select **Run / resume with API**. The skill is in `.agents/skills/dev-den/SKILL.md`; a symlink in `~/.codex/skills/dev-den` makes it available to Codex (restart/refresh skill discovery if necessary). Other platforms can read the same skill and use the CLI; native automatic skill discovery varies by platform.

The local browser watches durable session events, including CLI submissions. Reviews survive browser/server restarts. Pause waits for the in-flight contribution to finish; resume starts at the next uncompleted step. Replay has pause, previous/next, and speed controls. Each contribution links to a short matched evidence excerpt, original source, date when known, attribution, and context. The decision view records trade-offs, conditions, next steps, dissent, amendments, and a falsifiable experiment. Download Markdown/JSON/PDF from the side panel. PDF uses the locally vendored MIT jsPDF library.

## Portable agent protocol

```sh
node app/cli.mjs roster
node app/cli.mjs recommend examples/todo.json
node app/cli.mjs prepare examples/todo.json auto
node app/cli.mjs packet SESSION
# Write a JSON response to the returned schema and exact next step.
node app/cli.mjs submit SESSION opening:dhh /tmp/my-card.json
# Repeat packet / submit through chair verdict.
node app/cli.mjs report SESSION
```

An optional board file contains `{id,weight,reason}` objects. Explicit text/code context files can follow it in `prepare`; only their supplied contents enter the brief. The agent protocol is platform independent: any host that can read files and produce JSON can participate. External HTTP producers may use `/api/sessions/ID/packet` and POST `/submit` with the loopback bootstrap token. Do not submit credentials as project evidence. Cards accepted by the validator are immutable. Identical submissions are idempotent.

## Optional provider adapters

Credentials are server-side only. OpenAI reads `OPENAI_API_KEY` or the existing `.env` 1Password FIFO. The FIFO is never overwritten. Provider URLs, models, rates and global allocation are operator environment settings; the browser cannot change them.

- Default: OpenAI Responses, `gpt-6.1-terra`, `https://api.openai.com/v1`.
- `DEN_PROVIDER=compatible`: OpenAI-compatible Chat Completions with JSON schema. Set `DEN_API_BASE`, `DEN_MODEL`, `OPENAI_API_KEY` and `DEN_RATES`.
- `DEN_PROVIDER=anthropic`: Messages adapter with structured output. Set `DEN_API_BASE=https://api.anthropic.com/v1`, `DEN_MODEL`, `ANTHROPIC_API_KEY`, and `DEN_RATES`. Default/short cache writes are supported; do not enable long-lived caching without extending accounting.
- New adapters can implement `invoke(config, request) → {id,text,usage}` in `lib/providers.mjs`. The host-agent packet/submit route works without any provider-specific adapter.

For every non-default model/base/provider, explicitly configure current per-million-token rates:

```sh
DEN_RATES='{"input":1,"output":5,"cached":0.05,"write":1.25,"longWrite":2.5}'
```

This example is the current pilot Terra schedule, not a claim that those rates apply to other models. The compatibility and Anthropic adapters are tested through controlled providers; only OpenAI/Terra receives a live qualification here. Your endpoint must implement its chosen schema/usage contract.

The initial **cumulative runtime allocation is $0.75**, separately recorded in `.den/usage.json`. Source collection accounting remains unchanged. `DEN_RUNTIME_BUDGET` changes the configured cumulative runtime cap; increase it only with the owner's authorization. Per-review caps cannot bypass the cumulative cap. There are no purchases, automatic top-ups, web-search tools, or automatic paid retries.

Each paid step reserves a conservative UTF-8 input bound, cache-write/long-context premiums and maximum output before POST. Completed responses and exact cache-aware usage are retained. The runner holds a process lock across the paid review. One paid review runs at a time. If the browser closes, the server continues. Stop the server only after pausing if you want no further contributions.

### Recovery

- **Paused, no pending request:** resume the runner. Accepted cards are skipped.
- **Charged response failed card validation:** inspect `.den/usage.json` locally for that step's retained `response_text`. Correct the schema/citations through packet/submit; do not repeat its paid POST. No API key is stored in the ledger.
- **Pending/unknown charge:** no automatic retry. Inspect provider usage externally if needed. `node app/cli.mjs acknowledge-unknown SESSION` clears the session's pending flag while retaining the entire cost reservation and its immutable ledger job. It permits a corrected external agent card; it does not refund, fabricate usage, or retry the paid step. The report continues to show unresolved reservations.
- **Stale `.den/run.lock`:** read its PID and verify that process is gone before removing this small lock file. Never remove an active runner's lock.

The app binds only `127.0.0.1`. Mutations require a same-origin token, Host is restricted to loopback, static paths are contained, and provider credentials are never returned. This is a local personal app, not a hosted multi-user service. Do not expose the port publicly without adding authentication and reviewing deployment boundaries.

## Evidence limitations

All advisor text is simulated application of first-hand evidence. It is not a historical statement about your project. Text matching establishes passage integrity, not the truth of a source claim or perfect semantic support. Attribution/context were assessed during collection. Captions are not audio verified. Retrieval selects source-linked working context, voice guidance and relevant compiled knowledge together with all supporting passages, under a total serialized packet budget (56,000 characters by default). Omitted sections and weak source coverage remain explicit. Prepared evidence can be refined within the original corpus snapshot; the runtime rejects changed source hashes and snapshot identities. Weak coverage, unknown dates, and historical contexts remain visible in reports. Inferred compilation summaries are not supplied as authority.

## Verification

```sh
npm test
python3 -B -m unittest discover -s tests -v
python3 -B -m collection.audit
```

Native Node tests exercise the complete protocol, citations, actual dissent, budgets, uncertain charges, pause/resume, replay events, HTTP boundaries, and reports with controlled providers. Browser verification uses an opt-in workflow fixture (`DEN_DEMO=1`) labeled as a demonstration, never as real advisor reasoning. The default UI does not expose the fixture button.

The visual room is a provisional pixel study. The final portrait/art direction remains open. Animation follows published contribution playback and respects reduced motion; it is not a claim of live human participation or token streaming.

Provider references: [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [Anthropic structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs). Upstream adaptation and third-party licensing are documented in [NOTICE.md](../NOTICE.md).

## Review modes and saved boards

`prepare BRIEF [BOARD|auto]` conducts a normal 5–7-person review. `quick BRIEF [BOARD|auto]` uses four and conditionally skips ratification after a converged debate. `consult BRIEF ADVISOR` uses one advisor plus synthesis. `selected BRIEF BOARD` supports 1–9 explicitly selected advisors. `all BRIEF` rejects a roster larger than nine; it does not silently truncate our thirteen-person roster. Browser mode selection follows the same contracts.

`node app/cli.mjs board` shows saved policy/defaults. `board set '{"board":"default","default":["dhh","tobi","primeagen","carmack","linus"]}'` saves validated preferences atomically. Policies are ask/auto/default; explicit participants win. Under ask, a host agent confirms participants while a machine CLI must pass an explicit board. The browser exposes settings and lets you use the saved board. `DEN_PROJECT_ROOT` isolates configuration/corpus for a different project.

`node app/cli.mjs evidence SESSION ADVISOR 'QUERY' [LIMIT]` adds verified passages from the same prepared snapshot before the next contribution. The browser has the equivalent source search. It cannot run while a provider request is pending or alter a completed review.

Computed decision safeguards are visible in the room and every export: weighted fit, spread, confidence, support for the actual draft, material-risk blockers requiring the original advisor's mitigation endorsement, weak-dimension fixes, and experiments before divided irreversible choices. These are simulated fit judgments, not probabilities. Version-2 output schemas are strict; version-1 reviews remain readable/resumable without rewriting accepted contributions.

To add or deepen an advisor, use [the advisor-building workflow](../collection/ADVISOR.md) through `node app/cli.mjs advisor ...` or the dedicated host-agent skill. It uses the original validation/export machinery and refuses incomplete or corrupted registration. Depth shortfalls require explicit acknowledgement and remain in the knowledge. Final portrait style remains replaceable.
