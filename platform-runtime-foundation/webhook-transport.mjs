import crypto from 'node:crypto';

function req(v,n){ if(typeof v!=='string'||!v.trim()) throw new Error(`INVALID_${n}`); return v.trim(); }
function sha(v){ return crypto.createHash('sha256').update(v).digest('hex'); }
function hmac(secret, value){ return crypto.createHmac('sha256', secret).update(value).digest('hex'); }

export function createSignedWebhook({
  event,
  secret,
  timestamp_seconds = Math.floor(Date.now()/1000),
  delivery_id = null,
}){
  const eventId=req(event?.event_id,'EVENT_ID');
  const type=req(event?.type,'EVENT_TYPE');
  const tenantId=req(event?.tenant_id,'TENANT_ID');
  const s=req(secret,'SIGNING_SECRET');
  const deliveryId=delivery_id ? req(delivery_id,'DELIVERY_ID') : `delivery:${eventId}`;
  const payload={
    schema:'deus-webhook-event/1',
    event_id:eventId,
    tenant_id:tenantId,
    type,
    delivery_id:deliveryId,
    data:event.data ?? {},
    source_ref:event.source_ref ?? null,
  };
  const rawBody=JSON.stringify(payload);
  const signedPayload=`${timestamp_seconds}.${rawBody}`;
  const signature=hmac(s,signedPayload);
  return Object.freeze({
    rawBody,
    headers:Object.freeze({
      'content-type':'application/json',
      'x-deus-event-id':eventId,
      'x-deus-delivery-id':deliveryId,
      'x-deus-timestamp':String(timestamp_seconds),
      'x-deus-signature':`v1=${signature}`,
    }),
    metadata:Object.freeze({
      event_id:eventId,
      tenant_id:tenantId,
      type,
      delivery_id:deliveryId,
      timestamp_seconds,
      body_sha256:sha(rawBody),
      signature_version:'v1',
    }),
  });
}

export function verifySignedWebhook({
  rawBody,
  headers,
  secret,
  now_ms = Date.now(),
  tolerance_seconds = 300,
  replayStore = null,
}){
  const body=String(rawBody ?? '');
  const s=req(secret,'SIGNING_SECRET');
  const timestampRaw=header(headers,'x-deus-timestamp');
  const signatureRaw=header(headers,'x-deus-signature');
  const eventId=header(headers,'x-deus-event-id');
  const deliveryId=header(headers,'x-deus-delivery-id');

  if(!timestampRaw||!signatureRaw||!eventId||!deliveryId) return Object.freeze({ok:false,reason:'MISSING_REQUIRED_HEADER'});
  const timestamp=Number(timestampRaw);
  if(!Number.isInteger(timestamp)||timestamp<=0) return Object.freeze({ok:false,reason:'INVALID_TIMESTAMP'});
  const age=Math.abs(Math.floor(now_ms/1000)-timestamp);
  if(age>Number(tolerance_seconds)) return Object.freeze({ok:false,reason:'TIMESTAMP_OUTSIDE_TOLERANCE',age_seconds:age});
  const match=/^v1=([a-f0-9]{64})$/i.exec(signatureRaw);
  if(!match) return Object.freeze({ok:false,reason:'INVALID_SIGNATURE_FORMAT'});

  const expected=hmac(s,`${timestamp}.${body}`);
  const supplied=match[1].toLowerCase();
  const a=Buffer.from(expected,'hex'), b=Buffer.from(supplied,'hex');
  if(a.length!==b.length||!crypto.timingSafeEqual(a,b)) return Object.freeze({ok:false,reason:'SIGNATURE_MISMATCH'});

  const replayKey=`${eventId}::${deliveryId}::${timestamp}`;
  if(replayStore){
    if(replayStore.has(replayKey)) return Object.freeze({ok:false,reason:'REPLAY'});
    replayStore.add(replayKey);
  }
  return Object.freeze({
    ok:true,
    event_id:eventId,
    delivery_id:deliveryId,
    timestamp_seconds:timestamp,
    body_sha256:sha(body),
  });
}

export async function deliverSignedWebhook({
  url,
  event,
  secret,
  timeout_ms = 10_000,
  fetchImpl = globalThis.fetch,
  timestamp_seconds = Math.floor(Date.now()/1000),
  delivery_id = null,
}){
  if(typeof fetchImpl!=='function') throw new Error('fetch implementation required');
  const target=req(url,'WEBHOOK_URL');
  if(!/^https:\/\//i.test(target)) throw new Error('WEBHOOK_URL_MUST_BE_HTTPS');
  const signed=createSignedWebhook({event,secret,timestamp_seconds,delivery_id});
  const response=await fetchImpl(target,{
    method:'POST',
    headers:signed.headers,
    body:signed.rawBody,
    signal:AbortSignal.timeout(Number(timeout_ms)||10_000),
  });
  const responseText=await response.text();
  return Object.freeze({
    ok:response.ok,
    status:response.status,
    event_id:signed.metadata.event_id,
    delivery_id:signed.metadata.delivery_id,
    body_sha256:signed.metadata.body_sha256,
    response_sha256:sha(responseText),
    response_bytes:Buffer.byteLength(responseText),
    signature_version:'v1',
    secret_rendered:false,
    response_text:responseText,
  });
}

function header(headers,name){
  if(!headers) return null;
  if(typeof headers.get==='function') return headers.get(name);
  const lower=name.toLowerCase();
  for(const [k,v] of Object.entries(headers)) if(String(k).toLowerCase()===lower) return String(v);
  return null;
}
