"""Advisor-building workflow for Den of Devs (host-agent supervised)."""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

from .pilot import (read_json, write_json, digest, canonical, get_source, normalize, SECTIONS, now)

SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def root_from_args(args):
    return Path(args.project).resolve() if getattr(args, "project", None) else Path.cwd()


def manifest_path(root, advisor_id):
    return root / ".collection" / "advisor-builds" / advisor_id / "manifest.json"


def load_manifest(root, advisor_id):
    p = manifest_path(root, advisor_id)
    if not p.exists():
        raise SystemExit(f"No manifest for advisor {advisor_id}")
    return read_json(p)


def save_manifest(root, manifest):
    write_json(manifest_path(root, manifest["advisor_id"]), manifest)


def cmd_prepare(args):
    root = root_from_args(args)
    aid = args.id
    if not SLUG_RE.match(aid):
        raise SystemExit("advisor id must be lowercase slug")
    mpath = manifest_path(root, aid)
    if mpath.exists() and not args.update:
        raise SystemExit(f"advisor {aid} already has a build manifest; use --update")
    roster_path = root / "collection" / "roster.json"
    roster = read_json(roster_path, {"developers": []})
    existing = [d for d in roster.get("developers", []) if d["id"] == aid]
    if existing and not args.update:
        raise SystemExit(f"advisor {aid} already registered in roster")
    manifest = {
        "advisor_id": aid,
        "name": args.name,
        "aliases": args.alias or [args.name],
        "focus": args.focus,
        "pillar": args.pillar,
        "depth": args.depth,
        "default_board": bool(args.default_board),
        "created_at": now(),
        "sources": [],
        "status": "prepared",
    }
    save_manifest(root, manifest)
    packet = {"advisor_id": aid, "task": "discovery",
              "instructions": "Find lawful first-hand source URLs for this developer. Submit via import command."}
    print(json.dumps({"manifest": str(mpath), "discovery_packet": packet}, indent=2))


def cmd_import(args):
    root = root_from_args(args)
    m = load_manifest(root, args.id)
    if args.text_file:
        text = Path(args.text_file).read_text()
        rec = {"url": args.url, "title": args.title, "text": text, "metadata": {}}
    else:
        src = get_source(args.url)
        rec = {"url": args.url, "title": src.get("metadata", {}).get("title", args.url),
               "text": src["text"], "metadata": src.get("metadata", {})}
    h = digest(normalize(rec["text"]))
    for s in m["sources"]:
        if s.get("text_sha256") == h:
            print(json.dumps({"status": "duplicate_text", "source_id": s["source_id"]}))
            return
    sid = args.id + "-" + digest(canonical(args.url))[:14]
    if any(s["source_id"] == sid for s in m["sources"]):
        print(json.dumps({"status": "duplicate_source", "source_id": sid}))
        return
    folder = root / ".collection" / "advisor-builds" / args.id / "sources" / sid
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "source.txt").write_text(rec["text"])
    source_rec = {"source_id": sid, "url": canonical(args.url), "title": rec["title"],
                  "text_sha256": h, "status": "imported", "metadata": rec.get("metadata", {}),
                  "candidate": {"url": args.url}}
    m["sources"].append(source_rec)
    m["status"] = "imported"
    save_manifest(root, m)
    print(json.dumps({"status": "imported", "source_id": sid}))


def cmd_extraction_packet(args):
    root = root_from_args(args)
    m = load_manifest(root, args.id)
    folder = root / ".collection" / "advisor-builds" / args.id / "sources" / args.source_id
    text = (folder / "source.txt").read_text()
    chunk_size = 40000
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)] or [text]
    part = args.part or 1
    chunk_text = chunks[part-1] if part <= len(chunks) else ""
    packet = {"advisor_id": args.id, "source_id": args.source_id, "part": part,
              "total_chunks": len(chunks), "text": chunk_text, "schema": "EXTRACTION"}
    print(json.dumps(packet))


def cmd_extraction_submit(args):
    root = root_from_args(args)
    m = load_manifest(root, args.id)
    data = json.loads(Path(args.file).read_text())
    folder = root / ".collection" / "advisor-builds" / args.id / "sources" / args.source_id
    text = (folder / "source.txt").read_text()
    ok = True
    errs = []
    for e in data.get("evidence", []):
        if e["quote"] not in text:
            ok = False
            errs.append("quote not found: " + e["quote"][:40])
    aliases = m["aliases"]
    for e in data.get("evidence", []):
        if e.get("attribution") == "speaker":
            if not any(a.lower() in (e.get("speaker") or "").lower() for a in aliases):
                ok = False
                errs.append("speaker mismatch")
    if not ok:
        print(json.dumps({"status": "rejected", "errors": errs}))
        return
    ext_path = folder / "extraction.json"
    existing = read_json(ext_path, {"parts_done": [], "evidence": [], "total_chunks": 1})
    part = args.part or 1
    if part in existing.get("parts_done", []):
        print(json.dumps({"status": "already_accepted", "source_id": args.source_id}))
        return
    existing.setdefault("parts_done", []).append(part)
    existing.setdefault("evidence", []).extend(data.get("evidence", []))
    existing["total_chunks"] = data.get("total_chunks", existing.get("total_chunks", 1))
    write_json(ext_path, existing)
    src = next(s for s in m["sources"] if s["source_id"] == args.source_id)
    src["status"] = "extracted" if len(set(existing["parts_done"])) == existing["total_chunks"] else "extracting"
    save_manifest(root, m)
    print(json.dumps({"status": "accepted", "source_id": args.source_id, "parts_done": existing["parts_done"]}))


def cmd_compilation_packet(args):
    root = root_from_args(args)
    m = load_manifest(root, args.id)
    all_ev = []
    for s in m["sources"]:
        folder = root / ".collection" / "advisor-builds" / args.id / "sources" / s["source_id"]
        ext = read_json(folder / "extraction.json", {})
        for e in ext.get("evidence", []):
            e = dict(e)
            e["source_id"] = s["source_id"]
            all_ev.append(e)
    packet = {"advisor_id": args.id, "evidence": all_ev, "schema": "COMPILATION", "sections": SECTIONS}
    print(json.dumps(packet))


def cmd_compilation_submit(args):
    root = root_from_args(args)
    m = load_manifest(root, args.id)
    data = json.loads(Path(args.file).read_text())
    sections = data.get("sections", [])
    names = [s["name"] for s in sections]
    if sorted(names) != sorted(SECTIONS):
        print(json.dumps({"status": "rejected", "errors": ["sections must be exactly the seven"]}))
        return
    all_ids = set()
    for s in m["sources"]:
        folder = root / ".collection" / "advisor-builds" / args.id / "sources" / s["source_id"]
        ext = read_json(folder / "extraction.json", {})
        for e in ext.get("evidence", []):
            all_ids.add(e.get("id"))
    for sec in sections:
        for item in sec.get("items", []):
            for eid in item.get("evidence_ids", []):
                if eid not in all_ids:
                    print(json.dumps({"status": "rejected", "errors": ["unknown evidence id " + str(eid)]}))
                    return
    compiled_path = root / ".collection" / "advisor-builds" / args.id / "compiled.json"
    write_json(compiled_path, data)
    m["status"] = "compiled"
    save_manifest(root, m)
    print(json.dumps({"status": "accepted"}))


def export_markdown(root, aid):
    base = root / ".collection" / "advisor-builds" / aid
    compiled = read_json(base / "compiled.json", {})
    outdir = root / "knowledge" / aid
    outdir.mkdir(parents=True, exist_ok=True)
    for sec in compiled.get("sections", []):
        (outdir / (sec["name"] + ".md")).write_text("# " + sec["name"] + "\n")
    (outdir / "sources.md").write_text("# sources\n")
    return outdir


def cmd_validate(args):
    root = root_from_args(args)
    m = load_manifest(root, args.id)
    gaps = []
    if len(m["sources"]) < 1:
        gaps.append("no sources")
    if m["depth"] in ("standard", "deep") and len(m["sources"]) < 2:
        gaps.append("thin depth")
    if gaps and not args.allow_gaps:
        print(json.dumps({"status": "invalid", "errors": gaps}))
        raise SystemExit(1)
    print(json.dumps({"status": "valid", "gaps": gaps}))


def cmd_register(args):
    root = root_from_args(args)
    m = load_manifest(root, args.id)
    roster_path = root / "collection" / "roster.json"
    roster = read_json(roster_path, {"developers": []})
    if any(d["id"] == args.id for d in roster.get("developers", [])):
        if not args.update:
            raise SystemExit("collision: advisor already registered")
    dev = {"id": args.id, "name": m["name"], "aliases": m["aliases"], "focus": m["focus"]}
    src_base = root / ".collection" / "advisor-builds" / args.id
    dst_base = root / ".collection" / "pilot" / args.id
    if dst_base.exists():
        shutil.rmtree(dst_base)
    shutil.copytree(src_base, dst_base)
    if not any(d["id"] == args.id for d in roster.get("developers", [])):
        roster["developers"].append(dev)
    else:
        for i, d in enumerate(roster["developers"]):
            if d["id"] == args.id:
                roster["developers"][i] = dev
    write_json(roster_path, roster)
    export_markdown(root, args.id)
    m["status"] = "registered"
    save_manifest(root, m)
    print(json.dumps({"status": "registered", "consult": f"node app/cli.mjs consult {args.id} --root {root}"}))


def cmd_update(args):
    root = root_from_args(args)
    m = load_manifest(root, args.id)
    m["status"] = "updating"
    save_manifest(root, m)
    print(json.dumps({"status": "update_ready"}))


def main():
    p = argparse.ArgumentParser(prog="python3 -m collection.advisor")
    p.add_argument("--project", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("prepare")
    s.add_argument("--id", required=True)
    s.add_argument("--name", required=True)
    s.add_argument("--alias", action="append")
    s.add_argument("--focus", required=True)
    s.add_argument("--pillar", default=None)
    s.add_argument("--depth", default="standard", choices=["quick", "standard", "deep"])
    s.add_argument("--default-board", action="store_true")
    s.add_argument("--update", action="store_true")
    s.set_defaults(func=cmd_prepare)
    s = sub.add_parser("import")
    s.add_argument("--id", required=True)
    s.add_argument("--url", required=True)
    s.add_argument("--text-file", default=None)
    s.add_argument("--title", default=None)
    s.add_argument("--author", default=None)
    s.add_argument("--date", default=None)
    s.set_defaults(func=cmd_import)
    s = sub.add_parser("extraction-packet")
    s.add_argument("--id", required=True)
    s.add_argument("--source-id", required=True)
    s.add_argument("--part", type=int, default=1)
    s.set_defaults(func=cmd_extraction_packet)
    s = sub.add_parser("extraction-submit")
    s.add_argument("--id", required=True)
    s.add_argument("--source-id", required=True)
    s.add_argument("--part", type=int, default=1)
    s.add_argument("--file", required=True)
    s.set_defaults(func=cmd_extraction_submit)
    s = sub.add_parser("compilation-packet")
    s.add_argument("--id", required=True)
    s.set_defaults(func=cmd_compilation_packet)
    s = sub.add_parser("compilation-submit")
    s.add_argument("--id", required=True)
    s.add_argument("--file", required=True)
    s.set_defaults(func=cmd_compilation_submit)
    s = sub.add_parser("validate")
    s.add_argument("--id", required=True)
    s.add_argument("--allow-gaps", action="store_true")
    s.set_defaults(func=cmd_validate)
    s = sub.add_parser("register")
    s.add_argument("--id", required=True)
    s.add_argument("--update", action="store_true")
    s.set_defaults(func=cmd_register)
    s = sub.add_parser("update")
    s.add_argument("--id", required=True)
    s.set_defaults(func=cmd_update)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
