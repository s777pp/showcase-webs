/* Admin console: News & updates (2026-10-01). analytics-dashboard.js calls
   SMAdminNews.load(api, toast) when the "Новости" view opens; api() carries the admin
   session and CSRF header. Posts are written in Russian and English; other languages
   show the English text. */
(function () {
  'use strict';
  var CATS = { news: 'Новости', update: 'Обновление', feature: 'Новая функция', announcement: 'Анонс', event: 'Событие', maintenance: 'Техработы', promo: 'Промо' };
  var host, api, toast, items = [], editing = null, tab = 'ru';
  var esc = function (v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  var date = function (ts) { return ts ? new Date(Number(ts) * 1000).toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' }) : '—'; };
  function blank() { return { id: '', category: 'update', status: 'draft', pinned: false, notify: true, cover_url: '', published_at: null,
    title_ru: '', title_en: '', summary_ru: '', summary_en: '', body_ru: '', body_en: '' }; }
  // A date more than an hour in the past = archive post (server: news.BACKDATE_GRACE): no bell, no dot.
  function backdated(ts) { return !!ts && Number(ts) < Date.now() / 1000 - 3600; }
  function localInput(ts) { if (!ts) return ''; var d = new Date(Number(ts) * 1000); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 16); }

  function renderList() {
    var rows = items.length ? items.map(function (n) {
      var state = n.status === 'published' ? (Number(n.published_at) > Date.now() / 1000 ? '<span class="tag tag--warn">ПО РАСПИСАНИЮ</span>' : '<span class="tag tag--success">ОПУБЛИКОВАНО</span>') : '<span class="tag">ЧЕРНОВИК</span>';
      if (n.published_at && n.created_at && Number(n.published_at) < Number(n.created_at) - 3600) state += ' <span class="tag">ЗАДНИМ ЧИСЛОМ</span>';
      return '<tr><td><div class="table-primary">' + esc(n.title_ru || n.title_en) + (n.pinned ? ' 📌' : '') + '</div><div class="cell-sub">/news/' + esc(n.slug) + '</div></td>' +
        '<td>' + esc(CATS[n.category] || n.category) + '</td><td>' + state + (n.notify ? '' : ' <span class="cell-sub">без уведомления</span>') + '</td>' +
        '<td>' + date(n.published_at || n.created_at) + '</td><td class="an-actions"><button class="mini-button" data-an-edit="' + esc(n.id) + '">Изменить</button>' +
        (n.status === 'published' ? '<a class="mini-button" target="_blank" rel="noopener" href="/ru/news/' + esc(n.slug) + '">Открыть</a>' : '') +
        '<button class="mini-button mini-button--danger" data-an-delete="' + esc(n.id) + '">Удалить</button></td></tr>';
    }).join('') : '<tr><td colspan="5" class="empty-state">Новостей пока нет. Нажми «Новая новость».</td></tr>';
    return '<article class="panel"><div class="panel-head"><div><p class="overline">НОВОСТИ И ОБНОВЛЕНИЯ</p><h2>Публикации</h2>' +
      '<p class="muted">Публикация с галочкой «Уведомить» попадает в колокольчик всем пользователям и ставит точку на пункте «Новости».</p></div>' +
      '<button class="button" data-an-new>+ Новая новость</button></div><div class="table-wrap"><table><thead><tr><th>Заголовок</th><th>Категория</th><th>Статус</th><th>Дата</th><th></th></tr></thead><tbody>' + rows + '</tbody></table></div></article>';
  }
  function renderEditor() {
    var n = editing, cats = Object.keys(CATS).map(function (k) { return '<option value="' + k + '"' + (n.category === k ? ' selected' : '') + '>' + CATS[k] + '</option>'; }).join('');
    var lang = tab;
    return '<form class="panel form-panel an-form" data-an-form>' +
      '<div class="panel-head"><div><p class="overline">' + (n.id ? 'РЕДАКТИРОВАНИЕ' : 'НОВАЯ ПУБЛИКАЦИЯ') + '</p><h2>' + esc(n['title_' + lang] || 'Новость') + '</h2></div>' +
      '<button type="button" class="button button--ghost" data-an-close>← К списку</button></div>' +
      '<div class="an-grid"><label>Категория<select name="category">' + cats + '</select></label>' +
      '<label>Статус<select name="status"><option value="draft"' + (n.status === 'draft' ? ' selected' : '') + '>Черновик</option><option value="published"' + (n.status === 'published' ? ' selected' : '') + '>Опубликовать</option></select></label>' +
      '<label>Дата публикации <small>(пусто = сейчас; будущая = по расписанию; прошлая = задним числом)</small><input type="datetime-local" name="published_at" value="' + localInput(n.published_at) + '"></label>' +
      '<div class="an-checks"><label class="switch-row"><input type="checkbox" name="pinned"' + (n.pinned ? ' checked' : '') + '> Закрепить как главную</label>' +
      '<label class="switch-row"><input type="checkbox" name="notify"' + (n.notify ? ' checked' : '') + '> Уведомить пользователей (колокольчик)</label>' +
      '<p class="muted an-backdate" style="margin:0;font-size:12px" data-an-backdate hidden>Задним числом: встанет в ленту на эту дату, без колокольчика и точки.</p></div></div>' +
      '<div class="an-cover"><div class="an-cover__img">' + (n.cover_url ? '<img src="' + esc(n.cover_url) + '" alt="">' : '<span>Обложки нет</span>') + '</div>' +
      '<div><b>Обложка</b><p class="muted">16:9, от 1280 px в ширину. Картинка сохранится в WebP.</p><label class="button button--ghost an-file">Загрузить картинку<input type="file" accept="image/*" data-an-cover hidden></label>' +
      (n.cover_url ? ' <button type="button" class="text-button" data-an-cover-remove>Убрать</button>' : '') + '</div></div>' +
      '<div class="segmented an-tabs"><button type="button" data-an-tab="ru" class="' + (lang === 'ru' ? 'is-active' : '') + '">Русский</button><button type="button" data-an-tab="en" class="' + (lang === 'en' ? 'is-active' : '') + '">English (для всех остальных языков)</button></div>' +
      '<label>Заголовок<input name="title" maxlength="160" value="' + esc(n['title_' + lang]) + '" placeholder="' + (lang === 'ru' ? 'Showcase Maker v1.8 — новый редактор' : 'Showcase Maker v1.8 — new editor') + '"></label>' +
      '<label>Краткое описание <small>(под заголовком и в карточке, до 300 символов)</small><textarea name="summary" rows="2" maxlength="300">' + esc(n['summary_' + lang]) + '</textarea></label>' +
      '<div class="an-editor"><div class="an-toolbar">' +
        '<button type="button" data-an-cmd="bold"><b>B</b></button><button type="button" data-an-cmd="italic"><i>I</i></button><button type="button" data-an-cmd="underline"><u>U</u></button>' +
        '<button type="button" data-an-block="h2">H2</button><button type="button" data-an-block="h3">H3</button><button type="button" data-an-block="p">¶</button>' +
        '<button type="button" data-an-cmd="insertUnorderedList">• Список</button><button type="button" data-an-block="blockquote">❝ Цитата</button>' +
        '<button type="button" data-an-link>🔗 Ссылка</button><label class="an-file">🖼 Картинка<input type="file" accept="image/*" data-an-inline hidden></label>' +
        '<button type="button" data-an-cmd="insertHorizontalRule">— Линия</button><button type="button" data-an-cmd="removeFormat">Tx</button></div>' +
        '<div class="an-body" contenteditable="true" data-an-body>' + (n['body_' + lang] || '') + '</div></div>' +
      '<div class="actions"><button class="button" type="submit">Сохранить</button><span class="form-status" data-an-status></span></div></form>';
  }
  function paint() { host.innerHTML = editing ? renderEditor() : renderList(); syncBackdate(); }
  // Past date chosen in the editor: switch the bell off and explain why (the server enforces it too).
  // An existing post whose saved date is unchanged keeps its own setting.
  function syncBackdate() {
    var form = host.querySelector('[data-an-form]'); if (!form) return;
    var value = form.published_at.value ? new Date(form.published_at.value).getTime() / 1000 : null;
    var past = backdated(value), moved = !editing.id || Math.abs((Number(editing.published_at) || 0) - (value || 0)) > 60;
    if (past && moved) form.notify.checked = false;
    form.notify.disabled = past && moved;
    form.querySelector('[data-an-backdate]').hidden = !past;
  }
  function collect() {
    var form = host.querySelector('[data-an-form]'); if (!form || !editing) return;
    editing.category = form.category.value; editing.status = form.status.value; editing.pinned = form.pinned.checked; editing.notify = form.notify.checked;
    editing.published_at = form.published_at.value ? new Date(form.published_at.value).getTime() / 1000 : null;
    editing['title_' + tab] = form.title.value; editing['summary_' + tab] = form.summary.value;
    editing['body_' + tab] = host.querySelector('[data-an-body]').innerHTML;
  }
  function upload(file) {
    var data = new FormData(); data.append('file', file);
    return api('/news/image', { method: 'POST', body: data }).then(function (r) { return r.url; });
  }
  function load() {
    return api('/news').then(function (data) { items = data.items || []; paint(); });
  }

  function wire() {
    host.addEventListener('click', function (event) {
      var t = event.target;
      if (t.closest('[data-an-new]')) { editing = blank(); tab = 'ru'; paint(); return; }
      if (t.closest('[data-an-close]')) { editing = null; paint(); return; }
      var edit = t.closest('[data-an-edit]');
      if (edit) { editing = Object.assign({}, items.find(function (n) { return n.id === edit.dataset.anEdit; })); tab = 'ru'; paint(); return; }
      var del = t.closest('[data-an-delete]');
      if (del) {
        if (del.dataset.confirm !== '1') { del.dataset.confirm = '1'; del.textContent = 'Точно удалить?'; return; }
        api('/news/' + encodeURIComponent(del.dataset.anDelete), { method: 'DELETE' }).then(function () { toast('Новость удалена'); load(); }).catch(function (e) { toast(e.message, true); });
        return;
      }
      var tabButton = t.closest('[data-an-tab]');
      if (tabButton) { collect(); tab = tabButton.dataset.anTab; paint(); return; }
      if (t.closest('[data-an-cover-remove]')) { collect(); editing.cover_url = ''; paint(); return; }
      var cmd = t.closest('[data-an-cmd]');
      if (cmd) { event.preventDefault(); document.execCommand(cmd.dataset.anCmd); return; }
      var block = t.closest('[data-an-block]');
      if (block) { event.preventDefault(); document.execCommand('formatBlock', false, block.dataset.anBlock); return; }
      if (t.closest('[data-an-link]')) {
        event.preventDefault();
        var sel = window.getSelection(); if (!sel || sel.isCollapsed) { toast('Сначала выдели текст для ссылки', true); return; }
        var range = sel.getRangeAt(0), box = host.querySelector('.an-toolbar'), row = document.createElement('div');
        row.className = 'an-linkrow'; row.innerHTML = '<input placeholder="https://… или /app" data-an-url><button type="button" class="mini-button" data-an-url-ok>Вставить</button>';
        box.after(row); row.querySelector('input').focus();
        row.querySelector('[data-an-url-ok]').addEventListener('click', function () {
          var href = row.querySelector('input').value.trim(); row.remove();
          if (!href) return; sel.removeAllRanges(); sel.addRange(range); document.execCommand('createLink', false, href);
        });
      }
    });
    host.addEventListener('mousedown', function (event) { if (event.target.closest('[data-an-cmd],[data-an-block],[data-an-link]')) event.preventDefault(); });
    host.addEventListener('change', function (event) {
      if (event.target.name === 'published_at') { syncBackdate(); return; }
      var cover = event.target.closest('[data-an-cover]');
      if (cover && cover.files[0]) { collect(); toast('Загружаем обложку…'); upload(cover.files[0]).then(function (url) { editing.cover_url = url; paint(); toast('Обложка загружена'); }).catch(function (e) { toast(e.message, true); }); return; }
      var inline = event.target.closest('[data-an-inline]');
      if (inline && inline.files[0]) {
        var body = host.querySelector('[data-an-body]'), sel = window.getSelection(), range = sel && sel.rangeCount && body.contains(sel.anchorNode) ? sel.getRangeAt(0) : null;
        toast('Загружаем картинку…');
        upload(inline.files[0]).then(function (url) {
          body.focus(); if (range) { sel.removeAllRanges(); sel.addRange(range); }
          document.execCommand('insertHTML', false, '<img src="' + esc(url) + '" alt="">'); toast('Картинка вставлена');
        }).catch(function (e) { toast(e.message, true); });
      }
    });
    host.addEventListener('submit', function (event) {
      if (!event.target.closest('[data-an-form]')) return;
      event.preventDefault(); collect();
      var status = host.querySelector('[data-an-status]'); status.textContent = 'Сохраняем…';
      api('/news', { method: 'POST', body: JSON.stringify(editing) }).then(function (r) {
        editing.id = r.id; editing.slug = r.slug; status.textContent = 'Сохранено'; toast('Новость сохранена');
        return api('/news').then(function (data) { items = data.items || []; });
      }).catch(function (e) { status.textContent = e.message; toast(e.message, true); });
    });
  }

  window.SMAdminNews = {
    load: function (apiFn, toastFn) {
      api = apiFn; toast = toastFn; host = document.getElementById('newsAdmin');
      if (!host) return Promise.resolve();
      if (!host.dataset.wired) { host.dataset.wired = '1'; wire(); }
      editing = null; return load();
    }
  };
})();
