import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

test('C35 micro plan coalesces 311M logical sample-pixels into 7 bounded physical shards',()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'dige-micro-'));
  const out=path.join(dir,'plan.json');
  const r=spawnSync(process.execPath,['experiments/dige-v8-executor-capsule/compile_c35_micro_render_plan.mjs'],{
    cwd:path.resolve(process.cwd(),'../..'),
    env:{...process.env,DIGE_MICRO_PLAN_OUT:out,DEUS_SIMUL_VCPU_LB:'28',DIGE_RENDER_VCPU_PER_SHARD:'4',DEUS_GPU_COUNT:'0',DEUS_VRAM_GIB:'0',DIGE_TOTAL_SAMPLES:'384'},
    encoding:'utf8'
  });
  assert.equal(r.status,0,r.stderr);
  const p=JSON.parse(fs.readFileSync(out,'utf8'));
  assert.equal(p.logicalMicrocells,'311040000');
  assert.equal(p.physicalShards,7);
  assert.equal(p.matrix.reduce((s,x)=>s+x.samples,0),384);
  assert.equal(new Set(p.matrix.map(x=>x.seed)).size,7);
  assert.ok(p.matrix.every(x=>x.execution==='CPU'));
  assert.match(p.truthBoundary,/NOT_PHYSICAL_CORES/);
});
