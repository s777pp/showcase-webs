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

  var LANGS = [
    { code: 'ru', name: 'Русский' },
    { code: 'en', name: 'English' }
  ];

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
    return '<div class="ss-lang" id="ssLang">' +
      '<button class="ss-lang__btn" type="button" aria-haspopup="true">' +
        cur.toUpperCase() + '<span>▾</span></button>' +
      '<div class="ss-lang__list">' + LANGS.map(function (l) {
        return '<button type="button" data-lang="' + l.code + '"' +
          (l.code === cur ? ' class="is-on"' : '') + '>' + esc(l.name) + '</button>';
      }).join('') + '</div></div>';
  }

  function headerHTML() {
    return '<header class="ss-head"><div class="ss-wrap ss-head__in">' +
      '<a class="ss-logo" href="/"><span class="ss-logo__mark"><img src="/static/icon.png" alt=""></span>' +
      '<span class="ss-logo__txt">Showcase <span>Maker</span></span></a>' +
      '<nav class="ss-nav">' + navHTML() + '</nav>' +
      '<span class="ss-head__sp"></span>' +
      '<div class="ss-head__right">' + langHTML() +
        '<a class="ss-pill" id="ssUser" href="/profile" hidden></a>' +
        '<a class="ss-btn ss-btn--sm" id="ssLogin" href="/app#login" hidden>' +
          (lang() === 'ru' ? 'Войти' : 'Log in') + '</a>' +
        '<button class="ss-burger" id="ssBurger" type="button" aria-label="Menu"><span></span></button>' +
      '</div></div></header>' +
      '<div class="ss-drawer" id="ssDrawer">' + drawerHTML() + '</div>';
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
    if (!pill || !login) return;
    if (!me || !me.logged_in) { pill.hidden = true; login.hidden = false; return; }
    login.hidden = true;
    var name = me.display_name || (me.email || '').split('@')[0] || 'profile';
    var av = me.avatar_url || '';
    pill.innerHTML =
      (av ? '<img class="ss-pill__av" src="' + esc(av) + '" alt="">'
          : '<span class="ss-pill__av"></span>') +
      '<span>' + esc(name) + '</span>' +
      '<i class="ss-pill__plan ' + (me.is_pro ? 'is-pro">PRO' : 'is-free">FREE') + '</i>';
    pill.hidden = false;
  }

  function loadMe() {
    return fetch('/api/auth/me', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .catch(function () { return { logged_in: false }; })
      .then(function (me) {
        window.SS_ME = me;
        paintUser(me);
        document.dispatchEvent(new CustomEvent('ss:me', { detail: me }));
        return me;
      });
  }

  function wire() {
    var burger = document.getElementById('ssBurger');
    var drawer = document.getElementById('ssDrawer');
    if (burger && drawer) {
      burger.addEventListener('click', function () {
        drawer.classList.toggle('is-open');
        document.body.style.overflow = drawer.classList.contains('is-open') ? 'hidden' : '';
      });
    }
    var box = document.getElementById('ssLang');
    if (box) {
      box.querySelector('.ss-lang__btn').addEventListener('click', function (e) {
        e.stopPropagation();
        box.classList.toggle('is-open');
      });
      box.querySelectorAll('[data-lang]').forEach(function (b) {
        b.addEventListener('click', function () {
          var code = b.getAttribute('data-lang');
          try { localStorage.setItem('ss_lang', code); localStorage.setItem('sm_lang', code); } catch (e) {}
          if (typeof window.ssApplyLang === 'function') {
            window.ssApplyLang(code);
            box.classList.remove('is-open');
            mount();               /* redraw chrome in the new language */
          } else if (typeof window.applyAppLang === 'function') {
            window.applyAppLang(code);
            box.classList.remove('is-open');
            mount();
          } else if (typeof window.applyLang === 'function') {
            window.applyLang(code);
            box.classList.remove('is-open');
            mount();
          } else {
            location.reload();     /* page has no live i18n — reload is honest */
          }
        });
      });
      document.addEventListener('click', function () { box.classList.remove('is-open'); });
    }
  }

  function mount() {
    var head = document.getElementById('ssHeadHost');
    var foot = document.getElementById('ssFootHost');
    if (head) head.innerHTML = headerHTML();
    if (foot) foot.innerHTML = footerHTML();
    wire();
    paintUser(window.SS_ME);
  }

  window.SSShell = { mount: mount, loadMe: loadMe, lang: lang, t: t, esc: esc };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { mount(); loadMe(); });
  } else { mount(); loadMe(); }
})();
