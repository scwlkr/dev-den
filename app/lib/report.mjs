import { weightedScores } from "./protocol.mjs";
export function report(s) {
  const verdict = s.cards.verdict;
  return {
    version: 1,
    id: s.id,
    created: s.created,
    status: s.status,
    mode: s.mode,
    notice:
      "Simulated advisors applying documented first-hand principles. These developers did not participate or endorse this review. Applied reasoning is not a historical quotation. Caption matches verify text, not audio or truth.",
    brief: s.brief,
    board: s.board.map((a) => ({
      ...a,
      name: s.packets[a.id].name,
      coverage: s.packets[a.id].coverage,
      gaps: s.packets[a.id].gaps,
    })),
    scores: weightedScores(s),
    verdict: verdict || null,
    dissent: s.board
      .filter((a) => s.cards["ratification:" + a.id]?.vote === "dissent")
      .map((a) => ({ advisor: a.id, ...s.cards["ratification:" + a.id] })),
    amendments: s.board
      .filter((a) => s.cards["ratification:" + a.id]?.amendment)
      .map((a) => ({
        advisor: a.id,
        text: s.cards["ratification:" + a.id].amendment,
        resolution: verdict?.amendments.find((x) => x.advisor === a.id),
      })),
    cards: s.cards,
    sources: usedEvidence(s),
    usage: s.usage,
  };
}
export function usedEvidence(s) {
  const ids = new Set(
    Object.values(s.cards).flatMap((c) => c.evidence_ids || []),
  );
  const works = new Set();
  return Object.values(s.packets)
    .flatMap((p) => p.evidence)
    .filter((e) => ids.has(e.id))
    .map((e) => {
      const excerpt = works.has(e.work)
        ? ""
        : e.quote.split(/\s+/).slice(0, 12).join(" ");
      works.add(e.work);
      return {
        id: e.id,
        advisor: e.developer,
        source_id: e.source_id,
        title: e.title,
        url: e.url,
        date: e.date,
        attribution: e.attribution,
        speaker: e.speaker,
        claim: e.claim,
        context: e.context,
        excerpt,
        caption: e.caption,
        source_hash: e.source_hash,
      };
    });
}
const safe = (s) => String(s).replace(/([\\`*_[\]<>])/g, "\\$1");
export function markdown(s) {
  const r = report(s),
    lines = [
      "# Den of Devs — Decision review",
      "",
      safe(r.notice),
      "",
      `Session: ${s.id} · ${s.created} · ${s.mode}`,
      "",
      "## Decision brief",
      "",
      ...Object.entries(s.brief).map(
        ([k, v]) =>
          `**${k}**: ${safe(typeof v === "string" ? v : JSON.stringify(v))}`,
      ),
      "",
      "## Council",
      "",
      ...r.board.map(
        (a) =>
          `- ${safe(a.name)} · weight ${a.weight}: ${safe(a.reason)} (${a.coverage.works} works, ${a.coverage.words.toLocaleString()} words)`,
      ),
      "",
      "## Recommendation",
      "",
    ];
  if (r.verdict) {
    const v = r.verdict;
    lines.push(
      "**" + safe(v.recommendation) + "**",
      safe(v.rationale),
      "",
      "### Trade-offs",
      ...v.tradeoffs.map((x) => "- " + safe(x)),
      "",
      "### Conditions",
      ...v.conditions.map((x) => "- " + safe(x)),
      "",
      "### Next steps",
      ...v.next_steps.map((x) => "- " + safe(x)),
      "",
      "### Experiment",
      safe(v.experiment),
      "",
      "### Revisit when",
      ...v.revisit.map((x) => "- " + safe(x)),
      "",
      "### Unknowns",
      ...v.unknowns.map((x) => "- " + safe(x)),
    );
  } else lines.push("Review in progress. No final recommendation.");
  lines.push(
    "",
    "## Weighted option fit (0–10, not a probability)",
    "",
    ...r.scores.map((x) => `- ${safe(x.option)}: ${x.score ?? "pending"}`),
    "",
    "## Dissent",
    "",
    ...(r.dissent.length
      ? r.dissent.map((c) => `- ${c.advisor}: ${safe(c.amendment)}`)
      : ["No recorded dissent."]),
    "",
    "## Amendments",
    "",
    ...r.amendments.map(
      (a) =>
        `- ${a.advisor}: ${safe(a.text)} — ${a.resolution ? (a.resolution.adopted ? "Adopted" : "Declined") + ": " + safe(a.resolution.reason) : "Pending"}`,
    ),
    "",
    "## Deliberation",
  );
  for (const [key, c] of Object.entries(s.cards)) {
    lines.push(
      "",
      "### " + key,
      "",
      safe(c.argument || c.summary || c.rationale || ""),
    );
    if (c.scores)
      lines.push(
        "Recommendation: " +
          safe(c.recommendation) +
          "; confidence " +
          c.confidence +
          "/5; risk " +
          c.risk +
          "; vote " +
          c.vote,
        "Option fit: " +
          c.scores
            .map((x) => safe(x.option) + " " + x.score + "/10")
            .join(" · "),
      );
    if (c.concern)
      lines.push(
        "Concern: " + safe(c.concern),
        "Change my mind: " + safe(c.change_mind),
        "Next action: " + safe(c.next_action),
      );
    if (c.challenge?.advisor !== "none" && c.challenge)
      lines.push(
        "Challenge to " + c.challenge.advisor + ": " + safe(c.challenge.point),
        "Concession: " + safe(c.concession),
      );
    if (c.cruxes)
      for (const crux of c.cruxes)
        lines.push(
          "- " +
            safe(crux.question) +
            " (" +
            crux.advisors.join(", ") +
            "): " +
            safe(crux.why),
        );
    lines.push("Evidence: " + (c.evidence_ids || []).join(", "));
  }
  lines.push(
    "",
    "## First-hand sources",
    "",
    ...r.sources.flatMap((e) => [
      `- **${e.id}** · ${e.advisor} · ${e.attribution} · ${e.date || "date unknown"} · [${safe(e.title)}](${e.url})`,
      e.excerpt ? `  Verified excerpt: “${safe(e.excerpt)}…”` : "",
      `  Context: ${safe(e.context)}${e.caption ? " Caption text; not audio verified." : ""}`,
    ]),
    "",
    "## Coverage and limits",
    "",
    ...r.board.flatMap((a) => [
      "### " + safe(a.name),
      ...(a.gaps || []).map(
        (g) => "- " + safe(typeof g === "string" ? g : JSON.stringify(g)),
      ),
    ]),
    "",
    `Runtime API usage: $${s.usage.usd.toFixed(6)}; unresolved reservations: $${s.usage.reserved.toFixed(6)}. Collection costs are accounted separately.`,
  );
  return lines.join("\n");
}
