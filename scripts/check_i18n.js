/* Static audit for all shipped dictionaries and generated language packs. */
'use strict';
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');

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

function evaluateDictionary(jsFile, marker) {
  const source = fs.readFileSync(path.join(root, jsFile), 'utf8');
  return Function(`"use strict"; return (${objectLiteral(source, marker)});`)();
}

function attributeKeys(htmlFile) {
  const source = fs.readFileSync(path.join(root, htmlFile), 'utf8');
  return [...source.matchAll(/\sdata-i(?:-ph|-title|-html)?="([^"]+)"/g)].map(match => match[1]);
}

function check(name, dictionary, keys = []) {
  const en = dictionary.en || {}, ru = dictionary.ru || {};
  const errors = [];
  for (const key of Object.keys(en)) if (!(key in ru)) errors.push(`${name}: RU missing ${key}`);
  for (const key of Object.keys(ru)) if (!(key in en)) errors.push(`${name}: EN missing ${key}`);
  for (const key of new Set(keys)) {
    if (!(key in en)) errors.push(`${name}: data-i key missing in EN: ${key}`);
    if (!(key in ru)) errors.push(`${name}: data-i key missing in RU: ${key}`);
  }
  return errors;
}

function collectStrings(value, output = []) {
  if (typeof value === 'string') output.push(value);
  else if (Array.isArray(value)) value.forEach(item => collectStrings(item, output));
  else if (value && typeof value === 'object') Object.values(value).forEach(item => collectStrings(item, output));
  return output;
}

function likelyUiLiteral(value) {
  if (/^(?:blob:|restored\.)/.test(value)) return false;
  if (/^\s+is-[a-z-]+$/.test(value)) return false;
  if (!/[A-Za-z]/.test(value) || value.length < 2 || value.length > 700) return false;
  if (/[<>{}=`\\]/.test(value) || /\b(?:class|href|src|aria-|data-|querySelector|getElementById)\b/.test(value)) return false;
  if (/^(?:https?:|\/|\.|#|\[|data-|aria-|application\/|image\/|video\/|[a-z]+:[a-z]|[A-Z0-9_-]{2,})/.test(value)) return false;
  if (/^[a-z0-9_-]+$/.test(value) && !/^(?:loading|ready|error|close|open|save|delete|profile|gallery|tools|account|free|pro)$/i.test(value)) return false;
  return /\s|[.!?…:→·]/.test(value) || /^[A-Z][a-z]+$/.test(value);
}

function jsUiStrings(file, output) {
  let source = fs.readFileSync(path.join(root, file), 'utf8');
  /* These strings are reviewed in all eight languages in the source itself. */
  if (file === 'static/js/showcase-builder.js' && source.includes('var NEW_COPY =')) {
    source = source.replace(objectLiteral(source, 'var NEW_COPY ='), '{}');
  }
  if (file === 'static/js/steam-dna.js' && source.includes('var DNA_COPY=')) {
    source = source.replace(objectLiteral(source, 'var DNA_COPY='), '{}');
    if (source.includes('var AI_COPY=')) source = source.replace(objectLiteral(source, 'var AI_COPY='), '{}');
    if (source.includes('var LIVE_COPY=')) source = source.replace(objectLiteral(source, 'var LIVE_COPY='), '{}');
    if (source.includes('var DESIGN_COPY=')) source = source.replace(objectLiteral(source, 'var DESIGN_COPY='), '{}');
  }
  if (file === 'static/ss-shell.js') {
    for (const marker of ['var ACCOUNT_COPY =', 'var RESET_ERROR_COPY =']) {
      if (source.includes(marker)) source = source.replace(objectLiteral(source, marker), '{}');
    }
  }
  const literal = /(['"])((?:\\.|(?!\1)[^\\\r\n])*)\1/g;
  for (const match of source.matchAll(literal)) {
    let value;
    try { value = Function(`return ${match[0]}`)(); } catch (_) { continue; }
    if (likelyUiLiteral(value)) output.add(value);
  }
}

function extraPacks() {
  const source = fs.readFileSync(path.join(root, 'static/js/locales-extra.js'), 'utf8');
  const match = source.match(/window\.SM_EXTRA_TRANSLATIONS=(\{[\s\S]*\});\s*$/);
  if (!match) throw new Error('Generated extra locale bundle is invalid');
  return JSON.parse(match[1]);
}

const errors = [];
const workspaceWords = evaluateDictionary('static/js/workspace-copy.js', 'const words =');
for (const [key, translations] of Object.entries(workspaceWords)) {
  if (!Array.isArray(translations) || translations.length !== 8 || translations.some(value => typeof value !== 'string' || !value.trim())) errors.push(`workspace: incomplete translations for ${key}`);
}
const builderManual = evaluateDictionary('static/js/showcase-builder.js', 'var NEW_COPY =');
const builderManualKeys = Object.keys(builderManual.en || {}).sort().join('|');
for (const language of ['en','ru','de','tr','fr','uk','es','pt']) {
  if (Object.keys(builderManual[language] || {}).sort().join('|') !== builderManualKeys) errors.push(`builder manual copy: incomplete ${language}`);
}
const dnaManual = evaluateDictionary('static/js/steam-dna.js', 'var DNA_COPY=');
const dnaManualKeys = Object.keys(dnaManual.en || {}).sort().join('|');
for (const language of ['en','ru','de','tr','fr','uk','es','pt']) {
  const values = dnaManual[language] || {};
  if (Object.keys(values).sort().join('|') !== dnaManualKeys) errors.push(`Steam DNA copy: incomplete ${language}`);
  if (Object.values(values).some(value => typeof value !== 'string' || !value.trim())) errors.push(`Steam DNA copy: empty ${language}`);
}
const dnaAiManual = evaluateDictionary('static/js/steam-dna.js', 'var AI_COPY=');
const dnaAiManualKeys = Object.keys(dnaAiManual.en || {}).sort().join('|');
for (const language of ['en','ru','de','tr','fr','uk','es','pt']) {
  const values = dnaAiManual[language] || {};
  if (Object.keys(values).sort().join('|') !== dnaAiManualKeys) errors.push(`Steam DNA AI copy: incomplete ${language}`);
  if (Object.values(values).some(value => typeof value !== 'string' || !value.trim())) errors.push(`Steam DNA AI copy: empty ${language}`);
}
const dnaLiveManual = evaluateDictionary('static/js/steam-dna.js', 'var LIVE_COPY=');
const dnaLiveManualKeys = Object.keys(dnaLiveManual.en || {}).sort().join('|');
for (const language of ['en','ru','de','tr','fr','uk','es','pt']) {
  const values = dnaLiveManual[language] || {};
  if (Object.keys(values).sort().join('|') !== dnaLiveManualKeys) errors.push(`Steam DNA live copy: incomplete ${language}`);
  if (Object.values(values).some(value => typeof value !== 'string' || !value.trim())) errors.push(`Steam DNA live copy: empty ${language}`);
}
const dnaDesignManual = evaluateDictionary('static/js/steam-dna.js', 'var DESIGN_COPY=');
const dnaDesignManualKeys = Object.keys(dnaDesignManual.en || {}).sort().join('|');
for (const language of ['en','ru','de','tr','fr','uk','es','pt']) {
  const values = dnaDesignManual[language] || {};
  if (Object.keys(values).sort().join('|') !== dnaDesignManualKeys) errors.push(`Steam DNA design copy: incomplete ${language}`);
  if (Object.values(values).some(value => typeof value !== 'string' || !value.trim())) errors.push(`Steam DNA design copy: empty ${language}`);
}
for (const [name, dictionary] of [
  ['account copy', evaluateDictionary('static/ss-shell.js', 'var ACCOUNT_COPY =')],
  ['password reset errors', evaluateDictionary('static/ss-shell.js', 'var RESET_ERROR_COPY =')],
  ['account deletion errors', evaluateDictionary('static/js/account-controls.js', 'var DELETE_ERROR_COPY =')],
]) {
  const manualKeys = Object.keys(dictionary.en || {}).sort().join('|');
  for (const language of ['en','ru','de','tr','fr','uk','es','pt']) {
    if (Object.keys(dictionary[language] || {}).sort().join('|') !== manualKeys) errors.push(`${name}: incomplete ${language}`);
  }
}
errors.push(...check('app', evaluateDictionary('static/js/app.js', 'var DICT ='), attributeKeys('static/app.html')));
errors.push(...check('index', evaluateDictionary('static/js/index.js', 'const I18N ='), attributeKeys('static/index.html')));
errors.push(...check('profile', evaluateDictionary('static/js/profile.js', 'var PDICT='), attributeKeys('static/profile.html')));
errors.push(...check('gallery', evaluateDictionary('static/js/gallery.js', 'const GDICT ='), attributeKeys('static/gallery.html')));
const dictionaries = [
  evaluateDictionary('static/js/index.js', 'const I18N ='),
  evaluateDictionary('static/js/app.js', 'const APP_I18N ='),
  evaluateDictionary('static/js/app.js', 'var DICT ='),
  evaluateDictionary('static/js/app.js', 'var WM_TIPS ='),
  evaluateDictionary('static/js/gallery.js', 'const GDICT ='),
  evaluateDictionary('static/js/profile.js', 'var PDICT='),
  evaluateDictionary('static/js/profile.js', 'var A='),
  evaluateDictionary('static/js/seamless-loop.js', 'const copy='),
  evaluateDictionary('static/js/showcase-builder.js', 'var COPY ='),
  evaluateDictionary('static/js/steam-check.js', 'const copy ='),
  evaluateDictionary('static/js/steam-mockup.js', 'var UI ='),
];
const extras = extraPacks();
const languages = ['de','tr','fr','uk','es','pt'];
const preserved = /^(?:Steam|Steam DNA(?: ·)?|Showcase Maker|SteamShowcase Helper|Discord|Google|Telegram|Groq|Gemini|DeviantArt|Workshop|Featured|Artwork Split|GIF|PNG|JPG|WEBP|WebM|MP4|MOV|AVI|FFmpeg|gifski|HEX 21|FAQ|Pro|Free|LIVE)$/i;
const expected = new Set(dictionaries.flatMap(dictionary => collectStrings(dictionary.en || {})).filter(value => /[A-Za-z]/.test(value) && !preserved.test(value.trim())));
const literalStrings = new Set();
for (const file of [
  'static/ss-shell.js', 'static/js/index.js', 'static/js/index-tail.js',
  'static/js/app.js', 'static/js/app-tail.js', 'static/js/gallery.js',
  'static/js/profile.js', 'static/js/profile-insights.js', 'static/js/support-chat.js',
  'static/js/seamless-loop.js', 'static/js/showcase-builder.js',
  'static/js/steam-dna.js',
  'static/js/steam-check.js', 'static/js/steam-mockup.js',
  'static/js/steam-extension-status.js', 'static/js/layout-refinement.js',
  'static/js/sm-auth.js'
]) jsUiStrings(file, literalStrings);
for (const value of literalStrings) {
  if (/[A-Za-z]/.test(value) && !/[А-Яа-яЁёІіЇїЄє]/.test(value) && !preserved.test(value.trim())) expected.add(value);
}
for (const language of languages) {
  const pack = extras[language] || {};
  for (const value of expected) if (!(value in pack)) errors.push(`${language}: missing generated translation for ${value}`);
  if (Object.keys(pack).some(value => /[А-Яа-яЁёІіЇїЄє]/.test(value))) errors.push(`${language}: source pack contains non-English keys`);
}

if (errors.length) {
  console.error(errors.join('\n'));
  process.exitCode = 1;
} else {
  console.log('RU/EN keys, data-i bindings and DE/TR/FR/UK/ES/PT generated packs are complete.');
}
