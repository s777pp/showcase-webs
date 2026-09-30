/* "Create a design" layout (2026-09-29): tool rail -> context panel -> stage -> layers.
   The editor logic stays in showcase-builder.js; this script only moves its existing
   controls into a clearer layout, keeps every id, and adds inline layer renaming.
   Loaded right after showcase-builder.js (tool-loader "builder" group). */
(function () {
  'use strict';
  var root = document.getElementById('showcaseBuilder');
  if (!root || root.dataset.bxReady || !window.SMBuilder) return;
  root.dataset.bxReady = '1';
  var $ = function (id) { return document.getElementById(id); };
  var LANGS = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'];
  var COPY = {
    background: ['Background', 'Фон', 'Hintergrund', 'Arka plan', 'Arrière-plan', 'Фон', 'Fondo', 'Fundo'],
    character: ['Character', 'Персонаж', 'Figur', 'Karakter', 'Personnage', 'Персонаж', 'Personaje', 'Personagem'],
    text: ['Text', 'Текст', 'Text', 'Metin', 'Texte', 'Текст', 'Texto', 'Texto'],
    frame: ['Frame', 'Рамка', 'Rahmen', 'Çerçeve', 'Cadre', 'Рамка', 'Marco', 'Moldura'],
    effect: ['Effects', 'Эффекты', 'Effekte', 'Efektler', 'Effets', 'Ефекти', 'Efectos', 'Efeitos'],
    templates: ['Templates', 'Шаблоны', 'Vorlagen', 'Şablonlar', 'Modèles', 'Шаблони', 'Plantillas', 'Modelos'],
    scene: ['Scene length', 'Длина сцены', 'Szenenlänge', 'Sahne süresi', 'Durée de scène', 'Довжина сцени', 'Duración de escena', 'Duração da cena'],
    hint_background: ['The picture or video your showcase is built on: your own file or a Steam background.', 'Картинка или видео, на котором строится витрина: свой файл или фон из Steam.', 'Bild oder Video als Grundlage: eigene Datei oder ein Steam-Hintergrund.', 'Vitrinin temeli olan görsel ya da video: kendi dosyan veya bir Steam arka planı.', 'L’image ou la vidéo de base : votre fichier ou un arrière-plan Steam.', 'Зображення або відео, на якому будується вітрина: свій файл або фон зі Steam.', 'La imagen o vídeo base: tu archivo o un fondo de Steam.', 'A imagem ou vídeo base: seu arquivo ou um fundo da Steam.'],
    hint_character: ['A character or object on top of the background. Transparency is kept.', 'Персонаж или объект поверх фона. Прозрачность сохраняется.', 'Eine Figur oder ein Objekt über dem Hintergrund. Transparenz bleibt erhalten.', 'Arka planın üstünde karakter veya nesne. Şeffaflık korunur.', 'Un personnage ou objet au-dessus du fond. La transparence est conservée.', 'Персонаж або об’єкт поверх фону. Прозорість зберігається.', 'Un personaje u objeto sobre el fondo. Se conserva la transparencia.', 'Um personagem ou objeto sobre o fundo. A transparência é mantida.'],
    hint_text: ['A title, nickname or signature.', 'Надпись: ник, название или подпись.', 'Titel, Nickname oder Signatur.', 'Başlık, takma ad veya imza.', 'Un titre, un pseudo ou une signature.', 'Напис: нік, назва або підпис.', 'Un título, apodo o firma.', 'Um título, apelido ou assinatura.'],
    hint_frame: ['A frame around the showcase: shape, animation and colour.', 'Рамка вокруг витрины: форма, анимация и цвет.', 'Ein Rahmen um die Vitrine: Form, Animation und Farbe.', 'Vitrin çevresinde çerçeve: şekil, animasyon ve renk.', 'Un cadre autour de la vitrine : forme, animation et couleur.', 'Рамка навколо вітрини: форма, анімація і колір.', 'Un marco alrededor del expositor: forma, animación y color.', 'Uma moldura em volta da vitrine: forma, animação e cor.'],
    hint_effect: ['An animated layer: petals, snow, rain, sparks and more.', 'Анимированный слой: лепестки, снег, дождь, искры и другое.', 'Eine animierte Ebene: Blüten, Schnee, Regen, Funken und mehr.', 'Animasyonlu katman: yapraklar, kar, yağmur, kıvılcımlar ve dahası.', 'Un calque animé : pétales, neige, pluie, étincelles…', 'Анімований шар: пелюстки, сніг, дощ, іскри тощо.', 'Una capa animada: pétalos, nieve, lluvia, chispas y más.', 'Uma camada animada: pétalas, neve, chuva, faíscas e mais.'],
    hint_templates: ['Ready combinations of title, frame and effect. Your pictures are not replaced.', 'Готовые сочетания надписи, рамки и эффекта. Твои картинки не заменяются.', 'Fertige Kombinationen aus Titel, Rahmen und Effekt. Deine Bilder bleiben.', 'Hazır başlık, çerçeve ve efekt kombinasyonları. Görsellerin değişmez.', 'Combinaisons prêtes de titre, cadre et effet. Vos images restent.', 'Готові поєднання напису, рамки та ефекту. Твої зображення не замінюються.', 'Combinaciones listas de título, marco y efecto. Tus imágenes no se reemplazan.', 'Combinações prontas de título, moldura e efeito. Suas imagens não são trocadas.'],
    hint_scene: ['How long the animation lasts, how it loops and how strong the motion is.', 'Сколько длится анимация, как она зацикливается и насколько сильное движение.', 'Bewegung der ganzen Vitrine: Länge, Schleife und Intensität.', 'Tüm vitrinin hareketi: süre, döngü ve yoğunluk.', 'Mouvement de toute la vitrine : durée, boucle et intensité.', 'Рух усієї вітрини: тривалість, цикл та інтенсивність.', 'Movimiento de todo el expositor: duración, bucle e intensidad.', 'Movimento da vitrine inteira: duração, loop e intensidade.'],
    add_background: ['Upload a background', 'Загрузить фон', 'Hintergrund hochladen', 'Arka plan yükle', 'Importer un fond', 'Завантажити фон', 'Subir fondo', 'Enviar fundo'],
    add_character: ['Upload a character', 'Загрузить персонажа', 'Figur hochladen', 'Karakter yükle', 'Importer un personnage', 'Завантажити персонажа', 'Subir personaje', 'Enviar personagem'],
    add_text: ['Add text', 'Добавить текст', 'Text hinzufügen', 'Metin ekle', 'Ajouter du texte', 'Додати текст', 'Añadir texto', 'Adicionar texto'],
    add_frame: ['Add a frame', 'Добавить рамку', 'Rahmen hinzufügen', 'Çerçeve ekle', 'Ajouter un cadre', 'Додати рамку', 'Añadir marco', 'Adicionar moldura'],
    add_effect: ['Add an effect', 'Добавить эффект', 'Effekt hinzufügen', 'Efekt ekle', 'Ajouter un effet', 'Додати ефект', 'Añadir efecto', 'Adicionar efeito'],
    add_more: ['Add another', 'Добавить ещё', 'Weitere hinzufügen', 'Bir tane daha', 'En ajouter un', 'Додати ще', 'Añadir otro', 'Adicionar outro'],
    on_showcase: ['On the showcase', 'На витрине', 'Auf der Vitrine', 'Vitrinde', 'Sur la vitrine', 'На вітрині', 'En el expositor', 'Na vitrine'],
    layers: ['Layers', 'Слои', 'Ebenen', 'Katmanlar', 'Calques', 'Шари', 'Capas', 'Camadas'],
    selected_bg: ['Selected background', 'Выбранный фон', 'Gewählter Hintergrund', 'Seçilen arka plan', 'Fond choisi', 'Вибраний фон', 'Fondo elegido', 'Fundo escolhido'],
    add_layer: ['Add a layer', 'Добавить слой', 'Ebene hinzufügen', 'Katman ekle', 'Ajouter un calque', 'Додати шар', 'Añadir capa', 'Adicionar camada'],
    rename: ['Rename', 'Переименовать', 'Umbenennen', 'Yeniden adlandır', 'Renommer', 'Перейменувати', 'Renombrar', 'Renomear'],
    rename_hint: ['Drag layers to change the order, double-click a name to rename it. Upper layers are in front.', 'Перетаскивай слои, чтобы менять порядок, двойной клик по названию — переименовать. Верхние слои — спереди.', 'Ziehe Ebenen, um die Reihenfolge zu ändern, Doppelklick auf einen Namen zum Umbenennen. Obere Ebenen liegen vorn.', 'Sırayı değiştirmek için katmanları sürükle, yeniden adlandırmak için ada çift tıkla. Üstteki katmanlar öndedir.', 'Faites glisser les calques pour changer l’ordre, double-cliquez sur un nom pour le renommer. Les calques du haut sont devant.', 'Перетягуй шари, щоб змінити порядок, подвійний клік по назві — перейменувати. Верхні шари — спереду.', 'Arrastra las capas para cambiar el orden, doble clic en un nombre para renombrarlo. Las capas de arriba van delante.', 'Arraste as camadas para mudar a ordem, clique duas vezes no nome para renomear. Camadas de cima ficam na frente.'],
    drag: ['Drag to reorder (Alt + ↑/↓ on the keyboard)', 'Перетащи, чтобы поменять порядок (Alt + ↑/↓ с клавиатуры)', 'Ziehen zum Umsortieren (Alt + ↑/↓ per Tastatur)', 'Sıralamak için sürükle (klavyede Alt + ↑/↓)', 'Glisser pour réordonner (Alt + ↑/↓ au clavier)', 'Перетягни, щоб змінити порядок (Alt + ↑/↓ з клавіатури)', 'Arrastra para reordenar (Alt + ↑/↓ con el teclado)', 'Arraste para reordenar (Alt + ↑/↓ no teclado)'],
    textdir: ['Direction', 'Направление', 'Richtung', 'Yön', 'Direction', 'Напрямок', 'Dirección', 'Direção'],
    textdir_h: ['Horizontal', 'Горизонтально', 'Waagerecht', 'Yatay', 'Horizontal', 'Горизонтально', 'Horizontal', 'Horizontal'],
    textdir_v: ['Vertical', 'Вертикально', 'Senkrecht', 'Dikey', 'Vertical', 'Вертикально', 'Vertical', 'Vertical'],
    textfx_speed: ['Speed', 'Скорость', 'Tempo', 'Hız', 'Vitesse', 'Швидкість', 'Velocidad', 'Velocidade'],
    textfx_speed_hint: ['Repeats per scene loop. For a slower animation make the scene longer.', 'Сколько раз анимация проходит за цикл сцены. Чтобы медленнее — увеличь длину сцены.', 'Wiederholungen pro Szenen-Schleife. Langsamer: Szene verlängern.', 'Sahne döngüsü başına tekrar. Daha yavaş için sahneyi uzat.', 'Répétitions par boucle de scène. Plus lent : allongez la scène.', 'Скільки разів анімація проходить за цикл сцени. Щоб повільніше — збільш довжину сцени.', 'Repeticiones por ciclo de escena. Más lento: alarga la escena.', 'Repetições por ciclo da cena. Mais lento: aumente a cena.'],
    media_loading: ['Loading the animated background{pct}…', 'Загружаем анимированный фон{pct}…', 'Animierter Hintergrund lädt{pct}…', 'Hareketli arka plan yükleniyor{pct}…', 'Chargement du fond animé{pct}…', 'Завантажуємо анімоване тло{pct}…', 'Cargando el fondo animado{pct}…', 'Carregando o fundo animado{pct}…'],
    media_slow: ['Animated backgrounds are video files of several MB, so the time depends on your connection. The editor keeps working meanwhile.', 'Анимированные фоны — это видео на несколько МБ, поэтому время зависит от скорости интернета. Редактор при этом работает.', 'Animierte Hintergründe sind Videos mit mehreren MB, die Dauer hängt von deiner Verbindung ab. Der Editor funktioniert weiter.', 'Hareketli arka planlar birkaç MB’lık videolardır; süre bağlantına bağlı. Bu sırada editör çalışır.', 'Les fonds animés sont des vidéos de plusieurs Mo : la durée dépend de votre connexion. L’éditeur reste utilisable.', 'Анімовані тла — це відео на кілька МБ, тож час залежить від швидкості інтернету. Редактор тим часом працює.', 'Los fondos animados son vídeos de varios MB: el tiempo depende de tu conexión. El editor sigue funcionando.', 'Fundos animados são vídeos de vários MB, então o tempo depende da sua conexão. O editor continua funcionando.'],
    media_error: ['The background could not be loaded. Check the connection or pick it again.', 'Не удалось загрузить фон. Проверь интернет или выбери его ещё раз.', 'Der Hintergrund konnte nicht geladen werden. Prüfe die Verbindung oder wähle ihn erneut.', 'Arka plan yüklenemedi. Bağlantını kontrol et ya da yeniden seç.', 'Impossible de charger le fond. Vérifiez la connexion ou choisissez-le à nouveau.', 'Не вдалося завантажити тло. Перевір інтернет або обери його ще раз.', 'No se pudo cargar el fondo. Revisa la conexión o elígelo de nuevo.', 'Não foi possível carregar o fundo. Verifique a conexão ou escolha de novo.'],
    textfx_none: ['No animation', 'Без анимации', 'Keine Animation', 'Animasyon yok', 'Sans animation', 'Без анімації', 'Sin animación', 'Sem animação'],
    textfx_color: ['Glow colour', 'Цвет свечения', 'Leuchtfarbe', 'Parıltı rengi', 'Couleur de lueur', 'Колір світіння', 'Color del brillo', 'Cor do brilho'],
    textfx_hint: ['The animation repeats with the scene length and plays in the exported GIF or video.', 'Анимация повторяется по длине сцены и сохраняется в экспорте GIF или видео.', 'Die Animation wiederholt sich mit der Szenenlänge und landet im exportierten GIF oder Video.', 'Animasyon sahne süresiyle tekrarlanır ve dışa aktarılan GIF ya da videoda oynar.', 'L’animation se répète selon la durée de scène et figure dans le GIF ou la vidéo exportés.', 'Анімація повторюється з довжиною сцени й зберігається в експорті GIF або відео.', 'La animación se repite con la duración de la escena y se incluye en el GIF o vídeo exportado.', 'A animação se repete com a duração da cena e aparece no GIF ou vídeo exportado.'],
    scene_hint: ['Looks at the background under the character and tunes brightness, contrast, saturation and tint so the character sits in the same light.', 'Смотрит на фон под персонажем и подбирает яркость, контраст, насыщенность и оттенок, чтобы персонаж был в том же свете, что и сцена.', 'Analysiert den Hintergrund hinter der Figur und passt Helligkeit, Kontrast, Sättigung und Farbton an, damit die Figur im selben Licht steht.', 'Karakterin arkasındaki arka plana bakar ve karakter aynı ışıkta dursun diye parlaklık, kontrast, doygunluk ve tonu ayarlar.', 'Analyse le fond derrière le personnage et règle luminosité, contraste, saturation et teinte pour qu’il soit dans la même lumière.', 'Дивиться на тло під персонажем і підбирає яскравість, контраст, насиченість і відтінок, щоб персонаж був у тому ж світлі, що й сцена.', 'Mira el fondo detrás del personaje y ajusta brillo, contraste, saturación y tono para que quede con la misma luz.', 'Analisa o fundo atrás do personagem e ajusta brilho, contraste, saturação e tom para que ele fique na mesma luz.'],
    scene_apply: ['Match the scene', 'Подстроить под сцену', 'An Szene anpassen', 'Sahneye uydur', 'Accorder à la scène', 'Підлаштувати під сцену', 'Ajustar a la escena', 'Ajustar à cena'],
    scene_strength: ['Strength', 'Сила', 'Stärke', 'Güç', 'Intensité', 'Сила', 'Intensidad', 'Intensidade'],
    scene_undo: ['Original colours', 'Исходные цвета', 'Originalfarben', 'Orijinal renkler', 'Couleurs d’origine', 'Початкові кольори', 'Colores originales', 'Cores originais'],
    scene_done: ['Matched: {what}. Fine-tune it in Colour correction.', 'Подстроено: {what}. Точнее можно поправить в «Цветокоррекции».', 'Angepasst: {what}. Feinschliff unter Farbkorrektur.', 'Uyduruldu: {what}. İnce ayar Renk düzeltme bölümünde.', 'Accordé : {what}. Affinez dans Correction des couleurs.', 'Підлаштовано: {what}. Точніше можна виправити в «Корекції кольору».', 'Ajustado: {what}. Afínalo en Corrección de color.', 'Ajustado: {what}. Refine em Correção de cor.'],
    scene_same: ['the character already fits the scene', 'персонаж уже подходит к сцене', 'die Figur passt schon zur Szene', 'karakter sahneye zaten uyuyor', 'le personnage va déjà avec la scène', 'персонаж уже пасує до сцени', 'el personaje ya encaja en la escena', 'o personagem já combina com a cena'],
    scene_darker: ['darker', 'темнее', 'dunkler', 'daha koyu', 'plus sombre', 'темніше', 'más oscuro', 'mais escuro'],
    scene_lighter: ['lighter', 'светлее', 'heller', 'daha açık', 'plus clair', 'світліше', 'más claro', 'mais claro'],
    scene_softer: ['softer contrast', 'мягче контраст', 'weicherer Kontrast', 'daha yumuşak kontrast', 'contraste plus doux', 'м’якший контраст', 'contraste más suave', 'contraste mais suave'],
    scene_harder: ['more contrast', 'больше контраста', 'mehr Kontrast', 'daha fazla kontrast', 'plus de contraste', 'більше контрасту', 'más contraste', 'mais contraste'],
    scene_muted: ['calmer colours', 'спокойнее цвета', 'ruhigere Farben', 'daha sakin renkler', 'couleurs plus calmes', 'спокійніші кольори', 'colores más tranquilos', 'cores mais calmas'],
    scene_vivid: ['richer colours', 'сочнее цвета', 'kräftigere Farben', 'daha canlı renkler', 'couleurs plus riches', 'соковитіші кольори', 'colores más vivos', 'cores mais vivas'],
    scene_tint: ['tint toward the background', 'оттенок в сторону фона', 'Farbton zum Hintergrund', 'ton arka plana doğru', 'teinte vers le fond', 'відтінок у бік тла', 'tono hacia el fondo', 'tom em direção ao fundo'],
    scene_nobg: ['Add a background first: there is nothing to match yet.', 'Сначала добавь фон: пока не под что подстраиваться.', 'Füge zuerst einen Hintergrund hinzu.', 'Önce bir arka plan ekle: henüz uyulacak bir şey yok.', 'Ajoutez d’abord un fond : rien à accorder pour l’instant.', 'Спершу додай тло: поки нема під що підлаштовуватися.', 'Primero añade un fondo: aún no hay nada que ajustar.', 'Adicione um fundo primeiro: ainda não há o que ajustar.'],
    scene_wait: ['The picture is still loading, try again in a second.', 'Картинка ещё загружается, попробуй через секунду.', 'Das Bild lädt noch, versuche es gleich noch einmal.', 'Görsel hâlâ yükleniyor, birazdan tekrar dene.', 'L’image charge encore, réessayez dans une seconde.', 'Зображення ще вантажиться, спробуй за секунду.', 'La imagen aún se carga, inténtalo en un segundo.', 'A imagem ainda está carregando, tente em um segundo.'],
    scene_blocked: ['This background cannot be analysed in the browser. Use Colour correction manually.', 'Этот фон нельзя проанализировать в браузере. Поправь цвета вручную в «Цветокоррекции».', 'Dieser Hintergrund lässt sich im Browser nicht analysieren. Nutze die Farbkorrektur manuell.', 'Bu arka plan tarayıcıda analiz edilemiyor. Renk düzeltmeyi elle kullan.', 'Ce fond ne peut pas être analysé dans le navigateur. Utilisez la correction manuelle.', 'Це тло не можна проаналізувати в браузері. Виправ кольори вручну в «Корекції кольору».', 'Este fondo no se puede analizar en el navegador. Usa la corrección de color manual.', 'Este fundo não pode ser analisado no navegador. Use a correção de cor manualmente.'],
    transform: ['Size, rotation, opacity', 'Размер, поворот, прозрачность', 'Größe, Drehung, Deckkraft', 'Boyut, döndürme, opaklık', 'Taille, rotation, opacité', 'Розмір, поворот, прозорість', 'Tamaño, giro, opacidad', 'Tamanho, rotação, opacidade'],
    empty_layers: ['Nothing here yet. Start with a background.', 'Пока пусто. Начни с фона.', 'Noch leer. Beginne mit einem Hintergrund.', 'Henüz boş. Bir arka planla başla.', 'Encore vide. Commencez par un fond.', 'Поки порожньо. Почни з фону.', 'Aún vacío. Empieza con un fondo.', 'Ainda vazio. Comece com um fundo.']
  };
  var LAYER_TOOLS = ['background', 'character', 'text', 'frame', 'effect'];
  var TOOLS = LAYER_TOOLS.concat(['templates', 'scene']);
  var EXTRA_ICONS = {
    templates: '<rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><path d="M17 13.5v7M13.5 17h7"/>',
    scene: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M10 9.5v5l4-2.5z"/>',
    rename: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
    plus: '<path d="M12 5v14M5 12h14"/>'
  };
  var tool = 'background';

  function language() { return (window.SMLang && SMLang.get && SMLang.get()) || document.documentElement.lang || 'en'; }
  function t(key) { var i = Math.max(0, LANGS.indexOf(language())); var row = COPY[key] || []; return row[i] || row[0] || key; }
  function icon(name) {
    if (EXTRA_ICONS[name]) return '<svg class="editor-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' + EXTRA_ICONS[name] + '</svg>';
    return window.WorkspaceEditor ? WorkspaceEditor.icon(name) : '';
  }
  function node(tag, cls, html) { var n = document.createElement(tag); if (cls) n.className = cls; if (html != null) n.innerHTML = html; return n; }

  // ------------------------------------------------------------------ skeleton
  root.classList.add('bx');
  var rail = $('bxRail'), panel = $('bxPanel');
  if (!rail) { rail = node('nav', 'bx-rail'); rail.id = 'bxRail'; root.prepend(rail); }
  if (!panel) { panel = node('aside', 'bx-panel card'); panel.id = 'bxPanel'; rail.after(panel); }
  rail.setAttribute('role', 'tablist');
  TOOLS.forEach(function (key) {
    var b = node('button', 'bx-rail__tool');
    b.type = 'button'; b.dataset.bxTool = key; b.setAttribute('role', 'tab');
    b.innerHTML = '<span class="bx-rail__icon">' + icon(key) + '</span><span class="bx-rail__label"></span><i class="bx-rail__count" hidden></i>';
    if (key === 'templates') rail.append(node('span', 'bx-rail__sep'));
    b.addEventListener('click', function () { setTool(key, false); });
    rail.append(b);
  });
  panel.innerHTML = '<header class="bx-panel__head"><strong class="bx-panel__title" role="heading" aria-level="2"></strong><p class="bx-panel__hint"></p></header><div class="bx-panel__scroll"></div>';
  var scroll = panel.querySelector('.bx-panel__scroll');
  function section(name) { var s = node('section', 'bx-section bx-section--' + name); s.dataset.bxSection = name; scroll.append(s); return s; }
  var addSection = section('add'), bgSection = section('background'), templatesSection = section('templates'),
    sceneSection = section('scene'), inspectorSection = section('inspector');

  // Add buttons: the existing [data-add-layer] buttons keep their handlers.
  var addButtons = {};
  root.querySelectorAll('[data-add-layer]').forEach(function (button) {
    addButtons[button.dataset.addLayer] = button;
    button.classList.add('bx-add');
    var label = button.querySelector('[data-builder-i]');
    if (label) { label.removeAttribute('data-builder-i'); label.dataset.bxLabel = '1'; }
    addSection.append(button);
  });
  var chips = node('div', 'bx-chips'); addSection.prepend(chips);

  // Background extras: Steam backgrounds + catalog.
  var source = $('builderSourcePanel'); if (source) bgSection.append(source);
  var catalog = $('builderCatalog'); if (catalog) bgSection.append(catalog);
  // Templates: always open inside their tool.
  var templates = $('builderTemplates'); if (templates) { templates.open = true; templatesSection.append(templates); }
  // Scene motion: the scene-wide details panel from builder-motion.js.
  var scene = root.querySelector('.builder-motion-panel:not(#bmLocalPanel)'); if (scene) { scene.open = true; sceneSection.append(scene); }

  // Element settings move from the right column into the panel.
  var inspector = $('builderInspector');
  if (inspector) {
    inspectorSection.append(inspector);
    var nameLabel = $('builderLayerName') && $('builderLayerName').closest('label');
    if (nameLabel) nameLabel.classList.add('bx-hidden-name');
    var title = inspector.querySelector('.builder-panel-title'); if (title) title.classList.add('bx-hidden');
    var grade = $('builderGrade'), media = $('builderMediaControls');
    if (grade && media) media.after(grade);
    var group = node('details', 'bx-transform'); group.innerHTML = '<summary></summary>';
    ['builderScale', 'builderRotation', 'builderOpacity', 'bmLinked'].forEach(function (id) {
      var control = $(id); var label = control && control.closest('label'); if (label) group.append(label);
    });
    inspector.append(group);
  }
  var emptyInspector = $('builderInspectorEmpty'); if (emptyInspector) emptyInspector.classList.add('bx-hidden');
  var tools = root.querySelector('.builder-tools'); if (tools) tools.classList.add('bx-hidden');
  var mobileNav = document.querySelector('#tab-builder .editor-mobile-nav'); if (mobileNav) mobileNav.classList.add('bx-hidden');

  // Stage: modes, undo/redo and canvas options in one top bar.
  var head = root.querySelector('.builder-stage-head');
  var history = root.querySelector('.builder-history');
  var canvasOptions = root.querySelector('.editor-canvas-options') || root.querySelector('.builder-canvas-toolbar');
  /* One tidy toolbar under the showcase type switch: edit history, canvas options and,
     when the background is sold on Steam, a labelled purchase block. */
  var toolbar = node('div', 'bx-toolbar');
  var editGroup = node('div', 'bx-toolbar__group bx-toolbar__edit'), viewGroup = node('div', 'bx-toolbar__group');
  var buyGroup = node('div', 'bx-toolbar__buy'); buyGroup.hidden = true;
  buyGroup.innerHTML = '<span class="bx-toolbar__buy-copy"><small></small><b></b></span>';
  toolbar.append(editGroup, viewGroup, buyGroup);
  if (head) head.after(toolbar);
  if (history) editGroup.append(history);
  if (canvasOptions) viewGroup.append(canvasOptions);
  var watchedBuy = null;
  function setText(el, value) { if (el.textContent !== value) el.textContent = value; }
  function adoptBuyButton() {
    var buy = $('builderBuyBackground');
    if (!buy) { buyGroup.hidden = true; return; }
    if (buy.parentNode !== buyGroup) buyGroup.append(buy);
    if (watchedBuy !== buy) {
      // Watch only the button itself; writing our own label must not re-trigger this.
      watchedBuy = buy;
      new MutationObserver(adoptBuyButton).observe(buy, { attributes: true, attributeFilter: ['hidden', 'title', 'href'] });
    }
    if (buyGroup.hidden !== buy.hidden) buyGroup.hidden = buy.hidden;
    setText(buyGroup.querySelector('small'), t('selected_bg'));
    setText(buyGroup.querySelector('b'), buy.title || '');
  }
  if (history) new MutationObserver(adoptBuyButton).observe(history, { childList: true });
  adoptBuyButton();
  var live = root.querySelector('.builder-live'); if (live) live.classList.add('bx-hidden');

  // Layers column: title, hint and an "add a layer" menu.
  var layers = root.querySelector('.builder-layers');
  var list = $('builderLayerList');
  var layerTitle = layers && layers.querySelector('.builder-panel-title');
  var layerHint = node('p', 'bx-layers__hint');
  if (list) list.before(layerHint);
  var addMenu = node('div', 'bx-addmenu');
  addMenu.innerHTML = '<button type="button" class="bx-addmenu__toggle" aria-expanded="false"><span>' + icon('plus') + '</span><b></b></button><div class="bx-addmenu__list" hidden></div>';
  var menuList = addMenu.querySelector('.bx-addmenu__list'), menuToggle = addMenu.querySelector('.bx-addmenu__toggle');
  LAYER_TOOLS.forEach(function (key) {
    var b = node('button', 'bx-addmenu__item'); b.type = 'button'; b.dataset.bxAdd = key;
    b.innerHTML = '<span>' + icon(key) + '</span><b></b>';
    b.addEventListener('click', function () { toggleMenu(false); setTool(key, false); if (addButtons[key]) addButtons[key].click(); });
    menuList.append(b);
  });
  function toggleMenu(open) { menuList.hidden = !open; menuToggle.setAttribute('aria-expanded', String(open)); }
  menuToggle.addEventListener('click', function () { toggleMenu(menuList.hidden); });
  document.addEventListener('click', function (event) { if (!addMenu.contains(event.target)) toggleMenu(false); });
  var retention = layers && layers.querySelector('.builder-retention');
  if (layers) { if (retention) retention.before(addMenu); else layers.append(addMenu); }

  // ------------------------------------------------------------ inline rename
  function startRename(row) {
    var id = row && row.dataset.layerId, label = row && row.querySelector('.builder-layer__copy b');
    if (!id || !label || row.querySelector('.bx-rename')) return;
    var input = node('input', 'bx-rename'); input.value = label.textContent; input.maxLength = 80;
    input.setAttribute('aria-label', t('rename'));
    label.hidden = true; label.after(input); input.focus(); input.select();
    var done = false;
    function finish(save) {
      if (done) return; done = true;
      if (save && input.value.trim() && input.value.trim() !== label.textContent) SMBuilder.rename(id, input.value);
      else { input.remove(); label.hidden = false; }
    }
    input.addEventListener('keydown', function (event) {
      event.stopPropagation();
      if (event.key === 'Enter') { event.preventDefault(); finish(true); }
      if (event.key === 'Escape') { event.preventDefault(); finish(false); row.focus(); }
    });
    input.addEventListener('blur', function () { finish(true); });
    input.addEventListener('click', function (event) { event.stopPropagation(); });
  }
  function decorateRows() {
    if (!list) return;
    list.querySelectorAll('.builder-layer').forEach(function (row) {
      if (row.querySelector('[data-action=rename]')) return;
      var actions = row.querySelector('.builder-layer__actions');
      var b = node('button', null, icon('rename')); b.type = 'button'; b.dataset.action = 'rename';
      b.title = t('rename'); b.setAttribute('aria-label', t('rename'));
      b.addEventListener('click', function (event) { event.stopPropagation(); startRename(row); });
      if (actions) actions.prepend(b);
      var grip = node('span', 'bx-grip', '<i></i><i></i><i></i>'); grip.title = t('drag'); grip.setAttribute('aria-hidden', 'true');
      row.prepend(grip);
      row.addEventListener('keydown', function (event) { if (event.key === 'F2' && event.target === row) { event.preventDefault(); startRename(row); } });
    });
  }
  if (list) {
    new MutationObserver(decorateRows).observe(list, { childList: true });
    // Delegated: the first click of a double click may re-render the rows.
    list.addEventListener('dblclick', function (event) {
      if (event.target.closest && event.target.closest('.builder-layer__actions')) return;
      var row = (event.target.isConnected && event.target.closest && event.target.closest('.builder-layer')) || list.querySelector('.builder-layer.is-selected');
      if (row) { event.preventDefault(); startRename(row); }
    });
  }


  // ---------------------------------------------------- collapsible groups
  /* Every optional block of the element settings is a group with a clear title that
     the user opens when needed; the choice is remembered per group in this browser. */
  var GROUPS = {
    removebg: ['Background removal', 'Удаление фона', 'Hintergrund entfernen', 'Arka plan kaldırma', 'Suppression du fond', 'Видалення фону', 'Quitar fondo', 'Remover fundo'],
    motion: ['Animation', 'Анимация', 'Animation', 'Animasyon', 'Animation', 'Анімація', 'Animación', 'Animação'],
    grade: ['Colour correction', 'Цветокоррекция', 'Farbkorrektur', 'Renk düzeltme', 'Correction des couleurs', 'Корекція кольору', 'Corrección de color', 'Correção de cor'],
    effectMore: ['Depth and light', 'Глубина и свет', 'Tiefe und Licht', 'Derinlik ve ışık', 'Profondeur et lumière', 'Глибина і світло', 'Profundidad y luz', 'Profundidade e luz'],
    transform: COPY.transform,
    textfx: ['Text animation', 'Анимация текста', 'Textanimation', 'Metin animasyonu', 'Animation du texte', 'Анімація тексту', 'Animación de texto', 'Animação de texto'],
    scene: ['Match the scene', 'Под сцену', 'An Szene anpassen', 'Sahneye uydur', 'Accorder à la scène', 'Під сцену', 'Ajustar a la escena', 'Ajustar à cena']
  };
  function remembered(name, fallback) { try { var v = localStorage.getItem('sm_bx_group_' + name); return v == null ? fallback : v === '1'; } catch (e) { return fallback; } }
  function makeGroup(name, nodes, host, before, openByDefault) {
    var g = node('details', 'bx-group'); g.dataset.bxGroup = name;
    g.innerHTML = '<summary><span class="bx-group__title"></span><i aria-hidden="true"></i></summary><div class="bx-group__body"></div>';
    var body = g.querySelector('.bx-group__body');
    nodes.forEach(function (n) { if (n) body.append(n); });
    if (before) host.insertBefore(g, before); else host.append(g);
    g.open = remembered(name, !!openByDefault);
    g.addEventListener('toggle', function () { try { localStorage.setItem('sm_bx_group_' + name, g.open ? '1' : '0'); } catch (e) {} });
    return g;
  }
  var mediaBox = $('builderMediaControls');
  if (mediaBox) {
    var chromaLabel = $('builderChroma') && $('builderChroma').closest('label');
    makeGroup('removebg', [chromaLabel, $('builderChromaSettings'), mediaBox.querySelector('.builder-ai-cut-row')], mediaBox);
    var animLabel = $('builderAnimation') && $('builderAnimation').closest('label');
    makeGroup('motion', [animLabel, $('bmLocalPanel')], mediaBox);
    var sceneBox = node('div', 'bx-scene');
    sceneBox.innerHTML = '<p class="bx-scene__hint"></p><div class="bx-scene__row"><button type="button" class="btn bx-scene__apply"></button><button type="button" class="btn ghost bx-scene__undo"></button></div>' +
      '<label class="bx-scene__strength"><span><b></b><output>60%</output></span><input type="range" min="20" max="100" step="5" value="60"/></label><p class="bx-scene__status" role="status" hidden></p>';
    var sceneGroup = makeGroup('scene', [sceneBox], mediaBox, null, true);
    var gradeBox = $('builderGrade');
    if (gradeBox) { makeGroup('grade', [gradeBox], mediaBox); var gradeHead = gradeBox.querySelector('.builder-grade__head strong'); if (gradeHead) gradeHead.classList.add('bx-hidden'); }
  }
  var effectMore = root.querySelector('.editor-effect-options');
  if (effectMore) { var moreBody = Array.prototype.slice.call(effectMore.children).filter(function (n) { return n.tagName !== 'SUMMARY'; }); makeGroup('effectMore', moreBody, effectMore.parentNode, effectMore); effectMore.classList.add('bx-hidden'); }
  var oldTransform = inspector && inspector.querySelector('.bx-transform');
  if (oldTransform) {
    var transformNodes = Array.prototype.slice.call(oldTransform.children).filter(function (n) { return n.tagName !== 'SUMMARY'; });
    makeGroup('transform', transformNodes, inspector, oldTransform); oldTransform.remove();
  }
  function paintGroups() {
    var i = Math.max(0, LANGS.indexOf(language()));
    root.querySelectorAll('.bx-group').forEach(function (g) { var row = GROUPS[g.dataset.bxGroup] || []; g.querySelector('.bx-group__title').textContent = row[i] || row[0] || ''; });
  }

  // ------------------------------------------------------- effect picker
  var EFFECT_NAMES = {
    aura: ['Aura', 'Аура', 'Aura', 'Aura', 'Aura', 'Аура', 'Aura', 'Aura'],
    fireflies: ['Fireflies', 'Светлячки', 'Glühwürmchen', 'Ateşböcekleri', 'Lucioles', 'Світлячки', 'Luciérnagas', 'Vaga-lumes'],
    bokeh: ['Bokeh', 'Боке', 'Bokeh', 'Bokeh', 'Bokeh', 'Боке', 'Bokeh', 'Bokeh'],
    hyperspace: ['Hyperspace', 'Гиперпрыжок', 'Hyperraum', 'Hiperuzay', 'Hyperespace', 'Гіперстрибок', 'Hiperespacio', 'Hiperespaço'],
    network: ['Network', 'Сеть', 'Netzwerk', 'Ağ', 'Réseau', 'Мережа', 'Red', 'Rede'],
    rings: ['Equalizer rings', 'Кольца-эквалайзер', 'Equalizer-Ringe', 'Ekolayzer halkaları', 'Anneaux égaliseur', 'Кільця-еквалайзер', 'Anillos ecualizador', 'Anéis equalizador'],
    scan: ['Scan pulse', 'Скан-импульс', 'Scan-Puls', 'Tarama darbesi', 'Impulsion scan', 'Скан-імпульс', 'Pulso de escaneo', 'Pulso de varredura'],
    arcane: ['Arcane circle', 'Магический круг', 'Arkaner Kreis', 'Gizemli çember', 'Cercle arcanique', 'Магічне коло', 'Círculo arcano', 'Círculo arcano'],
    hex: ['Hex pulse', 'Гекс-импульс', 'Hex-Puls', 'Altıgen darbe', 'Pulsation hex', 'Гекс-імпульс', 'Pulso hexagonal', 'Pulso hexagonal'],
    glitch: ['Glitch', 'Глитч', 'Glitch', 'Glitch', 'Glitch', 'Глітч', 'Glitch', 'Glitch'],
    dotwave: ['Dot wave', 'Волна точек', 'Punktwelle', 'Nokta dalgası', 'Vague de points', 'Хвиля точок', 'Onda de puntos', 'Onda de pontos'],
    smoke: ['Smoke', 'Дым', 'Rauch', 'Duman', 'Fumée', 'Дим', 'Humo', 'Fumaça'],
    embers: ['Embers', 'Угольки', 'Glut', 'Kor', 'Braises', 'Жаринки', 'Brasas', 'Brasas'],
    shards: ['Glass shards', 'Осколки', 'Glassscherben', 'Cam kırıkları', 'Éclats de verre', 'Уламки', 'Fragmentos', 'Estilhaços'],
    crosses: ['Pixel crosses', 'Пиксельные кресты', 'Pixelkreuze', 'Piksel artıları', 'Croix pixel', 'Піксельні хрести', 'Cruces de píxel', 'Cruzes de pixel']
  };
  var effectSelect = $('builderEffectType'), effectPicker = null, effectTiles = [];
  function effectLabel(name) {
    var i = Math.max(0, LANGS.indexOf(language()));
    if (EFFECT_NAMES[name]) return EFFECT_NAMES[name][i] || EFFECT_NAMES[name][0];
    var option = effectSelect && effectSelect.querySelector('option[value="' + name + '"]');
    return option ? option.textContent : name;
  }
  if (effectSelect) {
    var fxGroup = document.createElement('optgroup'); fxGroup.label = 'FX';
    Object.keys(EFFECT_NAMES).forEach(function (name) { var o = document.createElement('option'); o.value = name; o.dataset.bxEffect = '1'; fxGroup.append(o); });
    effectSelect.append(fxGroup);
    var effectLabelNode = effectSelect.closest('label'); if (effectLabelNode) effectLabelNode.classList.add('bx-hidden');
    var swatch = $('builderEffectSwatch'); if (swatch) swatch.classList.add('bx-hidden');
    effectPicker = node('div', 'bx-effects'); effectPicker.setAttribute('role', 'radiogroup');
    (effectLabelNode || effectSelect).before(effectPicker);
    var order = ['petals', 'snow', 'rain', 'lightning', 'particle', 'stars', 'sparks', 'matrix', 'streaks'].concat(Object.keys(EFFECT_NAMES));
    order.forEach(function (name) {
      var b = node('button', 'bx-effect'); b.type = 'button'; b.dataset.effect = name; b.setAttribute('role', 'radio');
      var c = document.createElement('canvas'); c.width = 168; c.height = 112; c.setAttribute('aria-hidden', 'true');
      b.append(c, node('span')); effectPicker.append(b);
      b.addEventListener('click', function () {
        effectSelect.value = name; effectSelect.dispatchEvent(new Event('change', { bubbles: true }));
        paintEffects();
      });
      effectTiles.push({ button: b, canvas: c, name: name });
    });
  }
  function paintEffects() {
    if (!effectPicker) return;
    var current = SMBuilder.current(), active = current && current.type === 'effect' ? current.effect : '';
    Array.prototype.forEach.call(effectSelect.querySelectorAll('option[data-bx-effect]'), function (o) { o.textContent = effectLabel(o.value); });
    effectTiles.forEach(function (tile) {
      tile.button.setAttribute('aria-checked', String(tile.name === active));
      tile.button.querySelector('span').textContent = effectLabel(tile.name);
    });
  }
  /* Live previews: ~12 fps, only tiles on screen, only while the Effects tool is open. */
  var lastPreview = 0;
  function previewLoop(now) {
    requestAnimationFrame(previewLoop);
    if (!effectPicker || tool !== 'effect' || inspectorSection.hidden || document.hidden || now - lastPreview < 80) return;
    lastPreview = now;
    var still = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
    var current = SMBuilder.current(), color = current && current.type === 'effect' ? current.color : '#52d5ff';
    var view = scroll.getBoundingClientRect();
    effectTiles.forEach(function (tile) {
      var r = tile.canvas.getBoundingClientRect();
      if (r.bottom < view.top || r.top > view.bottom || !r.width) return;
      if (still && tile.drawn) return;
      SMBuilder.previewEffect(tile.canvas, tile.name, color, still ? 1800 : now); tile.drawn = true;
    });
  }
  requestAnimationFrame(previewLoop);

  // ------------------------------------------------------ text animations
  /* Picture tiles with a live preview of each SMTextFx animation (builder-text-fx.js). */
  var TEXT_FX_NAMES = {
    typewriter: ['Typewriter', 'Печатная машинка', 'Schreib­maschine', 'Daktilo', 'Machine à écrire', 'Друкарська машинка', 'Máquina de escribir', 'Máquina de escrever'],
    fadeup: ['Letters rise', 'Появление по буквам', 'Buchstaben steigen', 'Harfler yükselir', 'Lettres montantes', 'Поява по літерах', 'Letras que suben', 'Letras surgindo'],
    decode: ['Decode', 'Рас­шифровка', 'Ent­schlüsseln', 'Şifre çözme', 'Décodage', 'Роз­шифрування', 'Descifrar', 'Decodificar'],
    wave: ['Wave', 'Волна', 'Welle', 'Dalga', 'Vague', 'Хвиля', 'Ola', 'Onda'],
    bounce: ['Pop-in', 'Выпры­гивание', 'Aufploppen', 'Zıplama', 'Apparition rebond', 'Вистри­бування', 'Aparición con rebote', 'Surgir com salto'],
    saber: ['Saber', 'Сабля (Saber)', 'Saber', 'Saber', 'Saber', 'Шабля (Saber)', 'Saber', 'Saber'],
    neon: ['Neon', 'Неон', 'Neon', 'Neon', 'Néon', 'Неон', 'Neón', 'Neon'],
    glitch: ['Glitch', 'Глитч', 'Glitch', 'Glitch', 'Glitch', 'Глітч', 'Glitch', 'Glitch'],
    rainbow: ['Rainbow', 'Радуга', 'Regen­bogen', 'Gökkuşağı', 'Arc-en-ciel', 'Веселка', 'Arcoíris', 'Arco-íris'],
    shine: ['Shine', 'Блик', 'Glanz', 'Parlama', 'Reflet', 'Відблиск', 'Destello', 'Brilho'],
    fire: ['Fire outline', 'Огненная обводка', 'Feuerkontur', 'Ateş çerçeve', 'Contour de feu', 'Вогняний контур', 'Contorno de fuego', 'Contorno de fogo'],
    electric: ['Electric outline', 'Электри­чество', 'Strom­kontur', 'Elektrik çerçeve', 'Contour électrique', 'Електрика', 'Contorno eléctrico', 'Contorno elétrico'],
    lightning: ['Lightning outline', 'Молнии', 'Blitzkontur', 'Şimşek çerçeve', 'Contour éclair', 'Блискавки', 'Contorno de rayos', 'Contorno de raios'],
    runner: ['Running outline', 'Бегущая обводка', 'Laufende Kontur', 'Akan çerçeve', 'Contour en course', 'Біжучий контур', 'Contorno en marcha', 'Contorno corrente'],
    plasma: ['Plasma outline', 'Переливы', 'Plasma­kontur', 'Plazma çerçeve', 'Contour plasma', 'Переливи', 'Contorno plasma', 'Contorno plasma'],
    sparkle: ['Sparkles', 'Блёстки', 'Funkeln', 'Işıltı', 'Paillettes', 'Блискітки', 'Destellos', 'Brilhos']
  };
  var TEXT_FX_COLOR = (window.SMTextFx && SMTextFx.colored) || ['saber', 'neon'];
  function tr(row) { var i = Math.max(0, LANGS.indexOf(language())); return row[i] || row[0]; }
  var textBox = $('builderTextControls'), textFxTiles = [], textFxBox = null;
  if (textBox && window.SMTextFx) {
    textFxBox = node('div', 'bx-textfx');
    var textFxGrid = node('div', 'bx-effects bx-textfx__grid'); textFxGrid.setAttribute('role', 'radiogroup');
    var fxColorLabel = node('label', 'bx-textfx__color', '<span></span><input type="color" id="builderTextFxColor" value="#52d5ff"/>');
    var textFxHint = node('p', 'bx-textfx__hint');
    var speedLabel = node('label', 'bx-textfx__speed', '<span><b></b><output>×1</output></span><input type="range" id="builderTextFxSpeed" min="1" max="4" step="1" value="1"/><small></small>');
    textFxBox.append(textFxGrid, fxColorLabel, speedLabel, textFxHint);
    speedLabel.querySelector('input').addEventListener('input', function (event) {
      var layer = SMBuilder.current(); if (!layer || layer.type !== 'text' || layer.locked) return;
      layer.textFxSpeed = Number(event.target.value) || 1; speedLabel.querySelector('output').textContent = '×' + layer.textFxSpeed; SMBuilder.redraw();
    });
    speedLabel.querySelector('input').addEventListener('change', function () { SMBuilder.commit(); });
    var dirRow = node('div', 'bx-textdir', '<span></span><div role="group"><button type="button" data-dir="horizontal"><b>A→</b><i></i></button><button type="button" data-dir="vertical"><b>A↓</b><i></i></button></div>');
    textBox.append(dirRow);
    dirRow.addEventListener('click', function (event) {
      var b = event.target.closest('[data-dir]'), layer = SMBuilder.current(); if (!b || !layer || layer.type !== 'text' || layer.locked) return;
      layer.textDir = b.dataset.dir; SMBuilder.redraw(); SMBuilder.commit(); paintTextFx();
    });
    ['none'].concat(SMTextFx.names).forEach(function (name) {
      var b = node('button', 'bx-effect bx-textfx__tile'); b.type = 'button'; b.dataset.textFx = name; b.setAttribute('role', 'radio');
      var c = document.createElement('canvas'); c.width = 168; c.height = 84; c.setAttribute('aria-hidden', 'true');
      b.append(c, node('span')); textFxGrid.append(b);
      b.addEventListener('click', function () {
        var layer = SMBuilder.current(); if (!layer || layer.type !== 'text' || layer.locked) return;
        layer.textFx = name === 'none' ? 'none' : name;
        if (TEXT_FX_COLOR.indexOf(name) >= 0 && !layer.fxColor) layer.fxColor = (layer.color && layer.color.toLowerCase() !== '#ffffff') ? layer.color : '#52d5ff';
        SMBuilder.redraw(); SMBuilder.commit(); paintTextFx();
      });
      textFxTiles.push({ button: b, canvas: c, name: name });
    });
    fxColorLabel.querySelector('input').addEventListener('input', function (event) {
      var layer = SMBuilder.current(); if (!layer || layer.type !== 'text' || layer.locked) return;
      layer.fxColor = event.target.value; SMBuilder.redraw();
    });
    fxColorLabel.querySelector('input').addEventListener('change', function () { SMBuilder.commit(); });
    makeGroup('textfx', [textFxBox], textBox, null, true);
  }
  function paintTextFx() {
    if (!textFxBox) return;
    var layer = SMBuilder.current(), active = layer && layer.type === 'text' ? (layer.textFx || 'none') : 'none';
    textFxTiles.forEach(function (tile) {
      tile.button.setAttribute('aria-checked', String(tile.name === active));
      tile.button.querySelector('span').textContent = tile.name === 'none' ? t('textfx_none') : tr(TEXT_FX_NAMES[tile.name] || [tile.name]);
    });
    var colorRow = textFxBox.querySelector('.bx-textfx__color');
    colorRow.hidden = TEXT_FX_COLOR.indexOf(active) < 0;
    colorRow.querySelector('span').textContent = t('textfx_color');
    if (layer && layer.type === 'text') colorRow.querySelector('input').value = layer.fxColor || '#52d5ff';
    textFxBox.querySelector('.bx-textfx__hint').textContent = t('textfx_hint');
    var speed = textFxBox.querySelector('.bx-textfx__speed'), speedValue = layer && layer.type === 'text' ? (layer.textFxSpeed || 1) : 1;
    speed.hidden = active === 'none';
    speed.querySelector('b').textContent = t('textfx_speed'); speed.querySelector('small').textContent = t('textfx_speed_hint');
    speed.querySelector('input').value = speedValue; speed.querySelector('output').textContent = '×' + speedValue;
    var dir = textBox.querySelector('.bx-textdir'), current = layer && layer.type === 'text' && layer.textDir === 'vertical' ? 'vertical' : 'horizontal';
    dir.querySelector('span').textContent = t('textdir');
    dir.querySelectorAll('[data-dir]').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.dataset.dir === current));
      b.querySelector('i').textContent = t(b.dataset.dir === 'vertical' ? 'textdir_v' : 'textdir_h');
    });
  }
  var lastTextPreview = 0;
  function textPreviewLoop(now) {
    requestAnimationFrame(textPreviewLoop);
    if (!textFxBox || tool !== 'text' || inspectorSection.hidden || document.hidden || now - lastTextPreview < 50) return;
    lastTextPreview = now;
    var still = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
    var layer = SMBuilder.current(), glow = layer && layer.type === 'text' && layer.fxColor || '#52d5ff';
    var view = scroll.getBoundingClientRect();
    textFxTiles.forEach(function (tile) {
      var r = tile.canvas.getBoundingClientRect();
      if (r.bottom < view.top || r.top > view.bottom || !r.width) return;
      if ((still || tile.name === 'none') && tile.drawn) return;
      var c = tile.canvas, g = c.getContext('2d');
      g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, c.width, c.height);
      g.fillStyle = '#0b1328'; g.fillRect(0, 0, c.width, c.height);
      g.save(); g.translate(c.width / 2, c.height / 2); g.fillStyle = '#ffffff'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.font = '800 30px Mulish,sans-serif';
      if (tile.name === 'none') g.fillText('Steam', 0, 0);
      else SMTextFx.draw(g, tile.name, ['Steam'], { u: still ? .5 : (now / 1000 % 3) / 3, period: 3, size: 30, color: glow });
      g.restore(); tile.drawn = true;
    });
  }
  requestAnimationFrame(textPreviewLoop);

  // --------------------------------------------------- match the scene
  /* Samples the background under the character (both small, 64 px) and moves the
     character's grade part of the way toward the scene: mean brightness, contrast
     (luminance spread), saturation and, for coloured scenes, a small hue shift. */
  var sceneState = null;
  function sampleStats(media, maskAlpha) {
    if (!media) return 'wait';
    var w = media.videoWidth || media.naturalWidth, h = media.videoHeight || media.naturalHeight;
    if (!w || !h || (media.readyState != null && media.tagName === 'VIDEO' && media.readyState < 2)) return 'wait';
    var size = 64, c = document.createElement('canvas'); c.width = size; c.height = Math.max(8, Math.round(size * h / w));
    var g = c.getContext('2d', { willReadFrequently: true }), data;
    g.drawImage(media, 0, 0, c.width, c.height);
    try { data = g.getImageData(0, 0, c.width, c.height).data; } catch (e) { return 'blocked'; }
    var n = 0, sumL = 0, sumL2 = 0, sumS = 0, hx = 0, hy = 0;
    for (var k = 0; k < data.length; k += 4) {
      if (maskAlpha && data[k + 3] < 140) continue;
      var r = data[k] / 255, gg = data[k + 1] / 255, b = data[k + 2] / 255;
      var max = Math.max(r, gg, b), min = Math.min(r, gg, b), l = .2126 * r + .7152 * gg + .0722 * b, s = max ? (max - min) / max : 0;
      n++; sumL += l; sumL2 += l * l; sumS += s;
      if (max - min > .04) {
        var hue = max === r ? ((gg - b) / (max - min)) % 6 : max === gg ? (b - r) / (max - min) + 2 : (r - gg) / (max - min) + 4;
        hue *= Math.PI / 3; hx += Math.cos(hue) * s; hy += Math.sin(hue) * s;
      }
    }
    if (n < 20) return 'wait';
    var mean = sumL / n;
    return { l: mean, sd: Math.sqrt(Math.max(0, sumL2 / n - mean * mean)), s: sumS / n, hue: Math.atan2(hy, hx), chroma: Math.hypot(hx, hy) / n };
  }
  function sceneStatus(text) { var st = sceneBox.querySelector('.bx-scene__status'); st.textContent = text || ''; st.hidden = !text; }
  function clampN(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function matchScene() {
    var layer = SMBuilder.current();
    if (!layer || layer.type !== 'character' || layer.locked) return;
    var all = SMBuilder.layers(), index = all.indexOf(layer);
    var bg = all.slice(0, index).reverse().find(function (l) { return l.type === 'background' && l.visible !== false && l.src; }) || all.find(function (l) { return l.type === 'background' && l.visible !== false && l.src; });
    if (!bg) { sceneStatus(t('scene_nobg')); return; }
    var a = sampleStats(SMBuilder.media(bg), false), c = sampleStats(SMBuilder.media(layer), true);
    if (a === 'blocked' || c === 'blocked') { sceneStatus(t('scene_blocked')); return; }
    if (a === 'wait' || c === 'wait') { sceneStatus(t('scene_wait')); return; }
    if (!sceneState || sceneState.id !== layer.id) sceneState = { id: layer.id, before: SMColorGrade.normalize(layer.grade) };
    sceneState.bg = a; sceneState.ch = c;
    applyScene();
  }
  function applyScene() {
    var layer = SMBuilder.current();
    if (!sceneState || !layer || layer.id !== sceneState.id) return;
    var k = Number(sceneBox.querySelector('.bx-scene__strength input').value) / 100, a = sceneState.bg, c = sceneState.ch;
    /* Ratios are taken in log space and damped: a character keeps its own look and only
       leans toward the scene (full strength = about half of the way). */
    function lean(ratio, damp) { return Math.exp(Math.log(clampN(ratio, .25, 4)) * k * damp); }
    var brightness = clampN(100 * lean(a.l / Math.max(.04, c.l), .5), 65, 135);
    var contrast = clampN(100 * lean(a.sd / Math.max(.02, c.sd), .4), 75, 125);
    var saturation = clampN(100 * lean(a.s / Math.max(.03, c.s), .55), 45, 150);
    var hue = 0;
    if (a.chroma > .06 && c.chroma > .02) {
      var d = Math.atan2(Math.sin(a.hue - c.hue), Math.cos(a.hue - c.hue)) * 180 / Math.PI;
      hue = clampN(d * .12 * k * Math.min(1, a.chroma * 5), -18, 18);
    }
    layer.grade = SMColorGrade.normalize({ brightness: brightness, contrast: contrast, saturation: saturation, hue: hue });
    SMBuilder.sync(); SMBuilder.redraw(); SMBuilder.commit();
    var what = [], gr = layer.grade;
    if (gr.brightness <= 95) what.push(t('scene_darker')); else if (gr.brightness >= 105) what.push(t('scene_lighter'));
    if (gr.contrast <= 95) what.push(t('scene_softer')); else if (gr.contrast >= 105) what.push(t('scene_harder'));
    if (gr.saturation <= 92) what.push(t('scene_muted')); else if (gr.saturation >= 108) what.push(t('scene_vivid'));
    if (Math.abs(gr.hue) >= 3) what.push(t('scene_tint'));
    sceneStatus(t('scene_done').replace('{what}', what.length ? what.join(', ') : t('scene_same')));
    paintScene();
  }
  function paintScene() {
    if (!sceneGroup) return;
    var layer = SMBuilder.current();
    sceneGroup.hidden = !layer || layer.type !== 'character';
    sceneBox.querySelector('.bx-scene__hint').textContent = t('scene_hint');
    sceneBox.querySelector('.bx-scene__apply').textContent = t('scene_apply');
    sceneBox.querySelector('.bx-scene__undo').textContent = t('scene_undo');
    sceneBox.querySelector('.bx-scene__strength b').textContent = t('scene_strength');
    var input = sceneBox.querySelector('.bx-scene__strength input');
    sceneBox.querySelector('.bx-scene__strength output').textContent = input.value + '%';
    var matched = !!sceneState && !!layer && sceneState.id === layer.id;
    sceneBox.querySelector('.bx-scene__undo').hidden = !matched;
    sceneBox.querySelector('.bx-scene__strength').hidden = !matched;
    if (!matched) sceneStatus('');
  }
  if (sceneGroup) {
    sceneBox.querySelector('.bx-scene__apply').addEventListener('click', matchScene);
    sceneBox.querySelector('.bx-scene__undo').addEventListener('click', function () {
      var layer = SMBuilder.current(); if (!sceneState || !layer || layer.id !== sceneState.id) return;
      layer.grade = sceneState.before; sceneState = null;
      SMBuilder.sync(); SMBuilder.redraw(); SMBuilder.commit(); paintScene();
    });
    var strength = sceneBox.querySelector('.bx-scene__strength input');
    strength.addEventListener('input', function () { sceneBox.querySelector('.bx-scene__strength output').textContent = strength.value + '%'; applyScene(); });
  }

  // ------------------------------------------------ media loading notice
  var mediaNote = node('div', 'bx-media-note'); mediaNote.hidden = true; mediaNote.setAttribute('role', 'status');
  mediaNote.innerHTML = '<i aria-hidden="true"></i><div><b></b><small></small></div>';
  var loadingMedia = {}, slowTimer = 0;
  function paintMediaNote() {
    var ids = Object.keys(loadingMedia), errors = ids.filter(function (id) { return loadingMedia[id].state === 'error'; });
    var busy = ids.filter(function (id) { return loadingMedia[id].state === 'loading'; });
    mediaNote.hidden = !ids.length;
    mediaNote.classList.toggle('is-error', !!errors.length && !busy.length);
    if (!ids.length) return;
    if (busy.length) {
      var pct = loadingMedia[busy[0]].pct;
      mediaNote.querySelector('b').textContent = t('media_loading').replace('{pct}', pct != null ? ' · ' + pct + '%' : '');
      mediaNote.querySelector('small').textContent = loadingMedia[busy[0]].slow ? t('media_slow') : '';
    } else {
      mediaNote.querySelector('b').textContent = t('media_error'); mediaNote.querySelector('small').textContent = '';
    }
  }
  root.addEventListener('sm:builder-media', function (event) {
    var d = event.detail || {}; if (!d.id) return;
    if (d.state === 'ready') delete loadingMedia[d.id];
    else if (d.state === 'error') { loadingMedia[d.id] = { state: 'error' }; setTimeout(function () { if (loadingMedia[d.id] && loadingMedia[d.id].state === 'error') { delete loadingMedia[d.id]; paintMediaNote(); } }, 8000); }
    else {
      var entry = loadingMedia[d.id] || (loadingMedia[d.id] = { state: 'loading', started: Date.now() });
      entry.state = 'loading'; if (d.pct != null) entry.pct = d.pct;
      clearTimeout(slowTimer);
      slowTimer = setTimeout(function () { Object.keys(loadingMedia).forEach(function (id) { if (loadingMedia[id].state === 'loading') loadingMedia[id].slow = true; }); paintMediaNote(); }, 3500);
    }
    // Only show the notice when the load is not instant (cached files finish at once).
    setTimeout(paintMediaNote, d.state === 'loading' && d.pct == null ? 400 : 0);
  });
  var stageWrap = root.querySelector('.builder-canvas-wrap'); if (stageWrap) stageWrap.append(mediaNote);
  window.addEventListener('sm:langchange', paintMediaNote);

  // ------------------------------------------------------ drag to reorder
  /* Rows can be dragged with the mouse anywhere on the row, and on touch screens by
     the grip (so the list still scrolls). The list shows the top layer first. */
  var drag = null, swallowClick = false;
  function rowsOf() { return Array.prototype.slice.call(list.querySelectorAll('.builder-layer')); }
  function dropIndex(y) {
    var rows = rowsOf().filter(function (r) { return r !== drag.row; }), k = rows.length;
    for (var i = 0; i < rows.length; i++) { var r = rows[i].getBoundingClientRect(); if (y < r.top + r.height / 2) { k = i; break; } }
    return { k: k, rows: rows };
  }
  function placeMarker(y) {
    var hit = dropIndex(y), box = list.getBoundingClientRect(), top;
    if (!hit.rows.length) top = 0;
    else if (hit.k < hit.rows.length) top = hit.rows[hit.k].getBoundingClientRect().top - box.top - 3;
    else top = hit.rows[hit.rows.length - 1].getBoundingClientRect().bottom - box.top + 1;
    drag.marker.style.transform = 'translateY(' + Math.round(top + list.scrollTop) + 'px)';
    drag.k = hit.k;
  }
  function endDrag(commit) {
    if (!drag) return;
    var d = drag; drag = null;
    list.classList.remove('is-dragging'); d.row.classList.remove('is-drag-source'); d.row.style.transform = ''; d.marker.remove();
    if (!d.started || !commit) return;
    swallowClick = true; setTimeout(function () { swallowClick = false; }, 0);
    var total = SMBuilder.layers().length, target = total - 1 - d.k;
    var from = SMBuilder.layers().findIndex(function (l) { return l.id === d.id; });
    if (from !== target) SMBuilder.move(d.id, target);
  }
  if (list) {
    list.addEventListener('pointerdown', function (event) {
      var row = event.target.closest && event.target.closest('.builder-layer');
      if (!row || event.button !== 0 || event.target.closest('button,input,textarea')) return;
      var grip = event.target.closest('.bx-grip');
      if (event.pointerType !== 'mouse' && !grip) return;
      var layer = SMBuilder.layers().find(function (l) { return l.id === row.dataset.layerId; });
      if (!layer || layer.locked || SMBuilder.layers().length < 2) return;
      drag = { row: row, id: row.dataset.layerId, y0: event.clientY, started: false, k: 0, pointer: event.pointerId, marker: node('div', 'bx-drop-marker') };
      if (grip) event.preventDefault();
    });
    window.addEventListener('pointermove', function (event) {
      if (!drag || event.pointerId !== drag.pointer) return;
      var dy = event.clientY - drag.y0;
      if (!drag.started) {
        if (Math.abs(dy) < 6) return;
        drag.started = true; list.classList.add('is-dragging'); drag.row.classList.add('is-drag-source'); list.append(drag.marker);
        try { drag.row.setPointerCapture(event.pointerId); } catch (e) {}
      }
      event.preventDefault();
      drag.row.style.transform = 'translateY(' + dy + 'px)';
      placeMarker(event.clientY);
      var box = list.getBoundingClientRect();
      if (event.clientY < box.top + 24) list.scrollTop -= 8; else if (event.clientY > box.bottom - 24) list.scrollTop += 8;
    }, { passive: false });
    window.addEventListener('pointerup', function (event) { if (drag && event.pointerId === drag.pointer) endDrag(true); });
    window.addEventListener('pointercancel', function () { endDrag(false); });
    window.addEventListener('keydown', function (event) { if (drag && event.key === 'Escape') endDrag(false); });
    list.addEventListener('click', function (event) { if (swallowClick) { event.stopPropagation(); event.preventDefault(); } }, true);
    list.addEventListener('keydown', function (event) {
      if (!event.altKey || (event.key !== 'ArrowUp' && event.key !== 'ArrowDown')) return;
      var row = event.target.closest && event.target.closest('.builder-layer'); if (!row) return;
      var b = row.querySelector('[data-action=' + (event.key === 'ArrowUp' ? 'up' : 'down') + ']'); if (!b) return;
      event.preventDefault(); var id = row.dataset.layerId; b.click();
      var again = list.querySelector('.builder-layer[data-layer-id="' + id + '"]'); if (again) again.focus();
    });
  }

  // ---------------------------------------------- Steam catalogue on stage
  var canvasWrap = root.querySelector('.builder-canvas-wrap');
  if (catalog && canvasWrap) { canvasWrap.append(catalog); catalog.classList.add('bx-catalog-stage'); }

  // ------------------------------------------------ on-canvas resize handles
  /* Corner handles scale the selected character / text / DNA layer, the top handle
     rotates it. The box follows the layer on every frame while the Builder is open. */
  var handles = node('div', 'bx-handles'); handles.hidden = true;
  handles.innerHTML = '<div class="bx-handles__box"><i data-h="nw"></i><i data-h="ne"></i><i data-h="sw"></i><i data-h="se"></i><b data-h="rot"></b></div>';
  var handleBox = handles.querySelector('.bx-handles__box'), gesture = null;
  if (canvasWrap) canvasWrap.append(handles);
  var stageCanvas = $('builderCanvas');
  function placeHandles() {
    var layer = SMBuilder.current(), box = layer && !layer.locked && layer.visible !== false && SMBuilder.box(layer);
    var catalogOpen = catalog && !catalog.hidden;
    if (!box || !stageCanvas || catalogOpen || !canvasWrap) { handles.hidden = true; return; }
    var rc = stageCanvas.getBoundingClientRect(), rw = canvasWrap.getBoundingClientRect(), k = rc.width / box.W;
    if (!rc.width) { handles.hidden = true; return; }
    handles.hidden = false;
    handleBox.style.width = Math.max(12, box.w * k) + 'px'; handleBox.style.height = Math.max(12, box.h * k) + 'px';
    handleBox.style.left = (rc.left - rw.left + box.cx * k) + 'px'; handleBox.style.top = (rc.top - rw.top + box.cy * k) + 'px';
    handleBox.style.transform = 'translate(-50%,-50%) rotate(' + box.rot + 'deg)';
  }
  function handleLoop() {
    requestAnimationFrame(handleLoop);
    if (!root.closest('.tab') || !root.closest('.tab').classList.contains('active')) { handles.hidden = true; return; }
    placeHandles();
  }
  requestAnimationFrame(handleLoop);
  handles.addEventListener('pointerdown', function (event) {
    var kind = event.target.dataset && event.target.dataset.h, layer = SMBuilder.current();
    if (!kind || !layer || layer.locked) return;
    event.preventDefault(); event.stopPropagation();
    var r = handleBox.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    gesture = { kind: kind, cx: cx, cy: cy, d0: Math.hypot(event.clientX - cx, event.clientY - cy) || 1, s0: layer.scale || 1,
      a0: Math.atan2(event.clientY - cy, event.clientX - cx), r0: layer.rotation || 0, id: layer.id };
    event.target.setPointerCapture(event.pointerId);
  });
  handles.addEventListener('pointermove', function (event) {
    if (!gesture) return;
    var layer = SMBuilder.current(); if (!layer || layer.id !== gesture.id) return;
    if (gesture.kind === 'rot') {
      var deg = gesture.r0 + (Math.atan2(event.clientY - gesture.cy, event.clientX - gesture.cx) - gesture.a0) * 180 / Math.PI;
      deg = ((deg + 540) % 360) - 180; if (event.shiftKey) deg = Math.round(deg / 15) * 15;
      layer.rotation = Math.round(deg);
    } else {
      layer.scale = Math.max(.1, Math.min(3, gesture.s0 * Math.hypot(event.clientX - gesture.cx, event.clientY - gesture.cy) / gesture.d0));
    }
    SMBuilder.redraw();
  });
  function endGesture() { if (!gesture) return; gesture = null; SMBuilder.sync(); SMBuilder.commit(); SMBuilder.redraw(); }
  handles.addEventListener('pointerup', endGesture);
  handles.addEventListener('pointercancel', endGesture);

  // ------------------------------------------------------------------ state
  function layersOf(type) { return SMBuilder.layers().filter(function (layer) { return layer.type === type; }); }
  function setTool(key, fromSelection) {
    tool = key;
    var current = SMBuilder.current();
    if (!fromSelection && LAYER_TOOLS.indexOf(key) >= 0 && (!current || current.type !== key)) {
      var same = layersOf(key);
      if (same.length) { SMBuilder.select(same[same.length - 1].id); return; }
    }
    paint();
    if (!fromSelection && matchMedia('(max-width:860px)').matches) panel.scrollIntoView({ block: 'start', behavior: 'smooth' });
  }
  function paint() {
    var current = SMBuilder.current(), editing = !!current && current.type === tool;
    root.dataset.bxActive = tool;
    rail.querySelectorAll('[data-bx-tool]').forEach(function (b) {
      var active = b.dataset.bxTool === tool;
      b.classList.toggle('is-active', active); b.setAttribute('aria-selected', String(active));
      b.querySelector('.bx-rail__label').textContent = t(b.dataset.bxTool);
      var count = LAYER_TOOLS.indexOf(b.dataset.bxTool) >= 0 ? layersOf(b.dataset.bxTool).length : 0, badge = b.querySelector('.bx-rail__count');
      badge.hidden = !count; badge.textContent = count;
    });
    panel.querySelector('.bx-panel__title').textContent = t(tool);
    panel.querySelector('.bx-panel__hint').textContent = t('hint_' + tool);
    var layerTool = LAYER_TOOLS.indexOf(tool) >= 0;
    addSection.hidden = !layerTool; bgSection.hidden = tool !== 'background';
    templatesSection.hidden = tool !== 'templates'; sceneSection.hidden = tool !== 'scene';
    inspectorSection.hidden = !editing;
    Object.keys(addButtons).forEach(function (key) {
      var b = addButtons[key]; b.hidden = key !== tool;
      var label = b.querySelector('[data-bx-label]');
      if (label) label.textContent = editing ? t('add_more') : t('add_' + key);
      b.classList.toggle('is-secondary', editing);
    });
    chips.replaceChildren();
    var same = layerTool ? layersOf(tool) : [];
    if (same.length > 1 || (same.length === 1 && !editing)) {
      chips.append(node('span', 'bx-chips__label', t('on_showcase')));
      same.slice().reverse().forEach(function (layer) {
        var c = node('button', 'bx-chip'); c.type = 'button'; c.textContent = layer.name || SMBuilder.typeName(layer.type);
        c.setAttribute('aria-pressed', String(!!current && current.id === layer.id));
        c.addEventListener('click', function () { SMBuilder.select(layer.id); });
        chips.append(c);
      });
    }
    chips.hidden = !chips.childElementCount;
    var group = inspector && inspector.querySelector('.bx-transform');
    if (group) {
      group.querySelector('summary').textContent = t('transform');
      if (!group.dataset.bxTouched) group.open = !!current && (current.type === 'text' || current.type === 'character');
    }
    if (layerTitle) { var strong = layerTitle.querySelector('strong'); if (strong) strong.textContent = t('layers'); }
    layerHint.textContent = SMBuilder.layers().length ? t('rename_hint') : t('empty_layers');
    menuToggle.querySelector('b').textContent = t('add_layer');
    menuList.querySelectorAll('[data-bx-add]').forEach(function (b) { b.querySelector('b').textContent = t(b.dataset.bxAdd); });
    decorateRows();
    adoptBuyButton();
    paintGroups();
    paintEffects();
    paintTextFx();
    paintScene();
  }
  var groupNode = inspector && inspector.querySelector('.bx-transform');
  if (groupNode) groupNode.querySelector('summary').addEventListener('click', function () { groupNode.dataset.bxTouched = '1'; });
  root.addEventListener('sm:builder-select', function (event) {
    var layer = event.detail && event.detail.layer;
    if (layer && LAYER_TOOLS.indexOf(layer.type) >= 0 && layer.type !== tool) { tool = layer.type; }
    paint();
  });
  window.addEventListener('sm:langchange', paint);
  // Opening the Steam catalogue always happens inside the Background tool.
  var steamButton = $('builderSteamBackgrounds');
  if (steamButton) steamButton.addEventListener('click', function () { if (tool !== 'background') { tool = 'background'; paint(); } }, true);
  document.querySelectorAll('[data-editor-start]').forEach(function (b) {
    b.addEventListener('click', function () { tool = b.dataset.editorStart === 'steam' ? 'background' : (b.dataset.editorStart || 'background'); if (LAYER_TOOLS.indexOf(tool) < 0) tool = 'background'; paint(); }, true);
  });
  // The Steam catalogue opens inside the panel: scroll the panel, not the page.
  if (window.WorkspaceEditor && WorkspaceEditor.catalogOpened) {
    WorkspaceEditor.catalogOpened = function (reset) {
      if (!reset || !catalog) return;
      // The catalogue covers the canvas; on phones bring the canvas into view.
      catalog.scrollTop = 0;
      if (matchMedia('(max-width:860px)').matches && canvasWrap) canvasWrap.scrollIntoView({ block: 'start', behavior: 'smooth' });
      var search = $('builderCatalogSearch'); if (search) search.focus({ preventScroll: true });
    };
    WorkspaceEditor.catalogClosed = function () { if (steamButton) steamButton.focus({ preventScroll: true }); };
  }
  var first = SMBuilder.current();
  if (first && LAYER_TOOLS.indexOf(first.type) >= 0) tool = first.type;
  paint();
  root.classList.add('bx-ready');
  window.SMBuilderLayout = { setTool: function (key) { setTool(key, false); }, tool: function () { return tool; } };
})();
