/* Font library for Builder text layers (2026-09-30): a dialog over the page with every
   font drawn as "ShowcaseMaker", themes, search, favourites and the user's own fonts.
   Catalogue: static/assets/fonts/catalog.json (scripts/build_font_catalog.py, Google Fonts).
   Tiles load only the letters they show (css2 ... &text=ShowcaseMaker); a chosen font
   loads fully. Own fonts (TTF/OTF/WOFF/WOFF2) stay in this browser (IndexedDB) and are
   registered with the FontFace API. Loaded after builder-layout.js. */
(function () {
  'use strict';
  var root = document.getElementById('showcaseBuilder');
  if (!root || root.dataset.bxFonts || !window.SMBuilder) return;
  root.dataset.bxFonts = '1';
  var $ = function (id) { return document.getElementById(id); };
  var CATALOG_URL = '/static/assets/fonts/catalog.json?v=20260930-f1', SAMPLE = 'ShowcaseMaker', PAGE = 90;
  var LANGS = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'];
  var COPY = {
    title: ['Fonts', 'Шрифты', 'Schriften', 'Yazı tipleri', 'Polices', 'Шрифти', 'Fuentes', 'Fontes'],
    search: ['Search fonts', 'Поиск шрифта', 'Schrift suchen', 'Yazı tipi ara', 'Rechercher une police', 'Пошук шрифту', 'Buscar fuente', 'Buscar fonte'],
    upload: ['Upload your font', 'Загрузить свой шрифт', 'Eigene Schrift hochladen', 'Kendi yazı tipini yükle', 'Importer votre police', 'Завантажити свій шрифт', 'Subir tu fuente', 'Enviar sua fonte'],
    close: ['Close', 'Закрыть', 'Schließen', 'Kapat', 'Fermer', 'Закрити', 'Cerrar', 'Fechar'],
    font: ['Font', 'Шрифт', 'Schrift', 'Yazı tipi', 'Police', 'Шрифт', 'Fuente', 'Fonte'],
    choose: ['Choose', 'Выбрать', 'Wählen', 'Seç', 'Choisir', 'Обрати', 'Elegir', 'Escolher'],
    more: ['Show more', 'Показать ещё', 'Mehr anzeigen', 'Daha fazla', 'Afficher plus', 'Показати ще', 'Ver más', 'Ver mais'],
    empty: ['Nothing found', 'Ничего не найдено', 'Nichts gefunden', 'Bulunamadı', 'Aucun résultat', 'Нічого не знайдено', 'Sin resultados', 'Nada encontrado'],
    mine_empty: ['Upload a .ttf, .otf, .woff or .woff2 file: it stays in this browser.', 'Загрузи файл .ttf, .otf, .woff или .woff2 — он сохранится в этом браузере.', 'Lade eine .ttf-, .otf-, .woff- oder .woff2-Datei hoch – sie bleibt in diesem Browser.', '.ttf, .otf, .woff veya .woff2 yükle; bu tarayıcıda kalır.', 'Importez un fichier .ttf, .otf, .woff ou .woff2 : il reste dans ce navigateur.', 'Завантаж файл .ttf, .otf, .woff або .woff2 — він залишиться в цьому браузері.', 'Sube un .ttf, .otf, .woff o .woff2: se guarda en este navegador.', 'Envie um .ttf, .otf, .woff ou .woff2: ele fica neste navegador.'],
    bad_font: ['This file is not a font we can read.', 'Этот файл не удалось прочитать как шрифт.', 'Diese Datei ist keine lesbare Schrift.', 'Bu dosya okunabilir bir yazı tipi değil.', 'Ce fichier n’est pas une police lisible.', 'Цей файл не вдалося прочитати як шрифт.', 'Este archivo no es una fuente legible.', 'Este arquivo não é uma fonte legível.'],
    too_big: ['The font file is larger than 8 MB.', 'Файл шрифта больше 8 МБ.', 'Die Schriftdatei ist größer als 8 MB.', 'Yazı tipi dosyası 8 MB’tan büyük.', 'Le fichier dépasse 8 Mo.', 'Файл шрифту більший за 8 МБ.', 'El archivo supera 8 MB.', 'O arquivo tem mais de 8 MB.'],
    all: ['All', 'Все', 'Alle', 'Tümü', 'Toutes', 'Усі', 'Todas', 'Todas'],
    popular: ['Popular', 'Популярные', 'Beliebt', 'Popüler', 'Populaires', 'Популярні', 'Populares', 'Populares'],
    favorites: ['Favourites', 'Избранные', 'Favoriten', 'Favoriler', 'Favoris', 'Обрані', 'Favoritas', 'Favoritas'],
    mine: ['My fonts', 'Свои', 'Meine', 'Benim', 'Mes polices', 'Мої', 'Mías', 'Minhas'],
    no_cyr: ['no Cyrillic', 'нет кириллицы', 'ohne Kyrillisch', 'Kiril yok', 'sans cyrillique', 'без кирилиці', 'sin cirílico', 'sem cirílico'],
    site: ['Site fonts', 'Шрифты сайта', 'Website', 'Site', 'Site', 'Шрифти сайту', 'Del sitio', 'Do site'],
    cyrillic: ['Cyrillic', 'Кириллица', 'Kyrillisch', 'Kiril', 'Cyrillique', 'Кирилиця', 'Cirílico', 'Cirílico'],
    gaming: ['Gaming', 'Игровые', 'Gaming', 'Oyun', 'Gaming', 'Ігрові', 'Gaming', 'Games'],
    horror: ['Horror', 'Хоррор', 'Horror', 'Korku', 'Horreur', 'Хорор', 'Terror', 'Terror'],
    gothic: ['Gothic & fantasy', 'Готика и фэнтези', 'Gotik & Fantasy', 'Gotik & fantastik', 'Gothique & fantasy', 'Готика і фентезі', 'Gótico y fantasía', 'Gótico e fantasia'],
    cute: ['Cute', 'Милые', 'Niedlich', 'Sevimli', 'Mignonnes', 'Милі', 'Tiernas', 'Fofas'],
    poster: ['Poster', 'Афишные', 'Plakat', 'Afiş', 'Affiche', 'Афішні', 'Cartel', 'Pôster'],
    elegant: ['Elegant', 'Элегантные', 'Elegant', 'Zarif', 'Élégantes', 'Елегантні', 'Elegantes', 'Elegantes'],
    script: ['Script', 'Скриптовые', 'Schreibschrift', 'El yazısı', 'Scriptes', 'Скриптові', 'Caligráficas', 'Cursivas'],
    handwriting: ['Handwriting', 'Рукописные', 'Handschrift', 'El yazısı (serbest)', 'Manuscrites', 'Рукописні', 'Manuscritas', 'Manuscritas'],
    display: ['Decorative', 'Декоративные', 'Dekorativ', 'Dekoratif', 'Décoratives', 'Декоративні', 'Decorativas', 'Decorativas'],
    serif: ['Serif', 'С засечками', 'Serif', 'Tırnaklı', 'Avec empattements', 'З зарубками', 'Con serifa', 'Com serifa'],
    sans: ['Sans serif', 'Без засечек', 'Serifenlos', 'Tırnaksız', 'Sans empattements', 'Без зарубок', 'Sin serifa', 'Sem serifa'],
    mono: ['Monospace', 'Моноширинные', 'Monospace', 'Eş aralıklı', 'Chasse fixe', 'Моноширинні', 'Monoespaciadas', 'Monoespaçadas']
  };
  var TABS = ['popular', 'all', 'favorites', 'mine', 'site', 'cyrillic', 'gaming', 'horror', 'gothic', 'cute', 'poster', 'elegant', 'script', 'handwriting', 'display', 'serif', 'sans', 'mono'];
  var catalog = null, byName = {}, siteFonts = [], userFonts = {}, favorites = readFavorites(), tab = 'popular', query = '', shown = 0, list = [];
  var previewLoaded = new Set(), fullLoaded = new Map();

  function language() { return (window.SMLang && SMLang.get && SMLang.get()) || document.documentElement.lang || 'en'; }
  function t(key) { var i = Math.max(0, LANGS.indexOf(language())); var row = COPY[key] || []; return row[i] || row[0] || key; }
  function node(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function readFavorites() { try { return JSON.parse(localStorage.getItem('sm_font_favorites') || '[]'); } catch (e) { return []; } }
  function saveFavorites() { try { localStorage.setItem('sm_font_favorites', JSON.stringify(favorites.slice(0, 200))); } catch (e) {} }
  function cssFamily(name) { return name.trim().replace(/\s+/g, '+'); }
  function linkCss(href) { var l = document.createElement('link'); l.rel = 'stylesheet'; l.href = href; document.head.appendChild(l); return l; }

  // ------------------------------------------------------------- loading
  function loadCatalog() {
    if (catalog) return Promise.resolve(catalog);
    return fetch(CATALOG_URL).then(function (r) { return r.json(); }).then(function (data) {
      catalog = data.fonts.map(function (row, index) { return { name: row[0], cat: row[1], cyr: !!row[2], weights: row[3], tags: row[4], rank: index }; });
      catalog.forEach(function (f) { byName[f.name] = f; });
      return catalog;
    });
  }
  function previewFont(name) {
    var f = byName[name]; if (!f || previewLoaded.has(name) || fullLoaded.has(name)) return;
    previewLoaded.add(name);
    linkCss('https://fonts.googleapis.com/css2?family=' + cssFamily(name) + '&text=' + SAMPLE + '&display=swap');
  }
  /* Whole font (all glyphs, up to three weights) before it is used on the canvas. */
  function ensureFont(name) {
    var f = byName[name]; if (!f) return Promise.resolve();
    if (fullLoaded.has(name)) return fullLoaded.get(name);
    var weights = f.weights.filter(function (w) { return w === 400 || w === 700 || w === 900; });
    if (!weights.length) weights = [f.weights[0]];
    linkCss('https://fonts.googleapis.com/css2?family=' + cssFamily(name) + ':wght@' + weights.join(';') + '&display=swap');
    var promise = Promise.all(weights.map(function (w) { return document.fonts.load(w + ' 64px "' + name + '"', 'ShowcaseMaker АБВ'); })).catch(function () {});
    fullLoaded.set(name, promise);
    return promise;
  }
  function bestWeight(name) {
    var f = byName[name]; if (!f) return 800;
    var w = f.weights.filter(function (v) { return v >= 700; });
    return w.length ? Math.min.apply(null, w) : Math.max.apply(null, f.weights);
  }

  // ------------------------------------------------------- own fonts (IDB)
  var dbPromise = null;
  function db() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise(function (resolve, reject) {
      if (!window.indexedDB) { reject(Error('no idb')); return; }
      var req = indexedDB.open('sm-user-fonts', 1);
      req.onupgradeneeded = function () { req.result.createObjectStore('fonts', { keyPath: 'name' }); };
      req.onsuccess = function () { resolve(req.result); }; req.onerror = function () { reject(req.error); };
    });
    return dbPromise;
  }
  function registerUserFont(name, buffer) {
    var face = new FontFace(name, buffer);
    return face.load().then(function (loaded) { document.fonts.add(loaded); userFonts[name] = true; return name; });
  }
  function restoreUserFonts() {
    return db().then(function (d) {
      return new Promise(function (resolve) {
        var req = d.transaction('fonts', 'readonly').objectStore('fonts').getAll();
        req.onsuccess = function () { Promise.all((req.result || []).map(function (row) { return registerUserFont(row.name, row.data).catch(function () {}); })).then(resolve); };
        req.onerror = function () { resolve(); };
      });
    }).catch(function () {}).then(function () { SMBuilder.redraw && SMBuilder.redraw(); });
  }
  function addUserFont(file) {
    if (!file) return Promise.resolve();
    if (file.size > 8 * 1024 * 1024) { setStatus(t('too_big')); return Promise.resolve(); }
    var base = file.name.replace(/\.(ttf|otf|woff2?|)$/i, '').replace(/[^\p{L}\p{N} _-]+/gu, ' ').trim().slice(0, 40) || 'My font';
    var name = byName[base] ? base + ' (my)' : base;
    return file.arrayBuffer().then(function (buffer) {
      return registerUserFont(name, buffer).then(function () {
        return db().then(function (d) {
          return new Promise(function (resolve) { var tx = d.transaction('fonts', 'readwrite'); tx.objectStore('fonts').put({ name: name, data: buffer, added: Date.now() }); tx.oncomplete = resolve; tx.onerror = resolve; });
        }).catch(function () {});
      }).then(function () { tab = 'mine'; render(); choose(name); });
    }).catch(function () { setStatus(t('bad_font')); });
  }

  // ------------------------------------------------------------------ UI
  var dialog = node('div', 'bx-fonts'); dialog.hidden = true;
  dialog.innerHTML = '<div class="bx-fonts__backdrop" data-close></div>' +
    '<section class="bx-fonts__panel" role="dialog" aria-modal="true" aria-labelledby="bxFontsTitle">' +
    '<header class="bx-fonts__head"><h2 id="bxFontsTitle"></h2><input type="search" class="bx-fonts__search" autocomplete="off">' +
    '<label class="bx-fonts__upload"><input type="file" accept=".ttf,.otf,.woff,.woff2,font/ttf,font/otf,font/woff,font/woff2" hidden data-sm-enhanced="1"><span></span></label>' +
    '<button type="button" class="bx-fonts__close" data-close aria-label="Close">×</button></header>' +
    '<nav class="bx-fonts__tabs" role="tablist"></nav><p class="bx-fonts__status" role="status"></p>' +
    '<div class="bx-fonts__grid" role="listbox"></div><button type="button" class="bx-fonts__more"></button></section>';
  document.body.appendChild(dialog);
  var grid = dialog.querySelector('.bx-fonts__grid'), tabsNav = dialog.querySelector('.bx-fonts__tabs'), search = dialog.querySelector('.bx-fonts__search');
  var moreButton = dialog.querySelector('.bx-fonts__more'), statusLine = dialog.querySelector('.bx-fonts__status'), uploadInput = dialog.querySelector('.bx-fonts__upload input');
  function setStatus(text) { statusLine.textContent = text || ''; }
  var observer = 'IntersectionObserver' in window ? new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) { if (entry.isIntersecting) { previewFont(entry.target.dataset.font); observer.unobserve(entry.target); } });
  }, { root: grid, rootMargin: '200px' }) : null;

  function needsCyrillic() { var l = currentText(); return !!l && /[\u0400-\u04FF]/.test(l.text || ''); }
  function currentText() { var l = SMBuilder.current(); return l && l.type === 'text' ? l : null; }
  function matches(f) {
    if (query && f.name.toLowerCase().indexOf(query) < 0) return false;
    if (tab === 'all') return true;
    if (tab === 'popular') return f.rank < 160;
    if (tab === 'favorites') return favorites.indexOf(f.name) >= 0;
    if (tab === 'cyrillic') return f.cyr;
    if (['sans', 'serif', 'display', 'handwriting', 'mono'].indexOf(tab) >= 0) return f.cat === tab;
    return f.tags.indexOf(tab) >= 0;
  }
  function entries() {
    if (tab === 'mine') return Object.keys(userFonts).filter(function (n) { return !query || n.toLowerCase().indexOf(query) >= 0; }).map(function (n) { return { name: n, own: true }; });
    if (tab === 'site') return siteFonts.filter(function (n) { return !query || n.toLowerCase().indexOf(query) >= 0; }).map(function (n) { return { name: n, site: true }; });
    var result = (catalog || []).filter(matches);
    if (tab === 'favorites') siteFonts.concat(Object.keys(userFonts)).forEach(function (n) { if (favorites.indexOf(n) >= 0 && (!query || n.toLowerCase().indexOf(query) >= 0)) result.unshift({ name: n, site: true }); });
    return result;
  }
  function tabCount(key) {
    if (key === 'mine') return Object.keys(userFonts).length;
    if (key === 'site') return siteFonts.length;
    var keep = tab, q = query; tab = key; query = ''; var n = (catalog || []).filter(matches).length + (key === 'favorites' ? siteFonts.concat(Object.keys(userFonts)).filter(function (x) { return favorites.indexOf(x) >= 0; }).length : 0); tab = keep; query = q; return n;
  }
  function renderTabs() {
    tabsNav.replaceChildren();
    TABS.forEach(function (key) {
      var b = node('button', 'bx-fonts__tab'); b.type = 'button'; b.setAttribute('role', 'tab'); b.setAttribute('aria-selected', String(key === tab));
      b.append(node('span', null, t(key)), node('small', null, String(tabCount(key))));
      b.addEventListener('click', function () { tab = key; render(); });
      tabsNav.append(b);
    });
  }
  function tile(f) {
    var layer = currentText(), b = node('div', 'bx-font'); b.dataset.font = f.name; b.setAttribute('role', 'option'); b.tabIndex = 0;
    b.setAttribute('aria-selected', String(!!layer && layer.font === f.name));
    var head = node('div', 'bx-font__head'); head.append(node('span', 'bx-font__name', f.name));
    var star = node('button', 'bx-font__star', favorites.indexOf(f.name) >= 0 ? '★' : '☆'); star.type = 'button'; star.setAttribute('aria-label', t('favorites'));
    star.addEventListener('click', function (event) {
      event.stopPropagation();
      var i = favorites.indexOf(f.name); if (i >= 0) favorites.splice(i, 1); else favorites.unshift(f.name);
      saveFavorites(); star.textContent = i >= 0 ? '☆' : '★'; if (tab === 'favorites') render();
    });
    head.append(star);
    var sample = node('div', 'bx-font__sample', SAMPLE); sample.style.fontFamily = '"' + f.name + '", "Mulish", sans-serif';
    if (f.cyr) head.append(node('i', 'bx-font__cyr', 'Кир'));
    else if (!f.own && !f.site && needsCyrillic()) head.append(node('i', 'bx-font__cyr bx-font__cyr--no', t('no_cyr')));
    b.append(head, sample);
    b.addEventListener('click', function () { choose(f.name); });
    b.addEventListener('keydown', function (event) { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); choose(f.name); } });
    if (!f.own && !f.site) { if (observer) observer.observe(b); else previewFont(f.name); }
    return b;
  }
  function render(append) {
    if (!append) { list = entries(); shown = 0; grid.replaceChildren(); grid.scrollTop = 0; renderTabs(); }
    var next = list.slice(shown, shown + PAGE); shown += next.length;
    next.forEach(function (f) { grid.append(tile(f)); });
    moreButton.hidden = shown >= list.length; moreButton.textContent = t('more');
    setStatus(!list.length ? (tab === 'mine' ? t('mine_empty') : t('empty')) : '');
  }
  grid.addEventListener('scroll', function () { if (grid.scrollTop + grid.clientHeight > grid.scrollHeight - 300 && shown < list.length) render(true); });
  moreButton.addEventListener('click', function () { render(true); });
  search.addEventListener('input', function () { query = search.value.trim().toLowerCase(); render(); });
  uploadInput.addEventListener('change', function () { addUserFont(uploadInput.files[0]); uploadInput.value = ''; });
  dialog.addEventListener('click', function (event) { if (event.target.closest('[data-close]')) close(); });
  dialog.addEventListener('keydown', function (event) { if (event.key === 'Escape') { event.preventDefault(); close(); } });

  var opener = null;
  function open() {
    opener = document.activeElement;
    dialog.querySelector('#bxFontsTitle').textContent = t('title');
    search.placeholder = t('search'); search.setAttribute('aria-label', t('search'));
    dialog.querySelector('.bx-fonts__upload span').textContent = '+ ' + t('upload');
    dialog.querySelector('.bx-fonts__close').setAttribute('aria-label', t('close'));
    dialog.hidden = false; document.documentElement.classList.add('bx-fonts-open');
    loadCatalog().then(function () { render(); }).catch(function () { tab = 'site'; render(); });
    setTimeout(function () { search.focus(); }, 30);
  }
  function close() {
    dialog.hidden = true; document.documentElement.classList.remove('bx-fonts-open');
    if (opener && opener.focus) opener.focus();
  }
  function choose(name) {
    var layer = currentText(); if (!layer) { close(); return; }
    var done = function () {
      layer.font = name;
      layer.fontWeight = byName[name] ? bestWeight(name) : (userFonts[name] ? 400 : 800);
      SMBuilder.redraw(); SMBuilder.sync(); SMBuilder.commit(); paintButton(); close();
    };
    if (byName[name]) { setStatus('…'); ensureFont(name).then(done); } else done();
  }

  // ------------------------------------------------ font button in the panel
  var select = $('builderFont');
  var fontButton = node('button', 'bx-font-button'); fontButton.type = 'button';
  fontButton.innerHTML = '<span class="bx-font-button__label"></span><b class="bx-font-button__name"></b><span class="bx-font-button__go"></span>';
  if (select) {
    Array.prototype.forEach.call(select.options, function (o) { if (siteFonts.indexOf(o.value) < 0) siteFonts.push(o.value); });
    var row = select.closest('.builder-two') || select.closest('label');
    var label = select.closest('label'); if (label) label.classList.add('bx-hidden');
    if (row) row.before(fontButton);
  }
  var oldPreview = root.querySelector('.builder-font-preview'); if (oldPreview) oldPreview.classList.add('bx-hidden');
  fontButton.addEventListener('click', open);
  function paintButton() {
    var layer = currentText(); if (!layer) return;
    var name = layer.font || 'Mulish';
    fontButton.querySelector('.bx-font-button__label').textContent = t('font');
    var nameNode = fontButton.querySelector('.bx-font-button__name'); nameNode.textContent = name; nameNode.style.fontFamily = '"' + name + '", "Mulish", sans-serif';
    fontButton.querySelector('.bx-font-button__go').textContent = t('choose') + ' ›';
  }
  /* Text layers of a restored / loaded project get their Google fonts before drawing. */
  function ensureProjectFonts() {
    var names = SMBuilder.layers().filter(function (l) { return l.type === 'text' && l.font; }).map(function (l) { return l.font; });
    if (!names.length) return;
    loadCatalog().then(function () {
      names.forEach(function (n) { if (byName[n] && !fullLoaded.has(n)) { previewFont(n); ensureFont(n).then(function () { SMBuilder.redraw(); }); } });
    }).catch(function () {});
  }
  root.addEventListener('sm:builder-select', function () { paintButton(); ensureProjectFonts(); });
  window.addEventListener('sm:langchange', paintButton);
  restoreUserFonts();
  paintButton(); ensureProjectFonts();
  window.SMBuilderFonts = { open: open, close: close, ensure: ensureFont };
})();
