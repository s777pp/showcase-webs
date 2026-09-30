/* Process tab presentation: copy for the "Style it" / "Quality" cards, the
   summary above the main button and the phone dock. Presentation only: it
   reads existing controls and never changes processing options. */
(function () {
  'use strict';
  var root = document.getElementById('tab-process');
  if (!root) return;
  var LANGS = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'];
  var WORDS = {
    designTitle: ['Style it', 'Оформление', 'Gestaltung', 'Görünüm', 'Style', 'Оформлення', 'Estilo', 'Estilo'],
    designHint: ['Optional. Everything you change here appears on the preview right away.', 'Необязательно. Всё, что меняешь здесь, сразу видно на предпросмотре.', 'Optional. Jede Änderung siehst du sofort in der Vorschau.', 'İsteğe bağlı. Burada değiştirdiğin her şey önizlemede hemen görünür.', 'Facultatif. Chaque modification apparaît aussitôt dans l’aperçu.', 'Необов’язково. Усе, що змінюєш тут, одразу видно на попередньому перегляді.', 'Opcional. Todo lo que cambies aquí se ve al instante en la vista previa.', 'Opcional. Tudo o que você mudar aqui aparece na hora na prévia.'],
    frameTitle: ['Frame', 'Рамка', 'Rahmen', 'Çerçeve', 'Cadre', 'Рамка', 'Marco', 'Moldura'],
    frameHint: ['Drawn inside the final files, sizes stay the same.', 'Рисуется внутри итоговых файлов, размеры не меняются.', 'Wird in die fertigen Dateien gezeichnet, die Größe bleibt gleich.', 'Son dosyaların içine çizilir, boyutlar değişmez.', 'Dessiné à l’intérieur des fichiers finaux, sans changer leur taille.', 'Малюється всередині підсумкових файлів, розміри не змінюються.', 'Se dibuja dentro de los archivos finales; el tamaño no cambia.', 'Desenhada dentro dos arquivos finais; o tamanho não muda.'],
    wmTitle: ['Watermark', 'Водяной знак', 'Wasserzeichen', 'Filigran', 'Filigrane', 'Водяний знак', 'Marca de agua', 'Marca-d’água'],
    wmHint: ['Drag it on the preview to move it.', 'Перетащи его на предпросмотре, чтобы передвинуть.', 'Ziehe es in der Vorschau, um es zu verschieben.', 'Taşımak için önizlemede sürükle.', 'Faites-le glisser dans l’aperçu pour le déplacer.', 'Перетягни його на попередньому перегляді, щоб пересунути.', 'Arrástrala en la vista previa para moverla.', 'Arraste na prévia para movê-la.'],
    wmFree: ['Free plan: the ShowcaseMaker mark is added automatically. With Pro you can use your own text or turn it off.', 'Бесплатный тариф: знак ShowcaseMaker добавляется автоматически. С Pro можно поставить свой текст или отключить его.', 'Kostenloser Tarif: Das ShowcaseMaker-Zeichen wird automatisch hinzugefügt. Mit Pro nutzt du eigenen Text oder schaltest es aus.', 'Ücretsiz plan: ShowcaseMaker işareti otomatik eklenir. Pro ile kendi metnini kullanabilir veya kapatabilirsin.', 'Offre gratuite : la marque ShowcaseMaker est ajoutée automatiquement. Avec Pro, utilisez votre propre texte ou désactivez-la.', 'Безкоштовний тариф: знак ShowcaseMaker додається автоматично. З Pro можна поставити свій текст або вимкнути його.', 'Plan gratuito: la marca ShowcaseMaker se añade automáticamente. Con Pro puedes usar tu propio texto o quitarla.', 'Plano gratuito: a marca ShowcaseMaker é adicionada automaticamente. Com o Pro você usa seu próprio texto ou a desativa.'],
    wmText: ['Text', 'Текст', 'Text', 'Metin', 'Texte', 'Текст', 'Texto', 'Texto'],
    wmMore: ['Font, size and opacity', 'Шрифт, размер и прозрачность', 'Schrift, Größe und Deckkraft', 'Yazı tipi, boyut ve opaklık', 'Police, taille et opacité', 'Шрифт, розмір і прозорість', 'Fuente, tamaño y opacidad', 'Fonte, tamanho e opacidade'],
    wmReset: ['Reset watermark position', 'Вернуть знак на место', 'Wasserzeichen zurücksetzen', 'Filigran konumunu sıfırla', 'Replacer le filigrane', 'Повернути знак на місце', 'Restablecer posición de la marca', 'Redefinir posição da marca'],
    modeHelpTitle: ['Which one do I have?', 'Как понять, какая у меня?', 'Welche habe ich?', 'Bende hangisi var?', 'Laquelle ai-je ?', 'Як зрозуміти, яка в мене?', '¿Cuál tengo?', 'Qual eu tenho?'],
    modeHelpPath: ['In Steam open your profile → Edit Profile → Featured Showcase and look at the showcase name:', 'В Steam открой профиль → «Редактировать профиль» → «Витрина» и посмотри на название витрины:', 'Öffne in Steam dein Profil → Profil bearbeiten → Vitrine und sieh dir den Namen der Vitrine an:', 'Steam’de profilini aç → Profili düzenle → Vitrin bölümünde vitrinin adına bak:', 'Dans Steam, ouvrez votre profil → Modifier le profil → Vitrine et regardez le nom de la vitrine :', 'У Steam відкрий профіль → «Редагувати профіль» → «Вітрина» і подивися на назву вітрини:', 'En Steam abre tu perfil → Editar perfil → Escaparate y mira el nombre del escaparate:', 'Na Steam abra seu perfil → Editar perfil → Vitrine e veja o nome da vitrine:'],
    modeHelpNone: ['No showcase yet? Choose one there first; Steam gives the first showcase at profile level 10.', 'Витрины ещё нет? Сначала выбери её там; первую витрину Steam даёт на 10 уровне профиля.', 'Noch keine Vitrine? Wähle sie dort zuerst aus; Steam schaltet die erste Vitrine ab Profilstufe 10 frei.', 'Henüz vitrinin yok mu? Önce oradan birini seç; Steam ilk vitrini profil seviyesi 10’da verir.', 'Pas encore de vitrine ? Choisissez-la d’abord ; Steam débloque la première vitrine au niveau 10.', 'Вітрини ще немає? Спочатку вибери її там; першу вітрину Steam дає на 10 рівні профілю.', '¿Aún no tienes escaparate? Elígelo allí primero; Steam da el primero en el nivel 10 del perfil.', 'Ainda sem vitrine? Escolha uma lá primeiro; a Steam libera a primeira no nível 10 do perfil.'],
    studioLink: ['Need full-height rows or five 150×150 squares?', 'Нужны ряды на всю высоту или 5 квадратов 150×150?', 'Brauchst du Reihen in voller Höhe oder fünf Quadrate 150×150?', 'Tam yükseklikte satırlar ya da beş 150×150 kare mi lazım?', 'Besoin de rangées pleine hauteur ou de cinq carrés 150×150 ?', 'Потрібні ряди на всю висоту або 5 квадратів 150×150?', '¿Necesitas filas a altura completa o cinco cuadrados de 150×150?', 'Precisa de linhas em altura total ou cinco quadrados 150×150?'],
    sample: ['✦ Try it with a sample picture', '✦ Попробовать на примере', '✦ Mit einem Beispielbild testen', '✦ Örnek bir görselle dene', '✦ Essayer avec une image d’exemple', '✦ Спробувати на прикладі', '✦ Probar con una imagen de ejemplo', '✦ Testar com uma imagem de exemplo'],
    sampleFail: ['Could not load the sample. Check your connection.', 'Не удалось загрузить пример. Проверь соединение.', 'Beispiel konnte nicht geladen werden. Prüfe die Verbindung.', 'Örnek yüklenemedi. Bağlantını kontrol et.', 'Impossible de charger l’exemple. Vérifiez la connexion.', 'Не вдалося завантажити приклад. Перевір з’єднання.', 'No se pudo cargar el ejemplo. Revisa la conexión.', 'Não foi possível carregar o exemplo. Verifique a conexão.'],
    gradeTitle: ['Colour correction', 'Цветокоррекция', 'Farbkorrektur', 'Renk düzeltme', 'Correction des couleurs', 'Корекція кольору', 'Corrección de color', 'Correção de cor'],
    gradeHint: ['Brightness, contrast, saturation and hue of the source.', 'Яркость, контраст, насыщенность и оттенок исходника.', 'Helligkeit, Kontrast, Sättigung und Farbton der Quelle.', 'Kaynağın parlaklığı, kontrastı, doygunluğu ve tonu.', 'Luminosité, contraste, saturation et teinte de la source.', 'Яскравість, контраст, насиченість і відтінок джерела.', 'Brillo, contraste, saturación y tono del original.', 'Brilho, contraste, saturação e matiz da imagem.'],
    gradeBrightness: ['Brightness', 'Яркость', 'Helligkeit', 'Parlaklık', 'Luminosité', 'Яскравість', 'Brillo', 'Brilho'],
    gradeContrast: ['Contrast', 'Контраст', 'Kontrast', 'Kontrast', 'Contraste', 'Контраст', 'Contraste', 'Contraste'],
    gradeSaturation: ['Saturation', 'Насыщенность', 'Sättigung', 'Doygunluk', 'Saturation', 'Насиченість', 'Saturación', 'Saturação'],
    gradeHue: ['Hue', 'Оттенок', 'Farbton', 'Ton', 'Teinte', 'Відтінок', 'Tono', 'Matiz'],
    gradeReset: ['Reset', 'Сбросить', 'Zurücksetzen', 'Sıfırla', 'Réinitialiser', 'Скинути', 'Restablecer', 'Redefinir'],
    gradeChip: ['Colour adjusted', 'Цвет изменён', 'Farbe angepasst', 'Renk ayarlandı', 'Couleurs ajustées', 'Колір змінено', 'Color ajustado', 'Cor ajustada'],
    linkTitle: ['Add from a link', 'Добавить по ссылке', 'Per Link hinzufügen', 'Bağlantıdan ekle', 'Ajouter depuis un lien', 'Додати за посиланням', 'Añadir desde un enlace', 'Adicionar por link'],
    linkSources: ['YouTube · TikTok · Instagram · Pinterest · Giphy · 50+ sites · direct file', 'YouTube · TikTok · Instagram · Pinterest · Giphy · 50+ сайтов · прямая ссылка', 'YouTube · TikTok · Instagram · Pinterest · Giphy · 50+ Seiten · direkte Datei', 'YouTube · TikTok · Instagram · Pinterest · Giphy · 50+ site · doğrudan dosya', 'YouTube · TikTok · Instagram · Pinterest · Giphy · 50+ sites · fichier direct', 'YouTube · TikTok · Instagram · Pinterest · Giphy · 50+ сайтів · пряме посилання', 'YouTube · TikTok · Instagram · Pinterest · Giphy · 50+ sitios · archivo directo', 'YouTube · TikTok · Instagram · Pinterest · Giphy · 50+ sites · arquivo direto'],
    linkPlaceholder: ['Paste a link to a picture, GIF or video', 'Вставь ссылку на картинку, GIF или видео', 'Link zu Bild, GIF oder Video einfügen', 'Görsel, GIF veya video bağlantısı yapıştır', 'Collez le lien d’une image, d’un GIF ou d’une vidéo', 'Встав посилання на зображення, GIF або відео', 'Pega el enlace de una imagen, GIF o vídeo', 'Cole o link de uma imagem, GIF ou vídeo'],
    linkAdd: ['Add', 'Добавить', 'Hinzufügen', 'Ekle', 'Ajouter', 'Додати', 'Añadir', 'Adicionar'],
    linkLoading: ['Fetching the file…', 'Скачиваем файл…', 'Datei wird geladen…', 'Dosya alınıyor…', 'Récupération du fichier…', 'Завантажуємо файл…', 'Obteniendo el archivo…', 'Baixando o arquivo…'],
    linkFail: ['Could not fetch this link. Check that it is public or download the file yourself.', 'Не удалось скачать по ссылке. Проверь, что она публичная, или скачай файл сам.', 'Link konnte nicht geladen werden. Ist er öffentlich? Sonst lade die Datei selbst herunter.', 'Bağlantı alınamadı. Herkese açık olduğundan emin ol ya da dosyayı kendin indir.', 'Impossible de récupérer ce lien. Vérifiez qu’il est public ou téléchargez le fichier vous-même.', 'Не вдалося завантажити за посиланням. Перевір, що воно публічне, або завантаж файл сам.', 'No se pudo obtener el enlace. Comprueba que es público o descarga el archivo tú mismo.', 'Não foi possível baixar o link. Verifique se é público ou baixe o arquivo você mesmo.'],
    dropHere: ['Drop the file to add it', 'Отпусти файл, чтобы добавить', 'Datei loslassen, um sie hinzuzufügen', 'Eklemek için dosyayı bırak', 'Déposez le fichier pour l’ajouter', 'Відпусти файл, щоб додати', 'Suelta el archivo para añadirlo', 'Solte o arquivo para adicionar'],
    pasteHint: ['Tip: you can also paste a picture with Ctrl+V.', 'Совет: картинку можно вставить и через Ctrl+V.', 'Tipp: Du kannst ein Bild auch mit Strg+V einfügen.', 'İpucu: Görseli Ctrl+V ile de yapıştırabilirsin.', 'Astuce : vous pouvez aussi coller une image avec Ctrl+V.', 'Порада: зображення можна вставити й через Ctrl+V.', 'Consejo: también puedes pegar una imagen con Ctrl+V.', 'Dica: você também pode colar uma imagem com Ctrl+V.'],
    closeSignedIn: ['You can close this tab: the result will be saved in My results (Jobs).', 'Можно закрыть вкладку: результат сохранится в «Моих работах» (раздел «Задачи»).', 'Du kannst den Tab schließen: Das Ergebnis wird unter „Meine Ergebnisse“ (Aufgaben) gespeichert.', 'Sekmeyi kapatabilirsin: sonuç Sonuçlarım’a (Görevler) kaydedilir.', 'Vous pouvez fermer l’onglet : le résultat sera enregistré dans Mes résultats (Tâches).', 'Можна закрити вкладку: результат збережеться в «Моїх роботах» (розділ «Завдання»).', 'Puedes cerrar la pestaña: el resultado se guardará en Mis resultados (Tareas).', 'Você pode fechar a aba: o resultado ficará em Meus resultados (Tarefas).'],
    closeGuest: ['You can switch to another tab; the finished job will wait in Jobs for 24 hours.', 'Можно перейти на другую вкладку: готовое задание будет ждать в «Задачах» 24 часа.', 'Du kannst den Tab wechseln; der fertige Auftrag wartet 24 Stunden unter „Aufgaben“.', 'Başka sekmeye geçebilirsin; biten görev 24 saat Görevler’de bekler.', 'Vous pouvez changer d’onglet ; la tâche terminée attendra 24 heures dans Tâches.', 'Можна перейти на іншу вкладку: готове завдання чекатиме в «Завданнях» 24 години.', 'Puedes cambiar de pestaña; la tarea terminada esperará 24 horas en Tareas.', 'Você pode mudar de aba; a tarefa pronta fica em Tarefas por 24 horas.'],
    qualityTitle: ['Quality and format', 'Качество и формат', 'Qualität und Format', 'Kalite ve format', 'Qualité et format', 'Якість і формат', 'Calidad y formato', 'Qualidade e formato'],
    qualityHint: ['For experienced users. The defaults already fit Steam.', 'Для опытных. Настройки по умолчанию уже подходят для Steam.', 'Für Fortgeschrittene. Die Standardwerte passen bereits zu Steam.', 'Deneyimli kullanıcılar için. Varsayılanlar Steam’e zaten uygun.', 'Pour les utilisateurs avancés. Les réglages par défaut conviennent déjà à Steam.', 'Для досвідчених. Типові налаштування вже підходять для Steam.', 'Para usuarios avanzados. Los valores predeterminados ya sirven para Steam.', 'Para usuários avançados. O padrão já serve para a Steam.'],
    workshop: ['Workshop · 5 parts', 'Workshop · 5 частей', 'Workshop · 5 Teile', 'Workshop · 5 parça', 'Workshop · 5 parties', 'Workshop · 5 частин', 'Workshop · 5 partes', 'Workshop · 5 partes'],
    featured: ['Featured · 1 file', 'Featured · 1 файл', 'Featured · 1 Datei', 'Featured · 1 dosya', 'Featured · 1 fichier', 'Featured · 1 файл', 'Featured · 1 archivo', 'Featured · 1 arquivo'],
    split: ['Artwork Split · 2 parts', 'Artwork Split · 2 части', 'Artwork Split · 2 Teile', 'Artwork Split · 2 parça', 'Artwork Split · 2 parties', 'Artwork Split · 2 частини', 'Artwork Split · 2 partes', 'Artwork Split · 2 partes'],
    allModes: ['All three types', 'Все три типа', 'Alle drei Typen', 'Üç türün hepsi', 'Les trois types', 'Усі три типи', 'Los tres tipos', 'Os três tipos'],
    files: ['Files: {n}', 'Файлов: {n}', 'Dateien: {n}', 'Dosya: {n}', 'Fichiers : {n}', 'Файлів: {n}', 'Archivos: {n}', 'Arquivos: {n}'],
    noFiles: ['No file yet', 'Файл ещё не выбран', 'Noch keine Datei', 'Henüz dosya yok', 'Aucun fichier', 'Файл ще не вибрано', 'Aún no hay archivo', 'Nenhum arquivo ainda'],
    frame: ['Frame: {name}', 'Рамка: {name}', 'Rahmen: {name}', 'Çerçeve: {name}', 'Cadre : {name}', 'Рамка: {name}', 'Marco: {name}', 'Moldura: {name}'],
    noFrame: ['No frame', 'Без рамки', 'Kein Rahmen', 'Çerçeve yok', 'Sans cadre', 'Без рамки', 'Sin marco', 'Sem moldura'],
    wmOn: ['Watermark on', 'Водяной знак включён', 'Wasserzeichen an', 'Filigran açık', 'Filigrane activé', 'Водяний знак увімкнено', 'Marca de agua activada', 'Marca-d’água ativada'],
    wmOff: ['No watermark', 'Без водяного знака', 'Ohne Wasserzeichen', 'Filigran yok', 'Sans filigrane', 'Без водяного знака', 'Sin marca de agua', 'Sem marca-d’água']
  };
  function language() { return (window.SMLang && SMLang.get && SMLang.get()) || document.documentElement.lang || 'en'; }
  function word(key, vars) {
    var list = WORDS[key] || [], text = list[Math.max(0, LANGS.indexOf(language()))] || list[0] || key;
    return vars ? text.replace(/\{(\w+)\}/g, function (all, name) { return name in vars ? String(vars[name]) : all; }) : text;
  }
  // Colour correction: same ranges and preview filter as Workshop Studio / Builder (color-grade.js).
  var gradeInputs = Array.prototype.slice.call(root.querySelectorAll('[data-grade]'));
  function gradeValue() {
    var value = {};
    gradeInputs.forEach(function (input) { value[input.dataset.grade] = Number(input.value); });
    return window.SMColorGrade ? SMColorGrade.normalize(value) : value;
  }
  function gradeChanged() {
    var value = gradeValue(), ranges = (window.SMColorGrade && SMColorGrade.ranges) || {};
    return Object.keys(value).some(function (key) { return ranges[key] && value[key] !== ranges[key][2]; });
  }
  function paintGrade() {
    var value = gradeValue();
    gradeInputs.forEach(function (input) {
      var out = root.querySelector('[data-grade-out="' + input.dataset.grade + '"]');
      if (out) out.textContent = value[input.dataset.grade] + (input.dataset.grade === 'hue' ? '°' : '%');
    });
    var reset = document.getElementById('processGradeReset');
    if (reset) reset.disabled = !gradeChanged();
  }
  window.SMProcessGrade = {
    get: function () { return gradeChanged() ? gradeValue() : null; },
    filter: function () { return gradeChanged() && window.SMColorGrade ? SMColorGrade.filter(gradeValue()) : 'none'; },
    set: function (value) {
      var grade = window.SMColorGrade ? SMColorGrade.normalize(value) : (value || {});
      gradeInputs.forEach(function (input) { if (grade[input.dataset.grade] != null) input.value = grade[input.dataset.grade]; });
      paintGrade();
      if (typeof window.__wmRedraw === 'function') window.__wmRedraw();
    }
  };
  gradeInputs.forEach(function (input) {
    input.addEventListener('input', function () { paintGrade(); if (typeof window.__wmRedraw === 'function') window.__wmRedraw(); });
  });
  var gradeReset = document.getElementById('processGradeReset');
  if (gradeReset) gradeReset.addEventListener('click', function () {
    window.SMProcessGrade.set(window.SMColorGrade ? SMColorGrade.normalize({}) : {});
    root.dispatchEvent(new Event('change', { bubbles: true }));
  });
  paintGrade();

  var summary = document.getElementById('processSummary');
  var dock = document.getElementById('processDock');
  var dockSummary = document.getElementById('processDockSummary');
  var dockRun = document.getElementById('processDockRun');
  var run = document.getElementById('btnRun');
  var submit = document.getElementById('processSubmit');

  function items() {
    var state = window.state || {}, list = [];
    var all = document.getElementById('allModes');
    list.push(all && all.checked ? word('allModes') : word(state.mode || 'workshop'));
    var count = (state.files || []).length;
    list.push(count ? word('files', { n: count }) : word('noFiles'));
    var frameName = window.SMProcessFrame && SMProcessFrame.styleName();
    list.push(frameName ? word('frame', { name: frameName }) : word('noFrame'));
    var wm = document.getElementById('wmEnable');
    list.push(wm && wm.checked ? word('wmOn') : word('wmOff'));
    if (gradeChanged()) list.push(word('gradeChip'));
    return list;
  }
  function paint() {
    var list = items();
    if (summary) {
      summary.replaceChildren.apply(summary, list.map(function (text) {
        var li = document.createElement('li'); li.textContent = text; return li;
      }));
    }
    if (dockSummary) dockSummary.textContent = list[0] + ' · ' + list[1];
    if (dockRun && run) dockRun.disabled = run.disabled;
  }
  // One-click sample so a first-time visitor sees a result without their own art.
  var library = document.querySelector('#processFilesCard .asset-library-open');
  if (library) {
    var sample = document.createElement('button');
    sample.type = 'button';
    sample.className = 'process-sample';
    sample.dataset.pl = 'sample';
    library.after(sample);
    sample.addEventListener('click', async function () {
      sample.disabled = true;
      try {
        var response = await fetch('/static/img/samples/sample-art.webp?v=1', { cache: 'force-cache' });
        if (!response.ok) throw new Error('sample');
        var file = new File([await response.blob()], 'showcase-sample.webp', { type: 'image/webp' });
        document.dispatchEvent(new CustomEvent('sm:assets-selected', { detail: { target: 'process', files: [file] } }));
      } catch (_) {
        var status = document.getElementById('status');
        if (status) { status.className = 'status err'; status.textContent = word('sampleFail'); }
      } finally { sample.disabled = false; }
    });
  }

  function addFiles(files) {
    files = Array.prototype.filter.call(files || [], function (file) { return /^(image|video)\//.test(file.type) || /\.(gif|mp4|webm|mov|avi|mkv|png|jpe?g|webp|ico|cur|bmp|tiff?|avif|tga|psd|qoi|jp2|j2k|jfif|dds|icns|pcx|apng|heic|heif)$/i.test(file.name || ''); });
    if (!files.length) return false;
    document.dispatchEvent(new CustomEvent('sm:assets-selected', { detail: { target: 'process', files: files } }));
    return true;
  }
  function processActive() { return root.classList.contains('active'); }

  // Paste a picture from the clipboard (not while typing in a field).
  document.addEventListener('paste', function (event) {
    if (!processActive() || (event.target.closest && event.target.closest('input,textarea,[contenteditable="true"]'))) return;
    var files = event.clipboardData && event.clipboardData.files;
    if (files && files.length && addFiles(files)) event.preventDefault();
  });

  // Drop a file anywhere on the Process tab, not only on the upload box.
  var dropLayer = document.createElement('div');
  dropLayer.className = 'process-droplayer';
  dropLayer.hidden = true;
  dropLayer.innerHTML = '<span data-pl="dropHere"></span>';
  root.append(dropLayer);
  var dragDepth = 0;
  function hasFiles(event) { return !!(event.dataTransfer && Array.prototype.indexOf.call(event.dataTransfer.types || [], 'Files') >= 0); }
  root.addEventListener('dragenter', function (event) { if (!hasFiles(event)) return; dragDepth += 1; dropLayer.hidden = false; });
  root.addEventListener('dragleave', function () { dragDepth = Math.max(0, dragDepth - 1); if (!dragDepth) dropLayer.hidden = true; });
  root.addEventListener('dragover', function (event) { if (hasFiles(event)) event.preventDefault(); });
  root.addEventListener('drop', function (event) {
    dragDepth = 0; dropLayer.hidden = true;
    if (!hasFiles(event) || event.target.closest('#drop')) return; // the upload box handles its own drop
    event.preventDefault();
    addFiles(event.dataTransfer.files);
  });

  // A link instead of a file (same downloader as the Download tab; charged once, by processing).
  var dropBox = document.getElementById('drop');
  if (dropBox) {
    var linkRow = document.createElement('form');
    linkRow.className = 'process-link';
    linkRow.innerHTML = '<p class="process-link__title"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 14a4 4 0 0 0 5.66 0l3.54-3.54a4 4 0 0 0-5.66-5.66L12 6.34M14 10a4 4 0 0 0-5.66 0l-3.54 3.54a4 4 0 0 0 5.66 5.66L12 17.66" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg><b data-pl="linkTitle"></b><small data-pl="linkSources"></small></p>' +
      '<input type="url" inputmode="url" autocomplete="off" required><button type="submit" class="btn" data-pl="linkAdd"></button><p class="process-link__status" role="status"></p>';
    var linkInput = linkRow.querySelector('input'), linkButton = linkRow.querySelector('button'), linkStatus = linkRow.querySelector('.process-link__status');
    dropBox.after(linkRow);
    var pasteHint = document.createElement('p');
    pasteHint.className = 'process-paste-hint';
    pasteHint.dataset.pl = 'pasteHint';
    linkRow.after(pasteHint);
    linkRow.addEventListener('submit', async function (event) {
      event.preventDefault();
      var url = linkInput.value.trim();
      if (!/^https?:\/\//i.test(url)) return;
      linkButton.disabled = true; linkStatus.className = 'process-link__status'; linkStatus.textContent = word('linkLoading');
      try {
        var headers = Object.assign({ 'Content-Type': 'application/json' }, window.__smHeaders ? window.__smHeaders() : {});
        var response = await fetch('/api/download-url', { method: 'POST', credentials: 'include', headers: headers, body: JSON.stringify({ url: url, quality: 'best', purpose: 'process' }) });
        var data = await response.json();
        if (!response.ok || !data.ok || !data.download) throw new Error(data.msg || 'link');
        var blob = await (await fetch(data.download, { credentials: 'include' })).blob();
        var name = String(data.name || 'linked-media').replace(/[\\/:*?"<>|]+/g, '_');
        if (!addFiles([new File([blob], name, { type: blob.type || '' })])) throw new Error('type');
        linkInput.value = ''; linkStatus.textContent = '';
      } catch (error) {
        linkStatus.className = 'process-link__status is-error';
        linkStatus.textContent = word('linkFail');
      } finally { linkButton.disabled = false; }
    });
  }

  // While processing: say that waiting on the page is not required.
  var submitCard = document.getElementById('processSubmit');
  var closeNote = document.createElement('p');
  closeNote.className = 'process-close-note';
  closeNote.hidden = true;
  if (submitCard) (document.getElementById('procProgress') || submitCard.lastElementChild).after(closeNote);
  function syncCloseNote() {
    var busy = root.classList.contains('is-processing');
    closeNote.hidden = !busy;
    if (!busy) return;
    Promise.resolve(window.SSShell && SSShell.me ? SSShell.me() : null).then(function (user) {
      closeNote.textContent = word(user && user.logged_in ? 'closeSignedIn' : 'closeGuest');
    }).catch(function () { closeNote.textContent = word('closeGuest'); });
  }

  // Workshop has two more layouts in the Workshop Studio tab; point there from the Workshop card.
  var modeCard = document.getElementById('processModeCard');
  var studioTab = document.querySelector('#nav [data-tab="workshop"]');
  var studioLink = null;
  if (modeCard && studioTab) {
    studioLink = document.createElement('p');
    studioLink.className = 'process-studio-link';
    studioLink.innerHTML = '<span data-pl="studioLink"></span><button type="button"></button>';
    studioLink.querySelector('button').addEventListener('click', function () { studioTab.click(); window.scrollTo({ top: 0 }); });
    var modes = modeCard.querySelector('.modes');
    if (modes) modes.after(studioLink);
  }
  function syncStudioLink() {
    if (!studioLink) return;
    studioLink.hidden = ((window.state || {}).mode || 'workshop') !== 'workshop';
    studioLink.querySelector('button').textContent = studioTab.textContent.trim() + ' →';
  }
  function localize() {
    root.querySelectorAll('[data-pl]').forEach(function (node) { node.textContent = word(node.dataset.pl); });
    var link = root.querySelector('.process-link input');
    if (link) { link.placeholder = word('linkPlaceholder'); link.setAttribute('aria-label', word('linkPlaceholder')); }
    if (!closeNote.hidden) syncCloseNote();
    setTimeout(syncStudioLink, 0);
    paint();
  }

  // Phone dock: visible while the real button is off screen and there is something to process.
  var submitVisible = true;
  function syncDock() {
    if (!dock) return;
    var phone = matchMedia('(max-width: 760px)').matches;
    var hasFiles = !!((window.state || {}).files || []).length;
    dock.hidden = !(phone && hasFiles && !submitVisible && root.classList.contains('active') && !root.classList.contains('is-processing'));
    document.body.classList.toggle('has-process-dock', !dock.hidden);
  }
  if (submit && 'IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) {
      submitVisible = entries.some(function (entry) { return entry.isIntersecting; });
      syncDock();
    }, { threshold: 0.35 }).observe(submit);
  }
  if (dockRun && run) dockRun.addEventListener('click', function () {
    if (run.disabled) return;
    submit.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'center' });
    run.click();
  });

  // Remember the last Process settings in this browser (a per-viewer convenience only).
  var STORE = 'sm_process_settings_v1';
  var restoring = false, saveTimer = 0;
  function byId(id) { return document.getElementById(id); }
  function snapshot() {
    var state = window.state || {}, wm = byId('wmEnable');
    var data = {
      mode: state.mode || 'workshop',
      allModes: !!(byId('allModes') || {}).checked,
      frame: window.SMProcessFrame && SMProcessFrame.state ? SMProcessFrame.state() : null,
      fps: (byId('fps') || {}).value, size: (byId('size') || {}).value, encoder: (byId('gifEncoder') || {}).value,
      autoContrast: !!(byId('autoContrast') || {}).checked,
      grade: window.SMProcessGrade ? SMProcessGrade.get() : null
    };
    // Free accounts have a fixed watermark; never store (or later push) those locked values.
    if (wm && !wm.disabled) {
      data.wm = { enabled: wm.checked };
      ['wmText', 'wmColor', 'wmCorner', 'wmFont', 'wmScale', 'wmOpacity'].forEach(function (id) { if (byId(id)) data.wm[id] = byId(id).value; });
    }
    return data;
  }
  function save() {
    if (restoring) return;
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () { try { localStorage.setItem(STORE, JSON.stringify(snapshot())); } catch (_) {} }, 300);
  }
  function setValue(id, value, event) {
    var node = byId(id);
    if (!node || value == null || node.disabled) return;
    if (node.tagName === 'SELECT' && !Array.prototype.some.call(node.options, function (o) { return o.value === String(value); })) return;
    node.value = String(value);
    node.dispatchEvent(new Event(event || 'change', { bubbles: true }));
  }
  function setChecked(id, value) {
    var node = byId(id);
    if (!node || node.disabled || node.checked === !!value) return;
    node.checked = !!value;
    node.dispatchEvent(new Event('change', { bubbles: true }));
  }
  function restore() {
    var data = null;
    try { data = JSON.parse(localStorage.getItem(STORE) || 'null'); } catch (_) { data = null; }
    if (!data || typeof data !== 'object') return;
    restoring = true;
    try {
      var mode = root.querySelector('.mode[data-mode="' + String(data.mode).replace(/[^a-z]/g, '') + '"]');
      if (mode && !mode.classList.contains('active')) mode.click();
      setChecked('allModes', data.allModes);
      setChecked('autoContrast', data.autoContrast);
      setValue('fps', data.fps); setValue('size', data.size); setValue('gifEncoder', data.encoder);
      if (data.frame && window.SMProcessFrame && SMProcessFrame.set) SMProcessFrame.set(data.frame);
      if (data.grade && window.SMProcessGrade) SMProcessGrade.set(data.grade);
      if (data.wm && byId('wmEnable') && !byId('wmEnable').disabled) {
        setChecked('wmEnable', data.wm.enabled);
        ['wmText', 'wmColor', 'wmScale', 'wmOpacity'].forEach(function (id) { setValue(id, data.wm[id], 'input'); });
        ['wmCorner', 'wmFont'].forEach(function (id) { setValue(id, data.wm[id]); });
      }
    } finally { restoring = false; }
  }
  root.addEventListener('change', save);
  root.addEventListener('input', save);
  document.addEventListener('sm:process-frame-change', save);

  var refresh = function () { paint(); syncDock(); };
  var list = document.getElementById('fileList');
  if (list) new MutationObserver(refresh).observe(list, { childList: true });
  if (run) new MutationObserver(refresh).observe(run, { attributes: true, attributeFilter: ['disabled'] });
  new MutationObserver(function () { syncDock(); syncCloseNote(); }).observe(root, { attributes: true, attributeFilter: ['class'] });
  root.addEventListener('click', function (event) { if (event.target.closest('.mode')) setTimeout(function () { refresh(); syncStudioLink(); save(); }, 0); });
  ['wmEnable', 'allModes'].forEach(function (id) { var node = document.getElementById(id); if (node) node.addEventListener('change', refresh); });
  document.addEventListener('sm:process-frame-change', refresh);
  window.addEventListener('resize', syncDock);
  window.addEventListener('sm:langchange', localize);
  localize();
  restore();
  refresh();
  syncDock();
})();
