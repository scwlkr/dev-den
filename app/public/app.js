import { Room } from "./room.js";
import { downloadPDF } from "./pdf.js";
const $ = (id) => document.getElementById(id),
  room = new Room($("room")),
  form = $("brief-form");
let boot,
  session = null,
  board = [],
  stream = null,
  playTimer = null,
  replay = -1,
  tab = "debate",
  files = [];
const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const brief = () =>
  Object.fromEntries(
    ["question", "context", "constraints", "success", "lean"].map((k) => [
      k,
      form.elements[k].value,
    ]),
  );
const notify = (text) => {
  $("message").textContent = text;
  $("message").hidden = false;
  clearTimeout(notify.timer);
  notify.timer = setTimeout(() => ($("message").hidden = true), 18000);
};
async function api(url, data) {
  const response = await fetch(
    url,
    data === undefined
      ? {}
      : {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Den-Token": boot.token,
          },
          body: JSON.stringify(data),
        },
  );
  const result = await response.json();
  if (!response.ok) throw Error(result.error || "Request failed");
  return result;
}
function showBrief() {
  session = null;
  form.reset();
  files = [];
  board = [];
  renderRoster();
  stream?.close();
  clearInterval(playTimer);
  playTimer = null;
  location.hash = "";
  $("title").textContent = "Bring a hard technical decision.";
  $("status").textContent = "Ready when you are";
  $("brief-panel").hidden = false;
  $("session-panel").hidden = true;
  $("evidence-panel").hidden = true;
  $("close-evidence").hidden = true;
  $("inspector-title").textContent = "Your decision brief";
  $("review").hidden = true;
  $("empty").hidden = false;
  room.set(board);
  $("room-caption").textContent = "Assemble your council";
  renderHistory();
}
function renderRoster() {
  const chosen = new Map(board.map((a) => [a.id, a]));
  $("roster").innerHTML = boot.roster
    .map(
      (a) =>
        `<div class="advisor-row"><input type="checkbox" id="seat-${a.id}" data-seat="${a.id}" ${chosen.has(a.id) ? "checked" : ""} aria-label="Include ${esc(a.name)}"><label for="seat-${a.id}">${esc(a.name)}<small>${a.works} works · ${Math.round(a.words / 1000)}k words</small></label><select data-weight="${a.id}" aria-label="Relevance weight for ${esc(a.name)}" ${!chosen.has(a.id) ? "disabled" : ""}>${[1, 2, 3].map((w) => `<option ${chosen.get(a.id)?.weight === w ? "selected" : ""}>${w}</option>`).join("")}</select><details><summary>Lens & coverage</summary><p>${esc(a.focus)}</p>${(a.gaps || []).map((g) => `<p>${esc(typeof g === "string" ? g : JSON.stringify(g))}</p>`).join("")}</details></div>`,
    )
    .join("");
  $("seat-count").textContent = board.length + " selected";
  room.set(board);
}
function renderHistory() {
  const rows = boot.sessions || [];
  $("sessions").innerHTML = rows.length
    ? rows
        .map(
          (s) =>
            `<button class="archive-item ${session?.id === s.id ? "active" : ""}" data-session="${s.id}">${esc(s.title)}<small>${s.created.slice(0, 10)} · ${esc(s.status)}${s.mode === "workflow-demo" ? " · fixture" : ""}</small></button>`,
        )
        .join("")
    : '<p class="field-note">Your decisions will be saved here.</p>';
  $("budget").textContent =
    `Runtime allocation: $${boot.runtime.cap.toFixed(2)}\nAccounted / reserved: $${boot.runtime.exposure.toFixed(4)}\nSource collection billed separately.`;
}
async function refreshArchive() {
  const fresh = await api("/api/bootstrap");
  boot.sessions = fresh.sessions;
  boot.runtime = fresh.runtime;
  renderHistory();
}
async function open(id) {
  $("evidence-panel").hidden = true;
  $("close-evidence").hidden = true;
  clearInterval(playTimer);
  playTimer = null;
  replay = -1;
  stream?.close();
  session = await api("/api/sessions/" + id);
  location.hash = id;
  renderSession();
  stream = new EventSource(
    "/api/sessions/" + id + "/events?after=" + session.events.length,
  );
  stream.onmessage = async (e) => {
    const event = JSON.parse(e.data);
    const updated = await api("/api/sessions/" + id);
    if (session?.id !== id) return;
    session = updated;
    renderSession();
    if (event.type === "complete" || event.type === "error")
      void refreshArchive();
  };
  stream.onerror = () => {
    $("status").textContent = "Reconnecting to local den…";
  };
}
const allCards = () => Object.entries(session?.cards || {});
function renderSession() {
  const s = session;
  if (!s) return;
  $("title").textContent = s.brief.question;
  $("status").textContent =
    s.status === "complete"
      ? "Decision recorded"
      : s.status.replaceAll("_", " ");
  $("brief-panel").hidden = true;
  $("session-panel").hidden = !$("evidence-panel").hidden;
  $("empty").hidden = true;
  $("review").hidden = false;
  $("inspector-title").textContent = $("evidence-panel").hidden
    ? "The locked brief"
    : "First-hand evidence";
  const b = s.brief;
  $("brief-summary").innerHTML =
    "<dl>" +
    ["context", "constraints", "success", "lean"]
      .map((k) => `<dt>${esc(k)}</dt><dd>${esc(b[k])}</dd>`)
      .join("") +
    `<dt>Options</dt><dd>${b.options.map(esc).join(" / ")}</dd><dt>Project evidence</dt><dd>${(b.contextFiles || []).map((f) => esc(f.name)).join(", ") || "None attached"}</dd></dl>`;
  $("council-list").innerHTML = s.board
    .map(
      (a) =>
        `<div class="seat-summary">${esc(s.packets[a.id].name)} <small>Weight ${a.weight} · ${s.packets[a.id].coverage.works} works</small><small>${esc(a.reason)}</small><details><summary>Coverage limits</summary>${(s.packets[a.id].gaps || []).map((g) => `<p class="field-note">${esc(typeof g === "string" ? g : JSON.stringify(g))}</p>`).join("")}</details></div>`,
    )
    .join("");
  $("usage").textContent =
    `API cost: $${s.usage.usd.toFixed(5)} · reserved: $${s.usage.reserved.toFixed(5)} · ${s.usage.calls} calls.`;
  $("run").disabled =
    s.status === "running" || s.status === "complete" || !!s.pending;
  $("pause").disabled = s.status !== "running";
  $("demo").hidden = !boot.demo || Object.keys(s.cards).length > 0;
  $("packet").disabled = s.status === "complete";
  $("cap").max = boot.runtime.cap;
  if (s.error) notify(s.error);
  renderCards();
  renderDecision();
  renderHistory();
  const thinking = [...s.events].reverse().find((e) => e.type === "thinking"),
    last = allCards().at(-1),
    active =
      replay >= 0
        ? allCards()[replay]?.[0].split(":")[1]
        : s.status === "running"
          ? thinking?.advisor
          : last?.[0].split(":")[1];
  room.set(s.board, active || "", !!playTimer);
  $("room-caption").textContent =
    s.mode === "workflow-demo"
      ? "Workflow demonstration · fixture contributions"
      : s.status === "running"
        ? `Considering ${thinking?.stage || "the brief"}…`
        : s.status === "complete"
          ? "Deliberation complete · replay any contribution"
          : "Prepared knowledge · ready to deliberate";
}
function renderCards() {
  const entries = allCards();
  $("progress").textContent =
    `${entries.length} / ${session.board.length * 3 + 3} contributions`;
  $("replay-position").textContent =
    replay >= 0 ? `${replay + 1} / ${entries.length}` : "";
  $("play").textContent = playTimer ? "Ⅱ Pause replay" : "▶ Replay";
  $("transcript").hidden = tab !== "debate";
  $("decision").hidden = tab !== "decision";
  $("transcript").innerHTML = entries.length
    ? entries
        .map(([key, c], index) => {
          const [stage, id] = key.split(":"),
            name = id ? session.packets[id].name : "Council chair";
          return `<article class="contribution ${replay === index ? "active-card" : ""}" id="card-${index}" ${replay >= 0 && index > replay ? "hidden" : ""}><div class="card-heading"><span class="avatar-dot">${esc(id?.slice(0, 2).toUpperCase() || "CH")}</span><h3>${esc(name)}</h3><small>${esc(stage)} · applied reasoning</small></div><p>${esc(c.argument || c.summary || c.rationale)}</p>${c.recommendation ? `<div class="detail"><b>Recommendation:</b> ${esc(c.recommendation)}${c.vote && c.vote !== "not_applicable" ? " · " + esc(c.vote) : ""}</div>` : ""}${c.scores ? `<div class="detail"><b>Option fit:</b> ${c.scores.map((x) => esc(x.option) + " " + x.score + "/10").join(" · ")}<br>Confidence ${c.confidence}/5 · risk ${esc(c.risk)}</div>` : ""}${c.cruxes ? c.cruxes.map((x) => `<div class="detail"><b>${esc(x.question)}</b> ${esc(x.why)} (${x.advisors.map(esc).join(", ")})</div>`).join("") : ""}${[
            "concern",
            "change_mind",
            "next_action",
            "concession",
            "amendment",
          ]
            .filter((k) => c[k])
            .map(
              (k) =>
                `<div class="detail"><b>${esc(k.replaceAll("_", " "))}:</b> ${esc(c[k])}</div>`,
            )
            .join(
              "",
            )}${c.challenge?.advisor !== "none" && c.challenge ? `<div class="detail"><b>Challenge to ${esc(c.challenge.advisor)}:</b> ${esc(c.challenge.point)}</div>` : ""}<div class="evidence-chips">${c.evidence_ids.map((e) => `<button class="evidence-chip" data-evidence="${esc(e)}">↗ ${esc(e)}</button>`).join("")}</div></article>`;
        })
        .join("")
    : '<p class="field-note">The brief is locked. Start the API runner or invoke $dev-den in Codex with this session ID.</p>';
}
function renderDecision() {
  const v = session.cards.verdict;
  if (!v) {
    $("decision").innerHTML =
      '<p class="field-note">The council has not recorded a final decision yet.</p>';
    return;
  }
  const scores = session.brief.options.map((option) => {
    let n = 0,
      d = 0;
    for (const seat of session.board) {
      const c = session.cards["ratification:" + seat.id];
      if (c) {
        n += c.scores.find((x) => x.option === option).score * seat.weight;
        d += seat.weight;
      }
    }
    return { option, score: d ? (n / d).toFixed(1) : "—" };
  });
  const section = (title, items) =>
    `<section class="decision-section"><h3>${esc(title)}</h3><ul>${items.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></section>`;
  const dissent = session.board
    .filter((a) => session.cards["ratification:" + a.id]?.vote === "dissent")
    .map((a) => a.id + ": " + session.cards["ratification:" + a.id].amendment);
  $("decision").innerHTML =
    `<p class="eyebrow">${session.mode === "workflow-demo" ? "Workflow fixture / " : ""}The council’s call</p><div class="recommendation">${esc(v.recommendation)}</div><p class="decision-body">${esc(v.rationale)}</p><div class="scores">${scores.map((x) => `<div class="score">${esc(x.option)}<strong>${x.score}</strong></div>`).join("")}</div><p class="field-note">Weighted fit to this brief, 0–10. These are judgments, not probabilities.</p>${section("Trade-offs", v.tradeoffs)}${section("Conditions", v.conditions)}${section("Next steps", v.next_steps)}${section("Test the decision", [v.experiment])}${section("Revisit when", v.revisit)}${section("Unknowns", v.unknowns)}${section("Dissent", dissent.length ? dissent : ["No advisor recorded dissent."])}${section(
      "Amendments",
      v.amendments.map(
        (a) =>
          `${a.advisor}: ${session.cards["ratification:" + a.advisor].amendment} — ${a.adopted ? "Adopted" : "Declined"}: ${a.reason}`,
      ),
    )}`;
}
function evidence(id) {
  const e = Object.values(session.packets)
    .flatMap((p) => p.evidence)
    .find((e) => e.id === id);
  if (!e) return;
  $("brief-panel").hidden = true;
  $("session-panel").hidden = true;
  $("evidence-panel").hidden = false;
  $("close-evidence").hidden = false;
  $("inspector-title").textContent = "First-hand evidence";
  $("evidence-panel").innerHTML =
    `<div class="evidence-title">${esc(e.title)}</div><div class="source-meta">${esc(session.packets[e.developer].name)} · ${esc(e.attribution)}<br>${esc(e.date || "Publication date unknown")}<br>${esc(e.id)}</div><blockquote>${esc(e.quote)}</blockquote><p class="evidence-context">${esc(e.context)}</p><p class="evidence-context"><b>Documented claim:</b> ${esc(e.claim)}</p><a href="${esc(e.url)}" target="_blank" rel="noopener noreferrer">Open original source ↗</a><p class="source-warning">Matched to retained source text. Attribution and context were assessed during collection; matching does not establish the truth of a claim.${e.caption ? " This is caption text, not audio-verified." : ""} The advisor’s contribution applies this evidence to your brief; it is not a quote from the real developer about your project.</p>`;
  if (innerWidth < 641)
    $("evidence-panel").scrollIntoView({ behavior: "smooth" });
}
function replayStep(delta) {
  const entries = allCards();
  if (!entries.length) return;
  replay = Math.min(
    entries.length - 1,
    Math.max(
      0,
      (replay < 0 ? (delta > 0 ? -1 : entries.length) : replay) + delta,
    ),
  );
  renderSession();
  $("card-" + replay)?.scrollIntoView({
    behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
      ? "instant"
      : "smooth",
    block: "nearest",
  });
}
function toggleReplay() {
  if (playTimer) {
    clearInterval(playTimer);
    playTimer = null;
    renderSession();
    return;
  }
  if (!allCards().length) return;
  tab = "debate";
  setTab();
  if (replay === allCards().length - 1) replay = -1;
  replayStep(1);
  playTimer = setInterval(
    () => {
      if (replay >= allCards().length - 1) {
        clearInterval(playTimer);
        playTimer = null;
        renderSession();
        return;
      }
      replayStep(1);
    },
    6000 / Number($("speed").value),
  );
  renderSession();
}
function setTab() {
  $("tab-debate").setAttribute("aria-selected", String(tab === "debate"));
  $("tab-decision").setAttribute("aria-selected", String(tab === "decision"));
  if (session) {
    renderCards();
    renderDecision();
  }
}
$("roster").addEventListener("change", (e) => {
  if (e.target.dataset.seat) {
    const id = e.target.dataset.seat;
    if (e.target.checked) {
      if (board.length === 7) {
        e.target.checked = false;
        notify("Choose at most seven advisors.");
        return;
      }
      board.push({
        id,
        weight: 1,
        reason: boot.roster.find((a) => a.id === id).focus,
      });
    } else board = board.filter((a) => a.id !== id);
  } else if (e.target.dataset.weight) {
    board.find((a) => a.id === e.target.dataset.weight).weight = Number(
      e.target.value,
    );
  }
  renderRoster();
});
$("example").onclick = async () => {
  const example = {
    question: "Which language should I use for a small personal to-do web app?",
    options: ["TypeScript", "Python", "Rust"],
    context:
      "A hypothetical demonstration. One developer building a browser interface with local storage, basic web knowledge, and no existing codebase.",
    constraints:
      "One developer, personal use, local storage, quick iteration. No accounts, server infrastructure or collaborative sync for the first version.",
    success:
      "Build add/edit/complete/filter within a weekend and keep it easy to change.",
    lean: "No predetermined winner.",
  };
  for (const k of ["question", "context", "constraints", "success", "lean"])
    form.elements[k].value = example[k];
  form.elements.options.value = example.options.join("\n");
  board = await api("/api/recommend", example);
  renderRoster();
};
$("recommend").onclick = async () => {
  try {
    board = await api("/api/recommend", {
      ...brief(),
      options: form.elements.options.value.split("\n").filter(Boolean),
    });
    renderRoster();
  } catch (e) {
    notify(e.message);
  }
};
$("context-files").onchange = async (e) => {
  try {
    files = [];
    let total = 0;
    for (const f of e.target.files) {
      total += f.size;
      if (total > 80000) throw Error("Keep project evidence under 80 KB total");
      const text = await f.text();
      if (
        /(^\.env|\.pem$|\.key$|credentials|secrets)/i.test(f.name) ||
        /-----BEGIN .*PRIVATE KEY-----|sk-(?:proj-|[A-Za-z0-9]{20})|AKIA[0-9A-Z]{16}/.test(
          text,
        )
      )
        throw Error("Do not attach credential material");
      files.push({ name: f.name, text });
    }
  } catch (e) {
    files = [];
    e.target.value = "";
    notify(e.message);
  }
};
form.onsubmit = async (e) => {
  e.preventDefault();
  try {
    const s = await api("/api/sessions", {
      brief: {
        ...brief(),
        options: form.elements.options.value
          .split("\n")
          .map((s) => s.trim())
          .filter(Boolean),
        contextFiles: files,
      },
      board,
    });
    await refreshArchive();
    await open(s.id);
  } catch (e) {
    notify(e.message);
  }
};
$("new").onclick = $("new-brief").onclick = showBrief;
$("sessions").onclick = (e) => {
  const button = e.target.closest("[data-session]");
  if (button) open(button.dataset.session).catch((e) => notify(e.message));
};
$("transcript").onclick = (e) => {
  const button = e.target.closest("[data-evidence]");
  if (button) evidence(button.dataset.evidence);
};
$("close-evidence").onclick = () => {
  $("evidence-panel").hidden = true;
  $("close-evidence").hidden = true;
  if (session) {
    $("session-panel").hidden = false;
    $("inspector-title").textContent = "The locked brief";
  } else {
    $("brief-panel").hidden = false;
    $("inspector-title").textContent = "Your decision brief";
  }
  if (innerWidth < 641 && session)
    $("review").scrollIntoView({ behavior: "smooth" });
};
$("inspector-jump").onclick = () =>
  document.querySelector(".inspector").scrollIntoView({ behavior: "smooth" });
$("about").onclick = () => $("about-dialog").showModal();
$("close-about").onclick = () => $("about-dialog").close();
$("play").onclick = toggleReplay;
$("next").onclick = () => replayStep(1);
$("prev").onclick = () => replayStep(-1);
$("speed").onchange = () => {
  if (playTimer) {
    toggleReplay();
    toggleReplay();
  }
};
$("tab-debate").onclick = () => {
  tab = "debate";
  setTab();
};
$("tab-decision").onclick = () => {
  tab = "decision";
  setTab();
};
$("run").onclick = async () => {
  try {
    await api("/api/sessions/" + session.id + "/start", {
      cap: Number($("cap").value),
    });
    session = await api("/api/sessions/" + session.id);
    renderSession();
  } catch (e) {
    notify(e.message);
  }
};
$("pause").onclick = () =>
  api("/api/sessions/" + session.id + "/pause", {}).catch((e) =>
    notify(e.message),
  );
$("demo").onclick = async () => {
  try {
    session = await api("/api/sessions/" + session.id + "/demo", {});
    replay = -1;
    renderSession();
    await refreshArchive();
  } catch (e) {
    notify(e.message);
  }
};
$("packet").onclick = async () => {
  try {
    const p = await api("/api/sessions/" + session.id + "/packet");
    await navigator.clipboard.writeText(JSON.stringify(p, null, 2));
    notify(
      "Next validated agent packet copied. Submit its response with the dev-den CLI.",
    );
  } catch (e) {
    notify(e.message);
  }
};
$("export-md").onclick = () =>
  (location.href = "/api/sessions/" + session.id + "/report?format=md");
$("export-json").onclick = () =>
  (location.href = "/api/sessions/" + session.id + "/report");
$("export-pdf").onclick = async () => {
  const response = await fetch(
    "/api/sessions/" + session.id + "/report?format=md",
  );
  downloadPDF(await response.text(), session.id);
};
async function init() {
  try {
    boot = await api("/api/bootstrap");
    renderRoster();
    renderHistory();
    if (location.hash) await open(location.hash.slice(1));
  } catch (e) {
    notify(e.message);
  }
}
window.addEventListener("hashchange", () => {
  const id = location.hash.slice(1);
  if (id && id !== session?.id) open(id).catch((e) => notify(e.message));
  else if (!id && session) showBrief();
});
void init();
