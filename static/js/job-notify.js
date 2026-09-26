/* Browser notification when a job finishes while the tab is in the background.
   Upscale and long GIF jobs take minutes; people switch tabs and forget.
   Permission is asked once, on the first click of a start button (a user gesture). */
(function () {
  'use strict';
  if (!('Notification' in window)) return;
  var START_BUTTONS = '#btnRun,#processDockRun,#btnCompose,#btnUpscale,#loopRun,#workshopCreate';
  var ASKED = 'sm_notify_asked_v1';
  var LANGS = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'];
  var WORDS = {
    done: ['Your file is ready', 'Файл готов', 'Deine Datei ist fertig', 'Dosyan hazır', 'Votre fichier est prêt', 'Файл готовий', 'Tu archivo está listo', 'Seu arquivo está pronto'],
    failed: ['The job could not finish', 'Задание не удалось выполнить', 'Der Auftrag konnte nicht abgeschlossen werden', 'Görev tamamlanamadı', 'La tâche n’a pas pu se terminer', 'Завдання не вдалося виконати', 'La tarea no pudo terminar', 'A tarefa não pôde ser concluída'],
    body: ['Open Showcase Maker to download it.', 'Открой Showcase Maker, чтобы скачать.', 'Öffne Showcase Maker, um sie herunterzuladen.', 'İndirmek için Showcase Maker’ı aç.', 'Ouvrez Showcase Maker pour le télécharger.', 'Відкрий Showcase Maker, щоб завантажити.', 'Abre Showcase Maker para descargarlo.', 'Abra o Showcase Maker para baixar.'],
    bodyFailed: ['Open Showcase Maker to see what happened.', 'Открой Showcase Maker, чтобы посмотреть причину.', 'Öffne Showcase Maker, um den Grund zu sehen.', 'Nedenini görmek için Showcase Maker’ı aç.', 'Ouvrez Showcase Maker pour voir la raison.', 'Відкрий Showcase Maker, щоб побачити причину.', 'Abre Showcase Maker para ver qué pasó.', 'Abra o Showcase Maker para ver o motivo.']
  };
  function word(key) {
    var lang = (window.SMLang && SMLang.get && SMLang.get()) || 'en';
    return WORDS[key][Math.max(0, LANGS.indexOf(lang))] || WORDS[key][0];
  }
  function asked() { try { return localStorage.getItem(ASKED) === '1'; } catch (_) { return true; } }
  function markAsked() { try { localStorage.setItem(ASKED, '1'); } catch (_) {} }

  var known = {}, timer = 0, idleRounds = 0;
  function headers() { return window.__smHeaders ? window.__smHeaders() : {}; }
  function notify(job) {
    if (Notification.permission !== 'granted' || !document.hidden) return;
    var ok = job.status === 'done';
    try {
      var note = new Notification(word(ok ? 'done' : 'failed'), { body: word(ok ? 'body' : 'bodyFailed'), icon: '/static/icon-256.png', tag: 'sm-job-' + job.id });
      note.onclick = function () { window.focus(); note.close(); };
    } catch (_) {}
  }
  async function poll() {
    timer = 0;
    var active = 0;
    try {
      var response = await fetch('/api/jobs?limit=10', { credentials: 'include', cache: 'no-store', headers: headers() });
      var data = await response.json();
      (data.jobs || []).forEach(function (job) {
        var before = known[job.id];
        if ((before === 'queued' || before === 'running') && (job.status === 'done' || job.status === 'error')) notify(job);
        known[job.id] = job.status;
        if (job.status === 'queued' || job.status === 'running') active += 1;
      });
    } catch (_) { active = 1; }
    // Keep watching while something runs; allow a few idle rounds for a job that is still being uploaded.
    idleRounds = active ? 0 : idleRounds + 1;
    if (active || idleRounds < 6) timer = setTimeout(poll, 5000);
  }
  function watch() { idleRounds = 0; if (!timer) timer = setTimeout(poll, 1500); }

  document.addEventListener('click', function (event) {
    if (!event.target.closest || !event.target.closest(START_BUTTONS)) return;
    if (Notification.permission === 'default' && !asked()) {
      markAsked();
      try { Notification.requestPermission(); } catch (_) {}
    }
    watch();
  }, true);
})();
