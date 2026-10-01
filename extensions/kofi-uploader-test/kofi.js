/* Runs on ko-fi.com/shop/* pages. The uploader page drives it through a port:
   create  -> fill the "Add product" modal (name, description, digital) and submit it
   fill    -> on the item's edit page: summary, price, pay-what-you-want, published
   file*   -> receive a file in base64 chunks and drop it into Ko-fi's own Dropzone
              uploader (preview images or the files buyers get), then wait for the upload
   save    -> press "Save changes" and report the item's share link
   Nothing is sent anywhere except to Ko-fi by Ko-fi's own page. */
(function () {
  'use strict';
  if (window.__kofiUploaderReady) return;
  window.__kofiUploaderReady = true;

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  async function waitFor(check, timeout = 30000, step = 250) {
    const end = Date.now() + timeout;
    while (Date.now() < end) {
      const value = check();
      if (value) return value;
      await sleep(step);
    }
    return null;
  }
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
    el.click(); // the page's own handlers (pay-what-you-want, published) react to clicks
  }
  function shareLink() {
    const text = document.body.innerText || '';
    const m = text.match(/https?:\/\/ko-fi\.com\/s\/[A-Za-z0-9]+/);
    if (m) return m[0];
    const input = Array.from(document.querySelectorAll('input')).find((i) => /ko-fi\.com\/s\//.test(i.value || ''));
    return input ? input.value : '';
  }

  // ---------------------------------------------------------------- steps
  async function create(msg) {
    const opener = Array.from(document.querySelectorAll('a,button')).find((a) => /addShopItemModal/.test(a.getAttribute('onclick') || ''));
    if (opener) opener.click();
    const modal = await waitFor(() => document.getElementById('addShopItemModal'));
    if (!modal) throw new Error('Add product window not found');
    const form = modal.querySelector('form');
    await sleep(400);
    setValue(form.querySelector('[name=Name]'), msg.name);
    setValue(form.querySelector('[name=Description]'), msg.description || '');
    const type = form.querySelector('select[name=Type]');
    if (type) { type.value = 'DIGITAL'; type.dispatchEvent(new Event('change', { bubbles: true })); }
    const next = form.querySelector('#shopModalNextStep, input[type=submit]');
    if (!next) throw new Error('"Next step" button not found');
    next.click(); // the page navigates to the new item's edit page
    return { ok: true };
  }

  async function fill(msg) {
    await waitFor(() => document.getElementById('Name') && document.getElementById('price'));
    if (msg.name) setValue(document.getElementById('Name'), msg.name);
    if (msg.description != null) setValue(document.getElementById('Description'), msg.description);
    if (msg.summary != null) setValue(document.getElementById('Summary'), msg.summary);
    if (msg.price != null && msg.price !== '') setValue(document.getElementById('price'), String(msg.price));
    setChecked(document.getElementById('payWhatYouWant'), !!msg.payWhatYouWant);
    setChecked(document.querySelector('input[type=checkbox]#Enabled'), !!msg.published);
    return { ok: true, link: shareLink() };
  }

  // Files arrive in chunks; the Dropzone hidden input is recreated after every use, so it is looked up each time.
  let incoming = null;
  function previewInput() {
    return Array.from(document.querySelectorAll('input.dz-hidden-input')).find((i) => /\.png|\.jpg|image/i.test(i.accept || ''));
  }
  function assetInput() {
    return Array.from(document.querySelectorAll('input.dz-hidden-input')).find((i) => !/\.png|\.jpg|image/i.test(i.accept || ''));
  }
  function busy() {
    return !!document.querySelector('.dz-preview.dz-processing:not(.dz-complete), .dz-preview-row .progress-bar:not([style*="100%"])');
  }
  async function fileEnd() {
    const blob = new Blob(incoming.parts.map((b64) => Uint8Array.from(atob(b64), (c) => c.charCodeAt(0))), { type: incoming.type || 'application/octet-stream' });
    const file = new File([blob], incoming.name, { type: incoming.type || 'application/octet-stream', lastModified: Date.now() });
    const slot = incoming.slot;
    incoming = null;
    const input = await waitFor(slot === 'preview' ? previewInput : assetInput, 15000);
    if (!input) throw new Error((slot === 'preview' ? 'Preview' : 'File') + ' uploader not found');
    const data = new DataTransfer();
    data.items.add(file);
    input.files = data.files;
    input.dispatchEvent(new Event('change', { bubbles: true }));
    // Wait until Ko-fi's uploader shows the file and finishes sending it.
    const seen = await waitFor(() => (document.body.innerText || '').includes(file.name) || document.querySelector('.dz-preview.dz-processing'), 20000);
    if (!seen && slot === 'asset') throw new Error('Ko-fi did not accept ' + file.name);
    const done = await waitFor(() => !busy(), 15 * 60 * 1000, 500);
    if (!done) throw new Error('Upload of ' + file.name + ' did not finish');
    const failed = Array.from(document.querySelectorAll('.dz-error-message')).map((e) => e.textContent.trim()).filter(Boolean);
    if (failed.length) throw new Error(failed[failed.length - 1]);
    await sleep(600);
    return { ok: true };
  }

  async function save() {
    const button = Array.from(document.querySelectorAll('input[type=button],button')).find((b) => /save changes/i.test(b.value || b.textContent || ''));
    if (!button) throw new Error('"Save changes" button not found');
    const before = location.href;
    button.click();
    // Ko-fi either reloads/redirects or shows a confirmation; give it time either way.
    await waitFor(() => location.href !== before || /saved|success/i.test((document.querySelector('.toast, .alert-success, .kfds-toast') || {}).textContent || ''), 20000);
    await sleep(1500);
    return { ok: true, link: shareLink() };
  }

  chrome.runtime.onConnect.addListener((port) => {
    if (port.name !== 'kofi-uploader') return;
    port.onMessage.addListener(async (msg) => {
      const reply = (data) => { try { port.postMessage(Object.assign({ id: msg.id }, data)); } catch (_) {} };
      try {
        if (msg.cmd === 'ping') return reply({ ok: true, page: location.pathname, link: shareLink() });
        if (msg.cmd === 'create') return reply(await create(msg));
        if (msg.cmd === 'fill') return reply(await fill(msg));
        if (msg.cmd === 'fileStart') { incoming = { slot: msg.slot, name: msg.name, type: msg.type, parts: [] }; return reply({ ok: true }); }
        if (msg.cmd === 'fileChunk') { incoming.parts.push(msg.data); return reply({ ok: true }); }
        if (msg.cmd === 'fileEnd') return reply(await fileEnd());
        if (msg.cmd === 'save') return reply(await save());
        reply({ ok: false, error: 'unknown command' });
      } catch (error) {
        reply({ ok: false, error: String(error && error.message || error) });
      }
    });
  });
})();
