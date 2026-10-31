"""Offline integrity audit of retained advisor knowledge; makes no API calls."""
from pathlib import Path
import json

from .expand import Expansion,work_key
from .pilot import read_json,normalize,digest,speaker_allowed,SECTIONS,caption_view,work_coverage,collection_fingerprint


def audit(project,config):
    collector=Expansion(project,config,None)
    errors=[];advisors=[]
    for dev in config['developers']:
        rows=[r for r in collector.records(dev) if r['status']=='accepted']
        evidence={};fingerprints=set();works=set()
        for r in rows:
            sid=r['source_id'];folder=collector.root/dev['id']/'sources'/sid
            if not (folder/'source.txt').exists():
                errors.append(sid+': missing source text');continue
            text=normalize((folder/'source.txt').read_text())
            prose=caption_view((folder/'source.txt').read_text())[0] if r.get('metadata',{}).get('duration_seconds') else text
            if digest(text)!=r['text_sha256']:errors.append(sid+': source hash mismatch')
            if r['text_sha256'] in fingerprints:errors.append(sid+': duplicate source text')
            key=r.get('work_key') or work_key(r['candidate'])
            if key!=work_key(r['candidate']):errors.append(sid+': work identity differs from the verified URL/candidate grouping')
            fingerprints.add(r['text_sha256']);works.add(key)
            completed=len(set(r['parts_done'])) if 'parts_done' in r else len(r.get('extractions',[]))
            if 'total_chunks' in r and completed!=r['total_chunks']:
                errors.append(sid+': accepted despite incomplete extraction')
            allowed={r['url'],r['metadata']['url']}|{p['url'] for p in r['metadata'].get('parts',[])}
            for e in r['evidence']:
                ident=e['id'];evidence[ident]=e;offset=e['passage_offset']
                if e['source_id']!=sid or e['developer']!=dev['id']:errors.append(ident+': source/advisor mismatch')
                view=prose if e.get('passage_view')=='caption-prose-v1' else text
                if view[offset:offset+len(e['quote'])]!=e['quote']:errors.append(ident+': quote/offset mismatch')
                if r.get('source_scope') and not any(a<=offset and offset+len(e['quote'])<=b for a,b in r['source_scope']['normalized_ranges']):
                    errors.append(ident+': quote outside verified source scope')
                if e['attribution']=='speaker' and not speaker_allowed(e['speaker'],dev.get('aliases',[dev['name']])):
                    errors.append(ident+': speaker mismatch')
                url=e.get('source_url',r['metadata']['url'])
                # Only evidence timestamp links may differ from the retrieved source URL.
                if url not in allowed and url.split('&t=')[0] not in allowed:errors.append(ident+': foreign source URL')
        compiled=read_json(collector.root/dev['id']/'compiled.json',{})
        if compiled.get('source_fingerprint'):
            if compiled['source_fingerprint']!=collection_fingerprint(rows):errors.append(dev['id']+': compilation predates the current accepted evidence/work grouping')
        elif config.get('require_compilation_fingerprint'):errors.append(dev['id']+': compilation snapshot is not established')
        sections=compiled.get('sections',[])
        if rows and sorted(s['name'] for s in sections)!=sorted(SECTIONS):errors.append(dev['id']+': missing knowledge sections')
        for section in sections:
            for item in section['items']:
                if not item['evidence_ids'] or any(i not in evidence for i in item['evidence_ids']):errors.append(dev['id']+': unknown compiled evidence')
            if not (Path(project)/'knowledge'/dev['id']/(section['name']+'.md')).exists():errors.append(dev['id']+': missing Markdown section')
        if rows and not (Path(project)/'knowledge'/dev['id']/'sources.md').exists():errors.append(dev['id']+': missing source index')
        elif rows:
            source_index=(Path(project)/'knowledge'/dev['id']/'sources.md').read_text()
            if any(r['source_id'] not in source_index for r in rows):errors.append(dev['id']+': source index omits accepted material')
        advisors.append({'id':dev['id'],'works':work_coverage(rows)[0],'source_representations':len(rows),'passages':len(evidence),'compiled_sections':len(sections)})
    jobs=collector.ledger.data['jobs']
    if any(j['status']!='recorded' for j in jobs.values()):errors.append('Unresolved paid request reservation')
    if collector.ledger.exposure()>collector.ledger.cap:errors.append(f'Cumulative budget exceeds ${collector.ledger.cap:g}')
    return {'ok':not errors,'errors':errors,'advisors':advisors,'cumulative_estimated_usd':collector.ledger.exposure()}


if __name__=='__main__':
    project=Path(__file__).resolve().parents[1]
    result=audit(project,read_json(project/'collection/roster.json'))
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['ok'] else 1)
