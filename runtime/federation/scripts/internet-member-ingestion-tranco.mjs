import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import { createHash } from 'node:crypto';
import { projectInternetIdentity } from '../lib/internet-functional-fabric.mjs';

const csvPath=process.argv[2] || '.deus/internet-fabric/input/tranco-top-1m.csv';
if(!fs.existsSync(csvPath)) throw new Error('missing Tranco CSV: '+csvPath);

let listId=null;
let latestUrl=null;
try{
  const resp=await fetch('https://tranco-list.eu/latest_list',{
    headers:{'user-agent':'DEUS-Internet-Observatory/1.0','accept':'text/html'},
    redirect:'follow',
    signal:AbortSignal.timeout(15000),
  });
  latestUrl=resp.url || null;
  const m=String(latestUrl||'').match(/\/list\/([^/]+)\/1000000/);
  listId=m?.[1] ?? null;
}catch{}

const csvHash=createHash('sha256');
await new Promise((resolve,reject)=>{
  const s=fs.createReadStream(csvPath);
  s.on('data',d=>csvHash.update(d));
  s.on('end',resolve);
  s.on('error',reject);
});
const csvSha256=csvHash.digest('hex');

const outRoot='.deus/internet-fabric/members/tranco-'+(listId||'latest');
fs.mkdirSync(outRoot,{recursive:true});
const CHUNK=100000;
let chunkIndex=-1, out=null, rankExpected=1, memberCount=0;
const uniqueKeys=new Set();
const uniqueSlots=new Set();
const memberDigestHash=createHash('sha256');
const samples={first:[],middle:[],last:[]};
let lastRing=[];

function openChunk(index){
  if(out) out.end();
  const name='chunk-'+String(index).padStart(3,'0')+'.tsv';
  out=fs.createWriteStream(path.join(outRoot,name),{encoding:'utf8'});
  out.write('rank\tdomain\tresource_key\tslot_id\n');
}

const rl=readline.createInterface({input:fs.createReadStream(csvPath),crlfDelay:Infinity});
for await (const line of rl){
  if(!line.trim()) continue;
  const comma=line.indexOf(',');
  if(comma<=0) throw new Error('malformed Tranco row near rank '+rankExpected);
  const rank=Number(line.slice(0,comma));
  const domain=line.slice(comma+1).trim().normalize('NFC').toLowerCase();
  if(!Number.isInteger(rank) || rank!==rankExpected) throw new Error('rank sequence mismatch expected='+rankExpected+' got='+rank);
  if(!domain || /\s/.test(domain)) throw new Error('invalid domain at rank '+rank);
  const newChunk=Math.floor((rank-1)/CHUNK);
  if(newChunk!==chunkIndex){ chunkIndex=newChunk; openChunk(chunkIndex); }
  const p=projectInternetIdentity({type:'dns',value:domain});
  const canonical=[rank,domain,p.resourceKey,p.slotId].join('|');
  memberDigestHash.update(canonical+'\n');
  uniqueKeys.add(p.resourceKey);
  uniqueSlots.add(p.slotId);
  out.write([rank,domain,p.resourceKey,p.slotId].join('\t')+'\n');
  const s={rank,domain,resourceKey:p.resourceKey,slotId:p.slotId};
  if(rank<=3) samples.first.push(s);
  if(rank>=499999 && rank<=500001) samples.middle.push(s);
  lastRing.push(s); if(lastRing.length>3) lastRing.shift();
  memberCount++; rankExpected++;
}
if(out) await new Promise((resolve,reject)=>{out.end(resolve);out.on('error',reject);});
samples.last=lastRing;
if(memberCount!==1000000) throw new Error('expected 1,000,000 Tranco members, got '+memberCount);

const chunkFiles=fs.readdirSync(outRoot).filter(x=>x.endsWith('.tsv')).sort();
const chunkMeta=chunkFiles.map(name=>{
  const b=fs.readFileSync(path.join(outRoot,name));
  const lines=b.toString('utf8').split('\n').filter(Boolean).length-1;
  return {name,rows:lines,bytes:b.length,sha256:createHash('sha256').update(b).digest('hex')};
});
const summary={
  schema:'deus-internet-membership-ingestion-summary/1',
  source:'TRANCO_TOP_1M',
  sourceUrl:'https://tranco-list.eu/top-1m.csv.zip',
  latestMetadataUrl:'https://tranco-list.eu/latest_list',
  latestResolvedUrl:latestUrl,
  listId,
  fetchedAt:new Date().toISOString(),
  csvSha256,
  memberCount,
  uniqueResourceKeys:uniqueKeys.size,
  uniqueSlots:uniqueSlots.size,
  slotCollisions:uniqueKeys.size-uniqueSlots.size,
  memberDigest:memberDigestHash.digest('hex'),
  chunkCount:chunkMeta.length,
  chunks:chunkMeta,
  samples,
  truthBoundary:'TRANCO_RANKED_DOMAIN_MEMBERSHIP_NE_DOMAIN_LIVENESS_NE_HOST_SERVICE_NE_EXECUTION_AUTHORITY',
};
fs.writeFileSync(path.join(outRoot,'manifest.json'),JSON.stringify(summary,null,2)+'\n');
console.log(JSON.stringify(summary));
