"""What search engines and link previews show for a page, in the page's own language (2026-10-09).

Before this, most pages carried an English <title>/<meta description> in the HTML and only the browser script
translated them, so Yandex and Google showed English snippets for /ru/, /de/... and had little Russian text to
match Russian queries with. ``apply()`` (called from pages._localized_content for every localized page):

* replaces the <title> and the meta description of the known pages with the text below (8 languages);
* adds Open Graph and Twitter tags to every localized page (Telegram, Discord, VK and X previews), with a
  per-language preview picture ``static/img/og/og-<lang>.jpg`` (scripts/build_og_images.py);
* adds JSON-LD for the landing (WebSite + WebApplication with the free offer);
* marks the page with ``<meta name="sm-seo">`` so page scripts (home.js, community-gallery.js, extension-guide.js,
  app.js) keep the server title instead of overwriting it with their English fallback.

Titles stay under ~60 characters and descriptions under ~160, the length search engines show. Product facts
in the copy (showcase types, free plan, the extension's features) are the site's real ones; keep them true.
"""
from __future__ import annotations

import html
import json
import re
from urllib.parse import unquote

from smweb.core import STATIC
from smweb.locales import SUPPORTED_LANGUAGES, localized_path

SITE = "https://showcasemaker.com"
BRAND = "Showcase Maker"
OG_LOCALE = {"en": "en_US", "ru": "ru_RU", "de": "de_DE", "tr": "tr_TR", "fr": "fr_FR", "uk": "uk_UA",
             "es": "es_ES", "pt": "pt_BR"}

# page -> language -> (title, description)
PAGES: dict[str, dict[str, tuple[str, str]]] = {
    "home": {
        "en": ("Steam Profile Design — Showcases & GIFs | Showcase Maker",
               "Design your Steam profile in 5 minutes: backgrounds, artwork showcases, GIFs, a profile mockup "
               "and ready-to-upload files. Free, right in your browser."),
        "ru": ("Оформление профиля Steam — витрины и GIF | Showcase Maker",
               "Красиво оформите профиль Steam за 5 минут: фоны, artwork-витрины, GIF, мокап профиля и готовые "
               "файлы для загрузки. Бесплатно, прямо в браузере."),
        "uk": ("Оформлення профілю Steam — вітрини та GIF | Showcase Maker",
               "Гарно оформіть профіль Steam за 5 хвилин: фони, artwork-вітрини, GIF, макет профілю та готові "
               "файли для завантаження. Безкоштовно, просто в браузері."),
        "de": ("Steam-Profil gestalten – Showcases & GIFs | Showcase Maker",
               "Gestalte dein Steam-Profil in 5 Minuten: Hintergründe, Artwork-Showcases, GIFs, Profilvorschau "
               "und fertige Dateien zum Hochladen. Kostenlos im Browser."),
        "fr": ("Design de profil Steam : vitrines et GIF | Showcase Maker",
               "Personnalisez votre profil Steam en 5 minutes : arrière-plans, vitrines d'illustrations, GIF, "
               "aperçu du profil et fichiers prêts à importer. Gratuit, dans le navigateur."),
        "es": ("Diseño de perfil de Steam: escaparates y GIF | Showcase Maker",
               "Personaliza tu perfil de Steam en 5 minutos: fondos, escaparates de ilustraciones, GIF, vista "
               "previa del perfil y archivos listos para subir. Gratis, en el navegador."),
        "pt": ("Design de perfil Steam: vitrines e GIFs | Showcase Maker",
               "Personalize seu perfil Steam em 5 minutos: fundos, vitrines de arte, GIFs, prévia do perfil e "
               "arquivos prontos para enviar. Grátis, direto no navegador."),
        "tr": ("Steam Profil Tasarımı: Vitrinler ve GIF | Showcase Maker",
               "Steam profilini 5 dakikada tasarla: arka planlar, çizim vitrinleri, GIF'ler, profil önizlemesi "
               "ve yüklemeye hazır dosyalar. Ücretsiz, tarayıcıda."),
    },
    "app": {
        "en": ("Steam Showcase Tools — Workshop, Artwork, GIF | Showcase Maker",
               "Three steps to a finished Steam profile: add a picture, GIF or video, pick the showcase "
               "(Workshop, Featured or Artwork Split) and download files ready for Steam."),
        "ru": ("Инструменты для витрин Steam: GIF и арты | Showcase Maker",
               "Оформление профиля Steam в три шага: загрузите картинку, GIF или видео, выберите витрину "
               "(мастерская, иллюстрация или избранное) и скачайте готовые файлы."),
        "uk": ("Інструменти для вітрин Steam: GIF і арти | Showcase Maker",
               "Оформлення профілю Steam у три кроки: додайте картинку, GIF або відео, виберіть вітрину "
               "(майстерня, ілюстрація чи обране) та завантажте готові файли."),
        "de": ("Steam-Showcase-Tools: Workshop, Artwork, GIF | Showcase Maker",
               "Dein Steam-Profil in drei Schritten: Bild, GIF oder Video hinzufügen, Showcase wählen (Workshop, "
               "Featured oder Artwork Split) und fertige Dateien herunterladen."),
        "fr": ("Outils de vitrines Steam : Workshop, GIF | Showcase Maker",
               "Votre profil Steam en trois étapes : ajoutez une image, un GIF ou une vidéo, choisissez la vitrine "
               "(Workshop, Featured ou Artwork Split) et téléchargez les fichiers."),
        "es": ("Herramientas para escaparates de Steam | Showcase Maker",
               "Tu perfil de Steam en tres pasos: añade una imagen, GIF o vídeo, elige el escaparate (Workshop, "
               "Featured o Artwork Split) y descarga archivos listos para Steam."),
        "pt": ("Ferramentas de vitrines Steam: GIFs e arte | Showcase Maker",
               "Seu perfil Steam em três passos: envie uma imagem, GIF ou vídeo, escolha a vitrine (Workshop, "
               "Featured ou Artwork Split) e baixe arquivos prontos para a Steam."),
        "tr": ("Steam Vitrin Araçları: GIF ve Çizim | Showcase Maker",
               "Üç adımda Steam profilin hazır: resim, GIF veya video ekle, vitrini seç (Workshop, Featured veya "
               "Artwork Split) ve Steam'e hazır dosyaları indir."),
    },
    "gallery": {
        "en": ("Steam Showcase Gallery — Profile Designs | Showcase Maker",
               "Ready Steam profile designs from the community: animated Workshop and Artwork showcases to "
               "preview, download and put on your own profile."),
        "ru": ("Галерея витрин Steam — готовые оформления | Showcase Maker",
               "Готовые оформления профиля Steam от авторов: анимированные витрины мастерской и иллюстраций. "
               "Смотрите, скачивайте и ставьте на свой профиль."),
        "uk": ("Галерея вітрин Steam — готові оформлення | Showcase Maker",
               "Готові оформлення профілю Steam від авторів: анімовані вітрини майстерні та ілюстрацій. "
               "Дивіться, завантажуйте й ставте на свій профіль."),
        "de": ("Steam-Showcase-Galerie – Profildesigns | Showcase Maker",
               "Fertige Steam-Profildesigns aus der Community: animierte Workshop- und Artwork-Showcases "
               "ansehen, herunterladen und aufs eigene Profil laden."),
        "fr": ("Galerie de vitrines Steam – designs de profil | Showcase Maker",
               "Designs de profil Steam prêts à l'emploi par la communauté : vitrines Workshop et Artwork "
               "animées à voir, télécharger et mettre sur votre profil."),
        "es": ("Galería de escaparates de Steam | Showcase Maker",
               "Diseños de perfil de Steam listos de la comunidad: escaparates animados de Workshop y Artwork "
               "para ver, descargar y poner en tu perfil."),
        "pt": ("Galeria de vitrines Steam – designs de perfil | Showcase Maker",
               "Designs de perfil Steam prontos da comunidade: vitrines animadas de Workshop e Artwork para ver, "
               "baixar e colocar no seu perfil."),
        "tr": ("Steam Vitrin Galerisi – Profil Tasarımları | Showcase Maker",
               "Topluluktan hazır Steam profil tasarımları: hareketli Workshop ve Artwork vitrinlerini incele, "
               "indir ve kendi profiline koy."),
    },
    "extension": {
        "en": ("SteamShowcase Helper — Auto-Upload to Steam | Showcase Maker",
               "Browser extension: uploads Showcase Maker files to Steam for you, places them into the right "
               "showcases, uploads in batches and keeps profile presets."),
        "ru": ("SteamShowcase Helper — автозагрузка в Steam | Showcase Maker",
               "Расширение для браузера: само загружает файлы Showcase Maker в Steam, расставляет их по витринам, "
               "загружает пачками и хранит пресеты профиля."),
        "uk": ("SteamShowcase Helper — автозавантаження в Steam | Showcase Maker",
               "Розширення для браузера: саме завантажує файли Showcase Maker у Steam, розставляє їх по вітринах, "
               "завантажує пачками й зберігає пресети профілю."),
        "de": ("SteamShowcase Helper – Auto-Upload zu Steam | Showcase Maker",
               "Browser-Erweiterung: lädt Showcase-Maker-Dateien für dich zu Steam hoch, ordnet sie den "
               "Showcases zu, lädt stapelweise hoch und speichert Profil-Presets."),
        "fr": ("SteamShowcase Helper – import auto sur Steam | Showcase Maker",
               "Extension de navigateur : importe pour vous les fichiers Showcase Maker sur Steam, les place dans "
               "les vitrines, envoie par lots et garde des préréglages de profil."),
        "es": ("SteamShowcase Helper – subida automática | Showcase Maker",
               "Extensión de navegador: sube por ti los archivos de Showcase Maker a Steam, los coloca en los "
               "escaparates, sube por lotes y guarda ajustes de perfil."),
        "pt": ("SteamShowcase Helper – envio automático | Showcase Maker",
               "Extensão de navegador: envia os arquivos do Showcase Maker para a Steam por você, coloca nas "
               "vitrines, envia em lotes e salva predefinições de perfil."),
        "tr": ("SteamShowcase Helper – Steam'e Otomatik Yükleme | Showcase Maker",
               "Tarayıcı eklentisi: Showcase Maker dosyalarını senin yerine Steam'e yükler, vitrinlere "
               "yerleştirir, toplu yükler ve profil ön ayarlarını saklar."),
    },
    "support": {
        "en": ("Support · Showcase Maker", "Your Showcase Maker support requests and our answers."),
        "ru": ("Поддержка · Showcase Maker", "Ваши обращения в поддержку Showcase Maker и ответы на них."),
        "uk": ("Підтримка · Showcase Maker", "Ваші звернення до підтримки Showcase Maker і відповіді на них."),
        "de": ("Support · Showcase Maker", "Deine Support-Anfragen bei Showcase Maker und unsere Antworten."),
        "fr": ("Assistance · Showcase Maker", "Vos demandes d'assistance Showcase Maker et nos réponses."),
        "es": ("Soporte · Showcase Maker", "Tus solicitudes de soporte de Showcase Maker y nuestras respuestas."),
        "pt": ("Suporte · Showcase Maker", "Seus pedidos de suporte do Showcase Maker e nossas respostas."),
        "tr": ("Destek · Showcase Maker", "Showcase Maker destek taleplerin ve yanıtlarımız."),
    },
    "account": {
        "en": ("Account · Showcase Maker", "Your Showcase Maker plan, purchases and settings."),
        "ru": ("Аккаунт · Showcase Maker", "Тариф, покупки и настройки вашего аккаунта Showcase Maker."),
        "uk": ("Акаунт · Showcase Maker", "Тариф, покупки та налаштування вашого акаунта Showcase Maker."),
        "de": ("Konto · Showcase Maker", "Dein Showcase-Maker-Tarif, Käufe und Einstellungen."),
        "fr": ("Compte · Showcase Maker", "Votre offre Showcase Maker, vos achats et vos réglages."),
        "es": ("Cuenta · Showcase Maker", "Tu plan de Showcase Maker, compras y ajustes."),
        "pt": ("Conta · Showcase Maker", "Seu plano do Showcase Maker, compras e configurações."),
        "tr": ("Hesap · Showcase Maker", "Showcase Maker planın, satın alımların ve ayarların."),
    },
    "profile": {
        "en": ("Steam Profile Editor · Showcase Maker", "Plan your Steam profile and its showcases before uploading."),
        "ru": ("Редактор профиля Steam · Showcase Maker", "Соберите профиль Steam и его витрины до загрузки."),
        "uk": ("Редактор профілю Steam · Showcase Maker", "Зберіть профіль Steam і його вітрини до завантаження."),
        "de": ("Steam-Profil-Editor · Showcase Maker", "Plane dein Steam-Profil und seine Showcases vor dem Hochladen."),
        "fr": ("Éditeur de profil Steam · Showcase Maker", "Préparez votre profil Steam et ses vitrines avant l'import."),
        "es": ("Editor de perfil de Steam · Showcase Maker", "Prepara tu perfil de Steam y sus escaparates antes de subirlos."),
        "pt": ("Editor de perfil Steam · Showcase Maker", "Monte seu perfil Steam e as vitrines antes de enviar."),
        "tr": ("Steam Profil Düzenleyici · Showcase Maker", "Steam profilini ve vitrinlerini yüklemeden önce planla."),
    },
    # Public author pages: "<name> — <title>"
    "author": {
        "en": ("Steam showcases by the author · Showcase Maker", "Steam profile designs and showcases by this author on Showcase Maker."),
        "ru": ("Витрины Steam автора · Showcase Maker", "Оформления профиля Steam и витрины этого автора на Showcase Maker."),
        "uk": ("Вітрини Steam автора · Showcase Maker", "Оформлення профілю Steam і вітрини цього автора на Showcase Maker."),
        "de": ("Steam-Showcases des Autors · Showcase Maker", "Steam-Profildesigns und Showcases dieses Autors auf Showcase Maker."),
        "fr": ("Vitrines Steam de l'auteur · Showcase Maker", "Designs de profil Steam et vitrines de cet auteur sur Showcase Maker."),
        "es": ("Escaparates de Steam del autor · Showcase Maker", "Diseños de perfil de Steam y escaparates de este autor en Showcase Maker."),
        "pt": ("Vitrines Steam do autor · Showcase Maker", "Designs de perfil Steam e vitrines deste autor no Showcase Maker."),
        "tr": ("Yazarın Steam vitrinleri · Showcase Maker", "Bu yazarın Showcase Maker'daki Steam profil tasarımları ve vitrinleri."),
    },
}

# Alt text of the preview picture (what the picture shows, in the page language).
OG_ALT = {
    "en": "Showcase Maker: Steam profile design, showcases and GIFs",
    "ru": "Showcase Maker: оформление профиля Steam, витрины и GIF",
    "uk": "Showcase Maker: оформлення профілю Steam, вітрини та GIF",
    "de": "Showcase Maker: Steam-Profil gestalten, Showcases und GIFs",
    "fr": "Showcase Maker : design de profil Steam, vitrines et GIF",
    "es": "Showcase Maker: diseño de perfil de Steam, escaparates y GIF",
    "pt": "Showcase Maker: design de perfil Steam, vitrines e GIFs",
    "tr": "Showcase Maker: Steam profil tasarımı, vitrinler ve GIF",
}


def page_for(route_path: str) -> tuple[str, str]:
    """(page key, author name) for a localized route; ("", "") when the page writes its own title."""
    if route_path == "/":
        return "home", ""
    if route_path in ("/app", "/gallery", "/extension", "/support", "/account", "/profile"):
        return route_path[1:], ""
    if route_path.startswith("/profile/"):
        return "author", unquote(route_path[len("/profile/"):])[:40]
    return "", ""


def text(page: str, language: str) -> tuple[str, str]:
    versions = PAGES[page]
    return versions.get(language) or versions["en"]


def og_image(language: str) -> str:
    name = f"og-{language}.jpg"
    if not (STATIC / "img" / "og" / name).is_file():
        name = "og-en.jpg"
    return f"{SITE}/static/img/og/{name}"


_TITLE = re.compile(r"<title>[\s\S]*?</title>", re.I)
_DESCRIPTION = re.compile(r'<meta\s+name="description"\s+content="[^"]*"\s*/?>', re.I)


def _current(content: str) -> tuple[str, str]:
    title = _TITLE.search(content)
    desc = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', content, re.I)
    raw_title = re.sub(r"^<title>|</title>$", "", title.group(0), flags=re.I) if title else BRAND
    return html.unescape(raw_title).strip(), html.unescape(desc.group(1)) if desc else ""


def _jsonld_home(language: str, title: str, description: str) -> str:
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "@id": f"{SITE}/#website", "url": f"{SITE}/", "name": BRAND,
             "inLanguage": list(SUPPORTED_LANGUAGES)},
            {"@type": "WebApplication", "name": BRAND, "url": f"{SITE}{localized_path(language, '/')}",
             "description": description, "inLanguage": language, "applicationCategory": "DesignApplication",
             "operatingSystem": "Web browser", "image": og_image(language),
             "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}},
        ],
    }
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def apply(content: str, language: str, route_path: str) -> str:
    """Localized title/description for known pages + Open Graph/Twitter tags for every page."""
    page, author = page_for(route_path)
    head_extra: list[str] = []
    if page:
        title, description = text(page, language)
        if author:
            title = f"{author} — {title}"
        safe_title = html.escape(title, quote=False)
        content = _TITLE.sub(lambda _m: f"<title>{safe_title}</title>", content, count=1) if _TITLE.search(content) \
            else content.replace("</head>", f"<title>{safe_title}</title>\n</head>", 1)
        meta = f'<meta name="description" content="{html.escape(description, quote=True)}">'
        content = _DESCRIPTION.sub(lambda _m: meta, content, count=1) if _DESCRIPTION.search(content) \
            else content.replace("</head>", meta + "\n</head>", 1)
        head_extra.append('<meta name="sm-seo" content="1">')
    if 'property="og:title"' not in content:
        title, description = _current(content)
        url = SITE + localized_path(language, route_path)
        image = og_image(language)
        alt = OG_ALT.get(language, OG_ALT["en"])
        tags = [
            ("property", "og:type", "website"), ("property", "og:site_name", BRAND),
            ("property", "og:title", title), ("property", "og:description", description),
            ("property", "og:url", url), ("property", "og:image", image),
            ("property", "og:image:width", "1200"), ("property", "og:image:height", "630"),
            ("property", "og:image:alt", alt), ("property", "og:locale", OG_LOCALE.get(language, "en_US")),
        ]
        tags += [("property", "og:locale:alternate", OG_LOCALE[code]) for code in SUPPORTED_LANGUAGES if code != language]
        tags += [("name", "twitter:card", "summary_large_image"), ("name", "twitter:title", title),
                 ("name", "twitter:description", description), ("name", "twitter:image", image),
                 ("name", "twitter:image:alt", alt)]
        head_extra += [f'<meta {kind}="{key}" content="{html.escape(value, quote=True)}">'
                       for kind, key, value in tags if value]
    if page == "home" and '"WebApplication"' not in content:
        head_extra.append(_jsonld_home(language, *text("home", language)))
    if head_extra:
        content = content.replace("</head>", "\n".join(head_extra) + "\n</head>", 1)
    return content
