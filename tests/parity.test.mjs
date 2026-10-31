// Independent public-workflow acceptance tests maintained by the supervising agent.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {Store} from '../app/lib/sessions.mjs';
import {ROOT} from '../app/lib/knowledge.mjs';
import {nextStep,needsRatification,weightedScores} from '../app/lib/protocol.mjs';
import {fixtureCard} from '../app/lib/demo.mjs';
import {report,markdown} from '../app/lib/report.mjs';
const brief=JSON.parse(fs.readFileSync(path.join(ROOT,'examples/todo.json'),'utf8'));
const names=['dhh','tobi','primeagen','carmack','linus'];
const board=n=>names.slice(0,n).map(id=>({id,weight:1,reason:'Independent acceptance test'}));
function withStore(fn){return ()=>{const dir=fs.mkdtempSync(path.join(os.tmpdir(),'dod-parity-'));try{return fn(new Store(path.join(dir,'sessions')),dir);}finally{fs.rmSync(dir,{recursive:true,force:true});}};}
function fill(store,id,adjust=()=>{}){let s=store.read(id),step;let n=0;while(step=nextStep(s)){assert.ok(n++<40,'Stage graph must terminate');const card=fixtureCard(s,step);adjust(s,step,card);store.submit(id,step.key,card);s=store.read(id);}return s;}
test('single-advisor consultation completes and exports real scores without ratification',withStore(store=>{
 const s=fill(store,store.create(brief,board(1),'consult').id);assert.equal(s.status,'complete');assert.deepEqual(Object.keys(s.cards),['opening:dhh','verdict']);const r=report(s);assert.equal(r.reviewMode,'consult');assert.deepEqual(r.scores,weightedScores(s,'opening'));assert.ok(r.scores.every(x=>x.score!==null));assert.equal(r.amendments.length,0);assert.ok(markdown(s).includes('Recommendation'));assert.equal(new Store(store.dir).read(s.id).status,'complete');
}));
test('quick converged debate skips ratification even with a large gap BETWEEN options',withStore(store=>{
 const s=fill(store,store.create(brief,board(4),'quick').id,(_,step,c)=>{if(c.scores)c.scores=c.scores.map((x,i)=>({...x,score:i===0?9:1}));});assert.equal(s.status,'complete');assert.ok(!Object.keys(s.cards).some(k=>k.startsWith('ratification:')));assert.equal(needsRatification(s),false);assert.deepEqual(report(s).scores,weightedScores(s,'debate'));
}));
test('quick divided debate ratifies and report uses the final ratification scores',withStore(store=>{
 const s=fill(store,store.create(brief,board(4),'quick').id,(_,step,c)=>{if(step.stage==='debate'){const index=names.indexOf(step.advisor);c.scores=c.scores.map((x,i)=>({...x,score:i===0?(index===3?0:10):1}));}if(step.stage==='ratification')c.scores=c.scores.map((x,i)=>({...x,score:i===0?6:2}));});assert.equal(s.status,'complete');assert.equal(Object.keys(s.cards).filter(k=>k.startsWith('ratification:')).length,4);assert.deepEqual(report(s).scores,weightedScores(s,'ratification'));
}));
test('quick likely material risk requires ratification despite identical scores',withStore(store=>{
 const s=fill(store,store.create(brief,board(4),'quick').id,(_,step,c)=>{if(step.stage==='debate'&&step.advisor==='dhh')c.risk='likely';});assert.equal(s.status,'complete');assert.equal(Object.keys(s.cards).filter(k=>k.startsWith('ratification:')).length,4);
}));
test('legacy accepted session remains readable without rewriting historical file',withStore(store=>{
 const s=fill(store,store.create(brief,board(5),'normal').id),file=path.join(store.folder(s.id),'session.json');const old=JSON.parse(fs.readFileSync(file));delete old.reviewMode;old.mode='openai:gpt-6.1-terra';old.version=1;const bytes=JSON.stringify(old);fs.writeFileSync(file,bytes);const restored=store.read(s.id);assert.equal(restored.reviewMode,'normal');assert.deepEqual(restored.cards,s.cards);assert.equal(fs.readFileSync(file,'utf8'),bytes);
}));
