/**
 * Shared Showcase Maker auth modal — include on any page:
 *   <script src="/static/js/sm-auth.js" defer></script>
 * Call: window.smOpenAuth('login' | 'register')
 */
(function () {
  if (window.__smAuthLoaded) return;
  window.__smAuthLoaded = true;

  var TG_SVG =
    '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="#26A5E4" d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.893-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>';
  var DC_SVG =
    '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="#5865F2" d="M20.317 4.37a19.8 19.8 0 0 0-4.885-1.515.07.07 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.74 19.74 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.08.08 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.1 13.1 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.3 12.3 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.84 19.84 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/></svg>';
  var GG_SVG =
    '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="#EA4335" d="M12 10.2v3.6h5.1c-.2 1.2-.9 2.2-1.9 2.9l3.1 2.4c1.8-1.7 2.9-4.1 2.9-7 0-.7-.1-1.3-.2-1.9H12z"/><path fill="#34A853" d="M5.3 14.3l-.8.6-2.3 1.8C3.9 19.5 7.7 22 12 22c2.7 0 5-.9 6.7-2.4l-3.1-2.4c-.9.6-2 .9-3.6.9-2.8 0-5.1-1.9-6-4.4z"/><path fill="#4A90E2" d="M3 7.1C2.4 8.3 2 9.6 2 11s.4 2.7 1 3.9l2.3-1.8C5 12.4 4.8 11.7 4.8 11s.2-1.4.5-2z"/><path fill="#FBBC05" d="M12 4.8c1.5 0 2.8.5 3.8 1.5l2.8-2.8C16.9 1.9 14.7 1 12 1 7.7 1 3.9 3.5 2.2 7.1l3.1 2.4C6.9 6.7 9.2 4.8 12 4.8z"/></svg>';

  function ru() {
    try {
      return (localStorage.getItem('sm_lang') || 'en') === 'ru';
    } catch (e) {
      return false;
    }
  }

  function ensureStyles() {
    if (document.getElementById('sm-auth-css')) return;
    var s = document.createElement('style');
    s.id = 'sm-auth-css';
    s.textContent =
      '.sm-auth-bg{display:none;position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.65);backdrop-filter:blur(10px);align-items:center;justify-content:center;padding:20px}' +
      '.sm-auth-bg.open{display:flex}' +
      '.sm-auth-modal{position:relative;width:100%;max-width:400px;border-radius:20px;border:1px solid rgba(255,255,255,.12);background:rgba(14,16,20,.96);padding:28px 24px;box-shadow:0 24px 80px rgba(0,0,0,.5);color:#fff;font-family:Mulish,system-ui,sans-serif}' +
      '.sm-auth-modal h3{margin:0 0 6px;font-size:20px;font-weight:600}' +
      '.sm-auth-modal .sub{margin:0 0 16px;font-size:13px;color:rgba(255,255,255,.55)}' +
      '.sm-auth-modal input{width:100%;margin-bottom:10px;padding:12px 14px;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.04);color:#fff;font:inherit;box-sizing:border-box}' +
      '.sm-auth-modal .btn-auth{width:100%;min-height:44px;border-radius:999px;border:none;background:#fff;color:#0c0c0c;font-weight:600;cursor:pointer;font-size:14px;font-family:inherit}' +
      '.sm-auth-modal .close-x{position:absolute;top:14px;right:16px;background:none;border:none;color:rgba(255,255,255,.5);font-size:20px;cursor:pointer}' +
      '.sm-auth-modal .status{font-size:13px;min-height:18px;margin:8px 0;color:rgba(255,255,255,.55)}' +
      '.sm-auth-modal .status.err{color:#ff6b6b}.sm-auth-modal .status.ok{color:#3ddc84}' +
      '.sm-auth-div{display:flex;align-items:center;gap:12px;margin:16px 0 12px;font-size:12px;color:rgba(255,255,255,.45)}' +
      '.sm-auth-div:before,.sm-auth-div:after{content:"";flex:1;height:1px;background:rgba(255,255,255,.12)}' +
      '.sm-auth-oauth{display:flex;flex-direction:column;gap:8px}' +
      '.sm-auth-oauth button{width:100%;min-height:46px;border-radius:999px;border:1px solid rgba(255,255,255,.15);background:rgba(255,255,255,.04);color:#fff;font-size:14px;font-weight:600;cursor:pointer;font-family:inherit;display:inline-flex;align-items:center;justify-content:center;gap:10px}' +
      '.sm-auth-oauth button:hover{background:rgba(255,255,255,.09)}' +
      '.sm-auth-modal .switch{margin-top:14px;font-size:13px;color:rgba(255,255,255,.55);text-align:center}' +
      '.sm-auth-modal .switch a{color:#fff;text-decoration:underline;cursor:pointer}';
    document.head.appendChild(s);
  }

  function ensureModal() {
    ensureStyles();
    var el = document.getElementById('smAuthModal');
    if (el) return el;
    el = document.createElement('div');
    el.id = 'smAuthModal';
    el.className = 'sm-auth-bg';
    el.setAttribute('aria-hidden', 'true');
    el.innerHTML =
      '<div class="sm-auth-modal">' +
      '<button type="button" class="close-x" id="smAuthClose" aria-label="Close">×</button>' +
      '<h3 id="smAuthTitle">Log in</h3>' +
      '<p class="sub" id="smAuthSub">Log in to buy Pro and keep access</p>' +
      '<input id="smAuthEmail" type="email" placeholder="Email" autocomplete="email"/>' +
      '<input id="smAuthPass" type="password" placeholder="Password (min 6)" autocomplete="current-password"/>' +
      '<button type="button" class="btn-auth" id="smAuthSubmit">Log in</button>' +
      '<div class="status" id="smAuthStatus"></div>' +
      '<div class="sm-auth-div"><span id="smAuthOr">or continue with</span></div>' +
      '<div class="sm-auth-oauth">' +
      '<button type="button" id="smAuthDiscord">' + DC_SVG + '<span>Discord</span></button>' +
      '<button type="button" id="smAuthGoogle">' + GG_SVG + '<span>Google</span></button>' +
      '<button type="button" id="smAuthTelegram">' + TG_SVG + '<span>Telegram</span></button>' +
      '<div id="smTgHost" style="display:none;text-align:center;margin-top:4px"></div>' +
      '</div>' +
      '<div class="switch" id="smAuthSwitch"></div>' +
      '</div>';
    document.body.appendChild(el);
    wire(el);
    return el;
  }

  var mode = 'login';

  function syncUi() {
    var isRu = ru();
    var reg = mode === 'register';
    var title = document.getElementById('smAuthTitle');
    var sub = document.getElementById('smAuthSub');
    var submit = document.getElementById('smAuthSubmit');
    var sw = document.getElementById('smAuthSwitch');
    var or = document.getElementById('smAuthOr');
    if (title) title.textContent = reg ? (isRu ? 'Регистрация' : 'Sign up') : isRu ? 'Вход' : 'Log in';
    if (sub)
      sub.textContent = reg
        ? isRu
          ? 'Создай аккаунт для Pro и сохранения доступа'
          : 'Create an account to buy Pro and keep access'
        : isRu
          ? 'Войди, чтобы купить Pro и сохранить доступ'
          : 'Log in to buy Pro and keep access';
    if (submit) submit.textContent = reg ? (isRu ? 'Создать аккаунт' : 'Create account') : isRu ? 'Войти' : 'Log in';
    if (or) or.textContent = isRu ? 'или войти через' : 'or continue with';
    if (sw)
      sw.innerHTML = reg
        ? isRu
          ? 'Уже есть аккаунт? <a data-sm-tog>Вход</a>'
          : 'Already have an account? <a data-sm-tog>Log in</a>'
        : isRu
          ? 'Нет аккаунта? <a data-sm-tog>Регистрация</a>'
          : 'No account? <a data-sm-tog>Sign up</a>';
  }

  function openAuth(m) {
    mode = m === 'register' ? 'register' : 'login';
    var el = ensureModal();
    var st = document.getElementById('smAuthStatus');
    if (st) {
      st.className = 'status';
      st.textContent = '';
    }
    syncUi();
    el.classList.add('open');
    el.setAttribute('aria-hidden', 'false');
  }

  function closeAuth() {
    var el = document.getElementById('smAuthModal');
    if (el) {
      el.classList.remove('open');
      el.setAttribute('aria-hidden', 'true');
    }
  }

  function wire(el) {
    document.getElementById('smAuthClose').onclick = closeAuth;
    el.onclick = function (e) {
      if (e.target === el) closeAuth();
    };
    el.addEventListener('click', function (e) {
      if (e.target && e.target.getAttribute('data-sm-tog') !== null) {
        e.preventDefault();
        openAuth(mode === 'register' ? 'login' : 'register');
      }
    });
    document.getElementById('smAuthSubmit').onclick = async function () {
      var email = (document.getElementById('smAuthEmail').value || '').trim();
      var password = document.getElementById('smAuthPass').value || '';
      var st = document.getElementById('smAuthStatus');
      var path = mode === 'register' ? '/api/auth/register' : '/api/auth/login';
      try {
        var r = await fetch(path, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ email: email, password: password }),
        });
        var j = await r.json();
        if (!j.ok) {
          if (st) {
            st.className = 'status err';
            st.textContent = j.msg || 'Error';
          }
          return;
        }
        if (j.token) {
          try {
            localStorage.setItem('sm_session', j.token);
          } catch (e) {}
        }
        location.reload();
      } catch (err) {
        if (st) {
          st.className = 'status err';
          st.textContent = String(err);
        }
      }
    };
    async function goOAuth(provider) {
      var path = provider === 'google' ? '/api/auth/google/login' : '/api/auth/discord/login';
      var win = provider === 'google' ? 'google_oauth' : 'discord_oauth';
      try {
        var r = await fetch(path);
        var d = await r.json();
        if (!d.ok || !d.url) {
          alert(d.msg || provider + ' not configured');
          return;
        }
        window.open(d.url, win, 'width=520,height=720');
      } catch (e) {
        alert(String(e));
      }
    }
    document.getElementById('smAuthDiscord').onclick = function () {
      goOAuth('discord');
    };
    document.getElementById('smAuthGoogle').onclick = function () {
      goOAuth('google');
    };
    document.getElementById('smAuthTelegram').onclick = async function () {
      try {
        var r = await fetch('/api/auth/telegram/config');
        var d = await r.json();
        if (!d.ok || !d.bot_username) {
          alert(d.msg || 'Telegram not configured');
          return;
        }
        var host = document.getElementById('smTgHost');
        host.style.display = 'block';
        host.innerHTML = '';
        window.onTelegramAuth = async function (user) {
          try {
            var res = await fetch('/api/auth/telegram', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'include',
              body: JSON.stringify(user),
            });
            var j = await res.json();
            if (!j.ok || !j.token) {
              alert(j.msg || 'Telegram auth failed');
              return;
            }
            try {
              localStorage.setItem('sm_session', j.token);
            } catch (e) {}
            location.reload();
          } catch (e) {
            alert(String(e));
          }
        };
        var s = document.createElement('script');
        s.async = true;
        s.src = 'https://telegram.org/js/telegram-widget.js?22';
        s.setAttribute('data-telegram-login', d.bot_username);
        s.setAttribute('data-size', 'large');
        s.setAttribute('data-radius', '12');
        s.setAttribute('data-request-access', 'write');
        s.setAttribute('data-userpic', 'true');
        s.setAttribute('data-onauth', 'onTelegramAuth(user)');
        host.appendChild(s);
      } catch (e) {
        alert(String(e));
      }
    };
    window.addEventListener('message', function (ev) {
      if (!ev.data) return;
      if (
        (ev.data.type === 'discord_login' ||
          ev.data.type === 'google_login' ||
          ev.data.type === 'telegram_login') &&
        ev.data.token
      ) {
        try {
          localStorage.setItem('sm_session', ev.data.token);
        } catch (e) {}
        location.reload();
      }
    });
  }

  window.smOpenAuth = openAuth;
  window.smCloseAuth = closeAuth;
  // aliases used by pages
  if (!window.openAuth) window.openAuth = openAuth;
  if (!window.openAuthModal) window.openAuthModal = openAuth;

  document.addEventListener('DOMContentLoaded', function () {
    ensureModal();
    document.querySelectorAll('[data-sm-login]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        openAuth('login');
      });
    });
    document.querySelectorAll('[data-sm-register]').forEach(function (btn) {
      btn.addEventListener('click', function (e) {
        e.preventDefault();
        openAuth('register');
      });
    });
  });
})();
