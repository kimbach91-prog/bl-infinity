import test from 'node:test';
import assert from 'node:assert/strict';
import { ControlAuthenticator, bindTaskToPrincipalTenant, parseControlPrincipals, parsePublicReadScopes } from '../lib/control-auth.mjs';

function req(token = null) {
  return { headers: token ? { authorization: `Bearer ${token}` } : {} };
}

test('principal config references env secrets and rejects embedded tokens', () => {
  const env = { TENANT_A_TOKEN: 'tenant-a-token-0123456789abcdef' };
  const principals = parseControlPrincipals([
    { id: 'tenant-a', tenantId: 'tenant-a', tokenEnv: 'TENANT_A_TOKEN', scopes: ['task:submit'] },
  ], env);
  assert.equal(principals[0].id, 'tenant-a');
  assert.match(principals[0].tokenHash, /^[a-f0-9]{64}$/);
  assert.equal(JSON.stringify(principals).includes(env.TENANT_A_TOKEN), false);
  assert.throws(() => parseControlPrincipals([
    { id: 'bad', tenantId: 'x', tokenEnv: 'TENANT_A_TOKEN', token: 'embedded', scopes: ['task:submit'] },
  ], env), /must reference tokenEnv/);
});

test('tenant principal cannot be granted global-only provider/runtime scopes', () => {
  const env = { TENANT_A_TOKEN: 'tenant-a-token-0123456789abcdef' };
  assert.throws(() => parseControlPrincipals([
    { id: 'tenant-a', tenantId: 'tenant-a', tokenEnv: 'TENANT_A_TOKEN', scopes: ['provider:admin'] },
  ], env), /requires tenantId=\*/);
  assert.throws(() => parseControlPrincipals([
    { id: 'tenant-a', tenantId: 'tenant-a', tokenEnv: 'TENANT_A_TOKEN', scopes: ['*'] },
  ], env), /requires tenantId=\*/);
});

test('unknown control scope is rejected instead of becoming a silent typo', () => {
  const env = { OPS_TOKEN: 'operator-root-token-0123456789abcdef' };
  assert.throws(() => parseControlPrincipals([
    { id:'ops', tenantId:'*', tokenEnv:'OPS_TOKEN', scopes:['provider:admn'] },
  ], env), /unknown scope/);
});

test('public read scopes are explicit and limited to read-only surfaces', () => {
  assert.deepEqual([...parsePublicReadScopes('search:read,route:read')].sort(), ['route:read','search:read']);
  assert.equal(parsePublicReadScopes('').size, 0);
  assert.throws(() => parsePublicReadScopes('provider:admin'), /unsupported scope/);
  assert.throws(() => parsePublicReadScopes('task:submit'), /unsupported scope/);
});

test('scoped auth distinguishes unauthenticated, forbidden and allowed', () => {
  const env = {
    TENANT_A_TOKEN: 'tenant-a-token-0123456789abcdef',
    OPS_TOKEN: 'operator-root-token-0123456789abcdef',
  };
  const principals = parseControlPrincipals([
    { id: 'tenant-a', tenantId: 'tenant-a', tokenEnv: 'TENANT_A_TOKEN', scopes: ['task:submit'] },
    { id: 'ops', tenantId: '*', tokenEnv: 'OPS_TOKEN', scopes: ['runtime:read','provider:read'] },
  ], env);
  const auth = new ControlAuthenticator({ principals });
  assert.equal(auth.authorize(req(), 'task:submit').status, 401);
  const denied = auth.authorize(req(env.TENANT_A_TOKEN), 'provider:read');
  assert.equal(denied.ok, false); assert.equal(denied.status, 403); assert.equal(denied.reason, 'scope-denied');
  const allowed = auth.authorize(req(env.TENANT_A_TOKEN), 'task:submit');
  assert.equal(allowed.ok, true); assert.equal(allowed.principal.id, 'tenant-a');
});

test('legacy control token remains root-compatible while principal mode can coexist', () => {
  const env = { TENANT_A_TOKEN: 'tenant-a-token-0123456789abcdef' };
  const principals = parseControlPrincipals([
    { id: 'tenant-a', tenantId: 'tenant-a', tokenEnv: 'TENANT_A_TOKEN', scopes: ['task:submit'] },
  ], env);
  const legacy = 'legacy-root-token-0123456789abcdef';
  const auth = new ControlAuthenticator({ legacyToken: legacy, principals });
  const root = auth.authorize(req(legacy), 'provider:admin');
  assert.equal(root.ok, true); assert.equal(root.principal.tenantId, '*'); assert.equal(root.principal.authType, 'legacy-root');
});

test('tenant binding assigns missing tenant and rejects cross-tenant task submission', () => {
  const principal = { id: 'tenant-a', tenantId: 'tenant-a', scopes: ['task:submit'] };
  assert.equal(bindTaskToPrincipalTenant({ id:'a', capability:'compute.echo' }, principal).tenantId, 'tenant-a');
  assert.equal(bindTaskToPrincipalTenant({ id:'a', capability:'compute.echo', tenantId:'tenant-a' }, principal).tenantId, 'tenant-a');
  assert.throws(
    () => bindTaskToPrincipalTenant({ id:'a', capability:'compute.echo', tenantId:'tenant-b' }, principal),
    (error) => error.code === 'TENANT_SCOPE_VIOLATION'
  );
});

test('authenticator exposes explicit optional mode but required mutations fail closed when unconfigured', () => {
  const auth = new ControlAuthenticator();
  assert.equal(auth.optionalAuthorize(req(), 'provider:read').ok, true);
  const required = auth.authorize(req(), 'task:submit');
  assert.equal(required.ok, false); assert.equal(required.status, 503); assert.equal(required.reason, 'control-auth-not-configured');
});
