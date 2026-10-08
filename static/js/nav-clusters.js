/* Tools strip in three labelled clusters (owner, 2026-10-08: "people must see every tool, and it must look good").
   Every tool stays a top-level tab (the owner's rule since 2026-09-26: nothing hidden in drop-downs except the
   profile group of nav-groups.js). This script only inserts a small caption before the first tool of each cluster;
   the buttons are not moved, so every handler in app.js / tool-loader.js keeps working. Styles: css/nav-clusters.css.
   Copy: 8 languages in the order of LANGS. */
(function () {
  'use strict';
  var nav = document.getElementById('nav');
  if (!nav || nav.dataset.clusters) return;
  nav.dataset.clusters = '1';
  var LANGS = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'];
  var CLUSTERS = [
    { id: 'create', first: 'process', label: ['Create', 'Создать', 'Erstellen', 'Oluştur', 'Créer', 'Створити', 'Crear', 'Criar'] },
    { id: 'files', first: 'download', label: ['Files', 'Файлы', 'Dateien', 'Dosyalar', 'Fichiers', 'Файли', 'Archivos', 'Arquivos'] },
    { id: 'profile', first: 'infobox', label: ['Profile', 'Профиль', 'Profil', 'Profil', 'Profil', 'Профіль', 'Perfil', 'Perfil'] }
  ];
  function lang() { return (window.SMLang && SMLang.get && SMLang.get()) || document.documentElement.lang || 'en'; }
  function pick(list) { return list[Math.max(0, LANGS.indexOf(lang()))] || list[0]; }
  var marks = CLUSTERS.map(function (cluster) {
    var first = nav.querySelector(':scope > button[data-tab="' + cluster.first + '"]');
    if (!first) return null;
    var mark = document.createElement('span');
    mark.className = 'nav-cluster nav-cluster--' + cluster.id;
    mark.setAttribute('aria-hidden', 'true');
    nav.insertBefore(mark, first);
    return { mark: mark, cluster: cluster };
  }).filter(Boolean);
  function paint() { marks.forEach(function (m) { m.mark.textContent = pick(m.cluster.label); }); }
  paint();
  window.addEventListener('sm:langchange', paint);
})();
