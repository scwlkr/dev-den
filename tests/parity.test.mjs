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
test('material risk persists until its own advisor endorses a named mitigation',withStore(store=>{
 const run=(endorsingAdvisor)=>fill(store,store.create(brief,board(5),'normal').id,(_,step,c)=>{
  if(step.stage==='opening'&&step.advisor==='dhh'){c.risk='likely';c.risk_option=brief.options[0];}
  if(step.stage==='ratification'&&step.advisor===endorsingAdvisor){c.mitigation='Prove a complete export and restore before shipping.';c.mitigation_for_option=brief.options[0];c.mitigation_endorsed=true;}
 });
 const unresolved=report(run('tobi'));assert.equal(unresolved.decisionMetrics.disposition,'RESHAPE');assert.ok(unresolved.decisionMetrics.blockingRisks.some(x=>x.advisor==='dhh'));assert.match(markdown(store.read(unresolved.id)),/RESHAPE/);
 const resolved=report(run('dhh'));assert.equal(resolved.decisionMetrics.blockingRisks.length,0);assert.notEqual(resolved.decisionMetrics.disposition,'RESHAPE');
}));
test('decision metrics evaluate the actual verdict option rather than a different score leader',withStore(store=>{
 const s=fill(store,store.create(brief,board(5),'normal').id,(_,step,c)=>{if(step.stage==='verdict')c.recommendation=brief.options[1];});assert.equal(report(s).decisionMetrics.recommendedOption,s.cards.verdict.recommendation);
}));
test('likely risk cannot name an unknown option to bypass safeguards',withStore(store=>{
 const s=store.create(brief,board(5),'normal'),step=nextStep(s),card=fixtureCard(s,step);card.risk='likely';card.risk_option='nonexistent option';assert.throws(()=>store.submit(s.id,step.key,card),/option|choice|risk/i);
}));
test('unanimous opening cannot bypass alternative evaluation with empty chair cruxes',withStore(store=>{
 const s=store.create(brief,board(5),'normal');while(nextStep(store.read(s.id)).stage==='opening'){const a=store.read(s.id),step=nextStep(a);store.submit(s.id,step.key,fixtureCard(a,step));}const a=store.read(s.id),step=nextStep(a),card=fixtureCard(a,step);card.cruxes=[];assert.throws(()=>store.submit(s.id,step.key,card),/alternative|unanim|steelman|crux/i);
}));
test('an unfinished legacy v1 review accepts the original card schema without invented new fields',withStore(store=>{
 const s=store.create(brief,board(5),'normal'),file=path.join(store.folder(s.id),'session.json');s.version=1;delete s.reviewMode;s.mode='agent';fs.writeFileSync(file,JSON.stringify(s));const state=store.read(s.id),step=nextStep(state),card=fixtureCard(state,step);for(const key of ['risk_option','resolution_support','mitigation','mitigation_for_option','mitigation_endorsed'])delete card[key];assert.doesNotThrow(()=>store.submit(s.id,step.key,card));
}));
test('new reviews use the versioned protocol rather than bypassing new required fields as legacy',withStore(store=>{
 const s=store.create(brief,board(5),'normal');assert.equal(s.version,2);assert.equal(s.reviewMode,'normal');
}));
test('an explicitly selected one-seat review also completes instead of requiring an impossible opponent',withStore(store=>{
 const s=fill(store,store.create(brief,board(1),'selected').id);assert.equal(s.status,'complete');assert.ok(report(s).scores.every(x=>x.score!==null));
}));
test('all mode supports a genuinely small roster and only rejects an over-limit roster',withStore((store,dir)=>{
 const root=path.join(dir,'small-project');fs.mkdirSync(path.join(root,'collection'),{recursive:true});fs.mkdirSync(path.join(root,'.collection'),{recursive:true});const r=JSON.parse(fs.readFileSync(path.join(ROOT,'collection/roster.json')));r.developers=r.developers.filter(d=>names.slice(0,3).includes(d.id));fs.writeFileSync(path.join(root,'collection/roster.json'),JSON.stringify(r));fs.symlinkSync(path.join(ROOT,'.collection/pilot'),path.join(root,'.collection/pilot'),'dir');const small=new Store(path.join(root,'sessions'),root),s=fill(small,small.create(brief,board(3),'all').id);assert.equal(s.status,'complete');assert.equal(s.board.length,3);
}));
test('server recovery does not rewrite completed historical sessions',withStore(store=>{
 const s=fill(store,store.create(brief,board(5),'normal').id),f=path.join(store.folder(s.id),'session.json'),before=fs.readFileSync(f,'utf8');store.recover();assert.equal(fs.readFileSync(f,'utf8'),before);
}));
test('all model output schemas satisfy strict provider object requirements',async()=>{
 const {schema}=await import('../app/lib/protocol.mjs');const walk=s=>{if(s.type==='object'){assert.deepEqual([...s.required].sort(),Object.keys(s.properties).sort());assert.equal(s.additionalProperties,false);Object.values(s.properties).forEach(walk);}if(s.items)walk(s.items);};for(const stage of ['opening','cruxes','debate','draft','ratification','verdict'])walk(schema(stage,brief.options,board(5)));
});
test('an assigned advisor must actually evaluate the alternative during debate',withStore(store=>{
 const s=store.create(brief,board(5),'normal');let state=store.read(s.id);while(nextStep(state).stage!=='debate'){const step=nextStep(state);store.submit(s.id,step.key,fixtureCard(state,step));state=store.read(s.id);}const step=nextStep(state),c=fixtureCard(state,step);assert.ok(state.cards.cruxes.alternative_test.advisors.includes(step.advisor));c.alternative_argument='';assert.throws(()=>store.submit(s.id,step.key,c),/alternative|steelman/i);
}));

test('divided irreversible reviews retain a concrete experiment even when fit already requires reshaping',withStore(store=>{
 const s=store.create({...brief,reversibility:'irreversible'},board(5),'normal');
 const done=fill(store,s.id,(_,step,c)=>{if(c.scores)c.scores=c.scores.map((x,i)=>({...x,score:i===0?(step.advisor==='dhh'?0:6):2}));});
 const m=report(done).decisionMetrics;assert.ok(m.irreversible);assert.ok(m.spread>=4);assert.equal(m.disposition,'RESHAPE');assert.equal(m.precondition,done.cards.verdict.experiment);
}));
