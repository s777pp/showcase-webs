/* One choice for every tool that makes Steam files (Process, Rows and squares,
   Character, "Download for Steam" in Create a design):

   - SMEncodeChoice.ask({animated}) shows the "Standard / Maximum quality" dialog
     before an animated job starts and resolves to 'standard' | 'max' (null when
     cancelled). Still pictures need no compression, so they skip the dialog.
     The server reads it as `encode_profile` (processor.encode_profile).
   - SMEncodeChoice.mountExtras(container) adds the two "also put in the ZIP"
     switches (original, DeviantArt preview); by default the ZIP holds only the
     Steam files. Sent as `include_original` / `include_preview`.
   - SMEncodeChoice.append(formData, profile, extras) writes all of it into a form. */
(function () {
  'use strict';

  var COPY={
    en:{eyebrow:'ANIMATION',title:'How should we prepare the animation?',intro:'Steam takes files up to 5 MB, so animations have to be compressed. Choose what matters more.',stdTitle:'Standard',stdBadge:'faster',stdText:'Two to three times faster. The difference in quality is hard to see.',maxTitle:'Maximum quality',maxBadge:'takes longer',maxText:'Squeezes the best picture right up to 5 MB. Noticeably slower.',start:'Start',cancel:'Cancel',close:'Close',extrasTitle:'Also put in the ZIP',original:'Add the original to the ZIP',originalHint:'The whole showcase as one file, not cut',preview:'Add a DeviantArt preview',previewHint:'The showcase with gaps, as on a profile. Handy for posting',extrasNote:'By default the ZIP holds only the files for Steam. Each extra file adds processing time.'},
    ru:{eyebrow:'АНИМАЦИЯ',title:'Как подготовить анимацию?',intro:'Steam принимает файлы до 5 МБ, поэтому анимацию нужно сжать. Выбери, что важнее.',stdTitle:'Стандарт',stdBadge:'быстрее',stdText:'В 2–3 раза быстрее. Разницу в качестве почти не видно.',maxTitle:'Максимальное качество',maxBadge:'дольше',maxText:'Выжимает лучшую картинку впритык к 5 МБ. Занимает заметно больше времени.',start:'Начать',cancel:'Отмена',close:'Закрыть',extrasTitle:'Дополнительно в архив',original:'Добавить в архив оригинал',originalHint:'Вся витрина одним файлом, без нарезки',preview:'Добавить превью для DeviantArt',previewHint:'Витрина с промежутками, как в профиле. Удобно для публикации',extrasNote:'По умолчанию в архиве только файлы для Steam. Каждый дополнительный файл добавляет времени обработке.'},
    de:{eyebrow:'ANIMATION',title:'Wie soll die Animation vorbereitet werden?',intro:'Steam nimmt Dateien bis 5 MB an, deshalb müssen Animationen komprimiert werden. Wähle, was dir wichtiger ist.',stdTitle:'Standard',stdBadge:'schneller',stdText:'Zwei- bis dreimal schneller. Der Qualitätsunterschied ist kaum zu sehen.',maxTitle:'Maximale Qualität',maxBadge:'dauert länger',maxText:'Holt das beste Bild knapp unter 5 MB heraus. Spürbar langsamer.',start:'Starten',cancel:'Abbrechen',close:'Schließen',extrasTitle:'Zusätzlich ins ZIP',original:'Original ins ZIP legen',originalHint:'Die ganze Vitrine als eine Datei, nicht zerschnitten',preview:'DeviantArt-Vorschau hinzufügen',previewHint:'Die Vitrine mit Lücken wie im Profil. Praktisch zum Posten',extrasNote:'Standardmäßig enthält das ZIP nur die Dateien für Steam. Jede zusätzliche Datei verlängert die Verarbeitung.'},
    tr:{eyebrow:'ANİMASYON',title:'Animasyon nasıl hazırlansın?',intro:'Steam en fazla 5 MB dosya kabul eder, bu yüzden animasyonların sıkıştırılması gerekir. Hangisinin daha önemli olduğunu seç.',stdTitle:'Standart',stdBadge:'daha hızlı',stdText:'İki ila üç kat daha hızlı. Kalite farkı neredeyse görünmez.',maxTitle:'En yüksek kalite',maxBadge:'daha uzun sürer',maxText:'En iyi görüntüyü 5 MB sınırına kadar çıkarır. Belirgin şekilde daha yavaş.',start:'Başlat',cancel:'İptal',close:'Kapat',extrasTitle:'ZIP’e ayrıca ekle',original:'Orijinali ZIP’e ekle',originalHint:'Vitrinin tamamı tek dosya, kesilmeden',preview:'DeviantArt önizlemesi ekle',previewHint:'Profildeki gibi boşluklu vitrin. Paylaşmak için kullanışlı',extrasNote:'Varsayılan olarak ZIP yalnızca Steam dosyalarını içerir. Her ek dosya işlem süresini uzatır.'},
    fr:{eyebrow:'ANIMATION',title:'Comment préparer l’animation ?',intro:'Steam accepte des fichiers jusqu’à 5 Mo, les animations doivent donc être compressées. Choisissez ce qui compte le plus.',stdTitle:'Standard',stdBadge:'plus rapide',stdText:'Deux à trois fois plus rapide. La différence de qualité se voit à peine.',maxTitle:'Qualité maximale',maxBadge:'plus long',maxText:'Tire la meilleure image au plus près de 5 Mo. Nettement plus lent.',start:'Lancer',cancel:'Annuler',close:'Fermer',extrasTitle:'Ajouter aussi au ZIP',original:'Ajouter l’original au ZIP',originalHint:'Toute la vitrine en un seul fichier, sans découpe',preview:'Ajouter un aperçu DeviantArt',previewHint:'La vitrine avec espaces, comme sur un profil. Pratique pour publier',extrasNote:'Par défaut, le ZIP ne contient que les fichiers pour Steam. Chaque fichier en plus allonge le traitement.'},
    uk:{eyebrow:'АНІМАЦІЯ',title:'Як підготувати анімацію?',intro:'Steam приймає файли до 5 МБ, тому анімацію потрібно стиснути. Обери, що важливіше.',stdTitle:'Стандарт',stdBadge:'швидше',stdText:'У 2–3 рази швидше. Різницю в якості майже не видно.',maxTitle:'Максимальна якість',maxBadge:'довше',maxText:'Вичавлює найкращу картинку впритул до 5 МБ. Займає помітно більше часу.',start:'Почати',cancel:'Скасувати',close:'Закрити',extrasTitle:'Додатково в архів',original:'Додати в архів оригінал',originalHint:'Уся вітрина одним файлом, без нарізки',preview:'Додати превʼю для DeviantArt',previewHint:'Вітрина з проміжками, як у профілі. Зручно для публікації',extrasNote:'Типово в архіві лише файли для Steam. Кожен додатковий файл додає часу обробці.'},
    es:{eyebrow:'ANIMACIÓN',title:'¿Cómo preparamos la animación?',intro:'Steam acepta archivos de hasta 5 MB, así que las animaciones hay que comprimirlas. Elige qué es más importante.',stdTitle:'Estándar',stdBadge:'más rápido',stdText:'De dos a tres veces más rápido. La diferencia de calidad apenas se nota.',maxTitle:'Calidad máxima',maxBadge:'tarda más',maxText:'Saca la mejor imagen justo hasta los 5 MB. Bastante más lento.',start:'Empezar',cancel:'Cancelar',close:'Cerrar',extrasTitle:'Añadir también al ZIP',original:'Añadir el original al ZIP',originalHint:'Todo el escaparate en un archivo, sin cortar',preview:'Añadir una vista previa para DeviantArt',previewHint:'El escaparate con huecos, como en un perfil. Útil para publicar',extrasNote:'Por defecto el ZIP solo trae los archivos para Steam. Cada archivo extra alarga el procesamiento.'},
    pt:{eyebrow:'ANIMAÇÃO',title:'Como preparar a animação?',intro:'A Steam aceita arquivos de até 5 MB, então as animações precisam ser comprimidas. Escolha o que importa mais.',stdTitle:'Padrão',stdBadge:'mais rápido',stdText:'Duas a três vezes mais rápido. A diferença de qualidade quase não aparece.',maxTitle:'Qualidade máxima',maxBadge:'demora mais',maxText:'Tira a melhor imagem bem perto dos 5 MB. Bem mais lento.',start:'Começar',cancel:'Cancelar',close:'Fechar',extrasTitle:'Também colocar no ZIP',original:'Adicionar o original ao ZIP',originalHint:'A vitrine inteira em um arquivo, sem cortes',preview:'Adicionar uma prévia para o DeviantArt',previewHint:'A vitrine com espaços, como no perfil. Prática para publicar',extrasNote:'Por padrão o ZIP traz só os arquivos para a Steam. Cada arquivo extra aumenta o tempo de processamento.'}
  };
  var PROFILE_KEY='sm_encode_profile', EXTRAS_KEY='sm_zip_extras';
  var ANIMATED_EXT=/\.(gif|mp4|webm|mov|mkv|avi|m4v)$/i;

  function language(){var l=window.SMLang&&SMLang.get?SMLang.get():(document.documentElement.lang||'en');return COPY[l]?l:'en'}
  function t(key){return (COPY[language()]||COPY.en)[key]||COPY.en[key]||key}
  function load(key){try{return window.localStorage.getItem(key)}catch(e){return null}}
  function store(key,value){try{window.localStorage.setItem(key,value)}catch(e){}}
  function node(tag,className,text){var el=document.createElement(tag);if(className)el.className=className;if(text!=null)el.textContent=text;return el}

  function lastProfile(){return load(PROFILE_KEY)==='max'?'max':'standard'}

  /* A file the server will treat as a moving source (GIF, video). */
  function isAnimatedFile(file){
    if(!file)return false;
    var type=String(file.type||''),name=String(file.name||'');
    return type==='image/gif'||type.indexOf('video/')===0||ANIMATED_EXT.test(name);
  }

  var open=null;
  function ask(options){
    options=options||{};
    if(options.animated===false)return Promise.resolve(lastProfile());
    if(open)return open.promise;
    var resolveFn,promise=new Promise(function(resolve){resolveFn=resolve});
    var previousFocus=document.activeElement,choice=lastProfile();

    var overlay=node('div','sm-encode');
    var backdrop=node('button','sm-encode__backdrop');backdrop.type='button';backdrop.tabIndex=-1;backdrop.setAttribute('aria-label',t('close'));
    var dialog=node('section','sm-encode__dialog');dialog.setAttribute('role','dialog');dialog.setAttribute('aria-modal','true');dialog.setAttribute('aria-labelledby','smEncodeTitle');
    var head=node('header','sm-encode__head'),heading=node('div');
    heading.append(node('span','sm-encode__eyebrow',t('eyebrow')));
    var title=node('h2',null,t('title'));title.id='smEncodeTitle';heading.append(title);
    var closeButton=node('button','sm-encode__close','×');closeButton.type='button';closeButton.setAttribute('aria-label',t('close'));
    head.append(heading,closeButton);
    var intro=node('p','sm-encode__intro',t('intro'));
    var group=node('div','sm-encode__options');group.setAttribute('role','radiogroup');group.setAttribute('aria-labelledby','smEncodeTitle');
    var cards={};
    [['standard','std','is-fast'],['max','max','is-best']].forEach(function(item){
      var card=node('button','sm-encode__option '+item[2]);card.type='button';card.setAttribute('role','radio');card.dataset.profile=item[0];
      var top=node('span','sm-encode__option-top');
      top.append(node('b',null,t(item[1]+'Title')),node('em',null,t(item[1]+'Badge')));
      card.append(top,node('span','sm-encode__option-text',t(item[1]+'Text')));
      card.addEventListener('click',function(){select(item[0])});
      card.addEventListener('dblclick',function(){select(item[0]);finish(item[0])});
      cards[item[0]]=card;group.append(card);
    });
    var foot=node('footer','sm-encode__foot');
    var cancel=node('button','btn ghost sm-encode__cancel',t('cancel'));cancel.type='button';
    var start=node('button','btn primary sm-encode__start',t('start'));start.type='button';
    foot.append(cancel,start);
    dialog.append(head,intro,group,foot);overlay.append(backdrop,dialog);

    function select(value){
      choice=value;
      Object.keys(cards).forEach(function(key){var on=key===value;cards[key].setAttribute('aria-checked',String(on));cards[key].tabIndex=on?0:-1;cards[key].classList.toggle('is-selected',on)});
    }
    function finish(value){
      if(!open)return;
      if(value)store(PROFILE_KEY,value);
      overlay.remove();document.body.classList.remove('has-sm-encode');open=null;
      if(previousFocus&&previousFocus.isConnected)try{previousFocus.focus({preventScroll:true})}catch(e){}
      resolveFn(value||null);
    }
    backdrop.onclick=closeButton.onclick=cancel.onclick=function(){finish(null)};
    start.onclick=function(){finish(choice)};
    overlay.addEventListener('keydown',function(event){
      if(event.key==='Escape'){event.preventDefault();finish(null);return}
      if((event.key==='ArrowDown'||event.key==='ArrowUp'||event.key==='ArrowLeft'||event.key==='ArrowRight')&&group.contains(document.activeElement)){
        event.preventDefault();var next=choice==='max'?'standard':'max';select(next);cards[next].focus();return;
      }
      if(event.key==='Enter'&&group.contains(document.activeElement)){event.preventDefault();finish(choice);return}
      if(event.key!=='Tab')return;
      var focusable=[].slice.call(dialog.querySelectorAll('button')).filter(function(b){return b.tabIndex!==-1&&!b.disabled});
      var first=focusable[0],last=focusable[focusable.length-1];
      if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}
      else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}
    });
    select(choice);
    document.body.append(overlay);document.body.classList.add('has-sm-encode');
    open={promise:promise};
    requestAnimationFrame(function(){start.focus({preventScroll:true})});
    return promise;
  }

  /* --------------------------------------------- "also put in the ZIP" */
  function savedExtras(){
    var raw=load(EXTRAS_KEY)||'';
    return {original:raw.indexOf('original')>=0,preview:raw.indexOf('preview')>=0};
  }
  var mounted=[];
  function mountExtras(container,opts){
    if(!container)return null;
    opts=opts||{};
    var box=node('fieldset','sm-extras'+(opts.className?' '+opts.className:''));
    var legend=node('legend','sm-extras__title');box.append(legend);
    var state=savedExtras(),inputs={};
    ['original','preview'].forEach(function(key){
      var label=node('label','sm-extras__item'),input=node('input');input.type='checkbox';input.checked=!!state[key];input.dataset.extra=key;
      if(opts.idPrefix)input.id=opts.idPrefix+key.charAt(0).toUpperCase()+key.slice(1);
      var text=node('span','sm-extras__text');text.append(node('b'),node('small'));
      label.append(input,text);box.append(label);inputs[key]=input;
      input.addEventListener('change',function(){
        var on=['original','preview'].filter(function(k){return inputs[k].checked});
        store(EXTRAS_KEY,on.join(','));
        // Keep every mounted copy (Process, Rows and squares) in step.
        mounted.forEach(function(other){if(other.inputs!==inputs)other.inputs[key].checked=input.checked});
        if(typeof opts.onChange==='function')opts.onChange(get());
      });
    });
    var note=node('p','sm-extras__note');box.append(note);
    function paint(){
      legend.textContent=t('extrasTitle');
      box.querySelector('[data-extra=original]').nextSibling.firstChild.textContent=t('original');
      box.querySelector('[data-extra=original]').nextSibling.lastChild.textContent=t('originalHint');
      box.querySelector('[data-extra=preview]').nextSibling.firstChild.textContent=t('preview');
      box.querySelector('[data-extra=preview]').nextSibling.lastChild.textContent=t('previewHint');
      note.textContent=t('extrasNote');
    }
    function get(){return {original:inputs.original.checked,preview:inputs.preview.checked}}
    paint();
    if(opts.before&&opts.before.parentNode===container)container.insertBefore(box,opts.before);else container.append(box);
    var handle={el:box,inputs:inputs,get:get,paint:paint};
    mounted.push(handle);
    return handle;
  }
  function extras(){return mounted.length?mounted[0].get():savedExtras()}

  function append(form,profile,picked){
    picked=picked||extras();
    form.append('encode_profile',profile||lastProfile());
    form.append('include_original',picked.original?'1':'0');
    form.append('include_preview',picked.preview?'1':'0');
    return form;
  }

  window.addEventListener('sm:langchange',function(){setTimeout(function(){mounted.forEach(function(m){m.paint()})},0)});
  // Process: the switches live in "Quality and format", above the smart compression note.
  var processAdvanced=document.getElementById('processAdvanced');
  if(processAdvanced)mountExtras(processAdvanced,{before:processAdvanced.querySelector(':scope > .steam-opt-row'),idPrefix:'processExtra'});
  window.SMEncodeChoice={ask:ask,isAnimatedFile:isAnimatedFile,mountExtras:mountExtras,extras:extras,append:append,lastProfile:lastProfile,t:t};
})();
