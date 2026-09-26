import {createSignedWebhook,verifySignedWebhook,deliverSignedWebhook} from './webhook-transport.mjs';

const secret='synthetic-live-canary-secret-not-sensitive';
const now=Math.floor(Date.now()/1000);
const event={
  event_id:'live-webhook-canary-'+now,
  tenant_id:'platform-prod-canary-A',
  type:'job.completed',
  data:{job_id:'synthetic-live-canary',value:1},
  source_ref:'GHA:webhook-live-canary'
};
const targets=[
  process.env.DEUS_WEBHOOK_CANARY_URL,
  'https://httpbin.org/anything',
  'https://postman-echo.com/post'
].filter(Boolean);

let lastError=null;
for(const url of [...new Set(targets)]){
  try{
    const signed=createSignedWebhook({event,secret,timestamp_seconds:now});
    const local=verifySignedWebhook({rawBody:signed.rawBody,headers:signed.headers,secret,now_ms:now*1000,tolerance_seconds:30});
    if(!local.ok) throw new Error('local verification failed: '+local.reason);

    const result=await deliverSignedWebhook({url,event,secret,timestamp_seconds:now,timeout_ms:15_000});
    if(!result.ok) throw new Error('remote HTTP '+result.status);
    let parsed={};
    try{ parsed=JSON.parse(result.response_text); }catch{}
    const echoedHeaders=parsed.headers||{};
    const echoedBody=parsed.json||parsed.data||parsed.body||null;
    const sig=Object.entries(echoedHeaders).find(([k])=>k.toLowerCase()==='x-deus-signature')?.[1] ?? null;
    const eventId=Object.entries(echoedHeaders).find(([k])=>k.toLowerCase()==='x-deus-event-id')?.[1] ?? null;
    if(sig!==signed.headers['x-deus-signature']) throw new Error('signature header not echoed');
    if(eventId!==event.event_id) throw new Error('event id not echoed');
    const bodyObj=typeof echoedBody==='string' ? JSON.parse(echoedBody) : echoedBody;
    if(!bodyObj||bodyObj.event_id!==event.event_id||bodyObj.tenant_id!==event.tenant_id) throw new Error('body not echoed');

    console.log(JSON.stringify({
      marker:'SIGNED_WEBHOOK_CANARY_PASS',
      target:new URL(url).hostname,
      status:result.status,
      event_id:event.event_id,
      body_sha256:result.body_sha256,
      signature_version:result.signature_version,
      secret_rendered:false
    }));
    process.exit(0);
  }catch(error){
    lastError=error;
    console.error(JSON.stringify({marker:'SIGNED_WEBHOOK_TARGET_FAIL',target:new URL(url).hostname,error:error.message}));
  }
}
throw lastError||new Error('no webhook canary target');
