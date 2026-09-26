/* Styled and animated frames in Process for every showcase type (Workshop,
   Featured, Artwork Split). Style tiles replace the old checkbox: "None" keeps
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
  row.innerHTML='<div class="sqfx__styles process-frame__styles" role="radiogroup"></div>'+
    '<label class="field workshop-outline__color2"><span data-pfx="color2"></span><input type="color" id="outlineColor2" value="#8a62ff"></label>'+
    '<label class="field workshop-outline__speed"><span data-pfx="speed"></span><input type="range" id="outlineSpeed" min="1" max="4" step="1" value="1"></label>'+
    '<div class="process-frame__target" role="group"><span data-pw="target"></span><button type="button" data-target="squares" data-pw="each"></button><button type="button" data-target="strip" data-pw="whole"></button></div>'+
    '<p class="workshop-outline__fxnote" data-pw="note"></p>';
  host.prepend(row);
  var tiles=row.querySelector('.process-frame__styles'),color2=row.querySelector('#outlineColor2'),speed=row.querySelector('#outlineSpeed');
  var targetBox=row.querySelector('.process-frame__target');
  var style='neon',target='squares',loop=0,lastDraw=0;
  row.after(color.closest('label'));color.closest('label').after(width.closest('label'));

  function language(){return window.SMLang?.get?.()||document.documentElement.lang||'en'}
  function word(key){var i=Math.max(0,LANGS.indexOf(language()));return (WORDS[key]||[])[i]||(WORDS[key]||[])[0]||key}
  function mode(){return (window.state&&window.state.mode)||'workshop'}
  function current(){return toggle&&toggle.checked?style:'none'}
  function relabel(){
    var lang=language();
    row.querySelectorAll('[data-pfx]').forEach(function(node){node.textContent=api.t(node.dataset.pfx,lang)});
    row.querySelectorAll('[data-pw]').forEach(function(node){node.textContent=word(node.dataset.pw)});
    tiles.setAttribute('aria-label',api.t('frame',lang));
    tiles.replaceChildren();
    api.FRAME_STYLES.forEach(function(key){
      var button=document.createElement('button');button.type='button';button.className='sqfx__style';button.dataset.style=key;button.setAttribute('role','radio');
      var swatch=document.createElement('span');swatch.className='sqfx__swatch';swatch.setAttribute('aria-hidden','true');
      for(var i=0;i<3;i++)swatch.append(document.createElement('i'));
      var name=document.createElement('b');name.textContent=api.t(key,lang);button.append(swatch,name);
      if(api.isAnimatedFrame(key)){var tag=document.createElement('small');tag.textContent=api.t('beta',lang);button.append(tag)}
      button.addEventListener('click',function(){
        if(key==='none'){if(toggle)toggle.checked=false}
        else{style=key;if(toggle)toggle.checked=true}
        if(toggle)toggle.dispatchEvent(new Event('change',{bubbles:true}));
        sync();
      });
      tiles.append(button);
    });
    sync();
  }
  function sync(){
    var value=current(),on=value!=='none',animated=api.isAnimatedFrame(value);
    tiles.querySelectorAll('.sqfx__style').forEach(function(button){button.setAttribute('aria-checked',String(button.dataset.style===value))});
    host.classList.toggle('is-off',!on);
    row.querySelector('.workshop-outline__color2').hidden=!on||['double','comet','dashes'].indexOf(value)<0;
    row.querySelector('.workshop-outline__speed').hidden=!animated;
    row.querySelector('.workshop-outline__fxnote').hidden=!animated;
    color.closest('label').hidden=!on||value==='rgb';
    width.closest('label').hidden=!on;
    targetBox.hidden=!on||mode()==='featured';
    targetBox.querySelectorAll('button').forEach(function(button){button.setAttribute('aria-pressed',String(button.dataset.target===target))});
    redraw();
    document.dispatchEvent(new CustomEvent('sm:process-frame-change'));
  }
  function redraw(){if(typeof window.__wmRedraw==='function')window.__wmRedraw();animate()}
  function previewVisible(){var canvas=document.getElementById('wmCanvas');return !!(canvas&&canvas.offsetParent&&canvas.style.display!=='none')}
  // Redraw the preview ~30 times per second only while an animated frame is visible.
  function animate(){
    if(loop)return;
    (function tick(now){
      var active=api.isAnimatedFrame(current())&&!document.hidden&&previewVisible();
      if(!active){loop=0;return}
      if(!now||now-lastDraw>33){lastDraw=now||0;if(typeof window.__wmRedraw==='function')window.__wmRedraw()}
      loop=requestAnimationFrame(tick);
    })();
  }
  /* Final-file rectangles on the preview canvas (the canvas shows the whole source). */
  function rects(w,h){
    var m=mode();
    if(m==='featured'||target==='strip')return [[0,0,w,h]];
    if(m==='split'){var cut=Math.round(w*506/606);return [[0,0,cut,h],[cut,0,w-cut,h]]}
    return api.panelRects(w,h,'squares');
  }

  window.SMProcessFrame={
    options:function(){return {style:current(),color2:color2.value,speed:Number(speed.value)||1,target:target}},
    styleName:function(){var value=current();return value==='none'?'':api.t(value,language())},
    /* Called by the Process preview (app.js) instead of the plain stroke. */
    draw:function(ctx,w,h,stroke){
      var period=4;
      api.drawFrame(ctx,(performance.now()/1000%period)/period,{style:current(),color:color.value,color2:color2.value,width:stroke,speed:Number(speed.value)||1,target:target==='strip'||mode()!=='workshop'?'strip':'squares'},rects(w,h));
      return true;
    },
    refresh:sync
  };
  targetBox.addEventListener('click',function(event){var button=event.target.closest('[data-target]');if(!button)return;target=button.dataset.target;sync()});
  [color2,speed].forEach(function(node){node.addEventListener('input',sync);node.addEventListener('change',sync)});
  [width,color].forEach(function(node){if(node)node.addEventListener('input',function(){redraw()})});
  document.addEventListener('visibilitychange',animate);
  document.querySelectorAll('.mode').forEach(function(button){button.addEventListener('click',function(){setTimeout(sync,0)})});
  window.addEventListener('sm:langchange',relabel);
  relabel();
})();
