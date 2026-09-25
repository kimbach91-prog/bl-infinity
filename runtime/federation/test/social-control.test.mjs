import test from 'node:test';
import assert from 'node:assert/strict';

process.env.SOCIAL_PUBLISH_ENABLED = 'false';
process.env.THREADS_ACCESS_TOKEN = 'test_threads_token_not_real';
process.env.THREADS_USER_ID = '123';
process.env.INSTAGRAM_ACCESS_TOKEN = 'test_instagram_token_not_real';
process.env.INSTAGRAM_USER_ID = '456';
process.env.TIKTOK_ACCESS_TOKEN = 'test_tiktok_token_not_real';

const social = await import(`../lib/social-control.mjs?test=${Date.now()}`);

test('status exposes capability/config state without secrets', () => {
  const status = social.socialControlStatus();
  assert.equal(status.providers.threads.configured, true);
  assert.equal(status.providers.instagram.configured, true);
  assert.equal(status.providers.tiktok.configured, true);
  assert.equal(status.providers.facebook.configured, false);
  assert.equal(status.publishMasterEnabled, false);
  const serialized = JSON.stringify(status);
  assert.equal(serialized.includes('test_threads_token_not_real'), false);
  assert.equal(serialized.includes('test_instagram_token_not_real'), false);
  assert.equal(serialized.includes('test_tiktok_token_not_real'), false);
});

test('provider allowlist is strict', () => {
  assert.equal(social.normalizeSocialProvider('Instagram'), 'instagram');
  assert.equal(social.normalizeSocialProvider('Facebook'), 'facebook');
  assert.throws(() => social.normalizeSocialProvider('https://evil.example'), /SOCIAL_PROVIDER_NOT_ALLOWED/);
});

test('publish stays staged while master switch is disabled', async () => {
  const result = await social.publishSocial('threads', { mediaType: 'TEXT', text: 'hello' });
  assert.equal(result.state, 'STAGED_ONLY');
  assert.equal(result.provider, 'threads');
  assert.equal(result.reason, 'SOCIAL_PUBLISH_MASTER_DISABLED');
});

test('staged previews never leak media urls', () => {
  const preview = social.sanitizePublishPayload('tiktok', {
    mediaType: 'PHOTO',
    title: 'demo',
    photoImages: ['https://private.example/1.jpg', 'https://private.example/2.jpg'],
    privacyLevel: 'SELF_ONLY',
  });
  assert.equal(preview.photoCount, 2);
  assert.equal(JSON.stringify(preview).includes('private.example'), false);
});
