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
  function localize() {
    root.querySelectorAll('[data-pl]').forEach(function (node) { node.textContent = word(node.dataset.pl); });
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

  var refresh = function () { paint(); syncDock(); };
  var list = document.getElementById('fileList');
  if (list) new MutationObserver(refresh).observe(list, { childList: true });
  if (run) new MutationObserver(refresh).observe(run, { attributes: true, attributeFilter: ['disabled'] });
  new MutationObserver(syncDock).observe(root, { attributes: true, attributeFilter: ['class'] });
  root.addEventListener('click', function (event) { if (event.target.closest('.mode')) setTimeout(refresh, 0); });
  ['wmEnable', 'allModes'].forEach(function (id) { var node = document.getElementById(id); if (node) node.addEventListener('change', refresh); });
  document.addEventListener('sm:process-frame-change', refresh);
  window.addEventListener('resize', syncDock);
  window.addEventListener('sm:langchange', localize);
  localize();
  syncDock();
})();
