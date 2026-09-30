/* Frames and effects for the Workshop "5 squares" layout: live preview + controls.
   The server (smweb/square_fx.py) renders the final files with the same formulas,
   so keep both in sync. Everything is a function of u in [0,1) = position in one
   loop; every motion makes whole cycles per loop, so the GIFs loop seamlessly. */
(function(){
  'use strict';
  var W=750,H=150,SQUARE=150,TAU=Math.PI*2;
  var STATIC_FRAMES=['none','solid','double','corners','neon'],ANIMATED_FRAMES=['rgb','comet','pulse','dashes','shimmer','grain'],FRAME_SHAPES=['rect','bevel','notch'];
  var EFFECTS=['none','petals','snow','rain','lightning','particle','stars','sparks','matrix','streaks'];
  var TEXTURE_URL='/static/assets/builder/effects/{n}.png?v=small-2',MATRIX_CHARS='0123456789ABCDEF';
  var PARTICLES=[];for(var i=0;i<74;i++)PARTICLES.push([(i*79%101)/100,(i*47%97)/96,1+i%4,i%3]);

  var COPY={
    en:{anim2:"animation 2",anim1:"animation 1",animation:"Animation",shape_blade:"Blades",shape_circuit:"Circuit",shape_arcs:"Arcs",shape_bend:"Bend",shape_wing:"Wings",shape_slash:"Slashes",shape_twin:"Twin lines",shape_bastion:"Bastion",shape_crown:"Crown",shape_pillars:"Pillars",shimmer:"Shimmer",grain:"Grain",shape:"Shape",plate:"Dark plate",shape_rect:"Classic",shape_bevel:"Bevel",shape_tech:"Tech",shape_notch:"Notches",shape_hud:"HUD",shape_diamond:"Diamonds",shape_rails:"Rails",shape_brackets:"Brackets",pr_hud:"HUD shimmer",pr_cyber:"Cyber grain",presets:'Quick looks',pr_neon:'Neon blue',pr_rgb:'RGB gamer',pr_sakura:'Sakura',pr_matrix:'Matrix',pr_space:'Space comets',pr_winter:'Winter',pr_minimal:'Minimal',title:'3 · Frame and effects',finish:'4 · Download',frame:'Frame',effect:'Effect',beta:'animated',none:'None',solid:'Line',double:'Double',corners:'Corners',neon:'Neon',rgb:'RGB strip',comet:'Comets',pulse:'Neon pulse',dashes:'Running dashes',color:'Color',color2:'Second color',width:'Thickness',speed:'Speed',target:'Frame around',squares:'each square',strip:'the whole strip',noEffect:'No effect',petals:'Sakura petals',snow:'Real snow',rain:'Rain',lightning:'Lightning',particle:'Particle Flow',stars:'Starfield Drift',sparks:'Obsidian Sparks',matrix:'Digital Matrix',streaks:'Light Streaks',effectColor:'Effect color',density:'Density',opacity:'Opacity',note:'Animated frames and effects turn the result into five synchronized looping GIFs. FPS and clip length are set below.',style:'Style',processNote:'Animated outlines turn a still picture into five looping GIFs (4 s). Videos and GIFs keep their own length.'},
    ru:{anim2:"анимация 2",anim1:"анимация 1",animation:"Анимация",shape_blade:"Клинки",shape_circuit:"Схема",shape_arcs:"Дуги",shape_bend:"Изгиб",shape_wing:"Крылья",shape_slash:"Срезы",shape_twin:"Две линии",shape_bastion:"Бастион",shape_crown:"Корона",shape_pillars:"Колонны",shimmer:"Переливы",grain:"Зерно",shape:"Форма",plate:"Тёмная подложка",shape_rect:"Классика",shape_bevel:"Скосы",shape_tech:"Техно",shape_notch:"Выемки",shape_hud:"HUD",shape_diamond:"Ромбы",shape_rails:"Планки",shape_brackets:"Скобки",pr_hud:"HUD с бликом",pr_cyber:"Кибер-зерно",presets:'Быстрые стили',pr_neon:'Синий неон',pr_rgb:'RGB-геймер',pr_sakura:'Сакура',pr_matrix:'Матрица',pr_space:'Космос',pr_winter:'Зима',pr_minimal:'Минимализм',title:'3 · Рамка и эффекты',finish:'4 · Скачай результат',frame:'Рамка',effect:'Эффект',beta:'анимация',none:'Нет',solid:'Линия',double:'Двойная',corners:'Уголки',neon:'Неон',rgb:'RGB-лента',comet:'Кометы',pulse:'Пульс неона',dashes:'Бегущий пунктир',color:'Цвет',color2:'Второй цвет',width:'Толщина',speed:'Скорость',target:'Рамка вокруг',squares:'каждого квадрата',strip:'всей полосы',noEffect:'Без эффекта',petals:'Лепестки сакуры',snow:'Настоящий снег',rain:'Дождь',lightning:'Молнии',particle:'Поток частиц',stars:'Звёздный поток',sparks:'Искры',matrix:'Цифровая матрица',streaks:'Световые линии',effectColor:'Цвет эффекта',density:'Плотность',opacity:'Прозрачность',note:'Анимированные рамки и эффекты превращают результат в пять синхронных зацикленных GIF. FPS и длина задаются ниже.',style:'Стиль',processNote:'Анимированная обводка превращает картинку в пять зацикленных GIF (4 с). Видео и GIF сохраняют свою длину.'},
    de:{anim2:"Animation 2",anim1:"Animation 1",animation:"Animation",shape_blade:"Klingen",shape_circuit:"Platine",shape_arcs:"Bögen",shape_bend:"Knick",shape_wing:"Flügel",shape_slash:"Schnitte",shape_twin:"Doppellinie",shape_bastion:"Bastion",shape_crown:"Krone",shape_pillars:"Säulen",shimmer:"Schimmer",grain:"Körnung",shape:"Form",plate:"Dunkle Fläche",shape_rect:"Klassisch",shape_bevel:"Abgeschrägt",shape_tech:"Tech",shape_notch:"Kerben",shape_hud:"HUD",shape_diamond:"Rauten",shape_rails:"Leisten",shape_brackets:"Klammern",pr_hud:"HUD-Schimmer",pr_cyber:"Cyber-Korn",presets:'Schnelle Looks',pr_neon:'Neonblau',pr_rgb:'RGB-Gamer',pr_sakura:'Sakura',pr_matrix:'Matrix',pr_space:'Weltraum',pr_winter:'Winter',pr_minimal:'Minimal',title:'3 · Rahmen und Effekte',finish:'4 · Herunterladen',frame:'Rahmen',effect:'Effekt',beta:'animiert',none:'Keiner',solid:'Linie',double:'Doppelt',corners:'Ecken',neon:'Neon',rgb:'RGB-Band',comet:'Kometen',pulse:'Neon-Puls',dashes:'Laufende Striche',color:'Farbe',color2:'Zweite Farbe',width:'Stärke',speed:'Geschwindigkeit',target:'Rahmen um',squares:'jedes Quadrat',strip:'den ganzen Streifen',noEffect:'Kein Effekt',petals:'Sakura-Blüten',snow:'Echter Schnee',rain:'Regen',lightning:'Blitze',particle:'Partikelstrom',stars:'Sternenstrom',sparks:'Funken',matrix:'Digitale Matrix',streaks:'Lichtstreifen',effectColor:'Effektfarbe',density:'Dichte',opacity:'Deckkraft',note:'Animierte Rahmen und Effekte machen aus dem Ergebnis fünf synchrone Endlos-GIFs. FPS und Cliplänge stellst du unten ein.',style:'Stil',processNote:'Animierte Rahmen machen aus einem Standbild fünf Endlos-GIFs (4 s). Videos und GIFs behalten ihre Länge.'},
    tr:{anim2:"animasyon 2",anim1:"animasyon 1",animation:"Animasyon",shape_blade:"Bıçaklar",shape_circuit:"Devre",shape_arcs:"Yaylar",shape_bend:"Kıvrım",shape_wing:"Kanatlar",shape_slash:"Kesikler",shape_twin:"İkiz çizgi",shape_bastion:"Burç",shape_crown:"Taç",shape_pillars:"Sütunlar",shimmer:"Parıltı",grain:"Tanecik",shape:"Şekil",plate:"Koyu zemin",shape_rect:"Klasik",shape_bevel:"Pahlı",shape_tech:"Tekno",shape_notch:"Çentikler",shape_hud:"HUD",shape_diamond:"Elmaslar",shape_rails:"Raylar",shape_brackets:"Ayraçlar",pr_hud:"HUD parıltısı",pr_cyber:"Siber tanecik",presets:'Hazır görünümler',pr_neon:'Mavi neon',pr_rgb:'RGB oyuncu',pr_sakura:'Sakura',pr_matrix:'Matris',pr_space:'Uzay',pr_winter:'Kış',pr_minimal:'Minimal',title:'3 · Çerçeve ve efektler',finish:'4 · İndir',frame:'Çerçeve',effect:'Efekt',beta:'animasyonlu',none:'Yok',solid:'Çizgi',double:'Çift',corners:'Köşeler',neon:'Neon',rgb:'RGB şerit',comet:'Kuyruklu yıldızlar',pulse:'Neon nabız',dashes:'Akan kesikli çizgi',color:'Renk',color2:'İkinci renk',width:'Kalınlık',speed:'Hız',target:'Çerçeve',squares:'her kare için',strip:'tüm şerit için',noEffect:'Efekt yok',petals:'Sakura yaprakları',snow:'Gerçek kar',rain:'Yağmur',lightning:'Şimşek',particle:'Parçacık akışı',stars:'Yıldız akışı',sparks:'Kıvılcımlar',matrix:'Dijital matris',streaks:'Işık çizgileri',effectColor:'Efekt rengi',density:'Yoğunluk',opacity:'Opaklık',note:'Animasyonlu çerçeve ve efektler sonucu beş senkron, döngülü GIF’e dönüştürür. FPS ve süre aşağıda ayarlanır.',style:'Stil',processNote:'Animasyonlu çerçeve durağan görseli beş döngülü GIF’e (4 sn) dönüştürür. Video ve GIF’ler kendi sürelerini korur.'},
    fr:{anim2:"animation 2",anim1:"animation 1",animation:"Animation",shape_blade:"Lames",shape_circuit:"Circuit",shape_arcs:"Arcs",shape_bend:"Coude",shape_wing:"Ailes",shape_slash:"Entailles",shape_twin:"Double ligne",shape_bastion:"Bastion",shape_crown:"Couronne",shape_pillars:"Piliers",shimmer:"Reflets",grain:"Grain",shape:"Forme",plate:"Fond sombre",shape_rect:"Classique",shape_bevel:"Biseauté",shape_tech:"Tech",shape_notch:"Encoches",shape_hud:"HUD",shape_diamond:"Losanges",shape_rails:"Rails",shape_brackets:"Crochets",pr_hud:"HUD scintillant",pr_cyber:"Grain cyber",presets:'Styles rapides',pr_neon:'Néon bleu',pr_rgb:'Gamer RGB',pr_sakura:'Sakura',pr_matrix:'Matrice',pr_space:'Espace',pr_winter:'Hiver',pr_minimal:'Minimal',title:'3 · Cadre et effets',finish:'4 · Télécharger',frame:'Cadre',effect:'Effet',beta:'animé',none:'Aucun',solid:'Ligne',double:'Double',corners:'Coins',neon:'Néon',rgb:'Bande RGB',comet:'Comètes',pulse:'Pulsation néon',dashes:'Pointillés animés',color:'Couleur',color2:'Seconde couleur',width:'Épaisseur',speed:'Vitesse',target:'Cadre autour de',squares:'chaque carré',strip:'toute la bande',noEffect:'Aucun effet',petals:'Pétales de sakura',snow:'Neige réaliste',rain:'Pluie',lightning:'Éclairs',particle:'Flux de particules',stars:'Dérive stellaire',sparks:'Étincelles',matrix:'Matrice numérique',streaks:'Traînées lumineuses',effectColor:'Couleur de l’effet',density:'Densité',opacity:'Opacité',note:'Les cadres et effets animés transforment le résultat en cinq GIF synchronisés en boucle. Les FPS et la durée se règlent plus bas.',style:'Style',processNote:'Les contours animés transforment une image fixe en cinq GIF en boucle (4 s). Les vidéos et GIF gardent leur durée.'},
    uk:{anim2:"анімація 2",anim1:"анімація 1",animation:"Анімація",shape_blade:"Клинки",shape_circuit:"Схема",shape_arcs:"Дуги",shape_bend:"Вигин",shape_wing:"Крила",shape_slash:"Зрізи",shape_twin:"Дві лінії",shape_bastion:"Бастіон",shape_crown:"Корона",shape_pillars:"Колони",shimmer:"Переливи",grain:"Зерно",shape:"Форма",plate:"Темна підкладка",shape_rect:"Класика",shape_bevel:"Скоси",shape_tech:"Техно",shape_notch:"Виїмки",shape_hud:"HUD",shape_diamond:"Ромби",shape_rails:"Планки",shape_brackets:"Дужки",pr_hud:"HUD з відблиском",pr_cyber:"Кібер-зерно",presets:'Швидкі стилі',pr_neon:'Синій неон',pr_rgb:'RGB-геймер',pr_sakura:'Сакура',pr_matrix:'Матриця',pr_space:'Космос',pr_winter:'Зима',pr_minimal:'Мінімалізм',title:'3 · Рамка та ефекти',finish:'4 · Завантаж результат',frame:'Рамка',effect:'Ефект',beta:'анімація',none:'Немає',solid:'Лінія',double:'Подвійна',corners:'Кутики',neon:'Неон',rgb:'RGB-стрічка',comet:'Комети',pulse:'Пульс неону',dashes:'Біжучий пунктир',color:'Колір',color2:'Другий колір',width:'Товщина',speed:'Швидкість',target:'Рамка навколо',squares:'кожного квадрата',strip:'всієї смуги',noEffect:'Без ефекту',petals:'Пелюстки сакури',snow:'Справжній сніг',rain:'Дощ',lightning:'Блискавки',particle:'Потік частинок',stars:'Зоряний потік',sparks:'Іскри',matrix:'Цифрова матриця',streaks:'Світлові смуги',effectColor:'Колір ефекту',density:'Щільність',opacity:'Прозорість',note:'Анімовані рамки та ефекти перетворюють результат на п’ять синхронних зациклених GIF. FPS і тривалість задаються нижче.',style:'Стиль',processNote:'Анімована обводка перетворює зображення на п’ять зациклених GIF (4 с). Відео та GIF зберігають свою тривалість.'},
    es:{anim2:"animación 2",anim1:"animación 1",animation:"Animación",shape_blade:"Cuchillas",shape_circuit:"Circuito",shape_arcs:"Arcos",shape_bend:"Curva",shape_wing:"Alas",shape_slash:"Cortes",shape_twin:"Doble línea",shape_bastion:"Bastión",shape_crown:"Corona",shape_pillars:"Pilares",shimmer:"Reflejos",grain:"Grano",shape:"Forma",plate:"Fondo oscuro",shape_rect:"Clásico",shape_bevel:"Biselado",shape_tech:"Tech",shape_notch:"Muescas",shape_hud:"HUD",shape_diamond:"Rombos",shape_rails:"Rieles",shape_brackets:"Corchetes",pr_hud:"HUD con destello",pr_cyber:"Grano cyber",presets:'Estilos rápidos',pr_neon:'Neón azul',pr_rgb:'Gamer RGB',pr_sakura:'Sakura',pr_matrix:'Matrix',pr_space:'Espacio',pr_winter:'Invierno',pr_minimal:'Minimalista',title:'3 · Marco y efectos',finish:'4 · Descarga',frame:'Marco',effect:'Efecto',beta:'animado',none:'Ninguno',solid:'Línea',double:'Doble',corners:'Esquinas',neon:'Neón',rgb:'Tira RGB',comet:'Cometas',pulse:'Pulso de neón',dashes:'Trazos en movimiento',color:'Color',color2:'Segundo color',width:'Grosor',speed:'Velocidad',target:'Marco alrededor de',squares:'cada cuadrado',strip:'toda la tira',noEffect:'Sin efecto',petals:'Pétalos de sakura',snow:'Nieve realista',rain:'Lluvia',lightning:'Relámpagos',particle:'Flujo de partículas',stars:'Deriva estelar',sparks:'Chispas',matrix:'Matriz digital',streaks:'Trazos de luz',effectColor:'Color del efecto',density:'Densidad',opacity:'Opacidad',note:'Los marcos y efectos animados convierten el resultado en cinco GIF sincronizados en bucle. Los FPS y la duración se ajustan abajo.',style:'Estilo',processNote:'Los contornos animados convierten una imagen fija en cinco GIF en bucle (4 s). Los vídeos y GIF mantienen su duración.'},
    pt:{anim2:"animação 2",anim1:"animação 1",animation:"Animação",shape_blade:"Lâminas",shape_circuit:"Circuito",shape_arcs:"Arcos",shape_bend:"Curva",shape_wing:"Asas",shape_slash:"Cortes",shape_twin:"Linha dupla",shape_bastion:"Bastião",shape_crown:"Coroa",shape_pillars:"Pilares",shimmer:"Reflexos",grain:"Grão",shape:"Forma",plate:"Fundo escuro",shape_rect:"Clássico",shape_bevel:"Chanfrado",shape_tech:"Tech",shape_notch:"Entalhes",shape_hud:"HUD",shape_diamond:"Losangos",shape_rails:"Trilhos",shape_brackets:"Colchetes",pr_hud:"HUD com brilho",pr_cyber:"Grão cyber",presets:'Estilos rápidos',pr_neon:'Neon azul',pr_rgb:'Gamer RGB',pr_sakura:'Sakura',pr_matrix:'Matrix',pr_space:'Espaço',pr_winter:'Inverno',pr_minimal:'Minimalista',title:'3 · Moldura e efeitos',finish:'4 · Baixar',frame:'Moldura',effect:'Efeito',beta:'animado',none:'Nenhuma',solid:'Linha',double:'Dupla',corners:'Cantos',neon:'Neon',rgb:'Fita RGB',comet:'Cometas',pulse:'Pulso neon',dashes:'Tracejado em movimento',color:'Cor',color2:'Segunda cor',width:'Espessura',speed:'Velocidade',target:'Moldura em volta de',squares:'cada quadrado',strip:'toda a faixa',noEffect:'Sem efeito',petals:'Pétalas de sakura',snow:'Neve realista',rain:'Chuva',lightning:'Relâmpagos',particle:'Fluxo de partículas',stars:'Deriva estelar',sparks:'Faíscas',matrix:'Matriz digital',streaks:'Rastros de luz',effectColor:'Cor do efeito',density:'Densidade',opacity:'Opacidade',note:'Molduras e efeitos animados transformam o resultado em cinco GIFs sincronizados em loop. FPS e duração ficam abaixo.',style:'Estilo',processNote:'Contornos animados transformam uma imagem estática em cinco GIFs em loop (4 s). Vídeos e GIFs mantêm a duração.'}
  };
  /* One-click combinations of the controls below (frame + effect). */
  var PRESETS=[
    ['neon',{style:'neon',color:'#51d7ff',width:3},{type:'none'}],
    ['rgb',{style:'rgb',width:3,speed:1},{type:'none'}],
    ['sakura',{style:'solid',color:'#ffc4dc',width:2},{type:'petals',color:'#ff9fc8',density:100,opacity:90}],
    ['matrix',{style:'dashes',color:'#39ff88',color2:'#0d3b22',width:2,speed:1},{type:'matrix',color:'#39ff88',density:80,opacity:70}],
    ['space',{style:'comet',color:'#8de9ff',color2:'#8a62ff',width:3,speed:1},{type:'stars',color:'#cfe8ff',density:100,opacity:85}],
    ['winter',{style:'double',color:'#e6f7ff',color2:'#7fb8ff',width:3},{type:'snow',color:'#ffffff',density:100,opacity:90}],
    ['minimal',{style:'corners',color:'#ffffff',width:2},{type:'none'}],
    ['hud',{style:'shimmer',shape:'hud',plate:100,color:'#5fe4ff',width:3,speed:1},{type:'none'}],
    ['cyber',{style:'grain',shape:'circuit',plate:100,color:'#b27bff',width:3,speed:1},{type:'none'}]
  ];
  function applyPreset(fx,key){
    var preset=PRESETS.filter(function(p){return p[0]===key})[0];if(!preset)return;
    var base=defaults();
    fx.frame=Object.assign(base.frame,{target:fx.frame.target||'squares'},preset[1]);
    fx.effect=Object.assign(base.effect,preset[2]);
  }
  function t(key,language){return (COPY[language]||COPY.en)[key]||COPY.en[key]||key}

  function defaults(){return {frame:{style:'none',shape:'rect',plate:0,color:'#8de9ff',color2:'#8a62ff',width:3,speed:1,target:'squares'},effect:{type:'none',color:'#ff9fc8',speed:100,density:100,opacity:90}}}
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
  // ----------------------------------------------------------- shaped frames
  /* Same geometry as smweb/square_fx.py + smweb/frame_designs.py: a dark plate
     (even-odd polygons plus unioned bars) and an outline along its edges.
     rect/bevel/notch are simple windows; the HUD designs come from
     /static/assets/frames/designs.json. Panel roles: full (ornaments both sides),
     left / right (the two Artwork Split files). */
  var DESIGNS_URL='/static/assets/frames/designs.json?v=20260929-hud1',SPLIT_SIDE=100,REF_HEIGHT=260;
  var designs=null,designList=[],designWaiters=[];
  function loadDesigns(){
    if(designs||loadDesigns.busy||typeof fetch!=='function')return;loadDesigns.busy=true;
    fetch(DESIGNS_URL).then(function(r){return r.json()}).then(function(data){useDesigns(data)}).catch(function(){loadDesigns.busy=false});
  }
  function useDesigns(data){
    designs={};designList=[];(data.designs||[]).forEach(function(d){designs[d.id]=d;designList.push(d.id)});
    FRAME_SHAPES.length=0;['rect','bevel','notch'].concat(designList).forEach(function(k){FRAME_SHAPES.push(k)});
    maskCache={};designWaiters.splice(0).forEach(function(fn){try{fn()}catch(e){}});
    if(typeof document!=='undefined'&&document.dispatchEvent&&typeof CustomEvent==='function')document.dispatchEvent(new CustomEvent('sm:frame-designs'));
  }
  function clamp(v,a,b){return Math.max(a,Math.min(b,v))}
  function bevel(x0,y0,x1,y1,c){return [[x0+c,y0],[x1-c,y0],[x1,y0+c],[x1,y1-c],[x1-c,y1],[x0+c,y1],[x0,y1-c],[x0,y0+c]]}
  function windowShapes(shape,r,width){
    var half=width/2,x0=r[0]+half,y0=r[1]+half,x1=r[0]+r[2]-half,y1=r[1]+r[3]-half,bw=Math.max(1,x1-x0),bh=Math.max(1,y1-y0),k=Math.min(bw,bh),c=clamp(k*.12,3,60);
    if(shape==='bevel')return [bevel(x0,y0,x1,y1,c)];
    if(shape==='notch'){
      var s=c*.5,d=clamp(k*.07,2,26),hn=Math.min(bw*.17,k*.45,bw/2-s-d-1),mx=(x0+x1)/2;
      if(hn<2)return [bevel(x0,y0,x1,y1,s)];
      return [[[x0+s,y0],[mx-hn-d,y0],[mx-hn,y0+d],[mx+hn,y0+d],[mx+hn+d,y0],[x1-s,y0],[x1,y0+s],[x1,y1-s],[x1-s,y1],[mx+hn+d,y1],[mx+hn,y1-d],[mx-hn,y1-d],[mx-hn-d,y1],[x0+s,y1],[x0,y1-s],[x0,y0+s]]];
    }
    return [[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]];
  }
  function designUnit(role,w,h,col){col=col||70;if(role==='left')return (w/506)*SPLIT_SIDE/col;if(role==='right')return w/col;return Math.min(w/606,h/REF_HEIGHT)}
  function coord(spec,origin,span,u){return Array.isArray(spec)?origin+spec[0]*span+spec[1]*u:origin+spec*u}
  function strokePolygon(points,thickness){
    var half=thickness/2,normals=[],left=[],right=[];
    for(var i=0;i+1<points.length;i++){var dx=points[i+1][0]-points[i][0],dy=points[i+1][1]-points[i][1],l=Math.hypot(dx,dy)||1;normals.push([-dy/l,dx/l])}
    points.forEach(function(p,i){
      var n,scale=half;
      if(i===0)n=normals[0];else if(i===points.length-1)n=normals[normals.length-1];
      else{var a=normals[i-1],b=normals[i],nx=a[0]+b[0],ny=a[1]+b[1],l=Math.hypot(nx,ny)||1;n=[nx/l,ny/l];scale=half/Math.max(.25,n[0]*a[0]+n[1]*a[1])}
      left.push([p[0]+n[0]*scale,p[1]+n[1]*scale]);right.push([p[0]-n[0]*scale,p[1]-n[1]*scale]);
    });
    return left.concat(right.reverse());
  }
  function arcPoints(cx,cy,r,a0,a1){var steps=Math.max(6,Math.floor(Math.abs(a1-a0)/6)),out=[];for(var i=0;i<=steps;i++){var a=(a0+(a1-a0)*i/steps)*Math.PI/180;out.push([cx+r*Math.cos(a),cy+r*Math.sin(a)])}return out}
  function onBorder(a,b,r){
    var eps=.75,x=r[0],y=r[1],w=r[2],h=r[3],lines=[[0,x],[0,x+w],[1,y],[1,y+h]];
    for(var i=0;i<4;i++){var ax=lines[i][0],v=lines[i][1];if(Math.abs(a[ax]-v)<=eps&&Math.abs(b[ax]-v)<=eps)return true}
    return Math.max(a[0],b[0])<=x+eps||Math.min(a[0],b[0])>=x+w-eps||Math.max(a[1],b[1])<=y+eps||Math.min(a[1],b[1])>=y+h-eps;
  }
  function outlines(polys,r){
    var paths=[];
    polys.forEach(function(ring){
      var n=ring.length,keep=[],i;for(i=0;i<n;i++)keep.push(!onBorder(ring[i],ring[(i+1)%n],r));
      if(keep.every(Boolean)){paths.push([ring.slice(),true]);return}
      if(!keep.some(Boolean))return;
      var start=keep.indexOf(false),run=[];
      for(var step=1;step<=n;step++){var k=(start+step)%n;if(keep[k]){if(!run.length)run.push(ring[k]);run.push(ring[(k+1)%n])}else if(run.length){paths.push([run,false]);run=[]}}
      if(run.length)paths.push([run,false]);
    });
    return paths;
  }
  /* {evenOdd, bars, paths} of one panel r=[x,y,w,h] for a shape and panel role. */
  function panelGeometry(shape,r,width,role){
    role=role||'full';
    var design=designs&&designs[shape];
    if(!design){
      var windows=windowShapes(['rect','bevel','notch'].indexOf(shape)>=0?shape:'rect',r,width);
      return {evenOdd:[[[r[0],r[1]],[r[0]+r[2],r[1]],[r[0]+r[2],r[1]+r[3]],[r[0],r[1]+r[3]]]].concat(windows),bars:[],paths:windows.map(function(w){return [w,true]})};
    }
    var x=r[0],y=r[1],w=r[2],h=r[3],u=designUnit(role,w,h,design.col),col=design.col*u,lc=(role==='full'||role==='left')?col:0,rc=(role==='full'||role==='right')?col:0;
    var edge=(design.edge==null?6:design.edge)*u,gap=(design.gap||0)*u,wx0=x+(lc||edge)+gap,wx1=x+w-(rc||edge)-gap;
    var boxes={P:[x,w],W:[wx0,Math.max(1,wx1-wx0)],L:[x,col]},evenOdd=[],bars=[],all=[];
    function pt(spec,box){var b=boxes[box],px=coord(spec[0],b[0],b[1],u);if(box==='W'||(box==='L'&&role!=='full'))px=clamp(px,b[0],b[0]+b[1]);return [px,coord(spec[1],y,h,u)]}
    var hasWindow=wx1-wx0>=2;
    design.items.forEach(function(item){
      if(item.box==='W'&&!hasWindow)return;
      var copies=item.box==='L'?(lc?[false]:[]).concat(rc?[true]:[]):[false];
      copies.forEach(function(mirrored){
        var pts;
        if(item.kind==='arc'){var c=pt(item.c,item.box);pts=arcPoints(c[0],c[1],item.r*u,item.a[0],item.a[1])}
        else pts=item.pts.map(function(s){return pt(s,item.box)});
        if(mirrored)pts=pts.map(function(p){return [2*x+w-p[0],p[1]]});
        if(item.kind==='bar'||item.kind==='arc')pts=strokePolygon(pts,Math.max(2,(item.t||5)*u));
        (item.kind==='poly'?evenOdd:bars).push(pts);all.push(pts);
      });
    });
    return {evenOdd:evenOdd,bars:bars,paths:outlines(all,r)};
  }
  function shapePaths(shape,r,width,role){return panelGeometry(shape,r,width,role).paths}
  function pathMetrics(points,closed){var pts=points.slice();if(closed)pts.push(points[0]);var lengths=[],total=0;for(var i=0;i+1<pts.length;i++){var l=Math.hypot(pts[i+1][0]-pts[i][0],pts[i+1][1]-pts[i][1]);lengths.push(l);total+=l}return {pts:pts,lengths:lengths,total:total}}
  function pathPoint(points,closed,distance){var m=pathMetrics(points,closed);if(m.total<=0)return m.pts[0];distance=closed?mod(distance,m.total):clamp(distance,0,m.total);for(var i=0;i<m.lengths.length;i++){var l=m.lengths[i],a=m.pts[i],b=m.pts[i+1];if(distance<=l){var t=l?distance/l:0;return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t]}distance-=l}return m.pts[m.pts.length-1]}
  function hash01(i,j){var n=mod(i*7919+j*104729+13,65521);n=mod(n*n*31+n*17,65521);return n/65521}
  /* Outline textures (see OUTLINE_TEXTURES in square_fx.py): value noise in image space and loop time. */
  var OUTLINE_TEXTURES={shimmer:[[[75,170,3],[36,80,3]],[.68,.32],1.35],grain:[[[10,16,10],[4.5,7,10]],[.6,.4],2.2]};
  function hash3(i,j,k){var n=mod(i*7919+j*104729+k*1299709+13,65521);n=mod(n*n*31+n*17,65521);return n/65521}
  function valueNoise(gx,gy,gt,period){
    var ix=Math.floor(gx),iy=Math.floor(gy),it=Math.floor(gt),fx=gx-ix,fy=gy-iy,ft=gt-it,sx=fx*fx*(3-2*fx),sy=fy*fy*(3-2*fy),st=ft*ft*(3-2*ft),t0=mod(it,period),t1=mod(it+1,period);
    var a=(hash3(ix,iy,t0)*(1-sx)+hash3(ix+1,iy,t0)*sx)*(1-sy)+(hash3(ix,iy+1,t0)*(1-sx)+hash3(ix+1,iy+1,t0)*sx)*sy;
    var b=(hash3(ix,iy,t1)*(1-sx)+hash3(ix+1,iy,t1)*sx)*(1-sy)+(hash3(ix,iy+1,t1)*(1-sx)+hash3(ix+1,iy+1,t1)*sx)*sy;
    return a*(1-st)+b*st;
  }
  function textureLevel(style,x,y,u,scale,speed){
    var spec=OUTLINE_TEXTURES[style],value=0;
    for(var o=0;o<spec[0].length;o++){var c=spec[0][o],period=c[2]*Math.max(1,speed);value+=spec[1][o]*valueNoise(x/(c[0]*scale),y/(c[1]*scale),mod(u,1)*period,period)}
    value=clamp((value-.5)*spec[2]+.5,0,1);return .12+.8*value*value*(3-2*value);
  }
  function styleColor(style,f,u,shift,color,color2){
    var cycles=f.speed||1;
    if(style==='rgb')return function(p){return rgba(hsv(mod(p+shift-cycles*u,1)))};
    if(style==='comet'){var heads=[mod(cycles*u+shift,1),mod(cycles*u+shift+.5,1)],tail=.34;return function(p){var d=Math.min(mod(heads[0]-p,1),mod(heads[1]-p,1));if(d>tail)return rgba(mix(color,[0,0,0],.45),70/255);var s=Math.pow(1-d/tail,.85),tone=mix(color2,color,s);if(d<.03)tone=mix(tone,[255,255,255],.7);return rgba(tone,(90+165*s)/255)}}
    if(style==='dashes'){var offset=u*cycles*14*6;return function(_p,d){return mod(d-offset,14)<8?rgba(color):rgba(color2,90/255)}}
    return null;
  }
  function strokePath(ctx,points,closed,width,colorAt){
    var m=pathMetrics(points,closed);if(m.total<=0)return;var walked=0;ctx.lineWidth=width;ctx.lineCap='butt';
    for(var i=0;i<m.lengths.length;i++){
      var a=m.pts[i],b=m.pts[i+1],l=m.lengths[i],count=Math.max(1,Math.ceil(l/2));
      for(var j=0;j<count;j++){var d0=walked+l*j/count,style=colorAt(d0/m.total,d0);if(!style)continue;var t0=j/count,t1=(j+1)/count;ctx.strokeStyle=style;ctx.beginPath();ctx.moveTo(a[0]+(b[0]-a[0])*t0,a[1]+(b[1]-a[1])*t0);ctx.lineTo(a[0]+(b[0]-a[0])*t1,a[1]+(b[1]-a[1])*t1);ctx.stroke()}
      if(width>=3&&(closed||walked+l<m.total)){var joint=colorAt(closed?mod(walked+l,m.total)/m.total:Math.min(1,(walked+l)/m.total),walked+l);if(joint){ctx.fillStyle=joint;ctx.beginPath();ctx.arc(b[0],b[1],width/2,0,TAU);ctx.fill()}}
      walked+=l;
    }
  }
  function cornerNear(points,closed,size){var m=pathMetrics(points,closed),marks=[0],acc=0;m.lengths.forEach(function(l){acc+=l;marks.push(acc)});return function(d){for(var i=0;i<marks.length;i++)if(Math.abs(d-marks[i])<=size)return true;return closed&&m.total-d<=size}}
  function canvasOf(w,h){var c=typeof OffscreenCanvas==='function'?new OffscreenCanvas(w,h):document.createElement('canvas');c.width=w;c.height=h;return c}
  function tracePolys(ctx,polys){polys.forEach(function(poly){poly.forEach(function(p,i){i?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1])});ctx.closePath()})}
  /* Plate (alpha mask) and its interior (plate shrunk by about the line width), cached per panel. */
  var maskCache={};
  function panelMasks(shape,w,h,width,role){
    var key=[shape,w,h,width,role].join('|');if(maskCache[key])return maskCache[key];
    var g=panelGeometry(shape,[0,0,w,h],width,role),plate=canvasOf(w,h),p=plate.getContext('2d');
    p.fillStyle='#000';p.beginPath();tracePolys(p,g.evenOdd);p.fill('evenodd');p.beginPath();tracePolys(p,g.bars);p.fill('nonzero');
    var data=p.getImageData(0,0,w,h),src=data.data,radius=Math.min(15,Math.round(width)+2),tmp=new Uint8ClampedArray(w*h),out=new Uint8ClampedArray(w*h),x,y,k,m;
    for(y=0;y<h;y++)for(x=0;x<w;x++){m=255;for(k=-radius;k<=radius;k++){var xx=x+k;var v=xx<0||xx>=w?255:src[(y*w+xx)*4+3];if(v<m)m=v}tmp[y*w+x]=m}
    for(y=0;y<h;y++)for(x=0;x<w;x++){m=255;for(k=-radius;k<=radius;k++){var yy=y+k;var v2=yy<0||yy>=h?255:tmp[yy*w+x];if(v2<m)m=v2}out[y*w+x]=m}
    var inner=canvasOf(w,h),ic=inner.getContext('2d'),id=ic.createImageData(w,h);for(k=0;k<w*h;k++){id.data[k*4+3]=out[k]}ic.putImageData(id,0,0);
    var entry={geometry:g,plate:plate,interior:inner,key:key};maskCache[key]=entry;
    var keys=Object.keys(maskCache);if(keys.length>40)delete maskCache[keys[0]];
    return entry;
  }
  function drawPanel(ctx,u,f,r,index,scale){
    var x=Math.round(r[0]),y=Math.round(r[1]),w=Math.max(1,Math.round(r[2])),h=Math.max(1,Math.round(r[3])),role=r[4]||'full';
    if(w<2||h<2)return;
    var style=f.style,width=f.width,color=rgb(f.color),color2=rgb(f.color2||'#8a62ff'),cycles=f.speed||1,masks=panelMasks(f.shape,w,h,width,role),g=masks.geometry;
    var level=(f.plate||0)/100,pulse=style==='pulse'?.5+.5*Math.cos(TAU*cycles*u):1,shift=f.target==='squares'?index*.2:0;
    ctx.save();ctx.beginPath();ctx.rect(x,y,w,h);ctx.clip();
    if(level>0){ctx.globalAlpha=level;ctx.drawImage(masks.plate,x,y);ctx.globalAlpha=1}
    // One scratch canvas per panel size, reused every frame (no allocations while animating).
    var layer=masks.layer||(masks.layer=canvasOf(w,h)),lc=layer.getContext('2d');lc.clearRect(0,0,w,h);
    if(OUTLINE_TEXTURES[style]||style==='solid'||style==='neon'||style==='pulse'||style==='double'){
      var outline=outlineOf(masks,w,h,width);
      if(OUTLINE_TEXTURES[style])paintTexture(lc,masks,outline,style,u,x,y,scale,cycles,color,w,h);
      else{lc.drawImage(outline.canvas,0,0);lc.globalCompositeOperation='source-in';lc.fillStyle=rgba((style==='neon'||style==='pulse')?mix(color,[255,255,255],.35):color);lc.fillRect(0,0,w,h);lc.globalCompositeOperation='source-over'}
    }else{
      var heads=[];
      g.paths.forEach(function(p,pathIndex){
        var points=p[0],closed=p[1],total=pathMetrics(points,closed).total,colorAt=styleColor(style,f,u,shift,color,color2);
        if(!colorAt){var near=cornerNear(points,closed,Math.min(w,h)*.14);colorAt=function(_p,dd){return near(dd)?rgba(color):null}}
        strokePath(lc,points,closed,width,colorAt);
        if(style==='comet'&&closed&&pathIndex===0)[mod(cycles*u+shift,1),mod(cycles*u+shift+.5,1)].forEach(function(hd){heads.push(pathPoint(points,closed,hd*total))});
      });
      lc.fillStyle='#fff';heads.forEach(function(p){lc.beginPath();lc.arc(p[0],p[1],width*.9+1.5,0,TAU);lc.fill()});
      lc.globalCompositeOperation='destination-out';lc.drawImage(masks.interior,0,0);lc.globalCompositeOperation='source-over';
    }
    var glow={neon:1.8,pulse:1.8,rgb:1.6,comet:1.6,dashes:1,shimmer:1.2,grain:1}[style]||0;
    if(glow){
      ctx.save();ctx.shadowColor=rgba(color,{neon:1,pulse:.25+.75*pulse,shimmer:.8,grain:.6}[style]||1);ctx.shadowBlur=Math.max(3,width*glow*2);
      ctx.globalAlpha=style==='pulse'?.55+.45*pulse:1;ctx.drawImage(layer,x,y);ctx.restore();
    }else{ctx.globalAlpha=style==='pulse'?.55+.45*pulse:1;ctx.drawImage(layer,x,y);ctx.globalAlpha=1}
    ctx.restore();
  }
  /* The outline mask of a panel (strokes minus the plate interior) and its pixels, cached. */
  function outlineOf(masks,w,h,width){
    if(masks.outline)return masks.outline;
    var c=canvasOf(w,h),k=c.getContext('2d');k.strokeStyle='#fff';k.lineWidth=width;k.lineJoin='round';k.lineCap='butt';
    masks.geometry.paths.forEach(function(p){k.beginPath();p[0].forEach(function(q,i){i?k.lineTo(q[0],q[1]):k.moveTo(q[0],q[1])});if(p[1])k.closePath();k.stroke()});
    k.globalCompositeOperation='destination-out';k.drawImage(masks.interior,0,0);k.globalCompositeOperation='source-over';
    var data=k.getImageData(0,0,w,h).data,idx=[],alpha=[];
    for(var i=0,n=w*h;i<n;i++){var a=data[i*4+3];if(a){idx.push(i);alpha.push(a)}}
    return masks.outline={canvas:c,idx:Uint32Array.from(idx),alpha:Uint8Array.from(alpha)};
  }
  /* Shimmer / grain: brightness per outline pixel for 48 steps of the loop, computed once
     per step and kept; every frame only recolours the cached pixels. */
  var TEXTURE_STEPS=48,textureCache=new Map();
  function textureStep(entry,step,style,idx,w,x,y,scale,cycles){
    var lum=entry.steps[step];if(lum)return lum;
    lum=entry.steps[step]=new Uint8Array(idx.length);var t=step/TEXTURE_STEPS;
    for(var i=0;i<idx.length;i++){var p=idx[i];lum[i]=Math.round(textureLevel(style,p%w+x,((p/w)|0)+y,t,scale,cycles)*255)}
    return lum;
  }
  function paintTexture(lc,masks,outline,style,u,x,y,scale,cycles,color,w,h){
    var key=[style,cycles,w,h,x,y,scale.toFixed(4),outline.idx.length,masks.key].join('|'),entry=textureCache.get(key);
    if(!entry){entry={steps:[],img:lc.createImageData(w,h)};textureCache.set(key,entry);if(textureCache.size>16)textureCache.delete(textureCache.keys().next().value)}
    // Two neighbouring cached steps blended by the exact position: smooth at any loop length
    // (the Builder loop is 8 s, so 48 plain steps looked like ~6 fps).
    var pos=mod(u,1)*TEXTURE_STEPS,step=Math.floor(pos)%TEXTURE_STEPS,next=(step+1)%TEXTURE_STEPS,f=pos-Math.floor(pos),idx=outline.idx,alpha=outline.alpha,i;
    var lumA=textureStep(entry,step,style,idx,w,x,y,scale,cycles),lumB=textureStep(entry,next,style,idx,w,x,y,scale,cycles);
    var d=entry.img.data,r=color[0]*1.25/255,gg=color[1]*1.25/255,b=color[2]*1.25/255;
    for(i=0;i<idx.length;i++){var o=idx[i]*4,l=lumA[i]+(lumB[i]-lumA[i])*f,hi=l>184?(l-184)*1.4:0;d[o]=r*l+hi;d[o+1]=gg*l+hi;d[o+2]=b*l+hi;d[o+3]=alpha[i]}
    lc.putImageData(entry.img,0,0);
  }
  /* Panels: [x,y,w,h,role?] (role "left"/"right" for the Split parts). */
  function drawShaped(ctx,u,f,list,surface){
    var canvas=ctx.canvas||{},scale=(surface||Math.max(canvas.width||W,canvas.height||H))/1000;
    list.forEach(function(r,index){drawPanel(ctx,u,f,r,index,scale)});
  }

  function drawFrame(ctx,u,f,list,surface){
    var style=f.style;if(style==='none')return;
    list=list||rects(f.target);
    if((f.shape&&f.shape!=='rect')||OUTLINE_TEXTURES[style]||list.some(function(r){return r[4]&&r[4]!=='full'})){drawShaped(ctx,u,f,list,surface);return}
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

  /* Shape picker: every tile draws its own outline, so new shapes need no icons. */
  // --------------------------------------------------------- visual pickers
  /* Frame and animation pickers with pictures instead of lists. Shape tiles draw
     the design on a sample picture for the current showcase type (Split shows
     both files: 506 + 100); animation tiles play the real animation on a small
     outline. Tiles animate only while visible; reduced motion shows one still. */
  var SAMPLE_URL='/static/img/samples/sample-art.webp',sample=null,liveTiles=[],ticker=0,lastTick=0;
  var PALETTE=['#ffffff','#ff2d2d','#ffa31a','#b5ff1f','#1fff8f','#19ffd5','#5fe4ff','#1a9bff','#2600ff','#8a62ff','#c13bff','#ff00a1','#ffe600','#ff6a00'];
  function sampleImage(onReady){
    if(sample&&sample.complete&&sample.naturalWidth)return sample;
    if(!sample&&typeof Image==='function'){sample=new Image();sample.decoding='async';sample.src=SAMPLE_URL;sample.onload=function(){liveTiles.forEach(function(t){t.dirty=true});(onReady||function(){})()}}
    return null;
  }
  function paintBackdrop(ctx,w,h){
    var img=sampleImage(requestTick);
    if(img){var s=Math.max(w/img.naturalWidth,h/img.naturalHeight),dw=img.naturalWidth*s,dh=img.naturalHeight*s;ctx.drawImage(img,(w-dw)/2,(h-dh)/2,dw,dh)}
    else{var g=ctx.createLinearGradient(0,0,w,h);g.addColorStop(0,'#3a5d9e');g.addColorStop(.55,'#b56aa8');g.addColorStop(1,'#f2b6c9');ctx.fillStyle=g;ctx.fillRect(0,0,w,h)}
  }
  /* Panels of a picker thumbnail for the showcase type ("workshop" | "featured" | "split"). */
  function thumbPanels(mode,w,h){
    if(mode==='split'){var main=Math.round(w*506/606);return [[0,0,main-1,h,'left'],[main+1,0,w-main-1,h,'right']]}
    if(mode==='workshop'){var out=[],cw=(w-4)/3;for(var i=0;i<3;i++)out.push([Math.round(i*(cw+2)),0,Math.round(cw),h,'full']);return out}
    return [[0,0,w,h,'full']];
  }
  function registerTile(canvas,draw){var tile={canvas:canvas,draw:draw,dirty:true};liveTiles.push(tile);requestTick();return tile}
  function visible(el){return !!(el&&el.isConnected&&el.offsetParent&&(typeof document==='undefined'||!document.hidden))}
  function requestTick(){if(!ticker&&typeof requestAnimationFrame==='function')ticker=requestAnimationFrame(tick)}
  function tick(now){
    ticker=0;liveTiles=liveTiles.filter(function(t){return t.canvas.isConnected});
    var still=typeof matchMedia==='function'&&matchMedia('(prefers-reduced-motion: reduce)').matches,animating=false;
    liveTiles.forEach(function(t){
      if(!visible(t.canvas))return;
      if(t.animated&&!still){animating=true;if(now-lastTick<66&&!t.dirty)return;t.draw(((now||0)/2000)%1);t.dirty=false}
      else if(t.dirty){t.draw(.2);t.dirty=false}
    });
    if(animating){if(now-lastTick>=66)lastTick=now;ticker=requestAnimationFrame(tick)}
  }
  if(typeof document!=='undefined'){document.addEventListener('visibilitychange',requestTick);document.addEventListener('sm:frame-designs',function(){liveTiles.forEach(function(t){t.dirty=true});requestTick()})}
  function tileCanvas(w,h){var c=document.createElement('canvas'),ratio=2;c.width=w*ratio;c.height=h*ratio;c.style.width=w+'px';c.style.height=h+'px';c.setAttribute('aria-hidden','true');return c}
  /* Frame design tiles. opts: {mode, value, color, language, onPick, includeNone} */
  function shapePicker(opts){
    loadDesigns();
    var box=el('div','sqfx-pick sqfx-pick--shapes'+(opts.mode==='split'?' is-split':'')),language=opts.language;
    box.setAttribute('role','radiogroup');box.setAttribute('aria-label',t('shape',language));
    function build(){
      box.replaceChildren();
      var keys=(opts.includeNone?['none']:[]).concat(FRAME_SHAPES);
      keys.forEach(function(key){
        var b=el('button','sqfx-pick__tile');b.type='button';b.dataset.shape=key;b.setAttribute('role','radio');b.setAttribute('aria-checked',String(opts.value===key));
        var label=key==='none'?t('none',language):t('shape_'+key,language);b.title=label;
        var cw=opts.mode==='split'?64:(opts.mode==='workshop'?66:58),ch=74,canvas=tileCanvas(cw,ch);
        registerTile(canvas,function(){
          var ctx=canvas.getContext('2d'),W2=canvas.width,H2=canvas.height;ctx.clearRect(0,0,W2,H2);paintBackdrop(ctx,W2,H2);
          if(key==='none')return;
          var panels=thumbPanels(opts.mode,W2,H2);
          if(opts.mode==='split'){ctx.fillStyle='#070b14';ctx.fillRect(panels[0][2],0,panels[1][0]-panels[0][2],H2)}
          if(opts.mode==='workshop'){ctx.fillStyle='#070b14';panels.slice(1).forEach(function(p){ctx.fillRect(p[0]-2,0,2,H2)})}
          drawShaped(ctx,.2,{style:'solid',shape:key,plate:key==='rect'?0:100,color:opts.color||'#5fe4ff',color2:'#8a62ff',width:2,speed:1,target:'strip'},panels,600);
        });
        b.append(canvas,el('span',null,label));b.onclick=function(){opts.onPick(key)};box.append(b);
      });
      requestTick();
    }
    build();
    if(!designs)designWaiters.push(build);
    return box;
  }
  /* Animation / style tiles, each playing its animation on a small outline. */
  function stylePicker(opts){
    var box=el('div','sqfx-pick sqfx-pick--styles'),language=opts.language,styles=opts.styles||STATIC_FRAMES.concat(ANIMATED_FRAMES);
    box.setAttribute('role','radiogroup');box.setAttribute('aria-label',t('animation',language));
    styles.forEach(function(key){
      var b=el('button','sqfx-pick__tile sqfx-pick__tile--style');b.type='button';b.dataset.style=key;b.setAttribute('role','radio');b.setAttribute('aria-checked',String(opts.value===key));
      var canvas=tileCanvas(76,34),tile=registerTile(canvas,function(u){
        var ctx=canvas.getContext('2d'),W2=canvas.width,H2=canvas.height;ctx.clearRect(0,0,W2,H2);ctx.fillStyle='#0a1222';ctx.fillRect(0,0,W2,H2);
        if(key==='none'){ctx.strokeStyle='rgba(140,170,200,.35)';ctx.setLineDash([6,6]);ctx.lineWidth=2;ctx.strokeRect(12,12,W2-24,H2-24);ctx.setLineDash([]);return}
        drawFrame(ctx,u,{style:key,shape:'rect',plate:0,color:opts.color||'#5fe4ff',color2:opts.color2||'#8a62ff',width:4,speed:1,target:'strip'},[[10,10,W2-20,H2-20]]);
      });
      tile.animated=ANIMATED_FRAMES.indexOf(key)>=0;
      var name=el('span',null,t(key,language));b.append(canvas,name);
      if(key==='shimmer'||key==='grain'){var tag=el('small',null,t(key==='shimmer'?'anim1':'anim2',language));b.append(tag)}
      else if(tile.animated)b.append(el('small',null,t('beta',language)));
      b.onclick=function(){opts.onPick(key)};box.append(b);
    });
    requestTick();
    return box;
  }
  /* Colour swatches plus the native picker. */
  function colorSwatches(opts){
    var box=el('div','sqfx-swatches');box.setAttribute('role','group');box.setAttribute('aria-label',t('color',opts.language));
    var custom=el('label','sqfx-swatches__custom'),input=el('input');input.type='color';input.value=opts.value||'#5fe4ff';input.setAttribute('aria-label',t('color',opts.language));
    input.oninput=function(){opts.onPick(this.value)};custom.append(input);box.append(custom);
    PALETTE.forEach(function(c){var b=el('button','sqfx-swatches__dot');b.type='button';b.style.background=c;b.title=c;b.setAttribute('aria-pressed',String((opts.value||'').toLowerCase()===c));b.onclick=function(){input.value=c;opts.onPick(c)};box.append(b)});
    return box;
  }

  function mountControls(host,fx,language,onChange){
    host.replaceChildren();
    var frame=fx.frame,effect=fx.effect,animated=ANIMATED_FRAMES.indexOf(frame.style)>=0,on=frame.style!=='none';
    function change(){onChange();mountControls(host,fx,language,onChange)}
    host.append(el('p','sqfx__label',t('presets',language)));
    var quick=el('div','sqfx__presets');quick.setAttribute('data-no-translate','');
    PRESETS.forEach(function(preset){
      var button=el('button','sqfx__preset',t('pr_'+preset[0],language));button.type='button';button.dataset.preset=preset[0];
      button.onclick=function(){applyPreset(fx,preset[0]);change()};quick.append(button);
    });
    host.append(quick);
    host.append(el('p','sqfx__label',t('frame',language)));
    host.append(shapePicker({mode:'workshop',value:on?(frame.shape||'rect'):'none',color:frame.color,language:language,includeNone:true,onPick:function(key){
      if(key==='none'){frame.style='none'}
      else{if(frame.style==='none')frame.style=key==='rect'?'neon':'shimmer';if(key!=='rect'&&frame.shape!==key&&!frame.plate)frame.plate=100;frame.shape=key}
      change();
    }}));
    if(on){
      host.append(el('p','sqfx__label',t('animation',language)));
      host.append(stylePicker({value:frame.style,color:frame.color,color2:frame.color2,language:language,styles:STATIC_FRAMES.filter(function(s){return s!=='none'}).concat(ANIMATED_FRAMES),onPick:function(key){frame.style=key;change()}}));
      if(frame.style!=='rgb'){host.append(el('p','sqfx__label',t('color',language)));host.append(colorSwatches({value:frame.color,language:language,onPick:function(v){frame.color=v;onChange();host.querySelectorAll('.sqfx-swatches__dot').forEach(function(d){d.setAttribute('aria-pressed',String(d.title===v))})}}))}
      var row=el('div','sqfx__grid');
      if((frame.shape||'rect')!=='rect')row.append(range(t('plate',language),frame.plate||0,0,100,5,'%',function(v){frame.plate=v;onChange()}));
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
  if(typeof window!=='undefined'&&typeof document!=='undefined'&&document.querySelector)loadDesigns();
  window.SMSquaresFx={COPY:COPY,t:t,PRESETS:PRESETS,applyPreset:applyPreset,defaults:defaults,isEmpty:isEmpty,isAnimated:isAnimated,render:render,mountControls:mountControls,W:W,H:H,
    FRAME_STYLES:STATIC_FRAMES.concat(ANIMATED_FRAMES),ANIMATED_FRAMES:ANIMATED_FRAMES,FRAME_SHAPES:FRAME_SHAPES,shapePaths:shapePaths,panelRects:panelRects,
    drawFrame:function(ctx,u,frame,list,surface){ctx.save();drawFrame(ctx,mod(u,1),frame,list,surface);ctx.restore()},
    shapePicker:shapePicker,stylePicker:stylePicker,colorSwatches:colorSwatches,panelGeometry:panelGeometry,loadDesigns:loadDesigns,useDesigns:useDesigns,
    textureLevel:textureLevel,hash3:hash3,
    isAnimatedFrame:function(style){return ANIMATED_FRAMES.indexOf(style)>=0}};
})();
