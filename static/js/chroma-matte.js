/* Background keying for characters on a solid backdrop of any colour.
   Browser twin of smweb/chroma_matte.py (Character compose on the server): keep the
   formulas identical, tests/test_chroma_matte.py runs both on the same picture.

   SMChroma.estimate([imageData...])        -> model of the backdrop (once per clip)
   SMChroma.resolve(mode, model)            -> model to key with, or null (leave as is)
   SMChroma.apply(imageData, model, opts, previousState) -> state for the next frame
     opts: {tolerance: 10..120, softness: 0..40, holes: true}
   Only backdrop connected to the frame border is removed (magic-wand fill), big enclosed
   pockets too, small ones (eyes, highlights) stay; the decision uses a 3x3 average of the
   distance (ignores dithering/compression noise); soft rims get the backdrop un-mixed out;
   in clips the alpha of unchanged pixels is averaged with the previous frame (no shimmer). */
(function (root) {
  'use strict';
  var RING = 2, CLUSTER = 36, MIN_COVERAGE = 0.3, HOLE_SHARE = 0.0008, SPECK_SHARE = 0.00005, STATIC_DIFF = 10, POCKET_MIN = 8, POCKET_EXACT = 0.5, FOREIGN = 0.3, OWN_BACKDROP = 0.45, OWN_SPREAD = 12;
  var PRESETS = { green: [0, 177, 64], blue: [0, 71, 187], red: [210, 30, 40], white: [255, 255, 255], black: [0, 0, 0] };

  function ycc(r, g, b) { return [0.299 * r + 0.587 * g + 0.114 * b, -0.168736 * r - 0.331264 * g + 0.5 * b, 0.5 * r - 0.418688 * g - 0.081312 * b]; }
  function keyInfo(key) {
    var c = ycc(key[0], key[1], key[2]), saturation = Math.hypot(c[1], c[2]);
    return { y: c[0], cb: c[1], cr: c[2], saturation: saturation, weight: 1 - 0.65 * Math.min(1, Math.max(0, (saturation - 20) / 40)) };
  }
  function distanceTo(r, g, b, k) {
    var y = 0.299 * r + 0.587 * g + 0.114 * b - k.y, cb = -0.168736 * r - 0.331264 * g + 0.5 * b - k.cb, cr = 0.5 * r - 0.418688 * g - 0.081312 * b - k.cr;
    return Math.sqrt(k.weight * y * y + cb * cb + cr * cr);
  }
  function ringSamples(image, out) {
    var d = image.data, w = image.width, h = image.height, band = Math.min(RING, Math.max(1, h >> 1), Math.max(1, w >> 1));
    function take(x, y) { var p = (y * w + x) * 4; if (d[p + 3] >= 128) out.push(d[p], d[p + 1], d[p + 2]); }
    for (var y = 0; y < h; y++) {
      var edgeRow = y < band || y >= h - band;
      for (var x = 0; x < w; x++) { if (edgeRow || x < band || x >= w - band) take(x, y); }
    }
  }
  function percentile(values, share) {
    if (!values.length) return 0;
    var sorted = Float64Array.from(values).sort(), pos = (sorted.length - 1) * share, lo = Math.floor(pos), hi = Math.min(sorted.length - 1, lo + 1);
    return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
  }
  function estimate(images, maxFrames) {
    images = (images || []).filter(Boolean); maxFrames = maxFrames || 12;
    if (!images.length) return null;
    var step = Math.max(1, Math.floor(images.length / maxFrames)), flat = [];
    for (var i = 0, used = 0; i < images.length && used < maxFrames; i += step, used++) ringSamples(images[i], flat);
    var n = flat.length / 3; if (!n) return null;
    var bins = new Uint32Array(32768), peak = 0;
    for (var s = 0; s < n; s++) { var code = (flat[s * 3] >> 3) * 1024 + (flat[s * 3 + 1] >> 3) * 32 + (flat[s * 3 + 2] >> 3); bins[code]++; if (bins[code] > bins[peak] || (bins[code] === bins[peak] && code < peak)) peak = code; }
    var centre = [(peak >> 10) * 8 + 4, ((peak >> 5) & 31) * 8 + 4, (peak & 31) * 8 + 4], sum = [0, 0, 0], members = [];
    for (s = 0; s < n; s++) {
      var r = flat[s * 3], g = flat[s * 3 + 1], b = flat[s * 3 + 2], dr = r - centre[0], dg = g - centre[1], db = b - centre[2];
      if (Math.sqrt(dr * dr + dg * dg + db * db) < CLUSTER) { sum[0] += r; sum[1] += g; sum[2] += b; members.push(s); }
    }
    var count = members.length; if (!count) return null;
    var key = [sum[0] / count, sum[1] / count, sum[2] / count], k = keyInfo(key), dists = new Array(count);
    for (var m = 0; m < count; m++) { s = members[m]; dists[m] = distanceTo(flat[s * 3], flat[s * 3 + 1], flat[s * 3 + 2], k); }
    var model = { key: key, spread: percentile(dists, 0.9), coverage: count / n, onset: 0 };
    var limit = Math.max(12, Math.max(model.spread * 2.5 + 4, 10)), far = [];
    for (i = 0, used = 0; i < images.length && used < maxFrames; i += step, used++) {
      var dd = images[i].data, total = images[i].width * images[i].height;
      for (var p = 0; p < total; p += 4) { if (dd[p * 4 + 3] < 128) continue; var v = distanceTo(dd[p * 4], dd[p * 4 + 1], dd[p * 4 + 2], k); if (v > limit) far.push(v); }
    }
    // where the figure's colours begin; the tolerance stays below it (muted backdrops vs dark clothes)
    // first 4-unit bin holding a quarter of the fullest one: a real colour mass, not the edge tail
    if (far.length >= 50) {
      var bins = [], top = 0;
      for (var f = 0; f < far.length; f++) { var b = Math.floor((far[f] - limit) / 4); bins[b] = (bins[b] || 0) + 1; if (bins[b] > top) top = bins[b]; }
      for (b = 0; b < bins.length; b++) if ((bins[b] || 0) >= 0.25 * top) { model.onset = limit + b * 4; break; }
    }
    return model;
  }
  function resolve(mode, model) {
    mode = String(mode || 'auto').trim().toLowerCase();
    if (mode === 'none' || mode === 'off' || mode === '0' || !mode) return null;
    var wanted = PRESETS[mode] || null;
    if (!wanted && /^#[0-9a-f]{6}$/.test(mode)) wanted = [parseInt(mode.slice(1, 3), 16), parseInt(mode.slice(3, 5), 16), parseInt(mode.slice(5, 7), 16)];
    if (!wanted) return model && model.coverage >= MIN_COVERAGE ? model : null;
    if (model && distanceTo(model.key[0], model.key[1], model.key[2], keyInfo(wanted)) < 40) return model;
    return { key: wanted.slice(), spread: 0, coverage: 0, onset: 0 };
  }
  function thresholds(model, opts) {
    var tolerance = Math.max(10, Math.min(120, opts.tolerance == null ? 45 : Number(opts.tolerance)));
    var softness = Math.max(0, Math.min(40, opts.softness == null ? 16 : Number(opts.softness)));
    var floor = model.spread * 1.25 + 4, inner = Math.max(6 + (tolerance - 10) * 0.75, floor);
    if (model.onset > 0) inner = Math.min(inner, Math.max(floor, 0.75 * model.onset));
    return [inner, inner + (softness > 0 ? 4 + softness * 1.2 : 0)];
  }
  /* 4-connected components of `mask`; label -1 = outside the mask. */
  function components(mask, w, h) {
    var labels = new Int32Array(w * h).fill(-1), stack = new Int32Array(w * h), count = 0;
    for (var start = 0; start < mask.length; start++) {
      if (!mask[start] || labels[start] >= 0) continue;
      var top = 0; stack[top++] = start; labels[start] = count;
      while (top) {
        var p = stack[--top], x = p % w;
        if (x > 0 && mask[p - 1] && labels[p - 1] < 0) { labels[p - 1] = count; stack[top++] = p - 1; }
        if (x < w - 1 && mask[p + 1] && labels[p + 1] < 0) { labels[p + 1] = count; stack[top++] = p + 1; }
        if (p >= w && mask[p - w] && labels[p - w] < 0) { labels[p - w] = count; stack[top++] = p - w; }
        if (p < w * (h - 1) && mask[p + w] && labels[p + w] < 0) { labels[p + w] = count; stack[top++] = p + w; }
      }
      count++;
    }
    return { labels: labels, count: count };
  }
  function apply(image, model, opts, previous) {
    opts = opts || {};
    if (!model) return null;
    var d = image.data, w = image.width, h = image.height, total = w * h, k = keyInfo(model.key), th = thresholds(model, opts), inner = th[0], outer = th[1];
    var raw = new Float32Array(total), near = new Float32Array(total), i, x, y;
    for (i = 0; i < total; i++) raw[i] = distanceTo(d[i * 4], d[i * 4 + 1], d[i * 4 + 2], k);
    // 3x3 average with clamped edges, as two 3-tap passes (same sum as the 9-tap window)
    var rows = new Float32Array(total);
    for (y = 0; y < h; y++) { var o = y * w; for (x = 0; x < w; x++) rows[o + x] = raw[o + (x > 0 ? x - 1 : 0)] + raw[o + x] + raw[o + (x < w - 1 ? x + 1 : x)]; }
    for (y = 0; y < h; y++) { var up = (y > 0 ? y - 1 : 0) * w, mid = y * w, down = (y < h - 1 ? y + 1 : y) * w;
      for (x = 0; x < w; x++) { i = mid + x; near[i] = d[i * 4 + 3] < 8 ? 0 : (rows[up + x] + rows[i] + rows[down + x]) / 9; } }
    var limit = Math.max(outer, inner + 1e-3), candidate = new Uint8Array(total), core = new Uint8Array(total);
    // smaller of raw and averaged distance: averaging ignores backdrop noise, raw keeps 1-3 px hair gaps
    var level = new Float32Array(total);
    for (i = 0; i < total; i++) { level[i] = Math.min(d[i * 4 + 3] < 8 ? 0 : raw[i], near[i]); candidate[i] = level[i] < limit ? 1 : 0; core[i] = level[i] < inner ? 1 : 0; }
    var comp = components(candidate, w, h), chosen = new Uint8Array(comp.count), pocket = new Uint32Array(comp.count), area = new Uint32Array(comp.count), exact = new Uint32Array(comp.count);
    var exactLimit = Math.max(model.spread * 2.5 + 4, 10);
    for (i = 0; i < total; i++) { var lab = comp.labels[i]; if (lab < 0) continue; area[lab]++; if (core[i]) pocket[lab]++; if (raw[i] < exactLimit) exact[lab]++; }
    function seed(p) { if (core[p] && comp.labels[p] >= 0) chosen[comp.labels[p]] = 1; }
    for (x = 0; x < w; x++) { seed(x); seed((h - 1) * w + x); }
    for (y = 0; y < h; y++) { seed(y * w); seed(y * w + w - 1); }
    if (opts.holes !== false) { var holeMin = k.saturation >= 40 ? POCKET_MIN : Math.max(48, HOLE_SHARE * total); for (var c = 0; c < comp.count; c++) if (pocket[c] >= holeMin && (k.saturation >= 40 || exact[c] >= POCKET_EXACT * area[c])) chosen[c] = 1; }
    var backdrop = new Uint8Array(total), alpha = new Float32Array(total);
    for (i = 0; i < total; i++) {
      backdrop[i] = comp.labels[i] >= 0 && chosen[comp.labels[i]] ? 1 : 0;
      if (!backdrop[i]) { alpha[i] = 1; continue; }
      if (outer > inner) { var t = Math.min(1, Math.max(0, (level[i] - inner) / (outer - inner))); alpha[i] = t * t * (3 - 2 * t); }
      else alpha[i] = level[i] >= inner ? 1 : 0;
    }
    rimAlpha(alpha, raw, backdrop, w, h);
    // Specks: tiny islands of near-backdrop colour standing alone in the removed area.
    var keep = new Uint8Array(total); for (i = 0; i < total; i++) keep[i] = backdrop[i] ? 0 : 1;
    var islands = components(keep, w, h), sizes = new Uint32Array(islands.count), close = new Float64Array(islands.count);
    for (i = 0; i < total; i++) { var l = islands.labels[i]; if (l >= 0) { sizes[l]++; close[l] += near[i]; } }
    var speckMin = Math.max(8, SPECK_SHARE * total);
    for (i = 0; i < total; i++) { l = islands.labels[i]; if (l >= 0 && sizes[l] < speckMin && close[l] / sizes[l] < outer * 2) alpha[i] = 0; }

    if (previous && previous.alpha.length === total) {
      for (i = 0; i < total; i++) {
        var p4 = i * 4, change = Math.max(Math.abs(d[p4] - previous.rgb[i * 3]), Math.abs(d[p4 + 1] - previous.rgb[i * 3 + 1]), Math.abs(d[p4 + 2] - previous.rgb[i * 3 + 2]));
        if (change < STATIC_DIFF) alpha[i] = (alpha[i] + previous.alpha[i]) * 0.5;
      }
    }
    var state = { rgb: new Uint8Array(total * 3), alpha: alpha };
    for (i = 0; i < total; i++) { state.rgb[i * 3] = d[i * 4]; state.rgb[i * 3 + 1] = d[i * 4 + 1]; state.rgb[i * 3 + 2] = d[i * 4 + 2]; }

    var out = new Float32Array(total * 3);
    for (i = 0; i < total; i++) {
      var a = alpha[i], r = d[i * 4], g = d[i * 4 + 1], b = d[i * 4 + 2];
      if (a > 0 && a < 1) {
        var div = Math.max(a, 0.05);
        r = Math.min(255, Math.max(0, (r - (1 - a) * model.key[0]) / div));
        g = Math.min(255, Math.max(0, (g - (1 - a) * model.key[1]) / div));
        b = Math.min(255, Math.max(0, (b - (1 - a) * model.key[2]) / div));
      }
      out[i * 3] = r; out[i * 3 + 1] = g; out[i * 3 + 2] = b;
    }
    despill(out, alpha, backdrop, w, h, k);
    var opaque = 0, newAlpha = new Uint8ClampedArray(total);
    for (i = 0; i < total; i++) { newAlpha[i] = Math.round(alpha[i] * d[i * 4 + 3]); if (newAlpha[i] > 16) opaque++; }
    if (opaque < Math.max(16, Math.floor(total * 0.004))) return previous || null; // keyed everything away: wrong guess
    for (i = 0; i < total; i++) { d[i * 4] = Math.round(out[i * 3]); d[i * 4 + 1] = Math.round(out[i * 3 + 1]); d[i * 4 + 2] = Math.round(out[i * 3 + 2]); d[i * 4 + 3] = newAlpha[i]; }
    return state;
  }
  /* Anti-aliased rim: a pixel touching the removed backdrop is a mix of the backdrop and its
     most different neighbour, so its opacity is how far it got towards that neighbour. */
  /* 1 where any pixel within `radius` (square window) is set: two sliding-count passes, O(n). */
  function grow(mask, w, h, radius) {
    var row = new Uint8Array(w * h), out = new Uint8Array(w * h), x, y, count;
    for (y = 0; y < h; y++) { var o = y * w; count = 0;
      for (x = 0; x < Math.min(radius, w); x++) count += mask[o + x];
      for (x = 0; x < w; x++) { if (x + radius < w) count += mask[o + x + radius]; if (x - radius - 1 >= 0) count -= mask[o + x - radius - 1]; row[o + x] = count ? 1 : 0; } }
    for (x = 0; x < w; x++) { count = 0;
      for (y = 0; y < Math.min(radius, h); y++) count += row[y * w + x];
      for (y = 0; y < h; y++) { if (y + radius < h) count += row[(y + radius) * w + x]; if (y - radius - 1 >= 0) count -= row[(y - radius - 1) * w + x]; out[y * w + x] = count ? 1 : 0; } }
    return out;
  }
  function rimAlpha(alpha, raw, backdrop, w, h) {
    var near = grow(backdrop, w, h, 1);
    for (var y = 0; y < h; y++) for (var x = 0; x < w; x++) {
      var i = y * w + x; if (backdrop[i] || !near[i]) continue;
      var touches = 0, far = raw[i];
      for (var oy = -1; oy <= 1; oy++) { var yy = y + oy; if (yy < 0 || yy >= h) continue;
        for (var ox = -1; ox <= 1; ox++) { var xx = x + ox; if (xx < 0 || xx >= w) continue; var j = yy * w + xx; if (backdrop[j]) touches = 1; if (raw[j] > far) far = raw[j]; } }
      if (!touches) continue;
      var share = Math.min(1, Math.max(0, raw[i] / Math.max(far, 1))); if (share > 0.92) share = 1;
      if (share < alpha[i]) alpha[i] = share;
    }
    // the soft band inside the removed area: same share against the most different colour within 2 px
    for (y = 0; y < h; y++) for (x = 0; x < w; x++) {
      i = y * w + x; if (!backdrop[i] || !(alpha[i] > 0)) continue;
      far = raw[i];
      for (oy = -2; oy <= 2; oy++) { yy = y + oy; if (yy < 0 || yy >= h) continue;
        for (ox = -2; ox <= 2; ox++) { xx = x + ox; if (xx < 0 || xx >= w) continue; if (raw[yy * w + xx] > far) far = raw[yy * w + xx]; } }
      share = Math.min(1, Math.max(0, raw[i] / Math.max(far, 1))); if (share > 0.92) share = 1;
      if (share < alpha[i]) alpha[i] = share;
    }
  }
  /* Pull the key's colour out of the rim (2 px next to the removed backdrop). */
  function despill(out, alpha, backdrop, w, h, k) {
    if (k.saturation < 40) return;
    var total = w * h, grown = grow(backdrop, w, h, 2), i;
    var ux = k.cb / k.saturation, uy = k.cr / k.saturation;
    for (i = 0; i < total; i++) {
      if (!grown[i] || !(alpha[i] > 0)) continue;
      var c = ycc(out[i * 3], out[i * 3 + 1], out[i * 3 + 2]), toward = Math.max(0, c[1] * ux + c[2] * uy) * 0.6, cb = c[1] - ux * toward, cr = c[2] - uy * toward;
      out[i * 3] = c[0] + 1.402 * cr; out[i * 3 + 1] = c[0] - 0.344136 * cb - 0.714136 * cr; out[i * 3 + 2] = c[0] + 1.772 * cb;
    }
  }
  /* Share of the frame border that is the model's backdrop colour. */
  function borderMatch(image, model) {
    var ring = []; ringSamples(image, ring); var n = ring.length / 3; if (!n) return 1;
    var k = keyInfo(model.key), hit = 0;
    for (var s = 0; s < n; s++) if (distanceTo(ring[s * 3], ring[s * 3 + 1], ring[s * 3 + 2], k) < CLUSTER) hit++;
    return hit / n;
  }
  /* The model to key this frame of a clip with: the clip's, unless the frame is an intro or
     flash on another solid colour (then its own; the caller drops the temporal state). */
  function frameModel(image, model, mode) {
    if (!model || borderMatch(image, model) >= FOREIGN) return model;
    var own = estimate([image]);
    return own && own.coverage >= OWN_BACKDROP && own.spread <= OWN_SPREAD ? (resolve(mode, own) || model) : model;
  }
  /* Already a cut-out (transparent border)? Then auto mode leaves it alone. */
  function isCutout(image) {
    var flat = []; var d = image.data, w = image.width, h = image.height, band = Math.min(RING, Math.max(1, h >> 1), Math.max(1, w >> 1)), n = 0, clear = 0;
    for (var y = 0; y < h; y++) for (var x = 0; x < w; x++) if (y < band || y >= h - band || x < band || x >= w - band) { n++; if (d[(y * w + x) * 4 + 3] < 250) clear++; }
    return n > 0 && clear / n > 0.5;
  }
  root.SMChroma = { estimate: estimate, resolve: resolve, apply: apply, frameModel: frameModel, borderMatch: borderMatch, isCutout: isCutout, distance: function (r, g, b, key) { return distanceTo(r, g, b, keyInfo(key)); }, PRESETS: PRESETS };
})(typeof window !== 'undefined' ? window : globalThis);
