import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { ROOT, packet, recommend } from "./knowledge.mjs";
import {
  validateBrief,
  validateBoard,
  allowedBoardSize,
  nextStep,
  validateCard,
  weightedScores,
} from "./protocol.mjs";
import { markdown } from "./report.mjs";
export class Store {
  constructor(dir = path.join(ROOT, "sessions"), root = ROOT) {
    this.dir = dir;
    this.root = root;
    fs.mkdirSync(dir, { recursive: true, mode: 0o700 });
  }
  folder(id) {
    if (!/^[a-z0-9-]{8,90}$/.test(id)) throw Error("Invalid session ID");
    return path.join(this.dir, id);
  }
  read(id) {
    const s = JSON.parse(
      fs.readFileSync(path.join(this.folder(id), "session.json"), "utf8"),
    );
    if (!s.reviewMode) s.reviewMode = "normal";
    if (s.provider === undefined && typeof s.mode === "string" && s.mode.includes(":")) {
      s.provider = s.mode;
      s.reviewMode = "normal";
    }
    return s;
  }
  list() {
    return fs
      .readdirSync(this.dir)
      .filter(
        (id) =>
          /^[a-z0-9-]{8,90}$/.test(id) &&
          fs.existsSync(path.join(this.dir, id, "session.json")),
      )
      .map((id) => {
        const s = this.read(id);
        return {
          id,
          title: s.brief.question,
          status: s.status,
          created: s.created,
          mode: s.mode,
          cards: Object.keys(s.cards).length,
          usage: s.usage,
        };
      })
      .sort((a, b) => b.created.localeCompare(a.created));
  }
  create(brief, board, mode = "agent") {
    brief = validateBrief(brief);
    board = board || recommend(brief, this.root);
    const [min, max] = allowedBoardSize(mode);
    if (!Array.isArray(board) || board.length < min || board.length > max)
      throw Error("Choose " + min + "–" + max + " advisors");
    const packets = {};
    for (const seat of board)
      packets[seat.id] = packet(seat.id, brief, this.root);
    validateBoard(board, packets, mode);
    const id =
      new Date()
        .toISOString()
        .replace(/[^0-9]/g, "")
        .slice(0, 14) +
      "-" +
      crypto.randomBytes(4).toString("hex");
    const s = {
      version: 1,
      id,
      created: new Date().toISOString(),
      brief,
      board,
      packets,
      mode,
      reviewMode: mode,
      status: "prepared",
      cards: {},
      events: [],
      usage: { usd: 0, reserved: 0, calls: 0 },
      error: null,
    };
    fs.mkdirSync(this.folder(id), { mode: 0o700 });
    this.event(s, "prepared", {
      message: "Council prepared from frozen first-hand evidence.",
    });
    this.save(s);
    return s;
  }
  event(s, type, data = {}) {
    s.events.push({
      seq: s.events.length + 1,
      type,
      t: new Date().toISOString(),
      ...data,
    });
  }
  save(s) {
    const folder = this.folder(s.id),
      tmp = path.join(folder, "session.tmp");
    fs.writeFileSync(tmp, JSON.stringify(s, null, 2), { mode: 0o600 });
    fs.renameSync(tmp, path.join(folder, "session.json"));
    fs.writeFileSync(
      path.join(folder, "brief.md"),
      "# Decision brief\n\n" +
        s.brief.question +
        "\n\n" +
        JSON.stringify(s.brief, null, 2),
    );
    fs.writeFileSync(
      path.join(folder, "council.json"),
      JSON.stringify(s.board, null, 2),
    );
    for (const [i, stage] of ["opening", "debate", "ratification"].entries())
      fs.writeFileSync(
        path.join(folder, `round-${i + 1}.md`),
        s.board
          .filter((a) => s.cards[stage + ":" + a.id])
          .map(
            (a) => "## " + a.id + "\n\n" + s.cards[stage + ":" + a.id].argument,
          )
          .join("\n\n"),
      );
    for (const stage of ["cruxes", "draft", "verdict"])
      if (s.cards[stage])
        fs.writeFileSync(
          path.join(folder, stage + ".json"),
          JSON.stringify(s.cards[stage], null, 2),
        );
    if (s.cards.verdict)
      fs.writeFileSync(path.join(folder, "verdict.md"), markdown(s));
  }
  mutate(id, fn) {
    const lock = path.join(this.folder(id), ".lock");
    let fd;
    try {
      fd = fs.openSync(lock, "wx");
    } catch {
      throw Error("Session is busy; retry this local operation");
    }
    try {
      const s = this.read(id);
      const result = fn(s);
      this.save(s);
      return result ?? s;
    } finally {
      fs.closeSync(fd);
      fs.unlinkSync(lock);
    }
  }
  submit(id, key, card, { internal = false } = {}) {
    return this.mutate(id, (s) => {
      if (s.status === "running" && !internal)
        throw Error("Pause the API runner before submitting external cards");
      if (s.pending)
        throw Error(
          "Resolve the pending paid request before submitting a card",
        );
      if (s.cards[key]) {
        if (JSON.stringify(s.cards[key]) === JSON.stringify(card)) return s;
        throw Error("Accepted cards are immutable");
      }
      const step = nextStep(s);
      if (!step || step.key !== key)
        throw Error("Expected " + (step?.key || "completed review"));
      validateCard(s, step, card);
      s.cards[key] = card;
      s.error = null;
      this.event(s, "card", {
        key,
        stage: step.stage,
        advisor: step.advisor,
        card,
      });
      if (!nextStep(s)) {
        s.status = "complete";
        this.event(s, "complete", { scores: weightedScores(s) });
      } else if (s.status !== "running") s.status = "prepared";
      return s;
    });
  }
  recover() {
    for (const row of this.list())
      this.mutate(row.id, (s) => {
        if (s.status === "running") {
          s.status = s.pending ? "needs_review" : "paused";
          s.error = s.pending
            ? "A request may have been charged before the server stopped. Its reservation is retained; no automatic retry."
            : "Server restarted. Resume from the next uncompleted step.";
          this.event(s, "paused", { message: s.error });
        }
      });
  }
}
export function publicSession(s) {
  return {
    ...s,
    packets: Object.fromEntries(
      Object.entries(s.packets).map(([id, p]) => [
        id,
        {
          ...p,
          evidence: p.evidence.map((e) => ({
            ...e,
            quote: e.quote.split(/\s+/).slice(0, 12).join(" ") + "…",
          })),
        },
      ]),
    ),
  };
}
