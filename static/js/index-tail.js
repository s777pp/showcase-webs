// index.html L2820-2878
(function(){
  var FUNPAY_URL = 'https://funpay.com/lots/offer?id=76420307';
  var TG_URL = 'https://t.me/SteamMakerBot';

  function i18nBuy(){
    var lang = SMLang.get();
    var ru = lang === 'ru';
    var t = document.getElementById('smBuyTitle');
    var s = document.getElementById('smBuySub');
    var fd = document.getElementById('smBuyFunpayD');
    var td = document.getElementById('smBuyTgD');
    var ct = document.getElementById('smBuyCardT');
    var cd = document.getElementById('smBuyCardD');
    var c = document.getElementById('smBuyClose');
    if (t) t.textContent = ru ? 'Купить Pro-ключ' : 'Buy Pro key';
    if (s) s.textContent = ru
      ? 'Выбери, где купить. После оплаты активируй код в аккаунте.'
      : 'Choose where to buy. After payment, activate the code in your account.';
    if (fd) fd.textContent = ru ? 'Код сразу после оплаты' : 'Instant code after payment';
    if (td) td.textContent = ru ? 'Через бота / поддержку' : 'Buy via bot / support';
    if (ct) ct.textContent = ru ? 'Оплата картой' : 'Pay by card';
    if (cd) cd.textContent = ru ? 'Банковская карта · защищённая оплата' : 'Bank card · secure checkout';
    if (c) c.textContent = ru ? 'Закрыть' : 'Close';
  }

  window.openBuyKeyModal = function openBuyKeyModal(e){
    if (e && e.preventDefault) e.preventDefault();
    if (window.SSShell && typeof window.SSShell.openActivation === 'function') {
      window.SSShell.openActivation();
      return;
    }
    var ov = document.getElementById('smBuyOverlay');
    if (!ov) return;
    i18nBuy();
    var fp = document.getElementById('smBuyFunpay');
    var tg = document.getElementById('smBuyTg');
    var card = document.getElementById('smBuyCard');
    if (fp) fp.href = FUNPAY_URL;
    if (tg) tg.href = TG_URL;
    if (card) card.href = 'https://store.showcasemaker.com';
    ov.classList.add('open');
    ov.setAttribute('aria-hidden', 'false');
  };
  window.closeBuyKeyModal = function(){
    var ov = document.getElementById('smBuyOverlay');
    if (!ov) return;
    ov.classList.remove('open');
    ov.setAttribute('aria-hidden', 'true');
  };

  function bind(){
    var ov = document.getElementById('smBuyOverlay');
    if (!ov) return;
    var closeBtn = document.getElementById('smBuyClose');
    if (closeBtn) closeBtn.onclick = window.closeBuyKeyModal;
    ov.addEventListener('click', function(ev){
      if (ev.target === ov) window.closeBuyKeyModal();
    });
    document.addEventListener('keydown', function(ev){
      if (ev.key === 'Escape') window.closeBuyKeyModal();
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bind);
  else bind();
})();
// index.html L2879-2886
document.querySelectorAll('[data-buy-key]').forEach(function(a){
  a.addEventListener('click', function(e){
    e.preventDefault();
    if (typeof openBuyKeyModal==='function') openBuyKeyModal(e);
  });
});
