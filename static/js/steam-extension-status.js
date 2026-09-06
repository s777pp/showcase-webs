(function () {
  'use strict';
  const state = document.getElementById('steamExtensionState');
  const action = document.getElementById('steamExtensionAction');
  if (!state || !action) return;
  const EXTENSION_ID = 'nopmeakgeongafdhgmlpllalpcfpedej';
  let installed = false;
  let version = '';
  const ru = () => (window.SMLang && SMLang.get ? SMLang.get() : document.documentElement.lang) === 'ru';
  const text = () => ru() ? {
    checking: 'Проверяем расширение…', installed: 'Расширение подключено', missing: 'Расширение не найдено',
    action: 'Расширение установлено ✓', install: 'Установить расширение'
  } : {
    checking: 'Checking extension…', installed: 'Extension connected', missing: 'Extension not detected',
    action: 'Extension installed ✓', install: 'Install extension'
  };
  function paint(status) {
    const copy = text();
    state.dataset.state = status;
    state.querySelector('span').textContent = status === 'installed' ? copy.installed + (version ? ' · v' + version : '') : copy[status];
    action.textContent = status === 'installed' ? copy.action : copy.install;
    action.classList.toggle('is-installed', status === 'installed');
    action.setAttribute('aria-disabled', status === 'installed' ? 'true' : 'false');
  }
  function pingBridge() {
    paint('checking');
    const requestId = 'ssh-steam-tab-' + Date.now() + '-' + Math.random().toString(36).slice(2);
    let finished = false;
    const finish = (reply) => {
      if (finished) return;
      finished = true;
      clearTimeout(timer);
      window.removeEventListener('message', receive);
      installed = !!(reply && reply.ok);
      version = installed ? String(reply.version || '') : '';
      paint(installed ? 'installed' : 'missing');
    };
    const receive = (event) => {
      const data = event.data || {};
      if (event.source === window && event.origin === location.origin && data.source === 'SSH_EXTENSION' && data.type === 'RESPONSE' && data.requestId === requestId) finish(data.reply);
    };
    window.addEventListener('message', receive);
    const timer = setTimeout(() => {
      if (!window.chrome || !chrome.runtime || !chrome.runtime.sendMessage) return finish(null);
      try { chrome.runtime.sendMessage(EXTENSION_ID, { type: 'PING' }, reply => finish(chrome.runtime.lastError ? null : reply)); }
      catch (_) { finish(null); }
    }, 1500);
    window.postMessage({ source: 'SSH_SITE', type: 'REQUEST', requestId, payload: { type: 'PING' } }, location.origin);
  }
  window.addEventListener('message', event => {
    const data = event.data || {};
    if (event.source === window && event.origin === location.origin && data.source === 'SSH_EXTENSION' && data.type === 'READY') {
      installed = true; version = String(data.version || ''); paint('installed');
    }
  });
  document.querySelector('#nav button[data-tab="steam"]')?.addEventListener('click', pingBridge);
  window.addEventListener('focus', () => { if (document.getElementById('tab-steam')?.classList.contains('active')) pingBridge(); });
  window.addEventListener('sm:langchange', () => paint(installed ? 'installed' : state.dataset.state || 'missing'));
  pingBridge();
})();
