/* /<lang>/billing/claim: attach a Pro purchase to the signed-in account (2026-10-06).
   Telegram bot: the bot sends ?tg=<claim token> when it does not know the buyer's account yet
   (/api/billing/telegram/claim, smweb/telegram_billing.py).
   Gumroad's purchase content links here with ?sale_id=...&product_id=...&product_permalink=...
   (its __sale_info__ placeholder). The server reads the sale back from Gumroad before granting Pro. */
(function () {
  'use strict';
  var LANGS = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'];
  var COPY = {
    en: { title: 'Activate Pro', checking: 'Checking your purchase with Gumroad…', login: 'Log in or create an account: the purchase will be attached to it.', loginBtn: 'Log in', register: 'Create an account', granted: 'Pro is active on your account. Thank you!', already: 'This purchase is already active on your account.', until: 'Pro until {date}', forever: 'Pro forever', taken: 'This purchase is already attached to another account. Log in to that account, or write to support if it is not yours.', refunded: 'This purchase was refunded, so it no longer gives Pro.', unknown: 'We could not find this purchase. Open the button from your Gumroad purchase again or write to support.', missing: 'The link is incomplete. Open the "Activate Pro" button from your Gumroad purchase (receipt e-mail or Gumroad library).', checkingTg: 'Checking your purchase from the Telegram bot…', unknownTg: 'We could not find this purchase. Open the link from the bot again or write to support.', missingTg: 'The link is incomplete. Open the link the bot sent you after the payment.', unavailable: 'Gumroad is not answering right now. Try again in a minute.', retry: 'Try again', tools: 'Open the tools', support: 'Write to support', error: 'Something went wrong. Try again or write to support.' },
    ru: { title: 'Активация Pro', checking: 'Проверяем покупку в Gumroad…', login: 'Войди или создай аккаунт: покупка привяжется к нему.', loginBtn: 'Войти', register: 'Создать аккаунт', granted: 'Pro активирован на твоём аккаунте. Спасибо!', already: 'Эта покупка уже активна на твоём аккаунте.', until: 'Pro до {date}', forever: 'Pro навсегда', taken: 'Эта покупка уже привязана к другому аккаунту. Войди в него или напиши в поддержку, если это не твой аккаунт.', refunded: 'За эту покупку оформлен возврат, поэтому Pro по ней больше не действует.', unknown: 'Не нашли такую покупку. Открой кнопку из покупки на Gumroad ещё раз или напиши в поддержку.', missing: 'Ссылка неполная. Открой кнопку «Активировать Pro» из покупки на Gumroad (письмо-чек или библиотека Gumroad).', checkingTg: 'Проверяем покупку из Telegram-бота…', unknownTg: 'Не нашли такую покупку. Открой ссылку из бота ещё раз или напиши в поддержку.', missingTg: 'Ссылка неполная. Открой ссылку, которую бот прислал после оплаты.', unavailable: 'Gumroad сейчас не отвечает. Попробуй через минуту.', retry: 'Попробовать ещё раз', tools: 'Открыть инструменты', support: 'Написать в поддержку', error: 'Что-то пошло не так. Попробуй ещё раз или напиши в поддержку.' },
    de: { title: 'Pro aktivieren', checking: 'Dein Kauf wird bei Gumroad geprüft…', login: 'Melde dich an oder erstelle ein Konto: der Kauf wird damit verknüpft.', loginBtn: 'Anmelden', register: 'Konto erstellen', granted: 'Pro ist auf deinem Konto aktiv. Danke!', already: 'Dieser Kauf ist auf deinem Konto bereits aktiv.', until: 'Pro bis {date}', forever: 'Pro für immer', taken: 'Dieser Kauf ist bereits mit einem anderen Konto verknüpft. Melde dich dort an oder schreib dem Support, wenn es nicht deins ist.', refunded: 'Dieser Kauf wurde erstattet und gibt kein Pro mehr.', unknown: 'Dieser Kauf wurde nicht gefunden. Öffne den Button aus deinem Gumroad-Kauf erneut oder schreib dem Support.', missing: 'Der Link ist unvollständig. Öffne den Button „Pro aktivieren“ aus deinem Gumroad-Kauf (Beleg-E-Mail oder Gumroad-Bibliothek).', checkingTg: 'Dein Kauf aus dem Telegram-Bot wird geprüft…', unknownTg: 'Dieser Kauf wurde nicht gefunden. Öffne den Link aus dem Bot erneut oder schreib dem Support.', missingTg: 'Der Link ist unvollständig. Öffne den Link, den dir der Bot nach der Zahlung geschickt hat.', unavailable: 'Gumroad antwortet gerade nicht. Versuche es in einer Minute erneut.', retry: 'Erneut versuchen', tools: 'Werkzeuge öffnen', support: 'Support schreiben', error: 'Etwas ist schiefgelaufen. Versuche es erneut oder schreib dem Support.' },
    tr: { title: 'Pro’yu etkinleştir', checking: 'Satın alman Gumroad’da kontrol ediliyor…', login: 'Giriş yap veya hesap oluştur: satın alma ona bağlanacak.', loginBtn: 'Giriş yap', register: 'Hesap oluştur', granted: 'Pro hesabında etkin. Teşekkürler!', already: 'Bu satın alma hesabında zaten etkin.', until: '{date} tarihine kadar Pro', forever: 'Süresiz Pro', taken: 'Bu satın alma başka bir hesaba bağlı. O hesaba giriş yap ya da senin değilse desteğe yaz.', refunded: 'Bu satın alma iade edildi, artık Pro vermiyor.', unknown: 'Bu satın alma bulunamadı. Gumroad satın almandaki düğmeyi yeniden aç ya da desteğe yaz.', missing: 'Bağlantı eksik. Gumroad satın almandaki “Pro’yu etkinleştir” düğmesini aç (makbuz e-postası veya Gumroad kütüphanesi).', checkingTg: 'Telegram botundaki satın alman kontrol ediliyor…', unknownTg: 'Bu satın alma bulunamadı. Bottaki bağlantıyı yeniden aç ya da desteğe yaz.', missingTg: 'Bağlantı eksik. Botun ödemeden sonra gönderdiği bağlantıyı aç.', unavailable: 'Gumroad şu an yanıt vermiyor. Bir dakika sonra tekrar dene.', retry: 'Tekrar dene', tools: 'Araçları aç', support: 'Desteğe yaz', error: 'Bir şeyler ters gitti. Tekrar dene ya da desteğe yaz.' },
    fr: { title: 'Activer Pro', checking: 'Vérification de votre achat auprès de Gumroad…', login: 'Connectez-vous ou créez un compte : l’achat y sera rattaché.', loginBtn: 'Se connecter', register: 'Créer un compte', granted: 'Pro est actif sur votre compte. Merci !', already: 'Cet achat est déjà actif sur votre compte.', until: 'Pro jusqu’au {date}', forever: 'Pro à vie', taken: 'Cet achat est déjà rattaché à un autre compte. Connectez-vous à ce compte ou écrivez au support s’il n’est pas à vous.', refunded: 'Cet achat a été remboursé et ne donne plus Pro.', unknown: 'Achat introuvable. Rouvrez le bouton de votre achat Gumroad ou écrivez au support.', missing: 'Le lien est incomplet. Ouvrez le bouton « Activer Pro » de votre achat Gumroad (e-mail de reçu ou bibliothèque Gumroad).', checkingTg: 'Vérification de votre achat effectué dans le bot Telegram…', unknownTg: 'Achat introuvable. Rouvrez le lien envoyé par le bot ou écrivez au support.', missingTg: 'Le lien est incomplet. Ouvrez le lien que le bot vous a envoyé après le paiement.', unavailable: 'Gumroad ne répond pas pour le moment. Réessayez dans une minute.', retry: 'Réessayer', tools: 'Ouvrir les outils', support: 'Écrire au support', error: 'Une erreur est survenue. Réessayez ou écrivez au support.' },
    uk: { title: 'Активація Pro', checking: 'Перевіряємо покупку в Gumroad…', login: 'Увійди або створи акаунт: покупка прив’яжеться до нього.', loginBtn: 'Увійти', register: 'Створити акаунт', granted: 'Pro активовано на твоєму акаунті. Дякуємо!', already: 'Ця покупка вже активна на твоєму акаунті.', until: 'Pro до {date}', forever: 'Pro назавжди', taken: 'Ця покупка вже прив’язана до іншого акаунта. Увійди в нього або напиши в підтримку, якщо це не твій акаунт.', refunded: 'За цю покупку оформлено повернення, тому Pro за нею більше не діє.', unknown: 'Не знайшли таку покупку. Відкрий кнопку з покупки на Gumroad ще раз або напиши в підтримку.', missing: 'Посилання неповне. Відкрий кнопку «Активувати Pro» з покупки на Gumroad (лист-чек або бібліотека Gumroad).', checkingTg: 'Перевіряємо покупку з Telegram-бота…', unknownTg: 'Не знайшли таку покупку. Відкрий посилання з бота ще раз або напиши в підтримку.', missingTg: 'Посилання неповне. Відкрий посилання, яке бот надіслав після оплати.', unavailable: 'Gumroad зараз не відповідає. Спробуй за хвилину.', retry: 'Спробувати ще раз', tools: 'Відкрити інструменти', support: 'Написати в підтримку', error: 'Щось пішло не так. Спробуй ще раз або напиши в підтримку.' },
    es: { title: 'Activar Pro', checking: 'Comprobando tu compra en Gumroad…', login: 'Inicia sesión o crea una cuenta: la compra se vinculará a ella.', loginBtn: 'Iniciar sesión', register: 'Crear una cuenta', granted: 'Pro está activo en tu cuenta. ¡Gracias!', already: 'Esta compra ya está activa en tu cuenta.', until: 'Pro hasta el {date}', forever: 'Pro para siempre', taken: 'Esta compra ya está vinculada a otra cuenta. Inicia sesión en esa cuenta o escribe a soporte si no es tuya.', refunded: 'Esta compra fue reembolsada y ya no da Pro.', unknown: 'No encontramos esta compra. Vuelve a abrir el botón de tu compra en Gumroad o escribe a soporte.', missing: 'El enlace está incompleto. Abre el botón «Activar Pro» de tu compra en Gumroad (correo del recibo o biblioteca de Gumroad).', checkingTg: 'Comprobando tu compra del bot de Telegram…', unknownTg: 'No encontramos esta compra. Vuelve a abrir el enlace del bot o escribe a soporte.', missingTg: 'El enlace está incompleto. Abre el enlace que el bot te envió después del pago.', unavailable: 'Gumroad no responde ahora. Inténtalo en un minuto.', retry: 'Reintentar', tools: 'Abrir las herramientas', support: 'Escribir a soporte', error: 'Algo salió mal. Inténtalo de nuevo o escribe a soporte.' },
    pt: { title: 'Ativar o Pro', checking: 'Verificando sua compra na Gumroad…', login: 'Entre ou crie uma conta: a compra será vinculada a ela.', loginBtn: 'Entrar', register: 'Criar uma conta', granted: 'O Pro está ativo na sua conta. Obrigado!', already: 'Esta compra já está ativa na sua conta.', until: 'Pro até {date}', forever: 'Pro para sempre', taken: 'Esta compra já está vinculada a outra conta. Entre nessa conta ou escreva ao suporte se ela não for sua.', refunded: 'Esta compra foi reembolsada e não dá mais o Pro.', unknown: 'Não encontramos esta compra. Abra de novo o botão da sua compra na Gumroad ou escreva ao suporte.', missing: 'O link está incompleto. Abra o botão “Ativar o Pro” da sua compra na Gumroad (e-mail do recibo ou biblioteca da Gumroad).', checkingTg: 'Verificando sua compra feita no bot do Telegram…', unknownTg: 'Não encontramos esta compra. Abra de novo o link do bot ou escreva ao suporte.', missingTg: 'O link está incompleto. Abra o link que o bot enviou depois do pagamento.', unavailable: 'A Gumroad não está respondendo agora. Tente de novo em um minuto.', retry: 'Tentar de novo', tools: 'Abrir as ferramentas', support: 'Escrever ao suporte', error: 'Algo deu errado. Tente de novo ou escreva ao suporte.' }
  };
  var root = document.getElementById('billingClaim');
  if (!root) return;
  var query = new URLSearchParams(location.search);
  var saleId = (query.get('sale_id') || '').trim();
  var tgToken = (query.get('tg') || '').trim();
  var fromBot = !!tgToken;
  // Text for the Gumroad flow, or its "...Tg" twin for a purchase made in the bot.
  function source(key) { return fromBot ? key + 'Tg' : key; }

  function lang() {
    var l = (window.SMLang && SMLang.get ? SMLang.get() : document.documentElement.lang || 'en').slice(0, 2);
    return LANGS.indexOf(l) >= 0 ? l : 'en';
  }
  function t(key, vars) {
    var text = COPY[lang()][key] || COPY.en[key] || key;
    Object.keys(vars || {}).forEach(function (k) { text = text.split('{' + k + '}').join(vars[k]); });
    return text;
  }
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function url(path) { return window.SMLang && SMLang.url ? SMLang.url(path) : path; }

  function card(kind, message, extra, actions) {
    root.replaceChildren();
    var box = el('section', 'bc__card is-' + kind);
    box.append(el('span', 'bc__icon', kind === 'ok' ? '✓' : kind === 'bad' ? '!' : '…'));
    box.append(el('h1', 'bc__title', t('title')), el('p', 'bc__text', message));
    if (extra) box.append(el('p', 'bc__extra', extra));
    if (actions && actions.length) {
      var row = el('div', 'bc__actions');
      actions.forEach(function (action) { row.append(action); });
      box.append(row);
    }
    root.append(box);
  }
  function button(text, onClick, ghost) {
    var b = el('button', 'btn' + (ghost ? ' ghost' : ''), text); b.type = 'button'; b.addEventListener('click', onClick); return b;
  }
  function link(text, href, ghost) { var a = el('a', 'btn' + (ghost ? ' ghost' : ''), text); a.href = href; return a; }
  function supportLink() { return link(t('support'), url('/support'), true); }

  function proLine(pro) {
    if (!pro || !pro.pro) return '';
    if (pro.lifetime) return t('forever');
    return t('until', { date: new Date(pro.until * 1000).toLocaleString(lang(), { dateStyle: 'long', timeStyle: 'short' }) });
  }

  function claim() {
    card('wait', t(source('checking')));
    fetch(fromBot ? '/api/billing/telegram/claim' : '/api/billing/gumroad/claim', {
      method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(fromBot ? { token: tgToken } : { sale_id: saleId })
    }).then(function (r) { return r.json().catch(function () { return {}; }).then(function (body) { return { status: r.status, body: body }; }); })
      .then(function (res) {
        var code = res.body && res.body.code;
        if (res.body && res.body.ok) {
          card('ok', t(code === 'already' ? 'already' : 'granted'), proLine(res.body.pro), [link(t('tools'), url('/app'))]);
          if (window.SSShell && SSShell.loadMe) SSShell.loadMe();
          return;
        }
        if (code === 'login') { askLogin(); return; }
        if (code === 'unavailable') { card('bad', t('unavailable'), '', [button(t('retry'), claim), supportLink()]); return; }
        if (code === 'taken' || code === 'refunded' || code === 'revoked') { card('bad', t(code === 'revoked' ? 'refunded' : code), '', [supportLink()]); return; }
        if (code === 'unknown' || code === 'other_product') { card('bad', t(source('unknown')), '', [supportLink()]); return; }
        card('bad', t('error'), '', [button(t('retry'), claim), supportLink()]);
      })
      .catch(function () { card('bad', t('error'), '', [button(t('retry'), claim), supportLink()]); });
  }

  function askLogin() {
    card('wait', t('login'), '', [
      button(t('loginBtn'), function () { if (window.SSShell && SSShell.openAuth) SSShell.openAuth('login'); }),
      button(t('register'), function () { if (window.SSShell && SSShell.openAuth) SSShell.openAuth('register'); }, true)
    ]);
  }

  function start() {
    var complete = fromBot ? /^[A-Za-z0-9_\-]{16,64}$/.test(tgToken) : /^[A-Za-z0-9_=\-]{6,80}$/.test(saleId);
    if (!complete) { card('bad', t(source('missing')), '', [supportLink()]); return; }
    var ready = window.SSShell && SSShell.me ? SSShell.me() : fetch('/api/bootstrap', { credentials: 'same-origin' }).then(function (r) { return r.json(); });
    ready.then(function (me) { if (me && me.logged_in) claim(); else askLogin(); })
      .catch(askLogin);
  }

  card('wait', t(source('checking')));
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
  window.addEventListener('sm:langchange', function () { start(); });
})();
