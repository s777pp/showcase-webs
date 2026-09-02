// app.html L1585-3215
const state = {
  mode: 'workshop', files: [],
  token: localStorage.getItem('sm_token') || '',
  session: localStorage.getItem('sm_session') || '',
  authMode: 'login'
};
window.state = state;
const titles = {
  process:['Process','Workshop / Featured / Split cuts, watermark and Steam ZIP'],
  compose:['Character + BG','Composite character on background, then send to Process'],
  download:['Download','Sources from YouTube, TikTok, X, Reddit and Pinterest'],
  preview:['Preview','How the showcase looks on a Steam profile'],
  steam:['Steam','Guide and console code for artwork upload'],
  da:['DeviantArt','Publishing — desktop version'],
  account:['Account','Sign up, log in and buy Pro'],
  about:['About','Limits, Pro and contacts']
};
function headers() {
  // re-read every time so navigation/home→tools keeps login
  state.session = localStorage.getItem('sm_session') || state.session || '';
  state.token = localStorage.getItem('sm_token') || state.token || '';
  const h = {};
  if (state.token) h['X-Access-Token'] = state.token;
  if (state.session) h['X-Session-Token'] = state.session;
  return h;
}
const fetchOpts = { credentials: 'include' };

let _trialEndsAt = null;
let _trialTick = null;

function fmtTrial(sec) {
  sec = Math.max(0, Math.floor(sec));
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  const pad = (n) => String(n).padStart(2, '0');
  return pad(h) + ':' + pad(m) + ':' + pad(s);
}

function updateTrialClock() {
  const box = document.getElementById('trialTimer');
  const clock = document.getElementById('trialClock');
  if (!box || !clock) return;
  if (_trialEndsAt == null) {
    box.style.display = 'none';
    return;
  }
  const left = Math.max(0, Math.floor(_trialEndsAt - Date.now() / 1000));
  clock.textContent = fmtTrial(left);
  box.style.display = 'flex';
  if (left <= 0) {
    _trialEndsAt = null;
    if (_trialTick) { clearInterval(_trialTick); _trialTick = null; }
    box.style.display = 'none';
    try { refreshQuota(); } catch (e) {}
  }
}

function setTrialTimer(remainingSec) {
  if (remainingSec == null || remainingSec <= 0) {
    _trialEndsAt = null;
    if (_trialTick) { clearInterval(_trialTick); _trialTick = null; }
    updateTrialClock();
    return;
  }
  _trialEndsAt = Date.now() / 1000 + remainingSec;
  updateTrialClock();
  if (_trialTick) clearInterval(_trialTick);
  _trialTick = setInterval(updateTrialClock, 1000);
}

function syncWatermarkAccess(isPro) {
  window.__watermarkIsPro = !!isPro;
  const fixed = {
    wmText: 'ShowcaseMaker', wmFont: 'Fineday', wmOpacity: '50',
    wmScale: '100', wmCorner: 'bl', wmColor: '#ffffff'
  };
  Object.keys(fixed).forEach(function (id) {
    const el = document.getElementById(id);
    if (!el) return;
    if (!isPro) el.value = fixed[id];
    el.disabled = !isPro;
  });
  const enabled = document.getElementById('wmEnable');
  if (enabled) {
    if (!isPro) enabled.checked = true;
    enabled.disabled = !isPro;
  }
  const reset = document.getElementById('btnWmReset');
  if (reset) reset.disabled = !isPro;
  if (!isPro) {
    const wx = document.getElementById('wmX');
    const wy = document.getElementById('wmY');
    if (wx) wx.value = '';
    if (wy) wy.value = '';
  }
  try { window.__wmRedraw && window.__wmRedraw(); } catch (e) {}
}

async function refreshQuota() {
  const r = await fetch('/api/quota', { headers: headers(), credentials: 'include' });
  const j = await r.json();
  const el = document.getElementById('quota');
  const badge = document.getElementById('planBadge');
  const userPill = document.getElementById('userPill');
  const btnUp = document.getElementById('btnUpgrade');
  const btnOut = document.getElementById('btnLogout');
  const btnAuth = document.getElementById('btnAuth');
  syncWatermarkAccess(!!j.pro);
  if (j.pro) {
    if (j.is_trial && j.remaining_sec != null) {
      el.innerHTML = `<b>Trial</b> · ` + fmtTrial(j.remaining_sec);
      badge.textContent = 'Trial'; badge.className = 'pill pro';
      setTrialTimer(j.remaining_sec);
    } else {
      el.innerHTML = `<b>Pro</b> · unlimited`;
      badge.textContent = j.label || 'Pro'; badge.className = 'pill pro';
      setTrialTimer(null);
    }
    btnUp.style.display = 'none';
  } else {
    el.innerHTML = `Today <b>${j.used}</b> / ${j.limit}`;
    badge.textContent = 'Free'; badge.className = 'pill';
    btnUp.style.display = state.session ? 'inline-block' : 'none';
    setTrialTimer(null);
  }
  if (j.email || state.session) {
    userPill.style.display = 'inline-block';
    userPill.textContent = (j.display_name || '').trim() || j.email || 'Account';
    btnAuth.style.display = 'none'; btnOut.style.display = 'inline-block';
  } else {
    userPill.style.display = 'none';
    btnAuth.style.display = 'inline-block'; btnOut.style.display = 'none';
    if (!j.pro) btnUp.style.display = 'none';
  }
}
const modal = document.getElementById('authModal');

window.openAuthModal = function openAuthModal(mode) {
  try {
    state.authMode = (mode === 'register') ? 'register' : 'login';
  } catch (e) {}
  try { if (typeof syncAuthUi === 'function') syncAuthUi(); } catch (e) { console.warn('syncAuthUi', e); }
  try {
    if (typeof syncAuthUiLang === 'function') {
      const L = (typeof appLang === 'function') ? appLang() : (localStorage.getItem('sm_lang') || 'en');
      syncAuthUiLang(L);
    }
  } catch (e) { console.warn('syncAuthUiLang', e); }
  const m = document.getElementById('authModal');
  if (m) {
    m.classList.add('open');
    m.style.display = 'flex';
  }
  try {
    const em = document.getElementById('authEmail');
    if (em) setTimeout(function(){ em.focus(); }, 50);
  } catch (e) {}
};

window.closeAuthModal = function closeAuthModal() {
  const m = document.getElementById('authModal');
  if (m) {
    m.classList.remove('open');
    m.style.display = '';
  }
};

function wireAuthOpeners() {
  const map = [
    ['btnAuth', 'login'],
    ['accLogin', 'login'],
    ['accRegister', 'register'],
  ];
  map.forEach(function (pair) {
    const el = document.getElementById(pair[0]);
    if (!el) return;
    el.onclick = function (e) {
      if (e) { e.preventDefault(); e.stopPropagation(); }
      openAuthModal(pair[1]);
    };
  });
  if (modal) {
    modal.onclick = function (e) {
      if (e.target === modal) closeAuthModal();
    };
  }
}
wireAuthOpeners();

function syncAuthUi() {
  const reg = state.authMode === 'register';
  const L = (typeof appLang === 'function') ? appLang() : (localStorage.getItem('sm_lang') || 'en');
  const isRu = L === 'ru';
  const title = document.getElementById('authTitle');
  const sub = document.getElementById('authSub');
  const submit = document.getElementById('authSubmit');
  const sw = document.getElementById('authSwitch');
  if (title) title.textContent = reg ? (isRu ? 'Регистрация' : 'Sign up') : (isRu ? 'Вход' : 'Log in');
  if (sub) sub.textContent = reg
    ? (isRu ? 'Создай аккаунт для Pro' : 'Create an account for Pro access')
    : (isRu ? 'Войди, чтобы купить Pro и сохранить доступ' : 'Log in to buy Pro and keep access');
  if (submit) submit.textContent = reg ? (isRu ? 'Создать аккаунт' : 'Create account') : (isRu ? 'Войти' : 'Log in');
  if (sw) {
    sw.innerHTML = reg
      ? (isRu ? 'Уже есть аккаунт? <a id="authToggle">Вход</a>' : 'Already have an account? <a id="authToggle">Log in</a>')
      : (isRu ? 'Нет аккаунта? <a id="authToggle">Регистрация</a>' : 'No account? <a id="authToggle">Sign up</a>');
    const tog = document.getElementById('authToggle');
    if (tog) tog.onclick = function () {
      state.authMode = reg ? 'login' : 'register';
      syncAuthUi();
    };
  }
}
document.getElementById('authSubmit').onclick = async () => {
  const email = document.getElementById('authEmail').value.trim();
  const password = document.getElementById('authPass').value;
  const url = state.authMode === 'register' ? '/api/auth/register' : '/api/auth/login';
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ email, password }),
  });
  let j;
  try { j = await r.json(); } catch(e) { alert('Server error'); return; }
  if (!j.ok) { alert(j.msg || 'Error'); return; }
  if (!j.token) { alert('No session token returned'); return; }
  state.session = j.token;
  localStorage.setItem('sm_session', j.token);
  try {
    const secure = location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = 'sm_session=' + encodeURIComponent(j.token) + '; path=/; max-age=' + (90*24*3600) + '; SameSite=Lax' + secure;
  } catch(e) {}
  if (typeof closeAuthModal === 'function') closeAuthModal(); else { try { modal.classList.remove('open'); } catch(e) {} }
  try { refreshAccountUI(); } catch(e) {}
  refreshQuota();
};
document.getElementById('btnLogout').onclick = async () => {
  await fetch('/api/auth/logout', { method:'POST', headers: headers(), credentials: 'include' });
  state.session = '';
  state.token = '';
  localStorage.removeItem('sm_session');
  localStorage.removeItem('sm_token');
  try { document.cookie = 'sm_session=; path=/; max-age=0'; } catch(e) {}
  try { refreshAccountUI(); } catch(e) {}
  refreshQuota();
};
function openFunPayBuy(e) {
  if (typeof openBuyKeyModal === 'function') openBuyKeyModal(e);
  else window.open('https://funpay.com/lots/offer?id=75434891', '_blank');
}
['btnBuyKeyAbout','btnBuyKeyAccount','btnBuyKeyGuest','btnUpgrade'].forEach(function(id) {
  const el = document.getElementById(id);
  if (el) el.onclick = openFunPayBuy;
});

async function doUnlock(code, statusEl) {
  code = (code || '').trim();
  if (!code) {
    if (statusEl) { statusEl.className = 'status err'; statusEl.textContent = 'Enter a code'; }
    else alert('Enter a code');
    return;
  }
  if (!localStorage.getItem('sm_session') && !state.session) {
    if (statusEl) { statusEl.className = 'status err'; statusEl.textContent = 'Log in first'; }
    else alert('Log in first');
    return;
  }
  if (statusEl) { statusEl.className = 'status'; statusEl.textContent = 'Activating…'; }
  try {
    const r = await fetch('/api/unlock', {
      method: 'POST',
      headers: { ...headers(), 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ code }),
    });
    const j = await r.json();
    if (j.ok) {
      localStorage.removeItem('sm_token');
      state.token = '';
      if (statusEl) { statusEl.className = 'status ok'; statusEl.textContent = j.msg || 'Pro activated'; }
      else alert(j.msg || 'Pro activated');
      try { await refreshQuota(); } catch (e) {}
      try { await refreshAccountUI(); } catch (e) {}
    } else {
      const msg = j.msg || 'Error';
      if (statusEl) { statusEl.className = 'status err'; statusEl.textContent = msg; }
      else alert(msg);
    }
  } catch (e) {
    if (statusEl) { statusEl.className = 'status err'; statusEl.textContent = String(e); }
    else alert(String(e));
  }
}
document.getElementById('btnUnlock')?.addEventListener('click', () => {
  doUnlock(document.getElementById('accessCode')?.value, document.getElementById('accProfileStatus') || document.getElementById('quotaBox'));
});
document.getElementById('btnUnlock2')?.addEventListener('click', () => {
  doUnlock(document.getElementById('accessCode2')?.value, document.getElementById('accProfileStatus'));
});

document.querySelectorAll('#nav button').forEach(btn => {
  btn.onclick = () => {
    document.querySelectorAll('#nav button').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    if (btn.dataset.tab === 'account') refreshAccountUI();
    const t = titles[btn.dataset.tab] || ['',''];
    document.getElementById('pageTitle').textContent = t[0];
    document.getElementById('pageSub').textContent = t[1];
  };
});
document.querySelectorAll('.mode').forEach(btn => {
  btn.onclick = () => {
    document.querySelectorAll('.mode').forEach(b => b.classList.remove('active'));
    btn.classList.add('active'); state.mode = btn.dataset.mode;
  };
});

const drop = document.getElementById('drop');
const fileInput = document.getElementById('fileInput');
drop.onclick = () => fileInput.click();
drop.ondragover = e => { e.preventDefault(); drop.classList.add('drag'); };
drop.ondragleave = () => drop.classList.remove('drag');
drop.ondrop = e => { e.preventDefault(); drop.classList.remove('drag'); addFiles([...e.dataTransfer.files]); };
fileInput.onchange = () => { addFiles([...fileInput.files]); fileInput.value=''; };
function addFiles(list){ state.files.push(...list); renderFiles(); try{ window.__wmLoadFromFiles && window.__wmLoadFromFiles(); }catch(e){} }
function renderFiles(){
  const box = document.getElementById('fileList'); box.innerHTML='';
  state.files.forEach((f,i)=>{
    const d=document.createElement('div'); d.className='fi';
    d.innerHTML=`<span>${f.name}</span><button type="button">✕</button>`;
    d.querySelector('button').onclick=()=>{ state.files.splice(i,1); renderFiles(); };
    box.appendChild(d);
  });
  document.getElementById('btnRun').disabled = !state.files.length;
}
document.getElementById('btnClear').onclick = () => {
  state.files=[]; renderFiles();
  document.getElementById('status').textContent='';
  document.getElementById('dlProcess').style.display='none';
  const _pg=document.getElementById('btnPublishGallery'); if(_pg) _pg.style.display='none';
};
document.getElementById('btnRun').onclick = async () => {
  const st = document.getElementById('status');
  const dl = document.getElementById('dlProcess');
  const btn = document.getElementById('btnRun');
  const prog = document.getElementById('procProgress');
  const fill = document.getElementById('procProgFill');
  const pctEl = document.getElementById('procProgPct');
  const label = document.getElementById('procProgLabel');
  const sub = document.getElementById('procProgSub');
  const ru = (localStorage.getItem('sm_lang') === 'ru');
  let tickTimer = null;
  let fakePct = 0;

  function setProg(pct, lab, subText) {
    pct = Math.max(0, Math.min(100, Math.round(pct)));
    if (prog) prog.classList.add('show');
    if (fill) fill.style.width = pct + '%';
    if (pctEl) pctEl.textContent = pct + '%';
    if (label && lab != null) label.textContent = lab;
    if (sub) sub.textContent = subText || '';
  }
  function hideProgLater() {
    setTimeout(function () {
      if (prog) prog.classList.remove('show');
      if (fill) fill.style.width = '0%';
    }, 2800);
  }
  function stopTick() {
    if (tickTimer) { clearInterval(tickTimer); tickTimer = null; }
  }

  st.className = 'status';
  st.textContent = ru ? 'Обработка…' : 'Processing…';
  dl.style.display = 'none';
  if (btn) btn.disabled = true;
  setProg(0, ru ? 'Подготовка…' : 'Preparing…', state.files.length + (ru ? ' файл(ов)' : ' file(s)'));

  const fd = new FormData();
  fd.append('mode', state.mode);
  fd.append('fps', document.getElementById('fps').value);
  fd.append('size', document.getElementById('size').value);
  fd.append('wm_text', document.getElementById('wmText').value);
  fd.append('wm_font', document.getElementById('wmFont').value);
  fd.append('wm_opacity', document.getElementById('wmOpacity').value);
  fd.append('wm_enable', document.getElementById('wmEnable').checked ? '1' : '0');
  fd.append('wm_corner', (document.getElementById('wmCorner') || {}).value || 'bl');
  const sc = document.getElementById('wmScale');
  fd.append('wm_color', document.getElementById('wmColor')?.value || '#ffffff');
  const _wx = document.getElementById('wmX')?.value;
  const _wy = document.getElementById('wmY')?.value;
  if (_wx) fd.append('wm_x', _wx);
  if (_wy) fd.append('wm_y', _wy);
  fd.append('auto_contrast', document.getElementById('autoContrast')?.checked ? '1' : '0');
  fd.append('gif_encoder', document.getElementById('gifEncoder')?.value || 'gifski');
  fd.append('wm_scale', sc ? (Number(sc.value) / 100) : 1);
  fd.append('all_modes', (document.getElementById('allModes') || {}).checked ? '1' : '0');
  state.files.forEach(f => fd.append('files', f));

  try {
    await new Promise(function (resolve, reject) {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', '/api/process');
      xhr.responseType = 'blob';
      xhr.withCredentials = true;
      try {
        const hdr = headers();
        Object.keys(hdr || {}).forEach(function (k) {
          if (k.toLowerCase() === 'content-type') return;
          xhr.setRequestHeader(k, hdr[k]);
        });
      } catch (e) {}

      xhr.upload.onprogress = function (ev) {
        if (!ev.lengthComputable) {
          setProg(8, ru ? 'Отправка файлов…' : 'Uploading files…', '');
          return;
        }
        // Upload = 0–55%
        const p = (ev.loaded / ev.total) * 55;
        const mb = (ev.loaded / 1048576).toFixed(1) + ' / ' + (ev.total / 1048576).toFixed(1) + ' MB';
        setProg(p, ru ? 'Отправка на сервер…' : 'Uploading to server…', mb);
      };
      xhr.upload.onload = function () {
        fakePct = 55;
        setProg(55, ru ? 'Обработка на сервере…' : 'Processing on server…', ru ? 'нарезка, watermark, ZIP…' : 'cuts, watermark, ZIP…');
        stopTick();
        tickTimer = setInterval(function () {
          // creep 55 → 92 while waiting
          if (fakePct < 92) {
            fakePct += (92 - fakePct) * 0.04 + 0.15;
            if (fakePct > 92) fakePct = 92;
            setProg(fakePct, ru ? 'Обработка на сервере…' : 'Processing on server…', ru ? 'подожди, это может занять время' : 'this can take a moment');
          }
        }, 400);
      };

      xhr.onload = function () {
        stopTick();
        const ct = (xhr.getResponseHeader('content-type') || '');
        if (xhr.status >= 200 && xhr.status < 300 && (ct.includes('application/zip') || ct.includes('application/octet-stream') || ct.includes('application/x-zip'))) {
          setProg(100, ru ? 'Готово!' : 'Done!', ru ? 'скачивание ZIP…' : 'downloading ZIP…');
          const blob = xhr.response;
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = 'showcase_' + (state.mode || 'out') + '.zip';
          document.body.appendChild(a);
          a.click();
          a.remove();
          setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
          const n = xhr.getResponseHeader('X-Processed') || '';
          st.className = 'status ok';
          st.textContent = n
            ? ((ru ? 'Готово: ' : 'Done: ') + n + (ru ? ' файл(ов) — скачано' : ' file(s) — downloaded'))
            : (ru ? 'Готово — ZIP скачан' : 'Done — ZIP downloaded');
          dl.style.display = 'none';
          try {
            const pg = document.getElementById('btnPublishGallery');
            if (pg) {
              pg.style.display = 'inline-flex';
              pg.disabled = false;
              const ruBtn = (localStorage.getItem('sm_lang') === 'ru');
              pg.textContent = ruBtn ? 'Опубликовать в галерею' : 'Publish to gallery';
            }
            window.__lastPublishReady = true;
          } catch (e) {}
          try { refreshQuota(); } catch (e) {}
          hideProgLater();
          resolve();
          return;
        }
        // JSON error or legacy
        const reader = new FileReader();
        reader.onload = function () {
          const raw = String(reader.result || '');
          let j;
          try { j = JSON.parse(raw); }
          catch (parseErr) {
            st.className = 'status err';
            st.textContent = (raw || ('HTTP ' + xhr.status)).slice(0, 300);
            setProg(0, ru ? 'Ошибка' : 'Error', st.textContent.slice(0, 80));
            reject(new Error(st.textContent));
            return;
          }
          if (!j.ok) {
            st.className = 'status err';
            let msg = j.msg || 'Error';
            if (j.errors && j.errors.length) msg = j.errors.join(' · ');
            st.textContent = msg;
            setProg(0, ru ? 'Ошибка' : 'Error', msg.slice(0, 100));
            reject(new Error(msg));
          } else if (j.download) {
            setProg(100, ru ? 'Готово!' : 'Done!', '');
            st.className = 'status ok';
            st.textContent = (ru ? 'Готово: ' : 'Done: ') + (j.processed || '') + (ru ? ' файл(ов)' : ' file(s)');
            dl.href = j.download;
            dl.style.display = 'inline-block';
            try {
              const pg = document.getElementById('btnPublishGallery');
              if (pg) {
                pg.style.display = 'inline-flex';
                pg.disabled = false;
                const ruBtn = (localStorage.getItem('sm_lang') === 'ru');
                pg.textContent = ruBtn ? 'Опубликовать в галерею' : 'Publish to gallery';
              }
              window.__lastPublishReady = true;
            } catch (e) {}
            try { refreshQuota(); } catch (e) {}
            hideProgLater();
            resolve();
          } else {
            st.className = 'status err';
            st.textContent = j.msg || 'Unknown response';
            setProg(0, ru ? 'Ошибка' : 'Error', st.textContent);
            reject(new Error(st.textContent));
          }
        };
        reader.onerror = function () {
          st.className = 'status err';
          st.textContent = 'HTTP ' + xhr.status;
          setProg(0, ru ? 'Ошибка' : 'Error', st.textContent);
          reject(new Error(st.textContent));
        };
        reader.readAsText(xhr.response);
      };
      xhr.onerror = function () {
        stopTick();
        const err = ru ? 'Сеть / ошибка запроса' : 'Network error';
        st.className = 'status err';
        st.textContent = err;
        setProg(0, ru ? 'Ошибка' : 'Error', err);
        reject(new Error(err));
      };
      xhr.send(fd);
    });
  } catch (e) {
    if (st && st.className.indexOf('err') < 0) {
      st.className = 'status err';
      st.textContent = String(e && e.message ? e.message : e);
    }
  }
  stopTick();
  if (btn) btn.disabled = !state.files.length;
  try { renderFiles(); } catch (e) {}
};

document.getElementById('btnDl').onclick = async () => {
  const st = document.getElementById('dlStatus');
  const link = document.getElementById('dlLink');
  const btn = document.getElementById('btnDl');
  const prog = document.getElementById('dlProgress');
  const fill = document.getElementById('dlProgressFill');
  const pctEl = document.getElementById('dlProgressPct');
  const label = document.getElementById('dlProgressLabel');
  const sub = document.getElementById('dlProgressSub');
  const ru = (localStorage.getItem('sm_lang') === 'ru');
  let tickTimer = null;
  let fakePct = 0;

  function setProg(pct, lab, subText) {
    pct = Math.max(0, Math.min(100, Math.round(pct)));
    if (prog) prog.classList.add('show');
    if (fill) fill.style.width = pct + '%';
    if (pctEl) pctEl.textContent = pct + '%';
    if (label && lab != null) label.textContent = lab;
    if (sub) sub.textContent = subText || '';
  }
  function stopTick() { if (tickTimer) { clearInterval(tickTimer); tickTimer = null; } }
  function hideLater() {
    setTimeout(function () {
      if (prog) prog.classList.remove('show');
      if (fill) fill.style.width = '0%';
    }, 2800);
  }

  const url = (document.getElementById('dlUrl').value || '').trim();
  if (!url) {
    st.className = 'status err';
    st.textContent = ru ? 'Вставь ссылку' : 'Paste a URL';
    return;
  }
  st.className = 'status';
  st.textContent = ru ? 'Скачивание…' : 'Downloading…';
  link.style.display = 'none';
  if (btn) btn.disabled = true;
  setProg(5, ru ? 'Запрос…' : 'Requesting…', url.slice(0, 48));
  fakePct = 5;
  tickTimer = setInterval(function () {
    if (fakePct < 88) {
      fakePct += (88 - fakePct) * 0.05 + 0.3;
      if (fakePct > 88) fakePct = 88;
      setProg(fakePct, ru ? 'Скачивание с платформы…' : 'Fetching from platform…', ru ? 'yt-dlp / сеть' : 'yt-dlp / network');
    }
  }, 350);

  try {
    const r = await fetch('/api/download-url', {
      method: 'POST',
      headers: { ...headers(), 'Content-Type': 'application/json' },
      body: JSON.stringify({
        url: url,
        quality: document.getElementById('dlQuality').value
      }),
      credentials: 'include'
    });
    stopTick();
    const j = await r.json();
    if (!j.ok) {
      st.className = 'status err';
      st.textContent = j.msg || 'Error';
      setProg(0, ru ? 'Ошибка' : 'Error', (j.msg || '').slice(0, 100));
    } else {
      setProg(100, ru ? 'Готово!' : 'Done!', j.name || '');
      st.className = 'status ok';
      st.textContent = j.name || (ru ? 'Готово' : 'Done');
      link.href = j.download;
      link.style.display = 'inline-block';
      try { refreshQuota(); } catch (e) {}
      hideLater();
    }
  } catch (e) {
    stopTick();
    st.className = 'status err';
    st.textContent = String(e);
    setProg(0, ru ? 'Ошибка' : 'Error', String(e).slice(0, 80));
  }
  if (btn) btn.disabled = false;
};

const pvFiles = {};
async function loadPvSlots() {
  const mode = document.getElementById('pvMode').value;
  const r = await fetch('/api/preview-slots?mode=' + encodeURIComponent(mode));
  const j = await r.json();
  const box = document.getElementById('pvSlots'); box.innerHTML = '';
  (j.slots || []).forEach(s => {
    const row = document.createElement('div'); row.className = 'fi';
    const name = document.createElement('span'); name.style.flex = '1';
    name.textContent = s.label + (pvFiles[s.id] ? ' · ' + pvFiles[s.id].name : ' · файл не выбран');
    const pick = document.createElement('button'); pick.type='button'; pick.className='btn ghost'; pick.style.padding='6px 12px'; pick.textContent='Choose';
    const inp = document.createElement('input'); inp.type='file'; inp.accept='image/*,.gif,video/*'; inp.style.display='none';
    inp.onchange = () => { if (inp.files[0]) { pvFiles[s.id]=inp.files[0]; name.textContent=s.label+' · '+inp.files[0].name; } };
    pick.onclick = (e) => { e.preventDefault(); inp.click(); };
    const clr = document.createElement('button'); clr.type='button'; clr.textContent='✕';
    clr.onclick = () => { delete pvFiles[s.id]; name.textContent=s.label+' · файл не выбран'; };
    row.appendChild(name); row.appendChild(inp); row.appendChild(pick); row.appendChild(clr);
    box.appendChild(row);
  });
}
document.getElementById('pvMode').onchange = () => { Object.keys(pvFiles).forEach(k=>delete pvFiles[k]); loadPvSlots(); };
document.getElementById('btnPvAvatar').onclick = (e) => { e.preventDefault(); document.getElementById('pvAvatar').click(); };
document.getElementById('pvAvatar').onchange = () => {
  const f = document.getElementById('pvAvatar').files[0];
  document.getElementById('pvAvName').textContent = f ? f.name : '—';
};
document.getElementById('btnPv').onclick = async () => {
  const st = document.getElementById('pvStatus');
  const btn = document.getElementById('btnPv');
  const prog = document.getElementById('pvProgress');
  const fill = document.getElementById('pvProgressFill');
  const pctEl = document.getElementById('pvProgressPct');
  const label = document.getElementById('pvProgressLabel');
  const sub = document.getElementById('pvProgressSub');
  const ru = (localStorage.getItem('sm_lang') === 'ru');
  let tickTimer = null;
  let fakePct = 0;

  function setProg(pct, lab, subText) {
    pct = Math.max(0, Math.min(100, Math.round(pct)));
    if (prog) prog.classList.add('show');
    if (fill) fill.style.width = pct + '%';
    if (pctEl) pctEl.textContent = pct + '%';
    if (label && lab != null) label.textContent = lab;
    if (sub) sub.textContent = subText || '';
  }
  function stopTick() { if (tickTimer) { clearInterval(tickTimer); tickTimer = null; } }
  function hideLater() {
    setTimeout(function () {
      if (prog) prog.classList.remove('show');
      if (fill) fill.style.width = '0%';
    }, 2500);
  }

  if (!Object.keys(pvFiles).length) {
    st.className = 'status err';
    st.textContent = ru ? 'Выбери хотя бы одну витрину' : 'Select at least one showcase';
    return;
  }
  st.className = 'status';
  st.textContent = ru ? 'Сборка…' : 'Building…';
  if (btn) btn.disabled = true;
  setProg(0, ru ? 'Подготовка…' : 'Preparing…', Object.keys(pvFiles).length + (ru ? ' слот(ов)' : ' slot(s)'));

  const fd = new FormData();
  fd.append('mode', document.getElementById('pvMode').value);
  const av = document.getElementById('pvAvatar').files[0];
  if (av) fd.append('avatar', av);
  Object.entries(pvFiles).forEach(([id, file]) => fd.append('slot_' + id, file));

  try {
    await new Promise(function (resolve, reject) {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', '/api/preview-build');
      xhr.withCredentials = true;
      try {
        const hdr = headers();
        Object.keys(hdr || {}).forEach(function (k) {
          if (k.toLowerCase() === 'content-type') return;
          xhr.setRequestHeader(k, hdr[k]);
        });
      } catch (e) {}

      xhr.upload.onprogress = function (ev) {
        if (!ev.lengthComputable) {
          setProg(12, ru ? 'Отправка…' : 'Uploading…', '');
          return;
        }
        const p = (ev.loaded / ev.total) * 50;
        const mb = (ev.loaded / 1048576).toFixed(1) + ' / ' + (ev.total / 1048576).toFixed(1) + ' MB';
        setProg(p, ru ? 'Отправка файлов…' : 'Uploading files…', mb);
      };
      xhr.upload.onload = function () {
        fakePct = 50;
        setProg(50, ru ? 'Сборка превью…' : 'Building preview…', '');
        stopTick();
        tickTimer = setInterval(function () {
          if (fakePct < 90) {
            fakePct += (90 - fakePct) * 0.06 + 0.2;
            if (fakePct > 90) fakePct = 90;
            setProg(fakePct, ru ? 'Сборка превью…' : 'Building preview…', ru ? 'подгонка под плашки' : 'fitting into slots');
          }
        }, 350);
      };
      xhr.onload = function () {
        stopTick();
        let j = {};
        try { j = JSON.parse(xhr.responseText || '{}'); } catch (e) {}
        if (xhr.status >= 200 && xhr.status < 300 && j.ok) {
          setProg(100, ru ? 'Готово!' : 'Done!', (j.applied || []).join(', '));
          try { window.open(j.open, '_blank'); } catch (e) {}
          st.className = 'status ok';
          st.textContent = (ru ? 'Открыто · ' : 'Opened · ') + (j.applied || []).join(', ');
          hideLater();
          resolve();
        } else {
          const msg = j.msg || ('HTTP ' + xhr.status);
          st.className = 'status err';
          st.textContent = msg;
          setProg(0, ru ? 'Ошибка' : 'Error', msg.slice(0, 100));
          reject(new Error(msg));
        }
      };
      xhr.onerror = function () {
        stopTick();
        const err = ru ? 'Сеть / ошибка' : 'Network error';
        st.className = 'status err';
        st.textContent = err;
        setProg(0, ru ? 'Ошибка' : 'Error', err);
        reject(new Error(err));
      };
      xhr.send(fd);
    });
  } catch (e) {
    if (st && st.className.indexOf('err') < 0) {
      st.className = 'status err';
      st.textContent = String(e && e.message ? e.message : e);
    }
  }
  stopTick();
  if (btn) btn.disabled = false;
};

/* steam copy wired in wireSteamTab */



async function refreshAccountUI() {
  const guest = document.getElementById('accGuest');
  const user = document.getElementById('accUser');
  if (!guest || !user) return;
  // session in localStorage → show profile shell immediately
  const hasSess = !!(localStorage.getItem('sm_session') || state.session);
  if (hasSess) {
    guest.style.display = 'none';
    user.style.display = '';
  }
  try {
    const r = await fetch('/api/auth/me', { headers: headers(), credentials: 'include' });
    const j = await r.json();
    if (!j.logged_in) {
      guest.style.display = '';
      user.style.display = 'none';
      return;
    }
    guest.style.display = 'none';
    user.style.display = '';
    const email = j.email || '';
    const nick = j.display_name || '';
    const emailLine = document.getElementById('accEmailLine');
    if (emailLine) emailLine.textContent = email;
    const nickInp = document.getElementById('accNick');
    if (nickInp && document.activeElement !== nickInp) nickInp.value = nick;
    const av = document.getElementById('accAvatar');
    if (av) {
      av.style.width = '88px';
      av.style.height = '88px';
      av.style.overflow = 'hidden';
      av.style.position = 'relative';
      if (j.avatar_url) {
        av.innerHTML = '<img alt="" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;border-radius:22px"/><span class="edit-hint">Change</span>';
        av.querySelector('img').src = j.avatar_url + '?t=' + Date.now();
      } else {
        const letter = ((nick || email)[0] || 'S').toUpperCase();
        av.innerHTML = '<span class="av-letter">' + letter + '</span><span class="edit-hint">Change</span>';
      }
    }
    const pro = !!j.is_pro;
    const plan = document.getElementById('accPlanLine');
    if (plan) plan.textContent = pro ? 'Pro · unlimited' : 'Free · daily limit';
    const badge = document.getElementById('accProBadge');
    if (badge) badge.style.display = pro ? 'inline-block' : 'none';
    const keyRow = document.getElementById('accKeyRow');
    const codeBlock = document.getElementById('accCodeBlock');
    const proCode = j.pro_code || '';
    if (keyRow) {
      if (pro && proCode) {
        keyRow.style.display = 'flex';
        const el = document.getElementById('accKeyMasked');
        if (el) {
          const mask = proCode.length > 8 ? proCode.slice(0, 4) + '••••' + proCode.slice(-4) : '••••••••';
          el.textContent = mask;
          el.dataset.full = proCode;
          el.dataset.shown = '0';
          el.onclick = () => {
            if (el.dataset.shown === '1') {
              el.textContent = mask; el.dataset.shown = '0';
              const h = document.getElementById('accKeyHint');
              if (h) h.textContent = 'click to show';
            } else {
              el.textContent = el.dataset.full; el.dataset.shown = '1';
              const h = document.getElementById('accKeyHint');
              if (h) h.textContent = 'click to hide';
            }
          };
        }
      } else {
        keyRow.style.display = 'none';
      }
    }
    if (codeBlock) codeBlock.style.display = pro ? 'none' : '';
  } catch (e) {}
}

async function saveProfile(extraFile) {
  const st = document.getElementById('accProfileStatus');
  const nick = (document.getElementById('accNick')?.value || '').trim();
  if (st) { st.className = 'status'; st.textContent = extraFile ? 'Uploading…' : 'Saving…'; }
  try {
    let r;
    if (extraFile) {
      const fd = new FormData();
      fd.append('avatar', extraFile);
      fd.append('display_name', nick);
      // do NOT set Content-Type — browser sets multipart boundary
      r = await fetch('/api/auth/profile', { method: 'POST', headers: headers(), body: fd, credentials: 'include' });
    } else {
      r = await fetch('/api/auth/profile', {
        method: 'POST',
        headers: { ...headers(), 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ display_name: nick }),
      });
    }
    let j;
    try { j = await r.json(); } catch (e) {
      if (st) { st.className = 'status err'; st.textContent = 'Server error ' + r.status; }
      return;
    }
    if (st) {
      st.className = j.ok ? 'status ok' : 'status err';
      st.textContent = j.msg || (j.ok ? (extraFile ? 'Avatar updated' : 'Saved') : ('Error ' + r.status));
    }
    if (j.ok) refreshAccountUI();
  } catch (err) {
    if (st) { st.className = 'status err'; st.textContent = String(err); }
  }
}
document.getElementById('accAvatar')?.addEventListener('click', (e) => {
  e.preventDefault();
  e.stopPropagation();
  const inp = document.getElementById('accAvatarInput');
  if (inp) { inp.value = ''; inp.click(); }
});
document.getElementById('accAvatarInput')?.addEventListener('change', (e) => {
  const f = e.target.files && e.target.files[0];
  if (f) saveProfile(f);
});
document.getElementById('accSaveProfile')?.addEventListener('click', (e) => {
  e.preventDefault();
  saveProfile(null);
});

document.getElementById('accLogin')?.addEventListener('click', () => openAuthModal('login'));
  document.getElementById('btnDiscordLogin')?.addEventListener('click', async () => {
    try {
      const r = await fetch('/api/auth/discord/login');
      const d = await r.json();
      if (!d.ok || !d.url) { alert(d.msg || 'Discord not configured'); return; }
      window.open(d.url, 'discord_oauth', 'width=520,height=720');
    } catch (e) { alert(String(e)); }
  });
  window.addEventListener('message', (ev) => {
    if (ev.data && (ev.data.type === 'discord_login' || ev.data.type === 'telegram_login') && ev.data.token) {
      try { localStorage.setItem('sm_session', ev.data.token); } catch(e) {}
      location.reload();
    }
  });
document.getElementById('accRegister')?.addEventListener('click', () => openAuthModal('register'));

async function init(){
  // restore session after navigating from home
  state.session = localStorage.getItem('sm_session') || '';
  state.token = localStorage.getItem('sm_token') || '';

  const m = await fetch('/api/meta').then(r=>r.json());
  /* steam code from STEAM_CODES via refreshSteamUI */ try { refreshSteamUI(); } catch(e) {}
  if (m.buy_url) { const bl = document.getElementById('buyLink'); if (bl) bl.href = m.buy_url; }
  const allSocials = m.socials || [];
  const sideSocials = allSocials.filter(s => {
    const k = ((s.name || '') + ' ' + (s.url || '') + ' ' + (s.icon || '')).toLowerCase();
    return k.indexOf('aboutme') < 0 && k.indexOf('about-me') < 0 && k.indexOf('guns.lol') < 0;
  });
  const mkSoc = (arr) => arr.map(s => '<a href="' + s.url + '" target="_blank" rel="noopener"><img src="' + s.icon + '" alt="' + s.name + '"/></a>').join('');
  const so = document.getElementById('socials'); if (so) so.innerHTML = mkSoc(sideSocials);
  const so2 = document.getElementById('socials2'); if (so2) so2.innerHTML = mkSoc(allSocials);
  document.querySelectorAll('.about-socials').forEach(el => { el.innerHTML = mkSoc(allSocials); });
  refreshQuota(); loadPvSlots(); refreshDa(); refreshAccountUI();
  if (new URLSearchParams(location.search).get('auth') === '1') {
    openAuthModal('register');
  }
  if (new URLSearchParams(location.search).get('billing') === 'success') {
    alert('Оплата прошла. Обнови страницу через пару секунд, если Pro ещё не активен.');
    history.replaceState({}, '', '/app');
  }
}
init();


/* ===== Steam tab (desktop-parity logic) ===== */
const STEAM_UPLOAD_URL = "https://steamcommunity.com/sharedfiles/edititem/767/3/";
const STEAM_CODES = {
  workshop: "$J('[name=consumer_app_id]').val(480);$J('[name=file_type]').val(0);$J('[name=visibility]').val(0);",
  featured: "$J('#image_width').val(1000).attr('id',''),$J('#image_height').val(1).attr('id','');",
  split: "$J('#image_width').val(1000).attr('id',''),$J('#image_height').val(1).attr('id','');"
};
const STEAM_FILES = {
  en: {
    workshop: "Files: part_1 … part_5 (in order). Unzip the Process ZIP first if needed.",
    featured: "File: featured_630.png / featured_630.gif",
    split: "Files: center_506 + side_100 (center first, then side)"
  },
  ru: {
    workshop: "Файлы: part_1 … part_5 (по порядку). Можно из ZIP.",
    featured: "Файл: featured_630.png / featured_630.gif",
    split: "Файлы: center_506 + side_100 (сначала центр, потом бок)"
  }
};
const STEAM_MODE_LABELS = {
  en: { workshop: "Workshop (5 parts)", featured: "Featured Artwork", split: "Artwork Split" },
  ru: { workshop: "Workshop (5 частей)", featured: "Featured Artwork", split: "Artwork Split" }
};

function steamLang() {
  return (localStorage.getItem("sm_lang") || "en");
}

function refreshSteamUI() {
  const mode = (document.getElementById("steamMode") || {}).value || "workshop";
  const codeEl = document.getElementById("steamCode");
  if (codeEl) codeEl.textContent = STEAM_CODES[mode] || STEAM_CODES.workshop;
  const L = steamLang();
  const files = (STEAM_FILES[L] || STEAM_FILES.en)[mode];
  const fh = document.getElementById("steamFilesHint");
  if (fh) fh.textContent = files;
  const sel = document.getElementById("steamMode");
  if (sel) {
    const labs = STEAM_MODE_LABELS[L] || STEAM_MODE_LABELS.en;
    Array.from(sel.options).forEach(o => {
      if (labs[o.value]) o.textContent = labs[o.value];
    });
  }
  // i18n chrome
  // APP_I18N is declared later in this classic script. Referring to the lexical
  // binding here puts it in the temporal dead zone and used to abort the whole
  // tools page before the file pickers were wired. Reading through window is
  // safe both before and after the translation table is mounted.
  const i18n = window.APP_I18N;
  const pack = (i18n && i18n[L]) ? i18n[L] : null;
  if (pack) {
    const map = [
      ["steamTitle", pack.steam_h],
      ["steamDesc", pack.steam_desc],
      ["steamTip", pack.steam_tip],
      ["steamPickModeLbl", pack.steam_pick_mode],
      ["steamStep1", pack.steam_step1],
      ["steamStep2", pack.steam_step2],
      ["steamStep3", pack.steam_step3],
      ["steamStep4", pack.steam_step4],
      ["steamFolderHint", pack.steam_folder_hint],
      ["btnSteamFolder", pack.steam_open_folder],
      ["btnSteamPage", pack.steam_open_page],
      ["btnCopyBlank", pack.steam_blank],
      ["btnCopyCode", pack.steam_copy],
      ["steamHowTitle", pack.steam_how],
    ];
    map.forEach(([id, val]) => {
      const el = document.getElementById(id);
      if (el && val) el.textContent = val;
    });
    const how = document.getElementById("steamHowList");
    if (how && pack.steam_how_items && Array.isArray(pack.steam_how_items)) {
      how.innerHTML = pack.steam_how_items.map(x => "<li>" + x + "</li>").join("");
    }
  }
}

(function wireSteamTab() {
  const modeEl = document.getElementById("steamMode");
  if (modeEl) modeEl.addEventListener("change", refreshSteamUI);
  const pageBtn = document.getElementById("btnSteamPage");
  if (pageBtn) pageBtn.onclick = () => window.open(STEAM_UPLOAD_URL, "_blank", "noopener");
  const folderBtn = document.getElementById("btnSteamFolder");
  if (folderBtn) folderBtn.onclick = () => {
    // Web has no local results folder — jump to Process (ZIP lives there after run)
    const btn = document.querySelector('#nav button[data-tab="process"]');
    if (btn) btn.click();
    else location.hash = "process";
  };
  const copyBtn = document.getElementById("btnCopyCode");
  if (copyBtn) copyBtn.onclick = async () => {
    const code = (document.getElementById("steamCode") || {}).textContent || "";
    const st = document.getElementById("steamCopyStatus");
    try {
      await navigator.clipboard.writeText(code);
      if (st) {
        st.className = "status ok";
        st.textContent = steamLang() === "ru" ? "Код скопирован!" : "Code copied!";
      }
    } catch (e) {
      if (st) {
        st.className = "status err";
        st.textContent = String(e);
      }
    }
  };
  refreshSteamUI();
})();


/* ===== i18n ===== */
const APP_I18N = window.APP_I18N = {
  ru: {
    back: "← На главную",
    nav: {
      process: "Обработка", download: "Скачать", convert: "Конвертер", hex: "HEX",
      preview: "Предпросмотр", steam: "Steam", da: "DeviantArt", account: "Аккаунт", about: "О сервисе"
    },
    titles: {
      process: ["Обработка", "Нарезка Workshop / Featured / Split, watermark и ZIP для Steam"],
      download: ["Скачать", "Исходники с YouTube, TikTok, X, Reddit и Pinterest"],
      convert: ["Конвертер", "Видео ↔ GIF и другие форматы"],
      hex: ["HEX", "Последний байт 0x21 для загрузки в Steam"],
      preview: ["Предпросмотр", "Как витрина выглядит на странице профиля Steam"],
      steam: ["Steam", "Инструкция и код консоли для загрузки artwork"],
      da: ["DeviantArt", "Публикация — в desktop-версии"],
      account: ["Аккаунт", "Регистрация, вход и покупка Pro"],
      about: ["О сервисе", "Лимиты, Pro и контакты"]
    },
    login: "Войти", logout: "Выйти", buy: "Купить Pro", buy_key: "Купить ключ",
    mode: "Режим", params: "Параметры", files: "Файлы",
    drop: "Перетащи PNG, JPG, GIF, MP4 или AVI — или нажми для выбора",
    run: "Обработать", clear: "Очистить",
    lbl_fps: "Кадр/с", lbl_width: "Ширина", lbl_wm: "Вотермарка", lbl_font: "Шрифт",
    lbl_opacity: "Прозрачность %", lbl_wm_size: "Размер WM %", lbl_corner: "Угол WM",
    lbl_color: "Цвет WM", lbl_encoder: "Кодек GIF", lbl_on: "Вкл",
    corner_bl: "Левый нижний", corner_br: "Правый нижний", corner_tl: "Левый верхний", corner_tr: "Правый верхний",
    all_modes: "Все режимы",
    mode_ws: "5 частей для витрины мастерской",
    mode_ft: "Artwork шириной 630 px",
    mode_sp: "Центр 506 + боковая 100",
    acc_guest: "Войди или зарегистрируйся",
    acc_guest_p: "Создай аккаунт, чтобы купить Pro и сохранить доступ.",
    reg: "Регистрация", acc_user: "Твой аккаунт",
    code_h: "Код доступа", code_p: "Купил на FunPay? Вставь код сюда.",
    apply: "Применить код",
    funpay_hint: "Покупка на FunPay. После оплаты получишь код — вставь его ниже.",
    steam_h: "Загрузка в Steam",
    steam_desc: "Полуавтомат: папка с файлами → страница Steam → код в консоль → загрузка.",
    steam_tip: "Совет: войди в Steam в браузере заранее. Код вставляется один раз на страницу, затем выбираешь файлы.",
    steam_pick_mode: "Тип витрины",
    steam_step1: "1. Папка с результатами",
    steam_step2: "2. Страница загрузки Steam",
    steam_step3: "3. Код для консоли (F12)",
    steam_step4: "4. Какие файлы грузить",
    steam_folder_hint: "После Process скачай ZIP и распакуй — это и есть готовые файлы. В браузере нет доступа к локальной папке как в десктопе.",
    steam_open_folder: "К вкладке Process",
    steam_open_page: "Открыть страницу Steam",
      steam_blank: "Скопировать пустой символ",
      steam_blank_ok: "Пустой символ скопирован (ㅤ)",
    steam_copy: "Копировать код",
    steam_how: "Пошаговая инструкция",
    steam_how_items: [
      "Нажми «К вкладке Process» — обработай и скачай ZIP",
      "Нажми «Открыть страницу Steam»",
      "Нажми «Копировать код»",
      "На странице Steam: F12 → Console → Ctrl+V → Enter",
      "Загрузи файлы в нужном порядке (см. список ниже)"
    ],

    about_h: "О сервисе",
    auth_login: "Войти", auth_reg: "Регистрация",
    auth_sub_l: "Войди, чтобы купить Pro и сохранить доступ",
    auth_sub_r: "Создай аккаунт, чтобы купить Pro и сохранить доступ",
    no_acc: "Нет аккаунта?", has_acc: "Уже есть аккаунт?",
    ph_email: "Email", ph_pass: "Пароль (мин. 6)",
    nick: "Никнейм", save_profile: "Сохранить профиль",
    activate_pro: "Активировать Pro-код",
    convert_h: "Конвертер", convert_p: "Выбери файл и целевой формат.",
    hex_h: "HEX 21", hex_p: "Меняет последний байт файла на 0x21 (трюк Steam).",
    hex_btn: "Применить HEX 21",
    free_plan: "Free — дневной лимит", pro_plan: "Pro",
  },
  en: {
    back: "← Home",
    nav: {
      process: "Process", download: "Download", convert: "Converter", hex: "HEX",
      preview: "Preview", steam: "Steam", da: "DeviantArt", account: "Account", about: "About"
    },
    titles: {
      process: ["Process", "Workshop / Featured / Split cuts, watermark and Steam ZIP"],
      download: ["Download", "Sources from YouTube, TikTok, X, Reddit and Pinterest"],
      convert: ["Converter", "Video ↔ GIF and other formats"],
      hex: ["HEX", "Last byte 0x21 for Steam upload"],
      preview: ["Preview", "How the showcase looks on a Steam profile"],
      steam: ["Steam", "Guide and console code for artwork upload"],
      da: ["DeviantArt", "Publishing — desktop version"],
      account: ["Account", "Sign up, log in and buy Pro"],
      about: ["About", "Limits, Pro and contacts"]
    },
    login: "Log in", logout: "Log out", buy: "Buy Pro", buy_key: "Buy Key",
    mode: "Mode", params: "Settings", files: "Files",
    drop: "Drop PNG, JPG, GIF, MP4 or AVI — or click to browse",
    run: "Process", clear: "Clear",
    lbl_fps: "FPS", lbl_width: "Width", lbl_wm: "Watermark", lbl_font: "Font",
    lbl_opacity: "Opacity %", lbl_wm_size: "WM size %", lbl_corner: "WM corner",
    lbl_color: "WM color", lbl_encoder: "GIF encoder", lbl_on: "On",
    corner_bl: "Bottom left", corner_br: "Bottom right", corner_tl: "Top left", corner_tr: "Top right",
    all_modes: "All modes",
    mode_ws: "5 panels for Workshop showcase",
    mode_ft: "Artwork 630px wide",
    mode_sp: "Center 506 + side 100",
    acc_guest: "Log in or sign up",
    acc_guest_p: "Create an account to buy Pro and keep access.",
    reg: "Sign up", acc_user: "Your account",
    code_h: "Access code", code_p: "Bought on FunPay? Paste the code here.",
    apply: "Apply code",
    funpay_hint: "Buy on FunPay. After payment you get a code — paste it below.",
    steam_h: "Upload to Steam",
    steam_desc: "Semi-auto: results → Steam page → console code → upload.",
    steam_tip: "Tip: log into Steam in the browser first. Paste the code once on the page, then pick files.",
    steam_pick_mode: "Showcase type",
    steam_step1: "1. Results folder",
    steam_step2: "2. Steam upload page",
    steam_step3: "3. Console code (F12)",
    steam_step4: "4. Which files to upload",
    steam_folder_hint: "After Process, download the ZIP and unpack it — those are your files. The browser cannot open a local folder like the desktop app.",
    steam_open_folder: "Go to Process tab",
    steam_open_page: "Open Steam page",
      steam_blank: "Copy blank character",
      steam_blank_ok: "Blank character copied (ㅤ)",
    steam_copy: "Copy code",
    steam_how: "Step-by-step",
    steam_how_items: [
      "Open Process — run and download the ZIP, then unpack",
      "Click «Open Steam page»",
      "Click «Copy code»",
      "On Steam: F12 → Console → Ctrl+V → Enter",
      "Upload files in the order listed above"
    ],

    about_h: "About",
    auth_login: "Log in", auth_reg: "Sign up",
    auth_sub_l: "Log in to buy Pro and keep access",
    auth_sub_r: "Create an account to buy Pro and keep access",
    no_acc: "No account?", has_acc: "Already have an account?",
    ph_email: "Email", ph_pass: "Password (min 6)",
    nick: "Nickname", save_profile: "Save profile",
    activate_pro: "Activate Pro code",
    convert_h: "Converter", convert_p: "Pick a file and target format.",
    hex_h: "HEX 21", hex_p: "Sets the last byte of the file to 0x21 (Steam trick).",
    hex_btn: "Apply HEX 21",
    free_plan: "Free — daily limit", pro_plan: "Pro",
  }
};

function appLang() {
  return localStorage.getItem('sm_lang') || 'en';
}

window.applyAppLang = function applyAppLang(lang) {

  const pack = APP_I18N[lang] || APP_I18N.ru;
  localStorage.setItem('sm_lang', lang);
  document.documentElement.lang = lang;
  const lb = document.getElementById('langBtn');
  if (lb) lb.textContent = lang === 'en' ? 'RU' : 'EN';

  document.querySelectorAll('#nav button').forEach(btn => {
    const k = btn.dataset.tab;
    if (pack.nav && pack.nav[k]) btn.textContent = pack.nav[k];
  });

  if (typeof titles !== 'undefined' && pack.titles) {
    Object.assign(titles, pack.titles);
    const active = document.querySelector('#nav button.active');
    if (active) {
      const key = active.dataset.tab;
      const pair = pack.titles[key];
      if (pair) {
        const pt = document.getElementById('pageTitle');
        const ps = document.getElementById('pageSub');
        if (pt) pt.textContent = pair[0];
        if (ps) ps.textContent = pair[1];
      }
    }
  }

  const back = document.querySelector('a.back');
  if (back && pack.back) back.textContent = pack.back;

  const setTxt = (id, val) => {
    const el = document.getElementById(id);
    if (el && val != null) el.textContent = val;
  };
  setTxt('btnAuth', pack.login);
  setTxt('btnLogout', pack.logout);
  setTxt('btnUpgrade', pack.buy);
  setTxt('btnBuyKeyAbout', pack.buy_key || pack.buy);
  setTxt('btnBuyKeyAccount', pack.buy_key || pack.buy);
  setTxt('btnBuyKeyGuest', pack.buy_key || pack.buy);
  setTxt('accLogout2', pack.logout);
  setTxt('btnRun', pack.run);
  setTxt('btnClear', pack.clear);
  setTxt('btnProcess', pack.run);
  setTxt('dlProcess', pack.dlzip);
  setTxt('accLogin', pack.login);
  setTxt('accRegister', pack.reg);
  setTxt('btnUnlock2', pack.apply);
  setTxt('accSaveProfile', pack.save_profile);
  setTxt('btnHex', pack.hex_btn);

  // drop zone text
  const dropEl = document.getElementById('drop');
  if (dropEl && pack.drop) dropEl.textContent = pack.drop;

  // process card titles
  const ph = document.querySelectorAll('#tab-process .card h2');
  if (ph[0] && pack.mode) ph[0].textContent = pack.mode;
  if (ph[1] && pack.params) ph[1].textContent = pack.params;
  if (ph[2] && pack.files) ph[2].textContent = pack.files;

  // mode descriptions
  const modes = document.querySelectorAll('.mode span');
  if (modes[0] && pack.mode_ws) modes[0].textContent = pack.mode_ws;
  if (modes[1] && pack.mode_ft) modes[1].textContent = pack.mode_ft;
  if (modes[2] && pack.mode_sp) modes[2].textContent = pack.mode_sp;

  // field labels
  const setFieldLabel = (inputId, text) => {
    if (!text) return;
    const el = document.getElementById(inputId);
    if (!el) return;
    const lab = el.closest('label');
    if (!lab) return;
    const span = lab.querySelector('.lbl-fps, .lbl');
    if (span) { span.textContent = text; return; }
    for (const node of lab.childNodes) {
      if (node.nodeType === 3 && node.textContent.trim()) {
        node.textContent = text;
        return;
      }
    }
  };
  setFieldLabel('fps', pack.lbl_fps);
  setFieldLabel('size', pack.lbl_width);
  setFieldLabel('wmText', pack.lbl_wm);
  setFieldLabel('wmFont', pack.lbl_font);
  setFieldLabel('wmOpacity', pack.lbl_opacity);
  setFieldLabel('wmScale', pack.lbl_wm_size);
  setFieldLabel('wmCorner', pack.lbl_corner);
  setFieldLabel('wmColor', pack.lbl_color);
  setFieldLabel('gifEncoder', pack.lbl_encoder);

  const corner = document.getElementById('wmCorner');
  if (corner && pack.corner_bl) {
    const map = { bl: pack.corner_bl, br: pack.corner_br, tl: pack.corner_tl, tr: pack.corner_tr };
    Array.from(corner.options).forEach(o => { if (map[o.value]) o.textContent = map[o.value]; });
  }

  const allModes = document.getElementById('allModes');
  if (allModes && pack.all_modes) {
    const lab = allModes.closest('label');
    if (lab) {
      lab.childNodes.forEach(n => {
        if (n.nodeType === 3 && n.textContent.trim()) n.textContent = ' ' + pack.all_modes;
      });
    }
  }
  const wmEn = document.getElementById('wmEnable');
  if (wmEn && pack.lbl_on) {
    const lab = wmEn.closest('label');
    if (lab) {
      lab.childNodes.forEach(n => {
        if (n.nodeType === 3 && n.textContent.trim()) n.textContent = ' ' + pack.lbl_on;
      });
    }
  }

  // account
  const ag = document.querySelector('#accGuest h2'); if (ag && pack.acc_guest) ag.textContent = pack.acc_guest;
  const agp = document.querySelector('#accGuest .steps'); if (agp && pack.acc_guest_p) agp.textContent = pack.acc_guest_p;
  const au = document.querySelector('#accUser h2'); if (au && pack.acc_user) au.textContent = pack.acc_user;
  const hint = document.getElementById('accBillingHint'); if (hint && pack.funpay_hint) hint.textContent = pack.funpay_hint;
  document.querySelectorAll('#tab-account .card').forEach(card => {
    const h = card.querySelector('h2');
    if (!h) return;
    const ht = h.textContent || '';
    if (ht.includes('Код') || ht.includes('Access') || ht.includes('код') || ht.includes('code')) {
      if (pack.code_h) h.textContent = pack.code_h;
      const sp = card.querySelector('.steps');
      if (sp && pack.code_p) sp.textContent = pack.code_p;
    }
  });

  // convert / hex
  const convH = document.querySelector('#tab-convert h2'); if (convH && pack.convert_h) convH.textContent = pack.convert_h;
  const hexH = document.querySelector('#tab-hex h2'); if (hexH && pack.hex_h) hexH.textContent = pack.hex_h;

  // auth modal placeholders
  const ae = document.getElementById('authEmail'); if (ae && pack.ph_email) ae.placeholder = pack.ph_email;
  const ap = document.getElementById('authPass'); if (ap && pack.ph_pass) ap.placeholder = pack.ph_pass;

  try { if (typeof updateFpsLabel === 'function') updateFpsLabel(); } catch (e) {}
  try { if (typeof refreshSteamUI === 'function') refreshSteamUI(); } catch (e) {}
  try { if (typeof syncAuthUiLang === 'function') syncAuthUiLang(); } catch (e) {}
}


function syncAuthUiLang(lang) {

  try {
    const fpsLbl = document.querySelector('.lbl-fps');
    if (fpsLbl) fpsLbl.textContent = (lang === 'ru') ? 'Кадр/с' : 'FPS';
  } catch(e) {}

  const t = APP_I18N[lang] || APP_I18N.en;
  const reg = (typeof state !== 'undefined' && state.authMode === 'register');
  const title = document.getElementById('authTitle');
  const sub = document.getElementById('authSub');
  const submit = document.getElementById('authSubmit');
  const sw = document.getElementById('authSwitch');
  const em = document.getElementById('authEmail');
  const pw = document.getElementById('authPass');
  if (title) title.textContent = reg ? t.auth_reg : t.auth_login;
  if (sub) sub.textContent = reg ? t.auth_sub_r : t.auth_sub_l;
  if (submit) submit.textContent = reg ? t.auth_reg : t.auth_login;
  if (em && t.ph_email) em.placeholder = t.ph_email;
  if (pw && t.ph_pass) pw.placeholder = t.ph_pass;
  if (sw) {
    sw.innerHTML = reg
      ? t.has_acc + ' <a id="authToggle">' + t.auth_login + '</a>'
      : t.no_acc + ' <a id="authToggle">' + t.auth_reg + '</a>';
    document.getElementById('authToggle')?.addEventListener('click', () => {
      state.authMode = reg ? 'login' : 'register';
      syncAuthUi();
      syncAuthUiLang(appLang());
    });
  }
}

/* lang wired in final script */

// apply after DOM / init

let daItems = []; // {file, title, name}

function renderDaList() {
  const box = document.getElementById('daList');
  if (!box) return;
  if (!daItems.length) {
    box.innerHTML = '<div class="steps">No files yet</div>';
    return;
  }
  box.innerHTML = daItems.map((it, i) => `
    <div class="fi" style="align-items:center">
      <span style="flex:1;min-width:100px">${it.name}</span>
      <input data-i="${i}" class="da-title" value="${(it.title||'').replace(/"/g,'&quot;')}" placeholder="Title on DeviantArt" style="flex:2;min-width:140px;padding:8px 10px;border-radius:10px;border:1px solid var(--border);background:rgba(0,0,0,.25);color:var(--text)"/>
      <button type="button" class="btn ghost da-rm" data-i="${i}" style="min-height:36px;padding:6px 10px">✕</button>
    </div>`).join('');
  box.querySelectorAll('.da-title').forEach(inp => {
    inp.oninput = () => { daItems[+inp.dataset.i].title = inp.value; };
  });
  box.querySelectorAll('.da-rm').forEach(btn => {
    btn.onclick = () => { daItems.splice(+btn.dataset.i, 1); renderDaList(); };
  });
}

async function refreshDa() {
  try {
    const r = await fetch('/api/da/status', { headers: headers(), credentials: 'include' });
    const j = await r.json().catch(() => ({}));
    const pill = document.getElementById('daStatusPill');
    const login = document.getElementById('daLogin');
    const logout = document.getElementById('daLogout');
    const block = document.getElementById('daConnectedBlock');
    if (j.redirect_hint) {
      const c = document.getElementById('daRedirectCode');
      if (c) c.textContent = j.redirect_hint;
    }
    if (login) {
      login.disabled = false;
      login.style.pointerEvents = 'auto';
      login.style.opacity = '1';
      login.style.cursor = 'pointer';
    }
    if (!pill) return;
    const ru = (localStorage.getItem('sm_lang') === 'ru');
    if (!j.logged_in) {
      pill.textContent = ru ? 'DA: сначала войди в аккаунт Showcase' : 'DA: log in to Showcase account first';
      if (logout) logout.style.display = 'none';
      if (block) block.style.display = 'none';
      if (login) login.style.display = 'inline-block';
      return;
    }
    const connected = !!j.da;
    pill.textContent = connected
      ? (ru ? 'DA: подключено' : 'DA: connected')
      : (j.has_keys
          ? (ru ? 'DA: ключи сохранены · не подключено' : 'DA: keys saved · not connected')
          : (ru ? 'DA: не подключено' : 'DA: not connected'));
    if (login) login.style.display = connected ? 'none' : 'inline-block';
    if (logout) logout.style.display = connected ? 'inline-block' : 'none';
    if (block) block.style.display = connected ? 'block' : 'none';
  } catch (e) {
    console.warn('refreshDa', e);
  }
}

window.addEventListener('message', function (ev) {
  if (ev.data && ev.data.type === 'da_connected') {
    const st = document.getElementById('daMsg');
    if (st) {
      st.className = 'status ok';
      st.textContent = (localStorage.getItem('sm_lang') === 'ru')
        ? 'Подключено. Добавь файлы и загрузи.'
        : 'Connected. Add files and upload.';
    }
    refreshDa();
  }
});

window.daDoConnect = async function daDoConnect() {
  var st = document.getElementById('daMsg');
  function setMsg(cls, text) {
    if (!st) {
      try { alert(text); } catch (e) {}
      return;
    }
    st.className = 'status' + (cls ? ' ' + cls : '');
    st.textContent = text;
  }
  var ru = (localStorage.getItem('sm_lang') === 'ru');
  setMsg('', ru ? 'Подключение…' : 'Connecting…');
  try {
    var sess = '';
    try { sess = localStorage.getItem('sm_session') || ''; } catch (e) {}
    try { if (!sess && typeof state !== 'undefined') sess = state.session || ''; } catch (e) {}
    if (!sess) {
      setMsg('err', ru ? 'Сначала войди в аккаунт Showcase (кнопка Войти сверху)' : 'Log in to Showcase first (Log in button at top)');
      try { if (typeof openAuthModal === 'function') openAuthModal('login'); } catch (e) {}
      return;
    }
    var cidEl = document.getElementById('daClientId');
    var secEl = document.getElementById('daClientSecret');
    var cid = (cidEl && cidEl.value || '').trim();
    var sec = (secEl && secEl.value || '').trim();
    if (!cid || !sec) {
      setMsg('err', ru ? 'Введи Client ID и Client Secret' : 'Enter Client ID and Client Secret');
      return;
    }
    setMsg('', ru ? 'Сохраняю ключи…' : 'Saving keys…');
    var hdr = {};
    try { hdr = headers(); } catch (e) { hdr = {}; }
    if (sess) hdr['X-Session-Token'] = sess;
    try {
      var tok = localStorage.getItem('sm_token');
      if (tok) hdr['X-Access-Token'] = tok;
    } catch (e) {}
    hdr['Content-Type'] = 'application/json';
    var sk = await fetch('/api/da/keys', {
      method: 'POST',
      headers: hdr,
      body: JSON.stringify({ client_id: cid, client_secret: sec }),
      credentials: 'include',
    });
    var sj = {};
    try { sj = await sk.json(); } catch (e) {}
    if (!sk.ok || !sj.ok) {
      setMsg('err', sj.msg || (ru ? 'Ошибка сохранения (' + sk.status + ') — войди в аккаунт' : 'Save failed (' + sk.status + ') — log in'));
      if (sk.status === 401) {
        try { if (typeof openAuthModal === 'function') openAuthModal('login'); } catch (e) {}
      }
      return;
    }
    setMsg('', ru ? 'Открываю DeviantArt…' : 'Opening DeviantArt…');
    var r = await fetch('/api/da/login', { headers: hdr, credentials: 'include' });
    var j = {};
    try { j = await r.json(); } catch (e) {}
    if (!r.ok || !j.ok) {
      setMsg('err', j.msg || ('Error ' + r.status));
      if (r.status === 401) {
        try { if (typeof openAuthModal === 'function') openAuthModal('login'); } catch (e) {}
      }
      return;
    }
    if (!j.url || String(j.url).indexOf('oauth2/authorize') < 0) {
      setMsg('err', 'Bad OAuth URL. Check Client ID / Redirect URI in DA app settings.');
      return;
    }
    var w = null;
    try {
      w = window.open(j.url, 'da_oauth_' + Date.now(), 'width=720,height=800,scrollbars=yes,resizable=yes');
    } catch (e) {}
    if (!w || w.closed) {
      st.className = 'status err';
      st.innerHTML = (ru ? 'Окно заблокировано браузером. ' : 'Popup blocked. ') +
        '<a href="' + j.url + '" target="_blank" rel="noopener" style="color:#00d2ff;text-decoration:underline;font-weight:600">' +
        (ru ? 'НАЖМИ СЮДА — авторизация DeviantArt' : 'CLICK HERE — DeviantArt authorization') + '</a>';
    } else {
      try { w.focus(); } catch (e) {}
      st.className = 'status';
      st.innerHTML = (ru ? 'Окно открыто. Разреши доступ. Или ' : 'Window opened. Allow access. Or ') +
        '<a href="' + j.url + '" target="_blank" rel="noopener" style="color:#00d2ff;text-decoration:underline">' +
        (ru ? 'открой ссылку' : 'open link') + '</a>';
    }
    var n = 0;
    var tmr = setInterval(async function () {
      n++;
      try {
        var stj = await fetch('/api/da/status', { headers: hdr, credentials: 'include' }).then(function (x) { return x.json(); });
        if (stj && stj.da) {
          clearInterval(tmr);
          try { if (w && !w.closed) w.close(); } catch (e) {}
          setMsg('ok', ru ? 'Подключено!' : 'Connected!');
          try { refreshDa(); } catch (e) {}
        }
      } catch (e) {}
      if (n > 90) {
        clearInterval(tmr);
        setMsg('err', ru ? 'Таймаут — нажми Connect ещё раз после разрешения' : 'Timeout — click Connect again after allowing');
      }
    }, 2000);
  } catch (e) {
    setMsg('err', String(e && e.message ? e.message : e));
    console.error('daDoConnect', e);
  }
};

// Capture-phase: works even if other handlers stopPropagation
document.addEventListener('click', function (e) {
  var el = e.target;
  if (!el) return;
  if (el.id === 'daLogin' || (el.closest && el.closest('#daLogin'))) {
    e.preventDefault();
    e.stopPropagation();
    window.daDoConnect();
  }
}, true);

document.getElementById('daLogout') && document.getElementById('daLogout').addEventListener('click', async function () {
  await fetch('/api/da/logout', { method: 'POST', headers: headers(), credentials: 'include' });
  daItems = [];
  renderDaList();
  refreshDa();
  var st = document.getElementById('daMsg');
  if (st) { st.className = 'status'; st.textContent = 'Disconnected'; }
});

document.getElementById('daAddFiles') && document.getElementById('daAddFiles').addEventListener('click', function () {
  var f = document.getElementById('daFiles');
  if (f) f.click();
});
document.getElementById('daFiles') && document.getElementById('daFiles').addEventListener('change', function (e) {
  Array.prototype.forEach.call(e.target.files || [], function (f) {
    daItems.push({ file: f, name: f.name, title: f.name.replace(/\.[^.]+$/, '') });
  });
  e.target.value = '';
  renderDaList();
});
document.getElementById('daClearFiles') && document.getElementById('daClearFiles').addEventListener('click', function () {
  daItems = [];
  renderDaList();
});

document.getElementById('daUpload') && document.getElementById('daUpload').addEventListener('click', async function () {
  var st = document.getElementById('daMsg');
  if (!daItems.length) {
    if (st) { st.className = 'status err'; st.textContent = 'Add files first'; }
    return;
  }
  if (st) { st.className = 'status'; st.textContent = 'Uploading…'; }
  var fd = new FormData();
  daItems.forEach(function (it) {
    fd.append('file', it.file, it.name);
    fd.append('title_' + it.name, it.title || it.name);
  });
  try {
    var r = await fetch('/api/da/upload', { method: 'POST', headers: headers(), body: fd, credentials: 'include' });
    var j = await r.json();
    if (!j.ok) {
      if (st) {
        st.className = 'status err';
        st.textContent = j.msg || (j.errors || []).join('; ') || 'Upload failed';
      }
    } else {
      if (st) {
        st.className = 'status ok';
        st.textContent = 'Uploaded ' + j.uploaded + '/' + j.total + ' to Sta.sh';
        if (j.errors && j.errors.length) st.textContent += ' · ' + j.errors.join('; ');
      }
    }
  } catch (e) {
    if (st) { st.className = 'status err'; st.textContent = String(e); }
  }
});

window.__daLegacyBound = true;

if (location.hash === '#account' || location.hash === '#profile') {
  var btnA = document.querySelector('#nav button[data-tab="account"]');
  if (btnA) btnA.click();
}
if (location.hash === '#da') {
  var btnD = document.querySelector('#nav button[data-tab="da"]');
  if (btnD) btnD.click();
  refreshDa();
}
// app.html L3217-3477
(function(){
  const layer = document.getElementById('starsLayer');
  if (!layer) return;
  const N = 70;
  for (let i = 0; i < N; i++) {
    const el = document.createElement('span');
    el.className = 'star' + (i % 5 === 0 ? ' s2' : (i % 3 === 0 ? ' s3' : ''));
    el.style.left = (Math.random() * 100) + '%';
    el.style.top = (Math.random() * 100) + '%';
    el.style.setProperty('--dx', ((Math.random() - 0.5) * 80) + 'px');
    el.style.animationDuration = (12 + Math.random() * 22) + 's';
    el.style.animationDelay = (-Math.random() * 20) + 's';
    layer.appendChild(el);
  }
})();

// Account tab login / signup open modal
document.querySelectorAll('#tab-account .btn').forEach(btn => {
  const label = (btn.textContent || '').trim().toLowerCase();
  if (label === 'log in' || label === 'войти') {
    btn.addEventListener('click', () => openAuthModal('login'));
  }
  if (label === 'sign up' || label === 'регистрация') {
    btn.addEventListener('click', () => openAuthModal('register'));
  }
});

/* ---- Converter ---- */
let cvFile = null;
function renderCvFile() {
  const box = document.getElementById('cvFileList');
  if (!box) return;
  if (!cvFile) { box.innerHTML = ''; return; }
  box.innerHTML = '<div class="fi"><span>' + cvFile.name + '</span><button type="button" id="cvRm">×</button></div>';
  document.getElementById('cvRm').onclick = () => { cvFile = null; renderCvFile(); document.getElementById('btnConvert').disabled = true; };
}
(function(){
  const drop = document.getElementById('cvDrop');
  const input = document.getElementById('cvInput');
  if (!drop || !input) return;
  drop.onclick = () => input.click();
  drop.ondragover = e => { e.preventDefault(); drop.classList.add('drag'); };
  drop.ondragleave = () => drop.classList.remove('drag');
  drop.ondrop = e => {
    e.preventDefault(); drop.classList.remove('drag');
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      cvFile = e.dataTransfer.files[0];
      renderCvFile();
      document.getElementById('btnConvert').disabled = false;
    }
  };
  input.onchange = () => {
    if (input.files && input.files[0]) {
      cvFile = input.files[0];
      renderCvFile();
      document.getElementById('btnConvert').disabled = false;
    }
  };
})();
document.getElementById('btnConvert')?.addEventListener('click', async () => {
  if (!cvFile) return;
  const st = document.getElementById('cvStatus');
  const dl = document.getElementById('cvDl');
  const btn = document.getElementById('btnConvert');
  const prog = document.getElementById('cvProgress');
  const fill = document.getElementById('cvProgressFill');
  const pctEl = document.getElementById('cvProgressPct');
  const label = document.getElementById('cvProgressLabel');
  const sub = document.getElementById('cvProgressSub');
  const ru = (localStorage.getItem('sm_lang') === 'ru');
  let tickTimer = null;
  let fakePct = 0;

  function setProg(pct, lab, subText) {
    pct = Math.max(0, Math.min(100, Math.round(pct)));
    if (prog) prog.classList.add('show');
    if (fill) fill.style.width = pct + '%';
    if (pctEl) pctEl.textContent = pct + '%';
    if (label && lab != null) label.textContent = lab;
    if (sub) sub.textContent = subText || '';
  }
  function stopTick() { if (tickTimer) { clearInterval(tickTimer); tickTimer = null; } }
  function hideLater() {
    setTimeout(function () {
      if (prog) prog.classList.remove('show');
      if (fill) fill.style.width = '0%';
    }, 2800);
  }

  st.className = 'status';
  st.textContent = ru ? 'Конвертация…' : 'Converting…';
  dl.style.display = 'none';
  if (btn) btn.disabled = true;
  setProg(0, ru ? 'Подготовка…' : 'Preparing…', cvFile.name || '');

  const fd = new FormData();
  fd.append('file', cvFile);
  fd.append('target', document.getElementById('cvTarget').value);

  try {
    await new Promise(function (resolve, reject) {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', '/api/convert');
      xhr.responseType = 'blob';
      xhr.withCredentials = true;
      try {
        const hdr = headers();
        Object.keys(hdr || {}).forEach(function (k) {
          if (k.toLowerCase() === 'content-type') return;
          xhr.setRequestHeader(k, hdr[k]);
        });
      } catch (e) {}

      xhr.upload.onprogress = function (ev) {
        if (!ev.lengthComputable) {
          setProg(10, ru ? 'Отправка…' : 'Uploading…', '');
          return;
        }
        const p = (ev.loaded / ev.total) * 45;
        const mb = (ev.loaded / 1048576).toFixed(1) + ' / ' + (ev.total / 1048576).toFixed(1) + ' MB';
        setProg(p, ru ? 'Отправка файла…' : 'Uploading file…', mb);
      };
      xhr.upload.onload = function () {
        fakePct = 45;
        setProg(45, ru ? 'Конвертация…' : 'Converting…', document.getElementById('cvTarget').value || '');
        stopTick();
        tickTimer = setInterval(function () {
          if (fakePct < 92) {
            fakePct += (92 - fakePct) * 0.05 + 0.25;
            if (fakePct > 92) fakePct = 92;
            setProg(fakePct, ru ? 'Конвертация на сервере…' : 'Converting on server…', '');
          }
        }, 400);
      };
      xhr.onload = function () {
        stopTick();
        const ct = (xhr.getResponseHeader('Content-Type') || '');
        if (xhr.status >= 200 && xhr.status < 300 && !ct.includes('application/json')) {
          setProg(100, ru ? 'Готово!' : 'Done!', '');
          const blob = xhr.response;
          const cd = xhr.getResponseHeader('Content-Disposition') || '';
          let name = 'converted.bin';
          const m = /filename="?([^";]+)"?/i.exec(cd);
          if (m) name = m[1];
          const url = URL.createObjectURL(blob);
          dl.href = url;
          dl.download = name;
          dl.style.display = 'inline-flex';
          dl.textContent = (ru ? 'Скачать ' : 'Download ') + name;
          st.className = 'status ok';
          st.textContent = ru ? 'Готово' : 'Done';
          try { refreshQuota(); } catch (e) {}
          hideLater();
          resolve();
          return;
        }
        const reader = new FileReader();
        reader.onload = function () {
          let j = {};
          try { j = JSON.parse(String(reader.result || '{}')); } catch (e) {}
          const msg = j.msg || ('HTTP ' + xhr.status);
          st.className = 'status err';
          st.textContent = msg;
          setProg(0, ru ? 'Ошибка' : 'Error', msg.slice(0, 100));
          reject(new Error(msg));
        };
        reader.onerror = function () {
          st.className = 'status err';
          st.textContent = 'HTTP ' + xhr.status;
          setProg(0, ru ? 'Ошибка' : 'Error', st.textContent);
          reject(new Error(st.textContent));
        };
        reader.readAsText(xhr.response);
      };
      xhr.onerror = function () {
        stopTick();
        const err = ru ? 'Сеть / ошибка' : 'Network error';
        st.className = 'status err';
        st.textContent = err;
        setProg(0, ru ? 'Ошибка' : 'Error', err);
        reject(new Error(err));
      };
      xhr.send(fd);
    });
  } catch (e) {
    if (st && st.className.indexOf('err') < 0) {
      st.className = 'status err';
      st.textContent = String(e && e.message ? e.message : e);
    }
  }
  stopTick();
  if (btn) btn.disabled = !cvFile;
});

/* ---- HEX 21 ---- */
let hexFiles = [];
function renderHexFiles() {
  const box = document.getElementById('hexFileList');
  if (!box) return;
  box.innerHTML = hexFiles.map((f, i) =>
    '<div class="fi"><span>' + f.name + '</span><button type="button" data-i="' + i + '">×</button></div>'
  ).join('');
  box.querySelectorAll('button').forEach(b => {
    b.onclick = () => {
      hexFiles.splice(Number(b.dataset.i), 1);
      renderHexFiles();
      document.getElementById('btnHex').disabled = !hexFiles.length;
    };
  });
}
(function(){
  const drop = document.getElementById('hexDrop');
  const input = document.getElementById('hexInput');
  if (!drop || !input) return;
  drop.onclick = () => input.click();
  drop.ondragover = e => { e.preventDefault(); drop.classList.add('drag'); };
  drop.ondragleave = () => drop.classList.remove('drag');
  drop.ondrop = e => {
    e.preventDefault(); drop.classList.remove('drag');
    if (e.dataTransfer.files) {
      hexFiles = hexFiles.concat(Array.from(e.dataTransfer.files));
      renderHexFiles();
      document.getElementById('btnHex').disabled = !hexFiles.length;
    }
  };
  input.onchange = () => {
    if (input.files) {
      hexFiles = hexFiles.concat(Array.from(input.files));
      renderHexFiles();
      document.getElementById('btnHex').disabled = !hexFiles.length;
      input.value = '';
    }
  };
})();
document.getElementById('btnHex')?.addEventListener('click', async () => {
  if (!hexFiles.length) return;
  const st = document.getElementById('hexStatus');
  const dl = document.getElementById('hexDl');
  st.className = 'status'; st.textContent = 'Applying HEX 21…';
  dl.style.display = 'none';
  const fd = new FormData();
  hexFiles.forEach(f => fd.append('files', f));
  try {
    const r = await fetch('/api/hex21', { method: 'POST', body: fd, headers: headers(), credentials: 'include' });
    if (!r.ok) {
      let msg = 'Error';
      try { const j = await r.json(); msg = j.msg || msg; } catch(e) { msg = await r.text(); }
      st.className = 'status err'; st.textContent = msg; return;
    }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    dl.href = url; dl.download = 'hex21.zip'; dl.style.display = 'inline-flex';
    st.className = 'status ok'; st.textContent = 'Done — last byte set to 0x21';
    try { refreshQuota(); } catch(e) {}
  } catch (e) {
    st.className = 'status err'; st.textContent = String(e);
  }
});
// app.html L3483-3992
/* ===== i18n bootstrap (full RU/EN) ===== */
(function () {
  var DICT = {
    en: {
      nav_process: "Process", nav_compose: "Character", nav_download: "Download", nav_convert: "Converter", nav_hex: "HEX",
      nav_preview: "Preview", nav_steam: "Steam", nav_da: "DeviantArt", nav_account: "Account", nav_about: "About",
      login: "Log in", logout: "Log out", buy: "Buy Pro", buy_key: "Buy Key", reg: "Sign up", apply: "Apply",
      save_profile: "Save profile", back: "← Home",
      title_process: "Process", sub_process: "Workshop / Featured / Split cuts, watermark and Steam ZIP",
      title_compose: "Character + BG", sub_compose: "Composite character on background, then send to Process",
      title_download: "Download", sub_download: "Sources from YouTube, TikTok, X, Reddit and Pinterest",
      title_convert: "Converter", sub_convert: "Convert between video, GIF and image formats",
      title_hex: "HEX 21", sub_hex: "Patch last byte to 0x21 for Steam",
      title_preview: "Preview", sub_preview: "How the showcase looks on a Steam profile",
      title_steam: "Steam", sub_steam: "Guide and console code for artwork upload",
      title_da: "DeviantArt", sub_da: "Publishing — desktop version",
      title_account: "Account", sub_account: "Sign up, log in and buy Pro",
      title_about: "About", sub_about: "Limits, Pro and contacts",
      compose_h: "Character + background",
      compose_intro: "Upload a background and a character (PNG / GIF / MP4). Live preview is on the right. «Compose» builds the final file (chromakey + animation).",
      compose_bg_lbl: "1. Showcase background",
      compose_char_lbl: "2. Character",
      compose_nofile: "no file selected",
      compose_pick: "Choose",
      compose_chroma_lbl: "Character background",
      compose_chroma_auto: "Remove colored backdrop automatically",
      compose_chroma_none: "Already transparent (don't touch)",
      compose_tol_lbl: "Chromakey tolerance",
      compose_feather_lbl: "Edge smoothing",
      compose_scale_lbl: "Character scale",
      compose_width_lbl: "Output width",
      compose_ox_lbl: "Position X (0=left → 1=right)",
      compose_oy_lbl: "Position Y (0=top → 1=bottom)",
      compose_enc_lbl: "GIF codec",
      compose_fps_lbl: "Animation FPS",
      compose_btn: "Compose",
      compose_dl: "Download",
      compose_to_process: "To Process →",
      compose_help_title: "How to use",
      compose_help_1: "Background — image the character is placed on (PNG/JPG).",
      compose_help_2: "Character — transparent PNG, or photo/video on green, blue or red screen.",
      compose_help_3: "Live preview on the right. Drag the character, use the corner handle or mouse wheel to resize. Sliders work too.",
      compose_help_4: "Colored backdrop — leave «Remove colored backdrop automatically». Pre-cut PNG — choose «Already transparent».",
      compose_help_5: "Tolerance — how aggressive chromakey is. Smoothing — edge softness (0 = hard).",
      compose_help_6: "Press Compose → download the result or send To Process for Workshop slicing.",
      compose_live_empty: "Add background and character — preview updates instantly",
      compose_final_empty: "Final result after Compose",
      compose_final_hint: "Click the finished image — opens in a new tab",
      compose_prog: "Compositing…",
      mode: "Mode", params: "Settings", files: "Files",
      mode_ws: "5 panels for Workshop showcase", mode_ft: "Artwork 630px wide", mode_sp: "Center 506 + side 100",
      run: "Process", clear: "Clear",
      drop: "Drop PNG, JPG, GIF, MP4 or AVI — or click to browse",
      cv_drop: "Drop file or click to browse",
      hex_drop: "Drop PNG, GIF or images — or click to browse",
      lbl_fps: "FPS", lbl_size: "Width", lbl_wm: "Watermark", lbl_font: "Font",
      lbl_op: "Opacity %", lbl_wm_size: "WM size %", lbl_corner: "WM corner",
      lbl_color: "WM color", lbl_enc: "GIF encoder",
      all_modes: "All modes", wm_on: "On",
      corner_bl: "Bottom left", corner_br: "Bottom right", corner_tl: "Top left", corner_tr: "Top right",
      about_h: "About",
      about_body: "Showcase Maker WEB — browser tools for Steam showcases.\nFree: daily file limit · Pro: unlimited (account + access code).\n\nby n1t1337",
      account_h: "Account",
      account_guest: "Log in or create an account — one profile for the whole site.",
      da_h: "DeviantArt",
      da_body: "Like the desktop app: paste Client ID & Secret from deviantart.com/developers, click Connect, allow access in the popup. Then pick files, set titles, upload to your Sta.sh.",
      da_redirect: "Redirect URI in your DA app must be exactly:",
      da_connect: "Connect",
      da_need_login: "DA: log in to Showcase account first",
      steam_h: "Upload to Steam",
      steam_desc: "Semi-auto: results folder → Steam page → console code → upload.",
      steam_tip: "Tip: log into Steam in the browser first. Paste the code once on the page, then pick files.",
      steam_pick_mode: "Showcase type",
      steam_step1: "1. Results folder",
      steam_step2: "2. Steam upload page",
      steam_step3: "3. Console code (F12)",
      steam_step4: "4. Which files to upload",
      steam_folder_hint: "After Process, download the ZIP and unpack it — those are your files.",
      steam_open_folder: "Open Process tab",
      steam_open_page: "Open Steam page",
      steam_blank: "Copy blank character",
      steam_blank_ok: "Blank character copied (ㅤ)",
      steam_video_cap: "Video guide: how to upload to Steam",
      steam_copy: "Copy code",
      steam_how: "Step-by-step",
      steam_how_1: "Run Process and download the ZIP, then unpack",
      steam_how_2: "Click «Open Steam page»",
      steam_how_3: "Click «Copy code»",
      steam_how_4: "On Steam: F12 → Console → Ctrl+V → Enter",
      steam_how_5: "Upload files in the order listed above",
      steam_files_ws: "Files: part_1 … part_5 (in order). Unzip the Process ZIP first if needed.",
      steam_files_fa: "File: featured_630.png / featured_630.gif",
      steam_files_split: "Files: center_506 + side_100 (center first, then side)",
      pv_h: "Profile preview",
      pv_body: "Pick page mode → file per showcase → open in a new tab (animated GIF and MP4).",
      pv_mode: "Mode",
      pv_showcases: "Showcases",
      pv_open: "Open in browser",
      pv_avatar: "Avatar",
      pv_choose: "Choose",
      pv_nofile: "no file selected",
      hex_h: "HEX 21",
      hex_body: "Steam trick: set last byte to 0x21 on PNG / GIF (and other files). Download ZIP with patched files.",
      hex_btn: "Apply HEX 21",
      convert_h: "Converter",
      convert_body: "Pick a file and the format you need — Video ↔ GIF, MP4, WEBM, PNG, JPG, WEBP.",
      convert_to: "Convert to",
      cv_btn: "Convert",
      dl_h: "Download from web",
      dl_body: "YouTube · TikTok · X · Reddit · Pinterest — no third-party sites",
      dl_btn: "Download",
      dl_best: "Best",
      ph_code: "Access code",
      free: "Free", pro: "Pro"
    },
    ru: {
      nav_process: "Обработка", nav_compose: "Персонаж", nav_download: "Скачать", nav_convert: "Конвертер", nav_hex: "HEX",
      nav_preview: "Предпросмотр", nav_steam: "Steam", nav_da: "DeviantArt", nav_account: "Аккаунт", nav_about: "О сервисе",
      login: "Войти", logout: "Выйти", buy: "Купить Pro", buy_key: "Купить ключ", reg: "Регистрация", apply: "Применить",
      save_profile: "Сохранить профиль", back: "← На главную",
      title_process: "Обработка", sub_process: "Нарезка Workshop / Featured / Split, водяной знак и ZIP для Steam",
      title_compose: "Персонаж + фон", sub_compose: "Наложить персонажа на фон и отправить в Обработку",
      title_download: "Скачать", sub_download: "Исходники с YouTube, TikTok, X, Reddit и Pinterest",
      title_convert: "Конвертер", sub_convert: "Конвертация видео, GIF и изображений",
      title_hex: "HEX 21", sub_hex: "Последний байт 0x21 для Steam",
      title_preview: "Предпросмотр", sub_preview: "Как витрина выглядит на странице профиля Steam",
      title_steam: "Steam", sub_steam: "Инструкция и код консоли для загрузки artwork",
      title_da: "DeviantArt", sub_da: "Публикация — как в десктоп-версии",
      title_account: "Аккаунт", sub_account: "Регистрация, вход и покупка Pro",
      title_about: "О сервисе", sub_about: "Лимиты, Pro и контакты",
      compose_h: "Персонаж + фон",
      compose_intro: "Загрузи фон и персонажа (PNG / GIF / MP4). Справа — живой превью. «Совместить» делает финальный файл (с хромакеем и анимацией).",
      compose_bg_lbl: "1. Фон витрины",
      compose_char_lbl: "2. Персонаж",
      compose_nofile: "файл не выбран",
      compose_pick: "Выбрать",
      compose_chroma_lbl: "Фон у персонажа",
      compose_chroma_auto: "Убрать цветной фон автоматически",
      compose_chroma_none: "Уже прозрачный (не трогать)",
      compose_tol_lbl: "Толерантность хромакея",
      compose_feather_lbl: "Сглаживание краёв",
      compose_scale_lbl: "Масштаб персонажа",
      compose_width_lbl: "Ширина результата",
      compose_ox_lbl: "Позиция X (0=лево → 1=право)",
      compose_oy_lbl: "Позиция Y (0=верх → 1=низ)",
      compose_enc_lbl: "Кодек GIF",
      compose_fps_lbl: "FPS анимации",
      compose_btn: "Совместить",
      compose_dl: "Скачать",
      compose_to_process: "В Обработку →",
      compose_help_title: "Как пользоваться",
      compose_help_1: "Фон витрины — картинка, на которую ставится персонаж (PNG/JPG).",
      compose_help_2: "Персонаж — PNG с прозрачностью или фото/видео на зелёном, синем или красном фоне.",
      compose_help_3: "Справа — live. Тащи персонажа мышью, угол рамки или колёсико — размер. Ползунки тоже работают.",
      compose_help_4: "Если фон цветной — оставь «Убрать цветной фон автоматически». Уже вырезанный PNG — выбери «Уже прозрачный».",
      compose_help_5: "Толерантность — насколько агрессивно режется хромакей. Сглаживание — мягкость края (0 = резко).",
      compose_help_6: "Нажми Совместить → скачай результат или отправь В Обработку для нарезки Workshop.",
      compose_live_empty: "Добавь фон и персонажа — превью обновится сразу",
      compose_final_empty: "Финальный результат после «Совместить»",
      compose_final_hint: "Нажми на готовое изображение — откроется в новой вкладке",
      compose_prog: "Склеиваем…",
      mode: "Режим", params: "Параметры", files: "Файлы",
      mode_ws: "5 панелей для витрины Workshop", mode_ft: "Artwork шириной 630px", mode_sp: "Центр 506 + бок 100",
      run: "Обработать", clear: "Очистить",
      drop: "Перетащи PNG, JPG, GIF, MP4 или AVI — или нажми для выбора",
      cv_drop: "Перетащи файл или нажми для выбора",
      hex_drop: "Перетащи PNG, GIF или изображения — или нажми для выбора",
      lbl_fps: "Кадр/с", lbl_size: "Ширина", lbl_wm: "Водяной знак", lbl_font: "Шрифт",
      lbl_op: "Прозрачность %", lbl_wm_size: "Размер WM %", lbl_corner: "Угол WM",
      lbl_color: "Цвет WM", lbl_enc: "Кодер GIF",
      all_modes: "Все режимы", wm_on: "Вкл",
      corner_bl: "Левый низ", corner_br: "Правый низ", corner_tl: "Левый верх", corner_tr: "Правый верх",
      about_h: "О сервисе",
      about_body: "Showcase Maker WEB — браузерные инструменты для витрин Steam.\nБесплатно: дневной лимит файлов · Pro: без лимита (аккаунт + код доступа).\n\nby n1t1337",
      account_h: "Аккаунт",
      account_guest: "Войди или создай аккаунт — один профиль на весь сайт.",
      da_h: "DeviantArt",
      da_body: "Как в десктопе: вставь Client ID и Secret с deviantart.com/developers, нажми Connect, разреши доступ во всплывающем окне. Затем выбери файлы, названия и загрузи в свой Sta.sh.",
      da_redirect: "Redirect URI в приложении DA должен быть точно:",
      da_connect: "Подключить",
      da_need_login: "DA: сначала войди в аккаунт Showcase",
      steam_h: "Загрузка в Steam",
      steam_desc: "Полуавтомат: папка с файлами → страница Steam → код в консоль → загрузка.",
      steam_tip: "Совет: войди в Steam в браузере заранее. Код вставляется один раз на страницу, затем выбираешь файлы.",
      steam_pick_mode: "Тип витрины",
      steam_step1: "1. Папка с результатами",
      steam_step2: "2. Страница загрузки Steam",
      steam_step3: "3. Код для консоли (F12)",
      steam_step4: "4. Какие файлы грузить",
      steam_folder_hint: "После Process скачай ZIP и распакуй — это готовые файлы.",
      steam_open_folder: "К вкладке Process",
      steam_open_page: "Открыть страницу Steam",
      steam_blank: "Скопировать пустой символ",
      steam_blank_ok: "Пустой символ скопирован (ㅤ)",
      steam_video_cap: "Видео-инструкция: как загружать в Steam",
      steam_copy: "Копировать код",
      steam_how: "Пошаговая инструкция",
      steam_how_1: "Обработай файлы и скачай ZIP, затем распакуй",
      steam_how_2: "Нажми «Открыть страницу Steam»",
      steam_how_3: "Нажми «Копировать код»",
      steam_how_4: "На странице Steam: F12 → Console → Ctrl+V → Enter",
      steam_how_5: "Загрузи файлы в нужном порядке (см. список ниже)",
      steam_files_ws: "Файлы: part_1 … part_5 (по порядку). Можно из ZIP.",
      steam_files_fa: "Файл: featured_630.png / featured_630.gif",
      steam_files_split: "Файлы: center_506 + side_100 (сначала центр, потом бок)",
      pv_h: "Предпросмотр профиля",
      pv_body: "Выбери режим страницы → файл на каждую витрину → открой в новой вкладке (GIF и MP4).",
      pv_mode: "Режим",
      pv_showcases: "Витрины",
      pv_open: "Открыть в браузере",
      pv_avatar: "Аватар",
      pv_choose: "Выбрать",
      pv_nofile: "файл не выбран",
      hex_h: "HEX 21",
      hex_body: "Трюк Steam: последний байт 0x21 у PNG / GIF (и других файлов). Скачай ZIP с пропатченными файлами.",
      hex_btn: "Применить HEX 21",
      convert_h: "Конвертер",
      convert_body: "Выбери файл и нужный формат — Video ↔ GIF, MP4, WEBM, PNG, JPG, WEBP.",
      convert_to: "Конвертировать в",
      cv_btn: "Конвертировать",
      dl_h: "Скачать из сети",
      dl_body: "YouTube · TikTok · X · Reddit · Pinterest — без сторонних сайтов",
      dl_btn: "Скачать",
      dl_best: "Лучшее",
      ph_code: "Код доступа",
      free: "Free", pro: "Pro"
    }
  };

  function getLang() {
    try { return localStorage.getItem("sm_lang") || "en"; } catch (e) { return "en"; }
  }
  function setLang(L) {
    try { localStorage.setItem("sm_lang", L); } catch (e) {}
  }

  function setLabelFor(inputId, text) {
    if (!text) return;
    var el = document.getElementById(inputId);
    if (!el) return;
    var lab = el.closest("label");
    if (!lab) return;
    for (var i = 0; i < lab.childNodes.length; i++) {
      var n = lab.childNodes[i];
      if (n.nodeType === 3 && n.textContent.trim()) {
        n.textContent = text + " ";
        return;
      }
    }
    var span = lab.querySelector(".lbl, .lbl-fps");
    if (span) span.textContent = text;
  }

  function applyDict(L) {
    var pack = DICT[L] || DICT.en;
    document.documentElement.lang = L;

    document.querySelectorAll("[data-i]").forEach(function (el) {
      var k = el.getAttribute("data-i");
      if (k && pack[k] != null) el.textContent = pack[k];
    });
    document.querySelectorAll("[data-i-ph]").forEach(function (el) {
      var k = el.getAttribute("data-i-ph");
      if (k && pack[k] != null) el.placeholder = pack[k];
    });
    document.querySelectorAll("[data-i-opt]").forEach(function (el) {
      var k = el.getAttribute("data-i-opt");
      if (k && pack[k] != null) el.textContent = pack[k];
    });
    // compose empty file labels (only if still "empty" state)
    ["composeBgName", "composeCharName"].forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      var inp = id === "composeBgName" ? document.getElementById("composeBg") : document.getElementById("composeChar");
      var hasFile = inp && inp.files && inp.files[0];
      if (!hasFile && pack.compose_nofile) el.textContent = pack.compose_nofile;
    });

    document.querySelectorAll("#nav button[data-tab]").forEach(function (btn) {
      var k = "nav_" + btn.getAttribute("data-tab");
      if (pack[k]) btn.textContent = pack[k];
    });

    var active = document.querySelector("#nav button.active");
    if (active) {
      var tab = active.getAttribute("data-tab");
      var pt = document.getElementById("pageTitle");
      var ps = document.getElementById("pageSub");
      if (pt && pack["title_" + tab]) pt.textContent = pack["title_" + tab];
      if (ps && pack["sub_" + tab]) ps.textContent = pack["sub_" + tab];
    }

    var lb = document.getElementById("langBtn");
    if (lb) lb.textContent = L === "en" ? "RU" : "EN";

    // Process field labels
    setLabelFor("fps", pack.lbl_fps);
    setLabelFor("size", pack.lbl_size);
    setLabelFor("wmText", pack.lbl_wm);
    setLabelFor("wmFont", pack.lbl_font);
    setLabelFor("wmOpacity", pack.lbl_op);
    setLabelFor("wmScale", pack.lbl_wm_size);
    setLabelFor("wmCorner", pack.lbl_corner);
    setLabelFor("wmColor", pack.lbl_color);
    setLabelFor("gifEncoder", pack.lbl_enc);

    // corner options
    var corner = document.getElementById("wmCorner");
    if (corner) {
      var map = { bl: pack.corner_bl, br: pack.corner_br, tl: pack.corner_tl, tr: pack.corner_tr };
      Array.from(corner.options).forEach(function (o) {
        if (map[o.value]) o.textContent = map[o.value];
      });
    }

    // checkboxes text nodes
    document.querySelectorAll("label").forEach(function (lab) {
      var inp = lab.querySelector('input[type="checkbox"]');
      if (!inp) return;
      if (inp.id === "wmEnable" || inp.name === "wm_enable") {
        for (var i = 0; i < lab.childNodes.length; i++) {
          if (lab.childNodes[i].nodeType === 3 && lab.childNodes[i].textContent.trim()) {
            lab.childNodes[i].textContent = " " + pack.wm_on;
          }
        }
      }
      if (inp.id === "allModes" || inp.name === "all_modes") {
        for (var j = 0; j < lab.childNodes.length; j++) {
          if (lab.childNodes[j].nodeType === 3 && lab.childNodes[j].textContent.trim()) {
            lab.childNodes[j].textContent = " " + pack.all_modes;
          }
        }
      }
    });

    // About body
    var aboutP = document.querySelector("#tab-about .about-text, #tab-about .steps");
    if (aboutP && pack.about_body) {
      aboutP.innerHTML = pack.about_body.replace(/\n/g, "<br/>");
    }

    // Account guest text
    var accGuestP = document.querySelector("#accGuest .steps, #accGuest p.steps");
    if (accGuestP && pack.account_guest) accGuestP.textContent = pack.account_guest;

    // DA body - first steps paragraph
    var daSteps = document.querySelector("#tab-da .card > p.steps");
    if (daSteps && pack.da_body) {
      // keep link if possible
      daSteps.textContent = pack.da_body;
    }

    // Preview body
    var pvSteps = document.querySelector("#tab-preview .card > p.steps");
    if (pvSteps && pack.pv_body) pvSteps.textContent = pack.pv_body;
    var pvModeLab = document.querySelector("#tab-preview label.field");
    if (pvModeLab && pack.pv_mode) {
      for (var pi = 0; pi < pvModeLab.childNodes.length; pi++) {
        if (pvModeLab.childNodes[pi].nodeType === 3 && pvModeLab.childNodes[pi].textContent.trim()) {
          pvModeLab.childNodes[pi].textContent = pack.pv_mode + " ";
          break;
        }
      }
    }
    // Preview choose buttons
    document.querySelectorAll("#pvSlots button").forEach(function (b) {
      if (b.textContent === "Choose" || b.textContent === "Выбрать" || b.classList.contains("pv-pick")) {
        b.textContent = pack.pv_choose;
      }
    });

    // HEX body
    var hexSteps = document.querySelector("#tab-hex .card > p.steps");
    if (hexSteps && pack.hex_body) hexSteps.textContent = pack.hex_body;

    // Convert
    var cvSteps = document.querySelector("#tab-convert .card > p.steps");
    if (cvSteps && pack.convert_body) cvSteps.textContent = pack.convert_body;
    var cvLab = document.querySelector("#tab-convert label.field");
    if (cvLab && pack.convert_to) {
      for (var ci = 0; ci < cvLab.childNodes.length; ci++) {
        if (cvLab.childNodes[ci].nodeType === 3 && cvLab.childNodes[ci].textContent.trim()) {
          cvLab.childNodes[ci].textContent = pack.convert_to + " ";
          break;
        }
      }
    }

    // Download
    var dlSteps = document.querySelector("#tab-download .card > p.steps, #tab-download .card .steps");
    if (dlSteps && pack.dl_body) dlSteps.textContent = pack.dl_body;
    var dlSel = document.querySelector("#tab-download select");
    if (dlSel && dlSel.options[0] && pack.dl_best) {
      // first option often Best
      if (/best|лучш/i.test(dlSel.options[0].textContent)) dlSel.options[0].textContent = pack.dl_best;
    }

    // Steam via refreshSteamUI + direct
    if (pack.steam_h) {
      var st = document.getElementById("steamTitle"); if (st) st.textContent = pack.steam_h;
      var sd = document.getElementById("steamDesc"); if (sd) sd.textContent = pack.steam_desc;
      var sti = document.getElementById("steamTip"); if (sti) sti.textContent = pack.steam_tip;
      var spm = document.getElementById("steamPickModeLbl"); if (spm) spm.textContent = pack.steam_pick_mode;
      var s1 = document.getElementById("steamStep1"); if (s1) s1.textContent = pack.steam_step1;
      var s2 = document.getElementById("steamStep2"); if (s2) s2.textContent = pack.steam_step2;
      var s3 = document.getElementById("steamStep3"); if (s3) s3.textContent = pack.steam_step3;
      var s4 = document.getElementById("steamStep4"); if (s4) s4.textContent = pack.steam_step4;
      var sfh = document.getElementById("steamFolderHint"); if (sfh) sfh.textContent = pack.steam_folder_hint;
      var sh = document.getElementById("steamHowTitle"); if (sh) sh.textContent = pack.steam_how;
      var how = document.getElementById("steamHowList");
      if (how) {
        how.innerHTML = [pack.steam_how_1, pack.steam_how_2, pack.steam_how_3, pack.steam_how_4, pack.steam_how_5]
          .map(function (x) { return "<li>" + x + "</li>"; }).join("");
      }
      var mode = (document.getElementById("steamMode") || {}).value || "workshop";
      var filesMap = { workshop: pack.steam_files_ws, featured: pack.steam_files_fa, split: pack.steam_files_split };
      var filesEl = document.getElementById("steamFilesHint");
      if (filesEl) filesEl.textContent = filesMap[mode] || pack.steam_files_ws;
    }

    try { if (typeof refreshSteamUI === "function") refreshSteamUI(); } catch (e) {}
    try { if (typeof window.applyAppLang === "function") window.applyAppLang(L); } catch (e) {}
  }

  function toggle(e) {
    if (e) { e.preventDefault(); e.stopPropagation(); }
    var next = getLang() === "en" ? "ru" : "en";
    setLang(next);
    applyDict(next);
  }

  function bind() {
    var lb = document.getElementById("langBtn");
    if (lb) {
      lb.onclick = toggle;
      lb.style.cursor = "pointer";
      lb.style.pointerEvents = "auto";
    }
  }

  function start() {
    bind();
    applyDict(getLang());
    try { if (typeof wireAuthOpeners === 'function') wireAuthOpeners(); } catch (e) {}
  }

  document.addEventListener("click", function (e) {
    var btn = e.target && e.target.closest && e.target.closest("#nav button[data-tab]");
    if (btn) setTimeout(function () { applyDict(getLang()); }, 0);
  });
  // steam mode change
  document.addEventListener("change", function (e) {
    if (e.target && e.target.id === "steamMode") applyDict(getLang());
  });


  // blank Hangul filler for Steam names
  (function () {
    function copyBlank() {
      var ch = "\u3164"; // ㅤ
      var st = document.getElementById("steamBlankStatus");
      var L = getLang();
      var pack = DICT[L] || DICT.en;
      navigator.clipboard.writeText(ch).then(function () {
        if (st) {
          st.className = "status ok";
          st.textContent = pack.steam_blank_ok || "Copied";
        }
      }).catch(function (e) {
        // fallback
        try {
          var ta = document.createElement("textarea");
          ta.value = ch;
          document.body.appendChild(ta);
          ta.select();
          document.execCommand("copy");
          document.body.removeChild(ta);
          if (st) {
            st.className = "status ok";
            st.textContent = pack.steam_blank_ok || "Copied";
          }
        } catch (err) {
          if (st) {
            st.className = "status err";
            st.textContent = String(err);
          }
        }
      });
    }
    function bindBlank() {
      var b = document.getElementById("btnCopyBlank");
      if (b && !b.dataset.wired) {
        b.dataset.wired = "1";
        b.onclick = copyBlank;
      }
    }
    var _start = start;
    start = function () {
      _start();
      bindBlank();
    };
  })();

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
  setTimeout(start, 200);
  setTimeout(start, 800);
})();
// app.html L3996-4353
/* DeviantArt Connect — standalone */
(function () {
  if (window.__daLegacyBound) return;
  function msg(text, cls) {
    var st = document.getElementById("daMsg");
    if (!st) { try { alert(text); } catch (e) {} return; }
    st.className = "status" + (cls ? " " + cls : "");
    st.style.display = "block";
    st.style.minHeight = "24px";
    st.style.marginTop = "12px";
    st.textContent = text;
  }
  function sessionHeaders() {
    var h = { "Content-Type": "application/json" };
    try {
      var s = localStorage.getItem("sm_session");
      if (s) h["X-Session-Token"] = s;
      var tk = localStorage.getItem("sm_token");
      if (tk) h["X-Access-Token"] = tk;
    } catch (e) {}
    return h;
  }
  window.__daConnect = async function () {
    var ru = false;
    try { ru = localStorage.getItem("sm_lang") === "ru"; } catch (e) {}
    msg(ru ? "Подключение…" : "Connecting…", "");
    try {
      var sess = null;
      try { sess = localStorage.getItem("sm_session"); } catch (e) {}
      if (!sess) {
        msg(ru ? "Сначала войди в аккаунт (кнопка сверху)" : "Log in first (button at top)", "err");
        return;
      }
      var cid = String((document.getElementById("daClientId") || {}).value || "").trim();
      var sec = String((document.getElementById("daClientSecret") || {}).value || "").trim();
      if (!cid || !sec) {
        msg(ru ? "Введи Client ID и Client Secret" : "Enter Client ID and Client Secret", "err");
        return;
      }
      msg(ru ? "Сохраняю ключи…" : "Saving keys…", "");
      var sk = await fetch("/api/da/keys", {
        method: "POST",
        headers: sessionHeaders(),
        credentials: "include",
        body: JSON.stringify({ client_id: cid, client_secret: sec })
      });
      var sj = {};
      try { sj = await sk.json(); } catch (e) {}
      if (!sk.ok || !sj.ok) {
        msg(sj.msg || ((ru ? "Ошибка " : "Error ") + sk.status), "err");
        return;
      }
      msg(ru ? "Открываю DeviantArt…" : "Opening DeviantArt…", "");
      var r = await fetch("/api/da/login", { headers: sessionHeaders(), credentials: "include" });
      var j = {};
      try { j = await r.json(); } catch (e) {}
      if (!r.ok || !j.ok) {
        msg(j.msg || ((ru ? "Ошибка " : "Error ") + r.status), "err");
        return;
      }
      if (!j.url) { msg("No OAuth URL", "err"); return; }
      var w = null;
      try { w = window.open(j.url, "da_oauth_" + Date.now(), "width=720,height=800,scrollbars=yes"); } catch (e) {}
      var st = document.getElementById("daMsg");
      if (!w || w.closed) {
        if (st) {
          st.className = "status err";
          st.innerHTML = (ru ? "Popup заблокирован. " : "Popup blocked. ") +
            "<a href=\"" + j.url + "\" target=\"_blank\" rel=\"noopener\" style=\"color:#00d2ff;font-weight:700;text-decoration:underline\">" +
            (ru ? "НАЖМИ СЮДА" : "CLICK HERE") + "</a>";
        }
      } else {
        try { w.focus(); } catch (e) {}
        if (st) {
          st.className = "status";
          st.innerHTML = (ru ? "Разреши доступ в окне DA. Или " : "Allow access in DA window. Or ") +
            "<a href=\"" + j.url + "\" target=\"_blank\" rel=\"noopener\" style=\"color:#00d2ff;text-decoration:underline\">" +
            (ru ? "ссылка" : "link") + "</a>";
        }
      }
      var n = 0;
      var tmr = setInterval(async function () {
        n++;
        try {
          var stj = await fetch("/api/da/status", { headers: sessionHeaders(), credentials: "include" }).then(function (x) { return x.json(); });
          if (stj && stj.da) {
            clearInterval(tmr);
            try { if (w && !w.closed) w.close(); } catch (e) {}
            msg(ru ? "Подключено!" : "Connected!", "ok");
            var pill = document.getElementById("daStatusPill");
            if (pill) pill.textContent = ru ? "DA: подключено" : "DA: connected";
            var block = document.getElementById("daConnectedBlock");
            if (block) block.style.display = "block";
            var login = document.getElementById("daLogin");
            if (login) login.style.display = "none";
          }
        } catch (e) {}
        if (n > 90) clearInterval(tmr);
      }, 2000);
    } catch (e) {
      msg(String(e && e.message ? e.message : e), "err");
      console.error(e);
    }
  };
  function bind() {
    var btn = document.getElementById("daLogin");
    if (!btn) return;
    btn.disabled = false;
    btn.removeAttribute("disabled");
    btn.style.pointerEvents = "auto";
    btn.style.cursor = "pointer";
    btn.onclick = function (e) {
      if (e) { e.preventDefault(); e.stopPropagation(); }
      window.__daConnect();
      return false;
    };
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind);
  else bind();
  setTimeout(bind, 300);
  setTimeout(bind, 1500);
  document.addEventListener("click", function (e) {
    var t = e.target;
    if (!t) return;
    if (t.id === "daLogin" || (t.closest && t.closest("#daLogin"))) {
      e.preventDefault();
      e.stopPropagation();
      window.__daConnect();
    }

  // --- file list for DA upload ---
  window.__daItems = window.__daItems || [];

  function renderDaListSafe() {
    var box = document.getElementById("daList");
    if (!box) return;
    var items = window.__daItems || [];
    if (!items.length) {
      box.innerHTML = "";
      return;
    }
    box.innerHTML = items.map(function (it, i) {
      return '<div class="file-row" style="display:flex;gap:8px;align-items:center;margin:6px 0">' +
        '<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px">' +
        (it.name || "") + "</span>" +
        '<input class="da-title" data-i="' + i + '" value="' +
        String(it.title || "").replace(/"/g, "&quot;") +
        '" style="flex:1;min-width:100px" placeholder="Title"/>' +
        '<button type="button" class="btn ghost da-rm" data-i="' + i + '" style="padding:4px 10px">×</button></div>';
    }).join("");
    box.querySelectorAll(".da-title").forEach(function (inp) {
      inp.oninput = function () {
        var i = +inp.getAttribute("data-i");
        if (window.__daItems[i]) window.__daItems[i].title = inp.value;
      };
    });
    box.querySelectorAll(".da-rm").forEach(function (btn) {
      btn.onclick = function () {
        window.__daItems.splice(+btn.getAttribute("data-i"), 1);
        renderDaListSafe();
      };
    });
  }

  window.__daPickFiles = function () {
    var f = document.getElementById("daFiles");
    if (!f) {
      // create on the fly
      f = document.createElement("input");
      f.type = "file";
      f.id = "daFiles";
      f.multiple = true;
      f.accept = "image/*,image/gif,video/mp4,video/webm,.gif,.png,.jpg,.jpeg,.mp4,.webm";
      f.style.cssText = "position:fixed;left:-9999px;opacity:0";
      document.body.appendChild(f);
      f.addEventListener("change", onDaFilesChange);
    }
    try {
      f.value = "";
      f.click();
    } catch (e) {
      alert("Cannot open file dialog: " + e);
    }
  };

  function onDaFilesChange(e) {
    var files = (e.target && e.target.files) || [];
    for (var i = 0; i < files.length; i++) {
      var f = files[i];
      window.__daItems.push({
        file: f,
        name: f.name,
        title: f.name.replace(/\.[^.]+$/, "")
      });
    }
    try { e.target.value = ""; } catch (err) {}
    renderDaListSafe();
    var st = document.getElementById("daMsg");
    if (st) {
      st.className = "status ok";
      st.textContent = "Files: " + window.__daItems.length;
    }
  }

  window.__daClearFiles = function () {
    window.__daItems = [];
    renderDaListSafe();
  };

  window.__daUpload = async function () {
    var st = document.getElementById("daMsg");
    var prog = document.getElementById("daProgress");
    var fill = document.getElementById("daProgFill");
    var pctEl = document.getElementById("daProgPct");
    var label = document.getElementById("daProgLabel");
    var sub = document.getElementById("daProgSub");
    var upBtn = document.getElementById("daUpload");
    var items = window.__daItems || [];
    var ru = false;
    try { ru = localStorage.getItem("sm_lang") === "ru"; } catch (e) {}

    function setProg(pct, lab, subText) {
      pct = Math.max(0, Math.min(100, Math.round(pct)));
      if (prog) prog.classList.add("show");
      if (fill) fill.style.width = pct + "%";
      if (pctEl) pctEl.textContent = pct + "%";
      if (label && lab) label.textContent = lab;
      if (sub) sub.textContent = subText || "";
    }
    function hideProgLater() {
      setTimeout(function () {
        if (prog) prog.classList.remove("show");
        if (fill) fill.style.width = "0%";
      }, 2500);
    }

    if (!items.length) {
      if (st) { st.className = "status err"; st.textContent = ru ? "Сначала добавь файлы" : "Add files first"; }
      return;
    }
    if (upBtn) upBtn.disabled = true;
    if (st) { st.className = "status"; st.textContent = ru ? "Загрузка…" : "Uploading…"; }
    setProg(0, ru ? "Загрузка на Sta.sh…" : "Uploading to Sta.sh…", "0 / " + items.length);

    var fd = new FormData();
    items.forEach(function (it) {
      fd.append("file", it.file, it.name);
      fd.append("title_" + it.name, it.title || it.name);
    });
    var hdr = {};
    try {
      var s = localStorage.getItem("sm_session");
      if (s) hdr["X-Session-Token"] = s;
      var tk = localStorage.getItem("sm_token");
      if (tk) hdr["X-Access-Token"] = tk;
    } catch (e) {}

    try {
      await new Promise(function (resolve, reject) {
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/da/upload");
        Object.keys(hdr).forEach(function (k) { xhr.setRequestHeader(k, hdr[k]); });
        xhr.withCredentials = true;

        xhr.upload.onprogress = function (ev) {
          if (!ev.lengthComputable) {
            setProg(10, ru ? "Загрузка…" : "Uploading…", items.length + " file(s)");
            return;
          }
          var p = (ev.loaded / ev.total) * 100;
          var mb = (ev.loaded / 1048576).toFixed(1) + " / " + (ev.total / 1048576).toFixed(1) + " MB";
          setProg(p, ru ? "Отправка файлов…" : "Sending files…", mb);
        };
        xhr.upload.onload = function () {
          setProg(95, ru ? "Обработка на сервере…" : "Processing on server…", "");
        };
        xhr.onload = function () {
          var j = {};
          try { j = JSON.parse(xhr.responseText || "{}"); } catch (e) {}
          if (xhr.status >= 200 && xhr.status < 300 && j.ok) {
            setProg(100, ru ? "Готово!" : "Done!", (j.uploaded || 0) + " / " + (j.total || items.length));
            if (st) {
              st.className = "status ok";
              st.textContent = (ru ? "Загружено " : "Uploaded ") + (j.uploaded || 0) + "/" + (j.total || items.length) + " → Sta.sh";
              if (j.errors && j.errors.length) st.textContent += " · " + j.errors.join("; ");
            }
            hideProgLater();
            resolve(j);
          } else {
            var err = (j && j.msg) || (j.errors && j.errors.join("; ")) || ("HTTP " + xhr.status);
            setProg(0, ru ? "Ошибка" : "Error", err);
            if (st) { st.className = "status err"; st.textContent = err; }
            reject(new Error(err));
          }
        };
        xhr.onerror = function () {
          var err = ru ? "Сеть / ошибка загрузки" : "Network upload error";
          setProg(0, ru ? "Ошибка" : "Error", err);
          if (st) { st.className = "status err"; st.textContent = err; }
          reject(new Error(err));
        };
        xhr.send(fd);
      });
    } catch (e) {
      if (st && st.className.indexOf("err") < 0) {
        st.className = "status err";
        st.textContent = String(e && e.message ? e.message : e);
      }
    }
    if (upBtn) upBtn.disabled = false;
  };

  // bind file input change + buttons
  function bindDaFiles() {
    var inp = document.getElementById("daFiles");
    if (inp && !inp.dataset.bound) {
      inp.dataset.bound = "1";
      inp.addEventListener("change", onDaFilesChange);
    }
    var add = document.getElementById("daAddFiles");
    if (add) {
      add.disabled = false;
      add.onclick = function (e) {
        if (e) { e.preventDefault(); e.stopPropagation(); }
        window.__daPickFiles();
        return false;
      };
    }
    var clr = document.getElementById("daClearFiles");
    if (clr) {
      clr.onclick = function (e) {
        if (e) { e.preventDefault(); }
        window.__daClearFiles();
        return false;
      };
    }
    var up = document.getElementById("daUpload");
    if (up) {
      up.onclick = function (e) {
        if (e) { e.preventDefault(); }
        window.__daUpload();
        return false;
      };
    }
    // sync with legacy daItems if main script has it
    try {
      if (typeof daItems !== "undefined" && Array.isArray(daItems)) {
        window.__daItems = daItems;
      }
    } catch (e) {}
  }
  bindDaFiles();
  setTimeout(bindDaFiles, 400);
  setTimeout(bindDaFiles, 1500);

  }, true);
})();
// app.html L4356-4776
/* ===== Watermark manual drag preview + gallery publish ===== */
(function(){
  const canvas = document.getElementById('wmCanvas');
  const empty = document.getElementById('wmCanvasEmpty');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let img = null;
  let wx = 0.04, wy = 0.88;
  let dragging = false;
  let fontReady = {};

  const FONT_MAP = {
    lap: '/fonts/lap.ttf',
    rob: '/fonts/rob.ttf',
    caratte: '/fonts/caratte.ttf',
    Fineday: '/fonts/Fineday.ttf',
    fineday: '/fonts/Fineday.ttf',
    roboto: '/fonts/roboto.ttf',
    'gothic-rus': '/fonts/gothic-rus.ttf'
  };

  function tip(msg){
    const el = document.getElementById('wmTip');
    if (!el) return;
    if (!msg){ el.style.display='none'; el.textContent=''; return; }
    el.style.display='block'; el.textContent = msg;
  }
  function opacityVal(){ return (parseInt(document.getElementById('wmOpacity')?.value||'22',10)||22)/100; }
  function scaleVal(){
    let raw = parseFloat(document.getElementById('wmScale')?.value||'100');
    if (isNaN(raw)) raw = 100;
    if (raw > 2.5) raw = raw / 100; // 40..250 UI
    return Math.max(0.4, Math.min(2.5, raw));
  }
  function colorVal(){ return document.getElementById('wmColor')?.value || '#ffffff'; }
  function textVal(){ return document.getElementById('wmText')?.value || ''; }
  function enabled(){ return !!document.getElementById('wmEnable')?.checked; }
  function fontKey(){ return document.getElementById('wmFont')?.value || 'lap'; }

  function ensureFont(key){
    key = key || 'lap';
    if (fontReady[key]) return Promise.resolve(fontReady[key]);
    const url = FONT_MAP[key];
    if (!url || typeof FontFace === 'undefined') {
      fontReady[key] = key;
      return Promise.resolve(key);
    }
    const face = new FontFace('wm_' + key, 'url(' + url + ')');
    return face.load().then(function(f){
      document.fonts.add(f);
      fontReady[key] = 'wm_' + key;
      return fontReady[key];
    }).catch(function(){
      fontReady[key] = 'Mulish';
      return 'Mulish';
    });
  }

  function firstPreviewFile(){
    try {
      const st = window.state;
      const list = (st && Array.isArray(st.files)) ? st.files : [];
      for (let i = 0; i < list.length; i++) {
        const f = list[i];
        if (!f) continue;
        const name = (f.name || '').toLowerCase();
        const type = (f.type || '').toLowerCase();
        if (type.startsWith('image/')) return f;
        if (type.startsWith('video/')) return f;
        if (/\.(png|jpe?g|webp|bmp|gif|mp4|webm|mov|avi|mkv)$/i.test(name)) return f;
      }
    } catch(e){}
    return null;
  }
  function firstImageFile(){ return firstPreviewFile(); }

  function draw(){
    if (!img || !img.naturalWidth) {
      canvas.style.display = 'none';
      if (empty) empty.style.display = 'block';
      return;
    }
    const maxW = Math.min(920, Math.max(200, (canvas.parentElement?.clientWidth || 600) - 4));
    const ratio = img.naturalWidth / img.naturalHeight;
    let w = maxW, h = Math.round(w / ratio);
    if (h > 420) { h = 420; w = Math.round(h * ratio); }
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
    canvas.style.display = 'block';
    canvas.style.cursor = 'grab';
    if (empty) empty.style.display = 'none';
    ctx.clearRect(0,0,w,h);
    ctx.drawImage(img, 0, 0, w, h);
    if (!enabled() || !textVal()) return;
    const key = fontKey();
    const family = fontReady[key] || ('wm_' + key);
    const fontSize = Math.max(12, Math.round((h / 28) * scaleVal()));
    ctx.font = '600 ' + fontSize + 'px "' + family + '", Mulish, system-ui, sans-serif';
    ctx.fillStyle = colorVal();
    ctx.globalAlpha = opacityVal();
    const tw = ctx.measureText(textVal()).width;
    const x = wx * w;
    const y = wy * h + fontSize * 0.85;
    ctx.fillText(textVal(), x, y);
    ctx.globalAlpha = 1;
    ctx.strokeStyle = 'rgba(0,210,255,.9)';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([5, 4]);
    ctx.strokeRect(x - 3, y - fontSize - 2, tw + 6, fontSize + 8);
    ctx.setLineDash([]);
  }
  window.__wmRedraw = draw;

  function loadFromImageUrl(url, revoke){
    return new Promise(function(resolve){
      const im = new Image();
      im.onload = function(){
        img = im;
        ensureFont(fontKey()).then(function(){ draw(); resolve(true); });
        if (revoke) URL.revokeObjectURL(url);
      };
      im.onerror = function(){
        tip('Не удалось открыть кадр');
        if (revoke) URL.revokeObjectURL(url);
        resolve(false);
      };
      im.src = url;
    });
  }
  function loadVideoFirstFrame(file){
    return new Promise(function(resolve){
      const url = URL.createObjectURL(file);
      const v = document.createElement('video');
      v.muted = true;
      v.playsInline = true;
      v.preload = 'auto';
      let done = false;
      function finish(ok){
        if (done) return;
        done = true;
        try { v.pause(); } catch(e){}
        v.removeAttribute('src');
        try { v.load(); } catch(e){}
        URL.revokeObjectURL(url);
        resolve(ok);
      }
      v.addEventListener('loadeddata', function(){
        try {
          // seek a tiny bit to ensure frame is painted
          try { v.currentTime = Math.min(0.05, (v.duration || 1) * 0.01); } catch(e){}
          setTimeout(function(){
            try {
              const c = document.createElement('canvas');
              const w = v.videoWidth || 640;
              const h = v.videoHeight || 360;
              c.width = w; c.height = h;
              const cx = c.getContext('2d');
              cx.drawImage(v, 0, 0, w, h);
              const dataUrl = c.toDataURL('image/jpeg', 0.92);
              loadFromImageUrl(dataUrl, false).then(function(ok){
                if (ok) tip('Превью: первый кадр видео. Таскай watermark — позиция применится ко всем кадрам.');
                finish(ok);
              });
            } catch (err) {
              tip('Не удалось взять кадр из видео');
              finish(false);
            }
          }, 120);
        } catch (e) { finish(false); }
      });
      v.addEventListener('error', function(){ tip('Браузер не смог открыть видео'); finish(false); });
      v.src = url;
      try { v.load(); } catch(e){}
    });
  }
  function loadFile(file){
    if (!file) return Promise.resolve(false);
    const name = (file.name || '').toLowerCase();
    const type = (file.type || '').toLowerCase();
    const isVideo = type.startsWith('video/') || /\\.(mp4|webm|mov|avi|mkv)$/i.test(name);
    if (isVideo) return loadVideoFirstFrame(file);
    // gif / images — Image handles first frame of GIF
    const url = URL.createObjectURL(file);
    return loadFromImageUrl(url, true).then(function(ok){
      if (ok && (type.indexOf('gif') >= 0 || name.endsWith('.gif'))) {
        tip('Превью: первый кадр GIF. Таскай watermark — позиция применится ко всем кадрам.');
      }
      return ok;
    });
  }

  window.__wmLoadFromFiles = function(){
    const f = firstImageFile();
    if (f) loadFile(f);
  };

  function savePos(){
    const elx = document.getElementById('wmX');
    const ely = document.getElementById('wmY');
    if (elx) elx.value = wx.toFixed(4);
    if (ely) ely.value = wy.toFixed(4);
  }

  document.getElementById('btnWmManual')?.addEventListener('click', async function(){
    const f = firstImageFile();
    if (!f && !img) {
      tip('Файл не найден в списке. Удали и добавь PNG/JPG ещё раз.');
      return;
    }
    if (f) await loadFile(f);
    await ensureFont(fontKey());
    draw();
    tip('Таскай watermark мышкой по картинке. Позиция сохранится для «Обработать».');
  });

  document.getElementById('btnWmReset')?.addEventListener('click', function(){
    wx = 0.04; wy = 0.88;
    const elx = document.getElementById('wmX');
    const ely = document.getElementById('wmY');
    if (elx) elx.value = '';
    if (ely) ely.value = '';
    draw();
    tip('Позиция сброшена — будет использован выбранный угол WM.');
  });

  function pointerPos(e){
    const r = canvas.getBoundingClientRect();
    return {
      x: (e.clientX - r.left) / Math.max(1, r.width),
      y: (e.clientY - r.top) / Math.max(1, r.height)
    };
  }
  canvas.addEventListener('pointerdown', function(e){
    if (!img || window.__watermarkIsPro === false) return;
    e.preventDefault();
    dragging = true;
    try { canvas.setPointerCapture(e.pointerId); } catch(err){}
    canvas.style.cursor = 'grabbing';
    const p = pointerPos(e);
    wx = Math.max(0, Math.min(0.98, p.x));
    wy = Math.max(0, Math.min(0.92, p.y));
    draw();
  });
  canvas.addEventListener('pointermove', function(e){
    if (!dragging) return;
    e.preventDefault();
    const p = pointerPos(e);
    wx = Math.max(0, Math.min(0.98, p.x));
    wy = Math.max(0, Math.min(0.92, p.y));
    draw();
  });
  function endDrag(){
    if (!dragging) return;
    dragging = false;
    canvas.style.cursor = 'grab';
    savePos();
  }
  canvas.addEventListener('pointerup', endDrag);
  canvas.addEventListener('pointercancel', endDrag);

  ['wmText','wmOpacity','wmScale','wmColor','wmEnable'].forEach(function(id){
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('input', draw);
    el.addEventListener('change', draw);
  });
  document.getElementById('wmFont')?.addEventListener('change', function(){
    ensureFont(fontKey()).then(draw);
  });
  document.getElementById('wmOpacity')?.addEventListener('input', function(){
    const v = parseInt(document.getElementById('wmOpacity').value,10);
    if (v > 45) tip('Прозрачность высокая — для незаметного watermark лучше 15–25%.');
  });

  document.getElementById('btnWmServerPreview')?.addEventListener('click', async function(){
    const f = firstImageFile();
    if (!f) { tip('Добавь PNG/JPG в «Файлы»'); return; }
    const fd = new FormData();
    fd.append('file', f);
    fd.append('wm_text', textVal());
    fd.append('wm_font', fontKey());
    fd.append('wm_opacity', document.getElementById('wmOpacity')?.value || '22');
    fd.append('wm_corner', document.getElementById('wmCorner')?.value || 'bl');
    let sc = scaleVal();
    fd.append('wm_scale', String(sc));
    fd.append('wm_color', colorVal());
    fd.append('wm_x', document.getElementById('wmX')?.value || '');
    fd.append('wm_y', document.getElementById('wmY')?.value || '');
    fd.append('auto_contrast', document.getElementById('autoContrast')?.checked ? '1' : '0');
    tip('Серверное превью…');
    try {
      const r = await fetch('/api/preview_wm', { method:'POST', body: fd, credentials:'include' });
      if (!r.ok) { tip('Ошибка превью'); return; }
      const sug = r.headers.get('X-WM-Suggestion');
      tip(sug || 'Серверное превью (точный шрифт с сервера)');
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const im = new Image();
      im.onload = function(){ img = im; draw(); };
      im.src = url;
    } catch (e) { tip(String(e)); }
  });

  // Publish to gallery
  document.getElementById('btnPublishGallery')?.addEventListener('click', async function(){
    const f = firstImageFile();
    const ru = (localStorage.getItem('sm_lang') === 'ru');
    if (!f) {
      alert(ru ? 'Нет файла для публикации' : 'No file to publish');
      return;
    }
    const title = prompt(ru ? 'Название для галереи (необязательно):' : 'Gallery title (optional):', '') || '';
    const fd = new FormData();
    fd.append('file', f);
    fd.append('mode', (window.state && window.state.mode) || 'workshop');
    fd.append('size', document.getElementById('size')?.value || '750');
    fd.append('wm_text', textVal());
    fd.append('wm_font', fontKey());
    fd.append('wm_opacity', document.getElementById('wmOpacity')?.value || '22');
    fd.append('wm_enable', enabled() ? '1' : '0');
    fd.append('wm_corner', document.getElementById('wmCorner')?.value || 'bl');
    fd.append('wm_scale', String(scaleVal()));
    fd.append('wm_color', colorVal());
    fd.append('wm_x', document.getElementById('wmX')?.value || '');
    fd.append('wm_y', document.getElementById('wmY')?.value || '');
    fd.append('auto_contrast', document.getElementById('autoContrast')?.checked ? '1' : '0');
    fd.append('title', title);
    const btn = document.getElementById('btnPublishGallery');
    const labelDefault = ru ? 'Опубликовать в галерею' : 'Publish to gallery';
    if (btn) {
      btn.disabled = true;
      btn.style.display = 'inline-flex';
      btn.textContent = ru ? 'Отправка…' : 'Sending…';
    }
    try {
      const hdr = {};
      try {
        const s = localStorage.getItem('sm_session') || '';
        if (s) hdr['X-Session-Token'] = s;
      } catch(e){}
      const r = await fetch('/api/gallery/publish', { method:'POST', body: fd, credentials:'include', headers: hdr });
      const d = await r.json().catch(function(){ return {}; });
      if (!r.ok || !d.ok) {
        alert(d.msg || 'Publish failed');
        if (btn) btn.textContent = labelDefault;
      } else {
        alert(ru ? 'Опубликовано в галерее: /gallery' : 'Published to gallery: /gallery');
        if (btn) btn.textContent = ru ? 'Опубликовано ✓' : 'Published ✓';
        setTimeout(function(){
          if (btn) btn.textContent = labelDefault;
        }, 2500);
      }
    } catch (e) {
      alert(String(e));
      if (btn) btn.textContent = labelDefault;
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.style.display = 'inline-flex';
      }
    }
  });

  async function startDiscord(){
    try {
      const r = await fetch('/api/auth/discord/login');
      const d = await r.json();
      if (!d.ok || !d.url) { alert(d.msg || 'Discord не настроен'); return; }
      window.open(d.url, 'discord_oauth', 'width=520,height=720');
    } catch (e) { alert(String(e)); }
  }
  document.getElementById('authDiscord')?.addEventListener('click', startDiscord);
  document.getElementById('btnDiscordLogin')?.addEventListener('click', startDiscord);

  document.getElementById('authTelegram')?.addEventListener('click', async function(){
    try {
      const r = await fetch('/api/auth/telegram/config');
      const d = await r.json();
      if (!d.ok || !d.bot_username) { alert(d.msg || 'Telegram not configured'); return; }
      const host = document.getElementById('tgWidgetHost');
      if (!host) return;
      host.style.display = 'block';
      host.innerHTML = '';
      window.onTelegramAuth = async function(user){
        try {
          const res = await fetch('/api/auth/telegram', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            credentials: 'include',
            body: JSON.stringify(user)
          });
          const j = await res.json();
          if (!j.ok || !j.token) { alert(j.msg || 'Telegram auth failed'); return; }
          try { localStorage.setItem('sm_session', j.token); } catch(e){}
          location.reload();
        } catch(e) { alert(String(e)); }
      };
      const s = document.createElement('script');
      s.async = true;
      s.src = 'https://telegram.org/js/telegram-widget.js?22';
      s.setAttribute('data-telegram-login', d.bot_username);
      s.setAttribute('data-size', 'large');
      s.setAttribute('data-radius', '12');
      s.setAttribute('data-request-access', 'write');
      s.setAttribute('data-userpic', 'true');
      s.setAttribute('data-onauth', 'onTelegramAuth(user)');
      host.appendChild(s);
    } catch(e) { alert(String(e)); }
  });
  window.addEventListener('message', function(ev){
    if (ev.data && (ev.data.type === 'discord_login' || ev.data.type === 'telegram_login') && ev.data.token) {
      try { localStorage.setItem('sm_session', ev.data.token); } catch(e) {}
      location.reload();
    }
  });

  setTimeout(function(){ window.__wmLoadFromFiles && window.__wmLoadFromFiles(); }, 400);
})();
// app.html L4779-5254
(function(){
  let lastBlob = null;
  let lastName = 'composed.png';
  const st = document.getElementById('composeStatus');
  const prev = document.getElementById('composePreview');
  const empty = document.getElementById('composeEmpty');
  const dl = document.getElementById('composeDl');
  const toProc = document.getElementById('btnComposeToProcess');

  // Click final preview → open full size in new tab
  if (prev) {
    prev.addEventListener('click', function() {
      const src = prev.getAttribute('src') || (lastBlob && lastBlob._url);
      if (src) window.open(src, '_blank', 'noopener');
    });
  }

  /* ── Live canvas preview ─────────────────────────────────── */
  const liveCanvas = document.getElementById('composeLiveCanvas');
  const liveEmpty  = document.getElementById('composeLiveEmpty');
  const liveCtx    = liveCanvas ? liveCanvas.getContext('2d') : null;
  let bgImg  = null;
  let charImg = null;
  let redrawPending = false;
  let animationPreviewRunning = false;
  // last placement on canvas (display px) for hit-testing
  let lastLayout = null; // { dispScale, bw, bh, ax, ay, nw, nh, dx, dy, dw, dh }
  let dragMode = null;   // 'move' | 'scale' | null
  let dragStart = null;

  function scaleVal() {
    return Math.max(0.1, Math.min(4.0, (parseInt(document.getElementById('composeScale')?.value || '100', 10) || 100) / 100));
  }
  function oxVal() {
    return Math.max(0, Math.min(1, (parseInt(document.getElementById('composeOx')?.value || '50', 10) || 50) / 100));
  }
  function oyVal() {
    return Math.max(0, Math.min(1, (parseInt(document.getElementById('composeOy')?.value || '100', 10) || 100) / 100));
  }
  function targetWidth() {
    return parseInt(document.getElementById('composeWidth')?.value || '750', 10) || 750;
  }

  function setScalePct(pct) {
    pct = Math.max(10, Math.min(400, Math.round(pct)));
    const el = document.getElementById('composeScale');
    if (el) el.value = String(pct);
  }
  function setOx(v) {
    v = Math.max(0, Math.min(1, v));
    const el = document.getElementById('composeOx');
    if (el) el.value = String(Math.round(v * 100));
  }
  function setOy(v) {
    v = Math.max(0, Math.min(1, v));
    const el = document.getElementById('composeOy');
    if (el) el.value = String(Math.round(v * 100));
  }

  function updateRangeLabels() {
    const s = document.getElementById('composeScaleVal');
    const ox = document.getElementById('composeOxVal');
    const oy = document.getElementById('composeOyVal');
    const tol = document.getElementById('composeTolVal');
    const fe = document.getElementById('composeFeatherVal');
    if (s) s.textContent = Math.round(scaleVal() * 100) + '%';
    if (ox) ox.textContent = oxVal().toFixed(2);
    if (oy) oy.textContent = oyVal().toFixed(2);
    if (tol) tol.textContent = document.getElementById('composeTol')?.value || '45';
    if (fe) {
      const raw = parseInt(document.getElementById('composeFeather')?.value || '16', 10) || 0;
      fe.textContent = (raw / 10).toFixed(1);
    }
  }

  function scheduleRedraw() {
    if (redrawPending) return;
    redrawPending = true;
    requestAnimationFrame(function() {
      redrawPending = false;
      drawLive();
    });
  }

  function mediaWidth(media) {
    return media ? (media.videoWidth || media.naturalWidth || media.width || 0) : 0;
  }
  function mediaHeight(media) {
    return media ? (media.videoHeight || media.naturalHeight || media.height || 0) : 0;
  }

  function ensureAnimationPreview() {
    if (animationPreviewRunning) return;
    animationPreviewRunning = true;
    function tick() {
      if (!bgImg && !charImg) { animationPreviewRunning = false; return; }
      drawLive();
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  }

  function computePlacement(bw, bh) {
    const sc = scaleVal();
    const ox = oxVal();
    const oy = oyVal();
    let targetH = Math.max(1, Math.round(bh * 0.85 * sc));
    let r = targetH / Math.max(1, mediaHeight(charImg));
    let nw = Math.max(1, Math.round(mediaWidth(charImg) * r));
    let nh = Math.max(1, targetH);
    let ax = Math.round(bw * ox - nw / 2);
    let ay = Math.round(bh * oy - nh);
    return { ax: ax, ay: ay, nw: nw, nh: nh, sc: sc, ox: ox, oy: oy };
  }

  function drawLive() {
    if (!liveCanvas || !liveCtx) return;
    updateRangeLabels();
    lastLayout = null;

    if (!bgImg || !mediaWidth(bgImg)) {
      liveCanvas.style.display = 'none';
      if (liveEmpty) liveEmpty.style.display = 'flex';
      return;
    }
    if (liveEmpty) liveEmpty.style.display = 'none';
    liveCanvas.style.display = 'block';
    liveCanvas.style.cursor = 'default';
    liveCanvas.style.touchAction = 'none';

    const tw = targetWidth();
    const ratio = mediaHeight(bgImg) / mediaWidth(bgImg);
    const bw = tw;
    const bh = Math.max(1, Math.round(tw * ratio));

    const maxDispW = Math.min(400, (liveCanvas.parentElement?.clientWidth || 360) - 4);
    const dispScale = maxDispW / bw;
    const cw = Math.round(bw * dispScale);
    const ch = Math.round(bh * dispScale);
    if (liveCanvas.width !== cw || liveCanvas.height !== ch) {
      liveCanvas.width = cw;
      liveCanvas.height = ch;
    }

    liveCtx.clearRect(0, 0, cw, ch);
    liveCtx.drawImage(bgImg, 0, 0, cw, ch);

    if (!charImg || !mediaWidth(charImg)) return;

    const p = computePlacement(bw, bh);
    const dx = p.ax * dispScale;
    const dy = p.ay * dispScale;
    const dw = p.nw * dispScale;
    const dh = p.nh * dispScale;

    liveCtx.drawImage(charImg, dx, dy, dw, dh);

    // selection frame + scale handle (bottom-right)
    liveCtx.save();
    liveCtx.strokeStyle = 'rgba(0,210,255,.85)';
    liveCtx.lineWidth = 1.5;
    liveCtx.setLineDash([5, 4]);
    liveCtx.strokeRect(dx + 0.5, dy + 0.5, Math.max(1, dw - 1), Math.max(1, dh - 1));
    liveCtx.setLineDash([]);
    const hs = 10;
    const hx = dx + dw - hs / 2;
    const hy = dy + dh - hs / 2;
    liveCtx.fillStyle = 'rgba(0,210,255,.95)';
    liveCtx.strokeStyle = 'rgba(0,0,0,.5)';
    liveCtx.lineWidth = 1;
    liveCtx.beginPath();
    liveCtx.rect(hx, hy, hs, hs);
    liveCtx.fill();
    liveCtx.stroke();
    // corner cue
    liveCtx.strokeStyle = 'rgba(255,255,255,.9)';
    liveCtx.beginPath();
    liveCtx.moveTo(hx + 2, hy + hs - 2);
    liveCtx.lineTo(hx + hs - 2, hy + hs - 2);
    liveCtx.lineTo(hx + hs - 2, hy + 2);
    liveCtx.stroke();
    liveCtx.restore();

    lastLayout = {
      dispScale: dispScale, bw: bw, bh: bh,
      ax: p.ax, ay: p.ay, nw: p.nw, nh: p.nh,
      dx: dx, dy: dy, dw: dw, dh: dh,
      hx: hx, hy: hy, hs: hs
    };
  }

  function canvasPos(e) {
    const r = liveCanvas.getBoundingClientRect();
    return {
      x: (e.clientX - r.left) * (liveCanvas.width / Math.max(1, r.width)),
      y: (e.clientY - r.top) * (liveCanvas.height / Math.max(1, r.height))
    };
  }

  function hitHandle(pos, L) {
    if (!L) return false;
    const pad = 6;
    return pos.x >= L.hx - pad && pos.x <= L.hx + L.hs + pad &&
           pos.y >= L.hy - pad && pos.y <= L.hy + L.hs + pad;
  }
  function hitChar(pos, L) {
    if (!L) return false;
    return pos.x >= L.dx && pos.x <= L.dx + L.dw &&
           pos.y >= L.dy && pos.y <= L.dy + L.dh;
  }

  if (liveCanvas) {
    liveCanvas.addEventListener('pointerdown', function(e) {
      if (!lastLayout || !charImg) return;
      const pos = canvasPos(e);
      const L = lastLayout;
      if (hitHandle(pos, L)) {
        dragMode = 'scale';
        dragStart = { x: pos.x, y: pos.y, sc: scaleVal(), nw: L.nw, nh: L.nh, bw: L.bw, bh: L.bh };
        liveCanvas.setPointerCapture(e.pointerId);
        liveCanvas.style.cursor = 'nwse-resize';
        e.preventDefault();
        return;
      }
      if (hitChar(pos, L)) {
        dragMode = 'move';
        dragStart = {
          x: pos.x, y: pos.y,
          ox: oxVal(), oy: oyVal(),
          dispScale: L.dispScale, bw: L.bw, bh: L.bh, nw: L.nw, nh: L.nh
        };
        liveCanvas.setPointerCapture(e.pointerId);
        liveCanvas.style.cursor = 'grabbing';
        e.preventDefault();
      }
    });

    liveCanvas.addEventListener('pointermove', function(e) {
      if (!lastLayout) return;
      const pos = canvasPos(e);
      if (!dragMode) {
        if (hitHandle(pos, lastLayout)) liveCanvas.style.cursor = 'nwse-resize';
        else if (hitChar(pos, lastLayout)) liveCanvas.style.cursor = 'grab';
        else liveCanvas.style.cursor = 'default';
        return;
      }
      e.preventDefault();
      if (dragMode === 'move' && dragStart) {
        const ddx = (pos.x - dragStart.x) / dragStart.dispScale;
        const ddy = (pos.y - dragStart.y) / dragStart.dispScale;
        // ox/oy are anchor fractions; character bottom-center
        // ax = bw*ox - nw/2  →  ox = (ax + nw/2) / bw
        const ax0 = dragStart.bw * dragStart.ox - dragStart.nw / 2;
        const ay0 = dragStart.bh * dragStart.oy - dragStart.nh;
        const ax1 = ax0 + ddx;
        const ay1 = ay0 + ddy;
        setOx((ax1 + dragStart.nw / 2) / dragStart.bw);
        setOy((ay1 + dragStart.nh) / dragStart.bh);
        scheduleRedraw();
      } else if (dragMode === 'scale' && dragStart) {
        // scale by drag distance from start (diagonal)
        const dist = (pos.x - dragStart.x) + (pos.y - dragStart.y);
        const factor = 1 + dist / 180;
        const newSc = Math.max(0.1, Math.min(4.0, dragStart.sc * factor));
        setScalePct(newSc * 100);
        scheduleRedraw();
      }
    });

    function endDrag(e) {
      if (!dragMode) return;
      dragMode = null;
      dragStart = null;
      try { liveCanvas.releasePointerCapture(e.pointerId); } catch (err) {}
      liveCanvas.style.cursor = 'default';
    }
    liveCanvas.addEventListener('pointerup', endDrag);
    liveCanvas.addEventListener('pointercancel', endDrag);

    // wheel = scale (keep anchor)
    liveCanvas.addEventListener('wheel', function(e) {
      if (!charImg || !bgImg) return;
      e.preventDefault();
      const delta = e.deltaY > 0 ? -0.06 : 0.06;
      const newSc = Math.max(0.1, Math.min(4.0, scaleVal() + delta));
      setScalePct(newSc * 100);
      scheduleRedraw();
    }, { passive: false });
  }

  function loadImageFromFile(file) {
    return new Promise(function(resolve) {
      if (!file) return resolve(null);
      const name = (file.name || '').toLowerCase();
      const type = (file.type || '').toLowerCase();
      const isVideo = type.startsWith('video/') || /\.(mp4|webm|mov|avi|mkv|m4v)$/i.test(name);

      if (isVideo) {
        const url = URL.createObjectURL(file);
        const v = document.createElement('video');
        v.muted = true; v.playsInline = true; v.preload = 'auto'; v.loop = true;
        v.__objectUrl = url;
        v.addEventListener('loadeddata', function() {
          Promise.resolve(v.play()).catch(function(){});
          resolve(v);
        });
        v.addEventListener('error', function(){ URL.revokeObjectURL(url); resolve(null); }, { once: true });
        v.src = url;
        try { v.load(); } catch(e){}
        return;
      }

      // image / gif — browser shows first frame of GIF
      const url = URL.createObjectURL(file);
      const im = new Image();
      im.onload = function(){ URL.revokeObjectURL(url); resolve(im); };
      im.onerror = function(){ URL.revokeObjectURL(url); resolve(null); };
      im.src = url;
    });
  }

  async function onBgChange() {
    const f = document.getElementById('composeBg')?.files?.[0];
    const el = document.getElementById('composeBgName');
    if (el) el.textContent = f ? f.name : 'файл не выбран';
    if (bgImg && bgImg.__objectUrl) { try { bgImg.pause(); URL.revokeObjectURL(bgImg.__objectUrl); } catch(e){} }
    bgImg = f ? await loadImageFromFile(f) : null;
    ensureAnimationPreview();
    scheduleRedraw();
  }
  async function onCharChange() {
    const f = document.getElementById('composeChar')?.files?.[0];
    const el = document.getElementById('composeCharName');
    if (el) el.textContent = f ? f.name : 'файл не выбран';
    if (charImg && charImg.__objectUrl) { try { charImg.pause(); URL.revokeObjectURL(charImg.__objectUrl); } catch(e){} }
    charImg = f ? await loadImageFromFile(f) : null;
    ensureAnimationPreview();
    scheduleRedraw();
  }

  document.getElementById('btnComposeBg')?.addEventListener('click', function(e){
    e.preventDefault();
    document.getElementById('composeBg')?.click();
  });
  document.getElementById('btnComposeChar')?.addEventListener('click', function(e){
    e.preventDefault();
    document.getElementById('composeChar')?.click();
  });
  document.getElementById('composeBg')?.addEventListener('change', onBgChange);
  document.getElementById('composeChar')?.addEventListener('change', onCharChange);

  // Live update on any slider / width change
  ['composeScale','composeOx','composeOy','composeTol','composeFeather','composeWidth'].forEach(function(id){
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('input', scheduleRedraw);
    el.addEventListener('change', scheduleRedraw);
  });

  // Initial labels
  updateRangeLabels();

  /* ── Server compose (final) ──────────────────────────────── */
  document.getElementById('btnCompose')?.addEventListener('click', function(){
    const bg = document.getElementById('composeBg')?.files?.[0];
    const ch = document.getElementById('composeChar')?.files?.[0];
    if (!bg || !ch) {
      if (st) { st.className = 'status err'; st.textContent = 'Добавь оба файла: сначала фон, потом персонажа'; }
      return;
    }
    const fd = new FormData();
    fd.append('background', bg);
    fd.append('character', ch);
    fd.append('chroma_key', document.getElementById('composeChroma')?.value || 'auto');
    fd.append('chroma_tol', document.getElementById('composeTol')?.value || '55');
    fd.append('feather', String(((parseInt(document.getElementById('composeFeather')?.value || '16', 10) || 0) / 10)));
    fd.append('scale', String(scaleVal()));
    fd.append('offset_x', String(oxVal()));
    fd.append('offset_y', String(oyVal()));
    fd.append('width', document.getElementById('composeWidth')?.value || '750');
    fd.append('gif_encoder', document.getElementById('composeGifEncoder')?.value || 'gifski');
    fd.append('fps', document.getElementById('composeFps')?.value || '12');

    const prog = document.getElementById('composeProgress');
    const fill = document.getElementById('composeProgFill');
    const pctEl = document.getElementById('composeProgPct');
    const lab = document.getElementById('composeProgLabel');
    const sub = document.getElementById('composeProgSub');
    const btn = document.getElementById('btnCompose');
    let fake = 0;
    let tick = null;
    function setProg(pct, label, subText) {
      pct = Math.max(0, Math.min(100, Math.round(pct)));
      if (prog) prog.classList.add('show');
      if (fill) fill.style.width = pct + '%';
      if (pctEl) pctEl.textContent = pct + '%';
      if (lab && label != null) lab.textContent = label;
      if (sub) sub.textContent = subText || '';
    }
    function stopTick() { if (tick) { clearInterval(tick); tick = null; } }
    if (btn) btn.disabled = true;
    if (st) { st.className = 'status'; st.textContent = 'Склеиваем…'; }
    setProg(3, 'Загрузка файлов…', bg.name + ' + ' + ch.name);
    fake = 3;
    tick = setInterval(function(){
      if (fake < 90) {
        fake += (90 - fake) * 0.04 + 0.25;
        if (fake > 90) fake = 90;
        const stage = fake < 25 ? 'Загрузка…' : (fake < 55 ? 'Убираем фон / хромакей…' : 'Собираем кадры и GIF…');
        setProg(fake, stage, 'Это может занять 10–60 сек для видео');
      }
    }, 350);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/compose/start');
    xhr.responseType = 'json';
    xhr.withCredentials = true;
    xhr.upload.onprogress = function(ev){
      if (!ev.lengthComputable) return;
      const up = 5 + (ev.loaded / Math.max(1, ev.total)) * 20;
      fake = Math.max(fake, up);
      setProg(fake, 'Загрузка на сервер…', Math.round(ev.loaded/1024) + ' KB');
    };
    xhr.onload = async function(){
      stopTick();
      const body = xhr.response || {};
      if (xhr.status < 200 || xhr.status >= 300 || !body.ok || !body.job_id) {
        if (btn) btn.disabled = false;
        const msg = body.msg || ('HTTP ' + xhr.status);
        if (st) { st.className = 'status err'; st.textContent = msg; }
        setProg(0, 'Ошибка', String(msg).slice(0,80));
        return;
      }
      const jid = body.job_id;
      const labels = {queued:'В очереди…',prepare:'Подготовка…',decode:'Читаем медиа…',background:'Конвертируем фон…',character:'Конвертируем персонажа…',chromakey:'Удаляем фон и собираем кадры…',encode:'Кодируем GIF…',upload:'Сохраняем результат…'};
      try {
        while (true) {
          await new Promise(function(resolve){ setTimeout(resolve, 1200); });
          const response = await fetch('/api/compose/status/' + encodeURIComponent(jid), {credentials:'include', cache:'no-store'});
          const job = await response.json();
          if (!response.ok || !job.ok) throw new Error(job.msg || 'Задача потеряна');
          setProg(job.pct || 3, labels[job.stage] || 'Обрабатываем…', 'Можно оставить эту вкладку открытой');
          if (job.status === 'error') throw new Error(job.error || 'Ошибка обработки');
          if (job.status === 'done') {
            const result = await fetch('/api/compose/download/' + encodeURIComponent(jid), {credentials:'include', cache:'no-store'});
            if (!result.ok) { const e = await result.json().catch(function(){return {}}); throw new Error(e.msg || 'Не удалось скачать результат'); }
            const blob = await result.blob();
            lastBlob = blob;
            lastName = job.filename || (blob.type.includes('gif') ? 'composed.gif' : 'composed.png');
            const url = URL.createObjectURL(blob);
            lastBlob._url = url;
            if (prev) { prev.src = url; prev.style.display = 'block'; }
            if (empty) empty.style.display = 'none';
            if (dl) { dl.href = url; dl.download = lastName; dl.style.display = 'inline-flex'; }
            if (toProc) toProc.style.display = 'inline-flex';
            if (st) { st.className = 'status ok'; st.textContent = 'Готово! Скачай результат или отправь его в Обработку'; }
            setProg(100, 'Готово!', '');
            setTimeout(function(){ if (prog) prog.classList.remove('show'); }, 2500);
            break;
          }
        }
      } catch (error) {
        const msg = error && error.message ? error.message : String(error);
        if (st) { st.className = 'status err'; st.textContent = msg; }
        setProg(0, 'Ошибка', msg.slice(0,80));
      } finally {
        if (btn) btn.disabled = false;
      }
    };
    xhr.onerror = function(){
      stopTick();
      if (btn) btn.disabled = false;
      if (st) { st.className = 'status err'; st.textContent = 'Сеть / сервер недоступны'; }
      setProg(0, 'Ошибка', '');
    };
    xhr.send(fd);
  });

  document.getElementById('btnComposeToProcess')?.addEventListener('click', async function(){
    if (!lastBlob) return;
    try {
      const file = new File([lastBlob], lastName, { type: lastBlob.type || 'image/png' });
      if (window.state) {
        state.files = [file];
        try { renderFiles(); } catch(e){}
        try { window.__wmLoadFromFiles && window.__wmLoadFromFiles(); } catch(e){}
      }
      const btn = document.querySelector('#nav button[data-tab="process"]');
      if (btn) btn.click();
      if (st) { st.className = 'status ok'; st.textContent = 'Отправлено во вкладку Обработка'; }
    } catch (e) {
      if (st) { st.className = 'status err'; st.textContent = String(e); }
    }
  });
})();
