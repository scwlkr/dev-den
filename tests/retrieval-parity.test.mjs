import {test} from 'node:test';
import assert from 'node:assert/strict';
import {packet,roster} from '../app/lib/knowledge.mjs';
test('actual all-advisor packets respect the total serialized budget and retain complete claim support',()=>{
 for(const d of roster()){
  const p=packet(d.id,{question:'Compare implementation simplicity, maintainability and performance for a small browser app',options:['TypeScript','Python','Rust']},undefined,{budget:48000});
  assert.ok(JSON.stringify(p).length<=48000,d.id+' packet exceeds total budget: '+JSON.stringify(p).length);
  const ids=new Set(p.evidence.map(e=>e.id));
  for(const item of [...p.working_context,...p.voice_guidance,...p.knowledge.flatMap(s=>s.items)])assert.ok(item.evidence_ids.length&&item.evidence_ids.every(id=>ids.has(id)),'Every retained claim must retain all declared support');
 }
});
