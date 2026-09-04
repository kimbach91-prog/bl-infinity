(() => {
  const $ = (s, root=document) => root.querySelector(s);
  const $$ = (s, root=document) => [...root.querySelectorAll(s)];
  const storeKey = 'kevin-intellectual-map-v1';
  const speechKey = 'kevin-intellectual-map-speech-v1';
  const state = { query:'', tag:'all', works:[], speechBlocks:[], speaking:false, paused:false, currentBlock:0, currentChunk:0, chunks:[], wakeLock:null };
  let prefs = { resumeRatio:0, bookmarkRatio:null, careReminder:true };
  let speechPrefs = { rate:0.96, pitch:1, voiceURI:'' };
  try { prefs = { ...prefs, ...JSON.parse(localStorage.getItem(storeKey) || '{}') }; } catch(_) {}
  try { speechPrefs = { ...speechPrefs, ...JSON.parse(localStorage.getItem(speechKey) || '{}') }; } catch(_) {}
  const save = () => { try { localStorage.setItem(storeKey, JSON.stringify(prefs)); } catch(_) {} };
  const saveSpeech = () => { try { localStorage.setItem(speechKey, JSON.stringify(speechPrefs)); } catch(_) {} };
  const clamp = (v,a,b) => Math.max(a,Math.min(b,v));

  const toast = (text, ms=3200) => {
    let node = $('.kevin-toast');
    if (!node){ node=document.createElement('div'); node.className='kevin-toast'; document.body.append(node); }
    node.textContent=text; node.classList.add('show');
    clearTimeout(toast._t); toast._t=setTimeout(()=>node.classList.remove('show'),ms);
  };

  const safeFetchText = async (url) => {
    const r = await fetch(url, {cache:'no-cache'});
    if (!r.ok) throw new Error(`${url}: ${r.status}`);
    return r.text();
  };
  const safeFetchJSON = async (url) => {
    const r = await fetch(url, {cache:'no-cache'});
    if (!r.ok) throw new Error(`${url}: ${r.status}`);
    return r.json();
  };

  function renderRanking(works){
    const mount = $('#rankingMount');
    if (!mount) return;
    const tags = ['all','frame','epistemology','systems','ai','reasoning','mechanism','cognition','causality','memory','verification','cycles','ontology'];
    mount.innerHTML = `
      <section class="kevin-ranking" aria-labelledby="thu-vien-100">
        <div class="kevin-ranking-head">
          <p class="eyebrow">THƯ VIỆN ĐỐI SÁNH · 100 CÔNG TRÌNH</p>
          <h2 id="thu-vien-100">100 công trình, từ gần nhất đến xa nhất</h2>
          <p>Điểm 0–100 là heuristic biên tập để điều hướng, không phải metric khoa học và không suy ra ảnh hưởng hay sao chép. Hãy dùng nó như bản đồ đọc.</p>
        </div>
        <div class="kevin-filterbar reader-chrome" data-skip-speech>
          <input class="kevin-search" id="workSearch" type="search" autocomplete="off" placeholder="Tìm theo tác giả, tên, cơ chế, frame, AI, memory…" aria-label="Tìm trong 100 công trình">
          <div class="kevin-chiprow" id="tagChips">${tags.map(t=>`<button class="kevin-chip" type="button" data-tag="${t}" aria-pressed="${t==='all'}">${t==='all'?'Tất cả':t}</button>`).join('')}</div>
          <div id="resultCount" style="font-size:.69rem;color:var(--reader-muted);padding-top:4px">100/100 công trình</div>
        </div>
        <ol class="kevin-worklist" id="workList">
          ${works.map(w=>`
          <li class="kevin-work" data-rank="${w.rank}" data-tags="${w.tags.join(' ')}" data-search="${escAttr(`${w.title} ${w.author} ${w.year} ${w.tags.join(' ')} ${w.similarity}`.toLowerCase())}">
            <div class="kevin-rank">#${String(w.rank).padStart(2,'0')}</div>
            <div>
              <h3>${escHTML(w.title)}</h3>
              <p class="by">${escHTML(w.author)} · ${escHTML(w.year)}</p>
              <p class="sim">${escHTML(w.similarity)}</p>
              <div class="kevin-tags">${w.tags.map(t=>`<span>${escHTML(t)}</span>`).join('')}</div>
            </div>
            <div class="kevin-score"><b>${w.score}</b>/100<span class="kevin-band">${escHTML(w.band)}</span></div>
          </li>`).join('')}
        </ol>
        <div class="kevin-empty" id="workEmpty" hidden>Không có mục khớp bộ lọc hiện tại.</div>
      </section>`;
    state.works = works;
    $('#workSearch')?.addEventListener('input', e => { state.query=e.target.value.trim().toLowerCase(); filterWorks(); });
    $$('#tagChips .kevin-chip').forEach(btn => btn.addEventListener('click',()=>{
      state.tag = btn.dataset.tag || 'all';
      $$('#tagChips .kevin-chip').forEach(b=>b.setAttribute('aria-pressed', String(b===btn)));
      filterWorks();
    }));
  }

  function filterWorks(){
    const items = $$('.kevin-work');
    let visible=0;
    items.forEach(item=>{
      const tagOK = state.tag==='all' || (item.dataset.tags||'').split(' ').includes(state.tag);
      const queryOK = !state.query || (item.dataset.search||'').includes(state.query);
      const show = tagOK && queryOK;
      item.hidden=!show; if(show) visible++;
    });
    const count=$('#resultCount'); if(count) count.textContent=`${visible}/${items.length} công trình`;
    const empty=$('#workEmpty'); if(empty) empty.hidden=visible>0;
    window.dispatchEvent(new Event('bl-reader-content-updated'));
    refreshSpeechBlocks();
  }

  const escHTML = (s='') => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const escAttr = (s='') => escHTML(s).replace(/\n/g,' ');

  function renderMonograph(md){
    const target=$('#monograph');
    if(!target || !window.BLReaderMarkdown) return;
    const rendered=window.BLReaderMarkdown.render(md,{skipH1:true});
    target.innerHTML=rendered.html;
  }

  function buildTOC(){
    const headings = $$('#monograph h2,#monograph h3,#thu-vien-100');
    const tocTargets = [$('#desktopToc'),$('#mobileToc')].filter(Boolean);
    tocTargets.forEach(t=>t.innerHTML='');
    headings.forEach((h,i)=>{
      if(!h.id) h.id=`kevin-section-${i+1}`;
      tocTargets.forEach(t=>{
        const a=document.createElement('a');
        a.href=`#${h.id}`; a.textContent=h.textContent;
        if(h.tagName==='H3') a.style.paddingLeft='20px';
        t.append(a);
      });
    });
    const links = tocTargets.flatMap(t=>$$('a',t));
    if('IntersectionObserver' in window){
      const obs=new IntersectionObserver(entries=>{
        const visible=entries.filter(e=>e.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top)[0];
        if(!visible) return;
        links.forEach(a=>a.setAttribute('aria-current',String(a.getAttribute('href')===`#${visible.target.id}`)));
        const current=$('#currentChapter'); if(current) current.textContent=visible.target.textContent.replace(/^Chương\s+\d+\.\s*/i,'').slice(0,50);
      },{rootMargin:'-8% 0px -78% 0px',threshold:[0,1]});
      headings.forEach(h=>obs.observe(h));
    }
  }

  function readingStats(){
    const surface=$('[data-reader-surface]'); if(!surface) return;
    const words=(surface.innerText.match(/\S+/g)||[]).length;
    const totalMin=Math.max(1,Math.round(words/220));
    const total=$('#totalReadTime'); if(total) total.textContent=`${totalMin} phút`;
    const wc=$('#wordCount'); if(wc) wc.textContent=Intl.NumberFormat('vi-VN').format(words);
    updateRemaining();
  }

  function updateRemaining(){
    const surface=$('[data-reader-surface]'); if(!surface) return;
    const rect=surface.getBoundingClientRect();
    const start=window.scrollY+rect.top;
    const end=start+surface.offsetHeight-window.innerHeight;
    const ratio=end<=start?1:clamp((window.scrollY-start)/(end-start),0,1);
    prefs.resumeRatio=ratio; save();
    const words=(surface.innerText.match(/\S+/g)||[]).length;
    const remaining=Math.max(0,Math.ceil((words*(1-ratio))/220));
    const node=$('#remainingReadTime'); if(node) node.textContent=`${remaining} phút`;
    const resume=$('#resumeButton'); if(resume){ resume.textContent=`Tiếp tục từ ${Math.round((prefs.resumeRatio||0)*100)}%`; resume.disabled=(prefs.resumeRatio||0)<.02; }
  }

  let scrollTimer;
  window.addEventListener('scroll',()=>{ clearTimeout(scrollTimer); scrollTimer=setTimeout(updateRemaining,120); },{passive:true});

  function scrollToRatio(ratio){
    const surface=$('[data-reader-surface]'); if(!surface) return;
    const rect=surface.getBoundingClientRect();
    const start=window.scrollY+rect.top;
    const end=start+surface.offsetHeight-window.innerHeight;
    window.scrollTo({top:start+(end-start)*clamp(Number(ratio)||0,0,1),behavior:'smooth'});
  }

  function wireRoutes(){
    $('#resumeButton')?.addEventListener('click',()=>scrollToRatio(prefs.resumeRatio||0));
    $('#bookmarkButton')?.addEventListener('click',()=>{ prefs.bookmarkRatio=prefs.resumeRatio||0; save(); toast(`Đã đánh dấu tại ${Math.round((prefs.bookmarkRatio||0)*100)}%`); });
    $('#goBookmark')?.addEventListener('click',()=>{
      if(prefs.bookmarkRatio==null) return toast('Chưa có dấu đọc cá nhân.');
      scrollToRatio(prefs.bookmarkRatio);
    });
    $$('.kevin-route button').forEach(btn=>btn.addEventListener('click',()=>{
      const phrase=btn.dataset.find||'';
      const h=$$('#monograph h2,#monograph h3,#thu-vien-100').find(x=>x.textContent.toLowerCase().includes(phrase.toLowerCase()));
      if(h){ h.scrollIntoView({behavior:'smooth',block:'start'}); toast(btn.dataset.note||`Mở: ${h.textContent}`); }
    }));
  }

  /* Vietnamese speech reader */
  const synth = 'speechSynthesis' in window ? window.speechSynthesis : null;
  let voices=[];
  function voiceScore(v){
    const lang=(v.lang||'').toLowerCase(), name=(v.name||'').toLowerCase();
    let s=0;
    if(lang==='vi-vn') s+=120; else if(lang.startsWith('vi')) s+=100;
    if(/natural|neural|online/.test(name)) s+=35;
    if(/hoai.?my|nam.?minh/.test(name)) s+=28;
    if(/microsoft/.test(name)) s+=16;
    if(/google/.test(name)) s+=12;
    if(v.localService) s+=3;
    return s;
  }
  function loadVoices(){
    if(!synth) return;
    voices=synth.getVoices().slice().sort((a,b)=>voiceScore(b)-voiceScore(a)||a.name.localeCompare(b.name));
    const sel=$('#voiceSelect'); if(!sel) return;
    const current=speechPrefs.voiceURI;
    sel.innerHTML='';
    voices.forEach(v=>{
      const o=document.createElement('option'); o.value=v.voiceURI; o.textContent=`${v.name} · ${v.lang}${voiceScore(v)>=100?' · ưu tiên Việt':''}`; sel.append(o);
    });
    const chosen=voices.find(v=>v.voiceURI===current)||voices[0];
    if(chosen){ sel.value=chosen.voiceURI; speechPrefs.voiceURI=chosen.voiceURI; saveSpeech(); }
    const note=$('#voiceAvailability');
    if(note){
      const vi=voices.filter(v=>(v.lang||'').toLowerCase().startsWith('vi'));
      note.textContent=vi.length ? `Thiết bị có ${vi.length} giọng tiếng Việt. Trình đọc đã ưu tiên giọng tự nhiên nhất có sẵn.` : 'Thiết bị chưa báo giọng vi-VN. Có thể cài thêm Vietnamese voice trong hệ điều hành hoặc chọn một voice khác.';
    }
  }
  if(synth){ loadVoices(); window.speechSynthesis.onvoiceschanged=loadVoices; }

  function refreshSpeechBlocks(){
    const blocks=[...$$('#monograph h2,#monograph h3,#monograph p,#monograph li'),...$$('#workList .kevin-work:not([hidden])')]
      .filter(el=>!el.closest('[data-skip-speech]'))
      .map(el=>({el,text:el.innerText.replace(/\s+/g,' ').trim()}))
      .filter(x=>x.text.length>2);
    state.speechBlocks=blocks;
  }
  function splitText(text,max=560){
    const sentences=(text.match(/[^.!?…]+[.!?…]?/g)||[text]).map(s=>s.trim()).filter(Boolean);
    const out=[]; let buf='';
    sentences.forEach(s=>{
      if((buf+' '+s).trim().length<=max){ buf=(buf+' '+s).trim(); return; }
      if(buf) out.push(buf); buf='';
      if(s.length<=max){ buf=s; return; }
      const words=s.split(/\s+/); let part='';
      words.forEach(w=>{ if((part+' '+w).trim().length>max){ if(part) out.push(part); part=w; } else part=(part+' '+w).trim(); });
      if(part) buf=part;
    });
    if(buf) out.push(buf); return out;
  }
  function selectedVoice(){ return voices.find(v=>v.voiceURI===speechPrefs.voiceURI)||voices[0]||null; }
  function nearestSpeechBlock(){
    if(!state.speechBlocks.length) return 0;
    let best=0, bestDist=Infinity;
    state.speechBlocks.forEach((b,i)=>{ const r=b.el.getBoundingClientRect(); const d=Math.abs(r.top-window.innerHeight*.28); if(d<bestDist){bestDist=d;best=i;} });
    return best;
  }
  async function requestWakeLock(){
    try{ if('wakeLock' in navigator && !state.wakeLock) state.wakeLock=await navigator.wakeLock.request('screen'); }catch(_){}
  }
  async function releaseWakeLock(){ try{ if(state.wakeLock){ await state.wakeLock.release(); state.wakeLock=null; } }catch(_){} }
  function clearSpeakingClass(){ $$('.tts-current').forEach(e=>e.classList.remove('tts-current')); }
  function setAudioStatus(text){ const s=$('#audioStatus'); if(s) s.textContent=text; }

  function speakCurrent(){
    if(!synth || !state.speaking) return;
    if(state.currentBlock>=state.speechBlocks.length){ stopSpeech('Đã đọc hết'); return; }
    const block=state.speechBlocks[state.currentBlock];
    if(!state.chunks.length) state.chunks=splitText(block.text);
    if(state.currentChunk>=state.chunks.length){ state.currentBlock++; state.currentChunk=0; state.chunks=[]; return speakCurrent(); }
    clearSpeakingClass(); block.el.classList.add('tts-current');
    const text=state.chunks[state.currentChunk];
    const u=new SpeechSynthesisUtterance(text);
    const v=selectedVoice(); if(v) u.voice=v;
    u.lang=v?.lang || 'vi-VN'; u.rate=clamp(Number(speechPrefs.rate)||.96,.72,1.35); u.pitch=clamp(Number(speechPrefs.pitch)||1,.7,1.3);
    u.onstart=()=>{
      setAudioStatus(`Đang đọc ${state.currentBlock+1}/${state.speechBlocks.length}`);
      if(!matchMedia('(prefers-reduced-motion: reduce)').matches) block.el.scrollIntoView({behavior:'smooth',block:'center'});
    };
    u.onend=()=>{ if(!state.speaking) return; state.currentChunk++; speakCurrent(); };
    u.onerror=e=>{ if(e.error==='interrupted'||e.error==='canceled') return; state.currentChunk++; speakCurrent(); };
    synth.speak(u);
  }
  function startSpeech(fromVisible=true){
    if(!synth) return toast('Trình duyệt này không hỗ trợ SpeechSynthesis.');
    refreshSpeechBlocks(); if(!state.speechBlocks.length) return;
    if(state.paused){ synth.resume(); state.paused=false; state.speaking=true; setAudioStatus('Tiếp tục đọc'); requestWakeLock(); return; }
    synth.cancel(); state.speaking=true; state.paused=false; state.currentBlock=fromVisible?nearestSpeechBlock():0; state.currentChunk=0; state.chunks=[];
    requestWakeLock(); speakCurrent();
  }
  function pauseSpeech(){ if(!synth||!state.speaking) return; synth.pause(); state.paused=true; setAudioStatus('Tạm dừng'); releaseWakeLock(); }
  function stopSpeech(label='Đã dừng'){
    if(synth) synth.cancel(); state.speaking=false; state.paused=false; state.currentChunk=0; state.chunks=[]; clearSpeakingClass(); setAudioStatus(label); releaseWakeLock();
  }
  function previewVoice(){
    if(!synth) return;
    synth.cancel(); const u=new SpeechSynthesisUtterance('Kevin, đây là chế độ đọc sách tiếng Việt. Bạn có thể đổi giọng và tốc độ bất cứ lúc nào.');
    const v=selectedVoice(); if(v) u.voice=v; u.lang=v?.lang||'vi-VN'; u.rate=Number(speechPrefs.rate)||.96; u.pitch=Number(speechPrefs.pitch)||1; synth.speak(u);
  }
  function readSelection(){
    const text=(window.getSelection()?.toString()||'').trim();
    if(text.length<3) return toast('Hãy bôi đen một đoạn rồi chọn “Đọc đoạn chọn”.');
    if(!synth) return;
    stopSpeech('Đọc đoạn chọn');
    const pieces=splitText(text); let i=0;
    const next=()=>{ if(i>=pieces.length) return setAudioStatus('Đã đọc đoạn chọn'); const u=new SpeechSynthesisUtterance(pieces[i++]); const v=selectedVoice(); if(v)u.voice=v; u.lang=v?.lang||'vi-VN'; u.rate=Number(speechPrefs.rate)||.96; u.pitch=Number(speechPrefs.pitch)||1; u.onend=next; synth.speak(u); };
    next();
  }

  function mountAudio(){
    const dock=$('#audioDock'), panel=$('#audioPanel');
    if(!dock||!panel) return;
    if(!synth){ dock.querySelectorAll('button').forEach(b=>b.disabled=true); setAudioStatus('Không có TTS'); return; }
    $('#audioPlay')?.addEventListener('click',()=>startSpeech(true));
    $('#audioPause')?.addEventListener('click',pauseSpeech);
    $('#audioStop')?.addEventListener('click',()=>stopSpeech());
    $('#audioSettings')?.addEventListener('click',()=>{ panel.hidden=!panel.hidden; });
    $('#audioClose')?.addEventListener('click',()=>panel.hidden=true);
    $('#audioStartTop')?.addEventListener('click',()=>startSpeech(false));
    $('#audioStartHere')?.addEventListener('click',()=>startSpeech(true));
    $('#audioPreview')?.addEventListener('click',previewVoice);
    $('#audioSelection')?.addEventListener('click',readSelection);
    $('#voiceSelect')?.addEventListener('change',e=>{ speechPrefs.voiceURI=e.target.value; saveSpeech(); });
    const rate=$('#speechRate'), rateLabel=$('#speechRateLabel');
    if(rate){ rate.value=String(speechPrefs.rate); if(rateLabel) rateLabel.textContent=`${Number(speechPrefs.rate).toFixed(2)}×`; rate.addEventListener('input',e=>{ speechPrefs.rate=Number(e.target.value); if(rateLabel) rateLabel.textContent=`${speechPrefs.rate.toFixed(2)}×`; saveSpeech(); }); }
    const care=$('#careReminder'); if(care){ care.checked=Boolean(prefs.careReminder); care.addEventListener('change',e=>{prefs.careReminder=e.target.checked;save();scheduleCare();}); }
    document.addEventListener('visibilitychange',()=>{ if(document.hidden && state.speaking && !state.paused) setAudioStatus('Đang đọc nền'); });
    window.addEventListener('beforeunload',()=>{ if(synth) synth.cancel(); releaseWakeLock(); });
  }

  let careTimer;
  function scheduleCare(){
    clearTimeout(careTimer);
    if(!prefs.careReminder) return;
    careTimer=setTimeout(()=>{ toast('Bạn đã đọc khá lâu. Nếu mắt mỏi, nghỉ nhìn xa khoảng 2 phút rồi quay lại đúng vị trí đã lưu.',7000); scheduleCare(); },25*60*1000);
  }

  function addSourceLinks(){
    const links=[
      ['First Brain','https://github.com/jkdkr2439/first-brain-pandas','frame · mechanism · source map'],
      ['Structured Reasoning','https://github.com/jkdkr2439/Structured_Reasoning','S/M/Q/R · benchmark'],
      ['CRIO','https://github.com/jkdkr2439/CRIO','repair · negative result · audit'],
      ['DCIP-AI','https://github.com/jkdkr2439/DCIP-AI','bounded systems · batching'],
      ['Spatial Box','https://github.com/jkdkr2439/A-Spatial-Operational-Box','license · verifier · fail-closed'],
      ['Memory-Gravity','https://github.com/jkdkr2439/Memory-Gravity-Attention','persistent importance · memory']
    ];
    const strip=$('#sourceStrip'); if(!strip)return;
    strip.innerHTML=links.map(([t,u,s])=>`<a href="${u}" target="_blank" rel="noreferrer noopener">${t}<span>${s}</span></a>`).join('');
  }

  async function init(){
    try{
      const [md,works]=await Promise.all([safeFetchText('monograph.md'),safeFetchJSON('works.json')]);
      renderMonograph(md); renderRanking(works); addSourceLinks(); buildTOC(); wireRoutes(); refreshSpeechBlocks(); readingStats(); mountAudio(); scheduleCare();
      const loading=$('#loadingState'); if(loading) loading.remove();
      window.dispatchEvent(new Event('bl-reader-content-updated'));
      if(location.hash){ const el=$(location.hash); if(el) setTimeout(()=>el.scrollIntoView({block:'start'}),80); }
      else if((prefs.resumeRatio||0)>.04) toast(`Đã nhớ vị trí đọc ${Math.round(prefs.resumeRatio*100)}%. Nút “Tiếp tục” nằm trong mục lục.`);
    }catch(err){
      console.error(err); const l=$('#loadingState'); if(l) l.textContent='Không tải được nội dung. Hãy thử tải lại trang.';
    }
  }
  init();
})();