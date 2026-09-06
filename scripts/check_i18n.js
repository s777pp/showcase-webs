/* Static audit for RU/EN dictionaries and data-i attributes. */
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

const errors = [];
errors.push(...check('app', evaluateDictionary('static/js/app.js', 'var DICT ='), attributeKeys('static/app.html')));
errors.push(...check('index', evaluateDictionary('static/js/index.js', 'const I18N ='), attributeKeys('static/index.html')));
errors.push(...check('profile', evaluateDictionary('static/js/profile.js', 'var PDICT='), attributeKeys('static/profile.html')));
errors.push(...check('gallery', evaluateDictionary('static/js/gallery.js', 'const GDICT ='), attributeKeys('static/gallery.html')));

if (errors.length) {
  console.error(errors.join('\n'));
  process.exitCode = 1;
} else {
  console.log('RU/EN dictionary keys and data-i bindings are complete.');
}
