import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { ROOT } from "./knowledge.mjs";
export const defaultRates = {
  input: 1,
  output: 5,
  cached: 0.05,
  write: 1.25,
  longWrite: 2.5,
};
export function cost(usage, rates = defaultRates) {
  const n = usage?.input_tokens,
    out = usage?.output_tokens,
    d = usage?.input_tokens_details || {},
    cached = d.cached_tokens || 0,
    writes = d.cache_write_tokens || 0,
    long = d.cache_write_tokens_details?.ttl_12h_tokens || 0;
  if (
    ![n, out, cached, writes, long].every(Number.isInteger) ||
    Math.min(n, out, cached, writes, long, n - cached - writes) < 0 ||
    long > writes
  )
    throw Error("Missing or inconsistent usage; reservation retained");
  return (
    (((n - cached - writes) * rates.input +
      cached * rates.cached +
      (writes - long) * rates.write +
      long * rates.longWrite) *
      (n > 272000 ? 2 : 1)) /
      1e6 +
    (out * rates.output * (n > 272000 ? 1.5 : 1)) / 1e6
  );
}
let mountedKey;
async function keyFromMount() {
  if (mountedKey) return mountedKey;
  const data = await new Promise((resolve, reject) => {
    const stream = fs.createReadStream(path.join(ROOT, ".env"), {
      encoding: "utf8",
    });
    let data = "";
    const timer = setTimeout(() => {
      stream.destroy();
      reject(
        Error(
          "1Password environment did not respond; use the mounted environment or an exported API key",
        ),
      );
    }, 12000);
    stream.on("data", (chunk) => {
      data += chunk;
      if (data.length > 64000) stream.destroy(Error("Environment too large"));
    });
    stream.on("error", (e) => {
      clearTimeout(timer);
      reject(Error("No readable API environment"));
    });
    stream.on("end", () => {
      clearTimeout(timer);
      resolve(data);
    });
  });
  const match = data.match(
    /^(?:export\s+)?OPENAI_API_KEY\s*=\s*["']?([^\s"']+)/m,
  );
  if (!match) throw Error("OPENAI_API_KEY missing from mounted environment");
  mountedKey = match[1];
  return mountedKey;
}
export function providerConfig() {
  const kind = process.env.DEN_PROVIDER || "openai",
    model = process.env.DEN_MODEL || "gpt-6.1-terra";
  const base = process.env.DEN_API_BASE || "https://api.openai.com/v1";
  if (!["openai", "compatible", "anthropic"].includes(kind))
    throw Error("Unsupported provider adapter");
  let rates = defaultRates;
  if (
    kind !== "openai" ||
    base !== "https://api.openai.com/v1" ||
    model !== "gpt-6.1-terra"
  ) {
    try {
      rates = JSON.parse(process.env.DEN_RATES || "");
      if (
        !["input", "output", "cached", "write", "longWrite"].every(
          (k) => Number.isFinite(rates[k]) && rates[k] >= 0,
        )
      )
        throw Error();
    } catch {
      throw Error("Set DEN_RATES for this model/provider before paid reviews");
    }
  }
  return { kind, model, base, rates };
}
export function requestFor(config, p) {
  const content = JSON.stringify({
    brief: p.brief,
    board: p.board,
    evidence: p.evidence,
    prior: p.prior,
    weighted_scores: p.weighted_scores,
  });
  const max = 2200;
  if (config.kind === "openai")
    return {
      model: config.model,
      instructions: p.instructions,
      input: content,
      max_output_tokens: max,
      text: {
        format: {
          type: "json_schema",
          name: "den_card",
          strict: true,
          schema: p.schema,
        },
      },
    };
  if (config.kind === "compatible")
    return {
      model: config.model,
      messages: [
        { role: "system", content: p.instructions },
        { role: "user", content },
      ],
      max_tokens: max,
      response_format: {
        type: "json_schema",
        json_schema: { name: "den_card", strict: true, schema: p.schema },
      },
    };
  return {
    model: config.model,
    system: p.instructions,
    messages: [{ role: "user", content }],
    max_tokens: max,
    output_config: { format: { type: "json_schema", schema: p.schema } },
  };
}
export async function invoke(config, request) {
  const key =
    config.kind === "anthropic"
      ? process.env.ANTHROPIC_API_KEY
      : process.env.OPENAI_API_KEY || (await keyFromMount());
  if (!key) throw Error("Provider API key not configured");
  const url =
    config.base.replace(/\/$/, "") +
    (config.kind === "anthropic"
      ? "/messages"
      : config.kind === "compatible"
        ? "/chat/completions"
        : "/responses");
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(config.kind === "anthropic"
          ? { "x-api-key": key, "anthropic-version": "2023-06-01" }
          : { Authorization: "Bearer " + key }),
      },
      body: JSON.stringify(request),
      signal: AbortSignal.timeout(240000),
    });
  } catch {
    throw Error(
      "Provider connection ended without a confirmed outcome; no automatic retry",
    );
  }
  if (!response.ok) {
    const e = Error(
      "Provider HTTP " + response.status + "; no automatic retry",
    );
    e.definite = [400, 401, 403, 404, 422, 429].includes(response.status);
    throw e;
  }
  const data = await response.json();
  let text, usage;
  if (config.kind === "openai") {
    text = data.output
      ?.flatMap((o) => o.content || [])
      .filter((c) => c.type === "output_text")
      .map((c) => c.text)
      .join("");
    usage = data.usage;
  } else if (config.kind === "compatible") {
    text = data.choices?.[0]?.message?.content;
    usage = {
      input_tokens: data.usage?.prompt_tokens,
      output_tokens: data.usage?.completion_tokens,
      input_tokens_details: data.usage?.prompt_tokens_details,
    };
  } else {
    text = data.content
      ?.filter((c) => c.type === "text")
      .map((c) => c.text)
      .join("");
    const u = data.usage || {};
    usage = {
      input_tokens:
        (u.input_tokens || 0) +
        (u.cache_read_input_tokens || 0) +
        (u.cache_creation_input_tokens || 0),
      output_tokens: u.output_tokens,
      input_tokens_details: {
        cached_tokens: u.cache_read_input_tokens || 0,
        cache_write_tokens: u.cache_creation_input_tokens || 0,
        cache_write_tokens_details: { ttl_12h_tokens: 0 },
      },
    };
  }
  return { id: data.id, text, usage };
}
export class Ledger {
  constructor(
    file = path.join(ROOT, ".den/usage.json"),
    cap = Number(process.env.DEN_RUNTIME_BUDGET || 0.75),
  ) {
    this.file = file;
    this.cap = cap;
    if (!Number.isFinite(cap) || cap <= 0)
      throw Error("Invalid runtime budget");
    fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 });
  }
  read() {
    return fs.existsSync(this.file)
      ? JSON.parse(fs.readFileSync(this.file, "utf8"))
      : { jobs: {} };
  }
  save(d) {
    fs.writeFileSync(this.file + ".tmp", JSON.stringify(d, null, 2), {
      mode: 0o600,
    });
    fs.renameSync(this.file + ".tmp", this.file);
  }
  exposure() {
    return Object.values(this.read().jobs).reduce(
      (n, j) => n + (j.cost ?? j.reservation),
      0,
    );
  }
  reserve(session, key, request, config, sessionCap) {
    const d = this.read(),
      id = session.id + ":" + key;
    if (d.jobs[id])
      throw Error(
        "This paid step already has an outcome or unresolved reservation; use its retained response or an external validated card",
      );
    const bound = Buffer.byteLength(JSON.stringify(request)) + 4096;
    const reservation =
      (bound * Math.max(config.rates.input * 2.5, config.rates.longWrite * 2)) /
        1e6 +
      ((request.max_output_tokens || request.max_tokens) *
        config.rates.output *
        1.5) /
        1e6;
    if (
      this.exposure() + reservation > this.cap ||
      session.usage.usd + session.usage.reserved + reservation > sessionCap
    )
      throw Error(
        "Budget stop: the next conservative reservation would exceed the runtime cap",
      );
    d.jobs[id] = {
      session: session.id,
      key,
      status: "reserved",
      reservation,
      started: new Date().toISOString(),
      provider: config.kind,
      model: config.model,
      request_hash: crypto
        .createHash("sha256")
        .update(JSON.stringify(request))
        .digest("hex"),
    };
    this.save(d);
    return { id, reservation };
  }
  finish(id, response, config) {
    const d = this.read(),
      job = d.jobs[id],
      actual = cost(response.usage, config.rates);
    job.cost = actual;
    job.usage = response.usage;
    job.response_id = response.id;
    job.response_text = response.text;
    job.status = "recorded";
    this.save(d);
    if (actual > job.reservation + 0.000001)
      throw Error("Actual usage exceeded reservation; stop for billing review");
    return actual;
  }
  rejected(id) {
    const d = this.read();
    d.jobs[id].status = "rejected";
    d.jobs[id].cost = 0;
    this.save(d);
  }
}
