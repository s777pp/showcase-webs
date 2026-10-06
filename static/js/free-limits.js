/* Free-plan allowances in the tools (2026-10-06, server side: smweb/free_limits.py).
   - Reads /api/quota ("free": weekly tries left, beta features, when the limits renew) and keeps it in SMLimits.
   - Draws a note at the top of every tool that is weekly on the Free plan (loop, design, doctor, dna, da, bg)
     or in beta (Pro only), so the limit is visible before it is hit.
   - When any API call is refused for a spent allowance (the answer carries "limit": {kind, feature, resets_at}),
     opens one dialog with the ways out: wait, 2 free hours of Pro in the Telegram bot, Pro for 24 hours, all plans.
   Other scripts ask SMLimits.canUse(feature) and listen for the "sm:limits" event. Styles: css/free-limits.css. */
(function () {
  'use strict';
  if (window.SMLimits) return;
  var LANGS = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'];
  var TRIAL_URL = 'https://t.me/SteamMakerBot';
  var COPY = {
    en: { weeklyOpen: 'Free plan: once a week. This week’s use is still available.', weeklySpent: 'Free plan: once a week. This week’s use is spent, the next one opens on {date}.', weeklyGuest: 'Free with an account: once a week. Log in to use it.', betaNote: 'Beta tool: available with Pro only for now.', bgOpen: 'Free: 1 removal a week, still available', bgSpent: 'Free: 1 removal a week, next on {date}', noLimit: 'No limit with Pro', getPro: 'Get Pro', titleWeekly: 'This week’s free use is spent', titleDaily: 'Today’s free files are spent', titleBuilder: 'Today’s free exports are spent', titleBeta: 'This tool is Pro only for now', renews: 'It renews on {date}.', betaText: 'New tools start in beta. While a tool is in beta it is available with Pro only.', ways: 'What you can do', day: 'Pro for 24 hours', daySub: 'One payment, no auto-renewal', trial: '2 hours of Pro for free', trialSub: 'In the Telegram bot, once per person', plans: 'All plans', wait: 'I’ll wait', close: 'Close' },
    ru: { weeklyOpen: 'Бесплатный тариф: раз в неделю. Попытка на этой неделе ещё не использована.', weeklySpent: 'Бесплатный тариф: раз в неделю. Попытка на этой неделе использована, следующая — {date}.', weeklyGuest: 'Бесплатно с аккаунтом: раз в неделю. Войди, чтобы пользоваться.', betaNote: 'Инструмент в бета-тесте: пока доступен только с Pro.', bgOpen: 'Бесплатно: 1 удаление в неделю, ещё доступно', bgSpent: 'Бесплатно: 1 удаление в неделю, следующее — {date}', noLimit: 'С Pro без лимита', getPro: 'Купить Pro', titleWeekly: 'Бесплатная попытка на этой неделе использована', titleDaily: 'Бесплатные файлы на сегодня закончились', titleBuilder: 'Бесплатные экспорты на сегодня закончились', titleBeta: 'Этот инструмент пока только для Pro', renews: 'Лимит обновится: {date}.', betaText: 'Новые инструменты сначала выходят в бета-тесте. Пока инструмент в бете, он доступен только с Pro.', ways: 'Что можно сделать', day: 'Pro на 24 часа', daySub: 'Разовая оплата, без автопродления', trial: '2 часа Pro бесплатно', trialSub: 'В Telegram-боте, один раз на человека', plans: 'Все тарифы', wait: 'Подожду', close: 'Закрыть' },
    de: { weeklyOpen: 'Kostenloser Tarif: einmal pro Woche. Der Versuch dieser Woche ist noch frei.', weeklySpent: 'Kostenloser Tarif: einmal pro Woche. Der Versuch dieser Woche ist verbraucht, der nächste öffnet am {date}.', weeklyGuest: 'Kostenlos mit Konto: einmal pro Woche. Melde dich an, um es zu nutzen.', betaNote: 'Beta-Werkzeug: vorerst nur mit Pro verfügbar.', bgOpen: 'Kostenlos: 1 Entfernung pro Woche, noch verfügbar', bgSpent: 'Kostenlos: 1 Entfernung pro Woche, nächste am {date}', noLimit: 'Mit Pro ohne Limit', getPro: 'Pro holen', titleWeekly: 'Der kostenlose Versuch dieser Woche ist verbraucht', titleDaily: 'Die kostenlosen Dateien für heute sind verbraucht', titleBuilder: 'Die kostenlosen Exporte für heute sind verbraucht', titleBeta: 'Dieses Werkzeug gibt es vorerst nur mit Pro', renews: 'Das Limit wird am {date} erneuert.', betaText: 'Neue Werkzeuge starten in der Beta. Solange ein Werkzeug in der Beta ist, gibt es es nur mit Pro.', ways: 'Das kannst du tun', day: 'Pro für 24 Stunden', daySub: 'Einmalzahlung, keine automatische Verlängerung', trial: '2 Stunden Pro kostenlos', trialSub: 'Im Telegram-Bot, einmal pro Person', plans: 'Alle Tarife', wait: 'Ich warte', close: 'Schließen' },
    tr: { weeklyOpen: 'Ücretsiz plan: haftada bir kez. Bu haftaki hakkın hâlâ duruyor.', weeklySpent: 'Ücretsiz plan: haftada bir kez. Bu haftaki hak kullanıldı, sonraki {date} açılır.', weeklyGuest: 'Hesapla ücretsiz: haftada bir kez. Kullanmak için giriş yap.', betaNote: 'Beta aracı: şimdilik yalnızca Pro ile kullanılabilir.', bgOpen: 'Ücretsiz: haftada 1 kaldırma, hâlâ kullanılabilir', bgSpent: 'Ücretsiz: haftada 1 kaldırma, sonraki {date}', noLimit: 'Pro ile sınırsız', getPro: 'Pro al', titleWeekly: 'Bu haftaki ücretsiz hak kullanıldı', titleDaily: 'Bugünkü ücretsiz dosyalar bitti', titleBuilder: 'Bugünkü ücretsiz dışa aktarımlar bitti', titleBeta: 'Bu araç şimdilik yalnızca Pro’da', renews: 'Sınır {date} yenilenir.', betaText: 'Yeni araçlar önce beta olarak çıkar. Bir araç betadayken yalnızca Pro ile kullanılabilir.', ways: 'Ne yapabilirsin', day: '24 saatlik Pro', daySub: 'Tek seferlik ödeme, otomatik yenileme yok', trial: '2 saat ücretsiz Pro', trialSub: 'Telegram botunda, kişi başına bir kez', plans: 'Tüm planlar', wait: 'Beklerim', close: 'Kapat' },
    fr: { weeklyOpen: 'Offre gratuite : une fois par semaine. L’essai de cette semaine est encore disponible.', weeklySpent: 'Offre gratuite : une fois par semaine. L’essai de cette semaine est utilisé, le prochain s’ouvre le {date}.', weeklyGuest: 'Gratuit avec un compte : une fois par semaine. Connectez-vous pour l’utiliser.', betaNote: 'Outil en bêta : disponible uniquement avec Pro pour l’instant.', bgOpen: 'Gratuit : 1 suppression par semaine, encore disponible', bgSpent: 'Gratuit : 1 suppression par semaine, prochaine le {date}', noLimit: 'Sans limite avec Pro', getPro: 'Obtenir Pro', titleWeekly: 'L’essai gratuit de cette semaine est utilisé', titleDaily: 'Les fichiers gratuits d’aujourd’hui sont utilisés', titleBuilder: 'Les exports gratuits d’aujourd’hui sont utilisés', titleBeta: 'Cet outil est réservé à Pro pour l’instant', renews: 'La limite se renouvelle le {date}.', betaText: 'Les nouveaux outils démarrent en bêta. Tant qu’un outil est en bêta, il n’est disponible qu’avec Pro.', ways: 'Ce que vous pouvez faire', day: 'Pro pour 24 heures', daySub: 'Paiement unique, sans renouvellement automatique', trial: '2 heures de Pro gratuites', trialSub: 'Dans le bot Telegram, une fois par personne', plans: 'Toutes les offres', wait: 'J’attendrai', close: 'Fermer' },
    uk: { weeklyOpen: 'Безкоштовний тариф: раз на тиждень. Спробу цього тижня ще не використано.', weeklySpent: 'Безкоштовний тариф: раз на тиждень. Спробу цього тижня використано, наступна — {date}.', weeklyGuest: 'Безкоштовно з акаунтом: раз на тиждень. Увійди, щоб користуватися.', betaNote: 'Інструмент у бета-тесті: поки доступний лише з Pro.', bgOpen: 'Безкоштовно: 1 видалення на тиждень, ще доступне', bgSpent: 'Безкоштовно: 1 видалення на тиждень, наступне — {date}', noLimit: 'З Pro без ліміту', getPro: 'Купити Pro', titleWeekly: 'Безкоштовну спробу цього тижня використано', titleDaily: 'Безкоштовні файли на сьогодні закінчилися', titleBuilder: 'Безкоштовні експорти на сьогодні закінчилися', titleBeta: 'Цей інструмент поки лише для Pro', renews: 'Ліміт оновиться: {date}.', betaText: 'Нові інструменти спершу виходять у бета-тесті. Поки інструмент у беті, він доступний лише з Pro.', ways: 'Що можна зробити', day: 'Pro на 24 години', daySub: 'Разова оплата, без автопродовження', trial: '2 години Pro безкоштовно', trialSub: 'У Telegram-боті, один раз на людину', plans: 'Усі тарифи', wait: 'Зачекаю', close: 'Закрити' },
    es: { weeklyOpen: 'Plan gratuito: una vez por semana. El uso de esta semana sigue disponible.', weeklySpent: 'Plan gratuito: una vez por semana. El uso de esta semana está gastado, el siguiente se abre el {date}.', weeklyGuest: 'Gratis con una cuenta: una vez por semana. Inicia sesión para usarlo.', betaNote: 'Herramienta en beta: por ahora solo disponible con Pro.', bgOpen: 'Gratis: 1 eliminación por semana, aún disponible', bgSpent: 'Gratis: 1 eliminación por semana, la siguiente el {date}', noLimit: 'Sin límite con Pro', getPro: 'Obtener Pro', titleWeekly: 'El uso gratuito de esta semana está gastado', titleDaily: 'Los archivos gratuitos de hoy están gastados', titleBuilder: 'Las exportaciones gratuitas de hoy están gastadas', titleBeta: 'Por ahora esta herramienta es solo para Pro', renews: 'El límite se renueva el {date}.', betaText: 'Las herramientas nuevas empiezan en beta. Mientras una herramienta está en beta, solo está disponible con Pro.', ways: 'Qué puedes hacer', day: 'Pro por 24 horas', daySub: 'Pago único, sin renovación automática', trial: '2 horas de Pro gratis', trialSub: 'En el bot de Telegram, una vez por persona', plans: 'Todos los planes', wait: 'Esperaré', close: 'Cerrar' },
    pt: { weeklyOpen: 'Plano gratuito: uma vez por semana. O uso desta semana ainda está disponível.', weeklySpent: 'Plano gratuito: uma vez por semana. O uso desta semana foi gasto, o próximo abre em {date}.', weeklyGuest: 'Grátis com uma conta: uma vez por semana. Entre para usar.', betaNote: 'Ferramenta em beta: por enquanto disponível só com o Pro.', bgOpen: 'Grátis: 1 remoção por semana, ainda disponível', bgSpent: 'Grátis: 1 remoção por semana, a próxima em {date}', noLimit: 'Sem limite com o Pro', getPro: 'Obter o Pro', titleWeekly: 'O uso gratuito desta semana foi gasto', titleDaily: 'Os arquivos gratuitos de hoje acabaram', titleBuilder: 'As exportações gratuitas de hoje acabaram', titleBeta: 'Por enquanto esta ferramenta é só para o Pro', renews: 'O limite renova em {date}.', betaText: 'Ferramentas novas começam em beta. Enquanto uma ferramenta está em beta, ela só está disponível com o Pro.', ways: 'O que você pode fazer', day: 'Pro por 24 horas', daySub: 'Pagamento único, sem renovação automática', trial: '2 horas de Pro grátis', trialSub: 'No bot do Telegram, uma vez por pessoa', plans: 'Todos os planos', wait: 'Vou esperar', close: 'Fechar' }
  };
  // Where each note goes: a tab of the app, or (bg) right after the Builder's AI button.
  var TAB_NOTES = { loop: 'tab-loop', design: 'tab-design-ai', doctor: 'tab-doctor', dna: 'tab-dna', da: 'tab-da' };
  var BETA_TABS = { gifopt: 'tab-gifopt' };
  // A successful start of a weekly tool: keep it open for this page view and re-read the counters.
  var STARTS = [[/\/api\/loop\/start/, 'loop'], [/\/api\/profile-insights\/start/, null], [/\/api\/steam-dna\/analyze/, 'dna'],
    [/\/api\/da\/upload/, 'da'], [/\/api\/builder\/remove-background$/, 'bg'], [/\/api\/builder\/reserve-export/, null],
    [/\/api\/process\/start/, null], [/\/api\/workshop-studio\/start/, null]];
  var state = null, grace = {}, wallAt = 0, timer = null;

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
  function when(seconds, withTime) {
    if (!seconds) return '';
    var options = withTime ? { weekday: 'long', hour: '2-digit', minute: '2-digit' } : { weekday: 'long', day: 'numeric', month: 'long' };
    try { return new Date(seconds * 1000).toLocaleString(lang(), options); } catch (e) { return new Date(seconds * 1000).toLocaleDateString(); }
  }

  (function css() {
    if (document.querySelector('link[data-free-limits]')) return;
    var link = document.createElement('link');
    link.rel = 'stylesheet'; link.href = '/static/css/free-limits.css?v=20261006-fl1'; link.dataset.freeLimits = '1';
    document.head.appendChild(link);
  })();

  // ---------------------------------------------------------------- state
  function free() { return (state && state.free) || null; }
  function isPro() { return !!(state && state.pro); }
  function weekly(feature) { var f = free(); return f && f.weekly && f.weekly[feature] ? f.weekly[feature] : null; }
  function isBeta(feature) { var f = free(); return !!(f && f.beta && f.beta.indexOf(feature) >= 0); }
  /* May a Free account use this weekly tool now? True for Pro, while a use is left, and after a use was
     spent in this page view (so the tool does not lock itself while its own job is still running). */
  function canUse(feature) {
    if (!state) return false;
    if (isPro()) return true;
    if (isBeta(feature)) return false;
    var item = weekly(feature);
    return !!grace[feature] || !!(item && item.left > 0 && state.user_id);
  }
  function refresh() {
    return fetch('/api/quota', { credentials: 'same-origin', cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) { if (data) { state = data; paint(); window.dispatchEvent(new Event('sm:limits')); } return state; })
      .catch(function () { return state; });
  }
  function soon() { clearTimeout(timer); timer = setTimeout(refresh, 900); }

  // ---------------------------------------------------------------- notes inside the tools
  function buy(plan) {
    if (window.SSShell && SSShell.openActivation) SSShell.openActivation(plan ? { plan: plan } : {});
    else location.href = (window.SMLang && SMLang.url ? SMLang.url('/') : '/') + '#pricing';
  }
  function noteNode(host, feature) {
    var node = host.querySelector(':scope > .fl-note[data-fl="' + feature + '"]');
    if (!node) { node = el('div', 'fl-note'); node.dataset.fl = feature; node.setAttribute('role', 'note'); host.prepend(node); }
    return node;
  }
  function fill(node, kind, text, actionText, onAction) {
    node.hidden = false;
    node.className = 'fl-note is-' + kind;
    node.replaceChildren(el('span', 'fl-note__dot'), el('span', 'fl-note__text', text));
    if (actionText) {
      var b = el('button', 'fl-note__btn', actionText); b.type = 'button';
      b.addEventListener('click', onAction);
      node.append(b);
    }
  }
  function paint() {
    if (!state) return;
    Object.keys(TAB_NOTES).forEach(function (feature) {
      var host = document.getElementById(TAB_NOTES[feature]);
      if (!host) return;
      var node = noteNode(host, feature), item = weekly(feature);
      if (isPro() || !item) { node.hidden = true; return; }
      if (!state.user_id) { fill(node, 'open', t('weeklyGuest')); return; }
      if (item.left > 0) fill(node, 'open', t('weeklyOpen'), t('noLimit'), function () { buy(); });
      else fill(node, 'spent', t('weeklySpent', { date: when(free().week_resets_at) }), t('getPro'),
        function () { wall({ kind: 'weekly', feature: feature, resets_at: free().week_resets_at }); });
    });
    Object.keys(BETA_TABS).forEach(function (feature) {
      var host = document.getElementById(BETA_TABS[feature]);
      if (!host) return;
      var node = noteNode(host, feature);
      if (isPro() || !isBeta(feature)) { node.hidden = true; return; }
      fill(node, 'beta', t('betaNote'), t('getPro'), function () { wall({ kind: 'beta', feature: feature }); });
    });
    var ai = document.getElementById('builderAiRemove');
    if (ai && ai.parentNode) {
      var hint = ai.parentNode.querySelector('.fl-inline');
      if (!hint) { hint = el('small', 'fl-inline'); ai.insertAdjacentElement('afterend', hint); }
      var bg = weekly('bg');
      hint.hidden = isPro() || !bg;
      if (!hint.hidden) hint.textContent = bg.left > 0 ? t('bgOpen') : t('bgSpent', { date: when(free().week_resets_at) });
    }
  }

  // ---------------------------------------------------------------- the dialog
  function closeWall() {
    var open = document.getElementById('flWall');
    if (!open) return;
    document.removeEventListener('keydown', onKey);
    var back = open._returnFocus;
    open.remove();
    if (back && back.focus) { try { back.focus(); } catch (e) {} }
  }
  function onKey(event) { if (event.key === 'Escape') closeWall(); }
  function choice(cls, title, sub, onClick, href) {
    var node = href ? el('a', 'fl-wall__opt ' + cls) : el('button', 'fl-wall__opt ' + cls);
    if (href) { node.href = href; node.target = '_blank'; node.rel = 'noopener'; } else node.type = 'button';
    var text = el('span', 'fl-wall__opt-text'); text.append(el('b', null, title));
    if (sub) text.append(el('small', null, sub));
    node.append(text, el('span', 'fl-wall__arrow', '→'));
    node.addEventListener('click', function () { closeWall(); if (onClick) onClick(); });
    return node;
  }
  function wall(limit) {
    limit = limit || {};
    if (isPro() || document.getElementById('flWall')) return;
    var kind = limit.kind || 'weekly';
    var title = { weekly: 'titleWeekly', daily: 'titleDaily', builder: 'titleBuilder', beta: 'titleBeta' }[kind] || 'titleWeekly';
    var root = el('div', 'fl-wall'); root.id = 'flWall';
    root._returnFocus = document.activeElement;
    var card = el('div', 'fl-wall__card'); card.setAttribute('role', 'dialog'); card.setAttribute('aria-modal', 'true'); card.setAttribute('aria-labelledby', 'flWallTitle');
    var x = el('button', 'fl-wall__close', '×'); x.type = 'button'; x.setAttribute('aria-label', t('close')); x.addEventListener('click', closeWall);
    var h = el('h2', 'fl-wall__title', t(title)); h.id = 'flWallTitle';
    var text = kind === 'beta' ? t('betaText') : (limit.resets_at ? t('renews', { date: when(limit.resets_at, kind !== 'weekly') }) : '');
    card.append(x, el('p', 'fl-wall__eyebrow', 'SHOWCASE MAKER / FREE'), h);
    if (text) card.append(el('p', 'fl-wall__text', text));
    card.append(el('p', 'fl-wall__ways', t('ways')));
    var list = el('div', 'fl-wall__list');
    list.append(choice('is-main', t('day'), t('daySub'), function () { buy('1d'); }));
    list.append(choice('', t('trial'), t('trialSub'), null, TRIAL_URL));
    list.append(choice('', t('plans'), '', function () { buy(); }));
    card.append(list);
    if (kind !== 'beta') { var later = el('button', 'fl-wall__wait', t('wait')); later.type = 'button'; later.addEventListener('click', closeWall); card.append(later); }
    root.append(card);
    root.addEventListener('mousedown', function (event) { if (event.target === root) closeWall(); });
    document.body.append(root);
    document.addEventListener('keydown', onKey);
    var first = card.querySelector('.fl-wall__opt'); if (first) first.focus();
    wallAt = Date.now();
  }

  // ---------------------------------------------------------------- watch API answers
  function watch(url, response) {
    if (response.status === 403 || response.status === 429) {
      response.clone().json().then(function (body) {
        if (!body || !body.limit || !body.limit.kind) return;
        soon();
        if (Date.now() - wallAt > 1500) wall(body.limit);
      }).catch(function () {});
      return;
    }
    if (!response.ok) return;
    for (var i = 0; i < STARTS.length; i++) {
      if (STARTS[i][0].test(url)) { if (STARTS[i][1]) grace[STARTS[i][1]] = true; soon(); return; }
    }
  }
  if (typeof window.fetch === 'function' && !window.fetch._smLimits) {
    var nativeFetch = window.fetch;
    var wrapped = function (input, init) {
      var promise = nativeFetch.apply(this, arguments);
      try {
        var url = typeof input === 'string' ? input : (input && input.url) || '';
        var path = url.indexOf(location.origin) === 0 ? url.slice(location.origin.length) : url;
        var method = String((init && init.method) || (input && input.method) || 'GET').toUpperCase();
        if (path.indexOf('/api/') === 0 && method !== 'GET') {
          promise.then(function (response) { try { watch(path.split('?')[0], response); } catch (e) {} }, function () {});
        }
      } catch (e) {}
      return promise;
    };
    wrapped._smLimits = true;
    window.fetch = wrapped;
  }

  window.SMLimits = { canUse: canUse, isBeta: isBeta, refresh: refresh, wall: wall, state: function () { return state; }, t: t };
  window.addEventListener('sm:langchange', function () { paint(); });
  document.addEventListener('click', function (event) {
    if (event.target.closest && event.target.closest('#nav [data-tab], [data-tu-open], .tu-tool')) setTimeout(paint, 60);
  });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', refresh); else refresh();
  window.addEventListener('focus', soon);
})();
