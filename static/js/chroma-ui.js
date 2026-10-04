/* Character tab: backdrop choice and a keyed live preview (owner, 2026-10-05).
   Adds the colours to #composeChroma (auto / none stay), a colour picker for "My colour",
   the "remove backdrop between arms and legs" switch, and SMComposeKey.source(), which
   app.js draws instead of the raw character: the same engine as the server compose
   (static/js/chroma-matte.js <-> smweb/chroma_matte.py), so the preview is the result. */
(function () {
  'use strict';
  var COPY = {
    en: { green: 'Green screen', blue: 'Blue screen', white: 'White', black: 'Black', custom: 'My colour…', colour: 'Backdrop colour', holes: 'Remove backdrop between arms and legs', note: 'The preview shows the cut-out exactly as it will be composed.' },
    ru: { green: 'Зелёный (хромакей)', blue: 'Синий', white: 'Белый', black: 'Чёрный', custom: 'Свой цвет…', colour: 'Цвет фона', holes: 'Убирать фон в просветах (между руками, ногами)', note: 'Предпросмотр показывает вырезку ровно так, как она попадёт в итог.' },
    de: { green: 'Greenscreen', blue: 'Bluescreen', white: 'Weiß', black: 'Schwarz', custom: 'Eigene Farbe…', colour: 'Hintergrundfarbe', holes: 'Hintergrund zwischen Armen und Beinen entfernen', note: 'Die Vorschau zeigt die Freistellung genau so wie im Ergebnis.' },
    tr: { green: 'Yeşil perde', blue: 'Mavi perde', white: 'Beyaz', black: 'Siyah', custom: 'Kendi rengim…', colour: 'Arka plan rengi', holes: 'Kollar ve bacaklar arasındaki arka planı kaldır', note: 'Önizleme, kesimi sonuçta olacağı gibi gösterir.' },
    fr: { green: 'Fond vert', blue: 'Fond bleu', white: 'Blanc', black: 'Noir', custom: 'Ma couleur…', colour: 'Couleur du fond', holes: 'Retirer le fond entre les bras et les jambes', note: 'L’aperçu montre le détourage tel qu’il sera dans le résultat.' },
    uk: { green: 'Зелений (хромакей)', blue: 'Синій', white: 'Білий', black: 'Чорний', custom: 'Свій колір…', colour: 'Колір фону', holes: 'Прибирати фон у просвітах (між руками, ногами)', note: 'Попередній перегляд показує вирізку саме так, як вона буде в результаті.' },
    es: { green: 'Croma verde', blue: 'Croma azul', white: 'Blanco', black: 'Negro', custom: 'Mi color…', colour: 'Color del fondo', holes: 'Quitar el fondo entre brazos y piernas', note: 'La vista previa muestra el recorte tal como quedará en el resultado.' },
    pt: { green: 'Fundo verde', blue: 'Fundo azul', white: 'Branco', black: 'Preto', custom: 'Minha cor…', colour: 'Cor do fundo', holes: 'Remover o fundo entre braços e pernas', note: 'A prévia mostra o recorte exatamente como ficará no resultado.' }
  };
  function language() { var l = window.SMLang && SMLang.get ? SMLang.get() : (document.documentElement.lang || 'en'); return COPY[l] ? l : 'en'; }
  function t(key) { return (COPY[language()] || COPY.en)[key] || COPY.en[key]; }
  function $(id) { return document.getElementById(id); }

  var select = $('composeChroma');
  if (!select) return;
  var EXTRA = ['green', 'blue', 'white', 'black', 'custom'];
  var none = select.querySelector('option[value="none"]');
  EXTRA.forEach(function (value) { var option = document.createElement('option'); option.value = value; option.dataset.chromaUi = value; select.insertBefore(option, none); });
  var field = select.closest('label') || select.parentNode;
  var colourBox = document.createElement('label'); colourBox.className = 'field compose-chroma-colour'; colourBox.hidden = true;
  colourBox.innerHTML = '<span></span><input type="color" id="composeChromaColor" value="#00b140"/>';
  var holesBox = document.createElement('label'); holesBox.className = 'field process-switch compose-chroma-holes';
  holesBox.innerHTML = '<span></span><input type="checkbox" id="composeChromaHoles" checked/>';
  var note = document.createElement('p'); note.className = 'compose-chroma-note';
  field.after(colourBox, holesBox);
  var row = field.closest('.row'); if (row) row.after(note);
  var colour = $('composeChromaColor'), holes = $('composeChromaHoles');

  function paint() {
    EXTRA.forEach(function (value) { select.querySelector('[data-chroma-ui="' + value + '"]').textContent = t(value); });
    colourBox.firstChild.textContent = t('colour'); holesBox.firstChild.textContent = t('holes'); note.textContent = t('note');
    colourBox.hidden = select.value !== 'custom'; holesBox.hidden = select.value === 'none';
  }
  function key() { return select.value === 'custom' ? colour.value.toLowerCase() : select.value; }
  function changed() { cache = null; paint(); redraw(); }
  function redraw() { ['composeTol', 'composeFeather'].forEach(function (id) { var n = $(id); if (n) n.dispatchEvent(new Event('change', { bubbles: true })); }); }
  select.addEventListener('change', changed); colour.addEventListener('input', changed); holes.addEventListener('change', changed);
  ['composeTol'].forEach(function (id) { var n = $(id); if (n) n.addEventListener('input', function () { if (cache) cache.dirty = true; }); });
  window.addEventListener('sm:langchange', function () { setTimeout(paint, 0); });
  paint();

  /* Keyed preview of the character. One cache per source + settings: the backdrop model
     is measured from the first frames, then frozen; moving sources re-key ~12x a second
     and keep the previous frame's state (no shimmer). */
  var cache = null;
  function moving(media) { return media && (media.tagName === 'VIDEO' || /\.gif(\?|$)|image\/gif/i.test((media.currentSrc || media.src || '') + ' ' + (media.dataset && media.dataset.type || ''))); }
  function source(media, width, height) {
    if (!window.SMChroma || !media || key() === 'none') return media;
    var w = Math.max(1, Math.min(900, Math.round(width))), h = Math.max(1, Math.round(height * w / Math.max(1, width)));
    var src = media.currentSrc || media.src || '', id = [src, w, h, key(), holes.checked].join('|'), now = performance.now();
    if (!cache || cache.id !== id) { var c = document.createElement('canvas'); c.width = w; c.height = h; cache = { id: id, canvas: c, ctx: c.getContext('2d', { willReadFrequently: true }), at: 0, samples: [], state: null, model: null, frozen: false }; }
    var isMoving = moving(media) || !!media.duration;
    if (cache.at && !cache.dirty && (!isMoving || now - cache.at < 80)) return cache.canvas;
    cache.at = now; cache.dirty = false;
    cache.ctx.clearRect(0, 0, w, h); cache.ctx.drawImage(media, 0, 0, w, h);
    var image;
    try { image = cache.ctx.getImageData(0, 0, w, h); } catch (e) { return media; }
    if (!cache.frozen && (!cache.samples.length || now - cache.sampledAt > 150)) {
      cache.samples.push(image); cache.sampledAt = now; cache.model = SMChroma.estimate(cache.samples);
      if (!isMoving || cache.samples.length >= 6) { cache.frozen = true; cache.samples = []; }
    }
    if (key() === 'auto' && SMChroma.isCutout(image)) return cache.canvas;
    var model = SMChroma.resolve(key(), cache.model);
    if (!model) return cache.canvas;
    var tolerance = Number(($('composeTol') || {}).value || 45);
    var frame = isMoving ? SMChroma.frameModel(image, model, key()) : model;  // intro/flash frames on another colour
    cache.state = SMChroma.apply(image, frame, { tolerance: tolerance, softness: 16, holes: holes.checked }, frame === model ? cache.state : null);
    cache.ctx.putImageData(image, 0, 0);
    return cache.canvas;
  }
  window.SMComposeKey = {
    key: key,
    holes: function () { return holes.checked; },
    source: source,
    append: function (form) { form.set('chroma_key', key()); form.set('chroma_holes', holes.checked ? '1' : '0'); return form; }
  };
})();
