/* Tab icon by browser theme (2026-10-09, owner: the navy tile hides the "S" in a dark tab bar).
   The HTML links the navy tile (/favicon.ico, favicon-192.png): search engines read those and never run this.
   In the browser the icon becomes the bare "S": white for a dark theme, black for a light one, and follows
   theme changes. Files: scripts/build_favicons.py. Loaded in <head> right after the icon links. */
(function () {
  'use strict';
  var query = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
  function apply() {
    var dark = !query || query.matches;
    var href = '/static/img/favicon/tab-' + (dark ? 'dark' : 'light') + '.png?v=20261009-fav1';
    var links = document.querySelectorAll('link[rel="icon"]');
    for (var i = 0; i < links.length; i++) links[i].parentNode.removeChild(links[i]);
    var link = document.createElement('link');
    link.rel = 'icon';
    link.type = 'image/png';
    link.sizes = '64x64';
    link.href = href;
    document.head.appendChild(link);
  }
  try {
    apply();
    if (query) {
      if (query.addEventListener) query.addEventListener('change', apply);
      else if (query.addListener) query.addListener(apply);
    }
  } catch (e) {}
})();
