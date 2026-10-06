/* GIF Optimizer tab (#tab-gifopt): palette colours + lossy with gifsicle, or "Auto up to 5 MB" with the
   same gifski fit as Process. Runs as a job (/api/gif-optimizer/*); before/after comparison with a divider
   dragged right across the GIF. Copy: keyed var COPY= in 8 languages (checked by scripts/check_i18n.js). */
(function () {
  'use strict';
  var COPY = {
    en: {
      title: 'GIF Optimizer', lead: 'Shrink a GIF to Steam limits and check the result before downloading.',
      settings: 'Compression settings', drop: 'Upload a GIF to compress', dropHint: 'Drop the file here or click to choose.',
      change: 'Choose another GIF', colors: 'Palette colour limit', custom: 'Other', customHint: 'From 2 to 256 colours',
      lossy: 'Compression level (Lossy)', lossyHint: 'Higher means a smaller file and more visible noise.',
      optimize: 'Optimize file', download: 'Download result', auto: 'Auto up to 5 MB',
      autoHint: 'Best quality that fits Steam\'s 5 MB', quotaNote: 'Each run counts as one file of the daily Free limit. Pro has no limit.',
      check: 'Check the result', checkLead: 'After optimizing, drag the divider right across the GIF to compare the original and the compressed version.',
      before: 'Before', after: 'After', empty: 'The GIF appears after upload', uploading: 'Uploading…', queued: 'Waiting in the queue…',
      working: 'Optimizing…', done: 'Done', saved: 'smaller by', bigger: 'The result is bigger than the original: try fewer colours or a higher Lossy.',
      fits: 'Fits Steam (up to 5 MB)', tooBig: 'Over 5 MB: Steam will not accept it', alreadyFits: 'The GIF is already under 5 MB, there is nothing to compress.',
      frames: 'frames', errNotGif: 'GIF files only. Convert other formats in the Converter tab first.',
      errQuota: 'The free files for today are used up. Pro has no limit.', errBeta: 'GIF Optimizer is in beta and available with Pro only for now.', errFail: 'Could not optimize the GIF. Try again or pick other settings.',
      errBig: 'The file is too large.', pickFirst: 'Choose a GIF first.', compareLabel: 'Divider between the original and the result'
    },
    ru: {
      title: 'GIF оптимизатор', lead: 'Сожмите GIF под лимиты Steam и проверьте результат перед скачиванием.',
      settings: 'Настройки сжатия', drop: 'Загрузите GIF для сжатия', dropHint: 'Перетащите файл сюда или нажмите, чтобы выбрать.',
      change: 'Выбрать другой GIF', colors: 'Ограничение цветов палитры', custom: 'Другое', customHint: 'От 2 до 256 цветов',
      lossy: 'Уровень компрессии (Lossy)', lossyHint: 'Больше — меньше файл, но заметнее шум.',
      optimize: 'Оптимизировать файл', download: 'Скачать результат', auto: 'Авто до 5 MB',
      autoHint: 'Лучшее качество, которое влезает в 5 МБ Steam', quotaNote: 'Каждый запуск — один файл из дневного лимита Free. У Pro без ограничений.',
      check: 'Проверка результата', checkLead: 'После оптимизации появится сравнение: перетаскивайте разделитель прямо по GIF, чтобы увидеть исходник и сжатую версию.',
      before: 'До', after: 'После', empty: 'GIF появится после загрузки', uploading: 'Загружаем…', queued: 'В очереди…',
      working: 'Оптимизируем…', done: 'Готово', saved: 'меньше на', bigger: 'Результат получился больше исходника: уменьшите число цветов или увеличьте Lossy.',
      fits: 'Подходит для Steam (до 5 МБ)', tooBig: 'Больше 5 МБ: Steam не примет', alreadyFits: 'GIF уже меньше 5 МБ, сжимать нечего.',
      frames: 'кадров', errNotGif: 'Только GIF. Другие форматы сначала переведите во вкладке «Конвертер».',
      errQuota: 'Бесплатные файлы на сегодня закончились. У Pro лимита нет.', errBeta: 'GIF оптимизатор в бета-тесте и пока доступен только с Pro.', errFail: 'Не удалось оптимизировать GIF. Попробуйте ещё раз или другие настройки.',
      errBig: 'Файл слишком большой.', pickFirst: 'Сначала выберите GIF.', compareLabel: 'Разделитель между исходником и результатом'
    },
    de: {
      title: 'GIF-Optimierer', lead: 'Verkleinere ein GIF auf die Steam-Limits und prüfe das Ergebnis vor dem Download.',
      settings: 'Komprimierung', drop: 'GIF zum Komprimieren hochladen', dropHint: 'Datei hierher ziehen oder klicken, um sie auszuwählen.',
      change: 'Anderes GIF wählen', colors: 'Farben der Palette begrenzen', custom: 'Andere', customHint: 'Von 2 bis 256 Farben',
      lossy: 'Kompressionsstufe (Lossy)', lossyHint: 'Höher bedeutet eine kleinere Datei und sichtbareres Rauschen.',
      optimize: 'Datei optimieren', download: 'Ergebnis herunterladen', auto: 'Auto bis 5 MB',
      autoHint: 'Beste Qualität, die in Steams 5 MB passt', quotaNote: 'Jeder Durchlauf zählt als eine Datei des täglichen Free-Limits. Pro hat kein Limit.',
      check: 'Ergebnis prüfen', checkLead: 'Nach dem Optimieren ziehst du den Trenner direkt über das GIF, um Original und komprimierte Version zu vergleichen.',
      before: 'Vorher', after: 'Nachher', empty: 'Das GIF erscheint nach dem Hochladen', uploading: 'Wird hochgeladen…', queued: 'Wartet in der Warteschlange…',
      working: 'Wird optimiert…', done: 'Fertig', saved: 'kleiner um', bigger: 'Das Ergebnis ist größer als das Original: weniger Farben oder ein höheres Lossy versuchen.',
      fits: 'Passt für Steam (bis 5 MB)', tooBig: 'Über 5 MB: Steam nimmt es nicht an', alreadyFits: 'Das GIF ist schon unter 5 MB, es gibt nichts zu komprimieren.',
      frames: 'Frames', errNotGif: 'Nur GIF-Dateien. Andere Formate zuerst im Tab „Konverter“ umwandeln.',
      errQuota: 'Die kostenlosen Dateien für heute sind aufgebraucht. Pro hat kein Limit.', errBeta: 'Der GIF-Optimierer ist in der Beta und vorerst nur mit Pro verfügbar.', errFail: 'Das GIF konnte nicht optimiert werden. Erneut versuchen oder andere Einstellungen wählen.',
      errBig: 'Die Datei ist zu groß.', pickFirst: 'Wähle zuerst ein GIF.', compareLabel: 'Trenner zwischen Original und Ergebnis'
    },
    tr: {
      title: 'GIF Optimize Edici', lead: 'GIF\'i Steam sınırlarına göre küçült ve indirmeden önce sonucu kontrol et.',
      settings: 'Sıkıştırma ayarları', drop: 'Sıkıştırmak için GIF yükle', dropHint: 'Dosyayı buraya sürükle veya seçmek için tıkla.',
      change: 'Başka bir GIF seç', colors: 'Palet renk sınırı', custom: 'Diğer', customHint: '2 ile 256 renk arası',
      lossy: 'Sıkıştırma düzeyi (Lossy)', lossyHint: 'Yüksek değer daha küçük dosya ama daha belirgin parazit demek.',
      optimize: 'Dosyayı optimize et', download: 'Sonucu indir', auto: '5 MB\'a kadar otomatik',
      autoHint: 'Steam\'in 5 MB sınırına sığan en iyi kalite', quotaNote: 'Her çalıştırma günlük Free sınırından bir dosya sayılır. Pro\'da sınır yok.',
      check: 'Sonucu kontrol et', checkLead: 'Optimizasyondan sonra ayırıcıyı GIF\'in üzerinde sürükleyerek orijinal ile sıkıştırılmış sürümü karşılaştır.',
      before: 'Önce', after: 'Sonra', empty: 'GIF yüklendikten sonra burada görünür', uploading: 'Yükleniyor…', queued: 'Sırada bekliyor…',
      working: 'Optimize ediliyor…', done: 'Hazır', saved: 'daha küçük:', bigger: 'Sonuç orijinalden büyük çıktı: daha az renk veya daha yüksek Lossy dene.',
      fits: 'Steam\'e uygun (5 MB\'a kadar)', tooBig: '5 MB\'tan büyük: Steam kabul etmez', alreadyFits: 'GIF zaten 5 MB\'tan küçük, sıkıştırılacak bir şey yok.',
      frames: 'kare', errNotGif: 'Yalnızca GIF dosyaları. Diğer biçimleri önce Dönüştürücü sekmesinde çevir.',
      errQuota: 'Bugünkü ücretsiz dosyalar bitti. Pro\'da sınır yok.', errBeta: 'GIF Optimizer beta aşamasında ve şimdilik yalnızca Pro ile kullanılabilir.', errFail: 'GIF optimize edilemedi. Tekrar dene veya başka ayarlar seç.',
      errBig: 'Dosya çok büyük.', pickFirst: 'Önce bir GIF seç.', compareLabel: 'Orijinal ile sonuç arasındaki ayırıcı'
    },
    fr: {
      title: 'Optimiseur GIF', lead: 'Réduisez un GIF aux limites de Steam et vérifiez le résultat avant de le télécharger.',
      settings: 'Réglages de compression', drop: 'Importez un GIF à compresser', dropHint: 'Déposez le fichier ici ou cliquez pour le choisir.',
      change: 'Choisir un autre GIF', colors: 'Limite de couleurs de la palette', custom: 'Autre', customHint: 'De 2 à 256 couleurs',
      lossy: 'Niveau de compression (Lossy)', lossyHint: 'Plus haut : fichier plus léger, bruit plus visible.',
      optimize: 'Optimiser le fichier', download: 'Télécharger le résultat', auto: 'Auto jusqu\'à 5 Mo',
      autoHint: 'La meilleure qualité qui tient dans les 5 Mo de Steam', quotaNote: 'Chaque passage compte pour un fichier de la limite Free du jour. Pro est illimité.',
      check: 'Vérifier le résultat', checkLead: 'Après l\'optimisation, faites glisser le séparateur directement sur le GIF pour comparer l\'original et la version compressée.',
      before: 'Avant', after: 'Après', empty: 'Le GIF apparaît après l\'import', uploading: 'Envoi…', queued: 'En file d\'attente…',
      working: 'Optimisation…', done: 'Terminé', saved: 'plus léger de', bigger: 'Le résultat est plus lourd que l\'original : essayez moins de couleurs ou un Lossy plus élevé.',
      fits: 'Convient à Steam (jusqu\'à 5 Mo)', tooBig: 'Plus de 5 Mo : Steam le refusera', alreadyFits: 'Le GIF fait déjà moins de 5 Mo, rien à compresser.',
      frames: 'images', errNotGif: 'Fichiers GIF uniquement. Convertissez d\'abord les autres formats dans l\'onglet Convertisseur.',
      errQuota: 'Les fichiers gratuits du jour sont épuisés. Pro est illimité.', errBeta: 'L’Optimiseur GIF est en bêta et réservé à Pro pour l’instant.', errFail: 'Impossible d\'optimiser le GIF. Réessayez ou changez les réglages.',
      errBig: 'Le fichier est trop volumineux.', pickFirst: 'Choisissez d\'abord un GIF.', compareLabel: 'Séparateur entre l\'original et le résultat'
    },
    uk: {
      title: 'GIF оптимізатор', lead: 'Стисніть GIF під ліміти Steam і перевірте результат перед завантаженням.',
      settings: 'Налаштування стиснення', drop: 'Завантажте GIF для стиснення', dropHint: 'Перетягніть файл сюди або натисніть, щоб вибрати.',
      change: 'Вибрати інший GIF', colors: 'Обмеження кольорів палітри', custom: 'Інше', customHint: 'Від 2 до 256 кольорів',
      lossy: 'Рівень компресії (Lossy)', lossyHint: 'Більше — менший файл, але помітніший шум.',
      optimize: 'Оптимізувати файл', download: 'Завантажити результат', auto: 'Авто до 5 MB',
      autoHint: 'Найкраща якість, що вміщується в 5 МБ Steam', quotaNote: 'Кожен запуск — один файл із денного ліміту Free. У Pro без обмежень.',
      check: 'Перевірка результату', checkLead: 'Після оптимізації з\'явиться порівняння: перетягуйте роздільник просто по GIF, щоб побачити оригінал і стиснену версію.',
      before: 'До', after: 'Після', empty: 'GIF з\'явиться після завантаження', uploading: 'Завантажуємо…', queued: 'У черзі…',
      working: 'Оптимізуємо…', done: 'Готово', saved: 'менше на', bigger: 'Результат вийшов більшим за оригінал: зменште кількість кольорів або збільште Lossy.',
      fits: 'Підходить для Steam (до 5 МБ)', tooBig: 'Більше 5 МБ: Steam не прийме', alreadyFits: 'GIF уже менший за 5 МБ, стискати нічого.',
      frames: 'кадрів', errNotGif: 'Лише GIF. Інші формати спершу переведіть на вкладці «Конвертер».',
      errQuota: 'Безкоштовні файли на сьогодні закінчилися. У Pro ліміту немає.', errBeta: 'GIF оптимізатор у бета-тесті й поки доступний лише з Pro.', errFail: 'Не вдалося оптимізувати GIF. Спробуйте ще раз або інші налаштування.',
      errBig: 'Файл завеликий.', pickFirst: 'Спершу виберіть GIF.', compareLabel: 'Роздільник між оригіналом і результатом'
    },
    es: {
      title: 'Optimizador de GIF', lead: 'Reduce un GIF a los límites de Steam y revisa el resultado antes de descargarlo.',
      settings: 'Ajustes de compresión', drop: 'Sube un GIF para comprimirlo', dropHint: 'Suelta el archivo aquí o haz clic para elegirlo.',
      change: 'Elegir otro GIF', colors: 'Límite de colores de la paleta', custom: 'Otro', customHint: 'De 2 a 256 colores',
      lossy: 'Nivel de compresión (Lossy)', lossyHint: 'Más alto significa un archivo más ligero y más ruido visible.',
      optimize: 'Optimizar archivo', download: 'Descargar resultado', auto: 'Auto hasta 5 MB',
      autoHint: 'La mejor calidad que cabe en los 5 MB de Steam', quotaNote: 'Cada ejecución cuenta como un archivo del límite diario Free. Pro no tiene límite.',
      check: 'Revisar el resultado', checkLead: 'Tras optimizar, arrastra el divisor sobre el GIF para comparar el original y la versión comprimida.',
      before: 'Antes', after: 'Después', empty: 'El GIF aparece después de subirlo', uploading: 'Subiendo…', queued: 'En la cola…',
      working: 'Optimizando…', done: 'Listo', saved: 'más ligero en', bigger: 'El resultado pesa más que el original: prueba menos colores o un Lossy más alto.',
      fits: 'Apto para Steam (hasta 5 MB)', tooBig: 'Más de 5 MB: Steam no lo aceptará', alreadyFits: 'El GIF ya pesa menos de 5 MB, no hay nada que comprimir.',
      frames: 'fotogramas', errNotGif: 'Solo archivos GIF. Convierte otros formatos primero en la pestaña Convertidor.',
      errQuota: 'Se acabaron los archivos gratuitos de hoy. Pro no tiene límite.', errBeta: 'El Optimizador de GIF está en beta y por ahora solo está disponible con Pro.', errFail: 'No se pudo optimizar el GIF. Inténtalo de nuevo o cambia los ajustes.',
      errBig: 'El archivo es demasiado grande.', pickFirst: 'Primero elige un GIF.', compareLabel: 'Divisor entre el original y el resultado'
    },
    pt: {
      title: 'Otimizador de GIF', lead: 'Reduza um GIF aos limites da Steam e confira o resultado antes de baixar.',
      settings: 'Ajustes de compressão', drop: 'Envie um GIF para comprimir', dropHint: 'Solte o arquivo aqui ou clique para escolher.',
      change: 'Escolher outro GIF', colors: 'Limite de cores da paleta', custom: 'Outro', customHint: 'De 2 a 256 cores',
      lossy: 'Nível de compressão (Lossy)', lossyHint: 'Mais alto significa arquivo menor e ruído mais visível.',
      optimize: 'Otimizar arquivo', download: 'Baixar resultado', auto: 'Auto até 5 MB',
      autoHint: 'A melhor qualidade que cabe nos 5 MB da Steam', quotaNote: 'Cada execução conta como um arquivo do limite diário Free. O Pro não tem limite.',
      check: 'Conferir o resultado', checkLead: 'Depois de otimizar, arraste o divisor sobre o GIF para comparar o original e a versão comprimida.',
      before: 'Antes', after: 'Depois', empty: 'O GIF aparece depois do envio', uploading: 'Enviando…', queued: 'Na fila…',
      working: 'Otimizando…', done: 'Pronto', saved: 'menor em', bigger: 'O resultado ficou maior que o original: tente menos cores ou um Lossy maior.',
      fits: 'Serve para a Steam (até 5 MB)', tooBig: 'Mais de 5 MB: a Steam não aceita', alreadyFits: 'O GIF já tem menos de 5 MB, não há o que comprimir.',
      frames: 'quadros', errNotGif: 'Somente arquivos GIF. Converta outros formatos primeiro na aba Conversor.',
      errQuota: 'Os arquivos gratuitos de hoje acabaram. O Pro não tem limite.', errBeta: 'O Otimizador de GIF está em beta e, por enquanto, só está disponível com o Pro.', errFail: 'Não foi possível otimizar o GIF. Tente de novo ou mude os ajustes.',
      errBig: 'O arquivo é grande demais.', pickFirst: 'Escolha um GIF primeiro.', compareLabel: 'Divisor entre o original e o resultado'
    }
  };
  var COLORS = [256, 200, 128, 64, 32, 16];
  var LIMIT = 5 * 1024 * 1024;

  function lang() { var l = window.SMLang && SMLang.get ? SMLang.get() : 'en'; return COPY[l] ? l : 'en'; }
  function t(key) { return (COPY[lang()] || COPY.en)[key] || COPY.en[key] || key; }
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function mb(bytes) { return (bytes / 1048576).toFixed(bytes < 10485760 ? 2 : 1) + ' MB'; }

  var host = document.getElementById('gifOptimizer');
  if (!host) return;

  var state = { file: null, srcUrl: '', colors: 256, custom: false, lossy: 30, busy: false, job: null, result: null, split: 50 };
  var refs = {};

  function build() {
    host.replaceChildren();
    var wrap = el('div', 'gopt');
    // ---- settings
    var side = el('aside', 'card gopt__side');
    // The page header already shows the tab name: the card starts with its own purpose.
    side.append(el('h2', 'gopt__title', t('settings')), el('p', 'gopt__lead', t('lead')));
    var box = el('div', 'gopt__panel');
    var drop = el('label', 'gopt-drop');
    var input = el('input'); input.type = 'file'; input.accept = 'image/gif'; input.hidden = true;
    input.dataset.smEnhanced = '1'; // app-tail.js would add a second upload widget next to it
    input.addEventListener('change', function () { if (input.files[0]) pick(input.files[0]); input.value = ''; });
    var dropIcon = el('span', 'gopt-drop__icon', '⇪');
    var dropText = el('span', 'gopt-drop__text');
    refs.dropText = dropText;
    drop.append(input, dropIcon, dropText);
    ['dragenter', 'dragover'].forEach(function (e) { drop.addEventListener(e, function (ev) { ev.preventDefault(); drop.classList.add('is-over'); }); });
    ['dragleave', 'drop'].forEach(function (e) { drop.addEventListener(e, function (ev) { ev.preventDefault(); drop.classList.remove('is-over'); }); });
    drop.addEventListener('drop', function (ev) { var f = ev.dataTransfer && ev.dataTransfer.files[0]; if (f) pick(f); });
    box.append(drop);

    var colors = el('div', 'gopt-group');
    colors.append(el('b', '', t('colors')));
    var chips = el('div', 'gopt-chips');
    COLORS.forEach(function (n) {
      var c = el('button', 'gopt-chip' + (!state.custom && state.colors === n ? ' is-on' : ''), String(n));
      c.type = 'button';
      c.addEventListener('click', function () { state.custom = false; state.colors = n; build(); });
      chips.append(c);
    });
    var other = el('button', 'gopt-chip' + (state.custom ? ' is-on' : ''), t('custom'));
    other.type = 'button';
    other.addEventListener('click', function () { state.custom = true; build(); var f = host.querySelector('.gopt-custom input'); if (f) f.focus(); });
    chips.append(other);
    colors.append(chips);
    if (state.custom) {
      var custom = el('label', 'gopt-custom');
      var num = el('input'); num.type = 'number'; num.min = 2; num.max = 256; num.value = state.colors;
      num.addEventListener('input', function () { var v = parseInt(num.value, 10); if (v >= 2 && v <= 256) state.colors = v; });
      custom.append(num, el('span', '', t('customHint')));
      colors.append(custom);
    }
    box.append(colors);

    var lossy = el('div', 'gopt-group');
    var lossyHead = el('div', 'gopt-row');
    lossyHead.append(el('b', '', t('lossy')));
    var lossyNum = el('label', 'gopt-num');
    var ln = el('input'); ln.type = 'number'; ln.min = 0; ln.max = 100; ln.value = state.lossy;
    lossyNum.append(ln, el('span', '', '%'));
    lossyHead.append(lossyNum);
    var range = el('input', 'gopt-range'); range.type = 'range'; range.min = 0; range.max = 100; range.value = state.lossy;
    range.setAttribute('aria-label', t('lossy'));
    function setLossy(v) { v = Math.max(0, Math.min(100, parseInt(v, 10) || 0)); state.lossy = v; ln.value = v; range.value = v; range.style.setProperty('--fill', v + '%'); }
    range.addEventListener('input', function () { setLossy(range.value); });
    ln.addEventListener('input', function () { setLossy(ln.value); });
    setLossy(state.lossy);
    lossy.append(lossyHead, range, el('small', 'gopt-muted', t('lossyHint')));
    box.append(lossy);
    side.append(box);

    var go = el('button', 'btn gopt-go', t('optimize'));
    go.type = 'button';
    go.addEventListener('click', function () { run('manual'); });
    var dl = el('a', 'btn ghost gopt-dl', t('download'));
    dl.setAttribute('aria-disabled', 'true');
    var auto = el('button', 'btn ghost gopt-auto');
    auto.type = 'button';
    auto.append(el('b', '', t('auto')), el('small', '', t('autoHint')));
    auto.addEventListener('click', function () { run('auto'); });
    var status = el('p', 'gopt-status');
    status.setAttribute('role', 'status');
    side.append(go, dl, auto, status, el('small', 'gopt-muted gopt-quota', t('quotaNote')));
    refs.go = go; refs.dl = dl; refs.auto = auto; refs.status = status;

    // ---- result
    var main = el('section', 'card gopt__main');
    main.append(el('h2', 'gopt__title', t('check')), el('p', 'gopt__lead', t('checkLead')));
    var stage = el('div', 'gopt-stage');
    var compare = el('div', 'gopt-compare');
    var before = el('img', 'gopt-compare__img'); before.alt = t('before');
    var after = el('img', 'gopt-compare__img gopt-compare__after'); after.alt = t('after');
    var line = el('span', 'gopt-compare__line');
    var knob = el('span', 'gopt-compare__knob', '⇆');
    var lb = el('span', 'gopt-compare__tag gopt-compare__tag--l', t('before'));
    var la = el('span', 'gopt-compare__tag gopt-compare__tag--r', t('after'));
    var slider = el('input', 'gopt-compare__range'); slider.type = 'range'; slider.min = 0; slider.max = 100; slider.value = state.split;
    slider.setAttribute('aria-label', t('compareLabel'));
    slider.addEventListener('input', function () { state.split = +slider.value; paintSplit(); });
    var empty = el('div', 'gopt-empty', t('empty'));
    compare.append(before, after, line, knob, lb, la, slider);
    stage.append(compare, empty);
    var stats = el('div', 'gopt-stats');
    main.append(stage, stats);
    refs.compare = compare; refs.before = before; refs.after = after; refs.line = line; refs.knob = knob;
    refs.empty = empty; refs.stats = stats; refs.slider = slider; refs.tagAfter = la;

    wrap.append(side, main);
    host.append(wrap);
    paint();
  }

  function paintSplit() {
    var x = state.split;
    refs.after.style.clipPath = 'inset(0 0 0 ' + x + '%)';
    refs.line.style.left = x + '%';
    refs.knob.style.left = x + '%';
  }

  function paint() {
    var f = state.file;
    refs.dropText.replaceChildren();
    if (f) {
      refs.dropText.append(el('b', '', f.name), el('small', '', mb(f.size) + (state.job && state.job.width ? ' · ' + state.job.width + '×' + state.job.height + ' · ' + state.job.frames + ' ' + t('frames') : '') + ' · ' + t('change')));
    } else {
      refs.dropText.append(el('b', '', t('drop')), el('small', '', t('dropHint')));
    }
    refs.go.disabled = state.busy;
    refs.auto.disabled = state.busy;
    var r = state.result;
    if (r && r.download_url) { refs.dl.href = r.download_url; refs.dl.removeAttribute('aria-disabled'); refs.dl.classList.remove('is-off'); }
    else { refs.dl.removeAttribute('href'); refs.dl.setAttribute('aria-disabled', 'true'); refs.dl.classList.add('is-off'); }
    refs.empty.hidden = !!state.srcUrl;
    refs.compare.hidden = !state.srcUrl;
    if (state.srcUrl && refs.before.getAttribute('src') !== state.srcUrl) refs.before.src = state.srcUrl;
    var hasAfter = !!(r && r.result_url);
    if (hasAfter && !refs.after.getAttribute('src')) refs.after.src = r.result_url; // after a language switch rebuilt the tab
    refs.after.hidden = !hasAfter;
    refs.line.hidden = refs.knob.hidden = refs.slider.hidden = refs.tagAfter.hidden = !hasAfter;
    paintSplit();
    // numbers
    refs.stats.replaceChildren();
    if (f) refs.stats.append(stat(t('before'), mb(r && r.size_before || f.size), ''));
    if (r && r.size_after != null) {
      var diff = r.size_before ? Math.round((1 - r.size_after / r.size_before) * 100) : 0;
      refs.stats.append(stat(t('after'), mb(r.size_after), diff > 0 ? t('saved') + ' ' + diff + '%' : ''));
      var ok = r.size_after <= LIMIT;
      refs.stats.append(el('span', 'gopt-badge ' + (ok ? 'is-ok' : 'is-bad'), ok ? '✓ ' + t('fits') : '✕ ' + t('tooBig')));
    }
  }
  function stat(label, value, sub) {
    var s = el('div', 'gopt-stat');
    s.append(el('small', '', label), el('b', '', value));
    if (sub) s.append(el('span', '', sub));
    return s;
  }
  function say(text, bad) { refs.status.textContent = text || ''; refs.status.classList.toggle('is-bad', !!bad); }

  function pick(file) {
    if (state.busy) return;
    var isGif = /\.gif$/i.test(file.name) || file.type === 'image/gif';
    if (!isGif) { say(t('errNotGif'), true); return; }
    if (state.srcUrl) URL.revokeObjectURL(state.srcUrl);
    state.file = file; state.srcUrl = URL.createObjectURL(file); state.result = null; state.job = null;
    say('');
    paint();
  }

  function errorText(json, status) {
    var code = json && json.code;
    if (code === 'not_gif' || code === 'bad_gif') return t('errNotGif');
    if (code === 'beta') return t('errBeta');   // beta tools are Pro-only (smweb/free_limits.py)
    if (code === 'quota' || status === 403) return t('errQuota');
    if (status === 413) return t('errBig');
    if (json && json.msg && /larger than/i.test(json.msg)) return t('errBig');
    return t('errFail');
  }

  function run(mode) {
    if (state.busy) return;
    if (!state.file) { say(t('pickFirst'), true); return; }
    state.busy = true; state.result = null;
    say(t('uploading'));
    paint();
    var fd = new FormData();
    fd.append('file', state.file, state.file.name);
    fd.append('mode', mode);
    fd.append('colors', String(state.colors));
    fd.append('lossy', String(state.lossy));
    fetch('/api/gif-optimizer/start', { method: 'POST', body: fd, credentials: 'include' })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { return { r: r, j: j }; }); })
      .then(function (x) {
        if (!x.r.ok || !x.j.ok) throw { text: errorText(x.j, x.r.status) };
        if (typeof window.refreshQuota === 'function') window.refreshQuota().catch(function () {});
        return poll(x.j.job_id, mode);
      })
      .catch(function (e) { state.busy = false; say(e && e.text ? e.text : t('errFail'), true); paint(); });
  }

  function poll(id, mode) {
    return fetch('/api/gif-optimizer/status/' + id, { credentials: 'include' })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (!j || !j.ok) throw { text: t('errFail') };
        state.job = { width: j.width, height: j.height, frames: j.frames };
        if (j.status === 'done') {
          state.busy = false;
          state.result = j;
          var note = mode === 'auto' && j.already_fits ? t('alreadyFits') : (j.size_after > j.size_before ? t('bigger') : t('done'));
          say(note, false);
          // Reload both pictures together so the two GIFs start in step.
          refs.after.onload = function () { refs.before.src = state.srcUrl + '#' + Date.now(); refs.after.onload = null; };
          refs.after.src = j.result_url + '&t=' + Date.now();
          paint();
          return;
        }
        if (j.status === 'error') throw { text: j.error && !/failed/i.test(j.error) ? j.error : t('errFail') };
        say(j.status === 'queued' ? t('queued') : t('working') + (j.pct ? ' ' + j.pct + '%' : ''));
        paint();
        return new Promise(function (resolve) { setTimeout(resolve, 900); }).then(function () { return poll(id, mode); });
      });
  }

  build();
  window.addEventListener('sm:langchange', build);
  window.SMGifOptimizer = { state: state, pick: pick, run: run };
})();
