/* Process tab for people who have never seen a Steam showcase (2026-10-07, owner: "a user who knows nothing").
   1) "How it works" window over the page (owner: a pop-up, not a block in the page), opened by itself the first
      time the Process tab is shown: a small Steam profile with the showcase lit up, three steps and the level-10
      requirement. Got it / x / Esc / a click outside close it and that is remembered in this browser; the
      "How does it work?" pill above step 1 opens it again. Automated browsers (navigator.webdriver) do not get
      it on their own unless the URL has ?intro=1, so UI test scripts are not blocked by it.
   2) Step 2: "Recommended" on Workshop, the English Steam names moved out of the cards (the "Which one do I
      have?" help still maps them), the help opens for first-time visitors.
   3) Step 4 for guests: the sign-in suggestion is a quiet tip instead of a warning-looking box.
   4) Inside the window: a 3-question wizard (level, showcase type, what you have) that ends on the right type with
      the file picker / link field / sample open; below level 10 it offers the owner's level-up partner link.
   Presentation only: no processing option is read or changed here, except the showcase type the wizard picks. Styles: css/process-onboarding.css. */
(function () {
  'use strict';
  var root = document.getElementById('tab-process');
  if (!root) return;
  var LANGS = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'];
  var COPY = {
    en: { kicker: 'How it works', title: 'A showcase is a block of pictures on your Steam profile', lead: 'Steam shows it right under your name. We cut your art into the exact pieces Steam needs, so it reads as one picture.', s1: 'Add a picture, GIF or video', s1d: 'Or try the sample picture.', s2: 'We cut it into parts', s2d: 'Right sizes, under 5 MB, ready for Steam.', s3: 'Put the parts on Steam', s3d: 'The free extension uploads them for you.', level: 'Showcases open from Steam profile level 10.', guide: 'Step-by-step guide', close: 'Got it', reopen: 'How does it work?', recommended: 'Recommended', guestTip: 'Tip: sign in, and after cutting we will show a detailed Steam check of every file.', guestLogin: 'Sign in', demoName: 'Your profile', demoLevel: 'Level 10', demoShowcase: 'Your showcase', start: 'Find my showcase — 3 questions', back: 'Back', stepOf: 'Question {n} of 3', qLevel: 'What is your Steam profile level?', aLevelOk: '10 or higher', aLevelLow: 'Below 10', aLevelUnknown: 'I don’t know', levelHint: 'It is the number in a circle next to your name on your Steam profile.', lowTitle: 'Showcases open at level 10', lowText: 'Steam adds showcases from profile level 10. You can raise your level quickly here, and prepare the files now so they are ready.', lowBoost: 'Raise my Steam level', lowPrepare: 'Prepare the files now', qType: 'Which showcase do you want?', typeWs: '5 pictures in a row', typeWsd: 'Workshop · the most popular', typeFt: 'One big picture', typeFtd: 'Featured', typeSp: 'Big picture + a narrow strip', typeSpd: 'Artwork Split', typeUnknown: 'I don’t know yet', typeUnknownd: 'We will start with Workshop', qFile: 'What do you have?', fileHave: 'A picture, GIF or video', fileHaved: 'On this device', fileLink: 'A link', fileLinkd: 'YouTube, Pinterest, Reddit and 50+ sites', fileNone: 'Nothing yet', fileNoned: 'Show me with a sample' },
    ru: { kicker: 'Как это работает', title: 'Витрина — это блок с картинками в твоём профиле Steam', lead: 'Steam показывает её прямо под ником. Мы нарежем твой арт на части точно под Steam, и в профиле они сложатся в одну картинку.', s1: 'Добавь картинку, GIF или видео', s1d: 'Или попробуй на примере.', s2: 'Мы нарежем её на части', s2d: 'Нужный размер, до 5 МБ, готово для Steam.', s3: 'Поставь части в Steam', s3d: 'Бесплатное расширение загрузит их за тебя.', level: 'Витрины открываются с 10 уровня профиля Steam.', guide: 'Пошаговая инструкция', close: 'Понятно', reopen: 'Как это работает?', recommended: 'Рекомендуем', guestTip: 'Совет: войди — и после нарезки мы покажем подробную проверку каждого файла для Steam.', guestLogin: 'Войти', demoName: 'Твой профиль', demoLevel: 'Уровень 10', demoShowcase: 'Твоя витрина', start: 'Подобрать витрину — 3 вопроса', back: 'Назад', stepOf: 'Вопрос {n} из 3', qLevel: 'Какой у тебя уровень профиля Steam?', aLevelOk: '10 и выше', aLevelLow: 'Ниже 10', aLevelUnknown: 'Не знаю', levelHint: 'Это число в кружке рядом с ником в твоём профиле Steam.', lowTitle: 'Витрины открываются с 10 уровня', lowText: 'Steam даёт витрины с 10 уровня профиля. Уровень можно быстро поднять здесь, а файлы подготовить уже сейчас, чтобы были готовы.', lowBoost: 'Поднять уровень Steam', lowPrepare: 'Подготовить файлы сейчас', qType: 'Какую витрину хочешь?', typeWs: '5 картинок в ряд', typeWsd: 'Workshop · самая популярная', typeFt: 'Одна большая картинка', typeFtd: 'Featured', typeSp: 'Большая картинка + узкая полоса', typeSpd: 'Artwork Split', typeUnknown: 'Пока не знаю', typeUnknownd: 'Начнём с Workshop', qFile: 'Что у тебя есть?', fileHave: 'Картинка, GIF или видео', fileHaved: 'На этом устройстве', fileLink: 'Ссылка', fileLinkd: 'YouTube, Pinterest, Reddit и ещё 50+ сайтов', fileNone: 'Пока ничего', fileNoned: 'Покажи на примере' },
    de: { kicker: 'So funktioniert es', title: 'Eine Vitrine ist ein Bildblock in deinem Steam-Profil', lead: 'Steam zeigt sie direkt unter deinem Namen. Wir schneiden dein Artwork in genau die Teile, die Steam braucht, sodass sie wie ein Bild wirken.', s1: 'Bild, GIF oder Video hinzufügen', s1d: 'Oder das Beispielbild testen.', s2: 'Wir schneiden es in Teile', s2d: 'Richtige Größen, unter 5 MB, bereit für Steam.', s3: 'Teile zu Steam bringen', s3d: 'Die kostenlose Erweiterung lädt sie für dich hoch.', level: 'Vitrinen gibt es ab Steam-Profillevel 10.', guide: 'Schritt-für-Schritt-Anleitung', close: 'Verstanden', reopen: 'Wie funktioniert das?', recommended: 'Empfohlen', guestTip: 'Tipp: Melde dich an, dann zeigen wir nach dem Schneiden eine genaue Steam-Prüfung jeder Datei.', guestLogin: 'Anmelden', demoName: 'Dein Profil', demoLevel: 'Level 10', demoShowcase: 'Deine Vitrine', start: 'Meine Vitrine finden — 3 Fragen', back: 'Zurück', stepOf: 'Frage {n} von 3', qLevel: 'Welches Level hat dein Steam-Profil?', aLevelOk: '10 oder höher', aLevelLow: 'Unter 10', aLevelUnknown: 'Weiß ich nicht', levelHint: 'Es ist die Zahl im Kreis neben deinem Namen im Steam-Profil.', lowTitle: 'Vitrinen gibt es ab Level 10', lowText: 'Steam schaltet Vitrinen ab Profillevel 10 frei. Hier kannst du dein Level schnell erhöhen und die Dateien schon jetzt vorbereiten.', lowBoost: 'Steam-Level erhöhen', lowPrepare: 'Dateien jetzt vorbereiten', qType: 'Welche Vitrine möchtest du?', typeWs: '5 Bilder in einer Reihe', typeWsd: 'Workshop · am beliebtesten', typeFt: 'Ein großes Bild', typeFtd: 'Featured', typeSp: 'Großes Bild + schmaler Streifen', typeSpd: 'Artwork Split', typeUnknown: 'Weiß ich noch nicht', typeUnknownd: 'Wir starten mit Workshop', qFile: 'Was hast du?', fileHave: 'Ein Bild, GIF oder Video', fileHaved: 'Auf diesem Gerät', fileLink: 'Einen Link', fileLinkd: 'YouTube, Pinterest, Reddit und 50+ Seiten', fileNone: 'Noch nichts', fileNoned: 'Zeig es mir an einem Beispiel' },
    tr: { kicker: 'Nasıl çalışır', title: 'Vitrin, Steam profilindeki bir görsel bloğudur', lead: 'Steam onu adının hemen altında gösterir. Görselini Steam’in istediği parçalara keseriz, profilde tek bir resim gibi görünür.', s1: 'Resim, GIF veya video ekle', s1d: 'Ya da örnek görseli dene.', s2: 'Parçalara keseriz', s2d: 'Doğru boyutlar, 5 MB altı, Steam’e hazır.', s3: 'Parçaları Steam’e koy', s3d: 'Ücretsiz eklenti senin yerine yükler.', level: 'Vitrinler Steam profil seviyesi 10’da açılır.', guide: 'Adım adım rehber', close: 'Anladım', reopen: 'Nasıl çalışır?', recommended: 'Önerilen', guestTip: 'İpucu: giriş yaparsan kesimden sonra her dosya için ayrıntılı Steam kontrolü gösteririz.', guestLogin: 'Giriş yap', demoName: 'Profilin', demoLevel: 'Seviye 10', demoShowcase: 'Vitrinin', start: 'Vitrinimi bul — 3 soru', back: 'Geri', stepOf: 'Soru {n} / 3', qLevel: 'Steam profil seviyen kaç?', aLevelOk: '10 veya üstü', aLevelLow: '10’un altında', aLevelUnknown: 'Bilmiyorum', levelHint: 'Steam profilinde adının yanındaki yuvarlak içindeki sayıdır.', lowTitle: 'Vitrinler 10. seviyede açılır', lowText: 'Steam vitrinleri profil seviyesi 10’dan itibaren verir. Seviyeni buradan hızlıca yükseltebilir, dosyaları şimdiden hazırlayabilirsin.', lowBoost: 'Steam seviyemi yükselt', lowPrepare: 'Dosyaları şimdi hazırla', qType: 'Hangi vitrini istiyorsun?', typeWs: 'Yan yana 5 resim', typeWsd: 'Workshop · en popüler', typeFt: 'Tek büyük resim', typeFtd: 'Featured', typeSp: 'Büyük resim + dar şerit', typeSpd: 'Artwork Split', typeUnknown: 'Henüz bilmiyorum', typeUnknownd: 'Workshop ile başlayalım', qFile: 'Elinde ne var?', fileHave: 'Resim, GIF veya video', fileHaved: 'Bu cihazda', fileLink: 'Bir bağlantı', fileLinkd: 'YouTube, Pinterest, Reddit ve 50+ site', fileNone: 'Henüz hiçbir şey', fileNoned: 'Bir örnekle göster' },
    fr: { kicker: 'Comment ça marche', title: 'Une vitrine est un bloc d’images sur votre profil Steam', lead: 'Steam l’affiche juste sous votre nom. Nous découpons votre image aux dimensions exactes de Steam, pour qu’elle se lise comme une seule image.', s1: 'Ajoutez une image, un GIF ou une vidéo', s1d: 'Ou essayez l’image d’exemple.', s2: 'Nous la découpons en parties', s2d: 'Bonnes tailles, moins de 5 Mo, prêtes pour Steam.', s3: 'Mettez les parties sur Steam', s3d: 'L’extension gratuite les envoie pour vous.', level: 'Les vitrines s’ouvrent au niveau 10 du profil Steam.', guide: 'Guide pas à pas', close: 'Compris', reopen: 'Comment ça marche ?', recommended: 'Recommandé', guestTip: 'Astuce : connectez-vous et, après le découpage, nous afficherons une vérification Steam détaillée de chaque fichier.', guestLogin: 'Se connecter', demoName: 'Votre profil', demoLevel: 'Niveau 10', demoShowcase: 'Votre vitrine', start: 'Trouver ma vitrine — 3 questions', back: 'Retour', stepOf: 'Question {n} sur 3', qLevel: 'Quel est le niveau de votre profil Steam ?', aLevelOk: '10 ou plus', aLevelLow: 'Moins de 10', aLevelUnknown: 'Je ne sais pas', levelHint: 'C’est le nombre dans un cercle à côté de votre nom sur votre profil Steam.', lowTitle: 'Les vitrines s’ouvrent au niveau 10', lowText: 'Steam débloque les vitrines au niveau 10 du profil. Vous pouvez monter de niveau rapidement ici, et préparer les fichiers dès maintenant.', lowBoost: 'Monter mon niveau Steam', lowPrepare: 'Préparer les fichiers maintenant', qType: 'Quelle vitrine voulez-vous ?', typeWs: '5 images en ligne', typeWsd: 'Workshop · la plus populaire', typeFt: 'Une grande image', typeFtd: 'Featured', typeSp: 'Grande image + bande étroite', typeSpd: 'Artwork Split', typeUnknown: 'Je ne sais pas encore', typeUnknownd: 'On commence par Workshop', qFile: 'Qu’avez-vous ?', fileHave: 'Une image, un GIF ou une vidéo', fileHaved: 'Sur cet appareil', fileLink: 'Un lien', fileLinkd: 'YouTube, Pinterest, Reddit et 50+ sites', fileNone: 'Rien pour l’instant', fileNoned: 'Montrez-moi avec un exemple' },
    uk: { kicker: 'Як це працює', title: 'Вітрина — це блок із картинками у твоєму профілі Steam', lead: 'Steam показує її одразу під ніком. Ми наріжемо твій арт на частини точно під Steam, і в профілі вони складуться в одну картинку.', s1: 'Додай картинку, GIF або відео', s1d: 'Або спробуй на прикладі.', s2: 'Ми наріжемо її на частини', s2d: 'Потрібний розмір, до 5 МБ, готово для Steam.', s3: 'Постав частини в Steam', s3d: 'Безкоштовне розширення завантажить їх за тебе.', level: 'Вітрини відкриваються з 10 рівня профілю Steam.', guide: 'Покрокова інструкція', close: 'Зрозуміло', reopen: 'Як це працює?', recommended: 'Радимо', guestTip: 'Порада: увійди — і після нарізки ми покажемо детальну перевірку кожного файлу для Steam.', guestLogin: 'Увійти', demoName: 'Твій профіль', demoLevel: 'Рівень 10', demoShowcase: 'Твоя вітрина', start: 'Підібрати вітрину — 3 питання', back: 'Назад', stepOf: 'Питання {n} з 3', qLevel: 'Який у тебе рівень профілю Steam?', aLevelOk: '10 і вище', aLevelLow: 'Нижче 10', aLevelUnknown: 'Не знаю', levelHint: 'Це число в кружечку поруч із ніком у твоєму профілі Steam.', lowTitle: 'Вітрини відкриваються з 10 рівня', lowText: 'Steam дає вітрини з 10 рівня профілю. Рівень можна швидко підняти тут, а файли підготувати вже зараз.', lowBoost: 'Підняти рівень Steam', lowPrepare: 'Підготувати файли зараз', qType: 'Яку вітрину хочеш?', typeWs: '5 картинок у ряд', typeWsd: 'Workshop · найпопулярніша', typeFt: 'Одна велика картинка', typeFtd: 'Featured', typeSp: 'Велика картинка + вузька смуга', typeSpd: 'Artwork Split', typeUnknown: 'Поки не знаю', typeUnknownd: 'Почнемо з Workshop', qFile: 'Що в тебе є?', fileHave: 'Картинка, GIF або відео', fileHaved: 'На цьому пристрої', fileLink: 'Посилання', fileLinkd: 'YouTube, Pinterest, Reddit і ще 50+ сайтів', fileNone: 'Поки нічого', fileNoned: 'Покажи на прикладі' },
    es: { kicker: 'Cómo funciona', title: 'Un escaparate es un bloque de imágenes en tu perfil de Steam', lead: 'Steam lo muestra justo debajo de tu nombre. Cortamos tu arte en las piezas exactas que necesita Steam, para que se vea como una sola imagen.', s1: 'Añade una imagen, GIF o vídeo', s1d: 'O prueba con la imagen de ejemplo.', s2: 'La cortamos en partes', s2d: 'Tamaños correctos, menos de 5 MB, listas para Steam.', s3: 'Pon las partes en Steam', s3d: 'La extensión gratuita las sube por ti.', level: 'Los escaparates se abren desde el nivel 10 del perfil de Steam.', guide: 'Guía paso a paso', close: 'Entendido', reopen: '¿Cómo funciona?', recommended: 'Recomendado', guestTip: 'Consejo: inicia sesión y, tras el corte, te mostraremos una comprobación de Steam detallada de cada archivo.', guestLogin: 'Iniciar sesión', demoName: 'Tu perfil', demoLevel: 'Nivel 10', demoShowcase: 'Tu escaparate', start: 'Encontrar mi escaparate — 3 preguntas', back: 'Atrás', stepOf: 'Pregunta {n} de 3', qLevel: '¿Qué nivel tiene tu perfil de Steam?', aLevelOk: '10 o más', aLevelLow: 'Menos de 10', aLevelUnknown: 'No lo sé', levelHint: 'Es el número en un círculo junto a tu nombre en tu perfil de Steam.', lowTitle: 'Los escaparates se abren en el nivel 10', lowText: 'Steam desbloquea los escaparates desde el nivel 10 del perfil. Puedes subir de nivel rápido aquí y preparar los archivos ya.', lowBoost: 'Subir mi nivel de Steam', lowPrepare: 'Preparar los archivos ahora', qType: '¿Qué escaparate quieres?', typeWs: '5 imágenes en fila', typeWsd: 'Workshop · el más popular', typeFt: 'Una imagen grande', typeFtd: 'Featured', typeSp: 'Imagen grande + franja estrecha', typeSpd: 'Artwork Split', typeUnknown: 'Aún no lo sé', typeUnknownd: 'Empezamos con Workshop', qFile: '¿Qué tienes?', fileHave: 'Una imagen, GIF o vídeo', fileHaved: 'En este dispositivo', fileLink: 'Un enlace', fileLinkd: 'YouTube, Pinterest, Reddit y 50+ sitios', fileNone: 'Nada todavía', fileNoned: 'Muéstrame con un ejemplo' },
    pt: { kicker: 'Como funciona', title: 'Uma vitrine é um bloco de imagens no seu perfil da Steam', lead: 'A Steam mostra a vitrine logo abaixo do seu nome. Cortamos sua arte nas peças exatas que a Steam pede, para ela aparecer como uma imagem só.', s1: 'Adicione uma imagem, GIF ou vídeo', s1d: 'Ou teste com a imagem de exemplo.', s2: 'Nós cortamos em partes', s2d: 'Tamanhos certos, menos de 5 MB, prontas para a Steam.', s3: 'Coloque as partes na Steam', s3d: 'A extensão gratuita envia para você.', level: 'As vitrines são liberadas a partir do nível 10 do perfil da Steam.', guide: 'Guia passo a passo', close: 'Entendi', reopen: 'Como funciona?', recommended: 'Recomendado', guestTip: 'Dica: entre na conta e, depois do corte, mostraremos uma verificação detalhada de cada arquivo para a Steam.', guestLogin: 'Entrar', demoName: 'Seu perfil', demoLevel: 'Nível 10', demoShowcase: 'Sua vitrine', start: 'Encontrar minha vitrine — 3 perguntas', back: 'Voltar', stepOf: 'Pergunta {n} de 3', qLevel: 'Qual é o nível do seu perfil da Steam?', aLevelOk: '10 ou mais', aLevelLow: 'Abaixo de 10', aLevelUnknown: 'Não sei', levelHint: 'É o número no círculo ao lado do seu nome no perfil da Steam.', lowTitle: 'As vitrines abrem no nível 10', lowText: 'A Steam libera vitrines a partir do nível 10 do perfil. Você pode subir de nível rápido aqui e já preparar os arquivos.', lowBoost: 'Subir meu nível na Steam', lowPrepare: 'Preparar os arquivos agora', qType: 'Qual vitrine você quer?', typeWs: '5 imagens em fila', typeWsd: 'Workshop · a mais popular', typeFt: 'Uma imagem grande', typeFtd: 'Featured', typeSp: 'Imagem grande + faixa estreita', typeSpd: 'Artwork Split', typeUnknown: 'Ainda não sei', typeUnknownd: 'Vamos começar com Workshop', qFile: 'O que você tem?', fileHave: 'Uma imagem, GIF ou vídeo', fileHaved: 'Neste dispositivo', fileLink: 'Um link', fileLinkd: 'YouTube, Pinterest, Reddit e 50+ sites', fileNone: 'Nada ainda', fileNoned: 'Mostre com um exemplo' }
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
    var actions = el('div', 'pon-intro__actions');
    var start = el('button', 'pon-intro__start', t('start')); start.type = 'button';
    start.addEventListener('click', function () { wizard(dialog, 'level'); focusFirst(dialog); });
    var ok = el('button', 'pon-intro__close', t('close')); ok.type = 'button';
    ok.addEventListener('click', hide);
    actions.append(start, ok);
    text.append(actions);
    var x = el('button', 'pon-modal__x', '×'); x.type = 'button'; x.setAttribute('aria-label', t('close'));
    x.addEventListener('click', hide);
    dialog.replaceChildren(x, demo, text);
    dialog.dataset.view = 'intro';
    return start;
  }
  // "Find my showcase" wizard (owner, 2026-10-08): level -> showcase type -> what you have. Below level 10 a
  // screen suggests raising the level (owner's partner link) or preparing the files anyway. The end picks the
  // showcase type on the page (the same mode buttons a visitor clicks) and opens the file picker, the link field or
  // the sample. Nothing is sent anywhere.
  var LEVEL_UP_URL = 'https://slvlup.com/r/uf9hte';
  var choice = { mode: 'workshop' };
  function option(label, hint, onClick, extraClass) {
    var b = el('button', 'pon-opt' + (extraClass ? ' ' + extraClass : '')); b.type = 'button';
    var body = el('span', 'pon-opt__body');
    body.append(el('b', null, label));
    if (hint) body.append(el('small', null, hint));
    b.append(body);
    b.addEventListener('click', onClick);
    return b;
  }
  function diagram(kind) {
    var d = el('span', 'pon-diagram pon-diagram--' + (kind || 'unknown')); d.setAttribute('aria-hidden', 'true');
    var n = kind === 'workshop' ? 5 : kind === 'split' ? 2 : kind === 'featured' ? 1 : 0;
    for (var i = 0; i < n; i += 1) d.append(el('i'));
    if (!n) d.textContent = '?';
    return d;
  }
  function focusFirst(dialog) {
    var first = dialog.querySelector('.pon-opt, .pon-wiz__cta');
    if (first) first.focus({ preventScroll: true });
  }
  function wizard(dialog, step) {
    dialog.dataset.view = 'wizard';
    dialog.dataset.step = step;
    var x = el('button', 'pon-modal__x', '×'); x.type = 'button'; x.setAttribute('aria-label', t('close'));
    x.addEventListener('click', hide);
    var box = el('div', 'pon-wiz');
    var number = { level: 1, low: 1, unknown: 1, type: 2, file: 3 }[step];
    var top = el('div', 'pon-wiz__top');
    var dots = el('span', 'pon-wiz__dots'); dots.setAttribute('aria-hidden', 'true');
    for (var i = 1; i <= 3; i += 1) dots.append(el('i', i <= number ? 'is-on' : ''));
    top.append(el('span', 'pon-wiz__step', t('stepOf').replace('{n}', number)), dots);
    box.append(top);
    var title = el('h2', 'pon-intro__title'); title.id = 'ponTitle';
    var list = el('div', 'pon-wiz__options');
    var go = function (to) { return function () { wizard(dialog, to); focusFirst(dialog); }; };
    var back = function (to) {
      var b = el('button', 'pon-wiz__back', '← ' + t('back')); b.type = 'button';
      b.addEventListener('click', function () {
        if (to === 'intro') { var first = introContent(dialog); first.focus({ preventScroll: true }); }
        else { wizard(dialog, to); focusFirst(dialog); }
      });
      return b;
    };
    if (step === 'level' || step === 'unknown') {
      title.textContent = t('qLevel');
      box.append(title);
      if (step === 'unknown') box.append(el('p', 'pon-wiz__hint', t('levelHint')));
      list.append(option(t('aLevelOk'), null, go('type')), option(t('aLevelLow'), null, go('low')));
      if (step === 'level') list.append(option(t('aLevelUnknown'), null, go('unknown'), 'is-quiet'));
      box.append(list, back(step === 'level' ? 'intro' : 'level'));
    } else if (step === 'low') {
      title.textContent = t('lowTitle');
      box.append(title, el('p', 'pon-wiz__hint', t('lowText')));
      var boost = el('a', 'pon-wiz__cta', t('lowBoost'));
      boost.href = LEVEL_UP_URL; boost.target = '_blank'; boost.rel = 'noopener sponsored';
      var later = el('button', 'pon-wiz__ghost', t('lowPrepare')); later.type = 'button';
      later.addEventListener('click', go('type'));
      var row = el('div', 'pon-wiz__row'); row.append(boost, later);
      box.append(row, back('level'));
    } else if (step === 'type') {
      title.textContent = t('qType');
      box.append(title);
      list.classList.add('is-types');
      [['workshop', 'typeWs', 'typeWsd'], ['featured', 'typeFt', 'typeFtd'], ['split', 'typeSp', 'typeSpd'], ['', 'typeUnknown', 'typeUnknownd']].forEach(function (row) {
        var b = option(t(row[1]), t(row[2]), function () { choice.mode = row[0] || 'workshop'; wizard(dialog, 'file'); focusFirst(dialog); }, row[0] ? '' : 'is-quiet');
        b.prepend(diagram(row[0]));
        list.append(b);
      });
      box.append(list, back('level'));
    } else {
      title.textContent = t('qFile');
      box.append(title);
      list.append(
        option(t('fileHave'), t('fileHaved'), function () { finish('file'); }),
        option(t('fileLink'), t('fileLinkd'), function () { finish('link'); }),
        option(t('fileNone'), t('fileNoned'), function () { finish('sample'); }, 'is-quiet'));
      box.append(list, back('type'));
    }
    dialog.replaceChildren(x, box);
  }
  function finish(what) {
    hide();
    var mode = root.querySelector('#processModeCard .mode[data-mode="' + choice.mode + '"]');
    if (mode && !mode.classList.contains('active')) mode.click();
    if (what === 'file') {
      var input = document.getElementById('fileInput');
      if (input) input.click();                       // still inside the click, so the browser allows the picker
    } else if (what === 'link') {
      var link = root.querySelector('.process-link input');
      if (link) { link.scrollIntoView({ block: 'center', behavior: 'smooth' }); setTimeout(function () { link.focus({ preventScroll: true }); }, 350); }
    } else {
      var sample = root.querySelector('.process-sample');
      if (sample) sample.click();
    }
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

  function paint() {
    paintModes(); paintHint(); sync();
    if (!modal) return;
    var d = modal.querySelector('.pon-modal__dialog');
    if (d.dataset.view === 'wizard') wizard(d, d.dataset.step || 'level'); else introContent(d);
  }
  paint();
  window.addEventListener('sm:langchange', function () { setTimeout(paint, 0); });
  window.SMProcessOnboarding = { show: show, hide: hide, reset: function () { setClosed(false); },
    wizard: function () { show(); if (modal) { var d = modal.querySelector('.pon-modal__dialog'); wizard(d, 'level'); focusFirst(d); } } };
})();
