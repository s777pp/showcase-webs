(function () {
  'use strict';
  const t = function (ru,en) { const L=window.SMLang?SMLang.get():'en'; return L==='ru'?ru:(window.SMLang&&SMLang.translate?SMLang.translate(en,L):en); };
  const authHeaders = function () { return window.__smHeaders ? window.__smHeaders() : {}; };
  let overlay, list, source;
  function jobName(kind) { return ({process:t('Нарезка витрины','Showcase processing'),compose:t('Персонаж + фон','Character + background'),upscale:t('Апскейл','Upscale'),seamless_loop:t('Бесшовный цикл','Seamless loop'),builder_bg_remove:t('Удаление фона','Background removal'),steam_profile_import:t('Импорт Steam-профиля','Steam profile import'),profile_insight:t('Анализ профиля','Profile analysis'),steam_dna:'Steam DNA'}[kind]||kind); }
  function shell() {
    if (overlay) return;
    overlay=document.createElement('div'); overlay.className='job-center';
    overlay.innerHTML='<aside role="dialog" aria-modal="true"><header><div><small>JOBS / LIVE</small><h3>'+t('Центр задач','Job center')+'</h3></div><button type="button" data-close>×</button></header><div class="job-center__queues" data-queues></div><div class="job-center__list"></div></aside>';
    list=overlay.querySelector('.job-center__list');
    overlay.onclick=function(e){if(e.target===overlay||e.target.closest('[data-close]'))close();}; document.body.appendChild(overlay);
  }
  function time(value){if(!value)return '';return new Date(value*1000).toLocaleString([], {day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});}
  function renderQueues(queues) {
    shell(); const box=overlay.querySelector('[data-queues]'); queues=queues||{};
    box.innerHTML=['media','profile','gpu'].map(function(name){return '<span><b>'+name.toUpperCase()+'</b> '+Number(queues[name]||0)+'</span>';}).join('');
  }
  function render(jobs) {
    shell(); list.innerHTML='';
    if(!jobs.length){list.innerHTML='<p class="job-center__empty">'+t('Задач пока нет. Запусти любой инструмент — задача останется здесь даже после перезагрузки страницы.','No jobs yet. Start any tool and it will stay here after a page reload.')+'</p>';return;}
    jobs.forEach(function(job){
      const row=document.createElement('article'); row.className='job-center__job is-'+job.status;
      row.innerHTML='<div class="job-center__main"><small></small><b></b><span></span><div class="job-center__bar"><i></i></div></div><div class="job-center__actions"></div>';
      row.querySelector('small').textContent=(job.queue||'media').toUpperCase()+' · '+time(job.updated);
      row.querySelector('b').textContent=jobName(job.kind);
      row.querySelector('span').textContent=(job.cached?t('Из кеша · ','Cached · '):'')+(job.stage||job.status)+' · '+job.pct+'%';
      row.querySelector('i').style.width=Math.max(0,Math.min(100,job.pct))+'%'; const actions=row.querySelector('.job-center__actions');
      if(job.download_url){const a=document.createElement('a');a.className='btn';a.href=job.download_url;a.textContent=t('Скачать','Download');actions.appendChild(a);}
      if(job.can_cancel){const b=document.createElement('button');b.type='button';b.className='btn ghost';b.textContent=t('Отменить','Cancel');b.onclick=function(){action(job.id,'cancel');};actions.appendChild(b);}
      if(job.can_retry){const b=document.createElement('button');b.type='button';b.className='btn ghost';b.textContent=t('Повторить','Retry');b.onclick=function(){action(job.id,'retry');};actions.appendChild(b);}
      list.appendChild(row);
    });
  }
  async function refresh(){const r=await fetch('/api/jobs',{credentials:'include',cache:'no-store',headers:authHeaders()});const j=await r.json();if(r.ok){renderQueues(j.queues);render(j.jobs||[]);}}
  async function action(id,name){await fetch('/api/jobs/'+encodeURIComponent(id)+'/'+name,{method:'POST',credentials:'include',headers:authHeaders()});refresh();}
  function live(){if(source)return;source=new EventSource('/api/jobs/events',{withCredentials:true});source.addEventListener('jobs',function(e){try{render(JSON.parse(e.data));}catch(_){}});source.onerror=function(){source.close();source=null;setTimeout(function(){if(overlay&&overlay.classList.contains('is-open'))live();},3000);};}
  function open(){shell();overlay.classList.add('is-open');refresh();live();}
  function close(){if(overlay)overlay.classList.remove('is-open');if(source){source.close();source=null;}}
  window.SMJobCenter={open:open,refresh:refresh};
})();
