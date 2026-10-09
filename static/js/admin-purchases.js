/* Admin console: Pro purchases (2026-10-09). Gumroad and Telegram-bot sales in one list, money per currency,
   and the three manual actions: attach a waiting sale to an account, re-read a Gumroad sale, mark a bot sale refunded.
   analytics-dashboard.js calls SMAdminPurchases.load(api, toast) when "Покупки" opens and SMAdminPurchases.preset()
   for links like "purchases:pending" from "Требует внимания". Server: smweb/admin_billing.py.
   Account names use data-user-detail and claim links use data-copy: the dashboard's own click handler does both.
   No localStorage/sessionStorage here (admin rule). */
(function () {
  'use strict';
  var host, api, toast, data = null, busy = false;
  var filters = { days: 30, source: '', status: '', q: '' };
  var DAYS = [[7, '7 дней'], [30, '30 дней'], [90, '90 дней'], [365, 'Год'], [3650, 'Всё время']];
  var SOURCES = [['', 'Все'], ['gumroad', 'Gumroad'], ['telegram', 'Telegram-бот']];
  var STATUSES = [['', 'Все'], ['pending', 'Ждут привязки'], ['granted', 'Выданы'], ['revoked', 'Возвраты']];
  var STATUS = {
    pending: ['ЖДЁТ ПРИВЯЗКИ', 'tag--warn', 'Оплачено, но Pro ещё не получил ни один аккаунт.'],
    granted: ['ВЫДАН', 'tag--success', ''],
    revoked: ['ВОЗВРАТ', 'tag--danger', 'Деньги вернули, дни Pro сняты.'],
    refunded: ['ВОЗВРАТ ДО ВЫДАЧИ', 'tag--danger', 'Вернули до того, как Pro кто-то получил.']
  };
  var esc = function (v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  var when = function (ts) { return ts ? new Date(Number(ts) * 1000).toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' }) : '—'; };
  var num = function (v) { return new Intl.NumberFormat('ru-RU').format(Number(v) || 0); };
  var $ = function (sel) { return host.querySelector(sel); };

  function money(revenue) {
    var parts = Object.keys(revenue || {}).map(function (cur) {
      var value = revenue[cur];
      return cur === 'USD' ? '$' + Number(value).toFixed(2) : num(value) + ' ' + cur;
    });
    return parts.length ? parts.join(' + ') : '—';
  }
  function segmented(name, list, current) {
    return '<div class="segmented" role="group">' + list.map(function (item) {
      return '<button type="button" data-pu-' + name + '="' + item[0] + '" class="' + (String(current) === String(item[0]) ? 'is-active' : '') + '">' + item[1] + '</button>';
    }).join('') + '</div>';
  }
  function statusTag(status) {
    var s = STATUS[status] || [status, '', ''];
    return '<span class="tag ' + s[1] + '" title="' + esc(s[2]) + '">' + esc(s[0]) + '</span>';
  }
  function who(item) {
    var parts = [];
    if (item.user) {
      parts.push(item.user.deleted ? '<span class="muted">Аккаунт ' + esc(item.user.id) + ' удалён</span>' :
        '<button type="button" class="link-button" data-user-detail="' + item.user.id + '">' + esc(item.user.name) + '</button>');
    } else {
      parts.push('<span class="muted">не привязана</span>');
    }
    if (item.buyer) parts.push('<span class="cell-sub">' + esc(item.buyer) + '</span>');
    return parts.join('');
  }
  function actions(item) {
    var out = [];
    if (item.status === 'pending') {
      out.push('<form class="pu-attach" data-pu-attach="' + esc(item.source) + ':' + esc(item.id) + '">' +
        '<input name="user" placeholder="ID, e-mail или ник" required maxlength="120"><button class="mini-button" type="submit">Выдать Pro</button></form>');
      if (item.claim_url) out.push('<button type="button" class="mini-button" data-copy="' + esc(item.claim_url) + '">Ссылка для покупателя</button>');
    }
    if (item.source === 'gumroad') out.push('<button type="button" class="mini-button" data-pu-recheck="' + esc(item.id) + '">Перепроверить в Gumroad</button>');
    if (item.source === 'telegram' && (item.status === 'granted' || item.status === 'pending')) {
      out.push('<button type="button" class="mini-button mini-button--danger" data-pu-refund="' + esc(item.id) + '">Отметить возврат</button>');
    }
    return '<div class="pu-actions">' + out.join('') + '</div>';
  }
  function rows() {
    if (!data.items.length) return '<tr><td colspan="5" class="empty-state">Покупок с такими условиями нет</td></tr>';
    return data.items.map(function (item) {
      return '<tr' + (item.status === 'pending' ? ' class="is-pending"' : '') + '><td>' + when(item.created_at) +
        '<span class="cell-sub">' + (item.source === 'gumroad' ? 'Gumroad' : 'Telegram-бот') + '</span></td>' +
        '<td><div class="table-primary">' + esc(item.plan_label) + ' · ' + esc(item.price || '—') + '</div><span class="cell-sub">' + esc(item.method) + '</span></td>' +
        '<td>' + who(item) + '</td><td>' + statusTag(item.status) +
        (item.revoked_at ? '<span class="cell-sub">' + when(item.revoked_at) + '</span>' : '') + '</td><td>' + actions(item) + '</td></tr>';
    }).join('');
  }
  function notes() {
    var out = [];
    if (!data.gumroad) out.push('Gumroad не подключён (нет GUMROAD_ACCESS_TOKEN): новые продажи Gumroad не приходят, перепроверка не работает.');
    if (!data.telegram) out.push('Покупки через бота выключены (нет BOT_ADMIN_SECRET).');
    return out.map(function (text) { return '<p class="section-note pu-note">' + esc(text) + '</p>'; }).join('');
  }
  function render() {
    var c = data.counts || {};
    var plans = Object.keys(data.by_plan || {}).map(function (name) {
      return '<span class="tag">' + esc(name) + ' · ' + num(data.by_plan[name]) + '</span>';
    }).join('') || '<span class="muted">Пока нет продаж</span>';
    host.innerHTML =
      '<div class="metric-grid">' +
        metric('ПРОДАЖИ', num((c.granted || 0) + (c.pending || 0)), 'за период, без тестовых') +
        metric('ПОЛУЧЕНО', money(data.revenue), 'оплачено и не возвращено', 'metric--money') +
        metric('ЖДУТ ПРИВЯЗКИ', num(data.pending_total), 'за всё время') +
        metric('ВОЗВРАТЫ', num((c.revoked || 0) + (c.refunded || 0)), 'за период') +
      '</div>' + notes() +
      '<article class="panel pu-plans"><p class="overline">ЧТО ПОКУПАЮТ</p><div>' + plans + '</div></article>' +
      '<div class="jobs-toolbar pu-toolbar">' + segmented('days', DAYS, filters.days) + segmented('source', SOURCES, filters.source) +
        segmented('status', STATUSES, filters.status) +
        '<form class="jobs-toolbar__search" data-pu-search><input type="search" name="q" value="' + esc(filters.q) +
        '" placeholder="E-mail, ник, @telegram, ID покупки"></form></div>' +
      '<p class="section-note">«Ждут привязки» — деньги пришли, но Pro не получил ни один аккаунт: покупатель купил без входа на сайте и не открыл ссылку. ' +
        'Можно выдать Pro нужному аккаунту здесь или скопировать ссылку для покупателя (из бота). «Отметить возврат» снимает дни Pro, как /refund в боте.</p>' +
      '<div class="table-wrap"><table><thead><tr><th>Когда</th><th>Что</th><th>Кто</th><th>Статус</th><th></th></tr></thead><tbody>' + rows() + '</tbody></table></div>';
  }
  function metric(label, value, sub, cls) {
    return '<article class="metric' + (cls ? ' ' + cls : '') + '"><p class="overline">' + esc(label) + '</p><strong>' + esc(value) + '</strong><span>' + esc(sub) + '</span></article>';
  }
  function load() {
    var query = new URLSearchParams({ days: filters.days, source: filters.source, status: filters.status, q: filters.q });
    return api('/purchases?' + query).then(function (d) {
      data = d;
      var badge = document.getElementById('purchasesNavCount');
      if (badge) badge.textContent = d.pending_total || '';
      render();
    });
  }
  function act(promise, message) {
    if (busy) return;
    busy = true;
    promise.then(function (r) { toast(typeof message === 'function' ? message(r) : message); return load(); })
      .catch(function (e) { toast(e.message, true); })
      .then(function () { busy = false; });
  }
  var ATTACH = { granted: 'Pro выдан', already: 'Эта покупка уже была выдана', taken: 'Покупка уже принадлежит другому аккаунту',
    refunded: 'Покупку вернули, выдавать нечего', pending: 'Gumroad пока не подтвердил покупку', unknown: 'Gumroad не знает такую покупку' };
  var RECHECK = { granted: 'Покупка подтверждена, Pro выдан', already: 'Всё в порядке: покупка действует', revoked: 'Gumroad сообщил о возврате, дни Pro сняты',
    refunded: 'Покупку вернули', pending: 'Покупка действует, но ещё не привязана', unknown: 'Gumroad не нашёл покупку', other_product: 'Это не наш товар' };
  function wire() {
    host.addEventListener('click', function (event) {
      var t = event.target, button;
      if ((button = t.closest('[data-pu-days]'))) { filters.days = Number(button.dataset.puDays); return reload(); }
      if ((button = t.closest('[data-pu-source]'))) { filters.source = button.dataset.puSource; return reload(); }
      if ((button = t.closest('[data-pu-status]'))) { filters.status = button.dataset.puStatus; return reload(); }
      if ((button = t.closest('[data-pu-recheck]'))) {
        button.disabled = true;
        return act(api('/purchases/gumroad/' + encodeURIComponent(button.dataset.puRecheck) + '/recheck', { method: 'POST', body: '{}' }),
          function (r) { return RECHECK[r.status] || ('Статус: ' + r.status); });
      }
      if ((button = t.closest('[data-pu-refund]'))) {
        if (button.dataset.confirm !== '1') { button.dataset.confirm = '1'; button.textContent = 'Точно? Дни Pro снимутся'; return; }
        return act(api('/purchases/telegram/' + encodeURIComponent(button.dataset.puRefund) + '/refund', { method: 'POST', body: '{}' }),
          function (r) { return r.status === 'already' ? 'Возврат уже был отмечен' : 'Возврат отмечен, дни Pro сняты'; });
      }
    });
    host.addEventListener('submit', function (event) {
      var form = event.target;
      event.preventDefault();
      if (form.matches('[data-pu-search]')) { filters.q = form.q.value.trim(); return reload(); }
      if (form.matches('[data-pu-attach]')) {
        var parts = form.dataset.puAttach.split(':'), source = parts.shift(), id = parts.join(':');
        act(api('/purchases/' + source + '/' + encodeURIComponent(id) + '/attach', { method: 'POST', body: JSON.stringify({ user: form.user.value }) }),
          function (r) { return ATTACH[r.status] || ('Статус: ' + r.status); });
      }
    });
  }
  function reload() { load().catch(function (e) { toast(e.message, true); }); }

  window.SMAdminPurchases = {
    preset: function (status) { filters.status = status === 'pending' ? 'pending' : ''; },
    load: function (apiFn, toastFn) {
      api = apiFn; toast = toastFn;
      if (!host) { host = document.getElementById('purchasesAdmin'); if (!host) return Promise.resolve(); wire(); }
      return load();
    }
  };
})();
