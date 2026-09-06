(function () {
  'use strict';

  const root = document.getElementById('steamCheckRoot');
  if (!root) return;

  const copy = {
    en: {
      nav: 'Steam Check', title: 'Steam Check', sub: 'Preflight inspection for finished Steam showcase files — Pro',
      gateTitle: 'Steam Check is a Pro tool', gateBody: 'Log in to a Pro account to inspect finished showcase files.', gateAction: 'Log in', buyPro: 'Get Pro',
      kicker: 'Preflight', inputTitle: 'Check finished files', inputBody: 'Upload a ZIP or separate PNG, JPG and GIF files. Nothing is modified.',
      modeLabel: 'Showcase type', modeAuto: 'Detect automatically', dropTitle: 'Drop the final set here', dropHint: 'ZIP or up to 20 files',
      run: 'Run checks', clear: 'Clear', emptyTitle: 'Steam admission report', emptyBody: 'The format, dimensions, weight, animation, HEX and completeness checks will appear here.',
      checking: 'Inspecting files…', ready: 'Ready for Steam', warn: 'Check warnings', fail: 'Not ready',
      files: 'Files', groups: 'Sets', problems: 'Problems', statusLine: '{groups} set(s) · {files} file(s)',
      remove: 'Remove', toProcess: 'Send originals to Process', newCheck: 'New check', downloadSet: 'Download ready set', safeFix: 'Fix names + HEX 21', fixing: 'Preparing a lossless fix…', fixed: 'Safe fix downloaded. No pixels or animation frames were changed.', zipNoTransfer: 'ZIP contents will be transferable when the repair stage is added.',
      uploadSteam: 'Upload through extension', chooseShowcases: 'Choose showcases', extensionMissing: 'Install SteamShowcase Helper to open the correct Steam uploader and apply long-showcase settings automatically.',
      installExtension: 'Install extension', extensionOld: 'Update SteamShowcase Helper to version 0.9.8 or newer.', extensionStarting: 'Opening Steam…', extensionFailed: 'The extension could not start the Steam upload.',
      mode: { auto: 'Auto', workshop: 'Workshop', featured: 'Featured', split: 'Artwork Split', unknown: 'Unknown set' },
      state: { pass: 'Passed', warn: 'Review', fail: 'Failed' },
      checks: { format: 'Format', geometry: 'Geometry', weight: 'Weight', animation: 'Animation', sync: 'Sync', hex21: 'HEX 21', set: 'Complete set', naming: 'Order' },
      issues: {
        empty: 'The file is empty.', unreadable: 'The image is damaged or cannot be read.', unsupported_format: 'Steam-ready output must be PNG, JPG or GIF.',
        file_too_large: 'The file exceeds 5 MB.', hex21_missing: 'HEX 21 is not applied.', animation_too_long: 'The animation is longer than 8 seconds.', too_many_frames: 'The animation contains too many frames.', auxiliary_not_for_upload: 'Auxiliary file — keep it for preview or storage, do not upload it to Steam.'
      },
      checkHelp: {
        format: 'One or more files are damaged or not PNG, JPG or GIF.', weight: 'Every final Steam file must be no larger than 5 MB.',
        animation: 'Animations longer than 8 seconds may require stronger compression to fit under 5 MB.', sync: 'Animated parts must have the same duration, frame count and FPS.',
        hex21: 'Apply HEX 21 to every final file before uploading it to Steam.', set: 'The selected showcase type does not have the required number of parts.',
        naming: 'Use the generated part names so the upload order is unambiguous.', geometry: 'The dimensions do not match the selected showcase type.'
      },
      requestFailed: 'Could not complete the check.', loginRequired: 'Log in to use Steam Check.', proRequired: 'Steam Check is available with Pro.', transferDone: 'Files were added to Process.'
    },
    ru: {
      nav: 'Steam Check', title: 'Готово для Steam', sub: 'Финальная проверка готовых файлов витрины — функция Pro',
      gateTitle: 'Steam Check доступен в Pro', gateBody: 'Войди в аккаунт с Pro, чтобы проверить готовые файлы витрины.', gateAction: 'Войти', buyPro: 'Получить Pro',
      kicker: 'Контроль перед загрузкой', inputTitle: 'Проверить готовые файлы', inputBody: 'Загрузи ZIP или отдельные PNG, JPG и GIF. Проверка ничего не изменяет.',
      modeLabel: 'Тип витрины', modeAuto: 'Определить автоматически', dropTitle: 'Перетащи готовый комплект', dropHint: 'ZIP или до 20 файлов',
      run: 'Начать проверку', clear: 'Очистить', emptyTitle: 'Отчёт допуска Steam', emptyBody: 'Здесь появятся формат, размеры, вес, анимация, HEX и комплектность файлов.',
      checking: 'Проверяем файлы…', ready: 'Готово для Steam', warn: 'Проверь замечания', fail: 'Не готово',
      files: 'Файлов', groups: 'Комплектов', problems: 'Проблем', statusLine: 'Комплектов: {groups} · файлов: {files}',
      remove: 'Удалить', toProcess: 'Передать исходники в Обработку', newCheck: 'Новая проверка', downloadSet: 'Скачать готовый комплект', safeFix: 'Исправить названия + HEX 21', fixing: 'Готовим исправление без потери качества…', fixed: 'Исправленный ZIP скачан. Пиксели и кадры анимации не изменялись.', zipNoTransfer: 'Передача содержимого ZIP появится вместе с этапом исправлений.',
      uploadSteam: 'Загрузить через расширение', chooseShowcases: 'Перейти к выбору витрин', extensionMissing: 'Установи SteamShowcase Helper: он откроет нужный загрузчик Steam и автоматически применит настройки длинной витрины.',
      installExtension: 'Установить расширение', extensionOld: 'Обнови SteamShowcase Helper до версии 0.9.8 или новее.', extensionStarting: 'Открываем Steam…', extensionFailed: 'Расширение не смогло начать загрузку в Steam.',
      mode: { auto: 'Авто', workshop: 'Workshop', featured: 'Featured', split: 'Artwork Split', unknown: 'Тип не определён' },
      state: { pass: 'Пройдено', warn: 'Проверить', fail: 'Ошибка' },
      checks: { format: 'Формат', geometry: 'Размеры', weight: 'Вес', animation: 'Анимация', sync: 'Синхронность', hex21: 'HEX 21', set: 'Комплект', naming: 'Порядок' },
      issues: {
        empty: 'Файл пустой.', unreadable: 'Изображение повреждено или не читается.', unsupported_format: 'Готовый файл для Steam должен быть PNG, JPG или GIF.',
        file_too_large: 'Файл превышает 5 МБ.', hex21_missing: 'Не применён HEX 21.', animation_too_long: 'Анимация длиннее 8 секунд.', too_many_frames: 'В анимации слишком много кадров.', auxiliary_not_for_upload: 'Вспомогательный файл — оставь для просмотра или хранения, в Steam его загружать не нужно.'
      },
      checkHelp: {
        format: 'Один или несколько файлов повреждены либо имеют формат не PNG, JPG или GIF.', weight: 'Каждый итоговый файл для Steam должен весить не больше 5 МБ.',
        animation: 'Анимация длиннее 8 секунд может потребовать более сильного сжатия, чтобы уложиться в 5 МБ.', sync: 'У анимированных частей должны совпадать длительность, количество кадров и FPS.',
        hex21: 'Перед загрузкой в Steam примени HEX 21 ко всем итоговым файлам.', set: 'Для выбранного типа витрины не хватает частей либо есть лишние.',
        naming: 'Используй имена с номерами частей, чтобы порядок загрузки был однозначным.', geometry: 'Размеры файлов не соответствуют выбранному типу витрины.'
      },
      requestFailed: 'Не удалось завершить проверку.', loginRequired: 'Войди, чтобы использовать Steam Check.', proRequired: 'Steam Check доступен только в Pro.', transferDone: 'Файлы добавлены в Обработку.'
    }
  };

  let selected = [];
  let quota = null;
  let lastReport = null;
  let resultDownload = '';
  const EXTENSION_ID = 'nopmeakgeongafdhgmlpllalpcfpedej';
  const EXTENSION_URL = 'https://chromewebstore.google.com/detail/steamshowcase-helper/' + EXTENSION_ID;
  const $ = (id) => document.getElementById(id);
  const esc = (value) => String(value == null ? '' : value).replace(/[&<>'"]/g, (ch) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  const language = () => (window.SMLang && SMLang.get ? SMLang.get() : document.documentElement.lang) === 'ru' ? 'ru' : 'en';
  const t = () => copy[language()];
  const bytes = (value) => {
    const n = Number(value || 0);
    if (n < 1024) return n + ' B';
    if (n < 1024 * 1024) return (n / 1024).toFixed(n < 10240 ? 1 : 0) + ' KB';
    return (n / 1024 / 1024).toFixed(2) + ' MB';
  };
  function bridgeMessage(message) {
    return new Promise((resolve, reject) => {
      const requestId = 'ssh-check-' + Date.now() + '-' + Math.random().toString(36).slice(2);
      let done = false;
      const finish = (ok, value) => {
        if (done) return;
        done = true;
        clearTimeout(timer);
        window.removeEventListener('message', receive);
        ok ? resolve(value) : reject(value);
      };
      const receive = (event) => {
        const data = event.data || {};
        if (event.source === window && event.origin === location.origin && data.source === 'SSH_EXTENSION' && data.type === 'RESPONSE' && data.requestId === requestId) finish(true, data.reply || {});
      };
      window.addEventListener('message', receive);
      const timer = setTimeout(() => finish(false, new Error('bridge-unavailable')), message.type === 'PING' ? 1300 : 10000);
      window.postMessage({ source: 'SSH_SITE', type: 'REQUEST', requestId, payload: message }, location.origin);
    });
  }
  function directMessage(message) {
    return new Promise((resolve, reject) => {
      if (!window.chrome || !chrome.runtime || !chrome.runtime.sendMessage) return reject(new Error('extension-missing'));
      try {
        chrome.runtime.sendMessage(EXTENSION_ID, message, (reply) => {
          if (chrome.runtime.lastError) reject(new Error(chrome.runtime.lastError.message));
          else resolve(reply || {});
        });
      } catch (error) { reject(error); }
    });
  }
  const extensionMessage = (message) => bridgeMessage(message).catch(() => directMessage(message));
  const versionAtLeast = (actual, wanted) => {
    const a = String(actual || '').split('.').map(Number), b = String(wanted).split('.').map(Number);
    for (let i = 0; i < Math.max(a.length, b.length); i++) {
      if ((a[i] || 0) !== (b[i] || 0)) return (a[i] || 0) > (b[i] || 0);
    }
    return true;
  };

  function applyLanguage() {
    const p = t();
    root.querySelectorAll('[data-sc]').forEach((node) => {
      const key = node.getAttribute('data-sc');
      if (p[key] != null) node.textContent = p[key];
    });
    const nav = document.querySelector('#nav button[data-tab="check"]');
    if (nav) nav.textContent = p.nav;
    if (nav && nav.classList.contains('active')) {
      if ($('pageTitle')) $('pageTitle').textContent = p.title;
      if ($('pageSub')) $('pageSub').textContent = p.sub;
    }
    if (quota) paintGate();
  }

  function paintGate() {
    const p = t();
    const integratedForAccount = root.dataset.integrated === '1' && quota && quota.email;
    const locked = !quota || (!quota.pro && !integratedForAccount);
    root.classList.toggle('is-locked', locked);
    $('steamCheckGate').hidden = !locked;
    if (!locked) return;
    const loggedIn = !!quota.email;
    root.querySelector('[data-sc="gateTitle"]').textContent = loggedIn ? p.proRequired : p.gateTitle;
    root.querySelector('[data-sc="gateBody"]').textContent = loggedIn ? p.gateBody : p.loginRequired;
    $('steamCheckGateAction').textContent = loggedIn ? p.buyPro : p.gateAction;
    $('steamCheckGateAction').onclick = () => {
      const target = $(loggedIn ? 'btnUpgrade' : 'btnAuth');
      if (target) target.click();
    };
  }

  async function refreshAccess() {
    try {
      const response = await fetch('/api/quota', { credentials: 'include' });
      quota = await response.json();
    } catch (_) {
      quota = { pro: false, email: '' };
    }
    paintGate();
  }

  function renderFiles() {
    const p = t();
    $('steamCheckFileList').innerHTML = selected.map((file, index) =>
      '<div class="steam-check__file"><span title="' + esc(file.name) + '">' + esc(file.name) + '</span><small>' + bytes(file.size) + '</small>' +
      '<button type="button" data-index="' + index + '" title="' + esc(p.remove) + '" aria-label="' + esc(p.remove) + '">×</button></div>'
    ).join('');
    $('steamCheckRun').disabled = selected.length === 0;
    $('steamCheckFileList').querySelectorAll('button').forEach((button) => {
      button.onclick = () => { selected.splice(Number(button.dataset.index), 1); renderFiles(); };
    });
  }

  function addFiles(files) {
    const allowed = /\.(zip|png|jpe?g|gif)$/i;
    for (const file of Array.from(files || [])) {
      if (allowed.test(file.name) && selected.length < 20) selected.push(file);
    }
    renderFiles();
  }

  function worstChecks(groups) {
    const rank = { pass: 0, warn: 1, fail: 2 };
    const all = {};
    groups.forEach((group) => group.checks.forEach((check) => {
      if (!all[check.id] || rank[check.state] > rank[all[check.id].state]) all[check.id] = check;
    }));
    return ['format','geometry','weight','animation','sync','hex21','set','naming'].map((id) => all[id] || { id, state: 'pass' });
  }

  function issueText(issue) {
    return t().issues[issue.code] || issue.code;
  }

  function renderReport(report) {
    const p = t();
    root.dataset.status = report.status;
    const verdict = p[report.status] || p.fail;
    const problemCount = Number(report.failures || 0) + Number(report.warnings || 0);
    const pipeline = worstChecks(report.groups).map((check) =>
      '<div class="steam-check__node" data-state="' + esc(check.state) + '"><i></i><b>' + esc(p.checks[check.id] || check.id) + '</b><small>' + esc(p.state[check.state]) + '</small></div>'
    ).join('');
    const groups = report.groups.map((group) => {
      const state = group.status === 'ready' ? 'pass' : group.status;
      const groupNotes = group.checks.filter((check) => check.state !== 'pass').map((check) =>
        '<li data-state="' + esc(check.state) + '"><b>' + esc(p.checks[check.id] || check.id) + ':</b> ' + esc(p.checkHelp[check.id] || '') + '</li>'
      ).join('');
      const files = group.files.map((file) => {
        const issues = (file.issues || []).map((issue) => '<div class="steam-check__issue ' + (issue.severity === 'fail' ? 'is-fail' : '') + '">' + esc(issueText(issue)) + '</div>').join('');
        const duration = file.animated ? (Number(file.duration_ms || 0) / 1000).toFixed(2) + 's · ' + file.frames + 'f · ' + Number(file.fps || 0).toFixed(1) + 'fps' : '—';
        const rowState = file.auxiliary ? ' is-auxiliary' : ((file.issues || []).some((issue) => issue.severity === 'fail') ? ' is-invalid' : '');
        return '<div class="steam-check__file-report' + rowState + '"><strong title="' + esc(file.name) + '">' + esc(file.name) + '</strong>' +
          '<span class="steam-check__datum">' + esc(file.format || '—') + '</span><span class="steam-check__datum">' + file.width + '×' + file.height + '</span>' +
          '<span class="steam-check__datum">' + bytes(file.size) + '</span><span class="steam-check__datum">' + esc(duration) + '</span>' + issues + '</div>';
      }).join('');
      return '<section class="steam-check__group"><header class="steam-check__group-head" data-state="' + esc(state) + '"><i class="steam-check__state"></i>' +
        '<strong title="' + esc(group.name) + '">' + esc(group.name) + '</strong><span class="steam-check__mode-tag">' + esc(p.mode[group.mode] || group.mode) + '</span></header>' +
        (groupNotes ? '<ul class="steam-check__group-notes">' + groupNotes + '</ul>' : '') + files + '</section>';
    }).join('');
    lastReport = report;
    const hasZip = selected.some((file) => /\.zip$/i.test(file.name));
    const uploadGroup = report.groups.find((group) => group.mode !== 'unknown' && group.status !== 'fail');
    const canSafeFix = quota && quota.pro && selected.length && report.groups.length && report.groups.every((group) => group.mode !== 'unknown');
    $('steamCheckResults').innerHTML =
      '<div class="steam-check__summary"><div class="steam-check__verdict"><small>STEAM / PREFLIGHT</small><strong>' + esc(verdict) + '</strong><span>' + esc(p.statusLine.replace('{groups}', report.group_count).replace('{files}', report.file_count)) + '</span></div>' +
      '<div class="steam-check__metrics"><div class="steam-check__metric"><b>' + report.file_count + '</b><span>' + esc(p.files) + '</span></div><div class="steam-check__metric"><b>' + report.group_count + '</b><span>' + esc(p.groups) + '</span></div><div class="steam-check__metric"><b>' + problemCount + '</b><span>' + esc(p.problems) + '</span></div></div></div>' +
      '<div class="steam-check__pipeline">' + pipeline + '</div><div class="steam-check__groups">' + groups + '</div>' +
      '<div class="steam-check__extension-note" id="steamCheckExtensionNote" hidden></div>' +
      '<div class="steam-check__result-actions">' + (resultDownload ? '<a class="btn" href="' + esc(resultDownload) + '">' + esc(p.downloadSet) + '</a>' : '') +
      (uploadGroup ? '<button class="btn" type="button" id="steamCheckUploadSteam">' + esc(p.uploadSteam) + '</button>' : '') +
      (canSafeFix ? '<button class="btn ghost" type="button" id="steamCheckSafeFix">' + esc(p.safeFix) + '</button>' : '') +
      '<button class="btn ghost" type="button" id="steamCheckChooseShowcases">' + esc(p.chooseShowcases) + '</button>' +
      (!resultDownload ? '<button class="btn ghost" type="button" id="steamCheckToProcess"' + (hasZip ? ' disabled title="' + esc(p.zipNoTransfer) + '"' : '') + '>' + esc(p.toProcess) + '</button>' : '') +
      '<button class="btn ghost" type="button" id="steamCheckAgain">' + esc(p.newCheck) + '</button></div>';
    $('steamCheckEmpty').hidden = true;
    $('steamCheckResults').hidden = false;
    $('steamCheckAgain').onclick = reset;
    if ($('steamCheckToProcess')) $('steamCheckToProcess').onclick = transferToProcess;
    if ($('steamCheckUploadSteam')) $('steamCheckUploadSteam').onclick = startSteamUpload;
    if ($('steamCheckSafeFix')) $('steamCheckSafeFix').onclick = runSafeFix;
    $('steamCheckChooseShowcases').onclick = openShowcasePicker;
  }

  async function runSafeFix() {
    if (!selected.length) return;
    const p = t();
    const button = $('steamCheckSafeFix');
    button.disabled = true;
    $('steamCheckStatus').className = 'status';
    $('steamCheckStatus').textContent = p.fixing;
    const body = new FormData();
    body.append('mode', $('steamCheckMode').value);
    selected.forEach((file) => body.append('files', file));
    try {
      const response = await fetch('/api/steam-check/fix-safe', { method: 'POST', body, credentials: 'include' });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.msg || p.requestFailed);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'steam_ready_safe_fix.zip';
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 30000);
      $('steamCheckStatus').className = 'status ok';
      $('steamCheckStatus').textContent = p.fixed;
    } catch (error) {
      $('steamCheckStatus').className = 'status err';
      $('steamCheckStatus').textContent = error && error.message ? error.message : p.requestFailed;
    } finally { button.disabled = false; }
  }

  function uploadPayload() {
    if (!lastReport) return null;
    const group = lastReport.groups.find((item) => item.mode !== 'unknown' && item.status !== 'fail');
    if (!group) return null;
    let files = group.files.filter((file) => !file.auxiliary);
    if (group.mode === 'workshop') files.sort((a, b) => String(a.name).localeCompare(String(b.name), undefined, { numeric: true }));
    if (group.mode === 'split') files.sort((a, b) => Number(b.width || 0) - Number(a.width || 0));
    return { type: 'START_STEAM_UPLOAD', mode: group.mode === 'split' ? 'artwork' : group.mode, files: files.map((file) => ({ name: file.name, width: file.width, height: file.height })), lang: language() };
  }
  function showExtensionOffer(message) {
    const note = $('steamCheckExtensionNote');
    if (!note) return;
    note.hidden = false;
    note.innerHTML = '<span>' + esc(message) + '</span><a href="' + esc(EXTENSION_URL) + '" target="_blank" rel="noopener">' + esc(t().installExtension) + '</a>';
  }
  async function startSteamUpload() {
    const payload = uploadPayload();
    if (!payload) return;
    const button = $('steamCheckUploadSteam');
    button.disabled = true;
    $('steamCheckStatus').textContent = t().extensionStarting;
    try {
      const ping = await extensionMessage({ type: 'PING' });
      if (!ping.ok) throw new Error('extension-missing');
      if (!versionAtLeast(ping.version, '0.9.8')) { showExtensionOffer(t().extensionOld); return; }
      const reply = await extensionMessage(payload);
      if (!reply.ok) throw new Error(reply.error || t().extensionFailed);
      $('steamCheckStatus').textContent = '';
    } catch (_) {
      showExtensionOffer(t().extensionMissing);
      $('steamCheckStatus').textContent = '';
    } finally { button.disabled = false; }
  }
  async function openShowcasePicker() {
    try {
      const reply = await extensionMessage({ type: 'OPEN_SHOWCASE_PICKER' });
      if (!reply.ok) throw new Error();
    } catch (_) {
      window.open('https://steamcommunity.com/my/edit/showcases', '_blank', 'noopener');
    }
  }

  function reset() {
    selected = [];
    lastReport = null;
    resultDownload = '';
    renderFiles();
    $('steamCheckStatus').textContent = '';
    $('steamCheckResults').hidden = true;
    $('steamCheckResults').innerHTML = '';
    $('steamCheckEmpty').hidden = false;
    root.removeAttribute('data-status');
  }

  function transferToProcess() {
    const p = t();
    if (selected.some((file) => /\.zip$/i.test(file.name))) return;
    try {
      if (typeof state !== 'undefined' && typeof window.renderFiles === 'function') {
        state.files = selected.slice();
        window.renderFiles();
        document.querySelector('#nav button[data-tab="process"]')?.click();
        window.scrollTo({ top: 0, behavior: 'smooth' });
        const status = $('status');
        if (status) { status.className = 'status ok'; status.textContent = p.transferDone; }
      }
    } catch (error) {
      $('steamCheckStatus').className = 'status err';
      $('steamCheckStatus').textContent = String(error);
    }
  }

  async function runCheck() {
    if (!selected.length) return;
    const p = t();
    $('steamCheckRun').disabled = true;
    $('steamCheckStatus').className = 'status';
    $('steamCheckStatus').textContent = p.checking;
    const body = new FormData();
    body.append('mode', $('steamCheckMode').value);
    selected.forEach((file) => body.append('files', file));
    try {
      const response = await fetch('/api/steam-check', { method: 'POST', body, credentials: 'include' });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.ok) {
        if (response.status === 401 || response.status === 403) await refreshAccess();
        throw new Error(payload.msg || p.requestFailed);
      }
      $('steamCheckStatus').textContent = '';
      renderReport(payload.report);
    } catch (error) {
      $('steamCheckStatus').className = 'status err';
      $('steamCheckStatus').textContent = error && error.message ? error.message : p.requestFailed;
    } finally {
      $('steamCheckRun').disabled = selected.length === 0;
    }
  }

  const drop = $('steamCheckDrop');
  const input = $('steamCheckFiles');
  drop.onclick = () => input.click();
  drop.onkeydown = (event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); input.click(); } };
  drop.ondragover = (event) => { event.preventDefault(); drop.classList.add('is-drag'); };
  drop.ondragleave = () => drop.classList.remove('is-drag');
  drop.ondrop = (event) => { event.preventDefault(); drop.classList.remove('is-drag'); addFiles(event.dataTransfer.files); };
  input.onchange = () => { addFiles(input.files); input.value = ''; };
  $('steamCheckRun').onclick = runCheck;
  $('steamCheckClear').onclick = reset;

  document.querySelector('#nav button[data-tab="check"]')?.addEventListener('click', () => {
    setTimeout(applyLanguage, 0);
    refreshAccess();
  });
  window.addEventListener('sm:langchange', applyLanguage);
  applyLanguage();
  renderFiles();
  refreshAccess();

  window.SteamCheckResult = {
    open(report, downloadUrl) {
      if (!report || !Array.isArray(report.groups)) return false;
      root.dataset.integrated = '1';
      resultDownload = String(downloadUrl || '');
      selected = [];
      renderFiles();
      const tab = document.querySelector('#nav button[data-tab="check"]');
      if (tab) tab.click();
      renderReport(report);
      paintGate();
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return true;
    }
  };
})();
