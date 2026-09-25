(function () {
  'use strict';
  var lang = window.SMLang && SMLang.get ? SMLang.get() : (/^\/ru(?:\/|$)/.test(location.pathname) ? 'ru' : 'en');
  if (lang === 'ru') {
    document.documentElement.lang = 'ru';
    document.title = 'SteamShowcase Helper — инструкция | Showcase Maker';
    var description = document.querySelector('meta[name="description"]');
    if (description) description.content = 'Как установить SteamShowcase Helper и загрузить готовую витрину в Steam: автоматически или вручную.';
    document.querySelectorAll('[data-eg-ru]').forEach(function (node) { node.textContent = node.getAttribute('data-eg-ru'); });
    document.querySelectorAll('[data-eg-alt-ru]').forEach(function (node) { node.alt = node.getAttribute('data-eg-alt-ru'); });
    document.querySelectorAll('[data-eg-aria-ru]').forEach(function (node) { node.setAttribute('aria-label', node.getAttribute('data-eg-aria-ru')); });
  }
  document.querySelectorAll('[data-eg-app]').forEach(function (link) {
    link.href = (window.SMLang && SMLang.url ? SMLang.url('/app') : '/' + lang + '/app') + '#steam';
  });
})();
