import fs from 'node:fs';
import { createHash } from 'node:crypto';

const BASELINE_DIGEST='520c9779ee08ca7484430a3c1b00cd610f9701136d5cf091f73cfef67f9b8907';
const SOURCES=[{"id":"RIR_APNIC","class":"NUMBERING_RIR","url":"https://ftp.apnic.net/stats/apnic/delegated-apnic-latest","baselineSha256":"bd770850a3cdfc09ca14273e361fb3a29430e32b2603c3164545a1c4f993888e"},{"id":"RIR_RIPE","class":"NUMBERING_RIR","url":"https://ftp.ripe.net/pub/stats/ripencc/delegated-ripencc-latest","baselineSha256":"d237d216a5a5f2a3097795407efbcc042c6a9611d01e68d681b8b64b20b6b9ed"},{"id":"RIR_ARIN","class":"NUMBERING_RIR","url":"https://ftp.arin.net/pub/stats/arin/delegated-arin-extended-latest","baselineSha256":"52e94b1653bdbc4114eee94722c5fbe8d8ad267968e1a38dc3a4466b54b296b7"},{"id":"RIR_LACNIC","class":"NUMBERING_RIR","url":"https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-latest","baselineSha256":"9e4ff3c9c2ba9b16369c21135b3fc3db41c79ef399129e654d621790a00e2204"},{"id":"RIR_AFRINIC","class":"NUMBERING_RIR","url":"https://ftp.afrinic.net/pub/stats/afrinic/delegated-afrinic-latest","baselineSha256":null},{"id":"DNS_ROOT_ZONE","class":"DNS_ROOT","url":"https://www.internic.net/domain/root.zone","baselineSha256":"3863797c7c0f209b4bc8a3acd7cdc24692e024d3c433187cc132a769bff57c9a"},{"id":"DNS_ROOT_HINTS","class":"DNS_ROOT","url":"https://www.internic.net/domain/named.root","baselineSha256":"75bfbceb2c0827b0eec94917452f41dc594e25a21482ac15514c314369b73726"},{"id":"ROOT_SERVERS","class":"DNS_ROOT","url":"https://root-servers.org/","baselineSha256":"0943846105cff92ade1f6e2437aa296d59ad143d33cb07d530178bbb57cd0ecb"},{"id":"RIPE_RIS_PEERS","class":"ROUTING_BGP","url":"https://stat.ripe.net/data/ris-peers/data.json","baselineSha256":"32784053a792fa3d982a344b4bed2a432273bee3dea9b5191cb9273bdaf6d0d8"},{"id":"ROUTEVIEWS","class":"ROUTING_BGP","url":"https://www.routeviews.org/routeviews/","baselineSha256":"532127967feb7e1ba5ee0fbbe19eb62a165161c7f78d554d02df905870c3f914"},{"id":"BGPSTREAM","class":"ROUTING_BGP","url":"https://bgpstream.caida.org/","baselineSha256":"df7a3dfea6a9955dddca6bf0c3e30a5e42dcd595799ad795c693fdf58392fb5d"},{"id":"PEERINGDB_NET_SAMPLE","class":"IX_PEERING","url":"https://www.peeringdb.com/api/net?limit=1","baselineSha256":"f9e495e6bdc8f98942f3c66f4e8aaca5ed5b1b8e8a95189e4e7a5b499bb48891"},{"id":"PEERINGDB_IX_SAMPLE","class":"IX_PEERING","url":"https://www.peeringdb.com/api/ix?limit=1","baselineSha256":"3813050d3eaf08da45c619f5140618b6c16f9cb215d91e194349aa3a7f20b567"},{"id":"COMMONCRAWL_COLLECTIONS","class":"WEB_CORPUS","url":"https://index.commoncrawl.org/collinfo.json","baselineSha256":"fdfe1131836096ec8ff6047997a035acbf464036a2ea09887239c949e0df41f9"},{"id":"COMMONCRAWL_HOME","class":"WEB_CORPUS","url":"https://commoncrawl.org/","baselineSha256":"f899df204c55deafa8beceaaf8fc91d708d35013888a9e2a939c129c3a0d6d1b"},{"id":"CHROME_CT_LOG_LIST","class":"CT_PKI","url":"https://www.gstatic.com/ct/log_list/v3/log_list.json","baselineSha256":"f207d6c07b6a0a76ac9c76bb3fbf39f42eeeb9350c1dab9e58a303ed47444684"},{"id":"CABFORUM","class":"CT_PKI","url":"https://cabforum.org/","baselineSha256":"9a7b0fd0c5a9deb1ff4d802b1b642c346079db6eee73843a6219693d4be17cdd"},{"id":"AWS_IP_RANGES","class":"CLOUD_RANGES","url":"https://ip-ranges.amazonaws.com/ip-ranges.json","baselineSha256":"9548fcab05cae4839cd3a63bff92783fe8d26523c544ae86202ab171ee632cd9"},{"id":"GOOGLE_CLOUD_RANGES","class":"CLOUD_RANGES","url":"https://www.gstatic.com/ipranges/cloud.json","baselineSha256":"ba68d267cdcf182864536dd607c5a657619d5780ddc70c5e39008da1a20a1584"},{"id":"GOOGLE_GLOBAL_RANGES","class":"CLOUD_RANGES","url":"https://www.gstatic.com/ipranges/goog.json","baselineSha256":"b6f79806369fd4283766d289359371194f97ab6038ed20367a5d3779ccf78f3d"},{"id":"CLOUDFLARE_IPS","class":"CLOUD_RANGES","url":"https://api.cloudflare.com/client/v4/ips","baselineSha256":"f3d0a35768afd4a9a8307aa1033d50b9fa011b73836c9235c170aa31acac5efd"},{"id":"GITHUB_META","class":"CLOUD_RANGES","url":"https://api.github.com/meta","baselineSha256":"850b1de90b0cdbaebf3f8c1eea095a1d99ea63ad0da8489f62d8d52dc54bb348"},{"id":"FASTLY_PUBLIC_IPS","class":"CLOUD_RANGES","url":"https://api.fastly.com/public-ip-list","baselineSha256":"d0fa4abe04cded896cf1a1d1a1c16ce2861ea4feb837ebd045a89c7b06a15ab5"},{"id":"RIPE_ATLAS_PROBES_SAMPLE","class":"MEASUREMENT","url":"https://atlas.ripe.net/api/v2/probes/?page_size=1","baselineSha256":"b10fd154b6c3b1e807287e1ca30e17ed9999d4c9eeb7d17b5bf6ea337a96b2a3"},{"id":"RIPE_ATLAS_HOME","class":"MEASUREMENT","url":"https://atlas.ripe.net/","baselineSha256":"288347d017c2d8f540792f4c71fc63a91299553621b9cd5a2d65d8e793f087ef"},{"id":"CAIDA_DATASETS","class":"MEASUREMENT","url":"https://www.caida.org/catalog/datasets/","baselineSha256":"f8806a932124b0bfb0c602ffbf4a52d926ae0caabd1505675d93121963c5dc24"},{"id":"AKASH_PROVIDER_API","class":"COMPUTE_MARKET","url":"https://console-api.akash.network/v1/providers","baselineSha256":"a3acc8eb0e3702c258d94e3d053884e4d7617209780c7cc51a3615d704111329"},{"id":"AIHORDE_PERFORMANCE","class":"COMPUTE_MARKET","url":"https://aihorde.net/api/v2/status/performance","baselineSha256":"4f93907b6d62e9b7c85b4b3e064eec995d7ed1bb5f37c256f0afb60eff74a2c2"},{"id":"BOINC_PROJECTS","class":"COMPUTE_MARKET","url":"https://boinc.berkeley.edu/projects.php","baselineSha256":"87cc6e2b82c60277a5929c5080681dc7c1344c061259e770e83a177b9114df46"}];
const OUT='.deus/global-internet-delta-registry/v1';
fs.mkdirSync(OUT,{recursive:true});
const UA={'user-agent':'DEUS-Global-Internet-Delta/1.0','accept':'application/json,text/plain,text/html,*/*'};
const sha=x=>createHash('sha256').update(x).digest('hex');

async function readSource(s){
  const t=Date.now();
  try{
    const r=await fetch(s.url,{headers:UA,redirect:'follow',signal:AbortSignal.timeout(25000)});
    const b=Buffer.from(await r.arrayBuffer());
    return {...s,ok:r.ok,status:r.status,finalUrl:r.url,bytes:b.length,sha256:sha(b),ms:Date.now()-t,
      etag:r.headers.get('etag'),lastModified:r.headers.get('last-modified'),contentLength:r.headers.get('content-length')};
  }catch(e){
    return {...s,ok:false,status:null,finalUrl:null,bytes:0,sha256:null,ms:Date.now()-t,error:String(e?.message||e),
      etag:null,lastModified:null,contentLength:null};
  }
}
const rows=[];
for(const s of SOURCES){
  const r=await readSource(s);
  let deltaState;
  if(r.ok && !s.baselineSha256) deltaState='RECOVERED';
  else if(!r.ok && s.baselineSha256) deltaState='REGRESSED_UNREACHABLE';
  else if(!r.ok && !s.baselineSha256) deltaState='STILL_HELD';
  else if(r.sha256===s.baselineSha256) deltaState='UNCHANGED';
  else deltaState='CONTENT_CHANGED';
  rows.push({...r,deltaState,truthBoundary:'HASH_DELTA_NE_SEMANTIC_CHANGE__SEMANTIC_CHANGE_NE_EXECUTION_AUTHORITY'});
}
const changed=rows.filter(x=>['RECOVERED','REGRESSED_UNREACHABLE','CONTENT_CHANGED'].includes(x.deltaState));
const classes=[...new Set(changed.map(x=>x.class))];
const stateCounts=Object.fromEntries([...new Set(rows.map(x=>x.deltaState))].sort().map(k=>[k,rows.filter(x=>x.deltaState===k).length]));
const validatorSeed=rows.map(x=>({id:x.id,class:x.class,url:x.url,sha256:x.sha256,ok:x.ok,status:x.status,etag:x.etag,lastModified:x.lastModified,contentLength:x.contentLength,bytes:x.bytes}));
const manifest={
  schema:'deus-global-internet-delta-registry/1',
  generatedAt:new Date().toISOString(),
  baselineDigest:BASELINE_DIGEST,
  sources:rows.length,
  reachable:rows.filter(x=>x.ok).length,
  stateCounts,
  deltaCount:changed.length,
  changedClasses:classes,
  changedSources:changed.map(x=>x.id),
  rows,
  next:'Rematerialize only changed classes/sources through the corresponding parser/member-ingestion lane; preserve unchanged canonical descriptors.',
  truthBoundary:'DELTA_HASH_NE_SEMANTIC_CHANGE__UNCHANGED_SOURCE_REUSES_CANON__MAPPING_NE_REMOTE_CONTROL__COMPUTE_REQUIRES_ACCORD_LEASE',
};
manifest.digest=sha(Buffer.from(JSON.stringify(manifest)));
fs.writeFileSync(OUT+'/delta.jsonl',rows.map(x=>JSON.stringify(x)).join('\n')+'\n');
fs.writeFileSync(OUT+'/validator-seed.json',JSON.stringify({schema:'deus-global-internet-validator-seed/1',generatedAt:manifest.generatedAt,baselineDigest:BASELINE_DIGEST,sources:validatorSeed},null,2)+'\n');
fs.writeFileSync(OUT+'/manifest.json',JSON.stringify(manifest,null,2)+'\n');

if(rows.length!==29) throw new Error('Expected 29 baseline sources');
if(rows.filter(x=>x.ok).length<20) throw new Error('Too few reachable sources for delta registry');
console.log(JSON.stringify({verdict:'PASS',sources:rows.length,reachable:rows.filter(x=>x.ok).length,stateCounts,deltaCount:changed.length,changedClasses:classes,changedSources:changed.map(x=>x.id),digest:manifest.digest}));
