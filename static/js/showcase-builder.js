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
  var catalogLoading = false;
  var catalogDone = false;
  var catalogGeneration = 0;
  var currentProjectId = '';
  var dragging = null;
  var editorHistory = null;
  var previewBackdrop = 'project';
  var snapEnabled = true;
  var exportingCanvas = false;
  var motionEngine = null;
  var chromaCache = new Map();
  var effectTextures = new Map();
  var effectTintCache = new Map();
  var effectPatternCache = new WeakMap();
  var EFFECT_ASSETS = {
    petals:'/static/assets/builder/effects/petals.png?v=small-2',
    snow:'/static/assets/builder/effects/snow.png?v=small-2',
    rain:'/static/assets/builder/effects/rain.png?v=small-2',
    lightning:'/static/assets/builder/effects/lightning.png?v=small-2'
  };
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
    en:{templates:'Quick templates','templates-hint':'Adds a coordinated title, frame and effect without replacing your media.','template-neon':'Neon title','template-neon-hint':'Cyan frame and particles','template-minimal':'Clean label','template-minimal-hint':'Quiet bottom signature','template-cinematic':'Cinematic','template-cinematic-hint':'Wide title and light streaks',snap:'Smart guides',backdrop:'Edge check','backdrop-project':'Project preview','backdrop-dark':'Dark background','backdrop-light':'Light background','backdrop-checker':'Transparency grid',shortcuts:'Arrow keys: move · Shift: 10 px · Ctrl/Cmd+D: duplicate',duplicate:'Duplicate',lock:'Lock',unlock:'Unlock','show-hide':'Show or hide',up:'Move up',down:'Move down','layer-locked':'Layer is locked','template-added':'Template added','buy-market':'Buy on Steam Market','buy-points':'Buy with Steam Points','ai-remove-help':'AI removal works only for still images. For GIF and video, use chromakey: the background must be a solid color.','ai-image-only':'For GIF and video, use chromakey with a solid-color background.','ai-unavailable':'AI background removal is temporarily unavailable.','ai-limit':'Background-removal limit reached. Try again later.','ai-too-large':'The image is too large for AI background removal.','ai-busy':'Background removal is busy. Try again later.'},
    ru:{templates:'Быстрые шаблоны','templates-hint':'Добавляет согласованные текст, рамку и эффект, не заменяя твои медиа.','template-neon':'Неоновый заголовок','template-neon-hint':'Голубая рамка и частицы','template-minimal':'Чистая подпись','template-minimal-hint':'Спокойная подпись снизу','template-cinematic':'Кинематографичный','template-cinematic-hint':'Широкий заголовок и световые линии',snap:'Умные направляющие',backdrop:'Проверка края','backdrop-project':'Предпросмотр проекта','backdrop-dark':'Тёмный фон','backdrop-light':'Светлый фон','backdrop-checker':'Сетка прозрачности',shortcuts:'Стрелки: перемещение · Shift: 10 px · Ctrl/Cmd+D: дубликат',duplicate:'Дублировать',lock:'Заблокировать',unlock:'Разблокировать','show-hide':'Показать или скрыть',up:'Поднять выше',down:'Опустить ниже','layer-locked':'Слой заблокирован','template-added':'Шаблон добавлен','buy-market':'Купить на торговой площадке','buy-points':'Купить за очки Steam','ai-remove-help':'Удаление через ИИ работает только для статичных изображений. Для GIF и видео используй хромакей: фон должен быть однотонным.','ai-image-only':'Для GIF и видео используй хромакей с однотонным фоном.','ai-unavailable':'Удаление фона через ИИ временно недоступно.','ai-limit':'Лимит удаления фона исчерпан. Попробуй позже.','ai-too-large':'Изображение слишком большое для удаления фона через ИИ.','ai-busy':'Сервис удаления фона занят. Попробуй позже.'},
    de:{templates:'Schnellvorlagen','templates-hint':'Fügt abgestimmten Titel, Rahmen und Effekt hinzu, ohne Medien zu ersetzen.','template-neon':'Neon-Titel','template-neon-hint':'Cyan-Rahmen und Partikel','template-minimal':'Klare Signatur','template-minimal-hint':'Ruhige Signatur unten','template-cinematic':'Filmisch','template-cinematic-hint':'Breiter Titel und Lichtstreifen',snap:'Intelligente Hilfslinien',backdrop:'Kantenprüfung','backdrop-project':'Projektvorschau','backdrop-dark':'Dunkler Hintergrund','backdrop-light':'Heller Hintergrund','backdrop-checker':'Transparenzraster',shortcuts:'Pfeiltasten: bewegen · Umschalt: 10 px · Strg/Cmd+D: duplizieren',duplicate:'Duplizieren',lock:'Sperren',unlock:'Entsperren','show-hide':'Ein- oder ausblenden',up:'Nach oben',down:'Nach unten','layer-locked':'Ebene ist gesperrt','template-added':'Vorlage hinzugefügt','buy-market':'Auf dem Steam-Markt kaufen','buy-points':'Mit Steam-Punkten kaufen','ai-remove-help':'KI-Freistellung funktioniert nur bei statischen Bildern. Verwende für GIFs und Videos Chroma-Key: Der Hintergrund muss einfarbig sein.','ai-image-only':'Verwende für GIFs und Videos Chroma-Key mit einfarbigem Hintergrund.','ai-unavailable':'Die KI-Freistellung ist vorübergehend nicht verfügbar.','ai-limit':'Das Limit für die Hintergrundentfernung ist erreicht. Versuche es später erneut.','ai-too-large':'Das Bild ist für die KI-Freistellung zu groß.','ai-busy':'Die Hintergrundentfernung ist ausgelastet. Versuche es später erneut.'},
    tr:{templates:'Hızlı şablonlar','templates-hint':'Medyanızı değiştirmeden uyumlu başlık, çerçeve ve efekt ekler.','template-neon':'Neon başlık','template-neon-hint':'Camgöbeği çerçeve ve parçacıklar','template-minimal':'Sade imza','template-minimal-hint':'Altta sakin bir imza','template-cinematic':'Sinematik','template-cinematic-hint':'Geniş başlık ve ışık çizgileri',snap:'Akıllı kılavuzlar',backdrop:'Kenar denetimi','backdrop-project':'Proje önizlemesi','backdrop-dark':'Koyu arka plan','backdrop-light':'Açık arka plan','backdrop-checker':'Saydamlık ızgarası',shortcuts:'Ok tuşları: taşı · Shift: 10 px · Ctrl/Cmd+D: çoğalt',duplicate:'Çoğalt',lock:'Kilitle',unlock:'Kilidi aç','show-hide':'Göster veya gizle',up:'Yukarı taşı',down:'Aşağı taşı','layer-locked':'Katman kilitli','template-added':'Şablon eklendi','buy-market':'Steam Pazarından satın al','buy-points':'Steam Puanlarıyla satın al','ai-remove-help':'Yapay zekâ ile arka plan kaldırma yalnızca sabit görüntülerde çalışır. GIF ve videolar için chroma key kullanın; arka plan tek renk olmalıdır.','ai-image-only':'GIF ve videolar için tek renkli arka planla chroma key kullanın.','ai-unavailable':'Yapay zekâ ile arka plan kaldırma geçici olarak kullanılamıyor.','ai-limit':'Arka plan kaldırma sınırına ulaşıldı. Daha sonra tekrar deneyin.','ai-too-large':'Görüntü, yapay zekâ ile arka plan kaldırma için çok büyük.','ai-busy':'Arka plan kaldırma servisi meşgul. Daha sonra tekrar deneyin.'},
    fr:{templates:'Modèles rapides','templates-hint':'Ajoute un titre, un cadre et un effet coordonnés sans remplacer vos médias.','template-neon':'Titre néon','template-neon-hint':'Cadre cyan et particules','template-minimal':'Signature épurée','template-minimal-hint':'Signature discrète en bas','template-cinematic':'Cinématique','template-cinematic-hint':'Titre large et traînées lumineuses',snap:'Repères intelligents',backdrop:'Contrôle des bords','backdrop-project':'Aperçu du projet','backdrop-dark':'Fond sombre','backdrop-light':'Fond clair','backdrop-checker':'Grille de transparence',shortcuts:'Flèches : déplacer · Maj : 10 px · Ctrl/Cmd+D : dupliquer',duplicate:'Dupliquer',lock:'Verrouiller',unlock:'Déverrouiller','show-hide':'Afficher ou masquer',up:'Monter',down:'Descendre','layer-locked':'Le calque est verrouillé','template-added':'Modèle ajouté','buy-market':'Acheter sur le marché Steam','buy-points':'Acheter avec des points Steam','ai-remove-help':'La suppression par IA fonctionne uniquement avec les images fixes. Pour les GIF et vidéos, utilisez l’incrustation chromatique : le fond doit être uni.','ai-image-only':'Pour les GIF et vidéos, utilisez l’incrustation chromatique sur un fond uni.','ai-unavailable':'La suppression de fond par IA est temporairement indisponible.','ai-limit':'La limite de suppression de fond est atteinte. Réessayez plus tard.','ai-too-large':'L’image est trop grande pour la suppression de fond par IA.','ai-busy':'Le service de suppression de fond est occupé. Réessayez plus tard.'},
    uk:{templates:'Швидкі шаблони','templates-hint':'Додає узгоджені текст, рамку й ефект, не замінюючи медіа.','template-neon':'Неоновий заголовок','template-neon-hint':'Блакитна рамка й частинки','template-minimal':'Чистий підпис','template-minimal-hint':'Стриманий підпис унизу','template-cinematic':'Кінематографічний','template-cinematic-hint':'Широкий заголовок і світлові смуги',snap:'Розумні напрямні',backdrop:'Перевірка краю','backdrop-project':'Перегляд проєкту','backdrop-dark':'Темне тло','backdrop-light':'Світле тло','backdrop-checker':'Сітка прозорості',shortcuts:'Стрілки: переміщення · Shift: 10 px · Ctrl/Cmd+D: дублювати',duplicate:'Дублювати',lock:'Заблокувати',unlock:'Розблокувати','show-hide':'Показати або приховати',up:'Підняти вище',down:'Опустити нижче','layer-locked':'Шар заблоковано','template-added':'Шаблон додано','buy-market':'Купити на торговельному майданчику','buy-points':'Купити за бали Steam','ai-remove-help':'Видалення через ШІ працює лише зі статичними зображеннями. Для GIF і відео використовуй хромакей: тло має бути однотонним.','ai-image-only':'Для GIF і відео використовуй хромакей з однотонним тлом.','ai-unavailable':'Видалення тла через ШІ тимчасово недоступне.','ai-limit':'Ліміт видалення тла вичерпано. Спробуй пізніше.','ai-too-large':'Зображення завелике для видалення тла через ШІ.','ai-busy':'Сервіс видалення тла зайнятий. Спробуй пізніше.'},
    es:{templates:'Plantillas rápidas','templates-hint':'Añade título, marco y efecto coordinados sin reemplazar tus medios.','template-neon':'Título neón','template-neon-hint':'Marco cian y partículas','template-minimal':'Firma limpia','template-minimal-hint':'Firma discreta en la parte inferior','template-cinematic':'Cinemática','template-cinematic-hint':'Título ancho y trazos de luz',snap:'Guías inteligentes',backdrop:'Comprobar bordes','backdrop-project':'Vista del proyecto','backdrop-dark':'Fondo oscuro','backdrop-light':'Fondo claro','backdrop-checker':'Cuadrícula de transparencia',shortcuts:'Flechas: mover · Mayús: 10 px · Ctrl/Cmd+D: duplicar',duplicate:'Duplicar',lock:'Bloquear',unlock:'Desbloquear','show-hide':'Mostrar u ocultar',up:'Subir',down:'Bajar','layer-locked':'La capa está bloqueada','template-added':'Plantilla añadida','buy-market':'Comprar en el Mercado de Steam','buy-points':'Comprar con puntos de Steam','ai-remove-help':'La eliminación con IA solo funciona con imágenes estáticas. Para GIF y vídeos, usa croma: el fondo debe ser de un solo color.','ai-image-only':'Para GIF y vídeos, usa croma con un fondo de un solo color.','ai-unavailable':'La eliminación de fondo con IA no está disponible temporalmente.','ai-limit':'Se alcanzó el límite de eliminación de fondo. Inténtalo más tarde.','ai-too-large':'La imagen es demasiado grande para eliminar el fondo con IA.','ai-busy':'El servicio de eliminación de fondo está ocupado. Inténtalo más tarde.'},
    pt:{templates:'Modelos rápidos','templates-hint':'Adiciona título, moldura e efeito coordenados sem substituir sua mídia.','template-neon':'Título neon','template-neon-hint':'Moldura ciano e partículas','template-minimal':'Assinatura limpa','template-minimal-hint':'Assinatura discreta embaixo','template-cinematic':'Cinemático','template-cinematic-hint':'Título amplo e rastros de luz',snap:'Guias inteligentes',backdrop:'Verificar bordas','backdrop-project':'Prévia do projeto','backdrop-dark':'Fundo escuro','backdrop-light':'Fundo claro','backdrop-checker':'Grade de transparência',shortcuts:'Setas: mover · Shift: 10 px · Ctrl/Cmd+D: duplicar',duplicate:'Duplicar',lock:'Bloquear',unlock:'Desbloquear','show-hide':'Mostrar ou ocultar',up:'Mover para cima',down:'Mover para baixo','layer-locked':'A camada está bloqueada','template-added':'Modelo adicionado','buy-market':'Comprar no Mercado Steam','buy-points':'Comprar com pontos Steam','ai-remove-help':'A remoção por IA funciona apenas com imagens estáticas. Para GIFs e vídeos, use chroma key: o fundo deve ter uma única cor.','ai-image-only':'Para GIFs e vídeos, use chroma key com um fundo de cor única.','ai-unavailable':'A remoção de fundo por IA está temporariamente indisponível.','ai-limit':'O limite de remoção de fundo foi atingido. Tente novamente mais tarde.','ai-too-large':'A imagem é grande demais para a remoção de fundo por IA.','ai-busy':'O serviço de remoção de fundo está ocupado. Tente novamente mais tarde.'}
  };
  var VFX_COPY = {
    en:{'effect-petals':'Sakura petals','effect-snow':'Real snow','effect-rain':'Rain','effect-lightning':'Lightning','effect-particle':'Particle Flow','effect-stars':'Starfield Drift','effect-matrix':'Digital Matrix','effect-streaks':'Comets','effect-sparks':'Obsidian Sparks','effect-custom':'Custom overlay','effect-speed':'Speed','effect-density':'Density','frame-style':'Frame style','frame-target':'Frame layout','frame-solid':'Solid','frame-double':'Double','frame-corners':'Corners','frame-neon':'Neon glow','frame-panels':'Each Steam panel','frame-outer':'Whole canvas'},
    ru:{'effect-petals':'Лепестки сакуры','effect-snow':'Настоящий снег','effect-rain':'Дождь','effect-lightning':'Молнии','effect-particle':'Поток частиц','effect-stars':'Звёздный поток','effect-matrix':'Цифровая матрица','effect-streaks':'Кометы','effect-sparks':'Искры','effect-custom':'Свой оверлей','effect-speed':'Скорость','effect-density':'Плотность','frame-style':'Стиль рамки','frame-target':'Схема рамки','frame-solid':'Сплошная','frame-double':'Двойная','frame-corners':'Угловая','frame-neon':'Неоновое свечение','frame-panels':'Каждая панель Steam','frame-outer':'Весь холст'},
    de:{'effect-petals':'Sakura-Blüten','effect-snow':'Echter Schnee','effect-rain':'Regen','effect-lightning':'Blitze','effect-particle':'Partikelstrom','effect-stars':'Sternenstrom','effect-matrix':'Digitale Matrix','effect-streaks':'Kometen','effect-sparks':'Funken','effect-custom':'Eigenes Overlay','effect-speed':'Geschwindigkeit','effect-density':'Dichte','frame-style':'Rahmenstil','frame-target':'Rahmenlayout','frame-solid':'Durchgehend','frame-double':'Doppelt','frame-corners':'Ecken','frame-neon':'Neonleuchten','frame-panels':'Jedes Steam-Panel','frame-outer':'Gesamte Leinwand'},
    tr:{'effect-petals':'Sakura yaprakları','effect-snow':'Gerçek kar','effect-rain':'Yağmur','effect-lightning':'Şimşek','effect-particle':'Parçacık akışı','effect-stars':'Yıldız akışı','effect-matrix':'Dijital matris','effect-streaks':'Kuyruklu yıldızlar','effect-sparks':'Kıvılcımlar','effect-custom':'Özel kaplama','effect-speed':'Hız','effect-density':'Yoğunluk','frame-style':'Çerçeve stili','frame-target':'Çerçeve düzeni','frame-solid':'Düz','frame-double':'Çift','frame-corners':'Köşeler','frame-neon':'Neon parıltı','frame-panels':'Her Steam paneli','frame-outer':'Tüm tuval'},
    fr:{'effect-petals':'Pétales de sakura','effect-snow':'Neige réaliste','effect-rain':'Pluie','effect-lightning':'Éclairs','effect-particle':'Flux de particules','effect-stars':'Dérive stellaire','effect-matrix':'Matrice numérique','effect-streaks':'Comètes','effect-sparks':'Étincelles','effect-custom':'Superposition personnalisée','effect-speed':'Vitesse','effect-density':'Densité','frame-style':'Style du cadre','frame-target':'Disposition du cadre','frame-solid':'Continu','frame-double':'Double','frame-corners':'Angles','frame-neon':'Lueur néon','frame-panels':'Chaque panneau Steam','frame-outer':'Toute la toile'},
    uk:{'effect-petals':'Пелюстки сакури','effect-snow':'Справжній сніг','effect-rain':'Дощ','effect-lightning':'Блискавки','effect-particle':'Потік частинок','effect-stars':'Зоряний потік','effect-matrix':'Цифрова матриця','effect-streaks':'Комети','effect-sparks':'Іскри','effect-custom':'Власний оверлей','effect-speed':'Швидкість','effect-density':'Щільність','frame-style':'Стиль рамки','frame-target':'Схема рамки','frame-solid':'Суцільна','frame-double':'Подвійна','frame-corners':'Кутова','frame-neon':'Неонове сяйво','frame-panels':'Кожна панель Steam','frame-outer':'Усе полотно'},
    es:{'effect-petals':'Pétalos de sakura','effect-snow':'Nieve realista','effect-rain':'Lluvia','effect-lightning':'Relámpagos','effect-particle':'Flujo de partículas','effect-stars':'Deriva estelar','effect-matrix':'Matriz digital','effect-streaks':'Cometas','effect-sparks':'Chispas','effect-custom':'Superposición propia','effect-speed':'Velocidad','effect-density':'Densidad','frame-style':'Estilo del marco','frame-target':'Diseño del marco','frame-solid':'Sólido','frame-double':'Doble','frame-corners':'Esquinas','frame-neon':'Brillo neón','frame-panels':'Cada panel de Steam','frame-outer':'Todo el lienzo'},
    pt:{'effect-petals':'Pétalas de sakura','effect-snow':'Neve realista','effect-rain':'Chuva','effect-lightning':'Relâmpagos','effect-particle':'Fluxo de partículas','effect-stars':'Deriva estelar','effect-matrix':'Matriz digital','effect-streaks':'Cometas','effect-sparks':'Faíscas','effect-custom':'Sobreposição própria','effect-speed':'Velocidade','effect-density':'Densidade','frame-style':'Estilo da moldura','frame-target':'Layout da moldura','frame-solid':'Sólida','frame-double':'Dupla','frame-corners':'Cantos','frame-neon':'Brilho neon','frame-panels':'Cada painel Steam','frame-outer':'Tela inteira'}
  };
  var GRADE_COPY = {
    en:{'grade-title':'Color correction','grade-reset':'Reset','grade-hint':'Select a character or background to match its colors to the scene.','grade-brightness':'Brightness','grade-contrast':'Contrast','grade-saturation':'Saturation','grade-hue':'Hue'},
    ru:{'grade-title':'Цветокоррекция','grade-reset':'Сбросить','grade-hint':'Выбери персонажа или фон, чтобы подогнать цвета под сцену.','grade-brightness':'Яркость','grade-contrast':'Контраст','grade-saturation':'Насыщенность','grade-hue':'Оттенок'},
    de:{'grade-title':'Farbkorrektur','grade-reset':'Zurücksetzen','grade-hint':'Wähle eine Figur oder einen Hintergrund, um die Farben an die Szene anzupassen.','grade-brightness':'Helligkeit','grade-contrast':'Kontrast','grade-saturation':'Sättigung','grade-hue':'Farbton'},
    tr:{'grade-title':'Renk düzeltme','grade-reset':'Sıfırla','grade-hint':'Renkleri sahneye uydurmak için karakter veya arka plan seç.','grade-brightness':'Parlaklık','grade-contrast':'Kontrast','grade-saturation':'Doygunluk','grade-hue':'Renk tonu'},
    fr:{'grade-title':'Correction des couleurs','grade-reset':'Réinitialiser','grade-hint':'Choisissez un personnage ou un fond pour harmoniser les couleurs avec la scène.','grade-brightness':'Luminosité','grade-contrast':'Contraste','grade-saturation':'Saturation','grade-hue':'Teinte'},
    uk:{'grade-title':'Корекція кольору','grade-reset':'Скинути','grade-hint':'Обери персонажа або тло, щоб узгодити кольори зі сценою.','grade-brightness':'Яскравість','grade-contrast':'Контраст','grade-saturation':'Насиченість','grade-hue':'Відтінок'},
    es:{'grade-title':'Corrección de color','grade-reset':'Restablecer','grade-hint':'Elige un personaje o fondo para ajustar sus colores a la escena.','grade-brightness':'Brillo','grade-contrast':'Contraste','grade-saturation':'Saturación','grade-hue':'Tono'},
    pt:{'grade-title':'Correção de cor','grade-reset':'Redefinir','grade-hint':'Escolha um personagem ou fundo para combinar as cores com a cena.','grade-brightness':'Brilho','grade-contrast':'Contraste','grade-saturation':'Saturação','grade-hue':'Matiz'}
  };
  var BG_COPY = {
    en:{"mode-workshop": "Workshop", "mode-featured": "One large artwork", "mode-split": "Artwork + side panel", "mode-workshop-hint": "Workshop Showcase: five files side by side", "mode-featured-hint": "Featured Artwork Showcase: one large picture", "mode-split-hint": "Artwork Showcase: two files, 506 + 100 px", "chroma-key-green": "Green", "chroma-key-blue": "Blue", "chroma-key-custom": "My colour…", "chroma-color": "Backdrop colour", "chroma-holes": "Remove backdrop between arms and legs", "chroma-holes-hint": "Pockets of the backdrop colour closed off by the figure. Small ones (eyes, highlights) always stay.", "chroma-key": "Background to remove", "chroma-key-auto": "Detect automatically", "chroma-key-color": "Coloured (green screen)", "chroma-key-black": "Black", "chroma-key-white": "White", "ai-model": "AI model", "ai-model-auto": "Automatic (best available)", "ai-model-modal": "ShowcaseMaker AI (best quality)", "ai-model-iloveapi": "iLoveAPI", "ai-model-problembo": "Problembo", "ai-model-removebg": "remove.bg", "ai-note-modal": "The first removal after a pause can take up to a minute while our AI server starts. The next ones take a few seconds.", "ai-note-auto": "If a service is unavailable, the next one takes over automatically.", "ai-waking": "Starting the AI server, the first image takes up to a minute…", "ai-fallback": "{from} was unavailable, so the background was removed with {to}.", "ai-remove-help": "AI removal works only for still images. For GIF and video, use chromakey: it removes a solid colour, black or white background."},
    ru:{"mode-workshop": "Мастерская", "mode-featured": "Избранная иллюстрация", "mode-split": "Витрина иллюстраций", "mode-workshop-hint": "«Витрина мастерской» в Steam: пять файлов в ряд", "mode-featured-hint": "Одна большая картинка шириной 630 px", "mode-split-hint": "Два файла: центральный 506 px и боковой 100 px", "chroma-key-green": "Зелёный", "chroma-key-blue": "Синий", "chroma-key-custom": "Свой цвет…", "chroma-color": "Цвет фона", "chroma-holes": "Убирать фон в просветах (между руками, ногами)", "chroma-holes-hint": "Участки цвета фона, закрытые персонажем. Маленькие (глаза, блики) всегда остаются.", "chroma-key": "Какой фон убрать", "chroma-key-auto": "Определить автоматически", "chroma-key-color": "Цветной (хромакей)", "chroma-key-black": "Чёрный", "chroma-key-white": "Белый", "ai-model": "Модель ИИ", "ai-model-auto": "Автоматически (лучшая доступная)", "ai-model-modal": "ИИ ShowcaseMaker (лучшее качество)", "ai-model-iloveapi": "iLoveAPI", "ai-model-problembo": "Problembo", "ai-model-removebg": "remove.bg", "ai-note-modal": "Первое удаление после перерыва может занять до минуты: запускается наш ИИ-сервер. Следующие — несколько секунд.", "ai-note-auto": "Если сервис недоступен, автоматически подключится следующий.", "ai-waking": "Запускаем ИИ-сервер, первая картинка занимает до минуты…", "ai-fallback": "{from} был недоступен, поэтому фон удалён через {to}.", "ai-remove-help": "Удаление через ИИ работает только для статичных изображений. Для GIF и видео используй хромакей: он убирает однотонный, чёрный или белый фон."},
    de:{"mode-workshop": "Workshop", "mode-featured": "Ein großes Artwork", "mode-split": "Artwork + Seitenpanel", "mode-workshop-hint": "Workshop-Vitrine: fünf Dateien nebeneinander", "mode-featured-hint": "Vitrine „Hauptkunstwerk“: ein großes Bild", "mode-split-hint": "Kunstwerk-Vitrine: zwei Dateien, 506 + 100 px", "chroma-key-green": "Grün", "chroma-key-blue": "Blau", "chroma-key-custom": "Eigene Farbe…", "chroma-color": "Hintergrundfarbe", "chroma-holes": "Hintergrund zwischen Armen und Beinen entfernen", "chroma-holes-hint": "Vom Motiv umschlossene Flächen in Hintergrundfarbe. Kleine (Augen, Glanzlichter) bleiben immer.", "chroma-key": "Zu entfernender Hintergrund", "chroma-key-auto": "Automatisch erkennen", "chroma-key-color": "Farbig (Greenscreen)", "chroma-key-black": "Schwarz", "chroma-key-white": "Weiß", "ai-model": "KI-Modell", "ai-model-auto": "Automatisch (bestes verfügbares)", "ai-model-modal": "ShowcaseMaker-KI (beste Qualität)", "ai-model-iloveapi": "iLoveAPI", "ai-model-problembo": "Problembo", "ai-model-removebg": "remove.bg", "ai-note-modal": "Die erste Freistellung nach einer Pause kann bis zu einer Minute dauern, während unser KI-Server startet. Danach dauert es nur wenige Sekunden.", "ai-note-auto": "Ist ein Dienst nicht erreichbar, übernimmt automatisch der nächste.", "ai-waking": "KI-Server startet, das erste Bild dauert bis zu einer Minute…", "ai-fallback": "{from} war nicht erreichbar, daher wurde der Hintergrund mit {to} entfernt.", "ai-remove-help": "KI-Freistellung funktioniert nur bei statischen Bildern. Verwende für GIFs und Videos Chroma-Key: Er entfernt einen einfarbigen, schwarzen oder weißen Hintergrund."},
    tr:{"mode-workshop": "Atölye", "mode-featured": "Tek büyük çizim", "mode-split": "Çizim + yan panel", "mode-workshop-hint": "Atölye vitrini: yan yana beş dosya", "mode-featured-hint": "Öne çıkan çizim vitrini: tek büyük resim", "mode-split-hint": "Çizim vitrini: iki dosya, 506 + 100 px", "chroma-key-green": "Yeşil", "chroma-key-blue": "Mavi", "chroma-key-custom": "Kendi rengim…", "chroma-color": "Arka plan rengi", "chroma-holes": "Kollar ve bacaklar arasındaki arka planı kaldır", "chroma-holes-hint": "Figürün kapattığı arka plan renginde alanlar. Küçükler (gözler, parlamalar) her zaman kalır.", "chroma-key": "Kaldırılacak arka plan", "chroma-key-auto": "Otomatik algıla", "chroma-key-color": "Renkli (yeşil perde)", "chroma-key-black": "Siyah", "chroma-key-white": "Beyaz", "ai-model": "Yapay zekâ modeli", "ai-model-auto": "Otomatik (en iyi kullanılabilir)", "ai-model-modal": "ShowcaseMaker yapay zekâsı (en iyi kalite)", "ai-model-iloveapi": "iLoveAPI", "ai-model-problembo": "Problembo", "ai-model-removebg": "remove.bg", "ai-note-modal": "Bir aradan sonraki ilk kaldırma, yapay zekâ sunucumuz başlarken bir dakikaya kadar sürebilir. Sonrakiler birkaç saniye sürer.", "ai-note-auto": "Bir hizmet kullanılamıyorsa sıradaki otomatik olarak devreye girer.", "ai-waking": "Yapay zekâ sunucusu başlatılıyor, ilk görsel bir dakikaya kadar sürer…", "ai-fallback": "{from} kullanılamadığı için arka plan {to} ile kaldırıldı.", "ai-remove-help": "Yapay zekâ ile arka plan kaldırma yalnızca sabit görüntülerde çalışır. GIF ve videolar için chroma key kullanın: tek renkli, siyah veya beyaz arka planı kaldırır."},
    fr:{"mode-workshop": "Workshop", "mode-featured": "Une grande illustration", "mode-split": "Illustration + panneau latéral", "mode-workshop-hint": "Vitrine Workshop : cinq fichiers côte à côte", "mode-featured-hint": "Vitrine « Illustration vedette » : une grande image", "mode-split-hint": "Vitrine d’illustrations : deux fichiers, 506 + 100 px", "chroma-key-green": "Vert", "chroma-key-blue": "Bleu", "chroma-key-custom": "Ma couleur…", "chroma-color": "Couleur du fond", "chroma-holes": "Retirer le fond entre les bras et les jambes", "chroma-holes-hint": "Zones de la couleur du fond fermées par le personnage. Les petites (yeux, reflets) restent toujours.", "chroma-key": "Fond à supprimer", "chroma-key-auto": "Détecter automatiquement", "chroma-key-color": "Coloré (fond vert)", "chroma-key-black": "Noir", "chroma-key-white": "Blanc", "ai-model": "Modèle d’IA", "ai-model-auto": "Automatique (le meilleur disponible)", "ai-model-modal": "IA ShowcaseMaker (meilleure qualité)", "ai-model-iloveapi": "iLoveAPI", "ai-model-problembo": "Problembo", "ai-model-removebg": "remove.bg", "ai-note-modal": "Après une pause, la première suppression peut prendre jusqu’à une minute, le temps que notre serveur d’IA démarre. Les suivantes prennent quelques secondes.", "ai-note-auto": "Si un service est indisponible, le suivant prend le relais automatiquement.", "ai-waking": "Démarrage du serveur d’IA, la première image prend jusqu’à une minute…", "ai-fallback": "{from} était indisponible, le fond a donc été supprimé avec {to}.", "ai-remove-help": "La suppression par IA fonctionne uniquement avec les images fixes. Pour les GIF et vidéos, utilisez l’incrustation chromatique : elle retire un fond uni, noir ou blanc."},
    uk:{"mode-workshop": "Майстерня", "mode-featured": "Одна велика ілюстрація", "mode-split": "Ілюстрація + бічна частина", "mode-workshop-hint": "«Вітрина майстерні»: п’ять файлів у ряд", "mode-featured-hint": "«Обрана ілюстрація»: одна велика картинка", "mode-split-hint": "«Вітрина ілюстрацій»: два файли, 506 + 100 px", "chroma-key-green": "Зелений", "chroma-key-blue": "Синій", "chroma-key-custom": "Свій колір…", "chroma-color": "Колір фону", "chroma-holes": "Прибирати фон у просвітах (між руками, ногами)", "chroma-holes-hint": "Ділянки кольору фону, закриті персонажем. Маленькі (очі, відблиски) завжди лишаються.", "chroma-key": "Який фон прибрати", "chroma-key-auto": "Визначити автоматично", "chroma-key-color": "Кольоровий (хромакей)", "chroma-key-black": "Чорний", "chroma-key-white": "Білий", "ai-model": "Модель ШІ", "ai-model-auto": "Автоматично (найкраща доступна)", "ai-model-modal": "ШІ ShowcaseMaker (найкраща якість)", "ai-model-iloveapi": "iLoveAPI", "ai-model-problembo": "Problembo", "ai-model-removebg": "remove.bg", "ai-note-modal": "Перше видалення після перерви може тривати до хвилини: запускається наш ШІ-сервер. Наступні — кілька секунд.", "ai-note-auto": "Якщо сервіс недоступний, автоматично підключиться наступний.", "ai-waking": "Запускаємо ШІ-сервер, перше зображення займає до хвилини…", "ai-fallback": "{from} був недоступний, тому фон видалено через {to}.", "ai-remove-help": "Видалення через ШІ працює лише зі статичними зображеннями. Для GIF і відео використовуй хромакей: він прибирає однотонний, чорний або білий фон."},
    es:{"mode-workshop": "Workshop", "mode-featured": "Una ilustración grande", "mode-split": "Ilustración + panel lateral", "mode-workshop-hint": "Escaparate de Workshop: cinco archivos en fila", "mode-featured-hint": "Escaparate de ilustración destacada: una imagen grande", "mode-split-hint": "Escaparate de ilustraciones: dos archivos, 506 + 100 px", "chroma-key-green": "Verde", "chroma-key-blue": "Azul", "chroma-key-custom": "Mi color…", "chroma-color": "Color del fondo", "chroma-holes": "Quitar el fondo entre brazos y piernas", "chroma-holes-hint": "Zonas del color del fondo cerradas por la figura. Las pequeñas (ojos, brillos) siempre se quedan.", "chroma-key": "Fondo que quitar", "chroma-key-auto": "Detectar automáticamente", "chroma-key-color": "De color (croma)", "chroma-key-black": "Negro", "chroma-key-white": "Blanco", "ai-model": "Modelo de IA", "ai-model-auto": "Automático (el mejor disponible)", "ai-model-modal": "IA de ShowcaseMaker (mejor calidad)", "ai-model-iloveapi": "iLoveAPI", "ai-model-problembo": "Problembo", "ai-model-removebg": "remove.bg", "ai-note-modal": "Tras una pausa, la primera eliminación puede tardar hasta un minuto mientras arranca nuestro servidor de IA. Las siguientes tardan unos segundos.", "ai-note-auto": "Si un servicio no está disponible, el siguiente toma el relevo automáticamente.", "ai-waking": "Iniciando el servidor de IA, la primera imagen tarda hasta un minuto…", "ai-fallback": "{from} no estaba disponible, así que el fondo se quitó con {to}.", "ai-remove-help": "La eliminación con IA solo funciona con imágenes estáticas. Para GIF y vídeos, usa croma: quita un fondo de un solo color, negro o blanco."},
    pt:{"mode-workshop": "Oficina", "mode-featured": "Uma ilustração grande", "mode-split": "Ilustração + painel lateral", "mode-workshop-hint": "Vitrine do Workshop: cinco arquivos lado a lado", "mode-featured-hint": "Vitrine de ilustração em destaque: uma imagem grande", "mode-split-hint": "Vitrine de ilustrações: dois arquivos, 506 + 100 px", "chroma-key-green": "Verde", "chroma-key-blue": "Azul", "chroma-key-custom": "Minha cor…", "chroma-color": "Cor do fundo", "chroma-holes": "Remover o fundo entre braços e pernas", "chroma-holes-hint": "Áreas da cor do fundo fechadas pela figura. As pequenas (olhos, brilhos) sempre ficam.", "chroma-key": "Fundo a remover", "chroma-key-auto": "Detectar automaticamente", "chroma-key-color": "Colorido (chroma key)", "chroma-key-black": "Preto", "chroma-key-white": "Branco", "ai-model": "Modelo de IA", "ai-model-auto": "Automático (o melhor disponível)", "ai-model-modal": "IA do ShowcaseMaker (melhor qualidade)", "ai-model-iloveapi": "iLoveAPI", "ai-model-problembo": "Problembo", "ai-model-removebg": "remove.bg", "ai-note-modal": "Após uma pausa, a primeira remoção pode levar até um minuto enquanto nosso servidor de IA inicia. As seguintes levam poucos segundos.", "ai-note-auto": "Se um serviço estiver indisponível, o próximo assume automaticamente.", "ai-waking": "Iniciando o servidor de IA, a primeira imagem leva até um minuto…", "ai-fallback": "{from} estava indisponível, então o fundo foi removido com {to}.", "ai-remove-help": "A remoção por IA funciona apenas com imagens estáticas. Para GIFs e vídeos, use chroma key: remove um fundo de cor única, preto ou branco."}
  };
  if (window.SMLang && SMLang.extend) SMLang.extend(COPY);
  Object.keys(NEW_COPY).forEach(function(language){COPY[language]=Object.assign({},COPY[language]||{},NEW_COPY[language],VFX_COPY[language]||{},GRADE_COPY[language]||{},BG_COPY[language]||{})});

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
    if(type==='background'||type==='character')common.grade=SMColorGrade.normalize();
    if(type==='background')Object.assign(common,{x:.5,y:.5,scale:1,chroma:false,chromaKey:'auto',chromaTolerance:45,chromaFeather:16});
    if(type==='character')Object.assign(common,{chroma:false,chromaKey:'auto',chromaTolerance:45,chromaFeather:16});
    if(type==='text')Object.assign(common,{text:lang()==='ru'?'ТВОЯ ВИТРИНА':'YOUR SHOWCASE',font:'Mulish',fontSize:64,color:'#ffffff',y:.18});
    if(type==='frame')Object.assign(common,{color:'#52d5ff',frameWidth:4,frameStyle:'solid',frameTarget:'panels',frameShape:'rect',framePlate:0});
    if(type==='effect')Object.assign(common,{effect:'petals',name:t('effect-petals'),color:'#ff9fc8',effectSpeed:100,effectDensity:100});
    return common;
  }

  /* Steam's CDN sends Access-Control-Allow-Origin: * and supports byte ranges, so the browser
     loads Steam media directly (fast, video starts before the whole file arrives). The
     shared.cloudflare host answers with a redirect WITHOUT CORS headers, so it is rewritten to
     its target host. proxySource() is the fallback when the direct load fails. */
  function isSteamMedia(url){return /^https:\/\/(shared|cdn)\.cloudflare\.steamstatic\.com\//i.test(url||'')}
  function proxySource(url){return '/api/steam/proxy-image?url='+encodeURIComponent(url)}
  function safeSource(url) {
    if (isSteamMedia(url)) return url.replace(/^https:\/\/shared\.cloudflare\.steamstatic\.com\//i, 'https://shared.steamstatic.com/');
    return url;
  }
  function aiRemovalEligible(layer) {
    if(!layer||!layer.src||!layer.src.startsWith('/api/builder/assets/'))return false;
    if(layer.animatedSource)return false;
    var mediaType=String(layer.mediaType||'').toLowerCase();
    if(mediaType==='image/gif'||mediaType.indexOf('video/')===0)return false;
    return !/\.(?:gif|mp4|webm|mov)(?:\?|$)/i.test(layer.src);
  }
  function aiRemovalMessage(data) {
    var code=typeof data==='string'?data:(data&&(data.code||data.error_code));
    var messages={image_only:'ai-image-only',invalid_image:'ai-image-only',image_too_large:'ai-too-large',not_configured:'ai-unavailable',provider_unavailable:'ai-unavailable',invalid_result:'ai-unavailable',provider_busy:'ai-busy',remove_bg_limit:'ai-limit'};
    return t(messages[code]||'failed');
  }
  function mediaFor(layer) {
    if (!layer || !layer.src) return null;
    var key=layer.id+'|'+layer.src;
    if(media.has(key))return media.get(key);
    var isVideo=layer.mediaType&&layer.mediaType.indexOf('video/')===0 || /\.(mp4|webm|mov)(\?|$)/i.test(layer.src);
    var node=document.createElement(isVideo?'video':'img');
    if(isVideo){node.muted=true;node.loop=true;node.playsInline=true;node.autoplay=true}
    node.crossOrigin='anonymous';node.addEventListener(isVideo?'loadeddata':'load',markDirty);
    if(isSteamMedia(layer.src))node.addEventListener('error',function(){if(node.dataset.viaProxy)return;node.dataset.viaProxy='1';node.src=proxySource(layer.src);if(isVideo)node.play().catch(function(){})});
    if(isVideo||/\.gif(\?|$)/i.test(layer.src)||layer.mediaType==='image/gif')watchLoading(node,layer,isVideo);
    node.src=safeSource(layer.src);
    if(isVideo)node.play().catch(function(){});
    media.set(key,node);return node;
  }
  /* Big animated backgrounds can take a while on a slow connection: report progress to the
     stage (builder-layout.js shows a notice) so the editor never looks frozen. */
  function watchLoading(node,layer,isVideo){
    var name=layer.name||'',done=false;
    function emit(state,pct){root.dispatchEvent(new CustomEvent('sm:builder-media',{detail:{id:layer.id,name:name,state:state,pct:pct}}))}
    function progress(){if(done||!isVideo||!node.duration||!node.buffered.length)return;emit('loading',Math.min(99,Math.round(node.buffered.end(node.buffered.length-1)/node.duration*100)))}
    function finish(state){if(done)return;if(state==='error'&&!node.dataset.viaProxy&&isSteamMedia(layer.src))return;done=true;emit(state)}
    emit('loading',null);
    node.addEventListener('progress',progress);
    node.addEventListener(isVideo?'canplay':'load',function(){finish('ready')});
    node.addEventListener('error',function(){setTimeout(function(){finish('error')},0)});
  }
  function mediaSize(node){return [node.videoWidth||node.naturalWidth||node.displayWidth||node.width||1,node.videoHeight||node.naturalHeight||node.displayHeight||node.height||1]}
  function coverBox(node) {
    var nw=mediaSize(node)[0],nh=mediaSize(node)[1];
    var s=Math.max(canvas.width/nw,canvas.height/nh);return {w:nw*s,h:nh*s};
  }
  function containBox(node, layer) {
    var nw=mediaSize(node)[0],nh=mediaSize(node)[1];
    var base=Math.min(canvas.width/nw,canvas.height/nh);return {w:nw*base*layer.scale,h:nh*base*layer.scale};
  }
  /* Angular speed (rad/ms) close to `base` that makes whole cycles in the scene length. */
  function loopRate(base){var ms=Math.max(1,Number(project.motion&&project.motion.duration)||8)*1000,turns=Math.max(1,Math.round(base*ms/(2*Math.PI)));return turns*2*Math.PI/ms}
  function animationTransform(layer, now) {
    var power=layer.motionPower==null?1:layer.motionPower;
    if(layer.animation==='breathing'){var b=loopRate(.0023);return {scale:1+Math.sin(now*b)*.018*power,rotate:0,y:Math.sin(now*b)*2*power}}
    if(layer.animation==='wave')return {scale:1,rotate:Math.sin(now*loopRate(.002))*.035*power,y:Math.sin(now*loopRate(.003))*3*power};
    return {scale:1,rotate:0,y:0};
  }
  function clamp(value,min,max){return Math.max(min,Math.min(max,Number(value)||0))}
  /* Chroma keying (static/js/chroma-matte.js, same engine as the server Character compose):
     the backdrop colour is measured once per clip from a few early frames, only backdrop
     connected to the edge (and big pockets) is removed, and each frame of a video/GIF keeps
     the previous frame's state so still parts do not shimmer. */
  function chromaModeOf(layer){
    var mode=layer.chromaKey||'auto';
    if(mode==='custom')return /^#[0-9a-f]{6}$/i.test(layer.chromaColor||'')?layer.chromaColor.toLowerCase():'auto';
    return mode==='color'?'auto':mode;
  }
  function shrinkForEstimate(image){
    var step=Math.max(1,Math.ceil(image.width/160)),w=Math.ceil(image.width/step),h=Math.ceil(image.height/step),out={width:w,height:h,data:new Uint8ClampedArray(w*h*4)},src=image.data;
    for(var y=0;y<h;y++)for(var x=0;x<w;x++){var from=((y*step)*image.width+x*step)*4,to=(y*w+x)*4;out.data[to]=src[from];out.data[to+1]=src[from+1];out.data[to+2]=src[from+2];out.data[to+3]=src[from+3]}
    return out;
  }
  function applyChroma(image,w,h,layer,entry){
    if(!window.SMChroma)return;
    var mode=chromaModeOf(layer),stamp=performance.now();
    if(!entry.frozen&&(!entry.samples||(stamp-entry.sampledAt>150))){
      entry.samples=entry.samples||[];entry.samples.push(shrinkForEstimate(image));entry.sampledAt=stamp;
      entry.model=SMChroma.estimate(entry.samples);
      if(!entry.moving||entry.samples.length>=6)entry.frozen=true;
    }
    if((mode==='auto')&&SMChroma.isCutout(image))return;
    var model=SMChroma.resolve(mode,entry.model);if(!model)return;
    var frame=entry.moving?SMChroma.frameModel(image,model,mode):model;  // intro/flash frames on another colour
    entry.state=SMChroma.apply(image,frame,{tolerance:layer.chromaTolerance==null?45:layer.chromaTolerance,softness:layer.chromaFeather==null?16:layer.chromaFeather,holes:layer.chromaHoles!==false},frame===model?entry.state:null);
  }
  /* Steam draws the profile background at its own size, centred on the page, and the
     976 px profile column in the middle. Each showcase file shows the part of the background
     right behind it (measured on steamcommunity.com, same numbers as steam.design and
     steamprofile.io). Offsets are from the left edge of the profile column; `y` is the top of
     the showcase images for a showcase placed first on the profile. */
  var STEAM_LAYOUT={featured:{y:256,parts:[[23,630]]},split:{y:256,parts:[[23,506],[538,100]]},workshop:{y:380,parts:[[24,122],[150,122],[276,122],[402,122],[528,122]]}};
  function steamParts(){
    var spec=STEAM_LAYOUT[project.mode]||STEAM_LAYOUT.workshop,W=canvas.width,widths=project.mode==='split'?[506,W-506]:(project.mode==='workshop'?[W/5,W/5,W/5,W/5,W/5]:[W]),dx=0;
    return spec.parts.map(function(part,i){var d={dx:dx,dw:widths[i],sx:part[0],sw:part[1],y:spec.y+(Number(project.steamOffsetY)||0)};dx+=widths[i];return d});
  }
  function drawSteamAligned(layer,node,now){
    var size=mediaSize(node),nw=size[0],nh=size[1],column=(nw-976)/2,H=canvas.height;
    var src=motionEngine?motionEngine.animateMedia(node,layer,now):node,k=mediaSize(src)[0]/nw;
    ctx.save();ctx.globalAlpha=Math.max(0,Math.min(1,layer.opacity));ctx.filter=SMColorGrade.filter(layer.grade);
    steamParts().forEach(function(p){
      var scale=p.sw/p.dw,sx=column+p.sx,sy=p.y,sh=H*scale;
      // Clip the source rectangle to the image; the rest stays the project colour, like Steam's page.
      var x0=Math.max(0,sx),y0=Math.max(0,sy),x1=Math.min(nw,sx+p.sw),y1=Math.min(nh,sy+sh);
      if(x1<=x0||y1<=y0)return;
      ctx.drawImage(src,x0*k,y0*k,(x1-x0)*k,(y1-y0)*k,p.dx+(x0-sx)/scale,(y0-sy)/scale,(x1-x0)/scale,(y1-y0)/scale);
    });
    ctx.restore();
  }
  function drawMediaLayer(layer, node, now) {
    if(exportSources.has(layer.id))node=exportSources.get(layer.id);
    if(!node || !(node.complete || node.readyState>=2 || node.displayWidth))return;
    if(layer.type==='background'&&layer.steamAlign&&!layer.chroma){drawSteamAligned(layer,node,now);return}
    var box=layer.type==='background'?coverBox(node):containBox(node,layer),a=animationTransform(layer,now);
    var x=layer.x*canvas.width,y=layer.y*canvas.height+a.y;
    ctx.save();ctx.globalAlpha=Math.max(0,Math.min(1,layer.opacity));ctx.filter=SMColorGrade.filter(layer.grade);ctx.translate(x,y);ctx.rotate(layer.rotation*Math.PI/180+a.rotate);ctx.scale(a.scale,a.scale);
    if(layer.chroma){
      var w=Math.max(1,Math.round(box.w)),h=Math.max(1,Math.round(box.h));
      // Keying runs on at most ~0.35 MP in the live preview (the stage shows the canvas at a few hundred
      // pixels) and ~1.2 MP for the export; drawn scaled up. Full-size keying every frame stalled the editor.
      // Preview: the resolution the canvas is shown at (x1.25, 120k..350k px); export: up to 1.2 MP.
      var shown=canvas.clientWidth?Math.min(1,canvas.clientWidth*1.25/canvas.width):1,budget=exportingCanvas?1200000:Math.max(120000,Math.min(350000,w*h*shown*shown));
      var keyScale=Math.min(1,Math.sqrt(budget/(w*h)));w=Math.max(1,Math.round(w*keyScale));h=Math.max(1,Math.round(h*keyScale));
      var cacheKey=[layer.id,layer.src,w,h,layer.chromaKey,layer.chromaColor,layer.chromaHoles,layer.chromaTolerance,layer.chromaFeather].join('|'),entry=chromaCache.get(cacheKey),isMoving=node.tagName==='VIDEO';
      if(!entry){var made=document.createElement('canvas');made.width=w;made.height=h;entry={canvas:made,updated:0};chromaCache.set(cacheKey,entry)}
      var off=entry.canvas,oc=off.getContext('2d');
      var isGif=layer.mediaType==='image/gif'||/\.gif(\?|$)/i.test(layer.src||'');entry.moving=isMoving||isGif;
      if(!entry.updated||((isMoving||isGif)&&Math.abs(now-entry.updated)>70)){oc.clearRect(0,0,w,h);oc.drawImage(node,0,0,w,h);try{var im=oc.getImageData(0,0,w,h);applyChroma(im,w,h,layer,entry);oc.putImageData(im,0,0)}catch(_){ }entry.updated=now||.001;if(chromaCache.size>24){var first=chromaCache.keys().next().value;chromaCache.delete(first)}}
      ctx.drawImage(motionEngine?motionEngine.animateMedia(off,layer,now):off,-box.w/2,-box.h/2,box.w,box.h);
    }else ctx.drawImage(motionEngine?motionEngine.animateMedia(node,layer,now):node,-box.w/2,-box.h/2,box.w,box.h);
    ctx.restore();
  }
  function effectTexture(type,color) {
    var url=EFFECT_ASSETS[type];if(!url)return null;
    var image=effectTextures.get(type);
    if(!image){image=new Image();image.src=url;image.onload=function(){effectTintCache.clear()};effectTextures.set(type,image)}
    if(!image.complete||!image.naturalWidth)return null;
    var key=type+'|'+color;if(effectTintCache.has(key))return effectTintCache.get(key);
    var tinted=document.createElement('canvas');tinted.width=image.naturalWidth;tinted.height=image.naturalHeight;var paint=tinted.getContext('2d');
    paint.drawImage(image,0,0);paint.globalCompositeOperation='source-atop';paint.globalAlpha=.48;paint.fillStyle=color;paint.fillRect(0,0,tinted.width,tinted.height);paint.globalCompositeOperation='source-over';paint.globalAlpha=.42;paint.drawImage(image,0,0);
    if(effectTintCache.size>20)effectTintCache.delete(effectTintCache.keys().next().value);effectTintCache.set(key,tinted);return tinted;
  }
  function drawTextureField(texture,tileWidth,offsetX,offsetY,rotation){
    var pattern=effectPatternCache.get(texture);
    if(!pattern){pattern=ctx.createPattern(texture,'repeat');if(pattern)effectPatternCache.set(texture,pattern)}
    if(pattern&&typeof pattern.setTransform==='function'&&typeof DOMMatrix==='function'){
      var patternScale=tileWidth/texture.width,angle=rotation||0,cos=Math.cos(angle),sin=Math.sin(angle);pattern.setTransform(new DOMMatrix([cos*patternScale,sin*patternScale,-sin*patternScale,cos*patternScale,offsetX,offsetY]));ctx.fillStyle=pattern;ctx.fillRect(0,0,canvas.width,canvas.height);return;
    }
    var tileHeight=tileWidth*texture.height/texture.width,pad=rotation?Math.max(canvas.width,canvas.height):0,startX=((offsetX%tileWidth)+tileWidth)%tileWidth-tileWidth-pad,startY=((offsetY%tileHeight)+tileHeight)%tileHeight-tileHeight-pad;
    ctx.save();if(rotation){ctx.translate(canvas.width/2,canvas.height/2);ctx.rotate(rotation);ctx.translate(-canvas.width/2,-canvas.height/2)}for(var x=startX;x<canvas.width+tileWidth+pad;x+=tileWidth)for(var y=startY;y<canvas.height+tileHeight+pad;y+=tileHeight)ctx.drawImage(texture,x,y,tileWidth,tileHeight);ctx.restore();
  }
  function drawFlowingTexture(texture,sec,speed,density,kind,opacity,particleScale,rotation,originX,originY){
    var passes=density>1.35?3:(density>.65?2:1),baseWidth=canvas.width*(kind==='rain'?1.08:1.18)*particleScale,cos=Math.cos(rotation),sin=Math.sin(rotation);
    for(var pass=0;pass<passes;pass++){
      var width=baseWidth*(1+pass*.14),height=width*texture.height/texture.width,velocity=(kind==='rain'?420:(kind==='snow'?42:58))*speed*(1+pass*.18),offset=(sec*velocity+pass*height*.47)%height-height;
      var drift=kind==='rain'?-canvas.width*.04:Math.sin(sec*(.35+pass*.11)+pass*2.1)*canvas.width*.055-canvas.width*.09,flowX=drift*cos-offset*sin,flowY=drift*sin+offset*cos;
      ctx.globalAlpha=opacity*Math.min(1,.42+density*.22-pass*.08);
      drawTextureField(texture,width,originX+flowX,originY+flowY,rotation);
    }
  }
  function drawEffect(layer, now) {
    if(layer.src){drawMediaLayer(layer,mediaFor(layer),now);return}
    var sec=now/1000,color=layer.color||'#52d5ff',a=animationTransform(layer,now),x=(layer.x==null ? .5 : layer.x)*canvas.width,y=(layer.y==null ? .5 : layer.y)*canvas.height+a.y,speed=clamp(layer.effectSpeed==null?100:layer.effectSpeed,1,500)/100,density=clamp(layer.effectDensity==null?100:layer.effectDensity,5,400)/100,particleScale=clamp((layer.scale||1)*a.scale,.1,4),rotation=layer.rotation*Math.PI/180+a.rotate,originX=x-canvas.width/2,originY=y-canvas.height/2;
    if(window.SMBuilderEffects&&SMBuilderEffects.has(layer.effect)){
      // New procedural effects draw on a scratch layer, then land with the layer opacity.
      var fxCanvas=drawEffect.layer||(drawEffect.layer=document.createElement('canvas'));
      if(fxCanvas.width!==canvas.width||fxCanvas.height!==canvas.height){fxCanvas.width=canvas.width;fxCanvas.height=canvas.height}
      var fx=fxCanvas.getContext('2d');fx.clearRect(0,0,fxCanvas.width,fxCanvas.height);fx.save();fx.translate(x,y);fx.rotate(rotation);fx.translate(-canvas.width/2,-canvas.height/2);
      SMBuilderEffects.draw(fx,canvas.width,canvas.height,layer.effect,{t:sec,color:color,speed:speed,density:density,scale:particleScale});fx.restore();
      ctx.save();ctx.globalAlpha=clamp(layer.opacity==null?1:layer.opacity,0,1);ctx.drawImage(fxCanvas,0,0);ctx.restore();return;
    }
    ctx.save();ctx.globalAlpha=layer.opacity;
    var texture=effectTexture(layer.effect,color);
    if(texture&&layer.effect==='lightning'){
      var pulse=(sec*speed)%3.7,flash=pulse<.12?1:(pulse<.22?.38:(pulse>.36&&pulse<.43?.68:0));
      if(flash){var fieldWidth=canvas.width*(1.02+Math.min(density,1.5)*.06)*particleScale;ctx.globalCompositeOperation='screen';ctx.globalAlpha=layer.opacity*flash*Math.min(1,.48+density*.34);ctx.shadowColor=color;ctx.shadowBlur=Math.max(2,7*particleScale);drawTextureField(texture,fieldWidth,originX+canvas.width*.013,originY+canvas.height*.017,rotation);if(density>1.35){ctx.globalAlpha*=.34;drawTextureField(texture,fieldWidth,originX+canvas.width*.061,originY+canvas.height*.043,rotation)}ctx.globalAlpha=layer.opacity*flash*.025;ctx.fillStyle=color;ctx.fillRect(0,0,canvas.width,canvas.height)}
    }else if(texture){ctx.globalCompositeOperation=layer.effect==='rain'?'screen':'source-over';drawFlowingTexture(texture,sec,speed,density,layer.effect,layer.opacity,particleScale,rotation,originX,originY)}
    else{
      ctx.translate(x,y);ctx.rotate(rotation);ctx.translate(-canvas.width/2,-canvas.height/2);
      var count=Math.max(8,Math.min(particles.length,Math.round(particles.length*density)));ctx.shadowColor=color;ctx.shadowBlur=layer.effect==='stars'?10:6;
      if(layer.effect==='matrix'){ctx.fillStyle=color;ctx.font=Math.max(3,15*particleScale)+'px'+String.fromCharCode(32)+safeFontName('monospace');particles.slice(0,Math.min(count,44)).forEach(function(p,i){ctx.fillText(String.fromCharCode(0x30A0+(i*17)%90),p.x*canvas.width,((p.y+sec*p.speed*2*speed)%1)*canvas.height)});}
      else if(layer.effect==='streaks'){ctx.strokeStyle=color;ctx.lineWidth=Math.max(.5,2*particleScale);particles.slice(0,Math.min(count,30)).forEach(function(p){var px=((p.x+sec*p.speed*speed)%1)*canvas.width,py=p.y*canvas.height;ctx.beginPath();ctx.moveTo(px,py);ctx.lineTo(px+70*particleScale,py-45*particleScale);ctx.stroke()});}
      else{ctx.fillStyle=color;particles.slice(0,count).forEach(function(p){var direction=layer.effect==='sparks'?-1:1,py=((p.y+direction*sec*p.speed*.55*speed)%1+1)%1*canvas.height,px=(p.x+Math.sin(sec+p.y*9)*.02)*canvas.width;ctx.beginPath();ctx.arc(px,py,Math.max(.35,p.r*particleScale),0,Math.PI*2);ctx.fill()});}
    }
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
  function frameRects(layer){
    var design=layer.frameShape&&['rect','bevel','notch'].indexOf(layer.frameShape)<0;
    if(layer.frameTarget==='outer'||(design&&project.mode==='split'))return [{x:0,y:0,w:canvas.width,h:canvas.height}];
    if(project.mode==='workshop')return Array.from({length:5},function(_,i){return {x:i*canvas.width/5,y:0,w:canvas.width/5,h:canvas.height}});
    if(project.mode==='split')return [{x:0,y:0,w:506,h:canvas.height},{x:506,y:0,w:100,h:canvas.height}];
    return [{x:0,y:0,w:canvas.width,h:canvas.height}];
  }
  function drawFrameRect(rect,width,style){
    var inset=width/2+1,x=rect.x+inset,y=rect.y+inset,w=Math.max(0,rect.w-width-2),h=Math.max(0,rect.h-width-2);
    if(style==='corners'){var length=Math.min(w,h)*.16;[[x,y,1,1],[x+w,y,-1,1],[x,y+h,1,-1],[x+w,y+h,-1,-1]].forEach(function(c){ctx.beginPath();ctx.moveTo(c[0]+c[2]*length,c[1]);ctx.lineTo(c[0],c[1]);ctx.lineTo(c[0],c[1]+c[3]*length);ctx.stroke()});return}
    ctx.strokeRect(x,y,w,h);if(style==='double'){var gap=width*2.2+3;ctx.strokeRect(x+gap,y+gap,Math.max(0,w-gap*2),Math.max(0,h-gap*2))}
  }
  function drawFrame(layer, now) {var fxApi=window.SMSquaresFx,animatedStyle=fxApi&&(fxApi.isAnimatedFrame(layer.frameStyle)||(layer.frameShape&&layer.frameShape!=='rect'));if(animatedStyle){var period=Math.max(1,Number(project.motion&&project.motion.duration)||8),panels=frameRects(layer),rects=panels.map(function(r,i){return [r.x,r.y,r.w,r.h,project.mode==='split'&&panels.length===2?(i?'right':'left'):'full']});ctx.save();ctx.globalAlpha=layer.opacity;fxApi.drawFrame(ctx,((now||0)/1000%period)/period,{style:layer.frameStyle,shape:layer.frameShape||'rect',plate:layer.frameShape&&layer.frameShape!=='rect'?(layer.framePlate||0):0,color:layer.color||'#52d5ff',color2:layer.color2||'#8a62ff',width:layer.frameWidth||4,speed:layer.frameSpeed||1,target:'squares'},rects);ctx.restore();return}ctx.save();ctx.globalAlpha=layer.opacity;ctx.strokeStyle=layer.color||'#52d5ff';ctx.lineWidth=layer.frameWidth||4;ctx.lineJoin='miter';var style=layer.frameStyle||'solid';if(style==='neon'){ctx.shadowColor=layer.color||'#52d5ff';ctx.shadowBlur=Math.max(8,ctx.lineWidth*3)}frameRects(layer).forEach(function(rect){drawFrameRect(rect,ctx.lineWidth,style)});ctx.restore()}
  function drawText(layer, now) {var a=animationTransform(layer,now),font=safeFontName(layer.font);ctx.save();ctx.globalAlpha=layer.opacity;ctx.translate(layer.x*canvas.width,layer.y*canvas.height+a.y);ctx.rotate(layer.rotation*Math.PI/180+a.rotate);ctx.scale(layer.scale*a.scale,layer.scale*a.scale);ctx.fillStyle=layer.color||'#fff';ctx.textAlign='center';ctx.textBaseline='middle';ctx.font=(layer.fontWeight||800)+' '+(layer.fontSize||64)+'px "'+font+'",Mulish,sans-serif';var textLines=String(layer.text||'').split('\n'),period=Math.max(1,Number(project.motion&&project.motion.duration)||8);var textFx=layer.textFx&&window.SMTextFx&&SMTextFx.has(layer.textFx)?layer.textFx:'',vertical=layer.textDir==='vertical';if(window.SMTextFx&&(textFx||vertical)){SMTextFx.draw(ctx,textFx||'plain',textLines,{u:(now/1000%period)/period,period:period,speed:layer.textFxSpeed||1,size:layer.fontSize||64,color:layer.fxColor||(textFx?SMTextFx.defaultColor(textFx):layer.color)||'#52d5ff',vertical:vertical});ctx.restore();return}textLines.forEach(function(line,i,arr){ctx.fillText(line,0,(i-(arr.length-1)/2)*(layer.fontSize||64)*1.12,canvas.width*.9)});ctx.restore()}
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
    function drawLayer(layer,time,paint){var original=ctx;ctx=paint||original;try{if(layer.type==='text')drawText(layer,time);else if(layer.type==='frame')drawFrame(layer,time);else if(layer.type==='effect')drawEffect(layer,time);else if(layer.type==='dna')drawDNA(layer,time);else drawMediaLayer(layer,mediaFor(layer),time)}finally{ctx=original}}
    var time=motionEngine?motionEngine.clock(now):now;
    if(motionEngine)motionEngine.renderScene(project,time,ctx,drawLayer,diagnostic);
    else project.layers.forEach(function(layer){if(layer.visible!==false&&!(diagnostic&&layer.type==='background'))drawLayer(layer,time,ctx)});
    if(motionEngine&&!exportingCanvas){motionEngine.blendPreview(time,ctx,drawLayer,diagnostic);motionEngine.overlays(ctx)}
  }
  /* Render only when something changed; animated scenes at most 30 times a second
     (full rate while recording an export). A static scene used to be redrawn on every
     display frame, which kept a CPU core busy for nothing. */
  var dirty=true,lastRender=-1e9;
  function markDirty(){dirty=true}
  var renderErrors=0;
  function draw(now) {
    // Schedule first: one failing layer must never stop the editor for good.
    requestAnimationFrame(draw);
    if(manualClock)return;
    var active=exportingCanvas||root.closest('.tab')?.classList.contains('active');
    if(!active)return;
    var animated=exportingCanvas||!!dragging||projectAnimated();
    if(exportingCanvas||dirty||(animated&&now-lastRender>=32)||now-lastRender>1500){
      dirty=false;lastRender=now;
      try{renderCanvas(now)}catch(error){if(renderErrors++<5)console.error('[builder] render failed',error)}
    }
  }
  ['input','change','pointerdown','pointermove','pointerup','click','keydown','wheel'].forEach(function(type){root.addEventListener(type,markDirty,true)});
  window.addEventListener('resize',markDirty);
  if(document.fonts&&document.fonts.addEventListener)document.fonts.addEventListener('loadingdone',markDirty);

  function updateGuides() {
    var host=el('builderGuides');host.dataset.mode=project.mode;host.innerHTML='';
    var cuts=project.mode==='workshop'?[.2,.4,.6,.8]:(project.mode==='split'?[506/606]:[]);
    var rect=canvas.getBoundingClientRect(),wrap=canvas.parentElement.getBoundingClientRect();
    cuts.forEach(function(c){var i=document.createElement('i');i.style.left=(rect.left-wrap.left+rect.width*c)+'px';i.style.top=(rect.top-wrap.top)+'px';i.style.height=rect.height+'px';host.appendChild(i)});
  }
  function setHeight(h){h=Math.round(Math.max(280,Math.min(1800,Number(h)||1000))/2)*2;if(project.height===h&&canvas.height===h)return h;project.height=h;canvas.height=h;markDirty();requestAnimationFrame(updateGuides);return h}
  function resizeMode(mode) {markDirty();project.mode=mode;project.width=mode==='featured'?630:(mode==='split'?606:750);canvas.width=project.width;canvas.height=project.height||1000;document.querySelectorAll('[data-builder-mode]').forEach(function(b){b.classList.toggle('active',b.dataset.builderMode===mode)});requestAnimationFrame(updateGuides)}

  function icon(type){return window.WorkspaceEditor?WorkspaceEditor.icon(type):({background:'▧',character:'♙',text:'T',frame:'□',effect:'✦',dna:'◎'}[type]||'·')}
  function renderLayers(){
    markDirty();
    var host=el('builderLayerList');host.innerHTML='';
    project.layers.slice().reverse().forEach(function(layer){
      var row=document.createElement('div');row.className='builder-layer'+(layer.id===selected?' is-selected':'')+(layer.locked?' is-locked':'');row.dataset.layerId=layer.id;row.dataset.layerType=layer.type;
      row.innerHTML='<span class="builder-layer__icon">'+icon(layer.type)+'</span><span class="builder-layer__copy"><b></b><span></span></span><span class="builder-layer__actions"><button data-action="visible">'+(layer.visible===false?'○':'●')+'</button><button data-action="lock">'+(layer.locked?'◆':'◇')+'</button><button data-action="duplicate">⧉</button><button data-action="up">↑</button><button data-action="down">↓</button><button data-action="delete">×</button></span>';
      row.querySelector('.builder-layer__copy b').textContent=layer.name;row.querySelector('.builder-layer__copy span').textContent=layer.type==='dna'?'Steam DNA':t(layer.type);
      var titles={visible:t('show-hide'),lock:layer.locked?t('unlock'):t('lock'),duplicate:t('duplicate'),up:t('up'),down:t('down'),delete:t('remove')};
      row.querySelectorAll('button').forEach(function(btn){btn.title=titles[btn.dataset.action]||'';btn.setAttribute('aria-label',titles[btn.dataset.action]||'');if(window.WorkspaceEditor){var action=btn.dataset.action;btn.innerHTML=WorkspaceEditor.icon(action==='visible'?(layer.visible===false?'hidden':'visible'):action==='lock'?(layer.locked?'lock':'unlock'):action)}btn.onclick=function(e){e.stopPropagation();layerAction(layer,btn.dataset.action)}});
      row.tabIndex=0;row.setAttribute('role','group');row.setAttribute('aria-label',layer.name||t(layer.type));
      row.onclick=function(){if(selected===layer.id)return;selected=layer.id;renderLayers();syncInspector()};row.onkeydown=function(e){if(e.target===row&&(e.key==='Enter'||e.key===' ')){e.preventDefault();row.click()}};host.appendChild(row);
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
  function syncInspector(){var layer=currentLayer(),box=el('builderInspector');box.hidden=!layer;if(!layer)return;el('builderLayerName').value=layer.name||'';el('builderScale').value=Math.round((layer.scale||1)*100);el('builderRotation').value=layer.rotation||0;el('builderOpacity').value=Math.round((layer.opacity==null?1:layer.opacity)*100);el('builderTextControls').hidden=layer.type!=='text';el('builderFrameControls').hidden=layer.type!=='frame';el('builderEffectControls').hidden=layer.type!=='effect';el('builderMediaControls').hidden=!['background','character'].includes(layer.type);if(layer.type==='text'){el('builderText').value=layer.text||'';el('builderFont').value=layer.font||'Mulish';el('builderColor').value=layer.color||'#ffffff';el('builderFontSize').value=layer.fontSize||64;syncFontPreview(layer)}if(layer.type==='frame'){el('builderFrameColor').value=layer.color||'#52d5ff';el('builderFrameWidth').value=layer.frameWidth||4;el('builderFrameStyle').value=layer.frameStyle||'solid';el('builderFrameTarget').value=layer.frameTarget||'panels';el('builderFrameColor2').value=layer.color2||'#8a62ff';el('builderFrameSpeed').value=layer.frameSpeed||1;el('builderFrameShape').value=layer.frameShape||'rect';el('builderFramePlate').value=layer.framePlate||0;syncFrameFx(layer)}if(layer.type==='effect'){el('builderEffectType').value=layer.effect||'petals';el('builderEffectColor').value=layer.color||'#52d5ff';el('builderEffectSpeed').value=layer.effectSpeed==null?100:layer.effectSpeed;el('builderEffectDensity').value=layer.effectDensity==null?100:layer.effectDensity;el('builderEffectColorRow').hidden=layer.effect==='custom'||!!layer.src;el('builderEffectSwatch').dataset.effect=layer.src?'custom':(layer.effect||'petals')}if(['background','character'].includes(layer.type)){var tolerance=layer.chromaTolerance==null?45:layer.chromaTolerance,feather=layer.chromaFeather==null?16:layer.chromaFeather;el('builderChroma').checked=!!layer.chroma;el('builderChromaSettings').hidden=!layer.chroma;el('builderChromaKey').value=layer.chromaKey||'auto';el('builderChromaColor').value=/^#[0-9a-f]{6}$/i.test(layer.chromaColor||'')?layer.chromaColor:'#00b140';el('builderChromaColorWrap').hidden=layer.chromaKey!=='custom';el('builderChromaHoles').checked=layer.chromaHoles!==false;el('builderChromaTolerance').value=tolerance;el('builderChromaToleranceValue').value=tolerance;el('builderChromaFeather').value=feather;el('builderChromaFeatherValue').value=(feather/10).toFixed(1);el('builderAnimation').value=layer.animation||'none'}box.classList.toggle('is-locked',!!layer.locked);box.querySelectorAll('input,select,textarea,button').forEach(function(control){control.disabled=!!layer.locked});el('builderAiRemove').disabled=!!layer.locked||!aiRemovalEligible(layer);box.title=layer.locked?t('layer-locked'):''}
  function syncGrade(layer){
    var editable=!!layer&&['background','character'].includes(layer.type),grade=SMColorGrade.normalize(layer&&layer.grade);
    el('builderGradeControls').hidden=!editable;el('builderGradeHint').hidden=editable;el('builderGradeReset').hidden=!editable;
    if(!editable)return;
    el('builderGradeSelected').textContent=layer.name||t(layer.type);
    Object.keys(SMColorGrade.ranges).forEach(function(key){var id='builderGrade'+key.charAt(0).toUpperCase()+key.slice(1),input=el(id);input.value=grade[key];el(id+'Value').value=grade[key]+(key==='hue'?'°':'%');input.disabled=!!layer.locked});
    el('builderGradeReset').disabled=!!layer.locked;
  }
  function steamPurchase(url) {
    try {
      var parsed=new URL(url);
      if(parsed.protocol!=='https:'||parsed.username||parsed.password||parsed.port)return null;
      var kind=/^steamcommunity\.com$/i.test(parsed.hostname)&&/^\/market\/listings\/753\/[^/]+$/.test(parsed.pathname)?'market':
        /^store\.steampowered\.com$/i.test(parsed.hostname)&&/^\/points\/shop\/app\/\d+(\/reward\/\d+)?\/?$/.test(parsed.pathname)?'points':'';
      return kind?{url:parsed.href,kind:kind}:null;
    } catch (_) { return null; }
  }
  function syncBackgroundPurchase() {
    var button=el('builderBuyBackground');
    if(!button){
      var toolbar=root.querySelector('.builder-history');if(!toolbar)return;
      button=document.createElement('a');button.id='builderBuyBackground';button.className='btn ghost';
      button.target='_blank';button.rel='noopener noreferrer';button.setAttribute('data-no-translate','');
      toolbar.appendChild(button);
    }
    var layer=currentLayer();
    if(!layer||layer.type!=='background')layer=project.layers.find(function(item){return item.type==='background'&&item.visible!==false});
    var purchase=layer&&steamPurchase(layer.buyUrl);
    button.hidden=!purchase;
    if(!purchase){button.removeAttribute('href');button.removeAttribute('title');return}
    button.href=purchase.url;button.textContent=t(purchase.kind==='points'?'buy-points':'buy-market');
    button.title=layer.name||'';
  }
  window.addEventListener('sm:langchange',syncBackgroundPurchase);
  var syncInspectorBase=syncInspector;
  var purchaseInspectorBase=syncInspectorBase;
  syncInspectorBase=function(){purchaseInspectorBase();syncBackgroundPurchase();syncGrade(currentLayer())};
  syncInspector=function(){syncInspectorBase();if(motionEngine)motionEngine.sync();window.WorkspaceEditor?.builderState({count:project.layers.length,selected:!!currentLayer(),exportable:project.layers.some(function(layer){return layer.visible!==false})});root.dispatchEvent(new CustomEvent('sm:builder-select',{detail:{layer:currentLayer(),count:project.layers.length}}))};
  function bind(id,event,fn){el(id).addEventListener(event,function(){var layer=currentLayer();if(!layer)return;fn(layer,this);motionEngine?.invalidate();if(id==='builderLayerName')renderLayers()})}
  Object.keys(SMColorGrade.ranges).forEach(function(key){var id='builderGrade'+key.charAt(0).toUpperCase()+key.slice(1);el(id).addEventListener('input',function(){var layer=currentLayer();if(!layer||layer.locked||!['background','character'].includes(layer.type))return;layer.grade=SMColorGrade.normalize(Object.assign({},layer.grade,{[key]:this.value}));el(id+'Value').value=layer.grade[key]+(key==='hue'?'°':'%');motionEngine?.invalidate();editorHistory?.changed()})});
  el('builderGradeReset').addEventListener('click',function(){var layer=currentLayer();if(!layer||layer.locked)return;layer.grade=SMColorGrade.normalize();syncGrade(layer);motionEngine?.invalidate();editorHistory?.commit()});
  bind('builderLayerName','input',function(l,n){l.name=n.value});bind('builderScale','input',function(l,n){l.scale=+n.value/100});bind('builderRotation','input',function(l,n){l.rotation=+n.value});bind('builderOpacity','input',function(l,n){l.opacity=+n.value/100});bind('builderText','input',function(l,n){l.text=n.value;syncFontPreview(l)});bind('builderFont','change',function(l,n){l.font=n.value;syncFontPreview(l);if(document.fonts)document.fonts.load('800 64px "'+safeFontName(n.value)+'"')});bind('builderColor','input',function(l,n){l.color=n.value});bind('builderFontSize','input',function(l,n){l.fontSize=+n.value});bind('builderFrameColor','input',function(l,n){l.color=n.value});bind('builderFrameWidth','input',function(l,n){l.frameWidth=+n.value});bind('builderFrameStyle','change',function(l,n){l.frameStyle=n.value;syncFrameFx(l)});bind('builderFrameColor2','input',function(l,n){l.color2=n.value});bind('builderFrameSpeed','input',function(l,n){l.frameSpeed=+n.value});bind('builderFrameTarget','change',function(l,n){l.frameTarget=n.value});bind('builderFrameShape','change',function(l,n){l.frameShape=n.value;if(n.value!=='rect'&&!l.framePlate)l.framePlate=60;el('builderFramePlate').value=l.framePlate||0;syncFrameFx(l)});bind('builderFramePlate','input',function(l,n){l.framePlate=+n.value});bind('builderEffectType','change',function(l,n){var colors={petals:'#ff9fc8',snow:'#e7f7ff',rain:'#8bdcff',lightning:'#73dfff'};l.effect=n.value;l.name=n.options[n.selectedIndex].text;if(colors[n.value]){l.color=colors[n.value];el('builderEffectColor').value=l.color}renderLayers()});bind('builderEffectColor','input',function(l,n){l.color=n.value;effectTintCache.clear()});bind('builderEffectSpeed','input',function(l,n){l.effectSpeed=+n.value});bind('builderEffectDensity','input',function(l,n){l.effectDensity=+n.value});bind('builderChroma','change',function(l,n){l.chroma=n.checked;chromaCache.clear();syncInspector()});bind('builderChromaKey','change',function(l,n){l.chromaKey=n.value;if(n.value==='custom'&&!l.chromaColor)l.chromaColor=el('builderChromaColor').value;el('builderChromaColorWrap').hidden=n.value!=='custom';chromaCache.clear()});bind('builderChromaColor','input',function(l,n){l.chromaColor=n.value;chromaCache.clear()});bind('builderChromaHoles','change',function(l,n){l.chromaHoles=n.checked;chromaCache.clear()});bind('builderChromaTolerance','input',function(l,n){l.chromaTolerance=+n.value;chromaCache.clear();el('builderChromaToleranceValue').value=n.value});bind('builderChromaFeather','input',function(l,n){l.chromaFeather=+n.value;chromaCache.clear();el('builderChromaFeatherValue').value=(+n.value/10).toFixed(1)});bind('builderAnimation','change',function(l,n){l.animation=n.value});

  Array.from(el('builderFont').options).forEach(function(option){option.style.fontFamily='"'+safeFontName(option.value)+'"'});

  /* AI models: only the services configured on the server are offered. Auto mode tries our
     own model first and moves on to the next service when one is down. */
  var aiProviders=null,AI_MODEL_KEY='sm_bx_ai_model';
  function aiModelLabel(id){return t('ai-model-'+id)}
  function aiChoice(){var n=el('builderAiModel');return (n&&n.value)||'auto'}
  function aiFirst(){var v=aiChoice();if(v!=='auto')return v;return aiProviders&&aiProviders[0]?aiProviders[0].id:''}
  function syncAiNote(){var note=el('builderAiNote');if(!note)return;var parts=[];if(aiFirst()==='modal')parts.push(t('ai-note-modal'));if(aiChoice()==='auto'&&aiProviders&&aiProviders.length>1)parts.push(t('ai-note-auto'));note.textContent=parts.join(' ');note.hidden=!parts.length}
  function renderAiModels(){var sel=el('builderAiModel'),wrap=el('builderAiModelWrap');if(!sel||!aiProviders)return;var saved='';try{saved=localStorage.getItem(AI_MODEL_KEY)||''}catch(_){}
    sel.innerHTML='';var auto=document.createElement('option');auto.value='auto';auto.dataset.builderI='ai-model-auto';auto.textContent=t('ai-model-auto');sel.appendChild(auto);
    aiProviders.forEach(function(p){var o=document.createElement('option');o.value=p.id;o.dataset.builderI='ai-model-'+p.id;o.textContent=aiModelLabel(p.id);sel.appendChild(o)});
    sel.value=aiProviders.some(function(p){return p.id===saved})?saved:'auto';wrap.hidden=aiProviders.length<2;syncAiNote()}
  function loadAiProviders(){if(aiProviders)return;aiProviders=[];fetch('/api/builder/remove-background/providers',{credentials:'same-origin'}).then(function(r){return r.json()}).then(function(d){aiProviders=(d&&d.ok&&d.providers)||[];renderAiModels()}).catch(function(){})}
  el('builderAiModel').addEventListener('change',function(){try{localStorage.setItem(AI_MODEL_KEY,this.value)}catch(_){}syncAiNote()});
  loadAiProviders();
  function waitForRemoval(jobId){var started=Date.now(),cold=aiFirst()==='modal';return new Promise(function(resolve,reject){function poll(){fetch('/api/builder/remove-background/'+encodeURIComponent(jobId),{credentials:'same-origin'}).then(function(r){return r.json()}).then(function(d){if(!d.ok)throw Error(aiRemovalMessage(d));if(d.status==='done'){resolve(d.result);setTimeout(function(){editorHistory?.commit()},0);return}if(d.status==='error'){reject(Error(aiRemovalMessage(d)));return}status((cold&&Date.now()-started>7000?t('ai-waking'):t('ai-working'))+' '+(d.pct||0)+'%','wait');setTimeout(poll,900)}).catch(reject)}poll()})}
  el('builderAiRemove').onclick=async function(){var layer=currentLayer();if(!aiRemovalEligible(layer)){status(t('ai-image-only'),'bad');return}this.disabled=true;status(t('ai-working'),'wait');try{var planned=aiFirst(),r=await fetch('/api/builder/remove-background',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:layer.src,provider:aiChoice()})}),d=await r.json();if(!r.ok||!d.ok){if(r.status===401)el('btnAuth')&&el('btnAuth').click();throw Error(aiRemovalMessage(d))}var result=await waitForRemoval(d.job_id);media.delete(layer.id+'|'+layer.src);layer.src=result.url;layer.mediaType=result.media_type;layer.animatedSource=false;layer.chroma=false;syncInspector();if(result.fallback&&result.provider&&planned)status(t('ai-fallback').replace('{from}',aiModelLabel(planned)).replace('{to}',aiModelLabel(result.provider)),'ok');else status('', '')}catch(e){status(e.message||t('failed'),'bad')}finally{syncInspector()}};

  async function upload(file,type){status(t('uploading'),'wait');var layer=defaultLayer(type);layer.name=file.name;layer.src=URL.createObjectURL(file);layer.mediaType=file.type;layer.animatedSource=file.type==='image/gif'||file.type.indexOf('video/')===0||/\.(?:gif|mp4|webm|mov)$/i.test(file.name);editorHistory?.remember(layer.src,file);project.layers.push(layer);selected=layer.id;renderLayers();editorHistory?.commit();try{var fd=new FormData();fd.append('file',file);var r=await fetch('/api/builder/assets',{method:'POST',credentials:'same-origin',body:fd}),d=await r.json();if(!r.ok||!d.ok)throw Error(d.msg||t('failed'));media.delete(layer.id+'|'+layer.src);layer.src=d.url;editorHistory?.remember(layer.src,file);layer.mediaType=d.media_type;layer.animatedSource=!!d.animated;editorHistory?.commit();syncInspector();status('', '')}catch(e){status(e.message==='Login required'?t('login'):e.message,'bad')}}
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
  document.querySelectorAll('[data-builder-mode]').forEach(function(b){b.onclick=function(){resizeMode(b.dataset.builderMode);document.dispatchEvent(new CustomEvent('sm:builder-mode',{detail:{mode:project.mode}}))}});

  el('builderSnap').addEventListener('change',function(){snapEnabled=this.checked;hideSnapGuides()});
  document.querySelectorAll('[data-builder-backdrop]').forEach(function(button){button.onclick=function(){previewBackdrop=button.dataset.builderBackdrop;document.querySelectorAll('[data-builder-backdrop]').forEach(function(item){item.classList.toggle('active',item===button)})}});
  function hideSnapGuides(){var guides=el('builderSnapGuides');guides.classList.remove('show-x','show-y')}
  function snapped(value,horizontal){var points=[0,.5,1].concat(horizontal&&project.motion?.seams&&motionEngine?motionEngine.seams():[]),best=value,distance=.022;points.forEach(function(point){var delta=Math.abs(value-point);if(delta<distance){distance=delta;best=point}});return best}
  function moveLayer(layer,x,y){
    var rawX=clamp(x,0,1),rawY=clamp(y,0,1),nextX=snapEnabled?snapped(rawX,true):rawX,nextY=snapEnabled?snapped(rawY,false):rawY,guides=el('builderSnapGuides');
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

  function catalogMessage(message){var target=el('builderCatalogStatus');if(target)target.textContent=window.SMLang?.translate?.(message)||message||''}
  var catalogKeys=new Set();
  function nearCatalogEnd(){var grid=el('builderCatalogGrid');return !el('builderCatalog').hidden&&grid.scrollHeight-grid.scrollTop-grid.clientHeight<160}
  async function openCatalog(reset){
    var wasHidden=el('builderCatalog').hidden;
    if(reset){catalogGeneration++;catalogPage=0;catalogDone=false;catalogLoading=false;catalogKeys.clear();el('builderCatalogGrid').querySelectorAll('video').forEach(function(video){video.pause()});el('builderCatalogGrid').innerHTML='';el('builderCatalogMore').hidden=true}
    if(catalogLoading||catalogDone)return;
    el('builderCatalog').hidden=false;window.WorkspaceEditor?.catalogOpened(wasHidden);
    var requestGeneration=catalogGeneration,q=el('builderCatalogSearch').value.trim(),page=catalogPage;
    catalogLoading=true;var received=false;catalogMessage((window.SMLang?.get?.()||document.documentElement.lang)==='ru'?'Загружаем фоны…':'Loading backgrounds…');
    try{
      var parts=await Promise.all([
        fetch('/api/steam/backgrounds?asset=points_background&kind=static&page='+page+'&count=12&q='+encodeURIComponent(q)).then(function(r){if(!r.ok)throw Error('HTTP '+r.status);return r.json()}),
        fetch('/api/steam/backgrounds?asset=animated_background&kind=animated&page='+page+'&count=12&q='+encodeURIComponent(q)).then(function(r){if(!r.ok)throw Error('HTTP '+r.status);return r.json()})
      ]);
      if(requestGeneration!==catalogGeneration)return;
      if(parts.some(function(d){return !d.ok}))throw Error('catalog_unavailable');
      var before=el('builderCatalogGrid').children.length;
      parts.forEach(function(d){(d.items||[]).forEach(addCatalogItem)});catalogPage=page+1;
      catalogDone=parts.every(function(d){return d.total!=null?(page+1)*12>=Number(d.total):(d.items||[]).length<12})||el('builderCatalogGrid').children.length===before;
      el('builderCatalogMore').hidden=true;
      catalogMessage(!el('builderCatalogGrid').children.length?((window.SMLang?.get?.()||document.documentElement.lang)==='ru'?'По запросу фоны не найдены':'No backgrounds found'):(catalogDone?((window.SMLang?.get?.()||document.documentElement.lang)==='ru'?'Все фоны загружены':'All backgrounds loaded'):''));
      received=true;
    }catch(e){if(requestGeneration===catalogGeneration){catalogMessage((window.SMLang?.get?.()||document.documentElement.lang)==='ru'?'Не удалось загрузить следующую страницу':'Could not load the next page');el('builderCatalogMore').hidden=false;var retryText=(window.SMLang?.get?.()||document.documentElement.lang)==='ru'?'Повторить загрузку':'Retry loading';el('builderCatalogMore').textContent=window.SMLang?.translate?.(retryText)||retryText;status(el('builderCatalogStatus').textContent,'bad')}}
    finally{
      if(requestGeneration===catalogGeneration){catalogLoading=false;if(received)requestAnimationFrame(function(){if(!catalogDone&&nearCatalogEnd())openCatalog(false)})}
    }
  }
  function closeCatalog(){el('builderCatalog').hidden=true;el('builderCatalogGrid').querySelectorAll('video').forEach(function(video){video.pause()});window.WorkspaceEditor?.catalogClosed()}
  function addCatalogItem(item){var grid=el('builderCatalogGrid'),key=String(item.appid||'')+':'+String(item.defid||item.image);if(catalogKeys.has(key))return;catalogKeys.add(key);var b=document.createElement('button');b.type='button';b.dataset.key=key;var src=item.movie||item.image,poster=item.image||src;b.innerHTML=item.movie?'<video muted loop playsinline preload="none"></video>':'<img alt="" loading="lazy" decoding="async">';var n=b.firstElementChild;if(item.movie){n.poster=safeSource(poster);b.addEventListener('pointerenter',function(){if(!n.src)n.src=safeSource(item.movie);n.play().catch(function(){})});b.addEventListener('pointerleave',function(){n.pause()})}else n.src=safeSource(poster);var caption=document.createElement('span');caption.textContent=item.name||t('background');b.title=caption.textContent;b.appendChild(caption);b.onclick=function(){var layer=defaultLayer('background');layer.name=item.name||t('background');layer.src=src;layer.mediaType=item.movie?'video/webm':'image/jpeg';layer.animatedSource=!!item.movie;layer.steamAlign=true;project.layers=project.layers.filter(function(x){return x.type!=='background'});project.layers.unshift(layer);selected=layer.id;renderLayers();closeCatalog();document.dispatchEvent(new CustomEvent('sm:builder-steam-bg',{detail:{layer:layer.id}}))};grid.appendChild(b)}
  var addCatalogItemBase=addCatalogItem;
  addCatalogItem=function(item){
    var grid=el('builderCatalogGrid'),count=grid.children.length;
    addCatalogItemBase(item);
    if(grid.children.length===count)return;
    var button=grid.lastElementChild,select=button.onclick;
    button.onclick=function(){
      select();
      var layer=currentLayer(),purchase=steamPurchase(item.buy_url||item.market_url);
      if(layer&&purchase)layer.buyUrl=purchase.url;
      syncBackgroundPurchase();editorHistory?.commit();
    };
  };
  el('builderSteamBackgrounds').onclick=function(){openCatalog(true)};el('builderCatalogMore').onclick=function(){openCatalog(false)};el('builderCatalogGrid').addEventListener('scroll',function(){if(nearCatalogEnd())openCatalog(false)},{passive:true});el('builderCatalogClose').onclick=closeCatalog;var searchTimer;el('builderCatalogSearch').oninput=function(){clearTimeout(searchTimer);searchTimer=setTimeout(function(){openCatalog(true)},350)};

  async function saveProject(){var r=await fetch('/api/builder/projects',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:currentProjectId,name:el('builderProjectName').value,project:project})}),d=await r.json();if(!r.ok||!d.ok){if(r.status===401)el('btnAuth')&&el('btnAuth').click();throw Error(d.msg||t('failed'))}currentProjectId=d.item.id;document.dispatchEvent(new CustomEvent('sm:builder-saved',{detail:{id:currentProjectId}}));status(t('saved')+(d.retention_days?' · 7 days':''),'ok');loadProjects()}
  el('builderSave').onclick=async function(){this.disabled=true;try{for(var held of project.layers){if(!held.depthSource||!held.depthSource.startsWith('blob:'))continue;var heldBlob=await (await fetch(held.depthSource)).blob(),heldForm=new FormData();heldForm.append('file',heldBlob,'restored.'+(({'image/jpeg':'jpg','image/webp':'webp'})[heldBlob.type]||'png'));var heldResponse=await fetch('/api/builder/assets',{method:'POST',credentials:'same-origin',body:heldForm}),heldData=await heldResponse.json();if(!heldResponse.ok||!heldData.ok)throw Error(heldData.msg||t('failed'));held.depthSource=heldData.url;held.depthSourceType=heldData.media_type}for(var layer of project.layers){if(!layer.src||!layer.src.startsWith('blob:'))continue;var source=await fetch(layer.src),blob=await source.blob(),fd=new FormData(),extension=({'image/png':'png','image/jpeg':'jpg','image/webp':'webp','image/gif':'gif','video/mp4':'mp4','video/webm':'webm','video/quicktime':'mov'})[layer.mediaType||blob.type]||'png';fd.append('file',blob,'restored.'+extension);var response=await fetch('/api/builder/assets',{method:'POST',credentials:'same-origin',body:fd}),data=await response.json();if(!response.ok||!data.ok)throw Error(data.msg||t('failed'));editorHistory?.remember(data.url,blob);layer.src=data.url;layer.mediaType=data.media_type;layer.animatedSource=!!data.animated}await saveProject();editorHistory?.commit()}catch(e){status(e.message==='Login required'?t('login'):e.message,'bad')}finally{this.disabled=false}};

  function projectAnimated(){return !!motionEngine?.hasAnimation()||project.layers.some(function(l){return l.visible!==false&&(l.type==='effect'||l.type==='text'&&!!l.textFx&&l.textFx!=='none'||l.type==='frame'&&!!window.SMSquaresFx?.isAnimatedFrame(l.frameStyle)||l.type==='dna'||l.animation&&l.animation!=='none'||l.mediaType==='image/gif'||l.mediaType&&l.mediaType.indexOf('video/')===0||/\.gif(\?|$)/i.test(l.src||''))})}
  var exportSources=new Map(),manualClock=false;
  function sceneMs(){return Math.max(1,Number(project.motion&&project.motion.duration)||8)*1000}
  function seekVideo(node,seconds){return new Promise(function(resolve){
    if(!isFinite(node.duration)||!node.duration){resolve();return}
    var target=((seconds%node.duration)+node.duration)%node.duration;
    if(Math.abs(node.currentTime-target)<.0005&&node.readyState>=2){resolve();return}
    var done=false,finish=function(){if(done)return;done=true;node.removeEventListener('seeked',finish);resolve()};
    node.addEventListener('seeked',finish);setTimeout(finish,4000);node.currentTime=target;
  })}
  /* Put every video / GIF layer on the exact frame for time `ms`. */
  async function syncMedia(ms,gifs){
    for(var i=0;i<project.layers.length;i++){var layer=project.layers[i];if(layer.visible===false||!layer.src)continue;
      if(gifs[layer.id]){exportSources.set(layer.id,await gifs[layer.id].frameAt(ms));continue}
      var node=mediaFor(layer);if(node&&node.tagName==='VIDEO')await seekVideo(node,ms/1000)}
  }
  function waitMedia(){return Promise.all(project.layers.filter(function(l){return l.visible!==false&&l.src}).map(function(l){var n=mediaFor(l);if(!n)return null;
    return new Promise(function(resolve){var ok=function(){return n.tagName==='VIDEO'?n.readyState>=2:(n.complete&&n.naturalWidth)};if(ok()){resolve();return}
      var t=setInterval(function(){if(ok()){clearInterval(t);resolve()}},100);setTimeout(function(){clearInterval(t);resolve()},20000)})}))}
  /* Scenes with motion that is not periodic in the scene length (particles, videos, GIFs,
     local motion) get a short crossfade from the loop's end into its start, so the GIF
     loops without a jump. Text animations and frames are periodic and look unchanged. */
  function needsSeamBlend(){return project.layers.some(function(l){return l.visible!==false&&(l.type==='effect'||l.type==='dna'||l.src&&(l.animatedSource||/\.(gif|mp4|webm|mov)(\?|$)/i.test(l.src)||(l.localMotion&&(l.localMotion.strokes||[]).length)))})}
  async function renderExact(onProgress){
    var fps=30,ms=sceneMs(),count=Math.round(ms/1000*fps),loop=project.motion&&project.motion.loop,blend=(!loop||loop==='none')&&needsSeamBlend(),fade=Math.min(600,ms*.1);
    var gifs={},videos=[];
    await waitMedia();
    for(var i=0;i<project.layers.length;i++){var l=project.layers[i];if(l.visible===false||!l.src)continue;
      if(l.mediaType==='image/gif'||/\.gif(\?|$)/i.test(l.src)){try{gifs[l.id]=await SMBuilderExport.gifTrack(safeSource(l.src))}catch(e){gifs[l.id]=null}}
      var n=mediaFor(l);if(n&&n.tagName==='VIDEO'){n.pause();videos.push(n)}}
    var mix=document.createElement('canvas');mix.width=canvas.width;mix.height=canvas.height;var mctx=mix.getContext('2d');
    try{
      return await SMBuilderExport.encode(canvas,{fps:fps,count:count,maxBitrate:20e6,maxBytes:30e6,onProgress:onProgress,render:async function(i,t){
        if(blend&&t<fade){await syncMedia(t+ms,gifs);renderCanvas(t+ms);mctx.clearRect(0,0,mix.width,mix.height);mctx.drawImage(canvas,0,0)}
        await syncMedia(t,gifs);renderCanvas(t);
        if(blend&&t<fade){ctx.save();ctx.globalAlpha=1-t/fade;ctx.drawImage(mix,0,0);ctx.restore()}
      }});
    }finally{
      exportSources.clear();Object.keys(gifs).forEach(function(k){if(gifs[k])gifs[k].close()});
      videos.forEach(function(v){v.play().catch(function(){})});
    }
  }
  function canvasBlob(animated,onProgress){
    if(animated&&window.SMBuilderExport&&SMBuilderExport.supported()){
      exportingCanvas=true;manualClock=true;
      return renderExact(onProgress).then(function(blob){return {blob:blob,name:'showcase.webm'}},function(error){if(error&&error.code==='unsupported')return legacyBlob(true);throw error}).finally(function(){exportingCanvas=false;manualClock=false;markDirty()});
    }
    return legacyBlob(animated);
  }
  /* Fallback without WebCodecs: real-time capture, but for the exact scene length from the
     start of the loop and at a high bitrate. */
  function legacyBlob(animated){return new Promise(function(resolve,reject){exportingCanvas=true;renderCanvas(0);if(!animated){canvas.toBlob(function(b){exportingCanvas=false;b?resolve({blob:b,name:'showcase.png'}):reject(Error('Canvas export failed'))},'image/png');return}if(!canvas.captureStream||!window.MediaRecorder){exportingCanvas=false;reject(Error('Animated export is not supported in this browser'));return}
    var stream=canvas.captureStream(30),chunks=[],rec,start=performance.now(),ms=sceneMs(),alive=true;manualClock=true;
    project.layers.forEach(function(l){var n=l.src&&mediaFor(l);if(n&&n.tagName==='VIDEO'){try{n.currentTime=0;n.play().catch(function(){})}catch(e){}}});
    (function tick(){if(!alive)return;renderCanvas(Math.min(ms,performance.now()-start));requestAnimationFrame(tick)})();
    try{rec=new MediaRecorder(stream,{mimeType:'video/webm;codecs=vp9',videoBitsPerSecond:16e6})}catch(_){rec=new MediaRecorder(stream,{videoBitsPerSecond:16e6})}
    rec.ondataavailable=function(e){if(e.data.size)chunks.push(e.data)};
    rec.onerror=function(){alive=false;manualClock=false;exportingCanvas=false;reject(Error('Animation recording failed'))};
    rec.onstop=function(){alive=false;manualClock=false;exportingCanvas=false;stream.getTracks().forEach(function(x){x.stop()});resolve({blob:new Blob(chunks,{type:rec.mimeType||'video/webm'}),name:'showcase.webm'})};
    rec.start(250);setTimeout(function(){rec.stop()},ms)})}
  async function buildLoop(made){
    var settings=project.motion||{},fd=new FormData();fd.append('file',made.blob,made.name);fd.append('mode',settings.loop);fd.append('output_format','mp4');fd.append('fps','24');fd.append('duration',String(settings.duration||8));fd.append('transition',String(settings.fade||.5));
    status(BuilderMotionCopy.get('loop-upload'),'wait');
    var response=await fetch('/api/loop/start',{method:'POST',body:fd,credentials:'same-origin'}),job=await response.json();
    if(!response.ok||!job.ok)throw Error(job.code==='pro'?BuilderMotionCopy.get('loop-pro'):(job.msg||t('failed')));
    var deadline=Date.now()+20*60*1000;
    while(Date.now()<deadline){await new Promise(function(r){setTimeout(r,1400)});response=await fetch('/api/loop/status/'+encodeURIComponent(job.job_id),{credentials:'same-origin',cache:'no-store'});var state=await response.json();if(!response.ok||!state.ok||state.status==='error')throw Error(state.error||state.msg||t('failed'));status(BuilderMotionCopy.get('loop-upload')+' '+(state.pct||0)+'%','wait');if(state.status==='done'){response=await fetch(state.download_url,{credentials:'same-origin'});if(!response.ok)throw Error(t('failed'));return {blob:await response.blob(),name:'showcase-loop.mp4'}}}
    throw Error(t('failed'));
  }
  async function previewLoop(){
    if(root.classList.contains('is-exporting'))return;
    root.classList.add('is-exporting');motionEngine?.recording(true);var button=el('bmSeamPreview');button.disabled=true;
    try{var account=await fetch('/api/auth/me',{credentials:'same-origin',cache:'no-store'}).then(function(r){return r.json()});if(!account.is_pro)throw Error(BuilderMotionCopy.get('loop-pro'));status(t('exporting'),'wait');var made=await buildLoop(await canvasBlob(true)),host=el('builderLoopPreview');if(!host){host=document.createElement('section');host.id='builderLoopPreview';host.className='builder-loop-preview';host.innerHTML='<video muted loop autoplay playsinline controls></video><button type="button" class="btn ghost">×</button>';el('builderStatus').before(host);host.lastElementChild.onclick=function(){host.firstElementChild.pause();URL.revokeObjectURL(host.firstElementChild.src);host.remove()}}var video=host.firstElementChild;if(video.src)URL.revokeObjectURL(video.src);video.src=URL.createObjectURL(made.blob);video.onloadedmetadata=function(){video.currentTime=Math.max(0,video.duration-.7);video.play().catch(function(){})};video.ontimeupdate=function(){if(video.currentTime>.7&&video.currentTime<video.duration-1)video.currentTime=Math.max(.7,video.duration-.7)};status('', '')}catch(e){status(e.message,'bad')}finally{motionEngine?.recording(false);root.classList.remove('is-exporting');button.disabled=false}
  }
  /* Render the design (exact frames for animations), apply the Pro loop if chosen and
     reserve the export. Shared by the cutting hand-off and the direct Steam download. */
  async function prepareDesign(onRender){
    var animated=projectAnimated(),loop=project.motion?.loop;
    if(animated&&loop&&loop!=='none'){var account=await fetch('/api/auth/me',{credentials:'same-origin',cache:'no-store'}).then(function(r){return r.json()});if(!account.is_pro)throw Error(BuilderMotionCopy.get('loop-pro'))}
    var made=await canvasBlob(animated,onRender||function(done,total){status(t('exporting')+' '+Math.round(done/total*100)+'%','wait')});
    if(animated&&loop&&loop!=='none')made=await buildLoop(made);
    var reserve=await fetch('/api/builder/reserve-export',{method:'POST',credentials:'same-origin'}),d=await reserve.json();
    if(!reserve.ok||!d.ok){if(reserve.status===401)el('btnAuth')&&el('btnAuth').click();throw Error(d.msg||t('failed'))}
    window.__builderGalleryMeta={title:el('builderProjectName').value.trim(),background:project.layers.find(function(layer){return layer.type==='background'&&layer.buyUrl})?.buyUrl||'',mode:project.mode};
    return new File([made.blob],made.name,{type:made.blob.type});
  }
  el('builderExport').onclick=async function(){var btn=this;btn.disabled=true;status(t('exporting'),'wait');root.classList.add('is-exporting');motionEngine?.recording(true);try{var file=await prepareDesign(),dt=new DataTransfer();dt.items.add(file);document.dispatchEvent(new CustomEvent('sm:builder-sent',{detail:{file:file}}));el('fileInput').files=dt.files;el('fileInput').dispatchEvent(new Event('change',{bubbles:true}));window.__builderGalleryMeta={title:el('builderProjectName').value.trim(),background:project.layers.find(function(layer){return layer.type==='background'&&layer.buyUrl})?.buyUrl||'',mode:project.mode};var mode=document.querySelector('[data-mode="'+project.mode+'"]');if(mode)mode.click();var nav=document.querySelector('#nav button[data-tab="process"]');if(nav)nav.click();status(t('sent'),'ok')}catch(e){status(e.message,'bad')}finally{motionEngine?.recording(false);root.classList.remove('is-exporting');btn.disabled=false}};

  async function loadProjects(){var grid=el('builderProjectGrid');if(!grid)return;try{var r=await fetch('/api/builder/projects',{credentials:'same-origin'}),d=await r.json();if(!r.ok||!d.ok){grid.innerHTML='<div class="builder-empty-layers">'+t('login')+'</div>';return}grid.innerHTML='';if(!d.items.length){grid.innerHTML='<div class="builder-empty-layers">'+t('empty-projects')+'</div>';return}d.items.forEach(function(item){var card=document.createElement('article');card.className='builder-project-card';var until=item.expires_at?new Date(item.expires_at*1000).toLocaleDateString() : '';var pmode=['workshop','featured','split'].indexOf(item.showcase_mode)>=0?item.showcase_mode:'workshop';card.innerHTML='<div class="builder-project-card__preview" data-mode="'+pmode+'"><b>'+t('mode-'+pmode)+'</b></div><h3></h3><p></p><div class="builder-project-card__actions"><button class="btn ghost" data-edit>'+t('edit')+'</button><button class="btn ghost" data-delete>'+t('remove')+'</button></div>';card.querySelector('h3').textContent=item.name;card.querySelector('p').textContent=until?t('expires')+' '+until:t('permanent');card.querySelector('[data-edit]').onclick=function(){currentProjectId=item.id;project=clone(item.project);el('builderProjectName').value=item.name;selected=project.layers.length?project.layers[project.layers.length-1].id:'';resizeMode(project.mode);media.clear();renderLayers();openTool('builder')};card.querySelector('[data-delete]').onclick=async function(){await fetch('/api/builder/projects/'+encodeURIComponent(item.id),{method:'DELETE',credentials:'same-origin'});loadProjects()};grid.appendChild(card)})}catch(e){el('builderProjectsStatus').textContent=e.message}}

  function loadExternalProject(value,name){
    if(!value||!Array.isArray(value.layers))return false;
    currentProjectId='';project=clone(value);selected=project.layers.length?project.layers[project.layers.length-1].id:'';el('builderProjectName').value=String(name||'Steam DNA');
    media.forEach(function(node){if(node.pause)node.pause()});media.clear();resizeMode(project.mode||'workshop');renderLayers();openTool('builder');editorHistory?.commit();return true;
  }

  function openTool(name){var nav=document.querySelector('#nav button[data-tab="'+name+'"]');if(nav)nav.click();document.querySelectorAll('[data-open-tool]').forEach(function(b){b.classList.toggle('active',b.dataset.openTool===name)});if(name==='projects')loadProjects();if(name==='builder')requestAnimationFrame(updateGuides)}
  document.querySelectorAll('[data-open-tool]').forEach(function(b){b.onclick=function(){if(b.dataset.openTool==='builder'&&b.closest('.builder-projects-page')){currentProjectId='';project=freshProject('workshop');selected='';el('builderProjectName').value=lang()==='ru'?'Моя витрина':'My showcase';media.clear();resizeMode('workshop');renderLayers()}openTool(b.dataset.openTool)}});
  document.querySelectorAll('#nav button[data-tab]').forEach(function(b){b.addEventListener('click',function(){var name=b.dataset.tab,inWorkspace=['process','dna','builder','projects'].includes(name),sw=document.querySelector('.workspace-switch');if(sw)sw.hidden=!inWorkspace;document.querySelectorAll('[data-open-tool]').forEach(function(x){x.classList.toggle('active',inWorkspace&&x.dataset.openTool===name)})})});
  function syncFrameFx(layer){var style=layer&&layer.frameStyle,api=window.SMSquaresFx,shape=(layer&&layer.frameShape)||'rect';el('builderFramePlateWrap').hidden=shape==='rect';renderFramePicker(layer);el('builderFrameColor2Wrap').hidden=['double','comet','dashes'].indexOf(style)<0;el('builderFrameSpeedWrap').hidden=!(api&&api.isAnimatedFrame(style));el('builderFrameFxRow').hidden=el('builderFrameColor2Wrap').hidden&&el('builderFrameSpeedWrap').hidden}
  /* Frame designs and animations as pictures (shared with Process / Workshop Studio). */
  function renderFramePicker(layer){
    var api=window.SMSquaresFx,host=el('builderFramePicker');if(!api||!api.shapePicker||!host||!layer||layer.type!=='frame')return;
    var lang=window.SMLang?.get?.()||document.documentElement.lang||'en',mode=layer.frameTarget==='outer'?'featured':project.mode;
    function commit(){motionEngine?.invalidate();syncInspector()}
    function label(key){var node=document.createElement('p');node.className='builder-frame-picker__label';node.textContent=api.t(key,lang);return node}
    var select=el('builderFrameShape');if(select&&select.options.length!==(api.FRAME_SHAPES||[]).length){select.replaceChildren();(api.FRAME_SHAPES||[]).forEach(function(key){var option=document.createElement('option');option.value=key;option.textContent=api.t('shape_'+key,lang);select.append(option)})}
    host.replaceChildren(
      label('frame'),
      api.shapePicker({mode:mode,value:layer.frameShape||'rect',color:layer.color||'#52d5ff',language:lang,onPick:function(key){if(key!=='rect'&&key!==layer.frameShape&&!layer.framePlate)layer.framePlate=100;layer.frameShape=key;if(key!=='rect'&&(layer.frameStyle==='solid'||!layer.frameStyle))layer.frameStyle='shimmer';commit()}}),
      label('animation'),
      api.stylePicker({value:layer.frameStyle||'solid',color:layer.color||'#52d5ff',color2:layer.color2||'#8a62ff',language:lang,styles:api.FRAME_STYLES.filter(function(key){return key!=='none'}),onPick:function(key){layer.frameStyle=key;commit()}}),
      label('color'),
      api.colorSwatches({value:layer.color||'#52d5ff',language:lang,onPick:function(value){layer.color=value;el('builderFrameColor').value=value;motionEngine?.invalidate()}})
    );
  }
  function applyFrameFxLanguage(){var api=window.SMSquaresFx;if(!api)return;var lang=window.SMLang?.get?.()||document.documentElement.lang||'en';document.querySelectorAll('[data-fx-i]').forEach(function(n){n.textContent=api.t(n.dataset.fxI,lang)+(n.dataset.fxBeta?' · '+api.t('beta',lang):'')})}
  function applyLanguage(){applyFrameFxLanguage();syncAiNote();document.querySelectorAll('[data-builder-i]').forEach(function(n){n.textContent=t(n.dataset.builderI)});document.querySelectorAll('[data-builder-i-title]').forEach(function(n){var value=t(n.dataset.builderITitle);n.title=value;n.setAttribute('aria-label',value)});renderLayers();loadProjects()}
  window.addEventListener('sm:langchange',applyLanguage);
  window.ShowcaseBuilder={loadProject:loadExternalProject,open:function(){openTool('builder')}};
  if(window.BuilderMotion)motionEngine=BuilderMotion.create(root,{canvas:canvas,project:function(){return project},layer:currentLayer,commit:function(){editorHistory?.commit()},guides:updateGuides,previewLoop:previewLoop,geometry:function(layer){var node=mediaFor(layer),box=layer.type==='background'?coverBox(node||{}):containBox(node||{},layer);return {x:layer.x*canvas.width,y:layer.y*canvas.height,w:box.w,h:box.h,rotation:(layer.rotation||0)*Math.PI/180}}});
  applyLanguage();resizeMode('workshop');renderLayers();requestAnimationFrame(draw);
  if(window.createBuilderHistory)editorHistory=window.createBuilderHistory(root,function(){return {project:project,name:el('builderProjectName').value,id:currentProjectId,selected:selected}},function(value){project=clone(value.project);currentProjectId=value.id||'';selected=value.selected||'';el('builderProjectName').value=value.name||'';media.forEach(function(node){if(node.pause)node.pause()});media.clear();resizeMode(project.mode);renderLayers();root.querySelectorAll('input[type="range"]').forEach(function(n){var progress=(n.value-n.min)/(n.max-n.min)*100;n.style.setProperty('--range-progress',progress+'%')})});
  window.WorkspaceEditor?.builderReady();
  /* Small API for the layout script (builder-layout.js): tool rail, inline rename. */
  window.SMBuilder={root:root,animated:function(){return projectAnimated()},layers:function(){return project.layers.slice()},current:currentLayer,
    select:function(id){selected=id||'';renderLayers()},redraw:markDirty,
    sync:function(){syncInspector()},commit:function(){editorHistory?.commit()},
    /* Move a layer to index (0 = bottom, like project.layers). */
    move:function(id,index){var from=project.layers.findIndex(function(l){return l.id===id});if(from<0)return;var layer=project.layers.splice(from,1)[0];index=Math.max(0,Math.min(project.layers.length,index));project.layers.splice(index,0,layer);renderLayers();editorHistory?.commit()},
    media:function(layer){return mediaFor(layer)},
    /* Draws one effect on a small tile canvas (effect picker previews). */
    previewEffect:function(target,name,color,now){var oc=canvas,octx=ctx;canvas=target;ctx=target.getContext('2d');try{ctx.fillStyle='#06101c';ctx.fillRect(0,0,target.width,target.height);drawEffect({effect:name,color:color||'#52d5ff',opacity:1,scale:.55,rotation:0,x:.5,y:.5,effectSpeed:100,effectDensity:100,animation:'none'},now)}finally{canvas=oc;ctx=octx}},
    rename:function(id,name){var layer=project.layers.find(function(l){return l.id===id});if(!layer)return;layer.name=String(name||'').trim().slice(0,80)||t(layer.type);renderLayers();editorHistory?.commit()},
    typeName:function(type){return type==='dna'?'Steam DNA':t(type)},
    /* Box of a layer in canvas pixels (centre, size, rotation) for on-canvas handles. */
    box:function(layer){layer=layer||currentLayer();if(!layer)return null;var W=canvas.width,H=canvas.height,s=layer.scale||1,base={cx:(layer.x==null?.5:layer.x)*W,cy:(layer.y==null?.5:layer.y)*H,rot:layer.rotation||0,W:W,H:H};
      if(layer.type==='character'||(layer.type==='effect'&&layer.src)){var node=mediaFor(layer);if(!node||!(node.naturalWidth||node.videoWidth))return null;var b=containBox(node,layer);base.w=b.w;base.h=b.h;return base}
      if(layer.type==='text'){ctx.save();ctx.font=(layer.fontWeight||800)+' '+(layer.fontSize||64)+'px "'+safeFontName(layer.font)+'"';var lines=String(layer.text||'').split('\n'),w=0;if(layer.textDir==='vertical'&&window.SMTextFx){var m=SMTextFx.measure(ctx,lines,layer.fontSize||64,true);ctx.restore();base.w=m.width*s+8;base.h=m.height*s+4;return base}lines.forEach(function(l){w=Math.max(w,ctx.measureText(l).width)});ctx.restore();base.w=Math.min(w,W*.9)*s+8;base.h=lines.length*(layer.fontSize||64)*1.12*s+4;return base}
      if(layer.type==='dna'){var d=Math.min(W,H)*.275*2.2*s;base.w=base.h=d;return base}
      return null},
    height:function(){return canvas.height},
    setHeight:function(h){var v=setHeight(h);return v},
    commitHeight:function(){editorHistory?.commit()},
    /* Where the current background meets the Steam profile (for the stage guides). */
    steamInfo:function(){var bg=project.layers.find(function(l){return l.type==='background'&&l.visible!==false&&l.src});if(!bg||!bg.steamAlign)return null;var n=mediaFor(bg);if(!n)return null;var size=mediaSize(n);return {width:size[0],height:size[1],parts:steamParts(),offsetY:Number(project.steamOffsetY)||0,layer:bg,node:n}},
    setSteamOffset:function(v){project.steamOffsetY=Math.round(Math.max(-600,Math.min(600,Number(v)||0)));markDirty();return project.steamOffsetY},
    setSteamAlign:function(on){var bg=project.layers.find(function(l){return l.type==='background'});if(!bg)return;bg.steamAlign=!!on;markDirty();editorHistory?.commit()},
    exportDesign:function(onProgress){return canvasBlob(projectAnimated(),onProgress)},
    /* Direct download flow: busy state, render + reserve, status line. */
    prepare:async function(onRender){root.classList.add('is-exporting');motionEngine?.recording(true);try{return await prepareDesign(onRender)}finally{motionEngine?.recording(false);root.classList.remove('is-exporting')}},
    status:function(message,kind){status(message,kind)},
    project:function(){return project}
  };
})();
