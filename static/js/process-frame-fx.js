/* Styled and animated frames in Process for every showcase type (Workshop,
   Featured, Artwork Split). Picture tiles (frame designs drawn for the chosen
   showcase type, animations playing live) replace the old checkbox: "None" keeps
   #workshopOutline unchecked, any other tile checks it, so app.js keeps sending
   the same form fields. Drawing and labels come from SMSquaresFx
   (workshop-squares-fx.js); the server uses smweb/square_fx.py with the same
   formulas (processor._split_parts / _draw_whole_frame for Featured/Split). */
(function(){
  'use strict';
  var api=window.SMSquaresFx,host=document.getElementById('workshopOutlineSettings');
  if(!api||!host)return;
  var toggle=document.getElementById('workshopOutline'),width=document.getElementById('outlineWidth'),color=document.getElementById('outlineColor');
  var LANGS=['en','ru','de','tr','fr','uk','es','pt'];
  var WORDS={
    target:['Frame around','Рамка вокруг','Rahmen um','Çerçeve','Cadre autour de','Рамка навколо','Marco alrededor de','Moldura em volta de'],
    each:['each part','каждой части','jedes Teil','her parça','chaque partie','кожної частини','cada parte','cada parte'],
    whole:['the whole showcase','всей витрины','die ganze Vitrine','tüm vitrin','toute la vitrine','всієї вітрини','todo el expositor','toda a vitrine'],
    note:['Animated frames turn a still picture into a looping GIF (4 s). Videos and GIFs keep their own length.','Анимированная рамка превращает картинку в зацикленный GIF (4 с). Видео и GIF сохраняют свою длину.','Animierte Rahmen machen aus einem Standbild ein Endlos-GIF (4 s). Videos und GIFs behalten ihre Länge.','Animasyonlu çerçeve durağan görseli döngülü bir GIF’e (4 sn) dönüştürür. Video ve GIF’ler kendi sürelerini korur.','Un cadre animé transforme une image fixe en GIF en boucle (4 s). Les vidéos et GIF gardent leur durée.','Анімована рамка перетворює зображення на зациклений GIF (4 с). Відео та GIF зберігають свою тривалість.','Un marco animado convierte una imagen fija en un GIF en bucle (4 s). Los vídeos y GIF mantienen su duración.','Uma moldura animada transforma uma imagem estática em um GIF em loop (4 s). Vídeos e GIFs mantêm a duração.']
  };
  var row=document.createElement('div');row.className='workshop-outline__fx';
  row.innerHTML='<div class="process-frame__looks" data-no-translate><span data-pfx="presets"></span><div class="sqfx__presets"></div></div>'+
    '<div class="process-frame__block process-frame__shape"><span class="sqfx__label" data-pfx="frame"></span><div class="process-frame__shapes"></div></div>'+
    '<div class="process-frame__block process-frame__anim"><span class="sqfx__label" data-pfx="animation"></span><div class="process-frame__styles"></div></div>'+
    '<div class="process-frame__block process-frame__colors"><span class="sqfx__label" data-pfx="color"></span><div class="process-frame__swatches"></div></div>'+
    '<label class="field workshop-outline__plate"><span><span data-pfx="plate"></span> <output id="outlinePlateValue">100%</output></span><input type="range" id="outlinePlate" min="0" max="100" step="5" value="100"></label>'+
    '<label class="field workshop-outline__color2"><span data-pfx="color2"></span><input type="color" id="outlineColor2" value="#8a62ff"></label>'+
    '<label class="field workshop-outline__speed"><span data-pfx="speed"></span><input type="range" id="outlineSpeed" min="1" max="4" step="1" value="1"></label>'+
    '<div class="process-frame__target" role="group"><span data-pw="target"></span><button type="button" data-target="squares" data-pw="each"></button><button type="button" data-target="strip" data-pw="whole"></button></div>'+
    '<p class="workshop-outline__fxnote" data-pw="note"></p>';
  host.prepend(row);
  var color2=row.querySelector('#outlineColor2'),speed=row.querySelector('#outlineSpeed');
  var targetBox=row.querySelector('.process-frame__target'),looks=row.querySelector('.process-frame__looks .sqfx__presets');
  var shapeHost=row.querySelector('.process-frame__shapes'),styleHost=row.querySelector('.process-frame__styles'),swatchHost=row.querySelector('.process-frame__swatches');
  var plate=row.querySelector('#outlinePlate'),plateValue=row.querySelector('#outlinePlateValue'),shape='rect';
  var style='neon',target='squares',loop=0,lastDraw=0,pickerTimer=0;
  // The native colour input now lives inside the swatch row (custom colour); app.js still reads it.
  row.after(width.closest('label'));color.closest('label').hidden=true;color.closest('label').classList.add('process-frame__legacy-color');

  function language(){return window.SMLang?.get?.()||document.documentElement.lang||'en'}
  function word(key){var i=Math.max(0,LANGS.indexOf(language()));return (WORDS[key]||[])[i]||(WORDS[key]||[])[0]||key}
  function mode(){return (window.state&&window.state.mode)||'workshop'}
  function current(){return toggle&&toggle.checked?style:'none'}
  function relabel(){
    var lang=language();
    row.querySelectorAll('[data-pfx]').forEach(function(node){node.textContent=api.t(node.dataset.pfx,lang)});
    row.querySelectorAll('[data-pw]').forEach(function(node){node.textContent=word(node.dataset.pw)});
    looks.replaceChildren();
    (api.PRESETS||[]).forEach(function(preset){
      var button=document.createElement('button');button.type='button';button.className='sqfx__preset';button.dataset.preset=preset[0];
      button.textContent=api.t('pr_'+preset[0],lang);
      button.addEventListener('click',function(){var f=preset[1];setFrame({style:f.style,shape:f.shape||'rect',plate:f.plate||0,color:f.color||'#ffffff',color2:f.color2||'#8a62ff',width:f.width||2,speed:f.speed||1})});
      looks.append(button);
    });
    renderPickers();
    sync();
  }
  function setOn(on){if(toggle&&toggle.checked!==on){toggle.checked=on;toggle.dispatchEvent(new Event('change',{bubbles:true}))}}
  /* Picture pickers: frame designs drawn for the current showcase type, animations playing live. */
  function renderPickers(){
    var lang=language(),on=current()!=='none';
    shapeHost.replaceChildren(api.shapePicker({mode:mode(),value:on?shape:'none',color:color.value,language:lang,includeNone:true,onPick:function(key){
      if(key==='none'){setOn(false)}
      else{
        if(key!=='rect'&&key!==shape&&Number(plate.value)===0)plate.value='100';
        shape=key;if(!on)style=key==='rect'?'neon':'shimmer';setOn(true);
      }
      renderPickers();sync();
    }}));
    styleHost.replaceChildren(api.stylePicker({value:style,color:color.value,color2:color2.value,language:lang,styles:api.FRAME_STYLES.filter(function(k){return k!=='none'}),onPick:function(key){style=key;setOn(true);renderPickers();sync()}}));
    swatchHost.replaceChildren(api.colorSwatches({value:color.value,language:lang,onPick:function(value){
      color.value=value;color.dispatchEvent(new Event('input',{bubbles:true}));
      swatchHost.querySelectorAll('.sqfx-swatches__dot').forEach(function(dot){dot.setAttribute('aria-pressed',String(dot.title===value))});
      clearTimeout(pickerTimer);pickerTimer=setTimeout(function(){renderPickers();sync()},180);
    }}));
  }
  function sync(){
    var value=current(),on=value!=='none',animated=api.isAnimatedFrame(value);
    styleHost.querySelectorAll('[data-style]').forEach(function(button){button.setAttribute('aria-checked',String(on&&button.dataset.style===value))});
    shapeHost.querySelectorAll('[data-shape]').forEach(function(button){button.setAttribute('aria-checked',String(button.dataset.shape===(on?shape:'none')))});
    host.classList.toggle('is-off',!on);
    row.querySelector('.process-frame__anim').hidden=!on;
    row.querySelector('.process-frame__colors').hidden=!on||value==='rgb';
    row.querySelector('.workshop-outline__color2').hidden=!on||['double','comet','dashes'].indexOf(value)<0;
    row.querySelector('.workshop-outline__speed').hidden=!animated;
    row.querySelector('.workshop-outline__plate').hidden=!on||shape==='rect';
    plateValue.textContent=plate.value+'%';
    row.querySelector('.workshop-outline__fxnote').hidden=!animated;
    width.closest('label').hidden=!on;
    targetBox.hidden=!on||mode()==='featured'||(mode()==='split'&&isDesign());
    targetBox.querySelectorAll('button').forEach(function(button){button.setAttribute('aria-pressed',String(button.dataset.target===target))});
    redraw();
    document.dispatchEvent(new CustomEvent('sm:process-frame-change'));
  }
  function redraw(){if(typeof window.__wmRedraw==='function')window.__wmRedraw();animate()}
  function previewVisible(){var canvas=document.getElementById('wmCanvas');return !!(canvas&&canvas.offsetParent&&canvas.style.display!=='none')}
  // Redraw the preview ~25 times per second only while an animated frame is visible.
  function animate(){
    if(loop)return;
    (function tick(now){
      var active=api.isAnimatedFrame(current())&&!document.hidden&&previewVisible();
      if(!active){loop=0;return}
      if(!now||now-lastDraw>40){lastDraw=now||0;if(typeof window.__wmRedraw==='function')window.__wmRedraw()}
      loop=requestAnimationFrame(tick);
    })();
  }
  /* Final-file rectangles on the preview canvas (the canvas shows the whole source).
     Split parts carry their role, so HUD ornaments sit on the outer side of each file. */
  function rects(w,h){
    var m=mode();
    if(m==='featured'||target==='strip'||(m==='split'&&isDesign()))return [[0,0,w,h,'full']];
    if(m==='split'){var cut=Math.round(w*506/606);return [[0,0,cut,h,'left'],[cut,0,w-cut,h,'right']]}
    return api.panelRects(w,h,'squares');
  }
  function isDesign(){return ['rect','bevel','notch'].indexOf(shape)<0}
  function withRoles(panels){
    if(mode()==='split'&&panels.length===2)return [panels[0].slice(0,4).concat('left'),panels[1].slice(0,4).concat('right')];
    return panels;
  }

  /* Programmatic frame change (quick looks, restored settings). Unknown values are ignored. */
  function setFrame(next){
    next=next||{};
    if(next.style==='none'){if(toggle)toggle.checked=false}
    else if(api.FRAME_STYLES.indexOf(next.style)>0){style=next.style;if(toggle)toggle.checked=true}
    if(/^#[0-9a-f]{6}$/i.test(next.color||''))color.value=next.color;
    if(/^#[0-9a-f]{6}$/i.test(next.color2||''))color2.value=next.color2;
    if(Number(next.width)>=1&&Number(next.width)<=8){width.value=String(Math.round(next.width));width.dispatchEvent(new Event('input',{bubbles:true}))}
    if(Number(next.speed)>=1&&Number(next.speed)<=4)speed.value=String(Math.round(next.speed));
    if(next.target==='squares'||next.target==='strip')target=next.target;
    if(typeof next.shape==='string'&&/^[a-z0-9_-]{2,24}$/.test(next.shape))shape=next.shape;
    if(Number(next.plate)>=0&&Number(next.plate)<=100)plate.value=String(Math.round(next.plate));
    if(toggle)toggle.dispatchEvent(new Event('change',{bubbles:true}));
    renderPickers();
    sync();
  }
  window.SMProcessFrame={
    set:setFrame,
    state:function(){return {style:current(),shape:shape,plate:Number(plate.value)||0,color:color.value,color2:color2.value,width:Number(width.value)||2,speed:Number(speed.value)||1,target:target}},
    options:function(){return {style:current(),shape:shape,plate:shape==='rect'?0:Number(plate.value)||0,color2:color2.value,speed:Number(speed.value)||1,target:target}},
    styleName:function(){var value=current();return value==='none'?'':api.t(value,language())},
    /* 'Crown · Shimmer' for the folded Design card. */
    summary:function(){var value=current();if(value==='none')return '';var lang=language();return (shape!=='rect'?api.t('shape_'+shape,lang)+' · ':'')+api.t(value,lang)},
    /* Called by the Process preview (app.js) instead of the plain stroke. */
    /* panels: [x,y,w,h] of each final file on the preview (parts are drawn with gaps). */
    draw:function(ctx,w,h,stroke,panels){
      var period=4;
      var whole=mode()==='featured'||target==='strip'||(mode()==='split'&&isDesign());
      var list=panels&&panels.length?(whole?[[0,0,w,h,'full']]:withRoles(panels)):rects(w,h);
      api.drawFrame(ctx,(performance.now()/1000%period)/period,{style:current(),shape:shape,plate:shape==='rect'?0:Number(plate.value)||0,color:color.value,color2:color2.value,width:stroke,speed:Number(speed.value)||1,target:target==='strip'||mode()!=='workshop'?'strip':'squares'},list);
      return true;
    },
    refresh:sync
  };
  targetBox.addEventListener('click',function(event){var button=event.target.closest('[data-target]');if(!button)return;target=button.dataset.target;sync()});
  [color2,speed,plate].forEach(function(node){node.addEventListener('input',sync);node.addEventListener('change',sync)});
  [width,color].forEach(function(node){if(node)node.addEventListener('input',function(){redraw()})});
  color2.addEventListener('change',function(){renderPickers();sync()});
  document.addEventListener('sm:frame-designs',function(){renderPickers();sync()});
  document.addEventListener('visibilitychange',animate);
  document.querySelectorAll('.mode').forEach(function(button){button.addEventListener('click',function(){setTimeout(function(){renderPickers();sync()},0)})});
  window.addEventListener('sm:langchange',relabel);

  /* A design sent from "Create a design" already carries its own frames, effects and
     colour grade. While that file is in the list, the Process frame and colour
     correction are switched off and locked (so no second frame is added); the
     previous choice comes back when the file leaves the list or on "Add anyway". */
  var LOCK_WORDS={
    title:['Frame and colours come from your design','Рамка и цвета уже есть в дизайне','Rahmen und Farben stammen aus deinem Design','Çerçeve ve renkler tasarımından geliyor','Le cadre et les couleurs viennent de votre design','Рамка й кольори вже є в дизайні','El marco y los colores vienen de tu diseño','A moldura e as cores vêm do seu design'],
    text:['This file was made in “Create a design”, so frames and colour correction are off here: a second frame would be drawn on top of yours.','Файл сделан во вкладке «Создать дизайн», поэтому рамки и цветокоррекция здесь выключены: иначе поверх твоей рамки легла бы ещё одна.','Diese Datei stammt aus „Design erstellen“, daher sind Rahmen und Farbkorrektur hier aus: sonst läge ein zweiter Rahmen über deinem.','Bu dosya “Tasarım oluştur” ile yapıldı; bu yüzden çerçeve ve renk düzeltme burada kapalı: yoksa seninkinin üstüne ikinci bir çerçeve çizilirdi.','Ce fichier vient de « Créer un design » : cadres et correction des couleurs sont désactivés ici, sinon un second cadre s’ajouterait au vôtre.','Файл зроблено у вкладці «Створити дизайн», тому рамки й корекція кольору тут вимкнені: інакше поверх твоєї рамки ляже ще одна.','Este archivo se hizo en «Crear un diseño», así que el marco y la corrección de color están desactivados aquí: si no, se añadiría un segundo marco.','Este arquivo foi feito em “Criar um design”, então moldura e correção de cor estão desligadas aqui: senão uma segunda moldura seria desenhada.'],
    short:['from your design','из дизайна','aus dem Design','tasarımdan','du design','з дизайну','del diseño','do design'],
    anyway:['Add a frame anyway','Всё равно добавить рамку','Trotzdem Rahmen hinzufügen','Yine de çerçeve ekle','Ajouter un cadre quand même','Все одно додати рамку','Añadir marco de todos modos','Adicionar moldura mesmo assim']
  };
  function lockWord(key){var i=Math.max(0,LANGS.indexOf(language()));return LOCK_WORDS[key][i]||LOCK_WORDS[key][0]}
  var gradeBlock=document.getElementById('processGradeBlock'),designCard=document.getElementById('processDesignCard');
  var lockNote=document.createElement('div');lockNote.className='process-builder-lock';lockNote.hidden=true;lockNote.setAttribute('role','note');
  lockNote.innerHTML='<b></b><span></span><button type="button" class="btn ghost"></button>';
  host.before(lockNote);
  var builderFile=null,locked=false,saved=null;
  function sameFile(a,b){return !!a&&!!b&&(a===b||a.name===b.name&&a.size===b.size&&a.lastModified===b.lastModified)}
  function hasBuilderFile(){return !!builderFile&&((window.state&&state.files)||[]).some(function(f){return sameFile(f,builderFile)})}
  function paintLock(){
    lockNote.querySelector('b').textContent=lockWord('title');lockNote.querySelector('span').textContent=lockWord('text');lockNote.querySelector('button').textContent=lockWord('anyway');
    lockNote.hidden=!locked;
    [host,gradeBlock].forEach(function(node){if(!node)return;node.classList.toggle('is-builder-locked',locked);if(locked)node.setAttribute('inert','');else node.removeAttribute('inert')});
    if(designCard)designCard.classList.toggle('has-builder-lock',locked);
  }
  function lock(){
    if(locked)return;
    saved={frame:window.SMProcessFrame.state(),grade:window.SMProcessGrade?SMProcessGrade.get():null};
    locked=true;
    setFrame({style:'none'});
    if(window.SMProcessGrade)SMProcessGrade.set(null);
    paintLock();
    document.dispatchEvent(new CustomEvent('sm:process-frame-change'));
  }
  function unlock(restore){
    if(!locked)return;
    locked=false;paintLock();
    document.dispatchEvent(new CustomEvent('sm:process-frame-change'));
    if(restore&&saved){setFrame(saved.frame);if(saved.grade&&window.SMProcessGrade)SMProcessGrade.set(saved.grade)}
    saved=null;
  }
  lockNote.querySelector('button').addEventListener('click',function(){builderFile=null;unlock(false)});
  document.addEventListener('sm:builder-sent',function(event){builderFile=event.detail&&event.detail.file||null;if(builderFile)lock()});
  var fileList=document.getElementById('fileList');
  if(fileList)new MutationObserver(function(){if(locked&&!hasBuilderFile()){builderFile=null;unlock(true)}}).observe(fileList,{childList:true});
  window.addEventListener('sm:langchange',paintLock);
  window.SMProcessFrame.locked=function(){return locked};
  window.SMProcessFrame.lockLabel=function(){return lockWord('short')};
  relabel();
})();
