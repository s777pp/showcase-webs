(function () {
  'use strict';
  const loaded = new Map();
  const scripts = new Map();
  const groups = {
    assets: ['/static/js/media-assets.js?v=20260916a'],
    jobs: ['/static/js/job-center.js?v=20260922-release'],
    builder: [
      '/static/js/builder-history.js?v=20260910-finish1',
      '/static/js/builder-motion-copy.js?v=20260913-motion1',
      '/static/js/builder-motion.js?v=20260913-motion1',
      '/static/js/showcase-builder.js?v=20260923-gallery1'
    ],
    dna: ['/static/js/steam-dna.js?v=20260912-exp7'],
    loop: ['/static/js/builder-motion-copy.js?v=20260913-motion1','/static/js/seamless-loop.js?v=20260913-motion1']
  };

  function script(src) {
    if (scripts.has(src)) return scripts.get(src);
    const pending = new Promise(function (resolve, reject) {
      const node = document.createElement('script');
      node.src = src; node.async = false; node.onload = resolve;
      node.onerror = function (event) { scripts.delete(src); node.remove(); reject(event); };
      document.body.appendChild(node);
    });
    scripts.set(src, pending);
    return pending;
  }
  function load(name) {
    if (loaded.has(name)) return loaded.get(name);
    const promise = (groups[name] || []).reduce(function (chain, src) {
      return chain.then(function () { return script(src); });
    }, Promise.resolve());
    const retryable = promise.catch(function (error) { loaded.delete(name); throw error; });
    loaded.set(name, retryable);
    return retryable;
  }
  window.SMToolLoader = { load: load };

  function localizeLaunchers() {
    const language = window.SMLang ? SMLang.get() : 'en';
    const words = {
      en:['Jobs','My media · upload once','Library','My media'], ru:['Задачи','Мои файлы · одна загрузка','Медиатека','Мои файлы'],
      de:['Aufgaben','Meine Medien · einmal hochladen','Mediathek','Meine Medien'], tr:['Görevler','Medyalarım · bir kez yükle','Medya','Medyalarım'],
      fr:['Tâches','Mes médias · un seul envoi','Médiathèque','Mes médias'], uk:['Завдання','Мої файли · одне завантаження','Медіатека','Мої файли'],
      es:['Tareas','Mis archivos · una sola carga','Biblioteca','Mis archivos'], pt:['Tarefas','Meus arquivos · um só envio','Biblioteca','Meus arquivos']
    }[language] || ['Jobs','My media · upload once','Library','My media'];
    document.querySelectorAll('[data-job-center]').forEach(function(node){node.textContent=words[0];});
    document.querySelectorAll('[data-asset-library]').forEach(function(node){
      node.textContent=node.classList.contains('asset-library-open')?(node.dataset.assetTarget?words[3]:words[1]):words[2];
    });
  }
  localizeLaunchers();
  window.addEventListener('sm:langchange', localizeLaunchers);

  document.addEventListener('click', function (event) {
    const jobButton = event.target.closest && event.target.closest('[data-job-center]');
    if (jobButton) { load('jobs').then(function () { window.SMJobCenter && window.SMJobCenter.open(); }); return; }
    const assetButton = event.target.closest && event.target.closest('[data-asset-library]');
    if (assetButton) { load('assets').then(function () { window.SMMediaAssets && window.SMMediaAssets.openLibrary(assetButton.getAttribute('data-asset-target') || 'process'); }); return; }
    const tool = event.target.closest && event.target.closest('[data-open-tool], [data-tab]');
    const name = tool && (tool.getAttribute('data-open-tool') || tool.getAttribute('data-tab'));
    const lazyGroup = name === 'builder' || name === 'projects' ? 'builder' : name === 'dna' ? 'dna' : '';
    if (lazyGroup && tool && !tool.dataset.lazyReady) {
      event.preventDefault();
      event.stopImmediatePropagation();
      load(lazyGroup).then(function () {
        tool.dataset.lazyReady = '1';
        tool.click();
      }).catch(function () { tool.dataset.lazyReady = ''; });
      return;
    }
    if (name === 'loop') load('loop');
  }, true);
})();
