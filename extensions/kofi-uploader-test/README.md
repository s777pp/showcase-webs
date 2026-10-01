# Ko-fi Shop Uploader (test, 0.2.0)

Creates Ko-fi shop products in bulk from the owner's own browser session: one product per file,
with title template, description, summary, price, pay-what-you-want, up to 5 categories, one
preview image and the file buyers get. Publish right away or save as a draft.
Not part of the website; excluded from `scripts/release_sync.py`.

## Install (Chrome / Edge 111+)

1. `chrome://extensions` → enable **Developer mode** → **Load unpacked** → pick this folder.
2. Log in on ko-fi.com in the same browser.
3. Click the extension icon: the uploader page opens.

## How it works

- `uploader.html/js` — the queue. Files never leave this tab except into Ko-fi's own uploader.
  For each product it opens `ko-fi.com/shop/settings`, then the new product's editor, in a
  background tab, and talks to `kofi.js` through a port (files go in 3 MB base64 chunks).
- `kofi.js` (isolated world) fills the "Add product" window and the editor, picks categories in
  `#categories-selector` (creates missing ones), drops files into Ko-fi's Dropzone inputs
  (`input.dz-hidden-input`, previews = the one accepting .png/.jpg) and calls save.
- `kofi-page.js` (page world, `"world": "MAIN"`) reads Ko-fi's own state: preview count
  (`multiImageUploadApp.getUploadedImages()`), uploaded assets (`getItemLevelAssetIds()`, failed
  ones via `multiFileUploader.getFilesWithStatus(Dropzone.ERROR)`), and calls
  `saveShopItem(publish)`; Ko-fi's `toastr.error` messages are captured and reported.
  The two scripts talk through `CustomEvent`s on `document` with JSON strings. **Never use
  `window.postMessage` on Ko-fi pages:** a probe message froze the product editor (2026-10-01).
- Success = Ko-fi leaves the editor and opens the product page (`ko-fi.com/s/<alias>`); that URL
  is the product link. After an error the Ko-fi tab stays open so the product can be checked.
- Publishing requires (Ko-fi's own checks): a preview image, a description, a summary and at
  least one asset. A new product may ask to accept the shop terms (`#agreeWithShopTerms`); the
  extension ticks it only when the user ticked "I accept the Ko-fi shop terms" in the uploader.

## Status

Checked read-only against a live product editor on 2026-10-01 (field ids, Dropzone inputs,
categories window, save function and its validation). Not yet run end to end: the
"Add product" → new editor step and real uploads need one test product (save as draft).
