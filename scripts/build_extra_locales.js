/* Generate committed client-side language packs from the existing English UI.
   This is a development tool only; production never calls a translation API. */
'use strict';
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const targets = ['de', 'tr', 'fr', 'uk', 'es', 'pt'];
const sourceFiles = [
  ['static/js/home.js', 'var I18N ='],
  ['static/js/app.js', 'const APP_I18N ='],
  ['static/js/app.js', 'var DICT ='],
  ['static/js/app.js', 'var WM_TIPS ='],
  ['static/js/gallery.js', 'const GDICT ='],
  ['static/js/profile.js', 'var PDICT='],
  ['static/js/profile.js', 'var A='],
  ['static/js/seamless-loop.js', 'const copy='],
  ['static/js/showcase-builder.js', 'var COPY ='],
  ['static/js/steam-check.js', 'const copy ='],
  ['static/js/steam-mockup.js', 'var UI ='],
];

function objectLiteral(source, marker) {
  const markerAt = source.indexOf(marker);
  if (markerAt < 0) throw new Error(`Dictionary marker not found: ${marker}`);
  const start = source.indexOf('{', markerAt);
  let depth = 0, quote = '', escaped = false;
  for (let index = start; index < source.length; index += 1) {
    const char = source[index];
    if (quote) {
      if (escaped) escaped = false;
      else if (char === '\\') escaped = true;
      else if (char === quote) quote = '';
      continue;
    }
    if (char === '"' || char === "'" || char === '`') { quote = char; continue; }
    if (char === '{') depth += 1;
    if (char === '}' && --depth === 0) return source.slice(start, index + 1);
  }
  throw new Error(`Unclosed dictionary: ${marker}`);
}

function values(value, output) {
  if (typeof value === 'string') output.add(value);
  else if (Array.isArray(value)) value.forEach(item => values(item, output));
  else if (value && typeof value === 'object') Object.values(value).forEach(item => values(item, output));
}

function visibleHtmlStrings(source, output) {
  source = source.replace(/<script\b[\s\S]*?<\/script>/gi, '').replace(/<style\b[\s\S]*?<\/style>/gi, '');
  for (const match of source.matchAll(/>([^<>]+)</g)) {
    const text = match[1].replace(/&amp;/g, '&').replace(/&nbsp;/g, ' ').replace(/&rarr;/g, '→').trim();
    if (/[A-Za-z]/.test(text)) output.add(text);
  }
  for (const match of source.matchAll(/\b(?:placeholder|title|aria-label|content)="([^"]*[A-Za-z][^"]*)"/g)) {
    if (!/^https?:|^width=device|^no-cache|^Showcase Maker$/i.test(match[1])) output.add(match[1]);
  }
}

function likelyUiLiteral(value) {
  if (/^(?:blob:|restored\.)/.test(value)) return false;
  if (!/[A-Za-z]/.test(value) || value.length < 2 || value.length > 700) return false;
  /* Concatenated HTML, selectors, source code and CSS are not interface copy. */
  if (/[<>{}=`\\]/.test(value) || /\b(?:class|href|src|aria-|data-|querySelector|getElementById)\b/.test(value)) return false;
  if (/^(?:https?:|\/|\.|#|\[|data-|aria-|application\/|image\/|video\/|[a-z]+:[a-z]|[A-Z0-9_-]{2,})/.test(value)) return false;
  if (/^[a-z0-9_-]+$/.test(value) && !/^(?:loading|ready|error|close|open|save|delete|profile|gallery|tools|account|free|pro)$/i.test(value)) return false;
  return /\s|[.!?…:→·]/.test(value) || /^[A-Z][a-z]+$/.test(value);
}

function jsUiStrings(source, output) {
  const literal = /(['"])((?:\\.|(?!\1)[^\\\r\n])*)\1/g;
  for (const match of source.matchAll(literal)) {
    let value;
    try { value = Function(`return ${match[0]}`)(); } catch (_) { continue; }
    if (likelyUiLiteral(value)) output.add(value);
  }
}

const strings = new Set();
for (const [file, marker] of sourceFiles) {
  const source = fs.readFileSync(path.join(root, file), 'utf8');
  const dictionary = Function(`"use strict";return (${objectLiteral(source, marker)});`)();
  values(dictionary.en || {}, strings);
}
for (const file of ['static/index.html', 'static/app.html', 'static/profile.html', 'static/profile-view.html', 'static/gallery.html']) {
  visibleHtmlStrings(fs.readFileSync(path.join(root, file), 'utf8'), strings);
}
visibleHtmlStrings(fs.readFileSync(path.join(root, 'static/privacy-en.html'), 'utf8'), strings);
const uiLiteralFiles = [
  'static/ss-shell.js', 'static/js/home.js', 'static/js/job-center.js',
  'static/js/app.js', 'static/js/app-tail.js', 'static/js/gallery.js',
  'static/js/profile.js', 'static/js/profile-insights.js', 'static/js/support-chat.js',
  'static/js/seamless-loop.js', 'static/js/showcase-builder.js',
  'static/js/steam-check.js', 'static/js/steam-mockup.js',
  'static/js/steam-extension-status.js', 'static/js/layout-refinement.js',
  'static/js/sm-auth.js'
];
for (const file of uiLiteralFiles) jsUiStrings(fs.readFileSync(path.join(root, file), 'utf8'), strings);
values(JSON.parse(fs.readFileSync(path.join(root, 'smweb/support_knowledge.json'), 'utf8')).map(item => item.en), strings);

const skip = /^(?:Steam|Showcase Maker|SteamShowcase Helper|Discord|Google|Telegram|Groq|Gemini|DeviantArt|Workshop|Featured|Artwork Split|GIF|PNG|JPG|WEBP|WebM|MP4|MOV|AVI|FFmpeg|gifski|HEX 21|FAQ|Pro|Free|LIVE)$/i;
const sourceStrings = [...strings].filter(value => /[A-Za-z]/.test(value) && !/[А-Яа-яЁёІіЇїЄє]/.test(value) && !skip.test(value.trim())).sort((a, b) => a.localeCompare(b));
const cachePath = path.join(root, 'scripts', '.locale-cache.json');
let cache = {};
try { cache = JSON.parse(fs.readFileSync(cachePath, 'utf8')); } catch (_) {}
const protectedTerms = ['Showcase Maker', 'SteamShowcase Helper', 'SteamShowcase', 'showcasemaker.com', 'Artwork Split', 'Workshop', 'Featured', 'Steam', 'ZIP', 'BG', 'HEX'];
if (cache._productMaskVersion !== 3) {
  for (const language of targets) {
    for (const text of Object.keys(cache[language] || {})) {
      if (protectedTerms.some(term => text.includes(term))) delete cache[language][text];
    }
  }
  cache._productMaskVersion = 3;
}

const overrides = {
  de: {
    'Showcase Maker — Steam showcases without the grind':'Showcase Maker — Steam-Vitrinen ohne Aufwand',
    'Steam showcases.':'Steam-Vitrinen.','Revitalized':'Ohne Routine',
    'Workshop, Featured and Split cuts, watermark, Steam size limits, source downloads and profile preview — one browser tool for creators.':'Workshop-, Featured- und Split-Zuschnitt, Wasserzeichen, Steam-Größenlimits, Quelldownloads und Profilvorschau – ein Browser-Tool für Kreative.',
    'Process':'Verarbeitung','Character':'Charakter','Character + BG':'Charakter + Hintergrund','Builder':'Editor','Upscale':'Hochskalieren','Upscale artwork':'Bild hochskalieren','About':'Über den Dienst','Steam Check':'Steam-Prüfung','HEX':'HEX',
    'Profile Rating':'Profilbewertung','Design Selection':'Designauswahl',
    'TELEGRAM / 7-DAY ACCESS':'TELEGRAM / 7 TAGE ZUGANG','Get 7 days of Pro free':'7 Tage Pro kostenlos','Join the channel and claim your free key.':'Abonniere den Kanal und sichere dir deinen kostenlosen Schlüssel.','Get the key':'Schlüssel sichern','7D':'7T',
    'Open tools':'Tools öffnen','Open tools →':'Tools öffnen →',
    'Open Showcase Maker':'Showcase Maker öffnen','Log in':'Anmelden','Log out':'Abmelden','Sign up':'Registrieren',
    'Tools':'Tools','Profile':'Profil','Gallery':'Galerie','Feed':'Feed','Pricing':'Preise','Support':'Support','Home':'Startseite',
    'Steam profile editor — Showcase Maker':'Steam-Profil-Editor — Showcase Maker',
    'Privacy policy':'Datenschutzerklärung','Privacy policy · Showcase Maker / SteamShowcase Helper':'Datenschutzerklärung · Showcase Maker / SteamShowcase Helper',
    'How SteamShowcase Helper and Showcase Maker handle data: Steam import, local files, retention and deletion.':'Wie SteamShowcase Helper und Showcase Maker Daten verarbeiten: Steam-Import, lokale Dateien, Speicherung und Löschung.',
    'Skip to policy':'Direkt zur Datenschutzerklärung','Contents':'Inhalt','← Back to site':'← Zurück zur Website',
    'Scope and contact':'Geltungsbereich und Kontakt','Requests to Steam and credentials':'Steam-Anfragen und Zugangsdaten',
    'Importing a profile into the website':'Profilimport auf die Website','Why browser permissions are used':'Warum Browserberechtigungen erforderlich sind',
    'Separate website services':'Separate Website-Dienste','Retention, deletion and your choices':'Speicherung, Löschung und Ihre Wahlmöglichkeiten',
    'Limited Use, sharing and security':'Eingeschränkte Nutzung, Weitergabe und Sicherheit',
    'Assistant':'Assistent','How can we help?':'Wie können wir helfen?'
  },
  tr: {
    'Showcase Maker — Steam showcases without the grind':'Showcase Maker — Zahmetsiz Steam vitrinleri',
    'Steam showcases.':'Steam vitrinleri.','Revitalized':'Rutinsiz',
    'Workshop, Featured and Split cuts, watermark, Steam size limits, source downloads and profile preview — one browser tool for creators.':'Workshop, Featured ve Split kesimi, filigran, Steam boyut sınırları, kaynak dosyalarını indirme ve profil önizleme — içerik üreticileri için tarayıcıda tek araç.',
    'Process':'İşleme','Character':'Karakter','Character + BG':'Karakter + arka plan','Builder':'Düzenleyici','Upscale':'Görüntü büyütme','Upscale artwork':'Görseli büyüt','About':'Hizmet hakkında','Steam Check':'Steam Kontrolü','HEX':'HEX',
    'Profile Rating':'Profil Değerlendirmesi','Design Selection':'Tasarım Seçimi',
    'TELEGRAM / 7-DAY ACCESS':'TELEGRAM / 7 GÜNLÜK ERİŞİM','Get 7 days of Pro free':'7 gün Pro ücretsiz','Join the channel and claim your free key.':'Kanala katıl ve ücretsiz anahtarını al.','Get the key':'Anahtarı al',
    'Open tools':'Araçları aç','Open tools →':'Araçları aç →',
    'Open Showcase Maker':"Showcase Maker’ı aç",'Log in':'Giriş yap','Log out':'Çıkış yap','Sign up':'Kayıt ol',
    'Tools':'Araçlar','Profile':'Profil','Gallery':'Galeri','Pricing':'Fiyatlar','Support':'Destek',
    'Privacy policy':'Gizlilik politikası','Assistant':'Asistan','How can we help?':'Nasıl yardımcı olabiliriz?'
  },
  fr: {
    'Showcase Maker — Steam showcases without the grind':'Showcase Maker — Des vitrines Steam sans effort',
    'Steam showcases.':'Vitrines Steam.','Revitalized':'Sans routine',
    'Workshop, Featured and Split cuts, watermark, Steam size limits, source downloads and profile preview — one browser tool for creators.':'Découpe Workshop, Featured et Split, filigrane, limites Steam, téléchargement des sources et aperçu du profil : un seul outil dans le navigateur pour les créateurs.',
    'Process':'Traitement','Character':'Personnage','Character + BG':'Personnage + arrière-plan','Builder':'Éditeur','Upscale':'Agrandissement','Upscale artwork':'Agrandir l’image','About':'À propos du service','Steam Check':'Vérification Steam','HEX':'HEX',
    'Profile Rating':'Évaluation du profil','Design Selection':'Sélection de design',
    'TELEGRAM / 7-DAY ACCESS':'TELEGRAM / ACCÈS 7 JOURS','Get 7 days of Pro free':'7 jours de Pro offerts','Join the channel and claim your free key.':'Rejoignez le canal et récupérez votre clé gratuite.','Get the key':'Obtenir la clé',
    'Open tools':'Ouvrir les outils','Open tools →':'Ouvrir les outils →',
    'Open Showcase Maker':'Ouvrir Showcase Maker','Log in':'Se connecter','Log out':'Se déconnecter','Sign up':'Créer un compte',
    'Tools':'Outils','Profile':'Profil','Gallery':'Galerie','Pricing':'Tarifs','Support':'Assistance',
    'Privacy policy':'Politique de confidentialité','Assistant':'Assistant','How can we help?':'Comment pouvons-nous vous aider ?'
  },
  uk: {
    'Showcase Maker — Steam showcases without the grind':'Showcase Maker — Вітрини Steam без рутини',
    'Steam showcases.':'Вітрини Steam.','Revitalized':'Без рутини',
    'Workshop, Featured and Split cuts, watermark, Steam size limits, source downloads and profile preview — one browser tool for creators.':'Нарізка Workshop, Featured і Split, водяний знак, ліміти Steam, завантаження вихідних файлів і попередній перегляд профілю — один інструмент у браузері для авторів.',
    'Process':'Обробка','Character':'Персонаж','Character + BG':'Персонаж + фон','Builder':'Редактор','Upscale':'Збільшення','Upscale artwork':'Збільшити зображення','About':'Про сервіс','Steam Check':'Перевірка Steam','HEX':'HEX',
    'Profile Rating':'Оцінка профілю','Design Selection':'Підбір оформлення',
    'TELEGRAM / 7-DAY ACCESS':'TELEGRAM / ДОСТУП НА 7 ДНІВ','Get 7 days of Pro free':'Отримайте 7 днів Pro безкоштовно','Join the channel and claim your free key.':'Підпишіться на канал і заберіть безкоштовний ключ.','Get the key':'Отримати ключ',
    'Open tools':'Відкрити інструменти','Open tools →':'Відкрити інструменти →',
    'Open Showcase Maker':'Відкрити Showcase Maker','Log in':'Увійти','Log out':'Вийти','Sign up':'Зареєструватися',
    'Tools':'Інструменти','Profile':'Профіль','Gallery':'Галерея','Feed':'Стрічка','Pricing':'Ціни','Support':'Підтримка',
    'Privacy policy':'Політика конфіденційності','Assistant':'Асистент','How can we help?':'Чим можемо допомогти?'
  },
  es: {
    'Showcase Maker — Steam showcases without the grind':'Showcase Maker — Vitrinas de Steam sin complicaciones',
    'Steam showcases.':'Vitrinas de Steam.','Revitalized':'Sin rutina',
    'Workshop, Featured and Split cuts, watermark, Steam size limits, source downloads and profile preview — one browser tool for creators.':'Recortes Workshop, Featured y Split, marca de agua, límites de Steam, descarga de archivos originales y vista previa del perfil: una sola herramienta en el navegador para creadores.',
    'Process':'Procesamiento','Character':'Personaje','Character + BG':'Personaje + fondo','Builder':'Editor','Upscale':'Ampliación','Upscale artwork':'Ampliar imagen','About':'Acerca del servicio','Steam Check':'Comprobación de Steam','HEX':'HEX',
    'Profile Rating':'Evaluación del perfil','Design Selection':'Selección de diseño',
    'TELEGRAM / 7-DAY ACCESS':'TELEGRAM / ACCESO DE 7 DÍAS','Get 7 days of Pro free':'7 días de Pro gratis','Join the channel and claim your free key.':'Únete al canal y consigue tu clave gratuita.','Get the key':'Obtener la clave',
    'Open tools':'Abrir herramientas','Open tools →':'Abrir herramientas →',
    'Open Showcase Maker':'Abrir Showcase Maker','Log in':'Iniciar sesión','Log out':'Cerrar sesión','Sign up':'Crear una cuenta',
    'Tools':'Herramientas','Profile':'Perfil','Gallery':'Galería','Pricing':'Precios','Support':'Soporte',
    'Privacy policy':'Política de privacidad','Assistant':'Asistente','How can we help?':'¿Cómo podemos ayudarte?'
  },
  pt: {
    'Showcase Maker — Steam showcases without the grind':'Showcase Maker — Vitrines da Steam sem complicações',
    'Steam showcases.':'Vitrines da Steam.','Revitalized':'Sem rotina',
    'Workshop, Featured and Split cuts, watermark, Steam size limits, source downloads and profile preview — one browser tool for creators.':'Recortes Workshop, Featured e Split, marca-d’água, limites da Steam, download dos arquivos originais e prévia do perfil — uma única ferramenta no navegador para criadores.',
    'Process':'Processamento','Character':'Personagem','Character + BG':'Personagem + fundo','Builder':'Editor','Upscale':'Ampliação','Upscale artwork':'Ampliar imagem','About':'Sobre o serviço','Steam Check':'Verificação Steam','HEX':'HEX',
    'Profile Rating':'Avaliação do perfil','Design Selection':'Seleção de design',
    'TELEGRAM / 7-DAY ACCESS':'TELEGRAM / ACESSO POR 7 DIAS','Get 7 days of Pro free':'Ganhe 7 dias de Pro grátis','Join the channel and claim your free key.':'Entre no canal e resgate sua chave gratuita.','Get the key':'Resgatar chave',
    'Open tools':'Abrir ferramentas','Open tools →':'Abrir ferramentas →',
    'Open Showcase Maker':'Abrir o Showcase Maker','Log in':'Entrar','Log out':'Sair','Sign up':'Criar conta',
    'Tools':'Ferramentas','Profile':'Perfil','Gallery':'Galeria','Pricing':'Preços','Support':'Suporte',
    'Privacy policy':'Política de privacidade','Assistant':'Assistente','How can we help?':'Como podemos ajudar?'
  }
};

const taskCopyOverrides = {
  de: {
    'Saving reusable sources…':'Wiederverwendbare Quellen werden gespeichert…',
    'resumable upload unavailable, using compatibility upload':'Fortsetzbarer Upload nicht verfügbar, Kompatibilitäts-Upload wird verwendet',
    'Cancel job':'Auftrag abbrechen','Processing cancelled':'Verarbeitung abgebrochen',
    'compose reusable upload unavailable':'Wiederverwendbarer Upload für die Komposition ist nicht verfügbar',
    'upscale reusable upload unavailable':'Wiederverwendbarer Upload für die Hochskalierung ist nicht verfügbar','Job cancelled':'Auftrag abgebrochen'
  },
  tr: {
    'Saving reusable sources…':'Yeniden kullanılabilir kaynaklar kaydediliyor…',
    'resumable upload unavailable, using compatibility upload':'Devam ettirilebilir yükleme kullanılamıyor, uyumluluk yüklemesi kullanılıyor',
    'Cancel job':'Görevi iptal et','Processing cancelled':'İşleme iptal edildi',
    'compose reusable upload unavailable':'Kompozisyon için yeniden kullanılabilir yükleme kullanılamıyor',
    'upscale reusable upload unavailable':'Büyütme için yeniden kullanılabilir yükleme kullanılamıyor','Job cancelled':'Görev iptal edildi'
  },
  fr: {
    'Saving reusable sources…':'Enregistrement des sources réutilisables…',
    'resumable upload unavailable, using compatibility upload':'Téléversement reprenable indisponible, utilisation du mode compatible',
    'Cancel job':'Annuler la tâche','Processing cancelled':'Traitement annulé',
    'compose reusable upload unavailable':'Téléversement réutilisable indisponible pour la composition',
    'upscale reusable upload unavailable':'Téléversement réutilisable indisponible pour l’agrandissement','Job cancelled':'Tâche annulée'
  },
  uk: {
    'Saving reusable sources…':'Зберігаємо багаторазові джерела…',
    'resumable upload unavailable, using compatibility upload':'Відновлюване завантаження недоступне, використовується сумісний режим',
    'Cancel job':'Скасувати завдання','Processing cancelled':'Обробку скасовано',
    'compose reusable upload unavailable':'Багаторазове завантаження для композиції недоступне',
    'upscale reusable upload unavailable':'Багаторазове завантаження для збільшення недоступне','Job cancelled':'Завдання скасовано'
  },
  es: {
    'Saving reusable sources…':'Guardando fuentes reutilizables…',
    'resumable upload unavailable, using compatibility upload':'La carga reanudable no está disponible; se usa la carga compatible',
    'Cancel job':'Cancelar tarea','Processing cancelled':'Procesamiento cancelado',
    'compose reusable upload unavailable':'La carga reutilizable para composición no está disponible',
    'upscale reusable upload unavailable':'La carga reutilizable para ampliación no está disponible','Job cancelled':'Tarea cancelada'
  },
  pt: {
    'Saving reusable sources…':'Salvando fontes reutilizáveis…',
    'resumable upload unavailable, using compatibility upload':'Upload retomável indisponível; usando o modo de compatibilidade',
    'Cancel job':'Cancelar tarefa','Processing cancelled':'Processamento cancelado',
    'compose reusable upload unavailable':'Upload reutilizável para composição indisponível',
    'upscale reusable upload unavailable':'Upload reutilizável para ampliação indisponível','Job cancelled':'Tarefa cancelada'
  }
};
const automaticUploadCopyKeys = [
  'Manual upload', 'Upload automatically', 'Automatic upload requires SteamShowcase Helper 1.0.3 or newer.',
  'Preparing verified files for the extension…', 'The automatic upload queue is open in the extension.',
  'Processing complete. The ZIP is downloading automatically; review Steam readiness.',
  'Loading backgrounds…', 'All backgrounds loaded', 'Could not load the next page',
  'Manual extension upload', 'Open file selection', 'Opening the ready-file selector…',
  'File selection is open in the extension.', 'No backgrounds found', 'Retry loading'
];
const automaticUploadCopy = {
  de: ['Manuell hochladen','Automatisch hochladen','Für den automatischen Upload ist SteamShowcase Helper 1.0.3 oder neuer erforderlich.','Geprüfte Dateien werden an die Erweiterung übergeben…','Die Warteschlange für den automatischen Upload ist in der Erweiterung geöffnet.','Verarbeitung abgeschlossen. Das ZIP wird automatisch heruntergeladen; prüfe die Steam-Bereitschaft.','Hintergründe werden geladen…','Alle Hintergründe geladen','Die nächste Seite konnte nicht geladen werden','Manueller Upload mit Erweiterung','Dateiauswahl öffnen','Auswahl der fertigen Dateien wird geöffnet…','Die Dateiauswahl ist in der Erweiterung geöffnet.','Keine Hintergründe gefunden','Erneut laden'],
  tr: ['Elle yükle','Otomatik yükle','Otomatik yükleme için SteamShowcase Helper 1.0.3 veya üzeri gerekir.','Kontrol edilen dosyalar eklentiye aktarılıyor…','Otomatik yükleme kuyruğu eklentide açıldı.','İşleme tamamlandı. ZIP otomatik indiriliyor; Steam uygunluğunu kontrol et.','Arka planlar yükleniyor…','Tüm arka planlar yüklendi','Sonraki sayfa yüklenemedi','Eklentiyle elle yükle','Dosya seçimini aç','Hazır dosya seçimi açılıyor…','Dosya seçimi eklentide açıldı.','Arka plan bulunamadı','Yeniden yükle'],
  fr: ['Importer manuellement','Importer automatiquement','L’import automatique nécessite SteamShowcase Helper 1.0.3 ou une version ultérieure.','Transfert des fichiers vérifiés vers l’extension…','La file d’import automatique est ouverte dans l’extension.','Traitement terminé. Le ZIP se télécharge automatiquement ; vérifiez la compatibilité Steam.','Chargement des fonds…','Tous les fonds sont chargés','Impossible de charger la page suivante','Import manuel avec l’extension','Ouvrir la sélection des fichiers','Ouverture de la sélection des fichiers prêts…','La sélection des fichiers est ouverte dans l’extension.','Aucun fond trouvé','Réessayer le chargement'],
  uk: ['Завантажити вручну','Завантажити автоматично','Для автоматичного завантаження потрібен SteamShowcase Helper 1.0.3 або новіший.','Передаємо перевірені файли в розширення…','Чергу автоматичного завантаження відкрито в розширенні.','Обробку завершено. ZIP завантажується автоматично; перевір готовність для Steam.','Завантажуємо фони…','Усі фони завантажено','Не вдалося завантажити наступну сторінку','Ручне завантаження через розширення','Відкрити вибір файлів','Відкриваємо вибір готових файлів…','Вибір файлів відкрито в розширенні.','Фони не знайдено','Повторити завантаження'],
  es: ['Subir manualmente','Subir automáticamente','La subida automática requiere SteamShowcase Helper 1.0.3 o una versión posterior.','Enviando los archivos comprobados a la extensión…','La cola de subida automática está abierta en la extensión.','Procesamiento terminado. El ZIP se descarga automáticamente; revisa la compatibilidad con Steam.','Cargando fondos…','Todos los fondos cargados','No se pudo cargar la página siguiente','Subida manual con la extensión','Abrir selección de archivos','Abriendo la selección de archivos listos…','La selección de archivos está abierta en la extensión.','No se encontraron fondos','Reintentar la carga'],
  pt: ['Enviar manualmente','Enviar automaticamente','O envio automático requer SteamShowcase Helper 1.0.3 ou mais recente.','Enviando os arquivos verificados para a extensão…','A fila de envio automático está aberta na extensão.','Processamento concluído. O ZIP está sendo baixado automaticamente; confira a compatibilidade com a Steam.','Carregando fundos…','Todos os fundos carregados','Não foi possível carregar a próxima página','Envio manual pela extensão','Abrir seleção de arquivos','Abrindo a seleção dos arquivos prontos…','A seleção de arquivos está aberta na extensão.','Nenhum fundo encontrado','Tentar carregar novamente']
};
for (const language of targets) {
  automaticUploadCopyKeys.forEach((key, index) => { taskCopyOverrides[language][key] = automaticUploadCopy[language][index]; });
}
const automaticUploadGuideKeys = [
  'Choose a showcase type, then open file selection for automatic upload or use the manual Steam handoff.',
  'Automatic: select files in the extension and start the queue.',
  'Manual: open Steam and choose the files yourself.',
  'Automatic upload selects files inside the extension. Manual upload lets you choose them on Steam.',
  'After Process, unpack the ZIP that downloaded automatically — those are your files.',
  'Run Process and unpack the automatically downloaded ZIP',
  'After Process, unpack the ZIP downloaded automatically — those are your files.',
  'After Process, unpack the ZIP downloaded automatically — those are your files. The browser cannot open a local folder for you.',
  'Open Process — run it and unpack the downloaded ZIP'
];
const automaticUploadGuideCopy = {
  de: ['Wähle eine Vitrine und öffne dann die Dateiauswahl für den automatischen Upload oder nutze die manuelle Übergabe an Steam.','Automatisch: Dateien in der Erweiterung auswählen und die Warteschlange starten.','Manuell: Steam öffnen und die Dateien selbst auswählen.','Beim automatischen Upload wählst du Dateien in der Erweiterung aus, beim manuellen Upload auf Steam.','Entpacke nach der Verarbeitung das automatisch heruntergeladene ZIP – darin liegen deine Dateien.','Verarbeitung starten und das automatisch heruntergeladene ZIP entpacken','Entpacke nach der Verarbeitung das automatisch heruntergeladene ZIP – darin liegen deine Dateien.','Entpacke nach der Verarbeitung das automatisch heruntergeladene ZIP. Der Browser kann keinen lokalen Ordner für dich öffnen.','Verarbeitung öffnen, starten und das heruntergeladene ZIP entpacken'],
  tr: ['Vitrin türünü seç, sonra otomatik yükleme için dosya seçimini aç veya Steam’e elle aktar.','Otomatik: dosyaları eklentide seç ve kuyruğu başlat.','Elle: Steam’i aç ve dosyaları kendin seç.','Otomatik yüklemede dosyaları eklentide, elle yüklemede Steam’de seçersin.','İşlemden sonra otomatik indirilen ZIP’i aç; dosyaların orada.','İşlemi başlat ve otomatik indirilen ZIP’i aç','İşlemden sonra otomatik indirilen ZIP’i aç; dosyaların orada.','İşlemden sonra otomatik indirilen ZIP’i aç. Tarayıcı yerel klasörü senin için açamaz.','İşleme sayfasını aç, çalıştır ve indirilen ZIP’i aç'],
  fr: ['Choisissez un type de vitrine, puis ouvrez la sélection des fichiers pour l’import automatique ou passez manuellement par Steam.','Automatique : choisissez les fichiers dans l’extension et lancez la file.','Manuel : ouvrez Steam et choisissez les fichiers vous-même.','L’import automatique sélectionne les fichiers dans l’extension ; en mode manuel, choisissez-les sur Steam.','Après le traitement, décompressez le ZIP téléchargé automatiquement : il contient vos fichiers.','Lancer le traitement et décompresser le ZIP téléchargé automatiquement','Après le traitement, décompressez le ZIP téléchargé automatiquement : il contient vos fichiers.','Après le traitement, décompressez le ZIP téléchargé automatiquement. Le navigateur ne peut pas ouvrir un dossier local à votre place.','Ouvrir le traitement, le lancer et décompresser le ZIP téléchargé'],
  uk: ['Обери тип вітрини, а потім відкрий вибір файлів для автозавантаження або передай їх у Steam вручну.','Автоматично: обери файли в розширенні та запусти чергу.','Вручну: відкрий Steam і сам обери файли.','Для автозавантаження обирай файли в розширенні, для ручного — на сторінці Steam.','Після обробки розпакуй ZIP, який завантажився автоматично, — там твої файли.','Запусти обробку та розпакуй автоматично завантажений ZIP','Після обробки розпакуй ZIP, який завантажився автоматично, — там твої файли.','Після обробки розпакуй автоматично завантажений ZIP. Браузер не може сам відкрити локальну папку.','Відкрий обробку, запусти її та розпакуй завантажений ZIP'],
  es: ['Elige un tipo de expositor y abre la selección de archivos para subir automáticamente o pásalos a Steam de forma manual.','Automático: elige los archivos en la extensión e inicia la cola.','Manual: abre Steam y elige los archivos tú mismo.','La subida automática selecciona los archivos en la extensión; la manual, en Steam.','Después del procesamiento, extrae el ZIP descargado automáticamente: ahí están tus archivos.','Procesar y extraer el ZIP descargado automáticamente','Después del procesamiento, extrae el ZIP descargado automáticamente: ahí están tus archivos.','Después del procesamiento, extrae el ZIP descargado automáticamente. El navegador no puede abrir una carpeta local por ti.','Abrir Procesar, ejecutarlo y extraer el ZIP descargado'],
  pt: ['Escolha o tipo de vitrine e abra a seleção de arquivos para o envio automático ou faça o envio manual pela Steam.','Automático: selecione os arquivos na extensão e inicie a fila.','Manual: abra a Steam e escolha os arquivos.','No envio automático, selecione os arquivos na extensão; no manual, na Steam.','Após o processamento, extraia o ZIP baixado automaticamente: seus arquivos estão nele.','Processar e extrair o ZIP baixado automaticamente','Após o processamento, extraia o ZIP baixado automaticamente: seus arquivos estão nele.','Após o processamento, extraia o ZIP baixado automaticamente. O navegador não pode abrir uma pasta local para você.','Abra o processamento, execute e extraia o ZIP baixado']
};
for (const language of targets) {
  automaticUploadGuideKeys.forEach((key, index) => { taskCopyOverrides[language][key] = automaticUploadGuideCopy[language][index]; });
}
const supportTicketCopyKeys = [
  'Dismiss announcement', 'Report a problem', 'What happened?', 'Reply email (optional)',
  'Send report', 'Sending…', 'Report received. ID:', 'Too many reports were sent today.', 'Could not send. Please try later.'
];
const supportTicketCopy = {
  de: ['Ankündigung schließen','Problem melden','Was ist passiert?','E-Mail für Rückfragen (optional)','Meldung senden','Wird gesendet…','Meldung erhalten. ID:','Heute wurden zu viele Meldungen gesendet.','Senden fehlgeschlagen. Bitte später erneut versuchen.'],
  tr: ['Duyuruyu kapat','Sorun bildir','Ne oldu?','Yanıt e-postası (isteğe bağlı)','Bildirimi gönder','Gönderiliyor…','Bildirim alındı. Kimlik:','Bugün çok fazla bildirim gönderildi.','Gönderilemedi. Lütfen daha sonra tekrar deneyin.'],
  fr: ['Fermer l’annonce','Signaler un problème','Que s’est-il passé ?','E-mail de réponse (facultatif)','Envoyer le signalement','Envoi…','Signalement reçu. ID :','Trop de signalements ont été envoyés aujourd’hui.','Envoi impossible. Réessayez plus tard.'],
  uk: ['Закрити оголошення','Повідомити про проблему','Що сталося?','Email для відповіді (необов’язково)','Надіслати звернення','Надсилаємо…','Звернення прийнято. Номер:','Сьогодні надіслано забагато звернень.','Не вдалося надіслати. Спробуйте пізніше.'],
  es: ['Cerrar anuncio','Informar de un problema','¿Qué ocurrió?','Correo de respuesta (opcional)','Enviar informe','Enviando…','Informe recibido. ID:','Hoy se han enviado demasiados informes.','No se pudo enviar. Inténtalo más tarde.'],
  pt: ['Fechar aviso','Relatar um problema','O que aconteceu?','E-mail para resposta (opcional)','Enviar relato','Enviando…','Relato recebido. ID:','Muitos relatos foram enviados hoje.','Não foi possível enviar. Tente novamente mais tarde.']
};
for (const language of targets) {
  supportTicketCopyKeys.forEach((key, index) => { taskCopyOverrides[language][key] = supportTicketCopy[language][index]; });
}
const authRecoveryCopyKeys = [
  'Telegram sign-in was not completed. Please try again.',
  'An account with this email already exists. Use the log in button below or reset your password.',
  'Already have an account? Log in',
  'We sent a code to your email. Enter it to complete registration.',
  'Confirm sign-in in Telegram…',
  'Could not load Telegram sign-in. Please try again.'
];
const authRecoveryCopy = {
  de: ['Die Telegram-Anmeldung wurde nicht abgeschlossen. Bitte versuche es erneut.','Ein Konto mit dieser E-Mail-Adresse existiert bereits. Melde dich unten an oder setze dein Passwort zurück.','Du hast schon ein Konto? Anmelden','Wir haben einen Code an deine E-Mail-Adresse gesendet. Gib ihn ein, um die Registrierung abzuschließen.','Bestätige die Anmeldung in Telegram…','Die Telegram-Anmeldung konnte nicht geladen werden. Bitte versuche es erneut.'],
  tr: ['Telegram ile giriş tamamlanmadı. Lütfen tekrar deneyin.','Bu e-posta adresiyle bir hesap zaten var. Aşağıdan giriş yapın veya şifrenizi sıfırlayın.','Zaten hesabınız var mı? Giriş yapın','E-postanıza bir kod gönderdik. Kaydı tamamlamak için kodu girin.','Telegram’da girişi onaylayın…','Telegram ile giriş yüklenemedi. Lütfen tekrar deneyin.'],
  fr: ['La connexion avec Telegram n’a pas été terminée. Réessayez.','Un compte existe déjà avec cette adresse e-mail. Connectez-vous ci-dessous ou réinitialisez votre mot de passe.','Déjà un compte ? Se connecter','Nous avons envoyé un code à votre adresse e-mail. Saisissez-le pour terminer l’inscription.','Confirmez la connexion dans Telegram…','Impossible de charger la connexion Telegram. Réessayez.'],
  uk: ['Вхід через Telegram не завершено. Спробуйте ще раз.','Обліковий запис із цією електронною адресою вже існує. Увійдіть нижче або відновіть пароль.','Уже маєте обліковий запис? Увійти','Ми надіслали код на вашу пошту. Введіть його, щоб завершити реєстрацію.','Підтвердьте вхід у Telegram…','Не вдалося завантажити вхід через Telegram. Спробуйте ще раз.'],
  es: ['No se completó el inicio de sesión con Telegram. Inténtalo de nuevo.','Ya existe una cuenta con esta dirección de correo. Inicia sesión abajo o restablece tu contraseña.','¿Ya tienes una cuenta? Inicia sesión','Te enviamos un código por correo. Introdúcelo para completar el registro.','Confirma el inicio de sesión en Telegram…','No se pudo cargar el inicio de sesión con Telegram. Inténtalo de nuevo.'],
  pt: ['O login pelo Telegram não foi concluído. Tente novamente.','Já existe uma conta com este endereço de e-mail. Entre abaixo ou redefina sua senha.','Já tem uma conta? Entrar','Enviamos um código para seu e-mail. Digite-o para concluir o cadastro.','Confirme o login no Telegram…','Não foi possível carregar o login pelo Telegram. Tente novamente.']
};
for (const language of targets) {
  authRecoveryCopyKeys.forEach((key, index) => { taskCopyOverrides[language][key] = authRecoveryCopy[language][index]; });
}
const workshopSupportKeys = [
  'Workshop Studio', 'Prepare one file for each Workshop row',
  'Prepare one full-height file for each Workshop row',
  'How would you like to contact us?',
  'Choose a channel. A report sent here uses the same form as “Report a problem”.',
  'Open Telegram ↗', 'Report a problem on the site', 'Value'
];
const workshopSupportCopy = {
  de:['Workshop-Studio','Bereite eine Datei für jede Workshop-Reihe vor','Bereite für jede Workshop-Reihe eine Datei in voller Höhe vor','Wie möchtest du uns kontaktieren?','Wähle einen Weg. Die Meldung nutzt dasselbe Formular wie „Problem melden“.','Telegram öffnen ↗','Problem auf der Website melden','Wert'],
  tr:['Workshop Stüdyosu','Her Workshop satırı için bir dosya hazırla','Her Workshop satırı için tam boy bir dosya hazırla','Bizimle nasıl iletişime geçmek istersin?','Bir yöntem seç. Buradaki bildirim “Sorun bildir” ile aynı formu kullanır.','Telegram’ı aç ↗','Siteden sorun bildir','Değer'],
  fr:['Studio Workshop','Préparez un fichier pour chaque rangée Workshop','Préparez un fichier en pleine hauteur pour chaque rangée Workshop','Comment souhaitez-vous nous contacter ?','Choisissez un moyen. Ce signalement utilise le même formulaire que « Signaler un problème ».','Ouvrir Telegram ↗','Signaler un problème sur le site','Valeur'],
  uk:['Майстерня Workshop','Підготуй файл для кожного ряду вітрини','Підготуй файл повної висоти для кожного ряду вітрини','Як хочеш зв’язатися з нами?','Обери спосіб. Звернення використовує ту саму форму, що й «Повідомити про проблему».','Відкрити Telegram ↗','Повідомити про проблему на сайті','Значення'],
  es:['Estudio Workshop','Prepara un archivo para cada fila Workshop','Prepara un archivo de altura completa para cada fila Workshop','¿Cómo quieres contactarnos?','Elige un canal. Este aviso usa el mismo formulario que «Informar de un problema».','Abrir Telegram ↗','Informar de un problema en el sitio','Valor'],
  pt:['Estúdio Workshop','Prepare um arquivo para cada linha Workshop','Prepare um arquivo de altura completa para cada linha Workshop','Como deseja falar conosco?','Escolha um canal. Este relato usa o mesmo formulário de «Relatar um problema».','Abrir Telegram ↗','Relatar um problema no site','Valor']
};
for (const language of targets) workshopSupportKeys.forEach((key,index)=>{taskCopyOverrides[language][key]=workshopSupportCopy[language][index]});
/* Hand-reviewed strings (landing blocks, job center, My results) kept outside this file. */
const reviewed = JSON.parse(fs.readFileSync(path.join(root, 'scripts', 'locale_reviewed.json'), 'utf8'));
for (const language of targets) Object.assign(taskCopyOverrides[language], reviewed[language] || {});
for (const language of targets) Object.assign(overrides[language], taskCopyOverrides[language]);

function maskProducts(text) {
  let output = text;
  protectedTerms.forEach((term, index) => { output = output.split(term).join(`__SMTERM${index}__`); });
  return output;
}

function unmaskProducts(text) {
  let output = text;
  protectedTerms.forEach((term, index) => { output = output.split(`__SMTERM${index}__`).join(term); });
  return output;
}

const delimiter = '\n<<<SMSEP>>>\n';
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

async function requestTranslation(text, language) {
  const url = `https://lingva.ml/api/v1/en/${language}/${encodeURIComponent(text)}`;
  for (let attempt = 0; attempt < 5; attempt += 1) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(45000), headers: { 'User-Agent': 'ShowcaseMaker locale builder' } });
      if (response.status === 429) {
        await wait(20000);
        throw new Error('HTTP 429');
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const body = await response.json();
      if (!body.translation) throw new Error('Empty translation');
      return body.translation;
    } catch (error) {
      if (attempt === 4) throw error;
      await wait(900 * (attempt + 1));
    }
  }
}

function batches(pending) {
  const result = [];
  let batch = [], length = 0;
  for (const text of pending) {
    const next = text.length + delimiter.length;
    if (batch.length && length + next > 2400) { result.push(batch); batch = []; length = 0; }
    batch.push(text); length += next;
  }
  if (batch.length) result.push(batch);
  return result;
}

async function translateLanguage(language) {
  cache[language] ||= {};
  const pending = sourceStrings.filter(text => !cache[language][text] && !overrides[language]?.[text]);
  const work = batches(pending);
  console.log(`${language}: ${pending.length} strings in ${work.length} batches`);
  for (let index = 0; index < work.length; index += 1) {
    const batch = work[index];
    const translated = await requestTranslation(batch.map(maskProducts).join(delimiter), language);
    let parts = translated.split(/\s*<<<SMSEP>>>\s*/);
    if (parts.length !== batch.length) {
      parts = [];
      for (const text of batch) parts.push(await requestTranslation(text, language));
    }
    batch.forEach((text, item) => { cache[language][text] = unmaskProducts(String(parts[item] || text).trim()); });
    fs.writeFileSync(cachePath, JSON.stringify(cache, null, 2));
    if ((index + 1) % 5 === 0 || index + 1 === work.length) console.log(`${language}: ${index + 1}/${work.length}`);
    await wait(2200);
  }
}

function translatedPrivacy(language) {
  let html = fs.readFileSync(path.join(root, 'static/privacy-en.html'), 'utf8');
  const translate = text => {
    const lead = text.match(/^\s*/)[0], tail = text.match(/\s*$/)[0], core = text.trim();
    return lead + (cache[language][core] || core) + tail;
  };
  html = html.replace('<html lang="en">', `<html lang="${language}">`);
  html = html.replace(/<link rel="canonical"[^>]*>/, `<link rel="canonical" href="https://showcasemaker.com/${language}/privacy">`);
  html = html.replace(/<link rel="alternate" hreflang="[^"]+"[^>]*>\s*/g, '');
  const allLanguages = ['en','ru', ...targets];
  const alternates = allLanguages.map(code => `<link rel="alternate" hreflang="${code}" href="https://showcasemaker.com/${code}/privacy">`).join('\n');
  html = html.replace('</head>', `${alternates}\n<link rel="alternate" hreflang="x-default" href="https://showcasemaker.com/en/privacy">\n</head>`);
  html = html.replace(/>([^<>]+)</g, (all, text) => /[A-Za-z]/.test(text) ? `>${translate(text)}<` : all);
  html = html.replace(/\b(placeholder|title|aria-label|content)="([^"]*[A-Za-z][^"]*)"/g, (all, attr, text) => `${attr}="${cache[language][text] || text}"`);
  html = html.replace(/<nav aria-label="[^"]*">[\s\S]*?<\/nav>/, `<nav aria-label="Language">${allLanguages.map(code => `<a href="/${code}/privacy" lang="${code}"${code === language ? ' aria-current="page"' : ''}>${code.toUpperCase()}</a>`).join('')}</nav>`);
  html = html.replace(/href="\/"/g, `href="/${language}/"`);
  html = html.replace(/<a class="brand" href="[^"]+"/, `<a class="brand" href="/${language}/"`);
  html = html.replace(/<a class="brand"([^>]*)>[\s\S]*?<\/a>/, `<a class="brand"$1><img src="/static/icon.png" width="40" height="40" alt=""><span>SHOWCASE <b>MAKER</b></span></a>`);
  html = html.replace(/<p class="eyebrow">[\s\S]*?<\/p>/, '<p class="eyebrow">STEAMSHOWCASE HELPER / SHOWCASE MAKER</p>');
  return html;
}

(async () => {
  if (process.argv.includes('--overrides-only')) {
    const file = path.join(root, 'static/js/locales-extra.js');
    const source = fs.readFileSync(file, 'utf8');
    const match = source.match(/window\.SM_EXTRA_TRANSLATIONS=(\{[\s\S]*\});\s*$/);
    if (!match) throw new Error('Generated extra locale bundle is invalid');
    const committed = JSON.parse(match[1]);
    for (const language of targets) Object.assign(committed[language], taskCopyOverrides[language]);
    fs.writeFileSync(file, '/* Generated by scripts/build_extra_locales.js. Do not edit by hand. */\n' +
      'window.SM_EXTRA_TRANSLATIONS=' + JSON.stringify(committed) + ';\n');
    console.log(`Applied reviewed task copy for ${targets.length} languages.`);
    return;
  }
  for (const language of targets) await translateLanguage(language);
  for (const language of targets) Object.assign(cache[language], overrides[language]);
  const committed = Object.fromEntries(targets.map(language => [language,
    Object.fromEntries(sourceStrings.map(text => [text, cache[language][text] || text]))
  ]));
  const output = '/* Generated by scripts/build_extra_locales.js. Do not edit by hand. */\n' +
    'window.SM_EXTRA_TRANSLATIONS=' + JSON.stringify(committed) + ';\n';
  fs.writeFileSync(path.join(root, 'static/js/locales-extra.js'), output);
  for (const language of targets) fs.writeFileSync(path.join(root, `static/privacy-${language}.html`), translatedPrivacy(language));
  console.log(`Wrote ${sourceStrings.length} source strings for ${targets.length} languages.`);
})().catch(error => { console.error(error); process.exitCode = 1; });
