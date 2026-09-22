(function () {
  'use strict';
  const t = function (ru,en) { const L=window.SMLang?SMLang.get():'en'; return L==='ru'?ru:(window.SMLang&&SMLang.translate?SMLang.translate(en,L):en); };
  const authHeaders = function () { return window.__smHeaders ? window.__smHeaders() : {}; };
  let overlay, list, source, notice, previousFocus;
  const pending = new Set();
  function jobName(kind) { return ({process:t('Нарезка витрины','Showcase processing'),compose:t('Персонаж + фон','Character + background'),upscale:t('Апскейл','Upscale'),seamless_loop:t('Бесшовный цикл','Seamless loop'),builder_bg_remove:t('Удаление фона','Background removal'),steam_profile_import:t('Импорт Steam-профиля','Steam profile import'),profile_insight:t('Анализ профиля','Profile analysis'),steam_dna:'Steam DNA'}[kind]||kind); }
  function shell() {
    if (overlay) return;
    overlay=document.createElement('div'); overlay.className='job-center';overlay.hidden=true;
    overlay.innerHTML='<aside role="dialog" aria-modal="true"><header><div><small>JOBS / LIVE</small><h3>'+t('Центр задач','Job center')+'</h3></div><button type="button" data-close>×</button></header><div class="job-center__queues" data-queues></div><div class="job-center__list"></div></aside>';
    list=overlay.querySelector('.job-center__list');
    overlay.querySelector('aside').setAttribute('aria-label',t('Центр задач','Job center'));
    overlay.querySelector('[data-close]').setAttribute('aria-label',t('Закрыть','Close'));
    notice=document.createElement('p');notice.className='job-center__empty';notice.setAttribute('role','alert');notice.hidden=true;
    list.before(notice);
    document.addEventListener('keydown',function(e){
      if(!overlay.classList.contains('is-open'))return;
      if(e.key==='Escape'){e.preventDefault();e.stopImmediatePropagation();close();return;}
      if(e.key!=='Tab')return;
      const nodes=Array.from(overlay.querySelectorAll('button:not(:disabled),a[href]')).filter(function(n){return n.getClientRects().length;});
      const first=nodes[0],last=nodes[nodes.length-1];
      if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
      else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
    },true);
    overlay.onclick=function(e){if(e.target===overlay||e.target.closest('[data-close]'))close();}; document.body.appendChild(overlay);
  }
  function time(value){if(!value)return '';return new Date(value*1000).toLocaleString([], {day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'});}
  function renderQueues(queues) {
    shell(); const box=overlay.querySelector('[data-queues]'); queues=queues||{};
    box.innerHTML=['media','profile','gpu'].map(function(name){return '<span><b>'+name.toUpperCase()+'</b> '+Number(queues[name]||0)+'</span>';}).join('');
  }
  function render(jobs) {
    shell(); const restoreFocus=list.contains(document.activeElement);list.innerHTML='';
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
      if(pending.has(job.id))actions.querySelectorAll('button').forEach(function(b){b.disabled=true;});
      list.appendChild(row);
    });
    if(restoreFocus)overlay.querySelector('[data-close]').focus();
  }
  function showError(message){shell();notice.textContent=message;notice.hidden=!message;}
  async function refresh(){try{const r=await fetch('/api/jobs',{credentials:'include',cache:'no-store',headers:authHeaders()});const j=await r.json();if(!r.ok)throw new Error();renderQueues(j.queues);render(j.jobs||[]);}catch(_){showError(t('Не удалось обновить задачи. Проверь соединение и открой окно снова.','Could not refresh jobs. Check your connection and reopen this window.'));}}
  async function action(id,name){
    if(pending.has(id))return;pending.add(id);showError('');
    try{
      const r=await fetch('/api/jobs/'+encodeURIComponent(id)+'/'+name,{method:'POST',credentials:'include',headers:authHeaders()});
      if(!r.ok){
        const messages={403:t('Дневной лимит исчерпан. Повтори позже.','Daily limit reached. Try again later.'),409:t('Действие уже недоступно. Список задач обновлён.','This action is no longer available. The job list has been refreshed.'),410:t('Исходные файлы истекли. Загрузи их заново.','Source files have expired. Upload them again.'),429:t('Подожди завершения текущих задач и повтори позже.','Wait for your current jobs to finish and try again later.')};
        showError(messages[r.status]||t('Не удалось выполнить действие. Попробуй снова.','The action failed. Please try again.'));
      }
    }catch(_){showError(t('Нет соединения. Проверь интернет и повтори.','Connection failed. Check your internet and try again.'));}
    finally{pending.delete(id);await refresh();}
  }
  function live(){if(source)return;const connection=new EventSource('/api/jobs/events',{withCredentials:true});source=connection;connection.addEventListener('jobs',function(e){try{render(JSON.parse(e.data));}catch(_){}});connection.onerror=function(){connection.close();if(source===connection)source=null;setTimeout(function(){if(overlay&&overlay.classList.contains('is-open'))live();},3000);};}
  function open(){shell();previousFocus=document.activeElement;overlay.hidden=false;overlay.classList.add('is-open');showError('');overlay.querySelector('[data-close]').focus();refresh();live();}
  function close(){if(overlay){overlay.classList.remove('is-open');overlay.hidden=true;}if(source){source.close();source=null;}if(previousFocus&&previousFocus.isConnected)previousFocus.focus();}
  window.SMJobCenter={open:open,refresh:refresh};
})();
