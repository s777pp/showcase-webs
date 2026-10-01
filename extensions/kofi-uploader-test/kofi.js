/* Runs on ko-fi.com/shop/* pages (isolated world). The uploader page drives it through a port:
   create      -> fill the "Add product" window (name, description, digital) and press "Next step"
   fill        -> on the item editor: name, description, summary, price, pay-what-you-want
   categories  -> pick up to 5 categories in Ko-fi's own window (creates missing ones)
   terms       -> tick "I agree with the shop terms" when a new item asks for it (only if the user allowed it)
   file*       -> receive a file in base64 chunks and drop it into Ko-fi's own uploader (preview
                  images or files for buyers); completion is read from Ko-fi's state via kofi-page.js
   save        -> call Ko-fi's saveShopItem(publish); Ko-fi then opens the product page
   Selectors were checked against the live editor on 2026-10-01. Nothing is sent anywhere except
   to Ko-fi by Ko-fi's own page. */
(function () {
  'use strict';
  if (window.__kofiUploaderReady) return;
  window.__kofiUploaderReady = true;

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  async function waitFor(check, timeout = 30000, step = 250) {
    const end = Date.now() + timeout;
    while (Date.now() < end) {
      const value = await check();
      if (value) return value;
      await sleep(step);
    }
    return null;
  }
  const visible = (el) => !!(el && (el.offsetWidth || el.offsetHeight || el.getClientRects().length));
  function setValue(el, value) {
    if (!el) return false;
    const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, value);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return true;
  }
  function setChecked(el, on) {
    if (!el || el.checked === !!on) return;
    el.click(); // the page's own handlers (pay-what-you-want, terms) react to clicks
  }

  // ---------------------------------------------------------------- page-world bridge (kofi-page.js)
  let seq = 0;
  // CustomEvents with JSON strings, never window.postMessage (a probe message froze the Ko-fi editor).
  function page(cmd, extra, timeout = 5000) {
    return new Promise((resolve, reject) => {
      const id = 'k' + (++seq) + '-' + Date.now();
      const timer = setTimeout(() => { document.removeEventListener('kofi-uploader:res', listen); reject(new Error('Ko-fi page did not answer')); }, timeout);
      function listen(event) {
        let msg;
        try { msg = JSON.parse(String(event.detail || '')); } catch (_) { return; }
        if (!msg || msg.id !== id) return;
        clearTimeout(timer); document.removeEventListener('kofi-uploader:res', listen);
        msg.ok ? resolve(msg) : reject(new Error(msg.error || 'page error'));
      }
      document.addEventListener('kofi-uploader:res', listen);
      document.dispatchEvent(new CustomEvent('kofi-uploader:req', { detail: JSON.stringify(Object.assign({ id, cmd }, extra || {})) }));
    });
  }
  const pageState = async () => (await page('state')).state;

  // ---------------------------------------------------------------- steps
  async function create(msg) {
    // The "Add product" button is a Vue template that appears only after the product list has
    // loaded (15-20 s in a background tab). The form behind it is in the HTML from the start, so it
    // is filled and submitted directly (checked 2026-10-01: it posts to /shop/items/add).
    const form = await waitFor(() => document.querySelector('#addShopItemModal form'), 20000);
    if (!form) throw new Error('Ko-fi "Add product" form not found (are you logged in to Ko-fi?)');
    const upgrade = Array.from(document.querySelectorAll('button')).find((b) =>
      /^add product$/i.test((b.textContent || '').trim()) && /showUpgradeCta/.test(b.getAttribute('onclick') || ''));
    if (upgrade) throw new Error('Ko-fi limit of products for this account is reached (Ko-fi offers Gold instead of a new product)');
    setValue(form.querySelector('[name=Name]'), msg.name);
    setValue(form.querySelector('[name=Description]'), msg.description || '');
    const type = form.querySelector('select[name=Type]');
    if (type) { type.value = 'DIGITAL'; type.dispatchEvent(new Event('change', { bubbles: true })); }
    const next = form.querySelector('#shopModalNextStep, input[type=submit]');
    if (!next) throw new Error('"Next step" button not found');
    if (typeof form.requestSubmit === 'function') form.requestSubmit(next); else next.click();
    return { ok: true }; // the page navigates to /shop/items/add (the new product's form)
  }

  async function fill(msg) {
    const ready = await waitFor(() => document.getElementById('Name') && document.getElementById('price') && document.getElementById('Summary'), 30000);
    if (!ready) throw new Error('Product editor did not load');
    await waitFor(async () => (await pageState()).ready, 15000);
    if (msg.name) setValue(document.getElementById('Name'), msg.name);
    if (msg.description != null) setValue(document.getElementById('Description'), msg.description);
    if (msg.summary != null) setValue(document.getElementById('Summary'), msg.summary);
    if (msg.price != null && msg.price !== '') setValue(document.getElementById('price'), String(msg.price));
    setChecked(document.getElementById('payWhatYouWant'), !!msg.payWhatYouWant);
    return { ok: true };
  }

  async function terms(msg) {
    const box = document.getElementById('agreeWithShopTerms');
    if (!box) return { ok: true, asked: false };
    // Per-product statement: "I created the original designs for this item and it doesn't contain any
    // copyrighted, illegal, adult or prohibited content". Ko-fi refuses to save a new product without it.
    if (!msg.accept) throw new Error('Ko-fi requires the "I created the original designs…" box for every new product: tick the confirmation in the uploader (section 2).');
    setChecked(box, true);
    return { ok: true, asked: true };
  }

  async function categories(msg) {
    const wanted = (msg.names || []).map((n) => String(n).trim()).filter(Boolean).slice(0, 5);
    if (!wanted.length) return { ok: true, set: [] };
    const buttons = Array.from(document.querySelectorAll('button')).filter((b) => !b.closest('#categories-selector'));
    const opener = buttons.find((b) => /^(add|edit) categories$/i.test((b.textContent || '').trim()))
      || buttons.find((b) => /categor/i.test((b.textContent || '').trim()) && (b.textContent || '').trim().length < 30);
    if (!opener) throw new Error('"Add categories" button not found');
    opener.click();
    const modal = await waitFor(() => { const m = document.getElementById('categories-selector'); return visible(m) && m; }, 10000);
    if (!modal) throw new Error('Categories window did not open');
    const key = (s) => String(s || '').trim().toLowerCase();
    const boxes = () => Array.from(modal.querySelectorAll('input[type=checkbox]')).map((input) => {
      const label = input.id ? modal.querySelector('label[for="' + input.id + '"]') : null;
      const text = (label || input.closest('label') || input.parentElement || {}).textContent || '';
      return { input, name: key(text) };
    });
    for (const name of wanted) {
      if (boxes().some((b) => b.name === key(name))) continue;
      const field = modal.querySelector('input[placeholder="Enter category name"]');
      const add = field && field.parentElement.querySelector('input[type=button], button');
      if (!field || !add) throw new Error('Cannot create category "' + name + '"');
      setValue(field, name.slice(0, 30));
      add.click();
      if (!await waitFor(() => boxes().some((b) => b.name === key(name)), 10000)) throw new Error('Ko-fi did not create category "' + name + '"');
    }
    const want = new Set(wanted.map(key));
    for (const b of boxes()) if (b.input.checked && !want.has(b.name)) { b.input.click(); await sleep(80); }
    for (const b of boxes()) if (!b.input.checked && want.has(b.name)) { b.input.click(); await sleep(80); }
    const save = Array.from(modal.querySelectorAll('button')).find((b) => /^save$/i.test((b.textContent || '').trim()));
    if (!save) throw new Error('Categories "Save" button not found');
    save.click();
    await waitFor(() => !visible(modal), 10000);
    return { ok: true, set: wanted };
  }

  // Files arrive in chunks; Ko-fi's Dropzone inputs live at the end of <body> and are looked up each time.
  let incoming = null;
  const dzInputs = () => Array.from(document.querySelectorAll('input.dz-hidden-input'));
  const previewInput = () => dzInputs().find((i) => /\.png|\.jpg/i.test(i.getAttribute('accept') || ''));
  const assetInput = () => dzInputs().find((i) => !/\.png|\.jpg/i.test(i.getAttribute('accept') || ''));

  async function fileEnd() {
    const blob = new Blob(incoming.parts.map((b64) => Uint8Array.from(atob(b64), (c) => c.charCodeAt(0))), { type: incoming.type || 'application/octet-stream' });
    const file = new File([blob], incoming.name, { type: incoming.type || 'application/octet-stream', lastModified: Date.now() });
    const slot = incoming.slot;
    incoming = null;
    const input = await waitFor(slot === 'preview' ? previewInput : assetInput, 15000);
    if (!input) throw new Error((slot === 'preview' ? 'Preview' : 'File') + ' uploader not found');
    const before = await pageState();
    const data = new DataTransfer();
    data.items.add(file);
    input.files = data.files;
    input.dispatchEvent(new Event('change', { bubbles: true }));
    // Done when Ko-fi's own state counts one more uploaded preview / asset; fail on a Dropzone error.
    const result = await waitFor(async () => {
      const now = await pageState();
      if (slot === 'preview' ? now.previews > before.previews : now.assets > before.assets) return { ok: true };
      if (slot === 'asset' && now.assetsFailed > before.assetsFailed) return { ok: false };
      return null;
    }, 30 * 60 * 1000, 700);
    if (!result) throw new Error('Upload of ' + file.name + ' did not finish in 30 minutes');
    if (!result.ok) {
      const message = Array.from(document.querySelectorAll('.dz-error-message')).map((e) => e.textContent.trim()).filter(Boolean).pop();
      throw new Error('Ko-fi rejected ' + file.name + (message ? ': ' + message : ''));
    }
    await sleep(500);
    return { ok: true };
  }

  async function save(msg) {
    const state = await pageState();
    if (!state.ready) throw new Error('Ko-fi editor is not ready');
    await page('save', { publish: !!msg.publish });
    // Success = Ko-fi leaves the editor (the port disconnects). If it stays, report its error toast.
    await sleep(2500);
    const failed = await waitFor(async () => {
      const now = await pageState();
      return !now.saving && now.errors.length ? now.errors[now.errors.length - 1].text : null;
    }, 30000, 500);
    if (failed) throw new Error('Ko-fi: ' + failed);
    return { ok: true, stayed: true };
  }

  chrome.runtime.onConnect.addListener((port) => {
    if (port.name !== 'kofi-uploader') return;
    port.onMessage.addListener(async (msg) => {
      const reply = (data) => { try { port.postMessage(Object.assign({ id: msg.id }, data)); } catch (_) {} };
      try {
        if (msg.cmd === 'ping') return reply({ ok: true, page: location.pathname, loggedIn: !/\/account\/login/i.test(location.pathname) });
        if (msg.cmd === 'create') return reply(await create(msg));
        if (msg.cmd === 'fill') return reply(await fill(msg));
        if (msg.cmd === 'terms') return reply(await terms(msg));
        if (msg.cmd === 'categories') return reply(await categories(msg));
        if (msg.cmd === 'fileStart') { incoming = { slot: msg.slot, name: msg.name, type: msg.type, parts: [] }; return reply({ ok: true }); }
        if (msg.cmd === 'fileChunk') { incoming.parts.push(msg.data); return reply({ ok: true }); }
        if (msg.cmd === 'fileEnd') return reply(await fileEnd());
        if (msg.cmd === 'save') return reply(await save(msg));
        reply({ ok: false, error: 'unknown command' });
      } catch (error) {
        reply({ ok: false, error: String(error && error.message || error) });
      }
    });
  });
})();
