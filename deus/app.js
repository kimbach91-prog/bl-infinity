(() => {
  'use strict';

  const $ = (id) => document.getElementById(id);
  const checks = [...document.querySelectorAll('.constitutionCheck')];

  const STORAGE = {
    receipt: 'deus_hos_receipt_v02',
    node: 'deus_hos_node_v02',
    drafts: 'deus_hos_task_drafts_v02',
    endpoint: 'deus_hos_gateway_endpoint',
    token: 'deus_hos_gateway_token',
    actor: 'deus_hos_actor_v02',
    auth: 'deus_hos_authenticated_v02',
    preview: 'deus_hos_preview_v02'
  };

  const state = {
    actor: null,
    authenticated: false,
    preview: false,
    receipt: null,
    node: null,
    gateway: null,
    token: null
  };

  const safeJson = (v, fallback = null) => {
    try { return v ? JSON.parse(v) : fallback; } catch { return fallback; }
  };

  function normalizeGateway(value) {
    const raw = String(value || '').trim();
    if (!raw) return null;
    try {
      const u = new URL(raw);
      if (u.protocol !== 'https:' && !['localhost', '127.0.0.1'].includes(u.hostname)) return null;
      return u.toString().replace(/\/$/, '');
    } catch { return null; }
  }

  async function sha256(text) {
    const bytes = new TextEncoder().encode(text);
    const hash = await crypto.subtle.digest('SHA-256', bytes);
    return [...new Uint8Array(hash)].map((b) => b.toString(16).padStart(2, '0')).join('');
  }

  function showOnly(view) {
    [$('loginView'), $('constitutionView'), $('nodeView')].forEach((v) => { v.hidden = v !== view; });
    $('gate').hidden = false;
    $('appView').hidden = true;
  }

  function showError(target, text) {
    target.textContent = text;
    target.hidden = false;
  }

  function clearError(target) {
    target.textContent = '';
    target.hidden = true;
  }

  function updateControlState() {
    const production = Boolean(state.gateway && state.authenticated && state.token && !state.preview);
    if (production) {
      $('controlPlaneChip').innerHTML = '<span class="dot ok"></span>CONTROL PLANE ATTACHED';
      $('modeChip').innerHTML = '<span class="dot ok"></span>PRODUCTION SESSION';
      $('workspaceSubtitle').textContent = 'Authenticated control plane attached';
      $('surplusState').textContent = 'Policy-gated';
    } else if (state.gateway) {
      $('controlPlaneChip').innerHTML = '<span class="dot warn"></span>GATEWAY CONFIGURED';
      $('modeChip').innerHTML = '<span class="dot warn"></span>PREVIEW';
      $('workspaceSubtitle').textContent = 'Gateway configured; production identity not established';
      $('surplusState').textContent = 'Unavailable';
    } else {
      $('controlPlaneChip').innerHTML = '<span class="dot warn"></span>CONTROL PLANE OFFLINE';
      $('modeChip').innerHTML = '<span class="dot warn"></span>PREVIEW';
      $('workspaceSubtitle').textContent = 'Founder Bootstrap · No production control plane attached';
      $('surplusState').textContent = 'Unavailable';
    }
  }

  function hydrateGateway() {
    const queryGateway = new URLSearchParams(location.search).get('gateway');
    if (queryGateway) {
      const normalized = normalizeGateway(queryGateway);
      if (normalized) sessionStorage.setItem(STORAGE.endpoint, normalized);
    }
    state.gateway = normalizeGateway(sessionStorage.getItem(STORAGE.endpoint));
    state.token = sessionStorage.getItem(STORAGE.token) || null;
    $('gatewayEndpoint').value = state.gateway || '';
    $('gatewayToken').value = state.token || '';
    updateControlState();
  }

  async function api(path, options = {}) {
    if (!state.gateway) throw new Error('Chưa cấu hình gateway.');
    const headers = new Headers(options.headers || {});
    headers.set('Content-Type', 'application/json');
    if (state.token) headers.set('Authorization', `Bearer ${state.token}`);
    const response = await fetch(`${state.gateway}${path}`, {
      ...options,
      headers,
      cache: 'no-store',
      mode: 'cors'
    });
    const text = await response.text();
    let body;
    try { body = text ? JSON.parse(text) : {}; } catch { body = { message: text }; }
    if (!response.ok) throw new Error(body?.error || body?.message || `HTTP ${response.status}`);
    return body || {};
  }

  function detectHardware() {
    $('cpuDetected').textContent = navigator.hardwareConcurrency ? `${navigator.hardwareConcurrency} threads` : 'Unknown';
    $('memoryDetected').textContent = navigator.deviceMemory ? `${navigator.deviceMemory} GB` : 'Unknown';
  }

  async function productionLogin() {
    clearError($('loginError'));
    const email = $('loginEmail').value.trim();
    const organization = $('loginOrg').value.trim();
    const accessCode = $('accessCode').value;
    if (!state.gateway) {
      showError($('loginError'), 'Production identity gateway chưa được gắn. Dùng Founder Preview chỉ để kiểm tra giao diện; không phải production authentication.');
      return;
    }
    if (!email || !organization || !accessCode) {
      showError($('loginError'), 'Cần email, tổ chức và thông tin xác thực của gateway.');
      return;
    }
    $('signInBtn').disabled = true;
    try {
      const result = await api('/auth/session', {
        method: 'POST',
        body: JSON.stringify({ email, organization, accessCode, surface: 'deus-human-os', version: '0.2' })
      });
      if (!result.sessionToken) throw new Error('Gateway không trả sessionToken.');
      state.actor = result.actor || { name: email, email, organization };
      state.token = result.sessionToken;
      state.authenticated = true;
      state.preview = false;
      sessionStorage.setItem(STORAGE.actor, JSON.stringify(state.actor));
      sessionStorage.setItem(STORAGE.token, state.token);
      sessionStorage.setItem(STORAGE.auth, '1');
      sessionStorage.removeItem(STORAGE.preview);
      $('accessCode').value = '';
      updateControlState();
      showOnly($('constitutionView'));
    } catch (err) {
      showError($('loginError'), `Đăng nhập thất bại: ${err.message}`);
    } finally {
      $('signInBtn').disabled = false;
    }
  }

  function founderPreview() {
    state.actor = { name: 'Founding Steward', organization: 'BL / DEUS Bootstrap', role: 'founder' };
    state.authenticated = false;
    state.preview = true;
    sessionStorage.setItem(STORAGE.actor, JSON.stringify(state.actor));
    sessionStorage.setItem(STORAGE.preview, '1');
    sessionStorage.removeItem(STORAGE.auth);
    updateControlState();
    showOnly($('constitutionView'));
  }

  function updateAcceptButton() {
    $('acceptConstitutionBtn').disabled = !checks.every((c) => c.checked);
  }

  async function acceptConstitution() {
    clearError($('constitutionError'));
    if (!checks.every((c) => c.checked)) return;

    const receiptBody = {
      surface: 'DEUS Human OS',
      surfaceVersion: '0.2',
      constitution: 'BL-CF Founding Constitution v0.4',
      schedule: 'DEUS Human OS Bootstrap Membership & Resource Schedule v0.2',
      actor: state.actor,
      acceptedAt: new Date().toISOString(),
      terms: {
        authorityAttested: true,
        commercializationCapacityTarget: 0.10,
        infrastructureDevelopmentCapacityTarget: 0.10,
        crossSessionMutualComputeIdleCap: 0.10,
        crossSessionIdleOnly: true,
        customerForegroundPriority: true,
        customerOwnWorkMayUseAllReasonablyAvailablePermittedLocalCapacity: true,
        federationSupplementationForCustomer: true,
        revocableGrant: true,
        coreIsolationAcknowledged: true
      },
      receiptMode: state.preview ? 'browser-preview' : 'server-required'
    };

    const digest = await sha256(JSON.stringify(receiptBody));
    const localReceipt = { ...receiptBody, localReceiptId: `local-sha256:${digest}` };
    $('acceptConstitutionBtn').disabled = true;
    $('acceptConstitutionBtn').textContent = 'Đang tạo receipt...';

    try {
      if (state.authenticated && state.gateway && !state.preview) {
        const result = await api('/constitution/acceptances', {
          method: 'POST',
          body: JSON.stringify(localReceipt)
        });
        if (!result.receiptId) throw new Error('Control plane không trả receiptId production.');
        state.receipt = { ...localReceipt, serverReceiptId: result.receiptId, serverProof: result.proof || null };
      } else {
        state.receipt = localReceipt;
      }
      localStorage.setItem(STORAGE.receipt, JSON.stringify(state.receipt));
      $('receiptId').textContent = state.receipt.serverReceiptId || state.receipt.localReceiptId;
      detectHardware();
      showOnly($('nodeView'));
    } catch (err) {
      showError($('constitutionError'), `Không thể hoàn tất acceptance: ${err.message}`);
    } finally {
      $('acceptConstitutionBtn').textContent = 'Chấp nhận và tạo receipt v0.2';
      updateAcceptButton();
    }
  }

  function currentNodeProfile() {
    return {
      nodeName: $('nodeName').value.trim() || 'Unnamed Node',
      region: $('nodeRegion').value.trim() || 'UNSPECIFIED',
      gpuLabel: $('gpuLabel').value.trim() || null,
      dataPolicy: $('dataPolicy').value,
      notes: $('nodeNotes').value.trim() || null,
      browserReported: {
        logicalCpuThreads: navigator.hardwareConcurrency || null,
        deviceMemoryGB: navigator.deviceMemory || null,
        platform: navigator.userAgentData?.platform || navigator.platform || 'unknown'
      },
      grant: {
        commercializationCapacityTarget: 0.10,
        infrastructureDevelopmentCapacityTarget: 0.10,
        crossSessionMutualComputeIdleCap: 0.10,
        crossSessionIdleOnly: true,
        customerForegroundPriority: true,
        customerOwnWorkMayUseAllReasonablyAvailablePermittedLocalCapacity: true,
        arbitraryInboundShell: false,
        revocable: true,
        productionAgentAttached: false
      }
    };
  }

  async function activateNode() {
    const profile = currentNodeProfile();
    $('activateNodeBtn').disabled = true;
    $('activateNodeBtn').textContent = 'Đang ghi grant...';
    try {
      if (state.authenticated && state.gateway && !state.preview) {
        const result = await api('/nodes/grants', {
          method: 'POST',
          body: JSON.stringify({ receiptId: state.receipt?.serverReceiptId, profile })
        });
        if (!result.grantId) throw new Error('Control plane không trả grantId.');
        state.node = { ...profile, grantId: result.grantId, productionAgentAttached: Boolean(result.agentAttached) };
      } else {
        const digest = await sha256(JSON.stringify({ profile, time: Date.now() }));
        state.node = { ...profile, grantId: `local-grant:${digest.slice(0, 24)}`, productionAgentAttached: false };
      }
      localStorage.setItem(STORAGE.node, JSON.stringify(state.node));
      enterApp();
    } catch (err) {
      alert(`Không thể kích hoạt node: ${err.message}`);
    } finally {
      $('activateNodeBtn').disabled = false;
      $('activateNodeBtn').textContent = 'Kích hoạt hồ sơ node';
    }
  }

  function updateIdentity() {
    const actor = state.actor || { name: 'Unknown actor', organization: 'Unknown' };
    $('actorName').textContent = actor.name || actor.email || 'Authenticated actor';
    $('actorOrg').textContent = actor.organization || actor.org || 'No organization';
    $('receiptId').textContent = state.receipt?.serverReceiptId || state.receipt?.localReceiptId || 'Not accepted';
    $('nodeState').textContent = state.node ? (state.node.productionAgentAttached ? 'Agent attached' : 'Profile active') : 'Not active';
    updateControlState();
  }

  function enterApp() {
    $('gate').hidden = true;
    $('appView').hidden = false;
    updateIdentity();
    $('composerInput').focus();
  }

  function appendMessage(kind, meta, text) {
    const box = document.createElement('div');
    box.className = `msg ${kind}`;
    const m = document.createElement('div');
    m.className = 'msg-meta';
    m.textContent = meta;
    const b = document.createElement('div');
    b.textContent = text;
    box.append(m, b);
    $('messages').appendChild(box);
    $('messages').scrollTop = $('messages').scrollHeight;
  }

  function setTaskStatus(stateText, execution, detail, progress = 0) {
    $('taskState').textContent = stateText;
    $('executionState').textContent = execution;
    $('taskDetail').textContent = detail;
    $('taskProgress').style.width = `${Math.max(0, Math.min(100, progress))}%`;
  }

  function storeDraft(task) {
    const drafts = safeJson(localStorage.getItem(STORAGE.drafts), []) || [];
    drafts.push(task);
    while (drafts.length > 50) drafts.shift();
    localStorage.setItem(STORAGE.drafts, JSON.stringify(drafts));
  }

  async function sendTask() {
    const text = $('composerInput').value.trim();
    if (!text) return;
    const task = {
      clientTaskId: crypto.randomUUID ? crypto.randomUUID() : `task-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      message: text,
      workloadClass: $('workloadClass').value,
      executionPreference: $('executionPreference').value,
      receiptId: state.receipt?.serverReceiptId || state.receipt?.localReceiptId || null,
      nodeGrantId: state.node?.grantId || null,
      resourcePolicy: {
        customerForegroundPriority: true,
        localCapacityMode: 'all-reasonably-available-permitted',
        federationSupplementation: true
      },
      createdAt: new Date().toISOString()
    };

    appendMessage('user', `YOU · ${task.workloadClass}`, text);
    $('composerInput').value = '';
    $('sendBtn').disabled = true;

    if (!(state.authenticated && state.gateway && state.token && !state.preview)) {
      storeDraft(task);
      setTaskStatus('Drafted', 'None', 'Task đã lưu cục bộ. Chưa có production execution record.', 0);
      appendMessage('system', 'SYSTEM · NOT EXECUTED', `Task ${task.clientTaskId} đã lưu cục bộ. Không có control plane production nên DEUS chưa xử lý task này.`);
      $('sendBtn').disabled = false;
      return;
    }

    try {
      setTaskStatus('Queued', 'Routing', 'Đang gửi task đến control plane với customer-first policy...', 18);
      const result = await api('/chat', { method: 'POST', body: JSON.stringify(task) });
      const taskId = result.taskId || task.clientTaskId;
      const execution = result.execution || result.route || 'Control plane';
      setTaskStatus(result.status || 'accepted', execution, `Execution record: ${taskId}`, result.progress ?? (result.reply ? 100 : 40));
      if (result.reply) appendMessage('deus', `DEUS · ${execution}`, result.reply);
      else appendMessage('system', 'SYSTEM · ACCEPTED', `Control plane đã nhận task ${taskId}. Chưa có final reply trong response này.`);
    } catch (err) {
      setTaskStatus('Error', 'None', err.message, 0);
      appendMessage('system', 'SYSTEM · EXECUTION ERROR', `Không có bằng chứng task đã hoàn tất. Gateway báo lỗi: ${err.message}`);
    } finally {
      $('sendBtn').disabled = false;
      $('composerInput').focus();
    }
  }

  function openDrawer() {
    $('settingsDrawer').hidden = false;
    $('gatewayEndpoint').value = state.gateway || '';
    $('gatewayToken').value = state.token || '';
  }

  function closeDrawer() { $('settingsDrawer').hidden = true; }

  function saveGateway() {
    const endpoint = normalizeGateway($('gatewayEndpoint').value);
    const token = $('gatewayToken').value.trim();
    if (!endpoint) {
      $('gatewayResult').textContent = 'Gateway phải là HTTPS hợp lệ. Localhost chỉ dành cho development.';
      return;
    }
    state.gateway = endpoint;
    state.token = token || null;
    sessionStorage.setItem(STORAGE.endpoint, endpoint);
    if (state.token) sessionStorage.setItem(STORAGE.token, state.token);
    else sessionStorage.removeItem(STORAGE.token);
    $('gatewayResult').textContent = state.preview
      ? 'Đã lưu gateway cho tab preview. Production Zero-Trust R2 phải dùng same-origin Passkey/MFA; preview này không được coi là production auth.'
      : 'Gateway đã lưu cho phiên hiện tại.';
    updateControlState();
  }

  function clearGateway() {
    state.gateway = null;
    state.token = null;
    sessionStorage.removeItem(STORAGE.endpoint);
    sessionStorage.removeItem(STORAGE.token);
    $('gatewayEndpoint').value = '';
    $('gatewayToken').value = '';
    $('gatewayResult').textContent = 'Đã ngắt gateway khỏi phiên trình duyệt.';
    updateControlState();
  }

  function leaveSession() {
    state.actor = null;
    state.authenticated = false;
    state.preview = false;
    state.token = null;
    [STORAGE.actor, STORAGE.auth, STORAGE.preview, STORAGE.token].forEach((k) => sessionStorage.removeItem(k));
    checks.forEach((c) => { c.checked = false; });
    updateAcceptButton();
    closeDrawer();
    showOnly($('loginView'));
    updateControlState();
  }

  function restoreSession() {
    state.actor = safeJson(sessionStorage.getItem(STORAGE.actor), null);
    state.authenticated = sessionStorage.getItem(STORAGE.auth) === '1';
    state.preview = sessionStorage.getItem(STORAGE.preview) === '1';
    state.receipt = safeJson(localStorage.getItem(STORAGE.receipt), null);
    state.node = safeJson(localStorage.getItem(STORAGE.node), null);
    if (state.actor && state.receipt && (state.authenticated || state.preview)) enterApp();
    else showOnly($('loginView'));
  }

  checks.forEach((c) => c.addEventListener('change', updateAcceptButton));
  $('signInBtn').addEventListener('click', productionLogin);
  $('founderPreviewBtn').addEventListener('click', founderPreview);
  $('backToLoginBtn').addEventListener('click', () => showOnly($('loginView')));
  $('acceptConstitutionBtn').addEventListener('click', acceptConstitution);
  $('activateNodeBtn').addEventListener('click', activateNode);
  $('skipNodeBtn').addEventListener('click', () => { state.node = null; enterApp(); });
  $('sendBtn').addEventListener('click', sendTask);
  $('composerInput').addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); sendTask(); }
  });
  [$('openGatewayBtn'), $('openNodeSettingsBtn'), $('mobileSettingsBtn')].forEach((btn) => btn.addEventListener('click', openDrawer));
  $('closeDrawerBtn').addEventListener('click', closeDrawer);
  $('settingsDrawer').addEventListener('click', (e) => { if (e.target === $('settingsDrawer')) closeDrawer(); });
  $('saveGatewayBtn').addEventListener('click', saveGateway);
  $('clearGatewayBtn').addEventListener('click', clearGateway);
  $('leaveBtn').addEventListener('click', leaveSession);

  hydrateGateway();
  detectHardware();
  restoreSession();
})();
