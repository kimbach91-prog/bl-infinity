import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {spawn} from 'node:child_process';

function collect(command,args,input,{timeoutMs=10000,maxBytes=262144}={}){
  return new Promise((resolve,reject)=>{
    const p=spawn(command,args,{stdio:['pipe','pipe','pipe'],windowsHide:true}),out=[],err=[];let n=0,done=false;
    const finish=(e,v)=>{if(done)return;done=true;clearTimeout(t);e?reject(e):resolve(v)};
    const t=setTimeout(()=>{try{p.kill()}catch{};finish(new Error('VAULT_HELPER_TIMEOUT'));},timeoutMs);
    p.stdout.on('data',c=>{n+=c.length;if(n>maxBytes)return finish(new Error('VAULT_HELPER_OUTPUT_LIMIT'));out.push(c)});
    p.stderr.on('data',c=>err.push(c));
    p.on('error',e=>finish(e));p.on('close',code=>code===0?finish(null,Buffer.concat(out).toString('utf8').trim()):finish(new Error('VAULT_HELPER_FAILED_'+code+':'+Buffer.concat(err).toString('utf8').slice(0,200))));
    p.stdin.end(input);
  });
}
const hash=s=>crypto.createHash('sha256').update(String(s)).digest('hex');

export function createOwnerVault({root=process.env.DEUS_STATE_ROOT,helper=process.env.DEUS_VAULT_HELPER,protect,unprotect}={}){
  const dir=path.join(root||path.resolve('data'),'owner-vault');
  const crypt=async(mode,text)=>{
    if(process.platform!=='win32'||!helper)throw new Error('WINDOWS_DPAPI_VAULT_REQUIRED');
    return collect(helper,['--vault-'+mode],text);
  };
  const enc=protect||((x)=>crypt('protect',x)),dec=unprotect||((x)=>crypt('unprotect',x));
  const file=ref=>path.join(dir,hash(ref)+'.bin');
  return Object.freeze({
    async set(ref,value){
      if(!ref||typeof ref!=='string')throw new Error('VAULT_REF_REQUIRED');
      const payload=JSON.stringify({schema:'deus.owner-vault/1',value,storedAt:new Date().toISOString()});
      const ciphertext=await enc(payload);if(!ciphertext||ciphertext.includes(payload))throw new Error('VAULT_ENCRYPTION_INVALID');
      await fs.mkdir(dir,{recursive:true,mode:0o700});
      const target=file(ref),temp=target+'.'+crypto.randomUUID()+'.tmp';
      try{await fs.writeFile(temp,ciphertext,{mode:0o600,flag:'wx'});await fs.rename(temp,target);}
      finally{await fs.rm(temp,{force:true}).catch(()=>{});}
      return {ref,digest:hash(ciphertext),ciphertextBytes:Buffer.byteLength(ciphertext)};
    },
    async get(ref){
      try{const ciphertext=await fs.readFile(file(ref),'utf8');const doc=JSON.parse(await dec(ciphertext));if(doc?.schema!=='deus.owner-vault/1')throw new Error('VAULT_PAYLOAD_INVALID');return doc.value;}
      catch(e){if(e.code==='ENOENT')return null;throw e;}
    },
    async delete(ref){await fs.rm(file(ref),{force:true});return {ref,deleted:true};},
    async status(){
      try{const names=await fs.readdir(dir);return {schema:'deus.owner-vault-status/1',backend:protect?'TEST_INJECTED':'WINDOWS_CURRENTUSER_DPAPI',entries:names.filter(x=>x.endsWith('.bin')).length,plaintextFallback:false};}
      catch(e){if(e.code==='ENOENT')return {schema:'deus.owner-vault-status/1',backend:protect?'TEST_INJECTED':'WINDOWS_CURRENTUSER_DPAPI',entries:0,plaintextFallback:false};throw e;}
    },
    async encryptedArtifact(ref){
      const ciphertext=await fs.readFile(file(ref),'utf8');
      return {schema:'deus.owner-vault-encrypted-artifact/1',refHash:hash(ref),ciphertext,digest:hash(ciphertext),bytes:Buffer.byteLength(ciphertext),plaintextIncluded:false};
    }
  });
}
