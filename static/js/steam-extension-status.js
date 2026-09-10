(function () {
  'use strict';

  const state = document.getElementById('steamExtensionState');
  const installAction = document.getElementById('steamExtensionAction');
  const uploadAction = document.getElementById('steamExtensionUpload');
  const launchStatus = document.getElementById('steamExtensionLaunchStatus');
  const modeSelect = document.getElementById('steamMode');
  const modeButtons = Array.from(document.querySelectorAll('[data-steam-upload-mode]'));
  if (!state || !installAction || !uploadAction || !modeSelect || !modeButtons.length) return;

  const EXTENSION_ID = 'nopmeakgeongafdhgmlpllalpcfpedej';
  const MIN_UPLOAD_VERSION = '0.9.8';
  let installed = false;
  let version = '';

  const ru = () => (window.SMLang && SMLang.get ? SMLang.get() : document.documentElement.lang) === 'ru';
  const text = () => ru() ? {
    checking: 'Проверяем расширение…', installed: 'Расширение подключено', missing: 'Расширение не найдено', outdated: 'Нужно обновить расширение',
    install: 'Установить расширение', update: 'Обновить расширение', upload: 'Загрузить через расширение',
    starting: 'Открываем загрузчик Steam…', opened: 'Страница Steam открыта. Выбери указанный файл.', failed: 'Не удалось запустить загрузку через расширение.'
  } : {
    checking: 'Checking extension…', installed: 'Extension connected', missing: 'Extension not detected', outdated: 'Extension update required',
    install: 'Install extension', update: 'Update extension', upload: 'Upload through extension',
    starting: 'Opening the Steam uploader…', opened: 'Steam is open. Choose the requested file.', failed: 'Could not start the extension upload.'
  };

  function versionAtLeast(value, minimum) {
    const current = String(value || '').split('.').map(Number);
    const required = String(minimum || '').split('.').map(Number);
    const length = Math.max(current.length, required.length);
    for (let index = 0; index < length; index += 1) {
      const left = Number.isFinite(current[index]) ? current[index] : 0;
      const right = Number.isFinite(required[index]) ? required[index] : 0;
      if (left !== right) return left > right;
    }
    return true;
  }

  function readyForUpload() {
    return installed && versionAtLeast(version, MIN_UPLOAD_VERSION);
  }

  function paint(status) {
    const copy = text();
    const ready = readyForUpload();
    const visibleStatus = installed && !ready ? 'outdated' : status;
    state.dataset.state = visibleStatus;
    state.querySelector('span').textContent = visibleStatus === 'installed'
      ? copy.installed + (version ? ' · v' + version : '')
      : copy[visibleStatus];
    uploadAction.textContent = copy.upload;
    uploadAction.disabled = !ready || visibleStatus === 'checking';
    installAction.hidden = ready;
    installAction.textContent = visibleStatus === 'outdated' ? copy.update : copy.install;
  }

  function bridgeMessage(message) {
    return new Promise((resolve, reject) => {
      const requestId = 'ssh-steam-tab-' + Date.now() + '-' + Math.random().toString(36).slice(2);
      let finished = false;
      const finish = (ok, value) => {
        if (finished) return;
        finished = true;
        clearTimeout(timer);
        window.removeEventListener('message', receive);
        ok ? resolve(value) : reject(value);
      };
      const receive = (event) => {
        const data = event.data || {};
        if (event.source === window && event.origin === location.origin && data.source === 'SSH_EXTENSION' && data.type === 'RESPONSE' && data.requestId === requestId) {
          finish(true, data.reply || {});
        }
      };
      window.addEventListener('message', receive);
      const timer = setTimeout(() => finish(false, new Error('bridge-unavailable')), 1500);
      window.postMessage({ source: 'SSH_SITE', type: 'REQUEST', requestId, payload: message }, location.origin);
    });
  }

  function directMessage(message) {
    return new Promise((resolve, reject) => {
      if (!window.chrome || !chrome.runtime || !chrome.runtime.sendMessage) return reject(new Error('extension-missing'));
      try {
        chrome.runtime.sendMessage(EXTENSION_ID, message, (reply) => {
          if (chrome.runtime.lastError) reject(chrome.runtime.lastError);
          else resolve(reply || {});
        });
      } catch (error) { reject(error); }
    });
  }

  const extensionMessage = (message) => bridgeMessage(message).catch(() => directMessage(message));

  async function pingExtension() {
    paint('checking');
    try {
      const reply = await extensionMessage({ type: 'PING' });
      installed = !!(reply && reply.ok);
      version = installed ? String(reply.version || '') : '';
    } catch (_) {
      installed = false;
      version = '';
    }
    paint(installed ? 'installed' : 'missing');
    return readyForUpload();
  }

  function selectMode(mode, notify) {
    if (!['workshop', 'featured', 'split'].includes(mode)) mode = 'workshop';
    modeButtons.forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.steamUploadMode === mode)));
    if (modeSelect.value !== mode) {
      modeSelect.value = mode;
      if (notify) modeSelect.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }

  function expectedFiles(mode) {
    if (mode === 'workshop') {
      return ['part_1', 'part_2', 'part_3', 'part_4', 'part_5'].map((name) => ({ name, width: 0, height: 0 }));
    }
    if (mode === 'featured') return [{ name: 'featured_630', width: 630, height: 0 }];
    return [
      { name: 'center_506', width: 506, height: 0 },
      { name: 'side_100', width: 100, height: 0 }
    ];
  }

  function uploadPayload() {
    const mode = ['workshop', 'featured', 'split'].includes(modeSelect.value) ? modeSelect.value : 'workshop';
    return {
      type: 'START_STEAM_UPLOAD',
      mode: mode === 'split' ? 'artwork' : mode,
      files: expectedFiles(mode),
      lang: ru() ? 'ru' : 'en'
    };
  }

  async function startUpload() {
    const copy = text();
    launchStatus.className = 'status steam-extension-card__launch-status';
    launchStatus.textContent = copy.starting;
    uploadAction.disabled = true;
    try { window.SMAnalytics && window.SMAnalytics.track('extension_launch_clicked', { mode:modeSelect.value }); } catch (_) {}
    try {
      const ping = await extensionMessage({ type: 'PING' });
      installed = !!(ping && ping.ok);
      version = installed ? String(ping.version || '') : '';
      if (!installed) throw new Error('extension-missing');
      if (!versionAtLeast(version, MIN_UPLOAD_VERSION)) {
        paint('outdated');
        throw new Error('extension-outdated');
      }
      const reply = await extensionMessage(uploadPayload());
      if (!reply || !reply.ok) throw new Error(reply && reply.error ? reply.error : 'upload-failed');
      launchStatus.className = 'status ok steam-extension-card__launch-status';
      launchStatus.textContent = copy.opened;
      try { window.SMAnalytics && window.SMAnalytics.track('extension_launch_confirmed', { mode:modeSelect.value }); } catch (_) {}
    } catch (_) {
      launchStatus.className = 'status err steam-extension-card__launch-status';
      launchStatus.textContent = copy.failed;
      if (!installed) paint('missing');
    } finally {
      uploadAction.disabled = !readyForUpload();
    }
  }

  modeButtons.forEach((button) => button.addEventListener('click', () => selectMode(button.dataset.steamUploadMode, true)));
  modeSelect.addEventListener('change', () => selectMode(modeSelect.value, false));
  uploadAction.addEventListener('click', startUpload);
  document.querySelector('#nav button[data-tab="steam"]')?.addEventListener('click', pingExtension);
  window.addEventListener('focus', () => { if (document.getElementById('tab-steam')?.classList.contains('active')) pingExtension(); });
  window.addEventListener('sm:langchange', () => paint(installed ? 'installed' : state.dataset.state || 'missing'));

  selectMode(modeSelect.value, false);
  pingExtension();
})();
