const GRAPH_VERSION = process.env.META_API_VERSION || 'v26.0';
const THREADS_BASE = 'https://graph.threads.net/v1.0';
const FACEBOOK_BASE = `https://graph.facebook.com/${GRAPH_VERSION}`;
const INSTAGRAM_BASE = `https://graph.instagram.com/${GRAPH_VERSION}`;
const TIKTOK_BASE = 'https://open.tiktokapis.com/v2';

const SOCIAL_PUBLISH_ENABLED = process.env.SOCIAL_PUBLISH_ENABLED === 'true';
const PROVIDER_WRITE = Object.freeze({
  threads: process.env.THREADS_PUBLISH_ENABLED === 'true',
  facebook: process.env.FB_PUBLISH_ENABLED === 'true',
  instagram: process.env.INSTAGRAM_PUBLISH_ENABLED === 'true',
  tiktok: process.env.TIKTOK_PUBLISH_ENABLED === 'true',
});

const CONFIG = Object.freeze({
  threads: {
    token: process.env.THREADS_ACCESS_TOKEN || '',
    userId: process.env.THREADS_USER_ID || 'me',
    requiredReadScopes: ['threads_basic'],
    requiredWriteScopes: ['threads_basic', 'threads_content_publish'],
    optionalScopes: ['threads_manage_insights', 'threads_read_replies', 'threads_manage_replies'],
    capabilities: ['profile', 'content', 'insights', 'publish'],
  },
  facebook: {
    token: process.env.FB_PAGE_ACCESS_TOKEN || '',
    pageId: process.env.FB_PAGE_ID || '',
    requiredReadScopes: ['pages_show_list', 'pages_read_engagement'],
    requiredWriteScopes: ['pages_show_list', 'pages_read_engagement', 'pages_manage_posts'],
    optionalScopes: ['read_insights', 'pages_manage_engagement'],
    capabilities: ['profile', 'content', 'insights', 'publish'],
    targetType: 'page',
  },
  instagram: {
    token: process.env.INSTAGRAM_ACCESS_TOKEN || process.env.IG_ACCESS_TOKEN || '',
    userId: process.env.INSTAGRAM_USER_ID || process.env.IG_USER_ID || '',
    requiredReadScopes: ['instagram_business_basic'],
    requiredWriteScopes: ['instagram_business_basic', 'instagram_business_content_publish'],
    optionalScopes: ['instagram_business_manage_insights', 'instagram_business_manage_comments', 'instagram_business_manage_messages'],
    capabilities: ['profile', 'content', 'insights', 'publish'],
    targetType: 'professional_account',
  },
  tiktok: {
    token: process.env.TIKTOK_ACCESS_TOKEN || '',
    openId: process.env.TIKTOK_OPEN_ID || '',
    requiredReadScopes: ['user.info.basic', 'video.list'],
    requiredWriteScopes: ['user.info.basic', 'video.publish'],
    optionalScopes: ['user.info.profile', 'user.info.stats', 'video.upload'],
    capabilities: ['profile', 'content', 'insights', 'publish'],
  },
});

const PROVIDERS = Object.freeze(['threads', 'facebook', 'instagram', 'tiktok']);

export class SocialControlError extends Error {
  constructor(provider, status, code, detail = null) {
    super(`${String(provider).toUpperCase()}_${code || 'API_ERROR'}`);
    this.name = 'SocialControlError';
    this.provider = provider;
    this.status = status;
    this.code = code || 'API_ERROR';
    this.detail = detail;
  }
}

function bool(value) {
  return Boolean(String(value || '').trim());
}

export function normalizeSocialProvider(value) {
  const provider = String(value || '').trim().toLowerCase();
  if (!PROVIDERS.includes(provider)) throw new SocialControlError('social', 400, 'PROVIDER_NOT_ALLOWED');
  return provider;
}

function configured(provider) {
  const cfg = CONFIG[provider];
  if (provider === 'facebook') return bool(cfg.token) && bool(cfg.pageId);
  if (provider === 'instagram') return bool(cfg.token) && bool(cfg.userId);
  return bool(cfg.token);
}

function writeEnabled(provider) {
  return SOCIAL_PUBLISH_ENABLED && PROVIDER_WRITE[provider] === true;
}

export function socialControlStatus() {
  return {
    schema: 'deus-social-control/2',
    graphVersion: GRAPH_VERSION,
    publishMasterEnabled: SOCIAL_PUBLISH_ENABLED,
    truthBoundary: 'configured != authorized_by_provider != executed != readback_confirmed',
    providers: Object.fromEntries(PROVIDERS.map((provider) => {
      const cfg = CONFIG[provider];
      return [provider, {
        configured: configured(provider),
        publishEnabled: writeEnabled(provider),
        requiredReadScopes: cfg.requiredReadScopes,
        requiredWriteScopes: cfg.requiredWriteScopes,
        optionalScopes: cfg.optionalScopes,
        capabilities: cfg.capabilities,
        ...(cfg.targetType ? { targetType: cfg.targetType } : {}),
      }];
    })),
  };
}

function assertConfigured(provider) {
  if (!configured(provider)) throw new SocialControlError(provider, 503, 'NOT_CONFIGURED');
}

function safeDetail(body) {
  if (!body || typeof body !== 'object') return null;
  if (body.error && typeof body.error === 'object') {
    return {
      message: body.error.message || null,
      type: body.error.type || null,
      code: body.error.code || null,
      subcode: body.error.error_subcode || null,
      logId: body.error.log_id || null,
      traceId: body.error.fbtrace_id || null,
    };
  }
  return {
    code: body.code || null,
    message: body.message || null,
    logId: body.log_id || null,
  };
}

async function requestJson(provider, url, { method = 'GET', headers = {}, body = null, token = CONFIG[provider]?.token || '', bearer = true } = {}) {
  assertConfigured(provider);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30_000);
  try {
    const response = await fetch(url, {
      method,
      headers: {
        accept: 'application/json',
        ...(bearer && token ? { authorization: `Bearer ${token}` } : {}),
        ...headers,
      },
      ...(body !== null ? { body } : {}),
      signal: controller.signal,
    });
    const text = await response.text();
    let data = {};
    try { data = text ? JSON.parse(text) : {}; }
    catch { data = { raw: text.slice(0, 1000) }; }
    const tiktokError = provider === 'tiktok' && data?.error?.code && data.error.code !== 'ok';
    if (!response.ok || tiktokError) {
      const code = data?.error?.code || data?.errors?.[0]?.title || data?.title || `HTTP_${response.status}`;
      throw new SocialControlError(provider, response.status || 502, String(code), safeDetail(data));
    }
    return data;
  } catch (error) {
    if (error instanceof SocialControlError) throw error;
    if (error?.name === 'AbortError') throw new SocialControlError(provider, 504, 'TIMEOUT');
    throw new SocialControlError(provider, 502, 'NETWORK_ERROR');
  } finally {
    clearTimeout(timeout);
  }
}

function qs(values = {}) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value === undefined || value === null || value === '') continue;
    params.set(key, Array.isArray(value) ? value.join(',') : String(value));
  }
  return params;
}

function form(values = {}) {
  return qs(values).toString();
}

export async function readSocialProfile(providerInput) {
  const provider = normalizeSocialProvider(providerInput);
  if (provider === 'threads') {
    const url = new URL(`${THREADS_BASE}/me`);
    url.search = qs({ fields: 'id,username,name,threads_profile_picture_url,threads_biography', access_token: CONFIG.threads.token });
    return requestJson(provider, url, { bearer: false });
  }
  if (provider === 'facebook') {
    const url = new URL(`${FACEBOOK_BASE}/${encodeURIComponent(CONFIG.facebook.pageId)}`);
    url.search = qs({ fields: 'id,name,link,fan_count,followers_count,verification_status', access_token: CONFIG.facebook.token });
    return requestJson(provider, url, { bearer: false });
  }
  if (provider === 'instagram') {
    const url = new URL(`${INSTAGRAM_BASE}/${encodeURIComponent(CONFIG.instagram.userId)}`);
    url.search = qs({ fields: 'id,username,name,account_type,profile_picture_url,followers_count,follows_count,media_count', access_token: CONFIG.instagram.token });
    return requestJson(provider, url, { bearer: false });
  }
  const url = new URL(`${TIKTOK_BASE}/user/info/`);
  url.search = qs({ fields: 'open_id,union_id,avatar_url,display_name,bio_description,profile_deep_link,is_verified,follower_count,following_count,likes_count,video_count' });
  return requestJson(provider, url);
}

export async function listSocialContent(providerInput, options = {}) {
  const provider = normalizeSocialProvider(providerInput);
  const limit = Math.min(Math.max(Number(options.limit || 20), 1), 100);
  if (provider === 'threads') {
    const url = new URL(`${THREADS_BASE}/me/threads`);
    url.search = qs({ fields: 'id,media_product_type,media_type,media_url,permalink,username,text,timestamp,shortcode,thumbnail_url,children,is_quote_post', limit, access_token: CONFIG.threads.token });
    return requestJson(provider, url, { bearer: false });
  }
  if (provider === 'facebook') {
    const url = new URL(`${FACEBOOK_BASE}/${encodeURIComponent(CONFIG.facebook.pageId)}/posts`);
    url.search = qs({ fields: 'id,message,created_time,permalink_url,shares,comments.limit(0).summary(true),reactions.limit(0).summary(true)', limit, access_token: CONFIG.facebook.token });
    return requestJson(provider, url, { bearer: false });
  }
  if (provider === 'instagram') {
    const url = new URL(`${INSTAGRAM_BASE}/${encodeURIComponent(CONFIG.instagram.userId)}/media`);
    url.search = qs({ fields: 'id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,username,comments_count,like_count', limit, access_token: CONFIG.instagram.token });
    return requestJson(provider, url, { bearer: false });
  }
  const url = new URL(`${TIKTOK_BASE}/video/list/`);
  url.search = qs({ fields: 'id,title,video_description,duration,cover_image_url,embed_link,create_time,share_url,like_count,comment_count,share_count,view_count' });
  return requestJson(provider, url, {
    method: 'POST',
    headers: { 'content-type': 'application/json; charset=UTF-8' },
    body: JSON.stringify({ max_count: Math.min(limit, 20), ...(options.cursor ? { cursor: Number(options.cursor) } : {}) }),
  });
}

export async function readSocialInsights(providerInput, options = {}) {
  const provider = normalizeSocialProvider(providerInput);
  if (provider === 'tiktok') return listSocialContent(provider, options);
  const targetId = String(options.targetId || (provider === 'instagram' ? CONFIG.instagram.userId : '')).trim();
  if (!targetId) throw new SocialControlError(provider, 400, 'TARGET_ID_REQUIRED');
  const metrics = String(options.metrics || '').trim();

  if (provider === 'threads') {
    const url = new URL(`${THREADS_BASE}/${encodeURIComponent(targetId)}/insights`);
    url.search = qs({ metric: metrics || 'views,likes,replies,reposts,quotes,shares', access_token: CONFIG.threads.token });
    return requestJson(provider, url, { bearer: false });
  }
  if (!metrics) throw new SocialControlError(provider, 400, 'METRICS_REQUIRED');
  const base = provider === 'facebook' ? FACEBOOK_BASE : INSTAGRAM_BASE;
  const token = CONFIG[provider].token;
  const url = new URL(`${base}/${encodeURIComponent(targetId)}/insights`);
  url.search = qs({
    metric: metrics,
    period: options.period || undefined,
    since: options.since || undefined,
    until: options.until || undefined,
    access_token: token,
  });
  return requestJson(provider, url, { bearer: false });
}

export function sanitizePublishPayload(providerInput, payload = {}) {
  const provider = normalizeSocialProvider(providerInput);
  if (provider === 'threads') return {
    mediaType: String(payload.mediaType || 'TEXT').toUpperCase(),
    text: String(payload.text || '').slice(0, 500),
    mediaUrlPresent: bool(payload.mediaUrl),
  };
  if (provider === 'facebook') return {
    message: String(payload.message || payload.text || '').slice(0, 500),
    linkPresent: bool(payload.link),
  };
  if (provider === 'instagram') return {
    mediaType: String(payload.mediaType || 'IMAGE').toUpperCase(),
    caption: String(payload.caption || payload.text || '').slice(0, 500),
    mediaUrlPresent: bool(payload.mediaUrl),
  };
  return {
    mediaType: String(payload.mediaType || 'VIDEO').toUpperCase(),
    title: String(payload.title || '').slice(0, 300),
    mediaUrlPresent: bool(payload.mediaUrl),
    photoCount: Array.isArray(payload.photoImages) ? Math.min(payload.photoImages.length, 35) : 0,
    privacyLevel: payload.privacyLevel || null,
  };
}

function staged(provider, payload) {
  return {
    state: 'STAGED_ONLY',
    provider,
    reason: !SOCIAL_PUBLISH_ENABLED ? 'SOCIAL_PUBLISH_MASTER_DISABLED' : `${provider.toUpperCase()}_PUBLISH_DISABLED`,
    proposed: sanitizePublishPayload(provider, payload),
  };
}

async function publishThreads(payload) {
  const mediaType = String(payload.mediaType || 'TEXT').toUpperCase();
  if (!['TEXT', 'IMAGE', 'VIDEO'].includes(mediaType)) throw new SocialControlError('threads', 400, 'MEDIA_TYPE_NOT_ALLOWED');
  const text = String(payload.text || '').trim();
  const mediaUrl = String(payload.mediaUrl || '').trim();
  if (mediaType === 'TEXT' && !text) throw new SocialControlError('threads', 400, 'TEXT_REQUIRED');
  if (mediaType !== 'TEXT' && !mediaUrl) throw new SocialControlError('threads', 400, 'MEDIA_URL_REQUIRED');

  const container = await requestJson('threads', `${THREADS_BASE}/me/threads`, {
    method: 'POST',
    bearer: false,
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: form({
      media_type: mediaType,
      ...(text ? { text } : {}),
      ...(mediaType === 'IMAGE' ? { image_url: mediaUrl } : {}),
      ...(mediaType === 'VIDEO' ? { video_url: mediaUrl } : {}),
      access_token: CONFIG.threads.token,
    }),
  });
  const creationId = container?.id;
  if (!creationId) throw new SocialControlError('threads', 502, 'CREATION_ID_MISSING');
  const published = await requestJson('threads', `${THREADS_BASE}/me/threads_publish`, {
    method: 'POST',
    bearer: false,
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: form({ creation_id: creationId, access_token: CONFIG.threads.token }),
  });
  const id = published?.id || null;
  return { state: 'EXECUTED_UNVERIFIED', provider: 'threads', creationId, id, ...(id ? { readback: await readSocialObject('threads', id) } : {}) };
}

async function publishFacebook(payload) {
  const message = String(payload.message || payload.text || '').trim();
  if (!message && !payload.link) throw new SocialControlError('facebook', 400, 'CONTENT_REQUIRED');
  const created = await requestJson('facebook', `${FACEBOOK_BASE}/${encodeURIComponent(CONFIG.facebook.pageId)}/feed`, {
    method: 'POST',
    bearer: false,
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: form({ message: message || undefined, link: payload.link || undefined, access_token: CONFIG.facebook.token }),
  });
  const id = created?.id || null;
  return { state: 'EXECUTED_UNVERIFIED', provider: 'facebook', id, ...(id ? { readback: await readSocialObject('facebook', id) } : {}) };
}

async function publishInstagram(payload) {
  const mediaType = String(payload.mediaType || 'IMAGE').toUpperCase();
  if (!['IMAGE', 'REELS'].includes(mediaType)) throw new SocialControlError('instagram', 400, 'MEDIA_TYPE_NOT_ALLOWED');
  const mediaUrl = String(payload.mediaUrl || '').trim();
  const caption = String(payload.caption || payload.text || '').trim();
  if (!mediaUrl) throw new SocialControlError('instagram', 400, 'MEDIA_URL_REQUIRED');

  const container = await requestJson('instagram', `${INSTAGRAM_BASE}/${encodeURIComponent(CONFIG.instagram.userId)}/media`, {
    method: 'POST',
    bearer: false,
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: form({
      ...(mediaType === 'IMAGE' ? { image_url: mediaUrl } : { media_type: 'REELS', video_url: mediaUrl }),
      ...(caption ? { caption } : {}),
      access_token: CONFIG.instagram.token,
    }),
  });
  const creationId = container?.id || null;
  if (!creationId) throw new SocialControlError('instagram', 502, 'CREATION_ID_MISSING');

  if (mediaType === 'REELS') {
    const statusUrl = new URL(`${INSTAGRAM_BASE}/${encodeURIComponent(creationId)}`);
    statusUrl.search = qs({ fields: 'id,status_code,status', access_token: CONFIG.instagram.token });
    const containerStatus = await requestJson('instagram', statusUrl, { bearer: false });
    if (containerStatus?.status_code && containerStatus.status_code !== 'FINISHED') {
      return { state: 'EXECUTED_UNVERIFIED', provider: 'instagram', stage: 'CONTAINER_PROCESSING', creationId, containerStatus };
    }
  }

  const published = await requestJson('instagram', `${INSTAGRAM_BASE}/${encodeURIComponent(CONFIG.instagram.userId)}/media_publish`, {
    method: 'POST',
    bearer: false,
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: form({ creation_id: creationId, access_token: CONFIG.instagram.token }),
  });
  const id = published?.id || null;
  return { state: 'EXECUTED_UNVERIFIED', provider: 'instagram', creationId, id, ...(id ? { readback: await readSocialObject('instagram', id) } : {}) };
}

async function publishTikTok(payload) {
  const mediaType = String(payload.mediaType || 'VIDEO').toUpperCase();
  if (!['VIDEO', 'PHOTO'].includes(mediaType)) throw new SocialControlError('tiktok', 400, 'MEDIA_TYPE_NOT_ALLOWED');
  const mediaUrl = String(payload.mediaUrl || '').trim();
  const photoImages = Array.isArray(payload.photoImages)
    ? payload.photoImages.map((value) => String(value || '').trim()).filter(Boolean).slice(0, 35)
    : [];
  const privacyLevel = String(payload.privacyLevel || '').trim();
  if (mediaType === 'VIDEO' && !mediaUrl) throw new SocialControlError('tiktok', 400, 'MEDIA_URL_REQUIRED');
  if (mediaType === 'PHOTO' && !photoImages.length) throw new SocialControlError('tiktok', 400, 'PHOTO_IMAGES_REQUIRED');
  if (!privacyLevel) throw new SocialControlError('tiktok', 400, 'PRIVACY_LEVEL_REQUIRED');

  const creator = await requestJson('tiktok', `${TIKTOK_BASE}/post/publish/creator_info/query/`, {
    method: 'POST',
    headers: { 'content-type': 'application/json; charset=UTF-8' },
    body: '{}',
  });
  const allowed = creator?.data?.privacy_level_options || [];
  if (Array.isArray(allowed) && allowed.length && !allowed.includes(privacyLevel)) {
    throw new SocialControlError('tiktok', 400, 'PRIVACY_LEVEL_NOT_ALLOWED');
  }

  const init = mediaType === 'VIDEO'
    ? await requestJson('tiktok', `${TIKTOK_BASE}/post/publish/video/init/`, {
        method: 'POST',
        headers: { 'content-type': 'application/json; charset=UTF-8' },
        body: JSON.stringify({
          post_info: {
            title: String(payload.title || '').slice(0, 2200),
            privacy_level: privacyLevel,
            disable_duet: Boolean(payload.disableDuet),
            disable_comment: Boolean(payload.disableComment),
            disable_stitch: Boolean(payload.disableStitch),
            is_aigc: Boolean(payload.isAigc),
            brand_organic_toggle: Boolean(payload.brandOrganicToggle),
          },
          source_info: { source: 'PULL_FROM_URL', video_url: mediaUrl },
        }),
      })
    : await requestJson('tiktok', `${TIKTOK_BASE}/post/publish/content/init/`, {
        method: 'POST',
        headers: { 'content-type': 'application/json; charset=UTF-8' },
        body: JSON.stringify({
          post_info: {
            title: String(payload.title || '').slice(0, 90),
            description: String(payload.description || payload.title || '').slice(0, 4000),
            privacy_level: privacyLevel,
            disable_comment: Boolean(payload.disableComment),
            auto_add_music: payload.autoAddMusic !== false,
          },
          source_info: {
            source: 'PULL_FROM_URL',
            photo_cover_index: Math.max(0, Number(payload.photoCoverIndex || 0)),
            photo_images: photoImages,
          },
          post_mode: 'DIRECT_POST',
          media_type: 'PHOTO',
        }),
      });

  const publishId = init?.data?.publish_id || null;
  return {
    state: 'EXECUTED_UNVERIFIED',
    provider: 'tiktok',
    publishId,
    creatorInfo: creator?.data || null,
    ...(publishId ? { readback: await readSocialObject('tiktok', publishId) } : {}),
  };
}

export async function publishSocial(providerInput, payload = {}) {
  const provider = normalizeSocialProvider(providerInput);
  assertConfigured(provider);
  if (!writeEnabled(provider)) return staged(provider, payload);
  if (provider === 'threads') return publishThreads(payload);
  if (provider === 'facebook') return publishFacebook(payload);
  if (provider === 'instagram') return publishInstagram(payload);
  return publishTikTok(payload);
}

export async function readSocialObject(providerInput, idInput) {
  const provider = normalizeSocialProvider(providerInput);
  const id = String(idInput || '').trim();
  if (!id) throw new SocialControlError(provider, 400, 'ID_REQUIRED');

  if (provider === 'threads') {
    const url = new URL(`${THREADS_BASE}/${encodeURIComponent(id)}`);
    url.search = qs({ fields: 'id,media_product_type,media_type,media_url,permalink,username,text,timestamp,shortcode,thumbnail_url,is_quote_post', access_token: CONFIG.threads.token });
    return requestJson(provider, url, { bearer: false });
  }
  if (provider === 'facebook') {
    const url = new URL(`${FACEBOOK_BASE}/${encodeURIComponent(id)}`);
    url.search = qs({ fields: 'id,message,created_time,permalink_url,shares,comments.limit(0).summary(true),reactions.limit(0).summary(true)', access_token: CONFIG.facebook.token });
    return requestJson(provider, url, { bearer: false });
  }
  if (provider === 'instagram') {
    const url = new URL(`${INSTAGRAM_BASE}/${encodeURIComponent(id)}`);
    url.search = qs({ fields: 'id,caption,media_type,media_url,permalink,thumbnail_url,timestamp,username,comments_count,like_count', access_token: CONFIG.instagram.token });
    return requestJson(provider, url, { bearer: false });
  }
  return requestJson(provider, `${TIKTOK_BASE}/post/publish/status/fetch/`, {
    method: 'POST',
    headers: { 'content-type': 'application/json; charset=UTF-8' },
    body: JSON.stringify({ publish_id: id }),
  });
}
