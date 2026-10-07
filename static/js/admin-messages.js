/* Admin console: messages to users (2026-10-07, owner: "send users messages they notice at once").
   analytics-dashboard.js calls SMAdminMessages.load(api, toast) when "Сообщения" opens; the user card
   has a "Написать сообщение" button (data-message-user) that opens this view with the user filled in.
   Server: smweb/admin_messages.py. The user sees the message in the bell and, with "Окном поверх
   страницы", as a window on the next page load or within a minute (site-bell.js).
   No localStorage/sessionStorage here (admin rule). */
(function () {
  'use strict';
  var host, api, toast, items = [], pendingTarget = '', countTimer = 0, sending = false;
  var form = { audience: 'users', targets: '', title_ru: '', body_ru: '', title_en: '', body_en: '', link: '', popup: true };
  var AUDIENCE = { users: 'Конкретным людям', all: 'Всем', pro: 'Только Pro', free: 'Только Free' };
  var esc = function (v) { return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  var when = function (ts) { return ts ? new Date(Number(ts) * 1000).toLocaleString('ru-RU', { dateStyle: 'short', timeStyle: 'short' }) : '—'; };
  var $ = function (sel) { return host.querySelector(sel); };

  function audienceButtons() {
    return Object.keys(AUDIENCE).map(function (key) {
      return '<button type="button" data-msg-audience="' + key + '" class="' + (form.audience === key ? 'is-active' : '') + '">' + AUDIENCE[key] + '</button>';
    }).join('');
  }
  function historyRows() {
    if (!items.length) return '<tr><td colspan="5" class="empty-state">Сообщений пока не было</td></tr>';
    return items.map(function (m) {
      var who = AUDIENCE[m.audience] || m.audience;
      if (m.audience === 'users' && m.targets) who += '<span class="cell-sub">ID ' + esc(String(m.targets).split(',').slice(0, 4).join(', ')) + (String(m.targets).split(',').length > 4 ? '…' : '') + '</span>';
      var read = m.recalled_at ? '<span class="tag tag--danger">ОТОЗВАНО</span>' :
        '<b>' + esc(m.read) + '</b> из ' + esc(m.delivered) + '<span class="cell-sub">' + (m.popup ? 'окном и в колокольчике' : 'только в колокольчике') + '</span>';
      return '<tr><td>' + when(m.created_at) + '</td><td>' + who + '</td><td><div class="table-primary">' + esc(m.title_ru) + '</div>' +
        (m.body_ru ? '<div class="cell-sub msg-history__body">' + esc(m.body_ru) + '</div>' : '') + '</td><td>' + read + '</td><td>' +
        (m.recalled_at ? '' : '<button class="mini-button mini-button--danger" data-msg-recall="' + esc(m.id) + '">Отозвать</button>') + '</td></tr>';
    }).join('');
  }
  function preview() {
    var box = $('[data-msg-preview]');
    if (!box) return;
    box.innerHTML = '<p class="msg-preview__from">✉️ От команды ShowcaseMaker</p><h3>' + esc(form.title_ru || 'Заголовок сообщения') + '</h3>' +
      (form.body_ru ? '<p class="msg-preview__body">' + esc(form.body_ru) + '</p>' : '') +
      '<div class="msg-preview__actions">' + (form.link ? '<span class="msg-preview__go">Открыть</span>' : '') + '<span class="msg-preview__ok">Понятно</span></div>';
  }
  function render() {
    host.innerHTML = '<div class="split-grid msg-grid"><form class="panel form-panel" data-msg-form>' +
      '<p class="overline">НОВОЕ СООБЩЕНИЕ</p><h2>Написать пользователям</h2>' +
      '<p class="muted">Сообщение придёт в колокольчик. С галочкой «Окном поверх страницы» человек увидит его сразу: при следующем открытии любой страницы сайта, а на открытой вкладке — в течение минуты. Гости (без аккаунта) сообщения не получают.</p>' +
      '<div class="segmented msg-audience" role="group" aria-label="Кому">' + audienceButtons() + '</div>' +
      '<label data-msg-targets-wrap' + (form.audience === 'users' ? '' : ' hidden') + '>Кому: ID, e-mail, ник или SteamID64 — через запятую или с новой строки' +
      '<textarea name="targets" rows="2" maxlength="6000" placeholder="12, user@mail.com, nickname">' + esc(form.targets) + '</textarea></label>' +
      '<p class="msg-count" data-msg-count>…</p>' +
      '<label>Заголовок<input name="title_ru" maxlength="120" required value="' + esc(form.title_ru) + '"></label>' +
      '<label>Текст<textarea name="body_ru" rows="6" maxlength="1500">' + esc(form.body_ru) + '</textarea><small>Обычный текст, переносы строк сохраняются. До 1500 символов.</small></label>' +
      '<label>Ссылка для кнопки «Открыть» (необязательно)<input name="link" maxlength="300" placeholder="/app#loop или https://…" value="' + esc(form.link) + '"></label>' +
      '<details class="msg-en"' + (form.title_en ? ' open' : '') + '><summary>Английская версия (для всех языков, кроме русского и украинского)</summary>' +
      '<label>Title<input name="title_en" maxlength="120" value="' + esc(form.title_en) + '"></label>' +
      '<label>Text<textarea name="body_en" rows="5" maxlength="1500">' + esc(form.body_en) + '</textarea></label>' +
      '<small>Без английской версии все увидят русский текст.</small></details>' +
      '<label class="switch-row"><span><b>Окном поверх страницы</b><small>Иначе — только в колокольчике</small></span><input name="popup" type="checkbox"' + (form.popup ? ' checked' : '') + '></label>' +
      '<button class="button" type="submit" data-msg-send>Отправить</button></form>' +
      '<article class="panel"><p class="overline">ТАК ЭТО УВИДИТ ПОЛЬЗОВАТЕЛЬ</p><h2>Предпросмотр</h2><div class="msg-preview" data-msg-preview></div></article></div>' +
      '<article class="panel"><div class="panel-head"><div><p class="overline">ИСТОРИЯ</p><h2>Отправленные сообщения</h2>' +
      '<p class="muted">«Прочитали» — сколько человек открыли окно или нажали на сообщение в колокольчике. «Отозвать» убирает сообщение у всех. Сообщения хранятся у пользователей 30 дней.</p></div></div>' +
      '<div class="table-wrap"><table><thead><tr><th>Когда</th><th>Кому</th><th>Сообщение</th><th>Прочитали</th><th></th></tr></thead><tbody>' + historyRows() + '</tbody></table></div></article>';
    preview();
    recount();
  }
  function recount() {
    clearTimeout(countTimer);
    var box = $('[data-msg-count]');
    if (!box) return;
    if (form.audience === 'users' && !form.targets.trim()) { box.textContent = 'Впиши, кому отправить.'; box.className = 'msg-count'; return; }
    box.textContent = 'Считаем получателей…';
    countTimer = setTimeout(function () {
      api('/messages/count', { method: 'POST', body: JSON.stringify({ audience: form.audience, targets: form.targets }) }).then(function (r) {
        var el = $('[data-msg-count]');
        if (!el) return;
        el.className = 'msg-count' + (r.count ? '' : ' is-warn');
        el.textContent = 'Получат: ' + r.count + (r.missing && r.missing.length ? ' · не найдены: ' + r.missing.slice(0, 6).join(', ') + (r.missing.length > 6 ? '…' : '') : '');
        el.dataset.count = r.count;
      }).catch(function (e) { var el = $('[data-msg-count]'); if (el) el.textContent = e.message; });
    }, 350);
  }
  function load() {
    if (pendingTarget) { form.audience = 'users'; form.targets = pendingTarget; pendingTarget = ''; }
    return api('/messages').then(function (d) { items = d.items || []; render(); });
  }
  function resetSend() {
    var btn = $('[data-msg-send]');
    if (btn) { btn.dataset.confirm = ''; btn.textContent = 'Отправить'; }
  }
  function wire() {
    host.addEventListener('input', function (event) {
      var t = event.target;
      if (!t.name || !(t.name in form)) return;
      form[t.name] = t.type === 'checkbox' ? t.checked : t.value;
      if (t.name === 'targets') recount();
      resetSend();
      preview();
    });
    host.addEventListener('change', function (event) {
      if (event.target.name === 'popup') form.popup = event.target.checked;
    });
    host.addEventListener('click', function (event) {
      var t = event.target;
      var aud = t.closest('[data-msg-audience]');
      if (aud) {
        form.audience = aud.dataset.msgAudience;
        host.querySelectorAll('[data-msg-audience]').forEach(function (b) { b.classList.toggle('is-active', b === aud); });
        $('[data-msg-targets-wrap]').hidden = form.audience !== 'users';
        resetSend(); recount();
        return;
      }
      var recall = t.closest('[data-msg-recall]');
      if (recall) {
        if (recall.dataset.confirm !== '1') { recall.dataset.confirm = '1'; recall.textContent = 'Точно отозвать?'; return; }
        api('/messages/' + encodeURIComponent(recall.dataset.msgRecall), { method: 'DELETE' })
          .then(function (r) { toast('Отозвано, убрано у ' + r.removed); return load(); })
          .catch(function (e) { toast(e.message, true); });
      }
    });
    host.addEventListener('submit', function (event) {
      event.preventDefault();
      if (sending) return;
      var btn = $('[data-msg-send]'), countEl = $('[data-msg-count]'), n = Number((countEl && countEl.dataset.count) || 0);
      if (!form.title_ru.trim()) { toast('Нужен заголовок', true); return; }
      // Broadcasts and long lists need a second click.
      if ((form.audience !== 'users' || n > 5) && btn.dataset.confirm !== '1') {
        btn.dataset.confirm = '1'; btn.textContent = 'Точно отправить ' + (n || '') + ' получателям?';
        return;
      }
      sending = true; btn.disabled = true;
      api('/messages', { method: 'POST', body: JSON.stringify(form) }).then(function (r) {
        toast('Отправлено: ' + r.recipients + (r.missing && r.missing.length ? ' (не найдены: ' + r.missing.join(', ') + ')' : ''));
        form = { audience: form.audience, targets: '', title_ru: '', body_ru: '', title_en: '', body_en: '', link: '', popup: true };
        return load();
      }).catch(function (e) { toast(e.message, true); resetSend(); })
        .then(function () { sending = false; var b = $('[data-msg-send]'); if (b) b.disabled = false; });
    });
  }
  // "Написать сообщение" on the user card.
  document.addEventListener('click', function (event) {
    var btn = event.target.closest('[data-message-user]');
    if (!btn) return;
    pendingTarget = String(btn.dataset.messageUser);
    var dialog = document.getElementById('userDetailDialog');
    if (dialog && dialog.open) dialog.close();
    var nav = document.querySelector('.admin-nav [data-view="messages"]');
    if (nav) nav.click();
  });

  window.SMAdminMessages = {
    load: function (apiFn, toastFn) {
      api = apiFn; toast = toastFn;
      if (!host) { host = document.getElementById('messagesAdmin'); if (!host) return Promise.resolve(); wire(); }
      return load();
    }
  };
})();
