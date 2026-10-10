/* "Change the design" for gallery works made in Create a design (owner, 2026-10-09: "liked the animation but want
   another background? another frame? let people change everything").
   Gallery page: the publish form gets "Project from Create a design" + "Let others change the design"
   (community-gallery.js appends SMGalleryRemix.append(fd)); a work with a project shows "Change the design", which
   opens /<lang>/app?remix=<id>. Tools page: ?remix=<id> loads the builder scripts, reads
   /api/gallery/works/<id>/remix and opens a copy as a new unsaved project (ShowcaseBuilder.loadProject).
   Server: smweb/gallery_remix.py. Copy: the keyed COPY dictionary below, 8 languages (scripts/check_i18n.js). */
(function () {
  'use strict';
  var COPY = {
    en: { publish: 'Publish to the gallery', publishHint: 'Share this design in the gallery: others can download it or open a copy and change it.',
      project: 'Project from Create a design (optional)', none: 'No project', hint: 'Attach the project you made this work in, and others can open a copy and change the background, frame, text and effects. Your work stays as it is.',
      allow: 'Let others change the design', empty: 'Save your design in Create a design first: it appears here.', login: 'Sign in to attach a project.',
      edit: 'Change the design', editHint: 'Open a copy in Create a design: change the background, frame, text and anything else.',
      loading: 'Opening the design…', failed: 'Could not open this design. Try again later.', copy: 'copy' },
    ru: { publish: 'Опубликовать в галерею', publishHint: 'Поделиться дизайном в галерее: его смогут скачать или открыть копию и изменить.',
      project: 'Проект из «Создать дизайн» (необязательно)', none: 'Без проекта', hint: 'Приложи проект, в котором сделана работа: другие смогут открыть его копию и поменять фон, рамку, текст и эффекты. Твоя работа при этом не меняется.',
      allow: 'Разрешить другим менять оформление', empty: 'Сначала сохрани дизайн в «Создать дизайн» — он появится здесь.', login: 'Войди, чтобы приложить проект.',
      edit: 'Изменить оформление', editHint: 'Открыть копию в «Создать дизайн»: поменять фон, рамку, текст и всё остальное.',
      loading: 'Открываем дизайн…', failed: 'Не получилось открыть этот дизайн. Попробуй позже.', copy: 'копия' },
    de: { publish: 'In der Galerie veröffentlichen', publishHint: 'Teile dieses Design in der Galerie: Andere können es herunterladen oder eine Kopie öffnen und ändern.',
      project: 'Projekt aus „Design erstellen“ (optional)', none: 'Kein Projekt', hint: 'Hänge das Projekt an, in dem die Arbeit entstanden ist: Andere können eine Kopie öffnen und Hintergrund, Rahmen, Text und Effekte ändern. Deine Arbeit bleibt unverändert.',
      allow: 'Anderen erlauben, das Design zu ändern', empty: 'Speichere dein Design zuerst in „Design erstellen“, dann erscheint es hier.', login: 'Melde dich an, um ein Projekt anzuhängen.',
      edit: 'Design ändern', editHint: 'Eine Kopie in „Design erstellen“ öffnen: Hintergrund, Rahmen, Text und alles andere ändern.',
      loading: 'Design wird geöffnet…', failed: 'Dieses Design konnte nicht geöffnet werden. Versuche es später.', copy: 'Kopie' },
    tr: { publish: 'Galeride yayınla', publishHint: 'Bu tasarımı galeride paylaş: başkaları indirebilir ya da bir kopyasını açıp değiştirebilir.',
      project: '“Tasarım oluştur” projesi (isteğe bağlı)', none: 'Proje yok', hint: 'Çalışmayı yaptığın projeyi ekle: başkaları bir kopyasını açıp arka planı, çerçeveyi, metni ve efektleri değiştirebilir. Senin çalışman olduğu gibi kalır.',
      allow: 'Başkalarının tasarımı değiştirmesine izin ver', empty: 'Önce tasarımını “Tasarım oluştur”da kaydet, burada görünür.', login: 'Proje eklemek için giriş yap.',
      edit: 'Tasarımı değiştir', editHint: '“Tasarım oluştur”da bir kopya aç: arka planı, çerçeveyi, metni ve her şeyi değiştir.',
      loading: 'Tasarım açılıyor…', failed: 'Bu tasarım açılamadı. Daha sonra tekrar dene.', copy: 'kopya' },
    fr: { publish: 'Publier dans la galerie', publishHint: 'Partage ce design dans la galerie : les autres pourront le télécharger ou en ouvrir une copie et la modifier.',
      project: 'Projet de « Créer un design » (facultatif)', none: 'Aucun projet', hint: 'Joins le projet dans lequel tu as fait cette œuvre : les autres pourront en ouvrir une copie et changer le fond, le cadre, le texte et les effets. Ton œuvre reste telle quelle.',
      allow: 'Autoriser les autres à changer le design', empty: 'Enregistre d’abord ton design dans « Créer un design » : il apparaîtra ici.', login: 'Connecte-toi pour joindre un projet.',
      edit: 'Changer le design', editHint: 'Ouvrir une copie dans « Créer un design » : changer le fond, le cadre, le texte et tout le reste.',
      loading: 'Ouverture du design…', failed: 'Impossible d’ouvrir ce design. Réessaie plus tard.', copy: 'copie' },
    uk: { publish: 'Опублікувати в галереї', publishHint: 'Поділитися дизайном у галереї: його зможуть завантажити або відкрити копію та змінити.',
      project: 'Проєкт зі «Створити дизайн» (необовʼязково)', none: 'Без проєкту', hint: 'Додай проєкт, у якому зроблено роботу: інші зможуть відкрити його копію й змінити фон, рамку, текст і ефекти. Твоя робота при цьому не змінюється.',
      allow: 'Дозволити іншим змінювати оформлення', empty: 'Спочатку збережи дизайн у «Створити дизайн» — він зʼявиться тут.', login: 'Увійди, щоб додати проєкт.',
      edit: 'Змінити оформлення', editHint: 'Відкрити копію у «Створити дизайн»: змінити фон, рамку, текст і все інше.',
      loading: 'Відкриваємо дизайн…', failed: 'Не вдалося відкрити цей дизайн. Спробуй пізніше.', copy: 'копія' },
    es: { publish: 'Publicar en la galería', publishHint: 'Comparte este diseño en la galería: otros podrán descargarlo o abrir una copia y cambiarla.',
      project: 'Proyecto de «Crear un diseño» (opcional)', none: 'Sin proyecto', hint: 'Adjunta el proyecto con el que hiciste la obra: otros podrán abrir una copia y cambiar el fondo, el marco, el texto y los efectos. Tu obra no cambia.',
      allow: 'Permitir que otros cambien el diseño', empty: 'Primero guarda tu diseño en «Crear un diseño»: aparecerá aquí.', login: 'Inicia sesión para adjuntar un proyecto.',
      edit: 'Cambiar el diseño', editHint: 'Abrir una copia en «Crear un diseño»: cambia el fondo, el marco, el texto y todo lo demás.',
      loading: 'Abriendo el diseño…', failed: 'No se pudo abrir este diseño. Inténtalo más tarde.', copy: 'copia' },
    pt: { publish: 'Publicar na galeria', publishHint: 'Compartilhe este design na galeria: outras pessoas podem baixar ou abrir uma cópia e mudar.',
      project: 'Projeto do «Criar um design» (opcional)', none: 'Sem projeto', hint: 'Anexe o projeto em que você fez o trabalho: outras pessoas poderão abrir uma cópia e mudar o fundo, a moldura, o texto e os efeitos. Seu trabalho continua igual.',
      allow: 'Permitir que outros mudem o design', empty: 'Primeiro salve seu design no «Criar um design»: ele vai aparecer aqui.', login: 'Entre para anexar um projeto.',
      edit: 'Mudar o design', editHint: 'Abrir uma cópia no «Criar um design»: mudar o fundo, a moldura, o texto e todo o resto.',
      loading: 'Abrindo o design…', failed: 'Não foi possível abrir este design. Tente mais tarde.', copy: 'cópia' }
  };
  function lang() {
    var l = window.SMLang && SMLang.get ? SMLang.get() : (document.documentElement.lang || 'en');
    l = String(l).slice(0, 2);
    return COPY[l] ? l : 'en';
  }
  function t(key) { return (COPY[lang()] || COPY.en)[key] || COPY.en[key] || key; }
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function langPrefix() {
    var first = location.pathname.split('/')[1] || '';
    return COPY[first] ? '/' + first : '/' + lang();
  }

  // ================================================================ tools page: ?remix=<id> opens a copy in the Builder
  var params = new URLSearchParams(location.search);
  var remixId = params.get('remix');
  if (document.getElementById('showcaseBuilder') && /^\d{1,12}$/.test(remixId || '')) {
    var note = el('div', 'gremix-toast', t('loading'));
    document.body.append(note);
    var done = function (text) {
      note.textContent = text || ''; note.hidden = !text;
      if (text) setTimeout(function () { note.remove(); }, 5000); else note.remove();
      params.delete('remix');
      history.replaceState(null, '', location.pathname + (params.toString() ? '?' + params : '') + location.hash);
    };
    var loader = window.SMToolLoader ? SMToolLoader.load('builder') : Promise.resolve();
    Promise.all([loader, fetch('/api/gallery/works/' + remixId + '/remix', { credentials: 'same-origin' }).then(function (r) { return r.json(); })])
      .then(function (results) {
        var data = results[1];
        if (!data || !data.ok || !window.ShowcaseBuilder) throw new Error('remix');
        var name = (data.title || data.project.name || 'Showcase').slice(0, 64) + ' · ' + t('copy');
        if (!window.ShowcaseBuilder.loadProject(data.project, name)) throw new Error('remix');
        done('');
      })
      .catch(function () { done(t('failed')); });
  }

  // ---- "Publish to the gallery" next to "Save project" once the design has been saved (showcase-builder.js event)
  document.addEventListener('sm:builder-saved', function (event) {
    var id = event.detail && event.detail.id, save = document.getElementById('builderSave');
    if (!id || !save) return;
    var link = document.getElementById('builderPublishGallery');
    if (!link) { link = el('a', 'btn ghost gremix-publish'); link.id = 'builderPublishGallery'; save.after(link); }
    link.textContent = '🖼 ' + t('publish'); link.title = t('publishHint');
    link.href = langPrefix() + '/gallery?project=' + encodeURIComponent(id);
  });

  // ================================================================ gallery page
  var form = document.getElementById('publishForm');
  if (!form) return;
  var box = el('div', 'gremix-box');
  var label = el('label', 'gremix-field');
  var caption = el('span', '', '');
  var select = el('select'); select.id = 'publishProject';
  label.append(caption, select);
  var allowWrap = el('label', 'community-check gremix-allow');
  var allow = el('input'); allow.type = 'checkbox'; allow.id = 'publishRemix';
  var allowText = el('span', '', '');
  allowWrap.append(allow, allowText);
  var hint = el('small', 'gremix-hint', '');
  box.append(label, allowWrap, hint);
  var archiveField = document.getElementById('publishArchive');
  var anchor = archiveField ? archiveField.closest('label') : null;
  if (anchor) anchor.after(box); else form.querySelector('.community-publish__fields').prepend(box);
  var projects = [], wanted = params.get('project') || '';

  function paint() {
    caption.textContent = t('project'); allowText.textContent = t('allow');
    var current = select.value;
    select.replaceChildren();
    var none = el('option', '', t('none')); none.value = ''; select.append(none);
    projects.forEach(function (item) { var o = el('option', '', item.name || item.id); o.value = item.id; select.append(o); });
    select.value = projects.some(function (p) { return p.id === current; }) ? current : '';
    // Same default as picking the project by hand (the change handler below).
    if (wanted && projects.some(function (p) { return p.id === wanted; })) { select.value = wanted; allow.checked = true; wanted = ''; }
    allowWrap.hidden = !select.value;
    hint.textContent = projects.length ? t('hint') : (refresh.loggedOut ? t('login') : t('empty'));
  }
  function refresh() {
    return fetch('/api/builder/projects', { credentials: 'same-origin' }).then(function (r) {
      refresh.loggedOut = r.status === 401;
      return r.ok ? r.json() : { items: [] };
    }).then(function (data) { projects = (data && data.items) || []; paint(); }).catch(function () { paint(); });
  }
  select.addEventListener('change', function () { allow.checked = !!select.value; allowWrap.hidden = !select.value; });

  // ---- "Change the design" on a work that carries its project (community-gallery.js fires sm:gallery-detail)
  var edit = el('a', 'community-secondary gremix-edit');
  edit.hidden = true;
  var download = document.getElementById('detailDownload');
  if (download) download.parentNode.insertBefore(edit, download.nextSibling);
  document.addEventListener('sm:gallery-detail', function (event) {
    var item = event.detail || {};
    edit.hidden = !item.remix;
    edit.textContent = '🎨 ' + t('edit');
    edit.title = t('editHint');
    edit.href = langPrefix() + '/app?remix=' + encodeURIComponent(item.id);
  });

  window.SMGalleryRemix = {
    append: function (fd) {
      if (select.value && allow.checked) { fd.append('builder_project_id', select.value); fd.append('remix_allowed', 'true'); }
    },
    reset: function (editing) { box.hidden = !!editing; if (!editing) refresh(); },
    open: refresh
  };
  window.addEventListener('sm:langchange', paint);
  paint();
  if (params.get('project')) {
    // "Publish to the gallery" from Create a design: open the form with this project chosen.
    var open = document.getElementById('publishOpen');
    if (open) setTimeout(function () { open.click(); }, 300);
  }
})();
