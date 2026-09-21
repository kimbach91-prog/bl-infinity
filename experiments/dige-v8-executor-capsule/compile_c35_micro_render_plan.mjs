import fs from 'node:fs';
import crypto from 'node:crypto';

const width=Number(process.env.DIGE_FRAME_WIDTH||900);
const height=Number(process.env.DIGE_FRAME_HEIGHT||900);
const totalSamples=Number(process.env.DIGE_TOTAL_SAMPLES||384);
const passCount=Number(process.env.DIGE_LOGICAL_PASS_COUNT||1);
const baseSeed=Number(process.env.DIGE_BASE_SEED||20263030);
const seedStride=Number(process.env.DIGE_SEED_STRIDE||104729);
const simulVcpu=Number(process.env.DEUS_SIMUL_VCPU_LB||28);
const vcpuPerShard=Math.max(1,Number(process.env.DIGE_RENDER_VCPU_PER_SHARD||4));
const verifiedGpuCount=Number(process.env.DEUS_GPU_COUNT||0);
const verifiedVramGiB=Number(process.env.DEUS_VRAM_GIB||0);
const requestedMax=Math.max(1,Number(process.env.DIGE_MAX_PHYSICAL_SHARDS||64));
const logicalNamespace=BigInt(process.env.DEUS_LOGICAL_NAMESPACE||'1000000000000');

for(const [name,value] of Object.entries({width,height,totalSamples,passCount,baseSeed,seedStride,simulVcpu,vcpuPerShard,requestedMax})){
  if(!Number.isFinite(value)||value<=0) throw new Error(`${name} must be positive`);
}

const logicalMicrocells=BigInt(width)*BigInt(height)*BigInt(totalSamples)*BigInt(passCount);
if(logicalMicrocells>logicalNamespace) throw new Error(`logical microcells ${logicalMicrocells} exceed namespace ${logicalNamespace}`);

const cpuShardCapacity=Math.max(1,Math.floor(simulVcpu/vcpuPerShard));
const gpuShardCapacity=(verifiedGpuCount>0&&verifiedVramGiB>0)?Math.max(1,Math.floor(verifiedGpuCount)):0;
const executorCapacity=Math.max(1,cpuShardCapacity+gpuShardCapacity);
const physicalShards=Math.max(1,Math.min(requestedMax,totalSamples,executorCapacity));

const base=Math.floor(totalSamples/physicalShards);
const rem=totalSamples%physicalShards;
const matrix=[];
let assigned=0;
for(let i=0;i<physicalShards;i++){
  const samples=base+(i<rem?1:0);
  const seed=baseSeed+i*seedStride;
  const execution=(i<gpuShardCapacity)?'GPU':'CPU';
  matrix.push({
    id:`s${String(i+1).padStart(2,'0')}`,
    index:i,
    samples,
    seed,
    execution,
    logicalMicrocells:(BigInt(width)*BigInt(height)*BigInt(samples)*BigInt(passCount)).toString(),
  });
  assigned+=samples;
}
if(assigned!==totalSamples) throw new Error('sample partition mismatch');

const payload={
  schema:'deus-dige-micro-render-plan/1.0',
  task:'DIGE_C35_MICRO_RENDER_FABRIC',
  logicalNamespace:logicalNamespace.toString(),
  logicalMicrocells:logicalMicrocells.toString(),
  logicalCellDefinition:'PIXEL_X_SAMPLE_X_PASS_STATE',
  width,height,totalSamples,passCount,
  physicalShards,
  cpuShardCapacity,
  gpuShardCapacity,
  verifiedGpuCount,
  verifiedVramGiB,
  provenSimultaneousVcpuLowerBound:simulVcpu,
  vcpuPerShard,
  baseSeed,
  seedStride,
  matrix,
  coalescingFactor:Number(logicalMicrocells)/physicalShards,
  reducer:'SAMPLE_COUNT_WEIGHTED_LINEAR_EXR_ACCUMULATION',
  denoisePolicy:'DENOISE_AFTER_REDUCE_ONLY',
  truthBoundary:'LOGICAL_MICROCELLS_ARE_SCHEDULING_AND_STATE_UNITS__NOT_PHYSICAL_CORES__PHYSICAL_JOB_COUNT_IS_BOUNDED_BY_VERIFIED_EXECUTOR_CAPACITY_AND_OVERHEAD',
};
payload.planDigest=crypto.createHash('sha256').update(JSON.stringify(payload)).digest('hex');
const out=process.env.DIGE_MICRO_PLAN_OUT||'runtime/DIGE_C35_MICRO_RENDER_PLAN.json';
fs.mkdirSync(new URL('.',new URL(`file://${process.cwd()}/${out}`)).pathname,{recursive:true});
fs.writeFileSync(out,JSON.stringify(payload,null,2)+'\n');
console.log(JSON.stringify(payload));
if(process.env.GITHUB_OUTPUT){
  fs.appendFileSync(process.env.GITHUB_OUTPUT,`matrix=${JSON.stringify(matrix)}\nphysical_shards=${physicalShards}\nplan_digest=${payload.planDigest}\nlogical_microcells=${logicalMicrocells}\n`);
}
