import http from 'node:http';
import { createHash, timingSafeEqual } from 'node:crypto';

const port = Number(process.env.PORT || 8080);
const host = process.env.HOST || '0.0.0.0';
const token = process.env.DEUS_WORKSTATION_001_TOKEN || '';
const maxBody = 1_048_576;
let latest = null;

if (token.length < 24) throw new Error('DEUS_WORKSTATION_001_TOKEN missing or too short');

const server = http.createServer(async (req,res) => {
  setHeaders(res);
  try {
    if (req.method === 'GET' && req.url === '/health') {
      return send(res,200,{ok:true,service:'deus-workstation-receipt',version:'1.0.0',receiptApi:'deus-workstation-benchmark/1',hasLatest:Boolean(latest)});
    }
    if (req.method === 'POST' && req.url === '/report') {
      if (!authorized(req)) return send(res,401,{error:'unauthorized'});
      const body = await readJson(req);
      validate(body);
      latest = structuredClone(body);
      const b=body.benchmark||{}, r=body.resources||{}, s=body.supercell||{};
      const summary={
        event:'DEUS_WORKSTATION_BENCHMARK_RECEIPT',
        workstationId:body.workstationId,
        receiptDigest:body.receiptDigest,
        nodeVersion:body.nodeVersion,
        createdAt:body.createdAt,
        cpuLogical:r.cpu?.logical_processors ?? null,
        ramBytes:r.memory?.total_bytes ?? null,
        gpuComputeCredit:r.gpu?.gpu_compute_credit ?? null,
        hashSingleMiBs:b.hash_single?.throughput_mib_s ?? null,
        hashParallelMiBs:b.hash_parallel?.throughput_mib_s ?? null,
        memoryGiBs:b.memory_copy?.throughput_gib_s ?? null,
        diskWriteMiBs:b.disk_sequential?.write_mib_s ?? null,
        diskReadMiBs:b.disk_sequential?.read_mib_s ?? null,
        runtimeLatencyMeanS:b.deus_runtime_latency?.mean_seconds ?? null,
        ordinal1TExact:b.ordinal_1t?.exact ?? null,
        ordinal1TSeconds:b.ordinal_1t?.seconds ?? null,
        periodic1TAvgSeconds:b.periodic_1t?.avg_program_seconds ?? null,
        periodic1TEffectiveLaneUpdatesPerS:b.periodic_1t?.effective_logical_lane_updates_per_second ?? null,
        localWaveWidth:s.physical_binding?.recommended_local_wave_width ?? null,
      };
      console.log(JSON.stringify(summary));
      return send(res,201,{accepted:true,workstationId:body.workstationId,receiptDigest:body.receiptDigest,summary});
    }
    if (req.method === 'GET' && req.url === '/latest') {
      if (!authorized(req)) return send(res,401,{error:'unauthorized'});
      return send(res,200,{report:latest});
    }
    return send(res,404,{error:'not_found'});
  } catch (e) {
    return send(res,e.code==='BODY_TOO_LARGE'?413:400,{error:e.message});
  }
});

server.listen(port,host,()=>console.log(JSON.stringify({event:'DEUS_WORKSTATION_RECEIPT_API_START',host,port,receiptApi:'deus-workstation-benchmark/1'})));

function authorized(req){
  const a=req.headers.authorization||'';
  if(!a.startsWith('Bearer ')) return false;
  const got=Buffer.from(a.slice(7)), exp=Buffer.from(token);
  return got.length===exp.length && timingSafeEqual(got,exp);
}
async function readJson(req){
  let n=0; const chunks=[];
  for await(const c of req){n+=c.length;if(n>maxBody){const e=new Error('body_too_large');e.code='BODY_TOO_LARGE';throw e;}chunks.push(c);}
  return JSON.parse(Buffer.concat(chunks).toString('utf8')||'{}');
}
function validate(x){
  if(!x||typeof x!=='object'||Array.isArray(x)) throw new Error('report_must_be_object');
  rejectSensitive(x);
  if(x.schema!=='deus-workstation-benchmark/1') throw new Error('unsupported_schema');
  if(x.workstationId!=='workstation-win-001') throw new Error('unexpected_workstation');
  if(typeof x.receiptDigest!=='string'||!/^[a-f0-9]{64}$/.test(x.receiptDigest)) throw new Error('invalid_receipt_digest');
}
function rejectSensitive(x,path=''){
  if(x==null) return;
  if(Array.isArray(x)){x.forEach((v,i)=>rejectSensitive(v,`${path}[${i}]`));return;}
  if(typeof x!=='object') return;
  for(const [k,v] of Object.entries(x)){
    if(/(token|secret|password|api[_-]?key|credential|private[_-]?key)/i.test(k)) throw new Error('sensitive_field_rejected:'+ (path?path+'.':'') + k);
    rejectSensitive(v,path?path+'.'+k:k);
  }
}
function setHeaders(res){res.setHeader('content-type','application/json; charset=utf-8');res.setHeader('cache-control','no-store');res.setHeader('x-content-type-options','nosniff');}
function send(res,status,body){res.statusCode=status;res.end(JSON.stringify(body));}
