/* Queue page of the Ko-fi uploader. Files stay in this tab; for each product it opens a Ko-fi tab,
   talks to kofi.js through a port and sends files in base64 chunks. Shared settings (not the
   terms consent) are remembered in chrome.storage.local. */
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const items = []; // {file, name, preview, previewUrl, status: '' | 'ok' | 'bad', link}
  let running = false, stopAsked = false;
  const SHOP = 'https://ko-fi.com/shop/settings?productType=0';
  const CHUNK = 3 * 1024 * 1024;
  const SETTINGS = ['titleTemplate', 'summary', 'description', 'categories', 'price', 'pwyw', 'mode', 'pause'];
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const stem = (name) => name.replace(/\.[^.]+$/, '');
  const norm = (s) => stem(s).toLowerCase().replace(/[^a-zа-я0-9]+/gi, '');

  // ---------------------------------------------------------------- settings
  function readSettings() {
    const out = {};
    SETTINGS.forEach((key) => { const el = $(key); out[key] = el.type === 'checkbox' ? el.checked : el.value; });
    return out;
  }
  function saveSettings() { chrome.storage.local.set({ kofiUploaderSettings: readSettings() }); }
  chrome.storage.local.get('kofiUploaderSettings').then((data) => {
    const saved = data.kofiUploaderSettings || {};
    SETTINGS.forEach((key) => {
      if (!(key in saved)) return;
      const el = $(key); if (el.type === 'checkbox') el.checked = !!saved[key]; else el.value = saved[key];
    });
    render();
  });
  SETTINGS.forEach((key) => { $(key).addEventListener('change', () => { saveSettings(); render(); }); $(key).addEventListener('input', saveSettings); });

  const fill = (template, item) => String(template || '').split('{name}').join(item.name).split('{title}').join(title(item));
  function title(item) {
    const tpl = $('titleTemplate').value || '{name}';
    return tpl.split('{name}').join(item.name).trim().slice(0, 100) || item.name;
  }
  function categoryList() {
    return $('categories').value.split(',').map((s) => s.trim()).filter(Boolean).slice(0, 5);
  }

  // ---------------------------------------------------------------- queue
  function render() {
    const host = $('items');
    host.replaceChildren();
    items.forEach((item, index) => {
      const row = document.createElement('div'); row.className = 'item' + (item.status ? ' is-' + item.status : '');
      const pic = item.previewUrl ? Object.assign(document.createElement('img'), { src: item.previewUrl, alt: '' }) : Object.assign(document.createElement('div'), { className: 'noimg', textContent: 'нет превью' });
      const meta = document.createElement('div'); meta.className = 'meta';
      const name = Object.assign(document.createElement('input'), { value: item.name, disabled: running });
      const final = document.createElement('small'); final.className = 'final';
      name.addEventListener('input', () => { item.name = name.value; final.textContent = '→ ' + title(item); });
      final.textContent = '→ ' + title(item);
      const info = document.createElement('small');
      info.textContent = item.file.name + ' · ' + (item.file.size / 1048576).toFixed(1) + ' MB' + (item.preview ? ' · превью: ' + item.preview.name : '') +
        (item.status === 'ok' ? ' · загружен' : item.status === 'bad' ? ' · ошибка' : '');
      meta.append(name, final, info);
      const tools = document.createElement('div'); tools.className = 'tools';
      const pick = document.createElement('label'); pick.className = 'btn ghost'; pick.textContent = 'Превью';
      const input = Object.assign(document.createElement('input'), { type: 'file', accept: '.png,.jpg,.jpeg,.gif', hidden: true });
      input.addEventListener('change', () => { if (input.files[0]) setPreview(item, input.files[0]); render(); });
      pick.append(input);
      const remove = Object.assign(document.createElement('button'), { type: 'button', className: 'btn ghost', textContent: '×', title: 'Убрать', disabled: running });
      remove.addEventListener('click', () => { items.splice(index, 1); render(); });
      tools.append(pick, remove);
      row.append(pic, meta, tools);
      host.append(row);
    });
  }
  function setPreview(item, file) {
    if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
    item.preview = file; item.previewUrl = URL.createObjectURL(file);
  }
  $('assets').addEventListener('change', (e) => {
    Array.from(e.target.files).forEach((file) => items.push({ file, name: stem(file.name).slice(0, 100), preview: null, previewUrl: '', status: '' }));
    e.target.value = ''; render();
  });
  $('previews').addEventListener('change', (e) => {
    const images = Array.from(e.target.files);
    items.forEach((item) => {
      const match = images.find((img) => norm(img.name) === norm(item.file.name)) || images.find((img) => norm(img.name).includes(norm(item.file.name)) || norm(item.file.name).includes(norm(img.name)));
      if (match) setPreview(item, match);
    });
    if (items.length === 1 && images.length === 1 && !items[0].preview) setPreview(items[0], images[0]);
    e.target.value = ''; render();
  });
  $('clear').addEventListener('click', () => { if (!running) { items.length = 0; $('retry').hidden = true; render(); } });

  // ---------------------------------------------------------------- log
  function log(text, kind) { const li = document.createElement('li'); li.textContent = text; if (kind) li.className = kind; $('log').append(li); li.scrollIntoView({ block: 'nearest' }); return li; }

  // ---------------------------------------------------------------- tab + port helpers
  function waitTab(tabId, test, timeout = 60000) {
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { chrome.tabs.onUpdated.removeListener(listener); reject(new Error('Ko-fi page did not load in time')); }, timeout);
      function listener(id, change, tab) {
        if (id !== tabId || tab.status !== 'complete' || !test(tab.url || '')) return;
        clearTimeout(timer); chrome.tabs.onUpdated.removeListener(listener); resolve(tab);
      }
      chrome.tabs.onUpdated.addListener(listener);
      chrome.tabs.get(tabId).then((tab) => { if (tab.status === 'complete' && test(tab.url || '')) listener(tabId, {}, tab); }).catch(() => {});
    });
  }
  async function connect(tabId) {
    for (let attempt = 0; attempt < 30; attempt++) {
      try {
        const port = chrome.tabs.connect(tabId, { name: 'kofi-uploader' });
        const api = makeApi(port);
        await api.call({ cmd: 'ping' }, 3000);
        return api;
      } catch (_) { await sleep(500); }
    }
    throw new Error('Could not talk to the Ko-fi page');
  }
  function makeApi(port) {
    let seq = 0; const waiting = new Map();
    port.onMessage.addListener((msg) => { const w = waiting.get(msg.id); if (w) { waiting.delete(msg.id); w(msg); } });
    port.onDisconnect.addListener(() => { waiting.forEach((w) => w({ ok: false, error: 'disconnected', disconnected: true })); waiting.clear(); });
    return {
      call(msg, timeout = 35 * 60 * 1000) {
        return new Promise((resolve, reject) => {
          const id = ++seq;
          const timer = setTimeout(() => { waiting.delete(id); reject(new Error('Ko-fi page did not answer')); }, timeout);
          waiting.set(id, (reply) => { clearTimeout(timer); reply.ok || reply.disconnected ? resolve(reply) : reject(new Error(reply.error || 'error')); });
          try { port.postMessage(Object.assign({ id }, msg)); } catch (e) { clearTimeout(timer); waiting.delete(id); reject(e); }
        });
      },
    };
  }
  function toBase64(buffer) {
    const bytes = new Uint8Array(buffer); let binary = '';
    for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return btoa(binary);
  }
  async function sendFile(api, slot, file, line) {
    await api.call({ cmd: 'fileStart', slot, name: file.name, type: file.type, size: file.size });
    for (let offset = 0; offset < file.size; offset += CHUNK) {
      const chunk = await file.slice(offset, offset + CHUNK).arrayBuffer();
      await api.call({ cmd: 'fileChunk', data: toBase64(chunk) });
      line.textContent = line.dataset.base + ' — передаём ' + file.name + ' ' + Math.min(100, Math.round((offset + CHUNK) / file.size * 100)) + '%';
    }
    line.textContent = line.dataset.base + ' — Ko-fi загружает ' + file.name + '…';
    const done = await api.call({ cmd: 'fileEnd' });
    if (done.disconnected) throw new Error('Ko-fi page was closed or reloaded during the upload');
  }
  // After "Next step" Ko-fi opens /shop/items/add (the product exists only after saving); existing ones use /edit.
  const isEditor = (url) => /\/shop\/items\/(add|[0-9a-f-]+\/edit)/i.test(url);
  const isLogin = (url) => /\/account\/login|\/login/i.test(url);

  // ---------------------------------------------------------------- run
  async function checkLogin() {
    const tab = await chrome.tabs.create({ url: SHOP, active: false });
    try {
      const loaded = await waitTab(tab.id, (url) => url.startsWith('https://ko-fi.com/'), 45000);
      if (isLogin(loaded.url || '') || !(loaded.url || '').startsWith('https://ko-fi.com/shop/settings')) throw new Error('Войди на ko-fi.com в этом браузере и запусти снова.');
    } finally { chrome.tabs.remove(tab.id).catch(() => {}); }
  }

  async function uploadOne(item, index, total, settings) {
    const name = title(item);
    const line = log((index + 1) + '/' + total + ' · ' + name);
    line.dataset.base = line.textContent;
    // Foreground on purpose: in a background tab Ko-fi renders its Vue parts 15-20 s late and timers are throttled.
    const tab = await chrome.tabs.create({ url: SHOP, active: true });
    let ok = false;
    try {
      await waitTab(tab.id, (url) => url.startsWith('https://ko-fi.com/shop/settings'));
      let api = await connect(tab.id);
      line.textContent = line.dataset.base + ' — создаём товар';
      await api.call({ cmd: 'create', name, description: fill(settings.description, item) }, 30000);
      await waitTab(tab.id, isEditor, 60000);
      api = await connect(tab.id);
      line.textContent = line.dataset.base + ' — заполняем поля';
      await api.call({ cmd: 'fill', name, description: fill(settings.description, item), summary: fill(settings.summary, item), price: settings.price, payWhatYouWant: settings.pwyw });
      await api.call({ cmd: 'terms', accept: $('terms').checked });
      const cats = categoryList();
      if (cats.length) { line.textContent = line.dataset.base + ' — категории'; await api.call({ cmd: 'categories', names: cats }, 60000); }
      if (item.preview) await sendFile(api, 'preview', item.preview, line);
      else if (settings.mode === 'publish') throw new Error('для публикации Ko-fi нужно превью — добавь картинку или выбери «черновик»');
      await sendFile(api, 'asset', item.file, line);
      line.textContent = line.dataset.base + ' — сохраняем';
      const saved = await api.call({ cmd: 'save', publish: settings.mode === 'publish' }, 90000);
      if (!saved.disconnected) throw new Error('Ko-fi не открыл страницу товара после сохранения');
      const after = await waitTab(tab.id, (url) => url.startsWith('https://ko-fi.com/') && !isEditor(url), 60000);
      const link = (after.url || '').split('?')[0];
      item.link = /ko-fi\.com\/s\//.test(link) ? link : '';
      line.textContent = line.dataset.base + ' — готово ' + (item.link || '(ссылку не нашли — проверь товар в магазине)');
      line.className = 'ok';
      item.status = 'ok';
      ok = true;
    } catch (error) {
      line.textContent = line.dataset.base + ' — ошибка: ' + error.message + ' (вкладка Ko-fi оставлена открытой, чтобы проверить товар)';
      line.className = 'bad';
      item.status = 'bad';
    } finally {
      // On success the tab is closed; after an error it stays open so the product can be checked by hand.
      if (ok) chrome.tabs.remove(tab.id).catch(() => {});
    }
  }

  async function run(queue) {
    if (running) return;
    if (!queue.length) { log('Сначала добавь файлы.', 'bad'); return; }
    running = true; stopAsked = false;
    $('start').disabled = true; $('retry').hidden = true; $('stop').disabled = false; $('log').replaceChildren(); $('result').hidden = true;
    render();
    const settings = readSettings();
    try {
      if (settings.mode === 'publish' && !String(settings.description).trim()) throw new Error('Для публикации Ko-fi требует описание: заполни поле «Описание» или выбери «черновик».');
      if (settings.mode === 'publish' && !String(settings.summary).trim()) throw new Error('Для публикации Ko-fi требует краткое описание (Product summary).');
      if (categoryList().length < $('categories').value.split(',').filter((s) => s.trim()).length) log('Ko-fi разрешает до 5 категорий — взяты первые пять.');
      log('Проверяем вход в Ko-fi…');
      await checkLogin();
      for (let i = 0; i < queue.length; i++) {
        if (stopAsked) { log('Остановлено.'); break; }
        await uploadOne(queue[i], i, queue.length, settings);
        render();
        if (i < queue.length - 1 && !stopAsked) await sleep(Math.max(3, Number(settings.pause) || 8) * 1000);
      }
    } catch (error) {
      log(error.message, 'bad');
    }
    running = false; $('start').disabled = false; $('stop').disabled = true;
    chrome.tabs.getCurrent().then((me) => me && chrome.tabs.update(me.id, { active: true })).catch(() => {});
    const done = items.filter((i) => i.status === 'ok');
    const failed = items.filter((i) => i.status === 'bad');
    if (done.length) { $('links').value = done.map((i) => title(i) + ' — ' + (i.link || 'ссылка не найдена')).join('\n'); $('result').hidden = false; }
    $('retry').hidden = !failed.length;
    log('Готово: ' + done.length + ' из ' + items.length + (failed.length ? ', с ошибкой: ' + failed.length : '') + '.', failed.length ? 'bad' : 'ok');
    render();
  }

  $('start').addEventListener('click', () => run(items.filter((i) => i.status !== 'ok')));
  $('retry').addEventListener('click', () => run(items.filter((i) => i.status === 'bad')));
  $('stop').addEventListener('click', () => { stopAsked = true; $('stop').disabled = true; });
  $('copy').addEventListener('click', () => { navigator.clipboard.writeText($('links').value).then(() => log('Ссылки скопированы.', 'ok')); });
  render();
})();
