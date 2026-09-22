import { createHash } from 'node:crypto';
import { loadGoogleServiceAccount, createServiceAccountTokenSource } from './lib/google-service-account.mjs';

const fileId=String(process.env.DEUS_WORKSTATION_PROBE_FILE_ID||'').trim();
const expectedSha=String(process.env.DEUS_WORKSTATION_PROBE_SHA256||'').trim().toLowerCase();
const expectedSize=Number(process.env.DEUS_WORKSTATION_PROBE_SIZE||0);

function fail(message, extra={}){
  console.error(JSON.stringify({event:'DEUS_DRIVE_ARTIFACT_PROBE_FAIL',message,...extra}));
  process.exit(1);
}

if(!fileId) fail('DEUS_WORKSTATION_PROBE_FILE_ID missing');
const credentials=loadGoogleServiceAccount();
if(!credentials) fail('Google service account credential missing');

console.log(JSON.stringify({
  event:'DEUS_DRIVE_ARTIFACT_PROBE_IDENTITY',
  clientEmail:credentials.clientEmail,
  fileId,
}));

const tokenSource=createServiceAccountTokenSource({
  credentials,
  scope:'https://www.googleapis.com/auth/drive.readonly',
});
const accessToken=await tokenSource();
const headers={authorization:`Bearer ${accessToken}`,accept:'application/json'};

const metaUrl=`https://www.googleapis.com/drive/v3/files/${encodeURIComponent(fileId)}?fields=id,name,size,mimeType,parents,shared&supportsAllDrives=true`;
const metaResp=await fetch(metaUrl,{headers,signal:AbortSignal.timeout(20_000)});
const metaText=await metaResp.text();
let meta={};
try{meta=metaText?JSON.parse(metaText):{};}catch{meta={raw:metaText};}
if(!metaResp.ok) fail('metadata request failed',{status:metaResp.status,body:meta});
if(expectedSize && Number(meta.size)!==expectedSize) fail('metadata size mismatch',{actual:Number(meta.size),expected:expectedSize});

const rawUrl=`https://www.googleapis.com/drive/v3/files/${encodeURIComponent(fileId)}?alt=media&supportsAllDrives=true`;
const rawResp=await fetch(rawUrl,{headers:{authorization:`Bearer ${accessToken}`},signal:AbortSignal.timeout(30_000)});
if(!rawResp.ok){
  const body=await rawResp.text();
  fail('download request failed',{status:rawResp.status,body:body.slice(0,1000)});
}
const bytes=Buffer.from(await rawResp.arrayBuffer());
if(expectedSize && bytes.length!==expectedSize) fail('download size mismatch',{actual:bytes.length,expected:expectedSize});
const sha=createHash('sha256').update(bytes).digest('hex');
if(expectedSha && sha!==expectedSha) fail('download SHA256 mismatch',{actual:sha,expected:expectedSha});

console.log(JSON.stringify({
  event:'DEUS_DRIVE_ARTIFACT_PROBE_PASS',
  clientEmail:credentials.clientEmail,
  fileId,
  name:meta.name||null,
  size:bytes.length,
  sha256:sha,
  mimeType:meta.mimeType||null,
  shared:meta.shared??null,
}));
