/** Pure public-data operators. No network I/O, dynamic evaluation or authority. */
import { createHash } from 'node:crypto';
const MOD=1n<<256n;
function canonical(x) { if(x===null||typeof x!=='object')return JSON.stringify(x);if(Array.isArray(x))return '['+x.map(canonical).join(',')+']';return '{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',')+'}'; }
export function atlasSummary(input) {
  const rows=input.value.rows;if(!Array.isArray(rows))throw Error('ROWS_REQUIRED');
  let checksum=0n,ipv4=0,ipv6=0;const bySource={};
  for(const r of rows){if(typeof r.source!=='string'||typeof r.prefix!=='string'||!r.prefix.includes('/'))throw Error('ATLAS_ROW_CONTRACT');
    if(['__proto__','constructor','prototype'].includes(r.source))throw Error('INVALID_SOURCE_KEY');
    bySource[r.source]=(bySource[r.source]??0)+1;r.prefix.includes(':')?ipv6++:ipv4++;
    checksum=(checksum+BigInt('0x'+createHash('sha256').update(canonical(r)).digest('hex')))%MOD;}
  return {schema:'atlas-range-summary/1',count:rows.length,ipv4,ipv6,bySource,contentSum256:checksum.toString(16).padStart(64,'0'),classification:'PUBLISHED_DATA_NOT_EXECUTION_AUTHORITY'};
}
export function reduceAtlas(input) {
  const children=Object.values(input.upstream);if(!children.length)throw Error('CHILDREN_REQUIRED');
  let count=0,ipv4=0,ipv6=0,checksum=0n;const bySource={};
  for(const r of children){if(r.schema!=='atlas-range-summary/1'||r.classification!=='PUBLISHED_DATA_NOT_EXECUTION_AUTHORITY')throw Error('SUMMARY_CONTRACT');
    count+=r.count;ipv4+=r.ipv4;ipv6+=r.ipv6;checksum=(checksum+BigInt('0x'+r.contentSum256))%MOD;
    for(const [k,n]of Object.entries(r.bySource)){if(['__proto__','constructor','prototype'].includes(k))throw Error('INVALID_SOURCE_KEY');bySource[k]=(bySource[k]??0)+n;}}
  return {schema:'atlas-range-summary/1',count,ipv4,ipv6,bySource,contentSum256:checksum.toString(16).padStart(64,'0'),classification:'PUBLISHED_DATA_NOT_EXECUTION_AUTHORITY'};
}
export function integerSum(input) {
  const rows=input.value?.numbers??Object.values(input.upstream).map(x=>x.sum);
  if(!Array.isArray(rows))throw Error('NUMBERS_REQUIRED');let sum=0n;
  for(const n of rows){if(!/^-?\d+$/.test(String(n)))throw Error('INTEGER_REQUIRED');sum+=BigInt(n);}
  return {sum:sum.toString()};
}

// File inputs are additionally checked against the host's allowlisted CAS root by
// the operator's validateInput callback before either execution OR cache reuse.
export async function atlasBlobSummary(input) {
  if(input.value.rows)return atlasSummary(input);
  const {readFileSync}=await import('node:fs');const {basename}=await import('node:path');
  const {blobPath,blobSha256}=input.value;
  if(!/^[a-f0-9]{64}$/.test(blobSha256)||basename(blobPath)!==blobSha256+'.json')throw Error('CAS_ID_REQUIRED');
  const b=readFileSync(blobPath);if(b.length>8*1024*1024||createHash('sha256').update(b).digest('hex')!==blobSha256)throw Error('CAS_HASH_OR_SIZE');
  return atlasSummary({value:{rows:JSON.parse(b)}});
}
