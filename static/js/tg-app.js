/* Telegram mini app (static/tg-app.html, owner 2026-10-09): cut files for showcases, download by link, convert,
   upscale (Pro), the Info box editor and the news, in the site's look. Every API call sends Telegram's signed
   initData (X-Tg-Init-Data); the server checks it (smweb/tg_app.py). Results stay on the server and are shown
   through short signed links; "To chat" makes the bot send the file, because downloads inside Telegram are flaky.
   Copy: the keyed COPY dictionary below, 8 languages (checked by scripts/check_i18n.js). */
(function () {
  'use strict';
  var COPY = {
    en: { hello: 'Hi, {name}!', helloAnon: 'Hi!', helloLead: 'Everything for your Steam profile, right in Telegram.',
      toolCut: 'Cut a file', toolCutHint: 'Picture, GIF or video into showcase files', toolDownload: 'Download', toolDownloadHint: 'YouTube, TikTok, Pinterest and more',
      toolConvert: 'Converter', toolConvertHint: 'GIF ↔ video, PNG, JPG, WebP', toolUpscale: 'Upscale', toolUpscaleHint: 'Enlarge a picture or GIF with AI',
      toolInfobox: 'Info box', toolInfoboxHint: 'Templates and an editor with a Steam preview', toolNews: 'News', toolNewsHint: 'What is new on the site',
      unlimited: 'Pro · no limits', left: '{left} of {limit} left today', pickFile: 'Choose a file', pickHint: 'Picture, GIF or video up to {mb} MB', pickImage: 'Picture, GIF or video',
      showcase: 'Showcase', workshop: 'Workshop', workshopHint: '5 parts', featured: 'Featured', featuredHint: '1 file', split: 'Artwork', splitHint: '2 files',
      frame: 'Frame', frameNone: 'No frame', frameLine: 'Line', frameNeon: 'Neon', frameRgb: 'RGB', cutGo: 'Cut for Steam',
      stageQueued: 'In the queue', stagePrepare: 'Preparing the file', stageCut: 'Cutting', stagePack: 'Packing', stageWork: 'Working', eta: '≈ {s} s left', almost: 'almost done',
      done: 'Done', sendChat: 'To chat', download: 'Download', again: 'Another file', sent: 'Sent to the chat', howUpload: 'How to upload to Steam',
      urlLabel: 'Link', sites: 'YouTube, TikTok, Pinterest, X, Tenor, Giphy, DeviantArt and direct file links', downloadGo: 'Download',
      convertTo: 'Convert to', convertGo: 'Convert', upModel: 'Model', upGeneral: 'Photo', upAnime: 'Anime', upSoft: 'Anime soft', upScale: 'Scale', upGo: 'Upscale',
      upVideo2: 'Videos are upscaled 2× only.', proOnly: 'Upscale is a Pro feature', proOnlyLead: 'Enlarges a picture, GIF or video 2× or 4× on a GPU.',
      noAccount: 'Already have Pro? Sign in on the site with Telegram once, and the app will see it.', buyPro: 'Get Pro', upOff: 'Upscale is not available right now. Try again later.',
      templates: 'Templates', all: 'All', editor: 'Text', preview: 'As in Steam', copy: 'Copy', copied: 'Copied', chars: '{n} / {max} characters',
      tooLong: 'Too long for Steam', textSent: 'The text is in the chat', ibxHint: 'Paste it in Steam: Edit Profile → Featured Showcase → Custom Info Box.',
      catAbout: 'About me', catFrames: 'Frames', catGames: 'Games', catStream: 'Streams', catQuotes: 'Quotes', catAesthetic: 'Aesthetic', catHoliday: 'Holidays', catArt: 'Art', catFun: 'Fun',
      newsEmpty: 'No news yet.', errLimit: 'Today’s limit is used up. Pro removes the limits.', errActive: 'The previous file is still being cut.',
      errBig: 'The file is too big.', errNetwork: 'No connection to the server. Try again.', errFailed: 'That did not work. Try another file.',
      errBlocked: 'The bot cannot write to you: press Start in the chat with the bot.', errAuth: 'Open the app with the menu button next to the message field in the bot.', openBot: 'Open the bot',
      errBusy: 'Too many requests. Wait a minute.', errLink: 'Could not download from this link.' },
    ru: { hello: 'Привет, {name}!', helloAnon: 'Привет!', helloLead: 'Всё для оформления профиля Steam прямо в Telegram.',
      toolCut: 'Нарезать файл', toolCutHint: 'Картинка, GIF или видео в файлы для витрины', toolDownload: 'Скачать', toolDownloadHint: 'YouTube, TikTok, Pinterest и другие',
      toolConvert: 'Конвертер', toolConvertHint: 'GIF ↔ видео, PNG, JPG, WebP', toolUpscale: 'Апскейл', toolUpscaleHint: 'Увеличить картинку или GIF нейросетью',
      toolInfobox: 'Инфо-поле', toolInfoboxHint: 'Шаблоны и редактор с предпросмотром как в Steam', toolNews: 'Новости', toolNewsHint: 'Что нового на сайте',
      unlimited: 'Pro · без ограничений', left: 'Сегодня осталось {left} из {limit}', pickFile: 'Выбери файл', pickHint: 'Картинка, GIF или видео до {mb} МБ', pickImage: 'Картинка, GIF или видео',
      showcase: 'Витрина', workshop: 'Мастерская', workshopHint: '5 частей', featured: 'Избранная', featuredHint: '1 файл', split: 'Иллюстрации', splitHint: '2 файла',
      frame: 'Рамка', frameNone: 'Без рамки', frameLine: 'Линия', frameNeon: 'Неон', frameRgb: 'RGB', cutGo: 'Нарезать для Steam',
      stageQueued: 'В очереди', stagePrepare: 'Готовим файл', stageCut: 'Нарезаем', stagePack: 'Упаковываем', stageWork: 'Обрабатываем', eta: '≈ {s} с', almost: 'почти готово',
      done: 'Готово', sendChat: 'В чат', download: 'Скачать', again: 'Ещё файл', sent: 'Отправлено в чат', howUpload: 'Как загрузить в Steam',
      urlLabel: 'Ссылка', sites: 'YouTube, TikTok, Pinterest, X, Tenor, Giphy, DeviantArt и прямые ссылки на файлы', downloadGo: 'Скачать',
      convertTo: 'Во что конвертировать', convertGo: 'Конвертировать', upModel: 'Модель', upGeneral: 'Фото', upAnime: 'Аниме', upSoft: 'Аниме мягко', upScale: 'Увеличение', upGo: 'Увеличить',
      upVideo2: 'Видео увеличивается только в 2 раза.', proOnly: 'Апскейл — функция Pro', proOnlyLead: 'Увеличивает картинку, GIF или видео в 2 или 4 раза на видеокарте.',
      noAccount: 'Pro уже есть? Один раз войди на сайте через Telegram, и приложение его увидит.', buyPro: 'Купить Pro', upOff: 'Апскейл сейчас недоступен. Попробуй позже.',
      templates: 'Шаблоны', all: 'Все', editor: 'Текст', preview: 'Как в Steam', copy: 'Копировать', copied: 'Скопировано', chars: '{n} / {max} символов',
      tooLong: 'Слишком длинно для Steam', textSent: 'Текст в чате', ibxHint: 'Вставь в Steam: Редактировать профиль → Витрина → Поле со своей информацией.',
      catAbout: 'Обо мне', catFrames: 'Рамки', catGames: 'Игры', catStream: 'Стримы', catQuotes: 'Цитаты', catAesthetic: 'Эстетика', catHoliday: 'Праздники', catArt: 'Арт', catFun: 'Юмор',
      newsEmpty: 'Новостей пока нет.', errLimit: 'Лимит на сегодня исчерпан. Pro снимает ограничения.', errActive: 'Предыдущий файл ещё нарезается.',
      errBig: 'Файл слишком большой.', errNetwork: 'Нет связи с сервером. Попробуй ещё раз.', errFailed: 'Не получилось. Попробуй другой файл.',
      errBlocked: 'Бот не может тебе написать: нажми «Старт» в чате с ботом.', errAuth: 'Открой приложение кнопкой «Обработать» слева от поля ввода в боте.', openBot: 'Открыть бота',
      errBusy: 'Слишком часто. Подожди минуту.', errLink: 'Не получилось скачать по этой ссылке.' },
    de: { hello: 'Hallo, {name}!', helloAnon: 'Hallo!', helloLead: 'Alles für dein Steam-Profil, direkt in Telegram.',
      toolCut: 'Datei zuschneiden', toolCutHint: 'Bild, GIF oder Video in Showcase-Dateien', toolDownload: 'Herunterladen', toolDownloadHint: 'YouTube, TikTok, Pinterest und mehr',
      toolConvert: 'Konverter', toolConvertHint: 'GIF ↔ Video, PNG, JPG, WebP', toolUpscale: 'Hochskalieren', toolUpscaleHint: 'Bild oder GIF mit KI vergrößern',
      toolInfobox: 'Infobox', toolInfoboxHint: 'Vorlagen und Editor mit Steam-Vorschau', toolNews: 'Neuigkeiten', toolNewsHint: 'Was es Neues auf der Seite gibt',
      unlimited: 'Pro · ohne Limits', left: 'Heute noch {left} von {limit}', pickFile: 'Datei wählen', pickHint: 'Bild, GIF oder Video bis {mb} MB', pickImage: 'Bild, GIF oder Video',
      showcase: 'Showcase', workshop: 'Workshop', workshopHint: '5 Teile', featured: 'Hervorgehoben', featuredHint: '1 Datei', split: 'Artwork', splitHint: '2 Dateien',
      frame: 'Rahmen', frameNone: 'Kein Rahmen', frameLine: 'Linie', frameNeon: 'Neon', frameRgb: 'RGB', cutGo: 'Für Steam zuschneiden',
      stageQueued: 'In der Warteschlange', stagePrepare: 'Datei wird vorbereitet', stageCut: 'Wird zugeschnitten', stagePack: 'Wird verpackt', stageWork: 'In Arbeit', eta: '≈ {s} s', almost: 'fast fertig',
      done: 'Fertig', sendChat: 'In den Chat', download: 'Herunterladen', again: 'Noch eine Datei', sent: 'In den Chat gesendet', howUpload: 'So lädst du es zu Steam hoch',
      urlLabel: 'Link', sites: 'YouTube, TikTok, Pinterest, X, Tenor, Giphy, DeviantArt und direkte Dateilinks', downloadGo: 'Herunterladen',
      convertTo: 'Umwandeln in', convertGo: 'Umwandeln', upModel: 'Modell', upGeneral: 'Foto', upAnime: 'Anime', upSoft: 'Anime sanft', upScale: 'Vergrößerung', upGo: 'Hochskalieren',
      upVideo2: 'Videos werden nur 2× vergrößert.', proOnly: 'Hochskalieren ist eine Pro-Funktion', proOnlyLead: 'Vergrößert ein Bild, GIF oder Video 2× oder 4× auf einer GPU.',
      noAccount: 'Schon Pro? Melde dich einmal auf der Seite mit Telegram an, dann sieht die App es.', buyPro: 'Pro holen', upOff: 'Hochskalieren ist gerade nicht verfügbar. Versuche es später.',
      templates: 'Vorlagen', all: 'Alle', editor: 'Text', preview: 'Wie in Steam', copy: 'Kopieren', copied: 'Kopiert', chars: '{n} / {max} Zeichen',
      tooLong: 'Zu lang für Steam', textSent: 'Der Text ist im Chat', ibxHint: 'In Steam einfügen: Profil bearbeiten → Showcase → Eigene Infobox.',
      catAbout: 'Über mich', catFrames: 'Rahmen', catGames: 'Spiele', catStream: 'Streams', catQuotes: 'Zitate', catAesthetic: 'Ästhetik', catHoliday: 'Feiertage', catArt: 'Kunst', catFun: 'Spaß',
      newsEmpty: 'Noch keine Neuigkeiten.', errLimit: 'Das heutige Limit ist aufgebraucht. Pro hebt die Limits auf.', errActive: 'Die vorige Datei wird noch zugeschnitten.',
      errBig: 'Die Datei ist zu groß.', errNetwork: 'Keine Verbindung zum Server. Versuche es noch einmal.', errFailed: 'Das hat nicht geklappt. Versuche eine andere Datei.',
      errBlocked: 'Der Bot kann dir nicht schreiben: Tippe im Chat mit dem Bot auf Start.', errAuth: 'Öffne die App über die Menütaste neben dem Eingabefeld im Bot.', openBot: 'Bot öffnen',
      errBusy: 'Zu viele Anfragen. Warte eine Minute.', errLink: 'Über diesen Link konnte nichts heruntergeladen werden.' },
    tr: { hello: 'Merhaba, {name}!', helloAnon: 'Merhaba!', helloLead: 'Steam profilin için her şey, doğrudan Telegram’da.',
      toolCut: 'Dosya kes', toolCutHint: 'Resim, GIF veya videoyu vitrin dosyalarına', toolDownload: 'İndir', toolDownloadHint: 'YouTube, TikTok, Pinterest ve daha fazlası',
      toolConvert: 'Dönüştürücü', toolConvertHint: 'GIF ↔ video, PNG, JPG, WebP', toolUpscale: 'Büyüt', toolUpscaleHint: 'Resmi veya GIF’i yapay zekâyla büyüt',
      toolInfobox: 'Bilgi kutusu', toolInfoboxHint: 'Şablonlar ve Steam önizlemeli düzenleyici', toolNews: 'Haberler', toolNewsHint: 'Sitede neler yeni',
      unlimited: 'Pro · sınırsız', left: 'Bugün {limit} içinden {left} kaldı', pickFile: 'Dosya seç', pickHint: '{mb} MB’a kadar resim, GIF veya video', pickImage: 'Resim, GIF veya video',
      showcase: 'Vitrin', workshop: 'Atölye', workshopHint: '5 parça', featured: 'Öne çıkan', featuredHint: '1 dosya', split: 'Çizim', splitHint: '2 dosya',
      frame: 'Çerçeve', frameNone: 'Çerçeve yok', frameLine: 'Çizgi', frameNeon: 'Neon', frameRgb: 'RGB', cutGo: 'Steam için kes',
      stageQueued: 'Sırada', stagePrepare: 'Dosya hazırlanıyor', stageCut: 'Kesiliyor', stagePack: 'Paketleniyor', stageWork: 'İşleniyor', eta: '≈ {s} sn', almost: 'neredeyse bitti',
      done: 'Hazır', sendChat: 'Sohbete', download: 'İndir', again: 'Başka dosya', sent: 'Sohbete gönderildi', howUpload: 'Steam’e nasıl yüklenir',
      urlLabel: 'Bağlantı', sites: 'YouTube, TikTok, Pinterest, X, Tenor, Giphy, DeviantArt ve doğrudan dosya bağlantıları', downloadGo: 'İndir',
      convertTo: 'Neye dönüştürülsün', convertGo: 'Dönüştür', upModel: 'Model', upGeneral: 'Fotoğraf', upAnime: 'Anime', upSoft: 'Yumuşak anime', upScale: 'Büyütme', upGo: 'Büyüt',
      upVideo2: 'Videolar yalnızca 2× büyütülür.', proOnly: 'Büyütme bir Pro özelliğidir', proOnlyLead: 'Resmi, GIF’i veya videoyu GPU’da 2× ya da 4× büyütür.',
      noAccount: 'Zaten Pro’n mu var? Sitede bir kez Telegram ile giriş yap, uygulama da görsün.', buyPro: 'Pro al', upOff: 'Büyütme şu an kullanılamıyor. Daha sonra dene.',
      templates: 'Şablonlar', all: 'Tümü', editor: 'Metin', preview: 'Steam’deki gibi', copy: 'Kopyala', copied: 'Kopyalandı', chars: '{n} / {max} karakter',
      tooLong: 'Steam için çok uzun', textSent: 'Metin sohbette', ibxHint: 'Steam’e yapıştır: Profili düzenle → Vitrin → Özel bilgi kutusu.',
      catAbout: 'Hakkımda', catFrames: 'Çerçeveler', catGames: 'Oyunlar', catStream: 'Yayınlar', catQuotes: 'Alıntılar', catAesthetic: 'Estetik', catHoliday: 'Bayramlar', catArt: 'Sanat', catFun: 'Eğlence',
      newsEmpty: 'Henüz haber yok.', errLimit: 'Bugünkü sınır doldu. Pro sınırları kaldırır.', errActive: 'Önceki dosya hâlâ kesiliyor.',
      errBig: 'Dosya çok büyük.', errNetwork: 'Sunucuya bağlanılamadı. Tekrar dene.', errFailed: 'Olmadı. Başka bir dosya dene.',
      errBlocked: 'Bot sana yazamıyor: botla sohbette Başlat’a dokun.', errAuth: 'Uygulamayı botta mesaj alanının yanındaki menü düğmesiyle aç.', openBot: 'Botu aç',
      errBusy: 'Çok fazla istek. Bir dakika bekle.', errLink: 'Bu bağlantıdan indirilemedi.' },
    fr: { hello: 'Salut, {name} !', helloAnon: 'Salut !', helloLead: 'Tout pour ton profil Steam, directement dans Telegram.',
      toolCut: 'Découper un fichier', toolCutHint: 'Image, GIF ou vidéo en fichiers de vitrine', toolDownload: 'Télécharger', toolDownloadHint: 'YouTube, TikTok, Pinterest et plus',
      toolConvert: 'Convertisseur', toolConvertHint: 'GIF ↔ vidéo, PNG, JPG, WebP', toolUpscale: 'Agrandir', toolUpscaleHint: 'Agrandir une image ou un GIF par IA',
      toolInfobox: 'Zone d’infos', toolInfoboxHint: 'Modèles et éditeur avec aperçu Steam', toolNews: 'Actualités', toolNewsHint: 'Les nouveautés du site',
      unlimited: 'Pro · sans limites', left: 'Encore {left} sur {limit} aujourd’hui', pickFile: 'Choisir un fichier', pickHint: 'Image, GIF ou vidéo jusqu’à {mb} Mo', pickImage: 'Image, GIF ou vidéo',
      showcase: 'Vitrine', workshop: 'Atelier', workshopHint: '5 parties', featured: 'En vedette', featuredHint: '1 fichier', split: 'Illustrations', splitHint: '2 fichiers',
      frame: 'Cadre', frameNone: 'Sans cadre', frameLine: 'Ligne', frameNeon: 'Néon', frameRgb: 'RGB', cutGo: 'Découper pour Steam',
      stageQueued: 'En file d’attente', stagePrepare: 'Préparation du fichier', stageCut: 'Découpage', stagePack: 'Emballage', stageWork: 'Traitement', eta: '≈ {s} s', almost: 'presque fini',
      done: 'Terminé', sendChat: 'Dans le chat', download: 'Télécharger', again: 'Un autre fichier', sent: 'Envoyé dans le chat', howUpload: 'Comment l’envoyer sur Steam',
      urlLabel: 'Lien', sites: 'YouTube, TikTok, Pinterest, X, Tenor, Giphy, DeviantArt et liens directs vers des fichiers', downloadGo: 'Télécharger',
      convertTo: 'Convertir en', convertGo: 'Convertir', upModel: 'Modèle', upGeneral: 'Photo', upAnime: 'Anime', upSoft: 'Anime doux', upScale: 'Agrandissement', upGo: 'Agrandir',
      upVideo2: 'Les vidéos sont agrandies 2× seulement.', proOnly: 'L’agrandissement est une fonction Pro', proOnlyLead: 'Agrandit une image, un GIF ou une vidéo 2× ou 4× sur GPU.',
      noAccount: 'Tu as déjà Pro ? Connecte-toi une fois sur le site avec Telegram et l’app le verra.', buyPro: 'Passer à Pro', upOff: 'L’agrandissement n’est pas disponible pour le moment. Réessaie plus tard.',
      templates: 'Modèles', all: 'Tous', editor: 'Texte', preview: 'Comme sur Steam', copy: 'Copier', copied: 'Copié', chars: '{n} / {max} caractères',
      tooLong: 'Trop long pour Steam', textSent: 'Le texte est dans le chat', ibxHint: 'Colle-le dans Steam : Modifier le profil → Vitrine → Zone d’infos personnalisée.',
      catAbout: 'À propos', catFrames: 'Cadres', catGames: 'Jeux', catStream: 'Streams', catQuotes: 'Citations', catAesthetic: 'Esthétique', catHoliday: 'Fêtes', catArt: 'Art', catFun: 'Humour',
      newsEmpty: 'Pas encore d’actualités.', errLimit: 'La limite du jour est atteinte. Pro supprime les limites.', errActive: 'Le fichier précédent est encore en découpe.',
      errBig: 'Le fichier est trop lourd.', errNetwork: 'Pas de connexion au serveur. Réessaie.', errFailed: 'Ça n’a pas marché. Essaie un autre fichier.',
      errBlocked: 'Le bot ne peut pas t’écrire : appuie sur Démarrer dans le chat avec le bot.', errAuth: 'Ouvre l’app avec le bouton de menu à côté du champ de message dans le bot.', openBot: 'Ouvrir le bot',
      errBusy: 'Trop de demandes. Attends une minute.', errLink: 'Impossible de télécharger depuis ce lien.' },
    uk: { hello: 'Привіт, {name}!', helloAnon: 'Привіт!', helloLead: 'Усе для оформлення профілю Steam просто в Telegram.',
      toolCut: 'Нарізати файл', toolCutHint: 'Картинка, GIF або відео у файли для вітрини', toolDownload: 'Завантажити', toolDownloadHint: 'YouTube, TikTok, Pinterest та інші',
      toolConvert: 'Конвертер', toolConvertHint: 'GIF ↔ відео, PNG, JPG, WebP', toolUpscale: 'Апскейл', toolUpscaleHint: 'Збільшити картинку або GIF нейромережею',
      toolInfobox: 'Інфо-поле', toolInfoboxHint: 'Шаблони й редактор із переглядом як у Steam', toolNews: 'Новини', toolNewsHint: 'Що нового на сайті',
      unlimited: 'Pro · без обмежень', left: 'Сьогодні лишилось {left} з {limit}', pickFile: 'Обери файл', pickHint: 'Картинка, GIF або відео до {mb} МБ', pickImage: 'Картинка, GIF або відео',
      showcase: 'Вітрина', workshop: 'Майстерня', workshopHint: '5 частин', featured: 'Вибрана', featuredHint: '1 файл', split: 'Ілюстрації', splitHint: '2 файли',
      frame: 'Рамка', frameNone: 'Без рамки', frameLine: 'Лінія', frameNeon: 'Неон', frameRgb: 'RGB', cutGo: 'Нарізати для Steam',
      stageQueued: 'У черзі', stagePrepare: 'Готуємо файл', stageCut: 'Нарізаємо', stagePack: 'Пакуємо', stageWork: 'Обробляємо', eta: '≈ {s} с', almost: 'майже готово',
      done: 'Готово', sendChat: 'У чат', download: 'Завантажити', again: 'Ще файл', sent: 'Надіслано в чат', howUpload: 'Як завантажити в Steam',
      urlLabel: 'Посилання', sites: 'YouTube, TikTok, Pinterest, X, Tenor, Giphy, DeviantArt і прямі посилання на файли', downloadGo: 'Завантажити',
      convertTo: 'У що конвертувати', convertGo: 'Конвертувати', upModel: 'Модель', upGeneral: 'Фото', upAnime: 'Аніме', upSoft: 'Аніме м’яко', upScale: 'Збільшення', upGo: 'Збільшити',
      upVideo2: 'Відео збільшується лише вдвічі.', proOnly: 'Апскейл — функція Pro', proOnlyLead: 'Збільшує картинку, GIF або відео в 2 чи 4 рази на відеокарті.',
      noAccount: 'Pro вже є? Один раз увійди на сайті через Telegram, і застосунок його побачить.', buyPro: 'Купити Pro', upOff: 'Апскейл зараз недоступний. Спробуй пізніше.',
      templates: 'Шаблони', all: 'Усі', editor: 'Текст', preview: 'Як у Steam', copy: 'Копіювати', copied: 'Скопійовано', chars: '{n} / {max} символів',
      tooLong: 'Задовго для Steam', textSent: 'Текст у чаті', ibxHint: 'Встав у Steam: Редагувати профіль → Вітрина → Поле зі своєю інформацією.',
      catAbout: 'Про мене', catFrames: 'Рамки', catGames: 'Ігри', catStream: 'Стріми', catQuotes: 'Цитати', catAesthetic: 'Естетика', catHoliday: 'Свята', catArt: 'Арт', catFun: 'Гумор',
      newsEmpty: 'Новин поки немає.', errLimit: 'Ліміт на сьогодні вичерпано. Pro знімає обмеження.', errActive: 'Попередній файл ще нарізається.',
      errBig: 'Файл завеликий.', errNetwork: 'Немає зв’язку із сервером. Спробуй ще раз.', errFailed: 'Не вийшло. Спробуй інший файл.',
      errBlocked: 'Бот не може тобі написати: натисни «Старт» у чаті з ботом.', errAuth: 'Відкрий застосунок кнопкою «Обработать» ліворуч від поля введення в боті.', openBot: 'Відкрити бота',
      errBusy: 'Надто часто. Зачекай хвилину.', errLink: 'Не вдалося завантажити за цим посиланням.' },
    es: { hello: '¡Hola, {name}!', helloAnon: '¡Hola!', helloLead: 'Todo para tu perfil de Steam, directamente en Telegram.',
      toolCut: 'Cortar un archivo', toolCutHint: 'Imagen, GIF o vídeo en archivos de escaparate', toolDownload: 'Descargar', toolDownloadHint: 'YouTube, TikTok, Pinterest y más',
      toolConvert: 'Conversor', toolConvertHint: 'GIF ↔ vídeo, PNG, JPG, WebP', toolUpscale: 'Ampliar', toolUpscaleHint: 'Ampliar una imagen o GIF con IA',
      toolInfobox: 'Cuadro de info', toolInfoboxHint: 'Plantillas y editor con vista de Steam', toolNews: 'Noticias', toolNewsHint: 'Novedades del sitio',
      unlimited: 'Pro · sin límites', left: 'Quedan {left} de {limit} hoy', pickFile: 'Elige un archivo', pickHint: 'Imagen, GIF o vídeo de hasta {mb} MB', pickImage: 'Imagen, GIF o vídeo',
      showcase: 'Escaparate', workshop: 'Taller', workshopHint: '5 partes', featured: 'Destacado', featuredHint: '1 archivo', split: 'Ilustraciones', splitHint: '2 archivos',
      frame: 'Marco', frameNone: 'Sin marco', frameLine: 'Línea', frameNeon: 'Neón', frameRgb: 'RGB', cutGo: 'Cortar para Steam',
      stageQueued: 'En cola', stagePrepare: 'Preparando el archivo', stageCut: 'Cortando', stagePack: 'Empaquetando', stageWork: 'Procesando', eta: '≈ {s} s', almost: 'casi listo',
      done: 'Listo', sendChat: 'Al chat', download: 'Descargar', again: 'Otro archivo', sent: 'Enviado al chat', howUpload: 'Cómo subirlo a Steam',
      urlLabel: 'Enlace', sites: 'YouTube, TikTok, Pinterest, X, Tenor, Giphy, DeviantArt y enlaces directos a archivos', downloadGo: 'Descargar',
      convertTo: 'Convertir a', convertGo: 'Convertir', upModel: 'Modelo', upGeneral: 'Foto', upAnime: 'Anime', upSoft: 'Anime suave', upScale: 'Ampliación', upGo: 'Ampliar',
      upVideo2: 'Los vídeos solo se amplían 2×.', proOnly: 'Ampliar es una función Pro', proOnlyLead: 'Amplía una imagen, GIF o vídeo 2× o 4× en una GPU.',
      noAccount: '¿Ya tienes Pro? Inicia sesión una vez en el sitio con Telegram y la app lo verá.', buyPro: 'Conseguir Pro', upOff: 'Ampliar no está disponible ahora. Inténtalo más tarde.',
      templates: 'Plantillas', all: 'Todas', editor: 'Texto', preview: 'Como en Steam', copy: 'Copiar', copied: 'Copiado', chars: '{n} / {max} caracteres',
      tooLong: 'Demasiado largo para Steam', textSent: 'El texto está en el chat', ibxHint: 'Pégalo en Steam: Editar perfil → Escaparate → Cuadro de información personalizado.',
      catAbout: 'Sobre mí', catFrames: 'Marcos', catGames: 'Juegos', catStream: 'Streams', catQuotes: 'Citas', catAesthetic: 'Estética', catHoliday: 'Fiestas', catArt: 'Arte', catFun: 'Humor',
      newsEmpty: 'Aún no hay noticias.', errLimit: 'Se acabó el límite de hoy. Pro quita los límites.', errActive: 'El archivo anterior aún se está cortando.',
      errBig: 'El archivo es demasiado grande.', errNetwork: 'Sin conexión con el servidor. Inténtalo de nuevo.', errFailed: 'No funcionó. Prueba otro archivo.',
      errBlocked: 'El bot no puede escribirte: pulsa Iniciar en el chat con el bot.', errAuth: 'Abre la app con el botón de menú junto al campo de mensaje en el bot.', openBot: 'Abrir el bot',
      errBusy: 'Demasiadas solicitudes. Espera un minuto.', errLink: 'No se pudo descargar desde este enlace.' },
    pt: { hello: 'Olá, {name}!', helloAnon: 'Olá!', helloLead: 'Tudo para o seu perfil Steam, direto no Telegram.',
      toolCut: 'Cortar arquivo', toolCutHint: 'Imagem, GIF ou vídeo em arquivos de vitrine', toolDownload: 'Baixar', toolDownloadHint: 'YouTube, TikTok, Pinterest e mais',
      toolConvert: 'Conversor', toolConvertHint: 'GIF ↔ vídeo, PNG, JPG, WebP', toolUpscale: 'Ampliar', toolUpscaleHint: 'Ampliar imagem ou GIF com IA',
      toolInfobox: 'Caixa de info', toolInfoboxHint: 'Modelos e editor com prévia do Steam', toolNews: 'Notícias', toolNewsHint: 'O que há de novo no site',
      unlimited: 'Pro · sem limites', left: 'Restam {left} de {limit} hoje', pickFile: 'Escolha um arquivo', pickHint: 'Imagem, GIF ou vídeo de até {mb} MB', pickImage: 'Imagem, GIF ou vídeo',
      showcase: 'Vitrine', workshop: 'Oficina', workshopHint: '5 partes', featured: 'Destaque', featuredHint: '1 arquivo', split: 'Ilustrações', splitHint: '2 arquivos',
      frame: 'Moldura', frameNone: 'Sem moldura', frameLine: 'Linha', frameNeon: 'Neon', frameRgb: 'RGB', cutGo: 'Cortar para o Steam',
      stageQueued: 'Na fila', stagePrepare: 'Preparando o arquivo', stageCut: 'Cortando', stagePack: 'Empacotando', stageWork: 'Processando', eta: '≈ {s} s', almost: 'quase pronto',
      done: 'Pronto', sendChat: 'No chat', download: 'Baixar', again: 'Outro arquivo', sent: 'Enviado ao chat', howUpload: 'Como enviar para o Steam',
      urlLabel: 'Link', sites: 'YouTube, TikTok, Pinterest, X, Tenor, Giphy, DeviantArt e links diretos de arquivos', downloadGo: 'Baixar',
      convertTo: 'Converter para', convertGo: 'Converter', upModel: 'Modelo', upGeneral: 'Foto', upAnime: 'Anime', upSoft: 'Anime suave', upScale: 'Ampliação', upGo: 'Ampliar',
      upVideo2: 'Vídeos são ampliados só 2×.', proOnly: 'Ampliar é um recurso Pro', proOnlyLead: 'Amplia imagem, GIF ou vídeo 2× ou 4× em uma GPU.',
      noAccount: 'Já tem Pro? Entre no site uma vez com o Telegram e o app vai reconhecer.', buyPro: 'Assinar Pro', upOff: 'Ampliar não está disponível agora. Tente mais tarde.',
      templates: 'Modelos', all: 'Todos', editor: 'Texto', preview: 'Como no Steam', copy: 'Copiar', copied: 'Copiado', chars: '{n} / {max} caracteres',
      tooLong: 'Longo demais para o Steam', textSent: 'O texto está no chat', ibxHint: 'Cole no Steam: Editar perfil → Vitrine → Caixa de informações personalizada.',
      catAbout: 'Sobre mim', catFrames: 'Molduras', catGames: 'Jogos', catStream: 'Lives', catQuotes: 'Citações', catAesthetic: 'Estética', catHoliday: 'Feriados', catArt: 'Arte', catFun: 'Humor',
      newsEmpty: 'Ainda não há notícias.', errLimit: 'O limite de hoje acabou. O Pro remove os limites.', errActive: 'O arquivo anterior ainda está sendo cortado.',
      errBig: 'O arquivo é grande demais.', errNetwork: 'Sem conexão com o servidor. Tente de novo.', errFailed: 'Não deu certo. Tente outro arquivo.',
      errBlocked: 'O bot não consegue te escrever: toque em Iniciar no chat com o bot.', errAuth: 'Abra o app pelo botão de menu ao lado do campo de mensagem no bot.', openBot: 'Abrir o bot',
      errBusy: 'Muitas solicitações. Espere um minuto.', errLink: 'Não foi possível baixar deste link.' }
  };

  var TG = window.Telegram && window.Telegram.WebApp;
  var INIT = (TG && TG.initData) || '';
  var tgUser = (TG && TG.initDataUnsafe && TG.initDataUnsafe.user) || {};
  // Apps opened from a reply-keyboard button get no initData: the bot then signs the link itself (?k=, smweb/tg_app.py).
  var LAUNCH = (function () {
    var k = '';
    try { k = new URLSearchParams(location.search).get('k') || sessionStorage.getItem('sm_tga_k') || ''; } catch (_) {}
    try { if (k) sessionStorage.setItem('sm_tga_k', k); } catch (_) {}
    return /^\d{3,20}\.\d+\.[a-z-]{0,8}\.[0-9a-f]{32}$/.test(k) ? k : '';
  })();
  var LANG = (function () {
    var code = String(tgUser.language_code || (LAUNCH && LAUNCH.split('.')[2]) || navigator.language || 'en').slice(0, 2).toLowerCase();
    return COPY[code] ? code : (code === 'be' || code === 'kk' ? 'ru' : 'en');
  })();
  document.documentElement.lang = LANG;
  function t(key, vars) {
    var text = (COPY[LANG] || COPY.en)[key] || COPY.en[key] || key;
    Object.keys(vars || {}).forEach(function (k) { text = text.replace('{' + k + '}', vars[k]); });
    return text;
  }
  function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  function btn(cls, text, onClick) { var b = el('button', cls, text); b.type = 'button'; if (onClick) b.addEventListener('click', onClick); return b; }
  var main = document.getElementById('tgaMain');
  var planChip = document.getElementById('tgaPlan');
  var backBtn = document.getElementById('tgaBack');
  var state = { view: 'home', me: null, bot: '', polls: 0 };

  // ---------------------------------------------------------------- Telegram shell
  if (TG) {
    try {
      TG.ready(); TG.expand();
      TG.setHeaderColor('#03070a'); TG.setBackgroundColor('#03070a');
      if (TG.setBottomBarColor) TG.setBottomBarColor('#03070a');
      if (TG.disableVerticalSwipes) TG.disableVerticalSwipes();
      TG.BackButton.onClick(function () { go('home'); });
    } catch (_) {}
  }
  function haptic(kind) { try { if (TG && TG.HapticFeedback) TG.HapticFeedback.notificationOccurred(kind); } catch (_) {} }
  function tap() { try { if (TG && TG.HapticFeedback) TG.HapticFeedback.selectionChanged(); } catch (_) {} }
  var toastTimer = 0;
  function toast(text) {
    var box = document.getElementById('tgaToast');
    box.textContent = text; box.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(function () { box.hidden = true; }, 2600);
  }
  function openLink(url) { if (TG && TG.openLink) TG.openLink(url); else window.open(url, '_blank', 'noopener'); }
  function siteUrl(path) { return location.origin + '/' + (COPY[LANG] ? LANG : 'en') + path; }

  // ---------------------------------------------------------------- API
  function api(path, options) {
    options = options || {};
    var headers = INIT ? { 'X-Tg-Init-Data': INIT } : { 'X-Tg-Launch': LAUNCH };
    var body = options.body;
    if (body && !(body instanceof FormData)) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(body); }
    return fetch(path, { method: options.method || (body ? 'POST' : 'GET'), headers: headers, body: body, credentials: 'same-origin' })
      .catch(function () { throw { code: 'network' }; })
      .then(function (r) {
        return r.json().catch(function () { return {}; }).then(function (data) {
          if (!r.ok || data.ok === false) throw { code: data.code || (r.status === 429 ? 'busy' : 'failed'), status: r.status, data: data };
          return data;
        });
      });
  }
  function errorText(error) {
    var code = error && error.code;
    return t({ limit: 'errLimit', active: 'errActive', too_big: 'errBig', network: 'errNetwork', blocked: 'errBlocked', auth: 'errAuth',
      busy: 'errBusy', no_account: 'noAccount', pro: 'proOnly' }[code] || 'errFailed');
  }
  function refreshMe() {
    return api('/api/tg-app/me').then(function (me) { state.me = me; paintPlan(); return me; });
  }
  function paintPlan() {
    var me = state.me;
    if (!me) return;
    planChip.hidden = false;
    planChip.classList.toggle('is-pro', !!me.pro);
    planChip.textContent = me.pro ? 'Pro' : (me.quota.left + ' / ' + me.quota.limit);
    document.querySelectorAll('.tga-quota').forEach(function (line) { line.replaceWith(quotaLine()); });
  }
  function quotaLine() {
    var me = state.me, q = me && me.quota;
    if (!q) return el('p', 'tga-quota', '');
    return el('p', 'tga-quota', me.pro ? t('unlimited') : t('left', { left: q.left, limit: q.limit }));
  }

  // ---------------------------------------------------------------- navigation
  var TOOLS = [
    ['cut', 'process', 'toolCut', 'toolCutHint'], ['download', 'download', 'toolDownload', 'toolDownloadHint'],
    ['convert', 'converter', 'toolConvert', 'toolConvertHint'], ['upscale', 'upscale', 'toolUpscale', 'toolUpscaleHint'],
    ['infobox', 'infobox', 'toolInfobox', 'toolInfoboxHint'], ['news', 'about', 'toolNews', 'toolNewsHint']
  ];
  function icon(name) {
    var box = el('span', 'tga-ico'), i = el('i');
    i.style.setProperty('--icon', 'url(/static/img/tool-icons/' + name + '.svg)');
    box.append(i);
    return box;
  }
  function go(view) {
    state.view = view; state.polls++;
    window.scrollTo(0, 0);
    var home = view === 'home';
    backBtn.hidden = home || !!(TG && TG.BackButton && TG.platform !== 'unknown');
    if (TG && TG.BackButton) { if (home) TG.BackButton.hide(); else TG.BackButton.show(); }
    main.replaceChildren();
    ({ home: viewHome, cut: viewCut, download: viewDownload, convert: viewConvert, upscale: viewUpscale, infobox: viewInfobox, news: viewNews }[view] || viewHome)();
  }
  backBtn.addEventListener('click', function () { go('home'); });
  document.getElementById('tgaHome').addEventListener('click', function (e) { e.preventDefault(); go('home'); });
  function header(tool) {
    var def = TOOLS.filter(function (x) { return x[0] === tool; })[0];
    var h = el('h1', 'tga-title'); h.append(icon(def[1]), el('span', '', t(def[2])));
    main.append(h, el('p', 'tga-lead', t(def[3])));
  }

  function viewHome() {
    var hello = el('div', 'tga-hello');
    var name = tgUser.first_name || '';
    hello.append(el('h1', '', name ? t('hello', { name: name }) : t('helloAnon')), el('p', '', t('helloLead')));
    var grid = el('div', 'tga-grid');
    TOOLS.forEach(function (tool) {
      var tile = btn('tga-tile' + (tool[0] === 'cut' || tool[0] === 'news' ? ' tga-tile--wide' : ''), null, function () { tap(); go(tool[0]); });
      tile.append(icon(tool[1]), el('b', '', t(tool[2])), el('small', '', t(tool[3])));
      if (tool[0] === 'upscale') tile.append(el('span', 'tga-tag', 'PRO'));
      grid.append(tile);
    });
    main.append(hello, grid);
  }

  // ---------------------------------------------------------------- shared pieces
  function filePicker(accept, onPick) {
    var label = el('label', 'tga-drop');
    var input = el('input'); input.type = 'file'; input.accept = accept;
    function empty() {
      label.classList.remove('has-file');
      label.replaceChildren(input, el('b', '', t('pickFile')), el('small', '', t('pickHint', { mb: (state.me && state.me.max_mb) || 100 })));
    }
    input.addEventListener('change', function () {
      var file = input.files && input.files[0];
      if (!file) { empty(); onPick(null); return; }
      label.classList.add('has-file');
      var thumb;
      if (/^image\//.test(file.type)) { thumb = el('img', 'tga-thumb'); thumb.src = URL.createObjectURL(file); thumb.alt = ''; }
      else thumb = el('span', 'tga-thumb', /^video\//.test(file.type) ? '🎬' : '📄');
      var info = el('span', 'tga-file');
      info.append(el('b', '', file.name), el('small', '', (file.size / 1048576).toFixed(1) + ' MB'));
      label.replaceChildren(input, thumb, info);
      onPick(file);
    });
    empty();
    return label;
  }
  function chips(options, current, onPick, scroll) {
    var row = el('div', 'tga-chips' + (scroll ? ' tga-chips--scroll' : ''));
    options.forEach(function (option) {
      var b = btn('tga-chip' + (option[0] === current ? ' is-on' : ''), option[1], function () {
        tap();
        row.querySelectorAll('.tga-chip').forEach(function (x) { x.classList.toggle('is-on', x === b); });
        onPick(option[0]);
      });
      row.append(b);
    });
    return row;
  }
  function card(label) { var c = el('section', 'tga-card'); if (label) c.append(el('span', 'tga-label', label)); return c; }
  function busy(button, on) {
    button.disabled = on;
    if (on) { button.dataset.text = button.textContent; button.replaceChildren(el('span', 'tga-spin')); }
    else if (button.dataset.text) button.textContent = button.dataset.text;
  }
  function stageText(stage) {
    stage = String(stage || '');
    if (!stage || stage === 'queued') return t('stageQueued');
    if (/^(prepare|file|depth|grade|download)/.test(stage)) return t('stagePrepare');
    if (/^(image|gif|video|cut|frames|encode)/.test(stage)) return t('stageCut');
    if (/^(upload|zip|pack|save|done)/.test(stage)) return t('stagePack');
    return t('stageWork');
  }
  function progressCard() {
    var box = card(null), wrap = el('div', 'tga-progress'), bar = el('div', 'tga-bar'), fill = el('i');
    var line = el('div', 'tga-stage'), stage = el('span', '', t('stageQueued')), eta = el('span', '', '');
    bar.append(fill); line.append(stage, eta); wrap.append(bar, line); box.append(wrap);
    var shown = 0;
    box.update = function (s) {
      shown = Math.max(shown, Math.min(99, Math.max(Number(s.pct) || 0, Number(s.pct_time) || 0)));
      fill.style.width = shown + '%';
      stage.textContent = stageText(s.stage);
      eta.textContent = s.eta_over ? t('almost') : (s.eta_seconds > 0 ? t('eta', { s: Math.round(s.eta_seconds) }) : '');
    };
    return box;
  }
  function poll(url, progress, done, fail) {
    var ticket = state.polls, misses = 0;
    function step() {
      if (ticket !== state.polls) return;
      api(url).then(function (s) {
        misses = 0;
        if (progress) progress.update(s);
        if (s.status === 'done') done(s);
        else if (s.status === 'error' || s.status === 'cancelled') fail(s);
        else setTimeout(step, 1500);
      }).catch(function (error) {
        if (++misses > 6 || (error && error.status === 404)) fail(error);
        else setTimeout(step, 2500);
      });
    }
    step();
  }
  function errorBox(text) { return el('div', 'tga-error', text); }
  function downloadFile(url, name) {
    var full = location.origin + url;
    try {
      if (TG && TG.downloadFile && TG.isVersionAtLeast && TG.isVersionAtLeast('8.0')) { TG.downloadFile({ url: full, file_name: name }); return; }
    } catch (_) {}
    var a = el('a'); a.href = full; a.download = name; document.body.append(a); a.click(); a.remove();
  }
  function resultCard(result, extra) {
    var box = card(null), wrap = el('div', 'tga-result');
    wrap.append(el('div', 'tga-done', t('done')));
    var type = String(result.type || '');
    if (/^image\//.test(type)) { var img = el('img', 'tga-preview'); img.src = result.preview; img.alt = ''; wrap.append(img); }
    else if (/^video\//.test(type)) { var video = el('video', 'tga-preview'); video.src = result.preview; video.controls = true; video.playsInline = true; video.muted = true; video.loop = true; video.autoplay = true; wrap.append(video); }
    if (extra) wrap.append(extra);
    var row = el('div', 'tga-row');
    var send = btn('tga-btn', '✈ ' + t('sendChat'), function () {
      busy(send, true);
      api('/api/tg-app/send', { body: { kind: result.kind, ref: result.ref } }).then(function () {
        busy(send, false); haptic('success'); toast(t('sent'));
      }).catch(function (error) { busy(send, false); haptic('error'); toast(errorText(error)); });
    });
    var dl = btn('tga-btn tga-btn--ghost', '⬇ ' + t('download'), function () { downloadFile(result.download, result.name); });
    row.append(send, dl);
    wrap.append(row);
    box.append(wrap);
    return box;
  }

  // ---------------------------------------------------------------- cut
  function viewCut() {
    header('cut');
    var pick = { file: null, mode: 'workshop', frame: 'none' };
    var fileCard = card(null);
    fileCard.append(filePicker('image/*,video/*,.gif,.webp,.mp4,.webm,.mov', function (f) { pick.file = f; refresh(); }));
    var typeCard = card(t('showcase')), types = el('div', 'tga-types');
    [['workshop', 'workshopHint', 5, ''], ['featured', 'featuredHint', 1, ''], ['split', 'splitHint', 2, ' tga-diagram--split']].forEach(function (m) {
      var b = btn('tga-type' + (pick.mode === m[0] ? ' is-on' : ''), null, function () {
        tap(); pick.mode = m[0];
        types.querySelectorAll('.tga-type').forEach(function (x) { x.classList.toggle('is-on', x === b); });
      });
      var diagram = el('span', 'tga-diagram' + m[3]);
      for (var i = 0; i < m[2]; i++) diagram.append(el('span'));
      b.append(diagram, el('b', '', t(m[0])), el('small', '', t(m[1])));
      types.append(b);
    });
    typeCard.append(types);
    var frameCard = card(t('frame'));
    frameCard.append(chips([['none', t('frameNone')], ['line', t('frameLine')], ['neon', t('frameNeon')], ['rgb', t('frameRgb')]], 'none', function (v) { pick.frame = v; }));
    var go2 = btn('tga-btn', '✂ ' + t('cutGo'), start);
    var out = el('div');
    main.append(fileCard, typeCard, frameCard, quotaLine(), go2, out);
    function refresh() { go2.disabled = !pick.file; }
    refresh();
    function start() {
      if (!pick.file) return;
      var form = new FormData();
      form.append('file', pick.file); form.append('mode', pick.mode); form.append('frame', pick.frame);
      busy(go2, true); out.replaceChildren();
      api('/api/tg-app/cut/start', { body: form }).then(function (r) {
        var progress = progressCard();
        out.replaceChildren(progress);
        go2.hidden = true;
        refreshMe();
        poll('/api/tg-app/cut/status/' + r.job_id, progress, function (s) {
          api('/api/tg-app/link', { body: { kind: 'cut', ref: r.job_id } }).then(function (res) {
            var files = el('div', 'tga-files');
            (s.files || []).forEach(function (name) { files.append(el('span', '', String(name).split('/').pop())); });
            var how = btn('tga-link', t('howUpload') + ' →', function () { openLink(siteUrl('/extension')); });
            var extra = el('div'); extra.append(files);
            out.replaceChildren(resultCard(res, extra), how, btn('tga-btn tga-btn--ghost', t('again'), function () { go('cut'); }));
            haptic('success');
          });
        }, function (error) { haptic('error'); out.replaceChildren(errorBox(errorText(error))); go2.hidden = false; busy(go2, false); });
      }).catch(function (error) { busy(go2, false); haptic('error'); out.replaceChildren(errorBox(errorText(error))); });
    }
  }

  // ---------------------------------------------------------------- download by link
  function viewDownload() {
    header('download');
    var box = card(t('urlLabel'));
    var input = el('input', 'tga-input'); input.type = 'url'; input.inputMode = 'url'; input.placeholder = 'https://'; input.autocomplete = 'off';
    box.append(input, el('p', 'tga-hint', t('sites')));
    var run = btn('tga-btn', '⬇ ' + t('downloadGo'), start);
    var out = el('div');
    main.append(box, quotaLine(), run, out);
    function start() {
      var url = input.value.trim();
      if (!/^https?:\/\//i.test(url)) { input.focus(); return; }
      busy(run, true); out.replaceChildren();
      api('/api/tg-app/download', { body: { url: url } }).then(function (res) {
        busy(run, false); refreshMe(); haptic('success');
        out.replaceChildren(resultCard(res));
      }).catch(function (error) {
        busy(run, false); haptic('error');
        out.replaceChildren(errorBox(error && error.status === 400 && !((error.data || {}).code) ? t('errLink') : errorText(error)));
      });
    }
  }

  // ---------------------------------------------------------------- convert
  function viewConvert() {
    header('convert');
    var pick = { file: null, target: 'gif' };
    var fileCard = card(null), targetCard = card(t('convertTo'));
    var targets = el('div');
    function paintTargets() {
      targets.replaceChildren(chips([['gif', 'GIF'], ['mp4', 'MP4'], ['webm', 'WEBM'], ['png', 'PNG'], ['jpg', 'JPG'], ['webp', 'WEBP']], pick.target, function (v) { pick.target = v; }));
    }
    fileCard.append(filePicker('image/*,video/*,.gif', function (f) {
      pick.file = f;
      if (f) pick.target = /^video\//.test(f.type) ? 'gif' : /gif$/.test(f.type) ? 'mp4' : /png$/.test(f.type) ? 'jpg' : 'png';
      paintTargets(); run.disabled = !f;
    }));
    paintTargets();
    targetCard.append(targets);
    var run = btn('tga-btn', '⇄ ' + t('convertGo'), start); run.disabled = true;
    var out = el('div');
    main.append(fileCard, targetCard, quotaLine(), run, out);
    function start() {
      if (!pick.file) return;
      var form = new FormData(); form.append('file', pick.file); form.append('target', pick.target);
      busy(run, true); out.replaceChildren();
      api('/api/tg-app/convert', { body: form }).then(function (res) {
        busy(run, false); refreshMe(); haptic('success'); out.replaceChildren(resultCard(res));
      }).catch(function (error) { busy(run, false); haptic('error'); out.replaceChildren(errorBox(errorText(error))); });
    }
  }

  // ---------------------------------------------------------------- upscale
  function viewUpscale() {
    header('upscale');
    var me = state.me || {};
    if (!me.upscale) { main.append(errorBox(t('upOff'))); return; }
    if (!me.pro) {
      var box = card(null);
      box.append(el('b', '', t('proOnly')), el('p', 'tga-hint', t('proOnlyLead')), el('p', 'tga-hint', t('noAccount')));
      var buy = btn('tga-btn', '💎 ' + t('buyPro'), function () {
        if (state.bot && TG && TG.openTelegramLink) { TG.openTelegramLink('https://t.me/' + state.bot + '?start=buy'); TG.close(); }
        else openLink(siteUrl('/?activate=1'));
      });
      main.append(box, buy);
      return;
    }
    var pick = { file: null, preset: 'general', scale: 2 };
    var fileCard = card(null), modelCard = card(t('upModel')), scaleCard = card(t('upScale'));
    var note = el('p', 'tga-hint', t('upVideo2')); note.hidden = true;
    fileCard.append(filePicker('image/png,image/jpeg,image/webp,image/gif,video/*', function (f) {
      pick.file = f; run.disabled = !f;
      var video = !!(f && /^video\//.test(f.type));
      note.hidden = !video;
      if (video) { pick.scale = 2; paintScale(); }
    }));
    modelCard.append(chips([['general', t('upGeneral')], ['anime', t('upAnime')], ['anime_soft', t('upSoft')]], 'general', function (v) { pick.preset = v; }));
    var scaleRow = el('div');
    function paintScale() { scaleRow.replaceChildren(chips([[2, '2×'], [4, '4×']], pick.scale, function (v) { pick.scale = v; })); }
    paintScale();
    scaleCard.append(scaleRow, note);
    var run = btn('tga-btn', '✦ ' + t('upGo'), start); run.disabled = true;
    var out = el('div');
    main.append(fileCard, modelCard, scaleCard, run, out);
    function start() {
      if (!pick.file) return;
      var form = new FormData();
      form.append('file', pick.file); form.append('preset', pick.preset); form.append('scale', String(pick.scale));
      busy(run, true); out.replaceChildren();
      api('/api/tg-app/upscale/start', { body: form }).then(function (r) {
        var progress = progressCard();
        out.replaceChildren(progress); run.hidden = true;
        poll('/api/tg-app/upscale/status/' + r.job_id, progress, function (s) {
          haptic('success');
          out.replaceChildren(resultCard(s), btn('tga-btn tga-btn--ghost', t('again'), function () { go('upscale'); }));
        }, function (error) { haptic('error'); out.replaceChildren(errorBox(errorText(error))); run.hidden = false; busy(run, false); });
      }).catch(function (error) { busy(run, false); haptic('error'); out.replaceChildren(errorBox(errorText(error))); });
    }
  }

  // ---------------------------------------------------------------- info box (renderer and templates of static/js/infobox.js)
  var DRAFT = 'sm_tga_infobox';
  var SYMBOLS = ['✦', '★', '♡', '➤', '•', '━', '┃', '┏', '┗', '═', '❖', '⚔', '🎮', '✧'];
  function viewInfobox() {
    header('infobox');
    var engine = window.SMInfoBox || {};
    var limit = engine.limit || 8000;
    var templates = engine.templates || window.SM_INFOBOX_TEMPLATES || [];
    var slavic = LANG === 'ru' || LANG === 'uk';
    var text = '';
    try { text = localStorage.getItem(DRAFT) || ''; } catch (_) {}
    var cats = ['all'];
    templates.forEach(function (tpl) { if (cats.indexOf(tpl.cat) < 0) cats.push(tpl.cat); });
    var cat = 'all';
    var tplCard = card(t('templates')), catRow = el('div'), list = el('div', 'tga-chips tga-chips--scroll');
    catRow.append(chips(cats.map(function (c) { return [c, c === 'all' ? t('all') : t('cat' + c.charAt(0).toUpperCase() + c.slice(1))]; }), 'all', function (c) { cat = c; paintList(); }, true));
    catRow.style.marginBottom = '8px';
    function paintList() {
      list.replaceChildren();
      templates.filter(function (tpl) { return cat === 'all' || tpl.cat === cat; }).forEach(function (tpl) {
        list.append(btn('tga-chip', slavic ? tpl.name.ru : tpl.name.en, function () { tap(); area.value = slavic ? tpl.ru : tpl.en; changed(); area.scrollIntoView({ block: 'center', behavior: 'smooth' }); }));
      });
    }
    paintList();
    tplCard.append(catRow, list);
    var editCard = card(t('editor'));
    var area = el('textarea', 'tga-text'); area.value = text; area.spellcheck = false;
    var symbols = el('div', 'tga-symbols');
    SYMBOLS.forEach(function (s) {
      symbols.append(btn('', s, function () {
        var a = area.selectionStart || area.value.length, b = area.selectionEnd || a;
        area.value = area.value.slice(0, a) + s + area.value.slice(b);
        area.focus(); area.selectionStart = area.selectionEnd = a + s.length; changed();
      }));
    });
    var count = el('div', 'tga-count'), counter = el('span'), warn = el('span', 'is-bad');
    count.append(counter, warn);
    editCard.append(area, symbols, count);
    var previewCard = card(t('preview')), wrap = el('div', 'tga-steam-wrap'), steam = el('div', 'tga-steam');
    var head = el('div', 'tga-steam__head', slavic ? 'Поле со своей информацией' : 'Custom Info Box'), content = el('div', 'tga-steam__content');
    steam.append(head, content); wrap.append(steam); previewCard.append(wrap);
    var row = el('div', 'tga-row');
    var copyBtn = btn('tga-btn tga-btn--ghost', '⧉ ' + t('copy'), function () {
      var done = function () { toast(t('copied')); haptic('success'); };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(area.value).then(done, fallback); else fallback();
      function fallback() { area.select(); try { document.execCommand('copy'); done(); } catch (_) {} }
    });
    var sendBtn = btn('tga-btn', '✈ ' + t('sendChat'), function () {
      if (!area.value.trim()) return;
      busy(sendBtn, true);
      api('/api/tg-app/text', { body: { text: area.value } }).then(function () { busy(sendBtn, false); toast(t('textSent')); haptic('success'); })
        .catch(function (error) { busy(sendBtn, false); toast(errorText(error)); haptic('error'); });
    });
    row.append(copyBtn, sendBtn);
    main.append(tplCard, editCard, previewCard, row, el('p', 'tga-hint', t('ibxHint')));
    function fit() {
      var width = wrap.clientWidth - 20;
      var scale = Math.min(1, width / 640);
      steam.style.transform = 'scale(' + scale + ')';
      wrap.style.height = Math.ceil(steam.offsetHeight * scale + 20) + 'px';
    }
    var timer = 0;
    function changed() {
      try { localStorage.setItem(DRAFT, area.value); } catch (_) {}
      counter.textContent = t('chars', { n: area.value.length, max: limit });
      warn.textContent = area.value.length > limit ? t('tooLong') : '';
      clearTimeout(timer);
      timer = setTimeout(function () { if (engine.render) engine.render(area.value, content); else content.textContent = area.value; fit(); }, 120);
    }
    area.addEventListener('input', changed);
    window.addEventListener('resize', fit);
    changed();
  }

  // ---------------------------------------------------------------- news
  function viewNews() {
    header('news');
    var list = el('div', 'tga-news');
    list.append(el('div', 'tga-empty', '…'));
    main.append(list);
    fetch('/api/news?limit=12&lang=' + encodeURIComponent(LANG)).then(function (r) { return r.json(); }).then(function (data) {
      list.replaceChildren();
      var items = (data && data.items) || [];
      if (!items.length) { list.append(el('div', 'tga-empty', t('newsEmpty'))); return; }
      items.forEach(function (post) {
        var item = btn('tga-post', null, function () { openLink(siteUrl('/news/' + encodeURIComponent(post.slug))); });
        if (post.cover_url) { var img = el('img'); img.src = post.cover_url; img.alt = ''; img.loading = 'lazy'; item.append(img); }
        var body = el('div');
        var date = post.published_at ? new Date(post.published_at * 1000).toLocaleDateString(LANG, { day: 'numeric', month: 'long' }) : '';
        body.append(el('small', '', date), el('b', '', post.title), post.summary ? el('p', '', post.summary) : el('span'));
        item.append(body);
        list.append(item);
      });
    }).catch(function () { list.replaceChildren(errorBox(t('errNetwork'))); });
  }

  // ---------------------------------------------------------------- start
  fetch('/api/tg-app/config').then(function (r) { return r.json(); }).then(function (cfg) { state.bot = cfg.bot || ''; }).catch(function () {});
  if (!INIT && !LAUNCH) {
    main.replaceChildren();
    var box = card(null);
    box.append(el('b', '', t('errAuth')));
    main.append(box);
    setTimeout(function () {
      if (state.bot) main.append(btn('tga-btn', t('openBot'), function () { location.href = 'https://t.me/' + state.bot; }));
    }, 600);
    return;
  }
  go('home');
  refreshMe().catch(function (error) { if (error && error.code === 'auth') { main.replaceChildren(errorBox(t('errAuth'))); } });
  window.SMTgApp = { go: go, state: state };
})();
