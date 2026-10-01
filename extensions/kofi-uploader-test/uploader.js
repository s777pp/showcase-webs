/* Queue page of the Ko-fi uploader prototype. Files stay in this tab; for each item it opens
   a Ko-fi tab, talks to kofi.js through a port and sends files in base64 chunks. */
(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const items = []; // {file, name, preview, previewUrl}
  let running = false, stopAsked = false;
  const SHOP = 'https://ko-fi.com/shop/settings?productType=0';
  const CHUNK = 3 * 1024 * 1024;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const stem = (name) => name.replace(/\.[^.]+$/, '');
  const norm = (s) => stem(s).toLowerCase().replace(/[^a-zа-я0-9]+/gi, '');

  function render() {
    const host = $('items');
    host.replaceChildren();
    items.forEach((item, index) => {
      const row = document.createElement('div'); row.className = 'item';
      const pic = item.previewUrl ? Object.assign(document.createElement('img'), { src: item.previewUrl, alt: '' }) : Object.assign(document.createElement('div'), { className: 'noimg', textContent: 'нет превью' });
      const meta = document.createElement('div'); meta.className = 'meta';
      const name = Object.assign(document.createElement('input'), { value: item.name });
      name.addEventListener('input', () => { item.name = name.value; });
      const info = document.createElement('small');
      info.textContent = item.file.name + ' · ' + (item.file.size / 1048576).toFixed(1) + ' MB' + (item.preview ? ' · превью: ' + item.preview.name : '');
      meta.append(name, info);
      const tools = document.createElement('div'); tools.className = 'tools';
      const pick = document.createElement('label'); pick.className = 'btn ghost'; pick.textContent = 'Превью';
      const input = Object.assign(document.createElement('input'), { type: 'file', accept: '.png,.jpg,.jpeg,.gif', hidden: true });
      input.addEventListener('change', () => { if (input.files[0]) setPreview(item, input.files[0]); render(); });
      pick.append(input);
      const remove = Object.assign(document.createElement('button'), { type: 'button', className: 'btn ghost', textContent: '×' });
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
    Array.from(e.target.files).forEach((file) => items.push({ file, name: stem(file.name).slice(0, 100), preview: null, previewUrl: '' }));
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
  $('clear').addEventListener('click', () => { if (!running) { items.length = 0; render(); } });

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
    for (let attempt = 0; attempt < 20; attempt++) {
      try {
        const port = chrome.tabs.connect(tabId, { name: 'kofi-uploader' });
        const api = makeApi(port);
        await api.call({ cmd: 'ping' }, 3000);
        return api;
      } catch (_) { await sleep(500); }
    }
    throw new Error('Could not talk to the Ko-fi page (are you logged in?)');
  }
  function makeApi(port) {
    let seq = 0; const waiting = new Map();
    port.onMessage.addListener((msg) => { const w = waiting.get(msg.id); if (w) { waiting.delete(msg.id); w(msg); } });
    port.onDisconnect.addListener(() => { waiting.forEach((w) => w({ ok: false, error: 'disconnected', disconnected: true })); waiting.clear(); });
    return {
      call(msg, timeout = 20 * 60 * 1000) {
        return new Promise((resolve, reject) => {
          const id = ++seq;
          const timer = setTimeout(() => { waiting.delete(id); reject(new Error('Ko-fi page did not answer')); }, timeout);
          waiting.set(id, (reply) => { clearTimeout(timer); reply.ok || reply.disconnected ? resolve(reply) : reject(new Error(reply.error || 'error')); });
          try { port.postMessage(Object.assign({ id }, msg)); } catch (e) { clearTimeout(timer); waiting.delete(id); reject(e); }
        });
      },
      port,
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
    await api.call({ cmd: 'fileEnd' });
  }
  const fillText = (template, item) => String(template || '').split('{name}').join(item.name);

  // ---------------------------------------------------------------- run
  async function uploadOne(item, index, total) {
    const line = log((index + 1) + '/' + total + ' · ' + item.name);
    line.dataset.base = line.textContent;
    const tab = await chrome.tabs.create({ url: SHOP, active: false });
    try {
      await waitTab(tab.id, (url) => url.startsWith('https://ko-fi.com/shop/settings'));
      let api = await connect(tab.id);
      line.textContent = line.dataset.base + ' — создаём товар';
      await api.call({ cmd: 'create', name: item.name, description: fillText($('description').value, item) }, 30000);
      await waitTab(tab.id, (url) => /\/shop\/items\/[0-9a-f-]+\/edit/i.test(url), 60000);
      api = await connect(tab.id);
      await api.call({ cmd: 'fill', summary: fillText($('summary').value, item), price: $('price').value, payWhatYouWant: $('pwyw').checked, published: $('published').checked });
      if (item.preview) await sendFile(api, 'preview', item.preview, line);
      await sendFile(api, 'asset', item.file, line);
      line.textContent = line.dataset.base + ' — сохраняем';
      const saved = await api.call({ cmd: 'save' }, 60000);
      let link = saved.link || '';
      if (!link) { try { const again = await connect(tab.id); link = (await again.call({ cmd: 'ping' }, 5000)).link || ''; } catch (_) {} }
      line.textContent = line.dataset.base + ' — готово ' + (link || '(ссылку не нашли — проверь товар в магазине)');
      line.className = 'ok';
      return link;
    } catch (error) {
      line.textContent = line.dataset.base + ' — ошибка: ' + error.message + ' (вкладка Ko-fi оставлена открытой для проверки)';
      line.className = 'bad';
      throw Object.assign(error, { keepTab: true });
    } finally {
      // On success the tab is closed; after an error it stays open so the item can be checked by hand.
      if (line.className === 'ok') chrome.tabs.remove(tab.id).catch(() => {});
    }
  }
  $('start').addEventListener('click', async () => {
    if (running || !items.length) { if (!items.length) log('Сначала добавь файлы.', 'bad'); return; }
    running = true; stopAsked = false; $('start').disabled = true; $('stop').disabled = false; $('log').replaceChildren(); $('result').hidden = true;
    const links = [];
    for (let i = 0; i < items.length; i++) {
      if (stopAsked) { log('Остановлено.'); break; }
      try { const link = await uploadOne(items[i], i, items.length); if (link) links.push(items[i].name + ' — ' + link); }
      catch (_) { /* logged; continue with the next item */ }
      if (i < items.length - 1 && !stopAsked) await sleep(Math.max(3, Number($('pause').value) || 8) * 1000);
    }
    running = false; $('start').disabled = false; $('stop').disabled = true;
    if (links.length) { $('links').value = links.join('\n'); $('result').hidden = false; }
    log('Готово: ' + links.length + ' из ' + items.length + '.', links.length === items.length ? 'ok' : 'bad');
  });
  $('stop').addEventListener('click', () => { stopAsked = true; $('stop').disabled = true; });
  $('copy').addEventListener('click', () => { navigator.clipboard.writeText($('links').value).then(() => log('Ссылки скопированы.', 'ok')); });
  render();
})();
