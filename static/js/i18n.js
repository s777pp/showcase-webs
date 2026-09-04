/* Shared language core — one source of truth for every page.
   sm_lang and ss_lang are always written together, so the ss-shell header and
   the page body can never end up on different languages. Loaded first (head),
   before ss-shell.js / app.js / profile.js / gallery.js. */
(function () {
  'use strict';

  var KEYS = ['sm_lang', 'ss_lang'];

  function read(k) {
    try { return localStorage.getItem(k) || ''; } catch (e) { return ''; }
  }
  function norm(v) {
    return String(v || '').slice(0, 2).toLowerCase() === 'ru' ? 'ru' : 'en';
  }

  /* Kept as a utility for callers that explicitly want browser detection. */
  function detect() {
    var list = [];
    try {
      list = (navigator.languages && navigator.languages.length)
        ? navigator.languages
        : [navigator.language || navigator.userLanguage || ''];
    } catch (e) {}
    for (var i = 0; i < list.length; i++) {
      if (String(list[i] || '').slice(0, 2).toLowerCase() === 'ru') return 'ru';
    }
    return 'en';
  }

  function write(L) {
    L = norm(L);
    try {
      for (var i = 0; i < KEYS.length; i++) localStorage.setItem(KEYS[i], L);
    } catch (e) {}
    return L;
  }

  function get() {
    /* Contract shared by every page: sm_lang || ss_lang || 'en'. */
    var L = norm(read('sm_lang') || read('ss_lang') || 'en');
    /* Keep both keys in sync even if only one of them was set. */
    if (read('sm_lang') !== L || read('ss_lang') !== L) write(L);
    return L;
  }

  function set(L) {
    L = write(L);
    try { document.documentElement.lang = L; } catch (e) {}
    return L;
  }

  function isRu() { return get() === 'ru'; }
  function t(ru, en) { return get() === 'ru' ? ru : en; }
  function pick(obj) {
    if (!obj) return '';
    var L = get();
    return obj[L] != null ? obj[L] : (obj.en != null ? obj.en : obj.ru);
  }

  /* generic data-i painter: textContent / placeholder / innerHTML / title */
  function apply(dict, root) {
    if (!dict) return;
    var pack = dict[get()] || dict.en || dict.ru || dict;
    var scope = root || document;
    function each(sel, fn) {
      var nodes = scope.querySelectorAll(sel);
      for (var i = 0; i < nodes.length; i++) fn(nodes[i]);
    }
    each('[data-i]', function (el) {
      var k = el.getAttribute('data-i');
      if (k && pack[k] != null) el.textContent = pack[k];
    });
    each('[data-i-html]', function (el) {
      var k = el.getAttribute('data-i-html');
      if (k && pack[k] != null) el.innerHTML = pack[k];
    });
    each('[data-i-ph]', function (el) {
      var k = el.getAttribute('data-i-ph');
      if (k && pack[k] != null) el.placeholder = pack[k];
    });
    each('[data-i-title]', function (el) {
      var k = el.getAttribute('data-i-title');
      if (k && pack[k] != null) el.title = pack[k];
    });
    try { document.documentElement.lang = get(); } catch (e) {}
    return pack;
  }

  /* Backwards-compatible switch helper. It no longer reloads the page. */
  function reload(L) {
    L = set(L);
    try { window.dispatchEvent(new CustomEvent('sm:langchange', { detail: { lang: L } })); } catch (e) {}
  }

  window.SMLang = {
    KEYS: KEYS,
    get: get, set: set, write: write, detect: detect,
    isRu: isRu, t: t, pick: pick, apply: apply, reload: reload
  };

  try { document.documentElement.lang = get(); } catch (e) {}
})();
