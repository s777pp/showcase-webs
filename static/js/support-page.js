/* "My requests" page (/<lang>/support, 2026-10-01): the user's support tickets, the thread
   with support's answers and a reply box. ?t=<id> opens one ticket (links from the bell). */
(function () {
  'use strict';
  var host = document.getElementById('supportPage'); if (!host) return;
  var LANGS = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'];
  function lang() { var l = window.SSShell ? SSShell.lang() : 'en'; return LANGS.indexOf(l) >= 0 ? l : 'en'; }
  function L(v) { return v[LANGS.indexOf(lang())] || v[0]; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  var T = {
    kicker: ['Support', 'Поддержка', 'Support', 'Destek', 'Support', 'Підтримка', 'Soporte', 'Suporte'],
    title: ['My requests', 'Мои обращения', 'Meine Anfragen', 'Taleplerim', 'Mes demandes', 'Мої звернення', 'Mis solicitudes', 'Minhas solicitações'],
    lead: ['Your messages to support and our answers. You can reply right here.', 'Твои сообщения в поддержку и наши ответы. Отвечать можно прямо здесь.', 'Deine Nachrichten an den Support und unsere Antworten. Du kannst direkt hier antworten.', 'Desteğe mesajların ve yanıtlarımız. Buradan yanıt verebilirsin.', 'Vos messages au support et nos réponses. Vous pouvez répondre ici.', 'Твої повідомлення в підтримку й наші відповіді. Відповідати можна прямо тут.', 'Tus mensajes a soporte y nuestras respuestas. Puedes responder aquí mismo.', 'Suas mensagens ao suporte e nossas respostas. Você pode responder aqui.'],
    login: ['Log in to see your requests. Guests get the answer by e-mail or Telegram.', 'Войди, чтобы увидеть свои обращения. Гостям ответ приходит на почту или в Telegram.', 'Melde dich an, um deine Anfragen zu sehen. Gäste erhalten die Antwort per E-Mail oder Telegram.', 'Taleplerini görmek için giriş yap. Misafirlere yanıt e-posta ya da Telegram ile gelir.', 'Connectez-vous pour voir vos demandes. Les invités reçoivent la réponse par e-mail ou Telegram.', 'Увійди, щоб побачити свої звернення. Гостям відповідь приходить на пошту або в Telegram.', 'Inicia sesión para ver tus solicitudes. Los invitados reciben la respuesta por correo o Telegram.', 'Entre para ver suas solicitações. Visitantes recebem a resposta por e-mail ou Telegram.'],
    loginBtn: ['Log in', 'Войти', 'Anmelden', 'Giriş yap', 'Se connecter', 'Увійти', 'Iniciar sesión', 'Entrar'],
    empty: ['No requests yet.', 'Обращений пока нет.', 'Noch keine Anfragen.', 'Henüz talep yok.', 'Aucune demande pour l’instant.', 'Звернень поки немає.', 'Aún no hay solicitudes.', 'Ainda não há solicitações.'],
    newRequest: ['Write to support', 'Написать в поддержку', 'Support kontaktieren', 'Desteğe yaz', 'Écrire au support', 'Написати в підтримку', 'Escribir a soporte', 'Falar com o suporte'],
    pick: ['Choose a request on the left.', 'Выбери обращение слева.', 'Wähle links eine Anfrage.', 'Soldan bir talep seç.', 'Choisissez une demande à gauche.', 'Обери звернення ліворуч.', 'Elige una solicitud a la izquierda.', 'Escolha uma solicitação à esquerda.'],
    you: ['You', 'Ты', 'Du', 'Sen', 'Vous', 'Ти', 'Tú', 'Você'],
    supportName: ['Showcase Maker support', 'Поддержка Showcase Maker', 'Showcase Maker Support', 'Showcase Maker desteği', 'Support Showcase Maker', 'Підтримка Showcase Maker', 'Soporte de Showcase Maker', 'Suporte Showcase Maker'],
    replyPh: ['Write a reply…', 'Напиши ответ…', 'Antwort schreiben…', 'Yanıt yaz…', 'Écrire une réponse…', 'Напиши відповідь…', 'Escribe una respuesta…', 'Escreva uma resposta…'],
    send: ['Send', 'Отправить', 'Senden', 'Gönder', 'Envoyer', 'Надіслати', 'Enviar', 'Enviar'],
    sent: ['Sent. We will answer here and notify you.', 'Отправлено. Ответим здесь и пришлём уведомление.', 'Gesendet. Wir antworten hier und benachrichtigen dich.', 'Gönderildi. Burada yanıtlayıp bildirim göndereceğiz.', 'Envoyé. Nous répondrons ici et vous préviendrons.', 'Надіслано. Відповімо тут і надішлемо сповіщення.', 'Enviado. Responderemos aquí y te avisaremos.', 'Enviado. Responderemos aqui e avisaremos você.'],
    closed: ['This request is closed. Write a new one if the question remains.', 'Обращение закрыто. Напиши новое, если вопрос остался.', 'Diese Anfrage ist geschlossen. Schreib eine neue, falls die Frage bleibt.', 'Bu talep kapandı. Soru devam ediyorsa yenisini yaz.', 'Cette demande est close. Écrivez-en une nouvelle si besoin.', 'Звернення закрите. Напиши нове, якщо питання лишилося.', 'Esta solicitud está cerrada. Escribe una nueva si la duda sigue.', 'Esta solicitação foi encerrada. Escreva uma nova se a dúvida continuar.'],
    error: ['Something went wrong. Try again.', 'Что-то пошло не так. Попробуй ещё раз.', 'Etwas ist schiefgelaufen. Versuche es erneut.', 'Bir şeyler ters gitti. Tekrar dene.', 'Un problème est survenu. Réessayez.', 'Щось пішло не так. Спробуй ще раз.', 'Algo salió mal. Inténtalo de nuevo.', 'Algo deu errado. Tente de novo.'],
    replies: ['answers: {n}', 'ответов: {n}', 'Antworten: {n}', 'yanıt: {n}', 'réponses : {n}', 'відповідей: {n}', 'respuestas: {n}', 'respostas: {n}'],
    s_new: ['Waiting for an answer', 'Ждёт ответа', 'Wartet auf Antwort', 'Yanıt bekliyor', 'En attente de réponse', 'Чекає відповіді', 'Esperando respuesta', 'Aguardando resposta'],
    s_working: ['In progress', 'В работе', 'In Bearbeitung', 'İnceleniyor', 'En cours', 'У роботі', 'En curso', 'Em andamento'],
    s_resolved: ['Answered', 'Есть ответ', 'Beantwortet', 'Yanıtlandı', 'Répondu', 'Є відповідь', 'Respondida', 'Respondida'],
    s_closed: ['Closed', 'Закрыто', 'Geschlossen', 'Kapandı', 'Clos', 'Закрито', 'Cerrada', 'Encerrada']
  };
  function date(ts) { try { return new Date(Number(ts) * 1000).toLocaleString(lang(), { dateStyle: 'medium', timeStyle: 'short' }); } catch (e) { return ''; } }
  var state = { items: [], current: new URLSearchParams(location.search).get('t') || '', thread: null, status: '' };

  function api(path, options) { return fetch(path, Object.assign({ credentials: 'same-origin', cache: 'no-store' }, options || {})).then(function (r) { return r.json().then(function (j) { j.httpStatus = r.status; return j; }); }); }
  function frame(inner) {
    host.innerHTML = '<header class="sp-head"><span class="sp-kicker">' + esc(L(T.kicker)) + '</span><h1>' + esc(L(T.title)) + '</h1><p>' + esc(L(T.lead)) + '</p></header>' + inner;
  }
  function renderGuest() {
    frame('<div class="sp-guest"><p>' + esc(L(T.login)) + '</p><button class="sp-btn" type="button" data-sp-login>' + esc(L(T.loginBtn)) + '</button></div>');
  }
  function render() {
    var list = state.items.length ? state.items.map(function (item) {
      return '<button type="button" class="sp-ticket' + (item.id === state.current ? ' is-on' : '') + '" data-sp-ticket="' + esc(item.id) + '">' +
        '<span class="sp-status sp-status--' + esc(item.status) + '">' + esc(L(T['s_' + item.status] || T.s_new)) + '</span>' +
        '<b>' + esc(item.message) + '</b><small>#' + esc(item.id) + ' · ' + esc(date(item.updated_at)) + (item.replies ? ' · ' + esc(L(T.replies).replace('{n}', item.replies)) : '') + '</small></button>';
    }).join('') : '<p class="sp-muted">' + esc(L(T.empty)) + '</p>';
    var thread = '<p class="sp-muted sp-pick">' + esc(L(T.pick)) + '</p>';
    if (state.thread) {
      thread = '<div class="sp-thread">' + state.thread.messages.map(function (m) {
        var mine = m.author === 'user';
        return '<article class="sp-msg' + (mine ? ' is-mine' : ' is-support') + '"><header><b>' + esc(mine ? L(T.you) : L(T.supportName)) + '</b><time>' + esc(date(m.created_at)) + '</time></header><p>' + esc(m.body).replace(/\n/g, '<br>') + '</p></article>';
      }).join('') + '</div>' + (state.thread.status === 'closed'
        ? '<p class="sp-muted">' + esc(L(T.closed)) + '</p>'
        : '<form class="sp-reply" data-sp-reply><textarea name="text" rows="3" maxlength="2000" required placeholder="' + esc(L(T.replyPh)) + '"></textarea><div><span class="sp-state" aria-live="polite">' + esc(state.status) + '</span><button class="sp-btn" type="submit">' + esc(L(T.send)) + '</button></div></form>');
    }
    frame('<div class="sp-layout"><aside class="sp-list"><button class="sp-btn sp-btn--ghost" type="button" data-support-choice>' + esc(L(T.newRequest)) + '</button>' + list + '</aside><section class="sp-view">' + thread + '</section></div>');
    var view = host.querySelector('.sp-thread'); if (view) view.scrollTop = view.scrollHeight;
  }
  function open(id) {
    state.current = id; state.status = '';
    history.replaceState(null, '', location.pathname + (id ? '?t=' + encodeURIComponent(id) : ''));
    if (!id) { state.thread = null; render(); return; }
    api('/api/support/my/' + encodeURIComponent(id)).then(function (j) { state.thread = j.ok ? j.ticket : null; render(); if (window.SMBell) SMBell.poll(); }).catch(function () { render(); });
  }
  function load() {
    api('/api/support/my').then(function (j) {
      if (j.httpStatus === 401) return renderGuest();
      state.items = j.items || [];
      if (!state.current && state.items.length && window.matchMedia('(min-width: 900px)').matches) state.current = state.items[0].id;
      if (state.current) open(state.current); else render();
    }).catch(function () { frame('<p class="sp-muted">' + esc(L(T.error)) + '</p>'); });
  }
  host.addEventListener('click', function (event) {
    var ticket = event.target.closest('[data-sp-ticket]'); if (ticket) return open(ticket.dataset.spTicket);
    if (event.target.closest('[data-sp-login]') && window.SSShell) SSShell.openAuth('login');
  });
  host.addEventListener('submit', function (event) {
    var form = event.target.closest('[data-sp-reply]'); if (!form) return;
    event.preventDefault();
    var text = form.text.value.trim(); if (text.length < 2) return;
    form.querySelector('button').disabled = true;
    api('/api/support/my/' + encodeURIComponent(state.current), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: text }) })
      .then(function (j) {
        if (!j.ok) { state.status = j.msg || L(T.error); render(); return; }
        state.thread.messages.push({ author: 'user', body: text, created_at: Date.now() / 1000 }); state.thread.status = 'new'; state.status = L(T.sent);
        state.items.forEach(function (item) { if (item.id === state.current) { item.status = 'new'; item.updated_at = Date.now() / 1000; } });
        render();
      }).catch(function () { state.status = L(T.error); render(); });
  });
  frame('<p class="sp-muted">…</p>');
  document.addEventListener('ss:me', load, { once: true });
  if (window.SS_ME) load();
})();
