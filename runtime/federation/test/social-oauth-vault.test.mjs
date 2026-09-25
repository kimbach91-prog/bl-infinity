import test from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';

process.env.SOCIAL_PUBLISH_ENABLED = 'false';
process.env.DEUS_SOCIAL_PUBLIC_BASE = 'https://social.example.test';
process.env.DEUS_WORKSTATION_001_TOKEN = 'test-runtime-kek-value-0123456789abcdef';
process.env.META_APP_ID = 'meta-app-id-test';
process.env.META_APP_SECRET = 'meta-app-secret-test';
process.env.TIKTOK_CLIENT_KEY = 'tiktok-client-key-test';
process.env.TIKTOK_CLIENT_SECRET = 'tiktok-client-secret-test';

const social = await import(`../lib/social-control.mjs?vault-test=${Date.now()}`);
const oauth = await import(`../lib/social-oauth-vault.mjs?vault-test=${Date.now()}`);

function vault() {
  return { ready: true, dek: crypto.randomBytes(32), pool: null };
}

test('oauth status exposes app configuration and callbacks without secret values', () => {
  const status = oauth.socialOAuthStatus(vault());
  assert.equal(status.vaultReady, true);
  assert.equal(status.publicBaseConfigured, true);
  for (const provider of ['facebook','instagram','threads','tiktok']) {
    assert.equal(status.providers[provider].appConfigured, true);
  }
  assert.equal(status.providers.facebook.callbackUrl, 'https://social.example.test/v1/social/oauth/facebook/callback');
  assert.equal(status.providers.instagram.callbackUrl, 'https://social.example.test/v1/social/oauth/instagram/callback');
  assert.equal(status.providers.threads.callbackUrl, 'https://social.example.test/v1/social/oauth/threads/callback');
  assert.equal(status.providers.tiktok.callbackUrl, 'https://social.example.test/v1/social/oauth/tiktok/callback');
  const serialized = JSON.stringify(status);
  assert.equal(serialized.includes('meta-app-secret-test'), false);
  assert.equal(serialized.includes('tiktok-client-secret-test'), false);
  assert.equal(serialized.includes('test-runtime-kek-value'), false);
});

test('facebook authorization uses exact callback and opaque state', () => {
  const result = oauth.socialAuthorizationUrl(vault(), 'facebook');
  const url = new URL(result.authorization_url);
  assert.equal(url.hostname, 'www.facebook.com');
  assert.equal(url.searchParams.get('redirect_uri'), 'https://social.example.test/v1/social/oauth/facebook/callback');
  assert.match(url.searchParams.get('scope'), /pages_manage_posts/);
  assert.ok((url.searchParams.get('state') || '').length > 20);
  assert.equal(url.searchParams.get('state').includes('meta-app-secret-test'), false);
});

test('instagram and tiktok authorization stay on allowlisted provider hosts', () => {
  const ig = new URL(oauth.socialAuthorizationUrl(vault(), 'instagram').authorization_url);
  const tt = new URL(oauth.socialAuthorizationUrl(vault(), 'tiktok').authorization_url);
  assert.equal(ig.hostname, 'www.instagram.com');
  assert.equal(ig.searchParams.get('enable_fb_login'), '0');
  assert.match(ig.searchParams.get('scope'), /instagram_business_content_publish/);
  assert.equal(tt.hostname, 'www.tiktok.com');
  assert.match(tt.searchParams.get('scope'), /video.publish/);
});

test('runtime social credentials can be hydrated and cleared without exposing token values', () => {
  const token = 'unit_test_social_token_not_real';
  const applied = social.applySocialRuntimeCredentials('instagram', { accessToken: token, accountId: 'ig-test-1' });
  assert.equal(applied.configured, true);
  assert.equal(applied.accountId, 'ig-test-1');
  assert.equal(JSON.stringify(social.socialControlStatus()).includes(token), false);
  assert.equal(social.clearSocialRuntimeCredentials('instagram').configured, false);
});

test('provider allowlist rejects arbitrary oauth destinations', () => {
  assert.throws(() => oauth.socialAuthorizationUrl(vault(), 'https://evil.example'), /SOCIAL_PROVIDER_NOT_ALLOWED/);
});
