(() => {
  'use strict';

  const IDS = {
    gate: 'gate', loginView: 'loginView', constitutionView: 'constitutionView', nodeView: 'nodeView', appView: 'appView',
    signInBtn: 'signInBtn', founderPreviewBtn: 'founderPreviewBtn', loginEmail: 'loginEmail', loginOrg: 'loginOrg', accessCode: 'accessCode', loginError: 'loginError',
    acceptConstitutionBtn: 'acceptConstitutionBtn', backToLoginBtn: 'backToLoginBtn', constitutionError: 'constitutionError',
    activateNodeBtn: 'activateNodeBtn', skipNodeBtn: 'skipNodeBtn', cpuDetected: 'cpuDetected', memoryDetected: 'memoryDetected', nodeName: 'nodeName', nodeRegion: 'nodeRegion', gpuLabel: 'gpuLabel', dataPolicy: 'dataPolicy', nodeNotes: 'nodeNotes',
    actorName: 'actorName', actorOrg: 'actorOrg', workspaceSubtitle: 'workspaceSubtitle', modeChip: 'modeChip', controlPlaneChip: 'controlPlaneChip',
    nodeState: 'nodeState', surplusState: 'surplusState', receiptId: 'receiptId', taskState: 'taskState', executionState: 'executionState', taskProgress: 'taskProgress', taskDetail: 'taskDetail',
    composerInput: 'composerInput', workloadClass: 'workloadClass', executionPreference: 'executionPreference', sendBtn: 'sendBtn', messages: 'messages',
    settingsDrawer: 'settingsDrawer', openGatewayBtn: 'openGatewayBtn', openNodeSettingsBtn: 'openNodeSettingsBtn', mobileSettingsBtn: 'mobileSettingsBtn', closeDrawerBtn: 'closeDrawerBtn',
    gatewayEndpoint: 'gatewayEndpoint', gatewayToken: 'gatewayToken', saveGatewayBtn: 'saveGatewayBtn', clearGatewayBtn: 'clearGatewayBtn', gatewayResult: 'gatewayResult', leaveBtn: 'leaveBtn'
  };

  const el = Object.fromEntries(Object.entries(IDS).map(([k, id]) => [k, document.getElementById(id)]));
  const constitutionChecks = [...document.querySelectorAll('.constitutionCheck')];

  const STORAGE = {
    receipt: 'deus_hos_receipt_v01',
    node: 'deus_hos_node_v01',
    drafts: 'deus_hos_task_drafts_v01',
    endpoint: 'deus_hos_gateway_endpoint',
    token: 'deus_hos_gateway_token',
    actor: 'deus_hos_actor',
    auth: 'deus_hos_authenticated',
    preview: 'deus_hos_preview'
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

  function safeJsonParse(value, fallback = null) {
    try { return value ? JSON.parse(value) : fallback; } catch { return fallback; }
  }

  function getSession(key) { return sessionStorage.getItem(key); }
  function setSession(key, value) { sessionStorage.setItem(key, value); }
  function clearSession(key) { sessionStorage.removeItem(key); }

  function normalizeGateway(value) {
    const raw = (value || '').trim();
    if (!raw) return null;
    try {
      const url = new URL(raw);
      if (url.protocol !== 'https:' && url.hostname !== 'localhost' && url.hostname !== '127.0.0.1') return null;
      return url.toString().replace(/\/$/, '');
    } catch {
      return null;
    }
  }

  function hydrateGateway() {
    const urlParam = new URLSearchParams(location.search).get('gateway');
    if (urlParam) {
      const normalized = normalizeGateway(urlParam);
      if (normalized) setSession(STORAGE.endpoint, normalized);
    }
    state.gateway = normalizeGateway(getSession(STORAGE.endpoint));
    state.token = getSession(STORAGE.token) || null;
    el.gatewayEndpoint.value = state.gateway || '';
    el.gatewayToken.value = state.token || '';
    updateControlPlaneStatus();
  }

  function updateControlPlaneStatus() {
    const online = Boolean(state.gateway && state.authenticated && state.token && !state.preview);
    if (online) {
      el.controlPlaneChip.innerHTML = '<span class="dot ok"></span>CONTROL PLANE ATTACHED';
      el.modeChip.innerHTML = '<span class="dot ok"></span>PRODUCTION SESSION';
      el.workspaceSubtitle.textContent = 'Authenticated control plane attached';
      el.surplusState.textContent = 'Policy-gated';
    } else if (state.gateway) {
      el.controlPlaneChip.innerHTML = '<span class="dot warn"></span>GATEWAY CONFIGURED';
      el.modeChip.innerHTML = '<span class="dot warn"></span>PREVIEW';
      el.workspaceSubtitle.textContent = 'Gateway configured, but no authenticated production session';
      el.surplusState.textContent = 'Unavailable';
    } else {
      el.controlPlaneChip.innerHTML = '<span class="dot warn"></span>CONTROL PLANE OFFLINE';
      el.modeChip.innerHTML = '<span class="dot warn"></span>PREVIEW';
      el.workspaceSubtitle.textContent = 'Founder Bootstrap · No production control plane attached';
      el.surplusState.textContent = 'Unavailable';
    }
  }

  async function api(path, options = {}) {
    if (!state.gateway) throw new Error('Chưa cấu hình gateway.');
    const headers = new Headers(options.headers || {});
    headers.set('Content-Type', 'application/json');
    if (state.token) headers.set('Authorization', `Bearer ${state.token}`);
    const res = await fetch(`${state.gateway}${path}`, { ...options, headers, mode: 'cors', cache: 'no-store' });
    const text = await res.text();
    let body = null;
    try { body = text ? JSON.parse(text) : {}; } catch { body = { message: text }; }
    if (!res.ok) throw new Error(body?.error || body?.message || `HTTP ${res.status}`);
    return body || {};
  }

  function showOnly(view) {
    [el.loginView, el.constitutionView, el.nodeView].forEach(v => { v.hidden = v !== view; });
    el.gate.hidden = false;
    el.appView.hidden = true;
  }

  function showError(target, message) {
    target.textContent = message;
    target.hidden = false;
  }

  function clearError(target) {
    target.hidden = true;
    target.textContent = '';
  }

  function detectHardware() {
    const cores = navigator.hardwareConcurrency || null;
    const memory = navigator.deviceMemory || null;
    el.cpuDetected.textContent = cores ? `${cores} threads` : 'Unknown';
    el.memoryDetected.textContent = memory ? `${memory} GB` : 'Unknown';
  }

  async function sha256(text) {
    const bytes = new TextEncoder().encode(text);
    const hash = await crypto.subtle.digest('SHA-256', bytes);
    return [...new Uint8Array(hash)].map(b => b.toString(16).padStart(2, '0')).join('');
  }

  async function startProductionLogin() {
    clearError(el.loginError);
    const email = el.loginEmail.value.trim();
    const org = el.loginOrg.value.trim();
    const code = el.accessCode.value;

    if (!state.gateway) {
      showError(el.loginError, 'Chưa có gateway production. Hiện có thể dùng Founder Preview hoặc mở URL với ?gateway=https://... để bootstrap identity service.');
      return;
    }
    if (!email || !org || !code) {
      showError(el.loginError, 'Cần email, tổ chức và mã truy cập để đăng nhập production.');
      return;
    }

    el.signInBtn.disabled = true;
    el.signInBtn.textContent = 'Đang xác thực...';
    try {
      const result = await api('/auth/session', {
        method: 'POST',
        body: JSON.stringify({ email, organization: org, accessCode: code, surface: 'deus-human-os', version: '0.1' })
      });
      if (!result.sessionToken) throw new Error('Gateway không trả sessionToken.');
      state.token = result.sessionToken;
      state.actor = result.actor || { name: email, organization: org, email };
      state.authenticated = true;
      state.preview = false;
      setSession(STORAGE.token, state.token);
      setSession(STORAGE.actor, JSON.stringify(state.actor));
      setSession(STORAGE.auth, '1');
      clearSession(STORAGE.preview);
      el.accessCode.value = '';
      updateControlPlaneStatus();
      showOnly(el.constitutionView);
    } catch (err) {
      showError(el.loginError, `Đăng nhập thất bại: ${err.message}`);
    } finally {
      el.signInBtn.disabled = false;
      el.signInBtn.textContent = 'Đăng nhập';
    }
  }

  function startFounderPreview() {
    state.actor = { name: 'Founding Steward', organization: 'BL / DEUS Bootstrap', role: 'founder' };
    state.authenticated = false;
    state.preview = true;
    setSession(STORAGE.actor, JSON.stringify(state.actor));
    setSession(STORAGE.preview, '1');
    clearSession(STORAGE.auth);
    updateControlPlaneStatus();
    showOnly(el.constitutionView);
  }

  function updateAcceptButton() {
    el.acceptConstitutionBtn.disabled = !constitutionChecks.every(c => c.checked);
  }

  async function acceptConstitution() {
    clearError(el.constitutionError);
    if (!constitutionChecks.every(c => c.checked)) return;

    const receiptBody = {
      surface: 'DEUS Human OS',
      surfaceVersion: '0.1',
      constitution: 'BL-CF Founding Constitution v0.4',
      schedule: 'DEUS Human OS Membership & Settlement Schedule v0.1',
      actor: state.actor,
      acceptedAt: new Date().toISOString(),
      terms: {
        authorityAttested: true,
        officialProtocolCommercialShare: 0.10,
        deusPerformanceShareVerifiedIncrementalValue: 0.10,
        eligibleIdleComputeCap: 0.10,
        localWorkloadPriority: true,
        revocableGrant: true,
        coreIsolationAcknowledged: true
      },
      receiptMode: state.preview ? 'browser-preview' : 'server-required'
    };
    const digest = await sha256(JSON.stringify(receiptBody));
    const localReceipt = { ...receiptBody, localReceiptId: `local-sha256:${digest}` };

    el.acceptConstitutionBtn.disabled = true;
    el.acceptConstitutionBtn.textContent = 'Đang tạo receipt...';
    try {
      if (state.authenticated && state.gateway && !state.preview) {
        const result = await api('/constitution/acceptances', { method: 'POST', body: JSON.stringify(localReceipt) });
        if (!result.receiptId) throw new Error('Control plane không trả receiptId production.');
        state.receipt = { ...localReceipt, serverReceiptId: result.receiptId, serverProof: result.proof || null };
      } else {
        state.receipt = localReceipt;
      }
      localStorage.setItem(STORAGE.receipt, JSON.stringify(state.receipt));
      el.receiptId.textContent = state.receipt.serverReceiptId || state.receipt.localReceiptId;
      detectHardware();
      showOnly(el.nodeView);
    } catch (err) {
      showError(el.constitutionError, `Không thể hoàn tất acceptance: ${err.message}`);
    } finally {
      el.acceptConstitutionBtn.textContent = 'Chấp nhận và tạo receipt';
      updateAcceptButton();
    }
  }

  function currentNodeProfile() {
    return {
      nodeName: el.nodeName.value.trim() || 'Unnamed Node',
      region: el.nodeRegion.value.trim() || 'UNSPECIFIED',
      gpuLabel: el.gpuLabel.value.trim() || null,
      dataPolicy: el.dataPolicy.value,
      notes: el.nodeNotes.value.trim() || null,
      browserReported: {
        logicalCpuThreads: navigator.hardwareConcurrency || null,
        deviceMemoryGB: navigator.deviceMemory || null,
        userAgentClass: navigator.userAgentData?.platform || navigator.platform || 'unknown'
      },
      grant: {
        eligibleIdleComputeCap: 0.10,
        localWorkloadPriority: true,
        arbitraryInboundShell: false,
        revocable: true,
        productionAgentAttached: false
      }
    };
  }

  async function activateNode() {
    const profile = currentNodeProfile();
    el.activateNodeBtn.disabled = true;
    el.activateNodeBtn.textContent = 'Đang ghi grant...';
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
      el.activateNodeBtn.disabled = false;
      el.activateNodeBtn.textContent = 'Kích hoạt hồ sơ node';
    }
  }

  function skipNode() {
    state.node = null;
    enterApp();
  }

  function updateAppIdentity() {
    const actor = state.actor || { name: 'Unknown actor', organization: 'Unknown' };
    el.actorName.textContent = actor.name || actor.email || 'Authenticated actor';
    el.actorOrg.textContent = actor.organization || actor.org || 'No organization';
    el.receiptId.textContent = state.receipt?.serverReceiptId || state.receipt?.localReceiptId || 'Not accepted';
    if (state.node) {
      el.nodeState.textContent = state.node.productionAgentAttached ? 'Agent attached' : 'Profile active';
    } else {
      el.nodeState.textContent = 'Not active';
    }
    updateControlPlaneStatus();
  }

  function enterApp() {
    el.gate.hidden = true;
    el.appView.hidden = false;
    updateAppIdentity();
    el.composerInput.focus();
  }

  function appendMessage(kind, meta, text) {
    const box = document.createElement('div');
    box.className = `msg ${kind}`;
    const m = document.createElement('div');
    m.className = 'msg-meta';
    m.textContent = meta;
    const body = document.createElement('div');
    body.textContent = text;
    box.append(m, body);
    el.messages.appendChild(box);
    el.messages.scrollTop = el.messages.scrollHeight;
  }

  function setTaskStatus(stateText, executionText, detail, progress = 0) {
    el.taskState.textContent = stateText;
    el.executionState.textContent = executionText;
    el.taskDetail.textContent = detail;
    el.taskProgress.style.width = `${Math.max(0, Math.min(100, progress))}%`;
  }

  function storeDraft(task) {
    const drafts = safeJsonParse(localStorage.getItem(STORAGE.drafts), []) || [];
    drafts.push(task);
    while (drafts.length > 50) drafts.shift();
    localStorage.setItem(STORAGE.drafts, JSON.stringify(drafts));
  }

  async function sendTask() {
    const text = el.composerInput.value.trim();
    if (!text) return;
    const task = {
      clientTaskId: crypto.randomUUID ? crypto.randomUUID() : `task-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      message: text,
      workloadClass: el.workloadClass.value,
      executionPreference: el.executionPreference.value,
      receiptId: state.receipt?.serverReceiptId || state.receipt?.localReceiptId || null,
      nodeGrantId: state.node?.grantId || null,
      createdAt: new Date().toISOString()
    };

    appendMessage('user', `YOU · ${task.workloadClass}`, text);
    el.composerInput.value = '';
    el.sendBtn.disabled = true;

    if (!(state.authenticated && state.gateway && state.token && !state.preview)) {
      storeDraft(task);
      setTaskStatus('Drafted', 'None', 'Task đã lưu cục bộ. Chưa có production execution record.', 0);
      appendMessage('system', 'SYSTEM · NOT EXECUTED', `Task ${task.clientTaskId} đã được lưu cục bộ. Không có control plane production nên DEUS chưa xử lý task này.`);
      el.sendBtn.disabled = false;
      return;
    }

    try {
      setTaskStatus('Queued', 'Routing', 'Đang gửi task đến control plane...', 18);
      const result = await api('/chat', {
        method: 'POST',
        body: JSON.stringify(task)
      });
      const taskId = result.taskId || task.clientTaskId;
      const status = result.status || 'accepted';
      const execution = result.execution || result.route || 'Control plane';
      setTaskStatus(status, execution, `Execution record: ${taskId}`, result.progress ?? (result.reply ? 100 : 40));
      if (result.reply) {
        appendMessage('deus', `DEUS · ${execution}`, result.reply);
      } else {
        appendMessage('system', 'SYSTEM · ACCEPTED', `Control plane đã nhận task ${taskId}. Chưa có final reply trong response này.`);
      }
    } catch (err) {
      setTaskStatus('Error', 'None', err.message, 0);
      appendMessage('system', 'SYSTEM · EXECUTION ERROR', `Không có bằng chứng task đã hoàn tất. Gateway báo lỗi: ${err.message}`);
    } finally {
      el.sendBtn.disabled = false;
      el.composerInput.focus();
    }
  }

  function openDrawer() {
    el.settingsDrawer.hidden = false;
    el.gatewayEndpoint.value = state.gateway || '';
    el.gatewayToken.value = state.token || '';
  }

  function closeDrawer() { el.settingsDrawer.hidden = true; }

  function saveGateway() {
    const endpoint = normalizeGateway(el.gatewayEndpoint.value);
    const token = el.gatewayToken.value.trim();
    if (!endpoint) {
      el.gatewayResult.textContent = 'Gateway phải là HTTPS hợp lệ. Localhost chỉ dành cho development.';
      return;
    }
    state.gateway = endpoint;
    state.token = token || null;
    setSession(STORAGE.endpoint, endpoint);
    if (state.token) setSession(STORAGE.token, state.token); else clearSession(STORAGE.token);
    el.gatewayResult.textContent = state.preview
      ? 'Gateway đã lưu cho tab này. Founder Preview vẫn không được coi là production auth; hãy thoát và đăng nhập qua identity service để thực thi thật.'
      : 'Gateway đã lưu cho phiên hiện tại.';
    updateControlPlaneStatus();
  }

  function clearGateway() {
    state.gateway = null;
    state.token = null;
    clearSession(STORAGE.endpoint);
    clearSession(STORAGE.token);
    el.gatewayEndpoint.value = '';
    el.gatewayToken.value = '';
    el.gatewayResult.textContent = 'Đã ngắt gateway khỏi phiên trình duyệt.';
    updateControlPlaneStatus();
  }

  function leaveSession() {
    state.actor = null;
    state.authenticated = false;
    state.preview = false;
    state.token = null;
    clearSession(STORAGE.actor);
    clearSession(STORAGE.auth);
    clearSession(STORAGE.preview);
    clearSession(STORAGE.token);
    closeDrawer();
    constitutionChecks.forEach(c => { c.checked = false; });
    updateAcceptButton();
    showOnly(el.loginView);
    updateControlPlaneStatus();
  }

  function restoreSession() {
    state.actor = safeJsonParse(getSession(STORAGE.actor), null);
    state.authenticated = getSession(STORAGE.auth) === '1';
    state.preview = getSession(STORAGE.preview) === '1';
    state.receipt = safeJsonParse(localStorage.getItem(STORAGE.receipt), null);
    state.node = safeJsonParse(localStorage.getItem(STORAGE.node), null);

    if (state.actor && state.receipt && (state.authenticated || state.preview)) {
      enterApp();
    } else {
      showOnly(el.loginView);
    }
  }

  constitutionChecks.forEach(c => c.addEventListener('change', updateAcceptButton));
  el.signInBtn.addEventListener('click', startProductionLogin);
  el.founderPreviewBtn.addEventListener('click', startFounderPreview);
  el.backToLoginBtn.addEventListener('click', () => showOnly(el.loginView));
  el.acceptConstitutionBtn.addEventListener('click', acceptConstitution);
  el.activateNodeBtn.addEventListener('click', activateNode);
  el.skipNodeBtn.addEventListener('click', skipNode);
  el.sendBtn.addEventListener('click', sendTask);
  el.composerInput.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      sendTask();
    }
  });
  [el.openGatewayBtn, el.openNodeSettingsBtn, el.mobileSettingsBtn].forEach(btn => btn.addEventListener('click', openDrawer));
  el.closeDrawerBtn.addEventListener('click', closeDrawer);
  el.settingsDrawer.addEventListener('click', e => { if (e.target === el.settingsDrawer) closeDrawer(); });
  el.saveGatewayBtn.addEventListener('click', saveGateway);
  el.clearGatewayBtn.addEventListener('click', clearGateway);
  el.leaveBtn.addEventListener('click', leaveSession);

  hydrateGateway();
  detectHardware();
  restoreSession();
})();
