/* Landing page: copy, header additions and small interactions.
   EN/RU are hand-written; the other six languages are translated from the
   English source by i18n.js (SM_EXTRA_TRANSLATIONS), falling back to English. */
(function () {
  'use strict';

  var I18N = {
    en: {
      page_title: 'Showcase Maker — Steam showcases without the grind',
      hero_script_a: 'Your Art',
      hero_script_b: 'Bigger Stories',
      h1a: 'Steam showcases.',
      h1b: 'Revitalized',
      hero_p: 'Workshop, Featured and Split cuts, watermark, Steam size limits, source downloads and profile preview — one browser tool for creators.',
      cta_open: 'Open Showcase Maker',
      cta_gallery: 'View gallery',
      tg_offer_title: 'Get 7 days of Pro free',
      tg_offer_text: 'Join the channel and claim your free key.',
      tg_offer_action: 'Get the key',
      feat_cut_t: 'Showcase cuts',
      feat_cut_s: '3 Steam formats',
      feat_up_t: 'AI Upscale',
      feat_up_s: 'Higher quality',
      feat_anim_t: 'Animations',
      feat_anim_s: 'GIF · MP4 · Loop',
      feat_steam_t: 'Steam Ready',
      feat_steam_s: 'Up to 5 MB · HEX 21',
      scroll: 'Scroll',
      footer_tagline: 'Steam showcase tools by n1t1337',
      footer_tools: 'Tools',
      footer_gallery: 'Gallery',
      footer_profile: 'Profile',
      // Blocks below the hero (restored from the previous landing)
      aud_artists: "Profile artists",
      aud_creators: "CREATORS",
      aud_power: "Power users",
      aud_sellers: "Commission sellers",
      aud_sellers_badge: "SELLERS",
      badge_instant: "instant",
      badge_live: "live",
      badge_local: "local",
      badge_safe: "safe",
      buy_fp: "Buy on FunPay",
      cta_h: "Close the tabs.<br/>Open your profile.",
      cta_open2: "Open tools",
      cta_p: "Process, download sources, preview on a Steam template, and ship — without leaving the browser.",
      cta_reg: "Create account →",
      desktop_web: "Desktop + Web",
      ext_eyebrow: "Browser extension",
      ext_hint: "Download the ZIP, unpack it and select “Load unpacked” on the browser extensions page.",
      ext_install: "Install extension",
      ext_list_engine_prev: "Files stay on your computer",
      ext_list_engine_sub: "PNG · JPG · WEBP · GIF",
      ext_list_modes: "Showcase modes",
      ext_list_modes_prev: "Ready-made Steam dimensions and layouts",
      ext_list_privacy: "Private by design",
      ext_list_privacy_prev: "Only the permissions required for Steam",
      ext_list_privacy_sub: "No passwords · no cookies",
      ext_list_profile: "Profile preview",
      ext_list_profile_prev: "Try the look before applying it",
      ext_list_profile_sub: "Backgrounds · frames · avatars",
      ext_list_steam: "Steam integration",
      ext_list_steam_prev: "Edit showcases without switching tabs",
      ext_list_steam_sub: "Tools inside Steam pages",
      ext_nav_browser: "Browser Engine",
      ext_nav_overview: "Overview",
      ext_nav_preview: "Profile preview",
      ext_nav_privacy: "Privacy",
      ext_nav_steam: "Steam tools",
      ext_reader_body: "Open a supported Steam page and the required tool appears automatically. Your media is processed locally whenever possible.",
      ext_reader_meta: "extension · v0.9.9",
      ext_reader_summary: "✦ Everything close at hand",
      ext_reader_summary_p: "Showcase preparation, local media processing and live Steam profile preview in one lightweight browser extension.",
      ext_reader_title: "SteamShowcase Helper",
      ext_supports: "Supports",
      flow_load: "3 · LOAD",
      flow_unpack: "2 · UNPACK",
      format_preview: "Preview",
      format_watermark: "Watermark",
      get_desk: "Get desktop",
      mock_title: "SteamShowcase Helper — Extension",
      pipe_animated: "Animated GIF / MP4",
      pipe_console: "Console code",
      pipe_core: "core",
      pipe_download: "Download",
      pipe_guide: "Step-by-step guide",
      pipe_preview: "Preview",
      pipe_process: "Process",
      pipe_profile: "profile",
      pipe_slots: "Template slots",
      pipe_sources: "sources",
      pipe_upload: "upload",
      pipe_watermark: "Watermark · font · opacity",
      price_account: "Account-bound access code",
      price_desk_d: "Full desktop app with offline processing and DeviantArt helpers.",
      price_desktop: "Desktop",
      price_ffmpeg: "Local FFmpeg power",
      price_files: "5 files / day",
      price_free: "Free",
      price_free_d: "Try the full pipeline with a daily file limit.",
      price_license: "License key system",
      price_modes: "All modes + HEX 21",
      price_priority: "Priority-ready pipeline",
      price_pro_d: "Unlimited processing for sellers and daily shippers.",
      price_same: "Same core pipeline",
      price_source: "Source download",
      price_unlimited: "Unlimited files",
      price_update: "Auto-update ready",
      price_watermark: "Watermark & preview",
      q1: "“Cuts Workshop into five parts with hex 21 in seconds. I stopped doing this by hand.”",
      q2: "“Download + process + preview in one tab. No more juggling five sites.”",
      q3: "“Pro is worth it when you ship showcases every week — no daily limit stress.”",
      start_free: "Start free",
      steam_native: "Steam-native",
      tri_h: "Clear the busywork.<br/>Ship the showcase.",
      tri_label: "Process",
      tri_p: "Showcase Maker cuts Workshop, Featured and Split, applies watermark, respects Steam limits, and packages a ZIP — so you stay on the art, not the crop math.",
      tri_today: "Today · showcase pipeline",
      trust: "Built for Steam profile creators",
      footer_pricing: "Pricing",
      footer_extension: "Extension"
    },
    ru: {
      page_title: 'Showcase Maker — витрины Steam без рутины',
      hero_script_a: 'Твой арт —',
      hero_script_b: 'большие истории',
      h1a: 'Steam-витрины.',
      h1b: 'Без рутины',
      hero_p: 'Нарезка Workshop, Featured и Split, водяной знак, лимиты Steam, скачивание исходников и предпросмотр профиля — один инструмент в браузере.',
      cta_open: 'Открыть Showcase Maker',
      cta_gallery: 'Открыть галерею',
      tg_offer_title: 'Получи 7 дней Pro бесплатно',
      tg_offer_text: 'Подпишись на канал и забери бесплатный ключ.',
      tg_offer_action: 'Забрать ключ',
      feat_cut_t: 'Нарезка витрин',
      feat_cut_s: '3 формата Steam',
      feat_up_t: 'ИИ-апскейл',
      feat_up_s: 'Выше качество',
      feat_anim_t: 'Анимации',
      feat_anim_s: 'GIF · MP4 · Loop',
      feat_steam_t: 'Готово для Steam',
      feat_steam_s: 'До 5 МБ · HEX 21',
      scroll: 'Вниз',
      footer_tagline: 'Инструменты для Steam-витрин от n1t1337',
      footer_tools: 'Инструменты',
      footer_gallery: 'Галерея',
      footer_profile: 'Профиль',
      // Blocks below the hero (restored from the previous landing)
      aud_artists: "Оформители профилей",
      aud_creators: "АВТОРЫ",
      aud_power: "Опытные пользователи",
      aud_sellers: "Продавцы оформления",
      aud_sellers_badge: "ПРОДАВЦЫ",
      badge_instant: "сразу",
      badge_live: "активно",
      badge_local: "локально",
      badge_safe: "безопасно",
      buy_fp: "Купить на FunPay",
      cta_h: "Закрой лишние вкладки.<br/>Открой профиль.",
      cta_open2: "Открыть инструменты",
      cta_p: "Обработка, исходники, превью на шаблоне Steam — без ухода из браузера.",
      cta_reg: "Создать аккаунт →",
      desktop_web: "Приложение + сайт",
      ext_eyebrow: "Расширение для браузера",
      ext_hint: "Скачай ZIP, распакуй его и выбери «Загрузить распакованное расширение» на странице расширений браузера.",
      ext_install: "Установить расширение",
      ext_list_engine_prev: "Файлы остаются на твоём компьютере",
      ext_list_engine_sub: "PNG · JPG · WEBP · GIF",
      ext_list_modes: "Режимы витрин",
      ext_list_modes_prev: "Готовые размеры и раскладки Steam",
      ext_list_privacy: "Приватность по умолчанию",
      ext_list_privacy_prev: "Только необходимые разрешения для Steam",
      ext_list_privacy_sub: "Без паролей · без файлов cookie",
      ext_list_profile: "Предпросмотр профиля",
      ext_list_profile_prev: "Примерь оформление перед применением",
      ext_list_profile_sub: "Фоны · рамки · аватары",
      ext_list_steam: "Интеграция со Steam",
      ext_list_steam_prev: "Настраивай витрины без переключения вкладок",
      ext_list_steam_sub: "Инструменты внутри страниц Steam",
      ext_nav_browser: "Браузерный движок",
      ext_nav_overview: "Обзор",
      ext_nav_preview: "Предпросмотр профиля",
      ext_nav_privacy: "Приватность",
      ext_nav_steam: "Инструменты Steam",
      ext_reader_body: "Открой поддерживаемую страницу Steam — нужный инструмент появится автоматически. Медиа по возможности обрабатываются локально.",
      ext_reader_meta: "расширение · v0.9.9",
      ext_reader_summary: "✦ Всё необходимое под рукой",
      ext_reader_summary_p: "Подготовка витрин, локальная обработка медиа и живой предпросмотр профиля Steam в одном лёгком расширении.",
      ext_reader_title: "SteamShowcase Helper",
      ext_supports: "Поддерживается",
      flow_load: "3 · ЗАГРУЗИТЬ",
      flow_unpack: "2 · РАСПАКОВАТЬ",
      format_preview: "Предпросмотр",
      format_watermark: "Водяной знак",
      get_desk: "Взять десктоп",
      mock_title: "SteamShowcase Helper — Расширение",
      pipe_animated: "Анимация GIF / MP4",
      pipe_console: "Код для консоли",
      pipe_core: "основа",
      pipe_download: "Скачивание",
      pipe_guide: "Пошаговая инструкция",
      pipe_preview: "Предпросмотр",
      pipe_process: "Обработка",
      pipe_profile: "профиль",
      pipe_slots: "Слоты шаблона",
      pipe_sources: "исходники",
      pipe_upload: "загрузка",
      pipe_watermark: "Водяной знак · шрифт · прозрачность",
      price_account: "Код доступа привязан к аккаунту",
      price_desk_d: "Десктоп-приложение: офлайн-обработка и помощники DeviantArt.",
      price_desktop: "Приложение",
      price_ffmpeg: "Локальная мощность FFmpeg",
      price_files: "5 файлов в сутки",
      price_free: "Бесплатно",
      price_free_d: "Полный пайплайн с дневным лимитом файлов.",
      price_license: "Система лицензионных ключей",
      price_modes: "Все режимы + HEX 21",
      price_priority: "Приоритетная обработка",
      price_pro_d: "Безлимитная обработка для продавцов и ежедневной отгрузки.",
      price_same: "Тот же основной конвейер",
      price_source: "Скачивание исходников",
      price_unlimited: "Безлимитные файлы",
      price_update: "Автоматические обновления",
      price_watermark: "Водяной знак и предпросмотр",
      q1: "«Режет Workshop на пять частей с hex 21 за секунды. Больше не делаю это руками.»",
      q2: "«Скачать + обработать + превью в одной вкладке. Не прыгаю по пяти сайтам.»",
      q3: "«Pro окупается, если витрины каждую неделю — без дневного лимита.»",
      start_free: "Начать бесплатно",
      steam_native: "Для Steam",
      tri_h: "Убери рутину.<br/>Отгрузи витрину.",
      tri_label: "Обработка",
      tri_p: "Showcase Maker режет Workshop, Featured и Split, ставит водяной знак, укладывается в лимиты Steam и собирает ZIP — ты занимаешься артом, а не пиксельной математикой.",
      tri_today: "Сегодня · конвейер витрин",
      trust: "Для авторов Steam-профилей",
      footer_pricing: "Цены",
      footer_extension: "Расширение"
    }
  };

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

  /* Blocks below the hero: purchase buttons open the shell's activation dialog
     (it lists the shops), "Create account" opens the shared registration. */
  function wireBlocks() {
    document.querySelectorAll('[data-buy-key]').forEach(function (button) {
      button.addEventListener('click', function (event) {
        event.preventDefault();
        if (window.SSShell && SSShell.openActivation) SSShell.openActivation();
      });
    });
    var register = document.getElementById('ctaReg');
    if (register) register.addEventListener('click', function (event) {
      event.preventDefault();
      if (window.SSShell && SSShell.openAuth) SSShell.openAuth('register');
    });
    // Seamless marquee: the list is duplicated once, CSS moves the track by 50%.
    var track = document.getElementById('formatsTrack');
    var list = document.getElementById('formatsSeq');
    if (track && list && track.children.length === 1) {
      var copy = list.cloneNode(true);
      copy.removeAttribute('id');
      copy.setAttribute('aria-hidden', 'true');
      track.appendChild(copy);
    }
  }

  /* Appearance on scroll (as on the live landing): cards rise and fade in with
     a small stagger, section headings reveal line by line. Runs once per item. */
  function initReveal() {
    var root = document.querySelector('.home-blocks');
    if (!root) return;
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var items = [];
    function mark(selector, kind) {
      root.querySelectorAll(selector).forEach(function (el) {
        if (el.hasAttribute('data-hb-reveal')) return;
        var index = Array.prototype.indexOf.call(el.parentNode.children, el);
        el.setAttribute('data-hb-reveal', kind);
        el.style.setProperty('--hb-delay', Math.min(index, 6) * 90 + 'ms');
        items.push(el);
      });
    }
    // Headings keep their <br/> structure; each line slides up from a mask.
    root.querySelectorAll('.hb-process h2, .hb-final-card h2').forEach(function (heading) {
      if (heading.querySelector('.hb-reveal-line')) return;
      var lines = heading.innerHTML.split(/<br\s*\/?>/i);
      heading.innerHTML = lines.map(function (line, index) {
        return '<span class="hb-reveal-line" style="--hb-line:' + index + '"><span>' + line + '</span></span>';
      }).join('');
      items.push(heading);
    });
    mark('.hb-mock-frame, .hb-subc, .hb-logos, .hb-q-card, .hb-c3-card, .hb-final-card', 'block');
    mark('.hb-eyebrow, .hb-lead, .hb-chips, .hb-c3-watermark-main', 'text');
    if (reduce || !('IntersectionObserver' in window)) {
      items.forEach(function (el) { el.classList.add('is-in'); });
      return;
    }
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-in');
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -8% 0px' });
    items.forEach(function (el) { observer.observe(el); });
  }

  function boot() {
    applyCopy();
    wireBlocks();
    initReveal();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  window.SMHomeI18N = I18N;
})();
