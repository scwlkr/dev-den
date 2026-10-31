import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

test('room draws finite coordinates for one through nine advisors, including unknown portraits',()=>{
  const calls=[];
  const ctx=new Proxy({}, {get:(_,method)=>(...args)=>calls.push({method,args}),set:()=>true});
  const code=fs.readFileSync(new URL('../app/public/room.js',import.meta.url),'utf8').replace('export class Room','globalThis.Room = class Room');
  const sandbox={matchMedia:()=>({matches:true}),setInterval:()=>0};
  vm.runInNewContext(code,sandbox);
  const room=new sandbox.Room({getContext:()=>ctx});
  for(let count=1;count<=9;count++){
    calls.length=0;
    room.set(Array.from({length:count},(_,i)=>({id:i===0?'dhh':'new-advisor-'+i,name:'New Advisor '+i})), 'dhh', true);
    assert.ok(calls.some(c=>c.method==='fillText'&&c.args[0]==='DHH'));
    if(count>1)assert.ok(calls.some(c=>c.method==='fillText'&&c.args[0]==='New Advisor 1'));
    for(const call of calls)for(const value of call.args)if(typeof value==='number')assert.ok(Number.isFinite(value),`${count} seats: ${call.method} received ${value}`);
  }
});
test('installed skill sources retain their invocation metadata',()=>{
  for(const name of ['dev-den','dev-den-advisor']){
    const text=fs.readFileSync(new URL(`../.agents/skills/${name}/SKILL.md`,import.meta.url),'utf8');
    assert.ok(text.startsWith(`---\nname: ${name}\ndescription: `));
    assert.ok(text.indexOf('\n---\n',4)>0);
  }
});
