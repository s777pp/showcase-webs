/* "Picture from emoticons" for the Info box tab (owner's idea list, 2026-10-08).
   A picture is rebuilt as a mosaic of the visitor's OWN Steam emoticons and goes into the Info box text as
   ːnameːːnameː… lines (U+02D0, the delimiter Steam itself stores; one emoticon = 18x18 px, 33 fit in Steam's 604 px line).
   Steam shows only emoticons the author owns, so the list comes from the visitor's own Steam page
   (steamcommunity.com/actions/EmoticonList, opened while signed in to Steam) and is pasted here; it stays in this browser.
   The server only reads the colours of each emoticon picture (POST /api/infobox/emoticons, smweb/emoticon_colors.py:
   3x3 cells of [r, g, b, a]). Matching runs here: OKLab distance over the 3x3 cells, optional error diffusion, and a
   per-character penalty that prefers short names when the text would pass Steam's limit; the width shrinks if needed.
   infobox.js adds this as a tool tab ("🧩") through window.SMInfoBoxEmoji. The engine also loads in node for tests. */
(function () {
  'use strict';

  // ---------------------------------------------------------------- engine (no DOM)
  var GRID = 3, SUB = GRID * GRID, CELL = 18, MAX_COLS = 33, MAX_ROWS = 33;
  var BG = [16, 19, 32];   // Steam's Info box content over a dark profile, the colour behind transparent pixels
  function lin(c) { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
  var LIN = new Float32Array(256);
  for (var i = 0; i < 256; i++) LIN[i] = lin(i);
  function labLinear(lr, lg, lb, out, at) {
    var l = Math.cbrt(0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb);
    var m = Math.cbrt(0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb);
    var s = Math.cbrt(0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb);
    out[at] = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s;
    out[at + 1] = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s;
    out[at + 2] = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s;
  }
  function cost(name) { return name.length + 2; }

  /* items: [{name, cells: [[r, g, b, a] x 9]}] -> flat OKLab table composited over `bg`. */
  function palette(items, bg) {
    bg = bg || BG;
    var n = items.length, lab = new Float32Array(n * SUB * 3), mean = new Float32Array(n * 3), costs = new Float32Array(n), names = [];
    items.forEach(function (item, p) {
      names.push(item.name);
      costs[p] = cost(item.name);
      for (var k = 0; k < SUB; k++) {
        var c = item.cells[k], a = (c[3] || 0) / 255;
        var at = (p * SUB + k) * 3;
        labLinear(lin(c[0] * a + bg[0] * (1 - a)), lin(c[1] * a + bg[1] * (1 - a)), lin(c[2] * a + bg[2] * (1 - a)), lab, at);
        mean[p * 3] += lab[at] / SUB; mean[p * 3 + 1] += lab[at + 1] / SUB; mean[p * 3 + 2] += lab[at + 2] / SUB;
      }
    });
    var min = Infinity;
    for (var p = 0; p < n; p++) min = Math.min(min, costs[p]);
    return { names: names, lab: lab, mean: mean, cost: costs, size: n, minCost: n ? min : 0 };
  }

  /* RGBA pixels of a (cols*3) x (rows*3) image -> OKLab samples, cell by cell (cell k, sub-cell, channel). */
  function samples(rgba, cols, rows, bg) {
    bg = bg || BG;
    var w = cols * GRID, out = new Float32Array(cols * rows * SUB * 3);
    for (var y = 0; y < rows * GRID; y++) {
      for (var x = 0; x < w; x++) {
        var o = (y * w + x) * 4, a = rgba[o + 3] / 255;
        var k = ((y / GRID) | 0) * cols + ((x / GRID) | 0), sub = (y % GRID) * GRID + (x % GRID);
        labLinear(a >= 1 ? LIN[rgba[o]] : lin(rgba[o] * a + bg[0] * (1 - a)),
          a >= 1 ? LIN[rgba[o + 1]] : lin(rgba[o + 1] * a + bg[1] * (1 - a)),
          a >= 1 ? LIN[rgba[o + 2]] : lin(rgba[o + 2] * a + bg[2] * (1 - a)), out, (k * SUB + sub) * 3);
      }
    }
    return out;
  }

  /* Distance of every cell to every emoticon (no diffusion), reused to try several name-length penalties cheaply. */
  function distances(S, cells, P) {
    var D = new Float32Array(cells * P.size), N = SUB * 3;
    for (var k = 0; k < cells; k++) {
      var base = k * N;
      for (var p = 0; p < P.size; p++) {
        var pb = p * N, d = 0;
        for (var j = 0; j < N; j++) { var v = S[base + j] - P.lab[pb + j]; d += v * v; }
        D[k * P.size + p] = d;
      }
    }
    return D;
  }
  function charsFor(D, cells, rows, P, lambda) {
    var total = rows - 1;
    for (var k = 0; k < cells; k++) {
      var best = 0, bestScore = Infinity, row = k * P.size;
      for (var p = 0; p < P.size; p++) { var s = D[row + p] + lambda * P.cost[p]; if (s < bestScore) { bestScore = s; best = p; } }
      total += P.cost[best];
    }
    return total;
  }

  /* The mosaic: picks[k] = palette index. Serpentine Floyd-Steinberg on the cell means when `dither` is on. */
  function solve(S, cols, rows, P, lambda, dither) {
    var cells = cols * rows, N = SUB * 3, picks = new Int32Array(cells), err = new Float32Array(cells * 3), t = new Float32Array(N);
    var chars = rows - 1;
    for (var r = 0; r < rows; r++) {
      var back = dither && r % 2 === 1;
      for (var i = 0; i < cols; i++) {
        var c = back ? cols - 1 - i : i, k = r * cols + c, base = k * N;
        for (var j = 0; j < N; j++) t[j] = S[base + j] + err[k * 3 + (j % 3)];
        var best = 0, bestScore = Infinity;
        for (var p = 0; p < P.size; p++) {
          var pb = p * N, d = lambda * P.cost[p];
          for (var q = 0; q < N && d < bestScore; q++) { var v = t[q] - P.lab[pb + q]; d += v * v; }
          if (d < bestScore) { bestScore = d; best = p; }
        }
        picks[k] = best;
        chars += P.cost[best];
        if (!dither) continue;
        var step = back ? -1 : 1;
        for (var ch = 0; ch < 3; ch++) {
          var target = 0;
          for (var s = 0; s < SUB; s++) target += t[s * 3 + ch];
          // Damped and clamped: when the palette cannot reach a colour (no white emoticon, say) full diffusion
          // piles the error up and paints whole areas in the opposite colour.
          var e = Math.max(-0.12, Math.min(0.12, (target / SUB - P.mean[best * 3 + ch]) * 0.6));
          var cn = c + step;
          if (cn >= 0 && cn < cols) err[(r * cols + cn) * 3 + ch] += e * 7 / 16;
          if (r + 1 < rows) {
            var below = (r + 1) * cols;
            if (c - step >= 0 && c - step < cols) err[(below + c - step) * 3 + ch] += e * 3 / 16;
            err[(below + c) * 3 + ch] += e * 5 / 16;
            if (cn >= 0 && cn < cols) err[(below + cn) * 3 + ch] += e / 16;
          }
        }
      }
    }
    return { picks: picks, chars: chars, cols: cols, rows: rows };
  }

  function text(result, P) {
    var lines = [];
    for (var r = 0; r < result.rows; r++) {
      var line = '';
      for (var c = 0; c < result.cols; c++) line += 'ː' + P.names[result.picks[r * result.cols + c]] + 'ː';
      lines.push(line);
    }
    return lines.join('\n');
  }

  // Name-length penalties per character, mild enough that colour still decides; past the last one the width shrinks.
  var LAMBDAS = [0, 0.001, 0.003, 0.006, 0.012, 0.025];
  /* Largest mosaic up to `cols` that fits `budget` characters. sampler(cols, rows) -> OKLab samples. */
  function fit(sampler, wantCols, aspect, P, budget, dither) {
    var cols = Math.max(2, Math.min(MAX_COLS, wantCols, Math.floor(MAX_ROWS / Math.max(aspect, 1e-3))));
    for (var attempt = 0; attempt < 40 && cols >= 2; attempt++) {
      var rows = Math.max(1, Math.min(MAX_ROWS, Math.round(cols * aspect))), cells = cols * rows;
      var floor = cells * P.minCost + rows - 1;
      if (floor > budget) { cols = Math.min(cols - 1, Math.floor(cols * Math.sqrt(budget / floor))); continue; }
      var S = sampler(cols, rows), D = distances(S, cells, P), lambda = -1;
      for (var i = 0; i < LAMBDAS.length; i++) if (charsFor(D, cells, rows, P, LAMBDAS[i]) <= budget) { lambda = i; break; }
      if (lambda < 0) { cols -= 1; continue; }
      for (var j = lambda; j < LAMBDAS.length; j++) {
        var result = solve(S, cols, rows, P, LAMBDAS[j], dither);
        if (result.chars <= budget) { result.shrunk = cols < wantCols; result.shorter = j > 0; return result; }
      }
      cols -= 1;
    }
    return null;
  }

  var ENGINE = { GRID: GRID, CELL: CELL, MAX_COLS: MAX_COLS, MAX_ROWS: MAX_ROWS, BG: BG, palette: palette, samples: samples,
    solve: solve, fit: fit, text: text, parse: parse };

  /* Names from whatever was pasted: the JSON array Steam returns, or any text with :name: / ːnameː. */
  function parse(raw) {
    var found = [], seen = {};
    function add(name) { name = String(name || '').replace(/^[:ː]+|[:ː]+$/g, ''); if (/^[A-Za-z0-9_-]{1,60}$/.test(name) && !seen[name]) { seen[name] = 1; found.push(name); } }
    var source = String(raw || '').trim(), list = null;
    try { list = JSON.parse(source); } catch (_) {}
    if (Array.isArray(list)) list.forEach(function (item) { add(typeof item === 'string' ? item : item && item.name); });
    else source.replace(/[:ː]([A-Za-z0-9_-]{1,60})[:ː]/g, function (m, name) { add(name); return m; });
    return found;
  }

  if (typeof module !== 'undefined' && module.exports) { module.exports = ENGINE; return; }
  if (typeof document === 'undefined') return;

  // ---------------------------------------------------------------- UI
  var LANGS = ['en', 'ru', 'de', 'tr', 'fr', 'uk', 'es', 'pt'];
  var COPY = {
    en: { tool: 'Picture from emoticons', lead: 'Your picture is assembled from your own Steam emoticons, one emoticon per cell. Steam shows only the emoticons you own, so nobody else can post the same picture.',
      s1: '1. Your emoticons', how1: 'Open this Steam page while signed in to Steam:', how2: 'Select everything on it (Ctrl+A), copy it (Ctrl+C) and paste it here.',
      pastePh: 'Paste the page here: [":steamhappy:", ":steamsad:", …]', none: 'No emoticon names found. Copy the whole Steam page.', listKept: 'The list is kept only in this browser.',
      colors: 'Reading the colours: {done} of {n}…', ready: '{n} emoticons ready', missing: '{n} are not on Steam and were skipped', retry: 'Some emoticons could not be read. Try again later.',
      change: 'Change the list', s2: '2. Picture', pick: 'Choose a picture', sample: 'Try the sample', width: 'Width', dither: 'Smooth transitions',
      building: 'Building the picture…', chars: '{n} of {max} characters', used: '{n} different emoticons', size: '{cols} × {rows} emoticons',
      shrunk: 'Made narrower to fit Steam’s limit.', shorter: 'Emoticons with shorter names are preferred to fit the limit.', noFit: 'This does not fit Steam’s limit even at the smallest size. Shorten your text or use more emoticons.',
      insert: 'Add to the text', copy: 'Copy', copied: 'Copied ✓', palette: 'My emoticons ({n}): click one to leave it out', tooFew: 'Add at least 2 emoticons (you have {n}). With fewer than 30 the picture will be rough.',
      few: 'With fewer than 30 emoticons the picture will be rough.', failed: 'Could not read the emoticon colours. Try again.', realSize: 'Real size on Steam', tip: 'Simple pictures work best: logos, silhouettes, pixel art, big shapes.' },
    ru: { tool: 'Картина из смайликов', lead: 'Твоя картинка собирается из твоих же смайликов Steam, один смайлик на клетку. Steam показывает только смайлики, которые у тебя есть, поэтому такую же картину больше никто не поставит.',
      s1: '1. Твои смайлики', how1: 'Открой эту страницу Steam, войдя в свой аккаунт Steam:', how2: 'Выдели на ней всё (Ctrl+A), скопируй (Ctrl+C) и вставь сюда.',
      pastePh: 'Вставь страницу сюда: [":steamhappy:", ":steamsad:", …]', none: 'Названий смайликов не нашлось. Скопируй всю страницу Steam.', listKept: 'Список хранится только в этом браузере.',
      colors: 'Считываем цвета: {done} из {n}…', ready: 'Готово смайликов: {n}', missing: 'Не найдено в Steam и пропущено: {n}', retry: 'Часть смайликов не прочиталась. Попробуй позже.',
      change: 'Изменить список', s2: '2. Картинка', pick: 'Выбрать картинку', sample: 'Попробовать на примере', width: 'Ширина', dither: 'Плавные переходы',
      building: 'Собираем картину…', chars: '{n} из {max} символов', used: 'Разных смайликов: {n}', size: '{cols} × {rows} смайликов',
      shrunk: 'Сделали уже, чтобы уложиться в лимит Steam.', shorter: 'Чтобы уложиться в лимит, берём смайлики с короткими названиями.', noFit: 'Даже самая маленькая картина не влезает в лимит Steam. Сократи текст или добавь смайликов.',
      insert: 'Добавить в текст', copy: 'Скопировать', copied: 'Скопировано ✓', palette: 'Мои смайлики ({n}): нажми, чтобы не использовать', tooFew: 'Нужно хотя бы 2 смайлика (у тебя {n}). Если их меньше 30, картина выйдет грубой.',
      few: 'Если смайликов меньше 30, картина выйдет грубой.', failed: 'Не удалось прочитать цвета смайликов. Попробуй ещё раз.', realSize: 'Настоящий размер в Steam', tip: 'Лучше всего выходят простые картинки: логотипы, силуэты, пиксель-арт, крупные формы.' },
    de: { tool: 'Bild aus Emoticons', lead: 'Dein Bild wird aus deinen eigenen Steam-Emoticons zusammengesetzt, ein Emoticon pro Feld. Steam zeigt nur Emoticons, die du besitzt, also kann niemand sonst dasselbe Bild posten.',
      s1: '1. Deine Emoticons', how1: 'Öffne diese Steam-Seite, während du bei Steam angemeldet bist:', how2: 'Markiere alles darauf (Strg+A), kopiere es (Strg+C) und füge es hier ein.',
      pastePh: 'Seite hier einfügen: [":steamhappy:", ":steamsad:", …]', none: 'Keine Emoticon-Namen gefunden. Kopiere die ganze Steam-Seite.', listKept: 'Die Liste bleibt nur in diesem Browser.',
      colors: 'Farben werden gelesen: {done} von {n}…', ready: '{n} Emoticons bereit', missing: '{n} gibt es auf Steam nicht, sie wurden übersprungen', retry: 'Einige Emoticons konnten nicht gelesen werden. Versuch es später noch einmal.',
      change: 'Liste ändern', s2: '2. Bild', pick: 'Bild wählen', sample: 'Mit Beispiel testen', width: 'Breite', dither: 'Weiche Übergänge',
      building: 'Bild wird zusammengesetzt…', chars: '{n} von {max} Zeichen', used: '{n} verschiedene Emoticons', size: '{cols} × {rows} Emoticons',
      shrunk: 'Schmaler gemacht, damit es in das Steam-Limit passt.', shorter: 'Emoticons mit kürzeren Namen werden bevorzugt, damit es ins Limit passt.', noFit: 'Selbst in der kleinsten Größe passt es nicht ins Steam-Limit. Kürze deinen Text oder nutze mehr Emoticons.',
      insert: 'Zum Text hinzufügen', copy: 'Kopieren', copied: 'Kopiert ✓', palette: 'Meine Emoticons ({n}): anklicken, um eines auszulassen', tooFew: 'Füge mindestens 2 Emoticons hinzu (du hast {n}). Mit weniger als 30 wird das Bild grob.',
      few: 'Mit weniger als 30 Emoticons wird das Bild grob.', failed: 'Die Farben der Emoticons konnten nicht gelesen werden. Versuch es noch einmal.', realSize: 'Echte Größe auf Steam', tip: 'Am besten klappen einfache Bilder: Logos, Silhouetten, Pixel-Art, große Formen.' },
    tr: { tool: 'İfadelerden resim', lead: 'Resmin kendi Steam ifadelerinden oluşturulur, her hücreye bir ifade. Steam yalnızca sahip olduğun ifadeleri gösterir, bu yüzden aynı resmi başka kimse koyamaz.',
      s1: '1. İfadelerin', how1: 'Steam hesabına giriş yapmışken bu Steam sayfasını aç:', how2: 'Sayfadaki her şeyi seç (Ctrl+A), kopyala (Ctrl+C) ve buraya yapıştır.',
      pastePh: 'Sayfayı buraya yapıştır: [":steamhappy:", ":steamsad:", …]', none: 'İfade adı bulunamadı. Steam sayfasının tamamını kopyala.', listKept: 'Liste yalnızca bu tarayıcıda saklanır.',
      colors: 'Renkler okunuyor: {done} / {n}…', ready: '{n} ifade hazır', missing: '{n} ifade Steam’de yok, atlandı', retry: 'Bazı ifadeler okunamadı. Daha sonra tekrar dene.',
      change: 'Listeyi değiştir', s2: '2. Resim', pick: 'Resim seç', sample: 'Örnekle dene', width: 'Genişlik', dither: 'Yumuşak geçişler',
      building: 'Resim oluşturuluyor…', chars: '{n} / {max} karakter', used: '{n} farklı ifade', size: '{cols} × {rows} ifade',
      shrunk: 'Steam sınırına sığması için daraltıldı.', shorter: 'Sınıra sığması için kısa adlı ifadeler tercih ediliyor.', noFit: 'En küçük boyutta bile Steam sınırına sığmıyor. Metnini kısalt ya da daha fazla ifade kullan.',
      insert: 'Metne ekle', copy: 'Kopyala', copied: 'Kopyalandı ✓', palette: 'İfadelerim ({n}): kullanmamak için birine tıkla', tooFew: 'En az 2 ifade ekle ({n} ifaden var). 30’dan az ifadeyle resim kaba olur.',
      few: '30’dan az ifadeyle resim kaba olur.', failed: 'İfadelerin renkleri okunamadı. Tekrar dene.', realSize: 'Steam’deki gerçek boyut', tip: 'En iyi sonucu basit resimler verir: logolar, siluetler, piksel sanatı, büyük şekiller.' },
    fr: { tool: 'Image en émoticônes', lead: 'Ton image est assemblée avec tes propres émoticônes Steam, une émoticône par case. Steam n’affiche que les émoticônes que tu possèdes : personne d’autre ne peut publier la même image.',
      s1: '1. Tes émoticônes', how1: 'Ouvre cette page Steam en étant connecté à Steam :', how2: 'Sélectionne tout (Ctrl+A), copie (Ctrl+C) et colle ici.',
      pastePh: 'Colle la page ici : [":steamhappy:", ":steamsad:", …]', none: 'Aucun nom d’émoticône trouvé. Copie toute la page Steam.', listKept: 'La liste reste uniquement dans ce navigateur.',
      colors: 'Lecture des couleurs : {done} sur {n}…', ready: '{n} émoticônes prêtes', missing: '{n} n’existent pas sur Steam et ont été ignorées', retry: 'Certaines émoticônes n’ont pas pu être lues. Réessaie plus tard.',
      change: 'Modifier la liste', s2: '2. Image', pick: 'Choisir une image', sample: 'Essayer avec l’exemple', width: 'Largeur', dither: 'Transitions douces',
      building: 'Assemblage de l’image…', chars: '{n} sur {max} caractères', used: '{n} émoticônes différentes', size: '{cols} × {rows} émoticônes',
      shrunk: 'Rendue plus étroite pour tenir dans la limite de Steam.', shorter: 'Les émoticônes aux noms courts sont privilégiées pour tenir dans la limite.', noFit: 'Même à la plus petite taille, ça ne tient pas dans la limite de Steam. Raccourcis ton texte ou utilise plus d’émoticônes.',
      insert: 'Ajouter au texte', copy: 'Copier', copied: 'Copié ✓', palette: 'Mes émoticônes ({n}) : clique sur une pour l’exclure', tooFew: 'Ajoute au moins 2 émoticônes (tu en as {n}). Avec moins de 30, l’image sera grossière.',
      few: 'Avec moins de 30 émoticônes, l’image sera grossière.', failed: 'Impossible de lire les couleurs des émoticônes. Réessaie.', realSize: 'Taille réelle sur Steam', tip: 'Les images simples donnent le meilleur résultat : logos, silhouettes, pixel art, grandes formes.' },
    uk: { tool: 'Картина зі смайликів', lead: 'Твоя картинка збирається з твоїх власних смайликів Steam, один смайлик на клітинку. Steam показує лише смайлики, які в тебе є, тож таку саму картину більше ніхто не поставить.',
      s1: '1. Твої смайлики', how1: 'Відкрий цю сторінку Steam, увійшовши у свій акаунт Steam:', how2: 'Виділи на ній усе (Ctrl+A), скопіюй (Ctrl+C) і встав сюди.',
      pastePh: 'Встав сторінку сюди: [":steamhappy:", ":steamsad:", …]', none: 'Назв смайликів не знайдено. Скопіюй усю сторінку Steam.', listKept: 'Список зберігається лише в цьому браузері.',
      colors: 'Зчитуємо кольори: {done} з {n}…', ready: 'Готово смайликів: {n}', missing: 'Немає в Steam і пропущено: {n}', retry: 'Частину смайликів не вдалося прочитати. Спробуй пізніше.',
      change: 'Змінити список', s2: '2. Картинка', pick: 'Вибрати картинку', sample: 'Спробувати на прикладі', width: 'Ширина', dither: 'Плавні переходи',
      building: 'Збираємо картину…', chars: '{n} з {max} символів', used: 'Різних смайликів: {n}', size: '{cols} × {rows} смайликів',
      shrunk: 'Зробили вужчою, щоб умістити в ліміт Steam.', shorter: 'Щоб умістити в ліміт, беремо смайлики з короткими назвами.', noFit: 'Навіть найменша картина не вміщується в ліміт Steam. Скороти текст або додай смайликів.',
      insert: 'Додати в текст', copy: 'Скопіювати', copied: 'Скопійовано ✓', palette: 'Мої смайлики ({n}): натисни, щоб не використовувати', tooFew: 'Потрібно хоча б 2 смайлики (у тебе {n}). Якщо їх менше 30, картина вийде грубою.',
      few: 'Якщо смайликів менше 30, картина вийде грубою.', failed: 'Не вдалося прочитати кольори смайликів. Спробуй ще раз.', realSize: 'Справжній розмір у Steam', tip: 'Найкраще виходять прості картинки: логотипи, силуети, піксель-арт, великі форми.' },
    es: { tool: 'Imagen con emoticonos', lead: 'Tu imagen se arma con tus propios emoticonos de Steam, uno por casilla. Steam solo muestra los emoticonos que tienes, así que nadie más puede publicar la misma imagen.',
      s1: '1. Tus emoticonos', how1: 'Abre esta página de Steam con tu sesión de Steam iniciada:', how2: 'Selecciona todo (Ctrl+A), cópialo (Ctrl+C) y pégalo aquí.',
      pastePh: 'Pega la página aquí: [":steamhappy:", ":steamsad:", …]', none: 'No se encontraron nombres de emoticonos. Copia toda la página de Steam.', listKept: 'La lista se guarda solo en este navegador.',
      colors: 'Leyendo los colores: {done} de {n}…', ready: '{n} emoticonos listos', missing: '{n} no existen en Steam y se omitieron', retry: 'Algunos emoticonos no se pudieron leer. Inténtalo más tarde.',
      change: 'Cambiar la lista', s2: '2. Imagen', pick: 'Elegir imagen', sample: 'Probar con el ejemplo', width: 'Ancho', dither: 'Transiciones suaves',
      building: 'Armando la imagen…', chars: '{n} de {max} caracteres', used: '{n} emoticonos distintos', size: '{cols} × {rows} emoticonos',
      shrunk: 'Se hizo más estrecha para caber en el límite de Steam.', shorter: 'Se prefieren emoticonos con nombres cortos para caber en el límite.', noFit: 'Ni en el tamaño más pequeño cabe en el límite de Steam. Acorta tu texto o usa más emoticonos.',
      insert: 'Añadir al texto', copy: 'Copiar', copied: 'Copiado ✓', palette: 'Mis emoticonos ({n}): haz clic en uno para no usarlo', tooFew: 'Añade al menos 2 emoticonos (tienes {n}). Con menos de 30 la imagen saldrá tosca.',
      few: 'Con menos de 30 emoticonos la imagen saldrá tosca.', failed: 'No se pudieron leer los colores de los emoticonos. Inténtalo de nuevo.', realSize: 'Tamaño real en Steam', tip: 'Funcionan mejor las imágenes simples: logos, siluetas, pixel art, formas grandes.' },
    pt: { tool: 'Imagem de emoticons', lead: 'Sua imagem é montada com os seus próprios emoticons da Steam, um por casa. A Steam só mostra os emoticons que você tem, então ninguém mais pode postar a mesma imagem.',
      s1: '1. Seus emoticons', how1: 'Abra esta página da Steam com a sua conta da Steam conectada:', how2: 'Selecione tudo nela (Ctrl+A), copie (Ctrl+C) e cole aqui.',
      pastePh: 'Cole a página aqui: [":steamhappy:", ":steamsad:", …]', none: 'Nenhum nome de emoticon encontrado. Copie a página inteira da Steam.', listKept: 'A lista fica só neste navegador.',
      colors: 'Lendo as cores: {done} de {n}…', ready: '{n} emoticons prontos', missing: '{n} não existem na Steam e foram ignorados', retry: 'Alguns emoticons não puderam ser lidos. Tente mais tarde.',
      change: 'Mudar a lista', s2: '2. Imagem', pick: 'Escolher imagem', sample: 'Testar com o exemplo', width: 'Largura', dither: 'Transições suaves',
      building: 'Montando a imagem…', chars: '{n} de {max} caracteres', used: '{n} emoticons diferentes', size: '{cols} × {rows} emoticons',
      shrunk: 'Ficou mais estreita para caber no limite da Steam.', shorter: 'Emoticons com nomes curtos são preferidos para caber no limite.', noFit: 'Nem no menor tamanho cabe no limite da Steam. Encurte o seu texto ou use mais emoticons.',
      insert: 'Adicionar ao texto', copy: 'Copiar', copied: 'Copiado ✓', palette: 'Meus emoticons ({n}): clique em um para não usá-lo', tooFew: 'Adicione pelo menos 2 emoticons (você tem {n}). Com menos de 30 a imagem fica grosseira.',
      few: 'Com menos de 30 emoticons a imagem fica grosseira.', failed: 'Não foi possível ler as cores dos emoticons. Tente de novo.', realSize: 'Tamanho real na Steam', tip: 'Imagens simples funcionam melhor: logos, silhuetas, pixel art, formas grandes.' }
  };
  var LIST_URL = 'https://steamcommunity.com/actions/EmoticonList';
  var CDN = 'https://community.fastly.steamstatic.com/economy/emoticon/';
  var STORE_KEY = 'sm_infobox_emoticons';
  var SAMPLE = '/static/icon-256.png';   // a bold shape: detailed art turns to noise at 33 emoticons wide
  var BATCH = 400;

  function lang() { var l = window.SMLang && SMLang.get ? SMLang.get() : 'en'; return LANGS.indexOf(l) >= 0 ? l : 'en'; }
  function t(key, vars) {
    var text = COPY[lang()][key] || COPY.en[key] || key;
    Object.keys(vars || {}).forEach(function (k) { text = text.replace('{' + k + '}', vars[k]); });
    return text;
  }
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function button(cls, text, onClick) { var b = el('button', cls, text); b.type = 'button'; if (onClick) b.addEventListener('click', onClick); return b; }

  var store = { names: [], off: [] };
  try {
    var kept = JSON.parse(localStorage.getItem(STORE_KEY) || 'null');
    if (kept && Array.isArray(kept.names)) store = { names: parse(JSON.stringify(kept.names)), off: Array.isArray(kept.off) ? kept.off.map(String) : [] };
  } catch (_) {}
  function keep() { try { localStorage.setItem(STORE_KEY, JSON.stringify(store)); } catch (_) {} }

  // Colours live for the page session; the server keeps them for good.
  var colors = {}, missing = {}, failed = {}, loading = null, images = {};
  var ui = { img: null, cols: 33, dither: false, result: null, palette: null, refs: null, timer: 0, api: null };

  function loadColors(onProgress) {
    var todo = store.names.filter(function (n) { return !colors[n] && !missing[n]; });
    if (!todo.length) return Promise.resolve();
    if (loading) return loading;
    var done = store.names.length - todo.length, i = 0;
    failed = {};
    function next() {
      if (i >= todo.length) return Promise.resolve();
      var part = todo.slice(i, i + BATCH);
      i += BATCH;
      return fetch('/api/infobox/emoticons', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ names: part }) })
        .then(function (r) { return r.json().then(function (d) { if (!r.ok || !d.ok) throw Error('failed'); return d; }); })
        .then(function (d) {
          Object.keys(d.items || {}).forEach(function (n) { colors[n] = d.items[n]; });
          (d.missing || []).forEach(function (n) { missing[n] = 1; });
          (d.failed || []).forEach(function (n) { failed[n] = 1; });
          done += part.length;
          onProgress(done);
          return next();
        });
    }
    loading = next().then(function () { loading = null; }, function (e) { loading = null; throw e; });
    return loading;
  }

  function usable() { return store.names.filter(function (n) { return colors[n] && store.off.indexOf(n) < 0; }); }
  function image(name) {
    if (!images[name]) { var img = new Image(); img.decoding = 'async'; img.src = CDN + encodeURIComponent(name); images[name] = img; }
    return images[name];
  }

  /* The picture at (cols*3) x (rows*3), drawn in halving steps so every sample averages its whole area. */
  function sampler(img) {
    return function (cols, rows) {
      var w = cols * GRID, h = rows * GRID, src = img, sw = img.naturalWidth, sh = img.naturalHeight;
      while (sw / 2 >= w * 2 && sh / 2 >= h * 2) {
        var half = document.createElement('canvas');
        half.width = Math.round(sw / 2); half.height = Math.round(sh / 2);
        var hc = half.getContext('2d'); hc.imageSmoothingQuality = 'high'; hc.drawImage(src, 0, 0, half.width, half.height);
        src = half; sw = half.width; sh = half.height;
      }
      var canvas = document.createElement('canvas'); canvas.width = w; canvas.height = h;
      var ctx = canvas.getContext('2d', { willReadFrequently: true });
      ctx.imageSmoothingQuality = 'high';
      ctx.drawImage(src, 0, 0, w, h);
      return samples(ctx.getImageData(0, 0, w, h).data, cols, rows);
    };
  }

  function budget() {
    var api = ui.api, body = api ? api.body() : '';
    return Math.max(400, (api ? api.limit : 8000) - body.length - (body.trim() ? 2 : 0) - 40);
  }

  function schedule() {
    clearTimeout(ui.timer);
    if (!ui.refs) return;
    ui.refs.stats.textContent = ui.img ? t('building') : '';
    ui.timer = setTimeout(compute, 60);
  }
  function compute() {
    var refs = ui.refs;
    if (!refs || !refs.box.isConnected) return;
    var names = usable();
    refs.result.hidden = true;
    if (!ui.img || names.length < 2) { refs.stats.textContent = ''; return; }
    ui.palette = palette(names.map(function (n) { return { name: n, cells: colors[n] }; }));
    var aspect = ui.img.naturalHeight / ui.img.naturalWidth;
    var result = fit(sampler(ui.img), ui.cols, aspect, ui.palette, budget(), ui.dither);
    ui.result = result;
    if (!result) { refs.stats.textContent = t('noFit'); return; }
    var used = {};
    for (var k = 0; k < result.picks.length; k++) used[result.picks[k]] = 1;
    var notes = [t('size', { cols: result.cols, rows: result.rows }), t('chars', { n: result.chars, max: ui.api ? ui.api.limit : 8000 }), t('used', { n: Object.keys(used).length })];
    refs.stats.textContent = notes.join(' · ');
    var hints = [];
    if (result.shrunk) hints.push(t('shrunk'));
    if (result.shorter) hints.push(t('shorter'));
    if (names.length < 30) hints.push(t('few'));
    refs.hints.replaceChildren.apply(refs.hints, hints.map(function (h) { return el('li', '', h); }));
    refs.result.hidden = false;
    draw();
  }
  function draw() {
    var refs = ui.refs, result = ui.result, P = ui.palette;
    if (!refs || !result) return;
    var canvas = refs.canvas, ctx = canvas.getContext('2d');
    canvas.width = result.cols * CELL; canvas.height = result.rows * CELL;
    ctx.fillStyle = 'rgb(' + BG.join(',') + ')';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    var waiting = 0;
    for (var k = 0; k < result.picks.length; k++) {
      var img = image(P.names[result.picks[k]]);
      if (img.complete && img.naturalWidth) ctx.drawImage(img, (k % result.cols) * CELL, ((k / result.cols) | 0) * CELL, CELL, CELL);
      else if (!img.complete) { waiting++; img.addEventListener('load', redrawSoon, { once: true }); }
    }
    return waiting;
  }
  var redrawQueued = false;
  function redrawSoon() { if (redrawQueued) return; redrawQueued = true; requestAnimationFrame(function () { redrawQueued = false; draw(); }); }

  function paintPalette(details) {
    var grid = details.querySelector('.ibx-emo__palette');
    var names = store.names.filter(function (n) { return colors[n]; });
    details.querySelector('summary').textContent = t('palette', { n: names.length });
    if (!details.open) return;
    grid.replaceChildren();
    names.forEach(function (n) {
      var b = button('ibx-emo__chip' + (store.off.indexOf(n) >= 0 ? ' is-off' : ''), null, function () {
        var at = store.off.indexOf(n);
        if (at >= 0) store.off.splice(at, 1); else store.off.push(n);
        b.classList.toggle('is-off', at < 0);
        keep();
        schedule();
      });
      var img = el('img'); img.loading = 'lazy'; img.alt = ':' + n + ':'; img.width = img.height = CELL; img.src = CDN + encodeURIComponent(n);
      b.title = ':' + n + ':';
      b.append(img);
      grid.append(b);
    });
  }

  function panel(api) {
    ui.api = api;
    var box = el('div', 'ibx-emo');
    box.append(el('p', 'ibx-muted', t('lead')));

    // ---- 1. the list
    var src = el('section', 'ibx-emo__step');
    src.append(el('h4', 'ibx-emo__h', t('s1')));
    var how = el('ol', 'ibx-emo__how');
    var li1 = el('li', '', t('how1') + ' ');
    var link = el('a', '', 'steamcommunity.com/actions/EmoticonList ↗'); link.href = LIST_URL; link.target = '_blank'; link.rel = 'noopener noreferrer';
    li1.append(link);
    how.append(li1, el('li', '', t('how2')));
    var paste = el('textarea', 'ibx-area ibx-emo__paste'); paste.rows = 3; paste.placeholder = t('pastePh'); paste.spellcheck = false;
    var listMsg = el('p', 'ibx-emo__msg');
    var status = el('div', 'ibx-emo__status');
    var statusText = el('span', '');
    var change = button('ibx-btn ibx-btn--ghost ibx-btn--small', t('change'), function () { showPaste(true); paste.focus(); });
    status.append(statusText, change);
    var palette = el('details', 'ibx-emo__pal');
    palette.append(el('summary', ''), el('div', 'ibx-emo__palette'));
    palette.addEventListener('toggle', function () { paintPalette(palette); });
    src.append(how, paste, listMsg, status, palette, el('p', 'ibx-muted ibx-small', t('listKept')));

    function showPaste(on) { how.hidden = paste.hidden = !on; status.hidden = palette.hidden = on || !store.names.length; }
    function refreshList() {
      var ready = store.names.filter(function (n) { return colors[n]; }).length;
      var gone = store.names.filter(function (n) { return missing[n]; }).length;
      var parts = [t('ready', { n: ready })];
      if (gone) parts.push(t('missing', { n: gone }));
      if (Object.keys(failed).length) parts.push(t('retry'));
      statusText.textContent = '✓ ' + parts.join(' · ');
      paintPalette(palette);
    }
    function startList() {
      showPaste(false);
      listMsg.textContent = '';
      statusText.textContent = t('colors', { done: 0, n: store.names.length });
      loadColors(function (done) { statusText.textContent = t('colors', { done: done, n: store.names.length }); })
        .then(function () {
          refreshList();
          var n = usable().length;
          if (n < 2) listMsg.textContent = t('tooFew', { n: n });
          schedule();
        }, function () { statusText.textContent = t('failed'); });
    }
    paste.addEventListener('input', function () {
      var names = parse(paste.value);
      if (!names.length) { listMsg.textContent = paste.value.trim() ? t('none') : ''; return; }
      store.names = names;
      store.off = store.off.filter(function (n) { return names.indexOf(n) >= 0; });
      keep();
      paste.value = '';
      startList();
    });

    // ---- 2. the picture
    var pic = el('section', 'ibx-emo__step');
    pic.append(el('h4', 'ibx-emo__h', t('s2')));
    var input = el('input'); input.type = 'file'; input.accept = 'image/*'; input.hidden = true; input.dataset.smEnhanced = '1';
    var row = el('div', 'ibx-art__row');
    row.append(button('ibx-btn', '🖼 ' + t('pick'), function () { input.click(); }),
      button('ibx-btn ibx-btn--ghost', t('sample'), function () { useImage(SAMPLE); }));
    var controls = el('div', 'ibx-art__controls');
    var range = el('input'); range.type = 'range'; range.min = 6; range.max = MAX_COLS; range.value = ui.cols;
    var num = el('b', '', String(ui.cols));
    range.addEventListener('input', function () { ui.cols = Number(range.value); num.textContent = range.value; schedule(); });
    var widthRow = el('label', 'ibx-range'); widthRow.append(el('span', '', t('width')), range, num);
    var ditherRow = el('label', 'ibx-check'); var tick = el('input'); tick.type = 'checkbox'; tick.checked = ui.dither;
    tick.addEventListener('change', function () { ui.dither = tick.checked; schedule(); });
    ditherRow.append(tick, el('span', '', t('dither')));
    controls.append(widthRow, ditherRow);
    pic.append(el('p', 'ibx-muted', t('tip')), row, input, controls);
    function useImage(url, revoke) {
      var img = new Image();
      img.onload = function () { ui.img = img; if (revoke) URL.revokeObjectURL(url); schedule(); };
      img.src = url;
    }
    input.addEventListener('change', function () {
      var file = input.files && input.files[0];
      if (file) useImage(URL.createObjectURL(file), true);
      input.value = '';
    });

    // ---- result
    var stats = el('p', 'ibx-emo__stats');
    var result = el('div', 'ibx-emo__result');
    var frame = el('div', 'ibx-emo__frame');
    var canvas = el('canvas', 'ibx-emo__canvas');
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', t('tool'));
    frame.append(canvas);
    var hints = el('ul', 'ibx-emo__hints');
    var actions = el('div', 'ibx-art__row');
    var copyBtn = button('ibx-btn', '⧉ ' + t('copy'), function () { if (ui.result) api.copy(text(ui.result, ui.palette), copyBtn); });
    actions.append(button('ibx-btn ibx-btn--primary', t('insert'), function () {
      if (!ui.result) return;
      api.insert(text(ui.result, ui.palette));
      schedule();
    }), copyBtn);
    result.append(el('p', 'ibx-muted ibx-small ibx-emo__real', t('realSize')), frame, hints, actions);
    result.hidden = true;
    box.append(src, pic, stats, result);

    ui.refs = { box: box, stats: stats, result: result, canvas: canvas, hints: hints };
    showPaste(!store.names.length);
    if (store.names.length) startList();
    if (ui.img) schedule();
    return box;
  }

  window.SMInfoBoxEmoji = { label: function () { return t('tool'); }, panel: panel, engine: ENGINE,
    state: function () { return { names: store.names.length, ready: usable().length, result: ui.result && { cols: ui.result.cols, rows: ui.result.rows, chars: ui.result.chars } }; },
    text: function () { return ui.result ? text(ui.result, ui.palette) : ''; } };
})();
