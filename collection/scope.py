"""Keep unrelated comments and archive messages out of coverage measurements."""
from __future__ import annotations
import re
from .pilot import normalize,speaker_allowed,digest


def normalized_span(raw,start,end):
    full=normalize(raw);segment=normalize(raw[start:end]);prefix=raw[:start]
    base=len(normalize(prefix))
    if prefix and raw[start:end] and (prefix[-1].isspace() or raw[start].isspace()):base+=1
    if full[base:base+len(segment)]!=segment:
        base=full.find(segment,max(0,base-2),base+len(segment)+2)
    if base<0:raise ValueError('Scope cannot be matched to its original snapshot')
    return [base,base+len(segment)]


def mail_sender_scope(raw,aliases):
    headers=list(re.finditer(r'(?m)^From:\s*([^\n]+?)\s+@\s+\d{4}-\d{2}-\d{2}',raw))
    ranges=[];messages=0
    for i,header in enumerate(headers):
        if not speaker_allowed(header.group(1),aliases):continue
        messages+=1;end=headers[i+1].start() if i+1<len(headers) else len(raw)
        block=raw[header.start():end];offset=header.start();run_start=None
        for line in block.splitlines(keepends=True):
            footer=bool(re.match(r'^\^ permalink|^Thread overview:',line))
            quoted=bool(re.match(r'^\s*>',line))
            if footer or quoted:
                if run_start is not None:
                    ranges.append(normalized_span(raw,run_start,offset));run_start=None
                if footer:break
            elif run_start is None:run_start=offset
            offset+=len(line)
        if run_start is not None:ranges.append(normalized_span(raw,run_start,offset))
    if not messages:raise ValueError('No explicitly attributed target messages found')
    return ranges,f'Coverage counts the unquoted material in {messages} explicitly attributed sender blocks, including their headers; unrelated thread messages are excluded. The full archive remains retained for audit.'


def apply_scope(record,raw,ranges,note):
    full=normalize(raw)
    if digest(full)!=record['text_sha256']:raise ValueError('Scope source hash mismatch')
    ranges=sorted([a,b] for a,b in ranges if b>a)
    if any(a<0 or b>len(full) for a,b in ranges) or any(ranges[i][1]>ranges[i+1][0] for i in range(len(ranges)-1)):
        raise ValueError('Invalid or overlapping source scope')
    good=[];bad=[]
    for e in record['evidence']:
        if any(a<=e['passage_offset'] and e['passage_offset']+len(e['quote'])<=b for a,b in ranges):good.append(e)
        else:bad.append({'reason':'Passage outside the verified primary-author/article scope','evidence_id':e['id']})
    record['evidence']=good;record['rejected_evidence']+=bad
    record['coverage_words']=sum(len(full[a:b].split()) for a,b in ranges)
    record['source_scope']={'normalized_ranges':ranges,'note':note,'source_sha256':record['text_sha256']}
    if not good:record['status']='held_out'
    return len(bad)
