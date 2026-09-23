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
    root.innerHTML='<button class="studio-chat-launch" type="button" aria-expanded="false" aria-controls="studioChat"><span aria-hidden="true">✦</span><span class="chat-launch-label"></span></button><section id="studioChat" class="studio-chat-panel" role="dialog" aria-labelledby="studioChatTitle" hidden><header><div><small>SHOWCASE MAKER</small><h2 id="studioChatTitle"></h2></div><button class="studio-chat-close" type="button">×</button></header><p class="studio-chat-note"></p><div class="studio-chat-suggestions" hidden><div id="studioChatTopics" class="studio-chat-topics" role="group"></div><button class="studio-chat-topics-toggle" type="button" aria-expanded="false" aria-controls="studioChatTopics"><span></span><span aria-hidden="true">⌄</span></button></div><div class="studio-chat-messages" role="log" aria-live="polite" aria-relevant="additions"></div><form class="studio-chat-form"><label for="studioChatInput" class="studio-sr-only"></label><textarea id="studioChatInput" maxlength="1500" rows="2" required></textarea><button class="studio-chat-send" type="submit">↑</button></form><button class="studio-ticket-toggle" type="button" aria-expanded="false"></button><form class="studio-ticket-form" hidden><label><span class="studio-ticket-message-label"></span><textarea name="message" minlength="10" maxlength="2000" rows="3" required></textarea></label><label><span class="studio-ticket-email-label"></span><input name="email" type="email" maxlength="254" autocomplete="email"></label><button type="submit"></button><output role="status"></output></form><p class="studio-chat-privacy"></p></section>';
    document.body.append(root);
    const find=s=>root.querySelector(s),panel=find('.studio-chat-panel'),input=find('#studioChatInput'),log=find('[role=log]'),form=find('.studio-chat-form'),launcher=find('.studio-chat-launch');
    const ticketToggle=find('.studio-ticket-toggle'),ticketForm=find('.studio-ticket-form');
    const suggestions=find('.studio-chat-suggestions'),topicsToggle=find('.studio-chat-topics-toggle');
    const choice=document.createElement('div');choice.className='studio-support-choice';choice.hidden=true;
    choice.innerHTML='<div class="studio-support-choice__card" role="dialog" aria-modal="true" aria-labelledby="studioSupportChoiceTitle"><div class="studio-support-choice__head"><h2 id="studioSupportChoiceTitle"></h2><button type="button" class="studio-support-choice__close" aria-label="Close">×</button></div><p class="studio-support-choice__hint"></p><a class="studio-support-choice__telegram" href="https://t.me/showcasemaker" target="_blank" rel="noopener noreferrer"></a><button type="button" class="studio-support-choice__report"></button></div>';
    document.body.append(choice);
    let choiceOrigin=null;
    function closeChoice(){choice.hidden=true;choiceOrigin?.focus();choiceOrigin=null}
    function paintChoice(){choice.querySelector('h2').textContent=t('Как связаться с нами?','How would you like to contact us?');choice.querySelector('.studio-support-choice__hint').textContent=t('Выбери удобный способ — обращение через сайт попадёт туда же, что и «Сообщить о проблеме».','Choose a channel. A report sent here uses the same form as “Report a problem”.');choice.querySelector('a').textContent=t('Написать в Telegram ↗','Open Telegram ↗');choice.querySelector('.studio-support-choice__report').textContent=t('Сообщить о проблеме на сайте','Report a problem on the site');choice.querySelector('.studio-support-choice__close').setAttribute('aria-label',t('Закрыть','Close'))}
    document.addEventListener('click',function(event){var link=event.target.closest('[data-support-choice]');if(!link)return;event.preventDefault();choiceOrigin=link;paintChoice();choice.hidden=false;choice.querySelector('.studio-support-choice__report').focus()});
    choice.querySelector('.studio-support-choice__close').addEventListener('click',closeChoice);
    choice.addEventListener('click',function(event){if(event.target===choice)closeChoice()});
    choice.addEventListener('keydown',function(event){if(event.key==='Escape')closeChoice()});
    choice.querySelector('.studio-support-choice__report').addEventListener('click',function(){closeChoice();if(panel.hidden)launcher.click();if(ticketForm.hidden)ticketToggle.click();ticketForm.message.focus()});
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
      find('.studio-ticket-email-label').textContent=t('Email для ответа (необязательно)','Reply email (optional)');
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
