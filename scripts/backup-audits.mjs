/** Owner-authorized audit-history snapshots; never writes or logs plaintext reports. */
import {createCipheriv,createDecipheriv,pbkdf2Sync,randomBytes} from 'node:crypto';
import {readFile,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {pathToFileURL} from 'node:url';
import {isDeepStrictEqual} from 'node:util';
const SOURCE='https://growthlens-free-test.onrender.com';
const AAD=Buffer.from('GrowthLens audit-history backup v1');
const ROUNDS=600000,MAX_BYTES=20000000;
function checkKey(secret){if(typeof secret!=='string'||secret.length<32||/[\r\n]/.test(secret))throw Error('A configured owner key of at least 32 characters is required');}
export function encryptSnapshot(snapshot,secret){
 checkKey(secret);const plaintext=Buffer.from(JSON.stringify(snapshot));if(plaintext.length>MAX_BYTES)throw Error('Backup exceeds the safe size limit');
 const salt=randomBytes(16),iv=randomBytes(12),key=pbkdf2Sync(secret,salt,ROUNDS,32,'sha256');
 try{const cipher=createCipheriv('aes-256-gcm',key,iv);cipher.setAAD(AAD);const ciphertext=Buffer.concat([cipher.update(plaintext),cipher.final()]);return {version:1,cipher:'AES-256-GCM',kdf:'PBKDF2-SHA256',rounds:ROUNDS,salt:salt.toString('base64'),iv:iv.toString('base64'),tag:cipher.getAuthTag().toString('base64'),ciphertext:ciphertext.toString('base64')};}
 finally{key.fill(0);plaintext.fill(0);}
}
export function decryptSnapshot(envelope,secret){
 checkKey(secret);if(envelope?.version!==1||envelope.cipher!=='AES-256-GCM'||envelope.kdf!=='PBKDF2-SHA256'||envelope.rounds!==ROUNDS||typeof envelope.ciphertext!=='string'||envelope.ciphertext.length>28000000)throw Error('Invalid encrypted backup format');
 const salt=Buffer.from(envelope.salt||'','base64'),iv=Buffer.from(envelope.iv||'','base64'),tag=Buffer.from(envelope.tag||'','base64');
 if(salt.length!==16||iv.length!==12||tag.length!==16)throw Error('Invalid encrypted backup parameters');
 const key=pbkdf2Sync(secret,salt,ROUNDS,32,'sha256');
 try{const decipher=createDecipheriv('aes-256-gcm',key,iv);decipher.setAAD(AAD);decipher.setAuthTag(tag);const clear=Buffer.concat([decipher.update(Buffer.from(envelope.ciphertext,'base64')),decipher.final()]);try{return JSON.parse(clear.toString('utf8'));}finally{clear.fill(0);}}
 finally{key.fill(0);}
}
async function responseJSON(response,maxBytes){
 const reader=response.body.getReader(),chunks=[];let bytes=0;
 try{while(true){const {done,value}=await reader.read();if(done)break;bytes+=value.byteLength;if(bytes>maxBytes)throw Error('Backup source exceeds safe response size');chunks.push(Buffer.from(value));}}
 catch(error){await reader.cancel().catch(()=>{});throw error;}
 try{return JSON.parse(Buffer.concat(chunks).toString('utf8'));}catch{throw Error('Backup source returned invalid JSON');}
}
export async function collectAudits({secret,fetchImpl=fetch,maxId=10000}={}){
 checkKey(secret);let total=0;const cancellation=new AbortController();
 async function get(path,allowMissing=false){
  const response=await fetchImpl(SOURCE+path,{headers:{'X-GrowthLens-Key':secret,'Accept':'application/json'},redirect:'error',signal:AbortSignal.any([AbortSignal.timeout(20000),cancellation.signal])});
  if(response.status===404&&allowMissing)return null;
  if(!response.ok)throw Error('Owner-authorized backup request failed (HTTP '+response.status+')');
  const value=await responseJSON(response,2000000);total+=Buffer.byteLength(JSON.stringify(value));if(total>MAX_BYTES)throw Error('Audit history exceeds the safe export size limit');return value;
 }
 function inspectList(rows){
  if(!Array.isArray(rows)||rows.length>50||rows.some(row=>!Number.isSafeInteger(row.id)||row.id<1))throw Error('Unexpected audit-history index');
  if(rows.some(row=>row.status==='running'))throw Error('An audit is still running; retry the backup after it finishes');
  return rows.length?Math.max(...rows.map(row=>row.id)):0;
 }
 const before=await get('/api/audits'),cutoffId=inspectList(before);if(cutoffId>maxId)throw Error('Audit history requires a larger owner-managed export');
 const records=[];let next=1;
 await Promise.all(Array.from({length:Math.min(3,cutoffId)},async()=>{
  while(next<=cutoffId&&!cancellation.signal.aborted){const identifier=next++,record=await get('/api/audits/'+identifier,true);if(!record)continue;
   if(record.id!==identifier||typeof record.url!=='string'||typeof record.created_at!=='string'||!['completed','partial','failed'].includes(record.status))throw Error('An audit record is incomplete or changed during the export');
   if(record.organization_id!=null)throw Error('Organization-linked history requires a full owner-managed database backup');
   records.push(record);
  }
 })).catch(error=>{cancellation.abort();throw error;});
 const after=await get('/api/audits');inspectList(after);if(!isDeepStrictEqual(before,after))throw Error('Audit history changed during export; retry before cutover');
 records.sort((a,b)=>a.id-b.id);return {version:1,source:SOURCE,created_at:new Date().toISOString(),cutoff_id:cutoffId,records};
}
export async function main(){
 const secret=process.env.GROWTHLENS_PRIVATE_KEY;
 if(process.argv[2]==='--decrypt'){
  // Use only as a pipe into the verified restore script, never as a CI log step.
  const envelope=JSON.parse(await readFile(process.argv[3],'utf8'));
  process.stdout.write(JSON.stringify(decryptSnapshot(envelope,secret)));return;
 }
 const snapshot=await collectAudits({secret}),encrypted=encryptSnapshot(snapshot,secret);
 if(!isDeepStrictEqual(snapshot,decryptSnapshot(encrypted,secret)))throw Error('Encrypted backup verification failed');
 const filename='growthlens-audits-'+Date.now()+'.enc.json',path=join(process.env.RUNNER_TEMP||tmpdir(),filename);
 await writeFile(path,JSON.stringify(encrypted),{mode:0o600,flag:'wx'});
 if(process.env.GITHUB_OUTPUT)await writeFile(process.env.GITHUB_OUTPUT,'path='+path+'\n',{flag:'a'});
 console.log(JSON.stringify({status:'encrypted_backup_verified',records:snapshot.records.length,cutoff_id:snapshot.cutoff_id}));
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)main().catch(()=>{console.error('Audit backup failed. Check the owner key, active audit jobs and source availability. No plaintext artifact was written.');process.exitCode=1;});
