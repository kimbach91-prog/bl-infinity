import { createHash, randomUUID } from 'node:crypto';

function required(value,name){
  const s=String(value??'').trim();
  if(!s) throw new Error(`${name} required`);
  return s;
}
function digest(value){
  return createHash('sha256').update(JSON.stringify(value)).digest('hex');
}

export class GoogleSheetsCanonicalBridge {
  constructor({
    spreadsheetId,
    tokenSource,
    fetchImpl=fetch,
    canonicalReadRange='10_LIGHT_BOOT!A2:O2',
    heartbeatRange='54_MACHINE_BRIDGE_HEALTH!A:H',
    instanceId=randomUUID(),
    clock=()=>Date.now(),
  }={}){
    this.spreadsheetId=required(spreadsheetId,'spreadsheetId');
    if(typeof tokenSource!=='function') throw new Error('tokenSource required');
    this.tokenSource=tokenSource;
    this.fetchImpl=fetchImpl;
    this.canonicalReadRange=required(canonicalReadRange,'canonicalReadRange');
    this.heartbeatRange=required(heartbeatRange,'heartbeatRange');
    this.instanceId=required(instanceId,'instanceId');
    this.clock=clock;
  }

  async #request(url,init={}){
    const accessToken=await this.tokenSource();
    const response=await this.fetchImpl(url,{
      ...init,
      headers:{
        authorization:`Bearer ${accessToken}`,
        accept:'application/json',
        ...(init.body?{'content-type':'application/json'}:{}),
        ...(init.headers||{}),
      },
      signal:init.signal||AbortSignal.timeout(20_000),
    });
    const text=await response.text();
    let body={};
    try{body=text?JSON.parse(text):{};}catch{body={raw:text};}
    if(!response.ok){
      const error=new Error(`google sheets request failed (${response.status})`);
      error.status=response.status;
      error.body=body;
      throw error;
    }
    return body;
  }

  async readRange(range=this.canonicalReadRange){
    const url=`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(this.spreadsheetId)}/values/${encodeURIComponent(range)}?majorDimension=ROWS`;
    const body=await this.#request(url);
    return {
      range:body.range??range,
      values:Array.isArray(body.values)?body.values:[],
    };
  }

  async appendHeartbeat({state='LIVE',receiptRef='',note=''}={}){
    const nowIso=new Date(this.clock()).toISOString();
    const row=[
      nowIso,
      this.instanceId,
      String(state),
      this.spreadsheetId,
      String(receiptRef||''),
      String(note||''),
      process.env.RAILWAY_SERVICE_ID||'',
      process.env.RAILWAY_DEPLOYMENT_ID||'',
    ];
    const url=`https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(this.spreadsheetId)}/values/${encodeURIComponent(this.heartbeatRange)}:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS`;
    const body=await this.#request(url,{method:'POST',body:JSON.stringify({values:[row]})});
    return {
      row,
      updatedRange:body.updates?.updatedRange??null,
      updatedRows:Number(body.updates?.updatedRows??0),
      digest:digest(row),
    };
  }

  async verifyReadWrite({receiptRef=''}={}){
    const read=await this.readRange();
    if(!read.values.length) throw new Error('canonical read returned no rows');
    const append=await this.appendHeartbeat({
      state:'LIVE',
      receiptRef,
      note:'machine bridge read/write canary',
    });
    if(append.updatedRows!==1) throw new Error('heartbeat append did not update exactly one row');
    return Object.freeze({
      schema:'deus-drive-machine-bridge-receipt/1',
      state:'LIVE',
      spreadsheetId:this.spreadsheetId,
      canonicalReadRange:this.canonicalReadRange,
      heartbeatRange:this.heartbeatRange,
      readRowCount:read.values.length,
      heartbeatUpdatedRange:append.updatedRange,
      heartbeatDigest:append.digest,
      instanceId:this.instanceId,
      truthBoundary:'LIVE_MEANS_THIS_MACHINE_IDENTITY_READ_CANONICAL_RANGE_AND_APPENDED_ONE_HEARTBEAT_ROW__IT_DOES_NOT_GRANT_AUTHORITY_BEYOND_SHARED_FILE_SCOPES',
    });
  }
}
