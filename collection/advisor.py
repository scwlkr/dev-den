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
                    verify_evidence, SECTIONS, EXTRACTION, COMPILATION, now, Pilot,
                    work_coverage, collection_fingerprint)

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


def depth_thresholds(depth):
    return {"quick": (12, 80000), "standard": (30, 250000), "deep": (80, 500000)}[depth]

def canonical_records(root, aid):
    m = load_manifest(root, aid)
    records = []
    for src in m["sources"]:
        folder = build_root(root, aid) / "sources" / src["source_id"]
        if not (folder / "evidence.json").exists():
            continue
        r = read_json(folder / "evidence.json")
        if r.get("status") == "accepted":
            records.append(r)
    return m, records

def validate_build(root, aid, allow_gaps=False):
    m, records = canonical_records(root, aid)
    # integrity: recompute hashes/quotes
    errors = []
    for r in records:
        folder = build_root(root, aid) / "sources" / r["source_id"]
        text = (folder / "source.txt").read_text()
        if digest(normalize(text)) != r.get("text_sha256"):
            errors.append("hash mismatch " + r["source_id"])
        # quote offsets
        for e in r.get("evidence", []):
            if e.get("developer") != aid or e.get("source_id") != r["source_id"]:
                errors.append("ownership mismatch")
            view = text
            norm = normalize(view)
            q = normalize(e.get("quote",""))
            if norm[e.get("passage_offset",0):e.get("passage_offset",0)+len(q)] != q:
                errors.append("quote offset mismatch")
            if e.get("attribution") == "speaker":
                aliases = m.get("aliases", [])
                if not any(a.lower() in (e.get("speaker") or "").lower() for a in aliases):
                    errors.append("speaker mismatch")
            # metadata url
            if not r.get("metadata", {}).get("url"):
                errors.append("missing metadata url")
    # full integrity checks
    cp = build_root(root, aid) / "compiled.json"
    if not cp.exists():
        errors.append("not compiled")
        compiled = {}
    else:
        compiled = read_json(cp)
    # hash/quote checks via audit? minimal: check compiled refs
    all_ids = {e["id"] for r in records for e in r.get("evidence", [])}
    if compiled:
        names = [sec["name"] for sec in compiled.get("sections", [])]
        if sorted(names) != sorted(SECTIONS) or len(names) != len(set(names)):
            errors.append("bad sections")
        total_items = sum(len(sec.get("items", [])) for sec in compiled.get("sections", []))
        if total_items == 0:
            errors.append("empty compilation")
        for sec in compiled.get("sections", []):
            for item in sec.get("items", []):
                if not item.get("evidence_ids"):
                    errors.append("missing refs")
                for eid in item.get("evidence_ids", []):
                    if eid not in all_ids:
                        errors.append("unknown ref " + str(eid))
        # fingerprint
        if compiled.get("source_fingerprint") and compiled["source_fingerprint"] != collection_fingerprint(records):
            errors.append("stale fingerprint")
    works, words = work_coverage(records)
    tw, ww = depth_thresholds(m.get("depth", "standard"))
    depth_ok = works >= tw and words >= ww
    gaps = list(compiled.get("gaps", [])) if compiled else []
    if not depth_ok:
        gapmsg = f"Depth shortfall: {works}/{tw} works, {words}/{ww} words"
        if gapmsg not in gaps:
            gaps.append(gapmsg)
    if errors:
        return False, errors, m, records, compiled, works, words, tw, ww, depth_ok, gaps
    if not depth_ok and not allow_gaps:
        return False, ["depth shortfall"], m, records, compiled, works, words, tw, ww, depth_ok, gaps
    return True, [], m, records, compiled, works, words, tw, ww, depth_ok, gaps

def cmd_validate(args):
    root = root_from_args(args)
    aid = args.id
    validate_id(aid)
    ok, errors, m, records, compiled, works, words, tw, ww, depth_ok, gaps = validate_build(root, aid, args.allow_gaps)
    if not ok:
        print(json.dumps({"status": "invalid", "errors": errors, "gaps": gaps}))
        raise SystemExit(1)
    print(json.dumps({"status": "valid", "gaps": gaps, "works": works, "words": words}))

def cmd_register(args):
    root = root_from_args(args)
    aid = args.id
    validate_id(aid)
    allow_gaps = getattr(args, "allow_gaps", False)
    update = getattr(args, "update", False)
    ok, errors, m, records, compiled, works, words, tw, ww, depth_ok, gaps = validate_build(root, aid, allow_gaps)
    if not ok:
        print(json.dumps({"status": "invalid", "errors": errors, "gaps": gaps}))
        raise SystemExit(1)
    # depth gaps persist
    if not depth_ok:
        compiled["gaps"] = gaps
    # fingerprint
    compiled["source_fingerprint"] = collection_fingerprint(records)
    write_json(build_root(root, aid) / "compiled.json", compiled)

    roster_path = root / "collection" / "roster.json"
    roster = read_json(roster_path, {"developers": []})
    existing_entry = any(d["id"] == aid for d in roster.get("developers", []))
    if existing_entry and not update:
        raise SystemExit("collision: advisor already registered")
    # protect initial advisors without manifest? if update and no manifest? manifest exists by load.

    # early collision of destination
    dst_base = root / ".collection" / "pilot" / aid
    knowledge_dir = root / "knowledge" / aid
    if dst_base.exists() and not update:
        if dst_base.is_file() or knowledge_dir.is_file():
            raise SystemExit("destination exists")
    if knowledge_dir.exists() and not update and not knowledge_dir.is_dir():
        raise SystemExit("destination exists")

    # staging
    import tempfile, fcntl, os, shutil
    stage = Path(tempfile.mkdtemp(prefix="adv-stage-", dir=str(root)))
    try:
        stage_corpus = stage / "corpus"
        stage_knowledge = stage / "knowledge"
        stage_corpus.mkdir()
        stage_knowledge.mkdir()
        # copy build to stage corpus
        shutil.copytree(build_root(root, aid), stage_corpus / aid)
        # export markdown into stage knowledge using Pilot.export
        exporter = Pilot.__new__(Pilot)
        exporter.project = root
        exporter.root = stage_corpus
        exporter.config = {"model": "none"}
        out_k = stage_knowledge / aid
        out_k.mkdir()
        # temporarily point project knowledge? Pilot.export writes to self.project/knowledge. We'll instead call export then move.
        # Use a temp project root for export
        export_root = stage / "exportroot"
        export_root.mkdir()
        (export_root / "knowledge").mkdir()
        exporter.project = export_root
        exporter.export({"id": aid, "name": m["name"], "focus": m["focus"]}, records, compiled)
        # move exported knowledge
        for item in (export_root / "knowledge" / aid).iterdir():
            shutil.move(str(item), str(stage_knowledge / aid / item.name))

        # transactional publish under lock
        lock_path = root / ".collection" / "advisor.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            # backup roster
            roster_bytes = roster_path.read_bytes() if roster_path.exists() else b""
            # publish corpus
            if dst_base.exists():
                if update:
                    # rename existing to backup
                    backup = stage / "backup_corpus"
                    if backup.exists():
                        shutil.rmtree(backup)
                    dst_base.rename(backup)
                else:
                    raise SystemExit("destination exists")
            try:
                shutil.move(str(stage_corpus / aid), str(dst_base))
            except Exception:
                # restore
                if (stage / "backup_corpus").exists():
                    (stage / "backup_corpus").rename(dst_base)
                raise
            # publish knowledge
            if knowledge_dir.exists():
                if update:
                    backupk = stage / "backup_knowledge"
                    if backupk.exists():
                        shutil.rmtree(backupk)
                    knowledge_dir.rename(backupk)
                else:
                    # remove newly created corpus? rollback
                    if dst_base.exists() and not existing_entry:
                        shutil.rmtree(dst_base)
                    raise SystemExit("destination exists")
            try:
                shutil.move(str(stage_knowledge / aid), str(knowledge_dir))
            except Exception:
                if (stage / "backup_knowledge").exists():
                    (stage / "backup_knowledge").rename(knowledge_dir)
                raise
            # roster last
            dev = {"id": aid, "name": m["name"], "aliases": m["aliases"], "focus": m["focus"]}
            if not existing_entry:
                roster["developers"].append(dev)
            else:
                for i, d in enumerate(roster["developers"]):
                    if d["id"] == aid:
                        roster["developers"][i] = dev
            write_json(roster_path, roster)
            fcntl.flock(lf, fcntl.LOCK_UN)
        m["status"] = "registered"
        save_manifest(root, m)
        print(json.dumps({"status": "registered", "consult": f"node app/cli.mjs consult BRIEF.json {aid}"}))
    except SystemExit as e:
        raise
    except Exception as e:
        print(json.dumps({"status": "error", "errors": [str(e)]}))
        raise SystemExit(1)
    finally:
        shutil.rmtree(stage, ignore_errors=True)

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
