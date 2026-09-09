(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const state = { loginMfaTicket: null, bootstrapMfaTicket: null, csrf: null };

  const b64uToBuf = (s) => {
    const pad = '='.repeat((4 - (s.length % 4)) % 4);
    const raw = atob((s + pad).replace(/-/g, '+').replace(/_/g, '/'));
    return Uint8Array.from(raw, c => c.charCodeAt(0));
  };
  const bufToB64u = (buf) => {
    const bytes = new Uint8Array(buf);
    let s = ''; for (const b of bytes) s += String.fromCharCode(b);
    return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '');
  };

  function registrationOptions(options) {
    return {
      ...options,
      challenge: b64uToBuf(options.challenge),
      user: { ...options.user, id: b64uToBuf(options.user.id) },
      excludeCredentials: (options.excludeCredentials || []).map(c => ({ ...c, id: b64uToBuf(c.id) }))
    };
  }
  function authOptions(options) {
    return {
      ...options,
      challenge: b64uToBuf(options.challenge),
      allowCredentials: (options.allowCredentials || []).map(c => ({ ...c, id: b64uToBuf(c.id) }))
    };
  }
  function serializeCredential(cred) {
    const response = cred.response;
    const out = {
      id: cred.id,
      rawId: bufToB64u(cred.rawId),
      type: cred.type,
      authenticatorAttachment: cred.authenticatorAttachment || undefined,
      clientExtensionResults: cred.getClientExtensionResults(),
      response: {}
    };
    if (response.attestationObject) {
      out.response = {
        clientDataJSON: bufToB64u(response.clientDataJSON),
        attestationObject: bufToB64u(response.attestationObject),
        transports: response.getTransports ? response.getTransports() : []
      };
    } else {
      out.response = {
        clientDataJSON: bufToB64u(response.clientDataJSON),
        authenticatorData: bufToB64u(response.authenticatorData),
        signature: bufToB64u(response.signature),
        userHandle: response.userHandle ? bufToB64u(response.userHandle) : undefined
      };
    }
    return out;
  }
  async function call(path, options = {}) {
    const headers = new Headers(options.headers || {});
    headers.set('content-type', 'application/json');
    if (state.csrf && options.method && options.method !== 'GET') headers.set('x-deus-csrf', state.csrf);
    const r = await fetch(path, { credentials: 'same-origin', cache: 'no-store', ...options, headers });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.error || `HTTP_${r.status}`);
    return data;
  }
  function status(id, msg, bad = false) { const el = $(id); el.textContent = msg; el.dataset.bad = bad ? '1' : '0'; }

  async function health() {
    try {
      const r = await fetch('/api/health', { cache: 'no-store' });
      const data = await r.json();
      $('health').textContent = data.ok ? 'SECURITY READY' : `FAIL-CLOSED · ${data.missing?.length || 0} blockers`;
      $('health').dataset.ok = data.ok ? '1' : '0';
      await restoreSession();
    } catch { $('health').textContent = 'GATEWAY UNREACHABLE'; }
  }

  async function bootstrapPasskey() {
    status('bootstrapStatus', 'Đang tạo WebAuthn challenge…');
    const email = $('bootstrapEmail').value.trim();
    const token = $('bootstrapToken').value;
    try {
      const start = await call('/api/auth/bootstrap/options', { method: 'POST', headers: { 'x-deus-bootstrap-token': token }, body: JSON.stringify({ email }) });
      const cred = await navigator.credentials.create({ publicKey: registrationOptions(start.options) });
      const verify = await call('/api/auth/bootstrap/verify', { method: 'POST', headers: { 'x-deus-bootstrap-token': token }, body: JSON.stringify({ challengeId: start.challengeId, response: serializeCredential(cred) }) });
      state.bootstrapMfaTicket = verify.mfaTicket;
      $('otpUri').value = verify.otpauth;
      $('mfaBootstrap').hidden = false;
      $('bootstrapToken').value = '';
      status('bootstrapStatus', 'Passkey đã xác minh. Cần MFA để đóng bootstrap.');
    } catch (e) { status('bootstrapStatus', `Bootstrap lỗi: ${e.message}`, true); }
  }

  async function verifyBootstrapMfa() {
    try {
      const data = await call('/api/auth/bootstrap/mfa/verify', { method: 'POST', body: JSON.stringify({ mfaTicket: state.bootstrapMfaTicket, code: $('bootstrapTotp').value.trim() }) });
      state.csrf = data.csrf;
      status('bootstrapStatus', 'Founder bootstrap hoàn tất. Hãy xóa bootstrap verifier khỏi secret manager ngay.');
      $('mfaBootstrap').hidden = true;
      await restoreSession();
    } catch (e) { status('bootstrapStatus', `MFA lỗi: ${e.message}`, true); }
  }

  async function loginPasskey() {
    status('loginStatus', 'Đang yêu cầu Passkey…');
    try {
      const start = await call('/api/auth/login/options', { method: 'POST', body: JSON.stringify({ email: $('loginEmail').value.trim() }) });
      const cred = await navigator.credentials.get({ publicKey: authOptions(start.options) });
      const verify = await call('/api/auth/login/verify', { method: 'POST', body: JSON.stringify({ challengeId: start.challengeId, response: serializeCredential(cred) }) });
      state.loginMfaTicket = verify.mfaTicket;
      $('mfaLogin').hidden = false;
      status('loginStatus', 'Passkey hợp lệ. Nhập MFA để mở phiên AAL2.');
    } catch (e) { status('loginStatus', `Đăng nhập lỗi: ${e.message}`, true); }
  }

  async function loginMfa() {
    try {
      const data = await call('/api/auth/mfa/verify', { method: 'POST', body: JSON.stringify({ mfaTicket: state.loginMfaTicket, code: $('loginTotp').value.trim() }) });
      state.csrf = data.csrf;
      $('mfaLogin').hidden = true;
      status('loginStatus', 'Đã mở phiên AAL2.');
      await restoreSession();
    } catch (e) { status('loginStatus', `MFA lỗi: ${e.message}`, true); }
  }

  async function restoreSession() {
    try {
      const data = await call('/api/session');
      $('sessionCard').hidden = false;
      $('sessionData').textContent = JSON.stringify(data, null, 2);
    } catch { $('sessionCard').hidden = true; }
  }

  async function logout() {
    try { await call('/api/auth/logout', { method: 'POST', body: '{}' }); } catch {}
    state.csrf = null;
    $('sessionCard').hidden = true;
    status('loginStatus', 'Đã đăng xuất.');
  }

  $('bootstrapPasskey').addEventListener('click', bootstrapPasskey);
  $('verifyBootstrapMfa').addEventListener('click', verifyBootstrapMfa);
  $('passkeyLogin').addEventListener('click', loginPasskey);
  $('verifyLoginMfa').addEventListener('click', loginMfa);
  $('logout').addEventListener('click', logout);
  health();
})();
