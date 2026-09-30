/* Text animations for Builder text layers (2026-09-30): typewriter, letter fade-up, decode,
   wave, bounce, Saber (glowing energy outline), neon flicker, glitch, rainbow, shine and the
   hollow outline family (fire, lightning, running outline, plasma) plus sparkles.
   Every animation is a function of u in [0, 1) = position in the scene loop, so exported
   loops have no jump. `speed` (0.25-4): continuous effects scale their cycle counts (always
   whole numbers per loop, so the loop stays seamless); one-shot reveals repeat round(speed)
   times when faster and stretch over more of the loop when slower.
   Vertical text stacks upright letters top to bottom, columns go left to right.
   showcase-builder.js has already moved / rotated / scaled the context to the text centre
   and set ctx.font; this module only draws the letters. */
(function () {
  'use strict';
  var TAU = Math.PI * 2;
  var NAMES = ['typewriter', 'fadeup', 'decode', 'wave', 'bounce', 'saber', 'neon', 'glitch', 'rainbow', 'shine',
    'fire', 'electric', 'lightning', 'runner', 'plasma', 'sparkle'];
  var ONE_SHOT = ['typewriter', 'fadeup', 'decode', 'bounce'];
  var GLYPHS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789#$%&@*+=?<>/';
  var layoutCache = new Map(), scratch = null, sprites = {};
  // A web font that finishes loading changes glyph widths: measure again.
  if (document.fonts && document.fonts.addEventListener) document.fonts.addEventListener('loadingdone', function () { layoutCache.clear(); });

  function hash(i, k) { var n = Math.sin(i * 127.1 + k * 311.7) * 43758.5453; return n - Math.floor(n); }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function frac(v) { return v - Math.floor(v); }
  function ease(p) { p = clamp(p, 0, 1); return 1 - Math.pow(1 - p, 3); }
  function rgb(hex) { var v = /^#?([0-9a-f]{6})$/i.exec(hex || '') ? hex.replace('#', '') : 'ffffff'; return [parseInt(v.slice(0, 2), 16), parseInt(v.slice(2, 4), 16), parseInt(v.slice(4, 6), 16)]; }
  function rgba(c, a) { return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + a + ')'; }

  /* Soft round glow, drawn with drawImage (much cheaper than shadowBlur per particle). */
  function sprite(c) {
    var key = c.join(','); if (sprites[key]) return sprites[key];
    var s = document.createElement('canvas'); s.width = s.height = 64;
    var g = s.getContext('2d'), grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    grad.addColorStop(0, rgba(c, 1)); grad.addColorStop(.35, rgba(c, .55)); grad.addColorStop(1, rgba(c, 0));
    g.fillStyle = grad; g.fillRect(0, 0, 64, 64);
    return (sprites[key] = s);
  }

  /* Letter positions (centre aligned), cached per font + text + direction. */
  function layout(ctx, lines, size, vertical) {
    var key = ctx.font + '|' + size + '|' + (vertical ? 'v' : 'h') + '|' + lines.join('\n'), hit = layoutCache.get(key);
    if (hit) return hit;
    var letters = [], rows = [], width = 1, height = 1, step;
    if (vertical) {
      var gap = size * 1.15, most = 1; step = size * 1.02;
      lines.forEach(function (line, ci) {
        var chars = Array.from(line), x = (ci - (lines.length - 1) / 2) * gap;
        most = Math.max(most, chars.length);
        chars.forEach(function (ch, j) { letters.push({ ch: ch, x: x, y: (j - (chars.length - 1) / 2) * step, w: ctx.measureText(ch).width, line: ci }); });
      });
      width = lines.length * gap; height = most * step; rows = null;
    } else {
      step = size * 1.12;
      lines.forEach(function (line, li) {
        var chars = Array.from(line), w = ctx.measureText(line).width, x = -w / 2, y = (li - (lines.length - 1) / 2) * step;
        width = Math.max(width, w); rows.push({ text: line, y: y });
        chars.forEach(function (ch) { var cw = ctx.measureText(ch).width; letters.push({ ch: ch, x: x + cw / 2, y: y, w: cw, line: li }); x += cw; });
      });
      height = lines.length * step;
    }
    hit = { rows: rows, letters: letters, width: width, height: height, lineHeight: step, vertical: !!vertical, pts: null };
    if (layoutCache.size > 60) layoutCache.delete(layoutCache.keys().next().value);
    layoutCache.set(key, hit);
    return hit;
  }
  function letter(ctx, l, dx, dy, text) { ctx.fillText(text == null ? l.ch : text, l.x + (dx || 0), l.y + (dy || 0)); }
  /* Whole lines when horizontal (one draw call and one shadow per line), letters when vertical. */
  function strokeAll(ctx, L, dx, dy) {
    dx = dx || 0; dy = dy || 0;
    if (L.rows) { ctx.textAlign = 'center'; L.rows.forEach(function (r) { ctx.strokeText(r.text, dx, r.y + dy); }); }
    else L.letters.forEach(function (l) { ctx.strokeText(l.ch, l.x + dx, l.y + dy); });
  }
  function fillAll(ctx, L) {
    if (L.rows) { ctx.textAlign = 'center'; L.rows.forEach(function (r) { ctx.fillText(r.text, 0, r.y); }); }
    else L.letters.forEach(function (l) { letter(ctx, l); });
  }
  /* Points on the letter outlines (sampled once per layout from a small offscreen stroke),
     in a fixed pseudo-random order so particles spread evenly over the text. */
  function points(ctx, L, size) {
    if (L.pts) return L.pts;
    var pad = size * .5, w = L.width + pad * 2, h = L.height + pad * 2, s = Math.min(1, 520 / Math.max(w, h));
    var c = document.createElement('canvas'); c.width = Math.max(8, Math.ceil(w * s)); c.height = Math.max(8, Math.ceil(h * s));
    var g = c.getContext('2d', { willReadFrequently: true });
    g.scale(s, s); g.translate(w / 2, h / 2); g.font = ctx.font; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.lineWidth = 2 / s; g.strokeStyle = '#fff'; strokeAll(g, L);
    var data = g.getImageData(0, 0, c.width, c.height).data, stepPx = Math.max(2, Math.round(size * s * .045)), pts = [];
    for (var y = 0; y < c.height; y += stepPx) for (var x = 0; x < c.width; x += stepPx) {
      if (data[(y * c.width + x) * 4 + 3] > 90) pts.push({ x: x / s - w / 2, y: y / s - h / 2, k: hash(x, y) });
    }
    pts.sort(function (a, b) { return a.k - b.k; });
    return (L.pts = pts.slice(0, 700));
  }
  /* Glyph outlines as polylines (marching squares over a filled-text mask), computed once
     per layout: fire, electricity and similar effects follow the real letter edges.
     Each contour: Float32Array [x, y, nx, ny, arc] per point, spacing ~ size * 0.018. */
  var CASES = [[], [3, 2], [2, 1], [3, 1], [0, 1], [3, 0, 2, 1], [0, 2], [3, 0], [3, 0], [0, 2], [0, 1, 3, 2], [0, 1], [3, 1], [2, 1], [3, 2], []];
  function contours(ctx, L, size) {
    if (L.contours) return L.contours;
    var pad = size * .3, w = L.width + pad * 2, h = L.height + pad * 2, s = Math.min(1.2, 70 / size);
    while (w * h * s * s > 360000) s *= .85;
    var W = Math.ceil(w * s) + 2, H = Math.ceil(h * s) + 2;
    var c = document.createElement('canvas'); c.width = W; c.height = H;
    var g = c.getContext('2d', { willReadFrequently: true });
    g.translate(W / 2, H / 2); g.scale(s, s); g.font = ctx.font; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillStyle = '#fff';
    fillAll(g, L);
    var data = g.getImageData(0, 0, W, H).data, b = new Uint8Array(W * H);
    for (var i = 0; i < W * H; i++) b[i] = data[i * 4 + 3] > 127 ? 1 : 0;
    // Edge ids: horizontal edge (x,y)-(x+1,y) = 2*(y*W+x), vertical edge (x,y)-(x,y+1) = 2*(y*W+x)+1.
    var n1 = new Int32Array(W * H * 2).fill(-1), n2 = new Int32Array(W * H * 2).fill(-1);
    function link(a, e) { if (n1[a] < 0) n1[a] = e; else n2[a] = e; }
    for (var y = 0; y < H - 1; y++) for (var x = 0; x < W - 1; x++) {
      var k = y * W + x, idx = b[k] * 8 + b[k + 1] * 4 + b[k + W + 1] * 2 + b[k + W];
      var segs = CASES[idx]; if (!segs.length) continue;
      var edge = [2 * k, 2 * (k + 1) + 1, 2 * (k + W), 2 * k + 1];  // top, right, bottom, left
      for (var j = 0; j < segs.length; j += 2) { var a = edge[segs[j]], e = edge[segs[j + 1]]; link(a, e); link(e, a); }
    }
    var seen = new Uint8Array(W * H * 2), out = [], step = size * .018;
    for (var start = 0; start < n1.length; start++) {
      if (n1[start] < 0 || seen[start]) continue;
      var pts = [], prev = -1, cur = start;
      while (cur >= 0 && !seen[cur]) {
        seen[cur] = 1;
        var cell = cur >> 1, cx = cell % W, cy = (cell - cx) / W;
        pts.push((cur & 1 ? cx : cx + .5) / s - W / 2 / s, (cur & 1 ? cy + .5 : cy) / s - H / 2 / s);
        var next = n1[cur] !== prev ? n1[cur] : n2[cur]; prev = cur; cur = next;
      }
      if (pts.length < 16) continue;
      // Smooth twice (closed), then resample to an even spacing.
      for (var pass = 0; pass < 2; pass++) {
        var sm = pts.slice(), m = pts.length / 2;
        for (var q = 0; q < m; q++) { var a0 = ((q - 1 + m) % m) * 2, a2 = ((q + 1) % m) * 2; sm[q * 2] = (pts[a0] + 2 * pts[q * 2] + pts[a2]) / 4; sm[q * 2 + 1] = (pts[a0 + 1] + 2 * pts[q * 2 + 1] + pts[a2 + 1]) / 4; }
        pts = sm;
      }
      var res = [], acc = 0, arc = 0, total = pts.length / 2;
      res.push(pts[0], pts[1]);
      for (var r = 1; r <= total; r++) {
        var px = pts[((r - 1) % total) * 2], py = pts[((r - 1) % total) * 2 + 1], qx = pts[(r % total) * 2], qy = pts[(r % total) * 2 + 1];
        var d = Math.hypot(qx - px, qy - py); acc += d;
        if (acc >= step) { res.push(qx, qy); acc = 0; }
      }
      var count = res.length / 2; if (count < 6) continue;
      var f = new Float32Array(count * 5);
      for (var t = 0; t < count; t++) {
        var ax = res[((t - 1 + count) % count) * 2], ay = res[((t - 1 + count) % count) * 2 + 1], bx = res[((t + 1) % count) * 2], by = res[((t + 1) % count) * 2 + 1];
        var tx = bx - ax, ty = by - ay, tl = Math.hypot(tx, ty) || 1;
        if (t) arc += Math.hypot(res[t * 2] - res[t * 2 - 2], res[t * 2 + 1] - res[t * 2 - 1]);
        f[t * 5] = res[t * 2]; f[t * 5 + 1] = res[t * 2 + 1]; f[t * 5 + 2] = -ty / tl; f[t * 5 + 3] = tx / tl; f[t * 5 + 4] = arc;
      }
      // Make the normals point OUT of the ink: probe the mask a little along the normal.
      var inside = 0, probes = 0;
      for (var pr = 0; pr < count; pr += Math.max(1, Math.floor(count / 12))) {
        var qx2 = Math.round((f[pr * 5] + f[pr * 5 + 2] * 2.5 / s) * s + W / 2), qy2 = Math.round((f[pr * 5 + 1] + f[pr * 5 + 3] * 2.5 / s) * s + H / 2);
        if (qx2 >= 0 && qy2 >= 0 && qx2 < W && qy2 < H) { probes++; inside += b[qy2 * W + qx2]; }
      }
      if (probes && inside * 2 > probes) for (var fl = 0; fl < count; fl++) { f[fl * 5 + 2] = -f[fl * 5 + 2]; f[fl * 5 + 3] = -f[fl * 5 + 3]; }
      out.push(f);
    }
    return (L.contours = out);
  }
  /* Value noise along a line; `seed` picks an independent curve. */
  function vnoise(x, seed) { var i = Math.floor(x), f = x - i, a = hash(i, seed), b = hash(i + 1, seed); f = f * f * (3 - 2 * f); return a + (b - a) * f; }
  /* Noise in (x, t) that repeats in t with period `per` (whole loops stay seamless). */
  function tnoise(x, t, per, seed) {
    var ti = Math.floor(t), f = t - ti, a = vnoise(x, seed + (((ti % per) + per) % per) * 17.31), b = vnoise(x, seed + ((((ti + 1) % per) + per) % per) * 17.31);
    f = f * f * (3 - 2 * f); return a + (b - a) * f;
  }
  /* Draw every contour as one path, each point moved along its normal by off(i, contourIndex, arc). */
  function contourPath(ctx, list, off) {
    ctx.beginPath();
    list.forEach(function (f, ci) {
      var n = f.length / 5;
      for (var i = 0; i <= n; i++) {
        var k = (i % n) * 5, d = off(i % n, ci, f[k + 4]), x = f[k] + f[k + 2] * d, y = f[k + 1] + f[k + 3] * d;
        if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y);
      }
    });
  }
  /* Flame tongue sprite for a base colour: white-hot core -> light tint -> colour -> dark edge.
     The default orange keeps the classic fire palette. */
  var flameSprites = {};
  function flame(c) {
    var key = c.join(','); if (flameSprites[key]) return flameSprites[key];
    var cv = document.createElement('canvas'); cv.width = 48; cv.height = 128;
    var g = cv.getContext('2d'); g.translate(24, 112); g.scale(1, 3.4);
    var grad = g.createRadialGradient(0, 0, 0, 0, 0, 22), dark = mix(c, [0, 0, 0], .3), deep = mix(c, [0, 0, 0], .45);
    grad.addColorStop(0, rgba(mix(c, [255, 255, 255], .88), 1)); grad.addColorStop(.22, rgba(mix(c, [255, 255, 255], .5), .95));
    grad.addColorStop(.5, rgba(c, .6)); grad.addColorStop(.8, rgba(dark, .22)); grad.addColorStop(1, rgba(deep, 0));
    g.fillStyle = grad; g.beginPath(); g.arc(0, 0, 22, 0, TAU); g.fill();
    return (flameSprites[key] = cv);
  }

  /* Fade the whole text out during the last 8 % of the loop and back in at the start. */
  /* Whole cycles per loop for a rate given in cycles per second (o.period already includes the speed). */
  function cyc(o, perSecond) { return Math.max(1, Math.round(o.period * perSecond)); }
  /* Default glow colour of each effect (used for tiles and when the user has not picked one). */
  var DEFAULT_COLORS = { fire: '#ff6a00', neon: '#ff2d8a', electric: '#2a8cff', lightning: '#52d5ff', saber: '#52d5ff', runner: '#52d5ff', sparkle: '#ffd66e' };
  function mix(c, t, k) { return [Math.round(c[0] + (t[0] - c[0]) * k), Math.round(c[1] + (t[1] - c[1]) * k), Math.round(c[2] + (t[2] - c[2]) * k)]; }
  function loopFade(u) { return u > .92 ? clamp((1 - u) / .08, 0, 1) : clamp(u / .03, 0, 1); }

  var FX = {
    plain: function (ctx, L) { L.letters.forEach(function (l) { letter(ctx, l); }); },
    typewriter: function (ctx, L, o) {
      var n = L.letters.length, shown = Math.floor(clamp(o.u / o.span, 0, 1) * n), fade = loopFade(o.u);
      ctx.globalAlpha *= fade;
      for (var i = 0; i < shown; i++) letter(ctx, L.letters[i]);
      if (Math.floor(o.u * cyc(o, 1.1) * 2) % 2 !== 0) return;
      var last = L.letters[Math.max(0, shown - 1)] || { x: 0, y: 0, w: 0 };
      if (L.vertical) {
        var first = L.letters[0] || { x: 0, y: 0 }, cy = shown ? last.y + o.size * .58 : first.y - o.size * .4;
        ctx.fillRect((shown ? last.x : first.x) - o.size * .32, cy, o.size * .64, Math.max(2, o.size * .07));
      } else {
        if (!shown) last = { x: -L.width / 2, y: (L.letters[0] || { y: 0 }).y, w: 0 };
        var cx = shown ? last.x + last.w / 2 + o.size * .06 : last.x;
        ctx.fillRect(cx, last.y - o.size * .42, Math.max(2, o.size * .07), o.size * .84);
      }
    },
    fadeup: function (ctx, L, o) {
      var n = L.letters.length, base = ctx.globalAlpha, fade = loopFade(o.u);
      L.letters.forEach(function (l, i) {
        var k = o.span / .55, p = ease((o.u - i / Math.max(1, n) * .45 * k) / (.14 * k));
        ctx.globalAlpha = base * p * fade; letter(ctx, l, 0, (1 - p) * o.size * .5);
      });
    },
    decode: function (ctx, L, o) {
      var n = L.letters.length, tick = Math.floor(o.u * cyc(o, 18)), fade = loopFade(o.u);
      ctx.globalAlpha *= fade;
      L.letters.forEach(function (l, i) {
        var done = o.u > (.08 + i / Math.max(1, n) * .5) * o.span / .55;
        if (done || l.ch === ' ') { letter(ctx, l); return; }
        ctx.save(); ctx.globalAlpha *= .75; letter(ctx, l, 0, 0, GLYPHS[Math.floor(hash(i, tick) * GLYPHS.length)]); ctx.restore();
      });
    },
    wave: function (ctx, L, o) {
      L.letters.forEach(function (l, i) {
        var d = Math.sin(o.u * TAU * cyc(o, .25) - i * .55) * o.size * .14;
        if (L.vertical) letter(ctx, l, d, 0); else letter(ctx, l, 0, d);
      });
    },
    bounce: function (ctx, L, o) {
      var n = L.letters.length;
      L.letters.forEach(function (l, i) {
        var k = o.span / .55, p = clamp((o.u - i / Math.max(1, n) * .4 * k) / (.16 * k), 0, 1), s = p < 1 ? (p < .6 ? p / .6 * 1.25 : 1.25 - (p - .6) / .4 * .25) : 1 + .04 * Math.sin(o.u * TAU * 3 + i);
        if (p <= 0) return;
        ctx.save(); ctx.globalAlpha *= loopFade(o.u); ctx.translate(l.x, l.y); ctx.scale(s, s); ctx.fillText(l.ch, 0, 0); ctx.restore();
      });
    },
    /* Saber: hot white core, several glowing colour passes and crawling energy dashes. */
    saber: function (ctx, L, o) {
      var c = rgb(o.color), flick = .82 + .18 * Math.sin(o.u * TAU * cyc(o, .875)) * Math.sin(o.u * TAU * cyc(o, .375) + 1), jitter = o.size * .012;
      var tick = Math.floor(o.u * cyc(o, 24));
      ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.lineJoin = 'round'; ctx.lineCap = 'round';
      [[.2, .14, .5], [.11, .26, .32], [.055, .5, .18]].forEach(function (pass, k) {
        ctx.lineWidth = o.size * pass[0]; ctx.strokeStyle = rgba(c, pass[1] * flick); ctx.shadowColor = rgba(c, .9); ctx.shadowBlur = o.size * pass[2];
        if (k === 1) { ctx.setLineDash([o.size * .35, o.size * .12]); ctx.lineDashOffset = -o.u * cyc(o, 1.6) * o.size * .47; } else ctx.setLineDash([]);
        var j = (hash(k * 7, tick) - .5) * jitter; strokeAll(ctx, L, j, -j);
      });
      ctx.setLineDash([]); ctx.shadowBlur = o.size * .15; ctx.shadowColor = rgba(c, 1);
      ctx.lineWidth = Math.max(1.2, o.size * .028); ctx.strokeStyle = 'rgba(255,255,255,' + (.85 + .15 * flick) + ')';
      strokeAll(ctx, L);
      ctx.restore();
    },
    /* Neon tube (hollow letters, traced from the glyph mask so overlapping font contours
       leave no inner lines): pink haze, coloured tube, white-hot core, rare flicker. */
    neon: function (ctx, L, o) {
      var c = rgb(o.color), f = o.u * 20, off = [2.2, 2.35, 9.1, 9.2, 9.35, 15.6].some(function (s) { return f > s && f < s + .09; });
      var hum = .94 + .06 * Math.sin(o.u * TAU * Math.max(1, Math.round(o.period * 6))), list = contours(ctx, L, o.size), sz = o.size;
      ctx.save(); ctx.lineJoin = 'round'; ctx.lineCap = 'round';
      contourPath(ctx, list, function () { return 0; });
      if (off) {
        ctx.lineWidth = sz * .05; ctx.strokeStyle = rgba(c, .2); ctx.stroke();
        ctx.lineWidth = Math.max(1, sz * .018); ctx.strokeStyle = 'rgba(255,255,255,.22)'; ctx.stroke();
        ctx.restore(); return;
      }
      ctx.globalCompositeOperation = 'lighter';
      ctx.shadowColor = rgba(c, .85 * hum); ctx.shadowBlur = sz * .8;
      ctx.lineWidth = sz * .16; ctx.strokeStyle = rgba(c, .07 * hum); ctx.stroke();
      ctx.shadowBlur = sz * .3;
      ctx.lineWidth = sz * .055; ctx.strokeStyle = rgba(c, .7 * hum); ctx.stroke();
      ctx.shadowBlur = sz * .08; ctx.shadowColor = rgba(c, 1);
      ctx.lineWidth = Math.max(1, sz * .02); ctx.strokeStyle = 'rgba(255,245,250,' + (.95 * hum) + ')'; ctx.stroke();
      ctx.restore();
    },
    glitch: function (ctx, L, o) {
      var tick = Math.floor(o.u * cyc(o, 12)), burst = hash(tick >> 2, 5) > .55, d = o.size * (burst ? .07 : .03);
      ctx.save(); ctx.globalCompositeOperation = 'lighter';
      ctx.fillStyle = 'rgba(255,40,90,.85)'; L.letters.forEach(function (l) { letter(ctx, l, -d, 0); });
      ctx.fillStyle = 'rgba(40,230,255,.85)'; L.letters.forEach(function (l) { letter(ctx, l, d, 0); });
      ctx.restore();
      L.letters.forEach(function (l, i) { var shift = burst && hash(i, tick) > .7 ? (hash(i, tick + 3) - .5) * o.size * .3 : 0; letter(ctx, l, shift, 0); });
    },
    rainbow: function (ctx, L, o) {
      var g = L.vertical ? ctx.createLinearGradient(0, -L.height / 2, 0, L.height / 2) : ctx.createLinearGradient(-L.width / 2, 0, L.width / 2, 0);
      for (var k = 0; k <= 6; k++) g.addColorStop(k / 6, 'hsl(' + Math.round(frac(k / 6 + o.u * cyc(o, .125)) * 360) + ',95%,62%)');
      ctx.save(); ctx.fillStyle = g; ctx.shadowColor = 'rgba(255,255,255,.35)'; ctx.shadowBlur = o.size * .12;
      fillAll(ctx, L); ctx.restore();
    },
    /* Shine: a light band sweeps over the letters twice per loop. */
    shine: function (ctx, L, o) {
      var pad = Math.ceil(o.size * .3), w = Math.ceil(L.width + pad * 2), h = Math.ceil(L.height + pad * 2);
      if (!scratch) scratch = document.createElement('canvas');
      if (scratch.width < w || scratch.height < h) { scratch.width = Math.max(scratch.width, w); scratch.height = Math.max(scratch.height, h); }
      var s = scratch.getContext('2d'); s.setTransform(1, 0, 0, 1, 0, 0); s.clearRect(0, 0, scratch.width, scratch.height);
      s.font = ctx.font; s.textAlign = 'center'; s.textBaseline = 'middle'; s.fillStyle = ctx.fillStyle;
      s.translate(w / 2, h / 2); L.letters.forEach(function (l) { s.fillText(l.ch, l.x, l.y); });
      var p = frac(o.u * cyc(o, .25)), len = L.vertical ? h : w, b = -len / 2 + p * (len * 1.6) - len * .3;
      var g = L.vertical ? s.createLinearGradient(0, b - o.size * .6, 0, b + o.size * .6) : s.createLinearGradient(b - o.size * .6, 0, b + o.size * .6, 0);
      g.addColorStop(0, 'rgba(255,255,255,0)'); g.addColorStop(.5, 'rgba(255,255,255,.95)'); g.addColorStop(1, 'rgba(255,255,255,0)');
      s.globalCompositeOperation = 'source-atop'; s.fillStyle = g; s.fillRect(-w / 2, -h / 2, w, h); s.globalCompositeOperation = 'source-over';
      ctx.drawImage(scratch, 0, 0, w, h, -w / 2, -h / 2, w, h);
    },
    /* Burning outline: flame tongues along every letter edge (taller on top edges, since fire
       rises), thin licks, a jagged white-hot edge, soft red glow and embers. Everything is
       periodic noise in loop time, so the loop is seamless. */
    fire: function (ctx, L, o) {
      var list = contours(ctx, L, o.size), cyc = Math.max(2, Math.round(o.period * 3.5)), t = o.u * cyc, sz = o.size;
      var c = rgb(o.color), hot = mix(c, [255, 255, 255], .45), core = mix(c, [255, 255, 255], .85), dark = mix(c, [0, 0, 0], .45);
      var glow = sprite(dark), tongue = flame(c), puffCyc = Math.max(1, Math.round(o.period * 1.6));
      ctx.save(); ctx.lineJoin = 'round'; ctx.lineCap = 'round'; ctx.globalCompositeOperation = 'lighter';
      list.forEach(function (f, ci) {
        var n = f.length / 5, i, k, r;
        for (i = 0; i < n; i += 6) {
          k = i * 5; r = sz * .42; ctx.globalAlpha = .1;
          ctx.drawImage(glow, f[k] - r, f[k + 1] - r * 1.2, r * 2, r * 2);
        }
        for (i = 0; i < n; i += 3) {
          k = i * 5;
          var arc = f[k + 4] / sz + ci * 13.7, up = clamp(.3 - f[k + 3] * .9, 0, 1);
          if (up < .2 || (up < .5 && hash(i, ci + 17) > up * 1.6)) continue;
          var lift = tnoise(arc * 2.2, t, cyc, 3), h = sz * (.2 + .95 * lift * lift) * up;
          var sway = (tnoise(arc * 1.3, t, cyc, 9) - .5) * sz * .55, w = Math.min(sz * (.2 + .1 * tnoise(arc * 3, t, cyc, 21)), h * .55);
          var jx = (hash(i, ci + 3) - .5) * sz * .05;
          ctx.globalAlpha = (.3 + .35 * lift) * (.55 + .45 * up);
          ctx.save(); ctx.translate(f[k] + jx, f[k + 1] + sz * .03); ctx.transform(1, 0, clamp(sway / Math.max(1, h), -.45, .45), 1, 0, 0);
          ctx.drawImage(tongue, -w / 2, -h * .875, w, h);
          ctx.restore();
        }
        // Puffs of flame that break off the top edges, rise and fade.
        for (i = 2; i < n; i += 5) {
          k = i * 5;
          var upP = clamp(-f[k + 3], 0, 1); if (upP < .35) continue;
          var life = frac(o.u * puffCyc + hash(i, ci + 71)), size = sz * (.34 + .2 * hash(i, ci + 73)) * (1 - life * .6);
          var px = f[k] + Math.sin((life * .8 + hash(i, ci + 79)) * TAU) * sz * .06, py = f[k + 1] - sz * .02 - life * sz * (.32 + .3 * hash(i, ci + 83));
          ctx.globalAlpha = .5 * upP * Math.sin(Math.PI * life) * (1 - life * .3);
          ctx.drawImage(tongue, px - size * .35, py - size * 1.1, size * .7, size * 1.3);
        }
        for (i = 1; i < n; i += 11) {
          k = i * 5;
          var a2 = f[k + 4] / sz + ci * 7.3, up2 = clamp(-f[k + 3], 0, 1); if (up2 < .3) continue;
          var l2 = tnoise(a2 * 4, t * 2, cyc * 2, 57), h2 = sz * (.35 + 1.1 * l2 * l2 * l2) * up2, s2 = (tnoise(a2 * 2, t * 2, cyc * 2, 61) - .5) * sz * .8;
          ctx.globalAlpha = .55 * l2;
          ctx.save(); ctx.translate(f[k], f[k + 1]); ctx.transform(1, 0, clamp(s2 / Math.max(1, h2), -.5, .5), 1, 0, 0);
          ctx.drawImage(tongue, -sz * .045, -h2 * .875, sz * .09, h2);
          ctx.restore();
        }
      });
      ctx.globalAlpha = 1;
      var cyc2 = cyc * 3, t2 = o.u * cyc2;
      contourPath(ctx, list, function (i, ci, arc) { return (tnoise(arc / sz * 7 + ci * 5, t2, cyc2, 31) - .5) * sz * .045; });
      ctx.lineWidth = sz * .06; ctx.strokeStyle = rgba(c, .5); ctx.stroke();
      ctx.lineWidth = sz * .028; ctx.strokeStyle = rgba(hot, .8); ctx.stroke();
      ctx.lineWidth = Math.max(1, sz * .011); ctx.strokeStyle = rgba(core, .95); ctx.stroke();
      var pts = points(ctx, L, sz), cycE = Math.max(1, Math.round(o.period / 1.2));
      ctx.fillStyle = rgba(hot, 1);
      for (var e = 0; e < Math.min(pts.length, 26); e++) {
        var p = pts[e], life = frac(o.u * cycE + hash(e, 41)), rise = life * sz * (.8 + .7 * hash(e, 43)), rr = sz * .022 * (1 - life);
        if (rr <= .2) continue;
        ctx.globalAlpha = (1 - life) * .9;
        ctx.beginPath(); ctx.arc(p.x + Math.sin((life + hash(e, 47)) * TAU) * sz * .1, p.y - rise, rr, 0, TAU); ctx.fill();
      }
      ctx.restore();
    },
    /* Electric outline: several jagged arcs crackle along every letter edge (they jump to a new
       shape ~18 times a second), a soft blue halo, bright sparks. */
    electric: function (ctx, L, o) {
      var c = rgb(o.color), list = contours(ctx, L, o.size), sz = o.size, tick = Math.floor(o.u * cyc(o, 18));
      var hi = [Math.min(255, c[0] + 150), Math.min(255, c[1] + 150), Math.min(255, c[2] + 150)];
      ctx.save(); ctx.lineJoin = 'round'; ctx.lineCap = 'round'; ctx.globalCompositeOperation = 'lighter';
      contourPath(ctx, list, function () { return 0; });
      ctx.shadowColor = rgba(c, .9); ctx.shadowBlur = sz * .45;
      ctx.lineWidth = sz * .05; ctx.strokeStyle = rgba(c, .22); ctx.stroke();
      ctx.shadowBlur = 0;
      [0, 1, 2].forEach(function (k) {
        var seed = tick * 7 + k * 101, amp = sz * (k === 2 ? .07 : .045);
        contourPath(ctx, list, function (i, ci, arc) {
          var d = (vnoise(arc / (sz * .16) + ci * 3.1, seed) - .5) * 2 * amp * .7 + (hash(i + ci * 997, seed) - .5) * amp * .55;
          if (hash((i >> 3) + ci * 131, seed + 5) > .94) d += (hash(i, seed + 9) - .3) * amp * 2.2;
          return d;
        });
        ctx.lineWidth = sz * (k === 2 ? .05 : .075); ctx.strokeStyle = rgba(c, k === 2 ? .12 : .22); ctx.stroke();
        ctx.lineWidth = sz * .026; ctx.strokeStyle = rgba(c, k === 2 ? .45 : .8); ctx.stroke();
        ctx.lineWidth = Math.max(.8, sz * .009); ctx.strokeStyle = rgba(hi, k === 2 ? .55 : .95); ctx.stroke();
      });
      var glow = sprite(c), core = sprite([230, 245, 255]);
      list.forEach(function (f, ci) {
        var n = f.length / 5, sparks = Math.max(1, Math.round(n / 70));
        for (var j = 0; j < sparks; j++) {
          if (hash(j + ci * 31, tick) < .45) continue;
          var k = Math.floor(hash(j * 7 + ci, tick + 3) * n) * 5, r = sz * (.12 + .18 * hash(j, tick + 7));
          ctx.globalAlpha = .75; ctx.drawImage(glow, f[k] - r, f[k + 1] - r, r * 2, r * 2);
          ctx.globalAlpha = .9; ctx.drawImage(core, f[k] - r * .3, f[k + 1] - r * .3, r * .6, r * .6);
        }
      });
      ctx.restore();
    },
    /* Hollow letters with an electric outline and short bolts jumping between edges. */
    lightning: function (ctx, L, o) {
      var c = rgb(o.color), pts = points(ctx, L, o.size), n = pts.length, tick = Math.floor(o.u * cyc(o, 14));
      var strike = hash(tick, 11) > .72, flash = strike ? 1 : .75 + .1 * Math.sin(o.u * TAU * o.period * 3);
      ctx.save(); ctx.lineJoin = 'round'; ctx.lineCap = 'round';
      ctx.shadowColor = rgba(c, 1); ctx.shadowBlur = o.size * (strike ? .4 : .22);
      ctx.lineWidth = o.size * .035; ctx.strokeStyle = rgba(c, .85 * flash); strokeAll(ctx, L);
      ctx.shadowBlur = 0; ctx.lineWidth = Math.max(1, o.size * .012); ctx.strokeStyle = 'rgba(255,255,255,' + (.7 + .3 * flash) + ')'; strokeAll(ctx, L);
      if (n > 4) {
        ctx.globalCompositeOperation = 'lighter';
        var bolts = strike ? 7 : 4;
        for (var j = 0; j < bolts; j++) {
          if (hash(j, tick + 5) < .3) continue;
          var a = pts[Math.floor(hash(j, tick) * n)], b = null;
          for (var k = 0; k < 8 && !b; k++) {
            var cand = pts[Math.floor(hash(j * 13 + k, tick + 1) * n)], d = Math.hypot(cand.x - a.x, cand.y - a.y);
            if (d > o.size * .25 && d < o.size * 1.3) b = cand;
          }
          if (!b) continue;
          var dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy), nx = -dy / len, ny = dx / len, path = [[a.x, a.y]];
          for (var s = 1; s < 7; s++) { var f = s / 7, off = (hash(j * 31 + s, tick) - .5) * len * .38; path.push([a.x + dx * f + nx * off, a.y + dy * f + ny * off]); }
          path.push([b.x, b.y]);
          var m = path[3], e = [m[0] + nx * len * .3 + dx * .15, m[1] + ny * len * .3 + dy * .15], mid = [(m[0] + e[0]) / 2 + (hash(j, tick + 9) - .5) * len * .15, (m[1] + e[1]) / 2];
          [[o.size * .07, rgba(c, .28)], [o.size * .028, rgba(c, .9)], [Math.max(1, o.size * .01), 'rgba(255,255,255,.95)']].forEach(function (pass) {
            ctx.lineWidth = pass[0]; ctx.strokeStyle = pass[1]; ctx.beginPath();
            path.forEach(function (pt, i) { if (i) ctx.lineTo(pt[0], pt[1]); else ctx.moveTo(pt[0], pt[1]); });
            ctx.moveTo(m[0], m[1]); ctx.lineTo(mid[0], mid[1]); ctx.lineTo(e[0], e[1]);
            ctx.stroke();
          });
        }
      }
      ctx.restore();
    },
    /* Hollow letters, faint outline, bright segments running around every letter. */
    runner: function (ctx, L, o) {
      var c = rgb(o.color), P = o.size * .9, cyc = Math.max(1, Math.round(o.period / 2));
      ctx.save(); ctx.lineJoin = 'round'; ctx.lineCap = 'round';
      ctx.lineWidth = o.size * .03; ctx.strokeStyle = rgba(c, .28); strokeAll(ctx, L);
      ctx.setLineDash([P * .38, P * .62]); ctx.lineDashOffset = -o.u * cyc * P;
      ctx.globalCompositeOperation = 'lighter';
      ctx.lineWidth = o.size * .1; ctx.strokeStyle = rgba(c, .22); strokeAll(ctx, L);
      ctx.lineWidth = o.size * .045; ctx.strokeStyle = rgba(c, .95); strokeAll(ctx, L);
      ctx.lineWidth = Math.max(1, o.size * .015); ctx.strokeStyle = 'rgba(255,255,255,.95)'; strokeAll(ctx, L);
      ctx.restore();
    },
    /* Hollow letters with a thick glowing outline whose colours flow along the text. */
    plasma: function (ctx, L, o) {
      var g = L.vertical ? ctx.createLinearGradient(0, -L.height / 2, 0, L.height / 2) : ctx.createLinearGradient(-L.width / 2, 0, L.width / 2, 0);
      for (var k = 0; k <= 8; k++) g.addColorStop(k / 8, 'hsl(' + Math.round(frac(k / 8 * .6 - o.u * cyc(o, .125)) * 360) + ',100%,62%)');
      var pulse = 1 + .25 * Math.sin(o.u * TAU * cyc(o, .25)), base = ctx.globalAlpha;
      ctx.save(); ctx.lineJoin = 'round'; ctx.strokeStyle = g; ctx.globalCompositeOperation = 'lighter';
      ctx.globalAlpha = base * .25; ctx.lineWidth = o.size * .14 * pulse; strokeAll(ctx, L);
      ctx.globalAlpha = base * .5; ctx.lineWidth = o.size * .07; strokeAll(ctx, L);
      ctx.globalAlpha = base; ctx.lineWidth = o.size * .03; strokeAll(ctx, L);
      ctx.globalCompositeOperation = 'source-over'; ctx.strokeStyle = 'rgba(255,255,255,.8)'; ctx.lineWidth = Math.max(1, o.size * .01); strokeAll(ctx, L);
      ctx.restore();
    },
    /* Solid letters with four-point stars twinkling along their edges. */
    sparkle: function (ctx, L, o) {
      fillAll(ctx, L);
      var pts = points(ctx, L, o.size), n = Math.min(pts.length, 34), cyc = Math.max(1, Math.round(o.period / 1.6)), c = rgb(o.color), glow = sprite(c);
      ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = '#fff';
      var base = ctx.globalAlpha;
      for (var i = 0; i < n; i++) {
        var p = pts[i], t = frac(o.u * cyc + hash(i, 3)), s = Math.sin(Math.PI * clamp(t / .5, 0, 1));
        if (t > .5 || s < .02) continue;
        var r = o.size * (.1 + .12 * hash(i, 7)) * s;
        ctx.globalAlpha = base * s * .7; ctx.drawImage(glow, p.x - r, p.y - r, r * 2, r * 2);
        ctx.globalAlpha = base * s; ctx.beginPath();
        ctx.moveTo(p.x, p.y - r); ctx.quadraticCurveTo(p.x, p.y, p.x + r, p.y); ctx.quadraticCurveTo(p.x, p.y, p.x, p.y + r);
        ctx.quadraticCurveTo(p.x, p.y, p.x - r, p.y); ctx.quadraticCurveTo(p.x, p.y, p.x, p.y - r); ctx.fill();
      }
      ctx.restore();
    }
  };

  window.SMTextFx = {
    names: NAMES.slice(),
    /* Animations that use the glow colour. */
    colored: ['saber', 'neon', 'fire', 'electric', 'lightning', 'runner', 'sparkle'],
    defaultColor: function (name) { return DEFAULT_COLORS[name] || '#52d5ff'; },
    /* Speed steps of the slider (the middle one is x1). */
    speeds: [.25, .35, .5, .7, 1, 1.4, 2, 3, 4],
    has: function (name) { return NAMES.indexOf(name) >= 0; },
    /* Size of the text block in context units (for the on-canvas handles). */
    measure: function (ctx, lines, size, vertical) { var L = layout(ctx, lines, size, vertical); return { width: L.width, height: L.height }; },
    /* lines: text lines; o: {u, period (s), speed (1-4), size (px), color, vertical}.
       name 'plain' draws still letters (used for vertical text without animation). */
    draw: function (ctx, name, lines, o) {
      var fn = FX[name]; if (!fn) return false;
      var L = layout(ctx, lines, o.size, o.vertical), speed = clamp(Number(o.speed) || 1, .25, 4), period = o.period || 8, u = frac(o.u), opts;
      if (ONE_SHOT.indexOf(name) >= 0) {
        var repeats = speed >= 1 ? Math.max(1, Math.round(speed)) : 1;
        opts = { u: frac(u * repeats), period: period / repeats, span: speed < 1 ? Math.min(.9, .55 / speed) : .55 };
      } else opts = { u: u, period: period * speed, span: .55 };
      opts.size = o.size; opts.color = o.color || DEFAULT_COLORS[name] || '#52d5ff';
      ctx.save();
      try { fn(ctx, L, opts); } finally { ctx.restore(); }
      return true;
    }
  };
})();
