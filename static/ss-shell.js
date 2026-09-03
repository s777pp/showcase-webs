/* Shared site shell: one header + footer for every tab.
   Pages include ss.css + this file and get the same chrome, the same active-tab
   logic and the same auth pill. Nothing here touches page-local markup, so it
   can be added to an existing page without changing its behaviour. */
(function () {
  'use strict';

  var NAV = [
    { href: '/',        key: 'home',    label: { ru: 'Главная',    en: 'Home' },     icon: 'home' },
    { href: '/app',     key: 'tools',   label: { ru: 'Инструменты',en: 'Tools' },    icon: 'tools' },
    { href: '/profile', key: 'builder', label: { ru: 'Профиль',    en: 'Profile' },  icon: 'user', tag: 'new' },
    { href: '/gallery', key: 'gallery', label: { ru: 'Галерея',    en: 'Gallery' },  icon: 'grid' }
  ];

  var GROUPS = [
    { title: { ru: 'Сайт',        en: 'Site' },    items: ['home', 'gallery'] },
    { title: { ru: 'Инструменты', en: 'Tools' },   items: ['tools', 'builder'] },
    { title: { ru: 'Аккаунт',     en: 'Account' }, items: ['account'] }
  ];

  var ICONS = {
    home: '<path d="M3 10.5 12 3l9 7.5V21H3z"/>',
    tools: '<path d="M4 7h16M4 12h10M4 17h7"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8"/>',
    grid: '<path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"/>',
    key: '<circle cx="8" cy="12" r="4"/><path d="M12 12h9M18 12v4"/>'
  };

  var OAUTH_ICONS = {
    discord: '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="#8b95ff" d="M20.3 4.4a19.7 19.7 0 0 0-4.9-1.5l-.6 1.2a18.3 18.3 0 0 0-5.5 0l-.6-1.2a19.7 19.7 0 0 0-4.9 1.5C.5 9-.3 13.6.1 18.1a19.9 19.9 0 0 0 6 3l1.2-2a13 13 0 0 1-1.9-.9l.4-.3c3.9 1.8 8.2 1.8 12.1 0l.4.3a12 12 0 0 1-1.9.9l1.2 2a19.8 19.8 0 0 0 6-3c.5-5.2-.8-9.7-3.3-13.7ZM8 15.3c-1.2 0-2.2-1.1-2.2-2.4s1-2.4 2.2-2.4 2.2 1.1 2.2 2.4-1 2.4-2.2 2.4Zm8 0c-1.2 0-2.2-1.1-2.2-2.4s1-2.4 2.2-2.4 2.2 1.1 2.2 2.4-1 2.4-2.2 2.4Z"/></svg>',
    google: '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="#4285F4" d="M21.6 12.2c0-.7-.1-1.5-.2-2.2H12v4.3h5.4a4.6 4.6 0 0 1-2 3v2.8h3.3c1.9-1.8 2.9-4.4 2.9-7.9Z"/><path fill="#34A853" d="M12 22c2.7 0 5-.9 6.7-2.4l-3.3-2.8c-.9.6-2.1 1-3.4 1a5.9 5.9 0 0 1-5.5-4.1H3.1v2.9A10 10 0 0 0 12 22Z"/><path fill="#FBBC05" d="M6.5 13.7a6 6 0 0 1 0-3.8V7H3.1a10 10 0 0 0 0 9.6l3.4-2.9Z"/><path fill="#EA4335" d="M12 5.8c1.5 0 2.8.5 3.8 1.5l2.9-2.8A9.7 9.7 0 0 0 12 2a10 10 0 0 0-8.9 5.4l3.4 2.5A5.9 5.9 0 0 1 12 5.8Z"/></svg>',
    telegram: '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><circle cx="12" cy="12" r="11" fill="#26A5E4"/><path fill="#fff" d="m17.8 7-2 10c-.2.7-.6.9-1.2.5l-3-2.2-1.5 1.4c-.2.2-.3.3-.7.3l.2-3.1 5.7-5.2c.2-.2 0-.4-.4-.2l-7 4.4-3-.9c-.7-.2-.7-.7.1-1l11.7-4.5c.6-.2 1.1.1 1.1.5Z"/></svg>',
    steam: '<img src="/static/steam.png" width="20" height="20" alt="" aria-hidden="true" style="display:block;object-fit:contain">'
  };

  function lang() {
    try { return localStorage.getItem('sm_lang') || localStorage.getItem('ss_lang') || 'ru'; } catch (e) { return 'ru'; }
  }
  function t(obj) { return obj[lang()] || obj.ru; }
  function svg(name) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" ' +
      'stroke-linecap="round" stroke-linejoin="round">' + (ICONS[name] || '') + '</svg>';
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function active(href) {
    var p = location.pathname.replace(/\/+$/, '') || '/';
    if (href === '/') return p === '/';
    /* конструктор пока живёт на временном адресе /profile2 — подсвечиваем «Профиль» */
    if (href === '/profile' && p === '/profile2') return true;
    return p === href || p.indexOf(href + '/') === 0;
  }

  function navHTML() {
    return NAV.map(function (n) {
      return '<a class="ss-nav__i' + (active(n.href) ? ' is-on' : '') + '" href="' + n.href + '">' +
        svg(n.icon) + '<span>' + esc(t(n.label)) + '</span>' +
        (n.tag ? '<i class="ss-nav__tag">' + esc(n.tag) + '</i>' : '') + '</a>';
    }).join('');
  }

  function drawerHTML() {
    var byKey = {};
    NAV.forEach(function (n) { byKey[n.key] = n; });
    byKey.account = { href: '/profile#account', key: 'account', icon: 'key',
                      label: { ru: 'Аккаунт и Pro-ключ', en: 'Account & Pro key' } };
    return GROUPS.map(function (g) {
      var links = g.items.map(function (k) {
        var n = byKey[k];
        if (!n) return '';
        return '<a href="' + n.href + '"' + (active(n.href) ? ' class="is-on"' : '') + '>' +
          svg(n.icon) + esc(t(n.label)) + '</a>';
      }).join('');
      return '<div class="ss-drawer__g"><p class="ss-drawer__t">' + esc(t(g.title)) + '</p>' + links + '</div>';
    }).join('');
  }

  function langHTML() {
    var cur = lang();
    return '<button class="ss-lang__btn" id="ssLangToggle" type="button" aria-label="' +
      (cur === 'ru' ? 'Switch to English' : 'Переключить на русский') + '">' + cur.toUpperCase() + '</button>';
  }

  function headerHTML() {
    return '<header class="ss-head"><div class="ss-wrap ss-head__in">' +
      '<a class="ss-logo" href="/"><span class="ss-logo__mark"><img src="/static/icon.png" alt=""></span>' +
      '<span class="ss-logo__txt">Showcase <span>Maker</span></span></a>' +
      '<nav class="ss-nav">' + navHTML() + '</nav>' +
      '<span class="ss-head__sp"></span>' +
      '<div class="ss-head__right"><button class="ss-activate" id="ssActivate" type="button">' + svg('key') + '<span>' +
        (lang() === 'ru' ? 'Активация' : 'Activate') + '</span></button>' + langHTML() +
        '<a class="ss-pill" id="ssUser" href="/profile" hidden></a>' +
        '<button class="ss-btn ss-btn--sm" id="ssLogin" type="button">' +
          (lang() === 'ru' ? 'Войти' : 'Log in') + '</button>' +
        '<button class="ss-btn ss-btn--sm ss-btn--logout" id="ssLogout" type="button" hidden style="background:#c0392b;color:#fff;border-color:#c0392b">' +
          (lang() === 'ru' ? 'Выйти' : 'Log out') + '</button>' +
        '<button class="ss-burger" id="ssBurger" type="button" aria-label="Menu"><span></span></button>' +
      '</div></div></header>' +
      '<div class="ss-drawer" id="ssDrawer">' + drawerHTML() + '</div>';
  }

  function activationHTML() {
    var ru = lang() === 'ru';
    return '<div class="ss-activation" id="ssActivation" aria-hidden="true"><div class="ss-activation__card" role="dialog" aria-modal="true" aria-labelledby="ssActivationTitle">' +
      '<button class="ss-auth__close" id="ssActivationClose" type="button" aria-label="Close">×</button>' +
      '<div class="ss-activation__icon">' + svg('key') + '</div>' +
      '<p class="ss-auth__eyebrow">SHOWCASE MAKER / PRO</p>' +
      '<h2 id="ssActivationTitle">' + (ru ? 'Активировать ключ' : 'Activate a key') + '</h2>' +
      '<p class="ss-auth__sub">' + (ru ? 'Ключ привязывается к аккаунту. Один ключ нельзя использовать повторно.' : 'The key is linked to your account and cannot be reused.') + '</p>' +
      '<form class="ss-activation__form" id="ssActivationForm"><label><span>' + (ru ? 'Ключ доступа' : 'Access key') + '</span><div class="ss-activation__entry"><input id="ssActivationCode" autocomplete="off" spellcheck="false" placeholder="XXXX-XXXX-XXXX"><button type="submit">' + (ru ? 'Активировать' : 'Activate') + '</button></div></label><p class="ss-auth__state" id="ssActivationState"></p></form>' +
      '<div class="ss-activation__divide"><span>' + (ru ? 'Купить ключ' : 'Buy a key') + '</span></div>' +
      '<div class="ss-activation__shops" style="display:grid;grid-template-columns:1fr 1fr;gap:10px"><a href="https://funpay.com/lots/offer?id=76420307" target="_blank" rel="noopener"><b>FunPay</b><small>' + (ru ? 'Код после оплаты' : 'Code after payment') + '</small><i>↗</i></a><a href="https://t.me/SteamMakerBot" target="_blank" rel="noopener"><b>Telegram</b><small>' + (ru ? 'Покупка через бота' : 'Buy via bot') + '</small><i>↗</i></a><a href="https://store.showcasemaker.com" target="_blank" rel="noopener" style="grid-column:1 / -1"><b>Gumroad</b><small>' + (ru ? 'Купить Pro ключ' : 'Buy Pro key') + '</small><i>↗</i></a></div>' +
    '</div></div>';
  }

  function authHTML() {
    var ru = lang() === 'ru';
    return '<div class="ss-auth" id="ssAuth" aria-hidden="true"><div class="ss-auth__card" role="dialog" aria-modal="true" aria-labelledby="ssAuthTitle">' +
      '<button class="ss-auth__close" id="ssAuthClose" type="button" aria-label="Close">×</button>' +
      '<div class="ss-auth__mark"><img src="/static/icon.png" alt=""></div>' +
      '<p class="ss-auth__eyebrow">SHOWCASE MAKER / ACCOUNT</p>' +
      '<h2 id="ssAuthTitle">' + (ru ? 'С возвращением' : 'Welcome back') + '</h2>' +
      '<p class="ss-auth__sub" id="ssAuthSub">' + (ru ? 'Войди, чтобы сохранять проекты и использовать Pro.' : 'Log in to save projects and use Pro.') + '</p>' +
      '<form class="ss-auth__form" id="ssAuthForm">' +
        '<label><span>Email</span><input id="ssAuthEmail" type="email" autocomplete="email" required placeholder="name@example.com"></label>' +
        '<label><span>' + (ru ? 'Пароль' : 'Password') + '</span><input id="ssAuthPass" type="password" autocomplete="current-password" minlength="6" required placeholder="••••••••"></label>' +
        '<p class="ss-auth__state" id="ssAuthState"></p>' +
        '<button class="ss-auth__submit" id="ssAuthSubmit" type="submit">' + (ru ? 'Войти' : 'Log in') + '</button>' +
      '</form>' +
      '<div class="ss-auth__div"><span>' + (ru ? 'или войти через' : 'or continue with') + '</span></div>' +
      '<div class="ss-auth__oauth" style="display:flex;flex-direction:column;gap:10px;width:100%;margin:0 0 8px">' +
        '<button type="button" class="ss-auth__oauth-btn" id="ssAuthDiscord" style="display:flex;align-items:center;justify-content:center;gap:10px;width:100%;min-height:48px;border-radius:14px;border:1px solid rgba(88,101,242,.45);background:rgba(88,101,242,.18);color:#fff;font-weight:700;font-size:14px;cursor:pointer">' + OAUTH_ICONS.discord + '<span>Discord</span></button>' +
        '<button type="button" class="ss-auth__oauth-btn" id="ssAuthGoogle" style="display:flex;align-items:center;justify-content:center;gap:10px;width:100%;min-height:48px;border-radius:14px;border:1px solid rgba(255,255,255,.16);background:rgba(255,255,255,.06);color:#fff;font-weight:700;font-size:14px;cursor:pointer">' + OAUTH_ICONS.google + '<span>Google</span></button>' +
        '<button type="button" class="ss-auth__oauth-btn" id="ssAuthTelegram" style="display:flex;align-items:center;justify-content:center;gap:10px;width:100%;min-height:48px;border-radius:14px;border:1px solid rgba(38,165,228,.45);background:rgba(38,165,228,.14);color:#fff;font-weight:700;font-size:14px;cursor:pointer">' + OAUTH_ICONS.telegram + '<span>Telegram</span></button>' +
        '<button type="button" class="ss-auth__oauth-btn" id="ssAuthSteam" style="display:flex;align-items:center;justify-content:center;gap:10px;width:100%;min-height:48px;border-radius:14px;border:1px solid rgba(27,40,56,.9);background:linear-gradient(180deg,#2a475e,#1b2838);color:#fff;font-weight:700;font-size:14px;cursor:pointer">' + OAUTH_ICONS.steam + '<span>Steam</span></button>' +
      '</div>' +
      '<div id="ssTgHost" style="display:none;text-align:center;margin-top:8px"></div>' +
      '<button class="ss-auth__switch" id="ssAuthSwitch" type="button">' + (ru ? 'Нет аккаунта? Создать' : 'No account? Sign up') + '</button>' +
    '</div></div>';
  }

  function footerHTML() {
    var ru = lang() === 'ru';
    var links = [
      ['/app', ru ? 'Инструменты' : 'Tools'],
      ['/gallery', ru ? 'Галерея' : 'Gallery'],
      ['/profile', ru ? 'Профиль' : 'Profile'],
      ['/#pricing', ru ? 'Тарифы' : 'Pricing'],
      ['/#faq', 'FAQ']
    ];
    return '<footer class="ss-foot"><div class="ss-wrap ss-foot__in">' +
      '<nav class="ss-foot__nav">' + links.map(function (l) {
        return '<a href="' + l[0] + '">' + esc(l[1]) + '</a>';
      }).join('') + '</nav>' +
      '<p class="ss-foot__note">Steam and Valve are trademarks of Valve Corporation. ' +
      (ru ? 'Проект неофициальный и не связан с Valve.' : 'This project is unofficial and not affiliated with Valve.') +
      '</p></div></footer>';
  }

  /* auth pill — one request, cached on window so a page can reuse it */
  function paintUser(me) {
    var pill = document.getElementById('ssUser');
    var login = document.getElementById('ssLogin');
    var logout = document.getElementById('ssLogout');
    var logged = !!(me && (me.logged_in === true || me.ok === true && me.email));
    /* use display — [hidden] is overridden by .ss-btn { display:inline-flex } */
    if (pill) {
      pill.hidden = !logged;
      pill.style.display = logged ? 'inline-flex' : 'none';

      // User pill -> PUBLIC profile.
      // The "Profile" menu item still opens the editor at /profile.
      var publicUsername = me && (me.profile_username || me.username);
      if (logged && publicUsername) {
        pill.href = '/profile/' + encodeURIComponent(publicUsername);
      } else {
        pill.href = '/profile';
      }
    }
    if (login) {
      login.hidden = logged;
      login.style.setProperty('display', logged ? 'none' : 'inline-flex', 'important');
    }
    if (logout) {
      logout.hidden = !logged;
      logout.style.setProperty('display', logged ? 'inline-flex' : 'none', 'important');
    }
    var activate = document.getElementById('ssActivate');

    // Activation button state:
    // FREE -> show Activate
    // TRIAL -> show live countdown
    // PERMANENT PRO -> hide activation button
    if (window.SS_PRO_TIMER) {
      clearInterval(window.SS_PRO_TIMER);
      window.SS_PRO_TIMER = null;
    }

    if (activate) {
      if (!logged || !me.is_pro) {
        activate.style.display = 'inline-flex';
        activate.disabled = false;
        activate.onclick = openActivation;
        activate.innerHTML = svg('key') + '<span>' +
          (lang() === 'ru' ? 'Активация' : 'Activate') + '</span>';
      } else if (me.pro_until) {
        var untilMs = Number(me.pro_until) * 1000;

        var renderProTimer = function () {
          var left = Math.max(0, untilMs - Date.now());

          if (left <= 0) {
            if (window.SS_PRO_TIMER) {
              clearInterval(window.SS_PRO_TIMER);
              window.SS_PRO_TIMER = null;
            }
            activate.style.display = 'inline-flex';
            activate.disabled = false;
            activate.onclick = openActivation;
            activate.innerHTML = svg('key') + '<span>' +
              (lang() === 'ru' ? 'Активация' : 'Activate') + '</span>';
            return;
          }

          var total = Math.floor(left / 1000);
          var hours = Math.floor(total / 3600);
          var minutes = Math.floor((total % 3600) / 60);
          var seconds = total % 60;

          var timer =
            String(hours).padStart(2, '0') + ':' +
            String(minutes).padStart(2, '0') + ':' +
            String(seconds).padStart(2, '0');

          activate.style.display = 'inline-flex';
          activate.disabled = true;
          activate.onclick = null;
          activate.innerHTML = '<span>⏱ ' + timer + '</span>';
        };

        renderProTimer();
        window.SS_PRO_TIMER = setInterval(renderProTimer, 1000);
      } else {
        // Permanent Pro
        activate.style.display = 'none';
        activate.onclick = null;
      }
    }

    if (!logged || !pill) return;
    var name = me.display_name || (me.email || '').split('@')[0] || 'profile';
    var av = me.avatar_url || '';
    pill.innerHTML =
      (av ? '<img class="ss-pill__av" src="' + esc(av) + '" alt="">'
          : '<span class="ss-pill__av"></span>') +
      '<span>' + esc(name) + '</span>' +
      '<i class="ss-pill__plan ' + (me.is_pro ? 'is-pro">PRO' : 'is-free">FREE') + '</i>';
  }

  // One request for the whole shell. /api/bootstrap returns everything
  // /api/auth/me did plus the unread count, so a page's own scripts can reuse
  // this response instead of asking the server about the same session again.
  var _mePromise = null;

  function loadMe() {
    _mePromise = fetch('/api/bootstrap', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .catch(function () { return { logged_in: false }; })
      .then(function (me) {
        window.SS_ME = me;
        paintUser(me);
        document.dispatchEvent(new CustomEvent('ss:me', { detail: me }));
        return me;
      });
    return _mePromise;
  }

  // The in-flight (or already finished) bootstrap, without starting a second
  // request. Use loadMe() instead when the state must be re-read - after a
  // login, for instance.
  function me() { return _mePromise || loadMe(); }

  function wire() {
    var burger = document.getElementById('ssBurger');
    var drawer = document.getElementById('ssDrawer');
    if (burger && drawer) {
      burger.addEventListener('click', function () {
        drawer.classList.toggle('is-open');
        document.body.style.overflow = drawer.classList.contains('is-open') ? 'hidden' : '';
      });
    }
    var langToggle = document.getElementById('ssLangToggle');
    if (langToggle) {
      langToggle.addEventListener('click', function () {
        var code = lang() === 'ru' ? 'en' : 'ru';
        try { localStorage.setItem('ss_lang', code); localStorage.setItem('sm_lang', code); } catch (e) {}
        if (typeof window.ssApplyLang === 'function') window.ssApplyLang(code);
        else if (typeof window.applyAppLang === 'function') window.applyAppLang(code);
        else if (typeof window.applyLang === 'function') window.applyLang(code);
        else { location.reload(); return; }
        mount();
      });
    }
    wireAuth();
    wireActivation();
  }

  function openActivation() {
    var modal = document.getElementById('ssActivation');
    if (!modal) return;
    modal.classList.add('is-open'); modal.setAttribute('aria-hidden', 'false'); document.body.style.overflow = 'hidden';
    setTimeout(function () { document.getElementById('ssActivationCode')?.focus(); }, 40);
  }
  function closeActivation() {
    var modal = document.getElementById('ssActivation');
    if (!modal) return;
    modal.classList.remove('is-open'); modal.setAttribute('aria-hidden', 'true'); document.body.style.overflow = '';
  }
  function wireActivation() {
    var open = document.getElementById('ssActivate'), close = document.getElementById('ssActivationClose');
    var modal = document.getElementById('ssActivation'), form = document.getElementById('ssActivationForm');
    if (open) open.onclick = openActivation;
    if (close) close.onclick = closeActivation;
    if (modal) modal.onclick = function (e) { if (e.target === modal) closeActivation(); };
    if (form) form.onsubmit = function (e) {
      e.preventDefault();
      var code = (document.getElementById('ssActivationCode').value || '').trim();
      var state = document.getElementById('ssActivationState'), button = form.querySelector('button[type="submit"]');
      if (!code) { state.textContent = lang() === 'ru' ? 'Введите ключ.' : 'Enter a key.'; state.className = 'ss-auth__state is-bad'; return; }
      state.textContent = lang() === 'ru' ? 'Проверяем ключ…' : 'Checking key…'; state.className = 'ss-auth__state is-wait'; button.disabled = true;
      fetch('/api/unlock', { method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify({code:code}) })
        .then(function (r) { return r.json().then(function (j) { return { status:r.status, data:j }; }); })
        .then(function (x) {
          if (!x.data || !x.data.ok) {
            if (x.status === 401) { closeActivation(); openAuth('login'); throw new Error(lang() === 'ru' ? 'Сначала войдите в аккаунт.' : 'Log in first.'); }
            throw new Error((x.data && x.data.msg) || 'Activation failed');
          }
          state.textContent = x.data.msg || (lang() === 'ru' ? 'Pro активирован.' : 'Pro activated.'); state.className = 'ss-auth__state is-ok';
          return loadMe();
        }).catch(function (err) { state.textContent = err.message; state.className = 'ss-auth__state is-bad'; })
        .then(function () { button.disabled = false; });
    };
  }

  var authMode = 'login';
  function openAuth(mode) {
    authMode = mode === 'register' ? 'register' : 'login';
    var modal = document.getElementById('ssAuth');
    if (!modal) return;
    paintAuth();
    modal.classList.add('is-open'); modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
    setTimeout(function () { var e = document.getElementById('ssAuthEmail'); if (e) e.focus(); }, 40);
  }
  function closeAuth() {
    var modal = document.getElementById('ssAuth');
    if (!modal) return;
    modal.classList.remove('is-open'); modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }
  function paintAuth() {
    var ru = lang() === 'ru', reg = authMode === 'register';
    var title = document.getElementById('ssAuthTitle'), sub = document.getElementById('ssAuthSub');
    var submit = document.getElementById('ssAuthSubmit'), sw = document.getElementById('ssAuthSwitch');
    if (title) title.textContent = reg ? (ru ? 'Создать аккаунт' : 'Create account') : (ru ? 'С возвращением' : 'Welcome back');
    if (sub) sub.textContent = reg ? (ru ? 'Один аккаунт для проектов, галереи и Pro.' : 'One account for projects, gallery and Pro.') : (ru ? 'Войди, чтобы сохранять проекты и использовать Pro.' : 'Log in to save projects and use Pro.');
    if (submit) submit.textContent = reg ? (ru ? 'Зарегистрироваться' : 'Sign up') : (ru ? 'Войти' : 'Log in');
    if (sw) sw.textContent = reg ? (ru ? 'Уже есть аккаунт? Войти' : 'Already registered? Log in') : (ru ? 'Нет аккаунта? Создать' : 'No account? Sign up');
  }
  function wireAuth() {
    var login = document.getElementById('ssLogin'), modal = document.getElementById('ssAuth');
    var close = document.getElementById('ssAuthClose'), sw = document.getElementById('ssAuthSwitch');
    var form = document.getElementById('ssAuthForm');
    if (login) login.onclick = function () { openAuth('login'); };
    if (close) close.onclick = closeAuth;
    if (modal) modal.onclick = function (e) { if (e.target === modal) closeAuth(); };
    if (sw) sw.onclick = function () { authMode = authMode === 'login' ? 'register' : 'login'; paintAuth(); };
    if (form) form.onsubmit = function (e) {
      e.preventDefault();
      var email = document.getElementById('ssAuthEmail').value.trim();
      var password = document.getElementById('ssAuthPass').value;
      var state = document.getElementById('ssAuthState'), submit = document.getElementById('ssAuthSubmit');
      state.textContent = lang() === 'ru' ? 'Подключаем…' : 'Connecting…'; state.className = 'ss-auth__state is-wait';
      submit.disabled = true;
      fetch(authMode === 'register' ? '/api/auth/register' : '/api/auth/login', { method:'POST', credentials:'include', headers:{'Content-Type':'application/json'}, body:JSON.stringify({email:email,password:password}) })
        .then(function (r) { return r.json(); }).then(function (j) {
          if (!j || !j.ok) throw new Error((j && j.msg) || 'Authentication failed');
          if (j.token) {
            try { localStorage.setItem('sm_session', j.token); } catch (e) {}
            var secure = location.protocol === 'https:' ? '; Secure' : '';
            document.cookie = 'sm_session=' + encodeURIComponent(j.token) + '; path=/; max-age=' + (90*24*3600) + '; SameSite=Lax' + secure;
          }
          state.textContent = lang() === 'ru' ? 'Готово' : 'Done'; state.className = 'ss-auth__state is-ok';
          return loadMe().then(function () { setTimeout(closeAuth, 350); });
        }).catch(function (err) { state.textContent = err.message; state.className = 'ss-auth__state is-bad'; })
        .then(function () { submit.disabled = false; });
    };
  }

  function mount() {
    var head = document.getElementById('ssHeadHost');
    var foot = document.getElementById('ssFootHost');
    if (head) head.innerHTML = headerHTML() + authHTML() + activationHTML();
    if (foot) foot.innerHTML = footerHTML();
    wire();
    paintUser(window.SS_ME);
  }

  window.SSShell = { mount: mount, loadMe: loadMe, me: me, lang: lang, t: t, esc: esc, openAuth: openAuth, closeAuth: closeAuth, openActivation: openActivation, closeActivation: closeActivation };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { mount(); 
    var logoutBtn = document.getElementById('ssLogout');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', function () {
        fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' })
          .then(function () {
            try { localStorage.removeItem('sm_session'); } catch (e) {}
            location.reload();
          });
      });
    }
    function openOAuth(path, name) {
      fetch(path, { credentials: 'same-origin' })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (!d.ok || !d.url) { alert((d && d.msg) || (name + ' not configured')); return; }
          var w = window.open(d.url, name + '_oauth', 'width=560,height=720');
          if (!w) location.href = d.url;
        })
        .catch(function (e) { alert(String(e)); });
    }
    var dBtn = document.getElementById('ssAuthDiscord');
    if (dBtn) dBtn.onclick = function () { openOAuth('/api/auth/discord/login', 'discord'); };
    var gBtn = document.getElementById('ssAuthGoogle');
    if (gBtn) gBtn.onclick = function () { openOAuth('/api/auth/google/login', 'google'); };
    var sBtn = document.getElementById('ssAuthSteam');
    if (sBtn) sBtn.onclick = function () { openOAuth('/api/auth/steam/login', 'steam'); };
    var tBtn = document.getElementById('ssAuthTelegram');
    if (tBtn) tBtn.onclick = function () {
      fetch('/api/auth/telegram/config').then(function (r) { return r.json(); }).then(function (d) {
        if (!d.ok || !d.bot_username) { alert((d && d.msg) || 'Telegram not configured'); return; }
        var host = document.getElementById('ssTgHost');
        if (!host) return;
        host.style.display = 'block';
        host.innerHTML = '';
        window.onTelegramAuth = function (user) {
          fetch('/api/auth/telegram', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(user),
          }).then(function (r) { return r.json(); }).then(function (j) {
            if (j.token) try { localStorage.setItem('sm_session', j.token); } catch (e) {}
            location.reload();
          });
        };
        var s = document.createElement('script');
        s.src = 'https://telegram.org/js/telegram-widget.js?22';
        s.setAttribute('data-telegram-login', d.bot_username);
        s.setAttribute('data-size', 'large');
        s.setAttribute('data-radius', '12');
        s.setAttribute('data-onauth', 'onTelegramAuth(user)');
        s.setAttribute('data-request-access', 'write');
        host.appendChild(s);
      });
    };
    window.addEventListener('message', function (ev) {
      if (!ev.data) return;
      if (ev.data.type === 'discord_login' || ev.data.type === 'google_login' ||
          ev.data.type === 'telegram_login' || ev.data.type === 'steam_login') {
        if (ev.data.token) try { localStorage.setItem('sm_session', ev.data.token); } catch (e) {}
        location.reload();
      }
    });

  loadMe(); });
  } else { mount(); loadMe(); }
})();



/* SHOWCASEMAKER_PAYMENT_CARDS_V2 */
(() => {
  const STYLE_ID = "sm-payment-card-style-v2";

  function addStyles() {
    if (document.getElementById(STYLE_ID)) return;

    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      .ss-activation__shops .sm-shop-icon-right {
        width: 20px;
        height: 20px;
        min-width: 20px;
        margin-left: auto;
        margin-right: 7px;
        object-fit: contain;
        display: block;
      }

      .ss-activation__shops .sm-shop-icon-svg {
        width: 20px;
        height: 20px;
        min-width: 20px;
        margin-left: auto;
        margin-right: 7px;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .ss-activation__shops a.sm-card-payment {
        grid-column: 1 / -1 !important;
        width: 100% !important;
        max-width: none !important;
        justify-self: stretch !important;
        box-sizing: border-box !important;
      }

      .ss-activation__shops a.sm-shop-fixed {
        display: flex !important;
        align-items: center !important;
      }

      .ss-activation__shops a.sm-shop-fixed > span:last-child {
        margin-left: 0 !important;
      }
    `;

    document.head.appendChild(style);
  }

  function telegramIcon() {
    const span = document.createElement("span");
    span.className = "sm-shop-icon-svg";
    span.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="12" cy="12" r="11" fill="#229ED9"/>
        <path d="M17.7 7.2L6.7 11.45c-.75.3-.74.72-.14.91l2.83.88
                 1.08 3.36c.14.38.07.53.47.53.31 0 .44-.14.61-.3
                 l1.36-1.32 2.82 2.08c.52.29.89.14 1.02-.48
                 l1.85-8.73c.19-.76-.29-1.11-.9-.88z"
              fill="white"/>
      </svg>`;
    return span;
  }

  function cardIcon() {
    const span = document.createElement("span");
    span.className = "sm-shop-icon-svg";
    span.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="2.5" y="5" width="19" height="14" rx="3"
              stroke="#7DDFFF" stroke-width="1.8"/>
        <path d="M3 9H21" stroke="#7DDFFF" stroke-width="1.8"/>
        <path d="M6 15H10" stroke="#7DDFFF" stroke-width="1.8"
              stroke-linecap="round"/>
      </svg>`;
    return span;
  }

  function decorate() {
    addStyles();

    const root = document.querySelector(".ss-activation__shops");
    if (!root) return;

    const links = [...root.querySelectorAll("a")];

    for (const a of links) {
      if (a.dataset.smPaymentV2 === "1") continue;

      const href = (a.getAttribute("href") || "").toLowerCase();
      const txt = (a.textContent || "").toLowerCase();

      let type = null;

      if (href.includes("funpay.com") || txt.includes("funpay")) {
        type = "funpay";
      } else if (href.includes("t.me") || txt.includes("telegram")) {
        type = "telegram";
      } else if (
        href.includes("store.showcasemaker.com") ||
        txt.includes("gumroad") ||
        txt.includes("оплатить картой") ||
        txt.includes("pay by card")
      ) {
        type = "card";
      }

      if (!type) continue;

      a.classList.add("sm-shop-fixed");

      const arrow = a.lastElementChild;

      let icon;

      if (type === "funpay") {
        icon = document.createElement("img");
        icon.className = "sm-shop-icon-right";
        icon.src = "/static/img/funpay-favicon.ico";
        icon.alt = "";
        icon.onerror = function () {
          if (!this.dataset.pngFallback) {
            this.dataset.pngFallback = "1";
            this.src = "/static/img/funpay-favicon.png";
          }
        };
      }

      if (type === "telegram") {
        icon = telegramIcon();
      }

      if (type === "card") {
        icon = cardIcon();

        a.classList.add("sm-card-payment");

        const b = a.querySelector("b");
        const small = a.querySelector("small");

        if (b) {
          b.setAttribute("data-ru", "Оплатить картой");
          b.setAttribute("data-en", "Pay by card");

          const lang =
            (document.documentElement.lang || "").toLowerCase();

          b.textContent = lang.startsWith("en")
            ? "Pay by card"
            : "Оплатить картой";
        }

        if (small) {
          small.setAttribute("data-ru", "Купить Pro ключ");
          small.setAttribute("data-en", "Buy Pro key");

          const lang =
            (document.documentElement.lang || "").toLowerCase();

          small.textContent = lang.startsWith("en")
            ? "Buy Pro key"
            : "Купить Pro ключ";
        }
      }

      if (icon) {
        if (arrow) {
          a.insertBefore(icon, arrow);
        } else {
          a.appendChild(icon);
        }
      }

      a.dataset.smPaymentV2 = "1";
    }
  }

  const observer = new MutationObserver(decorate);

  function start() {
    decorate();

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
