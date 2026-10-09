/* Admin console: community Info box templates (2026-10-09). Anyone signed in can publish a template on the
   Info box tab; until now the owner could only hide one by id. Here: every template with its author and full
   text (shown as plain escaped BBCode, never rendered), search, hide and bring back.
   Server: GET /api/admin/control/infobox, POST /infobox/{id}/restore (routers/admin.py),
   DELETE /api/admin/control/infobox/{id} (routers/infobox.py). No localStorage/sessionStorage (admin rule). */
(function () {
  'use strict';
  var host, api, toast, items = [], total = 0, counts = {}, newWeek = 0;
  var filters = { status: 'published', q: '' };
  var CATEGORY = { about: 'О себе', frames: 'Рамки', games: 'Игры', quotes: 'Цитаты', art: 'Арт', other: 'Другое' };
  var esc = function (v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  var when = function (ts) { return ts ? new Date(Number(ts) * 1000).toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' }) : '—'; };
  var $ = function (sel) { return host.querySelector(sel); };

  function card(t) {
    var hidden = t.status === 'hidden';
    return '<article class="ibx-admin-card' + (hidden ? ' is-hidden' : '') + '">' +
      '<header><div><b>' + esc(t.title) + '</b><span class="cell-sub">' + esc(CATEGORY[t.category] || t.category) + ' · ' +
      esc(t.chars) + ' символов · ' + esc(t.lines) + ' строк · взяли ' + esc(t.uses) + ' раз</span></div>' +
      (hidden ? '<span class="tag tag--danger">СКРЫТ</span>' : '<span class="tag tag--success">ОПУБЛИКОВАН</span>') + '</header>' +
      '<pre class="ibx-admin-card__body">' + esc(t.body) + '</pre>' +
      '<footer><span><button type="button" class="link-button" data-user-detail="' + esc(t.user_id) + '">' + esc(t.author) + '</button>' +
      '<span class="cell-sub">' + when(t.created_at) + '</span></span>' +
      (hidden ? '<button type="button" class="mini-button" data-ibx-restore="' + esc(t.id) + '">Вернуть в галерею</button>' :
        '<button type="button" class="mini-button mini-button--danger" data-ibx-hide="' + esc(t.id) + '">Скрыть</button>') +
      '</footer></article>';
  }
  function render() {
    var tabs = [['published', 'Опубликованы · ' + (counts.published || 0)], ['hidden', 'Скрыты · ' + (counts.hidden || 0)], ['all', 'Все']];
    host.innerHTML =
      '<article class="panel panel--toolbar"><div><p class="overline">СООБЩЕСТВО</p><h2>Шаблоны пользователей</h2>' +
      '<p class="muted">Новых за 7 дней: ' + newWeek + '. Автор при публикации подтверждает, что текст его. Скрытый шаблон пропадает из галереи на вкладке Info box, но остаётся здесь: его можно вернуть. Текст показан как есть, без отрисовки BBCode.</p></div>' +
      '<form data-ibx-search><input type="search" name="q" value="' + esc(filters.q) + '" placeholder="Название, текст, автор"><button class="button">Найти</button></form></article>' +
      '<div class="jobs-toolbar"><div class="segmented" role="group">' + tabs.map(function (tab) {
        return '<button type="button" data-ibx-status="' + tab[0] + '" class="' + (filters.status === tab[0] ? 'is-active' : '') + '">' + esc(tab[1]) + '</button>';
      }).join('') + '</div></div>' +
      (items.length ? '<div class="ibx-admin-grid">' + items.map(card).join('') + '</div>' : '<p class="empty-state">Шаблонов нет</p>') +
      (items.length < total ? '<div class="pager"><button type="button" data-ibx-more>Показать ещё (' + (total - items.length) + ')</button></div>' : '');
  }
  function load(more) {
    var query = new URLSearchParams({ status: filters.status, q: filters.q, offset: more ? items.length : 0 });
    return api('/infobox?' + query).then(function (d) {
      items = more ? items.concat(d.items) : d.items;
      total = d.total; counts = d.counts || {}; newWeek = d.new_week || 0;
      render();
    });
  }
  function reload(more) { load(more).catch(function (e) { toast(e.message, true); }); }
  function wire() {
    host.addEventListener('click', function (event) {
      var t = event.target, button;
      if ((button = t.closest('[data-ibx-status]'))) { filters.status = button.dataset.ibxStatus; return reload(); }
      if (t.closest('[data-ibx-more]')) return reload(true);
      if ((button = t.closest('[data-ibx-hide]'))) {
        if (button.dataset.confirm !== '1') { button.dataset.confirm = '1'; button.textContent = 'Точно скрыть?'; return; }
        button.disabled = true;
        return api('/infobox/' + encodeURIComponent(button.dataset.ibxHide), { method: 'DELETE' })
          .then(function () { toast('Шаблон скрыт из галереи'); return load(); })
          .catch(function (e) { toast(e.message, true); button.disabled = false; });
      }
      if ((button = t.closest('[data-ibx-restore]'))) {
        button.disabled = true;
        return api('/infobox/' + encodeURIComponent(button.dataset.ibxRestore) + '/restore', { method: 'POST', body: '{}' })
          .then(function () { toast('Шаблон снова в галерее'); return load(); })
          .catch(function (e) { toast(e.message, true); button.disabled = false; });
      }
    });
    host.addEventListener('submit', function (event) {
      if (!event.target.matches('[data-ibx-search]')) return;
      event.preventDefault();
      filters.q = event.target.q.value.trim();
      reload();
    });
  }

  window.SMAdminInfobox = {
    load: function (apiFn, toastFn) {
      api = apiFn; toast = toastFn;
      if (!host) { host = document.getElementById('infoboxAdmin'); if (!host) return Promise.resolve(); wire(); }
      return load();
    }
  };
})();
