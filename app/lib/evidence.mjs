import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {corpusFingerprint,searchEvidence,normalize} from './knowledge.mjs';
const digest=s=>crypto.createHash('sha256').update(s).digest('hex');
export function retrieveEvidence(store,id,advisor,query,limit=6){
 if(typeof query!=='string'||query.trim().length<3||query.length>2000)throw Error('Provide a prepared-evidence query of 3–2,000 characters');
 if(!Number.isInteger(limit)||limit<1||limit>20)throw Error('Evidence limit must be 1–20');
 let result;
 store.mutate(id,s=>{
  if(s.pending||s.status==='running')throw Error('Pause the runner and finish its pending contribution before refining evidence');
  if(s.status==='complete')throw Error('Completed reviews are immutable; prepare a follow-up review with the new question');
  if(!s.board.some(a=>a.id===advisor))throw Error('Evidence advisor must belong to this council');
  const p=s.packets[advisor];
  if(!p.corpusFingerprint)throw Error('Legacy review has no corpus snapshot; start a follow-up review to refine evidence safely');
  if(corpusFingerprint(advisor,store.root)!==p.corpusFingerprint)throw Error('Prepared corpus changed since this review was created');
  const found=searchEvidence(advisor,query,{limit},store.root),existing=new Map(p.evidence.map(e=>[e.id,e])),added=[];
  for(const e of found.results){
   if(e.developer!==advisor||!e.source_id.startsWith(advisor+'-')||!/^https?:\/\//.test(e.url))throw Error('Foreign evidence was rejected');
   const base=path.join(store.root,'.collection/pilot',advisor,'sources',e.source_id);
   const r=JSON.parse(fs.readFileSync(path.join(base,'evidence.json'),'utf8'));
   const text=normalize(fs.readFileSync(path.join(base,'source.txt'),'utf8'));
   if(r.status!=='accepted'||r.developer!==advisor||r.source_id!==e.source_id||digest(text)!==e.source_hash||r.text_sha256!==e.source_hash)throw Error('Prepared source hash or ownership changed');
   const canonical=r.evidence.find(x=>x.id===e.id);
   const view=canonical?.passage_view==='caption-prose-v1'?normalize(text.replace(/\[\d{2}:\d{2}:\d{2}\]/g,' ')):text;
   if(!canonical||canonical.quote!==e.quote||Array.from(view).slice(canonical.passage_offset,canonical.passage_offset+Array.from(e.quote).length).join('')!==e.quote)throw Error('Prepared quote membership changed');
   if(r.source_scope&&!r.source_scope.normalized_ranges.some(([a,b])=>a<=canonical.passage_offset&&canonical.passage_offset+Array.from(e.quote).length<=b))throw Error('Quote is outside the original attribution scope');
   if(!existing.has(e.id)){const copy={...e};delete copy.score;p.evidence.push(copy);existing.set(copy.id,copy);added.push(copy.id);}
  }
  if(p.evidence.length>160)throw Error('Review evidence budget reached; use a more focused follow-up review');
  const retrieval={advisor,query:query.trim(),added,corpusFingerprint:p.corpusFingerprint,t:new Date().toISOString()};
  s.retrievals??=[];s.retrievals.push(retrieval);store.event(s,'retrieval',retrieval);
  result={added,results:found.results,no_match:found.no_match,limitations:found.limitations,session:s};
 });
 return result;
}
