import http from 'node:http';
import crypto from 'node:crypto';

const ARC_BASE='https://arcprize.org';
const ARC_KEY=process.env.ARC_API_KEY||'';
const SHEET_ID=process.env.DEUS_LIVEBUS_SPREADSHEET_ID||'1pVtDbKFGECbogSR0-nrVDEecF8xQNelCux6GFUEmVrQ';
const SA=JSON.parse(process.env.DEUS_GOOGLE_SERVICE_ACCOUNT_JSON||'{}');
const GAME_PREFIX=process.env.DEUS_ARC_GAME||'ls20';
const MAX_CALLS=Number(process.env.DEUS_ARC_MAX_CALLS||16);
const MAX_ACTIONS=Number(process.env.DEUS_ARC_MAX_ACTIONS||64);
const JOB_TIMEOUT_MS=Number(process.env.DEUS_ARC_JOB_TIMEOUT_MS||120000);
const JOB_QUEUE_WAIT_MS=Number(process.env.DEUS_ARC_JOB_QUEUE_WAIT_MS||900000);
const PORT=Number(process.env.PORT||8080);
const SOURCE_URL='https://github.com/kimbach91-prog/bl-infinity/tree/deus/arc-scorecard-ab-20260926/public_benchmark/arc-agi-3';
const MODEL_SHA='7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5';
const R335_SOURCE_SHA='460f10d4ddacd8418202045caa5b489c9d179eb2ae9e50b297daff4de0c732d2';

let finalResult=null;
http.createServer((req,res)=>{
  res.setHeader('content-type','application/json');
  if(req.url==='/health') return res.end(JSON.stringify({ok:true,running:!finalResult,result:finalResult}));
  res.end(JSON.stringify({ok:true}));
}).listen(PORT,'0.0.0.0');

const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const sha=v=>crypto.createHash('sha256').update(typeof v==='string'?v:JSON.stringify(v)).digest('hex');
const b64u=v=>Buffer.from(typeof v==='string'?v:JSON.stringify(v)).toString('base64url');

async function googleToken(){
  const now=Math.floor(Date.now()/1000);
  const h=b64u({alg:'RS256',typ:'JWT'});
  const p=b64u({iss:SA.client_email,scope:'https://www.googleapis.com/auth/spreadsheets',aud:SA.token_uri||'https://oauth2.googleapis.com/token',iat:now,exp:now+3600});
  const sign=crypto.createSign('RSA-SHA256');sign.update(h+'.'+p);sign.end();
  const assertion=h+'.'+p+'.'+sign.sign(SA.private_key).toString('base64url');
  const r=await fetch(SA.token_uri||'https://oauth2.googleapis.com/token',{method:'POST',headers:{'content-type':'application/x-www-form-urlencoded'},body:new URLSearchParams({grant_type:'urn:ietf:params:oauth:grant-type:jwt-bearer',assertion}),signal:AbortSignal.timeout(15000)});
  const j=await r.json();if(!r.ok||!j.access_token)throw new Error('google token '+r.status);
  return j.access_token;
}
let gToken=null,gTokenAt=0;
async function gfetch(path,opt={}){
  if(!gToken||Date.now()-gTokenAt>3000000){gToken=await googleToken();gTokenAt=Date.now();}
  let last=null;
  for(let attempt=0;attempt<7;attempt++){
    const r=await fetch('https://sheets.googleapis.com/v4/spreadsheets/'+SHEET_ID+path,{...opt,headers:{authorization:'Bearer '+gToken,'content-type':'application/json',...(opt.headers||{})},signal:AbortSignal.timeout(20000)});
    const t=await r.text();let j;try{j=JSON.parse(t)}catch{j={raw:t.slice(0,500)}}
    if(r.ok)return j;
    last={status:r.status,body:j};
    if(r.status!==429)throw new Error('sheets '+r.status+' '+JSON.stringify(j).slice(0,500));
    const retryHeader=Number(r.headers.get('retry-after')||0);
    await sleep(Math.max(15000,retryHeader*1000,15000*(attempt+1)));
  }
  throw new Error('sheets '+last.status+' '+JSON.stringify(last.body).slice(0,500));
}
const HEAD=['JOB_ID','TARGET_NODE','STATE','CREATED_AT_UTC','NOT_BEFORE_UTC','EXPIRES_AT_UTC','AUTHORITY_REF','COMMAND_MODE','COMMAND_TEXT','ARGS_JSON','WORKDIR_REL','ENV_JSON','TIMEOUT_S','MAX_OUTPUT_BYTES','LEASE_OWNER','LEASE_ACQUIRED_AT_UTC','LEASE_UNTIL_UTC','STARTED_AT_UTC','FINISHED_AT_UTC','EXIT_CODE','STDOUT_SHA256','STDERR_SHA256','STDOUT_PREVIEW','STDERR_PREVIEW','RESULT_REF','RECEIPT_ID','ATTEMPT','NOTES'];
const iso=(ms=Date.now())=>new Date(ms).toISOString();

async function appendBrain3(prompt,turn){
  const jid='JOB-DEUS-ARC3-R7-R335M-'+Date.now()+'-'+crypto.randomBytes(4).toString('hex').toUpperCase();
  const row=[jid,'workstation-win-001','QUEUED',iso(),'',iso(Date.now()+Math.max(180000,JOB_QUEUE_WAIT_MS+60000)),'AUTH-GMAIL-REMOTE-EXEC-1a0ce128e8726a83','NATIVE_INFERENCE_SCOPED','CHAT_V1',JSON.stringify([prompt]),'arc3-v6-online-r335','{}',String(Math.ceil(JOB_TIMEOUT_MS/1000)),'65536','','','','','','','','','','','','','0','DEUS V6 R7 R335+motion-derived generic online decision turn '+turn+'; no route replay.'];
  const range=encodeURIComponent('84_WORKSTATION_REMOTE_JOBS!A:AB');
  const j=await gfetch('/values/'+range+':append?valueInputOption=RAW&insertDataOption=INSERT_ROWS',{method:'POST',body:JSON.stringify({values:[row]})});
  const m=String(j.updates?.updatedRange||'').match(/!A?(\d+):/);if(!m)throw new Error('append range');
  return {jid,row:Number(m[1])};
}
async function readBrain3(row){
  const range=encodeURIComponent('84_WORKSTATION_REMOTE_JOBS!A'+row+':AB'+row);
  const j=await gfetch('/values/'+range);
  const v=(j.values?.[0]||[]).concat(Array(28).fill('')).slice(0,28);
  return Object.fromEntries(HEAD.map((h,i)=>[h,v[i]||'']));
}
async function infer(prompt,turn){
  const deadline=Date.now()+JOB_QUEUE_WAIT_MS;
  const attempts=[];
  for(let retry=0;retry<3 && Date.now()<deadline;retry++){
    const x=await appendBrain3(prompt,turn);attempts.push(x.jid);
    let rec=null;
    while(Date.now()<deadline){
      rec=await readBrain3(x.row);
      if(['SUCCEEDED','FAILED','REJECTED','EXPIRED','CANCELLED'].includes(rec.STATE)){
        if(rec.STATE==='SUCCEEDED'&&(!rec.EXIT_CODE||String(rec.EXIT_CODE)==='0')){
          const p=JSON.parse(rec.STDOUT_PREVIEW||'{}');
          return {text:String(p.content||''),job_id:x.jid,receipt_id:rec.RECEIPT_ID||null,latency_s:p.latency_s??null,usage:p.usage??null,model:p.model??null,retry_count:retry,attempt_jobs:attempts};
        }
        throw new Error('Brain3 '+x.jid+' '+rec.STATE+' '+rec.STDERR_PREVIEW.slice(0,400));
      }
      if(rec.STATE==='RUNNING'){
        const lease=Date.parse(String(rec.LEASE_UNTIL_UTC||''));
        if(Number.isFinite(lease)&&Date.now()>lease+30000){
          console.log(JSON.stringify({event:'DEUS_ARC_STALE_LEASE_RETRY',turn,retry,job_id:x.jid,lease_until:rec.LEASE_UNTIL_UTC}));
          break;
        }
      }
      await sleep(15000);
    }
  }
  throw new Error('Brain3 queue timeout/retry exhausted turn='+turn+' attempts='+attempts.join(','));
}

const jar=new Map();
function absorb(r){for(const s of (r.headers.getSetCookie?.()||[])){const p=s.split(';')[0],i=p.indexOf('=');if(i>0)jar.set(p.slice(0,i),p.slice(i+1));}}
function ah(){return {'X-API-Key':ARC_KEY,Accept:'application/json','Content-Type':'application/json',...(jar.size?{Cookie:[...jar].map(([k,v])=>k+'='+v).join('; ')}:{})};}
async function arc(path,opt={}){
  const r=await fetch(ARC_BASE+path,{...opt,headers:{...ah(),...(opt.headers||{})},signal:AbortSignal.timeout(25000)});absorb(r);
  const t=await r.text();let j;try{j=JSON.parse(t)}catch{j={raw:t.slice(0,500)}};if(!r.ok)throw new Error('ARC '+path+' '+r.status+' '+JSON.stringify(j).slice(0,700));return j;
}

function grid(frame){
  let g=frame;
  if(Array.isArray(g)&&g.length&&Array.isArray(g[0])&&g[0].length&&Array.isArray(g[0][0]))g=g[g.length-1];
  return Array.isArray(g)?g:[];
}
function rle(row){
  const out=[];for(const raw of row){const v=Number(raw);if(out.length&&out[out.length-1][0]===v)out[out.length-1][1]++;else out.push([v,1]);}return out;
}
function describe(frame){
  const g=grid(frame).map(r=>r.map(Number));if(!g.length||!g[0]?.length)throw new Error('EMPTY_FRAME');
  const h=g.length,w=g[0].length;
  const counts=new Map();for(const row of g)for(const v of row)counts.set(v,(counts.get(v)||0)+1);
  const background=[...counts.entries()].sort((a,b)=>b[1]-a[1])[0][0];
  const seen=new Set(),components=[];
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){
    const key=x+','+y;if(seen.has(key)||g[y][x]===background)continue;
    const colour=g[y][x],todo=[[x,y]],pts=[];seen.add(key);
    while(todo.length){
      const [a,b]=todo.pop();pts.push([a,b]);
      for(const [c,d] of [[a-1,b],[a+1,b],[a,b-1],[a,b+1]]){
        const k=c+','+d;if(c>=0&&c<w&&d>=0&&d<h&&!seen.has(k)&&g[d][c]===colour){seen.add(k);todo.push([c,d]);}
      }
    }
    const xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]);
    components.push({colour,area:pts.length,bbox:[Math.min(...xs),Math.min(...ys),Math.max(...xs),Math.max(...ys)]});
  }
  const runs=g.map(rle),patterns=[],ids=[],lookup=new Map();
  for(const row of runs){const k=JSON.stringify(row);if(!lookup.has(k)){lookup.set(k,patterns.length);patterns.push(row);}ids.push(lookup.get(k));}
  const enc=[{encoding:'rle_rows',rows:runs},{encoding:'rle_row_dictionary',patterns,row_pattern_ids:ids}];
  if(g.every(row=>row.every(v=>v>=0&&v<16)))enc.push({encoding:'hex_rows',rows:g.map(row=>row.map(v=>v.toString(16)).join(''))});
  enc.sort((a,b)=>JSON.stringify(a).length-JSON.stringify(b).length);
  return [{...enc[0],width:w,height:h,palette_counts:Object.fromEntries(counts),components:components.slice(0,24),components_truncated:components.length>24,animation_policy:'final_visible_frame'},g];
}
function diff(before,after){
  const out=[];if(!before?.length||!after?.length)return out;
  for(let y=0;y<Math.min(before.length,after.length);y++)for(let x=0;x<Math.min(before[y].length,after[y].length);x++)if(before[y][x]!==after[y][x])out.push([x,y,before[y][x],after[y][x]]);
  return out;
}
function centre(b){return [(b[0]+b[2])/2,(b[1]+b[3])/2];}
function motionSummary(beforeV,afterV){
  const A=(beforeV.components||[]).map((x,i)=>({...x,_i:i})),B=(afterV.components||[]).map((x,i)=>({...x,_i:i}));
  const used=new Set(),out=[];
  for(const a of A){
    const [ax,ay]=centre(a.bbox);let best=null,bd=Infinity;
    for(const b of B){
      if(used.has(b._i)||b.colour!==a.colour||b.area!==a.area)continue;
      const [bx,by]=centre(b.bbox),d=Math.abs(bx-ax)+Math.abs(by-ay);
      if(d<bd){bd=d;best=b;}
    }
    if(best){
      used.add(best._i);const [bx,by]=centre(best.bbox),dx=bx-ax,dy=by-ay;
      if(dx!==0||dy!==0)out.push({colour:a.colour,area:a.area,from:a.bbox,to:best.bbox,dx,dy});
    }
  }
  return out.slice(0,12);
}
function actionModel(history,legal){
  const out={};
  for(const a of legal){
    const hs=history.filter(x=>x.kind==='transition'&&x.action===a);
    out[a]={trials:hs.length,noops:hs.filter(x=>x.changed_pixels===0).length,last_changed:hs.at(-1)?.changed_pixels??null,last_motion:hs.at(-1)?.motion||[]};
  }
  return out;
}
function spatialSummary(visible,model){
  const sigs=new Map(),vectors={};
  for(const [action,m] of Object.entries(model)){
    const motions=m.last_motion||[];
    if(motions.length){
      const vs=motions.map(x=>[Number(x.dx),Number(x.dy)]);
      const first=vs[0];
      if(vs.every(v=>v[0]===first[0]&&v[1]===first[1]))vectors[action]={dx:first[0],dy:first[1]};
      for(const x of motions)sigs.set(String(x.colour)+':'+String(x.area),true);
    }
  }
  const comps=(visible.components||[]).map((x,i)=>({...x,index:i,center:centre(x.bbox)}));
  const movers=comps.filter(x=>sigs.has(String(x.colour)+':'+String(x.area))).slice(0,8);
  const staticComps=comps.filter(x=>!sigs.has(String(x.colour)+':'+String(x.area)));
  const anchor=movers[0]?.center||[visible.width/2,visible.height/2];
  const dist=x=>Math.abs(x.center[0]-anchor[0])+Math.abs(x.center[1]-anchor[1]);
  const nearby=[...staticComps].sort((a,b)=>dist(a)-dist(b)||a.area-b.area).slice(0,12).map(x=>({colour:x.colour,area:x.area,bbox:x.bbox,center:x.center,distance:dist(x)}));
  const small=[...staticComps].filter(x=>x.area<=Math.max(32,(movers[0]?.area||8)*4)).sort((a,b)=>dist(a)-dist(b)||a.area-b.area).slice(0,8).map(x=>({colour:x.colour,area:x.area,bbox:x.bbox,center:x.center,distance:dist(x)}));
  return {action_vectors:vectors,moving_components:movers.map(x=>({colour:x.colour,area:x.area,bbox:x.bbox,center:x.center})),nearby_static_components:nearby,small_static_candidates:small,truth_boundary:'geometric_candidates_not_known_goals'};
}
function noopGuard(history,legal){
  if(history.length<2)return null;
  const trans=history.filter(x=>x.kind==='transition');
  if(trans.length<2)return null;
  const a=trans.at(-1)?.action;
  const tail=trans.slice(-3);
  if(!a||tail.length<2||!tail.every(x=>x.action===a&&x.changed_pixels===0))return null;
  const counts=Object.fromEntries(legal.map(x=>[x,trans.filter(t=>t.action===x).length]));
  const cand=legal.filter(x=>x!==a).sort((x,y)=>(counts[x]-counts[y])||x.localeCompare(y));
  return cand.length?{blocked:a,force:cand[0],reason:'repeated_visible_noop'}:null;
}
function seq(x){if(!Array.isArray(x)||x.length>4096)throw new Error('bounded sequence');for(const v of x)if(!['string','number'].includes(typeof v))throw new Error('token type');return x;}
function relation(rows){const m=new Map();if(!Array.isArray(rows)||rows.length>256)throw new Error('relation bound');for(const r of rows){const k=JSON.stringify(seq(r.input)),v=seq(r.output);if(!JSON.parse(k).length)throw new Error('empty key');if(m.has(k)&&JSON.stringify(m.get(k))!==JSON.stringify(v))throw new Error('conflict');m.set(k,v);}return m;}
function translate(rows,stream){
  const rel=relation(rows),s=seq(stream),keys=[...rel.keys()].map(k=>JSON.parse(k)),paths=new Map([[0,[[]]]]);
  for(let i=0;i<s.length;i++){if(!paths.has(i))continue;for(const k of keys){const j=i+k.length;if(JSON.stringify(s.slice(i,j))===JSON.stringify(k)){const dst=paths.get(j)||[];for(const p of paths.get(i)){const c=p.concat([k]);if(dst.length<2&&!dst.some(x=>JSON.stringify(x)===JSON.stringify(c)))dst.push(c);}paths.set(j,dst);}}}
  const hits=paths.get(s.length)||[];if(hits.length!==1)return {status:'ABSTAIN',reason:hits.length?'ambiguous':'no_parse'};
  return {status:'UNIQUE',segments:hits[0],output:hits[0].flatMap(k=>rel.get(JSON.stringify(k)))};
}
function executeTool(name,args){
  if(name==='cyclic_plan'){let {current:a,target:b,period,forward,backward=null}=args;if(!Number.isInteger(a)||!Number.isInteger(b)||!Number.isInteger(period)||period<1||period>4096)throw new Error('cyclic params');let d=(b-a)%period;if(d<0)d+=period;if(backward!==null&&Math.abs(d-period)<d)d-=period;return {status:'EXACT_GIVEN_ASSUMPTIONS',delta:d,actions:Array(Math.abs(d)).fill(d>=0?forward:backward)};}
  if(name==='shortest_path'){const {edges,start,goal}=args;if(!Array.isArray(edges)||edges.length>4096)throw new Error('edges');const graph=new Map();for(const e of edges){const [u,a,v]=e;if(!graph.has(u))graph.set(u,[]);graph.get(u).push([a,v]);}const q=[[start,[]]],seen=new Set([start]);while(q.length){const [s,p]=q.shift();if(s===goal)return {status:'EXACT_GIVEN_GRAPH',actions:p};for(const [a,n] of (graph.get(s)||[]))if(!seen.has(n)){seen.add(n);q.push([n,p.concat([a])]);}}return {status:'ABSTAIN',reason:'unreachable_in_supplied_graph'};}
  if(name==='discriminating_probe'){const pr=args.predictions;if(!pr||typeof pr!=='object')throw new Error('predictions');let best=null,costs={};for(const [a,vals] of Object.entries(pr)){const c={};for(const v of seq(vals)){const k=JSON.stringify(v);c[k]=(c[k]||0)+1;}costs[a]=Object.values(c).reduce((s,n)=>s+n*n,0)/vals.length;if(best===null||costs[a]<costs[best]||(costs[a]===costs[best]&&a<best))best=a;}return {status:'MODEL_CONDITIONAL',action:best,expected_remaining:costs};}
  if(name==='relate')return translate(args.relation,args.stream);
  if(name==='compose_relations'){const f=translate(args.first,args.stream);return f.status==='UNIQUE'?translate(args.second,f.output):f;}
  if(name==='inverse_relation'){const rel=relation(args.relation),target=JSON.stringify(seq(args.target)),hits=[];for(const [k,v] of rel)if(JSON.stringify(v)===target)hits.push(JSON.parse(k));return hits.length===1?{status:'UNIQUE',output:hits[0]}:{status:'ABSTAIN',reason:'non_unique_inverse'};}
  if(name==='canonical_glyph'){const cells=args.cells;if(!Array.isArray(cells)||cells.length>4096)throw new Error('glyph');if(!cells.length)return {status:'EXACT',cells:[]};const vars=[];for(let k=0;k<8;k++){const pts=[];for(const cell of cells){let r=Number(cell[0]),c=Number(cell[1]);for(let j=0;j<k%4;j++){const z=r;r=c;c=-z;}if(k>=4)c=-c;pts.push([r,c]);}const r0=Math.min(...pts.map(p=>p[0])),c0=Math.min(...pts.map(p=>p[1]));const norm=[...new Set(pts.map(p=>JSON.stringify([p[0]-r0,p[1]-c0])))].map(JSON.parse).sort();vars.push(norm);}vars.sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b)));return {status:'EXACT',cells:vars[0]};}
  throw new Error('unknown tool '+name);
}
const TOOL_NAMES=new Set(['canonical_glyph','relate','compose_relations','inverse_relation','cyclic_plan','shortest_path','discriminating_probe']);

function firstJSONObject(text){
  const start=text.indexOf('{');if(start<0)throw new Error('JSON_OBJECT_REQUIRED');
  let depth=0,inString=false,esc=false;
  for(let i=start;i<text.length;i++){
    const ch=text[i];
    if(inString){
      if(esc){esc=false;continue;}
      if(ch==='\\'){esc=true;continue;}
      if(ch==='"')inString=false;
      continue;
    }
    if(ch==='"'){inString=true;continue;}
    if(ch==='{')depth++;
    else if(ch==='}'){depth--;if(depth===0)return text.slice(start,i+1);}
  }
  throw new Error('JSON_OBJECT_UNCLOSED');
}
function parseDecision(raw,turn,legal,types,w,h){
  let text=String(raw||'').trim();if(text.startsWith('~~~')||text.startsWith('```')){const ls=text.split('\n');text=ls.slice(1,-1).join('\n').trim();}
  let o;try{o=JSON.parse(text)}catch{o=JSON.parse(firstJSONObject(text));}
  if(o.turn===undefined)o.turn=turn;if(!Number.isInteger(o.turn)||o.turn!==turn)throw new Error('TURN_BINDING');
  let memory=o.memory??'';memory=String(memory).slice(0,1200);
  let kind=o.kind;if(!['act','tool','stop'].includes(kind)){if(o.action)kind='act';else if(o.name&&o.args)kind='tool';else if(o.stop===true)kind='stop';else throw new Error('DECISION_KIND');}
  if(kind==='tool'){if(!TOOL_NAMES.has(o.name)||!o.args||typeof o.args!=='object')throw new Error('TOOL_SCHEMA');return {turn,kind:'tool',name:o.name,args:o.args,memory};}
  if(kind==='stop')return {turn,kind:'stop',memory};
  let action=String(o.action||'').toUpperCase();if(!legal.includes(action))throw new Error('ACTION_BOUND');
  let data=o.data&&typeof o.data==='object'?o.data:{};if(types[action]){if(o.x!==undefined&&data.x===undefined)data.x=o.x;if(o.y!==undefined&&data.y===undefined)data.y=o.y;if(!Number.isInteger(data.x)||!Number.isInteger(data.y)||data.x<0||data.x>=w||data.y<0||data.y>=h)throw new Error('COORDINATE');}else data={};
  let repeat=Number(o.repeat||1);if(!Number.isInteger(repeat))repeat=1;repeat=Math.max(1,Math.min(8,repeat));
  return {turn,kind:'act',action,data,repeat,memory};
}
function fallback(packet){
  const names=Object.keys(packet.available_actions).sort(),t=packet.turn||0;if(!names.length)return {turn:t,kind:'stop',memory:''};
  const simple=names.filter(n=>!packet.available_actions[n]),complex=names.filter(n=>packet.available_actions[n]),recent=packet.recent_events||[];
  const trans=recent.filter(x=>x.kind==='transition');
  const blocked=trans.length>=2&&trans.slice(-2).every(x=>x.action===trans.at(-1).action&&x.changed_pixels===0)?trans.at(-1).action:null;
  const simplePool=simple.filter(x=>x!==blocked);
  if(simplePool.length&&(t<simple.length*2||!complex.length)){
    const counts=Object.fromEntries(simplePool.map(a=>[a,trans.filter(x=>x.action===a).length]));
    const a=[...simplePool].sort((a,b)=>(counts[a]-counts[b])||a.localeCompare(b))[0];
    return {turn:t,kind:'act',action:a,data:{},repeat:1,memory:'',_fallback:true};
  }
  const o=packet.observation||{},W=Math.max(1,o.width||1),H=Math.max(1,o.height||1),pts=[];
  for(const c of (o.components||[]).slice(0,16)){const b=c.bbox;if(Array.isArray(b)&&b.length===4){const [x0,y0,x1,y1]=b;pts.push([Math.floor((x0+x1)/2),Math.floor((y0+y1)/2)],[x0,y0],[x1,y1]);}}
  pts.push([Math.floor(W/2),Math.floor(H/2)],[0,0],[W-1,H-1],[W-1,0],[0,H-1]);const [x,y]=pts[t%pts.length];
  const pool=(complex.length?complex:simple).filter(a=>a!==blocked);const a=(pool.length?pool:(complex.length?complex:simple))[t%Math.max(1,(pool.length?pool:(complex.length?complex:simple)).length)];
  return {turn:t,kind:'act',action:a,data:packet.available_actions[a]?{x,y}:{},repeat:1,memory:'',_fallback:true};
}

const SYSTEM=`You are the DEUS V6 ARC-AGI-3 interactive decision cortex using the verified R335/V4 generic observation/tool protocol plus generic transition-motion summaries. Control one unfamiliar interactive grid puzzle using only allowed observations and feedback; never replay a memorized route or hidden answer. Observations are losslessly compacted as rle_rows, rle_row_dictionary, or hex_rows; components, motion summaries, and spatial_summary are geometric evidence, not semantic truth. spatial_summary lists observed action vectors, moving components, and nearby static candidates; candidates are not known goals. Learn action semantics from actual transitions. First complete a level, then minimize actions. Keep memory factual and state-specific: observed action->effect rules, current hypotheses, uncertainty, and next discriminating probe. Never copy fallback labels into memory. If an action becomes a visible no-op twice, choose a different legal action. If repeated transitions establish a displacement/cycle, exploit the supported relation. After a level transition preserve only general action semantics and discard level-specific coordinates. A visually identical frame is not proof of identical hidden state.
Return exactly one JSON object. Fields: turn integer; kind act|tool|stop; memory short factual string. For act: action legal string, data object (empty for simple; x/y for complex), repeat 1..8 only when transition evidence supports it. For tool: name and args. Tool signatures: canonical_glyph({cells:[[row,col],...]}); relate({relation:[{input:[tokens],output:[tokens]}],stream:[tokens]}); compose_relations({first:[...],second:[...],stream:[tokens]}); inverse_relation({relation:[...],target:[tokens]}); cyclic_plan({current:int,target:int,period:int,forward:string,backward?:string}); shortest_path({edges:[[state,action,next_state],...],start:state,goal:state}); discriminating_probe({predictions:{ACTION:[predicted_outcome_per_hypothesis,...]}}). Tools are conditional calculators, not proof their premises are true. Do not fabricate observations. No markdown.`;

async function main(){
  if(!ARC_KEY||!SA.private_key)throw new Error('missing credentials');
  const games=await arc('/api/games'),game=games.find(x=>String(x.game_id||'').startsWith(GAME_PREFIX));if(!game)throw new Error('game missing');
  const opened=await arc('/api/scorecard/open',{method:'POST',body:JSON.stringify({tags:['deus-v6','r7-r335-motion','brain3-qwen-strong','owner-bound','no-route-replay'],source_url:SOURCE_URL,opaque:{system:'DEUS V6 R7 R335+motion-derived generic agent',r335_source_sha256:R335_SOURCE_SHA,cognition:'Brain3 Qwen3-4B strong',semi_private:false,route_replay:false}})});
  const card=opened.card_id;let fr=null,memory='',feedback=null,calls=0,actions=0,tools=0,rejections=0,fallbacks=0;const history=[],receipts=[];
  try{
    fr=await arc('/api/cmd/RESET',{method:'POST',body:JSON.stringify({card_id:card,game_id:game.game_id})});
    while(calls<MAX_CALLS&&actions<MAX_ACTIONS&&!['WIN','GAME_OVER'].includes(String(fr.state))){
      const [visible,g]=describe(fr.frame),legalNums=fr.available_actions||[],legal=legalNums.map(n=>'ACTION'+Number(n)),types=Object.fromEntries(legalNums.map(n=>['ACTION'+Number(n),Number(n)>=6]));
      const guard=noopGuard(history,legal),amodel=actionModel(history,legal);
      const packet={turn:calls,observation:visible,progress:{state:String(fr.state),levels_completed:Number(fr.levels_completed||0)},available_actions:types,memory,recent_events:history.slice(-5),action_model:amodel,spatial_summary:spatialSummary(visible,amodel),anti_loop:guard,feedback,remaining_actions:MAX_ACTIONS-actions,remaining_calls:MAX_CALLS-calls};
      const prompt=SYSTEM+'\nPACKET='+JSON.stringify(packet);
      const inf=await infer(prompt,calls);receipts.push(inf);const turn=calls;calls++;
      let msg,wasFallback=false;try{msg=parseDecision(inf.text,turn,legal,types,visible.width,visible.height);feedback=null;}catch(e){rejections++;feedback={rejected:String(e.message).slice(0,240)};msg=fallback(packet);fallbacks++;wasFallback=true;}
      if(msg.kind==='act'&&guard&&msg.action===guard.blocked){msg={...msg,action:guard.force,repeat:1,data:{},_anti_loop:true};}
      if(!wasFallback&&msg.memory)memory=msg.memory;
      if(msg.kind==='stop')break;
      if(msg.kind==='tool'){if(tools>=12){feedback={rejected:'TOOL_BUDGET'};continue;}let result;try{result=executeTool(msg.name,msg.args);tools++;}catch(e){result={status:'ERROR',error:String(e.message).slice(0,240)};}history.push({kind:'tool',name:msg.name,result});continue;}
      for(let k=0;k<Math.min(msg.repeat,MAX_ACTIONS-actions);k++){
        const [beforeV,before]=describe(fr.frame),bl=Number(fr.levels_completed||0);
        const payload={game_id:game.game_id,guid:fr.guid,reasoning:JSON.stringify({deus_r7_turn:turn,brain3_receipt:inf.receipt_id||null})};if(types[msg.action])payload.data=msg.data;
        fr=await arc('/api/cmd/'+msg.action,{method:'POST',body:JSON.stringify(payload)});actions++;
        const [afterV,after]=describe(fr.frame),changes=diff(before,after),motion=motionSummary(beforeV,afterV);
        history.push({kind:'transition',action:msg.action,data:msg.data,changed_pixels:changes.length,motion,anti_loop_override:Boolean(msg._anti_loop),changes:changes.slice(0,24),changes_truncated:changes.length>24,levels_completed:Number(fr.levels_completed||0),state:String(fr.state),frame_sha256:sha(afterV)});
        if(['WIN','GAME_OVER'].includes(String(fr.state))||Number(fr.levels_completed||0)!==bl)break;
      }
    }
    const cl=await arc('/api/scorecard/close',{method:'POST',body:JSON.stringify({card_id:card})});
    return {schema:'deus-arc3-v6-r7-r335-motion-online/1',state:'VERIFIED_DONE',card_id:card,scorecard_url:ARC_BASE+'/scorecards/'+card,game_id:game.game_id,score:cl.score,levels_completed:cl.total_levels_completed,total_levels:cl.total_levels,total_actions:cl.total_actions,local_actions:actions,brain3_calls:calls,tool_calls:tools,protocol_rejections:rejections,fallbacks,final_state:fr?.state||null,route_replay:false,semi_private:false,model_sha256:MODEL_SHA,r335_source_sha256:R335_SOURCE_SHA,receipts:receipts.map(x=>x.receipt_id).filter(Boolean),history_tail:history.slice(-12)};
  }catch(e){
    let cl=null;try{cl=await arc('/api/scorecard/close',{method:'POST',body:JSON.stringify({card_id:card})})}catch{}
    return {schema:'deus-arc3-v6-r7-r335-motion-online/1',state:'FAILED',card_id:card,scorecard_url:ARC_BASE+'/scorecards/'+card,error_type:e.constructor?.name||'Error',error:String(e.message||e).slice(0,1000),brain3_calls:calls,local_actions:actions,tool_calls:tools,protocol_rejections:rejections,fallbacks,closed_score:cl?.score??null,closed_actions:cl?.total_actions??null,history_tail:history.slice(-8)};
  }
}
main().then(r=>{finalResult=r;console.log('DEUS_ARC3_R7_RESULT='+JSON.stringify(r));}).catch(e=>{finalResult={state:'FAILED',error:String(e)};console.error('DEUS_ARC3_R7_FATAL='+JSON.stringify(finalResult));});
