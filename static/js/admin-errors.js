/* Admin console: server errors (2026-10-01). analytics-dashboard.js calls
   SMAdminErrors.load(api, toast) when "Ошибки сайта" opens and SMAdminErrors.badge(api)
   with the overview. Rows come from smweb/error_log.py: the same bug is one row with a
   counter; "Решено" hides it until it happens again (then the bot reports it again).
   No localStorage/sessionStorage here (admin rule). */
(function () {
  'use strict';
  var host, api, toast, status = 'open', data = { items: [], open: 0, recent: 0 }, openId = '';
  var esc = function (v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  var when = function (ts) { return ts ? new Date(Number(ts) * 1000).toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' }) : '—'; };
  var SOURCE = { app: 'Сайт', worker: 'Обработчик' };
  var KIND = { exception: 'Исключение', log: 'Запись в логе', http: 'Ответ 5xx' };

  function paintBadge(n) {
    var el = document.getElementById('errorsNavCount');
    if (el) el.textContent = n ? String(n) : '';
  }
  function row(e) {
    var where = [e.method, e.path].filter(Boolean).join(' ') || '—';
    var open = e.id === openId;
    var head = '<tr class="err-row' + (open ? ' is-open' : '') + '" data-err-toggle="' + esc(e.id) + '">' +
      '<td><div class="table-primary">' + esc(e.title || 'Без описания') + '</div><div class="cell-sub">' + esc(e.location || KIND[e.kind] || '') + '</div></td>' +
      '<td>' + esc(SOURCE[e.source] || e.source || '—') + '<div class="cell-sub">' + esc(where) + '</div></td>' +
      '<td><b>' + esc(e.count) + '</b></td>' +
      '<td>' + when(e.last_seen) + (e.resolved_at ? '<div class="cell-sub">решено ' + when(e.resolved_at) + '</div>' : '') + '</td></tr>';
    if (!open) return head;
    var detail = '<tr class="err-detail"><td colspan="4"><dl>' +
      '<dt>Тип</dt><dd>' + esc(KIND[e.kind] || e.kind) + (e.status ? ' · HTTP ' + esc(e.status) : '') + '</dd>' +
      '<dt>Впервые</dt><dd>' + when(e.first_seen) + '</dd><dt>Последний раз</dt><dd>' + when(e.last_seen) + '</dd>' +
      (e.request_id ? '<dt>ID запроса</dt><dd><code>' + esc(e.request_id) + '</code></dd>' : '') +
      (e.logger ? '<dt>Логгер</dt><dd><code>' + esc(e.logger) + '</code></dd>' : '') +
      (e.message && e.message !== e.title ? '<dt>Сообщение</dt><dd>' + esc(e.message) + '</dd>' : '') + '</dl>' +
      (e.trace ? '<pre class="err-trace">' + esc(e.trace) + '</pre>' : '<p class="muted">Трассировки нет: сервер вернул ошибку без записи в логе. Ищи по адресу и ID запроса.</p>') +
      '<div class="actions">' + (e.resolved_at ? '' : '<button class="mini-button" data-err-resolve="' + esc(e.id) + '">Решено</button>') +
      '<button class="mini-button" data-err-copy="' + esc(e.id) + '">Скопировать для разработчика</button></div></td></tr>';
    return head + detail;
  }
  function render() {
    var tabs = [['open', 'Открытые'], ['resolved', 'Решённые'], ['all', 'Все']].map(function (t) {
      return '<button type="button" data-err-status="' + t[0] + '" class="' + (status === t[0] ? 'is-active' : '') + '">' + t[1] + '</button>';
    }).join('');
    var rows = data.items.length ? data.items.map(row).join('') :
      '<tr><td colspan="4" class="empty-state">' + (status === 'open' ? 'Открытых ошибок нет 🎉' : 'Здесь пусто') + '</td></tr>';
    host.innerHTML = '<article class="panel"><div class="panel-head"><div><p class="overline">ДИАГНОСТИКА</p><h2>Ошибки сайта</h2>' +
      '<p class="muted">Ошибки сайта и обработчика сохраняются здесь и не пропадают при обновлении. Одинаковые собираются в одну строку со счётчиком. ' +
      '«Решено» прячет ошибку; если она повторится, вернётся сюда и снова придёт в бота. Хранится 14 дней.</p></div>' +
      '<div class="err-stats"><div><strong>' + esc(data.open) + '</strong><span>открытых</span></div><div><strong>' + esc(data.recent) + '</strong><span>раз за сутки</span></div></div></div>' +
      '<div class="err-toolbar"><div class="segmented">' + tabs + '</div><div class="actions">' +
      (status !== 'resolved' && data.open ? '<button class="button button--ghost" data-err-resolve-all>Отметить все решёнными</button>' : '') +
      (status !== 'open' ? '<button class="button button--ghost mini-button--danger" data-err-purge>Удалить решённые</button>' : '') + '</div></div>' +
      '<div class="table-wrap"><table class="err-table"><thead><tr><th>Ошибка</th><th>Где</th><th>Раз</th><th>Последний раз</th></tr></thead><tbody>' + rows + '</tbody></table></div></article>';
  }
  function load() {
    return api('/errors?status=' + encodeURIComponent(status)).then(function (d) { data = d; paintBadge(d.open); render(); });
  }
  function wire() {
    host.addEventListener('click', function (event) {
      var t = event.target;
      var tab = t.closest('[data-err-status]');
      if (tab) { status = tab.dataset.errStatus; openId = ''; load().catch(function (e) { toast(e.message, true); }); return; }
      var resolve = t.closest('[data-err-resolve]');
      if (resolve) { api('/errors/' + encodeURIComponent(resolve.dataset.errResolve) + '/resolve', { method: 'POST', body: '{}' }).then(function () { toast('Отмечено как решённое'); openId = ''; return load(); }).catch(function (e) { toast(e.message, true); }); return; }
      if (t.closest('[data-err-resolve-all]')) { api('/errors/resolve-all', { method: 'POST', body: '{}' }).then(function (r) { toast('Решено: ' + r.count); return load(); }).catch(function (e) { toast(e.message, true); }); return; }
      var purge = t.closest('[data-err-purge]');
      if (purge) {
        if (purge.dataset.confirm !== '1') { purge.dataset.confirm = '1'; purge.textContent = 'Точно удалить?'; return; }
        api('/errors/resolved', { method: 'DELETE' }).then(function (r) { toast('Удалено: ' + r.count); return load(); }).catch(function (e) { toast(e.message, true); });
        return;
      }
      var copy = t.closest('[data-err-copy]');
      if (copy) {
        var e = data.items.find(function (x) { return x.id === copy.dataset.errCopy; }); if (!e) return;
        var text = [e.title, 'Где: ' + [e.source, e.method, e.path].filter(Boolean).join(' '), e.location, 'Раз: ' + e.count + ', последний ' + when(e.last_seen), e.request_id ? 'ID запроса: ' + e.request_id : '', e.trace].filter(Boolean).join('\n');
        navigator.clipboard.writeText(text).then(function () { toast('Скопировано'); }).catch(function () { toast('Не удалось скопировать', true); });
        return;
      }
      var toggle = t.closest('[data-err-toggle]');
      if (toggle) { openId = openId === toggle.dataset.errToggle ? '' : toggle.dataset.errToggle; render(); }
    });
  }

  window.SMAdminErrors = {
    load: function (apiFn, toastFn) {
      api = apiFn; toast = toastFn; host = document.getElementById('errorsAdmin');
      if (!host) return Promise.resolve();
      if (!host.dataset.wired) { host.dataset.wired = '1'; wire(); }
      return load();
    },
    badge: function (apiFn) {
      return apiFn('/errors?status=open').then(function (d) { paintBadge(d.open); }).catch(function () {});
    }
  };
})();
