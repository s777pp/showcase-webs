(function () {
  'use strict';
  var embedded = new URLSearchParams(location.search).get('embed') === 'tools';
  if (embedded) document.documentElement.classList.add('profile-embedded');
  function ready() {
    // Keep offscreen content pending; reveal only inside the reading area.
    if (document.body.classList.contains('page-home') &&
        !matchMedia('(prefers-reduced-motion: reduce)').matches && window.IntersectionObserver) {
      var motion = matchMedia('(prefers-reduced-motion: reduce)');
      var reveal = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting || document.hidden) return;
          reveal.unobserve(entry.target);
          entry.target.setAttribute('data-home-visible', 'true');
        });
      }, { threshold: 0, rootMargin: '0px 0px -14% 0px' });
      var targets = document.querySelectorAll('.hero h1,.hero>p,.hero-cta,.hero-studio,.mock-frame,.grid2 h2,.grid2 .lead,.subc,.subc .h,.subc li,.q-card,.q-card blockquote,.c3-card,.c3-card .c3-desc,.c3-watermark-main,.final-card,.final-card h2,.final-card p');
      targets.forEach(function (el) {
        el.setAttribute('data-home-reveal', el.matches('h1,h2,p,blockquote,li,.h,.c3-watermark-main') ? 'text' : 'block');
        // Keyboard navigation must never land on an invisible control.
        el.addEventListener('focusin', function () { el.setAttribute('data-home-visible', 'true'); });
      });
      requestAnimationFrame(function () {
        requestAnimationFrame(function () { targets.forEach(function (el) { reveal.observe(el); }); });
      });
      document.addEventListener('visibilitychange', function () {
        if (!document.hidden) targets.forEach(function (el) {
          if (!el.hasAttribute('data-home-visible')) { reveal.unobserve(el); reveal.observe(el); }
        });
      });
      motion.addEventListener('change', function () {
        if (motion.matches) {
          reveal.disconnect();
          targets.forEach(function (el) { el.setAttribute('data-home-visible', 'true'); });
        }
      });
    }
    var preview = document.getElementById('tab-preview');
    var button = document.querySelector('.top-chrome [data-tab="preview"]');
    if (preview && button) {
      button.removeAttribute('data-href');
      var frame = document.createElement('iframe');
      // Extensions commonly inject their site bridge into the top frame only.
      // Relay catalog reads only, from this exact same-origin editor frame.
      var catalogRequests = new Map();
      window.addEventListener('message', function (event) {
        if (event.origin !== location.origin) return;
        var data = event.data || {};
        if (event.source === frame.contentWindow && data.source === 'SSH_SITE' && data.type === 'REQUEST') {
          if (!data.payload || !['PING', 'GET_CUSTOMIZATION_CATALOG'].includes(data.payload.type) || typeof data.requestId !== 'string') return;
          if (catalogRequests.has(data.requestId)) return;
          catalogRequests.set(data.requestId, setTimeout(function () { catalogRequests.delete(data.requestId); }, 95000));
          window.postMessage(data, location.origin);
        } else if (event.source === window && data.source === 'SSH_EXTENSION' && data.type === 'RESPONSE' && catalogRequests.has(data.requestId)) {
          clearTimeout(catalogRequests.get(data.requestId));
          catalogRequests.delete(data.requestId);
          frame.contentWindow.postMessage(data, location.origin);
        }
      });
      frame.className = 'tools-profile-editor';
      frame.title = document.documentElement.lang === 'ru' ? 'Редактор профиля' : 'Profile editor';
      frame.src = '/profile?embed=tools';
      preview.prepend(frame);
      function syncFrame() {
        frame.title = document.documentElement.lang === 'ru' ? 'Редактор профиля' : 'Profile editor';
        try { frame.contentWindow.dispatchEvent(new CustomEvent('sm:langchange', { detail: { lang: document.documentElement.lang } })); } catch (e) {}
      }
      frame.addEventListener('load', syncFrame);
      window.addEventListener('sm:langchange', syncFrame);
    }
    window.addEventListener('storage', function (e) {
      if (e.key === 'sm_lang' || e.key === 'ss_lang') {
        document.documentElement.lang = window.SMLang ? SMLang.get() : 'en';
        window.dispatchEvent(new CustomEvent('sm:langchange', { detail: { lang: document.documentElement.lang } }));
      }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready); else ready();
})();
