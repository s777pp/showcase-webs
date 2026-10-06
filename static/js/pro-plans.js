/* Pro purchase dialog (2026-10-06, owner: "first the plan, then the payment method").
   Lives inside the shell's activation dialog (#ssActivation, see ss-shell.js activationHTML):
     step "plans"  - choose 24 hours / 7 / 30 / 90 days / forever (prices from /api/billing/plans);
     step "pay"    - choose how to pay: Gumroad card/PayPal (automatic), the Telegram bot (automatic when the
                     server says so in /api/billing/plans "telegram", else a manual key), FunPay (manual key);
     step "key"    - the shell's own key form (#ssKeyPane), for keys bought on FunPay / Telegram.
   Every Buy and Activate button opens step plans; SSShell.openActivation({plan}) jumps to "pay".
   A Gumroad checkout is bound to the signed-in account (/api/billing/gumroad/order), a bot purchase too
   (/api/billing/telegram/order returns t.me/<bot>?start=buy_<token>); the dialog then polls until Pro
   switches on. Styles: css/pro-plans.css. */
(function () {
  'use strict';
  if (window.SMProPlans) return;
  var LANGS = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'];
  var FUNPAY_URL = 'https://funpay.com/lots/offer?id=76420307';
  var TELEGRAM_URL = 'https://t.me/SteamMakerBot';
  var COPY = {
    en: { title: 'Choose Pro', sub: 'One payment, no auto-renewal. Days add up with the Pro you already have.', d1: '24 hours', d7: '7 days', d30: '30 days', d90: '90 days', life: 'Forever', popular: 'Popular', best: 'Best value', haveKey: 'I already have a key', back: 'Plans', payTitle: 'How to pay', card: 'Card or PayPal', cardSub: 'Gumroad · Pro turns on automatically', auto: 'Automatic', manual: 'Manual', soon: 'Soon', funpaySub: 'Manual activation: the seller sends a key, you enter it here', tg: 'Telegram bot', tgSub: 'Manual activation for now: the bot gives a key, you enter it here', tgAuto: 'Stars, crypto or transfer · Pro turns on automatically', tgWaiting: 'Finish the payment in the Telegram bot. Pro turns on here by itself in a few seconds.', gotKey: 'Got a key? Enter it here', enterKey: 'Enter the key', login: 'Log in first: Pro is added to your account.', loginBtn: 'Log in', opening: 'Opening the checkout…', waiting: 'Finish the payment in the Gumroad tab. Pro turns on here by itself in a few seconds.', done: 'Pro is active! Reloading…', lifetime: 'You already have Pro forever.', error: 'Could not start the payment. Try again.', blocked: 'The new tab was blocked. Open the checkout:', open: 'Open checkout', cardOff: 'Card payment is not available yet. Use FunPay or Telegram.' },
    ru: { title: 'Выбери Pro', sub: 'Разовая оплата, без автопродления. Дни складываются с уже действующим Pro.', d1: '24 часа', d7: '7 дней', d30: '30 дней', d90: '90 дней', life: 'Навсегда', popular: 'Популярный', best: 'Выгоднее всего', haveKey: 'У меня уже есть ключ', back: 'Тарифы', payTitle: 'Способ оплаты', card: 'Карта или PayPal', cardSub: 'Gumroad · Pro включится автоматически', auto: 'Автоматически', manual: 'Вручную', soon: 'Скоро', funpaySub: 'Активация вручную: продавец пришлёт ключ, его нужно ввести здесь', tg: 'Telegram-бот', tgSub: 'Пока активация вручную: бот выдаст ключ, его нужно ввести здесь', tgAuto: 'Stars, крипта или перевод · Pro включится автоматически', tgWaiting: 'Заверши оплату в Telegram-боте. Pro включится здесь сам через несколько секунд.', gotKey: 'Получил ключ? Введи его здесь', enterKey: 'Ввести ключ', login: 'Сначала войди: Pro добавится к твоему аккаунту.', loginBtn: 'Войти', opening: 'Открываем оплату…', waiting: 'Заверши оплату во вкладке Gumroad. Pro включится здесь сам через несколько секунд.', done: 'Pro активирован! Обновляем страницу…', lifetime: 'У тебя уже есть Pro навсегда.', error: 'Не удалось начать оплату. Попробуй ещё раз.', blocked: 'Новая вкладка заблокирована. Открой оплату:', open: 'Открыть оплату', cardOff: 'Оплата картой пока недоступна. Используй FunPay или Telegram.' },
    de: { title: 'Pro wählen', sub: 'Einmalzahlung, keine automatische Verlängerung. Die Tage werden zu deinem aktuellen Pro addiert.', d1: '24 Stunden', d7: '7 Tage', d30: '30 Tage', d90: '90 Tage', life: 'Für immer', popular: 'Beliebt', best: 'Bester Preis', haveKey: 'Ich habe schon einen Schlüssel', back: 'Tarife', payTitle: 'Zahlungsart', card: 'Karte oder PayPal', cardSub: 'Gumroad · Pro wird automatisch aktiviert', auto: 'Automatisch', manual: 'Manuell', soon: 'Bald', funpaySub: 'Manuelle Aktivierung: der Verkäufer schickt einen Schlüssel, den du hier eingibst', tg: 'Telegram-Bot', tgSub: 'Vorerst manuell: der Bot gibt dir einen Schlüssel, den du hier eingibst', tgAuto: 'Stars, Krypto oder Überweisung · Pro wird automatisch aktiviert', tgWaiting: 'Schließe die Zahlung im Telegram-Bot ab. Pro wird hier in wenigen Sekunden automatisch aktiviert.', gotKey: 'Schlüssel erhalten? Hier eingeben', enterKey: 'Schlüssel eingeben', login: 'Melde dich zuerst an: Pro wird deinem Konto gutgeschrieben.', loginBtn: 'Anmelden', opening: 'Zahlung wird geöffnet…', waiting: 'Schließe die Zahlung im Gumroad-Tab ab. Pro wird hier in wenigen Sekunden automatisch aktiviert.', done: 'Pro ist aktiv! Seite wird neu geladen…', lifetime: 'Du hast Pro bereits für immer.', error: 'Die Zahlung konnte nicht gestartet werden. Versuche es erneut.', blocked: 'Der neue Tab wurde blockiert. Zahlung öffnen:', open: 'Zahlung öffnen', cardOff: 'Kartenzahlung ist noch nicht verfügbar. Nutze FunPay oder Telegram.' },
    tr: { title: 'Pro seç', sub: 'Tek seferlik ödeme, otomatik yenileme yok. Günler mevcut Pro’na eklenir.', d1: '24 saat', d7: '7 gün', d30: '30 gün', d90: '90 gün', life: 'Süresiz', popular: 'Popüler', best: 'En avantajlı', haveKey: 'Zaten bir anahtarım var', back: 'Planlar', payTitle: 'Ödeme yöntemi', card: 'Kart veya PayPal', cardSub: 'Gumroad · Pro otomatik açılır', auto: 'Otomatik', manual: 'Elle', soon: 'Yakında', funpaySub: 'Elle etkinleştirme: satıcı bir anahtar gönderir, onu buraya girersin', tg: 'Telegram botu', tgSub: 'Şimdilik elle: bot bir anahtar verir, onu buraya girersin', tgAuto: 'Stars, kripto veya havale · Pro otomatik açılır', tgWaiting: 'Ödemeyi Telegram botunda tamamla. Pro birkaç saniye içinde burada kendiliğinden açılır.', gotKey: 'Anahtarı aldın mı? Buraya gir', enterKey: 'Anahtarı gir', login: 'Önce giriş yap: Pro hesabına eklenir.', loginBtn: 'Giriş yap', opening: 'Ödeme açılıyor…', waiting: 'Ödemeyi Gumroad sekmesinde tamamla. Pro birkaç saniye içinde burada kendiliğinden açılır.', done: 'Pro etkin! Sayfa yenileniyor…', lifetime: 'Zaten süresiz Pro’n var.', error: 'Ödeme başlatılamadı. Tekrar dene.', blocked: 'Yeni sekme engellendi. Ödemeyi aç:', open: 'Ödemeyi aç', cardOff: 'Kartla ödeme henüz yok. FunPay veya Telegram’ı kullan.' },
    fr: { title: 'Choisir Pro', sub: 'Paiement unique, sans renouvellement automatique. Les jours s’ajoutent à votre Pro actuel.', d1: '24 heures', d7: '7 jours', d30: '30 jours', d90: '90 jours', life: 'À vie', popular: 'Populaire', best: 'Meilleur prix', haveKey: 'J’ai déjà une clé', back: 'Offres', payTitle: 'Moyen de paiement', card: 'Carte ou PayPal', cardSub: 'Gumroad · Pro s’active automatiquement', auto: 'Automatique', manual: 'Manuel', soon: 'Bientôt', funpaySub: 'Activation manuelle : le vendeur envoie une clé à saisir ici', tg: 'Bot Telegram', tgSub: 'Manuel pour l’instant : le bot donne une clé à saisir ici', tgAuto: 'Stars, crypto ou virement · Pro s’active automatiquement', tgWaiting: 'Terminez le paiement dans le bot Telegram. Pro s’active ici tout seul en quelques secondes.', gotKey: 'Vous avez reçu une clé ? Saisissez-la ici', enterKey: 'Saisir la clé', login: 'Connectez-vous d’abord : Pro est ajouté à votre compte.', loginBtn: 'Se connecter', opening: 'Ouverture du paiement…', waiting: 'Terminez le paiement dans l’onglet Gumroad. Pro s’active ici tout seul en quelques secondes.', done: 'Pro est actif ! Rechargement…', lifetime: 'Vous avez déjà Pro à vie.', error: 'Impossible de lancer le paiement. Réessayez.', blocked: 'Le nouvel onglet a été bloqué. Ouvrez le paiement :', open: 'Ouvrir le paiement', cardOff: 'Le paiement par carte n’est pas encore disponible. Utilisez FunPay ou Telegram.' },
    uk: { title: 'Обери Pro', sub: 'Разова оплата, без автопродовження. Дні додаються до вже чинного Pro.', d1: '24 години', d7: '7 днів', d30: '30 днів', d90: '90 днів', life: 'Назавжди', popular: 'Популярний', best: 'Найвигідніше', haveKey: 'У мене вже є ключ', back: 'Тарифи', payTitle: 'Спосіб оплати', card: 'Картка або PayPal', cardSub: 'Gumroad · Pro увімкнеться автоматично', auto: 'Автоматично', manual: 'Вручну', soon: 'Незабаром', funpaySub: 'Активація вручну: продавець надішле ключ, його треба ввести тут', tg: 'Telegram-бот', tgSub: 'Поки вручну: бот видасть ключ, його треба ввести тут', tgAuto: 'Stars, крипта або переказ · Pro увімкнеться автоматично', tgWaiting: 'Заверши оплату в Telegram-боті. Pro увімкнеться тут сам за кілька секунд.', gotKey: 'Отримав ключ? Введи його тут', enterKey: 'Ввести ключ', login: 'Спочатку увійди: Pro додасться до твого акаунта.', loginBtn: 'Увійти', opening: 'Відкриваємо оплату…', waiting: 'Заверши оплату у вкладці Gumroad. Pro увімкнеться тут сам за кілька секунд.', done: 'Pro активовано! Оновлюємо сторінку…', lifetime: 'У тебе вже є Pro назавжди.', error: 'Не вдалося почати оплату. Спробуй ще раз.', blocked: 'Нову вкладку заблоковано. Відкрий оплату:', open: 'Відкрити оплату', cardOff: 'Оплата карткою поки недоступна. Скористайся FunPay або Telegram.' },
    es: { title: 'Elige Pro', sub: 'Pago único, sin renovación automática. Los días se suman a tu Pro actual.', d1: '24 horas', d7: '7 días', d30: '30 días', d90: '90 días', life: 'Para siempre', popular: 'Popular', best: 'Mejor precio', haveKey: 'Ya tengo una clave', back: 'Planes', payTitle: 'Forma de pago', card: 'Tarjeta o PayPal', cardSub: 'Gumroad · Pro se activa automáticamente', auto: 'Automático', manual: 'Manual', soon: 'Pronto', funpaySub: 'Activación manual: el vendedor envía una clave que introduces aquí', tg: 'Bot de Telegram', tgSub: 'Por ahora manual: el bot te da una clave que introduces aquí', tgAuto: 'Stars, cripto o transferencia · Pro se activa automáticamente', tgWaiting: 'Termina el pago en el bot de Telegram. Pro se activará aquí solo en unos segundos.', gotKey: '¿Recibiste una clave? Introdúcela aquí', enterKey: 'Introducir la clave', login: 'Inicia sesión primero: Pro se añade a tu cuenta.', loginBtn: 'Iniciar sesión', opening: 'Abriendo el pago…', waiting: 'Termina el pago en la pestaña de Gumroad. Pro se activará aquí solo en unos segundos.', done: '¡Pro está activo! Recargando…', lifetime: 'Ya tienes Pro para siempre.', error: 'No se pudo iniciar el pago. Inténtalo de nuevo.', blocked: 'Se bloqueó la pestaña nueva. Abre el pago:', open: 'Abrir el pago', cardOff: 'El pago con tarjeta aún no está disponible. Usa FunPay o Telegram.' },
    pt: { title: 'Escolha o Pro', sub: 'Pagamento único, sem renovação automática. Os dias somam ao Pro que você já tem.', d1: '24 horas', d7: '7 dias', d30: '30 dias', d90: '90 dias', life: 'Para sempre', popular: 'Popular', best: 'Melhor preço', haveKey: 'Já tenho uma chave', back: 'Planos', payTitle: 'Forma de pagamento', card: 'Cartão ou PayPal', cardSub: 'Gumroad · o Pro é ativado automaticamente', auto: 'Automático', manual: 'Manual', soon: 'Em breve', funpaySub: 'Ativação manual: o vendedor envia uma chave que você digita aqui', tg: 'Bot do Telegram', tgSub: 'Manual por enquanto: o bot dá uma chave que você digita aqui', tgAuto: 'Stars, cripto ou transferência · o Pro é ativado automaticamente', tgWaiting: 'Conclua o pagamento no bot do Telegram. O Pro será ativado aqui sozinho em alguns segundos.', gotKey: 'Recebeu uma chave? Digite aqui', enterKey: 'Digitar a chave', login: 'Entre primeiro: o Pro é adicionado à sua conta.', loginBtn: 'Entrar', opening: 'Abrindo o pagamento…', waiting: 'Conclua o pagamento na aba da Gumroad. O Pro será ativado aqui sozinho em alguns segundos.', done: 'O Pro está ativo! Recarregando…', lifetime: 'Você já tem o Pro para sempre.', error: 'Não foi possível iniciar o pagamento. Tente de novo.', blocked: 'A nova aba foi bloqueada. Abra o pagamento:', open: 'Abrir o pagamento', cardOff: 'O pagamento com cartão ainda não está disponível. Use FunPay ou Telegram.' }
  };
  var LABEL = { '1d': 'd1', '7d': 'd7', '30d': 'd30', '90d': 'd90', unlimited: 'life' };
  var BADGE = { '30d': 'popular', unlimited: 'best' };
  var FALLBACK = { ok: true, enabled: false, signed_in: false, plans: [
    { id: '1d', days: 1, price: '$0.99' }, { id: '7d', days: 7, price: '$1.99' }, { id: '30d', days: 30, price: '$3.99' },
    { id: '90d', days: 90, price: '$4.99' }, { id: 'unlimited', days: null, lifetime: true, price: '$5.99' }] };
  var state = { data: null, step: 'plans', plan: null, poll: null };

  function lang() {
    var l = (window.SMLang && SMLang.get ? SMLang.get() : document.documentElement.lang || 'en').slice(0, 2);
    return LANGS.indexOf(l) >= 0 ? l : 'en';
  }
  function t(key) { return COPY[lang()][key] || COPY.en[key] || key; }
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function svg(name) { return window.SSShell && SSShell.svg ? SSShell.svg(name) : ''; }

  (function css() {
    if (document.querySelector('link[data-pro-plans]')) return;
    var link = document.createElement('link');
    link.rel = 'stylesheet'; link.href = '/static/css/pro-plans.css?v=20261006-pay3'; link.dataset.proPlans = '1';
    document.head.appendChild(link);
  })();

  function load() {
    return fetch('/api/billing/plans', { credentials: 'same-origin', cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; })
      .then(function (data) { if (data && data.plans && data.plans.length) state.data = data; return state.data; });
  }
  function data() { return state.data || FALLBACK; }
  function plan(id) { return data().plans.filter(function (p) { return p.id === id; })[0] || null; }

  function nodes() {
    return { buy: document.getElementById('ssBuy'), key: document.getElementById('ssKeyPane'),
      card: document.querySelector('#ssActivation .ss-activation__card') };
  }

  function go(step, planId) {
    state.step = step;
    if (planId) state.plan = planId;
    render();
  }

  function render() {
    var n = nodes();
    if (!n.buy || !n.key) return;
    var keyStep = state.step === 'key';
    n.buy.hidden = keyStep; n.key.hidden = !keyStep;
    if (n.card) n.card.setAttribute('aria-labelledby', keyStep ? 'ssActivationTitle' : 'ssBuyTitle');
    if (keyStep) {
      if (!n.key.querySelector('.ss-buy__back')) n.key.prepend(backButton());
      else n.key.querySelector('.ss-buy__back').lastChild.textContent = t('back');
      setTimeout(function () { var input = document.getElementById('ssActivationCode'); if (input) input.focus(); }, 40);
      return;
    }
    n.buy.replaceChildren();
    if (state.step === 'pay' && plan(state.plan)) renderPay(n.buy); else renderPlans(n.buy);
  }

  function backButton() {
    var b = el('button', 'ss-buy__back'); b.type = 'button';
    b.append(el('span', null, '←'), document.createTextNode(t('back')));
    b.addEventListener('click', function () { go('plans'); });
    return b;
  }

  function head(box, title, sub) {
    box.append(el('div', 'ss-buy__icon')); box.lastChild.innerHTML = svg('key');
    box.append(el('p', 'ss-auth__eyebrow', 'SHOWCASE MAKER / PRO'));
    var h = el('h2', 'ss-buy__title', title); h.id = 'ssBuyTitle'; box.append(h);
    if (sub) box.append(el('p', 'ss-auth__sub ss-buy__sub', sub));
  }

  function renderPlans(box) {
    var d = data(), lifetime = d.pro && d.pro.lifetime;
    head(box, t('title'), t('sub'));
    var grid = el('div', 'ss-plans__grid');
    d.plans.forEach(function (p) {
      var b = el('button', 'ss-plans__plan' + (p.lifetime ? ' is-life' : ''));
      b.type = 'button'; b.dataset.plan = p.id; b.disabled = !!lifetime;
      if (BADGE[p.id]) b.append(el('span', 'ss-plans__badge', t(BADGE[p.id])));
      b.append(el('span', 'ss-plans__term', t(LABEL[p.id] || p.id)), el('b', 'ss-plans__price', p.price || '—'));
      b.addEventListener('click', function () { go('pay', p.id); });
      grid.append(b);
    });
    box.append(grid);
    if (lifetime) box.append(el('p', 'ss-plans__status is-ok', t('lifetime')));
    var key = el('button', 'ss-buy__key', t('haveKey')); key.type = 'button';
    key.addEventListener('click', function () { go('key'); });
    box.append(key);
  }

  function renderPay(box) {
    var d = data(), p = plan(state.plan);
    box.append(backButton());
    head(box, t('payTitle'));
    var chosen = el('div', 'ss-buy__chosen');
    chosen.append(el('span', null, t(LABEL[p.id] || p.id)), el('b', null, p.price || ''));
    var change = el('button', 'ss-buy__change', '✎'); change.type = 'button'; change.setAttribute('aria-label', t('back'));
    change.addEventListener('click', function () { go('plans'); });
    chosen.append(change);
    box.append(chosen);

    var list = el('div', 'ss-pay');
    list.append(option({ kind: 'card', icon: svg('card'), title: t('card'), sub: t('cardSub'),
      tag: p.checkout ? t('auto') : t('soon'), tagKind: p.checkout ? 'auto' : 'off', disabled: !p.checkout,
      onClick: function () { buy(p.id); } }));
    list.append(option({ kind: 'funpay', icon: '<img src="/static/img/funpay-favicon.ico" alt="">', title: 'FunPay',
      sub: t('funpaySub'), tag: t('manual'), tagKind: 'manual', href: FUNPAY_URL, onClick: manualHint }));
    // The bot switches Pro on by itself when the server is linked to it; otherwise it still hands out a key.
    var tgAuto = !!d.telegram;
    list.append(option({ kind: 'telegram', icon: '<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><circle cx="12" cy="12" r="12" fill="#229ED9"/><path fill="#fff" d="M17.6 7.2 15.7 16.6c-.14.64-.52.8-1.06.5l-2.9-2.14-1.4 1.35c-.16.16-.29.29-.6.29l.21-3 5.45-4.92c.24-.21-.05-.33-.37-.12L8.3 12.8l-2.9-.9c-.63-.2-.64-.63.13-.93l11.3-4.36c.52-.19.98.13.8.59Z"/></svg>',
      title: t('tg'), sub: t(tgAuto ? 'tgAuto' : 'tgSub'), tag: t(tgAuto ? 'auto' : 'manual'), tagKind: tgAuto ? 'auto' : 'manual',
      href: tgAuto ? null : TELEGRAM_URL, onClick: tgAuto ? function () { buyTelegram(p.id); } : manualHint }));
    box.append(list);
    var line = el('p', 'ss-plans__status'); line.id = 'ssPlansStatus'; line.setAttribute('aria-live', 'polite');
    box.append(line);
    if (!p.checkout && !d.enabled) status(t('cardOff'));
    var key = el('button', 'ss-buy__key', t('haveKey')); key.type = 'button';
    key.addEventListener('click', function () { go('key'); });
    box.append(key);
  }

  function option(o) {
    var node = o.href ? el('a', 'ss-pay__opt') : el('button', 'ss-pay__opt');
    node.classList.add('ss-pay__opt--' + o.kind);
    if (o.href) { node.href = o.href; node.target = '_blank'; node.rel = 'noopener'; } else { node.type = 'button'; node.disabled = !!o.disabled; }
    var icon = el('span', 'ss-pay__icon'); icon.innerHTML = o.icon || '';
    var text = el('span', 'ss-pay__text'); text.append(el('b', null, o.title), el('small', null, o.sub));
    node.append(icon, text, el('span', 'ss-pay__tag is-' + o.tagKind, o.tag));
    if (o.onClick) node.addEventListener('click', function (event) { if (!o.href) event.preventDefault(); o.onClick(event); });
    return node;
  }

  function status(text, kind) {
    var line = document.getElementById('ssPlansStatus');
    if (!line) return;
    line.replaceChildren();
    if (text && typeof text === 'object') line.append(text); else line.textContent = text || '';
    line.className = 'ss-plans__status' + (kind ? ' is-' + kind : '');
  }

  function manualHint() {
    var wrap = el('span'), button = el('button', 'ss-plans__link', t('enterKey')); button.type = 'button';
    button.addEventListener('click', function () { go('key'); });
    wrap.append(t('gotKey') + ' → ', button);
    status(wrap);
  }

  function loginHint() {
    var wrap = el('span'), button = el('button', 'ss-plans__link', t('loginBtn')); button.type = 'button';
    button.addEventListener('click', function () {
      if (window.SSShell) { SSShell.closeActivation && SSShell.closeActivation(); SSShell.openAuth && SSShell.openAuth('login'); }
    });
    wrap.append(t('login') + ' ', button);
    status(wrap, 'wait');
  }

  function buy(planId) { checkout(planId, '/api/billing/gumroad/order', 'waiting'); }
  function buyTelegram(planId) { checkout(planId, '/api/billing/telegram/order', 'tgWaiting'); }

  // Both checkouts are bound to the signed-in account by the server, which answers with the URL to open.
  function checkout(planId, endpoint, waitingKey) {
    var d = data();
    if (!d.signed_in) { loginHint(); return; }
    if (d.pro && d.pro.lifetime) { status(t('lifetime'), 'ok'); return; }
    // Open the tab inside the click so pop-up blockers allow it, then point it at the checkout.
    var tab = null;
    try { tab = window.open('', '_blank'); } catch (e) { tab = null; }
    status(t('opening'), 'wait');
    fetch(endpoint, {
      method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plan: planId })
    }).then(function (r) { return r.json().catch(function () { return {}; }).then(function (body) { return { ok: r.ok, body: body }; }); })
      .then(function (res) {
        if (!res.ok || !res.body || !res.body.url) throw new Error((res.body && res.body.code) || 'order');
        var url = res.body.url;
        if (tab && !tab.closed) { try { tab.opener = null; } catch (e) {} tab.location.href = url; status(t(waitingKey), 'wait'); }
        else {
          var wrap = el('span'), link = el('a', 'ss-plans__link', t('open'));
          link.href = url; link.target = '_blank'; link.rel = 'noopener';
          wrap.append(t('blocked') + ' ', link); status(wrap, 'wait');
        }
        watch();
      })
      .catch(function (err) {
        if (tab && !tab.closed) tab.close();
        var code = String(err && err.message);
        if (code === 'login') { if (state.data) state.data.signed_in = false; loginHint(); return; }
        if (code === 'lifetime') { status(t('lifetime'), 'ok'); return; }
        status(t('error'), 'bad');
      });
  }

  // Wait for the Ping: poll the account's Pro state while the dialog stays open (up to 15 minutes).
  function watch() {
    var before = JSON.stringify(data().pro || null), started = Date.now();
    clearInterval(state.poll);
    state.poll = setInterval(function () {
      var dialog = document.getElementById('ssActivation');
      if (Date.now() - started > 15 * 60 * 1000 || !dialog || !dialog.classList.contains('is-open')) { clearInterval(state.poll); return; }
      fetch('/api/billing/plans', { credentials: 'same-origin', cache: 'no-store' })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (fresh) {
          if (fresh && fresh.pro && fresh.pro.pro && JSON.stringify(fresh.pro) !== before) {
            clearInterval(state.poll);
            status(t('done'), 'ok');
            setTimeout(function () { location.reload(); }, 1500);
          }
        }).catch(function () {});
    }, 4000);
  }

  // opts.plan -> straight to the payment step for that plan; opts.key -> the key form.
  function show(opts) {
    opts = opts || {};
    clearInterval(state.poll);
    state.step = opts.key ? 'key' : (opts.plan ? 'pay' : 'plans');
    state.plan = opts.plan || null;
    render();
    var before = JSON.stringify(data());
    // Re-draw only when the server's prices or Pro state differ, so a status line is not wiped.
    load().then(function () { if (state.step !== 'key' && JSON.stringify(data()) !== before) render(); });
  }

  window.addEventListener('sm:langchange', function () {
    var dialog = document.getElementById('ssActivation');
    if (dialog && dialog.classList.contains('is-open')) render();
  });
  window.SMProPlans = { show: show, reload: function () { return load().then(render); } };
})();
