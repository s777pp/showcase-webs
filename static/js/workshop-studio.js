/* "Rows and squares" tab (Workshop Studio), reworked 2026-10-01.
   Layout: header (showcase type + 1-3 rows) -> settings panel with tabs (Files, Frame,
   Color, Animation) and a sticky "create" footer -> live Steam-profile preview.
   Rows layout: one full-height file per row, optional frame around each file.
   Squares layout: per row, the user drags/zooms a source under a 5:1 window; the server
   cuts it into five 150x150 files (row_N/ folders when there are several rows).
   The preview draws the same frames/effects as the server (workshop-squares-fx.js) and
   shows the squares with Steam's gaps (122 px tiles, 4 px apart at 626 px). */
(function(){
  'use strict';
  var root=document.getElementById('workshopStudio');if(!root)return;
  var FX=window.SMSquaresFx,GRADE=window.SMColorGrade;
  var COPY={
    en:{title:'Rows and squares',introRows:'Each file becomes one full-height Workshop row. Up to three rows, HEX 21 included.',introSquares:'Each row is five 150×150 squares cut from your picture. Up to three rows, HEX 21 included.',typeRows:'Full-height rows',typeRowsHint:'one file = one row',typeSquares:'Squares 150×150',typeSquaresHint:'five squares per row',rowsLabel:'Rows',tabFiles:'Files',tabFrame:'Frame',tabFrameFx:'Frame & effects',tabColor:'Color',tabMotion:'Animation',row:'Row {n}',dropTitle:'Drop a file or click to choose',dropHint:'Image, GIF, MP4 or WebM',addMany:'Add several files at once',replace:'Replace file',remove:'Remove',moveUp:'Move up',moveDown:'Move down',area:'Visible area of row {n}',areaHint:'Drag the frame here or the picture in the preview. Scroll or use the slider to zoom.',zoom:'Zoom',reset:'Reset',colorFor:'Color of row {n}',colorEmpty:'Add a file to this row first.',applyAll:'Apply to all rows',resetColor:'Reset color',brightness:'Brightness',contrast:'Contrast',saturation:'Saturation',hue:'Hue',motionAnimated:'GIFs, videos and animated frames become looping GIFs with these settings.',motionStatic:'Everything is still right now, so you will get PNG files. These settings apply once something moves.',fps:'Frames per second',duration:'Clip length',start:'Start of row {n}, s',previewTitle:'Steam profile preview',previewRows:'Rows are shown in order, the way Steam stacks showcases.',previewSquares:'Drag a row to move the picture, scroll over it to zoom.',showcase:'Workshop Showcase',emptyRow:'Row {n}: drop a file here',summary:'Rows: {rows} · files: {files} · {format}',zipFolders:'One folder per row: row_1 … row_{n}.',create:'Prepare and download ZIP',missing:'Add a file to every row.',uploading:'Uploading files…',processing:'Preparing your rows…',done:'ZIP is ready and downloading.',download:'Download ZIP again',error:'Could not prepare the files. Please try again.',oversize:'Each source must be under 40 MB.',totalLimit:'All files together must be under 100 MB.',noPreview:'No browser preview for this format; the server will convert it.',cannotCrop:'This format cannot be cropped in the browser. Save it as PNG or JPG first.',freeRows:'Free plan: a small ShowcaseMaker watermark is added to each file.',freeSquares:'Free plan: the ShowcaseMaker watermark goes only on the DeviantArt preview (if you add it). The Steam files stay clean.',autoHex:'HEX 21 is applied automatically',frameRows:'The frame goes around each row file.',active:'editing',loading:'Loading…'},
    ru:{title:'Ряды и квадраты',introRows:'Каждый файл становится одним рядом Мастерской во всю высоту. До трёх рядов, HEX 21 уже внутри.',introSquares:'Каждый ряд — пять квадратов 150×150 из твоей картинки. До трёх рядов, HEX 21 уже внутри.',typeRows:'Ряды во всю высоту',typeRowsHint:'один файл = один ряд',typeSquares:'Квадраты 150×150',typeSquaresHint:'пять квадратов в ряду',rowsLabel:'Рядов',tabFiles:'Файлы',tabFrame:'Рамка',tabFrameFx:'Рамка и эффекты',tabColor:'Цвет',tabMotion:'Анимация',row:'Ряд {n}',dropTitle:'Перетащи файл или нажми, чтобы выбрать',dropHint:'Картинка, GIF, MP4 или WebM',addMany:'Добавить сразу несколько файлов',replace:'Заменить файл',remove:'Убрать',moveUp:'Выше',moveDown:'Ниже',area:'Видимая область ряда {n}',areaHint:'Двигай рамку здесь или картинку в предпросмотре. Масштаб — колесом мыши или ползунком.',zoom:'Масштаб',reset:'Сбросить',colorFor:'Цвет ряда {n}',colorEmpty:'Сначала добавь файл в этот ряд.',applyAll:'Применить ко всем рядам',resetColor:'Сбросить цвет',brightness:'Яркость',contrast:'Контраст',saturation:'Насыщенность',hue:'Оттенок',motionAnimated:'GIF, видео и анимированные рамки станут зацикленными GIF с этими настройками.',motionStatic:'Сейчас всё статично — получишь PNG. Эти настройки сработают, когда появится движение.',fps:'Кадров в секунду',duration:'Длина анимации',start:'Начало ряда {n}, с',previewTitle:'Предпросмотр в профиле Steam',previewRows:'Ряды идут по порядку, как Steam ставит витрины друг под другом.',previewSquares:'Тяни ряд, чтобы сдвинуть картинку, крути колесо над ним для масштаба.',showcase:'Витрина мастерской',emptyRow:'Ряд {n}: перетащи файл сюда',summary:'Рядов: {rows} · файлов: {files} · {format}',zipFolders:'По папке на ряд: row_1 … row_{n}.',create:'Подготовить и скачать ZIP',missing:'Добавь файл в каждый ряд.',uploading:'Загружаем файлы…',processing:'Готовим ряды…',done:'ZIP готов и скачивается.',download:'Скачать ZIP ещё раз',error:'Не удалось подготовить файлы. Попробуй ещё раз.',oversize:'Каждый исходник должен быть меньше 40 МБ.',totalLimit:'Общий размер файлов должен быть меньше 100 МБ.',noPreview:'Браузер не показывает этот формат; сервер сам его конвертирует.',cannotCrop:'Этот формат нельзя кадрировать в браузере. Сохрани его как PNG или JPG.',freeRows:'Бесплатный тариф: на каждый файл добавляется небольшой водяной знак ShowcaseMaker.',freeSquares:'Бесплатный тариф: водяной знак ShowcaseMaker ставится только на превью для DeviantArt (если его добавить). Файлы для Steam остаются чистыми.',autoHex:'HEX 21 применяется автоматически',frameRows:'Рамка рисуется вокруг каждого файла-ряда.',active:'редактируется',loading:'Загрузка…'},
    de:{title:'Reihen und Quadrate',introRows:'Jede Datei wird zu einer Workshop-Reihe in voller Höhe. Bis zu drei Reihen, HEX 21 inklusive.',introSquares:'Jede Reihe besteht aus fünf 150×150-Quadraten aus deinem Bild. Bis zu drei Reihen, HEX 21 inklusive.',typeRows:'Reihen in voller Höhe',typeRowsHint:'eine Datei = eine Reihe',typeSquares:'Quadrate 150×150',typeSquaresHint:'fünf Quadrate pro Reihe',rowsLabel:'Reihen',tabFiles:'Dateien',tabFrame:'Rahmen',tabFrameFx:'Rahmen & Effekte',tabColor:'Farbe',tabMotion:'Animation',row:'Reihe {n}',dropTitle:'Datei hierher ziehen oder klicken',dropHint:'Bild, GIF, MP4 oder WebM',addMany:'Mehrere Dateien auf einmal hinzufügen',replace:'Datei ersetzen',remove:'Entfernen',moveUp:'Nach oben',moveDown:'Nach unten',area:'Sichtbarer Bereich von Reihe {n}',areaHint:'Ziehe den Rahmen hier oder das Bild in der Vorschau. Zoomen mit dem Mausrad oder Regler.',zoom:'Zoom',reset:'Zurücksetzen',colorFor:'Farbe von Reihe {n}',colorEmpty:'Füge dieser Reihe zuerst eine Datei hinzu.',applyAll:'Auf alle Reihen anwenden',resetColor:'Farbe zurücksetzen',brightness:'Helligkeit',contrast:'Kontrast',saturation:'Sättigung',hue:'Farbton',motionAnimated:'GIFs, Videos und animierte Rahmen werden mit diesen Einstellungen zu Endlos-GIFs.',motionStatic:'Gerade ist alles statisch, du bekommst PNG-Dateien. Diese Einstellungen gelten, sobald sich etwas bewegt.',fps:'Bilder pro Sekunde',duration:'Cliplänge',start:'Start von Reihe {n}, s',previewTitle:'Vorschau im Steam-Profil',previewRows:'Die Reihen stehen untereinander, so wie Steam Vitrinen stapelt.',previewSquares:'Ziehe eine Reihe, um das Bild zu verschieben, scrolle darüber zum Zoomen.',showcase:'Workshop-Vitrine',emptyRow:'Reihe {n}: Datei hierher ziehen',summary:'Reihen: {rows} · Dateien: {files} · {format}',zipFolders:'Ein Ordner pro Reihe: row_1 … row_{n}.',create:'ZIP erstellen und herunterladen',missing:'Füge jeder Reihe eine Datei hinzu.',uploading:'Dateien werden hochgeladen…',processing:'Reihen werden vorbereitet…',done:'ZIP ist fertig und wird heruntergeladen.',download:'ZIP erneut herunterladen',error:'Dateien konnten nicht verarbeitet werden. Bitte erneut versuchen.',oversize:'Jede Quelldatei muss unter 40 MB bleiben.',totalLimit:'Alle Dateien zusammen müssen unter 100 MB bleiben.',noPreview:'Keine Browser-Vorschau für dieses Format; der Server wandelt es um.',cannotCrop:'Dieses Format lässt sich im Browser nicht zuschneiden. Speichere es zuerst als PNG oder JPG.',freeRows:'Kostenloser Tarif: Jede Datei erhält ein kleines ShowcaseMaker-Wasserzeichen.',freeSquares:'Kostenloser Tarif: Das ShowcaseMaker-Wasserzeichen kommt nur auf die DeviantArt-Vorschau (falls du sie hinzufügst). Die Steam-Dateien bleiben sauber.',autoHex:'HEX 21 wird automatisch angewendet',frameRows:'Der Rahmen liegt um jede Reihendatei.',active:'in Bearbeitung',loading:'Wird geladen…'},
    tr:{title:'Satırlar ve kareler',introRows:'Her dosya tam yükseklikte bir Atölye satırı olur. En fazla üç satır, HEX 21 dahil.',introSquares:'Her satır, resminden kesilen beş adet 150×150 karedir. En fazla üç satır, HEX 21 dahil.',typeRows:'Tam yükseklikte satırlar',typeRowsHint:'bir dosya = bir satır',typeSquares:'Kareler 150×150',typeSquaresHint:'satır başına beş kare',rowsLabel:'Satır',tabFiles:'Dosyalar',tabFrame:'Çerçeve',tabFrameFx:'Çerçeve ve efektler',tabColor:'Renk',tabMotion:'Animasyon',row:'Satır {n}',dropTitle:'Dosyayı bırak veya seçmek için tıkla',dropHint:'Görsel, GIF, MP4 veya WebM',addMany:'Birden fazla dosyayı birlikte ekle',replace:'Dosyayı değiştir',remove:'Kaldır',moveUp:'Yukarı',moveDown:'Aşağı',area:'Satır {n} görünen alanı',areaHint:'Çerçeveyi burada ya da resmi önizlemede sürükle. Yakınlaştırmak için tekerleği veya kaydırıcıyı kullan.',zoom:'Yakınlaştırma',reset:'Sıfırla',colorFor:'Satır {n} rengi',colorEmpty:'Önce bu satıra bir dosya ekle.',applyAll:'Tüm satırlara uygula',resetColor:'Rengi sıfırla',brightness:'Parlaklık',contrast:'Kontrast',saturation:'Doygunluk',hue:'Ton',motionAnimated:'GIF’ler, videolar ve animasyonlu çerçeveler bu ayarlarla döngülü GIF olur.',motionStatic:'Şu anda her şey sabit, PNG dosyaları alacaksın. Bu ayarlar bir şey hareket ettiğinde geçerli olur.',fps:'Saniyedeki kare',duration:'Klip uzunluğu',start:'Satır {n} başlangıcı, sn',previewTitle:'Steam profili önizlemesi',previewRows:'Satırlar, Steam’in vitrinleri dizdiği gibi sırayla gösterilir.',previewSquares:'Resmi kaydırmak için satırı sürükle, yakınlaştırmak için üzerinde tekerleği çevir.',showcase:'Atölye Vitrini',emptyRow:'Satır {n}: dosyayı buraya bırak',summary:'Satır: {rows} · dosya: {files} · {format}',zipFolders:'Her satır için bir klasör: row_1 … row_{n}.',create:'ZIP hazırla ve indir',missing:'Her satıra bir dosya ekle.',uploading:'Dosyalar yükleniyor…',processing:'Satırlar hazırlanıyor…',done:'ZIP hazır, indiriliyor.',download:'ZIP’i tekrar indir',error:'Dosyalar hazırlanamadı. Lütfen tekrar dene.',oversize:'Her kaynak 40 MB altında olmalıdır.',totalLimit:'Tüm dosyaların toplamı 100 MB altında olmalıdır.',noPreview:'Bu biçim tarayıcıda önizlenemez; sunucu dönüştürecek.',cannotCrop:'Bu biçim tarayıcıda kırpılamaz. Önce PNG veya JPG olarak kaydet.',freeRows:'Ücretsiz planda her dosyaya küçük bir ShowcaseMaker filigranı eklenir.',freeSquares:'Ücretsiz plan: ShowcaseMaker filigranı yalnızca DeviantArt önizlemesine eklenir (eklersen). Steam dosyaları temiz kalır.',autoHex:'HEX 21 otomatik uygulanır',frameRows:'Çerçeve her satır dosyasının etrafına çizilir.',active:'düzenleniyor',loading:'Yükleniyor…'},
    fr:{title:'Rangées et carrés',introRows:'Chaque fichier devient une rangée Workshop en pleine hauteur. Jusqu’à trois rangées, HEX 21 inclus.',introSquares:'Chaque rangée compte cinq carrés 150×150 découpés dans votre image. Jusqu’à trois rangées, HEX 21 inclus.',typeRows:'Rangées pleine hauteur',typeRowsHint:'un fichier = une rangée',typeSquares:'Carrés 150×150',typeSquaresHint:'cinq carrés par rangée',rowsLabel:'Rangées',tabFiles:'Fichiers',tabFrame:'Cadre',tabFrameFx:'Cadre et effets',tabColor:'Couleur',tabMotion:'Animation',row:'Rangée {n}',dropTitle:'Déposez un fichier ou cliquez pour choisir',dropHint:'Image, GIF, MP4 ou WebM',addMany:'Ajouter plusieurs fichiers d’un coup',replace:'Remplacer le fichier',remove:'Retirer',moveUp:'Monter',moveDown:'Descendre',area:'Zone visible de la rangée {n}',areaHint:'Déplacez le cadre ici ou l’image dans l’aperçu. Zoom avec la molette ou le curseur.',zoom:'Zoom',reset:'Réinitialiser',colorFor:'Couleur de la rangée {n}',colorEmpty:'Ajoutez d’abord un fichier à cette rangée.',applyAll:'Appliquer à toutes les rangées',resetColor:'Réinitialiser la couleur',brightness:'Luminosité',contrast:'Contraste',saturation:'Saturation',hue:'Teinte',motionAnimated:'Les GIF, vidéos et cadres animés deviennent des GIF en boucle avec ces réglages.',motionStatic:'Tout est fixe pour l’instant : vous obtiendrez des PNG. Ces réglages s’appliquent dès que quelque chose bouge.',fps:'Images par seconde',duration:'Durée du clip',start:'Début de la rangée {n}, s',previewTitle:'Aperçu du profil Steam',previewRows:'Les rangées se suivent, comme Steam empile les vitrines.',previewSquares:'Faites glisser une rangée pour déplacer l’image, molette dessus pour zoomer.',showcase:'Vitrine Workshop',emptyRow:'Rangée {n} : déposez un fichier ici',summary:'Rangées : {rows} · fichiers : {files} · {format}',zipFolders:'Un dossier par rangée : row_1 … row_{n}.',create:'Préparer et télécharger le ZIP',missing:'Ajoutez un fichier à chaque rangée.',uploading:'Envoi des fichiers…',processing:'Préparation des rangées…',done:'Le ZIP est prêt et se télécharge.',download:'Télécharger le ZIP à nouveau',error:'Impossible de préparer les fichiers. Réessayez.',oversize:'Chaque source doit faire moins de 40 Mo.',totalLimit:'La taille totale des fichiers doit rester inférieure à 100 Mo.',noPreview:'Pas d’aperçu navigateur pour ce format ; le serveur le convertira.',cannotCrop:'Ce format ne peut pas être recadré dans le navigateur. Enregistrez-le d’abord en PNG ou JPG.',freeRows:'Offre gratuite : un petit filigrane ShowcaseMaker est ajouté à chaque fichier.',freeSquares:'Offre gratuite : le filigrane ShowcaseMaker va uniquement sur l’aperçu DeviantArt (si vous l’ajoutez). Les fichiers Steam restent propres.',autoHex:'HEX 21 est appliqué automatiquement',frameRows:'Le cadre entoure chaque fichier de rangée.',active:'en cours',loading:'Chargement…'},
    uk:{title:'Ряди та квадрати',introRows:'Кожен файл стає одним рядом Майстерні на всю висоту. До трьох рядів, HEX 21 уже всередині.',introSquares:'Кожен ряд — п’ять квадратів 150×150 з твоєї картинки. До трьох рядів, HEX 21 уже всередині.',typeRows:'Ряди на всю висоту',typeRowsHint:'один файл = один ряд',typeSquares:'Квадрати 150×150',typeSquaresHint:'п’ять квадратів у ряду',rowsLabel:'Рядів',tabFiles:'Файли',tabFrame:'Рамка',tabFrameFx:'Рамка та ефекти',tabColor:'Колір',tabMotion:'Анімація',row:'Ряд {n}',dropTitle:'Перетягни файл або натисни, щоб вибрати',dropHint:'Картинка, GIF, MP4 або WebM',addMany:'Додати кілька файлів одразу',replace:'Замінити файл',remove:'Прибрати',moveUp:'Вище',moveDown:'Нижче',area:'Видима область ряду {n}',areaHint:'Рухай рамку тут або картинку в попередньому перегляді. Масштаб — колесом миші або повзунком.',zoom:'Масштаб',reset:'Скинути',colorFor:'Колір ряду {n}',colorEmpty:'Спочатку додай файл у цей ряд.',applyAll:'Застосувати до всіх рядів',resetColor:'Скинути колір',brightness:'Яскравість',contrast:'Контраст',saturation:'Насиченість',hue:'Відтінок',motionAnimated:'GIF, відео й анімовані рамки стануть зацикленими GIF з цими налаштуваннями.',motionStatic:'Зараз усе статичне — отримаєш PNG. Ці налаштування спрацюють, коли з’явиться рух.',fps:'Кадрів за секунду',duration:'Довжина анімації',start:'Початок ряду {n}, с',previewTitle:'Попередній перегляд у профілі Steam',previewRows:'Ряди йдуть по черзі, як Steam ставить вітрини одна під одною.',previewSquares:'Тягни ряд, щоб зсунути картинку, крути колесо над ним для масштабу.',showcase:'Вітрина майстерні',emptyRow:'Ряд {n}: перетягни файл сюди',summary:'Рядів: {rows} · файлів: {files} · {format}',zipFolders:'По теці на ряд: row_1 … row_{n}.',create:'Підготувати й завантажити ZIP',missing:'Додай файл у кожен ряд.',uploading:'Завантажуємо файли…',processing:'Готуємо ряди…',done:'ZIP готовий і завантажується.',download:'Завантажити ZIP ще раз',error:'Не вдалося підготувати файли. Спробуй ще раз.',oversize:'Кожен вихідний файл має бути менше 40 МБ.',totalLimit:'Загальний розмір файлів має бути менше 100 МБ.',noPreview:'Браузер не показує цей формат; сервер сам його конвертує.',cannotCrop:'Цей формат не можна кадрувати в браузері. Збережи його як PNG або JPG.',freeRows:'Безкоштовний тариф: до кожного файлу додається невеликий водяний знак ShowcaseMaker.',freeSquares:'Безкоштовний тариф: водяний знак ShowcaseMaker ставиться лише на превʼю для DeviantArt (якщо його додати). Файли для Steam лишаються чистими.',autoHex:'HEX 21 застосовується автоматично',frameRows:'Рамка малюється навколо кожного файлу-ряду.',active:'редагується',loading:'Завантаження…'},
    es:{title:'Filas y cuadrados',introRows:'Cada archivo se convierte en una fila Workshop de altura completa. Hasta tres filas, HEX 21 incluido.',introSquares:'Cada fila son cinco cuadrados de 150×150 recortados de tu imagen. Hasta tres filas, HEX 21 incluido.',typeRows:'Filas de altura completa',typeRowsHint:'un archivo = una fila',typeSquares:'Cuadrados 150×150',typeSquaresHint:'cinco cuadrados por fila',rowsLabel:'Filas',tabFiles:'Archivos',tabFrame:'Marco',tabFrameFx:'Marco y efectos',tabColor:'Color',tabMotion:'Animación',row:'Fila {n}',dropTitle:'Suelta un archivo o haz clic para elegir',dropHint:'Imagen, GIF, MP4 o WebM',addMany:'Añadir varios archivos a la vez',replace:'Reemplazar archivo',remove:'Quitar',moveUp:'Subir',moveDown:'Bajar',area:'Zona visible de la fila {n}',areaHint:'Arrastra el marco aquí o la imagen en la vista previa. Zoom con la rueda o el control.',zoom:'Zoom',reset:'Restablecer',colorFor:'Color de la fila {n}',colorEmpty:'Primero añade un archivo a esta fila.',applyAll:'Aplicar a todas las filas',resetColor:'Restablecer color',brightness:'Brillo',contrast:'Contraste',saturation:'Saturación',hue:'Tono',motionAnimated:'Los GIF, vídeos y marcos animados se convierten en GIF en bucle con estos ajustes.',motionStatic:'Ahora todo es estático: obtendrás archivos PNG. Estos ajustes se aplican cuando algo se mueva.',fps:'Fotogramas por segundo',duration:'Duración del clip',start:'Inicio de la fila {n}, s',previewTitle:'Vista previa del perfil de Steam',previewRows:'Las filas van en orden, como Steam apila los escaparates.',previewSquares:'Arrastra una fila para mover la imagen, usa la rueda encima para hacer zoom.',showcase:'Escaparate de Workshop',emptyRow:'Fila {n}: suelta un archivo aquí',summary:'Filas: {rows} · archivos: {files} · {format}',zipFolders:'Una carpeta por fila: row_1 … row_{n}.',create:'Preparar y descargar ZIP',missing:'Añade un archivo a cada fila.',uploading:'Subiendo archivos…',processing:'Preparando las filas…',done:'El ZIP está listo y se está descargando.',download:'Descargar ZIP otra vez',error:'No se pudieron preparar los archivos. Inténtalo de nuevo.',oversize:'Cada archivo debe pesar menos de 40 MB.',totalLimit:'El total de archivos debe ser menor de 100 MB.',noPreview:'El navegador no muestra este formato; el servidor lo convertirá.',cannotCrop:'Este formato no se puede recortar en el navegador. Guárdalo primero como PNG o JPG.',freeRows:'Plan gratuito: se añade una pequeña marca de agua de ShowcaseMaker a cada archivo.',freeSquares:'Plan gratuito: la marca de agua de ShowcaseMaker va solo en la vista previa para DeviantArt (si la añades). Los archivos de Steam quedan limpios.',autoHex:'HEX 21 se aplica automáticamente',frameRows:'El marco rodea cada archivo de fila.',active:'en edición',loading:'Cargando…'},
    pt:{title:'Linhas e quadrados',introRows:'Cada arquivo vira uma linha Workshop de altura completa. Até três linhas, HEX 21 incluído.',introSquares:'Cada linha são cinco quadrados 150×150 recortados da sua imagem. Até três linhas, HEX 21 incluído.',typeRows:'Linhas de altura completa',typeRowsHint:'um arquivo = uma linha',typeSquares:'Quadrados 150×150',typeSquaresHint:'cinco quadrados por linha',rowsLabel:'Linhas',tabFiles:'Arquivos',tabFrame:'Moldura',tabFrameFx:'Moldura e efeitos',tabColor:'Cor',tabMotion:'Animação',row:'Linha {n}',dropTitle:'Solte um arquivo ou clique para escolher',dropHint:'Imagem, GIF, MP4 ou WebM',addMany:'Adicionar vários arquivos de uma vez',replace:'Substituir arquivo',remove:'Remover',moveUp:'Subir',moveDown:'Descer',area:'Área visível da linha {n}',areaHint:'Arraste a moldura aqui ou a imagem na prévia. Zoom com a roda do mouse ou o controle.',zoom:'Zoom',reset:'Redefinir',colorFor:'Cor da linha {n}',colorEmpty:'Primeiro adicione um arquivo a esta linha.',applyAll:'Aplicar a todas as linhas',resetColor:'Redefinir cor',brightness:'Brilho',contrast:'Contraste',saturation:'Saturação',hue:'Matiz',motionAnimated:'GIFs, vídeos e molduras animadas viram GIFs em loop com estas configurações.',motionStatic:'Agora tudo está parado, então você receberá PNG. Estas configurações valem quando algo se mover.',fps:'Quadros por segundo',duration:'Duração do clipe',start:'Início da linha {n}, s',previewTitle:'Prévia do perfil Steam',previewRows:'As linhas aparecem em ordem, como a Steam empilha as vitrines.',previewSquares:'Arraste uma linha para mover a imagem, use a roda sobre ela para dar zoom.',showcase:'Vitrine do Workshop',emptyRow:'Linha {n}: solte um arquivo aqui',summary:'Linhas: {rows} · arquivos: {files} · {format}',zipFolders:'Uma pasta por linha: row_1 … row_{n}.',create:'Preparar e baixar ZIP',missing:'Adicione um arquivo a cada linha.',uploading:'Enviando arquivos…',processing:'Preparando as linhas…',done:'O ZIP está pronto e sendo baixado.',download:'Baixar ZIP novamente',error:'Não foi possível preparar os arquivos. Tente novamente.',oversize:'Cada arquivo deve ter menos de 40 MB.',totalLimit:'O total dos arquivos deve ser menor que 100 MB.',noPreview:'Sem prévia no navegador para este formato; o servidor fará a conversão.',cannotCrop:'Este formato não pode ser recortado no navegador. Salve-o primeiro como PNG ou JPG.',freeRows:'Plano gratuito: uma pequena marca d’água ShowcaseMaker é adicionada a cada arquivo.',freeSquares:'Plano gratuito: a marca d’água ShowcaseMaker vai só na prévia para o DeviantArt (se você adicionar). Os arquivos da Steam ficam limpos.',autoHex:'HEX 21 é aplicado automaticamente',frameRows:'A moldura fica em volta de cada arquivo de linha.',active:'editando',loading:'Carregando…'}
  };
  function language(){return window.SMLang?.get?.()||document.documentElement.lang||'en'}
  function t(key,vars){var text=(COPY[language()]||COPY.en)[key]||COPY.en[key]||key;if(vars)Object.keys(vars).forEach(function(name){text=text.split('{'+name+'}').join(vars[name])});return text}

  // Geometry in strip pixels: one row of squares is 750x150 (five 150x150 files).
  var STRIP={w:750,h:150},SQ=150,MAX_ZOOM=6,ROW_W=750;
  var LIMITS={brightness:[50,150,100],contrast:[50,150,100],saturation:[0,200,100],hue:[-180,180,0]};
  var VIDEO_EXT=['mp4','webm'],PREVIEW_EXT=['png','jpg','jpeg','webp','gif','bmp','avif','ico','apng','jfif'];
  var ACCEPT='image/*,video/mp4,video/webm,.ico,.cur,.bmp,.tif,.tiff,.avif,.tga,.psd,.qoi,.jp2,.j2k,.jfif,.dds,.icns,.pcx,.apng,.heic,.heif';
  var S={layout:'rows',rows:1,active:0,panel:'files',fps:12,duration:4,sources:[null,null,null],busy:false,pro:null,downloadUrl:'',
    fxRows:FX?FX.defaults():null,fxSquares:FX?FX.defaults():null};
  var runtime=[],fxStrip=null,fxDirty=true,loop=0,lastPaint=0;

  function el(tag,cls,text){var node=document.createElement(tag);if(cls)node.className=cls;if(text!=null)node.textContent=text;return node}
  function button(cls,text,onClick){var node=el('button',cls,text);node.type='button';if(onClick)node.addEventListener('click',onClick);return node}
  function icon(name){
    var paths={
      files:'<path d="M4 7a2 2 0 0 1 2-2h4l2 2h6a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z"/>',
      frame:'<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="8" y="8" width="8" height="8" rx="1"/>',
      color:'<path d="M12 3a9 9 0 1 0 0 18c1.1 0 1.6-.9 1.2-1.8-.5-1 .1-2.2 1.3-2.2H17a4 4 0 0 0 4-4c0-5.5-4-10-9-10z"/><circle cx="7.5" cy="11" r="1.2"/><circle cx="10.5" cy="7" r="1.2"/><circle cx="15" cy="7.5" r="1.2"/>',
      motion:'<circle cx="12" cy="12" r="8"/><path d="m10 9 5 3-5 3z"/>',
      upload:'<path d="M12 16V4m0 0-4 4m4-4 4 4M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/>',
      up:'<path d="m6 15 6-6 6 6"/>',down:'<path d="m6 9 6 6 6-6"/>',x:'<path d="M6 6l12 12M18 6 6 18"/>',
      plus:'<path d="M12 5v14M5 12h14"/>',reset:'<path d="M4 12a8 8 0 1 0 2.3-5.7M4 4v5h5"/>'
    };
    var svg='<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'+(paths[name]||'')+'</svg>';
    var span=el('span','wsx-icon');span.innerHTML=svg;return span;
  }
  function squares(){return S.layout==='squares'}
  function fx(){return squares()?S.fxSquares:S.fxRows}
  function rowFrame(){var f=S.fxRows&&S.fxRows.frame;return f&&f.style!=='none'?Object.assign({},f,{target:'strip'}):null}
  function frameAnimated(){if(!FX)return false;return squares()?FX.isAnimated(S.fxSquares):!!(rowFrame()&&FX.isAnimatedFrame(S.fxRows.frame.style))}
  function active(){return S.sources.slice(0,S.rows)}
  function moving(){return frameAnimated()||active().some(function(source){return source&&source.animated})}
  function fileCount(){return squares()?S.rows*5:S.rows}
  function suffixOf(file){return (file.name.split('.').pop()||'').toLowerCase()}
  function bytes(size){return size>=1048576?(size/1048576).toFixed(1)+' MB':Math.max(1,Math.round(size/1024))+' KB'}
  function gradeOf(source){return GRADE?GRADE.normalize(source&&source.grade):{brightness:100,contrast:100,saturation:100,hue:0}}
  function gradeFilter(source){return GRADE&&source?GRADE.filter(source.grade):'none'}
  function graded(source){var g=gradeOf(source);return g.brightness!==100||g.contrast!==100||g.saturation!==100||g.hue!==0}

  // ------------------------------------------------------------------ skeleton
  root.classList.add('wsx');root.replaceChildren();
  var head=el('header','wsx-head'),headText=el('div','wsx-head__text'),intro=el('p','wsx-head__intro');
  // The page title above already names the tab; this header explains the chosen type.
  headText.append(el('small','wsx-head__kicker','STEAM · WORKSHOP'),intro);
  var typeGroup=el('div','wsx-type');typeGroup.setAttribute('role','radiogroup');
  var typeButtons=['rows','squares'].map(function(key){
    var b=button('wsx-type__btn',null,function(){if(S.busy||S.layout===key)return;S.layout=key;S.panel=S.panel==='frame'||S.panel==='color'||S.panel==='motion'?S.panel:'files';fxDirty=true;setStatus('','');renderAll()});
    b.dataset.workshopLayout=key;b.setAttribute('role','radio');
    var art=el('span','wsx-type__art wsx-type__art--'+key);for(var i=0;i<(key==='rows'?2:5);i++)art.append(el('i'));
    b.append(art,el('span','wsx-type__name'),el('small','wsx-type__hint'));typeGroup.append(b);return b;
  });
  var rowsGroup=el('div','wsx-count'),rowsLabel=el('span','wsx-count__label'),rowsButtons=el('div','wsx-count__buttons');rowsButtons.setAttribute('role','radiogroup');
  var countButtons=[1,2,3].map(function(n){
    var b=button('wsx-count__btn',null,function(){if(S.busy)return;S.rows=n;if(S.active>=n)S.active=n-1;renderAll()});
    b.dataset.workshopRows=String(n);b.setAttribute('role','radio');
    var art=el('span','wsx-count__art');for(var i=0;i<n;i++)art.append(el('i'));b.append(art,el('b',null,String(n)));rowsButtons.append(b);return b;
  });
  rowsGroup.append(rowsLabel,rowsButtons);
  head.append(headText,typeGroup,rowsGroup);

  var body=el('div','wsx-body'),panel=el('aside','wsx-panel'),tabs=el('div','wsx-tabs'),panelBody=el('div','wsx-panel__body'),foot=el('div','wsx-foot');
  tabs.setAttribute('role','tablist');
  var tabKeys=['files','frame','color','motion'],tabButtons={};
  tabKeys.forEach(function(key){
    var b=button('wsx-tab',null,function(){S.panel=key;renderPanel();syncTabs()});
    b.dataset.panel=key;b.setAttribute('role','tab');b.append(icon(key),el('span','wsx-tab__name'),el('i','wsx-tab__dot'));tabs.append(b);tabButtons[key]=b;
  });
  var summary=el('p','wsx-foot__summary'),zipNote=el('p','wsx-foot__zip'),planNote=el('p','wsx-foot__plan'),create=button('btn wsx-foot__create',null,start);
  create.id='workshopCreate';
  var progress=el('progress','wsx-foot__progress');progress.max=100;progress.value=0;progress.hidden=true;
  var status=el('p','wsx-foot__status');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
  var download=el('a','wsx-foot__download');download.hidden=true;download.download='workshop.zip';
  planNote.hidden=true;
  foot.append(summary,zipNote,planNote,create,progress,status,download);
  // Squares: optional whole strip / preview in the ZIP (same switches as Process, encode-choice.js).
  var extrasBox=window.SMEncodeChoice?SMEncodeChoice.mountExtras(foot,{before:create,className:'wsx-foot__extras'}):null;
  panel.append(tabs,panelBody,foot);

  var stage=el('section','wsx-stage'),stageHead=el('div','wsx-stage__head'),stageTitle=el('strong','wsx-stage__title'),stageHint=el('span','wsx-stage__hint');
  var zoomBox=el('div','wsx-zoom'),zoomName=el('span'),zoomRange=el('input'),zoomReset=button('wsx-zoom__reset',null,function(){var source=S.sources[S.active];if(source&&source.natural){centerView(source);placeRow(S.active);syncZoom();drawMap()}});
  zoomRange.type='range';zoomRange.min='1';zoomRange.max=String(MAX_ZOOM);zoomRange.step='0.01';
  zoomRange.addEventListener('input',function(){var source=S.sources[S.active];if(source&&source.view){zoomTo(source,Number(this.value),STRIP.w/2,STRIP.h/2);placeRow(S.active);drawMap()}});
  zoomReset.append(icon('reset'));
  zoomBox.append(zoomName,zoomRange,zoomReset);
  var stageTitleWrap=el('div','wsx-stage__titles');stageTitleWrap.append(stageTitle,stageHint);
  stageHead.append(stageTitleWrap,zoomBox);
  var profile=el('div','wsx-profile'),stageFoot=el('p','wsx-stage__foot');
  stage.append(stageHead,profile,stageFoot);
  body.append(panel,stage);
  var picker=el('input');picker.type='file';picker.hidden=true;picker.accept=ACCEPT;picker.dataset.smEnhanced='1';
  var multiPicker=el('input');multiPicker.type='file';multiPicker.hidden=true;multiPicker.multiple=true;multiPicker.accept=ACCEPT;multiPicker.dataset.smEnhanced='1';
  root.append(head,body,picker,multiPicker);
  var pickTarget=0;
  picker.addEventListener('change',function(){if(this.files[0])setFile(pickTarget,this.files[0]);this.value=''});
  multiPicker.addEventListener('change',function(){addFiles(Array.from(this.files));this.value=''});
  function choose(row){pickTarget=row;picker.click()}

  // ------------------------------------------------------------------ files
  function setStatus(message,kind){status.textContent=message||'';status.dataset.kind=kind||''}
  function release(source){if(source){URL.revokeObjectURL(source.url)}}
  function setFile(index,file){
    var suffix=suffixOf(file),video=VIDEO_EXT.indexOf(suffix)>=0||/^video\//.test(file.type||'');
    if(file.size>40*1024*1024){setStatus(t('oversize'),'bad');return}
    if(!video&&!/^image\//.test(file.type||'')&&ACCEPT.indexOf('.'+suffix)<0&&PREVIEW_EXT.indexOf(suffix)<0){setStatus(t('error'),'bad');return}
    var old=S.sources[index];release(old);
    var source={file:file,url:URL.createObjectURL(file),video:video,animated:video||suffix==='gif'||suffix==='apng',grade:old?old.grade:gradeOf(null),start:0,duration:0,natural:null,view:null,loading:true,broken:false};
    S.sources[index]=source;S.active=index;setStatus('','');
    probe(source,function(){if(S.sources.indexOf(source)<0)return;renderAll()});
    renderAll();
  }
  function addFiles(files){
    files=files.filter(Boolean);if(!files.length)return;
    // Fill empty rows first (top to bottom); with no empty row, start over from row 1.
    var slots=[];for(var i=0;i<3;i++)if(!S.sources[i])slots.push(i);
    if(!slots.length)slots=[0,1,2];
    var needed=0;files.slice(0,slots.length).forEach(function(file,k){needed=Math.max(needed,slots[k]+1);setFile(slots[k],file)});
    if(needed>S.rows){S.rows=needed;renderAll()}
  }
  // Decode once to learn the natural size (crop maths and the overlay canvas need it).
  function probe(source,done){
    var media=document.createElement(source.video?'video':'img');
    function finish(ok){
      source.loading=false;
      if(ok){var w=source.video?media.videoWidth:media.naturalWidth,h=source.video?media.videoHeight:media.naturalHeight;if(w&&h){source.natural={w:w,h:h};centerView(source)}else source.broken=true}
      else source.broken=true;
      if(source.video&&Number.isFinite(media.duration))source.duration=media.duration;
      done();
    }
    if(source.video){media.preload='metadata';media.muted=true;media.onloadedmetadata=function(){finish(true)};media.onerror=function(){finish(false)}}
    else{media.onload=function(){finish(true)};media.onerror=function(){finish(false)}}
    media.src=source.url;
  }
  function moveRow(from,to){if(to<0||to>=S.rows)return;var a=S.sources[from];S.sources[from]=S.sources[to];S.sources[to]=a;S.active=to;renderAll()}
  function removeRow(index){release(S.sources[index]);S.sources[index]=null;renderAll()}

  // ------------------------------------------------------------------ crop maths
  function centerView(source){
    if(!source.natural)return;var n=source.natural,base=Math.max(STRIP.w/n.w,STRIP.h/n.h);
    source.view={base:base,zoom:1,ox:(STRIP.w-n.w*base)/2,oy:(STRIP.h-n.h*base)/2};
  }
  function scaleOf(source){return source.view.base*source.view.zoom}
  function clampView(source){var v=source.view,s=scaleOf(source),n=source.natural;v.ox=Math.min(0,Math.max(STRIP.w-n.w*s,v.ox));v.oy=Math.min(0,Math.max(STRIP.h-n.h*s,v.oy))}
  function zoomTo(source,value,px,py){var v=source.view,before=scaleOf(source);v.zoom=Math.max(1,Math.min(MAX_ZOOM,value));var ratio=scaleOf(source)/before;v.ox=px-(px-v.ox)*ratio;v.oy=py-(py-v.oy)*ratio;clampView(source)}
  function cropArea(source){var v=source.view,s=scaleOf(source),n=source.natural;return{x:-v.ox/s/n.w,y:-v.oy/s/n.h,w:STRIP.w/s/n.w,h:STRIP.h/s/n.h}}

  // ------------------------------------------------------------------ header + panel
  function syncHead(){
    intro.textContent=t(squares()?'introSquares':'introRows');
    typeButtons.forEach(function(b){var key=b.dataset.workshopLayout,on=key===S.layout;b.setAttribute('aria-checked',String(on));b.setAttribute('aria-pressed',String(on));b.querySelector('.wsx-type__name').textContent=t(key==='rows'?'typeRows':'typeSquares');b.querySelector('.wsx-type__hint').textContent=t(key==='rows'?'typeRowsHint':'typeSquaresHint')});
    rowsLabel.textContent=t('rowsLabel');
    countButtons.forEach(function(b,i){var on=i+1===S.rows;b.setAttribute('aria-checked',String(on));b.setAttribute('aria-pressed',String(on));b.title=t('rowsLabel')+': '+(i+1)});
    root.dataset.layout=S.layout;
  }
  function syncTabs(){
    tabKeys.forEach(function(key){
      var b=tabButtons[key],on=S.panel===key;b.setAttribute('aria-selected',String(on));b.classList.toggle('is-active',on);
      b.querySelector('.wsx-tab__name').textContent=t(key==='files'?'tabFiles':key==='frame'?(squares()?'tabFrameFx':'tabFrame'):key==='color'?'tabColor':'tabMotion');
      var dot=b.querySelector('.wsx-tab__dot'),mark='';
      if(key==='files')mark=active().filter(Boolean).length+'/'+S.rows;
      if(key==='frame'&&FX&&!FX.isEmpty(fx()))mark='•';
      if(key==='color'&&active().some(graded))mark='•';
      if(key==='motion'&&moving())mark='GIF';
      dot.textContent=mark;dot.hidden=!mark;
    });
  }
  function renderPanel(){
    panelBody.replaceChildren();panelBody.dataset.panel=S.panel;
    if(S.panel==='files')renderFiles();
    else if(S.panel==='frame')renderFrame();
    else if(S.panel==='color')renderColor();
    else renderMotion();
  }
  function rowLabel(index){return t('row',{n:index+1})}
  function renderFiles(){
    var list=el('div','wsx-files');
    for(var index=0;index<S.rows;index++)(function(row){
      var source=S.sources[row],card=el('div','wsx-file'+(row===S.active?' is-active':'')+(source?'':' is-empty'));
      card.dataset.row=String(row);
      dropTarget(card,row);
      if(!source){
        var pick=button('wsx-file__drop',null,function(){S.active=row;choose(row)});
        pick.append(icon('upload'),el('b',null,rowLabel(row)),el('span',null,t('dropTitle')),el('small',null,t('dropHint')));
        card.append(pick);list.append(card);return;
      }
      var thumb=el('div','wsx-file__thumb');
      if(!source.broken){var media=el(source.video?'video':'img');media.src=source.url;if(source.video){media.muted=true;media.preload='metadata'}else media.alt='';media.style.filter=gradeFilter(source);thumb.append(media)}
      var info=el('button','wsx-file__info');info.type='button';info.addEventListener('click',function(){S.active=row;renderAll()});
      var meta=[suffixOf(source.file).toUpperCase(),bytes(source.file.size)];if(source.natural)meta.splice(1,0,source.natural.w+'×'+source.natural.h);
      info.append(el('small',null,rowLabel(row)+(row===S.active&&S.rows>1?' · '+t('active'):'')),el('strong',null,source.file.name),el('span',null,source.loading?t('loading'):meta.join(' · ')));
      var tools=el('div','wsx-file__tools');
      if(S.rows>1){var up=button('wsx-mini',null,function(){moveRow(row,row-1)});up.append(icon('up'));up.title=up.ariaLabel=t('moveUp');up.disabled=row===0;
        var down=button('wsx-mini',null,function(){moveRow(row,row+1)});down.append(icon('down'));down.title=down.ariaLabel=t('moveDown');down.disabled=row===S.rows-1;tools.append(up,down)}
      var replace=button('wsx-mini',null,function(){choose(row)});replace.append(icon('upload'));replace.title=replace.ariaLabel=t('replace');
      var remove=button('wsx-mini wsx-mini--danger',null,function(){removeRow(row)});remove.append(icon('x'));remove.title=remove.ariaLabel=t('remove');
      tools.append(replace,remove);
      card.append(thumb,info,tools);
      if(source.broken)card.append(el('p','wsx-file__warn',t(squares()?'cannotCrop':'noPreview')));
      list.append(card);
    })(index);
    panelBody.append(list);
    if(S.rows>1&&active().some(function(source){return !source})){var many=button('wsx-ghost',null,function(){multiPicker.click()});many.append(icon('plus'),el('span',null,t('addMany')));panelBody.append(many)}
    var source=S.sources[S.active];
    if(squares()&&source&&source.view&&S.active<S.rows){
      var area=el('div','wsx-area');area.append(el('p','wsx-label',t('area',{n:S.active+1})),mapCanvas(),el('p','wsx-help',t('areaHint')));panelBody.append(area);drawMap();
    }
  }
  function renderFrame(){
    if(!FX){panelBody.append(el('p','wsx-help','—'));return}
    var host=el('div','wsx-fx');panelBody.append(host);
    if(!squares())panelBody.prepend(el('p','wsx-help wsx-help--top',t('frameRows')));
    FX.mountControls(host,fx(),language(),function(){fxDirty=true;syncTabs();updateSummary();kick()},{frameOnly:!squares()});
  }
  function renderColor(){
    if(S.rows>1){var chips=el('div','wsx-chips');for(var i=0;i<S.rows;i++)(function(row){var b=button('wsx-chip'+(row===S.active?' is-active':''),rowLabel(row),function(){S.active=row;renderAll()});b.disabled=!S.sources[row];chips.append(b)})(i);panelBody.append(chips)}
    var source=S.sources[S.active];
    panelBody.append(el('p','wsx-label',t('colorFor',{n:S.active+1})));
    if(!source){panelBody.append(el('p','wsx-help',t('colorEmpty')));return}
    var grid=el('div','wsx-sliders');
    Object.keys(LIMITS).forEach(function(key){
      var label=el('label','wsx-slider'),name=el('span',null,t(key)),value=el('output'),input=el('input');
      input.type='range';input.min=LIMITS[key][0];input.max=LIMITS[key][1];input.value=gradeOf(source)[key];
      function show(){value.textContent=input.value+(key==='hue'?'°':'%')}
      input.addEventListener('input',function(){source.grade=Object.assign(gradeOf(source),{[key]:Number(this.value)});show();applyGrade(S.active);syncTabs()});
      input.addEventListener('dblclick',function(){input.value=LIMITS[key][2];input.dispatchEvent(new Event('input'))});
      show();label.append(name,value,input);grid.append(label);
    });
    panelBody.append(grid);
    var actions=el('div','wsx-actions');
    actions.append(button('wsx-ghost',t('resetColor'),function(){source.grade=gradeOf(null);applyGrade(S.active);renderPanel();syncTabs()}));
    if(S.rows>1)actions.append(button('wsx-ghost',t('applyAll'),function(){active().forEach(function(other,row){if(other){other.grade=Object.assign({},source.grade);applyGrade(row)}});syncTabs();setStatus('','')}));
    panelBody.append(actions);
  }
  function renderMotion(){
    panelBody.append(el('p','wsx-note'+(moving()?' is-on':''),t(moving()?'motionAnimated':'motionStatic')));
    var grid=el('div','wsx-fields');
    grid.append(selectField('fps',t('fps'),[12,15,24],S.fps,function(v){S.fps=v}),selectField('duration',t('duration'),[4,6,8],S.duration,function(v){S.duration=v;kick()},' s'));
    panelBody.append(grid);
    active().forEach(function(source,row){
      if(!source||!source.video)return;
      var label=el('label','wsx-field'),name=el('span',null,t('start',{n:row+1})),input=el('input');input.type='number';input.min='0';input.step='0.1';input.max=String(Math.max(0,source.duration||600));input.value=String(source.start||0);
      input.addEventListener('change',function(){source.start=Math.max(0,Math.min(Number(input.max),Number(this.value)||0));this.value=String(source.start);seekRow(row)});
      label.append(name,input);panelBody.append(label);
    });
  }
  function selectField(id,label,values,current,onChange,suffix){
    var wrap=el('label','wsx-field'),name=el('span',null,label),select=el('select');select.id=id==='fps'?'workshopFps':'workshopDuration';
    values.forEach(function(v){var option=el('option',null,v+(suffix||''));option.value=String(v);option.selected=v===current;select.append(option)});
    select.addEventListener('change',function(){onChange(Number(this.value))});wrap.append(name,select);return wrap;
  }

  // ------------------------------------------------------------------ minimap (squares)
  var map=null,mapDrag=null;
  function mapCanvas(){
    map=el('canvas','wsx-map');map.width=640;map.height=300;map.setAttribute('aria-hidden','true');
    map.addEventListener('pointerdown',function(event){var source=S.sources[S.active];if(!source||!source.view)return;mapDrag={x:event.clientX,y:event.clientY,id:event.pointerId};map.setPointerCapture(event.pointerId)});
    map.addEventListener('pointermove',function(event){
      var source=S.sources[S.active];if(!mapDrag||event.pointerId!==mapDrag.id||!source||!source.view)return;
      var layout=mapLayout(source),k=map.width/map.clientWidth,dx=(event.clientX-mapDrag.x)*k/layout.scale,dy=(event.clientY-mapDrag.y)*k/layout.scale,s=scaleOf(source);
      source.view.ox-=dx*s;source.view.oy-=dy*s;clampView(source);mapDrag.x=event.clientX;mapDrag.y=event.clientY;placeRow(S.active);drawMap();
    });
    map.addEventListener('pointerup',function(){mapDrag=null});map.addEventListener('pointercancel',function(){mapDrag=null});
    return map;
  }
  function mapLayout(source){var n=source.natural,scale=Math.min(map.width/n.w,map.height/n.h);return{scale:scale,x:(map.width-n.w*scale)/2,y:(map.height-n.h*scale)/2,w:n.w*scale,h:n.h*scale}}
  function drawMap(){
    if(!map||!map.isConnected)return;var source=S.sources[S.active],ctx=map.getContext('2d');ctx.clearRect(0,0,map.width,map.height);
    if(!source||!source.view)return;var r=runtime[S.active],media=r&&(r.video||r.still);if(!media)return;
    var L=mapLayout(source);ctx.save();ctx.filter=gradeFilter(source);try{ctx.drawImage(media,L.x,L.y,L.w,L.h)}catch(_){}ctx.restore();
    var c=cropArea(source),x=L.x+c.x*L.w,y=L.y+c.y*L.h,w=c.w*L.w,h=c.h*L.h;
    ctx.fillStyle='rgba(3,7,16,.66)';ctx.beginPath();ctx.rect(0,0,map.width,map.height);ctx.rect(x,y,w,h);ctx.fill('evenodd');
    ctx.strokeStyle='#5fe4ff';ctx.lineWidth=3;ctx.strokeRect(x,y,w,h);ctx.strokeStyle='rgba(95,228,255,.55)';ctx.lineWidth=1.5;
    for(var i=1;i<5;i++){ctx.beginPath();ctx.moveTo(x+w*i/5,y);ctx.lineTo(x+w*i/5,y+h);ctx.stroke()}
  }

  // ------------------------------------------------------------------ Steam preview
  function dropTarget(node,row){
    node.addEventListener('dragover',function(event){if(!event.dataTransfer||Array.from(event.dataTransfer.types||[]).indexOf('Files')<0)return;event.preventDefault();node.classList.add('is-dragover')});
    node.addEventListener('dragleave',function(){node.classList.remove('is-dragover')});
    node.addEventListener('drop',function(event){event.preventDefault();node.classList.remove('is-dragover');var files=Array.from(event.dataTransfer.files||[]);if(files.length>1)addFiles(files);else if(files[0])setFile(row,files[0])});
  }
  function renderStage(){
    stageTitle.textContent=t('previewTitle');stageHint.textContent=t(squares()?'previewSquares':'previewRows');
    stageFoot.textContent=t('autoHex');zoomName.textContent=t('zoom');zoomReset.title=zoomReset.ariaLabel=t('reset');zoomRange.setAttribute('aria-label',t('zoom'));
    runtime.forEach(function(r){if(r&&r.video){r.video.pause();r.video.removeAttribute('src');r.video.load()}});
    runtime=[];profile.replaceChildren();profile.classList.toggle('is-squares',squares());
    for(var index=0;index<S.rows;index++)profile.append(showcase(index));
    syncZoom();drawMap();fxDirty=true;kick();
  }
  function showcase(row){
    var source=S.sources[row],block=el('article','wsx-show'+(row===S.active?' is-active':'')),top=el('div','wsx-show__head'),content=el('div','wsx-show__body');
    block.dataset.row=String(row);
    top.append(el('span','wsx-show__title',t('showcase')),el('span','wsx-show__tag',rowLabel(row)));
    block.append(top,content);dropTarget(block,row);
    block.addEventListener('pointerdown',function(){if(S.active!==row){S.active=row;syncActive()}},true);
    var r={block:block,tiles:[],overlay:null,video:null,still:null};runtime[row]=r;
    if(!source||source.broken&&squares()){
      var empty=button('wsx-show__empty'+(squares()?' is-squares':''),null,function(){S.active=row;choose(row)});
      if(squares()){var ghost=el('span','wsx-ghost-squares');for(var g=0;g<5;g++)ghost.append(el('i'));empty.append(ghost)}
      empty.append(icon('upload'),el('span',null,source?t('cannotCrop'):t('emptyRow',{n:row+1})));content.append(empty);return block;
    }
    if(source.loading){content.append(el('div','wsx-show__loading',t('loading')));return block}
    if(squares())buildSquares(row,source,content,r);else buildRow(row,source,content,r);
    return block;
  }
  // A full-height row is shown the way Steam shows a Workshop row: five columns of the
  // file (width / 5 each) with Steam's gaps between them. The frame is drawn on the
  // whole file (r.overlay) and each column shows its slice.
  function buildRow(row,source,content,r){
    if(source.broken){var box=el('div','wsx-rowmedia');box.append(el('div','wsx-show__loading',t('noPreview')));content.append(box);return}
    var n=source.natural,H=Math.max(2,Math.round(ROW_W*n.h/n.w)),grid=el('div','wsx-sq wsx-sq--rows');
    grid.style.setProperty('--wsx-col',(ROW_W/5)+' / '+H);
    if(source.video){var hidden=el('video','wsx-sq__source');hidden.muted=true;hidden.loop=true;hidden.autoplay=true;hidden.playsInline=true;hidden.preload='auto';hidden.src=source.url;r.video=hidden;hidden.addEventListener('loadedmetadata',function(){if(source.start)hidden.currentTime=Math.min(source.start,hidden.duration||0)});content.append(hidden)}
    for(var i=0;i<5;i++){
      var tile=el('div','wsx-sq__tile'),media;
      if(source.video){media=el('canvas','wsx-sq__media');media.width=ROW_W/5;media.height=H}
      else{media=el('img','wsx-sq__media wsx-sq__media--col');media.src=source.url;media.alt='';media.draggable=false;media.style.left=(-i*100)+'%';media.style.filter=gradeFilter(source);if(!i)r.still=media}
      var over=el('canvas','wsx-sq__fx');over.width=ROW_W/5;over.height=H;
      tile.append(media,over);grid.append(tile);r.tiles.push({tile:tile,media:media,fx:over});
    }
    var overlay=document.createElement('canvas');overlay.width=ROW_W;overlay.height=H;r.overlay=overlay;
    content.append(grid);
  }
  function buildSquares(row,source,content,r){
    var strip=el('div','wsx-sq');strip.tabIndex=0;strip.setAttribute('role','application');strip.setAttribute('aria-label',rowLabel(row)+'. '+t('previewSquares'));
    var hidden=null;
    if(source.video){hidden=el('video','wsx-sq__source');hidden.muted=true;hidden.loop=true;hidden.autoplay=true;hidden.playsInline=true;hidden.preload='auto';hidden.src=source.url;r.video=hidden;hidden.addEventListener('loadedmetadata',function(){if(source.start)hidden.currentTime=Math.min(source.start,hidden.duration||0)});content.append(hidden)}
    else{var still=new Image();still.onload=function(){if(row===S.active)drawMap()};still.src=source.url;r.still=still}
    for(var i=0;i<5;i++){
      var tile=el('div','wsx-sq__tile'),media;
      if(source.video){media=el('canvas','wsx-sq__media');media.width=media.height=SQ*2}
      else{media=el('img','wsx-sq__media');media.src=source.url;media.alt='';media.draggable=false;media.style.filter=gradeFilter(source)}
      var over=el('canvas','wsx-sq__fx');over.width=over.height=SQ;
      tile.append(media,over);strip.append(tile);r.tiles.push({tile:tile,media:media,fx:over});
    }
    content.append(strip);
    attachDrag(strip,row,source);
    if(window.ResizeObserver){var observer=new ResizeObserver(function(){placeRow(row)});observer.observe(strip);r.observer=observer}
    requestAnimationFrame(function(){placeRow(row)});
  }
  function placeRow(row){
    if(!squares())return;
    var r=runtime[row],source=S.sources[row];if(!r||!source||!source.view||!r.tiles.length)return;
    var tw=r.tiles[0].tile.clientWidth;if(!tw)return;var k=tw/SQ,s=scaleOf(source),n=source.natural;
    r.tiles.forEach(function(item,i){
      if(item.media.tagName==='IMG'){var st=item.media.style;st.width=n.w*s*k+'px';st.height=n.h*s*k+'px';st.left=(source.view.ox-i*SQ)*k+'px';st.top=source.view.oy*k+'px'}
    });
    if(r.video)paintVideoTiles(row);
  }
  function paintVideoTiles(row){
    var r=runtime[row],source=S.sources[row];if(!r||!r.video||!source||r.video.readyState<2)return;
    if(!squares()){var vw=r.video.videoWidth,vh=r.video.videoHeight;r.tiles.forEach(function(item,i){var c=item.media,ctx=c.getContext('2d');ctx.save();ctx.filter=gradeFilter(source);ctx.clearRect(0,0,c.width,c.height);try{ctx.drawImage(r.video,i*vw/5,0,vw/5,vh,0,0,c.width,c.height)}catch(_){}ctx.restore()});return}
    if(!source.view)return;var s=scaleOf(source),v=source.view;
    r.tiles.forEach(function(item,i){var ctx=item.media.getContext('2d'),size=item.media.width;ctx.save();ctx.filter=gradeFilter(source);ctx.clearRect(0,0,size,size);try{ctx.drawImage(r.video,(i*SQ-v.ox)/s,-v.oy/s,SQ/s,SQ/s,0,0,size,size)}catch(_){}ctx.restore()});
  }
  function attachDrag(strip,row,source){
    var drag=null;
    function k(){var r=runtime[row];return r&&r.tiles[0]?r.tiles[0].tile.clientWidth/SQ:1}
    strip.addEventListener('pointerdown',function(event){if(!source.view||event.button>0)return;drag={x:event.clientX,y:event.clientY,id:event.pointerId};strip.setPointerCapture(event.pointerId);strip.classList.add('is-dragging')});
    strip.addEventListener('pointermove',function(event){if(!drag||event.pointerId!==drag.id)return;var unit=k();source.view.ox+=(event.clientX-drag.x)/unit;source.view.oy+=(event.clientY-drag.y)/unit;drag.x=event.clientX;drag.y=event.clientY;clampView(source);placeRow(row);if(row===S.active)drawMap()});
    function end(){drag=null;strip.classList.remove('is-dragging')}
    strip.addEventListener('pointerup',end);strip.addEventListener('pointercancel',end);
    strip.addEventListener('wheel',function(event){
      if(!source.view)return;event.preventDefault();if(S.active!==row){S.active=row;syncActive()}
      var rect=strip.getBoundingClientRect(),unit=rect.width/STRIP.w;zoomTo(source,source.view.zoom*Math.exp(-event.deltaY*0.0015),(event.clientX-rect.left)/unit,(event.clientY-rect.top)/unit);placeRow(row);syncZoom();drawMap();
    },{passive:false});
    strip.addEventListener('keydown',function(event){
      if(!source.view)return;var step=event.shiftKey?30:8,keys={ArrowLeft:[step,0],ArrowRight:[-step,0],ArrowUp:[0,step],ArrowDown:[0,-step]};
      if(keys[event.key]){event.preventDefault();source.view.ox+=keys[event.key][0];source.view.oy+=keys[event.key][1];clampView(source)}
      else if(event.key==='+'||event.key==='='){event.preventDefault();zoomTo(source,source.view.zoom*1.1,STRIP.w/2,STRIP.h/2)}
      else if(event.key==='-'){event.preventDefault();zoomTo(source,source.view.zoom/1.1,STRIP.w/2,STRIP.h/2)}
      else return;
      placeRow(row);syncZoom();drawMap();
    });
    strip.addEventListener('dblclick',function(){centerView(source);placeRow(row);syncZoom();drawMap()});
  }
  function syncZoom(){
    var source=S.sources[S.active],show=squares()&&!!(source&&source.view)&&S.active<S.rows;
    zoomBox.hidden=!show;if(show)zoomRange.value=String(source.view.zoom);
  }
  function syncActive(){
    profile.querySelectorAll('.wsx-show').forEach(function(node){node.classList.toggle('is-active',Number(node.dataset.row)===S.active)});
    syncZoom();if(S.panel==='files'||S.panel==='color')renderPanel();
  }
  function applyGrade(row){
    var source=S.sources[row],r=runtime[row];if(!r)return;var filter=gradeFilter(source);
    r.block.querySelectorAll('.wsx-sq__media').forEach(function(node){if(node.tagName!=='CANVAS')node.style.filter=filter});
    if(r.video)paintVideoTiles(row);
    panelBody.querySelectorAll('.wsx-file[data-row="'+row+'"] .wsx-file__thumb>*').forEach(function(node){node.style.filter=filter});
    if(row===S.active)drawMap();
  }
  function seekRow(row){var r=runtime[row],source=S.sources[row];if(r&&r.video&&source)try{r.video.currentTime=Math.min(source.start||0,r.video.duration||0)}catch(_){}}

  // Frames/effects overlay: squares share one 750x150 loop; rows get a frame per file.
  function paintFx(u){
    if(!FX)return;
    if(squares()){
      if(!fxStrip){fxStrip=document.createElement('canvas');fxStrip.width=STRIP.w;fxStrip.height=STRIP.h}
      FX.render(fxStrip.getContext('2d'),u,S.fxSquares);
      runtime.forEach(function(r){if(!r)return;r.tiles.forEach(function(item,i){var ctx=item.fx.getContext('2d');ctx.clearRect(0,0,SQ,SQ);ctx.drawImage(fxStrip,i*SQ,0,SQ,SQ,0,0,SQ,SQ)})});
      return;
    }
    var frame=rowFrame();
    runtime.forEach(function(r){
      if(!r||!r.overlay)return;var c=r.overlay,ctx=c.getContext('2d');ctx.clearRect(0,0,c.width,c.height);if(frame)FX.drawFrame(ctx,u,frame,[[0,0,c.width,c.height,'full']]);
      var w=c.width/5;r.tiles.forEach(function(item,i){var tc=item.fx.getContext('2d');tc.clearRect(0,0,item.fx.width,item.fx.height);tc.drawImage(c,i*w,0,w,c.height,0,0,item.fx.width,item.fx.height)});
    });
  }
  function visible(){return !!root.offsetParent&&!document.hidden}
  function kick(){if(!loop)loop=requestAnimationFrame(tick)}
  function tick(now){
    loop=0;if(!visible())return;
    var animated=frameAnimated(),videos=runtime.some(function(r){return r&&r.video});
    if(now-lastPaint>=33||fxDirty){
      lastPaint=now;
      if(animated||fxDirty){paintFx(((now/1000)%S.duration)/S.duration);fxDirty=false}
      runtime.forEach(function(r,row){if(r&&r.video)paintVideoTiles(row)});
      var current=runtime[S.active];if(squares()&&current&&current.video)drawMap();
    }
    if(animated||videos)kick();
  }

  // ------------------------------------------------------------------ summary + start
  function updateSummary(){
    var ready=active().every(function(source){return source&&!source.loading&&!(squares()&&!source.view)});
    var format=moving()?'GIF':'PNG';
    summary.textContent=t('summary',{rows:S.rows,files:fileCount(),format:format});
    zipNote.textContent=squares()&&S.rows>1?t('zipFolders',{n:S.rows}):'';zipNote.hidden=!zipNote.textContent;
    planNote.textContent=t(squares()?'freeSquares':'freeRows');planNote.hidden=S.pro!==false;
    if(extrasBox)extrasBox.el.hidden=!squares();
    create.textContent=t('create');download.textContent=t('download');
    create.disabled=S.busy||!ready;
  }
  function renderAll(){syncHead();syncTabs();renderPanel();renderStage();updateSummary()}
  function refreshPlan(){fetch('/api/quota',{credentials:'same-origin',cache:'no-store'}).then(function(response){return response.ok?response.json():null}).then(function(data){if(data){S.pro=!!data.pro;updateSummary()}}).catch(function(){})}
  function wait(ms){return new Promise(function(resolve){setTimeout(resolve,ms)})}
  async function poll(jid){
    for(var attempt=0;attempt<360;attempt++){
      await wait(1500);
      var response=await fetch('/api/process/status/'+encodeURIComponent(jid),{credentials:'same-origin',cache:'no-store'}),result=await response.json();
      if(!response.ok||!result.ok)throw Error(result.msg||t('error'));
      progress.value=Number(result.pct)||0;
      if(result.status==='done')return result;
      if(result.status==='error'||result.status==='cancelled')throw Error(result.error||t('error'));
      setStatus(t('processing')+' '+progress.value+'%','wait');
    }
    throw Error(t('error'));
  }
  async function start(){
    var list=active();if(S.busy)return;
    if(list.some(function(source){return !source||(squares()&&!source.view)})){setStatus(t('missing'),'bad');S.panel='files';renderPanel();syncTabs();return}
    if(list.reduce(function(total,source){return total+source.file.size},0)>95*1024*1024){setStatus(t('totalLimit'),'bad');return}
    // Moving output: Standard or Maximum quality (encode-choice.js); stills skip the question.
    var profile=window.SMEncodeChoice?await SMEncodeChoice.ask({animated:moving()}):'standard';
    if(!profile||S.busy)return;
    S.busy=true;updateSummary();progress.hidden=false;progress.value=0;download.hidden=true;setStatus(t('uploading'),'wait');root.classList.add('is-busy');
    if(S.downloadUrl){URL.revokeObjectURL(S.downloadUrl);S.downloadUrl=''}
    try{
      var form=new FormData();
      form.append('layout',S.layout);form.append('rows',String(S.rows));form.append('fps',String(S.fps));form.append('duration',String(S.duration));form.append('outline','0');
      form.append('settings',JSON.stringify(list.map(function(source){return Object.assign({start:source.start||0},gradeOf(source))})));
      if(squares())form.append('crops',JSON.stringify(list.map(cropArea)));
      if(FX)form.append('fx',JSON.stringify(squares()?S.fxSquares:{frame:Object.assign({},S.fxRows.frame,{target:'strip'}),effect:{type:'none'}}));
      if(window.SMEncodeChoice)SMEncodeChoice.append(form,profile,squares()&&extrasBox?extrasBox.get():{original:false,preview:false});
      list.forEach(function(source){form.append('files',source.file)});
      var response=await fetch('/api/workshop-studio/start',{method:'POST',credentials:'same-origin',body:form}),result=await response.json();
      if(!response.ok||!result.ok)throw Error(result.msg||t('error'));
      var finished=await poll(result.job_id);
      var archive=await fetch('/api/process/download/'+encodeURIComponent(result.job_id),{credentials:'same-origin'});if(!archive.ok)throw Error(t('error'));
      S.downloadUrl=URL.createObjectURL(await archive.blob());download.href=S.downloadUrl;download.download=squares()?'workshop-squares.zip':'workshop-rows.zip';download.hidden=false;download.click();
      setStatus(t('done')+(finished&&finished.saved_days&&window.WorkspaceEditorCopy?' '+WorkspaceEditorCopy('savedNote',{days:finished.saved_days}):''),'ok');
    }catch(error){setStatus(error.message||t('error'),'bad')}
    finally{S.busy=false;progress.hidden=true;root.classList.remove('is-busy');updateSummary()}
  }

  // ------------------------------------------------------------------ wiring
  var tabButton=document.querySelector('#nav button[data-tab="workshop"]');
  if(tabButton)tabButton.addEventListener('click',function(){refreshPlan();requestAnimationFrame(function(){runtime.forEach(function(r,row){placeRow(row)});fxDirty=true;kick()})});
  window.addEventListener('sm:langchange',renderAll);
  document.addEventListener('visibilitychange',function(){if(!document.hidden){fxDirty=true;kick()}});
  document.addEventListener('sm:frame-designs',function(){fxDirty=true;kick()});
  window.addEventListener('beforeunload',function(){S.sources.forEach(release);if(S.downloadUrl)URL.revokeObjectURL(S.downloadUrl)});
  // Paste an image while this tab is open: it goes to the selected row.
  document.addEventListener('paste',function(event){
    if(!root.offsetParent||S.busy)return;var target=event.target;if(target&&(target.tagName==='INPUT'||target.tagName==='TEXTAREA'||target.isContentEditable))return;
    var file=Array.from((event.clipboardData||{}).files||[])[0];if(file){event.preventDefault();setFile(S.active,file)}
  });
  window.SMWorkshopStudio={state:function(){return{layout:S.layout,rows:S.rows,active:S.active,panel:S.panel,crops:active().map(function(source){return source&&source.view?cropArea(source):null})}},
    setLayout:function(key){if(key==='rows'||key==='squares'){S.layout=key;renderAll()}},setRows:function(n){if(n>=1&&n<=3){S.rows=n;if(S.active>=n)S.active=n-1;renderAll()}},
    setFile:setFile,fx:function(){return fx()}};
  renderAll();refreshPlan();
})();
