/* Landing hero: shooting stars and a few twinkling stars over the painted background.
   One canvas over the hero shade; the VRM silhouette is cut out, so stars fly behind her, paused off screen, in hidden tabs and for reduced motion.
   2026-10-10 (user report: particles stutter): the canvas covers only the left SPAN of the hero (stars never go further)
   and fades out inside the canvas; it used to cover the whole hero under a CSS mask-image, which the browser had to
   re-apply to a full-screen layer on every frame. */
(function () {
  'use strict';
  var canvas = document.getElementById('homeStars');
  if (!canvas || !canvas.getContext) return;
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var ctx = canvas.getContext('2d');
  var ANGLE = 0.42;                       // ~24 deg down to the right, like IMAGE/stars.png
  var DIR_X = Math.cos(ANGLE), DIR_Y = Math.sin(ANGLE);
  var COLORS = ['255,255,255', '140,230,255', '190,160,255', '120,200,255'];
  var W = 0, H = 0, FW = 0, unit = 1, dpr = 1;
  var SPAN = 0.56;                        // the canvas width as a share of the hero (home.css .home-stars)
  // Where the stars fade out, as shares of the hero width: behind the character once her silhouette is known,
  // before her otherwise (the old CSS masks: 47-56 % and 30-41 %).
  var FADE = { occluded: [0.47, 0.56], plain: [0.30, 0.41] };
  var meteors = [], sparks = [], nextSpawn = 0, last = 0, raf = 0, visible = true;
  // Character silhouette, copied from the VRM canvas right after each render (WebGL buffers
  // are only readable in the same task), so stars pass BEHIND her.
  var occluder = document.createElement('canvas'), occCtx = occluder.getContext('2d');
  var occ = null, maskTick = 0;
  window.__homeStarsMask = function (source) {
    if (!raf || (maskTick++ & 1) || !source.width) return;   // every other VRM frame is enough
    var w = Math.max(1, source.width >> 1), h = Math.max(1, source.height >> 1);
    if (occluder.width !== w || occluder.height !== h) { occluder.width = w; occluder.height = h; }
    occCtx.clearRect(0, 0, w, h);
    occCtx.drawImage(source, 0, 0, w, h);
    var a = source.getBoundingClientRect(), b = canvas.getBoundingClientRect();
    occ = { x: a.left - b.left, y: a.top - b.top, w: a.width, h: a.height, at: performance.now() };
    if (!canvas.classList.contains('is-occluded')) canvas.classList.add('is-occluded');
  };

  function rand(a, b) { return a + Math.random() * (b - a); }

  function resize() {
    var box = canvas.getBoundingClientRect();
    dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    W = Math.max(1, box.width); H = Math.max(1, box.height);
    FW = W / SPAN;                                       // the whole hero width
    unit = Math.max(0.6, Math.min(FW / 1672, H / 941)); // one reference pixel of the 1672x941 art
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    sparks = [];
    var count = Math.round(Math.min(70, FW * H / 26000));
    for (var i = 0; i < count; i++) {
      sparks.push({ x: rand(0, FW * 0.55), y: rand(0, H * 0.62), r: rand(0.7, 1.7) * Math.max(unit, 0.7),
        phase: rand(0, Math.PI * 2), speed: rand(0.6, 1.8), color: COLORS[i % COLORS.length] });
    }
  }

  function spawn(now) {
    // Mostly enter from the upper-left area and cross the copy column / sky.
    var fromTop = Math.random() < 0.45;
    var x = fromTop ? rand(-0.05 * FW, 0.42 * FW) : rand(-0.25 * FW, -0.02 * FW);
    var y = fromTop ? rand(-0.08 * H, 0.02 * H) : rand(0, 0.7 * H);
    var big = Math.random() < 0.22;
    meteors.push({
      x: x, y: y, born: now,
      speed: rand(480, 760) * unit * (big ? 1.25 : 1),
      tail: rand(230, 380) * unit * (big ? 1.5 : 1),
      width: rand(1.8, 2.6) * Math.max(unit, 0.75) * (big ? 1.4 : 1),
      life: rand(0.9, 1.5) * (big ? 1.2 : 1),
      color: COLORS[Math.floor(Math.random() * COLORS.length)]
    });
    nextSpawn = now + rand(big ? 0.7 : 0.35, 1.4);
    if (Math.random() < 0.25) nextSpawn = now + rand(0.12, 0.3); // occasional pair
  }

  function drawMeteor(m, now) {
    var age = now - m.born, t = age / m.life;
    if (t >= 1) return false;
    var hx = m.x + DIR_X * m.speed * age, hy = m.y + DIR_Y * m.speed * age;
    var fade = t < 0.12 ? t / 0.12 : 1 - Math.pow((t - 0.12) / 0.88, 2);
    var len = m.tail * Math.min(1, age / 0.25);
    var tx = hx - DIR_X * len, ty = hy - DIR_Y * len;
    var grad = ctx.createLinearGradient(hx, hy, tx, ty);
    grad.addColorStop(0, 'rgba(' + m.color + ',' + (0.95 * fade) + ')');
    grad.addColorStop(0.25, 'rgba(' + m.color + ',' + (0.45 * fade) + ')');
    grad.addColorStop(1, 'rgba(' + m.color + ',0)');
    var halo = ctx.createLinearGradient(hx, hy, tx, ty);
    halo.addColorStop(0, 'rgba(' + m.color + ',' + (0.28 * fade) + ')');
    halo.addColorStop(1, 'rgba(' + m.color + ',0)');
    ctx.lineCap = 'round';
    ctx.strokeStyle = halo; ctx.lineWidth = m.width * 4;
    ctx.beginPath(); ctx.moveTo(hx, hy); ctx.lineTo(hx - DIR_X * len * 0.6, hy - DIR_Y * len * 0.6); ctx.stroke();
    ctx.strokeStyle = grad; ctx.lineWidth = m.width;
    ctx.beginPath(); ctx.moveTo(hx, hy); ctx.lineTo(tx, ty); ctx.stroke();
    var glow = ctx.createRadialGradient(hx, hy, 0, hx, hy, m.width * 7);
    glow.addColorStop(0, 'rgba(255,255,255,' + fade + ')');
    glow.addColorStop(0.3, 'rgba(' + m.color + ',' + (0.5 * fade) + ')');
    glow.addColorStop(1, 'rgba(' + m.color + ',0)');
    ctx.fillStyle = glow;
    ctx.beginPath(); ctx.arc(hx, hy, m.width * 7, 0, Math.PI * 2); ctx.fill();
    return hx - len < W + 50 && hy - len * DIR_Y < H + 50;
  }

  function frame(ms) {
    raf = 0;
    if (!visible || document.hidden) return;
    var now = ms / 1000;
    if (!last) { last = now; nextSpawn = now + 0.6; }
    last = now;
    ctx.clearRect(0, 0, W, H);
    ctx.globalCompositeOperation = 'lighter';
    for (var i = 0; i < sparks.length; i++) {
      var s = sparks[i], a = 0.18 + 0.5 * (0.5 + 0.5 * Math.sin(now * s.speed + s.phase));
      ctx.fillStyle = 'rgba(' + s.color + ',' + a.toFixed(3) + ')';
      ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2); ctx.fill();
    }
    if (now >= nextSpawn && meteors.length < 8) spawn(now);
    meteors = meteors.filter(function (m) { return drawMeteor(m, now); });
    var occluded = occ && ms - occ.at < 1000;
    ctx.globalCompositeOperation = 'destination-out';
    if (occluded) ctx.drawImage(occluder, occ.x, occ.y, occ.w, occ.h);
    fadeOut(canvas.classList.contains('is-occluded') ? FADE.occluded : FADE.plain);
    ctx.globalCompositeOperation = 'source-over';
    raf = requestAnimationFrame(frame);
  }

  // Erase towards the right edge of the star area (destination-out is already set).
  var fadeCache = { key: '', grad: null };
  function fadeOut(band) {
    var x0 = band[0] * FW, x1 = Math.min(W, band[1] * FW), key = x0 + ':' + x1;
    if (fadeCache.key !== key) {
      var g = ctx.createLinearGradient(x0, 0, x1, 0);
      g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,1)');
      fadeCache = { key: key, grad: g };
    }
    ctx.fillStyle = fadeCache.grad;
    ctx.fillRect(x0, 0, x1 - x0, H);
    if (x1 < W) { ctx.fillStyle = '#000'; ctx.fillRect(x1, 0, W - x1, H); }
  }

  function start() { if (!raf && visible && !document.hidden) { last = 0; meteors = []; raf = requestAnimationFrame(frame); } }

  resize();
  window.addEventListener('resize', function () { resize(); });
  document.addEventListener('visibilitychange', start);
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) {
      visible = entries[0].isIntersecting;
      start();
    }).observe(canvas.parentElement || canvas);
  }
  start();
  window.__homeStars = { spawn: function () { spawn(performance.now() / 1000); }, state: function () { return { meteors: meteors.length, running: !!raf, visible: visible, unit: unit, occluder: occ && { rect: [occ.x, occ.y, occ.w, occ.h], size: [occluder.width, occluder.height], center: Array.prototype.slice.call(occCtx.getImageData(occluder.width >> 1, occluder.height >> 1, 1, 1).data) } }; } };
})();
