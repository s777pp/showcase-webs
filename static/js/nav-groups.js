/* Tools navigation: fewer top-level items. Existing #nav buttons are MOVED (not
   cloned) into small drop-down groups, so every handler bound in app.js,
   tool-loader.js and analytics keeps working and data-tab stays the contract.
   Only the profile tools are grouped (rating, design selection, profile preview);
   every other tool stays a top-level tab. */
(function () {
  'use strict';
  var nav = document.getElementById('nav');
  if (!nav || nav.dataset.grouped) return;
  nav.dataset.grouped = '1';
  var LANGS = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'];
  // Owner decision 2026-09-26: Upscale, Loop, Converter, Download, HEX, DeviantArt and About stay as
  // top-level tabs (users could not find them inside groups). Only the profile tools are grouped.
  var GROUPS = [
    { id: 'profile', icon: 'profile-rating', tabs: ['doctor', 'design-ai', 'preview'],
      label: ['Profile', 'Профиль', 'Profil', 'Profil', 'Profil', 'Профіль', 'Perfil', 'Perfil'] }
  ];
  var HINTS = {
    doctor: ['AI rates your profile and suggests fixes', 'ИИ оценит профиль и подскажет, что улучшить', 'KI bewertet dein Profil und gibt Tipps', 'Yapay zekâ profilini puanlar ve öneriler verir', 'L’IA note votre profil et propose des améliorations', 'ШІ оцінить профіль і підкаже, що покращити', 'La IA puntúa tu perfil y sugiere mejoras', 'A IA avalia seu perfil e sugere melhorias'],
    'design-ai': ['Design ideas that match your profile', 'Идеи оформления под твой профиль', 'Designideen passend zu deinem Profil', 'Profiline uygun tasarım fikirleri', 'Des idées de design adaptées à votre profil', 'Ідеї оформлення під твій профіль', 'Ideas de diseño para tu perfil', 'Ideias de design para o seu perfil'],
    preview: ['Try showcases on a Steam profile mock-up', 'Примерить витрины на макете профиля Steam', 'Vitrinen auf einem Steam-Profil ausprobieren', 'Vitrinleri Steam profil taslağında dene', 'Essayer les vitrines sur une maquette de profil', 'Приміряти вітрини на макеті профілю Steam', 'Probar escaparates en una maqueta de perfil', 'Testar vitrines em um modelo de perfil']
  };
  function lang() { return (window.SMLang && SMLang.get && SMLang.get()) || document.documentElement.lang || 'en'; }
  function pick(list) { return list[Math.max(0, LANGS.indexOf(lang()))] || list[0]; }

  var groups = [];
  GROUPS.forEach(function (group) {
    var members = group.tabs.map(function (tab) { return nav.querySelector(':scope > button[data-tab="' + tab + '"]'); }).filter(Boolean);
    if (!members.length) return;
    var wrap = document.createElement('div');
    wrap.className = 'nav-group';
    wrap.dataset.group = group.id;
    var trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'nav-group__trigger';
    trigger.dataset.navGroup = group.id;
    trigger.style.setProperty('--tool-icon', "url('/static/img/tool-icons/" + group.icon + ".svg')");
    trigger.setAttribute('aria-haspopup', 'true');
    trigger.setAttribute('aria-expanded', 'false');
    var menu = document.createElement('div');
    menu.className = 'nav-group__menu';
    menu.id = 'navGroup-' + group.id;
    menu.hidden = true;
    trigger.setAttribute('aria-controls', menu.id);
    members[0].before(wrap);
    // Hints live in data-hint (shown by CSS ::after): app.js rewrites button text on language change.
    members.forEach(function (button) { menu.append(button); });
    wrap.append(trigger, menu);
    groups.push({ config: group, wrap: wrap, trigger: trigger, menu: menu, members: members });
  });

  function close(except) {
    groups.forEach(function (group) {
      if (group === except) return;
      group.menu.hidden = true;
      group.trigger.setAttribute('aria-expanded', 'false');
      group.wrap.classList.remove('is-open');
    });
  }
  function place(group) {
    var rect = group.trigger.getBoundingClientRect();
    var width = Math.min(320, window.innerWidth - 16);
    group.menu.style.width = width + 'px';
    group.menu.style.left = Math.max(8, Math.min(rect.left, window.innerWidth - width - 8)) + 'px';
    group.menu.style.top = Math.round(rect.bottom + 6) + 'px';
  }
  function open(group) {
    close(group);
    place(group);
    group.menu.hidden = false;
    group.trigger.setAttribute('aria-expanded', 'true');
    group.wrap.classList.add('is-open');
  }
  function paint() {
    groups.forEach(function (group) {
      var active = group.members.filter(function (button) { return button.classList.contains('active'); })[0];
      // Not 'active': app.js and workspace-editor.js read '#nav button.active' / '#nav .active' as the open tab.
      group.trigger.classList.toggle('is-current', !!active);
      var chevron = document.createElement('span');
      chevron.className = 'nav-group__chev';
      chevron.setAttribute('aria-hidden', 'true');
      group.trigger.replaceChildren(document.createTextNode(pick(group.config.label)), chevron);
      group.trigger.title = active ? active.textContent.trim() : '';
      group.menu.setAttribute('aria-label', pick(group.config.label));
      group.members.forEach(function (button) {
        var hint = HINTS[button.dataset.tab];
        if (hint && button.dataset.hint !== pick(hint)) button.dataset.hint = pick(hint);
      });
    });
  }

  groups.forEach(function (group) {
    group.trigger.addEventListener('click', function (event) {
      event.stopPropagation();
      if (group.menu.hidden) open(group); else close();
    });
    group.menu.addEventListener('click', function (event) {
      if (event.target.closest('button[data-tab]')) { close(); setTimeout(paint, 0); }
    });
    group.wrap.addEventListener('keydown', function (event) {
      var items = group.members.filter(function (button) { return !button.hidden; });
      var index = items.indexOf(document.activeElement);
      if (event.key === 'Escape') { close(); group.trigger.focus(); }
      else if (event.key === 'ArrowDown') { event.preventDefault(); if (group.menu.hidden) open(group); (items[index + 1] || items[0]).focus(); }
      else if (event.key === 'ArrowUp' && index >= 0) { event.preventDefault(); (items[index - 1] || items[items.length - 1]).focus(); }
    });
  });
  document.addEventListener('click', function (event) { if (!event.target.closest('.nav-group')) close(); });
  // Keep an open menu attached to its trigger when the page or the (phone) tab strip scrolls.
  function follow() { groups.forEach(function (group) { if (!group.menu.hidden) place(group); }); }
  window.addEventListener('resize', follow);
  window.addEventListener('scroll', follow, { passive: true });
  nav.addEventListener('scroll', follow, { passive: true });
  // Any tab change (including programmatic ones from other scripts) repaints the triggers.
  new MutationObserver(function (records) {
    if (records.some(function (record) { return record.target.matches && record.target.matches('button[data-tab]'); })) paint();
  }).observe(nav, { subtree: true, attributes: true, attributeFilter: ['class'] });
  window.addEventListener('sm:langchange', function () { setTimeout(paint, 0); });
  paint();
  window.SMNavGroups = { open: function (id) { var g = groups.filter(function (x) { return x.config.id === id; })[0]; if (g) open(g); }, close: close };
})();
