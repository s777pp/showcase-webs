/* "Depth" for the Character layer of "Create a design" (owner, 2026-10-08: at first it sat on the background; the owner
   moved it: breathing and hair are about the character). A button in the layer's media controls opens the same editor
   as the Process tab (SMDepthEditor from process-depth.js: camera, particles, air, focus pull, breathing, hair; all of it
   kept). "Apply" asks the server for a seamless 4 s clip (/api/process/depth/clip, rendered by smweb.depth_fx like the
   Process files): a cut-out comes back as a WebM with alpha, so the character stays on the scene without a box, an opaque
   picture as an MP4. The clip becomes the layer's media; the still it was made from stays in layer.depthSource and the
   options in layer.depthFx, so the effect can be changed or removed later. The Builder already plays and exports video
   layers, and "Save" uploads blob media as assets. Only still pictures (not GIF / video) can get depth. */
(function () {
  'use strict';
  if (!window.SMBuilder || !window.SMDepthEditor) return;
  var LANGS = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'];
  var COPY = {
    en: { btn: 'Animation · Depth 3D', btnOn: 'Animation · Depth 3D: on', isNew: 'NEW', title: 'Depth for the character', lead: 'The character comes alive: breathing, hair in the wind, parallax, particles around them, fog and light. It becomes a seamless 4-second video; transparent parts stay transparent.', apply: 'Apply', applying: 'Making the video…', remove: 'Remove depth', cancel: 'Cancel', onlyStill: 'Depth works with a picture character, not with GIF or video.', loadFailed: 'Could not load the character picture.', failed: 'Could not make the video. Try again.', busy: 'The server is busy. Try again in a minute.', nothing: 'Pick at least one effect.', done: 'Depth added. Save the project to keep it.' },
    ru: { btn: 'Анимация · Объём 3D', btnOn: 'Анимация · Объём 3D: включена', isNew: 'НОВОЕ', title: 'Объём для персонажа', lead: 'Персонаж оживает: дыхание, волосы на ветру, параллакс, частицы вокруг, туман и свет. Получается бесшовное видео на 4 секунды, прозрачные места остаются прозрачными.', apply: 'Применить', applying: 'Собираем видео…', remove: 'Убрать объём', cancel: 'Отмена', onlyStill: 'Объём работает с персонажем-картинкой, не с GIF и не с видео.', loadFailed: 'Не удалось загрузить картинку персонажа.', failed: 'Не удалось собрать видео. Попробуй ещё раз.', busy: 'Сервер занят. Попробуй через минуту.', nothing: 'Выбери хотя бы один эффект.', done: 'Объём добавлен. Сохрани проект, чтобы он остался.' },
    de: { btn: 'Animation · Tiefe 3D', btnOn: 'Animation · Tiefe 3D: an', isNew: 'NEU', title: 'Tiefe für die Figur', lead: 'Die Figur wird lebendig: Atmen, Haare im Wind, Parallaxe, Partikel um sie herum, Nebel und Licht. Daraus wird ein nahtloses 4-Sekunden-Video; transparente Stellen bleiben transparent.', apply: 'Anwenden', applying: 'Video wird erstellt…', remove: 'Tiefe entfernen', cancel: 'Abbrechen', onlyStill: 'Tiefe funktioniert mit einer Figur als Bild, nicht mit GIF oder Video.', loadFailed: 'Das Bild der Figur konnte nicht geladen werden.', failed: 'Das Video konnte nicht erstellt werden. Versuch es noch einmal.', busy: 'Der Server ist ausgelastet. Versuch es in einer Minute.', nothing: 'Wähle mindestens einen Effekt.', done: 'Tiefe hinzugefügt. Speichere das Projekt, damit sie bleibt.' },
    tr: { btn: 'Animasyon · Derinlik 3D', btnOn: 'Animasyon · Derinlik 3D: açık', isNew: 'YENİ', title: 'Karakter için derinlik', lead: 'Karakter canlanır: nefes, rüzgârda saçlar, paralaks, etrafında parçacıklar, sis ve ışık. 4 saniyelik kesintisiz bir videoya dönüşür; saydam yerler saydam kalır.', apply: 'Uygula', applying: 'Video hazırlanıyor…', remove: 'Derinliği kaldır', cancel: 'İptal', onlyStill: 'Derinlik resim olan bir karakterle çalışır, GIF veya videoyla çalışmaz.', loadFailed: 'Karakter resmi yüklenemedi.', failed: 'Video hazırlanamadı. Tekrar dene.', busy: 'Sunucu meşgul. Bir dakika sonra tekrar dene.', nothing: 'En az bir efekt seç.', done: 'Derinlik eklendi. Kalması için projeyi kaydet.' },
    fr: { btn: 'Animation · Profondeur 3D', btnOn: 'Animation · Profondeur 3D : activée', isNew: 'NOUVEAU', title: 'Profondeur pour le personnage', lead: 'Le personnage prend vie : respiration, cheveux au vent, parallaxe, particules autour de lui, brume et lumière. Il devient une vidéo sans raccord de 4 secondes ; les zones transparentes restent transparentes.', apply: 'Appliquer', applying: 'Création de la vidéo…', remove: 'Retirer la profondeur', cancel: 'Annuler', onlyStill: 'La profondeur fonctionne avec un personnage en image, pas avec un GIF ni une vidéo.', loadFailed: 'Impossible de charger l’image du personnage.', failed: 'Impossible de créer la vidéo. Réessaie.', busy: 'Le serveur est occupé. Réessaie dans une minute.', nothing: 'Choisis au moins un effet.', done: 'Profondeur ajoutée. Enregistre le projet pour la garder.' },
    uk: { btn: 'Анімація · Обʼєм 3D', btnOn: 'Анімація · Обʼєм 3D: увімкнено', isNew: 'НОВЕ', title: 'Обʼєм для персонажа', lead: 'Персонаж оживає: дихання, волосся на вітрі, паралакс, частинки довкола, туман і світло. Виходить безшовне відео на 4 секунди, прозорі місця лишаються прозорими.', apply: 'Застосувати', applying: 'Збираємо відео…', remove: 'Прибрати обʼєм', cancel: 'Скасувати', onlyStill: 'Обʼєм працює з персонажем-картинкою, не з GIF і не з відео.', loadFailed: 'Не вдалося завантажити картинку персонажа.', failed: 'Не вдалося зібрати відео. Спробуй ще раз.', busy: 'Сервер зайнятий. Спробуй за хвилину.', nothing: 'Обери хоча б один ефект.', done: 'Обʼєм додано. Збережи проєкт, щоб він залишився.' },
    es: { btn: 'Animación · Profundidad 3D', btnOn: 'Animación · Profundidad 3D: activada', isNew: 'NUEVO', title: 'Profundidad para el personaje', lead: 'El personaje cobra vida: respiración, cabello al viento, paralaje, partículas a su alrededor, niebla y luz. Se convierte en un vídeo sin cortes de 4 segundos; las partes transparentes siguen transparentes.', apply: 'Aplicar', applying: 'Creando el vídeo…', remove: 'Quitar la profundidad', cancel: 'Cancelar', onlyStill: 'La profundidad funciona con un personaje de imagen, no con GIF ni vídeo.', loadFailed: 'No se pudo cargar la imagen del personaje.', failed: 'No se pudo crear el vídeo. Inténtalo de nuevo.', busy: 'El servidor está ocupado. Inténtalo en un minuto.', nothing: 'Elige al menos un efecto.', done: 'Profundidad añadida. Guarda el proyecto para conservarla.' },
    pt: { btn: 'Animação · Profundidade 3D', btnOn: 'Animação · Profundidade 3D: ligada', isNew: 'NOVO', title: 'Profundidade para o personagem', lead: 'O personagem ganha vida: respiração, cabelo ao vento, paralaxe, partículas ao redor, névoa e luz. Vira um vídeo contínuo de 4 segundos; as partes transparentes continuam transparentes.', apply: 'Aplicar', applying: 'Criando o vídeo…', remove: 'Remover a profundidade', cancel: 'Cancelar', onlyStill: 'A profundidade funciona com um personagem de imagem, não com GIF nem vídeo.', loadFailed: 'Não foi possível carregar a imagem do personagem.', failed: 'Não foi possível criar o vídeo. Tente de novo.', busy: 'O servidor está ocupado. Tente em um minuto.', nothing: 'Escolha pelo menos um efeito.', done: 'Profundidade adicionada. Salve o projeto para mantê-la.' }
  };
  var SOURCE_SIDE = 1600;
  function lang() { var l = window.SMLang && SMLang.get ? SMLang.get() : 'en'; return LANGS.indexOf(l) >= 0 ? l : 'en'; }
  function t(key) { return COPY[lang()][key] || COPY.en[key] || key; }
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function isStill(layer) {
    if (layer.depthSource) return true;
    var type = String(layer.mediaType || '');
    if (type === 'image/gif' || type.indexOf('video/') === 0) return false;
    return !/\.(?:gif|mp4|webm|mov)(?:\?|$)/i.test(layer.src || '');
  }
  function fetchable(url) {
    return /^https:\/\/(shared|cdn)\.cloudflare\.steamstatic\.com\//i.test(url || '') ? '/api/steam/proxy-image?url=' + encodeURIComponent(url) : url;
  }

  var root = SMBuilder.root;
  var controls = document.getElementById('builderMediaControls');
  if (!controls) return;
  var button = el('button', 'btn bdepth__btn'); button.type = 'button';
  controls.prepend(button);
  function current() { var layer = SMBuilder.current(); return layer && layer.type === 'character' ? layer : null; }
  function paintButton() {
    var layer = current();
    button.hidden = !layer || !layer.src;
    // Owner: say that it is an animation and that it is new, and make the button stand out.
    if (layer) button.replaceChildren(el('span', 'bdepth__btn-text', layer.depthFx ? t('btnOn') : t('btn')), el('mark', 'bdepth__new', t('isNew')));
    button.classList.toggle('is-on', !!(layer && layer.depthFx));
  }
  root.addEventListener('sm:builder-select', paintButton);
  window.addEventListener('sm:langchange', function () { setTimeout(paintButton, 0); });
  paintButton();

  var modal = null;
  function close() { if (modal) { modal.remove(); modal = null; document.body.classList.remove('pon-modal-open'); } }
  function open() {
    var layer = current();
    if (!layer || modal) return;
    modal = el('div', 'pon-modal bdepth');
    var backdrop = el('div', 'pon-modal__backdrop'); backdrop.addEventListener('click', close);
    var dialog = el('section', 'pon-intro pon-modal__dialog bdepth__dialog');
    dialog.setAttribute('role', 'dialog'); dialog.setAttribute('aria-modal', 'true'); dialog.setAttribute('aria-labelledby', 'bdepthTitle');
    var x = el('button', 'pon-modal__x', '×'); x.type = 'button'; x.setAttribute('aria-label', t('cancel')); x.addEventListener('click', close);
    var title = el('h2', 'pon-intro__title', t('title')); title.id = 'bdepthTitle';
    var lead = el('p', 'pon-intro__lead', t('lead'));
    var host = el('div', 'pdepth pdepth--always bdepth__editor');
    var note = el('p', 'bdepth__note'); note.hidden = true;
    var foot = el('div', 'bdepth__foot');
    var apply = el('button', 'btn bdepth__apply', t('apply')); apply.type = 'button';
    var remove = el('button', 'btn ghost', t('remove')); remove.type = 'button'; remove.hidden = !layer.depthFx;
    var cancel = el('button', 'btn ghost', t('cancel')); cancel.type = 'button'; cancel.addEventListener('click', close);
    foot.append(apply, remove, cancel);
    dialog.append(x, title, lead, host, note, foot);
    modal.append(backdrop, dialog);
    modal.addEventListener('keydown', function (event) { if (event.key === 'Escape') close(); });
    document.body.append(modal);
    document.body.classList.add('pon-modal-open');
    requestAnimationFrame(function () { modal && modal.classList.add('is-open'); });
    function say(text) { note.textContent = text || ''; note.hidden = !text; }
    if (!isStill(layer)) { host.hidden = true; apply.hidden = true; say(t('onlyStill')); return; }

    var editor = SMDepthEditor.create(host, { keepSource: true, fitHeight: true, largePreview: true });
    var canvas = null;
    fetch(fetchable(layer.depthSource || layer.src), { credentials: 'same-origin' })
      .then(function (r) { if (!r.ok) throw new Error('load'); return r.blob(); })
      .then(function (blob) { return createImageBitmap(blob); })
      .then(function (bitmap) {
        var k = Math.min(1, SOURCE_SIDE / Math.max(bitmap.width, bitmap.height));
        canvas = document.createElement('canvas');
        canvas.width = Math.round(bitmap.width * k); canvas.height = Math.round(bitmap.height * k);
        canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
        editor.setPicture(canvas);
        if (layer.depthFx) editor.load(layer.depthFx);
      })
      .catch(function () { say(t('loadFailed')); apply.disabled = true; });

    function clip(retry) {
      var options = editor.options();
      if (!options) { say(t('nothing')); return Promise.resolve(null); }
      return fetch('/api/process/depth/clip', {
        method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: editor.picture.token, options: options })
      }).then(function (r) {
        if (r.status === 404 && retry && canvas) {
          // The prepared picture expired (1 h): prepare it again, then try once more.
          editor.setPicture(canvas);
          return new Promise(function (done) {
            var wait = setInterval(function () { if (editor.picture.token) { clearInterval(wait); done(clip(false)); } }, 400);
          });
        }
        if (r.status === 503) throw new Error('busy');
        if (!r.ok) throw new Error('failed');
        return r.blob().then(function (blob) { return { blob: blob, options: options }; });
      });
    }
    apply.addEventListener('click', function () {
      if (!editor.picture.token) return;
      apply.disabled = true; say(t('applying'));
      clip(true).then(function (result) {
        if (!result) return;
        if (!layer.depthSource) { layer.depthSource = layer.src; layer.depthSourceType = layer.mediaType || 'image/png'; }
        layer.depthFx = result.options;
        layer.src = URL.createObjectURL(result.blob);
        layer.mediaType = result.blob.type || 'video/mp4';   // video/webm (with alpha) for a cut-out
        layer.animatedSource = true;
        SMBuilder.sync(); SMBuilder.redraw(); SMBuilder.commit();
        close();
        paintButton();
        var status = document.getElementById('builderStatus');
        if (status) { status.textContent = t('done'); status.className = 'status ok'; }
      }).catch(function (error) {
        say(t(error && error.message === 'busy' ? 'busy' : 'failed'));
      }).finally(function () { apply.disabled = false; });
    });
    remove.addEventListener('click', function () {
      if (!layer.depthSource) return;
      layer.src = layer.depthSource;
      layer.mediaType = layer.depthSourceType || 'image/png';
      layer.animatedSource = false;
      delete layer.depthSource; delete layer.depthSourceType; delete layer.depthFx;
      SMBuilder.sync(); SMBuilder.redraw(); SMBuilder.commit();
      close(); paintButton();
    });
  }
  button.addEventListener('click', open);
  window.SMBuilderDepth = { open: open, close: close };
})();
