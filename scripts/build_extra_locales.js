/* Generate committed client-side language packs from the existing English UI.
   This is a development tool only; production never calls a translation API. */
'use strict';
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const targets = ['de', 'tr', 'fr', 'uk', 'es', 'pt'];
const sourceFiles = [
  ['static/js/index.js', 'const I18N ='],
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
  'static/ss-shell.js', 'static/js/index.js', 'static/js/index-tail.js',
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
  const pending = sourceStrings.filter(text => !cache[language][text]);
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
