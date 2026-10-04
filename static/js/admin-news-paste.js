/* Admin news: turn a pasted plain-text post into the editor's fields (owner, 2026-10-05).
   The texts Claude writes look like:
     Заголовок: ...            (or H1: / Title: / "# ...")
     Анонс: ...                (or Краткое описание: / Summary:)
     Категория: Обновление     (key or Russian name)
     H2: Section               (or "## Section"; H3: / "###" for smaller)
     - item / • item / 1. item, > quote, ---, **bold**, *italic*, [text](url)
     RU / EN on their own line switch the language, so both versions fill in one paste.
   SMNewsPaste.parse(text) -> {category, ru:{title,summary,body}, en:{...}, languages:[...]};
   SMNewsPaste.looksStructured(text) tells the editor to take over the paste.
   The HTML uses only tags smweb/news.py clean_html keeps. Works in node too (tests). */
(function (root) {
  'use strict';
  var CATEGORY_NAMES = { news: ['news', 'новости', 'новость'], update: ['update', 'обновление'], feature: ['feature', 'новая функция', 'функция'],
    announcement: ['announcement', 'анонс'], event: ['event', 'событие'], maintenance: ['maintenance', 'техработы', 'технические работы'], promo: ['promo', 'промо', 'акция'] };
  var LANG_LINE = /^[\s#=*_\-—–:|>]*(ru|rus|русский|русская версия|по-русски|en|eng|english|английский|английская версия|in english)[\s#=*_\-—–:|]*$/i;
  var FIELD = /^\s*(?:\*\*)?(заголовок|title|h1|анонс|краткое описание|описание|summary|lead|лид|подзаголовок|subtitle|категория|category)(?:\*\*)?\s*[:：]\s*(.+)$/i;
  var HEADING = /^\s*(?:(h[2-4])\s*[:：.]\s*|(#{2,4})\s+)(.+)$/i;

  function esc(text) { return String(text).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function safeUrl(url) { return /^https?:\/\//i.test(url) ? url : ''; }
  function inline(text) {
    var out = esc(text.trim()), links = [];
    out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, function (_, label, url) { links.push('<a href="' + esc(safeUrl(url)) + '">' + label + '</a>'); return '\u0000' + (links.length - 1) + '\u0000'; });
    out = out.replace(/(^|[\s(«"])(https?:\/\/[^\s<)»"]+)/g, function (_, lead, url) { links.push('<a href="' + url + '">' + url + '</a>'); return lead + '\u0000' + (links.length - 1) + '\u0000'; });
    out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/__([^_]+)__/g, '<strong>$1</strong>');
    out = out.replace(/(^|[^*\w])\*([^*\s][^*]*?)\*(?!\*)/g, '$1<em>$2</em>');
    out = out.replace(/`([^`]+)`/g, '$1');
    return out.replace(/\u0000(\d+)\u0000/g, function (_, i) { return links[Number(i)]; });
  }
  function category(value) {
    var wanted = String(value || '').trim().toLowerCase().replace(/[.!]+$/, '');
    for (var key in CATEGORY_NAMES) if (CATEGORY_NAMES[key].indexOf(wanted) >= 0) return key;
    return '';
  }
  function emptyLang() { return { title: '', summary: '', blocks: [], list: null, para: [] }; }

  function parse(text) {
    var result = { category: '', languages: [], marked: false }, langs = { ru: emptyLang(), en: emptyLang() }, lang = 'ru', used = {};
    function flushPara(L) { if (L.para.length) { L.blocks.push('<p>' + L.para.map(inline).join('<br>') + '</p>'); L.para = []; } }
    function flushList(L) { if (L.list) { L.blocks.push('<' + L.list.tag + '>' + L.list.items.map(function (i) { return '<li>' + inline(i) + '</li>'; }).join('') + '</' + L.list.tag + '>'); L.list = null; } }
    function flush(L) { flushPara(L); flushList(L); }
    String(text || '').replace(/\r\n?/g, '\n').split('\n').forEach(function (line) {
      var L = langs[lang], m, trimmed = line.trim();
      var switchTo = LANG_LINE.exec(trimmed);
      if (switchTo) { flush(L); result.marked = true; lang = /^(en|eng|english|английский|английская версия|in english)$/i.test(switchTo[1]) ? 'en' : 'ru'; return; }
      if (!trimmed) { flush(L); return; }
      used[lang] = true;
      if ((m = FIELD.exec(line))) {
        flush(L);
        var field = m[1].toLowerCase(), value = m[2].replace(/^\*\*|\*\*$/g, '').trim();
        if (/^(заголовок|title|h1)$/.test(field)) L.title = value;
        else if (/^(категория|category)$/.test(field)) result.category = category(value) || result.category;
        else L.summary = value;
        return;
      }
      if ((m = /^\s*#\s+(.+)$/.exec(line))) { flush(L); if (!L.title) L.title = m[1].trim(); else L.blocks.push('<h2>' + inline(m[1]) + '</h2>'); return; }
      if ((m = HEADING.exec(line))) {
        flush(L);
        var level = m[1] ? m[1].toLowerCase() : 'h' + m[2].length;
        L.blocks.push('<' + level + '>' + inline(m[3].replace(/^\*\*|\*\*$/g, '')) + '</' + level + '>');
        return;
      }
      if (/^\s*(?:-{3,}|_{3,}|\*{3,}|—{2,})\s*$/.test(line)) { flush(L); L.blocks.push('<hr>'); return; }
      if ((m = /^\s*>\s?(.*)$/.exec(line))) { flush(L); L.blocks.push('<blockquote>' + inline(m[1]) + '</blockquote>'); return; }
      var bullet = /^\s*[-*•–]\s+(.+)$/.exec(line), numbered = /^\s*\d+[.)]\s+(.+)$/.exec(line);
      if (bullet || numbered) {
        flushPara(L);
        var tag = bullet ? 'ul' : 'ol';
        if (L.list && L.list.tag !== tag) flushList(L);
        if (!L.list) L.list = { tag: tag, items: [] };
        L.list.items.push((bullet || numbered)[1]);
        return;
      }
      flushList(L);
      L.para.push(line);
    });
    ['ru', 'en'].forEach(function (key) {
      var L = langs[key]; flush(L);
      result[key] = { title: L.title, summary: L.summary, body: L.blocks.join('') };
      if (used[key] && (L.title || L.summary || L.blocks.length)) result.languages.push(key);
    });
    return result;
  }
  /* Worth taking over the paste: several lines with at least one of our markers. */
  function looksStructured(text) {
    var lines = String(text || '').split(/\r?\n/);
    if (lines.length < 2) return false;
    return lines.some(function (line) {
      var t = line.trim();
      return FIELD.test(t) || HEADING.test(t) || /^#\s+\S/.test(t) || LANG_LINE.test(t) || /^[-*•]\s+\S/.test(t) || /^\d+[.)]\s+\S/.test(t) || /\*\*[^*]+\*\*/.test(t);
    });
  }
  root.SMNewsPaste = { parse: parse, looksStructured: looksStructured, category: category };
  if (typeof module !== 'undefined' && module.exports) module.exports = root.SMNewsPaste;
})(typeof window !== 'undefined' ? window : globalThis);
