import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { validateProviderGrant, providerGrantPayload } from '../runtime/federation/lib/manifest.mjs';

const shard = Number(process.env.SHARD);
if (!Number.isInteger(shard) || shard < 0 || shard > 7) throw new Error('SHARD must be 0..7');

const providersRaw = await readFile(new URL('../runtime/federation/config/providers.example.json', import.meta.url));
const schemaRaw = await readFile(new URL('../runtime/federation/config/provider.schema.json', import.meta.url));
const providers = JSON.parse(providersRaw);
const schema = JSON.parse(schemaRaw);
const now = Date.parse('2026-09-20T00:00:00Z');
const digest = createHash('sha256').update(providersRaw).update(schemaRaw).digest('hex');
const knownClasses = new Set(['public','internal','private','regulated','sealed']);
const envName = /^[A-Z][A-Z0-9_]{2,127}$/;

function assert(ok, msg) { if (!ok) throw new Error(msg); }
function walk(value, path = '$', out = []) {
  if (Array.isArray(value)) value.forEach((v,i)=>walk(v, `${path}[${i}]`, out));
  else if (value && typeof value === 'object') for (const [k,v] of Object.entries(value)) { out.push({ path: `${path}.${k}`, key:k, value:v }); walk(v, `${path}.${k}`, out); }
  return out;
}

const checks = [
  {
    name:'runtime-validator-accepts-public-fixtures',
    run() {
      for (const p of providers) assert(validateProviderGrant(p, now) === true, `validator rejected ${p.id}`);
      return { validated: providers.map(p=>p.id) };
    }
  },
  {
    name:'schema-version-contract-consistent',
    run() {
      const expected = schema?.properties?.manifestVersion?.const;
      assert(expected === 'bl-cf-provider/v1', 'schema manifest version drift');
      for (const p of providers) assert(p.manifestVersion === expected, `version mismatch ${p.id}`);
      return { manifest_version: expected };
    }
  },
  {
    name:'provider-identity-unique-and-bounded',
    run() {
      const ids = providers.map(p=>p.id);
      assert(new Set(ids).size === ids.length, 'duplicate provider id');
      for (const id of ids) assert(/^[a-zA-Z0-9._:-]{2,128}$/.test(id), `invalid id ${id}`);
      return { ids };
    }
  },
  {
    name:'authorization-data-class-gates-valid',
    run() {
      for (const p of providers) {
        const a = p.authorization;
        assert(a?.consentRef && a?.grantor, `missing authority ref ${p.id}`);
        assert(Number.isFinite(Date.parse(a.grantedAt)), `bad grantedAt ${p.id}`);
        assert(!a.expiresAt || Date.parse(a.expiresAt) > now, `expired ${p.id}`);
        assert(Array.isArray(a.allowedDataClasses) && a.allowedDataClasses.length > 0, `empty classes ${p.id}`);
        for (const cls of a.allowedDataClasses) assert(knownClasses.has(cls), `unknown class ${p.id}:${cls}`);
      }
      return { classes: Object.fromEntries(providers.map(p=>[p.id,p.authorization.allowedDataClasses])) };
    }
  },
  {
    name:'cost-and-concurrency-bounds-coherent',
    run() {
      for (const p of providers) {
        const l = p.limits;
        assert(Number.isInteger(l?.maxConcurrency) && l.maxConcurrency >= 1, `bad concurrency ${p.id}`);
        for (const x of [l.maxCostPerTaskUsd, p.authorization.maxTaskCostUsd].filter(x=>x!=null)) assert(Number(x) >= 0, `negative cost ${p.id}`);
        if (l.maxCostPerTaskUsd != null && p.authorization.maxTaskCostUsd != null) {
          assert(l.maxCostPerTaskUsd <= p.authorization.maxTaskCostUsd, `runtime cost cap exceeds grant ${p.id}`);
        }
      }
      return { bounds: providers.map(p=>({id:p.id,maxConcurrency:p.limits.maxConcurrency,maxCostPerTaskUsd:p.limits.maxCostPerTaskUsd??null})) };
    }
  },
  {
    name:'external-example-fails-closed-by-default',
    run() {
      const ext = providers.filter(p=>p.kind !== 'local');
      assert(ext.length > 0, 'no external fixture');
      for (const p of ext) {
        assert(p.status === 'disabled', `external example not disabled ${p.id}`);
        assert(new URL(p.endpoint).hostname.endsWith('.invalid'), `external example endpoint not reserved-invalid ${p.id}`);
        if (p.transport?.auth && p.transport.auth !== 'none') {
          assert(typeof p.transport.secretEnv === 'string' && envName.test(p.transport.secretEnv), `secret ref is not env-name-only ${p.id}`);
        }
      }
      return { external_ids: ext.map(p=>p.id), default_state:'disabled' };
    }
  },
  {
    name:'authority-grant-excludes-mutable-runtime-fields',
    run() {
      for (const p of providers) {
        const enriched = { ...p, status:'enabled', telemetry:{probe:1}, runtime:{revision:99}, signature:{algorithm:'ed25519',keyId:'x',value:'y'} };
        const grant = providerGrantPayload(enriched);
        for (const k of ['status','telemetry','runtime','signature']) assert(!(k in grant), `mutable field leaked into grant: ${p.id}.${k}`);
      }
      return { stripped:['status','telemetry','runtime','signature'] };
    }
  },
  {
    name:'no-embedded-secret-material-in-public-fixture',
    run() {
      const suspiciousValue = /(-----BEGIN .*PRIVATE KEY-----|\bsk-[A-Za-z0-9_-]{16,}|\bgh[pousr]_[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|Bearer\s+[A-Za-z0-9._-]{12,})/;
      for (const p of providers) {
        for (const e of walk(p)) {
          if (typeof e.value === 'string') assert(!suspiciousValue.test(e.value), `secret-like value at ${p.id}:${e.path}`);
          if (/password|private.?key|access.?token|api.?key/i.test(e.key)) assert(false, `secret-bearing key present at ${p.id}:${e.path}`);
          if (/secret/i.test(e.key)) assert(e.key === 'secretEnv' && typeof e.value === 'string' && envName.test(e.value), `secret field must be env ref only at ${p.id}:${e.path}`);
        }
      }
      return { embedded_secret_material:false };
    }
  }
];

const check = checks[shard];
let detail;
let state = 'RESULT_VERIFIED_RUNNER_SCOPE';
try {
  detail = check.run();
} catch (error) {
  state = 'RESULT_FAILED_RUNNER_SCOPE';
  detail = { error: String(error?.message || error) };
}

const receipt = {
  schema:'deus-provider-manifest-integrity-audit-receipt/1',
  route_id:'PUBLIC-GITHUB-ACTIONS-PROVIDER-MANIFEST-AUDIT',
  state,
  shard,
  shard_count:8,
  check:check.name,
  source_commit:process.env.GITHUB_SHA || null,
  run_id:process.env.GITHUB_RUN_ID || null,
  runner_os:process.env.RUNNER_OS || null,
  runner_arch:process.env.RUNNER_ARCH || null,
  provider_count:providers.length,
  input_digest:digest,
  detail,
  data_class:'BL-S0',
  protected_core_export:false,
  private_memory_export:false,
  credentials_requested:false,
  canonical_write:false,
  independent_planning:false,
  economic_yield_claim:false,
  authority_scope:'MECHANICAL_AUDIT_ONLY'
};
console.log('DEUS_PROVIDER_MANIFEST_AUDIT_RECEIPT=' + JSON.stringify(receipt));
if (state !== 'RESULT_VERIFIED_RUNNER_SCOPE') process.exitCode = 1;
