/* News pages: opening /news marks the news as seen (the dot on "News" and the bell count
   clear), and the article's "Copy link" button. */
(function () {
  'use strict';
  function markSeen() {
    fetch('/api/news/seen', { method: 'POST', credentials: 'same-origin' }).then(function () {
      var me = Object.assign({}, window.SS_ME || {});
      if (!me.logged_in) return;
      me.unread = Math.max(0, Number(me.unread || 0) - Number(me.news_unread || 0));
      me.news_unread = 0; me.news_dot = false; window.SS_ME = me;
      if (window.SSShell && SSShell.paintCounters) SSShell.paintCounters(me);
    }).catch(function () {});
  }
  document.addEventListener('ss:me', function (event) { if (event.detail && event.detail.logged_in && event.detail.news_dot) markSeen(); });
  if (window.SS_ME && window.SS_ME.logged_in && window.SS_ME.news_dot) markSeen();
  document.addEventListener('click', function (event) {
    var button = event.target.closest('[data-nw-copy]');
    if (!button) return;
    var done = function () { var label = button.textContent; button.textContent = button.dataset.nwCopied; setTimeout(function () { button.textContent = label; }, 1800); };
    if (navigator.clipboard) navigator.clipboard.writeText(button.dataset.nwCopy).then(done).catch(function () {});
  });
})();
