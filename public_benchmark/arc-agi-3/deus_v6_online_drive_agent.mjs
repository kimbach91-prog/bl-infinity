import http from 'node:http';
import crypto from 'node:crypto';

const ARC_BASE='https://arcprize.org';
const ARC_KEY=process.env.ARC_API_KEY||'';
const SHEET_ID=process.env.DEUS_LIVEBUS_SPREADSHEET_ID||'1pVtDbKFGECbogSR0-nrVDEecF8xQNelCux6GFUEmVrQ';
const SA=JSON.parse(process.env.DEUS_GOOGLE_SERVICE_ACCOUNT_JSON||'{}');
const GAME_PREFIX=process.env.DEUS_ARC_GAME||'ls20';
const MAX_TURNS=Number(process.env.DEUS_ARC_MAX_TURNS||24);
const JOB_TIMEOUT_MS=Number(process.env.DEUS_ARC_JOB_TIMEOUT_MS||120000);
const PORT=Number(process.env.PORT||8080);
const SOURCE_URL='https://github.com/kimbach91-prog/bl-infinity/tree/deus/arc-scorecard-ab-20260926/public_benchmark/arc-agi-3';

let finalResult=null;
http.createServer((req,res)=>{
  res.setHeader('content-type','application/json');
  if(req.url==='/health') return res.end(JSON.stringify({ok:true,running:!finalResult,result:finalResult}));
  res.end(JSON.stringify({ok:true}));
}).listen(PORT,'0.0.0.0');

const b64u=(v)=>Buffer.from(typeof v==='string'?v:JSON.stringify(v)).toString('base64url');
async function googleToken(){
  const now=Math.floor(Date.now()/1000);
  const head=b64u({alg:'RS256',typ:'JWT'});
  const body=b64u({iss:SA.client_email,scope:'https://www.googleapis.com/auth/spreadsheets',aud:SA.token_uri||'https://oauth2.googleapis.com/token',iat:now,exp:now+3600});
  const sign=crypto.createSign('RSA-SHA256'); sign.update(head+'.'+body); sign.end();
  const assertion=head+'.'+body+'.'+sign.sign(SA.private_key).toString('base64url');
  const r=await fetch(SA.token_uri||'https://oauth2.googleapis.com/token',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:new URLSearchParams({grant_type:'urn:ietf:params:oauth:grant-type:jwt-bearer',assertion}),signal:AbortSignal.timeout(15000)});
  const j=await r.json(); if(!r.ok||!j.access_token) throw new Error('google token '+r.status+' '+JSON.stringify(j).slice(0,300));
  return j.access_token;
}
let gToken=null,gTokenAt=0;
async function gfetch(path,opt={}){
  if(!gToken||Date.now()-gTokenAt>3000000){gToken=await googleToken();gTokenAt=Date.now();}
  let last=null;
  for(let attempt=0;attempt<7;attempt++){
    const r=await fetch('https://sheets.googleapis.com/v4/spreadsheets/'+SHEET_ID+path,{...opt,headers:{authorization:'Bearer '+gToken,'content-type':'application/json',...(opt.headers||{})},signal:AbortSignal.timeout(20000)});
    const t=await r.text(); let j;try{j=JSON.parse(t)}catch{j={raw:t.slice(0,500)}};
    if(r.ok)return j;
    last={status:r.status,body:j};
    if(r.status!==429)throw new Error('sheets '+r.status+' '+JSON.stringify(j).slice(0,500));
    const retryHeader=Number(r.headers.get('retry-after')||0);
    const delay=Math.max(15000,retryHeader*1000,15000*(attempt+1));
    console.log(JSON.stringify({event:'DEUS_SHEETS_QUOTA_BACKOFF',attempt:attempt+1,delay_ms:delay}));
    await new Promise(resolve=>setTimeout(resolve,delay));
  }
  throw new Error('sheets '+last.status+' '+JSON.stringify(last.body).slice(0,500));
}
const HEAD=['JOB_ID','TARGET_NODE','STATE','CREATED_AT_UTC','NOT_BEFORE_UTC','EXPIRES_AT_UTC','AUTHORITY_REF','COMMAND_MODE','COMMAND_TEXT','ARGS_JSON','WORKDIR_REL','ENV_JSON','TIMEOUT_S','MAX_OUTPUT_BYTES','LEASE_OWNER','LEASE_ACQUIRED_AT_UTC','LEASE_UNTIL_UTC','STARTED_AT_UTC','FINISHED_AT_UTC','EXIT_CODE','STDOUT_SHA256','STDERR_SHA256','STDOUT_PREVIEW','STDERR_PREVIEW','RESULT_REF','RECEIPT_ID','ATTEMPT','NOTES'];
function iso(ms=Date.now()){return new Date(ms).toISOString();}
async function appendBrain3(prompt,turn){
  const jid='JOB-DEUS-ARC3-V6-ONLINE-'+Date.now()+'-'+crypto.randomBytes(4).toString('hex').toUpperCase();
  const row=[jid,'workstation-win-001','QUEUED',iso(),'',
    iso(Date.now()+Math.max(180000,JOB_TIMEOUT_MS+60000)),'AUTH-GMAIL-REMOTE-EXEC-1a0ce128e8726a83',
    'NATIVE_INFERENCE_SCOPED','CHAT_V1',JSON.stringify([prompt]),'arc3-v6-online-fresh-agent','{}',
    String(Math.ceil(JOB_TIMEOUT_MS/1000)),'65536','','','','','','','','','','','','','0',
    'DEUS V6 fresh ARC ONLINE decision turn '+turn+'; owner scorecard; no route replay.'];
  const range=encodeURIComponent('84_WORKSTATION_REMOTE_JOBS!A:AB');
  const j=await gfetch('/values/'+range+':append?valueInputOption=RAW&insertDataOption=INSERT_ROWS',{method:'POST',body:JSON.stringify({values:[row]})});
  const m=String(j.updates?.updatedRange||'').match(/!A?(\d+):/); if(!m)throw new Error('append range '+JSON.stringify(j));
  return {jid,row:Number(m[1])};
}
async function readBrain3(row){
  const range=encodeURIComponent('84_WORKSTATION_REMOTE_JOBS!A'+row+':AB'+row);
  const j=await gfetch('/values/'+range);
  const v=(j.values?.[0]||[]).concat(Array(28).fill('')).slice(0,28); return Object.fromEntries(HEAD.map((h,i)=>[h,v[i]||'']));
}
const sleep=(ms)=>new Promise(r=>setTimeout(r,ms));
async function infer(prompt,turn){
  const x=await appendBrain3(prompt,turn); const end=Date.now()+JOB_TIMEOUT_MS+45000;
  let rec=null;
  while(Date.now()<end){
    rec=await readBrain3(x.row);
    if(['SUCCEEDED','FAILED','REJECTED','EXPIRED','CANCELLED'].includes(rec.STATE)){
      if(rec.STATE!=='SUCCEEDED'||(rec.EXIT_CODE&&String(rec.EXIT_CODE)!=='0'))throw new Error('Brain3 '+x.jid+' '+rec.STATE+' '+rec.STDERR_PREVIEW.slice(0,400));
      const p=JSON.parse(rec.STDOUT_PREVIEW||'{}');
      return {text:String(p.content||''),job_id:x.jid,receipt_id:rec.RECEIPT_ID||null,latency_s:p.latency_s??null,usage:p.usage??null,model:p.model??null};
    }
    await sleep(15000);
  }
  throw new Error('Brain3 timeout '+x.jid+' last='+(rec?.STATE||'UNKNOWN'));
}

const jar=new Map();
function absorb(r){const xs=r.headers.getSetCookie?.()||[];for(const s of xs){const p=s.split(';')[0],i=p.indexOf('=');if(i>0)jar.set(p.slice(0,i),p.slice(i+1));}}
function ah(){return {'X-API-Key':ARC_KEY,Accept:'application/json','Content-Type':'application/json',...(jar.size?{Cookie:[...jar].map(([k,v])=>k+'='+v).join('; ')}:{})};}
async function arc(path,opt={}){
  const r=await fetch(ARC_BASE+path,{...opt,headers:{...ah(),...(opt.headers||{})},signal:AbortSignal.timeout(20000)}); absorb(r); const t=await r.text(); let j;try{j=JSON.parse(t)}catch{j={raw:t.slice(0,500)}}; if(!r.ok)throw new Error('ARC '+path+' '+r.status+' '+JSON.stringify(j).slice(0,700)); return j;
}
function grid(frame){
  let g=frame;
  if(Array.isArray(g)&&g.length&&Array.isArray(g[0])&&g[0].length&&Array.isArray(g[0][0])) g=g[g.length-1];
  return Array.isArray(g)?g:[];
}
function gridText(g){const A='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';return g.map(r=>r.map(v=>A[Number(v)]??'?').join('')).join('\n');}
function dcount(a,b){if(!a?.length||!b?.length||a.length!==b.length||a[0].length!==b[0].length)return null;let n=0;for(let y=0;y<a.length;y++)for(let x=0;x<a[y].length;x++)if(a[y][x]!==b[y][x])n++;return n;}
function stagnationGuard(history,legal){
  if(history.length<6)return null;
  const tail=history.slice(-6);
  const blocked=tail[0].action;
  const stagnant=tail.every(x=>x.action===blocked&&Number(x.levels_after||0)===Number(x.levels_before||0));
  if(!stagnant)return null;
  const recent=history.slice(-18),counts=Object.fromEntries(legal.map(a=>[a,0]));
  for(const x of recent)if(counts[x.action]!==undefined)counts[x.action]++;
  const candidates=legal.filter(a=>a!==blocked).sort((a,b)=>(counts[a]-counts[b])||a.localeCompare(b));
  if(!candidates.length)return null;
  return {blocked,force:candidates[0],reason:'six_consecutive_same_action_without_level_gain',counts};
}
function decision(text,legal,w,h,turn,guard){
  let o=null;try{o=JSON.parse(text.trim())}catch{const m=text.match(/\{[\s\S]*\}/);if(m)try{o=JSON.parse(m[0])}catch{}}
  if(o&&legal.includes(String(o.action||'').toUpperCase())){
    let a=String(o.action).toUpperCase();let override=false;
    if(guard&&a===guard.blocked){a=guard.force;override=true;}
    const rep=override?1:Math.max(1,Math.min(8,Number(o.repeat||1)||1));
    return {action:a,repeat:rep,memory:String(o.memory||'').slice(0,900),fallback:false,anti_loop_override:override};
  }
  const a=guard?.force||legal[turn%legal.length];
  return {action:a,repeat:1,memory:'fallback systematic action probe',fallback:true,anti_loop_override:Boolean(guard)};
}

async function main(){
  if(!ARC_KEY||!SA.private_key)throw new Error('missing ARC or service-account credential');
  const games=await arc('/api/games'); const game=games.find(x=>String(x.game_id||'').startsWith(GAME_PREFIX)); if(!game)throw new Error('game missing '+GAME_PREFIX);
  const opened=await arc('/api/scorecard/open',{method:'POST',body:JSON.stringify({tags:['deus-v6','fresh-agent','brain3-qwen-strong','owner-bound','no-route-replay','anti-loop-r4'],source_url:SOURCE_URL,opaque:{system:'DEUS V6 fresh agent',cognition:'Brain3 Qwen3-4B strong via receipt-gated CHAT_V1',capability_score:true,semi_private:false}})});
  const card=opened.card_id; let fr=null;const history=[],receipts=[];let memory='',fallbacks=0,actions=0,antiLoopOverrides=0;
  try{
    fr=await arc('/api/cmd/RESET',{method:'POST',body:JSON.stringify({card_id:card,game_id:game.game_id})});
    for(let turn=0;turn<MAX_TURNS;turn++){
      if(['WIN','GAME_OVER'].includes(String(fr.state)))break;
      const g=grid(fr.frame),h=g.length,w=g[0]?.length||1;const legal=(fr.available_actions||[]).map(n=>'ACTION'+Number(n));
      if(!legal.length)break;
      const guard=stagnationGuard(history,legal);
      const antiLoop=guard?('ANTI_LOOP: '+guard.blocked+' has been repeated without any level gain. Do not choose it this turn; prefer '+guard.force+' or another less-used legal action.'): 'ANTI_LOOP: none.';
      const prompt='You are the DEUS V6 ARC-AGI-3 decision cortex in a fresh live public-development run. Do not replay a memorized route and do not copy placeholder text. Infer action semantics only from the visible grid and the actual transition history. First identify what prior actions changed, then choose the next action that most increases evidence or progress. Complete a level before optimizing action count. If recent actions repeat without level gain, deliberately test a different legal action. Output one raw JSON object with exactly three keys: action, repeat, memory. action MUST equal one legal action string; repeat MUST be an integer 1..8 and use values above 1 only when repeated behavior is supported by observed transitions; memory MUST be a concrete, state-specific hypothesis mentioning observed movement/change, never generic filler. No markdown, no explanation outside JSON.\n'+
        'turn='+turn+' state='+fr.state+' levels_completed='+Number(fr.levels_completed||0)+' size='+w+'x'+h+'\nlegal='+JSON.stringify(legal)+'\n'+antiLoop+'\nmemory='+memory+'\nrecent='+JSON.stringify(history.slice(-8))+'\ngrid_rows_top_to_bottom:\n'+gridText(g);
      const inf=await infer(prompt,turn);receipts.push(inf);const d=decision(inf.text,legal,w,h,turn,guard);memory=d.memory;fallbacks+=d.fallback?1:0;antiLoopOverrides+=d.anti_loop_override?1:0;
      for(let k=0;k<d.repeat;k++){
        const before=grid(fr.frame),bl=Number(fr.levels_completed||0);
        fr=await arc('/api/cmd/'+d.action,{method:'POST',body:JSON.stringify({game_id:game.game_id,guid:fr.guid,reasoning:JSON.stringify({deus_turn:turn,brain3_receipt:inf.receipt_id||null})})});
        actions++;
        history.push({turn,action:d.action,changed:dcount(before,grid(fr.frame)),levels_before:bl,levels_after:Number(fr.levels_completed||0),state:fr.state,brain3_job:inf.job_id,receipt:inf.receipt_id});
        if(['WIN','GAME_OVER'].includes(String(fr.state))||Number(fr.levels_completed||0)!==bl)break;
      }
    }
    const cl=await arc('/api/scorecard/close',{method:'POST',body:JSON.stringify({card_id:card})});
    return {schema:'deus-arc3-v6-online-fresh-agent/3',state:'VERIFIED_DONE',card_id:card,scorecard_url:ARC_BASE+'/scorecards/'+card,game_id:game.game_id,score:cl.score,levels_completed:cl.total_levels_completed,total_levels:cl.total_levels,total_actions:cl.total_actions,local_actions:actions,brain3_calls:receipts.length,fallbacks,anti_loop_overrides:antiLoopOverrides,final_state:fr?.state||null,route_replay:false,semi_private:false,model_sha256:'7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5',receipts:receipts.map(x=>x.receipt_id).filter(Boolean),history_tail:history.slice(-8)};
  }catch(e){
    let cl=null;try{cl=await arc('/api/scorecard/close',{method:'POST',body:JSON.stringify({card_id:card})})}catch{}
    return {schema:'deus-arc3-v6-online-fresh-agent/3',state:'FAILED',card_id:card,scorecard_url:ARC_BASE+'/scorecards/'+card,error_type:e.constructor?.name||'Error',error:String(e.message||e).slice(0,1000),brain3_calls:receipts.length,local_actions:actions,fallbacks,anti_loop_overrides:antiLoopOverrides,closed_score:cl?.score??null,closed_actions:cl?.total_actions??null,history_tail:history.slice(-5)};
  }
}
main().then(r=>{finalResult=r;console.log('DEUS_ARC3_V6_RESULT='+JSON.stringify(r));}).catch(e=>{finalResult={state:'FAILED',error:String(e)};console.error('DEUS_ARC3_V6_FATAL='+JSON.stringify(finalResult));});
