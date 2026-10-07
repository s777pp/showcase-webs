/* Landing page: copy, header additions and small interactions.
   EN/RU are hand-written; the other six languages are translated from the
   English source by i18n.js (SM_EXTRA_TRANSLATIONS), falling back to English.
   Every English string below needs an entry in scripts/locale_reviewed.json. */
(function () {
  'use strict';

  var I18N = {
    en: {
      page_title: 'Showcase Maker — Steam showcases without the grind',
      hero_script_a: 'Your Profile',
      hero_script_b: 'Your Story',
      h1a: 'Steam showcases.',
      h1b: 'Revitalized',
      hero_p: 'Workshop, Featured and Split cuts, watermark, Steam size limits, source downloads and profile preview — one browser tool for creators.',
      cta_open: 'Open Showcase Maker',
      cta_gallery: 'View gallery',
      tg_offer_title: 'Get 2 hours of Pro free',
      tg_offer_text: 'Join the channel and claim your free key.',
      tg_offer_action: 'Get the key',
      feat_cut_t: 'Showcase cuts',
      feat_cut_s: '3 Steam formats',
      feat_up_t: 'AI Upscale',
      feat_up_s: 'Higher quality',
      feat_anim_t: 'Animations',
      feat_anim_s: 'GIF · MP4 · Loop',
      scroll: 'Scroll',
      footer_tagline: 'Steam showcase tools by n1t1337',
      footer_tools: 'Tools',
      footer_gallery: 'Gallery',
      footer_profile: 'Profile',
      footer_pricing: 'Pricing',
      footer_extension: 'Extension',

      // Blocks below the hero (rebuilt 2026-10-07)
      fact_types: 'showcase types: Workshop, Featured and Split',
      fact_size_v: '≤ 5 MB',
      fact_size: 'GIFs are fitted to the Steam limit',
      fact_hex: 'added automatically',
      fact_sites: 'sites to download a source from',

      demo_eyebrow: 'Showcase cuts',
      demo_h_a: 'One artwork.',
      demo_h_b: 'Three showcases',
      demo_p: 'Drop in a picture, GIF or video. Showcase Maker cuts it exactly to the Steam grid, keeps every part under 5 MB and adds HEX 21.',
      demo_m_workshop: '5 parts · a 630 px row',
      demo_m_featured: '1 file · 630 px wide',
      demo_m_split: '2 parts · 506 + 100 px',
      demo_badge: 'under 5 MB · HEX 21',
      demo_b1: 'Frames, effects and a watermark in the same step',
      demo_b2: 'A preview on a Steam profile mock-up',
      demo_b3: 'A ready ZIP: the parts are named in upload order',
      demo_cta: 'Try it on your file',

      steps_eyebrow: 'How it works',
      steps_h_a: 'From file to profile.',
      steps_h_b: 'Four steps',
      step1_t: 'Bring a file',
      step1_d: 'A picture, GIF or video. Or paste a link and download the source right here.',
      step2_t: 'Pick a showcase',
      step2_d: 'Workshop, Featured or Split. Add a frame and effects, then check the look on a profile mock-up.',
      step3_t: 'Download the ZIP',
      step3_d: 'Parts at the right size, under 5 MB and with HEX 21 already applied.',
      step4_t: 'Upload to Steam',
      step4_d: 'With the extension in a couple of clicks, or by hand with the step-by-step guide.',

      tools_eyebrow: 'Tools',
      tools_h_a: 'Everything for a profile.',
      tools_h_b: 'In one tab',
      tools_p: 'No installs and no hopping between five sites: from the source file to the upload, it is all here.',
      t_process: 'Process',
      t_process_d: 'Cut a file into a Workshop, Featured or Split showcase with frames and a watermark.',
      t_rows: 'Workshop Studio',
      t_rows_d: 'Full-height rows and rows of 150×150 squares, up to three rows.',
      t_builder: 'Create a design',
      t_builder_d: 'Layered editor: background, character, text, frames and effects.',
      t_char: 'Character',
      t_char_d: 'Put a character on a background and get one picture or animation.',
      t_download: 'Download',
      t_download_d: 'Pictures, GIFs and videos from 50+ sites by link.',
      t_convert: 'Converter',
      t_convert_d: 'Video ↔ GIF, MP4, WebM, PNG, JPG, WebP.',
      t_loop: 'Loop',
      t_loop_d: 'Turn a clip into a seamless loop.',
      t_ai: 'Profile AI',
      t_ai_d: 'Profile rating, design ideas and Steam DNA from your public profile.',
      t_upscale: 'Upscale',
      t_upscale_d: 'AI enlargement of pictures, GIFs and video.',
      t_gifopt: 'GIF Optimizer',
      t_gifopt_d: 'Shrink a GIF: fewer colours, lossy compression or auto-fit under 5 MB.',
      t_preview: 'Profile preview',
      t_preview_d: 'Try showcases on a Steam profile mock-up.',
      t_steam: 'Steam upload',
      t_steam_d: 'Upload to Steam with the extension or by hand.',
      tag_week: 'Free: once a week',
      tag_beta: 'Pro · beta',
      tools_all: 'Open all tools',

      ext_eyebrow: 'Browser extension',
      ext_h_a: 'Into Steam.',
      ext_h_b: 'In a few clicks',
      ext_p: 'SteamShowcase Helper uploads your finished files to Steam, places them into the showcase in the right order and keeps whole profile looks as presets.',
      ext_b1: 'Automatic upload: pick the showcase type and drop the files in',
      ext_b2: 'No console and no code to paste',
      ext_b3: 'Never asks for a password: it works in your own Steam session',
      ext_install: 'Install for free',
      ext_more: 'See what it does',
      ext_browsers: 'Chrome, Edge, Opera, Yandex Browser',

      price_eyebrow: 'Pricing',
      price_h_a: 'No subscriptions.',
      price_h_b: 'Pay once',
      price_p: 'Free is enough for a showcase now and then. Pro lifts the limits for a day, a month or for good: one payment, no auto-renewal.',
      price_free: 'Free plan',
      price_free_d: 'Enough to build a showcase and see how everything works.',
      price_files: '5 files a day',
      price_builder: '3 exports a day from Create a design',
      price_weekly: 'AI tools and Loop: once a week',
      price_mark: 'Showcase Maker watermark on the result',
      price_from: 'from',
      price_pro_d: 'Pick a term. Days add up, and Pro turns on by itself after payment.',
      price_unlimited: 'No daily limit on files and exports',
      price_nomark: 'No watermark, or your own',
      price_tools: 'AI Upscale and the standalone Steam check',
      price_noweek: 'AI tools and Loop with no weekly limit',
      price_beta: 'New and beta tools first',
      term_1d: '24 hours',
      term_7d: '7 days',
      term_30d: '30 days',
      term_90d: '90 days',
      buy_plan: 'Choose a plan',
      price_best: 'Best value',
      price_forever: 'Pro forever',
      price_forever_d: 'One payment, and Pro stays on your account for good.',
      price_all: 'Everything in Pro',
      price_once: 'Pay once, no renewals',
      price_future: 'Every future Pro tool',
      price_account: 'Bound to your account',
      buy_forever: 'Get Pro forever',
      start_free: 'Start free',
      trial_t: 'Not sure yet? Try Pro for 2 hours',
      trial_d: 'A free key is waiting in our Telegram channel.',
      price_compare: 'Full Free and Pro comparison',

      faq_eyebrow: 'Questions',
      faq_h_a: 'Common questions.',
      faq_h_b: 'Short answers',
      faq_p: 'Did not find yours? Ask the assistant or write to support.',
      faq_support: 'Support',
      q1: 'Do I need to install anything?',
      a1: 'No, everything runs in the browser. The SteamShowcase Helper extension only speeds up uploading to Steam.',
      q2: 'Why does Steam reject my GIF?',
      a2: 'Steam accepts files up to 5 MB and needs the HEX 21 byte. Showcase Maker does both; for files made elsewhere use the HEX tab.',
      q3: 'Do you need my Steam password?',
      a3: 'No. The site never asks for it. The extension works inside your own Steam session in the browser: you sign in to Steam yourself, as usual.',
      q4: 'Are my files public?',
      a4: 'No. Sources and ZIPs are deleted automatically after their storage time; a preview becomes public only if you share its link yourself.',
      q5: 'How does paying for Pro work?',
      a5: 'You pay once for a term, with no auto-renewal. Days add up with the Pro you already have. Pro is bound to your account and turns on by itself after payment.',
      q6: 'Is this made by Valve?',
      a6: 'No. It is an independent project; Steam and Valve are trademarks of Valve Corporation.',

      cta_h_a: 'Your showcase is ready',
      cta_h_b: 'The rest is up to you',
      cta_p: 'Start without an account: 5 files a day are free.',
      cta_open2: 'Open tools',
      cta_reg: 'Create account'
    },
    ru: {
      page_title: 'Showcase Maker — витрины Steam без рутины',
      hero_script_a: 'Твой профиль',
      hero_script_b: 'твоя история',
      h1a: 'Steam-витрины.',
      h1b: 'Без рутины',
      hero_p: 'Нарезка Workshop, Featured и Split, водяной знак, лимиты Steam, скачивание исходников и предпросмотр профиля — один инструмент в браузере.',
      cta_open: 'Открыть Showcase Maker',
      cta_gallery: 'Открыть галерею',
      tg_offer_title: 'Получи 2 часа Pro бесплатно',
      tg_offer_text: 'Подпишись на канал и забери бесплатный ключ.',
      tg_offer_action: 'Забрать ключ',
      feat_cut_t: 'Нарезка витрин',
      feat_cut_s: '3 формата Steam',
      feat_up_t: 'ИИ-апскейл',
      feat_up_s: 'Выше качество',
      feat_anim_t: 'Анимации',
      feat_anim_s: 'GIF · MP4 · Loop',
      scroll: 'Вниз',
      footer_tagline: 'Инструменты для Steam-витрин от n1t1337',
      footer_tools: 'Инструменты',
      footer_gallery: 'Галерея',
      footer_profile: 'Профиль',
      footer_pricing: 'Цены',
      footer_extension: 'Расширение',

      // Blocks below the hero (rebuilt 2026-10-07)
      fact_types: 'типа витрин: Workshop, Featured и Split',
      fact_size_v: '≤ 5 МБ',
      fact_size: 'GIF сами подгоняются под лимит Steam',
      fact_hex: 'ставится автоматически',
      fact_sites: 'сайтов, откуда можно скачать исходник',

      demo_eyebrow: 'Нарезка витрин',
      demo_h_a: 'Один арт.',
      demo_h_b: 'Три витрины',
      demo_p: 'Загрузи картинку, GIF или видео. Showcase Maker разрежет файл точно по сетке Steam, уложит каждую часть в 5 МБ и поставит HEX 21.',
      demo_m_workshop: '5 частей · ряд 630 px',
      demo_m_featured: '1 файл · ширина 630 px',
      demo_m_split: '2 части · 506 + 100 px',
      demo_badge: 'до 5 МБ · HEX 21',
      demo_b1: 'Рамки, эффекты и водяной знак — в том же шаге',
      demo_b2: 'Предпросмотр на макете профиля Steam',
      demo_b3: 'Готовый ZIP: части подписаны по порядку загрузки',
      demo_cta: 'Попробовать на своём файле',

      steps_eyebrow: 'Как это работает',
      steps_h_a: 'От файла до профиля.',
      steps_h_b: 'Четыре шага',
      step1_t: 'Возьми файл',
      step1_d: 'Картинка, GIF или видео. Или вставь ссылку и скачай исходник прямо здесь.',
      step2_t: 'Выбери витрину',
      step2_d: 'Workshop, Featured или Split. Добавь рамку и эффекты, проверь вид на макете профиля.',
      step3_t: 'Скачай ZIP',
      step3_d: 'Части нужного размера, до 5 МБ и уже с HEX 21.',
      step4_t: 'Загрузи в Steam',
      step4_d: 'Через расширение в пару кликов или вручную по пошаговой инструкции.',

      tools_eyebrow: 'Инструменты',
      tools_h_a: 'Всё для профиля.',
      tools_h_b: 'В одной вкладке',
      tools_p: 'Без установки и без прыжков по пяти сайтам: от исходника до загрузки — всё здесь.',
      t_process: 'Обработка',
      t_process_d: 'Нарезка файла под Workshop, Featured или Split — с рамками и водяным знаком.',
      t_rows: 'Ряды и квадраты',
      t_rows_d: 'Ряды во всю высоту и ряды квадратов 150×150, до трёх рядов.',
      t_builder: 'Создать дизайн',
      t_builder_d: 'Редактор слоёв: фон, персонаж, текст, рамки и эффекты.',
      t_char: 'Персонаж',
      t_char_d: 'Персонаж на фоне — одна картинка или анимация.',
      t_download: 'Скачать',
      t_download_d: 'Картинки, GIF и видео с 50+ сайтов по ссылке.',
      t_convert: 'Конвертер',
      t_convert_d: 'Видео ↔ GIF, MP4, WebM, PNG, JPG, WebP.',
      t_loop: 'Зациклить',
      t_loop_d: 'Бесшовный цикл из короткого ролика.',
      t_ai: 'ИИ для профиля',
      t_ai_d: 'Оценка профиля, идеи оформления и Steam DNA по твоему публичному профилю.',
      t_upscale: 'Апскейл',
      t_upscale_d: 'ИИ-увеличение картинок, GIF и видео.',
      t_gifopt: 'GIF оптимизатор',
      t_gifopt_d: 'Сжать GIF: меньше цветов, сжатие с потерями или автоподгонка до 5 МБ.',
      t_preview: 'Предпросмотр профиля',
      t_preview_d: 'Примерить витрины на макете профиля Steam.',
      t_steam: 'Загрузка в Steam',
      t_steam_d: 'Загрузка в Steam через расширение или вручную.',
      tag_week: 'Бесплатно: раз в неделю',
      tag_beta: 'Pro · бета',
      tools_all: 'Открыть все инструменты',

      ext_eyebrow: 'Расширение для браузера',
      ext_h_a: 'В Steam.',
      ext_h_b: 'За пару кликов',
      ext_p: 'SteamShowcase Helper загружает готовые файлы в Steam, расставляет их по витрине в нужном порядке и хранит оформление профиля в пресетах.',
      ext_b1: 'Автозагрузка: выбери тип витрины и перетащи файлы',
      ext_b2: 'Без консоли и вставки кода',
      ext_b3: 'Не спрашивает пароль: работает в твоей сессии Steam',
      ext_install: 'Установить бесплатно',
      ext_more: 'Что умеет расширение',
      ext_browsers: 'Chrome, Edge, Opera, Яндекс Браузер',

      price_eyebrow: 'Тарифы',
      price_h_a: 'Без подписок.',
      price_h_b: 'Плати один раз',
      price_p: 'Бесплатного хватит на витрину время от времени. Pro снимает лимиты на день, на месяц или навсегда: разовая оплата без автопродления.',
      price_free: 'Бесплатно',
      price_free_d: 'Хватит, чтобы собрать витрину и понять, как всё устроено.',
      price_files: '5 файлов в день',
      price_builder: '3 экспорта в день из «Создать дизайн»',
      price_weekly: 'ИИ-инструменты и Зациклить — раз в неделю',
      price_mark: 'Водяной знак Showcase Maker на результате',
      price_from: 'от',
      price_pro_d: 'Выбери срок. Дни складываются, а Pro включается сам после оплаты.',
      price_unlimited: 'Без дневного лимита файлов и экспортов',
      price_nomark: 'Без водяного знака или со своим',
      price_tools: 'ИИ-апскейл и отдельная проверка Steam',
      price_noweek: 'ИИ-инструменты и Зациклить без недельного лимита',
      price_beta: 'Новые и бета-инструменты — сразу',
      term_1d: '24 часа',
      term_7d: '7 дней',
      term_30d: '30 дней',
      term_90d: '90 дней',
      buy_plan: 'Выбрать тариф',
      price_best: 'Выгоднее всего',
      price_forever: 'Pro навсегда',
      price_forever_d: 'Одна оплата — и Pro остаётся на аккаунте навсегда.',
      price_all: 'Всё, что есть в Pro',
      price_once: 'Платишь один раз, без продлений',
      price_future: 'Все будущие инструменты Pro',
      price_account: 'Привязан к твоему аккаунту',
      buy_forever: 'Взять Pro навсегда',
      start_free: 'Начать бесплатно',
      trial_t: 'Сомневаешься? Попробуй Pro на 2 часа',
      trial_d: 'Бесплатный ключ ждёт в нашем Telegram-канале.',
      price_compare: 'Полное сравнение Бесплатно и Pro',

      faq_eyebrow: 'Вопросы',
      faq_h_a: 'Частые вопросы.',
      faq_h_b: 'Короткие ответы',
      faq_p: 'Не нашёл свой? Спроси помощника или напиши в поддержку.',
      faq_support: 'Техподдержка',
      q1: 'Нужно ли что-то устанавливать?',
      a1: 'Нет, всё работает в браузере. Расширение SteamShowcase Helper только ускоряет загрузку в Steam.',
      q2: 'Почему Steam не принимает GIF?',
      a2: 'Steam принимает файлы до 5 МБ и требует служебный байт HEX 21. Сервис делает и то и другое сам; для файлов из других мест есть вкладка HEX.',
      q3: 'Нужен ли вам мой пароль от Steam?',
      a3: 'Нет. Сайт его не спрашивает. Расширение работает в твоей сессии Steam в браузере: в Steam ты входишь сам, как обычно.',
      q4: 'Мои файлы кто-то видит?',
      a4: 'Нет. Исходники и ZIP удаляются автоматически по сроку хранения; превью становится публичным, только если ты сам поделишься ссылкой.',
      q5: 'Как устроена оплата Pro?',
      a5: 'Ты платишь один раз за срок, без автопродления. Дни складываются с уже действующим Pro. Pro привязан к аккаунту и включается сам после оплаты.',
      q6: 'Это сервис от Valve?',
      a6: 'Нет. Это независимый проект; Steam и Valve — товарные знаки Valve Corporation.',

      cta_h_a: 'Витрина готова',
      cta_h_b: 'Дело за тобой',
      cta_p: 'Начни без аккаунта: 5 файлов в день бесплатно.',
      cta_open2: 'Открыть инструменты',
      cta_reg: 'Создать аккаунт'
    }
  };

  var reducedMotion = !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);

  function lang() {
    return window.SMLang ? SMLang.get() : 'en';
  }

  function pack() {
    return I18N[lang()] || I18N.en;
  }

  function applyCopy() {
    if (window.SMLang) SMLang.apply(I18N);
    document.title = pack().page_title;
  }

  /* Pricing cards show the prices the store really charges (Gumroad, read by the server). */
  function paintPrices() {
    fetch('/api/billing/plans', { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        (data && data.plans || []).forEach(function (plan) {
          if (!plan.price) return;
          document.querySelectorAll('[data-plan-price="' + plan.id + '"]').forEach(function (node) { node.textContent = plan.price; });
        });
      })
      .catch(function () {});
  }

  /* Purchase buttons open the shell's activation dialog (it lists the shops);
     "Create account" opens the shared registration and is hidden once signed in. */
  function wireBlocks() {
    document.querySelectorAll('[data-buy-key]').forEach(function (button) {
      button.addEventListener('click', function (event) {
        event.preventDefault();
        // data-buy-plan jumps straight to the payment step of that plan.
        if (window.SSShell && SSShell.openActivation) SSShell.openActivation(button.dataset.buyPlan ? { plan: button.dataset.buyPlan } : {});
      });
    });
    var register = document.getElementById('ctaReg');
    if (register) {
      register.addEventListener('click', function (event) {
        event.preventDefault();
        if (window.SSShell && SSShell.openAuth) SSShell.openAuth('register');
      });
      var hideWhenSignedIn = function (me) { if (me && me.logged_in) register.hidden = true; };
      hideWhenSignedIn(window.SS_ME);
      document.addEventListener('ss:me', function (event) { hideWhenSignedIn(event.detail); });
    }
    // Extension screenshots exist in Russian and English.
    var suffix = lang() === 'ru' ? '-ru' : '-en';
    document.querySelectorAll('.home-blocks img[data-shot]').forEach(function (img) {
      var src = '/static/img/extension-guide/v2/' + img.dataset.shot + suffix + '.webp';
      if (img.getAttribute('src') !== src) img.setAttribute('src', src);
    });
  }

  /* "One artwork, three showcases": the tabs move the cut lines over the same picture.
     Until the visitor picks a tab, the types rotate by themselves while the stage is on screen. */
  function wireCutDemo() {
    var stage = document.getElementById('cutStage');
    var tabs = Array.prototype.slice.call(document.querySelectorAll('.home-blocks .hb-seg [data-cut]'));
    if (!stage || !tabs.length) return;
    var order = tabs.map(function (tab) { return tab.dataset.cut; });
    var timer = 0, auto = !reducedMotion;
    function show(kind) {
      stage.dataset.cut = kind;
      tabs.forEach(function (tab) {
        var on = tab.dataset.cut === kind;
        tab.classList.toggle('is-on', on);
        tab.setAttribute('aria-selected', on ? 'true' : 'false');
        tab.tabIndex = on ? 0 : -1;
      });
    }
    function stop() { auto = false; clearInterval(timer); timer = 0; }
    tabs.forEach(function (tab, index) {
      tab.addEventListener('click', function () { stop(); show(tab.dataset.cut); });
      tab.addEventListener('keydown', function (event) {
        if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return;
        event.preventDefault();
        var next = tabs[(index + (event.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
        stop(); show(next.dataset.cut); next.focus();
      });
    });
    show(stage.dataset.cut || order[0]);
    // The desktop scroll scene (home-scroll.js) drives the tabs by scroll position instead of the timer.
    window.__homeCut = { show: show, stop: stop, order: order };
    if (!auto || !('IntersectionObserver' in window)) return;
    new IntersectionObserver(function (entries) {
      clearInterval(timer); timer = 0;
      if (!auto || !entries[0].isIntersecting) return;
      timer = setInterval(function () {
        if (!document.hidden) show(order[(order.indexOf(stage.dataset.cut) + 1) % order.length]);
      }, 3600);
    }, { threshold: 0.45 }).observe(stage);
  }

  /* Appearance on scroll: panels rise and fade in once with a small stagger,
     headings and lists follow. The mark is removed afterwards so hover
     transitions of the cards work as written in the stylesheet. */
  function initReveal() {
    var root = document.querySelector('.home-blocks');
    // The desktop scroll scene (home-scroll.js) animates the blocks itself.
    if (!root || document.documentElement.classList.contains('hs-own-reveal')) return;
    var items = [];
    function mark(selector, kind) {
      root.querySelectorAll(selector).forEach(function (el) {
        if (el.hasAttribute('data-hb-reveal')) return;
        var slot = el.closest('li') || el;
        var index = Array.prototype.indexOf.call(slot.parentNode.children, slot);
        el.setAttribute('data-hb-reveal', kind);
        el.style.setProperty('--hb-delay', (index % 4) * 80 + 'ms');
        items.push(el);
      });
    }
    mark('.hb-facts__list, .hb-stage, .hb-step, .hb-tool, .hb-ext, .hb-plan, .hb-trial, .hb-q, .hb-final__card', 'block');
    mark('.hb-eyebrow, .hb-title, .hb-lead, .hb-seg, .hb-ticks, .hb-demo .hb-btn', 'text');
    function done(el) {
      el.classList.add('is-in');
      setTimeout(function () { el.removeAttribute('data-hb-reveal'); el.classList.remove('is-in'); el.style.removeProperty('--hb-delay'); }, 1600);
    }
    if (reducedMotion || !('IntersectionObserver' in window)) {
      items.forEach(function (el) { el.removeAttribute('data-hb-reveal'); });
      return;
    }
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        done(entry.target);
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -6% 0px' });
    items.forEach(function (el) { observer.observe(el); });
  }

  function boot() {
    applyCopy();
    wireBlocks();
    wireCutDemo();
    paintPrices();
    initReveal();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  window.SMHomeI18N = I18N;
})();
