// Deterministic workflow fixture, explicitly labeled. Never presented as an AI review.
export function fixtureCard(s, step) {
  const options = s.brief.options,
    ids = s.board.map((a) => a.id),
    index = Math.max(0, ids.indexOf(step.advisor)),
    own = s.packets[step.advisor] || Object.values(s.packets)[0],
    evidence_ids = [own.evidence[0].id];
  const base = {
    recommendation: options[0],
    argument:
      "Workflow demonstration: apply a documented principle to the stated constraints, then test the smallest usable implementation. This text is a fixture, not a model-generated advisor opinion.",
    scores: options.map((option, i) => ({ option, score: 8 - i })),
    confidence: 3,
    risk: "possible",
    risk_option: options[0],
    resolution_support: 7,
    mitigation: "",
    mitigation_for_option: options[0],
    mitigation_endorsed: false,
    concern: "Persistence and maintenance need a concrete test.",
    change_mind:
      "Measured implementation effort or data-loss risk changes the fit.",
    next_action: "Build a small working slice and test persistence.",
    evidence_ids,
    challenge: {
      advisor: step.stage === "debate" ? ids[(index + 1) % ids.length] : "none",
      point:
        step.stage === "debate"
          ? "The opening argument needs an explicit persistence test."
          : "",
    },
    concession:
      step.stage === "debate"
        ? "A smaller implementation reduces maintenance work."
        : "",
    vote:
      step.stage === "ratification"
        ? index === 1
          ? "dissent"
          : "accept"
        : "not_applicable",
    amendment:
      step.stage === "ratification" && index === 1
        ? "Demonstrate export and recovery before committing."
        : "",
  };
  if (["opening", "debate", "ratification"].includes(step.stage)) return base;
  if (step.stage === "cruxes")
    return {
      summary:
        "Workflow fixture: scope and persistence are the decision cruxes.",
      cruxes: [
        {
          question: "Can the smallest implementation preserve data?",
          advisors: ids.slice(0, 2),
          why: "The brief requires local persistence.",
        },
      ],
      unanimous: true,
      evidence_ids,
    };
  const draft = {
    recommendation: options[0],
    rationale:
      "Workflow fixture: choose the smallest option that satisfies the stated browser constraints, subject to a persistence experiment.",
    conditions: ["Validate persistence and export."],
    tradeoffs: ["Less infrastructure; local-only data."],
    experiment:
      "Implement add, edit, complete and reload; export and restore ten tasks.",
    revisit: ["Sync becomes necessary or persistence test fails."],
    unknowns: ["Actual build effort is not measured."],
    evidence_ids,
  };
  if (step.stage === "draft") return draft;
  return {
    ...draft,
    next_steps: ["Build the slice.", "Test reload and restore."],
    amendments:
      s.board.length > 1 &&
      Object.keys(s.cards).some((k) => k.startsWith("ratification:"))
        ? [
            {
              advisor: ids[1],
              adopted: true,
              reason: "Recovery is part of the acceptance experiment.",
            },
          ]
        : [],
  };
}
