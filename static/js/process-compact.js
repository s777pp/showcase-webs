/* Lighter Process tab (2026-09-27): nothing is removed, only folded.
   - Step 1 "Add a file" folds to the chosen file(s) once something is added;
     "Change" reopens the drop zone, link import and media library.
   - Step 3 "Style it" starts folded with a one-line summary of the frame,
     watermark and colour; the choice to keep it open is remembered.
   Styles: css/process-compact.css. */
(function () {
  'use strict';
  var LANGS = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'];
  var WORDS = {
    change: ['Change', 'Изменить', 'Ändern', 'Değiştir', 'Modifier', 'Змінити', 'Cambiar', 'Alterar'],
    collapse: ['Collapse', 'Свернуть', 'Einklappen', 'Daralt', 'Réduire', 'Згорнути', 'Contraer', 'Recolher'],
    show: ['Show', 'Показать', 'Anzeigen', 'Göster', 'Afficher', 'Показати', 'Mostrar', 'Mostrar'],
    hide: ['Hide', 'Скрыть', 'Ausblenden', 'Gizle', 'Masquer', 'Сховати', 'Ocultar', 'Ocultar'],
    frame: ['Frame', 'Рамка', 'Rahmen', 'Çerçeve', 'Cadre', 'Рамка', 'Marco', 'Moldura'],
    watermark: ['Watermark', 'Водяной знак', 'Wasserzeichen', 'Filigran', 'Filigrane', 'Водяний знак', 'Marca de agua', 'Marca d’água'],
    on: ['on', 'вкл', 'an', 'açık', 'activé', 'увімк', 'sí', 'lig.'],
    off: ['off', 'выкл', 'aus', 'kapalı', 'désactivé', 'вимк', 'no', 'desl.'],
    color: ['Colour', 'Цвет', 'Farbe', 'Renk', 'Couleurs', 'Колір', 'Color', 'Cor'],
    colorSame: ['unchanged', 'без изменений', 'unverändert', 'değişmedi', 'inchangées', 'без змін', 'sin cambios', 'sem alterações'],
    colorChanged: ['adjusted', 'изменён', 'angepasst', 'ayarlandı', 'ajustées', 'змінено', 'ajustado', 'ajustada'],
    none: ['none', 'нет', 'keiner', 'yok', 'aucun', 'немає', 'ninguno', 'nenhuma']
  };
  function lang() {
    var value = 'en';
    try { value = window.SMLang && SMLang.get ? SMLang.get() : (document.documentElement.lang || 'en'); } catch (e) {}
    var index = LANGS.indexOf(String(value).slice(0, 2));
    return index < 0 ? 0 : index;
  }
  function w(key) { return WORDS[key][lang()] || WORDS[key][0]; }
  function store(key, value) { try { if (value === undefined) return localStorage.getItem(key); localStorage.setItem(key, value); } catch (e) { return null; } }

  var filesCard = document.getElementById('processFilesCard');
  var designCard = document.getElementById('processDesignCard');
  var fileList = document.getElementById('fileList');
  if (!filesCard || !designCard || !fileList) return;

  /* The whole step header is the fold control: a chevron on the left shows the
     state, a quiet hint on the right says what a click does. */
  function foldHeader(card, onToggle) {
    var head = card.querySelector('h2');
    var chevron = document.createElement('span');
    chevron.className = 'process-fold__chevron';
    chevron.setAttribute('aria-hidden', 'true');
    chevron.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m9 6 6 6-6 6"/></svg>';
    var hint = document.createElement('span');
    hint.className = 'process-fold__hint';
    hint.setAttribute('data-no-translate', '');
    head.classList.add('process-fold__head');
    head.insertBefore(chevron, head.firstChild);
    head.appendChild(hint);
    head.setAttribute('role', 'button');
    head.tabIndex = 0;
    function run(event) {
      if (!card.classList.contains('is-foldable')) return;
      event.preventDefault();
      onToggle();
    }
    head.addEventListener('click', run);
    head.addEventListener('keydown', function (event) { if (event.key === 'Enter' || event.key === ' ') run(event); });
    return { head: head, hint: hint };
  }
  function paintHead(card, parts, open, hintText) {
    card.classList.toggle('is-folded', !open);
    parts.head.setAttribute('aria-expanded', String(open));
    parts.hint.textContent = hintText;
  }

  /* ---- step 1: fold to the chosen files ---- */
  var filesOpenedByUser = false;
  var filesHead = foldHeader(filesCard, function () {
    filesOpenedByUser = filesCard.classList.contains('is-folded');
    syncFiles();
  });
  function syncFiles() {
    var hasFiles = fileList.children.length > 0;
    if (!hasFiles) filesOpenedByUser = false;
    var open = !hasFiles || filesOpenedByUser;
    filesCard.classList.toggle('is-foldable', hasFiles);
    paintHead(filesCard, filesHead, open, hasFiles ? (open ? w('collapse') : w('change')) : '');
  }
  new MutationObserver(syncFiles).observe(fileList, { childList: true });

  /* ---- step 3: folded "Style it" with a summary ---- */
  var designOpen = store('smProcessDesignOpen') === '1';
  function flipDesign() {
    designOpen = !designOpen;
    store('smProcessDesignOpen', designOpen ? '1' : '0');
    syncDesign();
  }
  var designHead = foldHeader(designCard, flipDesign);
  designCard.classList.add('is-foldable');
  var summary = document.createElement('p');
  summary.className = 'process-fold__summary';
  summary.setAttribute('data-no-translate', '');
  designHead.head.insertAdjacentElement('afterend', summary);
  // Folded, the card is just a plate: a click anywhere on it opens it.
  designCard.addEventListener('click', function (event) {
    if (designCard.classList.contains('is-folded') && !designHead.head.contains(event.target)) flipDesign();
  });

  function frameName() {
    if (window.SMProcessFrame && SMProcessFrame.locked && SMProcessFrame.locked()) return SMProcessFrame.lockLabel();
    var outline = document.getElementById('workshopOutline');
    if (outline && !outline.checked) return w('none');
    var summary = window.SMProcessFrame && SMProcessFrame.summary && SMProcessFrame.summary();
    return summary || w('none');
  }
  function paintSummary() {
    var wm = document.getElementById('wmEnable');
    var grade = window.SMProcessGrade && SMProcessGrade.get();
    summary.innerHTML = '';
    [[w('frame'), frameName()], [w('watermark'), wm && wm.checked ? w('on') : w('off')],
     [w('color'), window.SMProcessFrame && SMProcessFrame.locked && SMProcessFrame.locked() ? SMProcessFrame.lockLabel() : grade ? w('colorChanged') : w('colorSame')]].forEach(function (pair) {
      var chip = document.createElement('span');
      chip.className = 'process-fold__chip';
      chip.innerHTML = '<small></small><b></b>';
      chip.firstChild.textContent = pair[0];
      chip.lastChild.textContent = pair[1];
      summary.appendChild(chip);
    });
  }
  function syncDesign() {
    paintHead(designCard, designHead, designOpen, designOpen ? w('hide') : w('show'));
    paintSummary();
  }
  ['input', 'change', 'click'].forEach(function (type) {
    designCard.addEventListener(type, function () { requestAnimationFrame(paintSummary); });
  });
  document.addEventListener('sm:process-frame-change', function () { requestAnimationFrame(paintSummary); });

  /* ---- pinned title + preview: measure the sticky header and title ---- */
  var tab = document.getElementById('tab-process');
  function fitSplit() {
    // Below ~760 px of window height the preview would be tiny: keep plain scrolling.
    var wide = window.matchMedia('(min-width: 1051px)').matches && window.innerHeight >= 760;
    document.body.classList.toggle('pc-split', wide);
    document.body.classList.toggle('pc-process', tab.classList.contains('active'));
    if (!wide || !tab.classList.contains('active')) return;
    var chrome = document.querySelector('.top-chrome');
    var topbar = document.querySelector('.main > .topbar');
    var chromeBottom = chrome ? Math.max(0, Math.round(chrome.getBoundingClientRect().height + (parseFloat(getComputedStyle(chrome).top) || 0))) : 0;
    var top = chromeBottom + (topbar ? Math.round(topbar.getBoundingClientRect().height) : 0) + 8;
    var height = Math.max(420, window.innerHeight - top - 12);
    var root = document.body.style;
    root.setProperty('--pc-chrome', chromeBottom + 'px');
    root.setProperty('--pc-top', top + 'px');
    root.setProperty('--pc-h', height + 'px');
    // Give the preview whatever the rest of the right column leaves free.
    var column = tab.querySelector('.process-preview-column');
    var wrap = document.getElementById('wmCanvasWrap');
    if (column && wrap) {
      var rest = column.scrollHeight - wrap.getBoundingClientRect().height;
      var canvas = Math.max(150, Math.min(620, Math.floor(height - rest - 2)));
      root.setProperty('--pc-canvas', canvas + 'px');
    }
  }
  var fitQueued = false;
  function queueFit() { if (!fitQueued) { fitQueued = true; requestAnimationFrame(function () { fitQueued = false; fitSplit(); }); } }
  window.addEventListener('resize', queueFit);

  /* When the footer arrives the right column is pushed up by its grid row; move the
     pinned title up by the same distance so both leave together, like a page end. */
  var topbarEl = document.querySelector('.main > .topbar');
  var pinQueued = false;
  function syncPin() {
    pinQueued = false;
    if (!topbarEl) return;
    var column = tab.querySelector('.process-preview-column');
    var stuckTop = parseFloat(document.body.style.getPropertyValue('--pc-top')) || 0;
    var on = document.body.classList.contains('pc-split') && tab.classList.contains('active') && column && stuckTop;
    var push = 0;
    if (on && window.scrollY > 0) {
      var top = column.getBoundingClientRect().top;
      if (top < stuckTop - .5) push = stuckTop - top;
    }
    topbarEl.style.transform = push ? 'translateY(' + (-Math.round(push)) + 'px)' : '';
    // Show the glass backdrop only once the title is actually pinned under the header.
    var chromeBottom = parseFloat(document.body.style.getPropertyValue('--pc-chrome')) || 0;
    topbarEl.classList.toggle('is-stuck', !!(on && window.scrollY > 2 && topbarEl.getBoundingClientRect().top <= chromeBottom + 1));
  }
  function queuePin() { if (!pinQueued) { pinQueued = true; requestAnimationFrame(syncPin); } }
  window.addEventListener('scroll', queuePin, { passive: true });
  window.addEventListener('resize', queuePin);
  new MutationObserver(queueFit).observe(tab, { attributes: true, attributeFilter: ['class'] });
  // Step 4 grows or shrinks (login hint, summary chips, results): refit the preview.
  var column = tab.querySelector('.process-preview-column');
  if (column) new MutationObserver(queueFit).observe(column, { childList: true, subtree: true, attributes: true, attributeFilter: ['hidden'] });
  fitSplit();
  setTimeout(fitSplit, 400);

  /* Hints of the mode buttons are hidden on 1400-1599 px screens: keep them as tooltips. */
  function hintTooltips() {
    document.querySelectorAll('.workspace-switch__modes > button').forEach(function (button) {
      var hint = button.querySelector('small');
      if (hint && hint.textContent.trim()) button.title = hint.textContent.trim();
    });
  }
  hintTooltips();
  setTimeout(hintTooltips, 800);

  window.addEventListener('sm:langchange', function () { syncFiles(); syncDesign(); queueFit(); setTimeout(hintTooltips, 50); });
  syncFiles();
  syncDesign();
  // Frame tiles are rendered by process-frame-fx.js; repaint once they exist.
  setTimeout(paintSummary, 600);
})();
