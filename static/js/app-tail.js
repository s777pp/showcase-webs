// app.html L5287-5522
(function(){
  var FUNPAY_URL = 'https://funpay.com/lots/offer?id=76420307';
  var TG_URL = 'https://t.me/SteamMakerBot';

  function i18nBuy(){
    var lang = (localStorage.getItem('sm_lang') || document.documentElement.lang || 'en').slice(0,2).toLowerCase();
    var ru = lang === 'ru';
    var t = document.getElementById('smBuyTitle');
    var s = document.getElementById('smBuySub');
    var fd = document.getElementById('smBuyFunpayD');
    var td = document.getElementById('smBuyTgD');
    var c = document.getElementById('smBuyClose');
    if (t) t.textContent = ru ? 'Купить Pro-ключ' : 'Buy Pro key';
    if (s) s.textContent = ru
      ? 'Выбери, где купить. После оплаты активируй код в аккаунте.'
      : 'Choose where to buy. After payment, activate the code in your account.';
    if (fd) fd.textContent = ru ? 'Код сразу после оплаты' : 'Instant code after payment';
    if (td) td.textContent = ru ? 'Через бота / поддержку' : 'Buy via bot / support';
    if (c) c.textContent = ru ? 'Закрыть' : 'Close';
  }

  window.openBuyKeyModal = function openBuyKeyModal(e){
    if (e && e.preventDefault) e.preventDefault();
    var ov = document.getElementById('smBuyOverlay');
    if (!ov) return;
    i18nBuy();
    var fp = document.getElementById('smBuyFunpay');
    var tg = document.getElementById('smBuyTg');
    if (fp) fp.href = FUNPAY_URL;
    if (tg) tg.href = TG_URL;
    ov.classList.add('open');
    ov.setAttribute('aria-hidden', 'false');
  };
  window.closeBuyKeyModal = function(){
    var ov = document.getElementById('smBuyOverlay');
    if (!ov) return;
    ov.classList.remove('open');
    ov.setAttribute('aria-hidden', 'true');
  };

  function bind(){
    var ov = document.getElementById('smBuyOverlay');
    if (!ov) return;
    var closeBtn = document.getElementById('smBuyClose');
    if (closeBtn) closeBtn.onclick = window.closeBuyKeyModal;
    ov.addEventListener('click', function(ev){
      if (ev.target === ov) window.closeBuyKeyModal();
    });
    document.addEventListener('keydown', function(ev){
      if (ev.key === 'Escape') window.closeBuyKeyModal();
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind);
  else bind();
})();



/* ---- Upscale ---- */
(function(){
  const btn = document.getElementById('btnUpscale');
  const drop = document.getElementById('upscaleDrop');
  const fileInp = document.getElementById('upscaleFile');
  const fileName = document.getElementById('upscaleFileName');
  const st = document.getElementById('upscaleStatus');
  const prev = document.getElementById('upscalePreview');
  const prog = document.getElementById('upscaleProg');
  const progLbl = document.getElementById('upscaleProgLabel');
  const lock = document.getElementById('upscaleLock');
  const panel = document.getElementById('upscalePanel');
  const buy = document.getElementById('upscaleBuyPro');
  if (!btn || !fileInp) return;

  let beforeUrl = null;
  let afterUrl = null;
  let selectedFile = null;

  function setProg(on, text){
    if (prog) prog.classList.toggle('on', !!on);
    if (progLbl) {
      progLbl.classList.toggle('on', !!on);
      if (text) progLbl.textContent = text;
    }
  }

  function isPro(){
    try {
      // refreshQuota stores nothing global — read badge
      const b = document.getElementById('planBadge');
      const t = (b && b.textContent || '').toLowerCase();
      return t === 'pro' || t === 'trial' || (b && b.classList.contains('pro'));
    } catch(e){ return false; }
  }

  function syncLock(){
    const pro = isPro();
    if (lock) lock.style.display = pro ? 'none' : 'flex';
    if (panel) panel.style.display = pro ? '' : 'none';
  }

  // re-check when quota refreshes
  const _rq = window.refreshQuota;
  if (typeof refreshQuota === 'function' && !refreshQuota._upscalePatched) {
    const orig = refreshQuota;
    window.refreshQuota = async function(){
      const r = await orig.apply(this, arguments);
      try { syncLock(); } catch(e){}
      return r;
    };
    window.refreshQuota._upscalePatched = true;
  }
  setTimeout(syncLock, 300);
  setInterval(syncLock, 4000);

  if (buy) {
    buy.onclick = function(){
      const b = document.getElementById('btnUpgrade');
      if (b) b.click();
      else if (typeof window.openBuyKeyModal === 'function') window.openBuyKeyModal();
      else location.href = '/#pricing';
    };
  }

  function setFile(f){
    if (!f) return;
    selectedFile = f;
    if (fileName) fileName.textContent = f.name + ' · ' + Math.round(f.size/1024) + ' KB';
    if (beforeUrl) URL.revokeObjectURL(beforeUrl);
    beforeUrl = URL.createObjectURL(f);
  }

  if (drop) {
    drop.addEventListener('click', () => fileInp.click());
    drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('drag'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('drag'));
    drop.addEventListener('drop', (e) => {
      e.preventDefault(); drop.classList.remove('drag');
      const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (f) setFile(f);
    });
  }
  fileInp.addEventListener('change', () => {
    const f = fileInp.files && fileInp.files[0];
    if (f) setFile(f);
  });

  // before/after slider
  const wrap = document.getElementById('upscaleCompare');
  const clip = document.getElementById('upscaleAfterClip');
  const handle = document.getElementById('upscaleHandle');
  const imgBefore = document.getElementById('upscaleBefore');
  const imgAfter = document.getElementById('upscaleAfter');

  function setSplit(pct){
    pct = Math.max(2, Math.min(98, pct));
    if (clip) clip.style.width = pct + '%';
    if (handle) handle.style.left = pct + '%';
  }
  function bindCompare(){
    if (!wrap) return;
    let drag = false;
    function pos(e){
      const r = wrap.getBoundingClientRect();
      const x = (e.touches ? e.touches[0].clientX : e.clientX) - r.left;
      setSplit((x / r.width) * 100);
    }
    wrap.addEventListener('pointerdown', (e) => { drag = true; wrap.setPointerCapture(e.pointerId); pos(e); });
    wrap.addEventListener('pointermove', (e) => { if (drag) pos(e); });
    wrap.addEventListener('pointerup', () => { drag = false; });
    wrap.addEventListener('pointercancel', () => { drag = false; });
  }
  bindCompare();
  setSplit(50);

  function fitAfterImage(){
    if (!imgBefore || !imgAfter || !wrap) return;
    // after image should match before display width
    const w = imgBefore.clientWidth || wrap.clientWidth;
    if (w > 0) {
      imgAfter.style.width = w + 'px';
      imgAfter.style.height = 'auto';
      imgAfter.style.maxWidth = 'none';
    }
  }
  if (imgBefore) imgBefore.addEventListener('load', fitAfterImage);
  if (imgAfter) imgAfter.addEventListener('load', fitAfterImage);
  window.addEventListener('resize', fitAfterImage);

  btn.addEventListener('click', async function(){
    if (!isPro()) { syncLock(); return; }
    const f = selectedFile || (fileInp.files && fileInp.files[0]);
    const model = document.getElementById('upscaleModel')?.value || '4xBHI_dat2_real';
    if (!f) { if (st) st.textContent = 'Выбери изображение'; return; }
    btn.disabled = true;
    if (st) st.textContent = '';
    if (prev) prev.style.display = 'none';
    setProg(true, 'Увеличение… обычно 1–3 минуты');
    try {
      if (!beforeUrl) beforeUrl = URL.createObjectURL(f);
      const fd = new FormData();
      fd.append('file', f);
      fd.append('model', model);
      const r = await fetch('/api/upscale', {
        method: 'POST', body: fd, credentials: 'include',
        headers: (typeof headers === 'function' ? headers() : {})
      });
      if (!r.ok) {
        let msg = 'Upscale failed';
        let code = '';
        try { const j = await r.json(); msg = j.msg || msg; code = j.code || ''; } catch(e){}
        if (code === 'pro' || r.status === 403) { syncLock(); }
        throw new Error(msg);
      }
      const blob = await r.blob();
      if (afterUrl) URL.revokeObjectURL(afterUrl);
      afterUrl = URL.createObjectURL(blob);
      if (imgBefore) imgBefore.src = beforeUrl;
      if (imgAfter) imgAfter.src = afterUrl;
      const dl = document.getElementById('upscaleDownload');
      if (dl) { dl.href = afterUrl; dl.download = 'upscaled_' + model + '.png'; }
      if (prev) prev.style.display = 'block';
      setSplit(50);
      setTimeout(fitAfterImage, 50);
      if (st) st.textContent = 'Готово — двигай ползунок, чтобы сравнить до/после';
    } catch (e) {
      if (st) st.textContent = String(e.message || e);
    } finally {
      setProg(false);
      btn.disabled = false;
    }
  });
})();
// app.html L5524-5819  id="sm-modern-upload-nav-js"
(function(){
  'use strict';

  const $ = (sel, root=document) => root.querySelector(sel);
  const $$ = (sel, root=document) => Array.from(root.querySelectorAll(sel));

  function formatBytes(bytes){
    if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
    const units = ['B','KB','MB','GB'];
    const i = Math.min(Math.floor(Math.log(bytes)/Math.log(1024)), units.length-1);
    return (bytes/Math.pow(1024,i)).toFixed(i ? 2 : 0) + ' ' + units[i];
  }

  function prettyType(file){
    if (!file) return 'file';
    if (file.type) return file.type;
    const n=(file.name||'').toLowerCase();
    const m=n.match(/\.([a-z0-9]+)$/);
    return m ? m[1].toUpperCase() : 'file';
  }

  function fileMeta(files){
    const arr=Array.from(files||[]);
    if (!arr.length) return '';
    const items=arr.slice(0,4).map(f=>{
      const modified = f.lastModified ? new Date(f.lastModified).toLocaleDateString() : '—';
      return '<div class="sm-upload-file-card">' +
        '<div class="sm-upload-file-name">' + escapeHtml(f.name || 'file') + '</div>' +
        '<div class="sm-upload-file-size">' + formatBytes(f.size) + '</div>' +
        '<div class="sm-upload-file-info"><span><strong>Type</strong> ' + escapeHtml(prettyType(f)) + '</span><span><strong>Modified</strong> ' + escapeHtml(modified) + '</span></div>' +
      '</div>';
    }).join('');
    if (arr.length > 4) {
      return items + '<div style="margin-top:7px;color:rgba(255,255,255,.4);font-size:10px">+' + (arr.length-4) + ' more file(s)</div>';
    }
    return items;
  }

  function escapeHtml(s){
    return String(s).replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#039;','"':'&quot;'}[ch]));
  }

  function ensureSurfaceContents(surface, multi){
    if (surface.querySelector('.sm-upload-content')) return surface.querySelector('.sm-upload-content');
    const content=document.createElement('div');
    content.className='sm-upload-content';
    content.innerHTML =
      '<div class="sm-upload-icon-wrap" aria-hidden="true">' +
        '<svg class="sm-upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' +
          '<path d="M12 16V4"/><path d="m7 9 5-5 5 5"/><path d="M5 20h14"/>' +
        '</svg>' +
      '</div>' +
      '<div class="sm-upload-title">Upload file</div>' +
      '<div class="sm-upload-subtitle">Drag or drop your ' + (multi ? 'files' : 'file') + ' here or click to upload</div>' +
      '<div class="sm-upload-meta"><span>Drag &amp; drop</span><span>Browse</span></div>';
    surface.appendChild(content);
    return content;
  }

  function setSurfaceText(surface, fileCount, custom){
    const title=$('.sm-upload-title', surface);
    const sub=$('.sm-upload-subtitle', surface);
    const meta=$('.sm-upload-meta', surface);
    if (!title || !sub) return;
    const ru = (localStorage.getItem('sm_lang') || 'en') === 'ru';
    if (!fileCount) {
      title.textContent = ru ? 'Загрузить файл' : 'Upload file';
      sub.textContent = custom || (ru ? 'Перетащи файл сюда или нажми для выбора' : 'Drag or drop your files here or click to upload');
      if (meta) meta.innerHTML=ru ? '<span>Перетащить</span><span>Выбрать</span>' : '<span>Drag & drop</span><span>Browse</span>';
      return;
    }
    title.textContent = ru
      ? (fileCount === 1 ? 'Выбран 1 файл' : 'Выбрано файлов: ' + fileCount)
      : (fileCount === 1 ? '1 file selected' : fileCount + ' files selected');
    sub.textContent = ru ? 'Перетащи ещё файлы сюда или нажми, чтобы выбрать' : 'Drop more files here or click to replace / add';
    if (meta) meta.innerHTML=ru ? '<span>Готово</span><span>' + fileCount + (fileCount===1?' файл':' файла(ов)') + '</span>' : '<span>Ready</span><span>' + fileCount + (fileCount===1?' item':' items') + '</span>';
  }

  function addSelectionPanel(surface){
    if (surface.querySelector('.sm-upload-selection')) return;
    const panel=document.createElement('div');
    panel.className='sm-upload-selection';
    panel.setAttribute('aria-live','polite');
    const content=surface.querySelector('.sm-upload-content');
    if (content) content.appendChild(panel); else surface.appendChild(panel);
  }

  function showFiles(surface, files){
    const arr=Array.from(files||[]);
    addSelectionPanel(surface);
    const panel=surface.querySelector('.sm-upload-selection');
    if (!panel) return;
    if (!arr.length) {
      panel.classList.remove('show');
      panel.innerHTML='';
      setSurfaceText(surface, 0);
      return;
    }
    panel.innerHTML=fileMeta(arr);
    panel.classList.add('show');
    setSurfaceText(surface, arr.length);
  }

  function enhanceDropSurface(surface, input){
    if (!surface || surface.dataset.smEnhanced === '1') return;
    surface.dataset.smEnhanced='1';
    surface.classList.add('sm-upload-surface');
    // Existing drop zones contain a legacy text node. Remove only bare text nodes so
    // the new upload UI does not show duplicate instructions.
    Array.from(surface.childNodes).forEach(node => {
      if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()) node.remove();
    });
    ensureSurfaceContents(surface, !!input?.multiple);

    // Existing app handlers remain responsible for actually accepting files.
    // We only add visual state, preventing duplicate upload logic.
    surface.addEventListener('dragenter', e=>{ e.preventDefault(); surface.classList.add('drag'); });
    surface.addEventListener('dragover', e=>{ e.preventDefault(); surface.classList.add('drag'); });
    surface.addEventListener('dragleave', ()=>surface.classList.remove('drag'));
    surface.addEventListener('drop', e=>{
      surface.classList.remove('drag');
      if (e.dataTransfer?.files?.length) showFiles(surface, e.dataTransfer.files);
    });
    if (input) {
      input.addEventListener('change', ()=>showFiles(surface, input.files));
    }
  }

  function enhanceCompactChooser(fi, input){
    if (!fi || !input || fi.dataset.smEnhanced==='1') return;
    fi.dataset.smEnhanced='1';
    fi.classList.add('sm-file-chooser');
    const first=fi.querySelector('span');
    if (first && !first.closest('.sm-file-caption')) {
      const caption=document.createElement('span');
      caption.className='sm-file-caption';
      caption.appendChild(first);
      fi.insertBefore(caption, fi.firstChild);
    }
    fi.addEventListener('dragenter', e=>{e.preventDefault();fi.classList.add('drag');});
    fi.addEventListener('dragover', e=>{e.preventDefault();fi.classList.add('drag');});
    fi.addEventListener('dragleave', e=>{if(e.target===fi || !fi.contains(e.relatedTarget))fi.classList.remove('drag');});
    fi.addEventListener('drop', e=>{
      e.preventDefault();fi.classList.remove('drag');
      const files=e.dataTransfer?.files;
      if (!files?.length) return;
      try {
        const dt=new DataTransfer();
        dt.items.add(files[0]);
        input.files=dt.files;
        input.dispatchEvent(new Event('change',{bubbles:true}));
      } catch(_) {
        // Browser may disallow programmatic FileList assignment; user can still click Choose.
      }
    });
  }

  function enhanceHiddenPicker(input){
    if (!input || input.dataset.smEnhanced==='1') return;
    if (input.type !== 'file') return;
    if (input.closest('.drop,.sm-upload-surface,.fi.sm-file-chooser')) return;

    // These hidden inputs are already controlled by their dedicated large drop surface.
    // Do NOT insert a second upload component next to them.
    const pairedDropIds = {
      fileInput: 'drop',
      cvInput: 'cvDrop',
      hexInput: 'hexDrop',
      upscaleFile: 'upscaleDrop'
    };
    if (pairedDropIds[input.id]) {
      const existing = document.getElementById(pairedDropIds[input.id]);
      if (existing) return;
    }

    const parent=input.parentElement;
    if (!parent) return;

    // Special standalone preview avatar and dynamic picker rows keep their existing buttons.
    const row=input.closest('.fi');
    if (row) {
      enhanceCompactChooser(row,input);
      return;
    }

    // For completely hidden inputs create a visually consistent mini dropzone immediately before it.
    const surface=document.createElement('div');
    surface.className='sm-upload-surface sm-upload-mini';
    surface.setAttribute('role','button');
    surface.setAttribute('tabindex','0');
    surface.setAttribute('aria-label','Upload file');
    ensureSurfaceContents(surface, !!input.multiple);
    parent.insertBefore(surface,input);
    input.dataset.smEnhanced='1';
    surface.addEventListener('click',()=>input.click());
    surface.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();input.click();}});
    surface.addEventListener('dragenter',e=>{e.preventDefault();surface.classList.add('drag');});
    surface.addEventListener('dragover',e=>{e.preventDefault();surface.classList.add('drag');});
    surface.addEventListener('dragleave',()=>surface.classList.remove('drag'));
    surface.addEventListener('drop',e=>{
      e.preventDefault();surface.classList.remove('drag');
      const files=e.dataTransfer?.files;
      if(!files?.length)return;
      try{
        const dt=new DataTransfer();
        Array.from(files).slice(0,input.multiple?files.length:1).forEach(f=>dt.items.add(f));
        input.files=dt.files;
        input.dispatchEvent(new Event('change',{bubbles:true}));
      }catch(_){showFiles(surface,files);}
    });
    input.addEventListener('change',()=>showFiles(surface,input.files));
  }

  function refreshUploads(root=document){
    // Existing large dropzones are upgraded in place.
    $$('.drop', root).forEach(drop=>{
      const inputId={
        '#drop':'fileInput','#cvDrop':'cvInput','#hexDrop':'hexInput','#upscaleDrop':'upscaleFile'
      }['#'+drop.id];
      const input=inputId ? document.getElementById(inputId) : null;
      enhanceDropSurface(drop,input);
    });

    // The two Character + BG inputs are compact choosers.
    ['composeBg','composeChar'].forEach(id=>{
      const input=document.getElementById(id);
      if(input) enhanceCompactChooser(input.closest('.fi'),input);
    });

    $$('input[type="file"]', root).forEach(enhanceHiddenPicker);
  }

  /* ---------- Animated navbar indicator (Aceternity-like shared layout state) ---------- */
  function setupNav(){
    const nav=document.getElementById('nav');
    if(!nav || nav.querySelector('.sm-nav-indicator')) return;
    const indicator=document.createElement('div');
    indicator.className='sm-nav-indicator';
    nav.insertBefore(indicator,nav.firstChild);

    const buttons=()=>$$(':scope > button[data-tab]',nav);
    function moveTo(btn,visible=true){
      if(!btn)return;
      const nr=nav.getBoundingClientRect();
      const br=btn.getBoundingClientRect();
      indicator.style.width=br.width+'px';
      indicator.style.transform='translate3d('+(br.left-nr.left)+'px,0,0) scale(1)';
      indicator.classList.toggle('is-visible',visible);
    }
    function moveToActive(){
      const active=nav.querySelector(':scope > button.active') || buttons()[0];
      moveTo(active,!!active);
    }
    buttons().forEach(btn=>{
      btn.addEventListener('mouseenter',()=>moveTo(btn,true));
      btn.addEventListener('focus',()=>moveTo(btn,true));
      btn.addEventListener('mouseleave',moveToActive);
      btn.addEventListener('blur',moveToActive);
    });
    nav.addEventListener('mouseleave',moveToActive);
    window.addEventListener('resize',moveToActive,{passive:true});
    document.addEventListener('click',e=>{
      const btn=e.target?.closest?.('#nav > button[data-tab]');
      if(btn) setTimeout(moveToActive,0);
    });
    moveToActive();
  }

  // Existing preview slot code creates new .fi + input dynamically. Observe those nodes so
  // the same visual component appears there without changing the preview logic.
  function setupObserver(){
    const root=document.body;
    if(!root || window.__smModernObserver) return;
    const mo=new MutationObserver(mutations=>{
      let added=false;
      for(const m of mutations){ if(m.addedNodes?.length){ added=true; break; } }
      if(added) refreshUploads();
    });
    mo.observe(root,{childList:true,subtree:true});
    window.__smModernObserver=mo;
  }

  function start(){
    refreshUploads();
    setupNav();
    setupObserver();
    // Existing localized text can be applied after our mount; re-run visual enhancement safely.
    setTimeout(refreshUploads,200);
    setTimeout(refreshUploads,900);
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start);
  else start();
})();
