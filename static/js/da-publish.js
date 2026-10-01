/* DeviantArt publishing (2026-10-01, owner request): files -> title, download link, price,
   formatted description (bold, links, headings, separators, emoji), tags and every publish
   option (Mature, NoAI, AI-made, gallery folders, display size, watermark, free download,
   comments, feature). Publish right away or keep a Sta.sh draft. Presets live in the account
   (/api/da/presets); "Copy from my work" takes the description and tags of a published work.
   The server cleans everything again (smweb/da_publish.py). */
(function(){
  'use strict';
  var host=document.getElementById('daPublish');if(!host)return;
  var COPY={
    en:{linkNote:'DeviantArt does not keep links on text sent through its API: the address is added right after the link text. To keep the link on the text itself, copy the description and paste it into DeviantArt’s editor (Edit → Description → Ctrl+V).',copyDesc:'Copy the description for DeviantArt',copied:'Copied: paste it into the description on DeviantArt (Ctrl+V). Links and bold stay.',copyFail:'Could not copy. Select the preview text and copy it by hand.',files:'Files',filesHint:'Each file becomes its own deviation. The showcase preview with gaps (full_with_bars) works well.',addFiles:'Add files',dropHere:'or drop them here',clear:'Clear',fileTitle:'Title of this work',remove:'Remove',
      preset:'Preset',presetNone:'No preset',presetStarter:'Starter: shop release (link + price)',presetSave:'Save as preset',presetName:'Preset name',presetSaved:'Preset saved.',presetDelete:'Delete preset',presetDeleted:'Preset deleted.',save:'Save',cancel:'Cancel',
      fromWork:'Copy from my work',fromWorkHint:'The description and tags of the chosen work are copied here.',worksEmpty:'No works found.',loading:'Loading…',applied:'Description and tags copied.',
      title:'Title',titleHint:'{name} is the file name. Up to 50 characters.',link:'Download link',linkHint:'Replaces {link} in the description.',price:'Price',priceHint:'Replaces {price} in the description.',
      description:'Description',edit:'Editor',preview:'Preview',bold:'Bold',italic:'Italic',underline:'Underline',strike:'Strikethrough',linkBtn:'Link',heading:'Heading',separator:'Separator',list:'List',emoji:'Emoji',clearFormat:'Clear formatting',linkUrl:'Link address',linkUseVar:'Use {link}',insert:'Insert',previewNote:'This is how DeviantArt will show it, with {link} and {price} filled in.',descPh:'Introduce your work: a link, a price, notes…',
      tags:'Tags',tagsPh:'Type a tag and press Enter',tagsHint:'Letters, numbers and _ only. Up to 30 tags.',suggested:'Suggestions',
      options:'Options',mature:'Mature content',matureLevel:'Level',moderate:'Moderate',strict:'Strict',classification:'Reason',nudity:'Nudity',sexual:'Sexual themes',gore:'Gore',language:'Strong language',ideology:'Ideology',noai:'NoAI (not for AI datasets)',aiGenerated:'Created using AI tools',gallery:'Gallery folders',galleryHint:'With nothing selected the work goes to your main gallery.',galleryError:'Could not load the folders.',size:'Display size',sizeOriginal:'Original',watermark:'DeviantArt watermark',watermarkHint:'Available when a display size is chosen.',download:'Allow downloading the original',comments:'Allow comments',feature:'Feature it',
      modePublish:'Publish now',modeStash:'Save to Sta.sh (draft)',modeHint:'Drafts can be published later on DeviantArt.',go:'Publish',goStash:'Save to Sta.sh',count:'Files: {n}',uploading:'Sending to DeviantArt…',done:'Done: {ok} of {total}.',open:'Open',inStash:'saved in Sta.sh',needFiles:'Add files first.',linkMissing:'The description uses {link}, but the download link is empty.'},
    ru:{linkNote:'DeviantArt не сохраняет ссылку на тексте, если описание приходит через API: адрес будет добавлен сразу после текста ссылки. Чтобы ссылка была прямо на тексте, скопируй описание и вставь его в редакторе DeviantArt (Редактировать → Описание → Ctrl+V).',copyDesc:'Скопировать описание для DeviantArt',copied:'Скопировано: вставь в описание на DeviantArt (Ctrl+V) — ссылки и жирный сохранятся.',copyFail:'Не удалось скопировать. Выдели текст в предпросмотре и скопируй вручную.',files:'Файлы',filesHint:'Каждый файл станет отдельной работой. Хорошо подходит превью витрины с полосами (full_with_bars).',addFiles:'Добавить файлы',dropHere:'или перетащи их сюда',clear:'Очистить',fileTitle:'Название этой работы',remove:'Убрать',
      preset:'Шаблон',presetNone:'Без шаблона',presetStarter:'Стартовый: магазин (ссылка + цена)',presetSave:'Сохранить как шаблон',presetName:'Название шаблона',presetSaved:'Шаблон сохранён.',presetDelete:'Удалить шаблон',presetDeleted:'Шаблон удалён.',save:'Сохранить',cancel:'Отмена',
      fromWork:'Взять с моей работы',fromWorkHint:'Описание и теги выбранной работы скопируются сюда.',worksEmpty:'Работ не найдено.',loading:'Загрузка…',applied:'Описание и теги скопированы.',
      title:'Название',titleHint:'{name} — имя файла. До 50 символов.',link:'Ссылка на скачивание',linkHint:'Подставляется вместо {link} в описании.',price:'Цена',priceHint:'Подставляется вместо {price} в описании.',
      description:'Описание',edit:'Редактор',preview:'Предпросмотр',bold:'Жирный',italic:'Курсив',underline:'Подчёркнутый',strike:'Зачёркнутый',linkBtn:'Ссылка',heading:'Заголовок',separator:'Разделитель',list:'Список',emoji:'Эмодзи',clearFormat:'Убрать оформление',linkUrl:'Адрес ссылки',linkUseVar:'Взять {link}',insert:'Вставить',previewNote:'Так описание покажет DeviantArt — {link} и {price} уже подставлены.',descPh:'Расскажи о работе: ссылка, цена, заметки…',
      tags:'Теги',tagsPh:'Введи тег и нажми Enter',tagsHint:'Только буквы, цифры и _. До 30 тегов.',suggested:'Подсказки',
      options:'Параметры',mature:'Контент для взрослых (Mature)',matureLevel:'Уровень',moderate:'Умеренный',strict:'Строгий',classification:'Причина',nudity:'Обнажённость',sexual:'Сексуальные темы',gore:'Жестокость',language:'Грубые выражения',ideology:'Идеология',noai:'NoAI (не для обучения ИИ)',aiGenerated:'Создано с помощью ИИ',gallery:'Папки галереи',galleryHint:'Если ничего не выбрать, работа попадёт в основную галерею.',galleryError:'Не удалось загрузить папки.',size:'Размер показа',sizeOriginal:'Оригинал',watermark:'Водяной знак DeviantArt',watermarkHint:'Доступен, если выбран размер показа.',download:'Разрешить скачивать оригинал',comments:'Разрешить комментарии',feature:'Показывать в Featured',
      modePublish:'Опубликовать сразу',modeStash:'Сохранить в Sta.sh (черновик)',modeHint:'Черновик можно опубликовать позже на DeviantArt.',go:'Опубликовать',goStash:'Сохранить в Sta.sh',count:'Файлов: {n}',uploading:'Отправляем на DeviantArt…',done:'Готово: {ok} из {total}.',open:'Открыть',inStash:'сохранено в Sta.sh',needFiles:'Сначала добавь файлы.',linkMissing:'В описании есть {link}, но ссылка на скачивание не указана.'},
    de:{linkNote:'DeviantArt behält Links auf Text nicht, wenn die Beschreibung über die API kommt: Die Adresse wird direkt nach dem Linktext eingefügt. Für einen Link auf dem Text selbst kopiere die Beschreibung und füge sie im DeviantArt-Editor ein (Bearbeiten → Beschreibung → Strg+V).',copyDesc:'Beschreibung für DeviantArt kopieren',copied:'Kopiert: in die Beschreibung auf DeviantArt einfügen (Strg+V). Links und Fett bleiben erhalten.',copyFail:'Kopieren fehlgeschlagen. Markiere den Vorschautext und kopiere ihn von Hand.',files:'Dateien',filesHint:'Jede Datei wird zu einer eigenen Deviation. Die Vitrinen-Vorschau mit Lücken (full_with_bars) eignet sich gut.',addFiles:'Dateien hinzufügen',dropHere:'oder hierher ziehen',clear:'Leeren',fileTitle:'Titel dieses Werks',remove:'Entfernen',
      preset:'Vorlage',presetNone:'Keine Vorlage',presetStarter:'Start: Shop-Release (Link + Preis)',presetSave:'Als Vorlage speichern',presetName:'Name der Vorlage',presetSaved:'Vorlage gespeichert.',presetDelete:'Vorlage löschen',presetDeleted:'Vorlage gelöscht.',save:'Speichern',cancel:'Abbrechen',
      fromWork:'Von meinem Werk übernehmen',fromWorkHint:'Beschreibung und Tags des gewählten Werks werden übernommen.',worksEmpty:'Keine Werke gefunden.',loading:'Wird geladen…',applied:'Beschreibung und Tags übernommen.',
      title:'Titel',titleHint:'{name} ist der Dateiname. Bis zu 50 Zeichen.',link:'Download-Link',linkHint:'Ersetzt {link} in der Beschreibung.',price:'Preis',priceHint:'Ersetzt {price} in der Beschreibung.',
      description:'Beschreibung',edit:'Editor',preview:'Vorschau',bold:'Fett',italic:'Kursiv',underline:'Unterstrichen',strike:'Durchgestrichen',linkBtn:'Link',heading:'Überschrift',separator:'Trenner',list:'Liste',emoji:'Emoji',clearFormat:'Formatierung entfernen',linkUrl:'Linkadresse',linkUseVar:'{link} verwenden',insert:'Einfügen',previewNote:'So zeigt DeviantArt die Beschreibung, mit eingesetztem {link} und {price}.',descPh:'Stell dein Werk vor: Link, Preis, Hinweise…',
      tags:'Tags',tagsPh:'Tag eingeben und Enter drücken',tagsHint:'Nur Buchstaben, Ziffern und _. Bis zu 30 Tags.',suggested:'Vorschläge',
      options:'Optionen',mature:'Inhalt für Erwachsene (Mature)',matureLevel:'Stufe',moderate:'Mäßig',strict:'Streng',classification:'Grund',nudity:'Nacktheit',sexual:'Sexuelle Themen',gore:'Gewalt',language:'Derbe Sprache',ideology:'Ideologie',noai:'NoAI (nicht für KI-Datensätze)',aiGenerated:'Mit KI-Werkzeugen erstellt',gallery:'Galerieordner',galleryHint:'Ohne Auswahl landet das Werk in deiner Hauptgalerie.',galleryError:'Ordner konnten nicht geladen werden.',size:'Anzeigegröße',sizeOriginal:'Original',watermark:'DeviantArt-Wasserzeichen',watermarkHint:'Verfügbar, wenn eine Anzeigegröße gewählt ist.',download:'Download des Originals erlauben',comments:'Kommentare erlauben',feature:'Als Featured zeigen',
      modePublish:'Sofort veröffentlichen',modeStash:'In Sta.sh speichern (Entwurf)',modeHint:'Entwürfe kannst du später auf DeviantArt veröffentlichen.',go:'Veröffentlichen',goStash:'In Sta.sh speichern',count:'Dateien: {n}',uploading:'Wird an DeviantArt gesendet…',done:'Fertig: {ok} von {total}.',open:'Öffnen',inStash:'in Sta.sh gespeichert',needFiles:'Füge zuerst Dateien hinzu.',linkMissing:'Die Beschreibung nutzt {link}, aber der Download-Link ist leer.'},
    tr:{linkNote:'DeviantArt, API ile gelen açıklamada metne bağlı bağlantıyı korumaz: adres bağlantı metninin hemen arkasına eklenir. Bağlantının metnin üzerinde kalması için açıklamayı kopyalayıp DeviantArt düzenleyicisine yapıştır (Düzenle → Açıklama → Ctrl+V).',copyDesc:'Açıklamayı DeviantArt için kopyala',copied:'Kopyalandı: DeviantArt’ta açıklamaya yapıştır (Ctrl+V). Bağlantılar ve kalın yazı korunur.',copyFail:'Kopyalanamadı. Önizlemedeki metni seçip elle kopyala.',files:'Dosyalar',filesHint:'Her dosya ayrı bir eser olur. Boşluklu vitrin önizlemesi (full_with_bars) iyi gider.',addFiles:'Dosya ekle',dropHere:'veya buraya bırak',clear:'Temizle',fileTitle:'Bu eserin başlığı',remove:'Kaldır',
      preset:'Şablon',presetNone:'Şablon yok',presetStarter:'Başlangıç: mağaza yayını (bağlantı + fiyat)',presetSave:'Şablon olarak kaydet',presetName:'Şablon adı',presetSaved:'Şablon kaydedildi.',presetDelete:'Şablonu sil',presetDeleted:'Şablon silindi.',save:'Kaydet',cancel:'İptal',
      fromWork:'Eserimden al',fromWorkHint:'Seçilen eserin açıklaması ve etiketleri buraya kopyalanır.',worksEmpty:'Eser bulunamadı.',loading:'Yükleniyor…',applied:'Açıklama ve etiketler kopyalandı.',
      title:'Başlık',titleHint:'{name} dosya adıdır. En fazla 50 karakter.',link:'İndirme bağlantısı',linkHint:'Açıklamadaki {link} yerine geçer.',price:'Fiyat',priceHint:'Açıklamadaki {price} yerine geçer.',
      description:'Açıklama',edit:'Düzenleyici',preview:'Önizleme',bold:'Kalın',italic:'İtalik',underline:'Altı çizili',strike:'Üstü çizili',linkBtn:'Bağlantı',heading:'Başlık',separator:'Ayırıcı',list:'Liste',emoji:'Emoji',clearFormat:'Biçimi temizle',linkUrl:'Bağlantı adresi',linkUseVar:'{link} kullan',insert:'Ekle',previewNote:'DeviantArt açıklamayı böyle gösterir; {link} ve {price} doldurulmuş halde.',descPh:'Eserini tanıt: bağlantı, fiyat, notlar…',
      tags:'Etiketler',tagsPh:'Etiket yaz ve Enter’a bas',tagsHint:'Yalnızca harf, rakam ve _. En fazla 30 etiket.',suggested:'Öneriler',
      options:'Seçenekler',mature:'Yetişkin içerik (Mature)',matureLevel:'Seviye',moderate:'Orta',strict:'Katı',classification:'Neden',nudity:'Çıplaklık',sexual:'Cinsel temalar',gore:'Vahşet',language:'Ağır dil',ideology:'İdeoloji',noai:'NoAI (yapay zekâ veri setleri için değil)',aiGenerated:'Yapay zekâ araçlarıyla yapıldı',gallery:'Galeri klasörleri',galleryHint:'Hiçbiri seçilmezse eser ana galerine gider.',galleryError:'Klasörler yüklenemedi.',size:'Gösterim boyutu',sizeOriginal:'Orijinal',watermark:'DeviantArt filigranı',watermarkHint:'Bir gösterim boyutu seçildiğinde kullanılabilir.',download:'Orijinalin indirilmesine izin ver',comments:'Yorumlara izin ver',feature:'Öne çıkar (Featured)',
      modePublish:'Hemen yayınla',modeStash:'Sta.sh’e kaydet (taslak)',modeHint:'Taslakları daha sonra DeviantArt’ta yayınlayabilirsin.',go:'Yayınla',goStash:'Sta.sh’e kaydet',count:'Dosya: {n}',uploading:'DeviantArt’a gönderiliyor…',done:'Tamam: {ok} / {total}.',open:'Aç',inStash:'Sta.sh’e kaydedildi',needFiles:'Önce dosya ekle.',linkMissing:'Açıklamada {link} var ama indirme bağlantısı boş.'},
    fr:{linkNote:'DeviantArt ne garde pas les liens sur le texte quand la description arrive par l’API : l’adresse est ajoutée juste après le texte du lien. Pour garder le lien sur le texte, copiez la description et collez-la dans l’éditeur de DeviantArt (Modifier → Description → Ctrl+V).',copyDesc:'Copier la description pour DeviantArt',copied:'Copié : collez-la dans la description sur DeviantArt (Ctrl+V). Les liens et le gras sont conservés.',copyFail:'Copie impossible. Sélectionnez le texte de l’aperçu et copiez-le à la main.',files:'Fichiers',filesHint:'Chaque fichier devient une deviation à part. L’aperçu de vitrine avec espaces (full_with_bars) convient bien.',addFiles:'Ajouter des fichiers',dropHere:'ou déposez-les ici',clear:'Vider',fileTitle:'Titre de cette œuvre',remove:'Retirer',
      preset:'Modèle',presetNone:'Aucun modèle',presetStarter:'Départ : sortie boutique (lien + prix)',presetSave:'Enregistrer comme modèle',presetName:'Nom du modèle',presetSaved:'Modèle enregistré.',presetDelete:'Supprimer le modèle',presetDeleted:'Modèle supprimé.',save:'Enregistrer',cancel:'Annuler',
      fromWork:'Reprendre une de mes œuvres',fromWorkHint:'La description et les tags de l’œuvre choisie sont copiés ici.',worksEmpty:'Aucune œuvre trouvée.',loading:'Chargement…',applied:'Description et tags copiés.',
      title:'Titre',titleHint:'{name} est le nom du fichier. 50 caractères maximum.',link:'Lien de téléchargement',linkHint:'Remplace {link} dans la description.',price:'Prix',priceHint:'Remplace {price} dans la description.',
      description:'Description',edit:'Éditeur',preview:'Aperçu',bold:'Gras',italic:'Italique',underline:'Souligné',strike:'Barré',linkBtn:'Lien',heading:'Titre',separator:'Séparateur',list:'Liste',emoji:'Emoji',clearFormat:'Effacer la mise en forme',linkUrl:'Adresse du lien',linkUseVar:'Utiliser {link}',insert:'Insérer',previewNote:'Voici comment DeviantArt l’affichera, avec {link} et {price} remplis.',descPh:'Présentez votre œuvre : lien, prix, notes…',
      tags:'Tags',tagsPh:'Saisissez un tag puis Entrée',tagsHint:'Lettres, chiffres et _ uniquement. 30 tags maximum.',suggested:'Suggestions',
      options:'Options',mature:'Contenu pour adultes (Mature)',matureLevel:'Niveau',moderate:'Modéré',strict:'Strict',classification:'Raison',nudity:'Nudité',sexual:'Thèmes sexuels',gore:'Gore',language:'Langage grossier',ideology:'Idéologie',noai:'NoAI (pas pour les jeux de données IA)',aiGenerated:'Créé avec des outils d’IA',gallery:'Dossiers de galerie',galleryHint:'Sans sélection, l’œuvre va dans votre galerie principale.',galleryError:'Impossible de charger les dossiers.',size:'Taille d’affichage',sizeOriginal:'Originale',watermark:'Filigrane DeviantArt',watermarkHint:'Disponible si une taille d’affichage est choisie.',download:'Autoriser le téléchargement de l’original',comments:'Autoriser les commentaires',feature:'Mettre en avant (Featured)',
      modePublish:'Publier maintenant',modeStash:'Enregistrer dans Sta.sh (brouillon)',modeHint:'Les brouillons peuvent être publiés plus tard sur DeviantArt.',go:'Publier',goStash:'Enregistrer dans Sta.sh',count:'Fichiers : {n}',uploading:'Envoi vers DeviantArt…',done:'Terminé : {ok} sur {total}.',open:'Ouvrir',inStash:'enregistré dans Sta.sh',needFiles:'Ajoutez d’abord des fichiers.',linkMissing:'La description utilise {link}, mais le lien de téléchargement est vide.'},
    uk:{linkNote:'DeviantArt не зберігає посилання на тексті, якщо опис приходить через API: адресу буде додано одразу після тексту посилання. Щоб посилання було прямо на тексті, скопіюй опис і встав його в редакторі DeviantArt (Редагувати → Опис → Ctrl+V).',copyDesc:'Скопіювати опис для DeviantArt',copied:'Скопійовано: встав в опис на DeviantArt (Ctrl+V) — посилання й жирний збережуться.',copyFail:'Не вдалося скопіювати. Виділи текст у попередньому перегляді й скопіюй вручну.',files:'Файли',filesHint:'Кожен файл стане окремою роботою. Добре підходить прев’ю вітрини зі смугами (full_with_bars).',addFiles:'Додати файли',dropHere:'або перетягни їх сюди',clear:'Очистити',fileTitle:'Назва цієї роботи',remove:'Прибрати',
      preset:'Шаблон',presetNone:'Без шаблону',presetStarter:'Стартовий: магазин (посилання + ціна)',presetSave:'Зберегти як шаблон',presetName:'Назва шаблону',presetSaved:'Шаблон збережено.',presetDelete:'Видалити шаблон',presetDeleted:'Шаблон видалено.',save:'Зберегти',cancel:'Скасувати',
      fromWork:'Взяти з моєї роботи',fromWorkHint:'Опис і теги вибраної роботи скопіюються сюди.',worksEmpty:'Робіт не знайдено.',loading:'Завантаження…',applied:'Опис і теги скопійовано.',
      title:'Назва',titleHint:'{name} — ім’я файлу. До 50 символів.',link:'Посилання на завантаження',linkHint:'Підставляється замість {link} в описі.',price:'Ціна',priceHint:'Підставляється замість {price} в описі.',
      description:'Опис',edit:'Редактор',preview:'Попередній перегляд',bold:'Жирний',italic:'Курсив',underline:'Підкреслений',strike:'Закреслений',linkBtn:'Посилання',heading:'Заголовок',separator:'Роздільник',list:'Список',emoji:'Емодзі',clearFormat:'Прибрати оформлення',linkUrl:'Адреса посилання',linkUseVar:'Взяти {link}',insert:'Вставити',previewNote:'Так опис покаже DeviantArt — {link} і {price} уже підставлено.',descPh:'Розкажи про роботу: посилання, ціна, нотатки…',
      tags:'Теги',tagsPh:'Введи тег і натисни Enter',tagsHint:'Лише літери, цифри та _. До 30 тегів.',suggested:'Підказки',
      options:'Параметри',mature:'Контент для дорослих (Mature)',matureLevel:'Рівень',moderate:'Помірний',strict:'Суворий',classification:'Причина',nudity:'Оголеність',sexual:'Сексуальні теми',gore:'Жорстокість',language:'Грубі вирази',ideology:'Ідеологія',noai:'NoAI (не для навчання ШІ)',aiGenerated:'Створено за допомогою ШІ',gallery:'Теки галереї',galleryHint:'Якщо нічого не вибрати, робота потрапить в основну галерею.',galleryError:'Не вдалося завантажити теки.',size:'Розмір показу',sizeOriginal:'Оригінал',watermark:'Водяний знак DeviantArt',watermarkHint:'Доступний, якщо вибрано розмір показу.',download:'Дозволити завантажувати оригінал',comments:'Дозволити коментарі',feature:'Показувати у Featured',
      modePublish:'Опублікувати одразу',modeStash:'Зберегти в Sta.sh (чернетка)',modeHint:'Чернетку можна опублікувати пізніше на DeviantArt.',go:'Опублікувати',goStash:'Зберегти в Sta.sh',count:'Файлів: {n}',uploading:'Надсилаємо на DeviantArt…',done:'Готово: {ok} з {total}.',open:'Відкрити',inStash:'збережено в Sta.sh',needFiles:'Спочатку додай файли.',linkMissing:'В описі є {link}, але посилання на завантаження не вказано.'},
    es:{linkNote:'DeviantArt no conserva los enlaces sobre el texto cuando la descripción llega por la API: la dirección se añade justo después del texto del enlace. Para que el enlace quede en el texto, copia la descripción y pégala en el editor de DeviantArt (Editar → Descripción → Ctrl+V).',copyDesc:'Copiar la descripción para DeviantArt',copied:'Copiado: pégala en la descripción en DeviantArt (Ctrl+V). Los enlaces y la negrita se mantienen.',copyFail:'No se pudo copiar. Selecciona el texto de la vista previa y cópialo a mano.',files:'Archivos',filesHint:'Cada archivo se convierte en una obra aparte. La vista previa con huecos (full_with_bars) funciona bien.',addFiles:'Añadir archivos',dropHere:'o suéltalos aquí',clear:'Vaciar',fileTitle:'Título de esta obra',remove:'Quitar',
      preset:'Plantilla',presetNone:'Sin plantilla',presetStarter:'Inicial: venta en tienda (enlace + precio)',presetSave:'Guardar como plantilla',presetName:'Nombre de la plantilla',presetSaved:'Plantilla guardada.',presetDelete:'Borrar plantilla',presetDeleted:'Plantilla borrada.',save:'Guardar',cancel:'Cancelar',
      fromWork:'Tomar de una obra mía',fromWorkHint:'La descripción y las etiquetas de la obra elegida se copian aquí.',worksEmpty:'No se encontraron obras.',loading:'Cargando…',applied:'Descripción y etiquetas copiadas.',
      title:'Título',titleHint:'{name} es el nombre del archivo. Hasta 50 caracteres.',link:'Enlace de descarga',linkHint:'Sustituye {link} en la descripción.',price:'Precio',priceHint:'Sustituye {price} en la descripción.',
      description:'Descripción',edit:'Editor',preview:'Vista previa',bold:'Negrita',italic:'Cursiva',underline:'Subrayado',strike:'Tachado',linkBtn:'Enlace',heading:'Encabezado',separator:'Separador',list:'Lista',emoji:'Emoji',clearFormat:'Quitar formato',linkUrl:'Dirección del enlace',linkUseVar:'Usar {link}',insert:'Insertar',previewNote:'Así lo mostrará DeviantArt, con {link} y {price} ya rellenados.',descPh:'Presenta tu obra: enlace, precio, notas…',
      tags:'Etiquetas',tagsPh:'Escribe una etiqueta y pulsa Enter',tagsHint:'Solo letras, números y _. Hasta 30 etiquetas.',suggested:'Sugerencias',
      options:'Opciones',mature:'Contenido para adultos (Mature)',matureLevel:'Nivel',moderate:'Moderado',strict:'Estricto',classification:'Motivo',nudity:'Desnudez',sexual:'Temas sexuales',gore:'Violencia explícita',language:'Lenguaje fuerte',ideology:'Ideología',noai:'NoAI (no para datos de IA)',aiGenerated:'Creado con herramientas de IA',gallery:'Carpetas de la galería',galleryHint:'Sin selección, la obra va a tu galería principal.',galleryError:'No se pudieron cargar las carpetas.',size:'Tamaño de visualización',sizeOriginal:'Original',watermark:'Marca de agua de DeviantArt',watermarkHint:'Disponible si eliges un tamaño de visualización.',download:'Permitir descargar el original',comments:'Permitir comentarios',feature:'Destacar (Featured)',
      modePublish:'Publicar ahora',modeStash:'Guardar en Sta.sh (borrador)',modeHint:'Los borradores se pueden publicar más tarde en DeviantArt.',go:'Publicar',goStash:'Guardar en Sta.sh',count:'Archivos: {n}',uploading:'Enviando a DeviantArt…',done:'Listo: {ok} de {total}.',open:'Abrir',inStash:'guardado en Sta.sh',needFiles:'Primero añade archivos.',linkMissing:'La descripción usa {link}, pero el enlace de descarga está vacío.'},
    pt:{linkNote:'O DeviantArt não mantém links no texto quando a descrição chega pela API: o endereço é adicionado logo após o texto do link. Para manter o link no texto, copie a descrição e cole no editor do DeviantArt (Editar → Descrição → Ctrl+V).',copyDesc:'Copiar a descrição para o DeviantArt',copied:'Copiado: cole na descrição do DeviantArt (Ctrl+V). Links e negrito são mantidos.',copyFail:'Não foi possível copiar. Selecione o texto da prévia e copie à mão.',files:'Arquivos',filesHint:'Cada arquivo vira uma obra separada. A prévia da vitrine com espaços (full_with_bars) funciona bem.',addFiles:'Adicionar arquivos',dropHere:'ou solte aqui',clear:'Limpar',fileTitle:'Título desta obra',remove:'Remover',
      preset:'Modelo',presetNone:'Sem modelo',presetStarter:'Inicial: venda na loja (link + preço)',presetSave:'Salvar como modelo',presetName:'Nome do modelo',presetSaved:'Modelo salvo.',presetDelete:'Excluir modelo',presetDeleted:'Modelo excluído.',save:'Salvar',cancel:'Cancelar',
      fromWork:'Copiar de uma obra minha',fromWorkHint:'A descrição e as tags da obra escolhida são copiadas para cá.',worksEmpty:'Nenhuma obra encontrada.',loading:'Carregando…',applied:'Descrição e tags copiadas.',
      title:'Título',titleHint:'{name} é o nome do arquivo. Até 50 caracteres.',link:'Link de download',linkHint:'Substitui {link} na descrição.',price:'Preço',priceHint:'Substitui {price} na descrição.',
      description:'Descrição',edit:'Editor',preview:'Prévia',bold:'Negrito',italic:'Itálico',underline:'Sublinhado',strike:'Tachado',linkBtn:'Link',heading:'Título',separator:'Separador',list:'Lista',emoji:'Emoji',clearFormat:'Limpar formatação',linkUrl:'Endereço do link',linkUseVar:'Usar {link}',insert:'Inserir',previewNote:'É assim que o DeviantArt vai mostrar, com {link} e {price} preenchidos.',descPh:'Apresente sua obra: link, preço, notas…',
      tags:'Tags',tagsPh:'Digite uma tag e pressione Enter',tagsHint:'Só letras, números e _. Até 30 tags.',suggested:'Sugestões',
      options:'Opções',mature:'Conteúdo adulto (Mature)',matureLevel:'Nível',moderate:'Moderado',strict:'Rígido',classification:'Motivo',nudity:'Nudez',sexual:'Temas sexuais',gore:'Violência gráfica',language:'Linguagem forte',ideology:'Ideologia',noai:'NoAI (não para dados de IA)',aiGenerated:'Criado com ferramentas de IA',gallery:'Pastas da galeria',galleryHint:'Sem seleção, a obra vai para a galeria principal.',galleryError:'Não foi possível carregar as pastas.',size:'Tamanho de exibição',sizeOriginal:'Original',watermark:'Marca d’água do DeviantArt',watermarkHint:'Disponível quando um tamanho de exibição é escolhido.',download:'Permitir baixar o original',comments:'Permitir comentários',feature:'Destacar (Featured)',
      modePublish:'Publicar agora',modeStash:'Salvar no Sta.sh (rascunho)',modeHint:'Rascunhos podem ser publicados depois no DeviantArt.',go:'Publicar',goStash:'Salvar no Sta.sh',count:'Arquivos: {n}',uploading:'Enviando para o DeviantArt…',done:'Pronto: {ok} de {total}.',open:'Abrir',inStash:'salvo no Sta.sh',needFiles:'Adicione arquivos primeiro.',linkMissing:'A descrição usa {link}, mas o link de download está vazio.'}
  };
  function lang(){var l=window.SMLang&&SMLang.get?SMLang.get():'en';return COPY[l]?l:'en'}
  function t(key,vars){var s=COPY[lang()][key]||COPY.en[key]||key;if(vars)Object.keys(vars).forEach(function(k){s=s.split('{'+k+'}').join(vars[k])});return s}
  function el(tag,cls,text){var n=document.createElement(tag);if(cls)n.className=cls;if(text!=null)n.textContent=text;return n}
  function btn(cls,text,fn){var b=el('button',cls,text);b.type='button';if(fn)b.addEventListener('click',fn);return b}
  function field(label,control,hint){var w=el('label','dp-field');w.append(el('span','dp-field__label',label),control);if(hint)w.append(el('small','dp-field__hint',hint));return w}
  function check(label,checked,onChange){var w=el('label','dp-check'),i=el('input');i.type='checkbox';i.checked=!!checked;i.addEventListener('change',function(){onChange(i.checked)});w.append(i,el('span',null,label));return w}

  var SIZES=[0,400,600,800,900,1024,1280,1600,1920];
  var SUGGESTED=['steam','workshop','showcase','steamworkshop','steamprofile','steamartwork','anime','animegirl','digitalart','wallpaper','fanart','pixelart','artwork','design','gif'];
  var EMOJI=['✦','・','💠','✨','✅','📖','☕','♡','💖','🔗','⬇️','🎁','⭐','🔥','🎮','💜','🌸','⚡','➜','★','🛒','💬'];
  var SEPARATOR='᠌────────── ✦ ──────────';
  // A neutral starter in English (DeviantArt's audience); {link} and {price} come from the fields above.
  var STARTER='<p>✦・<a href="{link}"><b>LINK DOWNLOAD</b></a>・✦</p><p>💠 <b>Price:</b> Only <b>{price}</b></p><p>'+SEPARATOR+'</p><p>✨ <b>Notes:</b><br>✅ Preview may appear in lower quality.<br>✅ Purchased files do not include the watermark.<br>✅ Found a mistake? Feel free to DM me.</p><p>'+SEPARATOR+'</p><h4>THANK YOU ♡</h4>';
  var DEFAULT={titleTpl:'{name}',link:'',price:'',description:'',tags:[],mode:'publish',is_mature:false,mature_level:'moderate',mature_classification:[],noai:true,is_ai_generated:false,galleryids:[],display_resolution:0,add_watermark:false,allow_free_download:false,allow_comments:true,feature:true};
  var S=JSON.parse(JSON.stringify(DEFAULT));S.files=[];S.presets=[];S.presetId='';S.folders=null;S.view='edit';S.busy=false;S.works=null;S.panel='';

  // ---------------------------------------------------------------- HTML cleaning (mirror of the server)
  var ALLOWED={B:1,STRONG:1,I:1,EM:1,U:1,S:1,STRIKE:1,A:1,BR:1,P:1,H1:1,H2:1,H3:1,H4:1,UL:1,OL:1,LI:1,SUB:1,SUP:1,SMALL:1,CODE:1,BLOCKQUOTE:1,HR:1};
  function cleanHtml(html,keepVars){
    var doc=new DOMParser().parseFromString('<div>'+String(html||'')+'</div>','text/html'),rootNode=doc.body.firstChild;
    (function walk(node){Array.from(node.childNodes).forEach(function(child){
      if(child.nodeType===3)return;if(child.nodeType!==1){child.remove();return}
      walk(child);var tag=child.tagName==='DIV'?'P':child.tagName;
      if(/^(SCRIPT|STYLE|IFRAME|OBJECT|TEMPLATE)$/.test(child.tagName)){child.remove();return}
      if(!ALLOWED[tag]){child.replaceWith.apply(child,Array.from(child.childNodes));return}
      var href=tag==='A'?unwrap(child.getAttribute('href')||''):'';
      var clean=doc.createElement(tag);while(child.firstChild)clean.append(child.firstChild);
      if(tag==='A'){if(/^https?:\/\//i.test(href)||(keepVars&&/^\{[a-z_]+\}$/.test(href)))clean.setAttribute('href',href);else{child.replaceWith.apply(child,Array.from(clean.childNodes));return}}
      child.replaceWith(clean);
    })})(rootNode);
    return rootNode.innerHTML;
  }
  function unwrap(href){var m=/^https?:\/\/(?:www\.)?deviantart\.com\/users\/outgoing\?(.+)$/i.exec(href);return m?decodeURIComponent(m[1]):href}
  function fill(html){
    var link=S.link.trim(),safeLink=/^https?:\/\//i.test(link)?link:'';
    return String(html||'').split('{link}').join(safeLink.replace(/"/g,'%22')).split('{price}').join(escapeText(S.price));
  }
  function escapeText(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
  function titleFor(item){var stem=item.file.name.replace(/\.[^.]+$/,'');return item.edited?item.title:(S.titleTpl||'{name}').split('{name}').join(stem).slice(0,50)}

  // ---------------------------------------------------------------- server
  function api(path,options){return fetch(path,Object.assign({credentials:'same-origin',cache:'no-store'},options||{})).then(function(r){return r.json().catch(function(){return {}}).then(function(j){if(!r.ok||j.ok===false)throw Error(j.msg||('HTTP '+r.status));return j})})}
  function loadPresets(){return api('/api/da/presets').then(function(j){S.presets=j.presets||[];render()}).catch(function(){})}
  function loadFolders(){if(S.folders)return;S.folders='loading';api('/api/da/folders').then(function(j){S.folders=j.folders||[];render()}).catch(function(){S.folders='error';render()})}
  function snapshot(){var out={};Object.keys(DEFAULT).forEach(function(k){out[k]=S[k]});out.title=S.titleTpl;return out}
  function applyPreset(p){Object.keys(DEFAULT).forEach(function(k){if(p[k]!==undefined)S[k]=Array.isArray(p[k])?p[k].slice():p[k]});S.titleTpl=p.title||'{name}';S.files.forEach(function(f){f.edited=false})}

  // ---------------------------------------------------------------- UI
  var status=el('p','dp-status');status.setAttribute('aria-live','polite');
  function say(text,kind){status.textContent=text||'';status.dataset.kind=kind||''}
  var editor=null;
  function render(){
    var keepScroll=window.scrollY;host.replaceChildren();host.className='dp';
    host.append(filesSection(),presetSection(),postSection(),optionsSection(),actionSection());
    window.scrollTo(0,keepScroll);
  }
  function section(title,extra){var s=el('section','dp-section'),h=el('div','dp-section__head');h.append(el('h3',null,title));if(extra)h.append(extra);s.append(h);return s}

  function filesSection(){
    var s=section(t('files'),el('small','dp-muted',t('count',{n:S.files.length})));
    var drop=el('div','dp-drop'),input=el('input');input.type='file';input.multiple=true;input.hidden=true;input.dataset.smEnhanced='1';input.accept='image/*,video/mp4,video/webm,.gif';
    var add=btn('btn',t('addFiles'),function(){input.click()});
    drop.append(add,el('span',null,t('dropHere')),input);
    if(S.files.length)drop.append(btn('btn ghost dp-clear',t('clear'),function(){S.files.forEach(function(f){URL.revokeObjectURL(f.url)});S.files=[];render()}));
    input.addEventListener('change',function(){addFiles(input.files);input.value=''});
    drop.addEventListener('dragover',function(e){e.preventDefault();drop.classList.add('is-over')});
    drop.addEventListener('dragleave',function(){drop.classList.remove('is-over')});
    drop.addEventListener('drop',function(e){e.preventDefault();drop.classList.remove('is-over');addFiles(e.dataTransfer.files)});
    s.append(el('p','dp-muted',t('filesHint')),drop);
    if(S.files.length){
      var list=el('div','dp-files');
      S.files.forEach(function(item,index){
        var row=el('div','dp-file'),thumb=el(/^video\//.test(item.file.type)?'video':'img','dp-file__thumb');thumb.src=item.url;if(thumb.tagName==='VIDEO'){thumb.muted=true}else thumb.alt='';
        var title=el('input','dp-input');title.value=titleFor(item);title.maxLength=50;title.setAttribute('aria-label',t('fileTitle'));
        title.addEventListener('input',function(){item.title=title.value;item.edited=true});
        var meta=el('div','dp-file__meta');meta.append(el('small',null,item.file.name),title);
        row.append(thumb,meta,btn('dp-icon',null,function(){URL.revokeObjectURL(item.url);S.files.splice(index,1);render()}));
        row.lastChild.textContent='×';row.lastChild.title=t('remove');row.lastChild.setAttribute('aria-label',t('remove'));
        list.append(row);
      });
      s.append(list);
    }
    return s;
  }
  function addFiles(list){Array.from(list||[]).slice(0,20-S.files.length).forEach(function(file){S.files.push({file:file,url:URL.createObjectURL(file),title:'',edited:false})});say('');render()}

  function presetSection(){
    var s=section(t('preset')),row=el('div','dp-row');
    var select=el('select','dp-input dp-preset');
    [['',t('presetNone')],['starter',t('presetStarter')]].concat(S.presets.map(function(p){return [p.id,p.name]})).forEach(function(o){var op=el('option',null,o[1]);op.value=o[0];op.selected=o[0]===S.presetId;select.append(op)});
    select.addEventListener('change',function(){
      S.presetId=select.value;
      if(select.value==='starter'){S.description=STARTER;S.mode='publish'}
      else{var p=S.presets.filter(function(x){return x.id===select.value})[0];if(p)applyPreset(p.preset||{})}
      render();
    });
    row.append(select,btn('btn ghost',t('presetSave'),function(){S.panel=S.panel==='save'?'':'save';render()}));
    var current=S.presets.filter(function(x){return x.id===S.presetId})[0];
    if(current)row.append(btn('btn ghost dp-danger',t('presetDelete'),function(){api('/api/da/presets/'+encodeURIComponent(current.id),{method:'DELETE'}).then(function(){S.presetId='';say(t('presetDeleted'),'ok');loadPresets()}).catch(function(e){say(e.message,'bad')})}));
    row.append(btn('btn ghost',t('fromWork'),function(){S.panel=S.panel==='works'?'':'works';if(S.panel==='works'&&!S.works)loadWorks();render()}));
    s.append(row);
    if(S.panel==='save'){
      var box=el('div','dp-inline'),name=el('input','dp-input');name.placeholder=t('presetName');name.maxLength=60;name.value=current?current.name:'';
      box.append(name,btn('btn',t('save'),function(){
        if(!name.value.trim()){name.focus();return}
        api('/api/da/presets',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:current?current.id:'',name:name.value.trim(),preset:snapshot()})})
          .then(function(j){S.presetId=j.preset.id;S.panel='';say(t('presetSaved'),'ok');loadPresets()}).catch(function(e){say(e.message,'bad')});
      }),btn('btn ghost',t('cancel'),function(){S.panel='';render()}));
      s.append(box);setTimeout(function(){name.focus()},0);
    }
    if(S.panel==='works'){
      var works=el('div','dp-works');works.append(el('p','dp-muted',t('fromWorkHint')));
      if(!S.works||S.works==='loading')works.append(el('p','dp-muted',t('loading')));
      else if(S.works==='error'||!S.works.length)works.append(el('p','dp-muted',t('worksEmpty')));
      else{var grid=el('div','dp-works__grid');S.works.forEach(function(w){var b=btn('dp-work',null,function(){useWork(w)});var img=el('img');img.src=w.preview;img.alt='';img.loading='lazy';b.append(img,el('span',null,w.title));grid.append(b)});works.append(grid)}
      s.append(works);
    }
    return s;
  }
  function loadWorks(){S.works='loading';api('/api/da/works?limit=24').then(function(j){S.works=j.works||[];render()}).catch(function(){S.works='error';render()})}
  // A copied description becomes a template: the download link turns into {link} and the
  // first price into {price}, and both go into their fields, so the next work only needs
  // a new link (and price) instead of editing the text.
  var PRICE=/(?:[$€£₽]\s?\d+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?\s?(?:[$€£₽]|USD|EUR|руб\.?|rub))/i;
  function templateFrom(html){
    var doc=new DOMParser().parseFromString('<div>'+cleanHtml(html,true)+'</div>','text/html'),box=doc.body.firstChild,out={html:'',link:'',price:''};
    var anchors=Array.from(box.querySelectorAll('a[href]'));
    var target=anchors.filter(function(a){return /download|скач|завантаж|herunterladen|indir|télécharg|descarg|baixar|buy|купить/i.test(a.textContent)})[0]||anchors[0];
    if(target){out.link=target.getAttribute('href');target.setAttribute('href','{link}')}
    var walker=doc.createTreeWalker(box,NodeFilter.SHOW_TEXT),node;
    while((node=walker.nextNode())){var m=PRICE.exec(node.nodeValue);if(m){out.price=m[0];node.nodeValue=node.nodeValue.replace(m[0],'{price}');break}}
    out.html=box.innerHTML;return out;
  }
  function useWork(w){
    say(t('loading'));
    api('/api/da/work-meta/'+encodeURIComponent(w.id)).then(function(j){
      // Real links of the work become {link} only when the user asks for it; keep them as they are.
      var parts=templateFrom(j.description||'');S.description=parts.html;if(parts.link)S.link=parts.link;if(parts.price)S.price=parts.price;
      S.tags=(j.tags||[]).slice(0,30);S.is_mature=!!j.is_mature;S.panel='';say(t('applied'),'ok');render();
    }).catch(function(e){say(e.message,'bad')});
  }

  function postSection(){
    var s=section(t('description'));
    var title=el('input','dp-input');title.value=S.titleTpl;title.maxLength=60;title.addEventListener('input',function(){S.titleTpl=title.value;host.querySelectorAll('.dp-file .dp-input').forEach(function(input,i){if(S.files[i]&&!S.files[i].edited)input.value=titleFor(S.files[i])})});
    var link=el('input','dp-input');link.type='url';link.placeholder='https://…';link.value=S.link;link.addEventListener('input',function(){S.link=link.value;paintPreview()});
    var price=el('input','dp-input');price.placeholder='$2';price.value=S.price;price.maxLength=40;price.addEventListener('input',function(){S.price=price.value;paintPreview()});
    var grid=el('div','dp-grid3');grid.append(field(t('title'),title,t('titleHint')),field(t('link'),link,t('linkHint')),field(t('price'),price,t('priceHint')));
    s.append(grid);
    // editor / preview switch
    var tabs=el('div','dp-tabs');[['edit',t('edit')],['preview',t('preview')]].forEach(function(o){var b=btn('dp-tab'+(S.view===o[0]?' is-on':''),o[1],function(){if(editor)S.description=cleanHtml(editor.innerHTML,true);S.view=o[0];render()});b.setAttribute('aria-pressed',String(S.view===o[0]));tabs.append(b)});
    s.append(tabs);
    if(S.view==='preview'){
      var pv=el('div','dp-preview');pv.innerHTML=cleanHtml(fill(S.description))||'<p class="dp-muted">—</p>';
      s.append(el('p','dp-muted',t('previewNote')),pv);editor=null;
    }else{
      var bar=el('div','dp-toolbar');bar.setAttribute('role','toolbar');
      function tool(label,title,run,cls){var b=btn('dp-tool'+(cls?' '+cls:''),label,function(){editor.focus();restore();run();sync()});b.title=title;b.setAttribute('aria-label',title);b.addEventListener('mousedown',function(e){e.preventDefault()});bar.append(b);return b}
      tool('B',t('bold'),function(){document.execCommand('bold')},'is-b');
      tool('I',t('italic'),function(){document.execCommand('italic')},'is-i');
      tool('U',t('underline'),function(){document.execCommand('underline')},'is-u');
      tool('S',t('strike'),function(){document.execCommand('strikeThrough')},'is-s');
      tool('H',t('heading'),function(){document.execCommand('formatBlock',false,'h4')});
      tool('🔗',t('linkBtn'),function(){S.panel='link';render()});
      tool('•',t('list'),function(){document.execCommand('insertUnorderedList')});
      tool('—',t('separator'),function(){document.execCommand('insertHTML',false,'<p>'+SEPARATOR+'</p>')});
      tool('{link}','{link}',function(){document.execCommand('insertText',false,'{link}')},'is-var');
      tool('{price}','{price}',function(){document.execCommand('insertText',false,'{price}')},'is-var');
      tool('Tx',t('clearFormat'),function(){document.execCommand('removeFormat');document.execCommand('formatBlock',false,'p')});
      var emoji=el('div','dp-emoji');EMOJI.forEach(function(e){var b=btn('dp-emoji__b',e,function(){editor.focus();restore();document.execCommand('insertText',false,e);sync()});b.addEventListener('mousedown',function(ev){ev.preventDefault()});emoji.append(b)});
      s.append(bar);
      if(S.panel==='link'){
        var box=el('div','dp-inline'),url=el('input','dp-input');url.placeholder='https://…';url.value='{link}';
        box.append(url,btn('btn ghost',t('linkUseVar'),function(){url.value='{link}'}),btn('btn',t('insert'),function(){
          var href=url.value.trim();S.panel='';editor.focus();restore();
          if(/^https?:\/\//i.test(href)||href==='{link}'){
            if(window.getSelection().isCollapsed)document.execCommand('insertHTML',false,'<a href="'+href.replace(/"/g,'%22')+'">'+escapeText(href==='{link}'?'LINK DOWNLOAD':href)+'</a>');
            else document.execCommand('createLink',false,href);
          }
          sync();render();
        }),btn('btn ghost',t('cancel'),function(){S.panel='';render()}));
        s.append(box);
      }
      editor=el('div','dp-editor');editor.contentEditable='true';editor.setAttribute('role','textbox');editor.setAttribute('aria-multiline','true');editor.setAttribute('aria-label',t('description'));editor.dataset.placeholder=t('descPh');
      editor.innerHTML=S.description;
      editor.addEventListener('input',sync);editor.addEventListener('keyup',save);editor.addEventListener('mouseup',save);editor.addEventListener('blur',save);
      editor.addEventListener('paste',function(e){var data=e.clipboardData;if(!data)return;e.preventDefault();var html=data.getData('text/html');
        if(html)document.execCommand('insertHTML',false,cleanHtml(html,true));else document.execCommand('insertText',false,data.getData('text/plain'));sync()});
      s.append(editor,emoji);
    }
    var copyRow=el('div','dp-copy');copyRow.append(btn('btn ghost dp-copy__btn',t('copyDesc'),copyDescription),el('small','dp-field__hint',t('linkNote')));
    s.append(copyRow);
    // tags
    var tagsBox=el('div','dp-tags'),chips=el('div','dp-chips'),input=el('input','dp-tags__input');input.placeholder=t('tagsPh');
    function addTag(raw){String(raw||'').split(/[,\s#]+/).forEach(function(part){var tag=part.replace(/[^\p{L}\p{N}_]/gu,'').toLowerCase().slice(0,50);if(tag&&S.tags.indexOf(tag)<0&&S.tags.length<30)S.tags.push(tag)});paintTags()}
    function paintTags(){chips.replaceChildren();S.tags.forEach(function(tag,i){var c=el('span','dp-chip',tag),x=btn('dp-chip__x','×',function(){S.tags.splice(i,1);paintTags()});x.setAttribute('aria-label',t('remove')+' '+tag);c.append(x);chips.append(c)});chips.append(input);counter.textContent=S.tags.length+'/30';paintSuggest()}
    input.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===','){e.preventDefault();addTag(input.value);input.value='';input.focus()}else if(e.key==='Backspace'&&!input.value&&S.tags.length){S.tags.pop();paintTags();input.focus()}});
    input.addEventListener('blur',function(){if(input.value){addTag(input.value);input.value=''}});
    input.addEventListener('paste',function(e){e.preventDefault();addTag((e.clipboardData||window.clipboardData).getData('text'));input.focus()});
    var counter=el('small','dp-muted'),suggest=el('div','dp-suggest');
    function paintSuggest(){suggest.replaceChildren(el('span','dp-muted',t('suggested')+':'));SUGGESTED.filter(function(s){return S.tags.indexOf(s)<0}).forEach(function(tag){suggest.append(btn('dp-suggest__b','+ '+tag,function(){addTag(tag)}))})}
    tagsBox.append(chips);
    var head=el('div','dp-subhead');head.append(el('h4',null,t('tags')),counter);
    s.append(head,tagsBox,el('small','dp-field__hint',t('tagsHint')),suggest);
    paintTags();
    return s;
  }
  // Rich copy for DeviantArt's own editor: there the link stays on the text and bold stays bold.
  function copyDescription(){
    if(editor)S.description=cleanHtml(editor.innerHTML,true);
    var html=cleanHtml(fill(S.description)),box=document.createElement('div');box.innerHTML=html;
    var text=box.innerText||box.textContent||'';
    var done=function(){say(t('copied'),'ok')},fail=function(){say(t('copyFail'),'bad')};
    try{
      if(navigator.clipboard&&window.ClipboardItem){
        navigator.clipboard.write([new ClipboardItem({'text/html':new Blob([html],{type:'text/html'}),'text/plain':new Blob([text],{type:'text/plain'})})]).then(done,fail);
        return;
      }
    }catch(_){}
    // Fallback: copy a selected rendered copy of the description.
    var tmp=document.createElement('div');tmp.innerHTML=html;tmp.style.cssText='position:fixed;left:-9999px;top:0';document.body.append(tmp);
    var range=document.createRange();range.selectNodeContents(tmp);var sel=window.getSelection();sel.removeAllRanges();sel.addRange(range);
    var ok=false;try{ok=document.execCommand('copy')}catch(_){}
    sel.removeAllRanges();tmp.remove();ok?done():fail();
  }
  var range=null;
  function save(){var sel=window.getSelection();if(sel.rangeCount&&editor&&editor.contains(sel.anchorNode))range=sel.getRangeAt(0).cloneRange()}
  function restore(){if(!range)return;var sel=window.getSelection();sel.removeAllRanges();sel.addRange(range)}
  function sync(){if(editor){S.description=editor.innerHTML;save()}}
  function paintPreview(){var pv=host.querySelector('.dp-preview');if(pv)pv.innerHTML=cleanHtml(fill(S.description))}

  function optionsSection(){
    var s=section(t('options')),grid=el('div','dp-options');
    var mature=el('div','dp-opt');mature.append(check(t('mature'),S.is_mature,function(v){S.is_mature=v;render()}));
    if(S.is_mature){
      var level=el('select','dp-input');['moderate','strict'].forEach(function(k){var o=el('option',null,t(k));o.value=k;o.selected=S.mature_level===k;level.append(o)});level.addEventListener('change',function(){S.mature_level=level.value});
      var classes=el('div','dp-classes');['nudity','sexual','gore','language','ideology'].forEach(function(k){classes.append(check(t(k),S.mature_classification.indexOf(k)>=0,function(v){var i=S.mature_classification.indexOf(k);if(v&&i<0)S.mature_classification.push(k);if(!v&&i>=0)S.mature_classification.splice(i,1)}))});
      mature.append(field(t('matureLevel'),level),el('span','dp-field__label',t('classification')),classes);
    }
    var labels=el('div','dp-opt');labels.append(check(t('noai'),S.noai,function(v){S.noai=v}),check(t('aiGenerated'),S.is_ai_generated,function(v){S.is_ai_generated=v}),check(t('comments'),S.allow_comments,function(v){S.allow_comments=v}),check(t('feature'),S.feature,function(v){S.feature=v}),check(t('download'),S.allow_free_download,function(v){S.allow_free_download=v}));
    var display=el('div','dp-opt'),size=el('select','dp-input');SIZES.forEach(function(px,i){var o=el('option',null,i?px+' px':t('sizeOriginal'));o.value=String(i);o.selected=S.display_resolution===i;size.append(o)});
    size.addEventListener('change',function(){S.display_resolution=Number(size.value);if(!S.display_resolution)S.add_watermark=false;render()});
    var wm=check(t('watermark'),S.add_watermark,function(v){S.add_watermark=v});if(!S.display_resolution){wm.querySelector('input').disabled=true;wm.classList.add('is-off')}
    display.append(field(t('size'),size),wm,el('small','dp-field__hint',t('watermarkHint')));
    var gallery=el('div','dp-opt');gallery.append(el('span','dp-field__label',t('gallery')));
    if(S.folders==='loading'||S.folders===null)gallery.append(el('small','dp-muted',t('loading')));
    else if(S.folders==='error')gallery.append(el('small','dp-muted',t('galleryError')));
    else{var fl=el('div','dp-folders');S.folders.forEach(function(f){fl.append(check(f.name,S.galleryids.indexOf(f.id)>=0,function(v){var i=S.galleryids.indexOf(f.id);if(v&&i<0)S.galleryids.push(f.id);if(!v&&i>=0)S.galleryids.splice(i,1)}))});gallery.append(fl)}
    gallery.append(el('small','dp-field__hint',t('galleryHint')));
    grid.append(labels,mature,display,gallery);s.append(grid);
    return s;
  }

  function actionSection(){
    var s=el('section','dp-section dp-actions'),modes=el('div','dp-modes');
    [['publish',t('modePublish')],['stash',t('modeStash')]].forEach(function(o){var b=btn('dp-mode'+(S.mode===o[0]?' is-on':''),o[1],function(){S.mode=o[0];render()});b.setAttribute('aria-pressed',String(S.mode===o[0]));modes.append(b)});
    var go=btn('btn dp-go',(S.mode==='publish'?t('go'):t('goStash'))+(S.files.length?' · '+S.files.length:''),submit);go.disabled=S.busy||!S.files.length;
    s.append(modes,el('small','dp-muted',t('modeHint')),go,status,results);
    return s;
  }
  var results=el('ul','dp-results');
  function submit(){
    if(editor)S.description=cleanHtml(editor.innerHTML,true);
    if(!S.files.length){say(t('needFiles'),'bad');return}
    if(S.description.indexOf('{link}')>=0&&!/^https?:\/\//i.test(S.link.trim())){say(t('linkMissing'),'bad');return}
    var form=new FormData(),settings=snapshot();settings.description=cleanHtml(fill(S.description));
    S.files.forEach(function(item){form.append('file',item.file,item.file.name);form.append('title_'+item.file.name,titleFor(item))});
    form.append('settings',JSON.stringify(settings));
    S.busy=true;say(t('uploading'),'wait');results.replaceChildren();render();
    fetch('/api/da/upload',{method:'POST',body:form,credentials:'same-origin'}).then(function(r){return r.json().catch(function(){return {ok:false,msg:'HTTP '+r.status}})}).then(function(j){
      (j.results||[]).forEach(function(item){var li=el('li',item.ok?'is-ok':'is-bad');li.append(el('b',null,item.title||item.name));
        if(item.url){var a=el('a',null,t('open')+' ↗');a.href=item.url;a.target='_blank';a.rel='noopener';li.append(a)}
        if(item.ok)li.append(btn('dp-link',t('copyDesc'),copyDescription));
        else if(item.ok&&item.stash)li.append(el('span',null,t('inStash')));
        if(item.error)li.append(el('span',null,item.error));results.append(li)});
      say(j.total?t('done',{ok:j.uploaded||0,total:j.total}):(j.msg||'Error'),j.ok?'ok':'bad');
    }).catch(function(e){say(String(e.message||e),'bad')}).finally(function(){S.busy=false;var go=host.querySelector('.dp-go');if(go)go.disabled=!S.files.length});
  }

  // Load account data when the DeviantArt block becomes visible (app.js toggles it after /api/da/status).
  var block=document.getElementById('daConnectedBlock');
  function visible(){return block&&block.style.display!=='none'&&block.offsetParent!==null}
  function wake(){if(visible()){loadFolders();if(!S.presets.length)loadPresets()}}
  if(block&&window.MutationObserver)new MutationObserver(wake).observe(block,{attributes:true,attributeFilter:['style']});
  var nav=document.querySelector('#nav [data-tab="da"]');if(nav)nav.addEventListener('click',function(){setTimeout(wake,300)});
  window.addEventListener('sm:langchange',function(){if(editor)S.description=editor.innerHTML;render()});
  window.SMDaPublish={state:function(){return {files:S.files.length,tags:S.tags.slice(),mode:S.mode,description:S.description}},addFiles:addFiles};
  render();
})();
