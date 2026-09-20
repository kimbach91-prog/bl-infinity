const base = process.env.BASE_URL;
if (!base) throw new Error("BASE_URL required");

const controllerTimeout = (ms) => {
  const c = new AbortController();
  const t = setTimeout(() => c.abort(), ms);
  return { signal: c.signal, stop: () => clearTimeout(t) };
};

async function getJson(url, opts={}, timeoutMs=15000) {
  const t = controllerTimeout(timeoutMs);
  const started = Date.now();
  try {
    const res = await fetch(url, { ...opts, signal: t.signal });
    const text = await res.text();
    let json = null;
    try { json = JSON.parse(text); } catch {}
    return { res, json, text, latency_ms: Date.now()-started };
  } finally { t.stop(); }
}

const health = await getJson(base + "/healthz");
if (!health.res.ok || health.json?.ok !== true || health.json?.horde_s0_executor_bound !== true) {
  throw new Error("gateway health/binding check failed");
}

const cases = [
  { id:"A1", expected:"DEUS-S0-A1", input:"Return exactly this ASCII token and nothing else: DEUS-S0-A1" },
  { id:"B2", expected:"DEUS-S0-B2", input:"Output only the token DEUS-S0-B2. No quotes, no punctuation, no explanation." },
  { id:"C3", expected:"DEUS-S0-C3", input:"Echo this token exactly and output nothing else: DEUS-S0-C3" }
];

const results=[];
for (const tc of cases) {
  const body={
    model:"deus-horde-s0",
    input:tc.input,
    max_tokens:16,
    metadata:{data_class:"S0",public_content_confirmed:true,probe_id:tc.id}
  };
  let rec;
  try {
    const r=await getJson(base + "/v1/responses",{
      method:"POST",
      headers:{"content-type":"application/json"},
      body:JSON.stringify(body)
    },120000);
    const output = r.json?.output?.[0]?.content?.[0]?.text ?? "";
    const trimmed = String(output).trim();
    rec={
      id:tc.id,
      expected:tc.expected,
      http_status:r.res.status,
      latency_ms:r.latency_ms,
      route:r.res.headers.get("x-deus-route"),
      data_class:r.res.headers.get("x-deus-data-class"),
      commercial_default:r.res.headers.get("x-deus-commercial-default"),
      response_id:r.json?.id ?? null,
      model:r.json?.model ?? null,
      output_text:output,
      exact_trimmed:trimmed===tc.expected,
      valid_shape:Array.isArray(r.json?.output)
    };
  } catch (e) {
    rec={
      id:tc.id, expected:tc.expected, http_status:0, latency_ms:null,
      route:null,data_class:null,commercial_default:null,response_id:null,model:null,
      output_text:null,exact_trimmed:false,valid_shape:false,error:String(e?.message||e)
    };
  }
  results.push(rec);
  console.log("DEUS_AIHORDE_MICROTASK_CASE="+JSON.stringify(rec));
}

const http200 = results.filter(x=>x.http_status===200).length;
const routeOk = results.filter(x=>x.route==="ai-horde-s0" && x.data_class==="S0" && x.commercial_default==="false").length;
const exact = results.filter(x=>x.exact_trimmed).length;
const latencies=results.map(x=>x.latency_ms).filter(Number.isFinite);
const receipt={
  schema:"deus-aihorde-s0-microtask-probe/1",
  state:http200===3 && routeOk===3 ? "TRANSPORT_ROUTE_3_OF_3_VERIFIED" : "PARTIAL_OR_FAILED",
  route_id:"AIHORDE-S0-VIA-DEUS-GATE",
  base_url:base,
  source_commit:process.env.GITHUB_SHA || null,
  run_id:process.env.GITHUB_RUN_ID || null,
  probe_count:3,
  http200_count:http200,
  route_header_count:routeOk,
  exact_instruction_count:exact,
  latency_ms:latencies,
  latency_avg_ms:latencies.length?Math.round(latencies.reduce((a,b)=>a+b,0)/latencies.length):null,
  cases:results,
  data_class:"BL-S0",
  protected_core_export:false,
  private_memory_export:false,
  credentials_requested:false,
  canonical_write:false,
  independent_planning:false,
  economic_yield_claim:false,
  authority_scope:"BOUNDED_PUBLIC_MICROTASK_MEASUREMENT_ONLY"
};
console.log("DEUS_AIHORDE_MICROTASK_RECEIPT="+JSON.stringify(receipt));
if (http200!==3 || routeOk!==3) process.exitCode=1;
