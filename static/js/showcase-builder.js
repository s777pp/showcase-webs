(function () {
  'use strict';

  var root = document.getElementById('showcaseBuilder');
  if (!root) return;
  var canvas = document.getElementById('builderCanvas');
  canvas.tabIndex = 0;
  var ctx = canvas.getContext('2d', { alpha: false });
  var media = new Map();
  var selected = null;
  var uploadType = 'character';
  var catalogPage = 0;
  var currentProjectId = '';
  var dragging = null;
  var editorHistory = null;
  var previewBackdrop = 'project';
  var snapEnabled = true;
  var exportingCanvas = false;
  var chromaCache = new Map();
  var particles = Array.from({ length: 74 }, function (_, i) {
    return { x: (i * 79 % 101) / 100, y: (i * 47 % 97) / 96, r: 1 + (i % 4), speed: .025 + (i % 8) * .006 };
  });
  var project = freshProject('workshop');

  var COPY = {
    en: {
      'add-layer':'Add layer',background:'Background',character:'Character',text:'Text',frame:'Frame',effect:'Effect',upload:'Upload media','upload-effect':'Upload overlay','steam-backgrounds':'Steam backgrounds','source-hint':'Choose Background or Character above to upload media. PNG, JPG, GIF, WebM and MP4 are supported.',more:'More',settings:'Layer settings','layer-name':'Name',content:'Content',font:'Font','font-preview':'Font preview',color:'Color','font-size':'Font size','effect-type':'Effect type','effect-color':'Effect color','frame-color':'Frame color',thickness:'Thickness',chroma:'Remove chromakey','chroma-tolerance':'Tolerance','chroma-feather':'Edge feather','ai-remove':'Remove background with AI',animation:'Animation',none:'None',breathing:'Breathing',wave:'Wave',scale:'Scale',rotation:'Rotation',opacity:'Opacity','stage-help':'Select a layer, then drag it directly on the showcase. Guides show the exact Steam cut.',save:'Save project','to-process':'Send to Process',layers:'Layers','empty-layers':'Add a background, character, text, frame or effect.',storage:'Project storage','storage-hint':'Free: 7 days · Pro: until you delete it','my-projects':'My projects','projects-hint':'Continue editing saved showcases. Free projects are deleted after 7 days; Pro projects remain until you delete them.','new-project':'New project',edit:'Edit',remove:'Delete',saved:'Project saved',login:'Log in to save source files and projects.',uploading:'Uploading source…','ai-working':'AI is removing the background…',exporting:'Preparing the animated showcase…','sent':'The showcase was sent to Process.','empty-projects':'No saved projects yet.',expires:'Stored until',permanent:'Stored until you delete it',failed:'Could not complete the action'
    },
    ru: {
      'add-layer':'Добавить слой',background:'Фон',character:'Персонаж',text:'Текст',frame:'Рамка',effect:'Эффект',upload:'Загрузить медиа','upload-effect':'Загрузить оверлей','steam-backgrounds':'Фоны из Steam','source-hint':'Для загрузки нажми «Фон» или «Персонаж» выше. Поддерживаются PNG, JPG, GIF, WebM и MP4.',more:'Ещё',settings:'Настройки слоя','layer-name':'Название',content:'Текст',font:'Шрифт','font-preview':'Предпросмотр шрифта',color:'Цвет','font-size':'Размер шрифта','effect-type':'Тип эффекта','effect-color':'Цвет эффекта','frame-color':'Цвет рамки',thickness:'Толщина',chroma:'Удалить хромакей','chroma-tolerance':'Допуск','chroma-feather':'Растушёвка края','ai-remove':'Удалить фон через ИИ',animation:'Анимация',none:'Нет',breathing:'Дыхание',wave:'Волна',scale:'Масштаб',rotation:'Поворот',opacity:'Прозрачность','stage-help':'Выбери слой и перемещай его прямо на витрине. Направляющие показывают точную нарезку Steam.',save:'Сохранить проект','to-process':'В обработку',layers:'Слои','empty-layers':'Добавь фон, персонажа, текст, рамку или эффект.',storage:'Хранение проекта','storage-hint':'Free: 7 дней · Pro: пока не удалишь','my-projects':'Мои проекты','projects-hint':'Продолжай редактировать сохранённые витрины. Free-проекты удаляются через 7 дней, Pro-проекты — только вручную.','new-project':'Новый проект',edit:'Редактировать',remove:'Удалить',saved:'Проект сохранён',login:'Войди, чтобы сохранять исходники и проекты.',uploading:'Загружаем исходник…','ai-working':'ИИ удаляет фон…',exporting:'Готовим анимированную витрину…','sent':'Витрина передана в «Обработку».','empty-projects':'Сохранённых проектов пока нет.',expires:'Хранится до',permanent:'Хранится, пока ты не удалишь',failed:'Не удалось выполнить действие'
    }
  };
  var NEW_COPY = {
    en:{templates:'Quick templates','templates-hint':'Adds a coordinated title, frame and effect without replacing your media.','template-neon':'Neon title','template-neon-hint':'Cyan frame and particles','template-minimal':'Clean label','template-minimal-hint':'Quiet bottom signature','template-cinematic':'Cinematic','template-cinematic-hint':'Wide title and light streaks',snap:'Smart guides',backdrop:'Edge check','backdrop-project':'Project preview','backdrop-dark':'Dark background','backdrop-light':'Light background','backdrop-checker':'Transparency grid',shortcuts:'Arrow keys: move · Shift: 10 px · Ctrl/Cmd+D: duplicate',duplicate:'Duplicate',lock:'Lock',unlock:'Unlock','show-hide':'Show or hide',up:'Move up',down:'Move down','layer-locked':'Layer is locked','template-added':'Template added'},
    ru:{templates:'Быстрые шаблоны','templates-hint':'Добавляет согласованные текст, рамку и эффект, не заменяя твои медиа.','template-neon':'Неоновый заголовок','template-neon-hint':'Голубая рамка и частицы','template-minimal':'Чистая подпись','template-minimal-hint':'Спокойная подпись снизу','template-cinematic':'Кинематографичный','template-cinematic-hint':'Широкий заголовок и световые линии',snap:'Умные направляющие',backdrop:'Проверка края','backdrop-project':'Предпросмотр проекта','backdrop-dark':'Тёмный фон','backdrop-light':'Светлый фон','backdrop-checker':'Сетка прозрачности',shortcuts:'Стрелки: перемещение · Shift: 10 px · Ctrl/Cmd+D: дубликат',duplicate:'Дублировать',lock:'Заблокировать',unlock:'Разблокировать','show-hide':'Показать или скрыть',up:'Поднять выше',down:'Опустить ниже','layer-locked':'Слой заблокирован','template-added':'Шаблон добавлен'},
    de:{templates:'Schnellvorlagen','templates-hint':'Fügt abgestimmten Titel, Rahmen und Effekt hinzu, ohne Medien zu ersetzen.','template-neon':'Neon-Titel','template-neon-hint':'Cyan-Rahmen und Partikel','template-minimal':'Klare Signatur','template-minimal-hint':'Ruhige Signatur unten','template-cinematic':'Filmisch','template-cinematic-hint':'Breiter Titel und Lichtstreifen',snap:'Intelligente Hilfslinien',backdrop:'Kantenprüfung','backdrop-project':'Projektvorschau','backdrop-dark':'Dunkler Hintergrund','backdrop-light':'Heller Hintergrund','backdrop-checker':'Transparenzraster',shortcuts:'Pfeiltasten: bewegen · Umschalt: 10 px · Strg/Cmd+D: duplizieren',duplicate:'Duplizieren',lock:'Sperren',unlock:'Entsperren','show-hide':'Ein- oder ausblenden',up:'Nach oben',down:'Nach unten','layer-locked':'Ebene ist gesperrt','template-added':'Vorlage hinzugefügt'},
    tr:{templates:'Hızlı şablonlar','templates-hint':'Medyanızı değiştirmeden uyumlu başlık, çerçeve ve efekt ekler.','template-neon':'Neon başlık','template-neon-hint':'Camgöbeği çerçeve ve parçacıklar','template-minimal':'Sade imza','template-minimal-hint':'Altta sakin bir imza','template-cinematic':'Sinematik','template-cinematic-hint':'Geniş başlık ve ışık çizgileri',snap:'Akıllı kılavuzlar',backdrop:'Kenar denetimi','backdrop-project':'Proje önizlemesi','backdrop-dark':'Koyu arka plan','backdrop-light':'Açık arka plan','backdrop-checker':'Saydamlık ızgarası',shortcuts:'Ok tuşları: taşı · Shift: 10 px · Ctrl/Cmd+D: çoğalt',duplicate:'Çoğalt',lock:'Kilitle',unlock:'Kilidi aç','show-hide':'Göster veya gizle',up:'Yukarı taşı',down:'Aşağı taşı','layer-locked':'Katman kilitli','template-added':'Şablon eklendi'},
    fr:{templates:'Modèles rapides','templates-hint':'Ajoute un titre, un cadre et un effet coordonnés sans remplacer vos médias.','template-neon':'Titre néon','template-neon-hint':'Cadre cyan et particules','template-minimal':'Signature épurée','template-minimal-hint':'Signature discrète en bas','template-cinematic':'Cinématique','template-cinematic-hint':'Titre large et traînées lumineuses',snap:'Repères intelligents',backdrop:'Contrôle des bords','backdrop-project':'Aperçu du projet','backdrop-dark':'Fond sombre','backdrop-light':'Fond clair','backdrop-checker':'Grille de transparence',shortcuts:'Flèches : déplacer · Maj : 10 px · Ctrl/Cmd+D : dupliquer',duplicate:'Dupliquer',lock:'Verrouiller',unlock:'Déverrouiller','show-hide':'Afficher ou masquer',up:'Monter',down:'Descendre','layer-locked':'Le calque est verrouillé','template-added':'Modèle ajouté'},
    uk:{templates:'Швидкі шаблони','templates-hint':'Додає узгоджені текст, рамку й ефект, не замінюючи медіа.','template-neon':'Неоновий заголовок','template-neon-hint':'Блакитна рамка й частинки','template-minimal':'Чистий підпис','template-minimal-hint':'Стриманий підпис унизу','template-cinematic':'Кінематографічний','template-cinematic-hint':'Широкий заголовок і світлові смуги',snap:'Розумні напрямні',backdrop:'Перевірка краю','backdrop-project':'Перегляд проєкту','backdrop-dark':'Темне тло','backdrop-light':'Світле тло','backdrop-checker':'Сітка прозорості',shortcuts:'Стрілки: переміщення · Shift: 10 px · Ctrl/Cmd+D: дублювати',duplicate:'Дублювати',lock:'Заблокувати',unlock:'Розблокувати','show-hide':'Показати або приховати',up:'Підняти вище',down:'Опустити нижче','layer-locked':'Шар заблоковано','template-added':'Шаблон додано'},
    es:{templates:'Plantillas rápidas','templates-hint':'Añade título, marco y efecto coordinados sin reemplazar tus medios.','template-neon':'Título neón','template-neon-hint':'Marco cian y partículas','template-minimal':'Firma limpia','template-minimal-hint':'Firma discreta en la parte inferior','template-cinematic':'Cinemática','template-cinematic-hint':'Título ancho y trazos de luz',snap:'Guías inteligentes',backdrop:'Comprobar bordes','backdrop-project':'Vista del proyecto','backdrop-dark':'Fondo oscuro','backdrop-light':'Fondo claro','backdrop-checker':'Cuadrícula de transparencia',shortcuts:'Flechas: mover · Mayús: 10 px · Ctrl/Cmd+D: duplicar',duplicate:'Duplicar',lock:'Bloquear',unlock:'Desbloquear','show-hide':'Mostrar u ocultar',up:'Subir',down:'Bajar','layer-locked':'La capa está bloqueada','template-added':'Plantilla añadida'},
    pt:{templates:'Modelos rápidos','templates-hint':'Adiciona título, moldura e efeito coordenados sem substituir sua mídia.','template-neon':'Título neon','template-neon-hint':'Moldura ciano e partículas','template-minimal':'Assinatura limpa','template-minimal-hint':'Assinatura discreta embaixo','template-cinematic':'Cinemático','template-cinematic-hint':'Título amplo e rastros de luz',snap:'Guias inteligentes',backdrop:'Verificar bordas','backdrop-project':'Prévia do projeto','backdrop-dark':'Fundo escuro','backdrop-light':'Fundo claro','backdrop-checker':'Grade de transparência',shortcuts:'Setas: mover · Shift: 10 px · Ctrl/Cmd+D: duplicar',duplicate:'Duplicar',lock:'Bloquear',unlock:'Desbloquear','show-hide':'Mostrar ou ocultar',up:'Mover para cima',down:'Mover para baixo','layer-locked':'A camada está bloqueada','template-added':'Modelo adicionado'}
  };
  if (window.SMLang && SMLang.extend) SMLang.extend(COPY);
  Object.keys(NEW_COPY).forEach(function(language){COPY[language]=Object.assign({},COPY[language]||{},NEW_COPY[language])});

  function lang() { return window.SMLang && SMLang.get ? SMLang.get() : (document.documentElement.lang === 'ru' ? 'ru' : 'en'); }
  function t(key) { return (COPY[lang()] || COPY.en)[key] || COPY.en[key] || key; }
  function el(id) { return document.getElementById(id); }
  function uid() { return 'ly_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }
  function freshProject(mode) { return { version:1, mode:mode || 'workshop', width:mode === 'featured' ? 630 : (mode === 'split' ? 606 : 750), height:1000, background:'#061019', layers:[] }; }
  function status(message, kind) { var n=el('builderStatus'); n.textContent=message || ''; n.className='status ' + (kind || ''); }
  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function currentLayer() { return project.layers.find(function (x) { return x.id === selected; }) || null; }
  function safeFontName(value){return String(value||'Mulish').replace(/["\\]/g,'')}
  function syncFontPreview(layer){var name=safeFontName(layer&&layer.font),preview=el('builderFontPreview'),select=el('builderFont');if(!preview||!select)return;var sample=String(layer&&layer.text||'').split('\n')[0].trim()||(lang()==='ru'?'ТВОЯ ВИТРИНА':'YOUR SHOWCASE');preview.textContent=sample;preview.style.fontFamily='"'+name+'"';select.style.fontFamily='"'+name+'"'}
  function defaultLayer(type) {
    var common={id:uid(),type:type,name:t(type),x:.5,y:.5,scale:1,rotation:0,opacity:1,visible:true,animation:'none'};
    if(type==='background')Object.assign(common,{x:.5,y:.5,scale:1,chroma:false,chromaTolerance:45,chromaFeather:16});
    if(type==='character')Object.assign(common,{chroma:false,chromaTolerance:45,chromaFeather:16});
    if(type==='text')Object.assign(common,{text:lang()==='ru'?'ТВОЯ ВИТРИНА':'YOUR SHOWCASE',font:'Mulish',fontSize:64,color:'#ffffff',y:.18});
    if(type==='frame')Object.assign(common,{color:'#52d5ff',frameWidth:4});
    if(type==='effect')Object.assign(common,{effect:'particle',name:'Particle Flow',color:'#52d5ff'});
    return common;
  }

  function safeSource(url) {
    if (/^https:\/\/(shared|cdn)\.cloudflare\.steamstatic\.com\//i.test(url)) return '/api/steam/proxy-image?url=' + encodeURIComponent(url);
    return url;
  }
  function mediaFor(layer) {
    if (!layer || !layer.src) return null;
    var key=layer.id+'|'+layer.src;
    if(media.has(key))return media.get(key);
    var isVideo=layer.mediaType&&layer.mediaType.indexOf('video/')===0 || /\.(mp4|webm|mov)(\?|$)/i.test(layer.src);
    var node=document.createElement(isVideo?'video':'img');
    if(isVideo){node.muted=true;node.loop=true;node.playsInline=true;node.autoplay=true}
    node.crossOrigin='anonymous';node.src=safeSource(layer.src);
    if(isVideo)node.play().catch(function(){});
    media.set(key,node);return node;
  }
  function coverBox(node) {
    var nw=node.videoWidth||node.naturalWidth||1,nh=node.videoHeight||node.naturalHeight||1;
    var s=Math.max(canvas.width/nw,canvas.height/nh);return {w:nw*s,h:nh*s};
  }
  function containBox(node, layer) {
    var nw=node.videoWidth||node.naturalWidth||1,nh=node.videoHeight||node.naturalHeight||1;
    var base=Math.min(canvas.width/nw,canvas.height/nh);return {w:nw*base*layer.scale,h:nh*base*layer.scale};
  }
  function animationTransform(layer, now) {
    if(layer.animation==='breathing')return {scale:1+Math.sin(now*.0023)*.018,rotate:0,y:Math.sin(now*.0023)*2};
    if(layer.animation==='wave')return {scale:1,rotate:Math.sin(now*.002)*.035,y:Math.sin(now*.003)*3};
    return {scale:1,rotate:0,y:0};
  }
  function clamp(value,min,max){return Math.max(min,Math.min(max,Number(value)||0))}
  function applyChroma(image,w,h,layer){
    var d=image.data,spots=[[0,0],[w-1,0],[0,h-1],[w-1,h-1],[Math.floor(w/2),0],[Math.floor(w/2),h-1],[0,Math.floor(h/2)],[w-1,Math.floor(h/2)]],samples=[];
    spots.forEach(function(point){var p=(point[1]*w+point[0])*4;if(d[p+3]>16)samples.push([d[p],d[p+1],d[p+2]])});
    if(!samples.length)return;
    var key=samples[0],best=Infinity;
    samples.forEach(function(candidate){var score=samples.reduce(function(sum,other){var dr=candidate[0]-other[0],dg=candidate[1]-other[1],db=candidate[2]-other[2];return sum+dr*dr+dg*dg+db*db},0);if(score<best){best=score;key=candidate}});
    var rawTolerance=clamp(layer.chromaTolerance==null?45:layer.chromaTolerance,10,120),progress=(rawTolerance-10)/110;
    var tolerance=18+Math.pow(progress,1.45)*247,feather=clamp(layer.chromaFeather==null?16:layer.chromaFeather,0,40)*1.25;
    var keyMax=Math.max(key[0],key[1],key[2],1),keyNormal=[key[0]/keyMax,key[1]/keyMax,key[2]/keyMax],keyChannel=keyNormal.indexOf(Math.max.apply(Math,keyNormal));
    var inner=Math.max(0,tolerance-feather),outer=tolerance+feather;
    for(var p=0;p<d.length;p+=4){var pixelMax=Math.max(d[p],d[p+1],d[p+2],1),dr=d[p]/pixelMax-keyNormal[0],dg=d[p+1]/pixelMax-keyNormal[1],db=d[p+2]/pixelMax-keyNormal[2],distance=Math.sqrt(dr*dr+dg*dg+db*db)*255,keep;
      if(feather===0)keep=distance>tolerance?1:0;
      else if(distance<=inner)keep=0;
      else if(distance>=outer)keep=1;
      else{var n=(distance-inner)/(outer-inner);keep=n*n*(3-2*n)}
      var otherA=d[p+(keyChannel+1)%3],otherB=d[p+(keyChannel+2)%3],neutral=Math.max(otherA,otherB),dominance=d[p+keyChannel]-neutral;
      var dominanceStart=32-progress*30,dominanceWidth=18-progress*8;
      if(dominance>dominanceStart)keep=Math.min(keep,1-clamp((dominance-dominanceStart)/dominanceWidth,0,1));
      var spill=Math.max(1-keep,Math.max(0,1-distance/(outer+70))*.9);
      if(d[p+keyChannel]>neutral)d[p+keyChannel]=Math.round(d[p+keyChannel]+(neutral-d[p+keyChannel])*spill);
      d[p+3]=Math.round(d[p+3]*keep);
    }
    var cleanup=rawTolerance>=105?2:(rawTolerance>=75?1:0);
    if(cleanup){var alpha=new Uint8ClampedArray(w*h);for(var y=0;y<h;y++){for(var x=0;x<w;x++){var at=y*w+x,minAlpha=d[at*4+3];for(var radius=1;radius<=cleanup;radius++){if(x>=radius)minAlpha=Math.min(minAlpha,d[(at-radius)*4+3]);if(x+radius<w)minAlpha=Math.min(minAlpha,d[(at+radius)*4+3]);if(y>=radius)minAlpha=Math.min(minAlpha,d[(at-radius*w)*4+3]);if(y+radius<h)minAlpha=Math.min(minAlpha,d[(at+radius*w)*4+3])}alpha[at]=minAlpha}}for(var i=0;i<alpha.length;i++)d[i*4+3]=Math.min(d[i*4+3],alpha[i])}
  }
  function drawMediaLayer(layer, node, now) {
    if(!node || !(node.complete || node.readyState>=2))return;
    var box=layer.type==='background'?coverBox(node):containBox(node,layer),a=animationTransform(layer,now);
    var x=layer.x*canvas.width,y=layer.y*canvas.height+a.y;
    ctx.save();ctx.globalAlpha=Math.max(0,Math.min(1,layer.opacity));ctx.translate(x,y);ctx.rotate(layer.rotation*Math.PI/180+a.rotate);ctx.scale(a.scale,a.scale);
    if(layer.chroma){
      var w=Math.max(1,Math.round(box.w)),h=Math.max(1,Math.round(box.h));
      var cacheKey=[layer.id,layer.src,w,h,layer.chromaTolerance,layer.chromaFeather].join('|'),entry=chromaCache.get(cacheKey),isMoving=node.tagName==='VIDEO';
      if(!entry){var made=document.createElement('canvas');made.width=w;made.height=h;entry={canvas:made,updated:0};chromaCache.set(cacheKey,entry)}
      var off=entry.canvas,oc=off.getContext('2d');
      if(!entry.updated||!isMoving||now-entry.updated>70){oc.clearRect(0,0,w,h);oc.drawImage(node,0,0,w,h);try{var im=oc.getImageData(0,0,w,h);applyChroma(im,w,h,layer);oc.putImageData(im,0,0)}catch(_){ }entry.updated=now;if(chromaCache.size>24){var first=chromaCache.keys().next().value;chromaCache.delete(first)}}
      ctx.drawImage(off,-box.w/2,-box.h/2,box.w,box.h);
    }else ctx.drawImage(node,-box.w/2,-box.h/2,box.w,box.h);
    ctx.restore();
  }
  function drawEffect(layer, now) {
    if(layer.src){drawMediaLayer(layer,mediaFor(layer),now);return}
    var sec=now/1000,color=layer.color||'#52d5ff',a=animationTransform(layer,now),x=(layer.x==null ? .5 : layer.x)*canvas.width,y=(layer.y==null ? .5 : layer.y)*canvas.height+a.y;
    ctx.save();ctx.globalAlpha=layer.opacity;ctx.translate(x,y);ctx.rotate(layer.rotation*Math.PI/180+a.rotate);ctx.scale((layer.scale||1)*a.scale,(layer.scale||1)*a.scale);ctx.translate(-canvas.width/2,-canvas.height/2);
    ctx.shadowColor=color;ctx.shadowBlur=layer.effect==='snow'?0:6;
    if(layer.effect==='matrix'){ctx.fillStyle=color;ctx.font='15px monospace';particles.slice(0,36).forEach(function(p,i){ctx.fillText(String.fromCharCode(0x30A0+(i*17)%90),p.x*canvas.width,((p.y+sec*p.speed*2)%1)*canvas.height)});}
    else if(layer.effect==='streaks'){ctx.strokeStyle=color;ctx.lineWidth=2;particles.slice(0,24).forEach(function(p){var x=((p.x+sec*p.speed)%1)*canvas.width,y=p.y*canvas.height;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+70,y-45);ctx.stroke()});}
    else {ctx.fillStyle=color;particles.forEach(function(p){var y=((p.y+sec*p.speed*(layer.effect==='snow'?1:.45))%1)*canvas.height,x=(p.x+Math.sin(sec+p.y*9)*.02)*canvas.width;ctx.beginPath();ctx.arc(x,y,layer.effect==='snow'?p.r*1.4:p.r,0,Math.PI*2);ctx.fill()});}
    ctx.restore();
  }
  function drawDNA(layer, now) {
    var keys=['focus','variety','mastery','history','activity','collector'],signals=layer.signals||{},palette=Array.isArray(layer.palette)&&layer.palette.length?layer.palette:['#52d5ff','#8a62ff','#ff5fc7'];
    var seed=parseInt(String(layer.seed||'52d5ff').slice(0,8),16)||5436927,sec=now/1000,base=Math.min(canvas.width,canvas.height)*.275;
    var x=(layer.x==null?.5:layer.x)*canvas.width,y=(layer.y==null?.5:layer.y)*canvas.height;
    ctx.save();ctx.globalAlpha=clamp(layer.opacity==null?1:layer.opacity,0,1);ctx.globalCompositeOperation='screen';ctx.translate(x,y);ctx.rotate((layer.rotation||0)*Math.PI/180);ctx.scale(layer.scale||1,layer.scale||1);
    var glow=ctx.createRadialGradient(0,0,0,0,0,base*.82);glow.addColorStop(0,palette[0]+'cc');glow.addColorStop(.27,palette[1]+'55');glow.addColorStop(1,'#00000000');ctx.fillStyle=glow;ctx.beginPath();ctx.arc(0,0,base*.82,0,Math.PI*2);ctx.fill();
    keys.forEach(function(key,index){
      var value=clamp(signals[key]==null?.25:signals[key],0,1),radius=base*(.58+index*.135),color=palette[index%palette.length],direction=index%2?-1:1,speed=.055+value*.17+index*.012,angle=sec*speed*direction+(seed%(97+index*13))*.031;
      ctx.save();ctx.rotate(angle);ctx.strokeStyle=color;ctx.lineWidth=Math.max(2,base*(.010+value*.008));ctx.lineCap='round';ctx.shadowColor=color;ctx.shadowBlur=7+value*13;ctx.globalAlpha=.4+value*.58;ctx.beginPath();ctx.arc(0,0,radius,-Math.PI*.77,-Math.PI*.77+Math.PI*2*(.18+value*.68));ctx.stroke();
      var end=-Math.PI*.77+Math.PI*2*(.18+value*.68);ctx.fillStyle=color;ctx.beginPath();ctx.arc(Math.cos(end)*radius,Math.sin(end)*radius,ctx.lineWidth*1.45,0,Math.PI*2);ctx.fill();ctx.restore();
    });
    ctx.strokeStyle=palette[0];ctx.lineWidth=2;ctx.globalAlpha=.72;ctx.beginPath();ctx.arc(0,0,base*.47,0,Math.PI*2);ctx.stroke();
    for(var i=0;i<18;i++){var turn=((seed>>(i%16))&15)/15,angle=i*2.399+sec*(.02+turn*.03),radius=base*(.72+turn*1.02);ctx.fillStyle=palette[i%palette.length];ctx.globalAlpha=.25+turn*.45;ctx.beginPath();ctx.arc(Math.cos(angle)*radius,Math.sin(angle)*radius,1.2+turn*2.1,0,Math.PI*2);ctx.fill()}
    ctx.restore();
  }
  function drawFrame(layer) {ctx.save();ctx.globalAlpha=layer.opacity;ctx.strokeStyle=layer.color||'#52d5ff';ctx.lineWidth=layer.frameWidth||4;var n=ctx.lineWidth/2;ctx.strokeRect(n,n,canvas.width-ctx.lineWidth,canvas.height-ctx.lineWidth);ctx.restore()}
  function drawText(layer, now) {var a=animationTransform(layer,now),font=safeFontName(layer.font);ctx.save();ctx.globalAlpha=layer.opacity;ctx.translate(layer.x*canvas.width,layer.y*canvas.height+a.y);ctx.rotate(layer.rotation*Math.PI/180+a.rotate);ctx.scale(layer.scale*a.scale,layer.scale*a.scale);ctx.fillStyle=layer.color||'#fff';ctx.textAlign='center';ctx.textBaseline='middle';ctx.font='800 '+(layer.fontSize||64)+'px "'+font+'"';String(layer.text||'').split('\n').forEach(function(line,i,arr){ctx.fillText(line,0,(i-(arr.length-1)/2)*(layer.fontSize||64)*1.12,canvas.width*.9)});ctx.restore()}
  function drawBackdrop() {
    var mode=exportingCanvas?'project':previewBackdrop;
    if(mode==='project'){ctx.fillStyle=project.background||'#061019';ctx.fillRect(0,0,canvas.width,canvas.height);return false}
    if(mode==='checker'){
      var block=28;ctx.fillStyle='#e7edf0';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.fillStyle='#93a3aa';
      for(var y=0;y<canvas.height;y+=block)for(var x=0;x<canvas.width;x+=block)if(((x/block+y/block)&1)===0)ctx.fillRect(x,y,block,block);
    }else{ctx.fillStyle=mode==='light'?'#f4f7f8':'#030608';ctx.fillRect(0,0,canvas.width,canvas.height)}
    return true;
  }
  function renderCanvas(now) {
    var diagnostic=drawBackdrop();
    project.layers.forEach(function(layer){if(layer.visible===false||(diagnostic&&layer.type==='background'))return;if(layer.type==='text')drawText(layer,now);else if(layer.type==='frame')drawFrame(layer);else if(layer.type==='effect')drawEffect(layer,now);else if(layer.type==='dna')drawDNA(layer,now);else drawMediaLayer(layer,mediaFor(layer),now)});
  }
  function draw(now) {
    if(root.closest('.tab')?.classList.contains('active')||exportingCanvas)renderCanvas(now);
    requestAnimationFrame(draw);
  }

  function updateGuides() {
    var host=el('builderGuides');host.dataset.mode=project.mode;host.innerHTML='';
    var cuts=project.mode==='workshop'?[.2,.4,.6,.8]:(project.mode==='split'?[506/606]:[]);
    var rect=canvas.getBoundingClientRect(),wrap=canvas.parentElement.getBoundingClientRect();
    cuts.forEach(function(c){var i=document.createElement('i');i.style.left=(rect.left-wrap.left+rect.width*c)+'px';i.style.top=(rect.top-wrap.top)+'px';i.style.height=rect.height+'px';host.appendChild(i)});
  }
  function resizeMode(mode) {project.mode=mode;project.width=mode==='featured'?630:(mode==='split'?606:750);canvas.width=project.width;canvas.height=project.height||1000;document.querySelectorAll('[data-builder-mode]').forEach(function(b){b.classList.toggle('active',b.dataset.builderMode===mode)});requestAnimationFrame(updateGuides)}

  function icon(type){return {background:'▧',character:'♙',text:'T',frame:'□',effect:'✦',dna:'◎'}[type]||'·'}
  function renderLayers(){
    var host=el('builderLayerList');host.innerHTML='';
    project.layers.slice().reverse().forEach(function(layer){
      var row=document.createElement('div');row.className='builder-layer'+(layer.id===selected?' is-selected':'')+(layer.locked?' is-locked':'');
      row.innerHTML='<span class="builder-layer__icon">'+icon(layer.type)+'</span><span class="builder-layer__copy"><b></b><span></span></span><span class="builder-layer__actions"><button data-action="visible">'+(layer.visible===false?'○':'●')+'</button><button data-action="lock">'+(layer.locked?'◆':'◇')+'</button><button data-action="duplicate">⧉</button><button data-action="up">↑</button><button data-action="down">↓</button><button data-action="delete">×</button></span>';
      row.querySelector('.builder-layer__copy b').textContent=layer.name;row.querySelector('.builder-layer__copy span').textContent=layer.type==='dna'?'Steam DNA':t(layer.type);
      var titles={visible:t('show-hide'),lock:layer.locked?t('unlock'):t('lock'),duplicate:t('duplicate'),up:t('up'),down:t('down'),delete:t('remove')};
      row.querySelectorAll('button').forEach(function(btn){btn.title=titles[btn.dataset.action]||'';btn.setAttribute('aria-label',titles[btn.dataset.action]||'');btn.onclick=function(e){e.stopPropagation();layerAction(layer,btn.dataset.action)}});
      row.onclick=function(){selected=layer.id;renderLayers();syncInspector()};host.appendChild(row);
    });
    el('builderEmptyLayers').hidden=project.layers.length>0;syncInspector();
  }
  function duplicateLayer(layer){var copy=clone(layer);copy.id=uid();copy.name=(layer.name||t(layer.type))+' · '+t('duplicate');copy.x=clamp((copy.x==null ? .5 : copy.x)+.025,0,1);copy.y=clamp((copy.y==null ? .5 : copy.y)+.025,0,1);copy.locked=false;var i=project.layers.indexOf(layer);project.layers.splice(i+1,0,copy);selected=copy.id;return copy}
  function layerAction(layer,action){
    var i=project.layers.indexOf(layer);
    if(action==='lock'){layer.locked=!layer.locked}
    else if(action==='visible')layer.visible=layer.visible===false;
    else if(action==='duplicate')duplicateLayer(layer);
    else if(layer.locked){status(t('layer-locked'),'bad');return}
    else if(action==='delete'){project.layers.splice(i,1);if(selected===layer.id)selected=''}
    else if(action==='up'&&i<project.layers.length-1){project.layers.splice(i,1);project.layers.splice(i+1,0,layer)}
    else if(action==='down'&&i>0){project.layers.splice(i,1);project.layers.splice(i-1,0,layer)}
    renderLayers();
  }
  function syncInspector(){var layer=currentLayer(),box=el('builderInspector');box.hidden=!layer;if(!layer)return;el('builderLayerName').value=layer.name||'';el('builderScale').value=Math.round((layer.scale||1)*100);el('builderRotation').value=layer.rotation||0;el('builderOpacity').value=Math.round((layer.opacity==null?1:layer.opacity)*100);el('builderTextControls').hidden=layer.type!=='text';el('builderFrameControls').hidden=layer.type!=='frame';el('builderEffectControls').hidden=layer.type!=='effect';el('builderMediaControls').hidden=!['background','character'].includes(layer.type);if(layer.type==='text'){el('builderText').value=layer.text||'';el('builderFont').value=layer.font||'Mulish';el('builderColor').value=layer.color||'#ffffff';el('builderFontSize').value=layer.fontSize||64;syncFontPreview(layer)}if(layer.type==='frame'){el('builderFrameColor').value=layer.color||'#52d5ff';el('builderFrameWidth').value=layer.frameWidth||4}if(layer.type==='effect'){el('builderEffectType').value=layer.effect||'particle';el('builderEffectColor').value=layer.color||'#52d5ff';el('builderEffectColorRow').hidden=layer.effect==='custom'||!!layer.src}if(['background','character'].includes(layer.type)){var tolerance=layer.chromaTolerance==null?45:layer.chromaTolerance,feather=layer.chromaFeather==null?16:layer.chromaFeather;el('builderChroma').checked=!!layer.chroma;el('builderChromaSettings').hidden=!layer.chroma;el('builderChromaTolerance').value=tolerance;el('builderChromaToleranceValue').value=tolerance;el('builderChromaFeather').value=feather;el('builderChromaFeatherValue').value=(feather/10).toFixed(1);el('builderAnimation').value=layer.animation||'none'}box.classList.toggle('is-locked',!!layer.locked);box.querySelectorAll('input,select,textarea,button').forEach(function(control){control.disabled=!!layer.locked});box.title=layer.locked?t('layer-locked'):''}
  function bind(id,event,fn){el(id).addEventListener(event,function(){var layer=currentLayer();if(!layer)return;fn(layer,this);if(id==='builderLayerName')renderLayers()})}
  bind('builderLayerName','input',function(l,n){l.name=n.value});bind('builderScale','input',function(l,n){l.scale=+n.value/100});bind('builderRotation','input',function(l,n){l.rotation=+n.value});bind('builderOpacity','input',function(l,n){l.opacity=+n.value/100});bind('builderText','input',function(l,n){l.text=n.value;syncFontPreview(l)});bind('builderFont','change',function(l,n){l.font=n.value;syncFontPreview(l);if(document.fonts)document.fonts.load('800 64px "'+safeFontName(n.value)+'"')});bind('builderColor','input',function(l,n){l.color=n.value});bind('builderFontSize','input',function(l,n){l.fontSize=+n.value});bind('builderFrameColor','input',function(l,n){l.color=n.value});bind('builderFrameWidth','input',function(l,n){l.frameWidth=+n.value});bind('builderEffectType','change',function(l,n){l.effect=n.value;l.name=n.options[n.selectedIndex].text;renderLayers()});bind('builderEffectColor','input',function(l,n){l.color=n.value});bind('builderChroma','change',function(l,n){l.chroma=n.checked;chromaCache.clear();syncInspector()});bind('builderChromaTolerance','input',function(l,n){l.chromaTolerance=+n.value;chromaCache.clear();el('builderChromaToleranceValue').value=n.value});bind('builderChromaFeather','input',function(l,n){l.chromaFeather=+n.value;chromaCache.clear();el('builderChromaFeatherValue').value=(+n.value/10).toFixed(1)});bind('builderAnimation','change',function(l,n){l.animation=n.value});

  Array.from(el('builderFont').options).forEach(function(option){option.style.fontFamily='"'+safeFontName(option.value)+'"'});

  function waitForRemoval(jobId){return new Promise(function(resolve,reject){function poll(){fetch('/api/builder/remove-background/'+encodeURIComponent(jobId),{credentials:'same-origin'}).then(function(r){return r.json()}).then(function(d){if(!d.ok)throw Error(d.msg||t('failed'));if(d.status==='done'){resolve(d.result);setTimeout(function(){editorHistory?.commit()},0);return}if(d.status==='error'){reject(Error(d.error||t('failed')));return}status(t('ai-working')+' '+(d.pct||0)+'%','wait');setTimeout(poll,900)}).catch(reject)}poll()})}
  el('builderAiRemove').onclick=async function(){var layer=currentLayer();if(!layer||!layer.src)return;this.disabled=true;status(t('ai-working'),'wait');try{var r=await fetch('/api/builder/remove-background',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:layer.src})}),d=await r.json();if(!r.ok||!d.ok){if(r.status===401)el('btnAuth')&&el('btnAuth').click();throw Error(d.msg||t('failed'))}var result=await waitForRemoval(d.job_id);media.delete(layer.id+'|'+layer.src);layer.src=result.url;layer.mediaType=result.media_type;layer.chroma=false;syncInspector();status('', '')}catch(e){status(e.message,'bad')}finally{this.disabled=false}};

  async function upload(file,type){status(t('uploading'),'wait');var layer=defaultLayer(type);layer.name=file.name;layer.src=URL.createObjectURL(file);layer.mediaType=file.type;editorHistory?.remember(layer.src,file);project.layers.push(layer);selected=layer.id;renderLayers();editorHistory?.commit();try{var fd=new FormData();fd.append('file',file);var r=await fetch('/api/builder/assets',{method:'POST',credentials:'same-origin',body:fd}),d=await r.json();if(!r.ok||!d.ok)throw Error(d.msg||t('failed'));media.delete(layer.id+'|'+layer.src);layer.src=d.url;editorHistory?.remember(layer.src,file);layer.mediaType=d.media_type;editorHistory?.commit();status('', '')}catch(e){status(e.message==='Login required'?t('login'):e.message,'bad')}}
  document.querySelectorAll('[data-add-layer]').forEach(function(button){button.onclick=function(){var type=button.dataset.addLayer;if(type==='text'||type==='frame'||type==='effect'){var layer=defaultLayer(type);project.layers.push(layer);selected=layer.id;renderLayers()}else{uploadType=type;el('builderMediaInput').click()}}});
  function applyTemplate(name){
    project.layers=project.layers.filter(function(layer){return !layer.templateGenerated});
    var layers=[];
    if(name==='neon'){
      var glow=defaultLayer('effect'),frame=defaultLayer('frame'),title=defaultLayer('text');glow.effect='particle';glow.opacity=.72;frame.frameWidth=4;title.text='SHOWCASE';title.font='Unbounded';title.fontSize=62;title.y=.14;layers=[glow,frame,title];
    }else if(name==='minimal'){
      var line=defaultLayer('frame'),label=defaultLayer('text');line.color='#dff8ff';line.frameWidth=2;line.opacity=.7;label.text='STEAM / SHOWCASE';label.font='Consolas';label.fontSize=32;label.x=.5;label.y=.91;layers=[line,label];
    }else{
      var streak=defaultLayer('effect'),cinema=defaultLayer('text'),edge=defaultLayer('frame');streak.effect='streaks';streak.color='#5ad9ff';streak.opacity=.48;cinema.text='YOUR SHOWCASE';cinema.font='Oswald';cinema.fontSize=72;cinema.y=.13;edge.frameWidth=3;edge.color='#5ad9ff';edge.opacity=.75;layers=[streak,edge,cinema];
    }
    layers.forEach(function(layer){layer.templateGenerated=true;project.layers.push(layer)});selected=layers[layers.length-1].id;renderLayers();status(t('template-added'),'ok');
  }
  document.querySelectorAll('[data-builder-template]').forEach(function(button){button.onclick=function(){applyTemplate(button.dataset.builderTemplate)}});
  el('builderEffectUpload').onclick=function(){uploadType='effect';el('builderMediaInput').click()};
  el('builderMediaInput').onchange=function(){var file=this.files&&this.files[0];if(file)upload(file,uploadType);this.value=''};
  document.querySelectorAll('[data-builder-mode]').forEach(function(b){b.onclick=function(){resizeMode(b.dataset.builderMode)}});

  el('builderSnap').addEventListener('change',function(){snapEnabled=this.checked;hideSnapGuides()});
  document.querySelectorAll('[data-builder-backdrop]').forEach(function(button){button.onclick=function(){previewBackdrop=button.dataset.builderBackdrop;document.querySelectorAll('[data-builder-backdrop]').forEach(function(item){item.classList.toggle('active',item===button)})}});
  function hideSnapGuides(){var guides=el('builderSnapGuides');guides.classList.remove('show-x','show-y')}
  function snapped(value){var points=[0,.5,1],best=value,distance=.022;points.forEach(function(point){var delta=Math.abs(value-point);if(delta<distance){distance=delta;best=point}});return best}
  function moveLayer(layer,x,y){
    var rawX=clamp(x,0,1),rawY=clamp(y,0,1),nextX=snapEnabled?snapped(rawX):rawX,nextY=snapEnabled?snapped(rawY):rawY,guides=el('builderSnapGuides');
    layer.x=nextX;layer.y=nextY;guides.classList.toggle('show-x',snapEnabled&&nextX!==rawX);guides.classList.toggle('show-y',snapEnabled&&nextY!==rawY);
  }

  canvas.addEventListener('pointerdown',function(e){var layer=currentLayer();canvas.focus({preventScroll:true});if(!layer||layer.locked||layer.type==='frame')return;var r=canvas.getBoundingClientRect();dragging={id:layer.id,dx:(e.clientX-r.left)/r.width-layer.x,dy:(e.clientY-r.top)/r.height-layer.y};canvas.setPointerCapture(e.pointerId)});
  canvas.addEventListener('pointermove',function(e){if(!dragging)return;var layer=currentLayer();if(!layer||layer.id!==dragging.id||layer.locked)return;var r=canvas.getBoundingClientRect();moveLayer(layer,(e.clientX-r.left)/r.width-dragging.dx,(e.clientY-r.top)/r.height-dragging.dy)});
  canvas.addEventListener('pointerup',function(){dragging=null;hideSnapGuides();editorHistory?.commit()});
  canvas.addEventListener('pointercancel',function(){dragging=null;hideSnapGuides();editorHistory?.commit()});
  document.addEventListener('keydown',function(event){
    if(!root.closest('.tab')?.classList.contains('active')||event.target.closest('input,textarea,select,[contenteditable=true]'))return;
    var layer=currentLayer();if(!layer)return;
    if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='d'){event.preventDefault();duplicateLayer(layer);renderLayers();editorHistory?.commit();return}
    if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key))return;
    event.preventDefault();if(layer.locked){status(t('layer-locked'),'bad');return}
    var amount=event.shiftKey?10:1,dx=(event.key==='ArrowLeft'?-amount:event.key==='ArrowRight'?amount:0)/canvas.width,dy=(event.key==='ArrowUp'?-amount:event.key==='ArrowDown'?amount:0)/canvas.height;
    moveLayer(layer,(layer.x==null ? .5 : layer.x)+dx,(layer.y==null ? .5 : layer.y)+dy);hideSnapGuides();editorHistory?.changed();
  });
  window.addEventListener('resize',updateGuides);

  function openCatalog(reset){if(reset){catalogPage=0;el('builderCatalogGrid').innerHTML=''}el('builderCatalog').hidden=false;var q=el('builderCatalogSearch').value.trim();Promise.all([
    fetch('/api/steam/backgrounds?asset=points_background&kind=static&page='+catalogPage+'&count=24&q='+encodeURIComponent(q)).then(function(r){return r.json()}),
    fetch('/api/steam/backgrounds?asset=animated_background&kind=animated&page='+catalogPage+'&count=24&q='+encodeURIComponent(q)).then(function(r){return r.json()})
  ]).then(function(parts){parts.forEach(function(d){(d.items||[]).forEach(addCatalogItem)});catalogPage++}).catch(function(e){status(e.message,'bad')})}
  function addCatalogItem(item){var grid=el('builderCatalogGrid'),key=String(item.appid||'')+':'+String(item.defid||item.image);if(grid.querySelector('[data-key="'+CSS.escape(key)+'"]'))return;var b=document.createElement('button');b.type='button';b.dataset.key=key;var src=item.movie||item.image,poster=item.image||src;b.innerHTML=item.movie?'<video muted loop autoplay playsinline></video>':'<img alt="">';var n=b.firstElementChild;n.src=safeSource(item.movie||poster);if(item.movie)n.poster=safeSource(poster);b.onclick=function(){var layer=defaultLayer('background');layer.name=item.name||t('background');layer.src=src;layer.mediaType=item.movie?'video/webm':'image/jpeg';project.layers=project.layers.filter(function(x){return x.type!=='background'});project.layers.unshift(layer);selected=layer.id;renderLayers();el('builderCatalog').hidden=true};grid.appendChild(b)}
  el('builderSteamBackgrounds').onclick=function(){openCatalog(true)};el('builderCatalogMore').onclick=function(){openCatalog(false)};el('builderCatalogClose').onclick=function(){el('builderCatalog').hidden=true};var searchTimer;el('builderCatalogSearch').oninput=function(){clearTimeout(searchTimer);searchTimer=setTimeout(function(){openCatalog(true)},350)};

  async function saveProject(){var r=await fetch('/api/builder/projects',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:currentProjectId,name:el('builderProjectName').value,project:project})}),d=await r.json();if(!r.ok||!d.ok){if(r.status===401)el('btnAuth')&&el('btnAuth').click();throw Error(d.msg||t('failed'))}currentProjectId=d.item.id;status(t('saved')+(d.retention_days?' · 7 days':''),'ok');loadProjects()}
  el('builderSave').onclick=async function(){this.disabled=true;try{for(var layer of project.layers){if(!layer.src||!layer.src.startsWith('blob:'))continue;var source=await fetch(layer.src),blob=await source.blob(),fd=new FormData(),extension=({'image/png':'png','image/jpeg':'jpg','image/webp':'webp','image/gif':'gif','video/mp4':'mp4','video/webm':'webm','video/quicktime':'mov'})[layer.mediaType||blob.type]||'png';fd.append('file',blob,'restored.'+extension);var response=await fetch('/api/builder/assets',{method:'POST',credentials:'same-origin',body:fd}),data=await response.json();if(!response.ok||!data.ok)throw Error(data.msg||t('failed'));editorHistory?.remember(data.url,blob);layer.src=data.url;layer.mediaType=data.media_type}await saveProject();editorHistory?.commit()}catch(e){status(e.message==='Login required'?t('login'):e.message,'bad')}finally{this.disabled=false}};

  function projectAnimated(){return project.layers.some(function(l){return l.visible!==false&&(l.type==='effect'||l.type==='dna'||l.animation&&l.animation!=='none'||l.mediaType==='image/gif'||l.mediaType&&l.mediaType.indexOf('video/')===0||/\.gif(\?|$)/i.test(l.src||''))})}
  function canvasBlob(animated){return new Promise(function(resolve,reject){exportingCanvas=true;renderCanvas(performance.now());if(!animated){canvas.toBlob(function(b){exportingCanvas=false;b?resolve({blob:b,name:'showcase.png'}):reject(Error('Canvas export failed'))},'image/png');return}if(!canvas.captureStream||!window.MediaRecorder){exportingCanvas=false;reject(Error('Animated export is not supported in this browser'));return}var stream=canvas.captureStream(24),chunks=[],rec;try{rec=new MediaRecorder(stream,{mimeType:'video/webm;codecs=vp9'})}catch(_){rec=new MediaRecorder(stream)}rec.ondataavailable=function(e){if(e.data.size)chunks.push(e.data)};rec.onerror=function(){exportingCanvas=false;reject(Error('Animation recording failed'))};rec.onstop=function(){exportingCanvas=false;stream.getTracks().forEach(function(x){x.stop()});resolve({blob:new Blob(chunks,{type:rec.mimeType||'video/webm'}),name:'showcase.webm'})};rec.start(250);setTimeout(function(){rec.stop()},8000)})}
  el('builderExport').onclick=async function(){var btn=this;btn.disabled=true;status(t('exporting'),'wait');try{var made=await canvasBlob(projectAnimated());var reserve=await fetch('/api/builder/reserve-export',{method:'POST',credentials:'same-origin'}),d=await reserve.json();if(!reserve.ok||!d.ok){if(reserve.status===401)el('btnAuth')&&el('btnAuth').click();throw Error(d.msg||t('failed'))}var file=new File([made.blob],made.name,{type:made.blob.type}),dt=new DataTransfer();dt.items.add(file);el('fileInput').files=dt.files;el('fileInput').dispatchEvent(new Event('change',{bubbles:true}));var nav=document.querySelector('#nav button[data-tab="process"]');if(nav)nav.click();status(t('sent'),'ok')}catch(e){status(e.message,'bad')}finally{btn.disabled=false}};

  async function loadProjects(){var grid=el('builderProjectGrid');if(!grid)return;try{var r=await fetch('/api/builder/projects',{credentials:'same-origin'}),d=await r.json();if(!r.ok||!d.ok){grid.innerHTML='<div class="builder-empty-layers">'+t('login')+'</div>';return}grid.innerHTML='';if(!d.items.length){grid.innerHTML='<div class="builder-empty-layers">'+t('empty-projects')+'</div>';return}d.items.forEach(function(item){var card=document.createElement('article');card.className='builder-project-card';var until=item.expires_at?new Date(item.expires_at*1000).toLocaleDateString() : '';card.innerHTML='<div class="builder-project-card__preview">'+String(item.showcase_mode||'workshop')+'</div><h3></h3><p></p><div class="builder-project-card__actions"><button class="btn ghost" data-edit>'+t('edit')+'</button><button class="btn ghost" data-delete>'+t('remove')+'</button></div>';card.querySelector('h3').textContent=item.name;card.querySelector('p').textContent=until?t('expires')+' '+until:t('permanent');card.querySelector('[data-edit]').onclick=function(){currentProjectId=item.id;project=clone(item.project);el('builderProjectName').value=item.name;selected=project.layers.length?project.layers[project.layers.length-1].id:'';resizeMode(project.mode);media.clear();renderLayers();openTool('builder')};card.querySelector('[data-delete]').onclick=async function(){await fetch('/api/builder/projects/'+encodeURIComponent(item.id),{method:'DELETE',credentials:'same-origin'});loadProjects()};grid.appendChild(card)})}catch(e){el('builderProjectsStatus').textContent=e.message}}

  function loadExternalProject(value,name){
    if(!value||!Array.isArray(value.layers))return false;
    currentProjectId='';project=clone(value);selected=project.layers.length?project.layers[project.layers.length-1].id:'';el('builderProjectName').value=String(name||'Steam DNA');
    media.forEach(function(node){if(node.pause)node.pause()});media.clear();resizeMode(project.mode||'workshop');renderLayers();openTool('builder');editorHistory?.commit();return true;
  }

  function openTool(name){var nav=document.querySelector('#nav button[data-tab="'+name+'"]');if(nav)nav.click();document.querySelectorAll('[data-open-tool]').forEach(function(b){b.classList.toggle('active',b.dataset.openTool===name)});if(name==='projects')loadProjects();if(name==='builder')requestAnimationFrame(updateGuides)}
  document.querySelectorAll('[data-open-tool]').forEach(function(b){b.onclick=function(){if(b.dataset.openTool==='builder'&&b.closest('.builder-projects-page')){currentProjectId='';project=freshProject('workshop');selected='';el('builderProjectName').value=lang()==='ru'?'Моя витрина':'My showcase';media.clear();resizeMode('workshop');renderLayers()}openTool(b.dataset.openTool)}});
  document.querySelectorAll('#nav button[data-tab]').forEach(function(b){b.addEventListener('click',function(){var name=b.dataset.tab,inWorkspace=['process','dna','builder','projects'].includes(name),sw=document.querySelector('.workspace-switch');if(sw)sw.hidden=!inWorkspace;document.querySelectorAll('[data-open-tool]').forEach(function(x){x.classList.toggle('active',inWorkspace&&x.dataset.openTool===name)})})});
  function applyLanguage(){document.querySelectorAll('[data-builder-i]').forEach(function(n){n.textContent=t(n.dataset.builderI)});document.querySelectorAll('[data-builder-i-title]').forEach(function(n){var value=t(n.dataset.builderITitle);n.title=value;n.setAttribute('aria-label',value)});renderLayers();loadProjects()}
  window.addEventListener('sm:langchange',applyLanguage);
  window.ShowcaseBuilder={loadProject:loadExternalProject,open:function(){openTool('builder')}};
  applyLanguage();resizeMode('workshop');renderLayers();requestAnimationFrame(draw);
  if(window.createBuilderHistory)editorHistory=window.createBuilderHistory(root,function(){return {project:project,name:el('builderProjectName').value,id:currentProjectId,selected:selected}},function(value){project=clone(value.project);currentProjectId=value.id||'';selected=value.selected||'';el('builderProjectName').value=value.name||'';media.forEach(function(node){if(node.pause)node.pause()});media.clear();resizeMode(project.mode);renderLayers();root.querySelectorAll('input[type="range"]').forEach(function(n){var progress=(n.value-n.min)/(n.max-n.min)*100;n.style.setProperty('--range-progress',progress+'%')})});
})();
