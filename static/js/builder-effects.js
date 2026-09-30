/* Procedural Builder effects (2026-09-30). Each effect draws the whole canvas for time t
   (seconds) in the layer colour; showcase-builder.js positions / rotates the layer and
   calls SMBuilderEffects.draw. Glows use cached radial sprites and additive blending
   instead of shadowBlur, which keeps 30 fps cheap. Everything is deterministic (hashed
   seeds), so the preview tiles and the exported animation look the same. */
(function () {
  'use strict';
  var TAU = Math.PI * 2;
  // particle / stars / streaks replace the Builder's old versions (the first two looked the same).
  var NAMES = ['particle', 'stars', 'streaks', 'rain', 'aura', 'fireflies', 'bokeh', 'hyperspace', 'network', 'rings', 'scan', 'arcane', 'hex', 'glitch', 'dotwave', 'smoke', 'embers', 'shards', 'crosses'];
  var sprites = new Map();

  function hash(i, k) { var n = Math.sin(i * 127.1 + k * 311.7) * 43758.5453; return n - Math.floor(n); }
  function rgb(hex) { var v = /^#?([0-9a-f]{6})$/i.exec(hex || '') ? hex.replace('#', '') : '52d5ff'; return [parseInt(v.slice(0, 2), 16), parseInt(v.slice(2, 4), 16), parseInt(v.slice(4, 6), 16)]; }
  function rgba(c, a) { return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + a + ')'; }
  function mixWhite(c, k) { return [c[0] + (255 - c[0]) * k | 0, c[1] + (255 - c[1]) * k | 0, c[2] + (255 - c[2]) * k | 0]; }
  function frac(v) { return v - Math.floor(v); }
  /* Soft round glow sprite, cached per colour and size bucket. */
  function glow(color, radius, soft) {
    var r = Math.max(2, Math.round(radius)), key = color + '|' + r + '|' + (soft ? 1 : 0), s = sprites.get(key);
    if (s) return s;
    s = document.createElement('canvas'); s.width = s.height = r * 2;
    var g = s.getContext('2d'), c = rgb(color), grad = g.createRadialGradient(r, r, 0, r, r, r);
    if (soft) { grad.addColorStop(0, rgba(c, .55)); grad.addColorStop(1, rgba(c, 0)); }
    else { grad.addColorStop(0, rgba(mixWhite(c, .85), 1)); grad.addColorStop(.18, rgba(c, .9)); grad.addColorStop(.45, rgba(c, .25)); grad.addColorStop(1, rgba(c, 0)); }
    g.fillStyle = grad; g.fillRect(0, 0, r * 2, r * 2);
    if (sprites.size > 160) sprites.delete(sprites.keys().next().value);
    sprites.set(key, s);
    return s;
  }
  /* A falling drop: transparent tail, bright tip (motion blur), cached per colour. */
  function rainSprite(color) {
    var key = 'rain|' + color, s = sprites.get(key);
    if (s) return s;
    s = document.createElement('canvas'); s.width = 4; s.height = 64;
    var g = s.getContext('2d'), c = rgb(color), grad = g.createLinearGradient(0, 0, 0, 64);
    grad.addColorStop(0, rgba(c, 0)); grad.addColorStop(.75, rgba(c, .55)); grad.addColorStop(1, rgba(mixWhite(c, .7), 1));
    g.fillStyle = grad; g.fillRect(1, 0, 2, 64);
    sprites.set(key, s);
    return s;
  }
  function dot(ctx, color, x, y, r, alpha, soft) {
    if (alpha <= 0.01 || r <= 0) return;
    var s = glow(color, Math.max(3, r * 4), soft);
    ctx.globalAlpha = Math.min(1, alpha);
    ctx.drawImage(s, x - r * 4, y - r * 4, r * 8, r * 8);
  }

  var draw = {
    /* Rain: three depth layers of motion-blurred drops slanted by a light wind, splashes
       with ripples near the bottom and a soft mist. Drops are one cached gradient sprite
       drawn in a rotated space, so a heavy shower stays cheap. */
    rain: function (ctx, W, H, o, c) {
      var t = o.t * o.speed, wind = -.16, light = mixWhite(c, .55), diag = Math.hypot(W, H);
      var sprite = rainSprite(o.color);
      var layers = [[120, .5, 1.2, .5, .6], [85, .8, 1.8, .7, .85], [40, 1.2, 2.6, .95, 1.15]];
      ctx.save(); ctx.globalCompositeOperation = 'lighter';
      ctx.translate(W / 2, H / 2); ctx.rotate(wind); ctx.translate(-diag / 2, -diag / 2);
      layers.forEach(function (layer, li) {
        var n = Math.round(layer[0] * o.density), speed = layer[1], width = layer[2] * o.scale, alpha = layer[3], len = (38 + li * 26) * layer[4] * o.scale;
        for (var i = 0; i < n; i++) {
          var id = i + li * 500, fall = frac(hash(id, 1) + t * speed * (.9 + hash(id, 2) * .3));
          var x = hash(id, 3) * diag, y = fall * (diag + len) - len;
          ctx.globalAlpha = alpha * (.6 + .4 * hash(id, 4));
          ctx.drawImage(sprite, x - width / 2, y, width, len);
        }
      });
      ctx.restore();
      // Splashes: a small ring and two droplets where the nearest drops land.
      ctx.save(); ctx.globalCompositeOperation = 'lighter'; ctx.strokeStyle = rgba(light, 1); ctx.fillStyle = rgba(light, 1);
      var splashes = Math.round(18 * o.density);
      for (var k = 0; k < splashes; k++) {
        var cycle = .55 + hash(k, 7) * .6, p = frac(t / cycle + hash(k, 8)), sx = hash(k, 9) * W, sy = H * (.82 + hash(k, 10) * .16);
        if (p > .45) continue;
        var q = p / .45, rx = (3 + q * 14) * o.scale, ry = rx * .28;
        ctx.globalAlpha = (1 - q) * .55; ctx.lineWidth = Math.max(.6, .9 * o.scale);
        ctx.beginPath(); ctx.ellipse(sx, sy, rx, ry, 0, 0, TAU); ctx.stroke();
        var up = Math.sin(q * Math.PI) * 9 * o.scale;
        ctx.globalAlpha = (1 - q) * .7;
        ctx.beginPath(); ctx.arc(sx - rx * .6, sy - up, 1.1 * o.scale, 0, TAU); ctx.arc(sx + rx * .5, sy - up * .8, .9 * o.scale, 0, TAU); ctx.fill();
      }
      ctx.restore();
      // Mist near the bottom.
      var mist = ctx.createLinearGradient(0, H * .72, 0, H);
      mist.addColorStop(0, rgba(c, 0)); mist.addColorStop(1, rgba(c, .1 * Math.min(1.4, o.density)));
      ctx.globalCompositeOperation = 'screen'; ctx.globalAlpha = 1; ctx.fillStyle = mist; ctx.fillRect(0, H * .72, W, H * .28);
    },
    /* Particle flow: particles ride a smooth flow field and leave short glowing trails. */
    particle: function (ctx, W, H, o, c) {
      var n = Math.round(90 * o.density), t = o.t * o.speed, light = mixWhite(c, .35);
      function field(x, y, time) { return Math.sin(x * 2.1 + time * .35) * 1.1 + Math.cos(y * 3.3 - time * .28) * .9; }
      ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round';
      for (var i = 0; i < n; i++) {
        var life = frac(hash(i, 1) + t * (.06 + hash(i, 2) * .05)), x0 = hash(i, 3), y0 = 1.08 - life * 1.2;
        var px = [], steps = 7;
        for (var k = 0; k <= steps; k++) {
          var ly = y0 + k * .012, ang = field(x0, ly, t - k * .08);
          px.push([(x0 + Math.sin(ang) * .05 + (life - k * .004) * .04 * Math.cos(i)) * W, ly * H]);
        }
        var fade = Math.sin(Math.min(1, life) * Math.PI);
        for (var s = 0; s < steps; s++) {
          ctx.strokeStyle = rgba(light, fade * (1 - s / steps) * .7);
          ctx.lineWidth = Math.max(.6, (1.8 - s * .2) * o.scale);
          ctx.beginPath(); ctx.moveTo(px[s][0], px[s][1]); ctx.lineTo(px[s + 1][0], px[s + 1][1]); ctx.stroke();
        }
        dot(ctx, o.color, px[0][0], px[0][1], 1.5 * o.scale, fade, false);
      }
    },
    /* Starfield drift: three parallax layers, twinkling, flares on the brightest stars. */
    stars: function (ctx, W, H, o, c) {
      var t = o.t * o.speed, layers = [[.012, .7, 70], [.025, 1.1, 45], [.045, 1.7, 22]], light = mixWhite(c, .55);
      ctx.globalCompositeOperation = 'lighter';
      layers.forEach(function (layer, li) {
        var n = Math.round(layer[2] * o.density);
        for (var i = 0; i < n; i++) {
          var id = i + li * 1000, x = frac(hash(id, 1) + t * layer[0]) * W, y = hash(id, 2) * H;
          var tw = .45 + .55 * Math.pow(.5 + .5 * Math.sin(t * (1.5 + hash(id, 3) * 3) + id), 2), r = layer[1] * (.6 + hash(id, 4) * .8) * o.scale;
          dot(ctx, o.color, x, y, r, tw * (.55 + li * .2), false);
          if (li === 2 && hash(id, 5) > .7) {
            var len = r * 7 * tw; ctx.globalAlpha = tw * .55; ctx.strokeStyle = rgba(light, 1); ctx.lineWidth = Math.max(.5, .7 * o.scale);
            ctx.beginPath(); ctx.moveTo(x - len, y); ctx.lineTo(x + len, y); ctx.moveTo(x, y - len); ctx.lineTo(x, y + len); ctx.stroke();
          }
        }
      });
    },
    /* Light streaks: meteors on one diagonal with long fading tails and a bright head. */
    streaks: function (ctx, W, H, o, c) {
      var n = Math.round(16 * o.density), t = o.t * o.speed, ang = Math.PI * .8, dx = Math.cos(ang), dy = Math.sin(ang), diag = Math.hypot(W, H), light = mixWhite(c, .6);
      ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round';
      for (var i = 0; i < n; i++) {
        var cycle = 1.6 + hash(i, 1) * 2.4, p = frac(t / cycle + hash(i, 2)), active = p < .55;
        if (!active) continue;
        var q = p / .55, len = (.18 + hash(i, 3) * .25) * diag * o.scale;
        // (dx, dy) points down-left; heads start above the top edge and cross the canvas.
        var sx = (hash(i, 4) * 1.5 + .05) * W, sy = -.08 * H, travel = diag * 1.25 * q;
        var hx = sx + dx * travel, hy = sy + dy * travel, tx = hx - dx * len, ty = hy - dy * len;
        var fade = Math.sin(q * Math.PI), g = ctx.createLinearGradient(tx, ty, hx, hy);
        g.addColorStop(0, rgba(c, 0)); g.addColorStop(.7, rgba(c, .35 * fade)); g.addColorStop(1, rgba(light, .95 * fade));
        ctx.strokeStyle = g; ctx.lineWidth = Math.max(.8, (1.2 + hash(i, 5) * 1.6) * o.scale);
        ctx.beginPath(); ctx.moveTo(tx, ty); ctx.lineTo(hx, hy); ctx.stroke();
        dot(ctx, o.color, hx, hy, 2.2 * o.scale, fade, false);
      }
    },
    aura: function (ctx, W, H, o, c) {
      var cx = W / 2, cy = H / 2, R = Math.hypot(W, H) * .62 * o.scale, n = Math.round(40 * o.density), t = o.t * o.speed;
      ctx.globalCompositeOperation = 'lighter';
      for (var i = 0; i < n; i++) {
        var a = i / n * TAU + t * .06 + hash(i, 1) * .2, len = R * (.45 + .55 * (.5 + .5 * Math.sin(t * (.7 + hash(i, 2)) + i))), wdt = .012 + hash(i, 3) * .02;
        var g = ctx.createLinearGradient(cx, cy, cx + Math.cos(a) * len, cy + Math.sin(a) * len);
        g.addColorStop(0, rgba(mixWhite(c, .5), .35)); g.addColorStop(1, rgba(c, 0));
        ctx.globalAlpha = .55 + .45 * Math.sin(t * 1.3 + i * 1.7);
        ctx.fillStyle = g; ctx.beginPath(); ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(a - wdt) * len, cy + Math.sin(a - wdt) * len); ctx.lineTo(cx + Math.cos(a + wdt) * len, cy + Math.sin(a + wdt) * len); ctx.closePath(); ctx.fill();
      }
      dot(ctx, o.color, cx, cy, Math.min(W, H) * .06 * o.scale, .8, false);
    },
    fireflies: function (ctx, W, H, o) {
      var n = Math.round(46 * o.density), t = o.t * o.speed;
      ctx.globalCompositeOperation = 'lighter';
      for (var i = 0; i < n; i++) {
        var x = (hash(i, 1) + .06 * Math.sin(t * (.25 + hash(i, 2) * .3) + i)) * W, y = (hash(i, 3) + .05 * Math.cos(t * (.2 + hash(i, 4) * .3) + i * 2)) * H;
        var blink = Math.pow(.5 + .5 * Math.sin(t * (1.2 + hash(i, 5) * 2) + i * 3), 3);
        dot(ctx, o.color, x, y, (1.4 + hash(i, 6) * 2.2) * o.scale, .25 + .75 * blink, false);
      }
    },
    bokeh: function (ctx, W, H, o) {
      var n = Math.round(22 * o.density), t = o.t * o.speed;
      ctx.globalCompositeOperation = 'screen';
      for (var i = 0; i < n; i++) {
        var r = (14 + hash(i, 1) * 46) * o.scale, y = frac(hash(i, 2) - t * (.012 + hash(i, 3) * .02)) * (H + r * 2) - r, x = (hash(i, 4) + .03 * Math.sin(t * .3 + i)) * W;
        dot(ctx, o.color, x, y, r / 4, .22 + hash(i, 5) * .3, true);
      }
    },
    hyperspace: function (ctx, W, H, o, c) {
      var n = Math.round(140 * o.density), t = o.t * o.speed, cx = W / 2, cy = H / 2, R = Math.hypot(W, H) * .6;
      ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round';
      for (var i = 0; i < n; i++) {
        var a = hash(i, 1) * TAU, z = frac(hash(i, 2) - t * (.18 + hash(i, 3) * .12)), d = Math.pow(1 - z, 2.2) * R, d0 = d * (.72 - .1 * hash(i, 4));
        if (d < 4) continue;
        ctx.strokeStyle = rgba(mixWhite(c, .35 * (1 - z)), Math.min(1, (1 - z) * 1.3));
        ctx.lineWidth = (.6 + (1 - z) * 2.2) * o.scale;
        ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * d0, cy + Math.sin(a) * d0); ctx.lineTo(cx + Math.cos(a) * d, cy + Math.sin(a) * d); ctx.stroke();
      }
    },
    network: function (ctx, W, H, o, c) {
      var n = Math.round(44 * o.density), t = o.t * o.speed, pts = [], max = Math.min(W, H) * .22 * o.scale;
      for (var i = 0; i < n; i++) pts.push([(hash(i, 1) + .08 * Math.sin(t * (.12 + hash(i, 2) * .2) + i)) * W, (hash(i, 3) + .08 * Math.cos(t * (.1 + hash(i, 4) * .2) + i)) * H]);
      ctx.globalCompositeOperation = 'lighter'; ctx.lineWidth = Math.max(.6, .9 * o.scale);
      for (var a = 0; a < n; a++) for (var b = a + 1; b < n; b++) {
        var dx = pts[a][0] - pts[b][0], dy = pts[a][1] - pts[b][1], d = Math.sqrt(dx * dx + dy * dy);
        if (d < max) { ctx.strokeStyle = rgba(c, (1 - d / max) * .55); ctx.beginPath(); ctx.moveTo(pts[a][0], pts[a][1]); ctx.lineTo(pts[b][0], pts[b][1]); ctx.stroke(); }
      }
      pts.forEach(function (p, i) { dot(ctx, o.color, p[0], p[1], 1.6 * o.scale, .8 + .2 * Math.sin(t + i), false); });
    },
    rings: function (ctx, W, H, o, c) {
      var cx = W / 2, cy = H / 2, base = Math.min(W, H) * .2 * o.scale, t = o.t * o.speed * 3, bars = 96;
      ctx.globalCompositeOperation = 'lighter'; ctx.lineCap = 'round';
      for (var ring = 0; ring < 3; ring++) {
        var r = base * (1 + ring * .38);
        ctx.lineWidth = Math.max(1, (2.4 - ring * .5) * o.scale);
        for (var i = 0; i < bars; i++) {
          var a = i / bars * TAU + ring * .3 + t * .05 * (ring % 2 ? -1 : 1);
          var amp = Math.abs(Math.sin(i * .37 + t * (1 + ring * .3)) * Math.sin(i * .11 - t * .7)) * base * .22 * o.density;
          ctx.strokeStyle = rgba(ring ? c : mixWhite(c, .4), .45 + .4 * (amp / (base * .22 + 1)));
          ctx.beginPath(); ctx.moveTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r); ctx.lineTo(cx + Math.cos(a) * (r + 2 + amp), cy + Math.sin(a) * (r + 2 + amp)); ctx.stroke();
        }
      }
    },
    scan: function (ctx, W, H, o, c) {
      var cx = W / 2, cy = H / 2, R = Math.hypot(W, H) * .55 * o.scale, t = o.t * o.speed;
      ctx.globalCompositeOperation = 'lighter';
      for (var k = 0; k < 3; k++) {
        var p = frac(t * .35 + k / 3), r = p * R;
        ctx.strokeStyle = rgba(c, (1 - p) * .75); ctx.lineWidth = Math.max(1, 2.5 * o.scale * (1 - p) + .6);
        ctx.beginPath(); ctx.arc(cx, cy, r, 0, TAU); ctx.stroke();
      }
      var y = frac(t * .22) * (H + 80) - 40, g = ctx.createLinearGradient(0, y - 40, 0, y + 4);
      g.addColorStop(0, rgba(c, 0)); g.addColorStop(1, rgba(mixWhite(c, .4), .38 * o.density));
      ctx.fillStyle = g; ctx.globalAlpha = 1; ctx.fillRect(0, y - 40, W, 44);
    },
    arcane: function (ctx, W, H, o, c) {
      var cx = W / 2, cy = H / 2, R = Math.min(W, H) * .34 * o.scale, t = o.t * o.speed, light = mixWhite(c, .45);
      ctx.globalCompositeOperation = 'lighter'; ctx.lineWidth = Math.max(1, 1.6 * o.scale);
      dot(ctx, o.color, cx, cy, R * .28, .25 + .1 * Math.sin(t * 2), true);
      ctx.save(); ctx.translate(cx, cy);
      ctx.rotate(t * .25);
      ctx.strokeStyle = rgba(c, .85); ctx.beginPath(); ctx.arc(0, 0, R, 0, TAU); ctx.stroke();
      ctx.beginPath(); ctx.arc(0, 0, R * .9, 0, TAU); ctx.stroke();
      for (var i = 0; i < 36; i++) {  // rune ticks between the outer circles
        var a = i / 36 * TAU, k = hash(i, 7);
        ctx.strokeStyle = rgba(light, .5 + .5 * Math.sin(t * 2 + i));
        ctx.beginPath(); ctx.moveTo(Math.cos(a) * R * .92, Math.sin(a) * R * .92);
        ctx.lineTo(Math.cos(a + .05 * (k - .5)) * R * (.96 + .02 * k), Math.sin(a + .05 * (k - .5)) * R * (.96 + .02 * k)); ctx.stroke();
      }
      ctx.rotate(-t * .55);
      ctx.strokeStyle = rgba(light, .9); ctx.beginPath();  // pentagram
      for (var s = 0; s <= 5; s++) { var b = -Math.PI / 2 + s * 4 * Math.PI / 5, px = Math.cos(b) * R * .78, py = Math.sin(b) * R * .78; s ? ctx.lineTo(px, py) : ctx.moveTo(px, py); }
      ctx.stroke();
      ctx.strokeStyle = rgba(c, .7); ctx.beginPath(); ctx.arc(0, 0, R * .78, 0, TAU); ctx.stroke();
      ctx.beginPath(); ctx.arc(0, 0, R * .32, 0, TAU); ctx.stroke();
      for (var j = 0; j < 5; j++) { var e = -Math.PI / 2 + j * TAU / 5; dot(ctx, o.color, Math.cos(e) * R * .78, Math.sin(e) * R * .78, 2.6 * o.scale, .9, false); }
      ctx.restore();
    },
    hex: function (ctx, W, H, o, c) {
      var s = 24 * o.scale, t = o.t * o.speed, cx = W / 2, cy = H / 2, hw = Math.sqrt(3) * s, hh = 1.5 * s;
      ctx.globalCompositeOperation = 'lighter'; ctx.lineWidth = Math.max(.8, 1.2 * o.scale);
      for (var row = -1; row * hh < H + s; row++) for (var col = -1; col * hw < W + hw; col++) {
        var x = col * hw + (row % 2 ? hw / 2 : 0), y = row * hh, d = Math.hypot(x - cx, y - cy);
        var a = Math.max(0, Math.sin(d * .022 / o.scale - t * 2.6)) * o.density;
        if (a < .06) continue;
        ctx.strokeStyle = rgba(c, Math.min(.9, a * .8)); ctx.beginPath();
        for (var k = 0; k < 6; k++) { var an = Math.PI / 6 + k * Math.PI / 3, px = x + Math.cos(an) * s * .92, py = y + Math.sin(an) * s * .92; k ? ctx.lineTo(px, py) : ctx.moveTo(px, py); }
        ctx.closePath(); ctx.stroke();
      }
    },
    glitch: function (ctx, W, H, o, c) {
      var t = o.t * o.speed, step = Math.floor(t * 14), burst = hash(Math.floor(t * 1.6), 9) > .45;
      ctx.globalCompositeOperation = 'lighter';
      var n = Math.round((burst ? 14 : 4) * o.density);
      for (var i = 0; i < n; i++) {
        var y = hash(step, i) * H, h = (2 + hash(step, i + 40) * (burst ? 18 : 5)) * o.scale, x = hash(step, i + 80) * W * .6, w = W * (.2 + hash(step, i + 120) * .7);
        ctx.globalAlpha = .25 + hash(step, i + 160) * .45;
        ctx.fillStyle = rgba(i % 3 === 0 ? [255, 40, 90] : (i % 3 === 1 ? [40, 230, 255] : c), 1);
        ctx.fillRect(x, y, w, h);
      }
      ctx.globalAlpha = .08; ctx.fillStyle = rgba(c, 1);
      for (var yy = frac(t * .5) * 4; yy < H; yy += 4) ctx.fillRect(0, yy, W, 1);
    },
    dotwave: function (ctx, W, H, o, c) {
      var gap = 20 * o.scale, t = o.t * o.speed * 2.4;
      ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = rgba(mixWhite(c, .25), 1);
      for (var y = gap / 2; y < H; y += gap) for (var x = gap / 2; x < W; x += gap) {
        var v = .5 + .5 * Math.sin(x * .045 / o.scale + y * .03 / o.scale - t);
        ctx.globalAlpha = (.12 + .75 * v * v) * Math.min(1, o.density);
        var r = (.8 + 2.2 * v) * o.scale; ctx.fillRect(x - r / 2, y - r / 2, r, r);
      }
    },
    smoke: function (ctx, W, H, o) {
      var n = Math.round(16 * o.density), t = o.t * o.speed;
      ctx.globalCompositeOperation = 'screen';
      for (var i = 0; i < n; i++) {
        var life = frac(hash(i, 1) + t * (.035 + hash(i, 2) * .03)), r = (60 + 160 * life) * o.scale * (.7 + hash(i, 3) * .6);
        var x = (hash(i, 4) + .12 * Math.sin(t * .2 + i) + life * .1) * W, y = H * (1.05 - life * 1.2);
        dot(ctx, o.color, x, y, r / 4, .22 * Math.sin(life * Math.PI), true);
      }
    },
    embers: function (ctx, W, H, o) {
      var n = Math.round(70 * o.density), t = o.t * o.speed;
      ctx.globalCompositeOperation = 'lighter';
      for (var i = 0; i < n; i++) {
        var life = frac(hash(i, 1) + t * (.08 + hash(i, 2) * .1)), x = (hash(i, 3) + .04 * Math.sin(t * 1.4 + i * 3) + (life - .5) * .06 * (hash(i, 5) - .5)) * W, y = H * (1.02 - life * 1.1);
        var flick = .6 + .4 * Math.sin(t * 9 + i * 5);
        dot(ctx, o.color, x, y, (1 + hash(i, 4) * 1.8) * o.scale * (1 - life * .5), (1 - life) * flick, false);
      }
    },
    shards: function (ctx, W, H, o, c) {
      var n = Math.round(20 * o.density), t = o.t * o.speed;
      ctx.lineWidth = Math.max(.8, 1.1 * o.scale);
      for (var i = 0; i < n; i++) {
        var size = (10 + hash(i, 1) * 26) * o.scale, y = frac(hash(i, 2) + t * (.03 + hash(i, 3) * .04)) * (H + size * 2) - size, x = (hash(i, 4) + .03 * Math.sin(t * .6 + i)) * W, a = t * (hash(i, 5) - .5) * 1.4 + i;
        ctx.save(); ctx.translate(x, y); ctx.rotate(a);
        ctx.beginPath(); ctx.moveTo(0, -size); ctx.lineTo(size * (.35 + hash(i, 6) * .4), size * (.2 + hash(i, 7) * .5)); ctx.lineTo(-size * (.3 + hash(i, 8) * .4), size * .6); ctx.closePath();
        var shine = .5 + .5 * Math.sin(t * 2 + i * 3);
        ctx.globalCompositeOperation = 'screen'; ctx.globalAlpha = .08 + .12 * shine; ctx.fillStyle = rgba(c, 1); ctx.fill();
        ctx.globalCompositeOperation = 'lighter'; ctx.globalAlpha = .35 + .5 * shine; ctx.strokeStyle = rgba(mixWhite(c, .5), 1); ctx.stroke();
        ctx.restore();
      }
    },
    crosses: function (ctx, W, H, o, c) {
      var n = Math.round(60 * o.density), t = o.t * o.speed, p = Math.max(1.5, 2.2 * o.scale);
      ctx.globalCompositeOperation = 'lighter'; ctx.fillStyle = rgba(mixWhite(c, .3), 1);
      for (var i = 0; i < n; i++) {
        var x = Math.round(hash(i, 1) * W / p) * p, y = Math.round(hash(i, 2) * H / p) * p, v = Math.max(0, Math.sin(t * (1 + hash(i, 3) * 2) + i * 2.3));
        if (v < .05) continue;
        ctx.globalAlpha = v; ctx.fillRect(x - p, y, p * 3, p); ctx.fillRect(x, y - p, p, p * 3);
      }
    }
  };

  window.SMBuilderEffects = {
    names: NAMES.slice(),
    has: function (name) { return NAMES.indexOf(name) >= 0; },
    /* o: {t: seconds, color, speed (1 = normal), density (1 = normal), scale (1 = normal)} */
    draw: function (ctx, W, H, name, o) {
      var fn = draw[name]; if (!fn) return;
      var opts = { t: o.t || 0, color: o.color || '#52d5ff', speed: o.speed || 1, density: o.density || 1, scale: o.scale || 1 };
      ctx.save();
      try { fn(ctx, W, H, opts, rgb(opts.color)); } finally { ctx.restore(); }
    }
  };
})();
