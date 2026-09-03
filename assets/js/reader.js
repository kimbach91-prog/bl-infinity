(() => {
  const surface = document.querySelector('[data-reader-surface], article.prose, .reader-prose');
  if (!surface || document.body.dataset.readerMounted === 'true') return;
  document.body.dataset.readerMounted = 'true';
  document.body.classList.add('bl-reader');

  const lang = (document.documentElement.lang || 'vi').toLowerCase();
  const en = !lang.startsWith('vi');
  const key = 'bl-reader-v2';
  const defaults = { theme: 'paper', font: 'literary', size: 18, lineHeight: 1.78, focus: false };
  let prefs = { ...defaults };
  try { prefs = { ...defaults, ...JSON.parse(localStorage.getItem(key) || '{}') }; } catch (_) {}
  const clamp = (v, min, max) => Math.min(max, Math.max(min, v));
  const save = () => { try { localStorage.setItem(key, JSON.stringify(prefs)); } catch (_) {} };

  const apply = () => {
    prefs.size = clamp(Number(prefs.size) || 18, 16, 23);
    prefs.lineHeight = clamp(Number(prefs.lineHeight) || 1.78, 1.62, 2.02);
    if (!['paper','sepia','night'].includes(prefs.theme)) prefs.theme = 'paper';
    if (!['literary','system'].includes(prefs.font)) prefs.font = 'literary';
    document.body.dataset.readerTheme = prefs.theme;
    document.body.classList.toggle('reader-focus', Boolean(prefs.focus));
    document.documentElement.style.setProperty('--reader-font-size', `${prefs.size}px`);
    document.documentElement.style.setProperty('--reader-line-height', String(prefs.lineHeight));
    document.documentElement.style.setProperty('--reader-font-family', prefs.font === 'system'
      ? 'system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif'
      : '"Iowan Old Style","Palatino Linotype","Book Antiqua",Georgia,"Times New Roman",serif');
  };
  apply();

  const progressTrack = document.createElement('div');
  progressTrack.className = 'reader-progress-track';
  progressTrack.setAttribute('aria-hidden','true');
  const progressBar = document.createElement('div');
  progressBar.className = 'reader-progress-bar';
  progressTrack.append(progressBar);
  document.body.append(progressTrack);

  const dock = document.createElement('div');
  dock.className = 'reader-dock';
  dock.setAttribute('aria-label', en ? 'Reader controls' : 'Điều khiển trình đọc');
  const percent = document.createElement('span');
  percent.className = 'reader-percent';
  percent.textContent = '0%';
  const settings = document.createElement('button');
  settings.type = 'button'; settings.textContent = 'Aa';
  settings.setAttribute('aria-label', en ? 'Reading preferences' : 'Tùy chỉnh đọc');
  settings.setAttribute('aria-expanded','false');
  const theme = document.createElement('button');
  theme.type = 'button'; theme.textContent = '◐';
  theme.setAttribute('aria-label', en ? 'Cycle theme' : 'Đổi nền đọc');
  const focus = document.createElement('button');
  focus.type = 'button'; focus.textContent = '▣';
  focus.setAttribute('aria-label', en ? 'Focus mode' : 'Chế độ tập trung');
  dock.append(percent, settings, theme, focus);
  document.body.append(dock);

  const panel = document.createElement('section');
  panel.className = 'reader-panel'; panel.hidden = true;
  panel.setAttribute('aria-label', en ? 'Reading preferences' : 'Tùy chỉnh đọc');
  panel.innerHTML = `
    <div class="reader-panel-head"><span>${en ? 'Reader' : 'Trình đọc'}</span><button type="button" class="reader-panel-close" aria-label="${en ? 'Close' : 'Đóng'}">×</button></div>
    <div class="reader-setting-row"><span>${en ? 'Text size' : 'Cỡ chữ'}</span><div class="reader-controls"><button type="button" data-r-action="smaller">A−</button><button type="button" data-r-action="larger">A+</button></div></div>
    <div class="reader-setting-row"><span>${en ? 'Typeface' : 'Kiểu chữ'}</span><div class="reader-controls"><button type="button" data-r-font="literary">Serif</button><button type="button" data-r-font="system">Sans</button></div></div>
    <div class="reader-setting-row"><span>${en ? 'Leading' : 'Giãn dòng'}</span><div class="reader-controls"><button type="button" data-r-leading="1.68">${en ? 'Tight' : 'Gọn'}</button><button type="button" data-r-leading="1.78">${en ? 'Normal' : 'Chuẩn'}</button><button type="button" data-r-leading="1.92">${en ? 'Airy' : 'Thoáng'}</button></div></div>
    <div class="reader-setting-row"><span>${en ? 'Theme' : 'Nền'}</span><div class="reader-controls"><button type="button" data-r-theme="paper">${en ? 'Paper' : 'Giấy'}</button><button type="button" data-r-theme="sepia">Sepia</button><button type="button" data-r-theme="night">${en ? 'Night' : 'Đêm'}</button></div></div>
    <div class="reader-setting-row"><span>${en ? 'Reset' : 'Mặc định'}</span><div class="reader-controls"><button type="button" data-r-action="reset">${en ? 'Reset' : 'Đặt lại'}</button></div></div>`;
  document.body.append(panel);

  const refresh = () => {
    panel.querySelectorAll('[data-r-font]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.rFont === prefs.font)));
    panel.querySelectorAll('[data-r-theme]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.rTheme === prefs.theme)));
    panel.querySelectorAll('[data-r-leading]').forEach(b => b.setAttribute('aria-pressed', String(Math.abs(Number(b.dataset.rLeading) - Number(prefs.lineHeight)) < .03)));
    focus.setAttribute('aria-pressed', String(Boolean(prefs.focus)));
  };
  refresh();

  const openPanel = (open) => {
    panel.hidden = !open;
    settings.setAttribute('aria-expanded', String(open));
  };
  settings.addEventListener('click', () => openPanel(panel.hidden));
  panel.querySelector('.reader-panel-close')?.addEventListener('click', () => openPanel(false));
  panel.addEventListener('click', (event) => {
    const b = event.target.closest('button'); if (!b) return;
    if (b.dataset.rAction === 'smaller') prefs.size -= 1;
    if (b.dataset.rAction === 'larger') prefs.size += 1;
    if (b.dataset.rAction === 'reset') prefs = { ...defaults };
    if (b.dataset.rFont) prefs.font = b.dataset.rFont;
    if (b.dataset.rLeading) prefs.lineHeight = Number(b.dataset.rLeading);
    if (b.dataset.rTheme) prefs.theme = b.dataset.rTheme;
    apply(); save(); refresh(); updateProgress();
  });
  const themes = ['paper','sepia','night'];
  theme.addEventListener('click', () => {
    prefs.theme = themes[(themes.indexOf(prefs.theme) + 1) % themes.length];
    apply(); save(); refresh();
  });
  focus.addEventListener('click', () => {
    prefs.focus = !prefs.focus; apply(); save(); refresh(); updateProgress();
  });
  document.addEventListener('click', (event) => {
    if (!panel.hidden && !panel.contains(event.target) && !settings.contains(event.target)) openPanel(false);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !panel.hidden) openPanel(false);
  });

  function updateProgress(){
    const rect = surface.getBoundingClientRect();
    const start = window.scrollY + rect.top;
    const end = start + surface.offsetHeight - window.innerHeight;
    const ratio = end <= start ? 1 : clamp((window.scrollY - start) / (end - start), 0, 1);
    progressBar.style.width = `${(ratio * 100).toFixed(2)}%`;
    percent.textContent = `${Math.round(ratio * 100)}%`;
  }
  updateProgress();
  window.addEventListener('scroll', updateProgress, { passive:true });
  window.addEventListener('resize', updateProgress, { passive:true });
  if ('ResizeObserver' in window) new ResizeObserver(updateProgress).observe(surface);
  window.addEventListener('bl-reader-content-updated', updateProgress);
})();
