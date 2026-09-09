(function () {
  'use strict';

  var root = document.getElementById('showcaseBuilder');
  if (!root) return;
  var canvas = document.getElementById('builderCanvas');
  var ctx = canvas.getContext('2d', { alpha: false });
  var media = new Map();
  var selected = null;
  var uploadType = 'character';
  var catalogPage = 0;
  var currentProjectId = '';
  var dragging = null;
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
  if (window.SMLang && SMLang.extend) SMLang.extend(COPY);

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
      var off=document.createElement('canvas');off.width=w;off.height=h;var oc=off.getContext('2d');oc.drawImage(node,0,0,w,h);
      try{var im=oc.getImageData(0,0,w,h);applyChroma(im,w,h,layer);oc.putImageData(im,0,0)}catch(_){ }
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
  function drawFrame(layer) {ctx.save();ctx.globalAlpha=layer.opacity;ctx.strokeStyle=layer.color||'#52d5ff';ctx.lineWidth=layer.frameWidth||4;var n=ctx.lineWidth/2;ctx.strokeRect(n,n,canvas.width-ctx.lineWidth,canvas.height-ctx.lineWidth);ctx.restore()}
  function drawText(layer, now) {var a=animationTransform(layer,now),font=safeFontName(layer.font);ctx.save();ctx.globalAlpha=layer.opacity;ctx.translate(layer.x*canvas.width,layer.y*canvas.height+a.y);ctx.rotate(layer.rotation*Math.PI/180+a.rotate);ctx.scale(layer.scale*a.scale,layer.scale*a.scale);ctx.fillStyle=layer.color||'#fff';ctx.textAlign='center';ctx.textBaseline='middle';ctx.font='800 '+(layer.fontSize||64)+'px "'+font+'"';String(layer.text||'').split('\n').forEach(function(line,i,arr){ctx.fillText(line,0,(i-(arr.length-1)/2)*(layer.fontSize||64)*1.12,canvas.width*.9)});ctx.restore()}
  function draw(now) {
    ctx.fillStyle=project.background||'#061019';ctx.fillRect(0,0,canvas.width,canvas.height);
    project.layers.forEach(function(layer){if(layer.visible===false)return;if(layer.type==='text')drawText(layer,now);else if(layer.type==='frame')drawFrame(layer);else if(layer.type==='effect')drawEffect(layer,now);else drawMediaLayer(layer,mediaFor(layer),now)});
    requestAnimationFrame(draw);
  }

  function updateGuides() {
    var host=el('builderGuides');host.dataset.mode=project.mode;host.innerHTML='';
    var cuts=project.mode==='workshop'?[.2,.4,.6,.8]:(project.mode==='split'?[506/606]:[]);
    var rect=canvas.getBoundingClientRect(),wrap=canvas.parentElement.getBoundingClientRect();
    cuts.forEach(function(c){var i=document.createElement('i');i.style.left=(rect.left-wrap.left+rect.width*c)+'px';i.style.top=(rect.top-wrap.top)+'px';i.style.height=rect.height+'px';host.appendChild(i)});
  }
  function resizeMode(mode) {project.mode=mode;project.width=mode==='featured'?630:(mode==='split'?606:750);canvas.width=project.width;canvas.height=project.height||1000;document.querySelectorAll('[data-builder-mode]').forEach(function(b){b.classList.toggle('active',b.dataset.builderMode===mode)});requestAnimationFrame(updateGuides)}

  function icon(type){return {background:'▧',character:'♙',text:'T',frame:'□',effect:'✦'}[type]||'·'}
  function renderLayers(){var host=el('builderLayerList');host.innerHTML='';project.layers.slice().reverse().forEach(function(layer){var row=document.createElement('div');row.className='builder-layer'+(layer.id===selected?' is-selected':'');row.innerHTML='<span class="builder-layer__icon">'+icon(layer.type)+'</span><span class="builder-layer__copy"><b></b><span>'+layer.type+'</span></span><span class="builder-layer__actions"><button data-action="visible" title="Show / hide">'+(layer.visible===false?'○':'●')+'</button><button data-action="up" title="Move up">↑</button><button data-action="down" title="Move down">↓</button><button data-action="delete" title="Delete">×</button></span>';row.querySelector('b').textContent=layer.name;row.onclick=function(){selected=layer.id;renderLayers();syncInspector()};row.querySelectorAll('button').forEach(function(btn){btn.onclick=function(e){e.stopPropagation();layerAction(layer,btn.dataset.action)}});host.appendChild(row)});el('builderEmptyLayers').hidden=project.layers.length>0;syncInspector()}
  function layerAction(layer,action){var i=project.layers.indexOf(layer);if(action==='delete'){project.layers.splice(i,1);if(selected===layer.id)selected=''}else if(action==='up'&&i<project.layers.length-1){project.layers.splice(i,1);project.layers.splice(i+1,0,layer)}else if(action==='down'&&i>0){project.layers.splice(i,1);project.layers.splice(i-1,0,layer)}else if(action==='visible')layer.visible=layer.visible===false;renderLayers()}
  function syncInspector(){var layer=currentLayer(),box=el('builderInspector');box.hidden=!layer;if(!layer)return;el('builderLayerName').value=layer.name||'';el('builderScale').value=Math.round((layer.scale||1)*100);el('builderRotation').value=layer.rotation||0;el('builderOpacity').value=Math.round((layer.opacity==null?1:layer.opacity)*100);el('builderTextControls').hidden=layer.type!=='text';el('builderFrameControls').hidden=layer.type!=='frame';el('builderEffectControls').hidden=layer.type!=='effect';el('builderMediaControls').hidden=!['background','character'].includes(layer.type);if(layer.type==='text'){el('builderText').value=layer.text||'';el('builderFont').value=layer.font||'Mulish';el('builderColor').value=layer.color||'#ffffff';el('builderFontSize').value=layer.fontSize||64;syncFontPreview(layer)}if(layer.type==='frame'){el('builderFrameColor').value=layer.color||'#52d5ff';el('builderFrameWidth').value=layer.frameWidth||4}if(layer.type==='effect'){el('builderEffectType').value=layer.effect||'particle';el('builderEffectColor').value=layer.color||'#52d5ff';el('builderEffectColorRow').hidden=layer.effect==='custom'||!!layer.src}if(['background','character'].includes(layer.type)){var tolerance=layer.chromaTolerance==null?45:layer.chromaTolerance,feather=layer.chromaFeather==null?16:layer.chromaFeather;el('builderChroma').checked=!!layer.chroma;el('builderChromaSettings').hidden=!layer.chroma;el('builderChromaTolerance').value=tolerance;el('builderChromaToleranceValue').value=tolerance;el('builderChromaFeather').value=feather;el('builderChromaFeatherValue').value=(feather/10).toFixed(1);el('builderAnimation').value=layer.animation||'none'}}
  function bind(id,event,fn){el(id).addEventListener(event,function(){var layer=currentLayer();if(!layer)return;fn(layer,this);if(id==='builderLayerName')renderLayers()})}
  bind('builderLayerName','input',function(l,n){l.name=n.value});bind('builderScale','input',function(l,n){l.scale=+n.value/100});bind('builderRotation','input',function(l,n){l.rotation=+n.value});bind('builderOpacity','input',function(l,n){l.opacity=+n.value/100});bind('builderText','input',function(l,n){l.text=n.value;syncFontPreview(l)});bind('builderFont','change',function(l,n){l.font=n.value;syncFontPreview(l);if(document.fonts)document.fonts.load('800 64px "'+safeFontName(n.value)+'"')});bind('builderColor','input',function(l,n){l.color=n.value});bind('builderFontSize','input',function(l,n){l.fontSize=+n.value});bind('builderFrameColor','input',function(l,n){l.color=n.value});bind('builderFrameWidth','input',function(l,n){l.frameWidth=+n.value});bind('builderEffectType','change',function(l,n){l.effect=n.value;l.name=n.options[n.selectedIndex].text;renderLayers()});bind('builderEffectColor','input',function(l,n){l.color=n.value});bind('builderChroma','change',function(l,n){l.chroma=n.checked;syncInspector()});bind('builderChromaTolerance','input',function(l,n){l.chromaTolerance=+n.value;el('builderChromaToleranceValue').value=n.value});bind('builderChromaFeather','input',function(l,n){l.chromaFeather=+n.value;el('builderChromaFeatherValue').value=(+n.value/10).toFixed(1)});bind('builderAnimation','change',function(l,n){l.animation=n.value});

  Array.from(el('builderFont').options).forEach(function(option){option.style.fontFamily='"'+safeFontName(option.value)+'"'});

  function waitForRemoval(jobId){return new Promise(function(resolve,reject){function poll(){fetch('/api/builder/remove-background/'+encodeURIComponent(jobId),{credentials:'same-origin'}).then(function(r){return r.json()}).then(function(d){if(!d.ok)throw Error(d.msg||t('failed'));if(d.status==='done'){resolve(d.result);return}if(d.status==='error'){reject(Error(d.error||t('failed')));return}status(t('ai-working')+' '+(d.pct||0)+'%','wait');setTimeout(poll,900)}).catch(reject)}poll()})}
  el('builderAiRemove').onclick=async function(){var layer=currentLayer();if(!layer||!layer.src)return;this.disabled=true;status(t('ai-working'),'wait');try{var r=await fetch('/api/builder/remove-background',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:layer.src})}),d=await r.json();if(!r.ok||!d.ok){if(r.status===401)el('btnAuth')&&el('btnAuth').click();throw Error(d.msg||t('failed'))}var result=await waitForRemoval(d.job_id);media.delete(layer.id+'|'+layer.src);layer.src=result.url;layer.mediaType=result.media_type;layer.chroma=false;syncInspector();status('', '')}catch(e){status(e.message,'bad')}finally{this.disabled=false}};

  async function upload(file,type){status(t('uploading'),'wait');var layer=defaultLayer(type);layer.name=file.name;layer.src=URL.createObjectURL(file);layer.mediaType=file.type;project.layers.push(layer);selected=layer.id;renderLayers();try{var fd=new FormData();fd.append('file',file);var r=await fetch('/api/builder/assets',{method:'POST',credentials:'same-origin',body:fd}),d=await r.json();if(!r.ok||!d.ok)throw Error(d.msg||t('failed'));media.delete(layer.id+'|'+layer.src);URL.revokeObjectURL(layer.src);layer.src=d.url;layer.mediaType=d.media_type;status('', '')}catch(e){status(e.message==='Login required'?t('login'):e.message,'bad')}}
  document.querySelectorAll('[data-add-layer]').forEach(function(button){button.onclick=function(){var type=button.dataset.addLayer;if(type==='text'||type==='frame'||type==='effect'){var layer=defaultLayer(type);project.layers.push(layer);selected=layer.id;renderLayers()}else{uploadType=type;el('builderMediaInput').click()}}});
  el('builderEffectUpload').onclick=function(){uploadType='effect';el('builderMediaInput').click()};
  el('builderMediaInput').onchange=function(){var file=this.files&&this.files[0];if(file)upload(file,uploadType);this.value=''};
  document.querySelectorAll('[data-builder-mode]').forEach(function(b){b.onclick=function(){resizeMode(b.dataset.builderMode)}});

  canvas.addEventListener('pointerdown',function(e){var layer=currentLayer();if(!layer||layer.type==='frame'||layer.type==='effect')return;var r=canvas.getBoundingClientRect();dragging={id:layer.id,dx:(e.clientX-r.left)/r.width-layer.x,dy:(e.clientY-r.top)/r.height-layer.y};canvas.setPointerCapture(e.pointerId)});
  canvas.addEventListener('pointermove',function(e){if(!dragging)return;var layer=currentLayer();if(!layer||layer.id!==dragging.id)return;var r=canvas.getBoundingClientRect();layer.x=Math.max(0,Math.min(1,(e.clientX-r.left)/r.width-dragging.dx));layer.y=Math.max(0,Math.min(1,(e.clientY-r.top)/r.height-dragging.dy))});
  canvas.addEventListener('pointerup',function(){dragging=null});
  window.addEventListener('resize',updateGuides);

  function openCatalog(reset){if(reset){catalogPage=0;el('builderCatalogGrid').innerHTML=''}el('builderCatalog').hidden=false;var q=el('builderCatalogSearch').value.trim();Promise.all([
    fetch('/api/steam/backgrounds?asset=points_background&kind=static&page='+catalogPage+'&count=24&q='+encodeURIComponent(q)).then(function(r){return r.json()}),
    fetch('/api/steam/backgrounds?asset=animated_background&kind=animated&page='+catalogPage+'&count=24&q='+encodeURIComponent(q)).then(function(r){return r.json()})
  ]).then(function(parts){parts.forEach(function(d){(d.items||[]).forEach(addCatalogItem)});catalogPage++}).catch(function(e){status(e.message,'bad')})}
  function addCatalogItem(item){var grid=el('builderCatalogGrid'),key=String(item.appid||'')+':'+String(item.defid||item.image);if(grid.querySelector('[data-key="'+CSS.escape(key)+'"]'))return;var b=document.createElement('button');b.type='button';b.dataset.key=key;var src=item.movie||item.image,poster=item.image||src;b.innerHTML=item.movie?'<video muted loop autoplay playsinline></video>':'<img alt="">';var n=b.firstElementChild;n.src=safeSource(item.movie||poster);if(item.movie)n.poster=safeSource(poster);b.onclick=function(){var layer=defaultLayer('background');layer.name=item.name||t('background');layer.src=src;layer.mediaType=item.movie?'video/webm':'image/jpeg';project.layers=project.layers.filter(function(x){return x.type!=='background'});project.layers.unshift(layer);selected=layer.id;renderLayers();el('builderCatalog').hidden=true};grid.appendChild(b)}
  el('builderSteamBackgrounds').onclick=function(){openCatalog(true)};el('builderCatalogMore').onclick=function(){openCatalog(false)};el('builderCatalogClose').onclick=function(){el('builderCatalog').hidden=true};var searchTimer;el('builderCatalogSearch').oninput=function(){clearTimeout(searchTimer);searchTimer=setTimeout(function(){openCatalog(true)},350)};

  async function saveProject(){var r=await fetch('/api/builder/projects',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:currentProjectId,name:el('builderProjectName').value,project:project})}),d=await r.json();if(!r.ok||!d.ok){if(r.status===401)el('btnAuth')&&el('btnAuth').click();throw Error(d.msg||t('failed'))}currentProjectId=d.item.id;status(t('saved')+(d.retention_days?' · 7 days':''),'ok');loadProjects()}
  el('builderSave').onclick=function(){saveProject().catch(function(e){status(e.message==='Login required'?t('login'):e.message,'bad')})};

  function projectAnimated(){return project.layers.some(function(l){return l.visible!==false&&(l.type==='effect'||l.animation&&l.animation!=='none'||l.mediaType&&l.mediaType.indexOf('video/')===0||/\.gif(\?|$)/i.test(l.src||''))})}
  function canvasBlob(animated){return new Promise(function(resolve,reject){if(!animated){canvas.toBlob(function(b){b?resolve({blob:b,name:'showcase.png'}):reject(Error('Canvas export failed'))},'image/png');return}if(!canvas.captureStream||!window.MediaRecorder){reject(Error('Animated export is not supported in this browser'));return}var stream=canvas.captureStream(24),chunks=[],rec;try{rec=new MediaRecorder(stream,{mimeType:'video/webm;codecs=vp9'})}catch(_){rec=new MediaRecorder(stream)}rec.ondataavailable=function(e){if(e.data.size)chunks.push(e.data)};rec.onerror=function(){reject(Error('Animation recording failed'))};rec.onstop=function(){stream.getTracks().forEach(function(x){x.stop()});resolve({blob:new Blob(chunks,{type:rec.mimeType||'video/webm'}),name:'showcase.webm'})};rec.start(250);setTimeout(function(){rec.stop()},8000)})}
  el('builderExport').onclick=async function(){var btn=this;btn.disabled=true;status(t('exporting'),'wait');try{var made=await canvasBlob(projectAnimated());var reserve=await fetch('/api/builder/reserve-export',{method:'POST',credentials:'same-origin'}),d=await reserve.json();if(!reserve.ok||!d.ok){if(reserve.status===401)el('btnAuth')&&el('btnAuth').click();throw Error(d.msg||t('failed'))}var file=new File([made.blob],made.name,{type:made.blob.type}),dt=new DataTransfer();dt.items.add(file);el('fileInput').files=dt.files;el('fileInput').dispatchEvent(new Event('change',{bubbles:true}));var nav=document.querySelector('#nav button[data-tab="process"]');if(nav)nav.click();status(t('sent'),'ok')}catch(e){status(e.message,'bad')}finally{btn.disabled=false}};

  async function loadProjects(){var grid=el('builderProjectGrid');if(!grid)return;try{var r=await fetch('/api/builder/projects',{credentials:'same-origin'}),d=await r.json();if(!r.ok||!d.ok){grid.innerHTML='<div class="builder-empty-layers">'+t('login')+'</div>';return}grid.innerHTML='';if(!d.items.length){grid.innerHTML='<div class="builder-empty-layers">'+t('empty-projects')+'</div>';return}d.items.forEach(function(item){var card=document.createElement('article');card.className='builder-project-card';var until=item.expires_at?new Date(item.expires_at*1000).toLocaleDateString() : '';card.innerHTML='<div class="builder-project-card__preview">'+String(item.showcase_mode||'workshop')+'</div><h3></h3><p></p><div class="builder-project-card__actions"><button class="btn ghost" data-edit>'+t('edit')+'</button><button class="btn ghost" data-delete>'+t('remove')+'</button></div>';card.querySelector('h3').textContent=item.name;card.querySelector('p').textContent=until?t('expires')+' '+until:t('permanent');card.querySelector('[data-edit]').onclick=function(){currentProjectId=item.id;project=clone(item.project);el('builderProjectName').value=item.name;selected=project.layers.length?project.layers[project.layers.length-1].id:'';resizeMode(project.mode);media.clear();renderLayers();openTool('builder')};card.querySelector('[data-delete]').onclick=async function(){await fetch('/api/builder/projects/'+encodeURIComponent(item.id),{method:'DELETE',credentials:'same-origin'});loadProjects()};grid.appendChild(card)})}catch(e){el('builderProjectsStatus').textContent=e.message}}

  function openTool(name){var nav=document.querySelector('#nav button[data-tab="'+name+'"]');if(nav)nav.click();document.querySelectorAll('[data-open-tool]').forEach(function(b){b.classList.toggle('active',b.dataset.openTool===name)});if(name==='projects')loadProjects();if(name==='builder')requestAnimationFrame(updateGuides)}
  document.querySelectorAll('[data-open-tool]').forEach(function(b){b.onclick=function(){if(b.dataset.openTool==='builder'&&b.closest('.builder-projects-page')){currentProjectId='';project=freshProject('workshop');selected='';el('builderProjectName').value=lang()==='ru'?'Моя витрина':'My showcase';media.clear();resizeMode('workshop');renderLayers()}openTool(b.dataset.openTool)}});
  document.querySelectorAll('#nav button[data-tab]').forEach(function(b){b.addEventListener('click',function(){var name=b.dataset.tab,inWorkspace=['process','builder','projects'].includes(name),sw=document.querySelector('.workspace-switch');if(sw)sw.hidden=!inWorkspace;document.querySelectorAll('[data-open-tool]').forEach(function(x){x.classList.toggle('active',inWorkspace&&x.dataset.openTool===name)})})});
  function applyLanguage(){document.querySelectorAll('[data-builder-i]').forEach(function(n){n.textContent=t(n.dataset.builderI)});renderLayers();loadProjects()}
  window.addEventListener('sm:langchange',applyLanguage);
  applyLanguage();resizeMode('workshop');renderLayers();requestAnimationFrame(draw);
})();
