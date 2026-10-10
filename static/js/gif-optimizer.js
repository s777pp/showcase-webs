/* GIF Optimizer tab (#tab-gifopt). Rebuilt 2026-10-09 (owner: "it looks 1:1 like designsteam, make it ours"):
   a full-width stage (drop zone, then before / after as a slider or side by side), a size meter against Steam's
   5 MB, four goals instead of raw numbers ("Fit into Steam" = the server's auto mode, the same gifski fit as
   Process; "Balance" / "Smallest file" = gifsicle presets; "Manual" opens palette colours + Lossy) and one action
   bar. Runs as a job (/api/gif-optimizer/*). Copy: keyed var COPY= in 8 languages (scripts/check_i18n.js). */
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
      errBig: 'The file is too large.', pickFirst: 'Choose a GIF first.', compareLabel: 'Divider between the original and the result',
      dropTitle: 'Drop a GIF here', dropOr: 'Choose a file', dropNote: 'GIF up to 40 MB. Steam takes showcase files up to 5 MB.', replace: 'Replace', goal: 'What do you need?', g_auto: 'Fit into Steam', g_autoHint: 'The best quality that still fits 5 MB. We pick the settings.', recommended: 'Recommended', g_balance: 'Balance', g_balanceHint: 'Noticeably lighter with almost no visible loss.', g_max: 'Smallest file', g_maxHint: 'As light as possible: fewer colours, some grain.', g_manual: 'Manual', g_manualHint: 'Set the palette and Lossy yourself.', compress: 'Compress GIF', viewSlider: 'Slider', viewSide: 'Side by side', limitLabel: 'Steam limit · 5 MB', was: 'Original', now: 'Result', keptOriginal: 'This GIF is already packed tightly: the result came out bigger, so we kept your original. Try “Fit into Steam” or “Smallest file”.'
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
      errBig: 'Файл слишком большой.', pickFirst: 'Сначала выберите GIF.', compareLabel: 'Разделитель между исходником и результатом',
      dropTitle: 'Перетащи GIF сюда', dropOr: 'Выбрать файл', dropNote: 'GIF до 40 МБ. Steam принимает файлы витрины до 5 МБ.', replace: 'Заменить', goal: 'Что нужно сделать?', g_auto: 'Влезть в Steam', g_autoHint: 'Лучшее качество, которое ещё помещается в 5 МБ. Настройки подберём сами.', recommended: 'Рекомендуем', g_balance: 'Баланс', g_balanceHint: 'Заметно легче, потерь почти не видно.', g_max: 'Самый маленький файл', g_maxHint: 'Максимально лёгкий: меньше цветов, немного зерна.', g_manual: 'Вручную', g_manualHint: 'Сам выбираешь палитру и Lossy.', compress: 'Сжать GIF', viewSlider: 'Шторка', viewSide: 'Рядом', limitLabel: 'Лимит Steam · 5 МБ', was: 'Было', now: 'Стало', keptOriginal: 'Этот GIF уже плотно сжат: результат вышел больше, поэтому оставили исходный файл. Попробуй «Влезть в Steam» или «Самый маленький файл».'
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
      errBig: 'Die Datei ist zu groß.', pickFirst: 'Wähle zuerst ein GIF.', compareLabel: 'Trenner zwischen Original und Ergebnis',
      dropTitle: 'GIF hierher ziehen', dropOr: 'Datei wählen', dropNote: 'GIF bis 40 MB. Steam nimmt Präsentationsdateien bis 5 MB an.', replace: 'Ersetzen', goal: 'Was brauchst du?', g_auto: 'Passt in Steam', g_autoHint: 'Die beste Qualität, die noch in 5 MB passt. Die Einstellungen wählen wir.', recommended: 'Empfohlen', g_balance: 'Ausgewogen', g_balanceHint: 'Deutlich leichter, kaum sichtbarer Verlust.', g_max: 'Kleinste Datei', g_maxHint: 'So leicht wie möglich: weniger Farben, etwas Körnung.', g_manual: 'Manuell', g_manualHint: 'Palette und Lossy selbst einstellen.', compress: 'GIF komprimieren', viewSlider: 'Schieber', viewSide: 'Nebeneinander', limitLabel: 'Steam-Limit · 5 MB', was: 'Vorher', now: 'Nachher', keptOriginal: 'Dieses GIF ist schon dicht gepackt: das Ergebnis wurde größer, also bleibt dein Original. Versuch „Passt in Steam“ oder „Kleinste Datei“.'
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
      errBig: 'Dosya çok büyük.', pickFirst: 'Önce bir GIF seç.', compareLabel: 'Orijinal ile sonuç arasındaki ayırıcı',
      dropTitle: 'GIF\'i buraya bırak', dropOr: 'Dosya seç', dropNote: '40 MB\'a kadar GIF. Steam vitrin dosyalarını 5 MB\'a kadar kabul eder.', replace: 'Değiştir', goal: 'Ne yapmak istiyorsun?', g_auto: 'Steam\'e sığdır', g_autoHint: '5 MB\'a sığan en iyi kalite. Ayarları biz seçeriz.', recommended: 'Önerilen', g_balance: 'Denge', g_balanceHint: 'Belirgin şekilde hafif, kayıp neredeyse görünmez.', g_max: 'En küçük dosya', g_maxHint: 'Olabildiğince hafif: daha az renk, biraz gren.', g_manual: 'Elle', g_manualHint: 'Paleti ve Lossy\'yi kendin ayarla.', compress: 'GIF\'i sıkıştır', viewSlider: 'Perde', viewSide: 'Yan yana', limitLabel: 'Steam sınırı · 5 MB', was: 'Önce', now: 'Sonra', keptOriginal: 'Bu GIF zaten sıkı paketlenmiş: sonuç daha büyük çıktı, bu yüzden orijinali bıraktık. “Steam\'e sığdır” ya da “En küçük dosya”yı dene.'
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
      errBig: 'Le fichier est trop volumineux.', pickFirst: 'Choisissez d\'abord un GIF.', compareLabel: 'Séparateur entre l\'original et le résultat',
      dropTitle: 'Dépose un GIF ici', dropOr: 'Choisir un fichier', dropNote: 'GIF jusqu’à 40 Mo. Steam accepte les fichiers de vitrine jusqu’à 5 Mo.', replace: 'Remplacer', goal: 'Que veux-tu faire ?', g_auto: 'Entrer dans Steam', g_autoHint: 'La meilleure qualité qui tient encore dans 5 Mo. On choisit les réglages.', recommended: 'Recommandé', g_balance: 'Équilibre', g_balanceHint: 'Nettement plus léger, perte presque invisible.', g_max: 'Fichier le plus léger', g_maxHint: 'Aussi léger que possible : moins de couleurs, un peu de grain.', g_manual: 'Manuel', g_manualHint: 'Règle toi-même la palette et le Lossy.', compress: 'Compresser le GIF', viewSlider: 'Volet', viewSide: 'Côte à côte', limitLabel: 'Limite Steam · 5 Mo', was: 'Avant', now: 'Après', keptOriginal: 'Ce GIF est déjà bien compressé : le résultat était plus lourd, on a gardé l’original. Essaie « Entrer dans Steam » ou « Fichier le plus léger ».'
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
      errBig: 'Файл завеликий.', pickFirst: 'Спершу виберіть GIF.', compareLabel: 'Роздільник між оригіналом і результатом',
      dropTitle: 'Перетягни GIF сюди', dropOr: 'Вибрати файл', dropNote: 'GIF до 40 МБ. Steam приймає файли вітрини до 5 МБ.', replace: 'Замінити', goal: 'Що потрібно зробити?', g_auto: 'Вміститися в Steam', g_autoHint: 'Найкраща якість, що ще вміщується в 5 МБ. Налаштування підберемо самі.', recommended: 'Радимо', g_balance: 'Баланс', g_balanceHint: 'Помітно легше, втрат майже не видно.', g_max: 'Найменший файл', g_maxHint: 'Максимально легкий: менше кольорів, трохи зерна.', g_manual: 'Вручну', g_manualHint: 'Сам вибираєш палітру й Lossy.', compress: 'Стиснути GIF', viewSlider: 'Шторка', viewSide: 'Поруч', limitLabel: 'Ліміт Steam · 5 МБ', was: 'Було', now: 'Стало', keptOriginal: 'Цей GIF уже щільно стиснутий: результат вийшов більшим, тож залишили оригінал. Спробуй «Вміститися в Steam» або «Найменший файл».'
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
      errBig: 'El archivo es demasiado grande.', pickFirst: 'Primero elige un GIF.', compareLabel: 'Divisor entre el original y el resultado',
      dropTitle: 'Suelta un GIF aquí', dropOr: 'Elegir archivo', dropNote: 'GIF de hasta 40 MB. Steam acepta archivos de escaparate de hasta 5 MB.', replace: 'Cambiar', goal: '¿Qué necesitas?', g_auto: 'Que quepa en Steam', g_autoHint: 'La mejor calidad que aún cabe en 5 MB. Elegimos los ajustes por ti.', recommended: 'Recomendado', g_balance: 'Equilibrio', g_balanceHint: 'Bastante más ligero, casi sin pérdida visible.', g_max: 'Archivo más pequeño', g_maxHint: 'Lo más ligero posible: menos colores, algo de grano.', g_manual: 'Manual', g_manualHint: 'Ajusta tú la paleta y el Lossy.', compress: 'Comprimir GIF', viewSlider: 'Cortina', viewSide: 'Lado a lado', limitLabel: 'Límite de Steam · 5 MB', was: 'Antes', now: 'Después', keptOriginal: 'Este GIF ya está muy comprimido: el resultado pesaba más, así que dejamos el original. Prueba «Que quepa en Steam» o «Archivo más pequeño».'
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
      errBig: 'O arquivo é grande demais.', pickFirst: 'Escolha um GIF primeiro.', compareLabel: 'Divisor entre o original e o resultado',
      dropTitle: 'Solte um GIF aqui', dropOr: 'Escolher arquivo', dropNote: 'GIF de até 40 MB. A Steam aceita arquivos de vitrine de até 5 MB.', replace: 'Trocar', goal: 'O que você precisa?', g_auto: 'Caber na Steam', g_autoHint: 'A melhor qualidade que ainda cabe em 5 MB. Nós escolhemos os ajustes.', recommended: 'Recomendado', g_balance: 'Equilíbrio', g_balanceHint: 'Bem mais leve, quase sem perda visível.', g_max: 'Menor arquivo', g_maxHint: 'O mais leve possível: menos cores, um pouco de granulação.', g_manual: 'Manual', g_manualHint: 'Ajuste você mesmo a paleta e o Lossy.', compress: 'Comprimir GIF', viewSlider: 'Cortina', viewSide: 'Lado a lado', limitLabel: 'Limite da Steam · 5 MB', was: 'Antes', now: 'Depois', keptOriginal: 'Este GIF já está bem comprimido: o resultado ficou maior, então mantivemos o original. Tente «Caber na Steam» ou «Menor arquivo».'
    }
  };
  var COLORS = [256, 200, 128, 64, 32, 16];
  var LIMIT = 5 * 1024 * 1024;
  // Goals instead of raw numbers (owner 2026-10-09: "our own, not a copy of designsteam"). "fit" = the server's
  // auto mode (gifski fit under 5 MB, same as Process); the others are gifsicle presets; "manual" opens the controls.
  var GOALS = [
    { id: 'fit', mode: 'auto', icon: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r=".6"/>' },
    { id: 'balance', mode: 'manual', colors: 192, lossy: 30, icon: '<path d="M12 4v16M7 20h10M5 8h14M5 8l-2.5 6h5zM19 8l-2.5 6h5z"/>' },
    { id: 'max', mode: 'manual', colors: 96, lossy: 70, icon: '<path d="M4 4l6 6M10 5v5H5M20 20l-6-6M14 19v-5h5M20 4l-6 6M14 5v5h5M4 20l6-6M5 14h5v5"/>' },
    { id: 'manual', mode: 'manual', icon: '<path d="M5 6h9M18 6h1M5 12h3M12 12h7M5 18h11M20 18h-1"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>' }
  ];
  function svgIcon(paths) {
    var span = el('span', 'gox-goal__icon');
    span.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true">' + paths + '</svg>';  // constant markup from GOALS
    return span;
  }
  var GOAL_KEYS = { fit: ['g_auto', 'g_autoHint'], balance: ['g_balance', 'g_balanceHint'], max: ['g_max', 'g_maxHint'], manual: ['g_manual', 'g_manualHint'] };

  function lang() { var l = window.SMLang && SMLang.get ? SMLang.get() : 'en'; return COPY[l] ? l : 'en'; }
  function t(key) { return (COPY[lang()] || COPY.en)[key] || COPY.en[key] || key; }
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function mb(bytes) { return (bytes / 1048576).toFixed(bytes < 10485760 ? 2 : 1) + ' MB'; }
  function button(cls, text, onClick) { var b = el('button', cls, text); b.type = 'button'; if (onClick) b.addEventListener('click', onClick); return b; }

  var host = document.getElementById('gifOptimizer');
  if (!host) return;

  var state = { file: null, srcUrl: '', goal: 'fit', colors: 256, custom: false, lossy: 30, busy: false, pct: 0, job: null, result: null, split: 50, view: 'slider' };
  var refs = {};

  function build() {
    host.replaceChildren();
    var wrap = el('div', 'gox');

    // ---- stage: the drop zone, then the before / after view
    var stage = el('section', 'gox-stage');
    var input = el('input'); input.type = 'file'; input.accept = 'image/gif'; input.hidden = true;
    input.dataset.smEnhanced = '1'; // app-tail.js would add a second upload widget next to it
    input.addEventListener('change', function () { if (input.files[0]) pick(input.files[0]); input.value = ''; });
    refs.input = input;
    var drop = el('label', 'gox-drop');
    var orb = el('span', 'gox-drop__orb');
    orb.append(el('span', 'gox-drop__gif', 'GIF'));
    var dropText = el('span', 'gox-drop__text');
    dropText.append(el('b', '', t('dropTitle')), el('span', 'gox-drop__btn', t('dropOr')), el('small', '', t('dropNote')));
    drop.append(input, orb, dropText);
    ['dragenter', 'dragover'].forEach(function (e) { stage.addEventListener(e, function (ev) { ev.preventDefault(); stage.classList.add('is-over'); }); });
    ['dragleave', 'drop'].forEach(function (e) { stage.addEventListener(e, function (ev) { ev.preventDefault(); if (e === 'drop' || !stage.contains(ev.relatedTarget)) stage.classList.remove('is-over'); }); });
    stage.addEventListener('drop', function (ev) { var f = ev.dataTransfer && ev.dataTransfer.files[0]; if (f) pick(f); });

    var view = el('div', 'gox-view');
    var top = el('div', 'gox-view__top');
    refs.fileChip = el('div', 'gox-file');
    var switcher = el('div', 'gox-switch');
    refs.viewBtns = {};
    [['slider', 'viewSlider'], ['side', 'viewSide']].forEach(function (v) {
      var b = button('gox-switch__btn', t(v[1]), function () { state.view = v[0]; paint(); });
      refs.viewBtns[v[0]] = b; switcher.append(b);
    });
    refs.switcher = switcher;
    top.append(refs.fileChip, switcher);
    var compare = el('div', 'gox-compare');
    var before = el('img', 'gox-compare__img'); before.alt = t('before');
    var after = el('img', 'gox-compare__img gox-compare__after'); after.alt = t('after');
    var line = el('span', 'gox-compare__line');
    var knob = el('span', 'gox-compare__knob');
    var lb = el('span', 'gox-tag gox-tag--l', t('before'));
    var la = el('span', 'gox-tag gox-tag--r', t('after'));
    var slider = el('input', 'gox-compare__range'); slider.type = 'range'; slider.min = 0; slider.max = 100; slider.value = state.split;
    slider.setAttribute('aria-label', t('compareLabel'));
    slider.addEventListener('input', function () { state.split = +slider.value; paintSplit(); });
    compare.append(before, after, line, knob, lb, la, slider);
    var side = el('div', 'gox-side');
    var sideBefore = el('figure', 'gox-side__item'), sideAfter = el('figure', 'gox-side__item');
    var sb = el('img'); sb.alt = t('before'); var sa = el('img'); sa.alt = t('after');
    refs.sideBeforeCap = el('figcaption'); refs.sideAfterCap = el('figcaption');
    sideBefore.append(sb, refs.sideBeforeCap); sideAfter.append(sa, refs.sideAfterCap);
    side.append(sideBefore, sideAfter);
    refs.busy = el('div', 'gox-busy');
    refs.busyText = el('b');
    refs.busyBar = el('i');
    var bar = el('span', 'gox-busy__bar'); bar.append(refs.busyBar);
    refs.busy.append(el('span', 'gox-busy__spin'), refs.busyText, bar);
    view.append(top, compare, side, refs.busy);
    stage.append(drop, view);
    refs.stage = stage; refs.drop = drop; refs.view = view;
    refs.compare = compare; refs.before = before; refs.after = after; refs.line = line; refs.knob = knob; refs.slider = slider; refs.tagAfter = la;
    refs.side = side; refs.sideBefore = sb; refs.sideAfter = sa;

    // ---- size meter against Steam's 5 MB
    var meter = el('section', 'gox-meter');
    refs.meter = meter;

    // ---- goals
    var goals = el('section', 'gox-goals');
    goals.append(el('h3', 'gox-h', t('goal')));
    var grid = el('div', 'gox-goals__grid');
    refs.goalBtns = {};
    GOALS.forEach(function (g) {
      var card = button('gox-goal', null, function () { setGoal(g.id); });
      card.setAttribute('aria-pressed', 'false');
      var head = el('span', 'gox-goal__head');
      head.append(svgIcon(g.icon), el('b', '', t(GOAL_KEYS[g.id][0])));
      if (g.id === 'fit') head.append(el('span', 'gox-goal__tag', t('recommended')));
      card.append(head, el('small', '', t(GOAL_KEYS[g.id][1])));
      refs.goalBtns[g.id] = card;
      grid.append(card);
    });
    goals.append(grid);

    // manual controls (only for "Manual")
    var manual = el('div', 'gox-manual');
    var colors = el('div', 'gox-group');
    colors.append(el('b', '', t('colors')));
    var chips = el('div', 'gox-chips');
    COLORS.forEach(function (n) {
      chips.append(button('gox-chip' + (!state.custom && state.colors === n ? ' is-on' : ''), String(n), function () { state.custom = false; state.colors = n; build(); }));
    });
    chips.append(button('gox-chip' + (state.custom ? ' is-on' : ''), t('custom'), function () {
      state.custom = true; build(); var f = host.querySelector('.gox-custom input'); if (f) f.focus();
    }));
    colors.append(chips);
    if (state.custom) {
      var custom = el('label', 'gox-custom');
      var num = el('input'); num.type = 'number'; num.min = 2; num.max = 256; num.value = state.colors;
      num.addEventListener('input', function () { var v = parseInt(num.value, 10); if (v >= 2 && v <= 256) state.colors = v; });
      custom.append(num, el('span', '', t('customHint')));
      colors.append(custom);
    }
    var lossy = el('div', 'gox-group');
    var lossyHead = el('div', 'gox-row');
    lossyHead.append(el('b', '', t('lossy')));
    var lossyNum = el('label', 'gox-num');
    var ln = el('input'); ln.type = 'number'; ln.min = 0; ln.max = 100; ln.value = state.lossy;
    ln.setAttribute('aria-label', t('lossy'));
    lossyNum.append(ln, el('span', '', '%'));
    lossyHead.append(lossyNum);
    var range = el('input', 'gox-range'); range.type = 'range'; range.min = 0; range.max = 100; range.value = state.lossy;
    range.setAttribute('aria-label', t('lossy'));
    function setLossy(v) { v = Math.max(0, Math.min(100, parseInt(v, 10) || 0)); state.lossy = v; ln.value = v; range.value = v; range.style.setProperty('--fill', v + '%'); }
    range.addEventListener('input', function () { setLossy(range.value); });
    ln.addEventListener('input', function () { setLossy(ln.value); });
    setLossy(state.lossy);
    lossy.append(lossyHead, range, el('small', 'gox-muted', t('lossyHint')));
    manual.append(colors, lossy);
    refs.manual = manual;
    goals.append(manual);

    // ---- action bar
    var actions = el('section', 'gox-actions');
    var go = button('gox-go', t('compress'), function () { run(); });
    var dl = el('a', 'gox-dl', '⬇ ' + t('download'));
    var status = el('p', 'gox-status'); status.setAttribute('role', 'status');
    var main = el('div', 'gox-actions__main');
    main.append(go, dl);
    actions.append(main, status, el('small', 'gox-muted gox-quota', t('quotaNote')));
    refs.go = go; refs.dl = dl; refs.status = status;

    wrap.append(stage, meter, goals, actions);
    host.append(wrap);
    paint();
  }

  function setGoal(id) { state.goal = id; paint(); }

  function paintSplit() {
    var x = state.split;
    refs.after.style.clipPath = 'inset(0 0 0 ' + x + '%)';
    refs.line.style.left = x + '%';
    refs.knob.style.left = x + '%';
  }

  function paintMeter() {
    var m = refs.meter, f = state.file, r = state.result;
    m.replaceChildren();
    m.hidden = !f;
    if (!f) return;
    var was = (r && r.size_before) || f.size, now = r && r.size_after != null ? r.size_after : null;
    var scale = Math.max(was, now || 0, LIMIT) * 1.12;
    var track = el('div', 'gox-meter__track');
    var limit = el('span', 'gox-meter__limit'); limit.style.left = (LIMIT / scale * 100) + '%';
    limit.append(el('small', '', t('limitLabel')));
    var barWas = el('span', 'gox-meter__bar gox-meter__bar--was' + (was > LIMIT ? ' is-over' : ''));
    barWas.style.width = (was / scale * 100) + '%';
    track.append(barWas);
    if (now != null) {
      var barNow = el('span', 'gox-meter__bar gox-meter__bar--now' + (now > LIMIT ? ' is-over' : ''));
      barNow.style.width = (now / scale * 100) + '%';
      track.append(barNow);
    }
    track.append(limit);
    var legend = el('div', 'gox-meter__legend');
    var a = el('div', 'gox-meter__num');
    a.append(el('small', '', t('was')), el('b', '', mb(was)));
    legend.append(a);
    if (now != null) {
      var diff = was ? Math.round((1 - now / was) * 100) : 0;
      var b = el('div', 'gox-meter__num gox-meter__num--now');
      b.append(el('small', '', t('now')), el('b', '', mb(now)));
      legend.append(b);
      if (diff > 0) legend.append(el('span', 'gox-meter__save', '−' + diff + '%'));
      var ok = now <= LIMIT;
      legend.append(el('span', 'gox-badge ' + (ok ? 'is-ok' : 'is-bad'), ok ? '✓ ' + t('fits') : '✕ ' + t('tooBig')));
    } else {
      legend.append(el('span', 'gox-badge ' + (was <= LIMIT ? 'is-ok' : 'is-bad'), was <= LIMIT ? '✓ ' + t('fits') : '✕ ' + t('tooBig')));
    }
    m.append(legend, track);
  }

  function paint() {
    var f = state.file, r = state.result;
    refs.stage.classList.toggle('has-file', !!f);
    refs.drop.hidden = !!f;
    refs.view.hidden = !f;
    refs.fileChip.replaceChildren();
    if (f) {
      var info = el('span', 'gox-file__info');
      info.append(el('b', '', f.name), el('small', '', mb(f.size) + (state.job && state.job.width ? ' · ' + state.job.width + '×' + state.job.height + ' · ' + state.job.frames + ' ' + t('frames') : '')));
      var change = button('gox-file__change', t('replace'), function () { if (!state.busy) refs.input.click(); });
      refs.fileChip.append(el('span', 'gox-file__badge', 'GIF'), info, change);
    }
    if (state.srcUrl && refs.before.getAttribute('src') !== state.srcUrl) { refs.before.src = state.srcUrl; refs.sideBefore.src = state.srcUrl; }
    var hasAfter = !!(r && r.result_url);
    if (hasAfter && !refs.after.getAttribute('src')) { refs.after.src = r.result_url; refs.sideAfter.src = r.result_url; } // after a language switch rebuilt the tab
    var side = hasAfter && state.view === 'side';
    refs.compare.hidden = side;
    refs.side.hidden = !side;
    refs.switcher.hidden = !hasAfter;
    Object.keys(refs.viewBtns).forEach(function (k) { refs.viewBtns[k].classList.toggle('is-on', state.view === k); refs.viewBtns[k].setAttribute('aria-pressed', state.view === k ? 'true' : 'false'); });
    refs.after.hidden = !hasAfter;
    refs.line.hidden = refs.knob.hidden = refs.slider.hidden = refs.tagAfter.hidden = !hasAfter;
    refs.sideBeforeCap.textContent = t('before') + (f ? ' · ' + mb((r && r.size_before) || f.size) : '');
    refs.sideAfterCap.textContent = t('after') + (r && r.size_after != null ? ' · ' + mb(r.size_after) : '');
    paintSplit();
    refs.busy.hidden = !state.busy;
    refs.busyText.textContent = refs.status.textContent;
    refs.busyBar.style.width = Math.max(6, state.pct || 0) + '%';
    // goals
    Object.keys(refs.goalBtns).forEach(function (id) {
      refs.goalBtns[id].classList.toggle('is-on', state.goal === id);
      refs.goalBtns[id].setAttribute('aria-pressed', state.goal === id ? 'true' : 'false');
    });
    refs.manual.hidden = state.goal !== 'manual';
    refs.go.disabled = state.busy;
    refs.go.classList.toggle('is-busy', state.busy);
    if (r && r.download_url) { refs.dl.href = r.download_url; refs.dl.hidden = false; }
    else { refs.dl.removeAttribute('href'); refs.dl.hidden = true; }
    paintMeter();
  }
  function say(text, bad) {
    refs.status.textContent = text || ''; refs.status.classList.toggle('is-bad', !!bad);
    if (refs.busyText) refs.busyText.textContent = text || '';
  }

  function pick(file) {
    if (state.busy) return;
    var isGif = /\.gif$/i.test(file.name) || file.type === 'image/gif';
    if (!isGif) { say(t('errNotGif'), true); return; }
    if (state.srcUrl) URL.revokeObjectURL(state.srcUrl);
    state.file = file; state.srcUrl = URL.createObjectURL(file); state.result = null; state.job = null;
    refs.after.removeAttribute('src'); refs.sideAfter.removeAttribute('src');
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

  function run() {
    if (state.busy) return;
    if (!state.file) { say(t('pickFirst'), true); refs.input.click(); return; }
    var goal = GOALS.filter(function (g) { return g.id === state.goal; })[0] || GOALS[0];
    var mode = goal.mode, colors = goal.colors || state.colors, lossy = goal.lossy != null ? goal.lossy : state.lossy;
    state.busy = true; state.result = null; state.pct = 0;
    say(t('uploading'));
    paint();
    var fd = new FormData();
    fd.append('file', state.file, state.file.name);
    fd.append('mode', mode);
    fd.append('colors', String(colors));
    fd.append('lossy', String(lossy));
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
          state.busy = false; state.pct = 100;
          state.result = j;
          var note = mode === 'auto' && j.already_fits ? t('alreadyFits') : j.kept_original ? t('keptOriginal') : (j.size_after > j.size_before ? t('bigger') : t('done'));
          say(note, false);
          // Reload both pictures together so the two GIFs start in step.
          var url = j.result_url + '&t=' + Date.now();
          refs.after.onload = function () { var again = state.srcUrl + '#' + Date.now(); refs.before.src = again; refs.sideBefore.src = again; refs.after.onload = null; };
          refs.after.src = url; refs.sideAfter.src = url;
          paint();
          return;
        }
        if (j.status === 'error') throw { text: j.error && !/failed/i.test(j.error) ? j.error : t('errFail') };
        state.pct = j.pct || state.pct;
        say(j.status === 'queued' ? t('queued') : t('working') + (j.pct ? ' ' + j.pct + '%' : ''));
        paint();
        return new Promise(function (resolve) { setTimeout(resolve, 900); }).then(function () { return poll(id, mode); });
      });
  }

  build();
  window.addEventListener('sm:langchange', build);
  window.SMGifOptimizer = { state: state, pick: pick, run: run, setGoal: setGoal };
})();
