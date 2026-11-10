import test from 'node:test';
import assert from 'node:assert/strict';
import {collectAudits,encryptSnapshot,decryptSnapshot} from '../scripts/backup-audits.mjs';
const secret='test-owner-key-that-is-at-least-32-characters';
const row=id=>({id,url:'https://example.com/'+id,created_at:'2026-11-10T00:00:00Z',status:'completed',organization_id:null,result:{score:75}});
test('authenticated encryption round-trips history, hides report data, and rejects tampering and wrong keys',()=>{
 const snapshot={records:[row(1)]},encrypted=encryptSnapshot(snapshot,secret);
 assert.deepEqual(decryptSnapshot(encrypted,secret),snapshot);
 assert.doesNotMatch(JSON.stringify(encrypted),/example\.com|test-owner-key/);
 assert.throws(()=>decryptSnapshot(encrypted,secret+'wrong'));
 assert.throws(()=>decryptSnapshot({...encrypted,tag:Buffer.alloc(16).toString('base64')},secret));
 assert.throws(()=>encryptSnapshot(snapshot,'short'),/32 characters/);
});
test('all audit IDs are checked, including records outside the 50-row history window, with bounded concurrency',async()=>{
 let active=0,peak=0;const visited=[];
 const result=await collectAudits({secret,fetchImpl:async(url,options)=>{
  assert.equal(options.headers['X-GrowthLens-Key'],secret);assert.equal(options.redirect,'error');
  active++;peak=Math.max(peak,active);await new Promise(setImmediate);active--;
  if(url.endsWith('/api/audits'))return Response.json([{id:52,status:'completed'}]);
  const id=Number(url.split('/').pop());visited.push(id);return id===2?new Response('',{status:404}):Response.json(row(id));
 }});
 assert.equal(result.records.length,51);assert.equal(result.cutoff_id,52);assert.equal(visited.length,52);assert.ok(peak<=3);
});
test('running, changing or inaccessible histories fail instead of producing a misleading backup',async()=>{
 await assert.rejects(collectAudits({secret,fetchImpl:async()=>Response.json([{id:1,status:'running'}])}),/still running/);
 await assert.rejects(collectAudits({secret,fetchImpl:async()=>new Response('private diagnostic',{status:401})}),/HTTP 401/);
 let lists=0;await assert.rejects(collectAudits({secret,fetchImpl:async url=>url.endsWith('/api/audits')?Response.json(lists++?[{id:2,status:'completed'}]:[{id:1,status:'completed'}]):Response.json(row(1))}),/changed during/);
});
