"""Public how-to guides for search traffic (/<lang>/guides/<slug>).

Written in all eight site languages (2026-10-08; until then only EN/RU, the rest
showed English with ``noindex``). The steps are the manual route of the site's own
Steam tab (upload page -> console code -> files in order); the SteamShowcase Helper
extension is offered once, calmly, as the easier way (owner: no main focus on it).
"""
from __future__ import annotations

GUIDE_LANGUAGES = ("en", "ru", "de", "tr", "fr", "uk", "es", "pt")

GUIDES: dict[str, dict[str, dict]] = {
    "steam-workshop-showcase": {
        "en": {
            "title": "How to make an animated Steam Workshop showcase (5 panels)",
            "description": "Cut one picture, GIF or video into five synchronized Workshop panels and upload them to your Steam profile, step by step.",
            "intro": "The Workshop showcase shows five items side by side. If the five items are parts of one picture, your profile gets one wide artwork. Showcase Maker cuts the picture for you, keeps animations in sync and keeps every file under the Steam limits.",
            "mode": "workshop",
            "steps": [
                ("Prepare the five parts", "Open Showcase Maker, add your image, GIF or video and choose “Workshop”. The preview shows exactly where each part will be cut. Press “Create Steam files”: you get a ZIP with part_1 … part_5."),
                ("Unpack the ZIP", "Extract the ZIP to a folder. Keep the file names: the number in each name is the order in your profile."),
                ("Open the Steam upload page", "Log in to Steam in your browser and open the artwork upload page (the button “Open Steam page” in the Steam tab of Showcase Maker)."),
                ("Paste the console code", "Press F12, open the Console tab, paste the code from the Steam tab (“Copy code”) and press Enter. It switches the upload form to a Workshop item."),
                ("Upload part_1 … part_5 in order", "Upload the five files one by one, starting with part_1, and repeat the console code before each upload if the page reloads."),
                ("Add them to the showcase", "Open your profile → Edit Profile → Featured Showcase, choose “Workshop Showcase” and select the five items in the same order."),
            ],
            "faq": [
                ("Why does Steam reject my file?", "Steam checks the size and the last byte of uploaded artwork. Showcase Maker fits animated files under 5 MB and adds the required ending byte (HEX 21) automatically."),
                ("The parts do not line up", "Upload and select them strictly in order: part_1 is the leftmost panel. All five GIFs are encoded as one group so they stay in sync."),
                ("I have no showcases on my profile", "Steam gives the first showcase at profile level 10."),
            ],
        },
        "ru": {
            "title": "Как сделать анимированную витрину мастерской Steam (5 частей)",
            "description": "Нарежь одну картинку, GIF или видео на пять синхронных частей Workshop и загрузи их в профиль Steam — пошагово.",
            "intro": "Витрина мастерской показывает пять элементов в ряд. Если эти пять элементов — части одной картинки, в профиле получается одна широкая иллюстрация. Showcase Maker сам нарежет изображение, синхронизирует анимацию и уложит каждый файл в лимиты Steam.",
            "mode": "workshop",
            "steps": [
                ("Подготовь пять частей", "Открой Showcase Maker, добавь картинку, GIF или видео и выбери «Мастерская». Предпросмотр сразу показывает, где пройдёт разрез. Нажми «Подготовить витрину» — получишь ZIP с part_1 … part_5."),
                ("Распакуй ZIP", "Распакуй архив в папку. Не переименовывай файлы: номер в имени — это порядок в профиле."),
                ("Открой страницу загрузки Steam", "Войди в Steam в браузере и открой страницу загрузки иллюстраций (кнопка «Открыть страницу Steam» во вкладке Steam на сайте)."),
                ("Вставь код в консоль", "Нажми F12, открой вкладку Console, вставь код из вкладки Steam («Копировать код») и нажми Enter. Код переключает форму на элемент мастерской."),
                ("Загрузи part_1 … part_5 по порядку", "Загружай файлы по одному, начиная с part_1. Если страница перезагрузилась, вставь код в консоль ещё раз перед следующей загрузкой."),
                ("Добавь их в витрину", "Открой профиль → «Редактировать профиль» → «Витрина», выбери «Витрина мастерской» и отметь пять элементов в том же порядке."),
            ],
            "faq": [
                ("Почему Steam не принимает файл?", "Steam проверяет размер и последний байт загружаемой иллюстрации. Showcase Maker ужимает анимацию до 5 МБ и сам добавляет нужный последний байт (HEX 21)."),
                ("Части не совпадают по краям", "Загружай и выбирай их строго по порядку: part_1 — самая левая. Все пять GIF кодируются одной группой, поэтому анимация синхронна."),
                ("В профиле нет витрин", "Первую витрину Steam даёт на 10 уровне профиля."),
            ],
        },
    },
    "steam-featured-artwork-gif": {
        "en": {
            "title": "How to upload an animated GIF to the Steam Featured Artwork showcase",
            "description": "Make a 630 px wide Featured Artwork GIF under 5 MB and put it on your Steam profile.",
            "intro": "The Featured Artwork showcase shows one large picture. It is the easiest way to put an animated GIF on your profile — as long as the file has the right width and fits the Steam limits.",
            "mode": "featured",
            "steps": [
                ("Create the file", "In Showcase Maker add your image, GIF or video and choose “One large artwork”. The result is featured_630: 630 px wide, animation kept, under 5 MB."),
                ("Open the Steam upload page", "Log in to Steam in your browser and open the artwork upload page from the Steam tab of Showcase Maker."),
                ("Paste the console code", "Press F12 → Console, paste the code for Featured from the Steam tab and press Enter."),
                ("Upload featured_630", "Choose featured_630.gif (or .png), give it a title and upload it."),
                ("Select it in your profile", "Open Edit Profile → Featured Showcase, choose “Featured Artwork Showcase” and pick the uploaded artwork."),
            ],
            "faq": [
                ("My GIF does not move on the profile", "Steam shows a still preview for files that are too large. Keep the file under 5 MB — Showcase Maker does this automatically."),
                ("Can I use a video?", "Yes. MP4 and WebM are converted to a looping GIF; the Loop tool can make the ending seamless."),
            ],
        },
        "ru": {
            "title": "Как загрузить анимированный GIF в витрину «Избранная иллюстрация» Steam",
            "description": "Сделай GIF шириной 630 px до 5 МБ для витрины Featured Artwork и поставь его в профиль Steam.",
            "intro": "Витрина избранной иллюстрации показывает одну большую картинку. Это самый простой способ поставить анимированный GIF в профиль — если у файла правильная ширина и он укладывается в лимиты Steam.",
            "mode": "featured",
            "steps": [
                ("Создай файл", "В Showcase Maker добавь картинку, GIF или видео и выбери «Избранная иллюстрация». Получится featured_630: 630 px в ширину, с анимацией, до 5 МБ."),
                ("Открой страницу загрузки Steam", "Войди в Steam в браузере и открой страницу загрузки иллюстраций из вкладки Steam на сайте."),
                ("Вставь код в консоль", "Нажми F12 → Console, вставь код для Featured из вкладки Steam и нажми Enter."),
                ("Загрузи featured_630", "Выбери featured_630.gif (или .png), задай название и загрузи."),
                ("Выбери её в профиле", "Открой «Редактировать профиль» → «Витрина», выбери «Избранная иллюстрация» и отметь загруженную работу."),
            ],
            "faq": [
                ("GIF в профиле не двигается", "Для слишком больших файлов Steam показывает статичную картинку. Держи файл до 5 МБ — Showcase Maker делает это сам."),
                ("Можно ли использовать видео?", "Да. MP4 и WebM превращаются в зацикленный GIF, а инструмент «Зациклить» сделает стык незаметным."),
            ],
        },
    },
    "steam-artwork-showcase-split": {
        "en": {
            "title": "How to make a Steam Artwork showcase with a side panel (506 + 100)",
            "description": "Split one picture into the 506 px main image and the 100 px side panel of the Steam Artwork showcase.",
            "intro": "The Artwork showcase has a large image and a narrow column next to it. When both come from one picture, they form a single wide artwork. Showcase Maker cuts the 506 px and 100 px parts so they meet exactly.",
            "mode": "split",
            "steps": [
                ("Create the two parts", "In Showcase Maker add your image, GIF or video and choose “Artwork + side panel”. You get center_506 and side_100; animations stay in sync."),
                ("Open the Steam upload page", "Log in to Steam in your browser and open the artwork upload page from the Steam tab of Showcase Maker."),
                ("Paste the console code", "Press F12 → Console, paste the code for Artwork Split from the Steam tab and press Enter."),
                ("Upload center first, then side", "Upload center_506 first and side_100 second — the order decides which one Steam shows large."),
                ("Select them in your profile", "Open Edit Profile → Featured Showcase, choose “Artwork Showcase” and pick the two uploads."),
            ],
            "faq": [
                ("The side panel is on the wrong side", "Steam places the first selected artwork large. Select center_506 first."),
                ("Can I add a frame?", "Yes: Showcase Maker can draw a frame around each part or around the whole showcase, including animated frames."),
            ],
        },
        "ru": {
            "title": "Как сделать витрину иллюстраций Steam с боковой частью (506 + 100)",
            "description": "Раздели одну картинку на основное изображение 506 px и боковую полосу 100 px для витрины иллюстраций Steam.",
            "intro": "Витрина иллюстраций состоит из большой картинки и узкой колонки рядом. Когда обе части вырезаны из одного изображения, получается одна широкая иллюстрация. Showcase Maker нарежет части 506 px и 100 px так, чтобы они точно стыковались.",
            "mode": "split",
            "steps": [
                ("Создай две части", "В Showcase Maker добавь картинку, GIF или видео и выбери «Витрина иллюстраций». Получишь center_506 и side_100; анимация синхронна."),
                ("Открой страницу загрузки Steam", "Войди в Steam в браузере и открой страницу загрузки иллюстраций из вкладки Steam на сайте."),
                ("Вставь код в консоль", "Нажми F12 → Console, вставь код для Artwork Split из вкладки Steam и нажми Enter."),
                ("Сначала центр, потом бок", "Загрузи сначала center_506, затем side_100 — от порядка зависит, какая часть будет большой."),
                ("Выбери их в профиле", "Открой «Редактировать профиль» → «Витрина», выбери «Витрина иллюстраций» и отметь обе загрузки."),
            ],
            "faq": [
                ("Боковая часть оказалась не с той стороны", "Steam показывает крупно первую выбранную иллюстрацию. Выбирай center_506 первой."),
                ("Можно добавить рамку?", "Да: Showcase Maker рисует рамку вокруг каждой части или вокруг всей витрины, в том числе анимированную."),
            ],
        },
    },
}

# The other six site languages (2026-10-08, owner: guides in every language). Button and showcase-type names are
# the ones the site shows in that language (static/js/workspace-editor-copy.js); Steam's own showcase names stay in
# English quotes, because Steam's translation differs between client versions.
_MORE: dict[str, dict[str, dict]] = {
    "steam-workshop-showcase": {
        "de": {
            "title": "So erstellst du eine animierte Steam-Workshop-Vitrine (5 Teile)",
            "description": "Schneide ein Bild, GIF oder Video in fünf synchrone Workshop-Teile und lade sie Schritt für Schritt in dein Steam-Profil.",
            "intro": "Die Workshop-Vitrine zeigt fünf Elemente nebeneinander. Sind diese fünf Elemente Teile eines Bildes, entsteht im Profil ein breites Artwork. Showcase Maker schneidet das Bild für dich, hält Animationen synchron und bringt jede Datei unter die Steam-Grenzen.",
            "mode": "workshop",
            "steps": [
                ("Die fünf Teile vorbereiten", "Öffne Showcase Maker, füge dein Bild, GIF oder Video hinzu und wähle „Workshop“. Die Vorschau zeigt genau, wo geschnitten wird. Klicke auf „Steam-Dateien erstellen“: Du bekommst ein ZIP mit part_1 … part_5."),
                ("ZIP entpacken", "Entpacke das ZIP in einen Ordner. Benenne die Dateien nicht um: Die Zahl im Namen ist die Reihenfolge im Profil."),
                ("Steam-Uploadseite öffnen", "Melde dich im Browser bei Steam an und öffne die Artwork-Uploadseite (Schaltfläche im Steam-Tab von Showcase Maker)."),
                ("Konsolencode einfügen", "Drücke F12, öffne den Tab „Console“, füge den Code aus dem Steam-Tab ein und drücke Enter. Er stellt das Formular auf ein Workshop-Element um."),
                ("part_1 … part_5 der Reihe nach hochladen", "Lade die fünf Dateien einzeln hoch, beginnend mit part_1. Wird die Seite neu geladen, füge den Code vor dem nächsten Upload erneut ein."),
                ("Zur Vitrine hinzufügen", "Öffne dein Profil → Profil bearbeiten → Vitrine, wähle „Workshop Showcase“ und markiere die fünf Elemente in derselben Reihenfolge."),
            ],
            "faq": [
                ("Warum lehnt Steam meine Datei ab?", "Steam prüft die Größe und das letzte Byte hochgeladener Artworks. Showcase Maker bringt Animationen unter 5 MB und setzt das nötige letzte Byte (HEX 21) automatisch."),
                ("Die Teile passen nicht zusammen", "Lade und wähle sie streng der Reihe nach: part_1 ist ganz links. Alle fünf GIFs werden als eine Gruppe kodiert und laufen synchron."),
                ("In meinem Profil gibt es keine Vitrinen", "Die erste Vitrine gibt Steam ab Profillevel 10."),
            ],
        },
        "tr": {
            "title": "Animasyonlu Steam Atölye vitrini nasıl yapılır (5 parça)",
            "description": "Bir resmi, GIF’i veya videoyu senkron beş Atölye parçasına böl ve adım adım Steam profiline yükle.",
            "intro": "Atölye vitrini beş öğeyi yan yana gösterir. Bu beş öğe tek bir resmin parçalarıysa profilinde geniş tek bir çizim oluşur. Showcase Maker resmi senin için keser, animasyonları senkron tutar ve her dosyayı Steam sınırlarına sığdırır.",
            "mode": "workshop",
            "steps": [
                ("Beş parçayı hazırla", "Showcase Maker’ı aç, resmini, GIF’ini veya videonu ekle ve “Atölye”yi seç. Önizleme kesimin tam yerini gösterir. “Steam dosyalarını oluştur”a bas: part_1 … part_5 içeren bir ZIP alırsın."),
                ("ZIP’i aç", "ZIP’i bir klasöre çıkar. Dosya adlarını değiştirme: addaki sayı profildeki sıradır."),
                ("Steam yükleme sayfasını aç", "Tarayıcında Steam’e giriş yap ve çizim yükleme sayfasını aç (Showcase Maker’daki Steam sekmesindeki düğme)."),
                ("Konsol kodunu yapıştır", "F12’ye bas, Console sekmesini aç, Steam sekmesindeki kodu yapıştır ve Enter’a bas. Kod formu Atölye öğesine çevirir."),
                ("part_1 … part_5’i sırayla yükle", "Beş dosyayı part_1’den başlayarak tek tek yükle. Sayfa yenilenirse sonraki yüklemeden önce kodu tekrar yapıştır."),
                ("Vitrine ekle", "Profilini aç → Profili düzenle → Vitrin, “Workshop Showcase”i seç ve beş öğeyi aynı sırayla işaretle."),
            ],
            "faq": [
                ("Steam dosyamı neden kabul etmiyor?", "Steam yüklenen çizimin boyutunu ve son baytını kontrol eder. Showcase Maker animasyonu 5 MB’ın altına indirir ve gereken son baytı (HEX 21) kendisi ekler."),
                ("Parçalar birbirine oturmuyor", "Onları kesinlikle sırayla yükle ve seç: part_1 en soldadır. Beş GIF tek grup olarak kodlanır, bu yüzden animasyon senkron kalır."),
                ("Profilimde hiç vitrin yok", "Steam ilk vitrini profil seviyesi 10’da verir."),
            ],
        },
        "fr": {
            "title": "Comment créer une vitrine Workshop Steam animée (5 parties)",
            "description": "Découpez une image, un GIF ou une vidéo en cinq parties Workshop synchronisées et envoyez-les sur votre profil Steam, étape par étape.",
            "intro": "La vitrine Workshop affiche cinq éléments côte à côte. Si ces cinq éléments sont les parties d’une même image, votre profil montre une seule grande illustration. Showcase Maker découpe l’image pour vous, garde les animations synchronisées et fait passer chaque fichier sous les limites de Steam.",
            "mode": "workshop",
            "steps": [
                ("Préparer les cinq parties", "Ouvrez Showcase Maker, ajoutez votre image, GIF ou vidéo et choisissez « Workshop ». L’aperçu montre exactement où passe chaque coupe. Cliquez sur « Créer les fichiers Steam » : vous obtenez un ZIP avec part_1 … part_5."),
                ("Décompresser le ZIP", "Extrayez le ZIP dans un dossier. Ne renommez pas les fichiers : le numéro dans le nom est l’ordre sur le profil."),
                ("Ouvrir la page d’envoi Steam", "Connectez-vous à Steam dans le navigateur et ouvrez la page d’envoi d’illustrations (bouton dans l’onglet Steam de Showcase Maker)."),
                ("Coller le code dans la console", "Appuyez sur F12, ouvrez l’onglet Console, collez le code de l’onglet Steam et appuyez sur Entrée. Il transforme le formulaire en élément Workshop."),
                ("Envoyer part_1 … part_5 dans l’ordre", "Envoyez les cinq fichiers un par un en commençant par part_1. Si la page se recharge, recollez le code avant l’envoi suivant."),
                ("Les ajouter à la vitrine", "Ouvrez votre profil → Modifier le profil → Vitrine, choisissez « Workshop Showcase » et sélectionnez les cinq éléments dans le même ordre."),
            ],
            "faq": [
                ("Pourquoi Steam refuse-t-il mon fichier ?", "Steam vérifie la taille et le dernier octet des illustrations envoyées. Showcase Maker fait passer les animations sous 5 Mo et ajoute lui-même le dernier octet requis (HEX 21)."),
                ("Les parties ne s’alignent pas", "Envoyez-les et sélectionnez-les strictement dans l’ordre : part_1 est la plus à gauche. Les cinq GIF sont encodés ensemble, l’animation reste synchronisée."),
                ("Mon profil n’a aucune vitrine", "Steam donne la première vitrine au niveau 10 du profil."),
            ],
        },
        "uk": {
            "title": "Як зробити анімовану вітрину майстерні Steam (5 частин)",
            "description": "Наріж одну картинку, GIF або відео на п’ять синхронних частин майстерні й завантаж їх у профіль Steam — покроково.",
            "intro": "Вітрина майстерні показує п’ять елементів у ряд. Якщо ці п’ять елементів — частини однієї картинки, у профілі виходить одна широка ілюстрація. Showcase Maker сам наріже зображення, синхронізує анімацію й укладе кожен файл у ліміти Steam.",
            "mode": "workshop",
            "steps": [
                ("Підготуй п’ять частин", "Відкрий Showcase Maker, додай картинку, GIF або відео й обери «Майстерня». Попередній перегляд одразу показує, де пройде розріз. Натисни «Підготувати вітрину» — отримаєш ZIP із part_1 … part_5."),
                ("Розпакуй ZIP", "Розпакуй архів у папку. Не перейменовуй файли: номер в імені — це порядок у профілі."),
                ("Відкрий сторінку завантаження Steam", "Увійди в Steam у браузері й відкрий сторінку завантаження ілюстрацій (кнопка у вкладці Steam на сайті)."),
                ("Встав код у консоль", "Натисни F12, відкрий вкладку Console, встав код із вкладки Steam і натисни Enter. Код перемикає форму на елемент майстерні."),
                ("Завантаж part_1 … part_5 по черзі", "Завантажуй файли по одному, починаючи з part_1. Якщо сторінка перезавантажилась, встав код у консоль ще раз перед наступним завантаженням."),
                ("Додай їх у вітрину", "Відкрий профіль → «Редагувати профіль» → «Вітрина», обери «Workshop Showcase» і відміть п’ять елементів у тому самому порядку."),
            ],
            "faq": [
                ("Чому Steam не приймає файл?", "Steam перевіряє розмір і останній байт ілюстрації. Showcase Maker стискає анімацію до 5 МБ і сам додає потрібний останній байт (HEX 21)."),
                ("Частини не збігаються по краях", "Завантажуй і вибирай їх строго по черзі: part_1 — крайня ліва. Усі п’ять GIF кодуються однією групою, тому анімація синхронна."),
                ("У профілі немає вітрин", "Першу вітрину Steam дає на 10 рівні профілю."),
            ],
        },
        "es": {
            "title": "Cómo hacer un escaparate de Workshop animado en Steam (5 partes)",
            "description": "Corta una imagen, GIF o vídeo en cinco partes de Workshop sincronizadas y súbelas a tu perfil de Steam, paso a paso.",
            "intro": "El escaparate de Workshop muestra cinco elementos uno al lado del otro. Si esos cinco elementos son partes de una sola imagen, tu perfil muestra una gran ilustración. Showcase Maker corta la imagen por ti, mantiene las animaciones sincronizadas y deja cada archivo dentro de los límites de Steam.",
            "mode": "workshop",
            "steps": [
                ("Prepara las cinco partes", "Abre Showcase Maker, añade tu imagen, GIF o vídeo y elige «Workshop». La vista previa muestra exactamente dónde se corta. Pulsa «Crear archivos para Steam»: obtienes un ZIP con part_1 … part_5."),
                ("Descomprime el ZIP", "Extrae el ZIP en una carpeta. No cambies los nombres: el número del nombre es el orden en el perfil."),
                ("Abre la página de subida de Steam", "Inicia sesión en Steam en el navegador y abre la página de subida de ilustraciones (botón en la pestaña Steam de Showcase Maker)."),
                ("Pega el código en la consola", "Pulsa F12, abre la pestaña Console, pega el código de la pestaña Steam y pulsa Intro. Cambia el formulario a un elemento de Workshop."),
                ("Sube part_1 … part_5 en orden", "Sube los cinco archivos uno a uno, empezando por part_1. Si la página se recarga, vuelve a pegar el código antes de la siguiente subida."),
                ("Añádelos al escaparate", "Abre tu perfil → Editar perfil → Escaparate, elige «Workshop Showcase» y selecciona los cinco elementos en el mismo orden."),
            ],
            "faq": [
                ("¿Por qué Steam rechaza mi archivo?", "Steam comprueba el tamaño y el último byte de las ilustraciones subidas. Showcase Maker deja las animaciones por debajo de 5 MB y añade solo el último byte necesario (HEX 21)."),
                ("Las partes no encajan", "Súbelas y selecciónalas estrictamente en orden: part_1 es la de la izquierda. Los cinco GIF se codifican como un grupo, así la animación va sincronizada."),
                ("Mi perfil no tiene escaparates", "Steam da el primer escaparate en el nivel 10 del perfil."),
            ],
        },
        "pt": {
            "title": "Como fazer uma vitrine de Oficina animada na Steam (5 partes)",
            "description": "Corte uma imagem, GIF ou vídeo em cinco partes de Oficina sincronizadas e envie para o seu perfil da Steam, passo a passo.",
            "intro": "A vitrine de Oficina mostra cinco itens lado a lado. Se esses cinco itens forem partes de uma mesma imagem, o seu perfil mostra uma única ilustração larga. O Showcase Maker corta a imagem para você, mantém as animações sincronizadas e deixa cada arquivo dentro dos limites da Steam.",
            "mode": "workshop",
            "steps": [
                ("Prepare as cinco partes", "Abra o Showcase Maker, adicione sua imagem, GIF ou vídeo e escolha «Oficina». A prévia mostra exatamente onde cada corte passa. Clique em «Criar arquivos para a Steam»: você recebe um ZIP com part_1 … part_5."),
                ("Descompacte o ZIP", "Extraia o ZIP em uma pasta. Não renomeie os arquivos: o número no nome é a ordem no perfil."),
                ("Abra a página de envio da Steam", "Entre na Steam pelo navegador e abra a página de envio de ilustrações (botão na aba Steam do Showcase Maker)."),
                ("Cole o código no console", "Pressione F12, abra a aba Console, cole o código da aba Steam e pressione Enter. Ele muda o formulário para um item de Oficina."),
                ("Envie part_1 … part_5 em ordem", "Envie os cinco arquivos um por um, começando por part_1. Se a página recarregar, cole o código de novo antes do próximo envio."),
                ("Adicione à vitrine", "Abra seu perfil → Editar perfil → Vitrine, escolha «Workshop Showcase» e selecione os cinco itens na mesma ordem."),
            ],
            "faq": [
                ("Por que a Steam recusa meu arquivo?", "A Steam verifica o tamanho e o último byte das ilustrações enviadas. O Showcase Maker deixa as animações abaixo de 5 MB e adiciona sozinho o último byte necessário (HEX 21)."),
                ("As partes não se encaixam", "Envie e selecione estritamente em ordem: part_1 é a da esquerda. Os cinco GIFs são codificados como um grupo, então a animação fica sincronizada."),
                ("Meu perfil não tem vitrines", "A Steam libera a primeira vitrine no nível 10 do perfil."),
            ],
        },
    },
    "steam-featured-artwork-gif": {
        "de": {
            "title": "So lädst du ein animiertes GIF in die Steam-Vitrine „Featured Artwork“",
            "description": "Erstelle ein 630 px breites Featured-Artwork-GIF unter 5 MB und setze es in dein Steam-Profil.",
            "intro": "Die Featured-Artwork-Vitrine zeigt ein großes Bild. Das ist der einfachste Weg zu einem animierten GIF im Profil — wenn die Datei die richtige Breite hat und in die Steam-Grenzen passt.",
            "mode": "featured",
            "steps": [
                ("Datei erstellen", "Füge in Showcase Maker dein Bild, GIF oder Video hinzu und wähle „Ein großes Artwork“. Ergebnis ist featured_630: 630 px breit, mit Animation, unter 5 MB."),
                ("Steam-Uploadseite öffnen", "Melde dich im Browser bei Steam an und öffne die Artwork-Uploadseite über den Steam-Tab von Showcase Maker."),
                ("Konsolencode einfügen", "Drücke F12 → Console, füge den Code für Featured aus dem Steam-Tab ein und drücke Enter."),
                ("featured_630 hochladen", "Wähle featured_630.gif (oder .png), gib einen Titel ein und lade es hoch."),
                ("Im Profil auswählen", "Öffne Profil bearbeiten → Vitrine, wähle „Featured Artwork Showcase“ und das hochgeladene Artwork."),
            ],
            "faq": [
                ("Mein GIF bewegt sich im Profil nicht", "Bei zu großen Dateien zeigt Steam ein Standbild. Halte die Datei unter 5 MB — Showcase Maker erledigt das automatisch."),
                ("Kann ich ein Video verwenden?", "Ja. MP4 und WebM werden zu einem GIF in Schleife; das Werkzeug „Loop“ macht den Übergang nahtlos."),
            ],
        },
        "tr": {
            "title": "Steam “Featured Artwork” vitrinine animasyonlu GIF nasıl yüklenir",
            "description": "5 MB altında, 630 px genişliğinde bir Featured Artwork GIF’i hazırla ve Steam profiline koy.",
            "intro": "Featured Artwork vitrini tek bir büyük resim gösterir. Profiline animasyonlu GIF koymanın en kolay yolu budur — yeter ki dosyanın genişliği doğru olsun ve Steam sınırlarına sığsın.",
            "mode": "featured",
            "steps": [
                ("Dosyayı oluştur", "Showcase Maker’da resmini, GIF’ini veya videonu ekle ve “Tek büyük çizim”i seç. Sonuç featured_630 olur: 630 px genişlik, animasyonlu, 5 MB altı."),
                ("Steam yükleme sayfasını aç", "Tarayıcında Steam’e giriş yap ve Showcase Maker’ın Steam sekmesinden çizim yükleme sayfasını aç."),
                ("Konsol kodunu yapıştır", "F12 → Console, Steam sekmesindeki Featured kodunu yapıştır ve Enter’a bas."),
                ("featured_630’u yükle", "featured_630.gif’i (veya .png) seç, bir başlık ver ve yükle."),
                ("Profilinde seç", "Profili düzenle → Vitrin’i aç, “Featured Artwork Showcase”i seç ve yüklediğin çizimi işaretle."),
            ],
            "faq": [
                ("GIF profilde hareket etmiyor", "Çok büyük dosyalar için Steam sabit bir resim gösterir. Dosyayı 5 MB altında tut — Showcase Maker bunu kendiliğinden yapar."),
                ("Video kullanabilir miyim?", "Evet. MP4 ve WebM döngüsel GIF’e dönüşür; “Döngü” aracı geçişi kusursuz yapar."),
            ],
        },
        "fr": {
            "title": "Comment mettre un GIF animé dans la vitrine « Featured Artwork » de Steam",
            "description": "Créez un GIF Featured Artwork de 630 px de large sous 5 Mo et placez-le sur votre profil Steam.",
            "intro": "La vitrine Featured Artwork affiche une grande image. C’est le moyen le plus simple de mettre un GIF animé sur votre profil — à condition que le fichier ait la bonne largeur et respecte les limites de Steam.",
            "mode": "featured",
            "steps": [
                ("Créer le fichier", "Dans Showcase Maker, ajoutez votre image, GIF ou vidéo et choisissez « Une grande illustration ». Vous obtenez featured_630 : 630 px de large, animé, sous 5 Mo."),
                ("Ouvrir la page d’envoi Steam", "Connectez-vous à Steam dans le navigateur et ouvrez la page d’envoi d’illustrations depuis l’onglet Steam de Showcase Maker."),
                ("Coller le code dans la console", "Appuyez sur F12 → Console, collez le code Featured de l’onglet Steam et appuyez sur Entrée."),
                ("Envoyer featured_630", "Choisissez featured_630.gif (ou .png), donnez un titre et envoyez-le."),
                ("Le choisir sur le profil", "Ouvrez Modifier le profil → Vitrine, choisissez « Featured Artwork Showcase » et l’illustration envoyée."),
            ],
            "faq": [
                ("Mon GIF ne bouge pas sur le profil", "Pour les fichiers trop lourds, Steam affiche une image fixe. Gardez le fichier sous 5 Mo — Showcase Maker le fait automatiquement."),
                ("Puis-je utiliser une vidéo ?", "Oui. Les MP4 et WebM deviennent un GIF en boucle ; l’outil « Boucle » rend la jonction invisible."),
            ],
        },
        "uk": {
            "title": "Як завантажити анімований GIF у вітрину «Вибрана ілюстрація» Steam",
            "description": "Зроби GIF шириною 630 px до 5 МБ для вітрини Featured Artwork і постав його в профіль Steam.",
            "intro": "Вітрина вибраної ілюстрації показує одну велику картинку. Це найпростіший спосіб поставити анімований GIF у профіль — якщо файл має правильну ширину й вкладається в ліміти Steam.",
            "mode": "featured",
            "steps": [
                ("Створи файл", "У Showcase Maker додай картинку, GIF або відео й обери «Одна велика ілюстрація». Вийде featured_630: 630 px завширшки, з анімацією, до 5 МБ."),
                ("Відкрий сторінку завантаження Steam", "Увійди в Steam у браузері й відкрий сторінку завантаження ілюстрацій із вкладки Steam на сайті."),
                ("Встав код у консоль", "Натисни F12 → Console, встав код для Featured із вкладки Steam і натисни Enter."),
                ("Завантаж featured_630", "Обери featured_630.gif (або .png), задай назву й завантаж."),
                ("Обери її в профілі", "Відкрий «Редагувати профіль» → «Вітрина», обери «Featured Artwork Showcase» і відміть завантажену роботу."),
            ],
            "faq": [
                ("GIF у профілі не рухається", "Для завеликих файлів Steam показує статичну картинку. Тримай файл до 5 МБ — Showcase Maker робить це сам."),
                ("Чи можна взяти відео?", "Так. MP4 і WebM перетворюються на зациклений GIF, а інструмент «Зациклити» зробить стик непомітним."),
            ],
        },
        "es": {
            "title": "Cómo subir un GIF animado al escaparate «Featured Artwork» de Steam",
            "description": "Crea un GIF Featured Artwork de 630 px de ancho y menos de 5 MB y ponlo en tu perfil de Steam.",
            "intro": "El escaparate Featured Artwork muestra una imagen grande. Es la forma más sencilla de poner un GIF animado en tu perfil, siempre que el archivo tenga el ancho correcto y cumpla los límites de Steam.",
            "mode": "featured",
            "steps": [
                ("Crea el archivo", "En Showcase Maker añade tu imagen, GIF o vídeo y elige «Una ilustración grande». Obtienes featured_630: 630 px de ancho, animado, menos de 5 MB."),
                ("Abre la página de subida de Steam", "Inicia sesión en Steam en el navegador y abre la página de subida de ilustraciones desde la pestaña Steam de Showcase Maker."),
                ("Pega el código en la consola", "Pulsa F12 → Console, pega el código de Featured de la pestaña Steam y pulsa Intro."),
                ("Sube featured_630", "Elige featured_630.gif (o .png), ponle un título y súbelo."),
                ("Selecciónalo en tu perfil", "Abre Editar perfil → Escaparate, elige «Featured Artwork Showcase» y la ilustración subida."),
            ],
            "faq": [
                ("Mi GIF no se mueve en el perfil", "Con archivos demasiado grandes, Steam muestra una imagen fija. Mantén el archivo por debajo de 5 MB: Showcase Maker lo hace solo."),
                ("¿Puedo usar un vídeo?", "Sí. Los MP4 y WebM se convierten en un GIF en bucle; la herramienta «Bucle» hace la unión invisible."),
            ],
        },
        "pt": {
            "title": "Como enviar um GIF animado para a vitrine «Featured Artwork» da Steam",
            "description": "Crie um GIF Featured Artwork de 630 px de largura e menos de 5 MB e coloque no seu perfil da Steam.",
            "intro": "A vitrine Featured Artwork mostra uma imagem grande. É o jeito mais simples de colocar um GIF animado no perfil — desde que o arquivo tenha a largura certa e caiba nos limites da Steam.",
            "mode": "featured",
            "steps": [
                ("Crie o arquivo", "No Showcase Maker adicione sua imagem, GIF ou vídeo e escolha «Uma ilustração grande». O resultado é featured_630: 630 px de largura, animado, menos de 5 MB."),
                ("Abra a página de envio da Steam", "Entre na Steam pelo navegador e abra a página de envio de ilustrações pela aba Steam do Showcase Maker."),
                ("Cole o código no console", "Pressione F12 → Console, cole o código de Featured da aba Steam e pressione Enter."),
                ("Envie featured_630", "Escolha featured_630.gif (ou .png), dê um título e envie."),
                ("Selecione no perfil", "Abra Editar perfil → Vitrine, escolha «Featured Artwork Showcase» e a ilustração enviada."),
            ],
            "faq": [
                ("Meu GIF não se mexe no perfil", "Para arquivos grandes demais a Steam mostra uma imagem parada. Mantenha o arquivo abaixo de 5 MB — o Showcase Maker faz isso sozinho."),
                ("Posso usar um vídeo?", "Sim. MP4 e WebM viram um GIF em loop; a ferramenta «Loop» deixa a emenda invisível."),
            ],
        },
    },
    "steam-artwork-showcase-split": {
        "de": {
            "title": "So erstellst du eine Steam-Artwork-Vitrine mit Seitenteil (506 + 100)",
            "description": "Teile ein Bild in das 506 px große Hauptbild und das 100 px schmale Seitenteil der Steam-Artwork-Vitrine.",
            "intro": "Die Artwork-Vitrine besteht aus einem großen Bild und einer schmalen Spalte daneben. Stammen beide aus einem Bild, entsteht ein breites Artwork. Showcase Maker schneidet die Teile mit 506 px und 100 px so, dass sie genau aneinanderpassen.",
            "mode": "split",
            "steps": [
                ("Die zwei Teile erstellen", "Füge in Showcase Maker dein Bild, GIF oder Video hinzu und wähle „Artwork + Seitenpanel“. Du bekommst center_506 und side_100; Animationen bleiben synchron."),
                ("Steam-Uploadseite öffnen", "Melde dich im Browser bei Steam an und öffne die Artwork-Uploadseite über den Steam-Tab von Showcase Maker."),
                ("Konsolencode einfügen", "Drücke F12 → Console, füge den Code für Artwork Split aus dem Steam-Tab ein und drücke Enter."),
                ("Erst die Mitte, dann die Seite", "Lade zuerst center_506 und danach side_100 hoch — die Reihenfolge entscheidet, welches Teil Steam groß zeigt."),
                ("Im Profil auswählen", "Öffne Profil bearbeiten → Vitrine, wähle „Artwork Showcase“ und die zwei hochgeladenen Teile."),
            ],
            "faq": [
                ("Das Seitenteil ist auf der falschen Seite", "Steam zeigt das zuerst gewählte Artwork groß. Wähle center_506 zuerst."),
                ("Kann ich einen Rahmen hinzufügen?", "Ja: Showcase Maker zeichnet einen Rahmen um jedes Teil oder um die ganze Vitrine, auch animiert."),
            ],
        },
        "tr": {
            "title": "Yan panelli Steam Artwork vitrini nasıl yapılır (506 + 100)",
            "description": "Bir resmi Steam Artwork vitrininin 506 px ana görseli ve 100 px yan paneline böl.",
            "intro": "Artwork vitrini büyük bir resim ve yanında dar bir sütundan oluşur. İkisi de aynı resimden kesilirse tek bir geniş çizim oluşur. Showcase Maker 506 px ve 100 px parçaları tam birleşecek şekilde keser.",
            "mode": "split",
            "steps": [
                ("İki parçayı oluştur", "Showcase Maker’da resmini, GIF’ini veya videonu ekle ve “Çizim + yan panel”i seç. center_506 ve side_100 alırsın; animasyon senkron kalır."),
                ("Steam yükleme sayfasını aç", "Tarayıcında Steam’e giriş yap ve Showcase Maker’ın Steam sekmesinden çizim yükleme sayfasını aç."),
                ("Konsol kodunu yapıştır", "F12 → Console, Steam sekmesindeki Artwork Split kodunu yapıştır ve Enter’a bas."),
                ("Önce orta, sonra yan", "Önce center_506’yı, sonra side_100’ü yükle — Steam’in hangisini büyük göstereceğini sıra belirler."),
                ("Profilinde seç", "Profili düzenle → Vitrin’i aç, “Artwork Showcase”i seç ve iki yüklemeyi işaretle."),
            ],
            "faq": [
                ("Yan panel yanlış tarafta", "Steam ilk seçilen çizimi büyük gösterir. Önce center_506’yı seç."),
                ("Çerçeve ekleyebilir miyim?", "Evet: Showcase Maker her parçanın ya da tüm vitrinin etrafına, animasyonlu da olabilen bir çerçeve çizer."),
            ],
        },
        "fr": {
            "title": "Comment créer une vitrine Artwork Steam avec panneau latéral (506 + 100)",
            "description": "Découpez une image en image principale de 506 px et panneau latéral de 100 px pour la vitrine Artwork de Steam.",
            "intro": "La vitrine Artwork comprend une grande image et une colonne étroite à côté. Quand les deux viennent de la même image, elles forment une seule grande illustration. Showcase Maker découpe les parties de 506 px et 100 px pour qu’elles se raccordent exactement.",
            "mode": "split",
            "steps": [
                ("Créer les deux parties", "Dans Showcase Maker, ajoutez votre image, GIF ou vidéo et choisissez « Illustration + panneau latéral ». Vous obtenez center_506 et side_100 ; les animations restent synchronisées."),
                ("Ouvrir la page d’envoi Steam", "Connectez-vous à Steam dans le navigateur et ouvrez la page d’envoi d’illustrations depuis l’onglet Steam de Showcase Maker."),
                ("Coller le code dans la console", "Appuyez sur F12 → Console, collez le code Artwork Split de l’onglet Steam et appuyez sur Entrée."),
                ("D’abord le centre, puis le côté", "Envoyez d’abord center_506, puis side_100 : l’ordre décide quelle partie Steam affiche en grand."),
                ("Les choisir sur le profil", "Ouvrez Modifier le profil → Vitrine, choisissez « Artwork Showcase » et les deux envois."),
            ],
            "faq": [
                ("Le panneau latéral est du mauvais côté", "Steam affiche en grand la première illustration choisie. Choisissez center_506 en premier."),
                ("Puis-je ajouter un cadre ?", "Oui : Showcase Maker dessine un cadre autour de chaque partie ou de toute la vitrine, y compris animé."),
            ],
        },
        "uk": {
            "title": "Як зробити вітрину ілюстрацій Steam із бічною частиною (506 + 100)",
            "description": "Розділи одну картинку на основне зображення 506 px і бічну смугу 100 px для вітрини ілюстрацій Steam.",
            "intro": "Вітрина ілюстрацій складається з великої картинки й вузької колонки поруч. Коли обидві частини вирізані з одного зображення, виходить одна широка ілюстрація. Showcase Maker наріже частини 506 px і 100 px так, щоб вони точно стикувалися.",
            "mode": "split",
            "steps": [
                ("Створи дві частини", "У Showcase Maker додай картинку, GIF або відео й обери «Ілюстрація + бічна частина». Отримаєш center_506 і side_100; анімація синхронна."),
                ("Відкрий сторінку завантаження Steam", "Увійди в Steam у браузері й відкрий сторінку завантаження ілюстрацій із вкладки Steam на сайті."),
                ("Встав код у консоль", "Натисни F12 → Console, встав код для Artwork Split із вкладки Steam і натисни Enter."),
                ("Спочатку центр, потім бік", "Завантаж спочатку center_506, потім side_100 — від порядку залежить, яка частина буде великою."),
                ("Обери їх у профілі", "Відкрий «Редагувати профіль» → «Вітрина», обери «Artwork Showcase» і відміть обидва завантаження."),
            ],
            "faq": [
                ("Бічна частина опинилася не з того боку", "Steam показує великою першу вибрану ілюстрацію. Вибирай center_506 першою."),
                ("Можна додати рамку?", "Так: Showcase Maker малює рамку навколо кожної частини або всієї вітрини, зокрема анімовану."),
            ],
        },
        "es": {
            "title": "Cómo hacer un escaparate de Artwork de Steam con panel lateral (506 + 100)",
            "description": "Divide una imagen en la imagen principal de 506 px y el panel lateral de 100 px del escaparate de Artwork de Steam.",
            "intro": "El escaparate de Artwork tiene una imagen grande y una columna estrecha al lado. Cuando ambas salen de la misma imagen, forman una sola ilustración ancha. Showcase Maker corta las partes de 506 px y 100 px para que encajen exactamente.",
            "mode": "split",
            "steps": [
                ("Crea las dos partes", "En Showcase Maker añade tu imagen, GIF o vídeo y elige «Ilustración + panel lateral». Obtienes center_506 y side_100; las animaciones van sincronizadas."),
                ("Abre la página de subida de Steam", "Inicia sesión en Steam en el navegador y abre la página de subida de ilustraciones desde la pestaña Steam de Showcase Maker."),
                ("Pega el código en la consola", "Pulsa F12 → Console, pega el código de Artwork Split de la pestaña Steam y pulsa Intro."),
                ("Primero el centro, luego el lateral", "Sube primero center_506 y después side_100: el orden decide cuál muestra Steam en grande."),
                ("Selecciónalos en tu perfil", "Abre Editar perfil → Escaparate, elige «Artwork Showcase» y las dos subidas."),
            ],
            "faq": [
                ("El panel lateral está en el lado equivocado", "Steam muestra en grande la primera ilustración elegida. Elige center_506 primero."),
                ("¿Puedo añadir un marco?", "Sí: Showcase Maker dibuja un marco alrededor de cada parte o de todo el escaparate, también animado."),
            ],
        },
        "pt": {
            "title": "Como fazer uma vitrine de Artwork da Steam com painel lateral (506 + 100)",
            "description": "Divida uma imagem na imagem principal de 506 px e no painel lateral de 100 px da vitrine de Artwork da Steam.",
            "intro": "A vitrine de Artwork tem uma imagem grande e uma coluna estreita ao lado. Quando as duas saem da mesma imagem, formam uma única ilustração larga. O Showcase Maker corta as partes de 506 px e 100 px para que se encaixem exatamente.",
            "mode": "split",
            "steps": [
                ("Crie as duas partes", "No Showcase Maker adicione sua imagem, GIF ou vídeo e escolha «Ilustração + painel lateral». Você recebe center_506 e side_100; as animações ficam sincronizadas."),
                ("Abra a página de envio da Steam", "Entre na Steam pelo navegador e abra a página de envio de ilustrações pela aba Steam do Showcase Maker."),
                ("Cole o código no console", "Pressione F12 → Console, cole o código de Artwork Split da aba Steam e pressione Enter."),
                ("Primeiro o centro, depois a lateral", "Envie primeiro center_506 e depois side_100 — a ordem decide qual parte a Steam mostra grande."),
                ("Selecione no perfil", "Abra Editar perfil → Vitrine, escolha «Artwork Showcase» e os dois envios."),
            ],
            "faq": [
                ("O painel lateral ficou do lado errado", "A Steam mostra grande a primeira ilustração escolhida. Escolha center_506 primeiro."),
                ("Posso adicionar uma moldura?", "Sim: o Showcase Maker desenha uma moldura em volta de cada parte ou da vitrine inteira, inclusive animada."),
            ],
        },
    },
}
for _slug, _versions in _MORE.items():
    GUIDES[_slug].update(_versions)

# Guides for common questions (2026-10-09): profile design, showcase sizes, GIF over 5 MB, long Workshop showcase.
from smweb.guides_extra import GUIDES_EXTRA  # noqa: E402
GUIDES.update(GUIDES_EXTRA)


UI = {
    "en": {"kicker": "SHOWCASE MAKER / GUIDE", "steps": "Step by step", "faq": "Common questions", "cta": "Open Showcase Maker",
           "hub_title": "Steam showcase guides", "hub_description": "Step-by-step guides for Steam profile design: showcase sizes, animated Workshop, Featured Artwork and Artwork showcases, long showcases and GIFs over 5 MB.",
           "hub_intro": "Short, practical guides to the Steam profile and its showcases.", "more": "More guides", "read": "Read the guide",
           "ext_title": "Don’t want to deal with the console?",
           "ext_text": "The free SteamShowcase Helper extension uploads the parts for you: pick the showcase type and drop the files in. The steps above work just as well without it.",
           "ext_link": "About the extension"},
    "ru": {"kicker": "SHOWCASE MAKER / ИНСТРУКЦИЯ", "steps": "Пошагово", "faq": "Частые вопросы", "cta": "Открыть Showcase Maker",
           "hub_title": "Инструкции по витринам Steam", "hub_description": "Пошаговые инструкции по оформлению профиля Steam: размеры витрин, анимированные витрины мастерской и иллюстраций, длинные витрины и GIF больше 5 МБ.",
           "hub_intro": "Короткие практичные инструкции по профилю Steam и его витринам.", "more": "Другие инструкции", "read": "Читать инструкцию",
           "ext_title": "Не хочешь возиться с консолью?",
           "ext_text": "Бесплатное расширение SteamShowcase Helper загрузит части за тебя: выбери тип витрины и перетащи файлы. Шаги выше так же хорошо работают и без него.",
           "ext_link": "О расширении"},
    "de": {"kicker": "SHOWCASE MAKER / ANLEITUNG", "steps": "Schritt für Schritt", "faq": "Häufige Fragen", "cta": "Showcase Maker öffnen",
           "hub_title": "Anleitungen für Steam-Vitrinen", "hub_description": "Schritt-für-Schritt-Anleitungen zum Gestalten des Steam-Profils: Vitrinengrößen, animierte Workshop-, Featured- und Artwork-Vitrinen, lange Vitrinen und GIFs über 5 MB.",
           "hub_intro": "Kurze, praktische Anleitungen zum Steam-Profil und seinen Vitrinen.", "more": "Weitere Anleitungen", "read": "Anleitung lesen",
           "ext_title": "Keine Lust auf die Konsole?",
           "ext_text": "Die kostenlose Erweiterung SteamShowcase Helper lädt die Teile für dich hoch: Vitrinentyp wählen und Dateien hineinziehen. Die Schritte oben funktionieren genauso gut ohne sie.",
           "ext_link": "Über die Erweiterung"},
    "tr": {"kicker": "SHOWCASE MAKER / REHBER", "steps": "Adım adım", "faq": "Sık sorulan sorular", "cta": "Showcase Maker’ı aç",
           "hub_title": "Steam vitrin rehberleri", "hub_description": "Steam profil tasarımı için adım adım rehberler: vitrin boyutları, hareketli Atölye, Featured ve Artwork vitrinleri, uzun vitrinler ve 5 MB’tan büyük GIF’ler.",
           "hub_intro": "Steam profili ve vitrinleri için kısa, pratik rehberler.", "more": "Diğer rehberler", "read": "Rehberi oku",
           "ext_title": "Konsolla uğraşmak istemiyor musun?",
           "ext_text": "Ücretsiz SteamShowcase Helper eklentisi parçaları senin yerine yükler: vitrin türünü seç ve dosyaları sürükle. Yukarıdaki adımlar onsuz da aynı şekilde çalışır.",
           "ext_link": "Eklenti hakkında"},
    "fr": {"kicker": "SHOWCASE MAKER / GUIDE", "steps": "Pas à pas", "faq": "Questions fréquentes", "cta": "Ouvrir Showcase Maker",
           "hub_title": "Guides des vitrines Steam", "hub_description": "Guides pas à pas pour personnaliser le profil Steam : tailles des vitrines, vitrines Workshop, Featured et Artwork animées, vitrines longues et GIF de plus de 5 Mo.",
           "hub_intro": "Des guides courts et pratiques sur le profil Steam et ses vitrines.", "more": "Autres guides", "read": "Lire le guide",
           "ext_title": "Pas envie de passer par la console ?",
           "ext_text": "L’extension gratuite SteamShowcase Helper envoie les parties pour vous : choisissez le type de vitrine et déposez les fichiers. Les étapes ci-dessus fonctionnent aussi bien sans elle.",
           "ext_link": "À propos de l’extension"},
    "uk": {"kicker": "SHOWCASE MAKER / ІНСТРУКЦІЯ", "steps": "Покроково", "faq": "Часті питання", "cta": "Відкрити Showcase Maker",
           "hub_title": "Інструкції з вітрин Steam", "hub_description": "Покрокові інструкції з оформлення профілю Steam: розміри вітрин, анімовані вітрини майстерні та ілюстрацій, довгі вітрини й GIF понад 5 МБ.",
           "hub_intro": "Короткі практичні інструкції щодо профілю Steam і його вітрин.", "more": "Інші інструкції", "read": "Читати інструкцію",
           "ext_title": "Не хочеш возитися з консоллю?",
           "ext_text": "Безкоштовне розширення SteamShowcase Helper завантажить частини за тебе: обери тип вітрини й перетягни файли. Кроки вище так само добре працюють і без нього.",
           "ext_link": "Про розширення"},
    "es": {"kicker": "SHOWCASE MAKER / GUÍA", "steps": "Paso a paso", "faq": "Preguntas frecuentes", "cta": "Abrir Showcase Maker",
           "hub_title": "Guías de escaparates de Steam", "hub_description": "Guías paso a paso para decorar el perfil de Steam: tamaños de escaparates, escaparates animados de Workshop, Featured y Artwork, escaparates largos y GIF de más de 5 MB.",
           "hub_intro": "Guías cortas y prácticas sobre el perfil de Steam y sus escaparates.", "more": "Más guías", "read": "Leer la guía",
           "ext_title": "¿No quieres usar la consola?",
           "ext_text": "La extensión gratuita SteamShowcase Helper sube las partes por ti: elige el tipo de escaparate y suelta los archivos. Los pasos de arriba funcionan igual de bien sin ella.",
           "ext_link": "Sobre la extensión"},
    "pt": {"kicker": "SHOWCASE MAKER / GUIA", "steps": "Passo a passo", "faq": "Perguntas frequentes", "cta": "Abrir o Showcase Maker",
           "hub_title": "Guias de vitrines da Steam", "hub_description": "Guias passo a passo para personalizar o perfil Steam: tamanhos das vitrines, vitrines animadas da Oficina, Featured e Artwork, vitrines longas e GIFs acima de 5 MB.",
           "hub_intro": "Guias curtos e práticos sobre o perfil Steam e suas vitrines.", "more": "Mais guias", "read": "Ler o guia",
           "ext_title": "Não quer mexer no console?",
           "ext_text": "A extensão gratuita SteamShowcase Helper envia as partes para você: escolha o tipo de vitrine e solte os arquivos. Os passos acima funcionam igualmente bem sem ela.",
           "ext_link": "Sobre a extensão"},
}


def content_language(language: str) -> str:
    return language if language in GUIDE_LANGUAGES else "en"
