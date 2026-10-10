/* "Achievement letters" tab (#tab-letters, owner 2026-10-09): spell a word on the Steam Achievement Showcase with
   achievements whose icons are letters. Our own catalogue (scripts/build_achievement_letters.py, official Steam data:
   store search + GetSchemaForGame + global percentages) lives in static/assets/achievements/letters.json and is loaded
   when the tab opens. "All styles" picks the fewest games (greedy: the game covering most of the remaining letters,
   ties go to the easier one); a single style uses one game. Layout (rebuilt the same day): 1 word + Steam showcase, a tap
   on a letter opens every icon for it; 2 style gallery drawn on the visitor's word; 3 games, letters, how-to.
   Copy: the keyed COPY dictionary below, 8 languages (scripts/check_i18n.js). Debug hook: window.SMAchLetters. */
(function () {
  'use strict';
  var COPY = {
    en: { color: 'Colour', colorAll: 'All', c_red: 'Red', c_orange: 'Orange', c_yellow: 'Yellow', c_green: 'Green', c_blue: 'Blue', c_purple: 'Purple', c_pink: 'Pink', c_white: 'White', c_black: 'Black', setTitle: 'Set', setHint: '{n} letter achievements · {m} achievements in the game', setPick: 'Click an icon to put it in your word.', inWord: 'in the word', noColor: 'No icons of this colour for these letters.', stats: 'Statistics', elements: 'Icons',
      text: 'Text', textPh: 'Your word', mode: 'Style', modeAll: 'All styles (fewest games)', modeSet: '{name} · {n} letters', shuffle: 'Shuffle',
      slots: 'Slots', games: 'Games', icons: 'Icons in the catalogue', showcase: 'Achievement Showcase', tapHint: 'Tap a letter to see another icon for it.',
      missing: 'No icon for “{c}” in this style', listTitle: 'What goes into each slot', percent: '{p}% of players have it', noPercent: 'share of players unknown',
      store: 'Store', achievements: 'Achievements', buyTitle: 'Games you need', howTitle: 'How to put it on your profile',
      how1: 'Get these games on Steam: many of them cost very little.', how2: 'Unlock the achievement for each letter in the game.',
      how3: 'In Steam open Edit Profile → Featured Showcase → Achievement Showcase and pick the achievements in the order of your word.',
      catalog: 'All styles', catalogHint: '{n} games, {m} icons · updated {date}', use: 'Use this style', search: 'Find a game', more: 'Show more',
      loading: 'Loading the catalogue…', failed: 'Could not load the catalogue. Try again later.', empty: 'Type a word: Latin letters A–Z and digits.', letters: '{n} letters',
      s1: 'Write your word', s1Hint: 'Latin letters A–Z, digits and spaces, up to 32 characters.', examples: 'Try:', s2: 'Pick the letter style', s2Hint: 'Every style is shown on your word · {n} games, {m} icons.', s3: 'What you need', autoName: 'Mix: fewest games', autoHint: 'Letters from different games, as few games as possible.', cover: '{a}/{b} letters', chosen: 'Chosen', pickTitle: 'Icons for “{c}”', pickCount: '{n} options', close: 'Close', noStyles: 'No game matches the search.', missingShort: 'No icon', pickHint: '% = share of players who have it: higher is easier.' },
    ru: { color: 'Цвет', colorAll: 'Все', c_red: 'Красный', c_orange: 'Оранжевый', c_yellow: 'Жёлтый', c_green: 'Зелёный', c_blue: 'Синий', c_purple: 'Фиолетовый', c_pink: 'Розовый', c_white: 'Белый', c_black: 'Чёрный', setTitle: 'Набор', setHint: 'Буквенных достижений: {n} · всего достижений в игре: {m}', setPick: 'Нажми на иконку, чтобы поставить её в слово.', inWord: 'в слове', noColor: 'Для этих букв нет иконок такого цвета.', stats: 'Статистика', elements: 'Элем.',
      text: 'Текст', textPh: 'Твоё слово', mode: 'Стиль', modeAll: 'Все стили (меньше игр)', modeSet: '{name} · {n} букв', shuffle: 'Перемешать',
      slots: 'Слоты', games: 'Игры', icons: 'Иконок в каталоге', showcase: 'Витрина достижений', tapHint: 'Нажми на букву, чтобы посмотреть другую иконку для неё.',
      missing: 'Для «{c}» в этом стиле иконки нет', listTitle: 'Что стоит в каждом слоте', percent: 'есть у {p}% игроков', noPercent: 'доля игроков неизвестна',
      store: 'Магазин', achievements: 'Достижения', buyTitle: 'Какие игры нужны', howTitle: 'Как поставить в профиль',
      how1: 'Добавь эти игры в Steam: многие из них стоят совсем недорого.', how2: 'Получи в игре достижение для каждой буквы.',
      how3: 'В Steam открой «Редактировать профиль» → «Витрина» → «Витрина достижений» и выбери достижения в порядке букв слова.',
      catalog: 'Все стили', catalogHint: '{n} игр, {m} иконок · обновлено {date}', use: 'Взять этот стиль', search: 'Найти игру', more: 'Показать ещё',
      loading: 'Загружаем каталог…', failed: 'Не получилось загрузить каталог. Попробуй позже.', empty: 'Напиши слово: латинские буквы A–Z и цифры.', letters: '{n} букв',
      s1: 'Напиши слово', s1Hint: 'Латинские буквы A–Z, цифры и пробелы, до 32 символов.', examples: 'Например:', s2: 'Выбери стиль букв', s2Hint: 'Каждый стиль показан на твоём слове · {n} игр, {m} иконок.', s3: 'Что понадобится', autoName: 'Микс: меньше всего игр', autoHint: 'Буквы из разных игр, игр — как можно меньше.', cover: '{a}/{b} букв', chosen: 'Выбран', pickTitle: 'Иконки для «{c}»', pickCount: 'вариантов: {n}', close: 'Закрыть', noStyles: 'Игр по такому запросу нет.', missingShort: 'Без иконки', pickHint: '% — сколько игроков его получили: чем больше, тем проще.' },
    de: { color: 'Farbe', colorAll: 'Alle', c_red: 'Rot', c_orange: 'Orange', c_yellow: 'Gelb', c_green: 'Grün', c_blue: 'Blau', c_purple: 'Lila', c_pink: 'Rosa', c_white: 'Weiß', c_black: 'Schwarz', setTitle: 'Set', setHint: '{n} Buchstaben-Errungenschaften · {m} Errungenschaften im Spiel', setPick: 'Klicke auf ein Symbol, um es in dein Wort zu setzen.', inWord: 'im Wort', noColor: 'Für diese Buchstaben gibt es keine Symbole in dieser Farbe.', stats: 'Statistik', elements: 'Symbole',
      text: 'Text', textPh: 'Dein Wort', mode: 'Stil', modeAll: 'Alle Stile (wenigste Spiele)', modeSet: '{name} · {n} Buchstaben', shuffle: 'Mischen',
      slots: 'Plätze', games: 'Spiele', icons: 'Symbole im Katalog', showcase: 'Errungenschafts-Präsentation', tapHint: 'Tippe auf einen Buchstaben, um ein anderes Symbol zu sehen.',
      missing: 'Kein Symbol für „{c}“ in diesem Stil', listTitle: 'Was in jeden Platz kommt', percent: '{p} % der Spieler haben sie', noPercent: 'Anteil der Spieler unbekannt',
      store: 'Shop', achievements: 'Errungenschaften', buyTitle: 'Diese Spiele brauchst du', howTitle: 'So kommt es ins Profil',
      how1: 'Hol dir diese Spiele auf Steam: viele kosten sehr wenig.', how2: 'Schalte im Spiel die Errungenschaft für jeden Buchstaben frei.',
      how3: 'Öffne in Steam Profil bearbeiten → Präsentation → Errungenschafts-Präsentation und wähle die Errungenschaften in der Reihenfolge deines Worts.',
      catalog: 'Alle Stile', catalogHint: '{n} Spiele, {m} Symbole · aktualisiert {date}', use: 'Diesen Stil nehmen', search: 'Spiel suchen', more: 'Mehr zeigen',
      loading: 'Katalog wird geladen…', failed: 'Der Katalog konnte nicht geladen werden. Versuche es später.', empty: 'Schreib ein Wort: lateinische Buchstaben A–Z und Ziffern.', letters: '{n} Buchstaben',
      s1: 'Schreib dein Wort', s1Hint: 'Lateinische Buchstaben A–Z, Ziffern und Leerzeichen, bis zu 32 Zeichen.', examples: 'Beispiele:', s2: 'Wähle den Buchstabenstil', s2Hint: 'Jeder Stil wird an deinem Wort gezeigt · {n} Spiele, {m} Symbole.', s3: 'Was du brauchst', autoName: 'Mix: wenigste Spiele', autoHint: 'Buchstaben aus verschiedenen Spielen, möglichst wenige Spiele.', cover: '{a}/{b} Buchstaben', chosen: 'Gewählt', pickTitle: 'Symbole für „{c}“', pickCount: '{n} Optionen', close: 'Schließen', noStyles: 'Kein Spiel passt zur Suche.', missingShort: 'Ohne Symbol', pickHint: '% = Anteil der Spieler, die sie haben: je höher, desto leichter.' },
    tr: { color: 'Renk', colorAll: 'Tümü', c_red: 'Kırmızı', c_orange: 'Turuncu', c_yellow: 'Sarı', c_green: 'Yeşil', c_blue: 'Mavi', c_purple: 'Mor', c_pink: 'Pembe', c_white: 'Beyaz', c_black: 'Siyah', setTitle: 'Set', setHint: '{n} harf başarımı · oyunda {m} başarım', setPick: 'Kelimene koymak için bir simgeye tıkla.', inWord: 'kelimede', noColor: 'Bu harfler için bu renkte simge yok.', stats: 'İstatistik', elements: 'Simge',
      text: 'Metin', textPh: 'Kelimen', mode: 'Stil', modeAll: 'Tüm stiller (en az oyun)', modeSet: '{name} · {n} harf', shuffle: 'Karıştır',
      slots: 'Yuva', games: 'Oyun', icons: 'Katalogdaki simge', showcase: 'Başarım Vitrini', tapHint: 'Başka bir simge görmek için harfe dokun.',
      missing: 'Bu stilde “{c}” için simge yok', listTitle: 'Her yuvada ne var', percent: 'oyuncuların %{p}’sinde var', noPercent: 'oyuncu oranı bilinmiyor',
      store: 'Mağaza', achievements: 'Başarımlar', buyTitle: 'Gereken oyunlar', howTitle: 'Profiline nasıl eklenir',
      how1: 'Bu oyunları Steam’de edin: çoğu çok ucuz.', how2: 'Oyunda her harfin başarımını aç.',
      how3: 'Steam’de Profili Düzenle → Vitrin → Başarım Vitrini’ni aç ve başarımları kelimenin sırasıyla seç.',
      catalog: 'Tüm stiller', catalogHint: '{n} oyun, {m} simge · güncellendi {date}', use: 'Bu stili kullan', search: 'Oyun bul', more: 'Daha fazla göster',
      loading: 'Katalog yükleniyor…', failed: 'Katalog yüklenemedi. Daha sonra tekrar dene.', empty: 'Bir kelime yaz: Latin harfleri A–Z ve rakamlar.', letters: '{n} harf',
      s1: 'Kelimeni yaz', s1Hint: 'Latin harfleri A–Z, rakamlar ve boşluk, en fazla 32 karakter.', examples: 'Örnek:', s2: 'Harf stilini seç', s2Hint: 'Her stil senin kelimende gösteriliyor · {n} oyun, {m} simge.', s3: 'Neye ihtiyacın var', autoName: 'Karışık: en az oyun', autoHint: 'Farklı oyunlardan harfler, olabildiğince az oyun.', cover: '{a}/{b} harf', chosen: 'Seçildi', pickTitle: '“{c}” için simgeler', pickCount: '{n} seçenek', close: 'Kapat', noStyles: 'Aramaya uyan oyun yok.', missingShort: 'Simge yok', pickHint: '% = onu alan oyuncu oranı: ne kadar yüksekse o kadar kolay.' },
    fr: { color: 'Couleur', colorAll: 'Toutes', c_red: 'Rouge', c_orange: 'Orange', c_yellow: 'Jaune', c_green: 'Vert', c_blue: 'Bleu', c_purple: 'Violet', c_pink: 'Rose', c_white: 'Blanc', c_black: 'Noir', setTitle: 'Set', setHint: '{n} succès-lettres · {m} succès dans le jeu', setPick: 'Clique sur une icône pour la placer dans ton mot.', inWord: 'dans le mot', noColor: 'Pas d’icônes de cette couleur pour ces lettres.', stats: 'Statistiques', elements: 'Icônes',
      text: 'Texte', textPh: 'Ton mot', mode: 'Style', modeAll: 'Tous les styles (le moins de jeux)', modeSet: '{name} · {n} lettres', shuffle: 'Mélanger',
      slots: 'Emplacements', games: 'Jeux', icons: 'Icônes dans le catalogue', showcase: 'Vitrine des succès', tapHint: 'Touche une lettre pour voir une autre icône.',
      missing: 'Pas d’icône pour « {c} » dans ce style', listTitle: 'Ce que contient chaque emplacement', percent: '{p} % des joueurs l’ont', noPercent: 'part des joueurs inconnue',
      store: 'Boutique', achievements: 'Succès', buyTitle: 'Les jeux nécessaires', howTitle: 'Comment l’afficher sur ton profil',
      how1: 'Procure-toi ces jeux sur Steam : beaucoup coûtent très peu.', how2: 'Débloque dans le jeu le succès de chaque lettre.',
      how3: 'Dans Steam, ouvre Modifier le profil → Vitrine → Vitrine des succès et choisis les succès dans l’ordre de ton mot.',
      catalog: 'Tous les styles', catalogHint: '{n} jeux, {m} icônes · mis à jour le {date}', use: 'Prendre ce style', search: 'Trouver un jeu', more: 'Voir plus',
      loading: 'Chargement du catalogue…', failed: 'Impossible de charger le catalogue. Réessaie plus tard.', empty: 'Écris un mot : lettres latines A–Z et chiffres.', letters: '{n} lettres',
      s1: 'Écris ton mot', s1Hint: 'Lettres latines A–Z, chiffres et espaces, jusqu’à 32 caractères.', examples: 'Exemples :', s2: 'Choisis le style des lettres', s2Hint: 'Chaque style est montré sur ton mot · {n} jeux, {m} icônes.', s3: 'Ce qu’il te faut', autoName: 'Mélange : le moins de jeux', autoHint: 'Des lettres de plusieurs jeux, le moins de jeux possible.', cover: '{a}/{b} lettres', chosen: 'Choisi', pickTitle: 'Icônes pour « {c} »', pickCount: '{n} options', close: 'Fermer', noStyles: 'Aucun jeu ne correspond à la recherche.', missingShort: 'Sans icône', pickHint: '% = part des joueurs qui l’ont : plus c’est haut, plus c’est facile.' },
    uk: { color: 'Колір', colorAll: 'Усі', c_red: 'Червоний', c_orange: 'Помаранчевий', c_yellow: 'Жовтий', c_green: 'Зелений', c_blue: 'Синій', c_purple: 'Фіолетовий', c_pink: 'Рожевий', c_white: 'Білий', c_black: 'Чорний', setTitle: 'Набір', setHint: 'Літерних досягнень: {n} · усього досягнень у грі: {m}', setPick: 'Натисни на іконку, щоб поставити її в слово.', inWord: 'у слові', noColor: 'Для цих літер немає іконок такого кольору.', stats: 'Статистика', elements: 'Елем.',
      text: 'Текст', textPh: 'Твоє слово', mode: 'Стиль', modeAll: 'Усі стилі (менше ігор)', modeSet: '{name} · {n} літер', shuffle: 'Перемішати',
      slots: 'Слоти', games: 'Ігри', icons: 'Іконок у каталозі', showcase: 'Вітрина досягнень', tapHint: 'Натисни на літеру, щоб побачити іншу іконку для неї.',
      missing: 'Для «{c}» у цьому стилі іконки немає', listTitle: 'Що стоїть у кожному слоті', percent: 'є у {p}% гравців', noPercent: 'частка гравців невідома',
      store: 'Магазин', achievements: 'Досягнення', buyTitle: 'Які ігри потрібні', howTitle: 'Як поставити в профіль',
      how1: 'Додай ці ігри в Steam: багато з них коштують зовсім недорого.', how2: 'Отримай у грі досягнення для кожної літери.',
      how3: 'У Steam відкрий «Редагувати профіль» → «Вітрина» → «Вітрина досягнень» і вибери досягнення в порядку літер слова.',
      catalog: 'Усі стилі', catalogHint: '{n} ігор, {m} іконок · оновлено {date}', use: 'Взяти цей стиль', search: 'Знайти гру', more: 'Показати ще',
      loading: 'Завантажуємо каталог…', failed: 'Не вдалося завантажити каталог. Спробуй пізніше.', empty: 'Напиши слово: латинські літери A–Z і цифри.', letters: '{n} літер',
      s1: 'Напиши слово', s1Hint: 'Латинські літери A–Z, цифри й пробіли, до 32 символів.', examples: 'Наприклад:', s2: 'Вибери стиль літер', s2Hint: 'Кожен стиль показано на твоєму слові · {n} ігор, {m} іконок.', s3: 'Що знадобиться', autoName: 'Мікс: найменше ігор', autoHint: 'Літери з різних ігор, ігор — якомога менше.', cover: '{a}/{b} літер', chosen: 'Обрано', pickTitle: 'Іконки для «{c}»', pickCount: 'варіантів: {n}', close: 'Закрити', noStyles: 'Ігор за таким запитом немає.', missingShort: 'Без іконки', pickHint: '% — скільки гравців його отримали: що більше, то простіше.' },
    es: { color: 'Color', colorAll: 'Todos', c_red: 'Rojo', c_orange: 'Naranja', c_yellow: 'Amarillo', c_green: 'Verde', c_blue: 'Azul', c_purple: 'Morado', c_pink: 'Rosa', c_white: 'Blanco', c_black: 'Negro', setTitle: 'Set', setHint: '{n} logros de letras · {m} logros en el juego', setPick: 'Haz clic en un icono para ponerlo en tu palabra.', inWord: 'en la palabra', noColor: 'No hay iconos de este color para estas letras.', stats: 'Estadísticas', elements: 'Iconos',
      text: 'Texto', textPh: 'Tu palabra', mode: 'Estilo', modeAll: 'Todos los estilos (menos juegos)', modeSet: '{name} · {n} letras', shuffle: 'Mezclar',
      slots: 'Espacios', games: 'Juegos', icons: 'Iconos en el catálogo', showcase: 'Escaparate de logros', tapHint: 'Toca una letra para ver otro icono.',
      missing: 'No hay icono para «{c}» en este estilo', listTitle: 'Qué va en cada espacio', percent: 'lo tiene el {p}% de los jugadores', noPercent: 'porcentaje de jugadores desconocido',
      store: 'Tienda', achievements: 'Logros', buyTitle: 'Juegos que necesitas', howTitle: 'Cómo ponerlo en tu perfil',
      how1: 'Consigue estos juegos en Steam: muchos cuestan muy poco.', how2: 'Desbloquea en el juego el logro de cada letra.',
      how3: 'En Steam abre Editar perfil → Escaparate → Escaparate de logros y elige los logros en el orden de tu palabra.',
      catalog: 'Todos los estilos', catalogHint: '{n} juegos, {m} iconos · actualizado {date}', use: 'Usar este estilo', search: 'Buscar un juego', more: 'Ver más',
      loading: 'Cargando el catálogo…', failed: 'No se pudo cargar el catálogo. Inténtalo más tarde.', empty: 'Escribe una palabra: letras latinas A–Z y dígitos.', letters: '{n} letras',
      s1: 'Escribe tu palabra', s1Hint: 'Letras latinas A–Z, dígitos y espacios, hasta 32 caracteres.', examples: 'Prueba:', s2: 'Elige el estilo de las letras', s2Hint: 'Cada estilo se muestra con tu palabra · {n} juegos, {m} iconos.', s3: 'Lo que necesitas', autoName: 'Mezcla: menos juegos', autoHint: 'Letras de varios juegos, los menos posibles.', cover: '{a}/{b} letras', chosen: 'Elegido', pickTitle: 'Iconos para «{c}»', pickCount: '{n} opciones', close: 'Cerrar', noStyles: 'Ningún juego coincide con la búsqueda.', missingShort: 'Sin icono', pickHint: '% = jugadores que lo tienen: cuanto más alto, más fácil.' },
    pt: { color: 'Cor', colorAll: 'Todas', c_red: 'Vermelho', c_orange: 'Laranja', c_yellow: 'Amarelo', c_green: 'Verde', c_blue: 'Azul', c_purple: 'Roxo', c_pink: 'Rosa', c_white: 'Branco', c_black: 'Preto', setTitle: 'Conjunto', setHint: '{n} conquistas de letras · {m} conquistas no jogo', setPick: 'Clique em um ícone para colocá-lo na sua palavra.', inWord: 'na palavra', noColor: 'Não há ícones dessa cor para estas letras.', stats: 'Estatísticas', elements: 'Ícones',
      text: 'Texto', textPh: 'Sua palavra', mode: 'Estilo', modeAll: 'Todos os estilos (menos jogos)', modeSet: '{name} · {n} letras', shuffle: 'Embaralhar',
      slots: 'Espaços', games: 'Jogos', icons: 'Ícones no catálogo', showcase: 'Vitrine de conquistas', tapHint: 'Toque em uma letra para ver outro ícone.',
      missing: 'Sem ícone para «{c}» neste estilo', listTitle: 'O que vai em cada espaço', percent: '{p}% dos jogadores têm', noPercent: 'parcela de jogadores desconhecida',
      store: 'Loja', achievements: 'Conquistas', buyTitle: 'Jogos necessários', howTitle: 'Como colocar no perfil',
      how1: 'Pegue estes jogos na Steam: muitos custam bem pouco.', how2: 'Desbloqueie no jogo a conquista de cada letra.',
      how3: 'Na Steam abra Editar perfil → Vitrine → Vitrine de conquistas e escolha as conquistas na ordem da sua palavra.',
      catalog: 'Todos os estilos', catalogHint: '{n} jogos, {m} ícones · atualizado em {date}', use: 'Usar este estilo', search: 'Encontrar um jogo', more: 'Mostrar mais',
      loading: 'Carregando o catálogo…', failed: 'Não foi possível carregar o catálogo. Tente mais tarde.', empty: 'Escreva uma palavra: letras latinas A–Z e números.', letters: '{n} letras',
      s1: 'Escreva sua palavra', s1Hint: 'Letras latinas A–Z, números e espaços, até 32 caracteres.', examples: 'Experimente:', s2: 'Escolha o estilo das letras', s2Hint: 'Cada estilo aparece na sua palavra · {n} jogos, {m} ícones.', s3: 'O que você precisa', autoName: 'Mistura: menos jogos', autoHint: 'Letras de vários jogos, o mínimo de jogos possível.', cover: '{a}/{b} letras', chosen: 'Escolhido', pickTitle: 'Ícones para «{c}»', pickCount: '{n} opções', close: 'Fechar', noStyles: 'Nenhum jogo corresponde à busca.', missingShort: 'Sem ícone', pickHint: '% = jogadores que a têm: quanto maior, mais fácil.' }
  };
  var DATA_URL = '/static/assets/achievements/letters.json?v=20261009-ach1';
  var STORE = 'sm_ach_letters';
  var host = document.getElementById('achLetters');
  if (!host) return;

  function lang() { var l = window.SMLang && SMLang.get ? SMLang.get() : 'en'; return COPY[l] ? l : 'en'; }
  function t(key, vars) {
    var text = (COPY[lang()] || COPY.en)[key] || COPY.en[key] || key;
    Object.keys(vars || {}).forEach(function (k) { text = text.split('{' + k + '}').join(vars[k]); });
    return text;
  }
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function button(cls, text, onClick) { var b = el('button', cls, text); b.type = 'button'; if (onClick) b.addEventListener('click', onClick); return b; }

  var COLORS = ['red', 'orange', 'yellow', 'green', 'blue', 'purple', 'pink', 'white', 'black'];
  var SWATCH = { red: '#ef4444', orange: '#f59e0b', yellow: '#facc15', green: '#22c55e', blue: '#3b82f6', purple: '#a855f7', pink: '#ec4899', white: '#f8fafc', black: '#334155' };
  var state = { text: 'STEAM', mode: 'all', color: 'all', picks: {}, sel: null, picked: 0, data: null, error: false, catalogQuery: '', catalogShown: 24 };
  try {
    var saved = JSON.parse(localStorage.getItem(STORE) || 'null');
    if (saved && typeof saved.text === 'string') {
      state.text = saved.text.slice(0, 32); state.mode = String(saved.mode || 'all');
      state.color = COLORS.indexOf(saved.color) >= 0 ? saved.color : 'all';
    }
  } catch (_) {}
  var refs = {};

  // ---------------------------------------------------------------- catalogue
  var sets = [], byApp = {};
  function charsOf(set, ch) { return /[0-9]/.test(ch) ? (set.digits || {})[ch] : (set.letters || {})[ch]; }
  function icon(set, variant) { return state.data.cdn + set.appid + '/' + variant[0] + '.jpg'; }
  function load() {
    if (state.data || load.pending) return;
    load.pending = true;
    fetch(DATA_URL).then(function (r) { if (!r.ok) throw new Error('catalogue'); return r.json(); }).then(function (data) {
      state.data = data;
      sets = data.sets || [];
      sets.forEach(function (set) { byApp[set.appid] = set; });
      if (state.mode !== 'all' && !byApp[state.mode]) state.mode = 'all';
      build();
    }).catch(function () { state.error = true; build(); }).then(function () { load.pending = false; });
  }

  // ---------------------------------------------------------------- choosing icons
  function chars() { return state.text.toUpperCase().split(''); }
  function needed() {
    var seen = {};
    chars().forEach(function (c) { if (/[A-Z0-9]/.test(c)) seen[c] = 1; });
    return Object.keys(seen);
  }
  function colorOk(variant) { return state.color === 'all' || variant[3] === state.color; }
  // Index of the first variant of a character in the chosen colour, or -1.
  function firstOk(set, c) {
    var list = charsOf(set, c) || [];
    for (var i = 0; i < list.length; i++) if (colorOk(list[i])) return i;
    return -1;
  }
  function easiness(set, letters) {
    var sum = 0, n = 0;
    letters.forEach(function (c) { var v = charsOf(set, c); if (v && v[0] && v[0][1] != null) { sum += v[0][1]; n++; } });
    return n ? sum / n : 0;
  }
  // The default pick for every character: one style, or the fewest games for "all styles".
  function plan() {
    var picks = {}, rest = needed();
    if (state.mode !== 'all') {
      var only = byApp[state.mode];
      rest.forEach(function (c) { var v = only ? firstOk(only, c) : -1; if (v >= 0) picks[c] = { appid: only.appid, v: v }; });
      return picks;
    }
    while (rest.length) {
      var best = null, bestCover = [], bestEase = -1;
      sets.forEach(function (set) {
        var cover = rest.filter(function (c) { return firstOk(set, c) >= 0; });
        if (!cover.length) return;
        var ease = easiness(set, cover);
        if (cover.length > bestCover.length || (cover.length === bestCover.length && ease > bestEase)) { best = set; bestCover = cover; bestEase = ease; }
      });
      if (!best) break;
      bestCover.forEach(function (c) { picks[c] = { appid: best.appid, v: firstOk(best, c) }; });
      rest = rest.filter(function (c) { return bestCover.indexOf(c) < 0; });
    }
    return picks;
  }
  // Every (game, variant) for a character, the current game first.
  function options(c) {
    var list = [];
    var pool = state.mode === 'all' ? sets : [byApp[state.mode]].filter(Boolean);
    pool.forEach(function (set) { (charsOf(set, c) || []).forEach(function (variant, v) { if (colorOk(variant)) list.push({ appid: set.appid, v: v }); }); });
    var current = state.picks[c];
    if (current) list.sort(function (a, b) { return (b.appid === current.appid) - (a.appid === current.appid); });
    return list;
  }
  function cycle(c) {
    var list = options(c), current = state.picks[c];
    if (list.length < 2 || !current) return;
    var at = list.findIndex(function (o) { return o.appid === current.appid && o.v === current.v; });
    state.picks[c] = list[(at + 1) % list.length];
    paintResult(); paintSet();
  }
  function shuffle() {
    needed().forEach(function (c) { var list = options(c); if (list.length) state.picks[c] = list[Math.floor(Math.random() * list.length)]; });
    paintResult(); paintSet();
  }
  function save() { try { localStorage.setItem(STORE, JSON.stringify({ text: state.text, mode: state.mode, color: state.color })); } catch (_) {} }
  function pool() { return state.mode === 'all' ? sets : [byApp[state.mode]].filter(Boolean); }
  // Icons per colour for the word's letters across every style (owner 2026-10-09: with one style chosen the filter
  // used to offer only that style's colours). An empty word counts every letter.
  function colorCounts() {
    var counts = {}, wanted = needed().length ? needed() : null;
    sets.forEach(function (set) {
      ['letters', 'digits'].forEach(function (group) {
        Object.keys(set[group] || {}).forEach(function (c) {
          if (wanted && wanted.indexOf(c) < 0) return;
          set[group][c].forEach(function (v) { if (v[3]) counts[v[3]] = (counts[v[3]] || 0) + 1; });
        });
      });
    });
    return counts;
  }

  // ---------------------------------------------------------------- markup
  // Three steps (owner 2026-10-09: "chaos, unclear how to use it"): 1 the word and its Steam showcase (a tap on a
  // letter opens every icon for it below the showcase), 2 the style gallery (each style drawn on the visitor's own
  // word, with how many of its letters the style has), 3 what you need (games, letter by letter, how to set it up).
  var EXAMPLES = ['STEAM', 'GG WP', 'HELLO', 'GAMER', 'LOVE', '2026'];
  var SAMPLE = 7;          // letters of the word drawn on a style card
  var PICKER = 60;         // icons in the picker before "Show more"
  function step(n, title, hint) {
    var head = el('div', 'achl-step');
    var text = el('div', 'achl-step__text');
    text.append(el('h3', 'achl-h', title));
    if (hint) text.append(el('p', 'achl-hint', hint));
    head.append(el('span', 'achl-step__n', String(n)), text);
    return head;
  }
  function wordChars() { return chars().filter(function (c) { return /[A-Z0-9]/.test(c); }); }
  function coverage(set) {
    var wanted = needed();
    return { have: wanted.filter(function (c) { return firstOk(set, c) >= 0; }).length, of: wanted.length };
  }
  function replan() { state.picks = plan(); state.picked = 0; save(); }
  function setText(text) {
    state.text = String(text || '').replace(/[^A-Za-z0-9 ]/g, '').toUpperCase().slice(0, 32);
    if (refs.input && refs.input.value !== state.text) refs.input.value = state.text;
    if (state.sel != null && state.sel >= chars().length) state.sel = null;
    replan(); paintColors(); paintResult(); paintSet(); paintCatalogSoon();
  }
  function useStyle(mode) {
    state.mode = String(mode); state.sel = null; replan(); paintAll();
  }
  function build() {
    host.replaceChildren();
    var root = el('div', 'achl');
    if (!state.data) {
      root.append(el('div', 'achl-panel achl-note', state.error ? t('failed') : t('loading')));
      host.append(root);
      return;
    }
    var icons = 0;
    sets.forEach(function (set) { Object.keys(set.letters).concat(Object.keys(set.digits || {})).forEach(function (c) { icons += charsOf(set, c).length; }); });
    refs.icons = icons;

    // 1 The word and the Steam showcase
    var stage = el('section', 'achl-panel achl-stage');
    var word = el('div', 'achl-word');
    var input = el('input', 'achl-word__input'); input.maxLength = 32; input.value = state.text; input.placeholder = t('textPh');
    input.autocomplete = 'off'; input.spellcheck = false; input.setAttribute('aria-label', t('textPh'));
    input.addEventListener('input', function () { setText(input.value); });
    refs.input = input;
    word.append(input, button('achl-btn achl-word__shuffle', '🎲 ' + t('shuffle'), shuffle));
    var examples = el('div', 'achl-examples');
    examples.append(el('span', '', t('examples')));
    EXAMPLES.forEach(function (w) { examples.append(button('achl-chip', w, function () { setText(w); })); });
    refs.steam = el('div', 'achl-steam');
    refs.picker = el('div', 'achl-picker');
    stage.append(step(1, t('s1'), t('s1Hint')), word, examples, refs.steam, refs.picker);

    // 2 Style gallery
    var style = el('section', 'achl-panel achl-style');
    var bar = el('div', 'achl-style__bar');
    var search = el('input', 'achl-field achl-search'); search.type = 'search'; search.placeholder = t('search'); search.value = state.catalogQuery;
    search.setAttribute('aria-label', t('search'));
    search.addEventListener('input', function () { state.catalogQuery = search.value; state.catalogShown = 24; paintCatalog(); });
    refs.colors = el('div', 'achl-colors');
    bar.append(search, refs.colors);
    refs.catalog = el('div', 'achl-styles');
    refs.more = button('achl-btn achl-more', t('more'), function () { state.catalogShown += 24; paintCatalog(); });
    style.append(step(2, t('s2'), t('s2Hint', { n: sets.length, m: icons.toLocaleString() })), bar, refs.catalog, refs.more);

    // 3 What you need
    var need = el('section', 'achl-panel achl-need');
    refs.stats = el('div', 'achl-stats');
    refs.games = el('div', 'achl-games');
    var details = el('details', 'achl-details');
    details.append(el('summary', '', t('listTitle')));
    refs.list = el('div', 'achl-list');
    details.append(refs.list);
    var how = el('ol', 'achl-how');
    ['how1', 'how2', 'how3'].forEach(function (k) { how.append(el('li', '', t(k))); });
    need.append(step(3, t('s3')), refs.stats, refs.games, details, el('h4', 'achl-sub', t('howTitle')), how);

    var cols = el('div', 'achl-cols');
    cols.append(style, need);
    root.append(stage, cols);
    host.append(root);
    replan();
    paintAll();
  }
  function paintAll() { paintColors(); paintResult(); paintSet(); paintCatalog(); }
  function paintCatalogSoon() { clearTimeout(paintCatalogSoon.timer); paintCatalogSoon.timer = setTimeout(paintCatalog, 120); }
  function paintColors() {
    var counts = colorCounts();
    if (state.color !== 'all' && !counts[state.color]) { state.color = 'all'; state.picks = plan(); }
    refs.colors.replaceChildren();
    refs.colors.append(el('span', 'achl-colors__label', t('color')));
    var all = button('achl-color achl-color--all' + (state.color === 'all' ? ' is-on' : ''), t('colorAll'), function () { setColor('all'); });
    all.setAttribute('aria-pressed', state.color === 'all' ? 'true' : 'false');
    refs.colors.append(all);
    COLORS.forEach(function (name) {
      var n = counts[name] || 0;
      var chip = button('achl-color' + (state.color === name ? ' is-on' : ''), null, function () { setColor(name); });
      chip.style.setProperty('--swatch', SWATCH[name]);
      chip.append(el('i'), el('span', '', t('c_' + name)));
      chip.title = t('c_' + name) + ' · ' + n;
      chip.disabled = !n;
      chip.setAttribute('aria-pressed', state.color === name ? 'true' : 'false');
      refs.colors.append(chip);
    });
  }
  // A colour the chosen style cannot spell the whole word in switches to the mix, so the word stays complete.
  function setColor(name) {
    state.color = name; state.sel = null;
    var set = state.mode !== 'all' && byApp[state.mode];
    if (set && name !== 'all') { var cover = coverage(set); if (cover.have < cover.of) state.mode = 'all'; }
    replan(); paintAll();
  }
  // Every icon for the letter chosen in the showcase (the chosen style only, or every style for the mix).
  function paintSet() {
    var picker = refs.picker, list = chars(), c = state.sel != null ? list[state.sel] : null;
    picker.replaceChildren();
    picker.hidden = !c || !/[A-Z0-9]/.test(c);
    if (picker.hidden) return;
    var opts = options(c), pick = state.picks[c], set = pick && byApp[pick.appid], variant = set && charsOf(set, c)[pick.v];
    var head = el('div', 'achl-picker__head');
    var title = el('div', 'achl-picker__title');
    title.append(el('b', '', t('pickTitle', { c: c })), el('small', '', t('pickCount', { n: opts.length }) + ' · ' + t('pickHint')));
    head.append(title);
    if (variant) {
      var now = el('div', 'achl-picker__now');
      now.append(el('span', '', set.name + ' · «' + variant[2] + '»' + (variant[1] != null ? ' · ' + variant[1] + '%' : '')),
        link(t('store'), 'https://store.steampowered.com/app/' + set.appid + '/'),
        link(t('achievements'), 'https://steamcommunity.com/stats/' + set.appid + '/achievements/'));
      head.append(now);
    }
    var close = button('achl-picker__close', '×', function () { state.sel = null; paintResult(); paintSet(); });
    close.setAttribute('aria-label', t('close'));
    head.append(close);
    var grid = el('div', 'achl-picker__grid');
    opts.slice(0, state.picked ? PICKER * (state.picked + 1) : PICKER).forEach(function (o) {
      var s = byApp[o.appid], v = charsOf(s, c)[o.v];
      var on = pick && pick.appid === o.appid && pick.v === o.v;
      var tile = button('achl-icon' + (on ? ' is-on' : ''), null, function () { state.picks[c] = o; paintResult(); paintSet(); });
      var img = el('img'); img.src = icon(s, v); img.alt = c; img.loading = 'lazy'; img.width = 56; img.height = 56;
      img.onerror = function () { tile.remove(); };
      tile.append(img, el('small', '', v[1] != null ? v[1] + '%' : '—'));
      tile.title = s.name + ' · «' + v[2] + '»' + (v[1] != null ? ' · ' + t('percent', { p: v[1] }) : '');
      grid.append(tile);
    });
    var shown = state.picked ? PICKER * (state.picked + 1) : PICKER;
    var more = button('achl-btn achl-more', t('more'), function () { state.picked = (state.picked || 0) + 1; paintSet(); });
    more.hidden = opts.length <= shown;
    picker.append(head, grid, more);
  }
  function paintResult() {
    var list = chars(), used = {}, slots = 0, missing = 0;
    refs.steam.replaceChildren();
    refs.list.replaceChildren();
    var head = el('div', 'achl-steam__head');
    head.append(el('span', '', t('showcase')));
    var row = el('div', 'achl-steam__row');
    if (!needed().length) row.append(el('p', 'achl-steam__empty', t('empty')));
    list.forEach(function (c, index) {
      if (c === ' ') { row.append(el('span', 'achl-gap')); return; }
      if (!/[A-Z0-9]/.test(c)) return;
      slots++;
      var pick = state.picks[c], set = pick && byApp[pick.appid], variant = set && charsOf(set, c)[pick.v];
      var cell = button('achl-slot' + (variant ? '' : ' is-missing') + (state.sel === index ? ' is-sel' : ''), null, function () {
        state.sel = state.sel === index ? null : index; state.picked = 0; paintResult(); paintSet();
      });
      cell.title = variant ? set.name + ' · «' + variant[2] + '»' : t('missing', { c: c });
      cell.setAttribute('aria-pressed', state.sel === index ? 'true' : 'false');
      if (variant) {
        var img = el('img'); img.src = icon(set, variant); img.alt = c; img.width = 64; img.height = 64;
        img.onerror = function () { img.replaceWith(el('b', '', c)); };
        cell.append(img);
        used[set.appid] = used[set.appid] || [];
        if (!used[set.appid].some(function (u) { return u[0] === c; })) used[set.appid].push([c, variant]);
      } else { cell.append(el('b', '', c)); missing++; }
      row.append(cell);
      var line = el('div', 'achl-line' + (variant ? '' : ' is-missing'));
      var tag = el('span', 'achl-line__char', c);
      if (variant) {
        var info = el('div', 'achl-line__info');
        info.append(el('b', '', set.name), el('small', '', '«' + variant[2] + '» · ' + (variant[1] != null ? t('percent', { p: variant[1] }) : t('noPercent'))));
        line.append(tag, info);
      } else line.append(tag, el('small', '', t('missing', { c: c })));
      refs.list.append(line);
    });
    refs.steam.append(head, row);
    if (slots) refs.steam.append(el('p', 'achl-steam__hint', t('tapHint')));
    var games = Object.keys(used);
    refs.stats.replaceChildren(stat(slots, t('slots')), stat(games.length, t('games')));
    if (missing) refs.stats.append(stat(missing, t('missingShort'), 'is-warn'));
    refs.games.replaceChildren();
    games.forEach(function (appid) {
      var set = byApp[appid], item = el('article', 'achl-game');
      var cap = el('img', 'achl-game__cap'); cap.src = 'https://cdn.cloudflare.steamstatic.com/steam/apps/' + appid + '/capsule_184x69.jpg'; cap.alt = ''; cap.loading = 'lazy';
      cap.onerror = function () { cap.replaceWith(el('span', 'achl-game__cap achl-game__cap--none', set.name.slice(0, 1))); };
      var body = el('div', 'achl-game__body');
      body.append(el('b', '', set.name));
      var mini = el('div', 'achl-game__letters');
      used[appid].forEach(function (u) { var m = el('img'); m.src = icon(set, u[1]); m.alt = u[0]; m.title = u[0] + ' · «' + u[1][2] + '»'; m.width = 26; m.height = 26; mini.append(m); });
      var links = el('div', 'achl-game__links');
      links.append(link(t('store'), 'https://store.steampowered.com/app/' + appid + '/'),
        link(t('achievements'), 'https://steamcommunity.com/stats/' + appid + '/achievements/'));
      body.append(mini, links);
      item.append(cap, body);
      refs.games.append(item);
    });
    // The mix card shows the current picks, so it follows every change.
    var mixRow = refs.catalog && refs.catalog.querySelector('.achl-style-card--mix .achl-style-card__word');
    if (mixRow) mixRow.replaceWith(sampleRow(null));
  }
  // The visitor's word (first SAMPLE letters) in one style; null = the current mix picks.
  function sampleRow(set) {
    var row = el('div', 'achl-style-card__word');
    var letters = wordChars().slice(0, SAMPLE);
    if (!letters.length) letters = ['A', 'B', 'C', 'D'];
    letters.forEach(function (c) {
      var src = '';
      if (set) { var v = firstOk(set, c); if (v >= 0) src = icon(set, charsOf(set, c)[v]); }
      else { var p = state.picks[c], s = p && byApp[p.appid]; if (s) src = icon(s, charsOf(s, c)[p.v]); }
      if (src) {
        var img = el('img'); img.src = src; img.alt = c; img.loading = 'lazy'; img.width = 40; img.height = 40;
        img.onerror = function () { img.replaceWith(el('span', 'achl-style-card__miss', c)); };
        row.append(img);
      } else row.append(el('span', 'achl-style-card__miss', c));
    });
    row.style.setProperty('--n', String(letters.length));
    return row;
  }
  function paintCatalog() {
    var q = state.catalogQuery.trim().toLowerCase();
    refs.catalog.replaceChildren();
    if (!q) {
      var mix = button('achl-style-card achl-style-card--mix' + (state.mode === 'all' ? ' is-on' : ''), null, function () { useStyle('all'); });
      var mixHead = el('div', 'achl-style-card__head');
      mixHead.append(el('b', '', t('autoName')));
      if (state.mode === 'all') mixHead.append(el('span', 'achl-badge achl-badge--on', t('chosen')));
      mix.append(sampleRow(null), mixHead, el('small', '', t('autoHint')));
      refs.catalog.append(mix);
    }
    var list = sets.filter(function (set) { return !q || set.name.toLowerCase().indexOf(q) >= 0; }).map(function (set) {
      return { set: set, cover: coverage(set) };
    });
    list.sort(function (a, b) {
      return (b.cover.have - a.cover.have) || (easiness(b.set, needed()) - easiness(a.set, needed())) || a.set.name.localeCompare(b.set.name);
    });
    // With a colour chosen, styles without a single letter of the word in that colour are left out.
    if (state.color !== 'all') list = list.filter(function (item) { return item.cover.have > 0 || String(item.set.appid) === state.mode; });
    if (!list.length) refs.catalog.append(el('p', 'achl-hint achl-styles__empty', t('noStyles')));
    list.slice(0, state.catalogShown).forEach(function (item) {
      var set = item.set, on = String(set.appid) === state.mode, full = item.cover.of && item.cover.have === item.cover.of;
      var card = button('achl-style-card' + (on ? ' is-on' : ''), null, function () { useStyle(set.appid); });
      var head = el('div', 'achl-style-card__head');
      head.append(el('b', '', set.name));
      if (on) head.append(el('span', 'achl-badge achl-badge--on', t('chosen')));
      else if (item.cover.of) head.append(el('span', 'achl-badge' + (full ? ' achl-badge--full' : ''), t('cover', { a: item.cover.have, b: item.cover.of })));
      card.append(sampleRow(set), head, el('small', '', t('letters', { n: Object.keys(set.letters).length + Object.keys(set.digits || {}).length })));
      refs.catalog.append(card);
    });
    refs.more.hidden = list.length <= state.catalogShown;
  }
  function stat(value, label, cls) { var box = el('div', 'achl-stat' + (cls ? ' ' + cls : '')); box.append(el('b', '', String(value)), el('small', '', label)); return box; }
  function link(text, url) { var a = el('a', 'achl-link', text + ' ↗'); a.href = url; a.target = '_blank'; a.rel = 'noopener'; return a; }

  // ---------------------------------------------------------------- start: load when the tab is first opened
  function tabOpen() { var tab = document.getElementById('tab-letters'); return tab && tab.classList.contains('active'); }
  build();
  if (tabOpen()) load();
  document.addEventListener('click', function (event) {
    var b = event.target.closest && event.target.closest('[data-tab="letters"]');
    if (b) setTimeout(load, 0);
  });
  if (/#letters\b/.test(location.hash)) load();
  window.addEventListener('sm:langchange', function () { if (state.data) build(); else build(); });
  window.SMAchLetters = { state: state, load: load, plan: plan, cycle: cycle, setColor: function (c) { if (state.data) setColor(c); } };
})();
