import fs from 'node:fs';
import test from 'node:test';
import assert from 'node:assert/strict';
import { compileCapabilityAtlas, selectTaskFitRoutes } from '../lib/internet-functional-fabric.mjs';

const catalog=JSON.parse(fs.readFileSync(new URL('../config/internet-capability-catalog.v2.json',import.meta.url),'utf8'));

test('catalog compiles and contains independent public DNS families',()=>{
  const atlas=compileCapabilityAtlas(catalog.resources);
  assert.ok(atlas.summary.resources>=12);
  const routes=selectTaskFitRoutes(atlas,{capability:'net.dns.resolve',dataClass:'BL-S0',maxRoutes:8,requireIndependent:true});
  assert.ok(routes.length>=3);
  assert.equal(new Set(routes.map(x=>x.independenceGroup)).size,routes.length);
});

test('unbound AI and search resources do not become executable routes',()=>{
  const atlas=compileCapabilityAtlas(catalog.resources);
  for(const cap of ['ai.text.generate','web.search.query-space','compute.gpu']){
    const routes=selectTaskFitRoutes(atlas,{capability:cap,dataClass:'BL-S0',maxRoutes:20});
    assert.equal(routes.length,0);
  }
});

test('public data operators remain addressable without becoming arbitrary compute',()=>{
  const atlas=compileCapabilityAtlas(catalog.resources);
  assert.ok(selectTaskFitRoutes(atlas,{capability:'web.corpus.index.lookup'}).some(x=>x.id==='commoncrawl-index'));
  assert.ok(selectTaskFitRoutes(atlas,{capability:'net.bgp.observe'}).length>=2);
});
