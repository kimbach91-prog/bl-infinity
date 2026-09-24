import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { projectInternetIdentity } from '../lib/internet-functional-fabric.mjs';

const SOURCE='https://publicsuffix.org/list/public_suffix_list.dat';
const response=await fetch(SOURCE,{headers:{'user-agent':'DEUS-Internet-Observatory/1.0','accept':'text/plain'}});
if(!response.ok) throw new Error('PSL fetch failed HTTP '+response.status);
const text=await response.text();
const sourceSha256=createHash('sha256').update(text).digest('hex');
const lines=text.split(/\r?\n/);
const version=(lines.find(x=>x.startsWith('// VERSION:'))??'').replace('// VERSION:','').trim()||null;
const commit=(lines.find(x=>x.startsWith('// COMMIT:'))??'').replace('// COMMIT:','').trim()||null;

let section='UNKNOWN';
const members=[];
for(let i=0;i<lines.length;i++){
  const raw=lines[i].trim();
  if(raw==='// ===BEGIN ICANN DOMAINS===') { section='ICANN'; continue; }
  if(raw==='// ===BEGIN PRIVATE DOMAINS===') { section='PRIVATE'; continue; }
  if(!raw || raw.startsWith('//')) continue;
  const rule=raw.normalize('NFC').toLowerCase();
  const projection=projectInternetIdentity({type:'generic',value:'domain_suffix_rule|'+rule});
  members.push({
    schema:'deus-internet-membership-record/1',
    source:'PUBLIC_SUFFIX_LIST',
    sourceUrl:SOURCE,
    sourceVersion:version,
    sourceCommit:commit,
    sourceLine:i+1,
    section,
    identityType:'domain_suffix_rule',
    value:rule,
    ruleKind:rule.startsWith('!')?'EXCEPTION':rule.startsWith('*.')?'WILDCARD':'EXACT',
    resourceKey:projection.resourceKey,
    slotId:projection.slotId,
    observedClass:'DATA_ONLY',
    truthBoundary:'PSL_RULE_NE_DOMAIN_EXISTENCE_NE_LIVE_HOST_NE_EXECUTION_AUTHORITY',
  });
}
if(members.length<1000) throw new Error('PSL member count unexpectedly small: '+members.length);
const uniqueKeys=new Set(members.map(x=>x.resourceKey));
const uniqueSlots=new Set(members.map(x=>x.slotId));
const sectionCounts={};
const kindCounts={};
for(const m of members){
  sectionCounts[m.section]=(sectionCounts[m.section]??0)+1;
  kindCounts[m.ruleKind]=(kindCounts[m.ruleKind]??0)+1;
}
const canonicalLines=members.map(x=>[x.identityType,x.value,x.resourceKey,x.slotId,x.section,x.ruleKind].join('|')).sort();
const memberDigest=createHash('sha256').update(canonicalLines.join('\n')).digest('hex');
const outDir='.deus/internet-fabric/members';
fs.mkdirSync(outDir,{recursive:true});
const safeVersion=(version||'unknown').replace(/[^A-Za-z0-9_.-]+/g,'_');
const jsonlPath=path.join(outDir,'psl-'+safeVersion+'.jsonl');
const summaryPath=path.join(outDir,'psl-'+safeVersion+'.summary.json');
fs.writeFileSync(jsonlPath,members.map(x=>JSON.stringify(x)).join('\n')+'\n');
const summary={
  schema:'deus-internet-membership-ingestion-summary/1',
  source:'PUBLIC_SUFFIX_LIST',
  sourceUrl:SOURCE,
  fetchedAt:new Date().toISOString(),
  sourceVersion:version,
  sourceCommit:commit,
  sourceSha256,
  rawLineCount:lines.length,
  memberCount:members.length,
  uniqueResourceKeys:uniqueKeys.size,
  uniqueSlots:uniqueSlots.size,
  slotCollisions:uniqueKeys.size-uniqueSlots.size,
  sectionCounts,
  kindCounts,
  memberDigest,
  artifact:{jsonlPath,summaryPath},
  sample:{
    first:members.slice(0,3).map(x=>({value:x.value,slotId:x.slotId,resourceKey:x.resourceKey})),
    last:members.slice(-3).map(x=>({value:x.value,slotId:x.slotId,resourceKey:x.resourceKey})),
  },
  truthBoundary:'FULL_SOURCE_MEMBER_MATERIALIZATION_NE_DOMAIN_EXISTENCE_NE_LIVENESS_NE_EXECUTION_AUTHORITY',
};
fs.writeFileSync(summaryPath,JSON.stringify(summary,null,2)+'\n');
console.log(JSON.stringify(summary));
