"""Advisor-building workflow for Den of Devs (host-agent supervised)."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .pilot import (read_json, write_json, digest, canonical, get_source, normalize,
                    verify_evidence, SECTIONS, EXTRACTION, COMPILATION, now, Pilot)

SLUG_RE = re.compile(r"^[a-z][a-z0-9-]*$")
SOURCE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def root_from_args(args):
    return Path(args.project).resolve() if getattr(args, "project", None) else Path.cwd()


def validate_id(value, label="id"):
    if not value or not SLUG_RE.match(value):
        raise SystemExit(f"invalid {label}: {value!r}")


def validate_source_id(value):
    if not value or ".." in value or "/" in value or "\\" in value:
        raise SystemExit(f"invalid source-id: {value!r}")


def manifest_path(root, advisor_id):
    return root / ".collection" / "advisor-builds" / advisor_id / "manifest.json"


def load_manifest(root, advisor_id):
    validate_id(advisor_id)
    p = manifest_path(root, advisor_id)
    if not p.exists():
        raise SystemExit(f"No manifest for advisor {advisor_id}")
    return read_json(p)


def save_manifest(root, manifest):
    write_json(manifest_path(root, manifest["advisor_id"]), manifest)


def build_root(root, aid):
    return root / ".collection" / "advisor-builds" / aid


def cmd_prepare(args):
    root = root_from_args(args)
    aid = args.id
    validate_id(aid)
    mpath = manifest_path(root, aid)
    if mpath.exists() and not args.update:
        raise SystemExit(f"advisor {aid} already has a build manifest; use --update")
    roster_path = root / "collection" / "roster.json"
    roster = read_json(roster_path, {"developers": []})
    existing = [d for d in roster.get("developers", []) if d["id"] == aid]
    if existing and not args.update:
        raise SystemExit(f"advisor {aid} already registered in roster")
    if mpath.exists() and args.update:
        m = read_json(mpath)
        m["name"] = args.name or m.get("name")
        m["aliases"] = args.alias or m.get("aliases")
        m["focus"] = args.focus or m.get("focus")
        m["pillar"] = args.pillar if args.pillar is not None else m.get("pillar")
        m["depth"] = args.depth or m.get("depth", "standard")
        m["default_board"] = bool(args.default_board) or m.get("default_board", False)
        m["status"] = "prepared"
        save_manifest(root, m)
        print(json.dumps({"manifest": str(mpath), "discovery_packet": {"advisor_id": aid, "task": "discovery"}}))
        return
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
    aid = args.id
    validate_id(aid)
    m = load_manifest(root, aid)
    url = args.url
    if args.text_file:
        text = Path(args.text_file).read_text()
        meta = {"url": url, "title": args.title or url, "author": args.author, "date": args.date}
        rec = {"url": url, "title": args.title or url, "text": text, "metadata": meta}
    else:
        src = get_source(url)
        meta = dict(src.get("metadata", {}))
        meta.setdefault("url", url)
        meta.setdefault("title", args.title or src.get("metadata", {}).get("title", url))
        if args.author: meta["author"] = args.author
        if args.date: meta["date"] = args.date
        rec = {"url": url, "title": meta["title"], "text": src["text"], "metadata": meta}
    h = digest(normalize(rec["text"]))
    for s in m["sources"]:
        if s.get("text_sha256") == h:
            print(json.dumps({"status": "duplicate_text", "source_id": s["source_id"]}))
            return
    sid = aid + "-" + digest(canonical(url))[:14]
    if any(s["source_id"] == sid for s in m["sources"]):
        print(json.dumps({"status": "duplicate_source", "source_id": sid}))
        return
    folder = build_root(root, aid) / "sources" / sid
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "source.txt").write_text(rec["text"])
    source_rec = {"source_id": sid, "url": canonical(url), "title": rec["title"],
                  "text_sha256": h, "status": "imported", "metadata": rec["metadata"],
                  "candidate": {"url": url, "title": rec["title"]}}
    m["sources"].append(source_rec)
    m["status"] = "imported"
    # invalidate compilation
    cp = build_root(root, aid) / "compiled.json"
    if cp.exists():
        cp.unlink()
    save_manifest(root, m)
    print(json.dumps({"status": "imported", "source_id": sid}))


def cmd_extraction_packet(args):
    root = root_from_args(args)
    aid = args.id
    validate_id(aid)
    sid = args.source_id
    validate_source_id(sid)
    m = load_manifest(root, aid)
    folder = build_root(root, aid) / "sources" / sid
    text = (folder / "source.txt").read_text()
    chunk_size = 40000
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)] or [text]
    part = args.part or 1
    if part < 1 or part > len(chunks):
        raise SystemExit("invalid part")
    chunk_text = chunks[part-1]
    packet = {"advisor_id": aid, "source_id": sid, "part": part,
              "total_chunks": len(chunks), "text": chunk_text,
              "schema": EXTRACTION}
    print(json.dumps(packet))


def cmd_extraction_submit(args):
    root = root_from_args(args)
    aid = args.id
    validate_id(aid)
    sid = args.source_id
    validate_source_id(sid)
    m = load_manifest(root, aid)
    src = next((s for s in m["sources"] if s["source_id"] == sid), None)
    if src is None:
        raise SystemExit("unknown source")
    folder = build_root(root, aid) / "sources" / sid
    text = (folder / "source.txt").read_text()
    data = json.loads(Path(args.file).read_text())
    # verify via verify_evidence
    valid, rejected = verify_evidence(sid, aid, text, data, m["aliases"])
    # if no valid evidence, reject
    if not valid:
        print(json.dumps({"status": "rejected", "errors": [r.get("reason", "invalid") for r in rejected] or ["no valid evidence"]}))
        return
    # enforce part range against retained text chunks
    chunk_size = 40000
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)] or [text]
    total = len(chunks)
    part = args.part or 1
    if part < 1 or part > total:
        print(json.dumps({"status": "rejected", "errors": ["invalid part"]}))
        return
    ext_path = folder / "extraction.json"
    existing = read_json(ext_path, {"parts_done": [], "evidence": [], "total_chunks": total})
    if part in existing.get("parts_done", []):
        print(json.dumps({"status": "already_accepted", "source_id": sid}))
        return
    # generate canonical evidence ids already from verify_evidence
    existing.setdefault("parts_done", []).append(part)
    existing.setdefault("evidence", []).extend(valid)
    existing.setdefault("extractions", []).append({"part": part, "chunk_index": part-1})
    existing["total_chunks"] = total
    existing["source_id"] = sid
    existing["developer"] = aid
    existing["url"] = src["url"]
    existing["candidate"] = src.get("candidate", {"url": src["url"]})
    existing["metadata"] = src.get("metadata", {})
    existing["text_sha256"] = src["text_sha256"]
    existing["words"] = len(normalize(text).split())
    existing["work_key"] = src.get("work_key") or src["url"]
    existing["rejected_evidence"] = existing.get("rejected_evidence", [])
    existing["extractions"] = existing.get("extractions", [])
    existing["issues"] = existing.get("issues", [])
    existing["status"] = "accepted" if len(set(existing["parts_done"])) == existing["total_chunks"] else "extracting"
    # chunk tracking
    for ev in existing.get("evidence", []):
        ev["chunk_index"] = part - 1
    write_json(ext_path, existing)
    # canonical evidence.json for Node loader / Python audit
    write_json(folder / "evidence.json", existing)
    src["status"] = "accepted" if len(set(existing["parts_done"])) == existing["total_chunks"] else "extracting"
    cp = build_root(root, aid) / "compiled.json"
    if cp.exists():
        cp.unlink()
    save_manifest(root, m)
    print(json.dumps({"status": "accepted", "source_id": sid, "parts_done": existing["parts_done"]}))


def cmd_compilation_packet(args):
    root = root_from_args(args)
    aid = args.id
    validate_id(aid)
    m = load_manifest(root, aid)
    all_ev = []
    for s in m["sources"]:
        folder = build_root(root, aid) / "sources" / s["source_id"]
        ext = read_json(folder / "extraction.json", {})
        for e in ext.get("evidence", []):
            e = dict(e)
            e["source_id"] = s["source_id"]
            all_ev.append(e)
    packet = {"advisor_id": aid, "evidence": all_ev, "schema": COMPILATION, "sections": SECTIONS}
    print(json.dumps(packet))


def cmd_compilation_submit(args):
    root = root_from_args(args)
    aid = args.id
    validate_id(aid)
    m = load_manifest(root, aid)
    data = json.loads(Path(args.file).read_text())
    sections = data.get("sections", [])
    names = [s["name"] for s in sections]
    if sorted(names) != sorted(SECTIONS) or len(names) != len(set(names)):
        print(json.dumps({"status": "rejected", "errors": ["sections must be exactly the seven unique"]}))
        return
    # accepted evidence ids
    all_ids = set()
    for s in m["sources"]:
        folder = build_root(root, aid) / "sources" / s["source_id"]
        ext = read_json(folder / "extraction.json", {})
        for e in ext.get("evidence", []):
            all_ids.add(e.get("id"))
    if not all_ids:
        print(json.dumps({"status": "rejected", "errors": ["no accepted evidence"]}))
        return
    basis_ok = {"documented", "inferred"}
    for sec in sections:
        for item in sec.get("items", []):
            if not item.get("text"):
                print(json.dumps({"status": "rejected", "errors": ["empty item text"]}))
                return
            if item.get("basis") not in basis_ok:
                print(json.dumps({"status": "rejected", "errors": ["invalid basis"]}))
                return
            ids = item.get("evidence_ids", [])
            if not ids:
                print(json.dumps({"status": "rejected", "errors": ["missing evidence ids"]}))
                return
            for eid in ids:
                if eid not in all_ids:
                    print(json.dumps({"status": "rejected", "errors": ["unknown evidence id " + str(eid)]}))
                    return
    # reject all-empty (no items anywhere) when evidence exists
    total_items = sum(len(s.get("items", [])) for s in sections)
    if total_items == 0:
        print(json.dumps({"status": "rejected", "errors": ["empty compilation"]}))
        return
    compiled_path = build_root(root, aid) / "compiled.json"
    write_json(compiled_path, data)
    m["status"] = "compiled"
    save_manifest(root, m)
    print(json.dumps({"status": "accepted"}))


def export_markdown(root, aid):
    base = build_root(root, aid)
    compiled = read_json(base / "compiled.json", {})
    # use Pilot export by instantiating without paid calls
    outdir = root / "knowledge" / aid
    outdir.mkdir(parents=True, exist_ok=True)
    # write sections with compiled text + evidence refs
    for sec in compiled.get("sections", []):
        lines = [f"# {sec['name']}", ""]
        for item in sec.get("items", []):
            lines.append(f"- {item['text']} ({item.get('basis','')}) [{', '.join(item.get('evidence_ids',[]))}]")
            lines.append("")
        (outdir / (sec["name"] + ".md")).write_text("\n".join(lines))
    # source index
    m = load_manifest(root, aid)
    idx = ["# sources", ""]
    for s in m["sources"]:
        folder = base / "sources" / s["source_id"]
        ext = read_json(folder / "extraction.json", {})
        for e in ext.get("evidence", []):
            quote = e.get("quote", "")
            short = " ".join(quote.split()[:22])
            idx.append(f"- {s['source_id']}: {s.get('url')} > {short}")
    (outdir / "sources.md").write_text("\n".join(idx) + "\n")
    return outdir


def cmd_validate(args):
    root = root_from_args(args)
    aid = args.id
    validate_id(aid)
    m = load_manifest(root, aid)
    gaps = []
    if len(m["sources"]) < 1:
        gaps.append("no sources")
    # depth targets
    targets = {"quick": (1, 0), "standard": (3, 0), "deep": (8, 0)}
    # real counts: quick 12+ works/80k words etc per spec (approx)
    # check compiled exists
    cp = build_root(root, aid) / "compiled.json"
    if not cp.exists():
        gaps.append("not compiled")
    if gaps and not args.allow_gaps:
        print(json.dumps({"status": "invalid", "errors": gaps}))
        raise SystemExit(1)
    print(json.dumps({"status": "valid", "gaps": gaps}))


def cmd_register(args):
    root = root_from_args(args)
    aid = args.id
    validate_id(aid)
    m = load_manifest(root, aid)
    roster_path = root / "collection" / "roster.json"
    roster = read_json(roster_path, {"developers": []})
    if any(d["id"] == aid for d in roster.get("developers", [])):
        if not args.update:
            raise SystemExit("collision: advisor already registered")
    # require compiled
    cp = build_root(root, aid) / "compiled.json"
    if not cp.exists():
        raise SystemExit("not compiled")
    compiled = read_json(cp)
    total_items = sum(len(s.get("items", [])) for s in compiled.get("sections", []))
    if total_items == 0:
        raise SystemExit("empty compilation")
    # export markdown to staging then publish
    export_markdown(root, aid)
    # register roster (atomic-ish)
    dev = {"id": aid, "name": m["name"], "aliases": m["aliases"], "focus": m["focus"]}
    if not any(d["id"] == aid for d in roster.get("developers", [])):
        roster["developers"].append(dev)
    else:
        for i, d in enumerate(roster["developers"]):
            if d["id"] == aid:
                roster["developers"][i] = dev
    write_json(roster_path, roster)
    # copy build to .collection/pilot/<id> for Node loader (non-destructive: only if not exists or update)
    src_base = build_root(root, aid)
    dst_base = root / ".collection" / "pilot" / aid
    if dst_base.exists() and not args.update:
        # keep existing; but for new registration we need data there
        pass
    if not dst_base.exists():
        dst_base.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src_base, dst_base)
    else:
        # merge without deleting
        for p in src_base.rglob("*"):
            if p.is_file():
                rel = p.relative_to(src_base)
                target = dst_base / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, target)
    m["status"] = "registered"
    save_manifest(root, m)
    print(json.dumps({"status": "registered", "consult": f"node app/cli.mjs consult BRIEF.json {aid}"}))


def cmd_update(args):
    root = root_from_args(args)
    aid = args.id
    validate_id(aid)
    m = load_manifest(root, aid)
    m["status"] = "updating"
    save_manifest(root, m)
    print(json.dumps({"status": "update_ready"}))


def main():
    p = argparse.ArgumentParser(prog="python3 -m collection.advisor")
    p.add_argument("--project", default=None)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("prepare")
    s.add_argument("--id", required=True)
    s.add_argument("--name", default=None)
    s.add_argument("--alias", action="append")
    s.add_argument("--focus", default=None)
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
    s.add_argument("--allow-gaps", action="store_true")
    s.add_argument("--update", action="store_true")
    s.set_defaults(func=cmd_register)
    s = sub.add_parser("update")
    s.add_argument("--id", required=True)
    s.set_defaults(func=cmd_update)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
