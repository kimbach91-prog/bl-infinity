/** Final project-CI reducer: independently admitted shard receipts, one leased join.
 * Artifact/source hashes must be verified by the workflow before this program.
 */
import { readFileSync,writeFileSync,mkdirSync } from 'node:fs';
import { resolve,join } from 'node:path';
import assert from 'node:assert/strict';
import { sha256,sha256Json } from '../lib/canonical.mjs';
import { AtomStore,InstructionFabric,PinnedWorkerDriver } from '../lib/instruction-fabric.mjs';
import { reduceAtlas } from '../worker/instruction-operators.mjs';
const args=process.argv.slice(2),out=resolve(args[2]??'.deus/cross-runner');mkdirSync(out,{recursive:true});
const inputs=args.slice(0,2).map(p=>JSON.parse(readFileSync(p)));
assert.equal(inputs.length,2);
for(const x of inputs){assert.equal(x.verdict,'PASS_FOR_SCOPED_INTEGRATION');assert.equal(x.source.kind,'REAL_PUBLIC_ATLAS_SNAPSHOT');assert.equal(x.finalResourceState.active,0);assert.equal(x.classifier.fromAtlasExecutionAdmitted,0);assert.equal(sha256Json(x.expected),x.resultDigest);}
assert.notEqual(inputs[0].source.inputSha256,inputs[1].source.inputSha256);
assert.equal(inputs[0].code.controllerSha256,inputs[1].code.controllerSha256);
assert.equal(inputs[0].code.operatorModuleSha256,inputs[1].code.operatorModuleSha256);
const input={value:null,sourceDigest:sha256Json(inputs.map(x=>x.source.inputSha256)),upstream:{shard0:inputs[0].expected,shard1:inputs[1].expected}};
const expectedDigest='15d6384bab929662ff8b0770081e2e2ee5e4d093e0048026fc3d618ef4934e94';
assert.equal(sha256Json(reduceAtlas(input)),expectedDigest);
const url=new URL('../worker/instruction-operators.mjs',import.meta.url).href,hash=sha256(readFileSync(new URL(url)));
const canaryInput={...input,upstream:{sample:inputs[0].expected}};
const expectedCanary=reduceAtlas(canaryInput);
const store=new AtomStore(join(out,'join.sqlite'));
const f=new InstructionFabric({store,operators:[{id:'join',programDigest:hash,verificationDigest:sha256Json({expectedDigest,expectedCanary}),environmentDigest:sha256Json(process.version),canary:{input:canaryInput,expected:expectedCanary},verify:(value,p)=>sha256Json(value)===(Object.keys(p.upstream).length===1?sha256Json(expectedCanary):expectedDigest)}],
 bindings:[{routeId:'ci-final-reducer',poolId:'ci-final-reducer-allocation',slots:1,maxLeaseMs:10000,operatorIds:['join'],authority:{consentRef:'CURRENT_PROJECT_CI_INVOCATION',tenantId:'deus',allowedDataClasses:['public'],expiresAt:new Date(Date.now()+60000).toISOString(),zeroSpend:true},driver:new PinnedWorkerDriver({moduleUrl:url,moduleDigest:hash,exportName:'reduceAtlas'})}]});
const result=await f.invoke('ci-final-reducer','join',input);assert.equal(result.value.count,124397);assert.equal(sha256Json(result.value),expectedDigest);assert.equal(store.snapshot().active,0);
const receipt={schema:'deus-cross-runner-instruction-join/1',verdict:'PASS_TWO_CI_SHARDS_AND_LEASED_FINAL_REDUCER',workflowRunId:process.env.GITHUB_RUN_ID??null,codeCommit:process.env.GITHUB_SHA??null,sourceArtifactId:10815473100,sourceArtifactSha256:'99468a54ea2f6ff82d8b7786d23c0a90696795267a78b4875a75c480a66766ce',shards:inputs.map(x=>({inputHash:x.source.inputSha256,rows:x.source.rows,resultDigest:x.resultDigest,startedAt:x.startedAt,finishedAt:x.finishedAt})),result:result.value,executionReceipt:result.receipt,resourceState:store.snapshot(),completedAt:new Date().toISOString(),truthBoundary:'GITHUB_JOB_ALLOCATIONS_AND_ARTIFACT_TRANSPORT_ONLY; NOT_CROSS_PROVIDER_CONSENSUS_OR_ALWAYS_ON_GLOBAL_DEPLOYMENT'};
writeFileSync(join(out,'cross-runner-receipt.json'),JSON.stringify(receipt,null,2));store.close();console.log(JSON.stringify({verdict:receipt.verdict,rows:result.value.count,outputDigest:expectedDigest}));
