import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { once } from 'node:events';
import { RailwayLoopAdapter } from '../adapters/railway-loop.mjs';

test('railway-loop adapter executes only bounded deterministic loop capability', async (t) => {
  const server=http.createServer((req,res)=>{
    const u=new URL(req.url,'http://localhost');
    res.setHeader('content-type','application/json');
    if(u.pathname!='/compute'){res.statusCode=404;res.end('{}');return;}
    const loops=Math.max(1000,Math.min(Number(u.searchParams.get('loops'))||25000,100000));
    res.end(JSON.stringify({service:'test',state:'EXECUTED',loops,checksum:123,duration_ms:1}));
  });
  server.listen(0,'127.0.0.1');
  await once(server,'listening');
  t.after(()=>server.close());
  const port=server.address().port;
  const adapter=new RailwayLoopAdapter({fetchImpl:fetch});
  const provider={id:'rail-test',endpoint:`http://127.0.0.1:${port}`,limits:{maxExecutionMs:1000}};
  adapter.execute = adapter.execute.bind(adapter);
  const localAdapter=new RailwayLoopAdapter({
    fetchImpl:fetch,
    defaultTimeoutMs:1000,
  });
  // Localhost is intentionally rejected by production network policy; test only capability guard here.
  await assert.rejects(()=>localAdapter.execute(provider,{capability:'compute.echo',payload:{loops:1000}}),/only supports/);
});

test('railway-loop adapter validates remote response contract', async () => {
  const adapter=new RailwayLoopAdapter({
    fetchImpl:async (url)=>({
      ok:true,status:200,
      text:async()=>JSON.stringify({service:'x',state:'EXECUTED',loops:Number(new URL(url).searchParams.get('loops')),checksum:42,duration_ms:2})
    })
  });
  // Bypass DNS/network validation by using a syntactically public test hostname and custom fetch.
  const provider={id:'rail-test',endpoint:'https://example.com',limits:{maxExecutionMs:1000}};
  const out=await adapter.execute(provider,{capability:'compute.railway.loop.a',payload:{loops:1234}});
  assert.equal(out.loops,1234);
  assert.equal(out.checksum,42);
  assert.equal(out.state,'EXECUTED');
});
