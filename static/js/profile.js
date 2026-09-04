// profile.html L11-28
(function(){'use strict';
/* ---- i18n ---- */
var PDICT={
 en:{
  pf_title:'Steam profile editor — Showcase Maker',
  pf_designer:'Steam Profile Designer',pf_kind_static:'Static',pf_kind_animated:'Animated',
  pf_type_artwork:'Artwork 506+100',pf_type_featured:'Featured Artwork',pf_type_workshop:'Workshop ×5',pf_type_guide:'Favorite Guide',pf_type_info:'Custom Info',pf_type_artfav:'Favorite Artwork',
  pf_tab_design:'Design',pf_tab_profile:'Profile',pf_tab_export:'Export',
  pf_catalog_h:'Customization catalog',pf_catalog_hint:'Steam assets',
  pf_asset_bg:'Backgrounds',pf_asset_av:'Avatars',pf_asset_frame:'Frames',pf_asset_badge:'Badges',
  pf_ph_search:'Game or item name',pf_kind_all:'All',pf_more:'Show more',
  pf_showcases_h:'Profile showcases',pf_showcases_hint:'top-to-bottom order',pf_add:'Add',
  pf_slot_hint:'Click an image in the preview to upload PNG, GIF, WebM or MP4.',
  pf_account_data:'Account data',pf_import_h:'Import a public Steam profile',
  pf_import_ext:'Import my profile via the extension',pf_import_url:'Import by link',
  pf_basic_h:'Basics',pf_nick:'Nickname',pf_level:'Level',pf_status:'Status',pf_summary:'Summary',
  pf_offline:'Currently Offline',pf_online:'Currently Online',pf_ingame:'Currently In-Game',
  pf_stats_h:'Stats',pf_publish:'Publishing',pf_public_h:'Public profile',
  pf_save:'Save profile',pf_open_public:'Open public profile',pf_reset:'Discard unsaved changes',
  pf_live:'Live profile',pf_manual:'manual setup',pf_top:'Top',
  st_games:'Games',st_inventory:'Inventory',st_screenshots:'Screenshots',st_videos:'Videos',
  st_workshop:'Workshop',st_reviews:'Reviews',st_guides:'Guides',st_artwork:'Artwork',
  sc_up:'Move up',sc_down:'Move down',sc_del:'Remove',
  sc_artwork:'Artwork Showcase',sc_featured:'Featured Artwork Showcase',sc_workshop:'Workshop Showcase',
  sc_guide:'Favorite Guide',sc_info:'Custom Info Box',sc_artfav:'Favorite Artwork',
  sync_ext:'Steam API + extension',sync_html:'Steam API + profile',
  imp_wait:'Fetching Steam API, customization and showcases…',
  imp_done_a:'Done: ',imp_done_b:' showcase(s) · level ',imp_done_c:' · data is stored only in this account',
  lvl_hidden:'hidden',
  ext_missing:'The extension is not installed or is disabled',
  ext_check:'Checking the extension…',ext_no_reply:'The extension did not respond',
  ext_found_a:'Extension ',ext_found_b:' found. Preparing Steam…',
  ext_opening:'Opening Steam and collecting every public showcase…',
  ext_catalog_empty:'The extension catalog is still empty. Open your Steam profile and click Customization.',
  steam_confirm:'First we confirm your Steam account…',
  steam_popup:'Allow the pop-up window to sign in through Steam',
  steam_incomplete:'Steam sign-in was not completed',
  ticket_fail:'Could not create an import ticket',
  up_wait:'Uploading the file…',up_ok:'Media added. Save the profile to publish it.',
  save_wait:'Saving…',save_ok:'Saved. Public profile updated.',
  save_login:'Sign in to save a public profile.',
  pf_import_p:'The extension opens your Steam profile, waits for the whole page to load and copies over the background, frame, badges, stats and showcases. The Steam API fills in games and level.',
  pf_public_p:'Save your design — the link becomes available to other users and opens from the gallery.',
  ext_not_connected:'The extension is not connected to this page. Update it to 0.9.7 and reload the tab.',
  ext_done:'Import finished. Check the showcases and press «Save profile».'
  ,account_site:'Site account',account_settings:'Account settings',account_settings_hint:'Your identity and activity across Showcase Maker.',
  account_login_hint:'Sign in to view account details and activity.',login:'Log in',account_gallery_count:'Gallery uploads',account_showcase_count:'Profile showcases',
  account_identity:'Identity',account_nick:'Nickname',account_email:'Email',account_save_name:'Save nickname',account_password:'Change password',
  account_current_password:'Current password',account_new_password:'New password',account_repeat_password:'Repeat new password',account_change_password:'Change password'
 },
 ru:{
  pf_title:'Редактор Steam-профиля — Showcase Maker',
  pf_designer:'Дизайнер профиля Steam',pf_kind_static:'Статичные',pf_kind_animated:'Анимированные',
  pf_type_artwork:'Иллюстрация 506+100',pf_type_featured:'Избранная иллюстрация',pf_type_workshop:'Workshop ×5',pf_type_guide:'Избранное руководство',pf_type_info:'Информационный блок',pf_type_artfav:'Избранная иллюстрация',
  pf_tab_design:'Оформление',pf_tab_profile:'Профиль',pf_tab_export:'Экспорт',
  pf_catalog_h:'Каталог оформления',pf_catalog_hint:'ресурсы Steam',
  pf_asset_bg:'Фоны',pf_asset_av:'Аватары',pf_asset_frame:'Рамки',pf_asset_badge:'Значки',
  pf_ph_search:'Название игры или предмета',pf_kind_all:'Все',pf_more:'Показать ещё',
  pf_showcases_h:'Витрины профиля',pf_showcases_hint:'порядок сверху вниз',pf_add:'Добавить',
  pf_slot_hint:'Нажми на картинку в предпросмотре, чтобы загрузить PNG, GIF, WebM или MP4.',
  pf_account_data:'Данные аккаунта',pf_import_h:'Импорт публичного Steam-профиля',
  pf_import_ext:'Импортировать мой профиль через расширение',pf_import_url:'Импорт по ссылке',
  pf_basic_h:'Основное',pf_nick:'Ник',pf_level:'Уровень',pf_status:'Статус',pf_summary:'Описание',
  pf_offline:'Не в сети',pf_online:'В сети',pf_ingame:'В игре',
  pf_stats_h:'Статистика',pf_publish:'Публикация',pf_public_h:'Публичный профиль',
  pf_save:'Сохранить профиль',pf_open_public:'Открыть публичный профиль',pf_reset:'Сбросить несохранённые изменения',
  pf_live:'Живой профиль',pf_manual:'ручная настройка',pf_top:'Наверх',
  st_games:'Игры',st_inventory:'Инвентарь',st_screenshots:'Скриншоты',st_videos:'Видео',
  st_workshop:'Workshop',st_reviews:'Обзоры',st_guides:'Руководства',st_artwork:'Иллюстрации',
  sc_up:'Выше',sc_down:'Ниже',sc_del:'Удалить',
  sc_artwork:'Витрина иллюстраций',sc_featured:'Избранная иллюстрация',sc_workshop:'Витрина Workshop',
  sc_guide:'Избранное руководство',sc_info:'Информационный блок',sc_artfav:'Избранная иллюстрация',
  sync_ext:'Steam API + расширение',sync_html:'Steam API + профиль',
  imp_wait:'Получаем Steam API, оформление и витрины…',
  imp_done_a:'Готово: ',imp_done_b:' витрин · уровень ',imp_done_c:' · данные сохранены только в этом аккаунте',
  lvl_hidden:'скрыт',
  ext_missing:'Расширение не установлено или выключено',
  ext_check:'Проверяем расширение…',ext_no_reply:'Расширение не ответило',
  ext_found_a:'Расширение ',ext_found_b:' найдено. Подготавливаем Steam…',
  ext_opening:'Открываем Steam и собираем все публичные витрины…',
  ext_catalog_empty:'Каталог расширения пока пуст. Открой Steam-профиль и нажми Customization.',
  steam_confirm:'Сначала подтвердим твой Steam-аккаунт…',
  steam_popup:'Разреши всплывающее окно для входа через Steam',
  steam_incomplete:'Вход через Steam не завершён',
  ticket_fail:'Не удалось создать билет импорта',
  up_wait:'Загружаем файл…',up_ok:'Медиа добавлено. Сохрани профиль для публикации.',
  save_wait:'Сохраняем…',save_ok:'Сохранено. Публичный профиль обновлён.',
  save_login:'Войди в аккаунт, чтобы сохранить публичный профиль.',
  pf_import_p:'Расширение откроет твой Steam-профиль, дождётся загрузки всей страницы и перенесёт фон, рамку, значки, статистику и витрины. Steam API дополнит игры и уровень.',
  pf_public_p:'Сохрани оформление — ссылка будет доступна другим пользователям и откроется из галереи.',
  ext_not_connected:'Расширение не подключено к этой странице. Обнови его до 0.9.7 и перезагрузи вкладку сайта.',
  ext_done:'Импорт завершён. Проверь витрины и нажми «Сохранить профиль».'
  ,account_site:'Аккаунт сайта',account_settings:'Настройки аккаунта',account_settings_hint:'Ваш профиль и активность в Showcase Maker.',
  account_login_hint:'Войдите, чтобы увидеть данные аккаунта и активность.',login:'Войти',account_gallery_count:'Работ в галерее',account_showcase_count:'Витрин в профиле',
  account_identity:'Основные данные',account_nick:'Ник',account_email:'Почта',account_save_name:'Сохранить ник',account_password:'Смена пароля',
  account_current_password:'Текущий пароль',account_new_password:'Новый пароль',account_repeat_password:'Повторите новый пароль',account_change_password:'Изменить пароль'
 }
};
function pLang(){try{return window.SMLang?SMLang.get():'en'}catch(e){return 'en'}}
function pT(k){var pack=PDICT[pLang()]||PDICT.en;return pack[k]!=null?pack[k]:(PDICT.en[k]||'')}
function pShowcaseTitle(s){var names={'Artwork Showcase':'artwork','Featured Artwork Showcase':'featured','Workshop Showcase':'workshop','Favorite Guide':'guide','Custom Info Box':'info','Favorite Artwork':'artfav'};return names[String(s&&s.title||'')]?pT('sc_'+names[String(s.title)]):(s&&s.title)||pT('sc_'+(s&&s.type))||(s&&s.type)||''}
function applyProfileLang(){var pack=PDICT[pLang()]||PDICT.en;
 if(window.SMLang&&SMLang.apply){SMLang.apply(pack)}
 else{Array.prototype.forEach.call(document.querySelectorAll('[data-i]'),function(el){var v=pack[el.getAttribute('data-i')];if(v!=null)el.textContent=v});
      Array.prototype.forEach.call(document.querySelectorAll('[data-i-ph]'),function(el){var v=pack[el.getAttribute('data-i-ph')];if(v!=null)el.placeholder=v})}
 document.title=pT('pf_title')}
applyProfileLang();
window.addEventListener('sm:langchange',function(){applyProfileLang();document.querySelectorAll('[data-stat]').forEach(function(x){var s=x.closest('label')&&x.closest('label').querySelector('span');if(s)s.textContent=pT('st_'+x.dataset.stat)});try{render()}catch(e){}});
var state=SteamMockup.defaultState(),stage=document.getElementById('profileStage'),pending=null,asset='background',page=0,draftKey='sm_profile_draft:guest',lastSaved=null;function $(id){return document.getElementById(id)}function setStatus(id,text,kind){var e=$(id);e.textContent=text||'';e.className='status '+(kind||'')}function fitProfilePreview(){var pageEl=stage&&stage.querySelector('.profile_page');if(!pageEl)return;if(window.matchMedia('(max-width:820px)').matches){pageEl.style.zoom='1';pageEl.style.width='100%';return}var base=1000,available=Math.max(1,stage.clientWidth-32),scale=Math.min(1,available/base);pageEl.style.width=base+'px';pageEl.style.zoom=String(scale)}function render(){SteamMockup.render(state,stage);paintShowcases();syncStats();requestAnimationFrame(fitProfilePreview)}function sync(){['name','level','status','summary'].forEach(function(id){$(id).value=id==='level'?(state[id]||0):(state[id]||'')})}function mode(name){document.querySelectorAll('.mode-tab').forEach(function(x){x.classList.toggle('on',x.dataset.mode===name)});document.querySelectorAll('.mode-panel').forEach(function(x){x.classList.toggle('on',x.dataset.panel===name)})}document.querySelectorAll('.mode-tab').forEach(function(x){x.onclick=function(){mode(x.dataset.mode)}});if(window.ResizeObserver&&stage)new ResizeObserver(function(){fitProfilePreview()}).observe(stage);else window.addEventListener('resize',fitProfilePreview);
var stats=['games','inventory','screenshots','videos','workshop','reviews','guides','artwork'].map(function(k){return [k,pT('st_'+k)]});$('statFields').innerHTML=stats.map(function(x){return '<label class="field"><span>'+x[1]+'</span><input class="input" type="number" min="0" data-stat="'+x[0]+'"></label>'}).join('');function syncStats(){document.querySelectorAll('[data-stat]').forEach(function(x){if(document.activeElement!==x)x.value=(state.stats&&state.stats[x.dataset.stat])||0})}document.querySelectorAll('[data-stat]').forEach(function(x){x.oninput=function(){state.stats=state.stats||{};state.stats[x.dataset.stat]=Math.max(0,+x.value||0);render()}});
function paintShowcases(){var host=$('showcaseList');host.innerHTML=(state.showcases||[]).map(function(s,i){return '<div class="sc-row"><span>'+SteamMockup.esc(pShowcaseTitle(s))+'</span><button title="'+pT('sc_up')+'" data-up="'+i+'">↑</button><button title="'+pT('sc_down')+'" data-down="'+i+'">↓</button><button title="'+pT('sc_del')+'" data-del="'+i+'">×</button></div>'}).join('');host.querySelectorAll('[data-up]').forEach(function(b){b.onclick=function(){move(+b.dataset.up,-1)}});host.querySelectorAll('[data-down]').forEach(function(b){b.onclick=function(){move(+b.dataset.down,1)}});host.querySelectorAll('[data-del]').forEach(function(b){b.onclick=function(){state.showcases.splice(+b.dataset.del,1);render()}})}function move(i,d){var n=i+d;if(n<0||n>=state.showcases.length)return;var x=state.showcases.splice(i,1)[0];state.showcases.splice(n,0,x);render()}
['name','level','status','summary'].forEach(function(id){$(id).addEventListener(id==='status'?'change':'input',function(){state[id]=id==='level'?Math.max(0,+this.value||0):this.value;render()})});$('addShowcase').onclick=function(){var t=$('newType').value,base={type:t,title:pT('sc_'+t)||t,images:t==='workshop'?['','','','','']:(t==='artwork'?['','']:[''])};state.showcases.push(base);render()};
function applyImported(d,label){if(!d||!d.ok)throw Error(d&&d.msg||d&&d.error||'Steam profile unavailable');state=SteamMockup.applySteamProfile(d.profile,SteamMockup.defaultState());sync();render();stage.scrollTop=0;$('syncMode').textContent=label||pT('sync_ext');var n=(d.profile.showcase_instances||d.profile.showcases||[]).length;setStatus('importState',pT('imp_done_a')+n+pT('imp_done_b')+(d.profile.level==null?pT('lvl_hidden'):d.profile.level)+pT('imp_done_c'),'ok');mode('design')}
function importProfile(){var url=$('steamUrl').value.trim();if(!url)return;setStatus('importState',pT('imp_wait'),'wait');$('importProgress').classList.add('on');function fallback(){return fetch('/api/steam/profile?url='+encodeURIComponent(url)).then(function(r){return r.json()})}fetch('/api/profile/steam-import',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url})}).then(function(r){return r.status===401?fallback():r.json()}).then(function(d){applyImported(d,d.profile&&d.profile.sync_mode==='api_plus_html'?pT('sync_html'):'Steam API')}).catch(function(e){setStatus('importState',e.message,'bad')}).finally(function(){$('importProgress').classList.remove('on')})}$('importBtn').onclick=importProfile;$('steamUrl').onkeydown=function(e){if(e.key==='Enter')importProfile()};
var EXTENSION_ID='nopmeakgeongafdhgmlpllalpcfpedej';function bridgeMessage(message){return new Promise(function(resolve,reject){var bridgeTarget=window.parent!==window&&new URLSearchParams(location.search).get('embed')==='tools'&&['PING','GET_CUSTOMIZATION_CATALOG'].indexOf(message.type)>=0?window.parent:window;var id='ssh-'+Date.now()+'-'+Math.random().toString(36).slice(2),wait=message.type==='PING'?1200:90000,done=false;function finish(ok,value){if(done)return;done=true;clearTimeout(timer);window.removeEventListener('message',receive);ok?resolve(value):reject(value)}function receive(e){var d=e.data||{};if(e.source===bridgeTarget&&e.origin===location.origin&&d.source==='SSH_EXTENSION'&&d.type==='RESPONSE'&&d.requestId===id)finish(true,d.reply||{})}window.addEventListener('message',receive);var timer=setTimeout(function(){finish(false,Error('bridge-unavailable'))},wait);bridgeTarget.postMessage({source:'SSH_SITE',type:'REQUEST',requestId:id,payload:message},location.origin)})}function directMessage(message){return new Promise(function(resolve,reject){if(!window.chrome||!chrome.runtime||!chrome.runtime.sendMessage)return reject(Error(pT('ext_missing')));try{chrome.runtime.sendMessage(EXTENSION_ID,message,function(reply){if(chrome.runtime.lastError)return reject(Error(chrome.runtime.lastError.message));resolve(reply||{})})}catch(e){reject(e)}})}function extMessage(message){return bridgeMessage(message).catch(function(){return directMessage(message)}).catch(function(e){if(/Receiving end does not exist|Could not establish connection|bridge-unavailable/i.test(e.message||''))throw Error(pT('ext_not_connected'));throw e})}
function steamLogin(){return fetch('/api/auth/steam/login',{credentials:'same-origin'}).then(function(r){return r.json()}).then(function(d){if(!d.ok||!d.url)throw Error(d.msg||'Steam login unavailable');return new Promise(function(resolve,reject){var pop=window.open(d.url,'steam-login','width=780,height=760');if(!pop)return reject(Error(pT('steam_popup')));var timer=setTimeout(function(){window.removeEventListener('message',onMessage);reject(Error(pT('steam_incomplete')))},120000);function onMessage(e){if(e.origin!==location.origin||!e.data||e.data.type!=='steam_login')return;clearTimeout(timer);window.removeEventListener('message',onMessage);resolve()}window.addEventListener('message',onMessage)})})}
function getTicket(afterLogin){return fetch('/api/profile/import-ticket',{method:'POST',credentials:'same-origin'}).then(function(r){return r.json().then(function(d){return{status:r.status,data:d}})}).then(function(x){if((x.status===401||x.status===409)&&!afterLogin){setStatus('extensionState',pT('steam_confirm'),'wait');return steamLogin().then(function(){return getTicket(true)})}if(!x.data.ok)throw Error(x.data.msg||pT('ticket_fail'));return x.data})}
function extensionImport(){setStatus('extensionState',pT('ext_check'),'wait');$('importProgress').classList.add('on');extMessage({type:'PING'}).then(function(p){if(!p.ok)throw Error(pT('ext_no_reply'));setStatus('extensionState',pT('ext_found_a')+p.version+pT('ext_found_b'),'wait');return getTicket(false)}).then(function(t){setStatus('extensionState',pT('ext_opening'),'wait');return extMessage({type:'IMPORT_STEAM_PROFILE',ticket:t.ticket,steamid:t.steamid,profileUrl:t.profile_url,apiBase:location.origin})}).then(function(d){applyImported(d,pT('sync_ext'));setStatus('extensionState',pT('ext_done'),'ok')}).catch(function(e){setStatus('extensionState',e.message,'bad')}).finally(function(){$('importProgress').classList.remove('on')})}$('extensionImportBtn').onclick=extensionImport;
function appendCatalog(items,q){(items||[]).filter(function(it){return !q||String(it.name||it.game||'').toLowerCase().indexOf(q.toLowerCase())>=0}).forEach(function(it){var u=it.movie||it.video||it.image||it.url||'';if(!u)return;var poster=it.preview||it.image||u,b=document.createElement('button');b.className='asset';b.innerHTML=/\.(webm|mp4)(\?|$)/i.test(u)?'<video src="'+SteamMockup.esc(SteamMockup.px(u))+'" poster="'+SteamMockup.esc(SteamMockup.px(poster))+'" muted autoplay loop playsinline></video>':'<img src="'+SteamMockup.esc(SteamMockup.px(poster))+'" alt=""><span>'+SteamMockup.esc(it.name||it.game||'Steam')+'</span>';b.onclick=function(){if(asset==='background'){state.background=it.image||poster||'';state.backgroundMovie=it.movie||it.video||'';stage.scrollTop=0}else if(asset==='badge'){state.favBadge={image:it.image||u,title:it.name||'Favorite Badge',xp:''};state.badges=[{image:it.image||u}].concat(state.badges||[])}else state[asset]=it.movie||it.image||u;render()};$('catalog').appendChild(b)})}
function extensionCatalog(q,kind){var types;if(asset==='background')types=kind==='animated'?['animated_background']:(kind==='static'?['background']:['animated_background','background']);else if(asset==='frame'||asset==='avatar')types=[asset];else return Promise.reject(Error('server-catalog'));return extMessage({type:'PING'}).then(function(){return Promise.all(types.map(function(t){return extMessage({type:'GET_CUSTOMIZATION_CATALOG',asset:t,page:page,count:30})}))}).then(function(parts){var items=[];parts.forEach(function(d){if(d&&d.ok)items=items.concat(d.items||[])});if(!items.length)throw Error(pT('ext_catalog_empty'));appendCatalog(items,q);page++})}
function loadAssets(reset){if(reset){page=0;$('catalog').innerHTML=''}var q=$('assetSearch').value.trim(),kind=$('assetKind').value,requestAsset=asset;extensionCatalog(q,kind).catch(function(){if(asset==='background')requestAsset=kind==='animated'?'animated_background':'points_background';return fetch('/api/steam/backgrounds?asset='+requestAsset+'&kind='+kind+'&q='+encodeURIComponent(q)+'&page='+page+'&count=18').then(function(r){return r.json()}).then(function(d){if(!d.ok)throw Error(d.msg||'Catalog unavailable');appendCatalog(d.items||[],q);page++})}).catch(function(e){setStatus('saveState',e.message,'bad')})}
$('assetTabs').querySelectorAll('button').forEach(function(b){b.onclick=function(){$('assetTabs').querySelectorAll('button').forEach(function(x){x.classList.toggle('on',x===b)});asset=b.dataset.asset;$('assetKind').disabled=asset==='badge';loadAssets(true)}});var searchTimer;$('assetSearch').oninput=function(){clearTimeout(searchTimer);searchTimer=setTimeout(function(){loadAssets(true)},350)};$('assetKind').onchange=function(){loadAssets(true)};$('moreAssets').onclick=function(){loadAssets(false)};
stage.addEventListener('click',function(e){var el=e.target.closest('[data-slot]');if(!el)return;pending={slot:el.dataset.slot,index:el.dataset.index};$('mediaInput').value='';$('mediaInput').click()});$('mediaInput').onchange=function(){var f=this.files&&this.files[0];if(!f||!pending)return;var fd=new FormData();fd.append('file',f);setStatus('saveState',pT('up_wait'),'wait');fetch('/api/profile/asset',{method:'POST',credentials:'same-origin',body:fd}).then(function(r){return r.json()}).then(function(d){if(!d.ok)throw Error(d.msg||'Upload failed');if(pending.slot==='avatar')state.avatar=d.url;else if(pending.slot==='favBadge')state.favBadge.image=d.url;else{var p=String(pending.index).split(':'),sc=state.showcases[+p[0]];if(sc){sc.images=sc.images||[];sc.images[+p[1]]=d.url}}render();setStatus('saveState',pT('up_ok'),'ok')}).catch(function(e){setStatus('saveState',e.message,'bad')})};
$('saveBtn').onclick=function(){setStatus('saveState',pT('save_wait'),'wait');fetch('/api/profile/snapshot',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({snapshot:state})}).then(function(r){return r.json()}).then(function(d){if(!d.ok)throw Error(d.msg||'Save failed');lastSaved=JSON.parse(JSON.stringify(state));$('publicLink').href=d.url;$('publicLink').hidden=false;localStorage.setItem(draftKey,JSON.stringify(state));if(window.SSShell&&window.SSShell.loadMe)window.SSShell.loadMe();setStatus('saveState',pT('save_ok'),'ok')}).catch(function(e){setStatus('saveState',e.message==='Login required'?pT('save_login'):e.message,'bad')})};$('resetBtn').onclick=function(){state=lastSaved?JSON.parse(JSON.stringify(lastSaved)):SteamMockup.defaultState();sync();render()};$('topBtn').onclick=function(){stage.scrollTo({top:0,behavior:'smooth'})};
fetch('/api/profile/me',{credentials:'same-origin'}).then(function(r){return r.ok?r.json():null}).then(function(d){if(d&&d.ok){var p=d.profile||{};draftKey='sm_profile_draft:user:'+(p.id||p.username||'unknown');if(p.snapshot)state=Object.assign(SteamMockup.defaultState(),p.snapshot);else if(p.steam)state=SteamMockup.applySteamProfile(p.steam,SteamMockup.defaultState());lastSaved=JSON.parse(JSON.stringify(state));if(p.username){$('publicLink').href='/profile/'+encodeURIComponent(p.username);$('publicLink').hidden=false}}else{try{var draft=JSON.parse(localStorage.getItem(draftKey)||'null');if(draft)state=Object.assign(SteamMockup.defaultState(),draft)}catch(e){}}sync();render()}).catch(function(){sync();render()});sync();render();loadAssets(true)})();

/* Site account panel: deliberately independent from the profile canvas state. */
(function(){
 var A={en:{free:'Free',pro:'Pro',saved:'Nickname saved',saving:'Saving…',fill:'Fill in all password fields',match:'New passwords do not match',short:'Use at least 6 characters',changing:'Changing password…',changed:'Password changed'},ru:{free:'Free',pro:'Pro',saved:'Ник сохранён',saving:'Сохраняем…',fill:'Заполните все поля пароля',match:'Новые пароли не совпадают',short:'Минимум 6 символов',changing:'Меняем пароль…',changed:'Пароль изменён'}};
 function t(k){var l=window.SMLang&&SMLang.get()==='ru'?'ru':'en';return A[l][k]||A.en[k]||k}
 function el(id){return document.getElementById(id)}
 function state(id,text,kind){var n=el(id);if(!n)return;n.textContent=text||'';n.className='account-state '+(kind||'')}
 function paint(d){
  var guest=el('accountGuest'),content=el('accountContent');
  if(!d||!d.ok){if(guest)guest.hidden=false;if(content)content.hidden=true;return}
  if(guest)guest.hidden=true;if(content)content.hidden=false;
  el('accountName').textContent=d.display_name||d.email.split('@')[0];
  el('accountDisplayName').value=d.display_name||'';el('accountEmail').value=d.email||'';
  el('accountPlan').textContent=d.is_pro?t('pro'):t('free');el('accountPlan').className=d.is_pro?'is-pro':'';
  el('accountGalleryCount').textContent=d.gallery_uploads||0;el('accountShowcaseCount').textContent=d.showcase_count||0;
  var av=el('accountAvatar');if(d.avatar_url)av.innerHTML='<img src="'+d.avatar_url+'" alt="">';else av.textContent=(d.display_name||d.email||'S').charAt(0).toUpperCase();
 }
 function load(){return fetch('/api/profile/account-overview',{credentials:'same-origin'}).then(function(r){return r.json()}).then(paint).catch(function(){paint(null)})}
 var login=el('accountLogin');if(login)login.onclick=function(){if(window.SSShell&&SSShell.openAuth)SSShell.openAuth('login')};
 var save=el('accountSaveName');if(save)save.onclick=function(){var name=el('accountDisplayName').value.trim();state('accountNameState',t('saving'),'wait');save.disabled=true;fetch('/api/profile/update',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({display_name:name})}).then(function(r){return r.json()}).then(function(d){if(!d.ok)throw Error(d.msg||'Save failed');state('accountNameState',t('saved'),'ok');return load()}).catch(function(e){state('accountNameState',e.message,'bad')}).finally(function(){save.disabled=false})};
 var change=el('accountChangePassword');if(change)change.onclick=function(){var current=el('accountCurrentPassword').value,newPassword=el('accountNewPassword').value,repeat=el('accountRepeatPassword').value;if(!current||!newPassword||!repeat){state('accountPasswordState',t('fill'),'bad');return}if(newPassword!==repeat){state('accountPasswordState',t('match'),'bad');return}if(newPassword.length<6){state('accountPasswordState',t('short'),'bad');return}state('accountPasswordState',t('changing'),'wait');change.disabled=true;fetch('/api/auth/change-password',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({current_password:current,new_password:newPassword})}).then(function(r){return r.json()}).then(function(d){if(!d.ok)throw Error(d.msg||'Password change failed');el('accountCurrentPassword').value='';el('accountNewPassword').value='';el('accountRepeatPassword').value='';state('accountPasswordState',t('changed'),'ok')}).catch(function(e){state('accountPasswordState',e.message,'bad')}).finally(function(){change.disabled=false})};
 document.addEventListener('ss:me',function(e){if(e.detail&&e.detail.logged_in)load();else paint(null)});
 window.addEventListener('sm:langchange',function(){load()});
 load();
})();
