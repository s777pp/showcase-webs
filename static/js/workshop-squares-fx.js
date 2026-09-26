/* Frames and effects for the Workshop "5 squares" layout: live preview + controls.
   The server (smweb/square_fx.py) renders the final files with the same formulas,
   so keep both in sync. Everything is a function of u in [0,1) = position in one
   loop; every motion makes whole cycles per loop, so the GIFs loop seamlessly. */
(function(){
  'use strict';
  var W=750,H=150,SQUARE=150,TAU=Math.PI*2;
  var STATIC_FRAMES=['none','solid','double','corners','neon'],ANIMATED_FRAMES=['rgb','comet','pulse','dashes'];
  var EFFECTS=['none','petals','snow','rain','lightning','particle','stars','sparks','matrix','streaks'];
  var TEXTURE_URL='/static/assets/builder/effects/{n}.png?v=small-2',MATRIX_CHARS='0123456789ABCDEF';
  var PARTICLES=[];for(var i=0;i<74;i++)PARTICLES.push([(i*79%101)/100,(i*47%97)/96,1+i%4,i%3]);

  var COPY={
    en:{presets:'Quick looks',pr_neon:'Neon blue',pr_rgb:'RGB gamer',pr_sakura:'Sakura',pr_matrix:'Matrix',pr_space:'Space comets',pr_winter:'Winter',pr_minimal:'Minimal',title:'3 · Frame and effects',finish:'4 · Download',frame:'Frame',effect:'Effect',beta:'animated · beta',none:'None',solid:'Line',double:'Double',corners:'Corners',neon:'Neon',rgb:'RGB strip',comet:'Comets',pulse:'Neon pulse',dashes:'Running dashes',color:'Color',color2:'Second color',width:'Thickness',speed:'Speed',target:'Frame around',squares:'each square',strip:'the whole strip',noEffect:'No effect',petals:'Sakura petals',snow:'Real snow',rain:'Rain',lightning:'Lightning',particle:'Particle Flow',stars:'Starfield Drift',sparks:'Obsidian Sparks',matrix:'Digital Matrix',streaks:'Light Streaks',effectColor:'Effect color',density:'Density',opacity:'Opacity',note:'Animated frames and effects turn the result into five synchronized looping GIFs. FPS and clip length are set below.',style:'Style',processNote:'Animated outlines turn a still picture into five looping GIFs (4 s). Videos and GIFs keep their own length.'},
    ru:{presets:'Быстрые стили',pr_neon:'Синий неон',pr_rgb:'RGB-геймер',pr_sakura:'Сакура',pr_matrix:'Матрица',pr_space:'Космос',pr_winter:'Зима',pr_minimal:'Минимализм',title:'3 · Рамка и эффекты',finish:'4 · Скачай результат',frame:'Рамка',effect:'Эффект',beta:'анимация · бета',none:'Нет',solid:'Линия',double:'Двойная',corners:'Уголки',neon:'Неон',rgb:'RGB-лента',comet:'Кометы',pulse:'Пульс неона',dashes:'Бегущий пунктир',color:'Цвет',color2:'Второй цвет',width:'Толщина',speed:'Скорость',target:'Рамка вокруг',squares:'каждого квадрата',strip:'всей полосы',noEffect:'Без эффекта',petals:'Лепестки сакуры',snow:'Настоящий снег',rain:'Дождь',lightning:'Молнии',particle:'Поток частиц',stars:'Звёздный поток',sparks:'Искры',matrix:'Цифровая матрица',streaks:'Световые линии',effectColor:'Цвет эффекта',density:'Плотность',opacity:'Прозрачность',note:'Анимированные рамки и эффекты превращают результат в пять синхронных зацикленных GIF. FPS и длина задаются ниже.',style:'Стиль',processNote:'Анимированная обводка превращает картинку в пять зацикленных GIF (4 с). Видео и GIF сохраняют свою длину.'},
    de:{presets:'Schnelle Looks',pr_neon:'Neonblau',pr_rgb:'RGB-Gamer',pr_sakura:'Sakura',pr_matrix:'Matrix',pr_space:'Weltraum',pr_winter:'Winter',pr_minimal:'Minimal',title:'3 · Rahmen und Effekte',finish:'4 · Herunterladen',frame:'Rahmen',effect:'Effekt',beta:'animiert · Beta',none:'Keiner',solid:'Linie',double:'Doppelt',corners:'Ecken',neon:'Neon',rgb:'RGB-Band',comet:'Kometen',pulse:'Neon-Puls',dashes:'Laufende Striche',color:'Farbe',color2:'Zweite Farbe',width:'Stärke',speed:'Geschwindigkeit',target:'Rahmen um',squares:'jedes Quadrat',strip:'den ganzen Streifen',noEffect:'Kein Effekt',petals:'Sakura-Blüten',snow:'Echter Schnee',rain:'Regen',lightning:'Blitze',particle:'Partikelstrom',stars:'Sternenstrom',sparks:'Funken',matrix:'Digitale Matrix',streaks:'Lichtstreifen',effectColor:'Effektfarbe',density:'Dichte',opacity:'Deckkraft',note:'Animierte Rahmen und Effekte machen aus dem Ergebnis fünf synchrone Endlos-GIFs. FPS und Cliplänge stellst du unten ein.',style:'Stil',processNote:'Animierte Rahmen machen aus einem Standbild fünf Endlos-GIFs (4 s). Videos und GIFs behalten ihre Länge.'},
    tr:{presets:'Hazır görünümler',pr_neon:'Mavi neon',pr_rgb:'RGB oyuncu',pr_sakura:'Sakura',pr_matrix:'Matris',pr_space:'Uzay',pr_winter:'Kış',pr_minimal:'Minimal',title:'3 · Çerçeve ve efektler',finish:'4 · İndir',frame:'Çerçeve',effect:'Efekt',beta:'animasyonlu · beta',none:'Yok',solid:'Çizgi',double:'Çift',corners:'Köşeler',neon:'Neon',rgb:'RGB şerit',comet:'Kuyruklu yıldızlar',pulse:'Neon nabız',dashes:'Akan kesikli çizgi',color:'Renk',color2:'İkinci renk',width:'Kalınlık',speed:'Hız',target:'Çerçeve',squares:'her kare için',strip:'tüm şerit için',noEffect:'Efekt yok',petals:'Sakura yaprakları',snow:'Gerçek kar',rain:'Yağmur',lightning:'Şimşek',particle:'Parçacık akışı',stars:'Yıldız akışı',sparks:'Kıvılcımlar',matrix:'Dijital matris',streaks:'Işık çizgileri',effectColor:'Efekt rengi',density:'Yoğunluk',opacity:'Opaklık',note:'Animasyonlu çerçeve ve efektler sonucu beş senkron, döngülü GIF’e dönüştürür. FPS ve süre aşağıda ayarlanır.',style:'Stil',processNote:'Animasyonlu çerçeve durağan görseli beş döngülü GIF’e (4 sn) dönüştürür. Video ve GIF’ler kendi sürelerini korur.'},
    fr:{presets:'Styles rapides',pr_neon:'Néon bleu',pr_rgb:'Gamer RGB',pr_sakura:'Sakura',pr_matrix:'Matrice',pr_space:'Espace',pr_winter:'Hiver',pr_minimal:'Minimal',title:'3 · Cadre et effets',finish:'4 · Télécharger',frame:'Cadre',effect:'Effet',beta:'animé · bêta',none:'Aucun',solid:'Ligne',double:'Double',corners:'Coins',neon:'Néon',rgb:'Bande RGB',comet:'Comètes',pulse:'Pulsation néon',dashes:'Pointillés animés',color:'Couleur',color2:'Seconde couleur',width:'Épaisseur',speed:'Vitesse',target:'Cadre autour de',squares:'chaque carré',strip:'toute la bande',noEffect:'Aucun effet',petals:'Pétales de sakura',snow:'Neige réaliste',rain:'Pluie',lightning:'Éclairs',particle:'Flux de particules',stars:'Dérive stellaire',sparks:'Étincelles',matrix:'Matrice numérique',streaks:'Traînées lumineuses',effectColor:'Couleur de l’effet',density:'Densité',opacity:'Opacité',note:'Les cadres et effets animés transforment le résultat en cinq GIF synchronisés en boucle. Les FPS et la durée se règlent plus bas.',style:'Style',processNote:'Les contours animés transforment une image fixe en cinq GIF en boucle (4 s). Les vidéos et GIF gardent leur durée.'},
    uk:{presets:'Швидкі стилі',pr_neon:'Синій неон',pr_rgb:'RGB-геймер',pr_sakura:'Сакура',pr_matrix:'Матриця',pr_space:'Космос',pr_winter:'Зима',pr_minimal:'Мінімалізм',title:'3 · Рамка та ефекти',finish:'4 · Завантаж результат',frame:'Рамка',effect:'Ефект',beta:'анімація · бета',none:'Немає',solid:'Лінія',double:'Подвійна',corners:'Кутики',neon:'Неон',rgb:'RGB-стрічка',comet:'Комети',pulse:'Пульс неону',dashes:'Біжучий пунктир',color:'Колір',color2:'Другий колір',width:'Товщина',speed:'Швидкість',target:'Рамка навколо',squares:'кожного квадрата',strip:'всієї смуги',noEffect:'Без ефекту',petals:'Пелюстки сакури',snow:'Справжній сніг',rain:'Дощ',lightning:'Блискавки',particle:'Потік частинок',stars:'Зоряний потік',sparks:'Іскри',matrix:'Цифрова матриця',streaks:'Світлові смуги',effectColor:'Колір ефекту',density:'Щільність',opacity:'Прозорість',note:'Анімовані рамки та ефекти перетворюють результат на п’ять синхронних зациклених GIF. FPS і тривалість задаються нижче.',style:'Стиль',processNote:'Анімована обводка перетворює зображення на п’ять зациклених GIF (4 с). Відео та GIF зберігають свою тривалість.'},
    es:{presets:'Estilos rápidos',pr_neon:'Neón azul',pr_rgb:'Gamer RGB',pr_sakura:'Sakura',pr_matrix:'Matrix',pr_space:'Espacio',pr_winter:'Invierno',pr_minimal:'Minimalista',title:'3 · Marco y efectos',finish:'4 · Descarga',frame:'Marco',effect:'Efecto',beta:'animado · beta',none:'Ninguno',solid:'Línea',double:'Doble',corners:'Esquinas',neon:'Neón',rgb:'Tira RGB',comet:'Cometas',pulse:'Pulso de neón',dashes:'Trazos en movimiento',color:'Color',color2:'Segundo color',width:'Grosor',speed:'Velocidad',target:'Marco alrededor de',squares:'cada cuadrado',strip:'toda la tira',noEffect:'Sin efecto',petals:'Pétalos de sakura',snow:'Nieve realista',rain:'Lluvia',lightning:'Relámpagos',particle:'Flujo de partículas',stars:'Deriva estelar',sparks:'Chispas',matrix:'Matriz digital',streaks:'Trazos de luz',effectColor:'Color del efecto',density:'Densidad',opacity:'Opacidad',note:'Los marcos y efectos animados convierten el resultado en cinco GIF sincronizados en bucle. Los FPS y la duración se ajustan abajo.',style:'Estilo',processNote:'Los contornos animados convierten una imagen fija en cinco GIF en bucle (4 s). Los vídeos y GIF mantienen su duración.'},
    pt:{presets:'Estilos rápidos',pr_neon:'Neon azul',pr_rgb:'Gamer RGB',pr_sakura:'Sakura',pr_matrix:'Matrix',pr_space:'Espaço',pr_winter:'Inverno',pr_minimal:'Minimalista',title:'3 · Moldura e efeitos',finish:'4 · Baixar',frame:'Moldura',effect:'Efeito',beta:'animado · beta',none:'Nenhuma',solid:'Linha',double:'Dupla',corners:'Cantos',neon:'Neon',rgb:'Fita RGB',comet:'Cometas',pulse:'Pulso neon',dashes:'Tracejado em movimento',color:'Cor',color2:'Segunda cor',width:'Espessura',speed:'Velocidade',target:'Moldura em volta de',squares:'cada quadrado',strip:'toda a faixa',noEffect:'Sem efeito',petals:'Pétalas de sakura',snow:'Neve realista',rain:'Chuva',lightning:'Relâmpagos',particle:'Fluxo de partículas',stars:'Deriva estelar',sparks:'Faíscas',matrix:'Matriz digital',streaks:'Rastros de luz',effectColor:'Cor do efeito',density:'Densidade',opacity:'Opacidade',note:'Molduras e efeitos animados transformam o resultado em cinco GIFs sincronizados em loop. FPS e duração ficam abaixo.',style:'Estilo',processNote:'Contornos animados transformam uma imagem estática em cinco GIFs em loop (4 s). Vídeos e GIFs mantêm a duração.'}
  };
  /* One-click combinations of the controls below (frame + effect). */
  var PRESETS=[
    ['neon',{style:'neon',color:'#51d7ff',width:3},{type:'none'}],
    ['rgb',{style:'rgb',width:3,speed:1},{type:'none'}],
    ['sakura',{style:'solid',color:'#ffc4dc',width:2},{type:'petals',color:'#ff9fc8',density:100,opacity:90}],
    ['matrix',{style:'dashes',color:'#39ff88',color2:'#0d3b22',width:2,speed:1},{type:'matrix',color:'#39ff88',density:80,opacity:70}],
    ['space',{style:'comet',color:'#8de9ff',color2:'#8a62ff',width:3,speed:1},{type:'stars',color:'#cfe8ff',density:100,opacity:85}],
    ['winter',{style:'double',color:'#e6f7ff',color2:'#7fb8ff',width:3},{type:'snow',color:'#ffffff',density:100,opacity:90}],
    ['minimal',{style:'corners',color:'#ffffff',width:2},{type:'none'}]
  ];
  function applyPreset(fx,key){
    var preset=PRESETS.filter(function(p){return p[0]===key})[0];if(!preset)return;
    var base=defaults();
    fx.frame=Object.assign(base.frame,{target:fx.frame.target||'squares'},preset[1]);
    fx.effect=Object.assign(base.effect,preset[2]);
  }
  function t(key,language){return (COPY[language]||COPY.en)[key]||COPY.en[key]||key}

  function defaults(){return {frame:{style:'none',color:'#8de9ff',color2:'#8a62ff',width:3,speed:1,target:'squares'},effect:{type:'none',color:'#ff9fc8',speed:100,density:100,opacity:90}}}
  function isEmpty(fx){return fx.frame.style==='none'&&fx.effect.type==='none'}
  function isAnimated(fx){return ANIMATED_FRAMES.indexOf(fx.frame.style)>=0||fx.effect.type!=='none'}
  function rgb(hex){return [parseInt(hex.slice(1,3),16),parseInt(hex.slice(3,5),16),parseInt(hex.slice(5,7),16)]}
  function mix(a,b,k){return [0,1,2].map(function(i){return Math.round(a[i]+(b[i]-a[i])*k)})}
  function rgba(c,a){return 'rgba('+c[0]+','+c[1]+','+c[2]+','+(a==null?1:a)+')'}
  function mod(a,b){return ((a%b)+b)%b}

  // ---------------------------------------------------------------- effects
  var textures={},tinted={};
  function texture(name,color,tileWidth){
    var image=textures[name];
    if(!image){image=new Image();image.src=TEXTURE_URL.replace('{n}',name);image.onload=function(){tinted={}};textures[name]=image}
    if(!image.complete||!image.naturalWidth)return null;
    var key=name+'|'+color+'|'+tileWidth;if(tinted[key])return tinted[key];
    var canvas=document.createElement('canvas');canvas.width=tileWidth;canvas.height=Math.max(1,Math.round(tileWidth*image.naturalHeight/image.naturalWidth));
    var paint=canvas.getContext('2d');paint.drawImage(image,0,0,canvas.width,canvas.height);paint.globalCompositeOperation='source-atop';paint.globalAlpha=.48;paint.fillStyle=color;paint.fillRect(0,0,canvas.width,canvas.height);paint.globalCompositeOperation='source-over';paint.globalAlpha=.42;paint.drawImage(image,0,0,canvas.width,canvas.height);
    tinted[key]=canvas;return canvas;
  }
  function tile(ctx,tex,offsetX,offsetY,alpha){
    if(alpha<=0)return;ctx.save();ctx.globalAlpha=alpha;var tw=tex.width,th=tex.height,sx=Math.floor(mod(offsetX,tw))-tw,sy=Math.floor(mod(offsetY,th))-th;
    for(var x=sx;x<W;x+=tw)for(var y=sy;y<H;y+=th)ctx.drawImage(tex,x,y);ctx.restore();
  }
  function drawEffect(ctx,u,e){
    var kind=e.type;if(kind==='none')return;
    var speed=e.speed/100,density=e.density/100,opacity=e.opacity/100,color=rgb(e.color);
    if(kind==='petals'||kind==='snow'||kind==='rain'){
      var rain=kind==='rain',passes=density>1.35?3:(density>.65?2:1),base=Math.max(1,Math.round(speed*(rain?3:1)));
      for(var p=0;p<passes;p++){var tex=texture(kind,e.color,Math.round((rain?478:531)*(1+p*.14)));if(!tex)continue;var th=tex.height,offsetY=mod(u*(base+p)*th+p*th*.47,th),drift=rain?-W*.04:(.055*Math.sin(TAU*(u+p*.33))-.09)*W;tile(ctx,tex,drift,offsetY,opacity*Math.min(1,.42+density*.22-p*.08))}
      return;
    }
    if(kind==='lightning'){
      var cycles=Math.max(1,Math.round(speed)),pulse=mod(u*cycles,1)*3.7,flash=pulse<.12?1:(pulse<.22?.38:(pulse>.36&&pulse<.43?.68:0));if(!flash)return;
      var bolt=texture('lightning',e.color,765);if(!bolt)return;ctx.save();ctx.globalCompositeOperation='lighter';ctx.shadowColor=e.color;ctx.shadowBlur=6;tile(ctx,bolt,W*.013,H*.017,opacity*flash*Math.min(1,.48+density*.34));ctx.restore();return;
    }
    var count=Math.max(8,Math.min(PARTICLES.length,Math.round(PARTICLES.length*density)));
    ctx.save();ctx.shadowColor=e.color;ctx.shadowBlur=kind==='stars'?7:(kind==='sparks'?6:4);
    PARTICLES.slice(0,kind==='streaks'?Math.min(count,30):(kind==='matrix'?Math.min(count,44):count)).forEach(function(q,index){
      var px=q[0],py=q[1],radius=q[2],cycles=Math.max(1,Math.round((1+q[3])*speed)),x,y,alpha=1,r;
      if(kind==='particle'||kind==='sparks'){var dir=kind==='sparks'?-1:1;y=mod(py+dir*cycles*u,1)*H;x=(px+.02*Math.sin(TAU*(u+py)))*W;if(kind==='sparks')alpha=.55+.45*(.5+.5*Math.cos(TAU*(cycles*u+px*3)));r=radius*(kind==='sparks'?.7:.9);ctx.fillStyle=rgba(color,opacity*alpha);ctx.beginPath();ctx.arc(x,y,r,0,TAU);ctx.fill()}
      else if(kind==='stars'){x=mod(px+u*Math.max(1,Math.round(speed)),1)*W;y=py*H;alpha=.35+.65*(.5+.5*Math.cos(TAU*(2*u+px*7)));ctx.fillStyle=rgba(color,opacity*alpha);ctx.beginPath();ctx.arc(x,y,radius*.6,0,TAU);ctx.fill()}
      else if(kind==='streaks'){x=mod(px+cycles*u,1)*W;y=py*H;ctx.strokeStyle=rgba(color,opacity);ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+42,y-27);ctx.stroke()}
      else if(kind==='matrix'){x=px*W;y=mod(py+cycles*u,1)*H;ctx.fillStyle=rgba(color,opacity);ctx.font='12px monospace';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(MATRIX_CHARS[(index*17+Math.floor(u*12))%MATRIX_CHARS.length],x,y)}
    });
    ctx.restore();
  }

  // ----------------------------------------------------------------- frames
  /* Five Workshop panels (or the whole area) of a w x h surface; matches square_fx._rects. */
  function panelRects(w,h,target){if(target==='strip')return [[0,0,w,h]];var out=[];for(var i=0;i<5;i++){var a=Math.floor(i*w/5),b=Math.floor((i+1)*w/5);out.push([a,0,b-a,h])}return out}
  function rects(target){return panelRects(W,H,target)}
  function perimeter(rect,width){var half=width/2,x0=rect[0]+half,y0=rect[1]+half,x1=rect[0]+rect[2]-half,y1=rect[1]+rect[3]-half;return {corners:[[x0,y0],[x1,y0],[x1,y1],[x0,y1]],length:2*((x1-x0)+(y1-y0))}}
  function point(path,distance){distance=mod(distance,path.length);for(var i=0;i<4;i++){var a=path.corners[i],b=path.corners[(i+1)%4],side=Math.abs(b[0]-a[0])+Math.abs(b[1]-a[1]);if(distance<=side){var k=side?distance/side:0;return [a[0]+(b[0]-a[0])*k,a[1]+(b[1]-a[1])*k]}distance-=side}return path.corners[0]}
  function segments(ctx,rect,width,colorAt){var path=perimeter(rect,width),count=Math.max(8,Math.min(600,Math.floor(path.length/2)));ctx.lineWidth=width;ctx.lineCap='butt';for(var i=0;i<count;i++){var position=i/count,style=colorAt(position,position*path.length);if(!style)continue;var a=point(path,position*path.length),b=point(path,(i+1)/count*path.length);ctx.strokeStyle=style;ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke()}return path}
  function hsv(h){var i=Math.floor(h*6),f=h*6-i,q=1-f,values=[[1,f,0],[q,1,0],[0,1,f],[0,q,1],[f,0,1],[1,0,q]][mod(i,6)];return values.map(function(v){return Math.round(v*255)})}
  function drawFrame(ctx,u,f,list){
    var style=f.style;if(style==='none')return;
    var width=f.width,color=rgb(f.color),color2=rgb(f.color2||'#8a62ff'),cycles=f.speed||1;list=list||rects(f.target);
    ctx.save();
    if(style==='solid'||style==='double'||style==='neon'||style==='pulse'){
      var level=style==='pulse'?.5+.5*Math.cos(TAU*cycles*u):1,core=(style==='neon'||style==='pulse')?mix(color,[255,255,255],.35):color;
      list.forEach(function(r){
        if(style==='neon'||style==='pulse'){ctx.save();ctx.shadowColor=rgba(color,style==='pulse'?.25+.75*level:1);ctx.shadowBlur=Math.max(4,width*3.4);ctx.strokeStyle=rgba(color,.9);ctx.lineWidth=width+2;ctx.strokeRect(r[0]+(width+2)/2,r[1]+(width+2)/2,r[2]-width-2,r[3]-width-2);ctx.restore()}
        ctx.strokeStyle=rgba(core,style==='pulse'?.55+.45*level:1);ctx.lineWidth=width;ctx.strokeRect(r[0]+width/2,r[1]+width/2,r[2]-width,r[3]-width);
        if(style==='double'){var gap=width*2+3,inner=Math.max(1,width-1);ctx.strokeStyle=rgba(color2);ctx.lineWidth=inner;ctx.strokeRect(r[0]+gap+inner/2,r[1]+gap+inner/2,r[2]-2*gap-inner,r[3]-2*gap-inner)}
      });
    }else if(style==='corners'){
      ctx.strokeStyle=rgba(color);ctx.lineWidth=width;ctx.lineCap='butt';
      list.forEach(function(r){var size=Math.floor(Math.min(r[2],r[3])*.22),h=width/2,x0=r[0],y0=r[1],x1=r[0]+r[2],y1=r[1]+r[3];[[x0,y0,1,1],[x1,y0,-1,1],[x0,y1,1,-1],[x1,y1,-1,-1]].forEach(function(c){ctx.beginPath();ctx.moveTo(c[0]+c[2]*size,c[1]+c[3]*h);ctx.lineTo(c[0]+c[2]*h,c[1]+c[3]*h);ctx.lineTo(c[0]+c[2]*h,c[1]+c[3]*size);ctx.stroke()})});
    }else{
      ctx.shadowBlur=Math.max(4,width*(style==='dashes'?2:3.2));
      list.forEach(function(r,index){
        var shift=f.target==='squares'?index*.2:0,path;
        if(style==='rgb'){path=segments(ctx,r,width,function(position){var c=hsv(mod(position+shift-cycles*u,1));ctx.shadowColor=rgba(c);return rgba(c)})}
        else if(style==='comet'){
          var heads=[mod(cycles*u+shift,1),mod(cycles*u+shift+.5,1)],tail=.34;ctx.shadowColor=rgba(color);
          path=segments(ctx,r,width,function(position){var d=Math.min(mod(heads[0]-position,1),mod(heads[1]-position,1));if(d>tail)return rgba(mix(color,[0,0,0],.45),70/255);var s=Math.pow(1-d/tail,.85),tone=mix(color2,color,s);if(d<.03)tone=mix(tone,[255,255,255],.7);return rgba(tone,(90+165*s)/255)});
          ctx.fillStyle='#fff';heads.forEach(function(head){var p=point(path,head*path.length);ctx.beginPath();ctx.arc(p[0],p[1],width*.9+1.5,0,TAU);ctx.fill()});
        }else{var offset=u*cycles*14*6;ctx.shadowColor=rgba(color);segments(ctx,r,width,function(_p,distance){return mod(distance-offset,14)<8?rgba(color):rgba(color2,90/255)})}
      });
    }
    ctx.restore();
  }

  /* Draw the overlay (effect below, frame on top) for loop position u into a 750x150 canvas. */
  function render(ctx,u,fx){ctx.clearRect(0,0,W,H);drawEffect(ctx,mod(u,1),fx.effect);drawFrame(ctx,mod(u,1),fx.frame)}

  // --------------------------------------------------------------- controls
  function el(tag,cls,text){var node=document.createElement(tag);if(cls)node.className=cls;if(text!=null)node.textContent=text;return node}
  function range(label,value,min,max,step,suffix,onInput){var wrap=el('label','sqfx__range'),name=el('span',null,label),out=el('output',null,value+suffix),input=el('input');input.type='range';input.min=min;input.max=max;input.step=step;input.value=value;input.oninput=function(){out.textContent=this.value+suffix;onInput(Number(this.value))};wrap.append(name,out,input);return wrap}
  function colorInput(label,value,onInput){var wrap=el('label','sqfx__color'),name=el('span',null,label),input=el('input');input.type='color';input.value=value;input.oninput=function(){onInput(this.value)};wrap.append(input,name);return wrap}

  function mountControls(host,fx,language,onChange){
    host.replaceChildren();
    var frame=fx.frame,effect=fx.effect,animated=ANIMATED_FRAMES.indexOf(frame.style)>=0;
    function change(){onChange();mountControls(host,fx,language,onChange)}
    host.append(el('p','sqfx__label',t('presets',language)));
    var quick=el('div','sqfx__presets');quick.setAttribute('data-no-translate','');
    PRESETS.forEach(function(preset){
      var button=el('button','sqfx__preset',t('pr_'+preset[0],language));button.type='button';button.dataset.preset=preset[0];
      button.onclick=function(){applyPreset(fx,preset[0]);change()};quick.append(button);
    });
    host.append(quick);
    host.append(el('p','sqfx__label',t('frame',language)));
    var styles=el('div','sqfx__styles');styles.setAttribute('role','radiogroup');styles.setAttribute('aria-label',t('frame',language));
    STATIC_FRAMES.concat(ANIMATED_FRAMES).forEach(function(style){
      var button=el('button','sqfx__style');button.type='button';button.dataset.style=style;button.setAttribute('role','radio');button.setAttribute('aria-checked',String(frame.style===style));
      var swatch=el('span','sqfx__swatch');swatch.setAttribute('aria-hidden','true');for(var i=0;i<3;i++)swatch.append(el('i'));
      button.append(swatch,el('b',null,t(style,language)));if(ANIMATED_FRAMES.indexOf(style)>=0)button.append(el('small',null,t('beta',language)));
      button.onclick=function(){frame.style=style;change()};styles.append(button);
    });
    host.append(styles);
    if(frame.style!=='none'){
      var row=el('div','sqfx__grid');
      if(frame.style!=='rgb')row.append(colorInput(t('color',language),frame.color,function(v){frame.color=v;onChange()}));
      if(['double','comet','dashes'].indexOf(frame.style)>=0)row.append(colorInput(t('color2',language),frame.color2,function(v){frame.color2=v;onChange()}));
      row.append(range(t('width',language),frame.width,1,10,1,' px',function(v){frame.width=v;onChange()}));
      if(animated)row.append(range(t('speed',language),frame.speed,1,4,1,'×',function(v){frame.speed=v;onChange()}));
      host.append(row);
      var target=el('div','sqfx__target');target.append(el('span',null,t('target',language)));
      ['squares','strip'].forEach(function(key){var b=el('button',null,t(key,language));b.type='button';b.setAttribute('aria-pressed',String(frame.target===key));b.onclick=function(){frame.target=key;change()};target.append(b)});
      host.append(target);
    }
    host.append(el('p','sqfx__label',t('effect',language)));
    var select=el('select','sqfx__select');select.setAttribute('aria-label',t('effect',language));
    EFFECTS.forEach(function(kind){var option=el('option',null,kind==='none'?t('noEffect',language):t(kind,language));option.value=kind;option.selected=effect.type===kind;select.append(option)});
    select.onchange=function(){effect.type=this.value;change()};host.append(select);
    if(effect.type!=='none'){
      var grid=el('div','sqfx__grid');
      grid.append(colorInput(t('effectColor',language),effect.color,function(v){effect.color=v;onChange()}));
      grid.append(range(t('speed',language),effect.speed,50,300,10,'%',function(v){effect.speed=v;onChange()}));
      grid.append(range(t('density',language),effect.density,25,200,5,'%',function(v){effect.density=v;onChange()}));
      grid.append(range(t('opacity',language),effect.opacity,10,100,5,'%',function(v){effect.opacity=v;onChange()}));
      host.append(grid);
    }
    if(isAnimated(fx))host.append(el('p','sqfx__note',t('note',language)));
  }

  /* Shared with Process (Workshop outline) and the Builder frame layer:
     drawFrame(ctx, u, {style,color,color2,width,speed,target}, rects) on any surface. */
  window.SMSquaresFx={COPY:COPY,t:t,PRESETS:PRESETS,applyPreset:applyPreset,defaults:defaults,isEmpty:isEmpty,isAnimated:isAnimated,render:render,mountControls:mountControls,W:W,H:H,
    FRAME_STYLES:STATIC_FRAMES.concat(ANIMATED_FRAMES),ANIMATED_FRAMES:ANIMATED_FRAMES,panelRects:panelRects,
    drawFrame:function(ctx,u,frame,list){ctx.save();drawFrame(ctx,mod(u,1),frame,list);ctx.restore()},
    isAnimatedFrame:function(style){return ANIMATED_FRAMES.indexOf(style)>=0}};
})();
