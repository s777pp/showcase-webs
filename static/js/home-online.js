/* "Now on the site" on the painted monitor of the landing (2026-10-07, owner request).
   The art shows a Steam profile with "Currently Offline"; .home-online covers that line with the
   panel colour and shows, Steam-style, "Now on the site" + the live count. The count comes from
   the shell's presence ping (ss-shell.js -> /api/presence -> event sm:online). Hidden until the
   first answer, so a failed request leaves the painting as it is. */
(function () {
  'use strict';
  var box = document.getElementById('homeOnline');
  if (!box) return;
  // [state line, count line with {n}]
  var COPY = {
    en: ['Now on the site', '{n} online'],
    ru: ['Сейчас на сайте', '{n} онлайн'],
    de: ['Gerade auf der Seite', '{n} online'],
    tr: ['Şu an sitede', '{n} çevrimiçi'],
    fr: ['Sur le site en ce moment', '{n} en ligne'],
    uk: ['Зараз на сайті', '{n} онлайн'],
    es: ['Ahora en el sitio', '{n} en línea'],
    pt: ['Agora no site', '{n} online']
  };
  var stateEl = box.querySelector('.home-online__state'), countEl = box.querySelector('.home-online__count');
  function lang() {
    var l = (window.SSShell && SSShell.lang && SSShell.lang()) || document.documentElement.lang || 'en';
    l = String(l).slice(0, 2).toLowerCase();
    return COPY[l] ? l : 'en';
  }
  function paint(n) {
    n = Math.max(1, Number(n) || 0); // the visitor looking at it is always there
    var c = COPY[lang()];
    stateEl.textContent = c[0];
    countEl.textContent = c[1].replace('{n}', new Intl.NumberFormat(lang()).format(n));
    box.hidden = false;
  }
  document.addEventListener('sm:online', function (event) { paint(event.detail); });
  if (window.SM_ONLINE != null) paint(window.SM_ONLINE);
  // Language switch repaints the text.
  new MutationObserver(function () { if (!box.hidden && window.SM_ONLINE != null) paint(window.SM_ONLINE); })
    .observe(document.documentElement, { attributes: true, attributeFilter: ['lang'] });
})();
