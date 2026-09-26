"""Public how-to guides for search traffic (/<lang>/guides/<slug>).

Written in English and Russian; other site languages show the English text with
``noindex, follow`` (same policy as the extension page). Steps mirror the
site's own Steam tab (upload page -> console code -> files in order) and the
SteamShowcase Helper extension route.
"""
from __future__ import annotations

GUIDE_LANGUAGES = ("en", "ru")

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
                ("Upload part_1 … part_5 in order", "Upload the five files one by one, starting with part_1. Tip: the SteamShowcase Helper extension can upload them automatically without the console."),
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
                ("Загрузи part_1 … part_5 по порядку", "Загружай файлы по одному, начиная с part_1. Совет: расширение SteamShowcase Helper загрузит их автоматически, без консоли."),
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
                ("Создай файл", "В Showcase Maker добавь картинку, GIF или видео и выбери «Одна большая иллюстрация». Получится featured_630: 630 px в ширину, с анимацией, до 5 МБ."),
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
                ("Создай две части", "В Showcase Maker добавь картинку, GIF или видео и выбери «Иллюстрация + боковая часть». Получишь center_506 и side_100; анимация синхронна."),
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

UI = {
    "en": {"kicker": "SHOWCASE MAKER / GUIDE", "steps": "Step by step", "faq": "Common questions", "cta": "Open Showcase Maker",
           "hub_title": "Steam showcase guides", "hub_description": "Step-by-step guides for animated Steam profile showcases: Workshop, Featured Artwork and Artwork with a side panel.",
           "hub_intro": "Short, practical guides for the three showcase types that Showcase Maker prepares.", "more": "More guides", "read": "Read the guide"},
    "ru": {"kicker": "SHOWCASE MAKER / ИНСТРУКЦИЯ", "steps": "Пошагово", "faq": "Частые вопросы", "cta": "Открыть Showcase Maker",
           "hub_title": "Инструкции по витринам Steam", "hub_description": "Пошаговые инструкции по анимированным витринам профиля Steam: мастерская, избранная иллюстрация и иллюстрация с боковой частью.",
           "hub_intro": "Короткие практичные инструкции для трёх типов витрин, которые готовит Showcase Maker.", "more": "Другие инструкции", "read": "Читать инструкцию"},
}


def content_language(language: str) -> str:
    return language if language in GUIDE_LANGUAGES else "en"
