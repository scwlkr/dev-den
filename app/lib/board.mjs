import fs from "node:fs";
import path from "node:path";
import { ROOT, metadata } from "./knowledge.mjs";
export const DEFAULT_BOARD = ["dhh", "tobi", "primeagen", "carmack", "linus"];
export function boardPrefPath(root = ROOT) {
  return path.join(root, ".den", "board.json");
}
export function defaultBoardPrefs(root = ROOT) {
  const ids=metadata(root).map(a=>a.id);const preferred=DEFAULT_BOARD.filter(id=>ids.includes(id));
  return {board:"default",default:preferred.length?preferred:ids.slice(0,5),seats:ids};
}
export function loadBoardPrefs(root = ROOT) {
  const p = boardPrefPath(root);
  if (!fs.existsSync(p)) return defaultBoardPrefs(root);
  const prefs = JSON.parse(fs.readFileSync(p, "utf8"));
  validateBoardPrefs(prefs, root);
  return prefs;
}
export function validateBoardPrefs(prefs, root = ROOT) {
  const ids = new Set(metadata(root).map((a) => a.id));
  if (!prefs || typeof prefs !== "object") throw Error("Board preferences must be an object");
  if (!["ask", "auto", "default"].includes(prefs.board)) throw Error("board must be ask, auto, or default");
  if (!Array.isArray(prefs.default) || !prefs.default.length || prefs.default.length > 9) throw Error("default board must contain 1-9 advisors");
  if (new Set(prefs.default).size !== prefs.default.length) throw Error("default board cannot contain duplicates");
  if (prefs.default.some((id) => !ids.has(id))) throw Error("Unknown advisor in default board");
  if (prefs.seats && (!Array.isArray(prefs.seats) || prefs.seats.some((id) => !ids.has(id)))) throw Error("Unknown advisor in seats");
  return true;
}
export function saveBoardPrefs(prefs, root = ROOT) {
  validateBoardPrefs(prefs, root);
  const p = boardPrefPath(root);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  const tmp = p + ".tmp";
  fs.writeFileSync(tmp, JSON.stringify(prefs, null, 2));
  fs.renameSync(tmp, p);
}
export function resolveBoard({ brief, prefs, explicit, mode = "normal", root = ROOT }) {
  validateBoardPrefs(prefs || defaultBoardPrefs(root), root);
  if (explicit) {
    if (!Array.isArray(explicit)) throw Error("Explicit board must be an array");
    if (explicit.length > 9) throw Error("Selected review cannot contain more than 9 advisors");
    return explicit;
  }
  const policy = (prefs || {}).board || "ask";
  if (policy === "ask") throw Error("Board selection required: policy is ask; pass an explicit board");
  if (policy === "default") {
    return (prefs.default || DEFAULT_BOARD).map((id) => ({ id, weight: 1, reason: "Default board preference." }));
  }
  // auto
  return null; // caller uses recommend
}
