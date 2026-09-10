(function () {
  'use strict';
  const CONSENT_KEY = 'sm_analytics_consent_v1';
  const SESSION_KEY = 'sm_analytics_session_v1';
  const HOME_KEY = 'sm_analytics_home_seen_v1';
  const COPY = {
    ru:['Анонимная статистика','Помоги нам понять, какие инструменты полезны. Без IP, email, имён файлов и содержимого медиа.','Только необходимые','Разрешить','Политика'],
    en:['Anonymous analytics','Help us understand which tools are useful. No IP, email, filenames or media content.','Necessary only','Allow','Privacy'],
    de:['Anonyme Statistik','Hilf uns zu verstehen, welche Werkzeuge nützlich sind. Keine IP, E-Mail, Dateinamen oder Medieninhalte.','Nur notwendige','Erlauben','Datenschutz'],
    tr:['Anonim analiz','Hangi araçların yararlı olduğunu anlamamıza yardımcı olun. IP, e-posta, dosya adı veya medya içeriği yok.','Yalnızca gerekli','İzin ver','Gizlilik'],
    fr:['Statistiques anonymes','Aidez-nous à comprendre quels outils sont utiles. Sans IP, e-mail, nom de fichier ni contenu média.','Nécessaires seulement','Autoriser','Confidentialité'],
    uk:['Анонімна статистика','Допоможіть зрозуміти, які інструменти корисні. Без IP, email, назв файлів і вмісту медіа.','Лише необхідні','Дозволити','Політика'],
    es:['Estadísticas anónimas','Ayúdanos a saber qué herramientas son útiles. Sin IP, correo, nombres de archivo ni contenido multimedia.','Solo necesarias','Permitir','Privacidad'],
    pt:['Estatísticas anónimas','Ajude-nos a perceber quais ferramentas são úteis. Sem IP, email, nomes de ficheiro ou conteúdo multimédia.','Só necessárias','Permitir','Privacidade']
  };
  const ALLOWED = new Set(['home_view','tool_open','file_added','process_failed','extension_launch_clicked','extension_launch_confirmed']);

  function language() {
    const selected = window.SMLang && typeof window.SMLang.get === 'function' ? window.SMLang.get() : '';
    const first = location.pathname.split('/').filter(Boolean)[0];
    const value = String(selected || first || document.documentElement.lang || 'en').toLowerCase().split('-')[0];
    return COPY[value] ? value : 'en';
  }
  function randomId() {
    if (window.crypto && crypto.getRandomValues) {
      const bytes = new Uint8Array(16); crypto.getRandomValues(bytes);
      return Array.from(bytes, x => x.toString(16).padStart(2,'0')).join('');
    }
    return String(Date.now()) + '-' + Math.random().toString(16).slice(2) + Math.random().toString(16).slice(2);
  }
  function session() {
    let value = sessionStorage.getItem(SESSION_KEY);
    if (!value) { value = randomId(); sessionStorage.setItem(SESSION_KEY, value); }
    return value;
  }
  function consent() { return localStorage.getItem(CONSENT_KEY); }
  function eventKey() { return randomId() + randomId(); }
  function track(event, properties) {
    if (consent() !== 'yes' || !ALLOWED.has(event)) return Promise.resolve(false);
    return fetch('/api/analytics/event', {
      method:'POST', credentials:'same-origin', keepalive:true,
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({event:event,event_key:eventKey(),session_id:session(),language:language(),path:location.pathname,consent:true,properties:properties || {}})
    }).then(r => r.ok).catch(() => false);
  }
  function headers() {
    const result = {'X-SM-Language':language()};
    if (consent() === 'yes') result['X-SM-Analytics-Session'] = session();
    return result;
  }
  function recordHome() {
    if (!document.body.classList.contains('page-home') || sessionStorage.getItem(HOME_KEY)) return;
    sessionStorage.setItem(HOME_KEY, '1'); track('home_view');
  }
  function showConsent() {
    if (consent()) return;
    const c = COPY[language()];
    const box = document.createElement('aside'); box.className = 'sm-consent'; box.setAttribute('role','dialog'); box.setAttribute('aria-label',c[0]);
    const privacy = '/' + language() + '/privacy';
    box.innerHTML = '<div class="sm-consent__copy"><strong class="sm-consent__title"></strong><div class="sm-consent__text"></div></div><div class="sm-consent__actions"><button class="sm-consent__button" data-choice="no"></button><button class="sm-consent__button sm-consent__button--allow" data-choice="yes"></button></div>';
    box.querySelector('.sm-consent__title').textContent=c[0];
    box.querySelector('.sm-consent__text').append(document.createTextNode(c[1]+' '));
    const link=document.createElement('a'); link.href=privacy; link.textContent=c[4]; box.querySelector('.sm-consent__text').append(link);
    box.querySelector('[data-choice="no"]').textContent=c[2]; box.querySelector('[data-choice="yes"]').textContent=c[3];
    box.addEventListener('click', e => { const choice=e.target.closest('[data-choice]'); if(!choice)return; localStorage.setItem(CONSENT_KEY,choice.dataset.choice); box.remove(); if(choice.dataset.choice==='yes')recordHome(); });
    document.body.appendChild(box);
  }
  function classifyFile(file) {
    const mime=String(file && file.type || '').split('/')[0];
    const name=String(file && file.name || ''); const ext=name.includes('.')?name.split('.').pop().toLowerCase():'';
    const type=mime==='image'||mime==='video'?mime:(['png','jpg','jpeg','webp','bmp','gif'].includes(ext)?'image':['mp4','mov','webm','avi','mkv'].includes(ext)?'video':'other');
    const mb=Number(file && file.size || 0)/1048576; return {file_type:type,size_bucket:mb<1?'under_1mb':mb<5?'1_5mb':mb<20?'5_20mb':'over_20mb'};
  }
  window.SMAnalytics={track:track,headers:headers,consent:consent};
  document.addEventListener('DOMContentLoaded', function () {
    if (consent()==='yes') recordHome(); else showConsent();
    document.addEventListener('click', function (e) {
      const button=e.target.closest('#nav [data-tab], [data-open-tool]'); if(!button)return;
      const tool=button.dataset.tab || button.dataset.openTool || ''; if(tool) track('tool_open',{tool:tool});
    });
    document.addEventListener('change', function (e) {
      if (!e.target.matches('input[type="file"]') || !e.target.files || !e.target.files.length) return;
      const info=classifyFile(e.target.files[0]); info.value=e.target.files.length; track('file_added',info);
    });
  });
})();
