(function () {
  'use strict';
  var lang = window.SMLang && SMLang.get ? SMLang.get() : (/^\/ru(?:\/|$)/.test(location.pathname) ? 'ru' : 'en');
  var ru = lang === 'ru';
  if (ru) {
    document.documentElement.lang = 'ru';
    document.title = 'SteamShowcase Helper — расширение для витрин Steam | Showcase Maker';
    var description = document.querySelector('meta[name="description"]');
    if (description) description.content = 'SteamShowcase Helper 1.0.9: автозагрузка файлов Showcase Maker в Steam, автоматическая расстановка по витринам, пачки загрузок, пресеты профиля и помощники для страниц Steam.';
    document.querySelectorAll('[data-eg-ru]').forEach(function (node) { node.textContent = node.getAttribute('data-eg-ru'); });
    document.querySelectorAll('[data-eg-alt-ru]').forEach(function (node) { node.alt = node.getAttribute('data-eg-alt-ru'); });
    document.querySelectorAll('[data-eg-aria-ru]').forEach(function (node) { node.setAttribute('aria-label', node.getAttribute('data-eg-aria-ru')); });
    document.querySelectorAll('[data-eg-href-ru]').forEach(function (node) { node.href = node.getAttribute('data-eg-href-ru'); });
    // Lazy images below the fold have not been requested yet, so only the Russian file is downloaded.
    document.querySelectorAll('img[data-eg-src-ru]').forEach(function (img) { img.src = img.getAttribute('data-eg-src-ru'); });
  }
  // The hero collage picture has no src in the markup: it is set here in the page language.
  document.querySelectorAll('img[data-eg-src]').forEach(function (img) {
    if (!img.getAttribute('src')) img.src = (ru && img.getAttribute('data-eg-src-ru')) || img.getAttribute('data-eg-src');
  });
  document.querySelectorAll('[data-eg-app]').forEach(function (link) {
    link.href = (window.SMLang && SMLang.url ? SMLang.url('/app') : '/' + lang + '/app') + '#steam';
  });
  // Animations restart when they scroll into view, so the visitor sees them from the first frame.
  if ('IntersectionObserver' in window) {
    var seen = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var img = entry.target, src = img.currentSrc || img.src;
        if (src && !img.dataset.egPlayed) { img.dataset.egPlayed = '1'; img.src = src.split('#')[0] + '#play'; }
        seen.unobserve(img);
      });
    }, { threshold: 0.35 });
    document.querySelectorAll('.xg-shot--anim img').forEach(function (img) { seen.observe(img); });
  }
})();
