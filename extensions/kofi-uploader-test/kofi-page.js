/* Runs in the PAGE world of ko-fi.com/shop/* (manifest "world": "MAIN"), because Ko-fi keeps the
   upload state in its own globals: multiImageUploadApp (preview images), multiFileUploader /
   getItemLevelAssetIds (files for buyers) and saveShopItem(publish). kofi.js (isolated world)
   asks through CustomEvents on document with JSON strings ("kofi-uploader:req" / ":res").
   window.postMessage is NOT used: a probe message froze the Ko-fi editor on 2026-10-01 (the
   page has its own message listeners). Nothing leaves the page. Checked against the live editor. */
(function () {
  'use strict';
  if (window.__kofiUploaderPage) return;
  window.__kofiUploaderPage = true;

  const errors = [];
  function hookToastr() {
    if (!window.toastr || window.toastr.__kofiUploaderHooked) return;
    const original = window.toastr.error;
    window.toastr.error = function (message) {
      errors.push({ at: Date.now(), text: String(message || '') });
      return original.apply(this, arguments);
    };
    window.toastr.__kofiUploaderHooked = true;
  }

  function count(status) {
    try {
      if (window.multiFileUploader && typeof window.multiFileUploader.getFilesWithStatus === 'function') {
        return window.multiFileUploader.getFilesWithStatus(status).length;
      }
    } catch (_) {}
    return 0;
  }

  function state() {
    hookToastr();
    const D = window.Dropzone || {};
    let previews = 0;
    try { previews = window.multiImageUploadApp ? window.multiImageUploadApp.getUploadedImages().length : 0; } catch (_) {}
    let assets = 0;
    try { assets = typeof window.getItemLevelAssetIds === 'function' ? window.getItemLevelAssetIds().length : 0; } catch (_) {}
    return {
      ready: typeof window.saveShopItem === 'function',
      previews: previews,
      assets: assets,
      assetsUploading: count(D.UPLOADING) + count(D.QUEUED) + count(D.ADDED),
      assetsFailed: count(D.ERROR),
      saving: typeof window.isSavingShopItemInFlight !== 'undefined' && !!window.isSavingShopItemInFlight,
      payWhatYouWant: !!(window.priceAndVariationsApp && window.priceAndVariationsApp.isPayWhatYouWant),
      categories: (window.CategoriesSelectorApp && window.CategoriesSelectorApp.getSavedCategoryIds().length) || 0,
      errors: errors.slice(-5),
    };
  }

  document.addEventListener('kofi-uploader:req', (event) => {
    let msg;
    try { msg = JSON.parse(String(event.detail || '')); } catch (_) { return; }
    if (!msg || !msg.id) return;
    const reply = (data) => document.dispatchEvent(new CustomEvent('kofi-uploader:res',
      { detail: JSON.stringify(Object.assign({ id: msg.id }, data)) }));
    try {
      if (msg.cmd === 'state') return reply({ ok: true, state: state() });
      if (msg.cmd === 'save') {
        if (typeof window.saveShopItem !== 'function') return reply({ ok: false, error: 'Ko-fi save function not found' });
        hookToastr();
        errors.length = 0;
        window.saveShopItem(!!msg.publish); // on success Ko-fi navigates to the product page
        return reply({ ok: true });
      }
      reply({ ok: false, error: 'unknown page command' });
    } catch (error) {
      reply({ ok: false, error: String(error && error.message || error) });
    }
  });
  hookToastr();
})();
