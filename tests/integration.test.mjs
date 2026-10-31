// Supervisor-corrected integration fixtures: isolated writable root, shared read-only source inputs.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {Store} from '../app/lib/sessions.mjs';
import {ROOT} from '../app/lib/knowledge.mjs';
import {nextStep} from '../app/lib/protocol.mjs';
import {fixtureCard} from '../app/lib/demo.mjs';
import {createServer} from '../app/server.mjs';
import {Council} from '../app/lib/council.mjs';
import {Ledger} from '../app/lib/providers.mjs';
const brief=JSON.parse(fs.readFileSync(path.join(ROOT,'examples/todo.json')));
async function fixture(t){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'dod-integration-'));
 fs.mkdirSync(path.join(root,'collection'));fs.mkdirSync(path.join(root,'.collection'));
 fs.copyFileSync(path.join(ROOT,'collection/roster.json'),path.join(root,'collection/roster.json'));
 fs.symlinkSync(path.join(ROOT,'.collection/pilot'),path.join(root,'.collection/pilot'),'dir');
 const store=new Store(path.join(root,'sessions'),root),council=new Council(store,{ledger:new Ledger(path.join(root,'.den/usage.json'),0.75)}),server=createServer({store,council});
 t.after(async()=>{await new Promise(resolve=>server.close(resolve));fs.rmSync(root,{recursive:true,force:true});});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const base='http://127.0.0.1:'+server.address().port;
 const get=async route=>{const r=await fetch(base+route),data=await r.json();assert.equal(r.status,200,JSON.stringify(data));return data;};const boot=await get('/api/bootstrap');
 const post=async(route,body,status=200)=>{const r=await fetch(base+route,{method:'POST',headers:{'Content-Type':'application/json','X-Den-Token':boot.token},body:JSON.stringify(body)}),data=await r.json();assert.equal(r.status,status,JSON.stringify(data));return data;};
 return {root,store,post,get,boot};
}
async function complete(f,s){let step,n=0;while(step=nextStep(s)){assert.ok(n++<50);s=await f.post('/api/sessions/'+s.id+'/submit',{key:step.key,card:fixtureCard(s,step)});}return s;}
test('HTTP consultation completes, persists and exports computed metrics',async t=>{
 const f=await fixture(t);let s=await f.post('/api/sessions',{brief,board:[{id:'dhh',weight:3,reason:'Source-grounded consultation'}],reviewMode:'consult'},201);assert.equal(s.reviewMode,'consult');s=await complete(f,s);assert.equal(s.status,'complete');const r=await f.get('/api/sessions/'+s.id+'/report');assert.equal(r.reviewMode,'consult');assert.ok(r.decisionMetrics);assert.equal(r.decisionMetrics.recommendedOption,s.cards.verdict.recommendation);assert.ok(r.scores.every(x=>x.score!==null));assert.equal(f.store.read(s.id).status,'complete');
});
test('HTTP quick review completes its reduced-round branch and exports scores',async t=>{
 const f=await fixture(t),board=['dhh','tobi','primeagen','carmack'].map(id=>({id,weight:1,reason:'Quick review'}));let s=await f.post('/api/sessions',{brief,board,reviewMode:'quick'},201);assert.equal(s.reviewMode,'quick');s=await complete(f,s);assert.equal(s.status,'complete');assert.ok(!Object.keys(s.cards).some(k=>k.startsWith('ratification:')));const r=await f.get('/api/sessions/'+s.id+'/report');assert.ok(r.decisionMetrics);assert.ok(r.scores.every(x=>x.score!==null));
});
test('board settings are isolated, validated and returned by the API',async t=>{
 const f=await fixture(t),prefs={board:'default',default:['dhh','tobi','primeagen','carmack','linus']};const s=await f.post('/api/board',prefs);assert.equal(s.board,'default');const loaded=await f.get('/api/board');assert.deepEqual(loaded.default,prefs.default);await f.post('/api/board',{board:'invalid',default:['dhh']},400);assert.deepEqual((await f.get('/api/board')).default,prefs.default);
});
test('HTTP all mode explicitly rejects this over-nine roster',async t=>{const f=await fixture(t);const r=await f.post('/api/sessions',{brief,reviewMode:'all'},400);assert.match(r.error,/9|nine|selected/i);});
test('CLI usage advertises implemented review modes',()=>{const r=spawnSync(process.execPath,['app/cli.mjs'],{cwd:ROOT,encoding:'utf8'});assert.equal(r.status,0,r.stderr);const d=JSON.parse(r.stdout);assert.ok(d.usage.some(x=>x.includes('consult')));assert.ok(d.usage.some(x=>x.includes('selected')));});
test('selected nine-seat review completes through verdict and rejects a tenth seat',async t=>{
 const f=await fixture(t),board=f.boot.roster.slice(0,9).map(a=>({id:a.id,weight:1,reason:'Explicit selected council'}));
 let s=await f.post('/api/sessions',{brief,board,reviewMode:'selected'},201);s=await complete(f,s);assert.equal(s.status,'complete');assert.equal(s.board.length,9);
 const error=await f.post('/api/sessions',{brief,board:[...board,{id:f.boot.roster[9].id,weight:1,reason:'Too many'}],reviewMode:'selected'},400);assert.match(error.error,/9/);
});
test('saved policy affects actual creation, with explicit seats taking precedence',async t=>{
 const f=await fixture(t);
 await f.post('/api/board',{board:'default',default:['dhh','carmack']});
 let s=await f.post('/api/sessions',{brief},201);assert.deepEqual(s.board.map(a=>a.id),['dhh','carmack']);assert.equal(s.reviewMode,'selected');
 await f.post('/api/board',{board:'ask',default:['dhh','carmack']});await f.post('/api/sessions',{brief},400);
 s=await f.post('/api/sessions',{brief,reviewMode:'consult',board:[{id:'tobi',weight:2,reason:'Explicit consultation'}]},201);assert.equal(s.board[0].id,'tobi');
 await f.post('/api/board',{board:'auto',default:['dhh','carmack']});s=await f.post('/api/sessions',{brief},201);assert.equal(s.reviewMode,'normal');assert.equal(s.board.length,5);
});
