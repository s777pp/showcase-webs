/* Stateless assistant UI; no chat history in localStorage or analytics. */
(() => {
  'use strict';
  if(new URLSearchParams(location.search).get('embed')==='tools')return;
  const language=()=>window.SMLang?.get?.()||'en';
  const ru=()=>language()==='ru';
  const t=(a,b)=>ru()?a:(window.SMLang?.translate?.(b,language())||b);
  function start(){
    // FAQ links still open the requested existing tool without the redesign script.
    function openLinkedTool(){
      const path=location.pathname.replace(/^\/(?:en|ru|de|tr|fr|uk|es|pt)(?=\/|$)/,'').replace(/\/$/,'');
      if(path!=='/app')return;
      const id=location.hash.slice(1);
      const button=[...document.querySelectorAll('#nav button[data-tab]')].find(b=>b.dataset.tab===id&&id!=='check');
      if(button)button.click();
    }
    window.addEventListener('hashchange',openLinkedTool);
    if(document.readyState==='complete')openLinkedTool();
    else window.addEventListener('load',openLinkedTool,{once:true});
    let topics=[],available=false,loaded=false,pending=false,history=[],topicsExpanded=false;
    const root=document.createElement('aside');root.className='studio-support';
    root.innerHTML='<button class="studio-chat-launch" type="button" aria-expanded="false" aria-controls="studioChat"><span class="studio-chat-launch__icon" aria-hidden="true"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.4 8.4 0 0 1-8.5 8.3 8.9 8.9 0 0 1-3.9-.9L3 20.5l1.6-4.7A8 8 0 0 1 3.9 11.5a8.4 8.4 0 0 1 8.6-8.3 8.4 8.4 0 0 1 8.5 8.3Z"/><path d="M8.5 11.5h.01M12.5 11.5h.01M16.5 11.5h.01" stroke-width="2.6"/></svg></span><span class="chat-launch-label"></span></button><section id="studioChat" class="studio-chat-panel" role="dialog" aria-labelledby="studioChatTitle" hidden><header><div><small>SHOWCASE MAKER</small><h2 id="studioChatTitle"></h2></div><button class="studio-chat-close" type="button">×</button></header><p class="studio-chat-note"></p><div class="studio-chat-suggestions" hidden><div id="studioChatTopics" class="studio-chat-topics" role="group"></div><button class="studio-chat-topics-toggle" type="button" aria-expanded="false" aria-controls="studioChatTopics"><span></span><span aria-hidden="true">⌄</span></button></div><div class="studio-chat-messages" role="log" aria-live="polite" aria-relevant="additions"></div><form class="studio-chat-form"><label for="studioChatInput" class="studio-sr-only"></label><textarea id="studioChatInput" maxlength="1500" rows="2" required></textarea><button class="studio-chat-send" type="submit">↑</button></form><button class="studio-ticket-toggle" type="button" aria-expanded="false"></button><form class="studio-ticket-form" hidden><label><span class="studio-ticket-message-label"></span><textarea name="message" minlength="10" maxlength="2000" rows="3" required></textarea></label><label><span class="studio-ticket-email-label"></span><input name="email" type="text" maxlength="254" autocomplete="email"></label><button type="submit"></button><output role="status"></output></form><p class="studio-chat-privacy"></p></section>';
    document.body.append(root);
    // Keep the launcher above the page footer: while the footer is on screen the
    // button is lifted by the visible footer height so it never covers its links.
    const footerOf=()=>document.querySelector('.home-footer,#ssFootHost footer,.ss-foot,body>footer,.app-footer');
    let liftQueued=false;
    const updateLift=()=>{liftQueued=false;const footer=footerOf();if(!footer){root.style.removeProperty('--support-lift');return}
      const top=footer.getBoundingClientRect().top,visible=Math.max(0,window.innerHeight-top);
      root.style.setProperty('--support-lift',visible?Math.round(visible+12)+'px':'0px')};
    const queueLift=()=>{if(!liftQueued){liftQueued=true;requestAnimationFrame(updateLift)}};
    window.addEventListener('scroll',queueLift,{passive:true});window.addEventListener('resize',queueLift,{passive:true});
    if(window.ResizeObserver)new ResizeObserver(queueLift).observe(document.body);
    queueLift();
    const find=s=>root.querySelector(s),panel=find('.studio-chat-panel'),input=find('#studioChatInput'),log=find('[role=log]'),form=find('.studio-chat-form'),launcher=find('.studio-chat-launch');
    const ticketToggle=find('.studio-ticket-toggle'),ticketForm=find('.studio-ticket-form');
    const suggestions=find('.studio-chat-suggestions'),topicsToggle=find('.studio-chat-topics-toggle');
    const choice=document.createElement('div');choice.className='studio-support-choice';choice.hidden=true;
    // "Support" opens this window: a contact (e-mail or Telegram) and a message.
    // E-mail answers come by mail; Telegram contacts are answered in Telegram.
    choice.innerHTML='<div class="studio-support-choice__card sw-card" role="dialog" aria-modal="true" aria-labelledby="studioSupportChoiceTitle"><button type="button" class="studio-support-choice__close sw-close" aria-label="Close">×</button><div class="sw-head"><span class="sw-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M4 13v-1a8 8 0 0 1 16 0v1"/><path d="M4 13h3v6H5a1 1 0 0 1-1-1v-5Zm16 0h-3v6h2a1 1 0 0 0 1-1v-5ZM17 19c0 1.1-.9 2-2 2h-3"/></svg></span><div><small class="sw-eyebrow"></small><h2 id="studioSupportChoiceTitle"></h2><p class="studio-support-choice__hint sw-sub"></p></div></div><form class="sw-form" novalidate><label class="sw-field"><span class="sw-label sw-contact-label"></span><span class="sw-input"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="m4 7 8 6 8-6"/></svg><input name="contact" type="text" maxlength="254" autocomplete="email" required></span><small class="sw-help"></small></label><label class="sw-field"><span class="sw-label sw-message-label"></span><textarea name="message" minlength="10" maxlength="2000" rows="6" required></textarea><small class="sw-count">0 / 2000</small></label><button type="submit" class="sw-submit"></button><output class="sw-status" role="status"></output></form><div class="sw-divider"><span></span></div><div class="sw-alt"><a class="studio-support-choice__telegram sw-alt__btn" href="https://t.me/showcasemaker" target="_blank" rel="noopener noreferrer"><svg class="sw-alt__icon" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="11" fill="#26A5E4"/><path fill="#fff" d="m17.8 7-2 10c-.2.7-.6.9-1.2.5l-3-2.2-1.5 1.4c-.2.2-.3.3-.6.3l.2-3.1 5.6-5.1c.2-.2 0-.3-.4-.1l-6.9 4.4-3-.9c-.6-.2-.7-.6.1-1l11.7-4.5c.6-.2 1.1.1 1 .9Z"/></svg><span class="sw-alt__text"></span></a><button type="button" class="studio-support-choice__report sw-alt__btn"><svg class="sw-alt__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l1.9 4.6L18.5 9.5l-4.6 1.9L12 16l-1.9-4.6L5.5 9.5l4.6-1.9L12 3Z"/><path d="M19 15l.8 1.9 1.9.8-1.9.8L19 20.4l-.8-1.9-1.9-.8 1.9-.8L19 15Z"/></svg><span class="sw-alt__text"></span></button></div></div>';
    document.body.append(choice);
    let choiceOrigin=null;
    const supportForm=choice.querySelector('form');
    function closeChoice(){choice.hidden=true;choiceOrigin?.focus();choiceOrigin=null}
    function contactHint(){const v=supportForm.contact.value.trim(),help=choice.querySelector('.sw-help');if(/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v))help.textContent=t('✉️ Ответ придёт на эту почту','✉️ The reply will come to this e-mail');else{const m=v.match(/^(?:https?:\/\/)?(?:t\.me\/|telegram\.me\/)?@?([A-Za-z][A-Za-z0-9_]{4,31})\/?$/);help.textContent=m?t('💬 Напишем тебе в Telegram @','💬 We will message you on Telegram @')+m[1]:t('Почта — ответим письмом, Telegram (@username) — напишем в личные сообщения.','E-mail — we reply by mail; Telegram (@username) — we message you directly.')}}
    function paintChoice(){choice.querySelector('.sw-eyebrow').textContent=t('SHOWCASE MAKER · ПОДДЕРЖКА','SHOWCASE MAKER · SUPPORT');choice.querySelector('h2').textContent=t('Техподдержка','Support');choice.querySelector('.sw-sub').textContent=t('Опиши проблему и оставь почту или Telegram — ответим туда же.','Describe the problem and leave your e-mail or Telegram — we will reply there.');choice.querySelector('.sw-contact-label').textContent=t('Почта или Telegram','E-mail or Telegram');supportForm.contact.placeholder=t('you@mail.com или @username','you@mail.com or @username');choice.querySelector('.sw-message-label').textContent=t('Что случилось?','What happened?');supportForm.message.placeholder=t('Например: не зацикливается видео, ошибка при обработке…','For example: the loop fails, processing shows an error…');supportForm.querySelector('.sw-submit').textContent=t('Отправить обращение','Send request');choice.querySelector('.sw-divider span').textContent=t('или','or');choice.querySelector('.sw-alt a .sw-alt__text').textContent=t('Telegram-канал ↗','Telegram channel ↗');choice.querySelector('.studio-support-choice__report .sw-alt__text').textContent=t('Спросить ИИ-помощника','Ask the AI assistant');choice.querySelector('.studio-support-choice__close').setAttribute('aria-label',t('Закрыть','Close'));contactHint()}
    document.addEventListener('click',function(event){var link=event.target.closest('[data-support-choice]');if(!link)return;event.preventDefault();choiceOrigin=link;paintChoice();supportForm.querySelector('output').textContent='';supportForm.querySelector('output').className='sw-status';choice.hidden=false;supportForm.contact.focus()});
    choice.querySelector('.studio-support-choice__close').addEventListener('click',closeChoice);
    choice.addEventListener('click',function(event){if(event.target===choice)closeChoice()});
    choice.addEventListener('keydown',function(event){if(event.key==='Escape')closeChoice()});
    choice.querySelector('.studio-support-choice__report').addEventListener('click',function(){closeChoice();if(panel.hidden)launcher.click()});
    supportForm.contact.addEventListener('input',contactHint);supportForm.message.addEventListener('input',function(){choice.querySelector('.sw-count').textContent=supportForm.message.value.length+' / 2000'});
    const contactOk=value=>/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)||/^(?:https?:\/\/)?(?:t\.me\/|telegram\.me\/)?@?[A-Za-z][A-Za-z0-9_]{4,31}\/?$/.test(value);
    supportForm.addEventListener('submit',async function(event){
      event.preventDefault();const status=supportForm.querySelector('output'),button=supportForm.querySelector('.sw-submit'),contact=supportForm.contact.value.trim(),message=supportForm.message.value.trim();
      if(!contactOk(contact)){status.className=['sw-status','is-err'].join(' ');status.textContent=t('Укажи почту (name@mail.com) или Telegram (@username).','Enter an e-mail (name@mail.com) or a Telegram username (@username).');supportForm.contact.focus();return}
      if(message.length<10){status.className=['sw-status','is-err'].join(' ');status.textContent=t('Опиши проблему чуть подробнее (от 10 символов).','Please describe the problem (at least 10 characters).');supportForm.message.focus();return}
      button.disabled=true;status.className='sw-status';status.textContent=t('Отправляем…','Sending…');
      try{
        const response=await fetch('/api/support/tickets',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:message,contact:contact,page:location.pathname,context:{language:language(),viewport:`${innerWidth}x${innerHeight}`,browser:navigator.userAgent.slice(0,120)}})});
        const data=await response.json();if(!response.ok)throw Error(data.code||'failed');
        supportForm.reset();contactHint();choice.querySelector('.sw-count').textContent='0 / 2000';status.className=['sw-status','is-ok'].join(' ');status.textContent=contact.includes('@')&&contact.indexOf('@')>0?t('Готово! Ответим на почту. Номер обращения: #','Sent! We will reply by e-mail. Ticket #')+data.ticket_id:t('Готово! Напишем тебе в Telegram. Номер обращения: #','Sent! We will message you on Telegram. Ticket #')+data.ticket_id;
      }catch(error){status.className=['sw-status','is-err'].join(' ');status.textContent=error.message==='limit'?t('Сегодня отправлено слишком много обращений. Напиши нам в Telegram.','Too many reports today. Please message us on Telegram.'):error.message==='contact'?t('Укажи почту или Telegram (@username), чтобы мы могли ответить.','Enter an e-mail or a Telegram username so we can reply.'):error.message==='contact'?t('Укажи почту или Telegram.','Enter an e-mail or a Telegram username.'):t('Не удалось отправить. Попробуй ещё раз.','Could not send. Please try again.')}
      finally{button.disabled=false}
    });
    function paintTopicsState(){
      suggestions.hidden=topics.length===0;
      suggestions.classList.toggle('is-expanded',topicsExpanded);
      topicsToggle.setAttribute('aria-expanded',String(topicsExpanded));
      topicsToggle.querySelector('span').textContent=topicsExpanded?t('Свернуть','Collapse'):t('Развернуть','Expand');
      topicsToggle.setAttribute('aria-label',topicsExpanded?t('Свернуть частые вопросы','Collapse frequently asked questions'):t('Развернуть частые вопросы','Expand frequently asked questions'));
      find('.studio-chat-topics').setAttribute('aria-label',t('Частые вопросы','Frequently asked questions'));
    }
    topicsToggle.addEventListener('click',()=>{topicsExpanded=!topicsExpanded;paintTopicsState();});
    function message(text,role='assistant'){
      const item=document.createElement('div');item.className='studio-chat-message '+role; item.textContent=text;log.append(item);log.scrollTop=log.scrollHeight;return item;
    }
    function paint(){
      find('.chat-launch-label').textContent=t('Помощник','Assistant');
      find('h2').textContent=t('Чем помочь?','How can we help?');
      find('.studio-chat-close').setAttribute('aria-label',t('Закрыть','Close'));
      find('.studio-chat-send').setAttribute('aria-label',t('Отправить','Send'));
      find('label').textContent=t('Твой вопрос','Your question');
      input.placeholder=t('Как подготовить GIF для Steam?','How do I prepare a GIF for Steam?');
      find('.studio-chat-privacy').textContent=t('При включённом ИИ сообщения отправляются Groq. Не отправляй пароли и ключи. Ответы могут содержать ошибки.','When AI is enabled, messages are sent to Groq. Don’t share passwords or keys. Answers may contain mistakes.');
      ticketToggle.textContent=t('Сообщить о проблеме','Report a problem');
      find('.studio-ticket-message-label').textContent=t('Что произошло?','What happened?');
      find('.studio-ticket-email-label').textContent=t('Почта или Telegram для ответа','E-mail or Telegram for the reply');
      ticketForm.querySelector('button').textContent=t('Отправить обращение','Send report');
      find('.studio-chat-note').textContent=!loaded?t('Загружаем справку…','Loading help…'):available?t('Спроси об инструментах, витринах или аккаунте. Есть лимит запросов.','Ask about tools, showcases or your account. Request limits apply.'):t('ИИ ещё не подключён. Пока можно открыть инструкции ниже.','AI is not connected yet. Explore the help topics below.');
      input.disabled=!available||pending;find('.studio-chat-send').disabled=!available||pending;
      const list=find('.studio-chat-topics');list.replaceChildren();
      topics.forEach(topic=>{const source=topic[language()]||topic.en||topic.ru;const pack=topic[language()]||{title:window.SMLang?.translate?.(source.title,language())||source.title,text:window.SMLang?.translate?.(source.text,language())||source.text};const button=document.createElement('button');button.type='button';button.textContent=pack.title;button.addEventListener('click',()=>{
        if(topicsExpanded){topicsExpanded=false;paintTopicsState();topicsToggle.focus();}
        const item=message(pack.text);const link=document.createElement('a');link.href=window.SMLang?.url?.(topic.href)||topic.href;link.textContent=t('Открыть →','Open →');item.append(link);log.scrollTop=log.scrollHeight;
      });list.append(button);});
      paintTopicsState();
    }
    function close(){panel.hidden=true;launcher.setAttribute('aria-expanded','false');launcher.focus();}
    launcher.addEventListener('click',async()=>{
      if(!panel.hidden){close();return;}panel.hidden=false;launcher.setAttribute('aria-expanded','true');find('.studio-chat-close').focus();
      if(!loaded){try{const response=await fetch('/api/support/info');if(!response.ok)throw Error();const data=await response.json();topics=data.topics||[];available=!!data.available;loaded=true;}catch{loaded=true;message(t('Справка недоступна. Поддержка: https://t.me/showcasemaker','Help is unavailable. Contact: https://t.me/showcasemaker'));}paint();}
    });
    find('.studio-chat-close').addEventListener('click',close);
    ticketToggle.addEventListener('click',()=>{const opening=ticketForm.hidden;ticketForm.hidden=!opening;ticketToggle.setAttribute('aria-expanded',String(opening));if(opening)ticketForm.message.focus();});
    panel.addEventListener('keydown',e=>{if(e.key==='Escape')close();});
    input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();if(!pending&&available)form.requestSubmit();}});
    form.addEventListener('submit',async e=>{
      e.preventDefault();const value=input.value.trim();if(!value||pending||!available)return;
      pending=true;message(value,'user');input.value='';const waiting=message(t('Думаю…','Thinking…'));paint();
      try{
        const response=await fetch('/api/support/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:value,history:history.slice(-6),language:language()}),signal:AbortSignal.timeout(45000)});
        const data=await response.json();
        if(!response.ok){waiting.textContent=data.code==='limit'?t('Лимит запросов достигнут. Попробуй позже или открой справку выше.','Request limit reached. Try again later or use the help topics above.'):t('ИИ сейчас недоступен. Инструкции выше по-прежнему работают.','AI is currently unavailable. The help topics above still work.');}
        else{waiting.textContent=data.answer;history.push({role:'user',content:value},{role:'assistant',content:data.answer.slice(0,1500)});history=history.slice(-6);}
      }catch{waiting.textContent=t('Не удалось получить ответ. Попробуй ещё раз.','Couldn’t get an answer. Please try again.');}
      finally{pending=false;paint();input.focus();log.scrollTop=log.scrollHeight;}
    });
    ticketForm.addEventListener('submit',async e=>{
      e.preventDefault();const button=ticketForm.querySelector('button'),status=ticketForm.querySelector('output');button.disabled=true;status.textContent=t('Отправляем…','Sending…');
      try{
        const response=await fetch('/api/support/tickets',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:ticketForm.message.value.trim(),email:ticketForm.email.value.trim(),page:location.pathname,context:{language:language(),viewport:`${innerWidth}x${innerHeight}`,browser:navigator.userAgent.slice(0,120)}})});
        const data=await response.json();if(!response.ok)throw Error(data.code||'failed');ticketForm.reset();status.textContent=`${t('Обращение принято. Номер:','Report received. ID:')} #${data.ticket_id}`;
      }catch(error){status.textContent=error.message==='limit'?t('Сегодня отправлено слишком много обращений.','Too many reports were sent today.'):t('Не удалось отправить. Попробуй позже.','Could not send. Please try later.');}
      finally{button.disabled=false;}
    });
    paint();paintChoice();window.addEventListener('sm:langchange',()=>{history=[];log.replaceChildren();paint();paintChoice();});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
