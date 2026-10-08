/* Info box tab (#tab-infobox, owner 2026-10-08): templates for Steam's "Custom Info Box" showcase.
   Two views: "Templates" (search, categories, big cards that look like the Steam box) and "Editor" (text with BBCode
   buttons next to a live Steam preview, copy buttons on top, tools for symbols / picture to text / sharing).
   Preview = Steam's numbers: 640 px column, 13 px text on 18 px lines, 604 px content, ~600 px visible height.
   Our own templates live in static/js/infobox-templates.js (window.SM_INFOBOX_TEMPLATES, EN + RU; uk reads RU, other
   languages EN). Community templates: /api/infobox/templates (smweb/infobox.py). Nothing copied from other sites:
   "More templates" only links to Steam's ASCII art community.
   Copy: the keyed COPY dictionary below, 8 languages (checked by scripts/check_i18n.js). Draft: localStorage sm_infobox_draft. */
(function () {
  'use strict';
  var COPY = {
    en: {
      lead: 'Ready-made designs for Steam’s “Custom Info Box”. Pick one, change the text and copy it into your profile.',
      step1: 'Choose a template', step2: 'Change the text', step3: 'Copy it to Steam', search: 'Search templates',
      blank: 'Blank page', draft: 'My draft', back: 'All templates', count: '{n} templates', noResults: 'Nothing found. Try another word or category.',
      catAll: 'All', catAbout: 'About me', catFrames: 'Frames', catGames: 'Games', catStream: 'Links & streams', catQuotes: 'Quotes & status',
      catAesthetic: 'Aesthetic', catHoliday: 'Holidays', catArt: 'Symbol art', catFun: 'Fun', catCommunity: 'Community', catOther: 'Other',
      useTpl: 'Use template', by: 'by', uses: 'used {n}', del: 'Delete', loading: 'Loading…', empty: 'No community templates yet. Be the first!',
      more: 'Show more', sortNew: 'New', sortPopular: 'Popular', communityCta: 'Share your own template',
      boxTitle: 'Showcase title', boxTitleDefault: 'About me', textLabel: 'Text', tbH1: 'Heading', tbB: 'Bold', tbI: 'Italic', tbU: 'Underline',
      tbS: 'Strikethrough', tbSpoiler: 'Spoiler', tbHr: 'Line', tbUrl: 'Link', clear: 'Clear',
      toolsSymbols: 'Symbols', toolsArt: 'Picture to text', toolsShare: 'Share',
      previewHead: 'Preview: exactly as on Steam', chars: '{n} of ~8000 characters', tooLong: 'Over the limit: Steam will not save it.',
      wraps: 'Lines {list} are wider than the box and will wrap.', fits: 'Every line fits the width.',
      tall: 'Steam shows about 33 lines; the rest scrolls inside the box.', approx: 'The width check is approximate: Steam uses its own font.',
      emoNote: 'Emoticons (:name:) show on Steam only if you own them.', copy: 'Copy text', copyTitle: 'Copy title', copied: 'Copied ✓',
      openSteam: 'Open Steam', howTitle: 'How to put it on your profile', how1: 'On Steam open Edit Profile → Featured Showcase.',
      how2: 'Pick “Custom Info Box” and paste the title and the text.', how3: 'Press Save. Done!',
      artLead: 'Turns a picture into dot symbols that keep their width on Steam. Simple pictures with clear shapes work best.',
      artPick: 'Choose a picture', artWidth: 'Width', artThreshold: 'Brightness', artInvert: 'Invert', artDither: 'Smooth shading', artInsert: 'Add to the text',
      moreHead: 'Need more ideas?', moreLead: 'Steam communities that collect symbol art:',
      publishLead: 'Made something nice? Share it so others can use it too.', pubTitle: 'Template name', pubCat: 'Category',
      pubRights: 'I made this template or have the rights to share it.', pubSend: 'Publish', pubDone: 'Published. Thank you!',
      pubLogin: 'Sign in to share templates.', pubFail: 'Could not publish. Check the name and the text.', pubRate: 'Too many templates for now. Try again later.',
      confirmReplace: 'Use this template?', confirmDelete: 'Delete this template?', cancel: 'Cancel', yes: 'Yes'
    },
    ru: {
      lead: 'Готовые оформления для витрины Steam «Поле со своей информацией». Выбери, поменяй текст и скопируй в профиль.',
      step1: 'Выбери шаблон', step2: 'Поменяй текст', step3: 'Скопируй в Steam', search: 'Поиск по шаблонам',
      blank: 'Чистый лист', draft: 'Мой черновик', back: 'Все шаблоны', count: 'Шаблонов: {n}', noResults: 'Ничего не нашлось. Попробуй другое слово или категорию.',
      catAll: 'Все', catAbout: 'Обо мне', catFrames: 'Рамки', catGames: 'Игры', catStream: 'Ссылки и стримы', catQuotes: 'Цитаты и статус',
      catAesthetic: 'Эстетика', catHoliday: 'Праздники', catArt: 'Картинки из символов', catFun: 'Юмор', catCommunity: 'От сообщества', catOther: 'Другое',
      useTpl: 'Взять шаблон', by: 'автор', uses: 'взяли {n}', del: 'Удалить', loading: 'Загружаем…', empty: 'Шаблонов от сообщества пока нет. Стань первым!',
      more: 'Показать ещё', sortNew: 'Новые', sortPopular: 'Популярные', communityCta: 'Поделиться своим шаблоном',
      boxTitle: 'Заголовок витрины', boxTitleDefault: 'Обо мне', textLabel: 'Текст', tbH1: 'Заголовок', tbB: 'Жирный', tbI: 'Курсив', tbU: 'Подчёркнутый',
      tbS: 'Зачёркнутый', tbSpoiler: 'Спойлер', tbHr: 'Линия', tbUrl: 'Ссылка', clear: 'Очистить',
      toolsSymbols: 'Символы', toolsArt: 'Картинка в текст', toolsShare: 'Поделиться',
      previewHead: 'Превью: точно как в Steam', chars: '{n} из ~8000 символов', tooLong: 'Больше лимита: Steam не сохранит.',
      wraps: 'Строки {list} шире поля и перенесутся.', fits: 'Все строки помещаются по ширине.',
      tall: 'Steam показывает около 33 строк, остальное прокручивается внутри поля.', approx: 'Ширина проверяется примерно: у Steam свой шрифт.',
      emoNote: 'Смайлики (:name:) в Steam видны, только если они у тебя есть.', copy: 'Скопировать текст', copyTitle: 'Скопировать заголовок', copied: 'Скопировано ✓',
      openSteam: 'Открыть Steam', howTitle: 'Как поставить в профиль', how1: 'В Steam открой «Редактировать профиль» → «Витрина».',
      how2: 'Выбери «Поле со своей информацией» и вставь заголовок и текст.', how3: 'Нажми «Сохранить». Готово!',
      artLead: 'Превращает картинку в символы-точки, которые в Steam не съезжают. Лучше всего выходят простые картинки с чёткими формами.',
      artPick: 'Выбрать картинку', artWidth: 'Ширина', artThreshold: 'Яркость', artInvert: 'Инвертировать', artDither: 'Плавные тени', artInsert: 'Добавить в текст',
      moreHead: 'Нужно больше идей?', moreLead: 'Сообщества Steam, где собирают картинки из символов:',
      publishLead: 'Получилось красиво? Поделись, чтобы другие тоже могли взять.', pubTitle: 'Название шаблона', pubCat: 'Категория',
      pubRights: 'Я сделал этот шаблон или имею право им делиться.', pubSend: 'Опубликовать', pubDone: 'Опубликовано. Спасибо!',
      pubLogin: 'Войди в аккаунт, чтобы делиться шаблонами.', pubFail: 'Не получилось опубликовать. Проверь название и текст.', pubRate: 'Слишком много шаблонов подряд. Попробуй позже.',
      confirmReplace: 'Использовать этот шаблон?', confirmDelete: 'Удалить этот шаблон?', cancel: 'Отмена', yes: 'Да'
    },
    de: {
      lead: 'Fertige Designs für Steams „Benutzerdefinierte Infobox“. Wähle eins, ändere den Text und kopiere ihn ins Profil.',
      step1: 'Vorlage wählen', step2: 'Text ändern', step3: 'Zu Steam kopieren', search: 'Vorlagen durchsuchen',
      blank: 'Leere Seite', draft: 'Mein Entwurf', back: 'Alle Vorlagen', count: '{n} Vorlagen', noResults: 'Nichts gefunden. Versuche ein anderes Wort oder eine andere Kategorie.',
      catAll: 'Alle', catAbout: 'Über mich', catFrames: 'Rahmen', catGames: 'Spiele', catStream: 'Links & Streams', catQuotes: 'Zitate & Status',
      catAesthetic: 'Ästhetik', catHoliday: 'Feiertage', catArt: 'Symbolbilder', catFun: 'Spaß', catCommunity: 'Community', catOther: 'Sonstiges',
      useTpl: 'Vorlage verwenden', by: 'von', uses: '{n}× verwendet', del: 'Löschen', loading: 'Wird geladen…', empty: 'Noch keine Community-Vorlagen. Sei die erste Person!',
      more: 'Mehr anzeigen', sortNew: 'Neu', sortPopular: 'Beliebt', communityCta: 'Eigene Vorlage teilen',
      boxTitle: 'Titel des Showcase', boxTitleDefault: 'Über mich', textLabel: 'Text', tbH1: 'Überschrift', tbB: 'Fett', tbI: 'Kursiv', tbU: 'Unterstrichen',
      tbS: 'Durchgestrichen', tbSpoiler: 'Spoiler', tbHr: 'Linie', tbUrl: 'Link', clear: 'Leeren',
      toolsSymbols: 'Symbole', toolsArt: 'Bild zu Text', toolsShare: 'Teilen',
      previewHead: 'Vorschau: genau wie auf Steam', chars: '{n} von ~8000 Zeichen', tooLong: 'Über dem Limit: Steam speichert das nicht.',
      wraps: 'Die Zeilen {list} sind breiter als die Box und werden umbrochen.', fits: 'Alle Zeilen passen in die Breite.',
      tall: 'Steam zeigt etwa 33 Zeilen, der Rest scrollt in der Box.', approx: 'Die Breite wird nur ungefähr geprüft: Steam nutzt eine eigene Schrift.',
      emoNote: 'Emoticons (:name:) erscheinen auf Steam nur, wenn du sie besitzt.', copy: 'Text kopieren', copyTitle: 'Titel kopieren', copied: 'Kopiert ✓',
      openSteam: 'Steam öffnen', howTitle: 'So kommt es ins Profil', how1: 'Öffne auf Steam Profil bearbeiten → Präsentation.',
      how2: 'Wähle „Benutzerdefinierte Infobox“ und füge Titel und Text ein.', how3: 'Klicke auf Speichern. Fertig!',
      artLead: 'Wandelt ein Bild in Punktsymbole um, die auf Steam ihre Breite behalten. Einfache Bilder mit klaren Formen gelingen am besten.',
      artPick: 'Bild auswählen', artWidth: 'Breite', artThreshold: 'Helligkeit', artInvert: 'Umkehren', artDither: 'Weiche Schatten', artInsert: 'Zum Text hinzufügen',
      moreHead: 'Mehr Ideen gefällig?', moreLead: 'Steam-Communitys, die Symbolbilder sammeln:',
      publishLead: 'Etwas Schönes gemacht? Teile es, damit andere es auch nutzen können.', pubTitle: 'Name der Vorlage', pubCat: 'Kategorie',
      pubRights: 'Ich habe diese Vorlage erstellt oder darf sie teilen.', pubSend: 'Veröffentlichen', pubDone: 'Veröffentlicht. Danke!',
      pubLogin: 'Melde dich an, um Vorlagen zu teilen.', pubFail: 'Veröffentlichen fehlgeschlagen. Prüfe Name und Text.', pubRate: 'Zu viele Vorlagen auf einmal. Versuche es später.',
      confirmReplace: 'Diese Vorlage verwenden?', confirmDelete: 'Diese Vorlage löschen?', cancel: 'Abbrechen', yes: 'Ja'
    },
    tr: {
      lead: 'Steam’in “Özel Bilgi Kutusu” için hazır tasarımlar. Birini seç, metni değiştir ve profiline kopyala.',
      step1: 'Şablon seç', step2: 'Metni değiştir', step3: 'Steam’e kopyala', search: 'Şablonlarda ara',
      blank: 'Boş sayfa', draft: 'Taslağım', back: 'Tüm şablonlar', count: '{n} şablon', noResults: 'Hiçbir şey bulunamadı. Başka bir kelime ya da kategori dene.',
      catAll: 'Tümü', catAbout: 'Hakkımda', catFrames: 'Çerçeveler', catGames: 'Oyunlar', catStream: 'Bağlantılar ve yayınlar', catQuotes: 'Alıntılar ve durum',
      catAesthetic: 'Estetik', catHoliday: 'Bayramlar', catArt: 'Sembol resimleri', catFun: 'Eğlence', catCommunity: 'Topluluk', catOther: 'Diğer',
      useTpl: 'Şablonu kullan', by: 'yazan', uses: '{n} kez kullanıldı', del: 'Sil', loading: 'Yükleniyor…', empty: 'Henüz topluluk şablonu yok. İlk sen ol!',
      more: 'Daha fazla göster', sortNew: 'Yeni', sortPopular: 'Popüler', communityCta: 'Kendi şablonunu paylaş',
      boxTitle: 'Vitrin başlığı', boxTitleDefault: 'Hakkımda', textLabel: 'Metin', tbH1: 'Başlık', tbB: 'Kalın', tbI: 'İtalik', tbU: 'Altı çizili',
      tbS: 'Üstü çizili', tbSpoiler: 'Spoiler', tbHr: 'Çizgi', tbUrl: 'Bağlantı', clear: 'Temizle',
      toolsSymbols: 'Semboller', toolsArt: 'Resimden metne', toolsShare: 'Paylaş',
      previewHead: 'Önizleme: Steam’deki gibi', chars: '{n} / ~8000 karakter', tooLong: 'Sınırın üzerinde: Steam bunu kaydetmez.',
      wraps: '{list}. satırlar kutudan geniş ve alt satıra geçecek.', fits: 'Tüm satırlar genişliğe sığıyor.',
      tall: 'Steam yaklaşık 33 satır gösterir; gerisi kutunun içinde kayar.', approx: 'Genişlik yaklaşık kontrol edilir: Steam kendi yazı tipini kullanır.',
      emoNote: 'İfadeler (:ad:) Steam’de yalnızca sende varsa görünür.', copy: 'Metni kopyala', copyTitle: 'Başlığı kopyala', copied: 'Kopyalandı ✓',
      openSteam: 'Steam’i aç', howTitle: 'Profiline nasıl eklenir', how1: 'Steam’de Profili düzenle → Vitrin bölümünü aç.',
      how2: '“Özel Bilgi Kutusu”nu seç, başlığı ve metni yapıştır.', how3: 'Kaydet’e bas. Bitti!',
      artLead: 'Resmi Steam’de genişliği bozulmayan nokta sembollerine dönüştürür. En iyi sonuç net şekilli basit resimlerle olur.',
      artPick: 'Resim seç', artWidth: 'Genişlik', artThreshold: 'Parlaklık', artInvert: 'Ters çevir', artDither: 'Yumuşak gölgeler', artInsert: 'Metne ekle',
      moreHead: 'Daha fazla fikir mi lazım?', moreLead: 'Sembol resimleri toplayan Steam toplulukları:',
      publishLead: 'Güzel bir şey mi yaptın? Başkaları da kullanabilsin diye paylaş.', pubTitle: 'Şablon adı', pubCat: 'Kategori',
      pubRights: 'Bu şablonu ben yaptım ya da paylaşma hakkım var.', pubSend: 'Yayınla', pubDone: 'Yayınlandı. Teşekkürler!',
      pubLogin: 'Şablon paylaşmak için giriş yap.', pubFail: 'Yayınlanamadı. Adı ve metni kontrol et.', pubRate: 'Şimdilik çok fazla şablon. Daha sonra tekrar dene.',
      confirmReplace: 'Bu şablon kullanılsın mı?', confirmDelete: 'Bu şablon silinsin mi?', cancel: 'İptal', yes: 'Evet'
    },
    fr: {
      lead: 'Des designs prêts pour la « Boîte d’infos personnalisée » de Steam. Choisis-en un, change le texte et copie-le dans ton profil.',
      step1: 'Choisis un modèle', step2: 'Change le texte', step3: 'Copie-le sur Steam', search: 'Rechercher un modèle',
      blank: 'Page blanche', draft: 'Mon brouillon', back: 'Tous les modèles', count: '{n} modèles', noResults: 'Rien trouvé. Essaie un autre mot ou une autre catégorie.',
      catAll: 'Tous', catAbout: 'À propos de moi', catFrames: 'Cadres', catGames: 'Jeux', catStream: 'Liens et streams', catQuotes: 'Citations et statut',
      catAesthetic: 'Esthétique', catHoliday: 'Fêtes', catArt: 'Images en symboles', catFun: 'Humour', catCommunity: 'Communauté', catOther: 'Autre',
      useTpl: 'Utiliser ce modèle', by: 'par', uses: 'utilisé {n} fois', del: 'Supprimer', loading: 'Chargement…', empty: 'Pas encore de modèles de la communauté. Sois le premier !',
      more: 'Afficher plus', sortNew: 'Récents', sortPopular: 'Populaires', communityCta: 'Partager ton modèle',
      boxTitle: 'Titre de la vitrine', boxTitleDefault: 'À propos de moi', textLabel: 'Texte', tbH1: 'Titre', tbB: 'Gras', tbI: 'Italique', tbU: 'Souligné',
      tbS: 'Barré', tbSpoiler: 'Spoiler', tbHr: 'Ligne', tbUrl: 'Lien', clear: 'Effacer',
      toolsSymbols: 'Symboles', toolsArt: 'Image en texte', toolsShare: 'Partager',
      previewHead: 'Aperçu : comme sur Steam', chars: '{n} sur ~8000 caractères', tooLong: 'Au-delà de la limite : Steam ne l’enregistrera pas.',
      wraps: 'Les lignes {list} sont plus larges que la boîte et passeront à la ligne.', fits: 'Toutes les lignes tiennent en largeur.',
      tall: 'Steam affiche environ 33 lignes ; le reste défile dans la boîte.', approx: 'La largeur est vérifiée de façon approximative : Steam utilise sa propre police.',
      emoNote: 'Les émoticônes (:nom:) ne s’affichent sur Steam que si tu les possèdes.', copy: 'Copier le texte', copyTitle: 'Copier le titre', copied: 'Copié ✓',
      openSteam: 'Ouvrir Steam', howTitle: 'Comment l’ajouter au profil', how1: 'Sur Steam, ouvre Modifier le profil → Vitrine.',
      how2: 'Choisis « Boîte d’infos personnalisée » et colle le titre et le texte.', how3: 'Clique sur Enregistrer. C’est fait !',
      artLead: 'Transforme une image en symboles de points qui gardent leur largeur sur Steam. Les images simples aux formes nettes donnent le meilleur résultat.',
      artPick: 'Choisir une image', artWidth: 'Largeur', artThreshold: 'Luminosité', artInvert: 'Inverser', artDither: 'Ombres douces', artInsert: 'Ajouter au texte',
      moreHead: 'Besoin d’autres idées ?', moreLead: 'Communautés Steam qui rassemblent des images en symboles :',
      publishLead: 'Tu as fait quelque chose de joli ? Partage-le pour que d’autres puissent l’utiliser.', pubTitle: 'Nom du modèle', pubCat: 'Catégorie',
      pubRights: 'J’ai créé ce modèle ou j’ai le droit de le partager.', pubSend: 'Publier', pubDone: 'Publié. Merci !',
      pubLogin: 'Connecte-toi pour partager des modèles.', pubFail: 'Publication impossible. Vérifie le nom et le texte.', pubRate: 'Trop de modèles pour le moment. Réessaie plus tard.',
      confirmReplace: 'Utiliser ce modèle ?', confirmDelete: 'Supprimer ce modèle ?', cancel: 'Annuler', yes: 'Oui'
    },
    uk: {
      lead: 'Готові оформлення для вітрини Steam «Поле зі своєю інформацією». Обери, зміни текст і скопіюй у профіль.',
      step1: 'Обери шаблон', step2: 'Зміни текст', step3: 'Скопіюй у Steam', search: 'Пошук шаблонів',
      blank: 'Чистий аркуш', draft: 'Моя чернетка', back: 'Усі шаблони', count: 'Шаблонів: {n}', noResults: 'Нічого не знайшлося. Спробуй інше слово або категорію.',
      catAll: 'Усі', catAbout: 'Про мене', catFrames: 'Рамки', catGames: 'Ігри', catStream: 'Посилання й стріми', catQuotes: 'Цитати й статус',
      catAesthetic: 'Естетика', catHoliday: 'Свята', catArt: 'Картинки із символів', catFun: 'Гумор', catCommunity: 'Від спільноти', catOther: 'Інше',
      useTpl: 'Взяти шаблон', by: 'автор', uses: 'взяли {n}', del: 'Видалити', loading: 'Завантажуємо…', empty: 'Шаблонів від спільноти ще немає. Стань першим!',
      more: 'Показати ще', sortNew: 'Нові', sortPopular: 'Популярні', communityCta: 'Поділитися своїм шаблоном',
      boxTitle: 'Заголовок вітрини', boxTitleDefault: 'Про мене', textLabel: 'Текст', tbH1: 'Заголовок', tbB: 'Жирний', tbI: 'Курсив', tbU: 'Підкреслений',
      tbS: 'Закреслений', tbSpoiler: 'Спойлер', tbHr: 'Лінія', tbUrl: 'Посилання', clear: 'Очистити',
      toolsSymbols: 'Символи', toolsArt: 'Картинка в текст', toolsShare: 'Поділитися',
      previewHead: 'Превʼю: точно як у Steam', chars: '{n} з ~8000 символів', tooLong: 'Більше ліміту: Steam не збереже.',
      wraps: 'Рядки {list} ширші за поле й перенесуться.', fits: 'Усі рядки вміщуються по ширині.',
      tall: 'Steam показує близько 33 рядків, решта прокручується всередині поля.', approx: 'Ширина перевіряється приблизно: у Steam свій шрифт.',
      emoNote: 'Смайлики (:name:) у Steam видно, лише якщо вони в тебе є.', copy: 'Скопіювати текст', copyTitle: 'Скопіювати заголовок', copied: 'Скопійовано ✓',
      openSteam: 'Відкрити Steam', howTitle: 'Як поставити в профіль', how1: 'У Steam відкрий «Редагувати профіль» → «Вітрина».',
      how2: 'Обери «Поле зі своєю інформацією» й встав заголовок і текст.', how3: 'Натисни «Зберегти». Готово!',
      artLead: 'Перетворює картинку на символи-крапки, які в Steam не зʼїжджають. Найкраще виходять прості картинки з чіткими формами.',
      artPick: 'Обрати картинку', artWidth: 'Ширина', artThreshold: 'Яскравість', artInvert: 'Інвертувати', artDither: 'Плавні тіні', artInsert: 'Додати в текст',
      moreHead: 'Потрібно більше ідей?', moreLead: 'Спільноти Steam, де збирають картинки із символів:',
      publishLead: 'Вийшло гарно? Поділися, щоб інші теж могли взяти.', pubTitle: 'Назва шаблону', pubCat: 'Категорія',
      pubRights: 'Я зробив цей шаблон або маю право ним ділитися.', pubSend: 'Опублікувати', pubDone: 'Опубліковано. Дякуємо!',
      pubLogin: 'Увійди в акаунт, щоб ділитися шаблонами.', pubFail: 'Не вдалося опублікувати. Перевір назву й текст.', pubRate: 'Забагато шаблонів поспіль. Спробуй пізніше.',
      confirmReplace: 'Використати цей шаблон?', confirmDelete: 'Видалити цей шаблон?', cancel: 'Скасувати', yes: 'Так'
    },
    es: {
      lead: 'Diseños listos para el «Cuadro de información personalizado» de Steam. Elige uno, cambia el texto y cópialo en tu perfil.',
      step1: 'Elige una plantilla', step2: 'Cambia el texto', step3: 'Cópialo en Steam', search: 'Buscar plantillas',
      blank: 'Página en blanco', draft: 'Mi borrador', back: 'Todas las plantillas', count: '{n} plantillas', noResults: 'No se encontró nada. Prueba otra palabra o categoría.',
      catAll: 'Todas', catAbout: 'Sobre mí', catFrames: 'Marcos', catGames: 'Juegos', catStream: 'Enlaces y streams', catQuotes: 'Citas y estado',
      catAesthetic: 'Estética', catHoliday: 'Fiestas', catArt: 'Dibujos con símbolos', catFun: 'Humor', catCommunity: 'Comunidad', catOther: 'Otras',
      useTpl: 'Usar plantilla', by: 'de', uses: 'usada {n} veces', del: 'Eliminar', loading: 'Cargando…', empty: 'Aún no hay plantillas de la comunidad. ¡Sé el primero!',
      more: 'Mostrar más', sortNew: 'Nuevas', sortPopular: 'Populares', communityCta: 'Compartir tu plantilla',
      boxTitle: 'Título del escaparate', boxTitleDefault: 'Sobre mí', textLabel: 'Texto', tbH1: 'Título', tbB: 'Negrita', tbI: 'Cursiva', tbU: 'Subrayado',
      tbS: 'Tachado', tbSpoiler: 'Spoiler', tbHr: 'Línea', tbUrl: 'Enlace', clear: 'Borrar',
      toolsSymbols: 'Símbolos', toolsArt: 'Imagen a texto', toolsShare: 'Compartir',
      previewHead: 'Vista previa: igual que en Steam', chars: '{n} de ~8000 caracteres', tooLong: 'Supera el límite: Steam no lo guardará.',
      wraps: 'Las líneas {list} son más anchas que el cuadro y se partirán.', fits: 'Todas las líneas caben a lo ancho.',
      tall: 'Steam muestra unas 33 líneas; el resto se desplaza dentro del cuadro.', approx: 'El ancho se comprueba de forma aproximada: Steam usa su propia fuente.',
      emoNote: 'Los emoticonos (:nombre:) solo se ven en Steam si los tienes.', copy: 'Copiar texto', copyTitle: 'Copiar título', copied: 'Copiado ✓',
      openSteam: 'Abrir Steam', howTitle: 'Cómo ponerlo en tu perfil', how1: 'En Steam abre Editar perfil → Escaparate.',
      how2: 'Elige «Cuadro de información personalizado» y pega el título y el texto.', how3: 'Pulsa Guardar. ¡Listo!',
      artLead: 'Convierte una imagen en símbolos de puntos que mantienen su ancho en Steam. Lo mejor son imágenes simples con formas claras.',
      artPick: 'Elegir imagen', artWidth: 'Ancho', artThreshold: 'Brillo', artInvert: 'Invertir', artDither: 'Sombras suaves', artInsert: 'Añadir al texto',
      moreHead: '¿Necesitas más ideas?', moreLead: 'Comunidades de Steam que reúnen dibujos con símbolos:',
      publishLead: '¿Te quedó bonito? Compártelo para que otros también puedan usarlo.', pubTitle: 'Nombre de la plantilla', pubCat: 'Categoría',
      pubRights: 'Hice esta plantilla o tengo derecho a compartirla.', pubSend: 'Publicar', pubDone: 'Publicada. ¡Gracias!',
      pubLogin: 'Inicia sesión para compartir plantillas.', pubFail: 'No se pudo publicar. Revisa el nombre y el texto.', pubRate: 'Demasiadas plantillas por ahora. Inténtalo más tarde.',
      confirmReplace: '¿Usar esta plantilla?', confirmDelete: '¿Eliminar esta plantilla?', cancel: 'Cancelar', yes: 'Sí'
    },
    pt: {
      lead: 'Designs prontos para a “Caixa de informações personalizada” da Steam. Escolha um, mude o texto e copie para o seu perfil.',
      step1: 'Escolha um modelo', step2: 'Mude o texto', step3: 'Copie para a Steam', search: 'Buscar modelos',
      blank: 'Página em branco', draft: 'Meu rascunho', back: 'Todos os modelos', count: '{n} modelos', noResults: 'Nada encontrado. Tente outra palavra ou categoria.',
      catAll: 'Todos', catAbout: 'Sobre mim', catFrames: 'Molduras', catGames: 'Jogos', catStream: 'Links e streams', catQuotes: 'Citações e status',
      catAesthetic: 'Estética', catHoliday: 'Festas', catArt: 'Desenhos com símbolos', catFun: 'Humor', catCommunity: 'Comunidade', catOther: 'Outros',
      useTpl: 'Usar modelo', by: 'por', uses: 'usado {n} vezes', del: 'Excluir', loading: 'Carregando…', empty: 'Ainda não há modelos da comunidade. Seja o primeiro!',
      more: 'Mostrar mais', sortNew: 'Novos', sortPopular: 'Populares', communityCta: 'Compartilhar seu modelo',
      boxTitle: 'Título da vitrine', boxTitleDefault: 'Sobre mim', textLabel: 'Texto', tbH1: 'Título', tbB: 'Negrito', tbI: 'Itálico', tbU: 'Sublinhado',
      tbS: 'Riscado', tbSpoiler: 'Spoiler', tbHr: 'Linha', tbUrl: 'Link', clear: 'Limpar',
      toolsSymbols: 'Símbolos', toolsArt: 'Imagem em texto', toolsShare: 'Compartilhar',
      previewHead: 'Prévia: igual à Steam', chars: '{n} de ~8000 caracteres', tooLong: 'Acima do limite: a Steam não vai salvar.',
      wraps: 'As linhas {list} são mais largas que a caixa e vão quebrar.', fits: 'Todas as linhas cabem na largura.',
      tall: 'A Steam mostra cerca de 33 linhas; o resto rola dentro da caixa.', approx: 'A largura é verificada de forma aproximada: a Steam usa a própria fonte.',
      emoNote: 'Os emoticons (:nome:) só aparecem na Steam se você os tiver.', copy: 'Copiar texto', copyTitle: 'Copiar título', copied: 'Copiado ✓',
      openSteam: 'Abrir a Steam', howTitle: 'Como colocar no perfil', how1: 'Na Steam, abra Editar perfil → Vitrine.',
      how2: 'Escolha “Caixa de informações personalizada” e cole o título e o texto.', how3: 'Clique em Salvar. Pronto!',
      artLead: 'Transforma uma imagem em símbolos de pontos que mantêm a largura na Steam. Imagens simples com formas claras ficam melhores.',
      artPick: 'Escolher imagem', artWidth: 'Largura', artThreshold: 'Brilho', artInvert: 'Inverter', artDither: 'Sombras suaves', artInsert: 'Adicionar ao texto',
      moreHead: 'Precisa de mais ideias?', moreLead: 'Comunidades da Steam que reúnem desenhos com símbolos:',
      publishLead: 'Ficou bonito? Compartilhe para que outros também possam usar.', pubTitle: 'Nome do modelo', pubCat: 'Categoria',
      pubRights: 'Eu fiz este modelo ou tenho o direito de compartilhá-lo.', pubSend: 'Publicar', pubDone: 'Publicado. Obrigado!',
      pubLogin: 'Entre na conta para compartilhar modelos.', pubFail: 'Não foi possível publicar. Confira o nome e o texto.', pubRate: 'Modelos demais por enquanto. Tente mais tarde.',
      confirmReplace: 'Usar este modelo?', confirmDelete: 'Excluir este modelo?', cancel: 'Cancelar', yes: 'Sim'
    }
  };

  var TEMPLATES = window.SM_INFOBOX_TEMPLATES || [];
  var SYMBOLS = [
    '★ ☆ ✦ ✧ ✩ ✪ ⋆ ✷ ✹ ❂ ❉ ❋ ✺ ✶',
    '➤ ➜ ➔ → ⇢ ⟶ ↳ ↪ ▶ ◀ ▸ ◂ » «',
    '━ ─ ┈ ═ ▬ ⎯ ┄ ╌ ⋯ · • ∙ ○ ●',
    '┏ ┓ ┗ ┛ ┃ ╔ ╗ ╚ ╝ ║ 【 】 「 」 『 』 ❮ ❯',
    '♥ ♡ ❤ ❥ ღ ❦ ❧ ✿ ❀ ✾ ❁ ☘',
    '♪ ♫ ☾ ☀ ⚡ ⚔ ☯ ✔ ✖ ✎ ⏳ ☕ ♛ ✉ ⟡ ◈',
    '▰ ▱ █ ▓ ▒ ░ ■ □ ▮ ▯ ① ② ③ ④ ⑤',
    '❄ ❅ ❆ ☃ 🎃 🎁 🎂 🎮 🏆 🎨 🔴 ⚠'
  ];
  var CATS = ['all', 'about', 'frames', 'games', 'stream', 'quotes', 'aesthetic', 'holiday', 'art', 'fun', 'community'];
  var CAT_KEY = { all: 'catAll', about: 'catAbout', frames: 'catFrames', games: 'catGames', stream: 'catStream', quotes: 'catQuotes',
    aesthetic: 'catAesthetic', holiday: 'catHoliday', art: 'catArt', fun: 'catFun', community: 'catCommunity', other: 'catOther' };
  // Categories a visitor can publish into (the server keeps its own list: smweb/infobox.py CATEGORIES).
  var PUBLISH_CATS = ['about', 'frames', 'games', 'quotes', 'art', 'other'];
  var MORE_LINKS = [['Steam: ASCII Art', 'https://steamcommunity.com/groups/ascii-art']];
  var LIMIT = 8000, WIDTH = 604, LINE = 18, VISIBLE_LINES = 33;
  var DRAFT_KEY = 'sm_infobox_draft';

  function lang() { var l = window.SMLang && SMLang.get ? SMLang.get() : 'en'; return COPY[l] ? l : 'en'; }
  function t(key, vars) {
    var text = (COPY[lang()] || COPY.en)[key] || COPY.en[key] || key;
    Object.keys(vars || {}).forEach(function (k) { text = text.replace('{' + k + '}', vars[k]); });
    return text;
  }
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function button(cls, text, onClick) { var b = el('button', cls, text); b.type = 'button'; if (onClick) b.addEventListener('click', onClick); return b; }
  function slavic() { return lang() === 'ru' || lang() === 'uk'; }
  function tplText(tpl) { return slavic() ? tpl.ru : tpl.en; }
  function tplName(tpl) { return slavic() ? tpl.name.ru : tpl.name.en; }

  var host = document.getElementById('infoBox');
  if (!host) return;

  var state = { view: 'gallery', cat: 'all', query: '', title: '', body: '', editing: '', copied: false,
    tool: 'symbols', community: [], communityTotal: 0, sort: 'new', loading: false, loggedIn: false, art: null };
  try {
    var saved = JSON.parse(localStorage.getItem(DRAFT_KEY) || 'null');
    if (saved && typeof saved.body === 'string') { state.body = saved.body; state.title = String(saved.title || ''); state.editing = String(saved.editing || ''); }
  } catch (_) {}
  var refs = {};

  // ---------------------------------------------------------------- BBCode -> preview (DOM only, never HTML strings)
  var TAG = /\[(\/?)(b|i|u|s|strike|spoiler|h1|h2|h3|hr|url|noparse|quote|code)(?:=([^\]\n]*))?\]/i;
  // Steam stores profile emoticons as ːnameː (U+02D0); typed :name: works too.
  var EMOTICON = /[:\u02d0]([A-Za-z0-9_-]{2,60})[:\u02d0]/g;
  function textInto(parent, text) {
    text.split('\n').forEach(function (part, index) {
      if (index) parent.appendChild(el('br'));
      var last = 0, match;
      EMOTICON.lastIndex = 0;
      while ((match = EMOTICON.exec(part))) {
        if (match.index > last) parent.appendChild(document.createTextNode(part.slice(last, match.index)));
        var img = el('img', 'ibx-emoticon');
        img.alt = img.title = match[0];
        img.loading = 'lazy';
        img.src = 'https://community.fastly.steamstatic.com/economy/emoticon/' + encodeURIComponent(match[1]);
        parent.appendChild(img);
        last = match.index + match[0].length;
      }
      if (last < part.length) parent.appendChild(document.createTextNode(part.slice(last)));
    });
  }
  function renderBBCode(source, target) {
    target.replaceChildren();
    var stack = [{ node: target, tag: '' }], rest = String(source || '');
    function top() { return stack[stack.length - 1]; }
    while (rest) {
      var match = TAG.exec(rest);
      if (!match) { textInto(top().node, rest); break; }
      if (match.index) textInto(top().node, rest.slice(0, match.index));
      rest = rest.slice(match.index + match[0].length);
      var closing = match[1] === '/', tag = match[2].toLowerCase(), arg = match[3];
      if (tag === 'strike') tag = 's';
      if (tag === 'noparse' && !closing) {
        var end = rest.toLowerCase().indexOf('[/noparse]');
        textInto(top().node, end < 0 ? rest : rest.slice(0, end));
        rest = end < 0 ? '' : rest.slice(end + 10);
        continue;
      }
      if (tag === 'hr') { if (!closing) top().node.appendChild(el('hr')); continue; }
      if (closing) {
        var at = -1;
        for (var i = stack.length - 1; i > 0; i--) if (stack[i].tag === tag) { at = i; break; }
        if (at < 0) { textInto(top().node, match[0]); continue; }
        stack.length = at;
        // Steam eats the line break right after a closing heading.
        if (/^h[1-3]$/.test(tag) && rest.charAt(0) === '\n') rest = rest.slice(1);
        continue;
      }
      var node;
      if (tag === 'url') {
        node = el('a', 'ibx-link');
        var href = String(arg || '').trim();
        node.dataset.href = href;
        if (/^https?:\/\//i.test(href)) { node.href = href; node.target = '_blank'; node.rel = 'noopener noreferrer nofollow'; }
      } else if (/^h[1-3]$/.test(tag)) node = el('div', 'ibx-' + tag);
      else if (tag === 'quote') node = el('blockquote', 'ibx-quote');
      else if (tag === 'code') node = el('code', 'ibx-code');
      else node = el('span', 'ibx-' + tag);
      top().node.appendChild(node);
      stack.push({ node: node, tag: tag });
    }
    // [url=X] links without text show the address; external links get Steam's grey host hint.
    target.querySelectorAll('a.ibx-link').forEach(function (a) {
      if (!a.textContent) a.textContent = a.dataset.href || '';
      var host = '';
      try { host = new URL(a.dataset.href).hostname; } catch (_) {}
      if (host && !/(^|\.)steam(community|powered)\.com$/i.test(host)) a.after(el('span', 'ibx-host', ' [' + host + ']'));
    });
  }

  // ---------------------------------------------------------------- width check (canvas, Arial standing in for Motiva Sans)
  var measureCtx = document.createElement('canvas').getContext('2d');
  function wrappedLines(source) {
    var out = [], inHeading = false;
    String(source || '').split('\n').forEach(function (line, index) {
      var heading = inHeading || /\[h[1-3]\]/i.test(line);
      if (/\[h[1-3]\]/i.test(line)) inHeading = !/\[\/h[1-3]\]/i.test(line);
      else if (/\[\/h[1-3]\]/i.test(line)) inHeading = false;
      var plain = line.replace(/\[\/?[a-z0-9]+(?:=[^\]]*)?\]/gi, ''), emoticons = 0;
      plain = plain.replace(EMOTICON, function () { emoticons++; return ''; });
      measureCtx.font = (heading ? '20px' : '13px') + ' "Motiva Sans", Arial, Helvetica, sans-serif';
      if (measureCtx.measureText(plain).width + emoticons * LINE > WIDTH) out.push(index + 1);
    });
    return out;
  }

  // ---------------------------------------------------------------- picture -> braille text
  function brailleWidth() { measureCtx.font = '13px "Motiva Sans", Arial, Helvetica, sans-serif'; return measureCtx.measureText('⣿').width || 7; }
  function artText(img, cols, threshold, invert, dither) {
    var cell = brailleWidth();
    var rows = Math.max(1, Math.round((img.naturalHeight / img.naturalWidth) * cols * cell / LINE));
    // Keep the result well under Steam's limit (one symbol per cell plus the line break).
    rows = Math.min(rows, Math.floor((LIMIT - 400) / (cols + 1)));
    var w = cols * 2, h = rows * 4;
    var canvas = document.createElement('canvas');
    canvas.width = w; canvas.height = h;
    var ctx = canvas.getContext('2d', { willReadFrequently: true });
    ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, w, h);
    ctx.drawImage(img, 0, 0, w, h);
    var data = ctx.getImageData(0, 0, w, h).data, gray = new Float32Array(w * h);
    for (var p = 0; p < w * h; p++) {
      var a = data[p * 4 + 3] / 255;
      gray[p] = (0.299 * data[p * 4] + 0.587 * data[p * 4 + 1] + 0.114 * data[p * 4 + 2]) * a + 255 * (1 - a);
    }
    var on = new Uint8Array(w * h);
    for (var y = 0; y < h; y++) {
      for (var x = 0; x < w; x++) {
        var k = y * w + x, v = gray[k], dark = v < threshold;
        on[k] = (dark ? 1 : 0) ^ (invert ? 1 : 0);
        if (dither) {
          var err = v - (dark ? 0 : 255);
          if (x + 1 < w) gray[k + 1] += err * 7 / 16;
          if (y + 1 < h) {
            if (x > 0) gray[k + w - 1] += err * 3 / 16;
            gray[k + w] += err * 5 / 16;
            if (x + 1 < w) gray[k + w + 1] += err / 16;
          }
        }
      }
    }
    var BITS = [[0x01, 0x08], [0x02, 0x10], [0x04, 0x20], [0x40, 0x80]], lines = [];
    for (var r = 0; r < rows; r++) {
      var line = '';
      for (var c = 0; c < cols; c++) {
        var bits = 0;
        for (var dy = 0; dy < 4; dy++) for (var dx = 0; dx < 2; dx++) if (on[(r * 4 + dy) * w + c * 2 + dx]) bits |= BITS[dy][dx];
        // An empty cell is the blank braille symbol (U+2800), not a space: Steam would collapse spaces.
        line += String.fromCharCode(0x2800 + bits);
      }
      lines.push(line);
    }
    return lines.join('\n');
  }

  function averageBrightness(img) {
    var canvas = document.createElement('canvas'); canvas.width = canvas.height = 48;
    var ctx = canvas.getContext('2d', { willReadFrequently: true });
    ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, 48, 48); ctx.drawImage(img, 0, 0, 48, 48);
    var d = ctx.getImageData(0, 0, 48, 48).data, sum = 0;
    for (var i = 0; i < d.length; i += 4) sum += 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
    return sum / (d.length / 4);
  }

  // ---------------------------------------------------------------- community
  function loadCommunity(more) {
    if (state.loading) return;
    state.loading = true;
    var offset = more ? state.community.length : 0;
    fetch('/api/infobox/templates?sort=' + state.sort + '&limit=24&offset=' + offset, { credentials: 'include' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data || !data.ok) throw new Error('load');
        state.community = (more ? state.community : []).concat(data.items || []);
        state.communityTotal = data.total || 0;
        state.loggedIn = !!data.logged_in;
      })
      .catch(function () { if (!more) state.community = []; })
      .then(function () { state.loading = false; paintLibrary(); });
  }
  function markUsed(id) { fetch('/api/infobox/templates/' + encodeURIComponent(id) + '/use', { method: 'POST', credentials: 'include' }).catch(function () {}); }

  // ---------------------------------------------------------------- UI
  function save() {
    try { localStorage.setItem(DRAFT_KEY, JSON.stringify({ title: state.title, body: state.body, editing: state.editing })); } catch (_) {}
  }
  function steamBox(title, body, full) {
    // The same markup as the big preview: Steam's header + block + content.
    var box = el('div', 'ibx-steam');
    var head = el('div', 'ibx-steam__head', title);
    var block = el('div', 'ibx-steam__block');
    var content = el('div', 'ibx-steam__content');
    var text = el('div', 'ibx-text' + (full ? ' ibx-text--full' : ''));
    renderBBCode(body, text);
    content.append(text); block.append(content); box.append(head, block);
    return { box: box, head: head, text: text };
  }
  function askConfirm(text, okText) {
    // A site-styled dialog instead of the browser's confirm() (owner, 2026-10-08).
    return new Promise(function (resolve) {
      var back = el('div', 'ibx-confirm');
      var box = el('div', 'ibx-confirm__box');
      box.setAttribute('role', 'alertdialog');
      box.setAttribute('aria-modal', 'true');
      box.append(el('p', 'ibx-confirm__text', text));
      var row = el('div', 'ibx-confirm__row');
      var previous = document.activeElement;
      function close(answer) {
        document.removeEventListener('keydown', onKey, true);
        back.remove();
        if (previous && previous.focus) previous.focus();
        resolve(answer);
      }
      function onKey(event) { if (event.key === 'Escape') { event.preventDefault(); close(false); } }
      var cancel = button('ibx-btn', t('cancel'), function () { close(false); });
      var ok = button('ibx-btn ibx-btn--primary', okText, function () { close(true); });
      row.append(cancel, ok);
      box.append(row);
      back.append(box);
      back.addEventListener('click', function (event) { if (event.target === back) close(false); });
      document.addEventListener('keydown', onKey, true);
      document.body.append(back);
      ok.focus();
    });
  }
  function openEditor(body, name, communityId, keepIfSame) {
    var changed = state.body.trim() && state.body !== body && !keepIfSame;
    if (body !== null && changed) {
      askConfirm(t('confirmReplace'), t('yes')).then(function (yes) { if (yes) openEditor(body, name, communityId, true); });
      return;
    }
    if (body !== null) {
      state.body = body;
      state.editing = name || '';
      if (communityId) markUsed(communityId);
    }
    state.view = 'editor';
    state.copied = false;
    save();
    build();
    if (refs.area) { refs.area.focus(); refs.area.setSelectionRange(0, 0); }
    // Land just under the site header and the tools strip (the editor bar sticks there too).
    var chrome = document.querySelector('.top-chrome');
    var offset = chrome ? chrome.getBoundingClientRect().bottom + 12 : 120;
    window.scrollTo({ top: Math.max(0, host.getBoundingClientRect().top + window.scrollY - offset), behavior: 'smooth' });
  }
  function matches(name, body) {
    var q = state.query.trim().toLowerCase();
    return !q || name.toLowerCase().indexOf(q) >= 0 || body.toLowerCase().indexOf(q) >= 0;
  }
  function tcard(name, label, body, onUse, meta, extra) {
    var card = el('article', 'ibx-tcard');
    card.tabIndex = 0;
    card.setAttribute('role', 'button');
    card.setAttribute('aria-label', t('useTpl') + ': ' + name);
    var thumb = el('div', 'ibx-thumb');
    var inner = el('div', 'ibx-thumb__inner');
    inner.append(steamBox(t('boxTitleDefault'), body, false).box);
    thumb.append(inner);
    var caption = el('div', 'ibx-tcard__caption');
    caption.append(el('b', '', name));
    if (label) caption.append(el('span', 'ibx-tcard__cat', label));
    if (meta) caption.append(el('span', 'ibx-tcard__meta', meta));
    card.append(thumb, caption);
    if (extra) card.append(extra);
    card.addEventListener('click', function (event) { if (!event.target.closest('.ibx-tcard__extra')) onUse(); });
    card.addEventListener('keydown', function (event) { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onUse(); } });
    return card;
  }
  function paintGallery() {
    var grid = refs.grid;
    if (!grid) return;
    grid.replaceChildren();
    refs.tabs.querySelectorAll('[data-cat]').forEach(function (b) { b.classList.toggle('is-on', b.dataset.cat === state.cat); });
    refs.sort.hidden = state.cat !== 'community';
    var shown = 0;
    if (state.cat === 'community') {
      var cta = el('article', 'ibx-tcard ibx-tcard--cta');
      cta.tabIndex = 0;
      cta.append(el('span', 'ibx-cta__icon', '＋'), el('b', '', t('communityCta')), el('p', '', t('publishLead')));
      cta.addEventListener('click', function () { state.tool = 'share'; openEditor(null); });
      grid.append(cta);
      if (state.loading && !state.community.length) grid.append(el('p', 'ibx-muted ibx-grid__note', t('loading')));
      else if (!state.community.length) grid.append(el('p', 'ibx-muted ibx-grid__note', t('empty')));
      state.community.forEach(function (item) {
        if (!matches(item.title, item.body)) return;
        shown++;
        var extra = null;
        if (item.owner) {
          extra = el('div', 'ibx-tcard__extra');
          extra.append(button('ibx-btn ibx-btn--ghost ibx-btn--small', t('del'), function () {
            askConfirm(t('confirmDelete'), t('del')).then(function (yes) {
              if (!yes) return;
              fetch('/api/infobox/templates/' + encodeURIComponent(item.id), { method: 'DELETE', credentials: 'include' })
                .then(function () { loadCommunity(false); });
            });
          }));
        }
        grid.append(tcard(item.title, t(CAT_KEY[item.category] || 'catOther'), item.body,
          function () { openEditor(item.body, item.title, item.id); }, t('by') + ' ' + item.author + ' · ' + t('uses', { n: item.uses }), extra));
      });
      if (state.community.length < state.communityTotal) {
        grid.append(button('ibx-btn ibx-grid__more', t('more'), function () { loadCommunity(true); }));
      }
    } else {
      TEMPLATES.forEach(function (tpl) {
        if ((state.cat !== 'all' && tpl.cat !== state.cat) || !matches(tplName(tpl), tplText(tpl))) return;
        shown++;
        grid.append(tcard(tplName(tpl), state.cat === 'all' ? t(CAT_KEY[tpl.cat]) : '', tplText(tpl),
          function () { openEditor(tplText(tpl), tplName(tpl)); }));
      });
      if (!shown) grid.append(el('p', 'ibx-muted ibx-grid__note', t('noResults')));
    }
    refs.count.textContent = t('count', { n: state.cat === 'community' ? state.communityTotal : shown });
  }
  var paintLibrary = paintGallery;   // the community loader repaints through this name

  function steps() {
    var current = state.view === 'gallery' ? 1 : state.copied ? 3 : 2;
    var list = el('ol', 'ibx-steps');
    ['step1', 'step2', 'step3'].forEach(function (key, index) {
      var item = el('li', 'ibx-step' + (index + 1 === current ? ' is-on' : index + 1 < current ? ' is-done' : ''));
      item.append(el('span', 'ibx-step__n', index + 1 < current ? '✓' : String(index + 1)), el('span', '', t(key)));
      if (index === 0 && state.view === 'editor') { item.classList.add('is-link'); item.addEventListener('click', function () { state.view = 'gallery'; build(); }); }
      list.append(item);
    });
    return list;
  }

  function buildGallery(view) {
    view.append(el('p', 'ibx-lead', t('lead')));
    var bar = el('div', 'ibx-bar');
    var searchBox = el('label', 'ibx-search');
    var search = el('input');
    search.type = 'search';
    search.placeholder = t('search');
    search.value = state.query;
    search.setAttribute('aria-label', t('search'));
    search.addEventListener('input', function () { state.query = search.value; paintGallery(); });
    searchBox.append(el('span', 'ibx-search__icon', '⌕'), search);
    var actions = el('div', 'ibx-bar__actions');
    actions.append(button('ibx-btn', '✎ ' + t('blank'), function () { openEditor('', t('blank')); }));
    if (state.body.trim()) actions.append(button('ibx-btn ibx-btn--accent', '↻ ' + t('draft'), function () { openEditor(null); }));
    // Straight to "Picture to text" (owner: people should see that this exists).
    var artButton = button('ibx-btn ibx-btn--art', '🖼 ' + t('toolsArt'), function () { state.tool = 'art'; openEditor(null); });
    var emojiButton = window.SMInfoBoxEmoji ? button('ibx-btn ibx-btn--art', '🧩 ' + SMInfoBoxEmoji.label(), function () { state.tool = 'emoji'; openEditor(null); }) : null;
    artButton.title = t('artLead');
    actions.append(artButton);
    if (emojiButton) actions.append(emojiButton);
    var count = el('span', 'ibx-count');
    bar.append(searchBox, actions);
    var tabs = el('div', 'ibx-tabs');
    tabs.setAttribute('role', 'tablist');
    CATS.forEach(function (key) {
      var amount = key === 'all' ? TEMPLATES.length : key === 'community' ? 0 : TEMPLATES.filter(function (tpl) { return tpl.cat === key; }).length;
      var tab = button('ibx-tab', t(CAT_KEY[key]), function () {
        state.cat = key;
        if (key === 'community' && !state.community.length) loadCommunity(false);
        paintGallery();
      });
      tab.setAttribute('role', 'tab');
      tab.dataset.cat = key;
      if (amount) tab.append(el('small', '', String(amount)));
      tabs.append(tab);
    });
    var sort = el('div', 'ibx-sort');
    [['new', 'sortNew'], ['popular', 'sortPopular']].forEach(function (pair) {
      sort.append(button('ibx-chip' + (state.sort === pair[0] ? ' is-on' : ''), t(pair[1]), function () {
        state.sort = pair[0];
        sort.querySelectorAll('.ibx-chip').forEach(function (b, i) { b.classList.toggle('is-on', i === (pair[0] === 'new' ? 0 : 1)); });
        loadCommunity(false);
      }));
    });
    var head = el('div', 'ibx-gridhead');
    head.append(count, sort);
    var grid = el('div', 'ibx-grid');
    var more = el('section', 'ibx-morelinks');
    more.append(el('b', '', t('moreHead')), el('span', 'ibx-muted', t('moreLead')));
    MORE_LINKS.forEach(function (link) { var a = el('a', '', link[0] + ' ↗'); a.href = link[1]; a.target = '_blank'; a.rel = 'noopener'; more.append(a); });
    view.append(bar, tabs, head, grid, more);
    refs.tabs = tabs; refs.sort = sort; refs.grid = grid; refs.count = count; refs.search = search;
    paintGallery();
  }

  function wrapSelection(open, close) {
    var area = refs.area, start = area.selectionStart, end = area.selectionEnd, value = area.value;
    var picked = value.slice(start, end);
    area.value = value.slice(0, start) + open + picked + close + value.slice(end);
    area.selectionStart = start + open.length;
    area.selectionEnd = start + open.length + picked.length;
    area.focus();
    state.body = area.value;
    update();
  }
  function insertText(text) {
    wrapSelection(text, '');
    var pos = refs.area.selectionStart;
    refs.area.selectionStart = refs.area.selectionEnd = pos;
  }
  function update() {
    if (!refs.preview) return;
    var body = state.body;
    refs.previewTitle.textContent = state.title || t('boxTitleDefault');
    renderBBCode(body, refs.preview);
    refs.chars.textContent = t('chars', { n: body.length });
    refs.chars.classList.toggle('is-bad', body.length > LIMIT);
    var notes = [];
    if (body.length > LIMIT) notes.push(['bad', t('tooLong')]);
    var wraps = wrappedLines(body);
    notes.push(wraps.length ? ['warn', t('wraps', { list: wraps.slice(0, 12).join(', ') + (wraps.length > 12 ? '…' : '') })] : ['ok', t('fits')]);
    if (refs.preview.scrollHeight > VISIBLE_LINES * LINE + 8) notes.push(['info', t('tall')]);
    EMOTICON.lastIndex = 0;
    if (EMOTICON.test(body)) notes.push(['info', t('emoNote')]);
    EMOTICON.lastIndex = 0;
    refs.notes.replaceChildren();
    notes.forEach(function (n) { refs.notes.append(el('li', 'is-' + n[0], n[1])); });
    save();
    fitPreview();
  }
  function copy(text, btn) {
    var done = function () {
      var old = btn.textContent;
      btn.textContent = t('copied');
      btn.classList.add('is-done');
      if (!state.copied) { state.copied = true; var s = host.querySelector('.ibx-steps'); if (s) s.replaceWith(steps()); }
      setTimeout(function () { btn.textContent = old; btn.classList.remove('is-done'); }, 1500);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, function () {});
    else {
      var area = el('textarea'); area.value = text; document.body.append(area); area.select();
      try { document.execCommand('copy'); done(); } catch (_) {}
      area.remove();
    }
  }

  function toolSymbols() {
    var box = el('div', 'ibx-symbols');
    SYMBOLS.forEach(function (row) {
      var line = el('div', 'ibx-symbols__row');
      row.split(' ').forEach(function (ch) { line.append(button('ibx-symbol', ch, function () { insertText(ch); })); });
      box.append(line);
    });
    return box;
  }
  function toolArt() {
    var box = el('div', 'ibx-art');
    box.append(el('p', 'ibx-muted', t('artLead')));
    var input = el('input'); input.type = 'file'; input.accept = 'image/*'; input.hidden = true; input.dataset.smEnhanced = '1';
    var pick = button('ibx-btn', '🖼 ' + t('artPick'), function () { input.click(); });
    var controls = el('div', 'ibx-art__controls');
    var out = el('pre', 'ibx-art__out');
    var insert = button('ibx-btn ibx-btn--primary', t('artInsert'), function () { if (out.textContent) { insertText((state.body.trim() ? '\n' : '') + out.textContent + '\n'); } });
    var maxCols = Math.max(20, Math.min(60, Math.floor(WIDTH / brailleWidth())));
    var art = state.art || (state.art = { cols: Math.min(40, maxCols), threshold: 128, invert: false, dither: false, img: null });
    function slider(label, min, max, value, onInput) {
      var row = el('label', 'ibx-range'); var range = el('input'); range.type = 'range'; range.min = min; range.max = max; range.value = value;
      var num = el('b', '', String(value));
      range.addEventListener('input', function () { num.textContent = range.value; onInput(Number(range.value)); render(); });
      row.append(el('span', '', label), range, num); return row;
    }
    function toggle(label, value, onChange) {
      var row = el('label', 'ibx-check'); var box2 = el('input'); box2.type = 'checkbox'; box2.checked = value;
      box2.addEventListener('change', function () { onChange(box2.checked); render(); }); row.append(box2, el('span', '', label)); return row;
    }
    var thresholdRow = slider(t('artThreshold'), 20, 235, art.threshold, function (v) { art.threshold = v; });
    controls.append(slider(t('artWidth'), 12, maxCols, art.cols, function (v) { art.cols = v; }), thresholdRow,
      toggle(t('artInvert'), art.invert, function (v) { art.invert = v; }), toggle(t('artDither'), art.dither, function (v) { art.dither = v; }));
    function render() {
      var has = !!art.img;
      controls.hidden = insert.hidden = out.hidden = !has;
      if (has) out.textContent = artText(art.img, art.cols, art.threshold, art.invert, art.dither);
    }
    input.addEventListener('change', function () {
      var file = input.files && input.files[0];
      if (!file) return;
      var img = new Image();
      img.onload = function () {
        // Start from the picture's own average brightness: a fixed middle value left dark art almost all dots.
        art.threshold = Math.max(20, Math.min(235, Math.round(averageBrightness(img))));
        thresholdRow.querySelector('input').value = art.threshold;
        thresholdRow.querySelector('b').textContent = String(art.threshold);
        art.img = img;
        render();
      };
      img.src = URL.createObjectURL(file);
      input.value = '';
    });
    var row = el('div', 'ibx-art__row');
    row.append(pick, insert);
    box.append(row, input, controls, out);
    render();
    return box;
  }
  // What "Picture from emoticons" (infobox-emoji.js) may do with the editor.
  var emojiApi = {
    limit: LIMIT,
    body: function () { return state.body; },
    insert: function (text) { insertText((state.body.trim() ? '\n' : '') + text + '\n'); },
    copy: function (text, btn) { copy(text, btn); }
  };
  function toolShare() {
    var box = el('form', 'ibx-share');
    box.append(el('p', 'ibx-muted', t('publishLead')));
    var name = el('input'); name.maxLength = 60; name.required = true; name.placeholder = t('pubTitle');
    var cat = el('select');
    PUBLISH_CATS.forEach(function (key) { var o = el('option', '', t(CAT_KEY[key])); o.value = key; cat.append(o); });
    var label1 = el('label', 'ibx-field'); label1.append(el('span', '', t('pubTitle')), name);
    var label2 = el('label', 'ibx-field'); label2.append(el('span', '', t('pubCat')), cat);
    var fields = el('div', 'ibx-share__fields'); fields.append(label1, label2);
    var rights = el('label', 'ibx-check'); var tick = el('input'); tick.type = 'checkbox'; tick.required = true; rights.append(tick, el('span', '', t('pubRights')));
    var msg = el('p', 'ibx-share__msg');
    var send = el('button', 'ibx-btn ibx-btn--primary', t('pubSend')); send.type = 'submit';
    box.append(fields, rights, send, msg);
    box.addEventListener('submit', function (event) {
      event.preventDefault();
      send.disabled = true;
      fetch('/api/infobox/templates', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: name.value, body: state.body, category: cat.value, rights: tick.checked }) })
        .then(function (r) { return r.json().then(function (d) { return [r.status, d]; }); })
        .then(function (res) {
          if (res[1] && res[1].ok) { msg.textContent = t('pubDone'); state.community = []; return; }
          if (res[0] === 401) {
            msg.textContent = t('pubLogin');
            if (window.SSShell && SSShell.openAuth) SSShell.openAuth('login');
          } else msg.textContent = res[0] === 429 ? t('pubRate') : t('pubFail');
          send.disabled = false;
        })
        .catch(function () { msg.textContent = t('pubFail'); send.disabled = false; });
    });
    return box;
  }

  function buildEditor(view) {
    // ---- top bar: back, what is being edited, the main actions
    var bar = el('div', 'ibx-ebar');
    bar.append(button('ibx-btn ibx-btn--ghost', '← ' + t('back'), function () { state.view = 'gallery'; build(); }));
    var label = el('span', 'ibx-ebar__name', state.editing || t('draft'));
    var copyText = button('ibx-btn ibx-btn--primary ibx-btn--big', '⧉ ' + t('copy'), function () { copy(state.body, copyText); });
    var copyTitle = button('ibx-btn', t('copyTitle'), function () { copy(state.title || t('boxTitleDefault'), copyTitle); });
    var steamLink = el('a', 'ibx-btn', t('openSteam') + ' ↗');
    steamLink.href = 'https://steamcommunity.com/my/edit/showcases'; steamLink.target = '_blank'; steamLink.rel = 'noopener';
    var right = el('div', 'ibx-ebar__actions');
    right.append(copyTitle, steamLink, copyText);
    bar.append(label, right);

    var cols = el('div', 'ibx-cols');
    // ---- left: the text
    var edit = el('section', 'ibx-panel ibx-edit');
    var titleField = el('label', 'ibx-field');
    var title = el('input'); title.maxLength = 64; title.value = state.title; title.placeholder = t('boxTitleDefault');
    title.addEventListener('input', function () { state.title = title.value; update(); });
    titleField.append(el('span', '', t('boxTitle')), title);
    var toolbar = el('div', 'ibx-toolbar');
    [['tbH1', 'H', '[h1]', '[/h1]'], ['tbB', 'B', '[b]', '[/b]'], ['tbI', 'I', '[i]', '[/i]'], ['tbU', 'U', '[u]', '[/u]'],
      ['tbS', 'S', '[strike]', '[/strike]'], ['tbSpoiler', '◼', '[spoiler]', '[/spoiler]']].forEach(function (item) {
      var b = button('ibx-tool ibx-tool--' + item[0], item[1], function () { wrapSelection(item[2], item[3]); });
      b.title = t(item[0]); b.setAttribute('aria-label', t(item[0]));
      toolbar.append(b);
    });
    var hr = button('ibx-tool', '—', function () { insertText('\n[hr][/hr]\n'); }); hr.title = t('tbHr'); hr.setAttribute('aria-label', t('tbHr'));
    var link = button('ibx-tool', '🔗', function () { wrapSelection('[url=https://]', '[/url]'); }); link.title = t('tbUrl'); link.setAttribute('aria-label', t('tbUrl'));
    toolbar.append(hr, link, el('span', 'ibx-toolbar__gap'),
      button('ibx-tool ibx-tool--ghost', t('clear'), function () { state.body = ''; refs.area.value = ''; update(); refs.area.focus(); }));
    var areaField = el('label', 'ibx-field');
    var area = el('textarea', 'ibx-area'); area.value = state.body; area.spellcheck = false;
    area.addEventListener('input', function () { state.body = area.value; update(); });
    areaField.append(el('span', '', t('textLabel')), area);
    var chars = el('div', 'ibx-chars');
    // ---- tools under the text
    var tools = el('div', 'ibx-tools');
    var tabs = el('div', 'ibx-tools__tabs');
    var panel = el('div', 'ibx-tools__panel');
    var toolList = [['symbols', 'toolsSymbols', '✦'], ['art', 'toolsArt', '🖼']];
    if (window.SMInfoBoxEmoji) toolList.push(['emoji', '', '🧩']);
    toolList.push(['share', 'toolsShare', '↗']);
    if (state.tool === 'emoji' && !window.SMInfoBoxEmoji) state.tool = 'symbols';
    toolList.forEach(function (item) {
      var label = item[0] === 'emoji' ? SMInfoBoxEmoji.label() : t(item[1]);
      var tab = button('ibx-tools__tab' + (state.tool === item[0] ? ' is-on' : ''), item[2] + ' ' + label, function () {
        state.tool = item[0];
        tabs.querySelectorAll('.ibx-tools__tab').forEach(function (b) { b.classList.toggle('is-on', b === tab); });
        paintTool();
      });
      tabs.append(tab);
    });
    function paintTool() {
      panel.replaceChildren(state.tool === 'art' ? toolArt() : state.tool === 'share' ? toolShare()
        : state.tool === 'emoji' ? SMInfoBoxEmoji.panel(emojiApi) : toolSymbols());
    }
    tools.append(tabs, panel);
    edit.append(titleField, toolbar, areaField, chars, tools);

    // ---- right: Steam preview, checks, how to put it on the profile
    var side = el('aside', 'ibx-side');
    var preview = el('section', 'ibx-panel ibx-preview');
    preview.append(el('h3', 'ibx-h', t('previewHead')));
    var stage = el('div', 'ibx-stage');
    var box = steamBox(state.title || t('boxTitleDefault'), state.body, true);
    stage.append(box.box);
    var notes = el('ul', 'ibx-notes');
    preview.append(stage, notes, el('p', 'ibx-muted ibx-small', t('approx')));
    var how = el('section', 'ibx-panel ibx-how');
    how.append(el('h3', 'ibx-h', t('howTitle')));
    var list = el('ol', 'ibx-how__list');
    ['how1', 'how2', 'how3'].forEach(function (key) { list.append(el('li', '', t(key))); });
    how.append(list);
    side.append(preview, how);
    cols.append(edit, side);
    view.append(bar, cols);

    refs.area = area; refs.chars = chars; refs.preview = box.text; refs.previewTitle = box.head; refs.notes = notes; refs.stage = stage;
    paintTool();
    update();
    fitPreview();
  }
  function fitPreview() {
    // The 640 px Steam box shrinks to fit narrow columns (phones, small laptops) instead of scrolling sideways.
    if (!refs.stage || !refs.stage.clientWidth) return;
    var scale = Math.min(1, (refs.stage.clientWidth - 2) / 640);
    refs.stage.style.setProperty('--ibx-preview-scale', String(scale));
    var box = refs.stage.firstElementChild, style = getComputedStyle(refs.stage);
    var pad = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom);
    if (box) refs.stage.style.height = scale < 1 ? Math.ceil(box.offsetHeight * scale + pad) + 'px' : '';
  }

  function build() {
    host.replaceChildren();
    refs = {};
    var root = el('div', 'ibx2 ibx2--' + state.view);
    root.append(steps());
    var view = el('div', 'ibx-view');
    if (state.view === 'editor') buildEditor(view); else buildGallery(view);
    root.append(view);
    host.append(root);
  }

  build();
  window.addEventListener('sm:langchange', build);
  window.addEventListener('resize', fitPreview);
  if ('ResizeObserver' in window) new ResizeObserver(fitPreview).observe(host);
  window.SMInfoBox = { state: state, render: renderBBCode, art: artText, wraps: wrappedLines, templates: TEMPLATES,
    open: function (body, name) { openEditor(body, name); }, view: function (v) { state.view = v; build(); } };
})();
