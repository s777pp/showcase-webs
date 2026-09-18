(function () {
  'use strict';

  var root = document.documentElement;
  var loader = document.getElementById('homeLoader');
  if (!loader) {
    root.classList.remove('home-is-loading');
    return;
  }

  var copy = {
    en: ['SYSTEM / STARTUP', 'Preparing your workspace', 'Loading interface', 'Loading 3D scene', 'Ready'],
    ru: ['СИСТЕМА / ЗАПУСК', 'Подготавливаем рабочее пространство', 'Загружаем интерфейс', 'Загружаем 3D-сцену', 'Готово'],
    de: ['SYSTEM / START', 'Arbeitsbereich wird vorbereitet', 'Benutzeroberfläche wird geladen', '3D-Szene wird geladen', 'Bereit'],
    fr: ['SYSTÈME / DÉMARRAGE', 'Préparation de votre espace', 'Chargement de l’interface', 'Chargement de la scène 3D', 'Prêt'],
    uk: ['СИСТЕМА / ЗАПУСК', 'Готуємо робочий простір', 'Завантажуємо інтерфейс', 'Завантажуємо 3D-сцену', 'Готово'],
    es: ['SISTEMA / INICIO', 'Preparando tu espacio de trabajo', 'Cargando la interfaz', 'Cargando la escena 3D', 'Listo'],
    pt: ['SISTEMA / INÍCIO', 'Preparando o espaço de trabalho', 'Carregando a interface', 'Carregando a cena 3D', 'Pronto'],
    tr: ['SİSTEM / BAŞLATMA', 'Çalışma alanınız hazırlanıyor', 'Arayüz yükleniyor', '3D sahne yükleniyor', 'Hazır']
  };
  var routeLang = (location.pathname.split('/')[1] || '').toLowerCase();
  var language = copy[routeLang] ? routeLang : ((document.documentElement.lang || 'en').slice(0, 2).toLowerCase());
  var words = copy[language] || copy.en;
  var title = document.getElementById('homeLoaderTitle');
  var eyebrow = document.getElementById('homeLoaderEyebrow');
  var stage = document.getElementById('homeLoaderStage');
  var bar = document.getElementById('homeLoaderProgress');
  var percent = document.getElementById('homeLoaderPercent');
  var startedAt = window.__SM_HOME_LOADER_START || performance.now();
  var pageReady = document.readyState === 'complete';
  var fontsReady = !document.fonts;
  var heroReady = false;
  var heroObserver = null;
  var finished = false;
  var progress = 4;

  eyebrow.textContent = words[0];
  title.textContent = words[1];
  stage.textContent = words[2];
  loader.setAttribute('aria-label', words[1]);
  document.body.setAttribute('aria-busy', 'true');

  function paint(next) {
    progress = Math.max(progress, Math.min(100, Math.round(next)));
    bar.style.width = progress + '%';
    percent.textContent = progress + '%';
  }

  function maybeFinish() {
    if (finished || !pageReady || !fontsReady || !heroReady) return;
    var minimumDelay = Math.max(0, 650 - (performance.now() - startedAt));
    window.setTimeout(finish, minimumDelay);
  }

  function finish() {
    if (finished) return;
    finished = true;
    stage.textContent = words[4];
    paint(100);
    window.setTimeout(function () {
      loader.classList.add('is-leaving');
      root.classList.remove('home-is-loading');
      root.classList.add('home-is-ready');
      document.body.removeAttribute('aria-busy');
      window.setTimeout(function () { loader.remove(); }, 480);
    }, 140);
  }

  function markPageReady() {
    pageReady = true;
    paint(heroReady ? 94 : 72);
    maybeFinish();
  }

  function markHeroReady() {
    if (heroReady) return;
    heroReady = true;
    if (heroObserver) heroObserver.disconnect();
    stage.textContent = words[2];
    paint(pageReady ? 96 : 86);
    maybeFinish();
  }

  document.addEventListener('showcasemaker:hero-ready', markHeroReady, { once: true });
  var heroScene = document.querySelector('.creator-scene');
  if (heroScene && (heroScene.classList.contains('is-vrm-ready') || heroScene.classList.contains('is-vrm-fallback'))) {
    markHeroReady();
  } else if (heroScene && typeof MutationObserver !== 'undefined') {
    // This also supports an older cached hero-vrm.js: that script sets these
    // classes even though it does not dispatch the newer readiness event.
    heroObserver = new MutationObserver(function () {
      if (heroScene.classList.contains('is-vrm-ready') || heroScene.classList.contains('is-vrm-fallback')) {
        markHeroReady();
      }
    });
    heroObserver.observe(heroScene, { attributes: true, attributeFilter: ['class'] });
  }

  if (document.readyState === 'complete') markPageReady();
  else window.addEventListener('load', markPageReady, { once: true });

  if (document.fonts) {
    document.fonts.ready.then(function () {
      fontsReady = true;
      paint(78);
      maybeFinish();
    }, function () {
      fontsReady = true;
      maybeFinish();
    });
  }

  window.requestAnimationFrame(function () {
    paint(12);
    window.setTimeout(function () {
      if (!heroReady) {
        stage.textContent = words[3];
        paint(28);
      }
    }, 180);
  });

  // A broken third-party font or graphics driver must never trap the visitor.
  window.setTimeout(finish, 45000);
}());
