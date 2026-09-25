import test from 'node:test';
import assert from 'node:assert/strict';

process.env.SOCIAL_PUBLISH_ENABLED = 'false';

const social = await import(`../lib/social-control.mjs?vault-test=${Date.now()}`);
const vault = await import(`../lib/social-oauth-vault.mjs?vault-test=${Date.now()}`);

test('oauth status is safe without credentials', () => {
  const status = vault.socialOAuthStatus({ ready: false });
  assert.equal(status.vaultReady, false);
  assert.equal(status.providers.facebook.appConfigured, false);
  assert.equal(status.providers.instagram.appConfigured, false);
  assert.equal(status.providers.threads.appConfigured, false);
  assert.equal(status.providers.tiktok.appConfigured, false);
  const serialized = JSON.stringify(status);
  assert.equal(/access[_-]?token|client[_-]?secret/i.test(serialized), false);
});

test('runtime social credentials can be hydrated and cleared without exposing the token', () => {
  const token = 'unit_test_social_token_not_real';
  const applied = social.applySocialRuntimeCredentials('instagram', {
    accessToken: token,
    accountId: 'ig-test-1',
  });
  assert.equal(applied.configured, true);
  assert.equal(applied.accountId, 'ig-test-1');
  assert.equal(JSON.stringify(social.socialControlStatus()).includes(token), false);
  const cleared = social.clearSocialRuntimeCredentials('instagram');
  assert.equal(cleared.configured, false);
});

test('oauth module exports canonical lifecycle functions', () => {
  for (const name of [
    'createSocialOAuthVault','listSocialAccounts','hydrateActiveSocialAccounts',
    'activateSocialAccount','disconnectSocialAccount','socialAuthorizationUrl',
    'handleSocialOAuthCallback','refreshSocialAccount','claimSocialReceipt',
    'finalizeSocialReceipt','getSocialReceipt',
  ]) assert.equal(typeof vault[name], 'function', name);
});
