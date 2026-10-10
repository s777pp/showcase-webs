/* "Achievement letters" tab (#tab-letters): write a word on the Steam Achievement Showcase with achievements whose icons
   are letters. Our own catalogue (scripts/build_achievement_letters.py, official Steam data: store search +
   GetSchemaForGame in English and Russian + global percentages) lives in static/assets/achievements/letters.json and is
   loaded when the tab opens. Rebuilt 2026-10-10 (owner): a gallery first (every style drawn on the visitor's text, with
   A-Z / А-Я / 0-9 / symbol counts), then an editor for one style or the mix: Steam-sized preview, 7 slots (Steam's
   limit), icons in order with every option per slot, all icons of the game by group and colour, and "What to do" with
   the games to buy and the automatic fill through SteamShowcase Helper 1.2.1+ (bridge message
   APPLY_ACHIEVEMENT_LETTERS: [{appid, icon hash, letter, title, game} | null]; the extension matches each icon hash
   against the visitor's unlocked achievements and waits for Steam's Save). Steam drops empty slots on the profile
   (checked 2026-10-10: "HEL O" shows as "HELO"), so a space needs a blank icon of its own.
   Copy: the keyed COPY dictionary below, 8 languages (scripts/check_i18n.js). Debug hook: window.SMAchLetters. */
(function () {
  'use strict';
  var COPY = {
    en: { lead: 'Write a word with achievement icons on your Steam profile. Pick a style, adjust the letters and put it on the profile.',
      yourText: 'Your text', textPh: 'Up to 7 characters', counter: '{n}/7', examples: 'Try:', search: 'Find a game', gamesN: '{n} games',
      script: 'Alphabet', scriptAll: 'All', color: 'Colour', colorAll: 'All', c_red: 'Red', c_orange: 'Orange', c_yellow: 'Yellow', c_green: 'Green', c_blue: 'Blue', c_purple: 'Purple', c_pink: 'Pink', c_white: 'White', c_black: 'Black',
      mixName: 'Mix: fewest games', mixHint: 'Letters from different games, as few games as possible.', open: 'Open', wordCover: 'your text {a}/{b}', symbolsN: '+{n} symbols',
      more: 'Show more', noStyles: 'No game matches the search.', loading: 'Loading the catalogue…', failed: 'Could not load the catalogue. Try again later.',
      showcase: 'Achievement Showcase', statAch: 'Achievements', statPerfect: 'Perfect Games', statRate: 'Avg. Game Completion Rate', sample: 'Sample numbers: Steam shows your own.',
      back: 'All styles', store: 'Store', achievements: 'Achievements', slotsNote: 'The showcase holds 7 icons in a row. Steam removes empty slots, so a space needs an icon of its own.',
      order: 'Icons in order', orderHint: 'Click a slot to choose another icon for it.', options: '{n} options', noIcon: 'no icon', offColor: 'No icon in this colour: another colour is shown', noInGame: 'This game has no “{c}”', pickTitle: 'Icons for “{c}”', close: 'Close',
      allIcons: 'All icons of the game · {n}', allIconsMix: 'Icons of the games in your text', g_latin: 'Latin', g_cyr: 'Cyrillic', g_digits: 'Digits', g_symbols: 'Symbols',
      iconsHint: 'Click an icon: it replaces the same letter in your text or is added at the end.', full: 'The showcase holds only 7 icons.', space: 'space',
      todo: 'What to do', todoHint: 'Steam shows only achievements you have unlocked.', buy: 'Buy on Steam', percent: '{p}% of players', noPercent: 'share unknown', needGames: 'Games you need',
      how1: 'Get the games and unlock the achievement for each letter.', how2: 'On Steam open Edit Profile → Featured Showcase → Achievement Showcase.', how3: 'Click each slot, pick the game and the achievement in the order of your text, then press Save.',
      extTitle: 'Put it on the profile automatically', extReady: 'SteamShowcase Helper is connected{v}.', extAuto: 'Fill the showcase for me', extManual: 'Open Steam with a checklist',
      extNote: 'The extension opens your Steam editor, puts the letters you have unlocked into the Achievement Showcase and waits for you to press Save.',
      extMissing: 'Install the SteamShowcase Helper extension: it fills the Achievement Showcase for you.', extOld: 'Update SteamShowcase Helper to 1.2.1 or newer to fill the showcase automatically.',
      extInstall: 'Get the extension', extUpdate: 'How to update the extension', extChecking: 'Looking for the extension…', extOpened: 'Steam is open in a new tab: check the showcase there and press Save.',
      extFailed: 'The extension did not answer. Reload this page and try again.', extEmpty: 'Nothing to put yet: choose icons for your letters.', missingLetters: 'No icon for: {list}. Steam will skip them.' },
    ru: { lead: 'Напиши слово иконками достижений на своём профиле Steam. Выбери стиль, поправь буквы и поставь в профиль.',
      yourText: 'Ваш текст', textPh: 'До 7 символов', counter: '{n}/7', examples: 'Например:', search: 'Найти игру', gamesN: '{n} игр',
      script: 'Алфавит', scriptAll: 'Все', color: 'Цвет', colorAll: 'Все', c_red: 'Красный', c_orange: 'Оранжевый', c_yellow: 'Жёлтый', c_green: 'Зелёный', c_blue: 'Синий', c_purple: 'Фиолетовый', c_pink: 'Розовый', c_white: 'Белый', c_black: 'Чёрный',
      mixName: 'Микс: меньше всего игр', mixHint: 'Буквы из разных игр, игр — как можно меньше.', open: 'Открыть', wordCover: 'твой текст {a}/{b}', symbolsN: '+{n} символов',
      more: 'Показать ещё', noStyles: 'Игр по такому запросу нет.', loading: 'Загружаем каталог…', failed: 'Не получилось загрузить каталог. Попробуй позже.',
      showcase: 'Витрина достижений', statAch: 'Достижения', statPerfect: 'Идеальных игр', statRate: 'Ср. процент завершения игр', sample: 'Цифры для примера: Steam покажет твои.',
      back: 'Все стили', store: 'Магазин', achievements: 'Достижения', slotsNote: 'В витрине помещается 7 иконок подряд. Пустые ячейки Steam убирает, поэтому пробелу нужна своя иконка.',
      order: 'Иконки по порядку', orderHint: 'Нажми на ячейку, чтобы выбрать для неё другую иконку.', options: 'вариантов: {n}', noIcon: 'нет иконки', offColor: 'Нет иконки этого цвета: показан другой цвет', noInGame: 'В этой игре нет «{c}»', pickTitle: 'Иконки для «{c}»', close: 'Закрыть',
      allIcons: 'Все иконки игры · {n}', allIconsMix: 'Иконки игр из твоего текста', g_latin: 'Латиница', g_cyr: 'Кириллица', g_digits: 'Цифры', g_symbols: 'Символы',
      iconsHint: 'Нажми на иконку: она заменит такую же букву в тексте или добавится в конец.', full: 'В витрине помещается только 7 иконок.', space: 'пробел',
      todo: 'Что сделать', todoHint: 'Steam показывает только те достижения, которые ты получил.', buy: 'Купить в Steam', percent: 'есть у {p}% игроков', noPercent: 'доля неизвестна', needGames: 'Какие игры нужны',
      how1: 'Купи игры и получи в них достижение для каждой буквы.', how2: 'В Steam открой «Редактировать профиль» → «Витрина» → «Витрина достижений».', how3: 'Нажимай на ячейки по порядку, выбирай игру и достижение, затем нажми «Сохранить».',
      extTitle: 'Поставить в профиль автоматически', extReady: 'Расширение SteamShowcase Helper подключено{v}.', extAuto: 'Заполнить витрину за меня', extManual: 'Открыть Steam со списком',
      extNote: 'Расширение откроет редактор профиля Steam, поставит в витрину достижений буквы, которые у тебя уже есть, и дождётся, пока ты нажмёшь «Сохранить».',
      extMissing: 'Установи расширение SteamShowcase Helper — оно само заполнит витрину достижений.', extOld: 'Обнови SteamShowcase Helper до 1.2.1 или новее, чтобы витрина заполнялась автоматически.',
      extInstall: 'Установить расширение', extUpdate: 'Как обновить расширение', extChecking: 'Ищем расширение…', extOpened: 'Steam открыт в новой вкладке: проверь витрину и нажми «Сохранить».',
      extFailed: 'Расширение не ответило. Обнови эту страницу и попробуй ещё раз.', extEmpty: 'Пока нечего ставить: выбери иконки для букв.', missingLetters: 'Нет иконки для: {list}. Steam их пропустит.' },
    de: { lead: 'Schreib ein Wort mit Errungenschafts-Symbolen auf dein Steam-Profil. Wähle einen Stil, passe die Buchstaben an und setze es ins Profil.',
      yourText: 'Dein Text', textPh: 'Bis zu 7 Zeichen', counter: '{n}/7', examples: 'Beispiele:', search: 'Spiel suchen', gamesN: '{n} Spiele',
      script: 'Alphabet', scriptAll: 'Alle', color: 'Farbe', colorAll: 'Alle', c_red: 'Rot', c_orange: 'Orange', c_yellow: 'Gelb', c_green: 'Grün', c_blue: 'Blau', c_purple: 'Lila', c_pink: 'Rosa', c_white: 'Weiß', c_black: 'Schwarz',
      mixName: 'Mix: wenigste Spiele', mixHint: 'Buchstaben aus verschiedenen Spielen, möglichst wenige Spiele.', open: 'Öffnen', wordCover: 'dein Text {a}/{b}', symbolsN: '+{n} Symbole',
      more: 'Mehr zeigen', noStyles: 'Kein Spiel passt zur Suche.', loading: 'Katalog wird geladen…', failed: 'Der Katalog konnte nicht geladen werden. Versuche es später.',
      showcase: 'Errungenschafts-Präsentation', statAch: 'Errungenschaften', statPerfect: 'Perfekte Spiele', statRate: 'Durchschn. Abschlussrate', sample: 'Beispielzahlen: Steam zeigt deine eigenen.',
      back: 'Alle Stile', store: 'Shop', achievements: 'Errungenschaften', slotsNote: 'Die Präsentation fasst 7 Symbole in einer Reihe. Steam entfernt leere Plätze, ein Leerzeichen braucht also ein eigenes Symbol.',
      order: 'Symbole der Reihe nach', orderHint: 'Klicke auf einen Platz, um ein anderes Symbol dafür zu wählen.', options: '{n} Optionen', noIcon: 'kein Symbol', offColor: 'Kein Symbol in dieser Farbe: eine andere Farbe wird gezeigt', noInGame: 'Dieses Spiel hat kein „{c}“', pickTitle: 'Symbole für „{c}“', close: 'Schließen',
      allIcons: 'Alle Symbole des Spiels · {n}', allIconsMix: 'Symbole der Spiele in deinem Text', g_latin: 'Lateinisch', g_cyr: 'Kyrillisch', g_digits: 'Ziffern', g_symbols: 'Zeichen',
      iconsHint: 'Klicke auf ein Symbol: es ersetzt denselben Buchstaben im Text oder kommt ans Ende.', full: 'Die Präsentation fasst nur 7 Symbole.', space: 'Leerzeichen',
      todo: 'Was zu tun ist', todoHint: 'Steam zeigt nur Errungenschaften, die du freigeschaltet hast.', buy: 'Auf Steam kaufen', percent: '{p} % der Spieler', noPercent: 'Anteil unbekannt', needGames: 'Diese Spiele brauchst du',
      how1: 'Hol dir die Spiele und schalte für jeden Buchstaben die Errungenschaft frei.', how2: 'Öffne in Steam Profil bearbeiten → Präsentation → Errungenschafts-Präsentation.', how3: 'Klicke die Plätze der Reihe nach an, wähle Spiel und Errungenschaft und drücke dann Speichern.',
      extTitle: 'Automatisch ins Profil setzen', extReady: 'SteamShowcase Helper ist verbunden{v}.', extAuto: 'Präsentation für mich füllen', extManual: 'Steam mit Checkliste öffnen',
      extNote: 'Die Erweiterung öffnet deinen Steam-Editor, setzt die freigeschalteten Buchstaben in die Errungenschafts-Präsentation und wartet, bis du Speichern drückst.',
      extMissing: 'Installiere die Erweiterung SteamShowcase Helper: sie füllt die Errungenschafts-Präsentation für dich.', extOld: 'Aktualisiere SteamShowcase Helper auf 1.2.1 oder neuer, um die Präsentation automatisch zu füllen.',
      extInstall: 'Erweiterung holen', extUpdate: 'So aktualisierst du die Erweiterung', extChecking: 'Erweiterung wird gesucht…', extOpened: 'Steam ist in einem neuen Tab offen: prüfe die Präsentation dort und drücke Speichern.',
      extFailed: 'Die Erweiterung hat nicht geantwortet. Lade diese Seite neu und versuche es noch einmal.', extEmpty: 'Noch nichts zu setzen: wähle Symbole für deine Buchstaben.', missingLetters: 'Kein Symbol für: {list}. Steam lässt sie aus.' },
    tr: { lead: 'Steam profiline başarım simgeleriyle bir kelime yaz. Bir stil seç, harfleri ayarla ve profiline koy.',
      yourText: 'Metnin', textPh: 'En fazla 7 karakter', counter: '{n}/7', examples: 'Örnek:', search: 'Oyun bul', gamesN: '{n} oyun',
      script: 'Alfabe', scriptAll: 'Tümü', color: 'Renk', colorAll: 'Tümü', c_red: 'Kırmızı', c_orange: 'Turuncu', c_yellow: 'Sarı', c_green: 'Yeşil', c_blue: 'Mavi', c_purple: 'Mor', c_pink: 'Pembe', c_white: 'Beyaz', c_black: 'Siyah',
      mixName: 'Karışık: en az oyun', mixHint: 'Farklı oyunlardan harfler, olabildiğince az oyun.', open: 'Aç', wordCover: 'metnin {a}/{b}', symbolsN: '+{n} sembol',
      more: 'Daha fazla göster', noStyles: 'Aramaya uyan oyun yok.', loading: 'Katalog yükleniyor…', failed: 'Katalog yüklenemedi. Daha sonra tekrar dene.',
      showcase: 'Başarım Vitrini', statAch: 'Başarım', statPerfect: 'Mükemmel Oyun', statRate: 'Ort. Oyun Tamamlama Oranı', sample: 'Örnek sayılar: Steam seninkileri gösterir.',
      back: 'Tüm stiller', store: 'Mağaza', achievements: 'Başarımlar', slotsNote: 'Vitrine yan yana 7 simge sığar. Steam boş yuvaları kaldırır, bu yüzden boşluk için ayrı bir simge gerekir.',
      order: 'Sıradaki simgeler', orderHint: 'Başka bir simge seçmek için bir yuvaya tıkla.', options: '{n} seçenek', noIcon: 'simge yok', offColor: 'Bu renkte simge yok: başka bir renk gösteriliyor', noInGame: 'Bu oyunda “{c}” yok', pickTitle: '“{c}” için simgeler', close: 'Kapat',
      allIcons: 'Oyunun tüm simgeleri · {n}', allIconsMix: 'Metnindeki oyunların simgeleri', g_latin: 'Latin', g_cyr: 'Kiril', g_digits: 'Rakamlar', g_symbols: 'Semboller',
      iconsHint: 'Bir simgeye tıkla: metindeki aynı harfin yerine geçer ya da sona eklenir.', full: 'Vitrine yalnızca 7 simge sığar.', space: 'boşluk',
      todo: 'Yapılacaklar', todoHint: 'Steam yalnızca açtığın başarımları gösterir.', buy: 'Steam’de satın al', percent: 'oyuncuların %{p}’si', noPercent: 'oran bilinmiyor', needGames: 'Gereken oyunlar',
      how1: 'Oyunları al ve her harf için başarımı aç.', how2: 'Steam’de Profili Düzenle → Vitrin → Başarım Vitrini’ni aç.', how3: 'Yuvalara sırayla tıkla, oyunu ve başarımı metnindeki sırayla seç, sonra Kaydet’e bas.',
      extTitle: 'Profile otomatik koy', extReady: 'SteamShowcase Helper bağlı{v}.', extAuto: 'Vitrini benim için doldur', extManual: 'Steam’i kontrol listesiyle aç',
      extNote: 'Uzantı Steam düzenleyicini açar, açtığın harfleri Başarım Vitrini’ne koyar ve Kaydet’e basmanı bekler.',
      extMissing: 'SteamShowcase Helper uzantısını kur: Başarım Vitrini’ni senin için doldurur.', extOld: 'Vitrinin otomatik dolması için SteamShowcase Helper’ı 1.2.1 veya daha yeni sürüme güncelle.',
      extInstall: 'Uzantıyı al', extUpdate: 'Uzantı nasıl güncellenir', extChecking: 'Uzantı aranıyor…', extOpened: 'Steam yeni sekmede açık: vitrini orada kontrol et ve Kaydet’e bas.',
      extFailed: 'Uzantı yanıt vermedi. Bu sayfayı yenile ve tekrar dene.', extEmpty: 'Henüz konacak bir şey yok: harflerin için simge seç.', missingLetters: 'Simgesi olmayanlar: {list}. Steam bunları atlar.' },
    fr: { lead: 'Écris un mot avec des icônes de succès sur ton profil Steam. Choisis un style, ajuste les lettres et mets-le sur ton profil.',
      yourText: 'Ton texte', textPh: 'Jusqu’à 7 caractères', counter: '{n}/7', examples: 'Exemples :', search: 'Trouver un jeu', gamesN: '{n} jeux',
      script: 'Alphabet', scriptAll: 'Tous', color: 'Couleur', colorAll: 'Toutes', c_red: 'Rouge', c_orange: 'Orange', c_yellow: 'Jaune', c_green: 'Vert', c_blue: 'Bleu', c_purple: 'Violet', c_pink: 'Rose', c_white: 'Blanc', c_black: 'Noir',
      mixName: 'Mélange : le moins de jeux', mixHint: 'Des lettres de plusieurs jeux, le moins de jeux possible.', open: 'Ouvrir', wordCover: 'ton texte {a}/{b}', symbolsN: '+{n} symboles',
      more: 'Voir plus', noStyles: 'Aucun jeu ne correspond à la recherche.', loading: 'Chargement du catalogue…', failed: 'Impossible de charger le catalogue. Réessaie plus tard.',
      showcase: 'Vitrine des succès', statAch: 'Succès', statPerfect: 'Jeux parfaits', statRate: 'Taux moyen de réussite', sample: 'Chiffres d’exemple : Steam affiche les tiens.',
      back: 'Tous les styles', store: 'Boutique', achievements: 'Succès', slotsNote: 'La vitrine contient 7 icônes à la suite. Steam supprime les emplacements vides : un espace a besoin de sa propre icône.',
      order: 'Icônes dans l’ordre', orderHint: 'Clique sur un emplacement pour choisir une autre icône.', options: '{n} options', noIcon: 'pas d’icône', offColor: 'Pas d’icône de cette couleur : une autre couleur est affichée', noInGame: 'Ce jeu n’a pas de « {c} »', pickTitle: 'Icônes pour « {c} »', close: 'Fermer',
      allIcons: 'Toutes les icônes du jeu · {n}', allIconsMix: 'Icônes des jeux de ton texte', g_latin: 'Latin', g_cyr: 'Cyrillique', g_digits: 'Chiffres', g_symbols: 'Symboles',
      iconsHint: 'Clique sur une icône : elle remplace la même lettre dans ton texte ou s’ajoute à la fin.', full: 'La vitrine ne contient que 7 icônes.', space: 'espace',
      todo: 'À faire', todoHint: 'Steam n’affiche que les succès que tu as débloqués.', buy: 'Acheter sur Steam', percent: '{p} % des joueurs', noPercent: 'part inconnue', needGames: 'Les jeux nécessaires',
      how1: 'Procure-toi les jeux et débloque le succès de chaque lettre.', how2: 'Sur Steam, ouvre Modifier le profil → Vitrine → Vitrine des succès.', how3: 'Clique sur chaque emplacement dans l’ordre, choisis le jeu et le succès, puis Enregistrer.',
      extTitle: 'Le mettre sur le profil automatiquement', extReady: 'SteamShowcase Helper est connecté{v}.', extAuto: 'Remplir la vitrine pour moi', extManual: 'Ouvrir Steam avec une liste',
      extNote: 'L’extension ouvre ton éditeur Steam, place les lettres que tu as débloquées dans la vitrine des succès et attend que tu cliques sur Enregistrer.',
      extMissing: 'Installe l’extension SteamShowcase Helper : elle remplit la vitrine des succès pour toi.', extOld: 'Mets SteamShowcase Helper à jour (1.2.1 ou plus) pour remplir la vitrine automatiquement.',
      extInstall: 'Obtenir l’extension', extUpdate: 'Mettre à jour l’extension', extChecking: 'Recherche de l’extension…', extOpened: 'Steam est ouvert dans un nouvel onglet : vérifie la vitrine et clique sur Enregistrer.',
      extFailed: 'L’extension n’a pas répondu. Recharge cette page et réessaie.', extEmpty: 'Rien à placer pour l’instant : choisis des icônes pour tes lettres.', missingLetters: 'Pas d’icône pour : {list}. Steam les ignorera.' },
    uk: { lead: 'Напиши слово іконками досягнень на своєму профілі Steam. Вибери стиль, поправ літери й постав у профіль.',
      yourText: 'Ваш текст', textPh: 'До 7 символів', counter: '{n}/7', examples: 'Наприклад:', search: 'Знайти гру', gamesN: '{n} ігор',
      script: 'Абетка', scriptAll: 'Усі', color: 'Колір', colorAll: 'Усі', c_red: 'Червоний', c_orange: 'Помаранчевий', c_yellow: 'Жовтий', c_green: 'Зелений', c_blue: 'Синій', c_purple: 'Фіолетовий', c_pink: 'Рожевий', c_white: 'Білий', c_black: 'Чорний',
      mixName: 'Мікс: найменше ігор', mixHint: 'Літери з різних ігор, ігор — якомога менше.', open: 'Відкрити', wordCover: 'твій текст {a}/{b}', symbolsN: '+{n} символів',
      more: 'Показати ще', noStyles: 'Ігор за таким запитом немає.', loading: 'Завантажуємо каталог…', failed: 'Не вдалося завантажити каталог. Спробуй пізніше.',
      showcase: 'Вітрина досягнень', statAch: 'Досягнення', statPerfect: 'Ідеальних ігор', statRate: 'Сер. відсоток завершення ігор', sample: 'Цифри для прикладу: Steam покаже твої.',
      back: 'Усі стилі', store: 'Магазин', achievements: 'Досягнення', slotsNote: 'У вітрині вміщується 7 іконок поспіль. Порожні комірки Steam прибирає, тому пробілу потрібна своя іконка.',
      order: 'Іконки по порядку', orderHint: 'Натисни на комірку, щоб вибрати для неї іншу іконку.', options: 'варіантів: {n}', noIcon: 'немає іконки', offColor: 'Немає іконки цього кольору: показано інший колір', noInGame: 'У цій грі немає «{c}»', pickTitle: 'Іконки для «{c}»', close: 'Закрити',
      allIcons: 'Усі іконки гри · {n}', allIconsMix: 'Іконки ігор з твого тексту', g_latin: 'Латиниця', g_cyr: 'Кирилиця', g_digits: 'Цифри', g_symbols: 'Символи',
      iconsHint: 'Натисни на іконку: вона замінить таку саму літеру в тексті або додасться в кінець.', full: 'У вітрині вміщується лише 7 іконок.', space: 'пробіл',
      todo: 'Що зробити', todoHint: 'Steam показує лише ті досягнення, які ти отримав.', buy: 'Купити в Steam', percent: 'є у {p}% гравців', noPercent: 'частка невідома', needGames: 'Які ігри потрібні',
      how1: 'Купи ігри й отримай у них досягнення для кожної літери.', how2: 'У Steam відкрий «Редагувати профіль» → «Вітрина» → «Вітрина досягнень».', how3: 'Натискай на комірки по черзі, вибирай гру й досягнення, потім натисни «Зберегти».',
      extTitle: 'Поставити в профіль автоматично', extReady: 'Розширення SteamShowcase Helper підключено{v}.', extAuto: 'Заповнити вітрину за мене', extManual: 'Відкрити Steam зі списком',
      extNote: 'Розширення відкриє редактор профілю Steam, поставить у вітрину досягнень літери, які в тебе вже є, і дочекається, поки ти натиснеш «Зберегти».',
      extMissing: 'Встанови розширення SteamShowcase Helper — воно саме заповнить вітрину досягнень.', extOld: 'Онови SteamShowcase Helper до 1.2.1 або новішої, щоб вітрина заповнювалася автоматично.',
      extInstall: 'Встановити розширення', extUpdate: 'Як оновити розширення', extChecking: 'Шукаємо розширення…', extOpened: 'Steam відкрито в новій вкладці: перевір вітрину й натисни «Зберегти».',
      extFailed: 'Розширення не відповіло. Онови цю сторінку й спробуй ще раз.', extEmpty: 'Поки нічого ставити: вибери іконки для літер.', missingLetters: 'Немає іконки для: {list}. Steam їх пропустить.' },
    es: { lead: 'Escribe una palabra con iconos de logros en tu perfil de Steam. Elige un estilo, ajusta las letras y ponlo en tu perfil.',
      yourText: 'Tu texto', textPh: 'Hasta 7 caracteres', counter: '{n}/7', examples: 'Prueba:', search: 'Buscar un juego', gamesN: '{n} juegos',
      script: 'Alfabeto', scriptAll: 'Todos', color: 'Color', colorAll: 'Todos', c_red: 'Rojo', c_orange: 'Naranja', c_yellow: 'Amarillo', c_green: 'Verde', c_blue: 'Azul', c_purple: 'Morado', c_pink: 'Rosa', c_white: 'Blanco', c_black: 'Negro',
      mixName: 'Mezcla: menos juegos', mixHint: 'Letras de varios juegos, los menos posibles.', open: 'Abrir', wordCover: 'tu texto {a}/{b}', symbolsN: '+{n} símbolos',
      more: 'Ver más', noStyles: 'Ningún juego coincide con la búsqueda.', loading: 'Cargando el catálogo…', failed: 'No se pudo cargar el catálogo. Inténtalo más tarde.',
      showcase: 'Escaparate de logros', statAch: 'Logros', statPerfect: 'Juegos perfectos', statRate: 'Tasa media de finalización', sample: 'Números de ejemplo: Steam muestra los tuyos.',
      back: 'Todos los estilos', store: 'Tienda', achievements: 'Logros', slotsNote: 'El escaparate tiene 7 iconos seguidos. Steam quita los espacios vacíos, así que un espacio necesita su propio icono.',
      order: 'Iconos en orden', orderHint: 'Haz clic en un espacio para elegir otro icono.', options: '{n} opciones', noIcon: 'sin icono', offColor: 'No hay icono de este color: se muestra otro color', noInGame: 'Este juego no tiene «{c}»', pickTitle: 'Iconos para «{c}»', close: 'Cerrar',
      allIcons: 'Todos los iconos del juego · {n}', allIconsMix: 'Iconos de los juegos de tu texto', g_latin: 'Latín', g_cyr: 'Cirílico', g_digits: 'Dígitos', g_symbols: 'Símbolos',
      iconsHint: 'Haz clic en un icono: sustituye la misma letra de tu texto o se añade al final.', full: 'El escaparate solo tiene 7 iconos.', space: 'espacio',
      todo: 'Qué hacer', todoHint: 'Steam solo muestra los logros que has desbloqueado.', buy: 'Comprar en Steam', percent: '{p}% de los jugadores', noPercent: 'porcentaje desconocido', needGames: 'Juegos que necesitas',
      how1: 'Consigue los juegos y desbloquea el logro de cada letra.', how2: 'En Steam abre Editar perfil → Escaparate → Escaparate de logros.', how3: 'Haz clic en cada espacio en orden, elige el juego y el logro y pulsa Guardar.',
      extTitle: 'Ponerlo en el perfil automáticamente', extReady: 'SteamShowcase Helper está conectado{v}.', extAuto: 'Rellenar el escaparate por mí', extManual: 'Abrir Steam con una lista',
      extNote: 'La extensión abre tu editor de Steam, pone en el escaparate de logros las letras que ya tienes y espera a que pulses Guardar.',
      extMissing: 'Instala la extensión SteamShowcase Helper: rellena el escaparate de logros por ti.', extOld: 'Actualiza SteamShowcase Helper a 1.2.1 o posterior para rellenar el escaparate automáticamente.',
      extInstall: 'Obtener la extensión', extUpdate: 'Cómo actualizar la extensión', extChecking: 'Buscando la extensión…', extOpened: 'Steam está abierto en una pestaña nueva: revisa el escaparate y pulsa Guardar.',
      extFailed: 'La extensión no respondió. Recarga esta página e inténtalo de nuevo.', extEmpty: 'Aún no hay nada que poner: elige iconos para tus letras.', missingLetters: 'Sin icono para: {list}. Steam las omitirá.' },
    pt: { lead: 'Escreva uma palavra com ícones de conquistas no seu perfil Steam. Escolha um estilo, ajuste as letras e coloque no perfil.',
      yourText: 'Seu texto', textPh: 'Até 7 caracteres', counter: '{n}/7', examples: 'Experimente:', search: 'Encontrar um jogo', gamesN: '{n} jogos',
      script: 'Alfabeto', scriptAll: 'Todos', color: 'Cor', colorAll: 'Todas', c_red: 'Vermelho', c_orange: 'Laranja', c_yellow: 'Amarelo', c_green: 'Verde', c_blue: 'Azul', c_purple: 'Roxo', c_pink: 'Rosa', c_white: 'Branco', c_black: 'Preto',
      mixName: 'Mistura: menos jogos', mixHint: 'Letras de vários jogos, o mínimo de jogos possível.', open: 'Abrir', wordCover: 'seu texto {a}/{b}', symbolsN: '+{n} símbolos',
      more: 'Mostrar mais', noStyles: 'Nenhum jogo corresponde à busca.', loading: 'Carregando o catálogo…', failed: 'Não foi possível carregar o catálogo. Tente mais tarde.',
      showcase: 'Vitrine de conquistas', statAch: 'Conquistas', statPerfect: 'Jogos perfeitos', statRate: 'Taxa média de conclusão', sample: 'Números de exemplo: a Steam mostra os seus.',
      back: 'Todos os estilos', store: 'Loja', achievements: 'Conquistas', slotsNote: 'A vitrine comporta 7 ícones seguidos. A Steam remove espaços vazios, então um espaço precisa de um ícone próprio.',
      order: 'Ícones em ordem', orderHint: 'Clique em um espaço para escolher outro ícone.', options: '{n} opções', noIcon: 'sem ícone', offColor: 'Sem ícone desta cor: outra cor é mostrada', noInGame: 'Este jogo não tem «{c}»', pickTitle: 'Ícones para «{c}»', close: 'Fechar',
      allIcons: 'Todos os ícones do jogo · {n}', allIconsMix: 'Ícones dos jogos do seu texto', g_latin: 'Latino', g_cyr: 'Cirílico', g_digits: 'Números', g_symbols: 'Símbolos',
      iconsHint: 'Clique em um ícone: ele substitui a mesma letra do texto ou entra no final.', full: 'A vitrine comporta só 7 ícones.', space: 'espaço',
      todo: 'O que fazer', todoHint: 'A Steam mostra só as conquistas que você desbloqueou.', buy: 'Comprar na Steam', percent: '{p}% dos jogadores', noPercent: 'parcela desconhecida', needGames: 'Jogos necessários',
      how1: 'Pegue os jogos e desbloqueie a conquista de cada letra.', how2: 'Na Steam abra Editar perfil → Vitrine → Vitrine de conquistas.', how3: 'Clique em cada espaço na ordem, escolha o jogo e a conquista e depois Salvar.',
      extTitle: 'Colocar no perfil automaticamente', extReady: 'SteamShowcase Helper está conectado{v}.', extAuto: 'Preencher a vitrine para mim', extManual: 'Abrir a Steam com uma lista',
      extNote: 'A extensão abre seu editor da Steam, coloca na vitrine de conquistas as letras que você já tem e espera você clicar em Salvar.',
      extMissing: 'Instale a extensão SteamShowcase Helper: ela preenche a vitrine de conquistas para você.', extOld: 'Atualize o SteamShowcase Helper para 1.2.1 ou mais novo para preencher a vitrine automaticamente.',
      extInstall: 'Obter a extensão', extUpdate: 'Como atualizar a extensão', extChecking: 'Procurando a extensão…', extOpened: 'A Steam está aberta em uma nova aba: confira a vitrine e clique em Salvar.',
      extFailed: 'A extensão não respondeu. Recarregue esta página e tente de novo.', extEmpty: 'Nada para colocar ainda: escolha ícones para as letras.', missingLetters: 'Sem ícone para: {list}. A Steam vai pulá-las.' }
  };
  var DATA_URL = '/static/assets/achievements/letters.json?v=20261010-ach4';
  var STORE = 'sm_ach_letters';
  var EXT_ID = 'nopmeakgeongafdhgmlpllalpcfpedej';
  var EXT_MIN = '1.2.1';
  var SLOTS = 7;            // Steam's Achievement Showcase: 7 slots in one row
  var PAGE = 24;            // style cards per "Show more"
  var LATIN = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', CYRILLIC = 'АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ', DIGITS = '0123456789';
  var EXAMPLES = ['STEAM', 'GG WP', 'HELLO', 'GAMER', 'ПРИВЕТ', '2026'];
  var COLORS = ['red', 'orange', 'yellow', 'green', 'blue', 'purple', 'pink', 'white', 'black'];
  var SWATCH = { red: '#ef4444', orange: '#f59e0b', yellow: '#facc15', green: '#22c55e', blue: '#3b82f6', purple: '#a855f7', pink: '#ec4899', white: '#f8fafc', black: '#334155' };
  var SAMPLE_STATS = ['3 471', '12', '64%'];  // the preview's stats row is an example (Steam shows the visitor's own)
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
  function link(cls, text, url) { var a = el('a', cls, text); a.href = url; a.target = '_blank'; a.rel = 'noopener'; return a; }
  function storeUrl(appid) { return 'https://store.steampowered.com/app/' + appid + '/'; }
  function statsUrl(appid) { return 'https://steamcommunity.com/stats/' + appid + '/achievements/'; }
  function capsule(appid) { return 'https://cdn.cloudflare.steamstatic.com/steam/apps/' + appid + '/capsule_231x87.jpg'; }

  // view: gallery (every style drawn on the visitor's text) | editor (one style or the mix)
  var state = { text: 'STEAM', view: 'gallery', mode: 'all', color: 'all', script: 'all', query: '', shown: PAGE,
    slots: [], sel: null, picked: 1, iconColor: 'all', game: null, data: null, error: false, ext: { state: 'checking', version: '' }, notice: '' };
  try {
    var saved = JSON.parse(localStorage.getItem(STORE) || 'null');
    if (saved && typeof saved.text === 'string') { state.text = saved.text; state.color = COLORS.indexOf(saved.color) >= 0 ? saved.color : 'all'; }
  } catch (_) {}
  var refs = {};

  // ---------------------------------------------------------------- catalogue
  var sets = [], byApp = {}, symbolsAll = {};
  function group(c) { return DIGITS.indexOf(c) >= 0 ? 'digits' : (LATIN.indexOf(c) >= 0 || CYRILLIC.indexOf(c) >= 0) ? 'letters' : 'symbols'; }
  function charsOf(set, c) { return set && c != null ? (set[group(c)] || {})[c] : null; }
  function variantOf(slot) { var s = slot && byApp[slot.appid]; var list = s && charsOf(s, slot.c); return list ? list[slot.v] : null; }
  // Steam's icon hosts, tried in order (owner 2026-10-10): Fastly hosts (community.fastly / shared.steamstatic) did not
  // load for the owner, the old cdn.* path 404s for newer games; shared.akamai serves every game without a redirect.
  var ICON_HOSTS = ['https://shared.akamai.steamstatic.com/community_assets/images/apps/',
    'https://cdn.cloudflare.steamstatic.com/steamcommunity/public/images/apps/',
    'https://community.fastly.steamstatic.com/community_assets/images/apps/'];
  function icon(appid, variant, host) { return ICON_HOSTS[host || 0] + appid + '/' + variant[0] + '.jpg'; }
  // Sets an <img> to the icon and walks the hosts on errors; fail() runs when none of them answers.
  function setIcon(img, appid, variant, fail) {
    var host = 0;
    img.onerror = function () { host++; if (host < ICON_HOSTS.length) img.src = icon(appid, variant, host); else if (fail) fail(); };
    img.src = icon(appid, variant, 0);
    return img;
  }
  function load() {
    if (state.data || load.pending) return;
    load.pending = true;
    fetch(DATA_URL).then(function (r) { if (!r.ok) throw new Error('catalogue'); return r.json(); }).then(function (data) {
      state.data = data;
      sets = (data.sets || []).map(function (set) { set.symbols = set.symbols || {}; set.digits = set.digits || {}; return set; });
      sets.forEach(function (set) {
        byApp[set.appid] = set;
        Object.keys(set.symbols).forEach(function (c) { symbolsAll[c] = 1; });
        var keys = Object.keys(set.letters);
        set._latin = keys.filter(function (c) { return LATIN.indexOf(c) >= 0; }).length;
        set._cyr = keys.filter(function (c) { return CYRILLIC.indexOf(c) >= 0; }).length;
        set._icons = ['letters', 'digits', 'symbols'].reduce(function (n, g) { return n + Object.keys(set[g]).reduce(function (m, c) { return m + set[g][c].length; }, 0); }, 0);
      });
      state.text = clean(state.text);
      relayout(false);
      build();
    }).catch(function () { state.error = true; build(); }).then(function () { load.pending = false; });
  }

  // ---------------------------------------------------------------- the text and its slots
  // Allowed: Latin and Cyrillic letters, digits, a space and any symbol some game has as an achievement.
  function clean(text) {
    var out = '';
    Array.from(String(text || '').toUpperCase()).forEach(function (c) {
      if (out.length >= SLOTS) return;
      if (LATIN.indexOf(c) >= 0 || CYRILLIC.indexOf(c) >= 0 || DIGITS.indexOf(c) >= 0 || c === ' ' || symbolsAll[c]) out += c;
    });
    return out;
  }
  function chars() { return Array.from(state.text); }
  function unique() { var seen = {}; chars().forEach(function (c) { seen[c] = 1; }); return Object.keys(seen); }
  function colorOk(variant) { return state.color === 'all' || variant[3] === state.color; }
  function firstOk(set, c) {
    var list = charsOf(set, c) || [];
    for (var i = 0; i < list.length; i++) if (colorOk(list[i])) return i;
    return -1;
  }
  function easiness(set, list) {
    var sum = 0, n = 0;
    list.forEach(function (c) { var v = charsOf(set, c); if (v && v[0] && v[0][1] != null) { sum += v[0][1]; n++; } });
    return n ? sum / n : 0;
  }
  function pool() { return state.mode === 'all' ? sets : [byApp[state.mode]].filter(Boolean); }
  // Default icon per character: the chosen style, or the fewest games for the mix (greedy, ties go to the easier game).
  function planChars() {
    var picks = {}, rest = unique();
    if (state.mode !== 'all') {
      var only = byApp[state.mode];
      rest.forEach(function (c) {
        var v = only ? firstOk(only, c) : -1;
        if (v >= 0) picks[c] = { appid: only.appid, v: v };
        else { var f = fallback(only, c); if (f) picks[c] = { appid: f.appid, v: 0, off: true }; }
      });
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
    // Nothing in the chosen colour anywhere: the first game that has the character, dimmed.
    rest.forEach(function (c) {
      for (var i = 0; i < sets.length; i++) { var f = fallback(sets[i], c); if (f) { picks[c] = { appid: f.appid, v: 0, off: true }; return; } }
    });
    return picks;
  }
  // keep = leave slots whose character did not change (the visitor may have picked them by hand)
  function relayout(keep) {
    var picks = planChars(), old = state.slots;
    state.slots = chars().map(function (c, i) {
      var was = old[i];
      if (keep && was && was.c === c && was.appid && variantOf(was) && (state.mode === 'all' || String(was.appid) === String(state.mode))) return was;
      var p = picks[c];
      return p ? { c: c, appid: p.appid, v: p.v, off: !!p.off } : { c: c, appid: null, v: -1 };
    });
    if (state.sel != null && state.sel >= state.slots.length) state.sel = null;
  }
  function save() { try { localStorage.setItem(STORE, JSON.stringify({ text: state.text, color: state.color })); } catch (_) {} }
  function setText(text, keep) {
    state.text = clean(text);
    if (refs.input && refs.input.value !== state.text) refs.input.value = state.text;
    relayout(keep !== false); save();
    if (state.view === 'gallery') { paintCounter(); paintColors(); paintGallerySoon(); }
    else paintEditor();
  }
  // Every (game, variant) for a character in the current style (all styles for the mix), the current game first.
  function options(c, current) {
    var list = [];
    pool().forEach(function (set) { (charsOf(set, c) || []).forEach(function (variant, v) { if (colorOk(variant)) list.push({ c: c, appid: set.appid, v: v }); }); });
    // Nothing in the chosen colour: offer every colour rather than an empty picker.
    if (!list.length && state.color !== 'all') pool().forEach(function (set) { (charsOf(set, c) || []).forEach(function (variant, v) { list.push({ c: c, appid: set.appid, v: v, off: true }); }); });
    if (current && current.appid) list.sort(function (a, b) { return (b.appid === current.appid) - (a.appid === current.appid); });
    return list;
  }
  function coverage(set) {
    var wanted = unique().filter(function (c) { return c !== ' ' || symbolsAll[' ']; });
    return { have: wanted.filter(function (c) { return firstOk(set, c) >= 0; }).length, of: wanted.length };
  }
  function colorCounts() {
    var counts = {}, wanted = unique().length ? unique() : null;
    sets.forEach(function (set) {
      ['letters', 'digits', 'symbols'].forEach(function (g) {
        Object.keys(set[g]).forEach(function (c) {
          if (wanted && wanted.indexOf(c) < 0) return;
          set[g][c].forEach(function (v) { if (v[3]) counts[v[3]] = (counts[v[3]] || 0) + 1; });
        });
      });
    });
    return counts;
  }

  // ---------------------------------------------------------------- Steam showcase (shared by the cards and the editor)
  // slotsFor(set) = the text drawn in one style (cards); null = the editor's own slots.
  // A character the game has only in other colours is still shown (variant 0, `off`: dimmed, with a note), so an
  // empty cell always means the game has no such character (owner 2026-10-10: "why is it not always filled?").
  function fallback(set, c) { return set && (charsOf(set, c) || []).length ? { c: c, appid: set.appid, v: 0, off: true } : null; }
  function slotsFor(set) {
    return chars().map(function (c) {
      var v = set ? firstOk(set, c) : -1;
      return v >= 0 ? { c: c, appid: set.appid, v: v } : (fallback(set, c) || { c: c, appid: null, v: -1, none: !!set });
    });
  }
  function showcase(slots, opts) {
    opts = opts || {};
    var box = el('div', 'achl-sc' + (opts.big ? ' achl-sc--big' : ''));
    box.append(el('div', 'achl-sc__head', t('showcase')));
    var row = el('div', 'achl-sc__row');
    var list = slots.length ? slots : Array.from('ABC').map(function (c) { return { c: c, appid: null, v: -1 }; });
    list.forEach(function (slot, i) {
      var variant = variantOf(slot);
      var cell = opts.onSlot ? button('achl-sc__slot', null, function () { opts.onSlot(i); }) : el('span', 'achl-sc__slot');
      if (opts.onSlot) {
        cell.classList.toggle('is-sel', state.sel === i);
        cell.setAttribute('aria-pressed', state.sel === i ? 'true' : 'false');
        cell.title = variant ? byApp[slot.appid].name + ' · «' + variant[2] + '»' : (slot.c === ' ' ? t('space') : slot.c) + ' · ' + t('noIcon');
      }
      if (slot.off) { cell.classList.add('is-off'); cell.title = (cell.title ? cell.title + ' · ' : '') + t('offColor'); }
      else if (slot.none && !opts.onSlot) cell.title = t('noInGame', { c: slot.c === ' ' ? t('space') : slot.c });
      if (variant) {
        var img = el('img'); img.alt = slot.c; img.width = 64; img.height = 64; if (!opts.big) img.loading = 'lazy';
        setIcon(img, slot.appid, variant, function () { img.replaceWith(el('b', 'achl-sc__miss', slot.c)); });
        cell.append(img);
      } else {
        cell.classList.add('is-missing');
        cell.append(el('b', 'achl-sc__miss', slot.c === ' ' ? '␣' : slot.c));
      }
      row.append(cell);
    });
    box.append(row);
    if (opts.stats) {
      var stats = el('div', 'achl-sc__stats');
      [[SAMPLE_STATS[0], t('statAch')], [SAMPLE_STATS[1], t('statPerfect')], [SAMPLE_STATS[2], t('statRate')]].forEach(function (s) {
        var item = el('div', 'achl-sc__stat'); item.append(el('b', '', s[0]), el('small', '', s[1])); stats.append(item);
      });
      box.append(stats);
    }
    return box;
  }

  // ---------------------------------------------------------------- build
  function build() {
    host.replaceChildren();
    var root = el('div', 'achl');
    refs = {};
    if (!state.data) {
      root.append(el('div', 'achl-panel achl-note', state.error ? t('failed') : t('loading')));
      host.append(root);
      return;
    }
    if (state.view === 'editor') buildEditor(root); else buildGallery(root);
    host.append(root);
  }
  function textBox() {
    var box = el('div', 'achl-text');
    var label = el('label', 'achl-text__label');
    var input = el('input', 'achl-text__input'); input.maxLength = SLOTS; input.value = state.text; input.placeholder = t('textPh');
    input.autocomplete = 'off'; input.spellcheck = false;
    input.addEventListener('input', function () {
      var pos = input.selectionStart;
      setText(input.value);
      if (input.value !== state.text) { input.value = state.text; try { input.setSelectionRange(pos, pos); } catch (_) {} }
    });
    refs.input = input;
    refs.counter = el('span', 'achl-text__count');
    label.append(el('span', 'achl-text__title', t('yourText')), refs.counter);
    box.append(label, input);
    return box;
  }
  function paintCounter() { if (refs.counter) { refs.counter.textContent = t('counter', { n: chars().length }); refs.counter.classList.toggle('is-full', chars().length >= SLOTS); } }

  // ---- gallery
  function buildGallery(root) {
    var top = el('section', 'achl-panel achl-top');
    var intro = el('div', 'achl-top__intro');
    intro.append(el('p', 'achl-lead', t('lead')));
    var examples = el('div', 'achl-examples');
    examples.append(el('span', '', t('examples')));
    EXAMPLES.forEach(function (w) { examples.append(button('achl-chip', w, function () { setText(w, false); })); });
    var filters = el('div', 'achl-filters');
    var search = el('input', 'achl-field achl-search'); search.type = 'search'; search.placeholder = t('search'); search.value = state.query;
    search.setAttribute('aria-label', t('search'));
    search.addEventListener('input', function () { state.query = search.value; state.shown = PAGE; paintGallerySoon(); });
    refs.count = el('span', 'achl-count');
    refs.scripts = el('div', 'achl-seg');
    [['all', t('scriptAll')], ['latin', 'A–Z'], ['cyr', 'А–Я']].forEach(function (s) {
      var b = button('achl-seg__btn' + (state.script === s[0] ? ' is-on' : ''), s[1], function () {
        state.script = s[0]; state.shown = PAGE;
        refs.scripts.querySelectorAll('.achl-seg__btn').forEach(function (n) { n.classList.toggle('is-on', n === b); n.setAttribute('aria-pressed', n === b ? 'true' : 'false'); });
        paintGallery();
      });
      b.setAttribute('aria-pressed', state.script === s[0] ? 'true' : 'false');
      refs.scripts.append(b);
    });
    refs.colors = el('div', 'achl-colors');
    filters.append(search, refs.scripts, refs.count);
    top.append(intro, textBox(), examples, filters, refs.colors);
    refs.grid = el('div', 'achl-grid');
    refs.more = button('achl-btn achl-more', t('more'), function () { state.shown += PAGE; paintGallery(); });
    root.append(top, refs.grid, refs.more);
    paintCounter(); paintColors(); paintGallery();
  }
  function paintColors() {
    if (!refs.colors) return;
    var counts = colorCounts();
    if (state.color !== 'all' && !counts[state.color]) state.color = 'all';
    refs.colors.replaceChildren(el('span', 'achl-colors__label', t('color')));
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
  function setColor(name) { state.color = name; save(); relayout(false); paintColors(); paintGallery(); }
  function paintGallerySoon() { clearTimeout(paintGallerySoon.timer); paintGallerySoon.timer = setTimeout(paintGallery, 120); }
  function galleryList() {
    var q = state.query.trim().toLowerCase();
    var list = sets.filter(function (set) {
      if (q && set.name.toLowerCase().indexOf(q) < 0) return false;
      if (state.script === 'latin' && set._latin < 20) return false;
      if (state.script === 'cyr' && set._cyr < 20) return false;
      return true;
    }).map(function (set) { return { set: set, cover: coverage(set) }; });
    list.sort(function (a, b) {
      return (b.cover.have - a.cover.have) || (easiness(b.set, unique()) - easiness(a.set, unique())) || a.set.name.localeCompare(b.set.name);
    });
    if (state.color !== 'all') list = list.filter(function (item) { return item.cover.have > 0; });
    return list;
  }
  function paintGallery() {
    if (!refs.grid) return;
    var list = galleryList(), q = state.query.trim();
    refs.grid.replaceChildren();
    refs.count.textContent = t('gamesN', { n: list.length });
    if (!q && state.script === 'all') refs.grid.append(card(null));
    if (!list.length) refs.grid.append(el('p', 'achl-hint achl-grid__empty', t('noStyles')));
    list.slice(0, state.shown).forEach(function (item) { refs.grid.append(card(item.set, item.cover)); });
    refs.more.hidden = list.length <= state.shown;
  }
  // One style card: the visitor's text in this style on a Steam-like panel over the game's art.
  function card(set, cover) {
    var item = el('article', 'achl-card' + (set ? '' : ' achl-card--mix'));
    if (set) item.style.setProperty('--achl-art', 'url("' + capsule(set.appid) + '")');
    var slots = set ? slotsFor(set) : state.slots;   // the gallery always plans the mix (state.mode = all)
    item.append(showcase(slots));
    var body = el('div', 'achl-card__body');
    var title = el('div', 'achl-card__title');
    title.append(el('b', '', set ? set.name : t('mixName')));
    if (set && cover && cover.of) title.append(el('span', 'achl-badge' + (cover.have === cover.of ? ' achl-badge--full' : ''), t('wordCover', { a: cover.have, b: cover.of })));
    body.append(title);
    if (set) {
      var facts = el('div', 'achl-card__facts');
      if (set._latin) facts.append(el('span', '', 'A–Z ' + set._latin + '/26'));
      if (set._cyr) facts.append(el('span', '', 'А–Я ' + set._cyr + '/33'));
      var digits = Object.keys(set.digits).length;
      if (digits) facts.append(el('span', '', '0–9 ' + digits + '/10'));
      var symbols = Object.keys(set.symbols).length;
      if (symbols) facts.append(el('span', '', t('symbolsN', { n: symbols })));
      body.append(facts);
    } else body.append(el('small', 'achl-card__hint', t('mixHint')));
    item.append(body);
    // The whole card opens the editor (owner 2026-10-10: no separate "Open" button).
    var open = function () { openEditor(set ? set.appid : 'all'); };
    item.tabIndex = 0;
    item.setAttribute('role', 'button');
    item.setAttribute('aria-label', t('open') + ': ' + (set ? set.name : t('mixName')));
    item.addEventListener('click', open);
    item.addEventListener('keydown', function (event) { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); open(); } });
    return item;
  }

  // ---- editor
  function openEditor(mode) {
    state.mode = mode === 'all' ? 'all' : String(mode);
    state.view = 'editor'; state.sel = null; state.picked = 1; state.game = null; state.notice = '';
    relayout(false); build(); scrollTop();
  }
  function closeEditor() { state.view = 'gallery'; state.mode = 'all'; state.sel = null; relayout(false); build(); scrollTop(); }
  // Back to the top of the tool, below the sticky site header + tools strip (--achl-sticky).
  function scrollTop() {
    var top = host.getBoundingClientRect().top;
    if (top < 130) window.scrollTo({ top: Math.max(0, window.scrollY + top - 130), behavior: 'instant' });
  }
  function usedGames() {
    var seen = [];
    state.slots.forEach(function (s) { if (s.appid && seen.indexOf(s.appid) < 0) seen.push(s.appid); });
    return seen;
  }
  function buildEditor(root) {
    var set = state.mode !== 'all' && byApp[state.mode];
    var bar = el('div', 'achl-ed__bar');
    bar.append(button('achl-btn achl-back', '← ' + t('back'), closeEditor));
    var name = el('div', 'achl-ed__name');
    name.append(el('b', '', set ? set.name : t('mixName')));
    if (set) name.append(el('small', '', [set._latin ? 'A–Z ' + set._latin + '/26' : '', set._cyr ? 'А–Я ' + set._cyr + '/33' : '',
      Object.keys(set.digits).length ? '0–9 ' + Object.keys(set.digits).length + '/10' : ''].filter(Boolean).join(' · ')));
    bar.append(name);
    if (set) {
      var links = el('div', 'achl-ed__links');
      links.append(link('achl-link', t('store') + ' ↗', storeUrl(set.appid)), link('achl-link', t('achievements') + ' ↗', statsUrl(set.appid)));
      bar.append(links);
    }
    var grid = el('div', 'achl-ed');
    var main = el('div', 'achl-ed__main');
    refs.preview = el('section', 'achl-panel achl-pv');
    var edit = el('section', 'achl-panel achl-edit');
    edit.append(textBox(), el('p', 'achl-hint', t('slotsNote')));
    refs.order = el('div', 'achl-order');
    refs.picker = el('div', 'achl-picker');
    edit.append(el('h3', 'achl-h', t('order')), el('p', 'achl-hint', t('orderHint')), refs.order, refs.picker);
    refs.all = el('section', 'achl-panel achl-all');
    main.append(refs.preview, edit, refs.all);
    refs.todo = el('aside', 'achl-panel achl-todo');
    grid.append(main, refs.todo);
    root.append(bar, grid);
    paintEditor();
    pingExtension();
  }
  function paintEditor() {
    if (state.view !== 'editor' || !refs.preview) return;
    paintCounter();
    var first = usedGames()[0];
    refs.preview.style.setProperty('--achl-art', first ? 'url("' + capsule(first) + '")' : 'none');
    refs.preview.replaceChildren(showcase(state.slots, { big: true, stats: true, onSlot: selectSlot }), el('p', 'achl-pv__note', t('sample')));
    paintOrder(); paintPicker(); paintAll(); paintTodo();
  }
  function selectSlot(i) { state.sel = state.sel === i ? null : i; state.picked = 1; paintEditor(); }
  function paintOrder() {
    refs.order.replaceChildren();
    state.slots.forEach(function (slot, i) {
      var variant = variantOf(slot), n = options(slot.c, slot).length;
      var item = button('achl-order__item' + (state.sel === i ? ' is-sel' : '') + (variant ? '' : ' is-missing'), null, function () { selectSlot(i); });
      item.setAttribute('aria-pressed', state.sel === i ? 'true' : 'false');
      var pic = el('span', 'achl-order__pic');
      if (variant) { var img = el('img'); img.alt = slot.c; img.width = 44; img.height = 44; pic.append(setIcon(img, slot.appid, variant)); }
      else pic.append(el('b', '', slot.c === ' ' ? '␣' : slot.c));
      var text = el('span', 'achl-order__text');
      text.append(el('b', '', (i + 1) + ' · ' + (slot.c === ' ' ? t('space') : slot.c)), el('small', '', variant ? (slot.off ? t('offColor') : t('options', { n: n })) : t('noIcon')));
      if (slot.off) item.classList.add('is-off');
      item.append(pic, text);
      refs.order.append(item);
    });
  }
  function paintPicker() {
    var slot = state.sel != null ? state.slots[state.sel] : null;
    refs.picker.replaceChildren();
    refs.picker.hidden = !slot;
    if (!slot) return;
    var opts = options(slot.c, slot);
    var head = el('div', 'achl-picker__head');
    var title = el('div');
    title.append(el('b', '', t('pickTitle', { c: slot.c === ' ' ? t('space') : slot.c })), el('small', '', t('options', { n: opts.length })));
    var close = button('achl-picker__close', '×', function () { state.sel = null; paintEditor(); });
    close.setAttribute('aria-label', t('close'));
    head.append(title, close);
    var grid = el('div', 'achl-icons');
    opts.slice(0, 60 * state.picked).forEach(function (o) {
      var s = byApp[o.appid], v = charsOf(s, o.c)[o.v];
      var on = slot.appid === o.appid && slot.v === o.v;
      var tile = button('achl-icon' + (on ? ' is-on' : ''), null, function () { state.slots[state.sel] = o; paintEditor(); });
      var img = el('img'); img.alt = o.c; img.loading = 'lazy'; img.width = 52; img.height = 52;
      setIcon(img, o.appid, v, function () { tile.remove(); });
      tile.append(img, el('small', '', v[1] != null ? v[1] + '%' : '—'));
      tile.title = s.name + ' · «' + v[2] + '»' + (v[1] != null ? ' · ' + t('percent', { p: v[1] }) : '');
      grid.append(tile);
    });
    var more = button('achl-btn achl-more', t('more'), function () { state.picked++; paintPicker(); });
    more.hidden = opts.length <= 60 * state.picked;
    refs.picker.append(head, grid, more);
  }
  // Every icon of one game, grouped; a click replaces the same character in the text or appends it.
  function paintAll() {
    var games = state.mode !== 'all' ? [Number(state.mode)] : usedGames();
    if (!games.length) { refs.all.hidden = true; return; }
    refs.all.hidden = false;
    if (games.indexOf(state.game) < 0) state.game = games[0];
    var set = byApp[state.game];
    refs.all.replaceChildren();
    var head = el('div', 'achl-all__head');
    head.append(el('h3', 'achl-h', state.mode !== 'all' ? t('allIcons', { n: set._icons }) : t('allIconsMix')));
    if (games.length > 1) {
      var tabs = el('div', 'achl-seg');
      games.forEach(function (appid) {
        var b = button('achl-seg__btn' + (appid === state.game ? ' is-on' : ''), byApp[appid].name, function () { state.game = appid; paintAll(); });
        b.setAttribute('aria-pressed', appid === state.game ? 'true' : 'false');
        tabs.append(b);
      });
      head.append(tabs);
    }
    var counts = {};
    ['letters', 'digits', 'symbols'].forEach(function (g) { Object.keys(set[g]).forEach(function (c) { set[g][c].forEach(function (v) { if (v[3]) counts[v[3]] = (counts[v[3]] || 0) + 1; }); }); });
    if (state.iconColor !== 'all' && !counts[state.iconColor]) state.iconColor = 'all';
    var colors = el('div', 'achl-colors');
    var all = button('achl-color achl-color--all' + (state.iconColor === 'all' ? ' is-on' : ''), t('colorAll'), function () { state.iconColor = 'all'; paintAll(); });
    colors.append(el('span', 'achl-colors__label', t('color')), all);
    COLORS.forEach(function (name) {
      if (!counts[name]) return;
      var chip = button('achl-color' + (state.iconColor === name ? ' is-on' : ''), null, function () { state.iconColor = name; paintAll(); });
      chip.style.setProperty('--swatch', SWATCH[name]);
      chip.append(el('i'), el('span', '', t('c_' + name) + ' · ' + counts[name]));
      chip.setAttribute('aria-pressed', state.iconColor === name ? 'true' : 'false');
      colors.append(chip);
    });
    refs.all.append(head, el('p', 'achl-hint', t('iconsHint')), colors);
    var groups = [
      ['g_latin', Object.keys(set.letters).filter(function (c) { return LATIN.indexOf(c) >= 0; }).sort(), 'letters'],
      ['g_cyr', Object.keys(set.letters).filter(function (c) { return CYRILLIC.indexOf(c) >= 0; }).sort(function (a, b) { return CYRILLIC.indexOf(a) - CYRILLIC.indexOf(b); }), 'letters'],
      ['g_digits', Object.keys(set.digits).sort(), 'digits'],
      ['g_symbols', Object.keys(set.symbols), 'symbols']
    ];
    groups.forEach(function (g) {
      var tiles = [];
      g[1].forEach(function (c) {
        set[g[2]][c].forEach(function (v, index) {
          if (state.iconColor !== 'all' && v[3] !== state.iconColor) return;
          var inText = state.slots.some(function (s) { return s.appid === set.appid && s.c === c && s.v === index; });
          var tile = button('achl-icon achl-icon--plain' + (inText ? ' is-on' : ''), null, function () { putIcon({ c: c, appid: set.appid, v: index }); });
          var img = el('img'); img.alt = c; img.loading = 'lazy'; img.width = 48; img.height = 48;
          setIcon(img, set.appid, v, function () { tile.remove(); });
          tile.append(img, el('small', '', c === ' ' ? '␣' : c));
          tile.title = c + ' · «' + v[2] + '»' + (v[1] != null ? ' · ' + t('percent', { p: v[1] }) : '');
          tiles.push(tile);
        });
      });
      if (!tiles.length) return;
      var box = el('div', 'achl-all__group');
      box.append(el('h4', 'achl-sub', t(g[0]) + ' · ' + tiles.length));
      var grid = el('div', 'achl-icons achl-icons--dense');
      tiles.forEach(function (tile) { grid.append(tile); });
      box.append(grid);
      refs.all.append(box);
    });
    if (state.notice) refs.all.append(el('p', 'achl-warn', state.notice));
  }
  function putIcon(pick) {
    state.notice = '';
    var at = state.sel != null && state.slots[state.sel] && state.slots[state.sel].c === pick.c ? state.sel : -1;
    if (at < 0) at = state.slots.findIndex(function (s) { return s.c === pick.c; });
    if (at >= 0) state.slots[at] = pick;
    else if (state.slots.length < SLOTS) {
      state.slots.push(pick); state.text += pick.c; save();
      if (refs.input) refs.input.value = state.text;
    } else { state.notice = t('full'); paintAll(); return; }
    paintEditor();
  }

  // ---- what to do + the extension
  function paintTodo() {
    var box = refs.todo;
    box.replaceChildren(el('h3', 'achl-h', t('todo')), el('p', 'achl-hint', t('todoHint')));
    refs.ext = el('div', 'achl-ext');
    box.append(refs.ext);
    paintExt();
    var list = el('ol', 'achl-need');
    state.slots.forEach(function (slot) {
      var variant = variantOf(slot);
      var li = el('li', 'achl-need__item' + (variant ? '' : ' is-missing'));
      var pic = el('span', 'achl-need__pic');
      if (variant) { var img = el('img'); img.alt = slot.c; img.width = 36; img.height = 36; pic.append(setIcon(img, slot.appid, variant)); }
      else pic.append(el('b', '', slot.c === ' ' ? '␣' : slot.c));
      var text = el('div', 'achl-need__text');
      if (variant) {
        text.append(el('b', '', '«' + variant[2] + '»'), el('small', '', byApp[slot.appid].name + ' · ' + (variant[1] != null ? t('percent', { p: variant[1] }) : t('noPercent'))));
      } else text.append(el('b', '', slot.c === ' ' ? t('space') : slot.c), el('small', '', t('noIcon')));
      li.append(pic, text);
      list.append(li);
    });
    box.append(list);
    var games = usedGames();
    if (games.length) {
      box.append(el('h4', 'achl-sub', t('needGames')));
      var gl = el('div', 'achl-games');
      games.forEach(function (appid) {
        var set = byApp[appid], item = el('article', 'achl-game');
        var cap = el('img', 'achl-game__cap'); cap.src = capsule(appid); cap.alt = ''; cap.loading = 'lazy';
        cap.onerror = function () { cap.replaceWith(el('span', 'achl-game__cap achl-game__cap--none', set.name.slice(0, 1))); };
        var body = el('div', 'achl-game__body');
        body.append(el('b', '', set.name));
        var links = el('div', 'achl-game__links');
        links.append(link('achl-link achl-link--buy', t('buy') + ' ↗', storeUrl(appid)), link('achl-link', t('achievements') + ' ↗', statsUrl(appid)));
        body.append(links);
        item.append(cap, body);
        gl.append(item);
      });
      box.append(gl);
    }
    var how = el('ol', 'achl-how');
    ['how1', 'how2', 'how3'].forEach(function (k) { how.append(el('li', '', t(k))); });
    box.append(how);
  }
  function versionAtLeast(value, minimum) {
    var a = String(value || '').split('.').map(Number), b = String(minimum).split('.').map(Number);
    for (var i = 0; i < Math.max(a.length, b.length); i++) { var x = a[i] || 0, y = b[i] || 0; if (x !== y) return x > y; }
    return true;
  }
  // Same bridge as steam-extension-status.js: the content script relay first, then the Web Store id directly.
  function bridge(message) {
    return new Promise(function (resolve, reject) {
      var id = 'ssh-letters-' + Date.now() + '-' + Math.random().toString(36).slice(2);
      var done = false;
      function finish(ok, value) { if (done) return; done = true; clearTimeout(timer); window.removeEventListener('message', receive); ok ? resolve(value) : reject(value); }
      function receive(event) {
        var data = event.data || {};
        if (event.source === window && event.origin === location.origin && data.source === 'SSH_EXTENSION' && data.type === 'RESPONSE' && data.requestId === id) finish(true, data.reply || {});
      }
      window.addEventListener('message', receive);
      var timer = setTimeout(function () { finish(false, new Error('bridge')); }, 1500);
      window.postMessage({ source: 'SSH_SITE', type: 'REQUEST', requestId: id, payload: message }, location.origin);
    });
  }
  function direct(message) {
    return new Promise(function (resolve, reject) {
      if (!window.chrome || !chrome.runtime || !chrome.runtime.sendMessage) { reject(new Error('missing')); return; }
      try { chrome.runtime.sendMessage(EXT_ID, message, function (reply) { if (chrome.runtime.lastError) reject(chrome.runtime.lastError); else resolve(reply || {}); }); }
      catch (error) { reject(error); }
    });
  }
  function extMessage(message) { return bridge(message).catch(function () { return direct(message); }); }
  function pingExtension() {
    if (state.ext.state === 'ready') { paintExt(); return; }
    state.ext = { state: 'checking', version: '' }; paintExt();
    extMessage({ type: 'PING' }).then(function (reply) {
      if (!reply || !reply.ok) throw new Error('missing');
      var ok = (reply.features || []).indexOf('achievement_letters') >= 0 || versionAtLeast(reply.version, EXT_MIN);
      state.ext = { state: ok ? 'ready' : 'old', version: String(reply.version || '') };
    }).catch(function () { state.ext = { state: 'missing', version: '' }; }).then(paintExt);
  }
  function extPicks() {
    return state.slots.map(function (slot) {
      var variant = variantOf(slot);
      return variant ? { appid: slot.appid, icon: variant[0], letter: slot.c, title: variant[2], game: byApp[slot.appid].name } : null;
    });
  }
  function paintExt(status) {
    var box = refs.ext;
    if (!box) return;
    box.replaceChildren(el('b', 'achl-ext__title', t('extTitle')));
    var guide = '/' + lang() + '/extension';
    var missing = state.slots.filter(function (s) { return !variantOf(s); }).map(function (s) { return s.c === ' ' ? t('space') : s.c; });
    if (state.ext.state === 'checking') { box.append(el('p', 'achl-hint', t('extChecking'))); return; }
    if (state.ext.state !== 'ready') {
      box.append(el('p', 'achl-hint', t(state.ext.state === 'old' ? 'extOld' : 'extMissing')),
        link('achl-btn achl-btn--primary', t(state.ext.state === 'old' ? 'extUpdate' : 'extInstall'), guide));
      return;
    }
    box.append(el('p', 'achl-ext__ok', t('extReady', { v: state.ext.version ? ' · v' + state.ext.version : '' })), el('p', 'achl-hint', t('extNote')));
    if (missing.length) box.append(el('p', 'achl-warn', t('missingLetters', { list: missing.join(', ') })));
    var actions = el('div', 'achl-ext__actions');
    var auto = button('achl-btn achl-btn--primary', t('extAuto'), function () { apply('auto', auto); });
    var manual = button('achl-btn', t('extManual'), function () { apply('manual', manual); });
    if (!extPicks().some(Boolean)) { auto.disabled = true; manual.disabled = true; }
    actions.append(auto, manual);
    box.append(actions);
    if (status) box.append(el('p', status.bad ? 'achl-warn' : 'achl-ext__ok', status.text));
  }
  function apply(mode, trigger) {
    var picks = extPicks();
    if (!picks.some(Boolean)) { paintExt({ bad: true, text: t('extEmpty') }); return; }
    if (trigger) trigger.disabled = true;
    extMessage({ type: 'APPLY_ACHIEVEMENT_LETTERS', mode: mode, word: state.text, picks: picks }).then(function (reply) {
      if (!reply || !reply.ok) throw new Error(reply && reply.error || 'failed');
      paintExt({ text: t('extOpened') });
    }).catch(function () { paintExt({ bad: true, text: t('extFailed') }); });
  }

  // ---------------------------------------------------------------- start: load when the tab is first opened
  function tabOpen() { var tab = document.getElementById('tab-letters'); return tab && tab.classList.contains('active'); }
  build();
  if (tabOpen()) load();
  document.addEventListener('click', function (event) {
    var b = event.target.closest && event.target.closest('[data-tab="letters"]');
    if (b) setTimeout(load, 0);
  });
  if (/#letters\b/.test(location.hash)) load();
  window.addEventListener('sm:langchange', build);
  window.SMAchLetters = { state: state, load: load, open: function (mode) { if (state.data) openEditor(mode); }, back: function () { if (state.data) closeEditor(); },
    setText: function (text) { if (state.data) setText(text, false); }, setColor: function (c) { if (state.data) setColor(c); }, picks: extPicks, apply: apply, clean: clean };
})();
