/* Shared language core — one source of truth for every page.
   sm_lang and ss_lang are always written together, so the ss-shell header and
   the page body can never end up on different languages. Loaded first (head),
   before ss-shell.js / app.js / profile.js / gallery.js. */
(function () {
  'use strict';

  var KEYS = ['sm_lang', 'ss_lang'];
  var SUPPORTED = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'];
  var NAMES = { en:'English', ru:'Русский', de:'Deutsch', tr:'Türkçe', fr:'Français', uk:'Українська', es:'Español', pt:'Português' };

  function read(k) {
    try { return localStorage.getItem(k) || ''; } catch (e) { return ''; }
  }
  function norm(v) {
    var code = String(v || '').slice(0, 2).toLowerCase();
    return SUPPORTED.indexOf(code) >= 0 ? code : '';
  }

  function fromPath(pathname) {
    var match = String(pathname == null ? location.pathname : pathname).match(/^\/(en|ru|de|tr|fr|uk|es|pt)(?:\/|$)/i);
    return match ? match[1].toLowerCase() : '';
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
      var code = norm(list[i]);
      if (code) return code;
    }
    return 'en';
  }

  function write(L) {
    L = norm(L) || 'en';
    try {
      for (var i = 0; i < KEYS.length; i++) localStorage.setItem(KEYS[i], L);
      document.cookie = 'sm_lang=' + encodeURIComponent(L) + '; Max-Age=31536000; Path=/; SameSite=Lax';
    } catch (e) {}
    return L;
  }

  function get() {
    /* A prefixed URL is authoritative; storage remembers the next legacy URL. */
    var L = fromPath() || norm(read('sm_lang') || read('ss_lang')) || detect();
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
    if (obj[L] != null) return obj[L];
    var fallback = obj.en != null ? obj.en : obj.ru;
    return typeof fallback === 'string' ? translate(fallback, L) : fallback;
  }

  function translate(value, language) {
    var L = norm(language) || get();
    if (L === 'en' || L === 'ru' || typeof value !== 'string') return value;
    var pack = window.SM_EXTRA_TRANSLATIONS && window.SM_EXTRA_TRANSLATIONS[L];
    if (!pack) return value;
    var lead = (value.match(/^\s*/) || [''])[0], tail = (value.match(/\s*$/) || [''])[0];
    var end = tail.length ? value.length - tail.length : value.length;
    var core = value.slice(lead.length, end);
    return lead + (pack[core] || core) + tail;
  }

  function translatedObject(value, language) {
    if (typeof value === 'string') return translate(value, language);
    if (Array.isArray(value)) return value.map(function (item) { return translatedObject(item, language); });
    if (!value || typeof value !== 'object') return value;
    var result = {};
    Object.keys(value).forEach(function (key) { result[key] = translatedObject(value[key], language); });
    return result;
  }

  /* Complete dictionaries lazily from their English source pack.  Existing
     hand-written translations always win. */
  function extend(dictionary) {
    if (!dictionary || !dictionary.en) return dictionary;
    SUPPORTED.forEach(function (language) {
      if (!dictionary[language]) dictionary[language] = translatedObject(dictionary.en, language);
    });
    return dictionary;
  }

  function translateTree(root) {
    var L = get();
    if (L === 'en' || L === 'ru' || !window.SM_EXTRA_TRANSLATIONS) return;
    var scope = root && root.nodeType ? root : document;
    var nodes = [];
    if (scope.nodeType === 3) nodes.push(scope);
    else {
      var walker = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT, {
        acceptNode: function (node) {
          var parent = node.parentElement;
          var protectedBrand = parent && parent.closest('[data-no-translate],.ss-logo,.logo-link,.brand,.site-footer__brand');
          return parent && !protectedBrand && !/^(SCRIPT|STYLE|TEXTAREA|CODE|PRE)$/i.test(parent.tagName) && node.nodeValue.trim()
            ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
        }
      });
      while (walker.nextNode()) nodes.push(walker.currentNode);
    }
    nodes.forEach(function (node) {
      var next = translate(node.nodeValue, L);
      if (next !== node.nodeValue) node.nodeValue = next;
    });
    if (scope.querySelectorAll) scope.querySelectorAll('[placeholder],[title],[aria-label]').forEach(function (node) {
      ['placeholder','title','aria-label'].forEach(function (attr) {
        if (!node.hasAttribute(attr)) return;
        var value = node.getAttribute(attr), next = translate(value, L);
        if (value !== next) node.setAttribute(attr, next);
      });
    });
  }

  function stripLanguage(pathname) {
    var stripped = String(pathname || '/').replace(/^\/(?:en|ru|de|tr|fr|uk|es|pt)(?=\/|$)/i, '');
    return stripped || '/';
  }

  function url(href, language) {
    var L = norm(language) || get();
    try {
      var parsed = new URL(href, location.origin);
      if (parsed.origin !== location.origin) return href;
      var path = stripLanguage(parsed.pathname);
      if (/^\/(?:api|static|fonts|preview)(?:\/|$)/.test(path)) return href;
      if (!(path === '/' || /^\/(?:app|gallery|profile|privacy)(?:\/|$)/.test(path))) return href;
      parsed.pathname = '/' + L + (path === '/' ? '/' : path);
      return parsed.pathname + parsed.search + parsed.hash;
    } catch (e) { return href; }
  }

  function localizeLinks(root) {
    var scope = root || document;
    var links = [];
    if (scope.nodeType === 1 && scope.matches && scope.matches('a[href]')) links.push(scope);
    if (scope.querySelectorAll) scope.querySelectorAll('a[href]').forEach(function (link) { links.push(link); });
    links.forEach(function (link) {
      var href = link.getAttribute('href');
      if (href && !href.startsWith('#')) {
        var next = url(href);
        if (next !== href) link.setAttribute('href', next);
      }
    });
  }

  function switchTo(language) {
    var L = set(language);
    location.assign(url(location.href, L));
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
    KEYS: KEYS, SUPPORTED: SUPPORTED, NAMES: NAMES,
    get: get, set: set, write: write, detect: detect,
    isRu: isRu, t: t, pick: pick, apply: apply, reload: reload, extend: extend,
    fromPath: fromPath, translate: translate, translateTree: translateTree,
    url: url, localizeLinks: localizeLinks, switchTo: switchTo
  };

  try { document.documentElement.lang = get(); } catch (e) {}
  function startLocaleObserver() {
    write(get());
    localizeLinks(document);
    translateTree(document);
    if (!window.MutationObserver) return;
    var queued = false;
    var dirty = [];
    function queue(node) {
      if (!node) return;
      if (node.nodeType === 3) node = node.parentElement;
      if (node && dirty.indexOf(node) < 0) dirty.push(node);
    }
    new MutationObserver(function (records) {
      records.forEach(function (record) {
        if (record.type === 'childList') record.addedNodes.forEach(queue);
        else queue(record.target);
      });
      if (queued || !dirty.length) return;
      queued = true;
      requestAnimationFrame(function () {
        queued = false;
        var scopes = dirty.splice(0, dirty.length);
        if (scopes.length > 64) scopes = [document];
        scopes.forEach(function (scope) { localizeLinks(scope); translateTree(scope); });
      });
    }).observe(document.documentElement, { childList:true, subtree:true, characterData:true, attributes:true,
      attributeFilter:['placeholder','title','aria-label','href'] });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', startLocaleObserver);
  else startLocaleObserver();
})();
