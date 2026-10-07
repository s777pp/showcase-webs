/* Process tab for people who have never seen a Steam showcase (2026-10-07, owner: "a user who knows nothing").
   1) "How it works" window over the page (owner: a pop-up, not a block in the page), opened by itself the first
      time the Process tab is shown: a small Steam profile with the showcase lit up, three steps and the level-10
      requirement. Got it / x / Esc / a click outside close it and that is remembered in this browser; the
      "How does it work?" pill above step 1 opens it again. Automated browsers (navigator.webdriver) do not get
      it on their own unless the URL has ?intro=1, so UI test scripts are not blocked by it.
   2) Step 2: "Recommended" on Workshop, the English Steam names moved out of the cards (the "Which one do I
      have?" help still maps them), the help opens for first-time visitors.
   3) Step 4 for guests: the sign-in suggestion is a quiet tip instead of a warning-looking box.
   Presentation only: no processing option is read or changed here. Styles: css/process-onboarding.css. */
(function () {
  'use strict';
  var root = document.getElementById('tab-process');
  if (!root) return;
  var LANGS = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'];
  var COPY = {
    en: { kicker: 'How it works', title: 'A showcase is a block of pictures on your Steam profile', lead: 'Steam shows it right under your name. We cut your art into the exact pieces Steam needs, so it reads as one picture.', s1: 'Add a picture, GIF or video', s1d: 'Or try the sample picture.', s2: 'We cut it into parts', s2d: 'Right sizes, under 5 MB, ready for Steam.', s3: 'Put the parts on Steam', s3d: 'The free extension uploads them for you.', level: 'Showcases open from Steam profile level 10.', guide: 'Step-by-step guide', close: 'Got it', reopen: 'How does it work?', recommended: 'Recommended', guestTip: 'Tip: sign in, and after cutting we will show a detailed Steam check of every file.', guestLogin: 'Sign in', demoName: 'Your profile', demoLevel: 'Level 10', demoShowcase: 'Your showcase' },
    ru: { kicker: 'Как это работает', title: 'Витрина — это блок с картинками в твоём профиле Steam', lead: 'Steam показывает её прямо под ником. Мы нарежем твой арт на части точно под Steam, и в профиле они сложатся в одну картинку.', s1: 'Добавь картинку, GIF или видео', s1d: 'Или попробуй на примере.', s2: 'Мы нарежем её на части', s2d: 'Нужный размер, до 5 МБ, готово для Steam.', s3: 'Поставь части в Steam', s3d: 'Бесплатное расширение загрузит их за тебя.', level: 'Витрины открываются с 10 уровня профиля Steam.', guide: 'Пошаговая инструкция', close: 'Понятно', reopen: 'Как это работает?', recommended: 'Рекомендуем', guestTip: 'Совет: войди — и после нарезки мы покажем подробную проверку каждого файла для Steam.', guestLogin: 'Войти', demoName: 'Твой профиль', demoLevel: 'Уровень 10', demoShowcase: 'Твоя витрина' },
    de: { kicker: 'So funktioniert es', title: 'Eine Vitrine ist ein Bildblock in deinem Steam-Profil', lead: 'Steam zeigt sie direkt unter deinem Namen. Wir schneiden dein Artwork in genau die Teile, die Steam braucht, sodass sie wie ein Bild wirken.', s1: 'Bild, GIF oder Video hinzufügen', s1d: 'Oder das Beispielbild testen.', s2: 'Wir schneiden es in Teile', s2d: 'Richtige Größen, unter 5 MB, bereit für Steam.', s3: 'Teile zu Steam bringen', s3d: 'Die kostenlose Erweiterung lädt sie für dich hoch.', level: 'Vitrinen gibt es ab Steam-Profillevel 10.', guide: 'Schritt-für-Schritt-Anleitung', close: 'Verstanden', reopen: 'Wie funktioniert das?', recommended: 'Empfohlen', guestTip: 'Tipp: Melde dich an, dann zeigen wir nach dem Schneiden eine genaue Steam-Prüfung jeder Datei.', guestLogin: 'Anmelden', demoName: 'Dein Profil', demoLevel: 'Level 10', demoShowcase: 'Deine Vitrine' },
    tr: { kicker: 'Nasıl çalışır', title: 'Vitrin, Steam profilindeki bir görsel bloğudur', lead: 'Steam onu adının hemen altında gösterir. Görselini Steam’in istediği parçalara keseriz, profilde tek bir resim gibi görünür.', s1: 'Resim, GIF veya video ekle', s1d: 'Ya da örnek görseli dene.', s2: 'Parçalara keseriz', s2d: 'Doğru boyutlar, 5 MB altı, Steam’e hazır.', s3: 'Parçaları Steam’e koy', s3d: 'Ücretsiz eklenti senin yerine yükler.', level: 'Vitrinler Steam profil seviyesi 10’da açılır.', guide: 'Adım adım rehber', close: 'Anladım', reopen: 'Nasıl çalışır?', recommended: 'Önerilen', guestTip: 'İpucu: giriş yaparsan kesimden sonra her dosya için ayrıntılı Steam kontrolü gösteririz.', guestLogin: 'Giriş yap', demoName: 'Profilin', demoLevel: 'Seviye 10', demoShowcase: 'Vitrinin' },
    fr: { kicker: 'Comment ça marche', title: 'Une vitrine est un bloc d’images sur votre profil Steam', lead: 'Steam l’affiche juste sous votre nom. Nous découpons votre image aux dimensions exactes de Steam, pour qu’elle se lise comme une seule image.', s1: 'Ajoutez une image, un GIF ou une vidéo', s1d: 'Ou essayez l’image d’exemple.', s2: 'Nous la découpons en parties', s2d: 'Bonnes tailles, moins de 5 Mo, prêtes pour Steam.', s3: 'Mettez les parties sur Steam', s3d: 'L’extension gratuite les envoie pour vous.', level: 'Les vitrines s’ouvrent au niveau 10 du profil Steam.', guide: 'Guide pas à pas', close: 'Compris', reopen: 'Comment ça marche ?', recommended: 'Recommandé', guestTip: 'Astuce : connectez-vous et, après le découpage, nous afficherons une vérification Steam détaillée de chaque fichier.', guestLogin: 'Se connecter', demoName: 'Votre profil', demoLevel: 'Niveau 10', demoShowcase: 'Votre vitrine' },
    uk: { kicker: 'Як це працює', title: 'Вітрина — це блок із картинками у твоєму профілі Steam', lead: 'Steam показує її одразу під ніком. Ми наріжемо твій арт на частини точно під Steam, і в профілі вони складуться в одну картинку.', s1: 'Додай картинку, GIF або відео', s1d: 'Або спробуй на прикладі.', s2: 'Ми наріжемо її на частини', s2d: 'Потрібний розмір, до 5 МБ, готово для Steam.', s3: 'Постав частини в Steam', s3d: 'Безкоштовне розширення завантажить їх за тебе.', level: 'Вітрини відкриваються з 10 рівня профілю Steam.', guide: 'Покрокова інструкція', close: 'Зрозуміло', reopen: 'Як це працює?', recommended: 'Радимо', guestTip: 'Порада: увійди — і після нарізки ми покажемо детальну перевірку кожного файлу для Steam.', guestLogin: 'Увійти', demoName: 'Твій профіль', demoLevel: 'Рівень 10', demoShowcase: 'Твоя вітрина' },
    es: { kicker: 'Cómo funciona', title: 'Un escaparate es un bloque de imágenes en tu perfil de Steam', lead: 'Steam lo muestra justo debajo de tu nombre. Cortamos tu arte en las piezas exactas que necesita Steam, para que se vea como una sola imagen.', s1: 'Añade una imagen, GIF o vídeo', s1d: 'O prueba con la imagen de ejemplo.', s2: 'La cortamos en partes', s2d: 'Tamaños correctos, menos de 5 MB, listas para Steam.', s3: 'Pon las partes en Steam', s3d: 'La extensión gratuita las sube por ti.', level: 'Los escaparates se abren desde el nivel 10 del perfil de Steam.', guide: 'Guía paso a paso', close: 'Entendido', reopen: '¿Cómo funciona?', recommended: 'Recomendado', guestTip: 'Consejo: inicia sesión y, tras el corte, te mostraremos una comprobación de Steam detallada de cada archivo.', guestLogin: 'Iniciar sesión', demoName: 'Tu perfil', demoLevel: 'Nivel 10', demoShowcase: 'Tu escaparate' },
    pt: { kicker: 'Como funciona', title: 'Uma vitrine é um bloco de imagens no seu perfil da Steam', lead: 'A Steam mostra a vitrine logo abaixo do seu nome. Cortamos sua arte nas peças exatas que a Steam pede, para ela aparecer como uma imagem só.', s1: 'Adicione uma imagem, GIF ou vídeo', s1d: 'Ou teste com a imagem de exemplo.', s2: 'Nós cortamos em partes', s2d: 'Tamanhos certos, menos de 5 MB, prontas para a Steam.', s3: 'Coloque as partes na Steam', s3d: 'A extensão gratuita envia para você.', level: 'As vitrines são liberadas a partir do nível 10 do perfil da Steam.', guide: 'Guia passo a passo', close: 'Entendi', reopen: 'Como funciona?', recommended: 'Recomendado', guestTip: 'Dica: entre na conta e, depois do corte, mostraremos uma verificação detalhada de cada arquivo para a Steam.', guestLogin: 'Entrar', demoName: 'Seu perfil', demoLevel: 'Nível 10', demoShowcase: 'Sua vitrine' }
  };
  var STORE = 'sm_process_intro_closed';
  function lang() {
    var l = (window.SMLang && SMLang.get ? SMLang.get() : document.documentElement.lang || 'en').slice(0, 2);
    return LANGS.indexOf(l) >= 0 ? l : 'en';
  }
  function t(key) { return COPY[lang()][key] || COPY.en[key] || key; }
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function closed() { try { return localStorage.getItem(STORE) === '1'; } catch (_) { return false; } }
  function setClosed(value) { try { if (value) localStorage.setItem(STORE, '1'); else localStorage.removeItem(STORE); } catch (_) {} }
  function url(path) { return window.SMLang && SMLang.url ? SMLang.url(path) : path; }

  var controls = root.querySelector('.process-controls');
  var reopen = el('button', 'pon-reopen'); reopen.type = 'button';
  if (controls) controls.prepend(reopen);

  var modal = null, lastFocus = null;
  function introContent(dialog) {
    // A tiny Steam profile: avatar, name, level, and the showcase cut into 5 parts of the sample art.
    var demo = el('div', 'pon-demo'); demo.setAttribute('aria-hidden', 'true');
    var head = el('div', 'pon-demo__head');
    var level = el('span', 'pon-demo__level', '10'); level.title = t('demoLevel');
    head.append(el('span', 'pon-demo__avatar'), el('span', 'pon-demo__name', t('demoName')), level);
    var showcase = el('div', 'pon-demo__showcase');
    showcase.append(el('span', 'pon-demo__label', t('demoShowcase')));
    var parts = el('div', 'pon-demo__parts');
    for (var i = 0; i < 5; i += 1) { var part = el('i'); part.style.setProperty('--i', i); parts.append(part); }
    showcase.append(parts);
    demo.append(head, showcase, el('span', 'pon-demo__rest'), el('span', 'pon-demo__rest is-short'));
    var text = el('div', 'pon-intro__text');
    text.append(el('span', 'pon-intro__kicker', t('kicker')));
    var title = el('h2', 'pon-intro__title', t('title')); title.id = 'ponTitle';
    text.append(title, el('p', 'pon-intro__lead', t('lead')));
    var steps = el('ol', 'pon-steps');
    [['s1', 's1d'], ['s2', 's2d'], ['s3', 's3d']].forEach(function (pair, index) {
      var li = el('li'); li.append(el('span', 'pon-steps__n', String(index + 1)));
      var body = el('span'); body.append(el('b', null, t(pair[0])), el('small', null, t(pair[1]))); li.append(body);
      steps.append(li);
    });
    text.append(steps);
    var foot = el('div', 'pon-intro__foot');
    foot.append(el('span', 'pon-intro__level', t('level')));
    var guide = el('a', 'pon-intro__guide', t('guide')); guide.href = url('/guides'); guide.target = '_blank'; guide.rel = 'noopener';
    foot.append(guide);
    text.append(foot);
    var ok = el('button', 'pon-intro__close', t('close')); ok.type = 'button';
    ok.addEventListener('click', hide);
    text.append(ok);
    var x = el('button', 'pon-modal__x', '×'); x.type = 'button'; x.setAttribute('aria-label', t('close'));
    x.addEventListener('click', hide);
    dialog.replaceChildren(x, demo, text);
    return ok;
  }
  function show() {
    if (modal) return;
    lastFocus = document.activeElement;
    modal = el('div', 'pon-modal');
    var backdrop = el('div', 'pon-modal__backdrop'); backdrop.addEventListener('click', hide);
    var dialog = el('section', 'pon-intro pon-modal__dialog');
    dialog.setAttribute('role', 'dialog'); dialog.setAttribute('aria-modal', 'true'); dialog.setAttribute('aria-labelledby', 'ponTitle');
    var ok = introContent(dialog);
    modal.append(backdrop, dialog);
    modal.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') { event.preventDefault(); hide(); return; }
      if (event.key !== 'Tab') return;
      var items = dialog.querySelectorAll('a[href],button');
      if (!items.length) return;
      var first = items[0], last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
    document.body.append(modal);
    document.body.classList.add('pon-modal-open');
    requestAnimationFrame(function () { modal && modal.classList.add('is-open'); ok.focus({ preventScroll: true }); });
  }
  function hide() {
    setClosed(true);
    if (!modal) return;
    modal.remove(); modal = null;
    document.body.classList.remove('pon-modal-open');
    if (lastFocus && lastFocus.isConnected) lastFocus.focus({ preventScroll: true });
  }
  reopen.addEventListener('click', show);
  function autoShow() {
    if (closed() || modal || !root.classList.contains('active')) return;
    if (navigator.webdriver && !/[?&]intro=1\b/.test(location.search)) return;
    show();
  }
  // First visit: wait for the page to settle, and for the Process tab if another tab was opened first.
  setTimeout(autoShow, 600);
  new MutationObserver(function () { setTimeout(autoShow, 200); }).observe(root, { attributes: true, attributeFilter: ['class'] });
  function sync() {
    reopen.textContent = t('reopen');
    var help = document.getElementById('processModeHelp');
    if (help && !closed() && !help.dataset.ponTouched) help.open = true;
  }

  // Step 2: a "Recommended" badge on Workshop.
  function paintModes() {
    var workshop = root.querySelector('#processModeCard .mode[data-mode="workshop"]');
    if (!workshop) return;
    var badge = workshop.querySelector('.pon-badge');
    if (!badge) { badge = el('mark', 'pon-badge'); workshop.prepend(badge); }  // not a <span>: app.js writes the hint into the first span
    badge.textContent = t('recommended');
  }
  var help = document.getElementById('processModeHelp');
  if (help) help.addEventListener('toggle', function () { help.dataset.ponTouched = '1'; });

  // Step 4 for guests: one quiet line instead of a box that looks like an error.
  var hint = document.getElementById('processReadinessHint');
  function paintHint() {
    if (!hint) return;
    hint.classList.add('pon-guest');
    hint.querySelectorAll('[data-i]').forEach(function (node) { node.removeAttribute('data-i'); });
    var title = hint.querySelector('b'); if (title) title.hidden = true;
    var body = hint.querySelector('span'); if (body) body.textContent = t('guestTip');
    var login = document.getElementById('processReadinessLogin'); if (login) login.textContent = t('guestLogin');
  }

  function paint() { paintModes(); paintHint(); sync(); if (modal) introContent(modal.querySelector('.pon-modal__dialog')); }
  paint();
  window.addEventListener('sm:langchange', function () { setTimeout(paint, 0); });
  window.SMProcessOnboarding = { show: show, hide: hide, reset: function () { setClosed(false); } };
})();
