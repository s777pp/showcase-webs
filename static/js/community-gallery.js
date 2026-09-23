(function () {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const query = new URLSearchParams(location.search);
  const author = query.get('author') || '';
  const state = { items: [], total: 0, offset: 0, mode: '', animation: '', sort: 'new', loading: false,
    loggedIn: false, detail: null, jobId: query.get('job') || '', editId: null, previewUrl: '' };
  const dict = {
    en: { eyebrow:'SHOWCASE MAKER / COMMUNITY',heading:'Works made to be seen',intro:'Explore finished Steam showcases and download ready-to-use files.',publish:'Publish work',authorLabel:'CREATOR',works:'Works',downloads:'Downloads',likes:'Likes',editProfile:'Edit author profile',filterTitle:'Showcase type',reset:'Reset',motionTitle:'Media',sort:'Sort',sortNew:'Newest first',sortPopular:'Most downloaded',sortLiked:'Most liked',note:'Choose a showcase type to see files prepared for that Steam slot.',allWorks:'All works',emptyTitle:'No works here yet',emptyCopy:'Try another category or publish the first work.',loading:'Loading works…',more:'Show more',background:'Steam background ↗',downloadZip:'Download ZIP',buy:'Open store ↗',like:'Like',share:'Share',edit:'Edit',delete:'Delete work',publishKicker:'SHOWCASE MAKER / NEW WORK',publishTitle:'Publish your showcase',previewUpload:'Add a preview image, GIF or video',previewTypes:'PNG, JPG, WebP, GIF, MP4 or WebM',chooseFile:'Choose file',previewHelp:'People will see this in the catalogue. For processed work, we can take a preview from the ZIP.',title:'Title',description:'Description',category:'Showcase type',backgroundUrl:'Steam background link (optional)',archive:'Ready ZIP',archiveHint:'Add the ZIP with files ready for Steam.',jobArchive:'The completed ZIP from Process will be attached automatically.',access:'Access',free:'Free download for signed-in users',paid:'Sold elsewhere',saleUrl:'Purchase link',adult:'18+ work — blur the preview until the visitor confirms',rights:'I have the rights to publish this work.',publishAction:'Publish work',adultTitle:'18+ content',adultCopy:'Confirm that you are an adult to view this work.',cancel:'Cancel',confirmAdult:'I am 18 or older',all:'All',workshop:'Workshop',split:'Artwork Split',featured:'Featured',static:'Static',animated:'Animated',noDesc:'No description yet.',published:'Work published.',updated:'Changes saved.',removed:'Work deleted.',confirmDelete:'Delete this work and its files?',signIn:'Sign in to continue.',failed:'Could not load works. Try again.',publishedBy:'by',shareCopied:'Link copied.',uploading:'Uploading and saving…',previewNeeded:'Add a preview file or a completed processing job.',archiveNeeded:'Add the ready ZIP.',ageBadge:'18+',paidBadge:'Paid',freeBadge:'Free',openProfile:'View creator’s profile',authorWorks:'Works by',close:'Close' },
    ru: { eyebrow:'SHOWCASE MAKER / СООБЩЕСТВО',heading:'Работы, которые хочется показать',intro:'Смотри готовые витрины Steam и скачивай комплекты для загрузки.',publish:'Опубликовать работу',authorLabel:'АВТОР',works:'Работы',downloads:'Загрузки',likes:'Лайки',editProfile:'Настроить профиль автора',filterTitle:'Тип витрины',reset:'Сбросить',motionTitle:'Медиа',sort:'Сортировка',sortNew:'Сначала новые',sortPopular:'Чаще скачивают',sortLiked:'Больше лайков',note:'Выбери тип витрины, чтобы увидеть работы под нужный слот Steam.',allWorks:'Все работы',emptyTitle:'Здесь пока нет работ',emptyCopy:'Выбери другую категорию или опубликуй первую работу.',loading:'Загружаем работы…',more:'Показать ещё',background:'Фон Steam ↗',downloadZip:'Скачать ZIP',buy:'Перейти к покупке ↗',like:'Нравится',share:'Поделиться',edit:'Изменить',delete:'Удалить работу',publishKicker:'SHOWCASE MAKER / НОВАЯ РАБОТА',publishTitle:'Опубликовать витрину',previewUpload:'Добавь изображение, GIF или видео для превью',previewTypes:'PNG, JPG, WebP, GIF, MP4 или WebM',chooseFile:'Выбрать файл',previewHelp:'Это увидят посетители галереи. Для результата «Обработки» превью можно взять из ZIP автоматически.',title:'Название',description:'Описание',category:'Тип витрины',backgroundUrl:'Ссылка на фон Steam (необязательно)',archive:'Готовый ZIP',archiveHint:'Добавь архив с файлами, готовыми для Steam.',jobArchive:'Готовый ZIP из «Обработки» приложится автоматически.',access:'Доступ',free:'Бесплатно для авторизованных',paid:'Продаётся на другой площадке',saleUrl:'Ссылка на покупку',adult:'Работа 18+ — превью будет размыто до подтверждения возраста',rights:'Подтверждаю, что имею права на публикацию работы.',publishAction:'Опубликовать работу',adultTitle:'Контент 18+',adultCopy:'Подтверди, что тебе исполнилось 18 лет.',cancel:'Отмена',confirmAdult:'Мне есть 18 лет',all:'Все',workshop:'Мастерская',split:'Иллюстрации',featured:'Избранные иллюстрации',static:'Статичная',animated:'Анимированная',noDesc:'Описание пока не добавлено.',published:'Работа опубликована.',updated:'Изменения сохранены.',removed:'Работа удалена.',confirmDelete:'Удалить работу вместе с её файлами?',signIn:'Войди в аккаунт, чтобы продолжить.',failed:'Не удалось загрузить работы. Попробуй ещё раз.',publishedBy:'автор:',shareCopied:'Ссылка скопирована.',uploading:'Загружаем и сохраняем…',previewNeeded:'Добавь превью или готовый результат обработки.',archiveNeeded:'Добавь готовый ZIP.',ageBadge:'18+',paidBadge:'Платно',freeBadge:'Бесплатно',openProfile:'Открыть профиль автора',authorWorks:'Работы автора',close:'Закрыть' }
  };
  dict.en.intro = 'Explore works made for Steam showcases and download creator archives.';
  dict.ru.intro = 'Смотри работы для витрин Steam и скачивай архивы авторов.';
  dict.en.note = 'Choose a showcase category to filter the works.';
  dict.ru.note = 'Выбери тип витрины, чтобы отфильтровать работы.';
  dict.en.archive = 'Work archive (ZIP)';
  dict.ru.archive = 'Архив работы (ZIP)';
  dict.en.archiveHint = 'ZIP up to 80 MB; each PNG, JPG or GIF inside up to 25 MB. Steam’s 5 MB-per-file limit does not block gallery publication.';
  dict.ru.archiveHint = 'ZIP до 80 МБ; каждый PNG, JPG или GIF внутри — до 25 МБ. Лимит Steam 5 МБ на файл не мешает публикации в галерее.';
  dict.en.archiveNeeded = 'Add a ZIP with the work files.';
  dict.ru.archiveNeeded = 'Добавь ZIP с файлами работы.';
  const lang = () => window.SMLang?.get?.() === 'ru' ? 'ru' : 'en';
  const t = (key) => dict[lang()][key] || dict.en[key] || key;
  function serverError(data) {
    const message = String(data?.msg || t('failed'));
    if (lang() !== 'ru') return message;
    const known = {
      'ZIP is not a complete Steam-ready set for this showcase type': 'Архив не прошёл проверку файлов для витрины.',
      'ZIP contains an unsafe file path': 'В архиве есть небезопасный путь к файлу. Собери ZIP заново.',
      'ZIP contains an unreadable image or GIF': 'В архиве есть повреждённое изображение или GIF.',
      'ZIP contains an unsupported image or GIF': 'В архиве есть изображение или GIF неподдерживаемого формата.',
      'ZIP image dimensions are too large': 'У одного из изображений в архиве слишком большие размеры.',
      'GIF has too many frames': 'В одном из GIF слишком много кадров.',
      'ZIP may contain only PNG, JPG or GIF files': 'В ZIP можно добавлять только PNG, JPG и GIF.',
      'Unpacked files are too large': 'Файлы внутри ZIP превышают лимит галереи: 25 МБ на файл или 160 МБ суммарно.',
      'Add a ZIP with the work files': 'Добавь ZIP с файлами работы.',
      'Upload a ZIP with PNG, JPG or GIF files': 'Загрузи ZIP с файлами PNG, JPG или GIF.',
      'Add a preview image, GIF or video': 'Добавь изображение, GIF или видео для превью.',
      'Add a purchase link': 'Добавь ссылку на покупку.',
      'Check the title, showcase type and publishing rights': 'Проверь название, тип витрины и подтверждение прав.',
      'Use a full https:// link': 'Вставь полную ссылку, начинающуюся с https://.',
      'Link is too long': 'Ссылка слишком длинная.',
      'File is too large': 'Файл слишком большой.',
      'Preview dimensions are too large': 'Превью слишком большое по размеру изображения.',
      'This work has no ZIP. Publish a new free release with files': 'Для бесплатной работы нужен ZIP. Опубликуй новую работу с файлами.',
    };
    return known[message] || message;
  }
  const workCount = (count) => {
    if (lang() !== 'ru') return count + ' ' + (count === 1 ? 'work' : 'works');
    const tail = count % 100, digit = count % 10;
    return count + ' ' + (tail >= 11 && tail <= 14 ? 'работ' : digit === 1 ? 'работа' : digit >= 2 && digit <= 4 ? 'работы' : 'работ');
  };
  const categoryKeys = ['', 'workshop', 'split', 'featured'];
  const motionKeys = ['', 'static', 'animated'];
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  let restoreFocus = null;
  let loadEpoch = 0;

  function localize() {
    document.documentElement.lang = lang();
    document.title = (author ? t('authorWorks') + ' · ' : '') + t('allWorks') + ' — Showcase Maker';
    document.querySelectorAll('[data-gallery-i]').forEach((node) => { node.textContent = t(node.dataset.galleryI); });
    $('publishMode').querySelectorAll('option').forEach((node) => { node.textContent = t(node.value); });
    if(state.jobId&&!state.editId&&!$('publishOverlay').hidden){
      $('previewDrop').querySelector('strong').textContent=lang()==='ru'?'Превью возьмём из готового результата':'The finished result will provide the preview';
      $('previewDrop').querySelector('small').textContent=lang()==='ru'?'Можно выбрать свой файл вместо автоматического превью':'You can choose your own file instead';
    }
    renderFilters(); renderGrid();
    if (state.detail) renderDetail(state.detail);
  }
  function renderFilters() {
    for (const [host, values, active, property] of [[$('categoryFilters'),categoryKeys,state.mode,'mode'],[$('animationFilters'),motionKeys,state.animation,'animation']]) {
      host.replaceChildren();
      values.forEach((value) => {
        const button = document.createElement('button'); button.type = 'button'; button.textContent = t(value || 'all');
        button.className = value === active ? 'is-active' : ''; button.setAttribute('aria-pressed', value === active ? 'true' : 'false');
        button.addEventListener('click', () => { state[property] = value; state.offset = 0; state.items = []; load(); });
        host.appendChild(button);
      });
    }
    $('resultsTitle').textContent = t(state.mode || 'allWorks');
  }
  function params() {
    const p = new URLSearchParams({limit:'24',offset:String(state.offset),sort:state.sort});
    if (author) p.set('author',author);
    if (state.mode) p.set('mode',state.mode);
    if (state.animation) p.set('animation',state.animation);
    return p;
  }
  function textNode(tag, value, className) { const n = document.createElement(tag); n.textContent = value; if (className) n.className=className; return n; }
  function mediaFor(item, full) {
    const animatedVideo = !!item.video_preview;
    const media = document.createElement(full && animatedVideo ? 'video' : 'img');
    if (media.tagName === 'VIDEO') { media.src = item.preview_url; media.controls=true; media.muted=true; media.loop=true; media.playsInline=true; media.autoplay=true; }
    else { media.src = full ? item.preview_url : (item.thumb_url || item.preview_url); media.alt = item.title; media.loading = full ? 'eager' : 'lazy'; media.decoding='async'; }
    return media;
  }
  function card(item) {
    const button = document.createElement('button'); button.type='button'; button.className='community-card'; button.dataset.workId=String(item.id);
    const visual = document.createElement('span'); visual.className='community-card__visual'; visual.appendChild(mediaFor(item,false));
    const seams = textNode('span','','community-card__seams'); visual.appendChild(seams);
    const badges = document.createElement('span'); badges.className='community-card__badges'; badges.appendChild(textNode('span',t(item.mode),'community-card__mode'));
    if (item.animated) badges.appendChild(textNode('span',item.video_preview?'VIDEO':'GIF','community-card__gif'));
    if (item.paid) badges.appendChild(textNode('span',t('paidBadge'),'community-card__paid'));
    visual.appendChild(badges);
    if (item.adult && sessionStorage.getItem('sm_gallery_adult_ok')!=='1') { button.classList.add('is-adult'); visual.appendChild(textNode('span',t('ageBadge'),'community-card__adult')); }
    const content = document.createElement('span'); content.className='community-card__content';
    content.appendChild(textNode('strong',item.title));
    const sub = textNode('span',item.author+'  ·  ↓ '+item.downloads+'  ·  ♥ '+item.likes); content.appendChild(sub);
    button.append(visual,content);
    button.addEventListener('click', () => openWork(item.id));
    if (!reduced.matches) button.addEventListener('pointermove',(event)=>{
      const rect=button.getBoundingClientRect(),x=((event.clientX-rect.left)/rect.width-.5)*7,y=((event.clientY-rect.top)/rect.height-.5)*7;
      button.style.setProperty('--card-x',x.toFixed(2)+'px');button.style.setProperty('--card-y',y.toFixed(2)+'px');
    });
    button.addEventListener('pointerleave',()=>{button.style.removeProperty('--card-x');button.style.removeProperty('--card-y');});
    return button;
  }
  function renderGrid() {
    const grid=$('galleryGrid'); grid.replaceChildren(); state.items.forEach((item)=>grid.appendChild(card(item)));
    $('galleryEmpty').hidden=state.loading || !!state.items.length;
    $('resultsCount').textContent=workCount(state.total);
    $('galleryTotal').textContent=String(state.total).padStart(3,'0');
    $('galleryMore').hidden=state.items.length>=state.total || state.loading;
  }
  function renderAuthor(info) {
    const banner=$('authorBanner'); banner.hidden=!info;
    if (!info) return;
    $('galleryHeading').textContent=t('authorWorks')+' '+info.name;
    $('galleryIntro').textContent=info.bio || t('intro');
    $('authorName').textContent=info.name; $('authorBio').textContent=info.bio || '';
    $('authorAvatar').src=info.avatar_url || '/static/icon.png';
    $('authorWorks').textContent=info.stats.works; $('authorDownloads').textContent=info.stats.downloads; $('authorLikes').textContent=info.stats.likes;
    $('authorEdit').hidden=!info.owner;
    const links=$('authorLinks'); links.replaceChildren(); Object.entries(info.links||{}).forEach(([name,url])=>{if(!url)return;const a=textNode('a',name==='website'?'Website':name[0].toUpperCase()+name.slice(1));a.href=url;a.target='_blank';a.rel='noopener noreferrer';links.appendChild(a);});
  }
  async function load() {
    const epoch = ++loadEpoch;
    state.loading=true; $('galleryLoading').hidden=false; $('galleryEmpty').hidden=true; renderFilters();
    try {
      const r=await fetch('/api/gallery/works?'+params(),{credentials:'same-origin'}); const data=await r.json();
      if (epoch !== loadEpoch) return;
      if (!r.ok || !data.ok) throw Error(data.msg||t('failed'));
      $('galleryEmpty').querySelector('b').textContent=t('emptyTitle');
      state.loggedIn=!!data.logged_in; state.total=data.total; state.items.push(...data.items); state.offset=state.items.length;
      renderAuthor(data.author); if (data.author) $('resultsTitle').textContent=t(state.mode||'allWorks');
    } catch (error) { if(epoch===loadEpoch)$('galleryEmpty').querySelector('b').textContent=error.message||t('failed'); }
    finally {if(epoch===loadEpoch){state.loading=false;$('galleryLoading').hidden=true;renderGrid();}}
  }
  function openOverlay(id) {restoreFocus=document.activeElement;$(id).hidden=false;document.body.classList.add('community-modal-open');$(id).querySelector('button')?.focus();}
  function closeOverlay(id) {$(id).hidden=true;if(!['workOverlay','publishOverlay','adultOverlay'].some((key)=>!$(key).hidden))document.body.classList.remove('community-modal-open');restoreFocus?.focus?.();}
  let adultPending=null;
  function openWork(id) {
    const item=state.items.find((entry)=>entry.id===id);
    if (item?.adult && sessionStorage.getItem('sm_gallery_adult_ok')!=='1') {adultPending=id;openOverlay('adultOverlay');return;}
    fetch('/api/gallery/works/'+id,{credentials:'same-origin'}).then((r)=>r.json()).then((data)=>{
      if(!data.ok)throw Error(data.msg);
      if(data.item.adult && sessionStorage.getItem('sm_gallery_adult_ok')!=='1'){adultPending=id;openOverlay('adultOverlay');return;}
      state.detail=data.item;renderDetail(data.item);openOverlay('workOverlay');
      history.replaceState(null,'',new URL(location.href).pathname+'?'+new URLSearchParams({...Object.fromEntries(query),work:String(id)}));
    }).catch((error)=>alert(error.message||t('failed')));
  }
  function renderDetail(item) {
    $('detailType').textContent=t(item.mode)+(item.animated?' · '+(item.video_preview?'VIDEO':'GIF'):' · '+t('static'));
    $('detailTitle').textContent=item.title;$('detailDescription').textContent=item.description||t('noDesc');
    $('detailDownloads').textContent=item.downloads;$('detailLikes').textContent=item.likes;
    const creator=$('detailAuthor');creator.href=item.author_url||'#';creator.replaceChildren();
    const avatar=document.createElement('img');avatar.src=item.avatar_url||'/static/icon.png';avatar.alt='';creator.append(avatar,textNode('span',item.author));
    $('detailBackground').hidden=!item.background_url;if(item.background_url)$('detailBackground').href=item.background_url;
    const visual=$('detailPreview');visual.replaceChildren(mediaFor(item,true));
    $('detailDownload').hidden=!item.download_url;$('detailDownload').href=item.download_url||'#';
    $('detailBuy').hidden=!item.paid;$('detailBuy').href=item.sale_url||'#';
    $('detailLike').classList.toggle('is-liked',!!item.liked);
    $('detailOwner').hidden=!item.owner;$('detailFeedback').textContent='';
  }
  function selectedPaid() { return document.querySelector('input[name="accessMode"]:checked')?.value==='paid'; }
  function updateAccess() {const paid=selectedPaid();$('saleLinkField').hidden=!paid;$('publishSaleUrl').required=paid;$('publishArchive').closest('label').hidden=paid||!!state.editId;$('publishArchive').required=!paid&&!state.jobId&&!state.editId;}
  function updatePreview() {
    if(state.previewUrl)URL.revokeObjectURL(state.previewUrl);
    const file=$('publishPreview').files?.[0],box=$('previewSelected');box.replaceChildren();box.hidden=!file;
    $('previewDrop').hidden=!!file;
    if(!file)return;
    state.previewUrl=URL.createObjectURL(file);
    const media=document.createElement(file.type.startsWith('video/')?'video':'img'); media.src=state.previewUrl;
    if(media.tagName==='VIDEO'){media.controls=true;media.muted=true;}
    box.append(media,textNode('span',file.name));
    const change=textNode('button',t('chooseFile'));change.type='button';change.addEventListener('click',()=>$('publishPreview').click());box.appendChild(change);
  }
  function openPublish(editItem) {
    if(!state.loggedIn){window.SSShell?.openAuth?.('login');return;}
    $('publishForm').reset();state.editId=editItem?.id||null;
    $('publishTitle').textContent=state.editId?t('edit'):t('publishTitle');
    $('publishName').value=editItem?.title||query.get('title')||'';
    $('publishDescription').value=editItem?.description||'';
    $('publishMode').value=editItem?.mode||query.get('mode')||'workshop';
    $('publishBackground').value=editItem?.background_url||query.get('background')||'';
    $('publishAdult').checked=!!editItem?.adult;
    $('publishSaleUrl').value=editItem?.sale_url||'';
    document.querySelector('input[name="accessMode"][value="'+(editItem?.paid?'paid':'free')+'"]').checked=true;
    $('publishRights').checked=!!editItem;
    $('publishArchive').closest('label').hidden=!!editItem;
    $('jobArchiveNote').textContent=state.jobId&&!editItem?t('jobArchive'):t('archiveHint');
    if(state.jobId&&!editItem){
      $('previewDrop').querySelector('strong').textContent=lang()==='ru'?'Превью возьмём из готового результата':'The finished result will provide the preview';
      $('previewDrop').querySelector('small').textContent=lang()==='ru'?'Можно выбрать свой файл вместо автоматического превью':'You can choose your own file instead';
    }else{
      $('previewDrop').querySelector('strong').textContent=t('previewUpload');
      $('previewDrop').querySelector('small').textContent=t('previewTypes');
    }
    $('publishFeedback').textContent='';$('publishSubmit').textContent=state.editId?t('edit'):t('publishAction');
    $('publishPreview').value='';updatePreview();$('previewDrop').hidden=!!editItem;$('previewSelected').hidden=true;
    updateAccess();openOverlay('publishOverlay');
  }
  async function submitPublish(event) {
    event.preventDefault();const button=$('publishSubmit'),status=$('publishFeedback');button.disabled=true;status.textContent=t('uploading');
    try {
      const paid=selectedPaid();let response;
      if(state.editId){
        response=await fetch('/api/gallery/works/'+state.editId,{method:'PUT',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:$('publishName').value,description:$('publishDescription').value,mode:$('publishMode').value,background_url:$('publishBackground').value,sale_url:$('publishSaleUrl').value,is_paid:paid,is_adult:$('publishAdult').checked})});
      } else {
        if(!paid&&!state.jobId&&!$('publishArchive').files?.length)throw Error(t('archiveNeeded'));
        if(!state.jobId&&!$('publishPreview').files?.length)throw Error(t('previewNeeded'));
        const fd=new FormData();for(const [key,value] of [['title',$('publishName').value],['description',$('publishDescription').value],['mode',$('publishMode').value],['background_url',$('publishBackground').value],['sale_url',$('publishSaleUrl').value],['is_paid',String(paid)],['is_adult',String($('publishAdult').checked)],['rights_confirmed',String($('publishRights').checked)],['job_id',state.jobId]])fd.append(key,value);
        if($('publishPreview').files?.[0])fd.append('preview',$('publishPreview').files[0]);
        if($('publishArchive').files?.[0])fd.append('archive',$('publishArchive').files[0]);
        response=await fetch('/api/gallery/works',{method:'POST',credentials:'same-origin',body:fd});
      }
      const data=await response.json();
      if(response.status===413&&data.code==='GALLERY_STORAGE_QUOTA'){
        throw Error(lang()==='ru'?'Хранилище галереи заполнено. Удали старую работу, чтобы освободить место.':'Gallery storage is full. Delete an old work to free space.');
      }
      if(!response.ok||!data.ok)throw Error(serverError(data));
      status.textContent=state.editId?t('updated'):t('published');state.jobId='';
      closeOverlay('publishOverlay');state.items=[];state.offset=0;await load();if(data.id)openWork(data.id);
    }catch(error){status.textContent=error.message||t('failed');}
    finally{button.disabled=false;}
  }
  $('filtersReset').addEventListener('click',()=>{state.mode='';state.animation='';state.sort='new';$('gallerySort').value='new';state.items=[];state.offset=0;load();});
  $('gallerySort').addEventListener('change',()=>{state.sort=$('gallerySort').value;state.items=[];state.offset=0;load();});
  $('galleryMore').addEventListener('click',load);
  $('publishOpen').addEventListener('click',()=>openPublish());$('publishClose').addEventListener('click',()=>closeOverlay('publishOverlay'));
  $('publishForm').addEventListener('submit',submitPublish);
  $('publishPreview').addEventListener('change',updatePreview);
  document.querySelectorAll('input[name="accessMode"]').forEach((input)=>input.addEventListener('change',updateAccess));
  $('detailClose').addEventListener('click',()=>closeOverlay('workOverlay'));
  $('detailPreview').addEventListener('pointermove',(event)=>{
    if (reduced.matches || event.pointerType==='touch') return;
    const box=event.currentTarget.getBoundingClientRect();
    const x=((event.clientX-box.left)/box.width-.5)*8;
    const y=((event.clientY-box.top)/box.height-.5)*8;
    event.currentTarget.firstElementChild?.style.setProperty('transform',`translate(${x.toFixed(1)}px,${y.toFixed(1)}px) scale(1.012)`);
  });
  $('detailPreview').addEventListener('pointerleave',(event)=>event.currentTarget.firstElementChild?.style.removeProperty('transform'));
  $('detailLike').addEventListener('click',async()=>{
    if(!state.detail)return;
    const r=await fetch('/api/gallery/'+state.detail.id+'/like',{method:'POST',credentials:'same-origin'});const d=await r.json();
    if(!r.ok){$('detailFeedback').textContent=t('signIn');return;}
    state.detail.likes=d.likes;state.detail.liked=d.liked;
    const cardItem=state.items.find((item)=>item.id===state.detail.id);if(cardItem){cardItem.likes=d.likes;cardItem.liked=d.liked;}
    renderDetail(state.detail);renderGrid();
  });
  $('detailDownload').addEventListener('click',(event)=>{if(!state.loggedIn){event.preventDefault();closeOverlay('workOverlay');window.SSShell?.openAuth?.('login');}});
  $('detailShare').addEventListener('click',async()=>{if(!state.detail)return;await navigator.clipboard.writeText(location.origin+'/gallery?work='+state.detail.id);$('detailFeedback').textContent=t('shareCopied');});
  $('detailEdit').addEventListener('click',()=>{const item=state.detail;closeOverlay('workOverlay');openPublish(item);});
  $('detailDelete').addEventListener('click',async()=>{if(!state.detail||!confirm(t('confirmDelete')))return;const r=await fetch('/api/gallery/works/'+state.detail.id,{method:'DELETE',credentials:'same-origin'});if(r.ok){closeOverlay('workOverlay');state.items=[];state.offset=0;load();}});
  $('adultCancel').addEventListener('click',()=>closeOverlay('adultOverlay'));
  $('adultConfirm').addEventListener('click',()=>{sessionStorage.setItem('sm_gallery_adult_ok','1');closeOverlay('adultOverlay');renderGrid();if(adultPending)openWork(adultPending);adultPending=null;});
  ['workOverlay','publishOverlay','adultOverlay'].forEach((id)=>$(id).addEventListener('click',(event)=>{if(event.target===$(id))closeOverlay(id);}));
  document.addEventListener('keydown',(event)=>{
    const active=['adultOverlay','publishOverlay','workOverlay'].map((id)=>$(id)).find((overlay)=>!overlay.hidden);
    if(!active)return;
    if(event.key==='Escape'){closeOverlay(active.id);return;}
    if(event.key!=='Tab')return;
    const focusable=[...active.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled])')]
      .filter((node)=>!node.closest('[hidden]')&&node.getClientRects().length);
    if(!focusable.length)return;
    const first=focusable[0],last=focusable[focusable.length-1];
    if(event.shiftKey&&(document.activeElement===first||!active.contains(document.activeElement))){event.preventDefault();last.focus();}
    else if(!event.shiftKey&&(document.activeElement===last||!active.contains(document.activeElement))){event.preventDefault();first.focus();}
  });
  window.addEventListener('sm:langchange',localize);
  localize();load().then(()=>{const id=Number(query.get('work'));if(id)openWork(id);if(query.get('publish')==='1')openPublish();});
})();
