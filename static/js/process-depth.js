/* "Depth" card of the Process tab, between "Choose the showcase" and "Style it" (owner, 2026-10-08). A still picture
   becomes a seamless 4 s loop: camera parallax, particles between depth layers, fog or a light band, focus pull,
   breathing (with a soft chest follow-through) and hair sway on strands the visitor paints.
   Everything is rendered by the server (smweb/depth_fx.py): POST /api/process/depth keeps the picture + its depth map
   and answers a token, POST /api/process/depth/render answers an animated WebP of the current options. The final
   files use the same code (processor.parallax_source), so the preview is what the visitor gets.
   window.SMDepthEditor.create(host, {picture}) is the reusable editor (also used by the Builder background);
   window.SMProcessDepth is the Process wiring that app.js reads (get() -> form field "parallax", active()).
   Copy: the keyed COPY dictionary below, 8 languages (checked by scripts/check_i18n.js). */
(function () {
  'use strict';
  var COPY = {
    en: { title: 'Depth (3D effect)', hint: 'The picture comes alive: depth, particles between the layers, haze, focus, breathing and hair. You get a seamless 4-second GIF.',
      on: 'Add depth', looks: 'Quick looks', lookSnow: 'Snowfall', lookSakura: 'Sakura', lookRain: 'Rainy night', lookCinema: 'Cinema', lookAlive: 'Living portrait', lookNight: 'Starry night',
      camera: 'Camera', none: 'None', orbit: 'Orbit', sway: 'Sway', float: 'Float', dolly: 'Zoom in', strength: 'Strength', focus: 'What stays still', near: 'near', far: 'far',
      particles: 'Particles between the layers', snow: 'Snow', sakura: 'Sakura', rain: 'Rain', sparks: 'Sparks', stars: 'Stars', amount: 'How many',
      atmosphere: 'Air', fog: 'Fog', light: 'Light beam', focuspull: 'Focus pull', focuspullHint: 'Sharpness moves from the far plane to the near one and back.',
      breath: 'Breathing', chest: 'Chest bounce', markBody: 'Mark the body', bodyHint: 'Paint over what should breathe: the chest and shoulders. Paint nothing and the body is found automatically.',
      hair: 'Hair sway', hairTip: 'Works best on hair that is clearly visible: loose behind the back or at the sides. Better not paint the fringe or strands over the face.', markHair: 'Paint the hair', brush: 'Brush', undo: 'Undo', clear: 'Clear', hairHint: 'Paint over the strands that should sway, from the roots to the tips.',
      hairEmpty: 'Paint the hair so it can sway.', done: 'Done', loading: 'Building the depth map…', rendering: 'Updating the preview…',
      noFile: 'Add a picture to see the preview.', notStill: 'Depth works with pictures (PNG, JPG, WebP). GIFs and videos already move.',
      unavailable: 'Depth is not available right now. Try again later.', failed: 'Could not build the preview for this picture.',
      nothing: 'Pick at least one effect.', chip: 'Depth: {motion}', isNew: 'NEW', previewNote: 'Preview is simplified (smaller, fewer frames): the finished animation will be sharper and smoother.' },
    ru: { title: 'Объём (3D-эффект)', hint: 'Картинка оживает: объём, частицы между слоями, туман, фокус, дыхание и волосы. Получается бесшовная GIF на 4 секунды.',
      on: 'Добавить объём', looks: 'Быстрый выбор', lookSnow: 'Снегопад', lookSakura: 'Сакура', lookRain: 'Дождливая ночь', lookCinema: 'Кино', lookAlive: 'Живой портрет', lookNight: 'Звёздная ночь',
      camera: 'Камера', none: 'Нет', orbit: 'Облёт', sway: 'Покачивание', float: 'Парение', dolly: 'Наезд', strength: 'Сила', focus: 'Что стоит на месте', near: 'ближнее', far: 'дальнее',
      particles: 'Частицы между слоями', snow: 'Снег', sakura: 'Сакура', rain: 'Дождь', sparks: 'Искры', stars: 'Звёзды', amount: 'Сколько',
      atmosphere: 'Воздух', fog: 'Туман', light: 'Луч света', focuspull: 'Перевод фокуса', focuspullHint: 'Резкость переходит с дальнего плана на ближний и обратно.',
      breath: 'Дыхание', chest: 'Покачивание груди', markBody: 'Указать корпус', bodyHint: 'Закрась кистью то, что должно дышать: грудь и плечи. Если ничего не закрашивать, корпус найдётся сам.',
      hair: 'Волосы на ветру', hairTip: 'Лучше всего качаются волосы, которые хорошо видны: распущенные за спиной или по бокам. Чёлку и пряди на лице лучше не закрашивать.', markHair: 'Закрасить волосы', brush: 'Кисть', undo: 'Отменить', clear: 'Очистить', hairHint: 'Закрась кистью пряди, которые должны качаться, от корней до кончиков.',
      hairEmpty: 'Закрась волосы, чтобы они качались.', done: 'Готово', loading: 'Строим карту глубины…', rendering: 'Обновляем превью…',
      noFile: 'Добавь картинку, чтобы увидеть превью.', notStill: 'Объём работает с картинками (PNG, JPG, WebP). GIF и видео и так двигаются.',
      unavailable: 'Объём сейчас недоступен. Попробуй позже.', failed: 'Не получилось построить превью для этой картинки.',
      nothing: 'Выбери хотя бы один эффект.', chip: 'Объём: {motion}', isNew: 'НОВОЕ', previewNote: 'Превью упрощено (меньше размер и кадров): готовая анимация будет чётче и плавнее.' },
    de: { title: 'Tiefe (3D-Effekt)', hint: 'Das Bild wird lebendig: Tiefe, Partikel zwischen den Ebenen, Dunst, Fokus, Atmen und Haare. Du bekommst ein nahtloses 4-Sekunden-GIF.',
      on: 'Tiefe hinzufügen', looks: 'Schnellauswahl', lookSnow: 'Schneefall', lookSakura: 'Sakura', lookRain: 'Regennacht', lookCinema: 'Kino', lookAlive: 'Lebendiges Porträt', lookNight: 'Sternennacht',
      camera: 'Kamera', none: 'Keine', orbit: 'Umkreisen', sway: 'Schwenken', float: 'Schweben', dolly: 'Heranzoomen', strength: 'Stärke', focus: 'Was stillsteht', near: 'nah', far: 'fern',
      particles: 'Partikel zwischen den Ebenen', snow: 'Schnee', sakura: 'Sakura', rain: 'Regen', sparks: 'Funken', stars: 'Sterne', amount: 'Wie viele',
      atmosphere: 'Luft', fog: 'Nebel', light: 'Lichtstrahl', focuspull: 'Schärfeverlagerung', focuspullHint: 'Die Schärfe wandert von hinten nach vorne und zurück.',
      breath: 'Atmen', chest: 'Brustwippen', markBody: 'Oberkörper markieren', bodyHint: 'Male über das, was atmen soll: Brust und Schultern. Malst du nichts, wird der Oberkörper automatisch erkannt.',
      hair: 'Haare im Wind', hairTip: 'Am besten wirkt es bei gut sichtbaren Haaren: offen hinter dem Rücken oder an den Seiten. Pony und Strähnen über dem Gesicht besser nicht bemalen.', markHair: 'Haare bemalen', brush: 'Pinsel', undo: 'Rückgängig', clear: 'Leeren', hairHint: 'Male über die Strähnen, die schwingen sollen, vom Ansatz bis zu den Spitzen.',
      hairEmpty: 'Male die Haare an, damit sie schwingen.', done: 'Fertig', loading: 'Tiefenkarte wird erstellt…', rendering: 'Vorschau wird aktualisiert…',
      noFile: 'Füge ein Bild hinzu, um die Vorschau zu sehen.', notStill: 'Tiefe funktioniert mit Bildern (PNG, JPG, WebP). GIFs und Videos bewegen sich schon.',
      unavailable: 'Tiefe ist gerade nicht verfügbar. Versuche es später.', failed: 'Für dieses Bild konnte keine Vorschau erstellt werden.',
      nothing: 'Wähle mindestens einen Effekt.', chip: 'Tiefe: {motion}', isNew: 'NEU', previewNote: 'Die Vorschau ist vereinfacht (kleiner, weniger Bilder): die fertige Animation wird schärfer und flüssiger.' },
    tr: { title: 'Derinlik (3D efekt)', hint: 'Resim canlanır: derinlik, katmanlar arasında parçacıklar, sis, odak, nefes ve saçlar. Kusursuz döngülü 4 saniyelik bir GIF elde edersin.',
      on: 'Derinlik ekle', looks: 'Hızlı seçim', lookSnow: 'Kar yağışı', lookSakura: 'Sakura', lookRain: 'Yağmurlu gece', lookCinema: 'Sinema', lookAlive: 'Canlı portre', lookNight: 'Yıldızlı gece',
      camera: 'Kamera', none: 'Yok', orbit: 'Çevrele', sway: 'Salınım', float: 'Süzül', dolly: 'Yakınlaş', strength: 'Güç', focus: 'Sabit kalan', near: 'yakın', far: 'uzak',
      particles: 'Katmanlar arasında parçacıklar', snow: 'Kar', sakura: 'Sakura', rain: 'Yağmur', sparks: 'Kıvılcımlar', stars: 'Yıldızlar', amount: 'Ne kadar',
      atmosphere: 'Hava', fog: 'Sis', light: 'Işık huzmesi', focuspull: 'Odak kaydırma', focuspullHint: 'Netlik uzak plandan yakın plana geçer ve geri döner.',
      breath: 'Nefes', chest: 'Göğüs salınımı', markBody: 'Gövdeyi işaretle', bodyHint: 'Nefes alması gereken yeri boya: göğüs ve omuzlar. Hiçbir şey boyamazsan gövde otomatik bulunur.',
      hair: 'Rüzgarda saçlar', hairTip: 'En iyi sonuç iyi görünen saçlarda olur: sırtta ya da yanlarda açık saçlar. Kâküle ve yüzün üstündeki tutamlara boya sürmemek daha iyi.', markHair: 'Saçları boya', brush: 'Fırça', undo: 'Geri al', clear: 'Temizle', hairHint: 'Sallanması gereken tutamları kökten uca kadar fırçayla boya.',
      hairEmpty: 'Sallanmaları için saçları boya.', done: 'Tamam', loading: 'Derinlik haritası oluşturuluyor…', rendering: 'Önizleme güncelleniyor…',
      noFile: 'Önizlemeyi görmek için bir resim ekle.', notStill: 'Derinlik resimlerle çalışır (PNG, JPG, WebP). GIF ve videolar zaten hareketli.',
      unavailable: 'Derinlik şu an kullanılamıyor. Daha sonra tekrar dene.', failed: 'Bu resim için önizleme oluşturulamadı.',
      nothing: 'En az bir efekt seç.', chip: 'Derinlik: {motion}', isNew: 'YENİ', previewNote: 'Önizleme sadeleştirilmiştir (daha küçük, daha az kare): bitmiş animasyon daha net ve akıcı olur.' },
    fr: { title: 'Profondeur (effet 3D)', hint: 'L’image prend vie : profondeur, particules entre les plans, brume, mise au point, respiration et cheveux. Tu obtiens un GIF de 4 secondes qui boucle sans coupure.',
      on: 'Ajouter de la profondeur', looks: 'Choix rapide', lookSnow: 'Chute de neige', lookSakura: 'Sakura', lookRain: 'Nuit pluvieuse', lookCinema: 'Cinéma', lookAlive: 'Portrait vivant', lookNight: 'Nuit étoilée',
      camera: 'Caméra', none: 'Aucun', orbit: 'Orbite', sway: 'Balancement', float: 'Flottement', dolly: 'Zoom avant', strength: 'Intensité', focus: 'Ce qui reste fixe', near: 'proche', far: 'lointain',
      particles: 'Particules entre les plans', snow: 'Neige', sakura: 'Sakura', rain: 'Pluie', sparks: 'Étincelles', stars: 'Étoiles', amount: 'Quantité',
      atmosphere: 'Air', fog: 'Brouillard', light: 'Rayon de lumière', focuspull: 'Bascule de mise au point', focuspullHint: 'La netteté passe du plan lointain au plan proche, puis revient.',
      breath: 'Respiration', chest: 'Rebond de la poitrine', markBody: 'Indiquer le buste', bodyHint: 'Peins ce qui doit respirer : la poitrine et les épaules. Si tu ne peins rien, le buste est trouvé automatiquement.',
      hair: 'Cheveux au vent', hairTip: 'Ça marche le mieux sur des cheveux bien visibles : lâchés dans le dos ou sur les côtés. Mieux vaut ne pas peindre la frange ni les mèches sur le visage.', markHair: 'Peindre les cheveux', brush: 'Pinceau', undo: 'Annuler', clear: 'Effacer', hairHint: 'Peins les mèches qui doivent bouger, des racines aux pointes.',
      hairEmpty: 'Peins les cheveux pour qu’ils bougent.', done: 'Terminé', loading: 'Création de la carte de profondeur…', rendering: 'Mise à jour de l’aperçu…',
      noFile: 'Ajoute une image pour voir l’aperçu.', notStill: 'La profondeur fonctionne avec les images (PNG, JPG, WebP). Les GIF et vidéos bougent déjà.',
      unavailable: 'La profondeur n’est pas disponible pour le moment. Réessaie plus tard.', failed: 'Impossible de créer l’aperçu de cette image.',
      nothing: 'Choisis au moins un effet.', chip: 'Profondeur : {motion}', isNew: 'NOUVEAU', previewNote: 'L’aperçu est simplifié (plus petit, moins d’images) : l’animation finale sera plus nette et plus fluide.' },
    uk: { title: 'Обʼєм (3D-ефект)', hint: 'Картинка оживає: обʼєм, частинки між шарами, туман, фокус, дихання й волосся. Виходить безшовна GIF на 4 секунди.',
      on: 'Додати обʼєм', looks: 'Швидкий вибір', lookSnow: 'Снігопад', lookSakura: 'Сакура', lookRain: 'Дощова ніч', lookCinema: 'Кіно', lookAlive: 'Живий портрет', lookNight: 'Зоряна ніч',
      camera: 'Камера', none: 'Немає', orbit: 'Обліт', sway: 'Погойдування', float: 'Ширяння', dolly: 'Наїзд', strength: 'Сила', focus: 'Що стоїть на місці', near: 'ближнє', far: 'дальнє',
      particles: 'Частинки між шарами', snow: 'Сніг', sakura: 'Сакура', rain: 'Дощ', sparks: 'Іскри', stars: 'Зорі', amount: 'Скільки',
      atmosphere: 'Повітря', fog: 'Туман', light: 'Промінь світла', focuspull: 'Переведення фокуса', focuspullHint: 'Різкість переходить з дальнього плану на ближній і назад.',
      breath: 'Дихання', chest: 'Погойдування грудей', markBody: 'Вказати корпус', bodyHint: 'Зафарбуй пензлем те, що має дихати: груди й плечі. Якщо нічого не зафарбувати, корпус знайдеться сам.',
      hair: 'Волосся на вітрі', hairTip: 'Найкраще гойдається волосся, яке добре видно: розпущене за спиною або з боків. Чубчик і пасма на обличчі краще не зафарбовувати.', markHair: 'Зафарбувати волосся', brush: 'Пензель', undo: 'Скасувати', clear: 'Очистити', hairHint: 'Зафарбуй пензлем пасма, які мають гойдатися, від коренів до кінчиків.',
      hairEmpty: 'Зафарбуй волосся, щоб воно гойдалося.', done: 'Готово', loading: 'Будуємо карту глибини…', rendering: 'Оновлюємо превʼю…',
      noFile: 'Додай картинку, щоб побачити превʼю.', notStill: 'Обʼєм працює з картинками (PNG, JPG, WebP). GIF і відео й так рухаються.',
      unavailable: 'Обʼєм зараз недоступний. Спробуй пізніше.', failed: 'Не вдалося побудувати превʼю для цієї картинки.',
      nothing: 'Обери хоча б один ефект.', chip: 'Обʼєм: {motion}', isNew: 'НОВЕ', previewNote: 'Превʼю спрощене (менший розмір і менше кадрів): готова анімація буде чіткішою та плавнішою.' },
    es: { title: 'Profundidad (efecto 3D)', hint: 'La imagen cobra vida: profundidad, partículas entre capas, niebla, enfoque, respiración y cabello. Obtienes un GIF de 4 segundos que se repite sin cortes.',
      on: 'Añadir profundidad', looks: 'Elección rápida', lookSnow: 'Nevada', lookSakura: 'Sakura', lookRain: 'Noche lluviosa', lookCinema: 'Cine', lookAlive: 'Retrato vivo', lookNight: 'Noche estrellada',
      camera: 'Cámara', none: 'Nada', orbit: 'Órbita', sway: 'Balanceo', float: 'Flotar', dolly: 'Acercar', strength: 'Intensidad', focus: 'Lo que queda quieto', near: 'cerca', far: 'lejos',
      particles: 'Partículas entre capas', snow: 'Nieve', sakura: 'Sakura', rain: 'Lluvia', sparks: 'Chispas', stars: 'Estrellas', amount: 'Cantidad',
      atmosphere: 'Aire', fog: 'Niebla', light: 'Haz de luz', focuspull: 'Cambio de enfoque', focuspullHint: 'La nitidez pasa del plano lejano al cercano y vuelve.',
      breath: 'Respiración', chest: 'Rebote del pecho', markBody: 'Marcar el torso', bodyHint: 'Pinta lo que debe respirar: el pecho y los hombros. Si no pintas nada, el torso se detecta automáticamente.',
      hair: 'Cabello al viento', hairTip: 'Funciona mejor con cabello bien visible: suelto a la espalda o a los lados. Mejor no pintar el flequillo ni los mechones sobre la cara.', markHair: 'Pintar el cabello', brush: 'Pincel', undo: 'Deshacer', clear: 'Borrar', hairHint: 'Pinta los mechones que deben moverse, de la raíz a las puntas.',
      hairEmpty: 'Pinta el cabello para que se mueva.', done: 'Listo', loading: 'Creando el mapa de profundidad…', rendering: 'Actualizando la vista previa…',
      noFile: 'Añade una imagen para ver la vista previa.', notStill: 'La profundidad funciona con imágenes (PNG, JPG, WebP). Los GIF y vídeos ya se mueven.',
      unavailable: 'La profundidad no está disponible ahora. Inténtalo más tarde.', failed: 'No se pudo crear la vista previa de esta imagen.',
      nothing: 'Elige al menos un efecto.', chip: 'Profundidad: {motion}', isNew: 'NUEVO', previewNote: 'La vista previa está simplificada (más pequeña, menos fotogramas): la animación final será más nítida y fluida.' },
    pt: { title: 'Profundidade (efeito 3D)', hint: 'A imagem ganha vida: profundidade, partículas entre camadas, névoa, foco, respiração e cabelo. Você recebe um GIF de 4 segundos em loop perfeito.',
      on: 'Adicionar profundidade', looks: 'Escolha rápida', lookSnow: 'Nevasca', lookSakura: 'Sakura', lookRain: 'Noite chuvosa', lookCinema: 'Cinema', lookAlive: 'Retrato vivo', lookNight: 'Noite estrelada',
      camera: 'Câmera', none: 'Nada', orbit: 'Órbita', sway: 'Balanço', float: 'Flutuar', dolly: 'Aproximar', strength: 'Intensidade', focus: 'O que fica parado', near: 'perto', far: 'longe',
      particles: 'Partículas entre camadas', snow: 'Neve', sakura: 'Sakura', rain: 'Chuva', sparks: 'Faíscas', stars: 'Estrelas', amount: 'Quantidade',
      atmosphere: 'Ar', fog: 'Névoa', light: 'Feixe de luz', focuspull: 'Troca de foco', focuspullHint: 'A nitidez passa do plano distante para o próximo e volta.',
      breath: 'Respiração', chest: 'Balanço do peito', markBody: 'Marcar o tronco', bodyHint: 'Pinte o que deve respirar: o peito e os ombros. Se não pintar nada, o tronco é encontrado automaticamente.',
      hair: 'Cabelo ao vento', hairTip: 'Funciona melhor com cabelo bem visível: solto nas costas ou nos lados. Melhor não pintar a franja nem as mechas sobre o rosto.', markHair: 'Pintar o cabelo', brush: 'Pincel', undo: 'Desfazer', clear: 'Limpar', hairHint: 'Pinte as mechas que devem balançar, da raiz às pontas.',
      hairEmpty: 'Pinte o cabelo para ele balançar.', done: 'Pronto', loading: 'Criando o mapa de profundidade…', rendering: 'Atualizando a prévia…',
      noFile: 'Adicione uma imagem para ver a prévia.', notStill: 'A profundidade funciona com imagens (PNG, JPG, WebP). GIFs e vídeos já se movem.',
      unavailable: 'A profundidade não está disponível agora. Tente mais tarde.', failed: 'Não foi possível criar a prévia desta imagem.',
      nothing: 'Escolha pelo menos um efeito.', chip: 'Profundidade: {motion}', isNew: 'NOVO', previewNote: 'A prévia é simplificada (menor, menos quadros): a animação final ficará mais nítida e fluida.' }
  };
  var CAMERAS = ['none', 'orbit', 'sway', 'float', 'dolly'];
  var PARTICLES = ['none', 'snow', 'sakura', 'rain', 'sparks', 'stars'];
  var AIRS = ['none', 'fog', 'light'];
  var LOOKS = {
    lookSnow: { camera: 'sway', strength: 1, particles: 'snow', amount: 2, atmosphere: 'none', focuspull: false },
    lookSakura: { camera: 'orbit', strength: 1, particles: 'sakura', amount: 2, atmosphere: 'none', focuspull: false },
    lookRain: { camera: 'none', particles: 'rain', amount: 3, atmosphere: 'fog', focuspull: false },
    lookCinema: { camera: 'dolly', strength: 1.5, particles: 'none', atmosphere: 'light', focuspull: true },
    lookAlive: { camera: 'float', strength: 0.8, particles: 'none', atmosphere: 'none', focuspull: false, breath: true, hair: true },
    lookNight: { camera: 'orbit', strength: 1, particles: 'stars', amount: 2, atmosphere: 'fog', focuspull: false }
  };
  var MAX_STROKES = 600;

  function lang() { var l = window.SMLang && SMLang.get ? SMLang.get() : 'en'; return COPY[l] ? l : 'en'; }
  function t(key, vars) {
    var text = (COPY[lang()] || COPY.en)[key] || COPY.en[key] || key;
    Object.keys(vars || {}).forEach(function (k) { text = text.replace('{' + k + '}', vars[k]); });
    return text;
  }
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }

  // ================================================================ the editor (reusable)
  function create(host, hooks) {
    hooks = hooks || {};
    var o = {
      camera: 'orbit', strength: 1.5, focus: 0.5, particles: 'none', amount: 2, atmosphere: 'none', focuspull: false,
      breath: false, breathStrength: 1.5, chest: 1, region: null, bodyStrokes: [], hair: false, hairStrength: 1.5, strokes: [], brush: 0.025
    };
    var pic = { token: '', canvas: null, guess: null, status: '', busy: false };
    var mode = '';                 // '' | 'body' | 'hair'
    var refs = {}, renderTimer = 0, renderSeq = 0, previewUrl = '';

    function options() {
      return {
        camera: { motion: o.camera, strength: o.strength }, focus: o.focus,
        particles: o.particles === 'none' ? null : { kind: o.particles, amount: o.amount },
        atmosphere: o.atmosphere, focuspull: o.focuspull,
        breath: o.breath ? { on: true, strength: o.breathStrength, chest: o.chest, region: o.region || pic.guess || { cx: 0.5, cy: 0.55, rx: 0.16, ry: 0.14 },
          strokes: o.bodyStrokes.length ? o.bodyStrokes : undefined } : null,
        hair: o.hair && o.strokes.length ? { on: true, strength: o.hairStrength, strokes: o.strokes } : null
      };
    }
    function hasEffect() {
      return o.camera !== 'none' || o.particles !== 'none' || o.atmosphere !== 'none' || o.focuspull || o.breath || (o.hair && o.strokes.length);
    }
    function names() {
      var list = [];
      if (o.camera !== 'none') list.push(t(o.camera));
      if (o.particles !== 'none') list.push(t(o.particles));
      if (o.atmosphere !== 'none') list.push(t(o.atmosphere));
      if (o.focuspull) list.push(t('focuspull'));
      if (o.breath) list.push(t('breath'));
      if (o.hair && o.strokes.length) list.push(t('hair'));
      return list;
    }

    // ---- status and preview
    function setStatus(text, busy) {
      pic.status = text; pic.busy = !!busy;
      if (!refs.status) return;
      refs.status.textContent = text;
      refs.status.hidden = !text;
      refs.status.classList.toggle('is-busy', !!busy);
      refs.stage.classList.toggle('has-preview', !!previewUrl);
    }
    function schedule() {
      clearTimeout(renderTimer);
      if (!pic.token || mode) return;
      if (!hasEffect()) { setStatus(t('nothing')); return; }
      renderTimer = setTimeout(render, 380);
    }
    function render() {
      var seq = ++renderSeq;
      setStatus(t('rendering'), true);
      fetch('/api/process/depth/render', {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: pic.token, options: options(), size: hooks.largePreview ? 'large' : undefined })
      }).then(function (r) {
        if (r.status === 404) throw new Error('expired');
        if (!r.ok) throw new Error('failed');
        return r.blob();
      }).then(function (blob) {
        if (seq !== renderSeq) return;
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        previewUrl = URL.createObjectURL(blob);
        refs.img.src = previewUrl;
        setStatus('');
      }).catch(function (error) {
        if (seq !== renderSeq) return;
        if (error && error.message === 'expired' && pic.canvas) { prepare(pic.canvas); return; }
        setStatus(t('failed'));
      });
    }
    function changed() { schedule(); if (hooks.onChange) hooks.onChange(); }

    // ---- picture -> token (depth map on the server)
    function prepare(canvas) {
      var seq = ++renderSeq;
      pic.token = ''; pic.canvas = canvas;
      if (previewUrl) { URL.revokeObjectURL(previewUrl); previewUrl = ''; refs.img.removeAttribute('src'); }
      sizeView();
      if (!canvas) { setStatus(t('noFile')); return; }
      setStatus(t('loading'), true);
      new Promise(function (resolve) { canvas.toBlob(resolve, 'image/png'); }).then(function (blob) {
        var form = new FormData(); form.append('file', blob, 'depth.png');
        // The Builder background asks the server to keep a big copy for its full-size loop (/api/process/depth/clip).
        if (hooks.keepSource) form.append('keep', '1');
        return fetch('/api/process/depth', { method: 'POST', body: form, credentials: 'include' });
      }).then(function (r) {
        if (r.status === 503) return r.json().then(function (d) { throw new Error(d && d.code === 'depth_unavailable' ? 'unavailable' : 'failed'); });
        if (!r.ok) throw new Error('failed');
        return r.json();
      }).then(function (data) {
        if (seq !== renderSeq) return;
        pic.token = data.token; pic.guess = data.body || null;
        setStatus('');
        drawOverlay();
        schedule();
      }).catch(function (error) {
        if (seq !== renderSeq) return;
        setStatus(t(error && error.message === 'unavailable' ? 'unavailable' : 'failed'));
      });
    }
    function sizeView() {
      if (!refs.view) return;
      var c = pic.canvas, stage = refs.stage;
      var ratio = c ? c.width / c.height : 16 / 9;
      refs.view.style.aspectRatio = c ? c.width + ' / ' + c.height : '16 / 9';
      // The picture gets a width in pixels: a percentage width made the grid size its row for a different height and
      // the picture covered the brush bar. Height cap: 380 px in the Process card; with hooks.fitHeight (the Builder
      // window on wide screens) whatever the stage column has left under the marking bar, so painting has room.
      var cs = getComputedStyle(stage);
      var innerW = stage.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
      var maxH = 380;
      if (hooks.fitHeight) {
        if (window.matchMedia('(min-width: 900px)').matches) {
          maxH = stage.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
          if (!refs.markBar.hidden) maxH -= refs.markBar.offsetHeight + (parseFloat(cs.rowGap) || 0);
          if (refs.previewNote && !refs.previewNote.hidden) maxH -= refs.previewNote.offsetHeight + (parseFloat(cs.rowGap) || 0);
        } else maxH = Math.min(window.innerHeight * 0.55, 520);
        maxH = Math.max(220, maxH);
      }
      refs.view.style.width = innerW > 0 ? Math.floor(Math.min(innerW, maxH * ratio)) + 'px'
        : (c ? 'min(100%, ' + Math.round(maxH * ratio) + 'px)' : '100%');
      if (c && refs.still.dataset.drawn !== String(c.width + 'x' + c.height + ':' + pic.token)) {
        refs.still.width = c.width; refs.still.height = c.height;
        refs.still.getContext('2d').drawImage(c, 0, 0);
        refs.still.dataset.drawn = c.width + 'x' + c.height + ':' + pic.token;
      }
    }
    var resizeWatch = null, resizeQueued = false;
    function watchSize(stage) {
      if (resizeWatch) resizeWatch.disconnect();
      if (!window.ResizeObserver) return;
      resizeWatch = new ResizeObserver(function () {
        if (resizeQueued) return;
        resizeQueued = true;
        requestAnimationFrame(function () { resizeQueued = false; sizeView(); });
      });
      resizeWatch.observe(stage);
    }

    // ---- marking: painted body and hair (owner, 2026-10-08: the body box was clumsy, both are a brush now)
    function marks() { return mode === 'body' ? o.bodyStrokes : o.strokes; }
    function drawOverlay() {
      // "Paint the hair" is only a hint for an empty mask.
      if (refs.hairNote) refs.hairNote.hidden = o.strokes.length > 0;
      var cv = refs.overlay; if (!cv) return;
      var rect = refs.view.getBoundingClientRect();
      var dpr = Math.min(2, window.devicePixelRatio || 1);
      cv.width = Math.max(1, Math.round(rect.width * dpr)); cv.height = Math.max(1, Math.round(rect.height * dpr));
      var ctx = cv.getContext('2d'); ctx.clearRect(0, 0, cv.width, cv.height);
      if (!mode) return;
      var W = cv.width, H = cv.height;
      ctx.fillStyle = mode === 'body' ? 'rgba(95,242,181,.4)' : 'rgba(31,201,241,.42)';
      marks().forEach(function (s) { ctx.beginPath(); ctx.arc(s[0] * W, s[1] * H, s[2] * W, 0, Math.PI * 2); ctx.fill(); });
      // No outline of the automatic body (owner: it looked draggable and was not); only the brush.
    }
    function point(event) {
      var rect = refs.overlay.getBoundingClientRect();
      return { x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)), y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)), w: rect.width };
    }
    var drag = null;
    function onDown(event) {
      if (!mode || !pic.canvas) return;
      event.preventDefault();
      refs.overlay.setPointerCapture(event.pointerId);
      var p = point(event);
      drag = { start: p, last: null, strokeStart: marks().length, list: marks() };
      onMove(event);
    }
    function onMove(event) {
      if (!drag) return;
      var p = point(event);
      var gap = o.brush * 0.5;
      if (!drag.last || Math.hypot(p.x - drag.last.x, (p.y - drag.last.y) * pic.canvas.height / pic.canvas.width) >= gap) {
        if (drag.list.length < MAX_STROKES) drag.list.push([round4(p.x), round4(p.y), o.brush]);
        drag.last = p;
      }
      drawOverlay();
    }
    function onUp() {
      if (!drag) return;
      if (drag.list.length > drag.strokeStart) undoStack.push([drag.list, drag.strokeStart]);
      drag = null;
      if (hooks.onChange) hooks.onChange();
    }
    var undoStack = [];
    function round4(v) { return Math.round(v * 10000) / 10000; }
    function setMode(next) {
      mode = mode === next ? '' : next;
      refs.stage.classList.toggle('is-marking', !!mode);
      refs.markBar.hidden = !mode;
      refs.markHint.textContent = mode === 'hair' ? t('hairHint') + ' ' + t('hairTip') : mode === 'body' ? t('bodyHint') : '';
      refs.brushRow.hidden = !mode;
      if (refs.previewNote) refs.previewNote.hidden = !!mode;   // while painting the still picture is shown, not the preview
      sizeView();
      refs.undo.hidden = refs.clear.hidden = !mode;
      host.querySelectorAll('[data-mark]').forEach(function (b) { b.classList.toggle('is-on', b.getAttribute('data-mark') === mode); });
      requestAnimationFrame(drawOverlay);
      if (!mode) changed();
    }

    // ---- markup
    function chips(list, current, onPick, labelOf) {
      var row = el('div', 'pdepth__chips');
      list.forEach(function (value) {
        var b = el('button', 'pdepth__chip' + (value === current ? ' is-on' : ''), labelOf ? labelOf(value) : t(value));
        b.type = 'button';
        b.addEventListener('click', function () {
          row.querySelectorAll('button').forEach(function (x) { x.classList.toggle('is-on', x === b); });
          onPick(value);
        });
        row.append(b);
      });
      return row;
    }
    function range(label, min, max, step, value, onInput, ends) {
      var row = el('label', 'field pdepth__range');
      var head = el('span'); head.append(el('i', '', label));
      if (ends) head.append(el('small', '', ends));
      var input = el('input'); input.type = 'range'; input.min = min; input.max = max; input.step = step; input.value = value;
      input.addEventListener('input', function () { onInput(Number(input.value)); });
      input.addEventListener('change', changed);
      row.append(head, input);
      return row;
    }
    function group(title, extraClass) {
      var box = el('div', 'pdepth__group' + (extraClass ? ' ' + extraClass : ''));
      box.append(el('h3', 'pdepth__group-title', title));
      return box;
    }
    function toggle(label, checked, onFlip) {
      var wrap = el('label', 'pdepth__toggle');
      var box = el('input'); box.type = 'checkbox'; box.checked = checked;
      box.addEventListener('change', function () { onFlip(box.checked); });
      wrap.append(box, el('span', 'pdepth__knob pdepth__knob--sm'), el('span', 'pdepth__toggle-label', label));
      return wrap;
    }
    function build() {
      host.replaceChildren();
      var body = el('div', 'pdepth__body');
      // Stage: animated preview, the still picture while marking, and the marking overlay.
      var stage = el('div', 'pdepth__stage');
      var view = el('div', 'pdepth__view');
      var img = el('img', 'pdepth__img'); img.alt = '';
      var still = el('canvas', 'pdepth__still');
      var overlay = el('canvas', 'pdepth__overlay');
      overlay.addEventListener('pointerdown', onDown);
      overlay.addEventListener('pointermove', onMove);
      overlay.addEventListener('pointerup', onUp);
      overlay.addEventListener('pointercancel', onUp);
      view.append(img, still, overlay);
      var status = el('p', 'pdepth__status');
      var markBar = el('div', 'pdepth__markbar'); markBar.hidden = true;
      var markHint = el('p', 'pdepth__markhint');
      var brushRow = range(t('brush'), 0.008, 0.06, 0.002, o.brush, function (v) { o.brush = v; });
      var undo = el('button', 'pdepth__mini', t('undo')); undo.type = 'button';
      undo.addEventListener('click', function () {
        // Undo the last stroke of the list being painted (hair and body keep separate histories in one stack).
        for (var i = undoStack.length - 1; i >= 0; i--) {
          if (undoStack[i][0] === marks()) { undoStack[i][0].length = undoStack[i][1]; undoStack.splice(i, 1); drawOverlay(); return; }
        }
      });
      var clear = el('button', 'pdepth__mini', t('clear')); clear.type = 'button';
      clear.addEventListener('click', function () {
        var list = marks();
        undoStack = undoStack.filter(function (item) { return item[0] !== list; });
        list.length = 0;
        drawOverlay();
      });
      var done = el('button', 'pdepth__mini pdepth__mini--main', t('done')); done.type = 'button';
      done.addEventListener('click', function () { setMode(''); });
      var markButtons = el('div', 'pdepth__markbtns'); markButtons.append(undo, clear, done);
      markBar.append(markHint, brushRow, markButtons);
      // Owner: say that the preview is rougher than the result (smaller, 10 fps, lossy WebP).
      var previewNote = el('p', 'pdepth__pnote', t('previewNote'));
      stage.append(view, status, markBar, previewNote);

      var controls = el('div', 'pdepth__controls');
      // Quick looks
      var looks = group(t('looks'), 'pdepth__group--looks');
      var lookRow = el('div', 'pdepth__looks');
      Object.keys(LOOKS).forEach(function (key) {
        var b = el('button', 'pdepth__look', t(key)); b.type = 'button';
        b.addEventListener('click', function () { applyLook(LOOKS[key]); });
        lookRow.append(b);
      });
      looks.append(lookRow);
      // Camera
      var cam = group(t('camera'));
      var camExtra = el('div', 'pdepth__sub');
      camExtra.append(range(t('strength'), 0.5, 3, 0.1, o.strength, function (v) { o.strength = v; }),
        range(t('focus'), 0, 1, 0.05, o.focus, function (v) { o.focus = v; }, t('far') + ' ↔ ' + t('near')));
      camExtra.hidden = o.camera === 'none';
      cam.append(chips(CAMERAS, o.camera, function (v) { o.camera = v; camExtra.hidden = v === 'none'; changed(); }), camExtra);
      // Particles
      var parts = group(t('particles'));
      var partExtra = el('div', 'pdepth__sub');
      partExtra.append(range(t('amount'), 1, 3, 1, o.amount, function (v) { o.amount = v; }));
      partExtra.hidden = o.particles === 'none';
      parts.append(chips(PARTICLES, o.particles, function (v) { o.particles = v; partExtra.hidden = v === 'none'; changed(); }), partExtra);
      // Air + focus pull
      var air = group(t('atmosphere'));
      air.append(chips(AIRS, o.atmosphere, function (v) { o.atmosphere = v; changed(); }),
        toggle(t('focuspull'), o.focuspull, function (on) { o.focuspull = on; changed(); }),
        el('p', 'pdepth__note', t('focuspullHint')));
      // Breathing
      var breath = group(t('breath'));
      var breathExtra = el('div', 'pdepth__sub');
      var bodyBtn = el('button', 'pdepth__mark', t('markBody')); bodyBtn.type = 'button'; bodyBtn.setAttribute('data-mark', 'body');
      bodyBtn.addEventListener('click', function () { setMode('body'); });
      breathExtra.append(range(t('strength'), 0.5, 3, 0.1, o.breathStrength, function (v) { o.breathStrength = v; }),
        range(t('chest'), 0, 3, 0.1, o.chest, function (v) { o.chest = v; }), bodyBtn);
      breathExtra.hidden = !o.breath;
      breath.append(toggle(t('breath'), o.breath, function (on) { o.breath = on; breathExtra.hidden = !on; changed(); }), breathExtra);
      // Hair
      var hair = group(t('hair'));
      var hairExtra = el('div', 'pdepth__sub');
      var hairBtn = el('button', 'pdepth__mark', t('markHair')); hairBtn.type = 'button'; hairBtn.setAttribute('data-mark', 'hair');
      hairBtn.addEventListener('click', function () { setMode('hair'); });
      var hairNote = el('p', 'pdepth__note', t('hairEmpty'));
      // Owner, 2026-10-08: the sway reads well only on clearly visible hair (behind the figure, at the sides).
      var hairTip = el('p', 'pdepth__note pdepth__note--tip', t('hairTip'));
      hairExtra.append(range(t('strength'), 0.5, 3, 0.1, o.hairStrength, function (v) { o.hairStrength = v; }), hairBtn, hairNote, hairTip);
      hairExtra.hidden = !o.hair;
      hair.append(toggle(t('hair'), o.hair, function (on) {
        o.hair = on; hairExtra.hidden = !on;
        if (on && !o.strokes.length && pic.canvas && mode !== 'hair') setMode('hair'); else changed();
      }), hairExtra);
      controls.append(looks, cam, parts, air, breath, hair);
      body.append(stage, controls);
      host.append(body);
      refs = { stage: stage, view: view, img: img, still: still, overlay: overlay, status: status, markBar: markBar, markHint: markHint, previewNote: previewNote,
        brushRow: brushRow, undo: undo, clear: clear, hairNote: hairNote };
      hairNote.hidden = o.strokes.length > 0;
      sizeView();
      watchSize(stage);
      if (previewUrl) img.src = previewUrl;
      setStatus(pic.status, pic.busy);
      if (mode) { var m = mode; mode = ''; setMode(m); }
    }
    function applyLook(look) {
      o.camera = look.camera; if (look.strength) o.strength = look.strength;
      o.particles = look.particles; if (look.amount) o.amount = look.amount;
      o.atmosphere = look.atmosphere; o.focuspull = !!look.focuspull;
      o.breath = !!look.breath; o.hair = !!look.hair;
      build();
      if (o.hair && !o.strokes.length && pic.canvas) setMode('hair'); else changed();
    }
    window.addEventListener('resize', function () { if (mode) drawOverlay(); });

    build();
    return {
      setPicture: function (canvas) { prepare(canvas); },
      // Saved options (smweb.depth_fx.normalize shape) back into the controls, e.g. a Builder background re-opened.
      load: function (saved) {
        if (!saved) return;
        var cam = saved.camera || {};
        o.camera = CAMERAS.indexOf(cam.motion) >= 0 ? cam.motion : 'none';
        if (cam.strength) o.strength = cam.strength;
        if (saved.focus != null) o.focus = saved.focus;
        o.particles = saved.particles && PARTICLES.indexOf(saved.particles.kind) >= 0 ? saved.particles.kind : 'none';
        if (saved.particles && saved.particles.amount) o.amount = saved.particles.amount;
        o.atmosphere = AIRS.indexOf(saved.atmosphere) >= 0 ? saved.atmosphere : 'none';
        o.focuspull = !!saved.focuspull;
        o.breath = !!saved.breath;
        if (saved.breath) {
          o.breathStrength = saved.breath.strength || o.breathStrength; o.chest = saved.breath.chest || 0; o.region = saved.breath.region || null;
          o.bodyStrokes = Array.isArray(saved.breath.strokes) ? saved.breath.strokes.slice(0, MAX_STROKES) : [];
        }
        o.hair = !!saved.hair;
        o.strokes = saved.hair && Array.isArray(saved.hair.strokes) ? saved.hair.strokes.slice(0, MAX_STROKES) : [];
        if (saved.hair && saved.hair.strength) o.hairStrength = saved.hair.strength;
        build(); changed();
      },
      rebuild: build,
      options: function () { return hasEffect() ? options() : null; },
      names: names,
      hasEffect: hasEffect,
      state: o,
      picture: pic
    };
  }
  window.SMDepthEditor = { create: create, t: t };

  // ================================================================ Process wiring
  var designCard = document.getElementById('processDesignCard');
  if (!designCard) return;
  var STILL = /\.(png|jpe?g|webp|bmp|avif|heic|heif|tiff?)$/i;
  var on = false, fileKey = '';
  var card = el('div', 'card process-step-card pdepth-card');
  card.id = 'processDepthCard';
  designCard.parentNode.insertBefore(card, designCard);
  var block = el('section', 'pdepth');
  block.id = 'processDepthBlock';
  card.append(block);
  var head = el('header', 'pdepth__head');
  var editorHost = el('div', 'pdepth__editor');
  block.append(head, editorHost);
  var editor = create(editorHost, { onChange: notify });

  function buildHead() {
    head.replaceChildren();
    var titles = el('div', 'pdepth__titles');
    var h2 = el('h2', 'pdepth__title');
    h2.append(el('span', 'pdepth__spark', '✦'), el('span', '', t('title')), el('em', 'pdepth__new', t('isNew')));
    titles.append(h2, el('p', 'editor-note pdepth__hint', t('hint')));
    var sw = el('label', 'pdepth__switch');
    var box = el('input'); box.type = 'checkbox'; box.checked = on; box.id = 'processDepthOn';
    box.addEventListener('change', function () {
      on = box.checked;
      block.classList.toggle('is-on', on);
      card.classList.toggle('is-on', on);
      if (on) refresh();
      notify();
    });
    sw.append(box, el('span', 'pdepth__knob'), el('span', 'pdepth__label', t('on')));
    head.append(titles, sw);
  }
  function activeFile() {
    var s = window.state || {};
    var files = s.files || [];
    var index = Math.max(0, Math.min(files.length - 1, s.activeProcessFileIndex || 0));
    return files.length ? { file: files[index], rotation: Number((s.fileRotations || [])[index] || 0) } : null;
  }
  function upright(file, rotation) {
    // The picture as the server sees it: rotated, at most 640 px.
    return createImageBitmap(file).then(function (bmp) {
      var turn = ((Math.round(rotation / 90) % 4) + 4) % 4;
      var w = bmp.width, h = bmp.height, scale = Math.min(1, 640 / Math.max(w, h));
      var sw = Math.round(w * scale), sh = Math.round(h * scale);
      var canvas = document.createElement('canvas');
      canvas.width = turn % 2 ? sh : sw; canvas.height = turn % 2 ? sw : sh;
      var ctx = canvas.getContext('2d');
      ctx.translate(canvas.width / 2, canvas.height / 2); ctx.rotate(turn * Math.PI / 2);
      ctx.drawImage(bmp, -sw / 2, -sh / 2, sw, sh);
      return canvas;
    });
  }
  function refresh() {
    if (!on) return;
    var current = activeFile();
    var key = current ? (current.file.name || '') + '|' + current.file.size + '|' + (current.file.lastModified || 0) + '|' + current.rotation : '';
    if (key === fileKey) return;
    fileKey = key;
    if (!current) { editor.setPicture(null); return; }
    var file = current.file;
    if (!STILL.test(file.name || '') && !/^image\/(png|jpeg|webp|bmp|avif|heic|heif|tiff)/i.test(file.type || '')) {
      editor.setPicture(null);
      editor.picture.status = t('notStill'); editor.rebuild();
      return;
    }
    upright(file, current.rotation).then(function (canvas) { if (fileKey === key) editor.setPicture(canvas); })
      .catch(function () { if (fileKey === key) { editor.picture.status = t('failed'); editor.rebuild(); } });
  }
  function notify() {
    // Summary chips and the main preview listen to the card's change events.
    block.dispatchEvent(new Event('change', { bubbles: true }));
    document.dispatchEvent(new CustomEvent('sm:process-depth-change'));
  }

  buildHead();
  window.addEventListener('sm:langchange', function () { buildHead(); editor.rebuild(); });
  // The file list is owned by app.js: look at it while the effect is on.
  setInterval(function () { if (on && !document.hidden) refresh(); }, 800);

  window.SMProcessDepth = {
    active: function () { return on && editor.hasEffect(); },
    get: function () { return on ? editor.options() : null; },
    chip: function () { return on ? t('chip', { motion: editor.names().join(' + ') }) : ''; },
    editor: editor
  };
})();
