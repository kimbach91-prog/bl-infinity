import fs from 'node:fs';
import { sha256 } from '../lib/canonical.mjs';
import { compileInternetObservatoryKernel } from '../lib/internet-functional-fabric.mjs';

async function readJson(url){
  const response=await fetch(url,{headers:{accept:'application/json','user-agent':'DEUS-Internet-Observatory-Kernel/1.0'},signal:AbortSignal.timeout(15000)});
  if(!response.ok) throw new Error('HTTP '+response.status+' for '+url);
  const text=await response.text();
  return {url,status:response.status,sha256:sha256(text),json:JSON.parse(text)};
}

const observedAt=new Date().toISOString();
const cloudflare=await readJson('https://api.cloudflare.com/client/v4/ips');
const googleDns=await readJson('https://www.gstatic.com/ipranges/publicdns.json');

const cloudflareCidrs=[
  ...(cloudflare.json?.result?.ipv4_cidrs??[]),
  ...(cloudflare.json?.result?.ipv6_cidrs??[]),
];
const googleCidrs=(googleDns.json?.prefixes??[])
  .map(x=>x.ipv4Prefix??x.ipv6Prefix)
  .filter(Boolean);

if(cloudflareCidrs.length<1||googleCidrs.length<1) throw new Error('public provider catalog unexpectedly empty');

const runId=process.env.GITHUB_RUN_ID||'local-no-run-id';
const runAttempt=process.env.GITHUB_RUN_ATTEMPT||'1';
const receiptRef='github-actions-run:'+runId+':attempt:'+runAttempt;

const kernel=compileInternetObservatoryKernel({
  identities:[
    {type:'provider',value:'cloudflare'},
    {type:'provider',value:'google-public-dns'},
    ...cloudflareCidrs.map(value=>({type:'cidr',value})),
    ...googleCidrs.map(value=>({type:'cidr',value})),
  ],
  cidrs:[...cloudflareCidrs,...googleCidrs],
  computeRoutes:[{
    id:'github-actions-current-run',
    routeRoot:'GHA',
    platform:'GitHub Actions',
    resourceClass:'HOSTED_CPU_CI',
    executableState:'EXECUTED_VERIFIED',
    effectiveCredit:'POSITIVE',
    lastVerifiedUtc:observedAt,
    currentEvidenceAt:observedAt,
    currentExecutionReceipt:receiptRef,
  }],
  now:Date.parse(observedAt),
  maxFreshAgeMs:15*60*1000,
});

const addressCountBySource={
  cloudflare:cloudflareCidrs.reduce((sum,cidr)=>sum+BigInt(kernel.cidrCoverage.find(x=>x.cidr===cidr)?.addressCount??0),0n).toString(),
  googlePublicDns:googleCidrs.reduce((sum,cidr)=>sum+BigInt(kernel.cidrCoverage.find(x=>x.cidr===cidr)?.addressCount??0),0n).toString(),
};

const receipt={
  schema:'deus-internet-observatory-live-acceptance/1',
  observedAt,
  github:{runId,runAttempt,receiptRef},
  sources:{
    cloudflare:{url:cloudflare.url,status:cloudflare.status,sha256:cloudflare.sha256,prefixes:cloudflareCidrs.length},
    googlePublicDns:{url:googleDns.url,status:googleDns.status,sha256:googleDns.sha256,prefixes:googleCidrs.length,creationTime:googleDns.json?.creationTime??null,syncToken:googleDns.json?.syncToken??null},
  },
  addressCountBySource,
  kernel,
  acceptance:{
    sourceReads:true,
    allPublishedPrefixesVirtuallyAddressable:kernel.cidrCoverage.length===cloudflareCidrs.length+googleCidrs.length,
    boundaryProjectionVerified:kernel.cidrCoverage.every(x=>x.first.resourceKey&&x.last.resourceKey),
    currentComputeAdmitted:kernel.compute.currentAdmitted===1,
    zeroNetworkHostEnumeration:true,
  },
  truthBoundary:'LIVE_PUBLIC_CATALOG_READ_PLUS_GITHUB_ACTIONS_EXECUTION__VIRTUAL_ADDRESS_MAPPING_NE_LIVE_HOST_DISCOVERY__CURRENT_ADMISSION_IS_RUN_SCOPED',
};
receipt.digest=sha256(JSON.stringify(receipt));
fs.mkdirSync('.deus/internet-fabric',{recursive:true});
fs.writeFileSync('.deus/internet-fabric/observatory-kernel-v1.json',JSON.stringify(receipt,null,2)+'\n');
console.log(JSON.stringify({
  schema:receipt.schema,
  sources:receipt.sources,
  addressCountBySource,
  currentComputeAdmitted:kernel.compute.currentAdmitted,
  virtualCidrFamilies:kernel.virtualCidrFamilies,
  virtualAddressCount:kernel.virtualAddressCount,
  kernelDigest:kernel.kernelDigest,
  receiptDigest:receipt.digest,
}));
