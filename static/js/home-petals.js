/* Landing hero: sakura petals drifting down over the painted monitor (owner's sketch, 2026-10-07).
   The canvas sits inside .home-art UNDER the VRM box, so the character always covers the petals and no
   silhouette mask is needed. Paused off screen and in hidden tabs, off for reduced motion.
   Each colour is drawn ONCE into a sprite with its pink glow (2026-10-10: shadowBlur on every petal every frame made
   the petals stutter in every browser, user report); frames only drawImage the sprite with the petal's transform. */
(function () {
  'use strict';
  var canvas = document.getElementById('homePetals');
  if (!canvas || !canvas.getContext) return;
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  var ctx = canvas.getContext('2d');
  var COLORS = ['255,198,226', '255,172,214', '246,188,255', '255,224,240'];
  // Where petals appear, in fractions of the canvas: under the blossom at the top of the painted showcase.
  var SPAWN = { x0: 0.16, x1: 0.82, y0: 0.03, y1: 0.24 };
  var W = 0, H = 0, unit = 1, dpr = 1, limit = 18;
  var petals = [], raf = 0, last = 0, nextSpawn = 0, visible = true;

  function rand(a, b) { return a + Math.random() * (b - a); }

  // Sprite geometry: the petal path at s = REF with the glow (blur = 1.33 s, as the old 10 * unit at an average size).
  var REF = 32, BLUR = REF * 1.33, HALF = Math.ceil(REF + BLUR * 1.25), sprites = {};
  function petalPath(c, s) {
    c.beginPath();                                             // a petal with the small notch at its tip
    c.moveTo(0, -s * 0.72);
    c.lineTo(s * 0.17, -s);
    c.bezierCurveTo(s * 0.98, -s * 0.72, s * 0.82, s * 0.52, 0, s);
    c.bezierCurveTo(-s * 0.82, s * 0.52, -s * 0.98, -s * 0.72, -s * 0.17, -s);
    c.closePath();
  }
  function sprite(color) {
    if (sprites[color]) return sprites[color];
    var cv = document.createElement('canvas');
    cv.width = cv.height = HALF * 2;
    var c = cv.getContext('2d');
    c.translate(HALF, HALF);
    c.shadowColor = 'rgba(255,140,205,0.75)';
    c.shadowBlur = BLUR;
    c.fillStyle = 'rgb(' + color + ')';
    petalPath(c, REF);
    c.fill();
    c.shadowBlur = 0;
    c.fillStyle = 'rgba(255,255,255,0.3)';
    c.beginPath(); c.ellipse(0, REF * 0.18, REF * 0.26, REF * 0.5, 0, 0, Math.PI * 2); c.fill();
    return (sprites[color] = cv);
  }

  function resize() {
    var box = canvas.getBoundingClientRect();
    dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    W = Math.max(1, box.width); H = Math.max(1, box.height);
    unit = Math.max(0.55, W / (0.36 * 1672));   // one reference pixel of the 1672x941 art
    limit = W < 360 ? 10 : 18;
    canvas.width = Math.round(W * dpr); canvas.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function spawn(now, seeded) {
    var fx = rand(SPAWN.x0, SPAWN.x1);
    var depth = rand(0.55, 1);                  // far petals are smaller, slower and fainter
    petals.push({
      x: fx * W,
      y: seeded ? rand(SPAWN.y0, 0.8) * H : rand(SPAWN.y0, SPAWN.y1) * H,
      born: seeded ? now - 2 : now,
      vy: rand(34, 58) * unit * depth,
      // Petals from the left half lean left, from the right half lean right, as in the sketch.
      vx: ((fx - 0.5) * 26 + rand(-7, 7)) * unit,
      sway: rand(10, 26) * unit, swaySpeed: rand(0.7, 1.5), phase: rand(0, Math.PI * 2),
      size: rand(5.6, 9.4) * unit * depth,
      rot: rand(0, Math.PI * 2), spin: rand(-1.1, 1.1),
      flip: rand(0, Math.PI * 2), flipSpeed: rand(1.2, 2.6),
      alpha: rand(0.78, 0.98) * (0.6 + 0.4 * depth),
      color: COLORS[Math.floor(Math.random() * COLORS.length)]
    });
  }

  function draw(p, now, dt) {
    var age = now - p.born;
    p.y += p.vy * dt;
    p.x += p.vx * dt;
    p.rot += p.spin * dt;
    p.flip += p.flipSpeed * dt;
    if (p.y - p.size > H) return false;
    var x = p.x + Math.sin(now * p.swaySpeed + p.phase) * p.sway;
    var fadeIn = Math.min(1, age / 0.9);
    var fadeOut = Math.min(1, Math.max(0, (H - p.y) / (H * 0.16)));
    var alpha = p.alpha * fadeIn * fadeOut;
    if (alpha <= 0.01) return true;
    var k = p.size / REF, flip = 0.32 + 0.68 * Math.abs(Math.cos(p.flip));   // tumbling: the petal turns edge-on
    var cos = Math.cos(p.rot), sin = Math.sin(p.rot);
    ctx.setTransform(dpr * cos * k, dpr * sin * k, -dpr * sin * k * flip, dpr * cos * k * flip, dpr * x, dpr * p.y);
    ctx.globalAlpha = alpha;
    ctx.drawImage(sprite(p.color), -HALF, -HALF);
    return true;
  }

  function frame(ms) {
    raf = 0;
    if (!visible || document.hidden) return;
    var now = ms / 1000;
    if (!last) {
      last = now; nextSpawn = now + 0.4;
      for (var i = 0; i < Math.round(limit * 0.45); i++) spawn(now, true);   // do not start with an empty sky
    }
    var dt = Math.min(0.05, now - last);
    last = now;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.globalAlpha = 1;
    ctx.clearRect(0, 0, W, H);
    if (now >= nextSpawn && petals.length < limit) { spawn(now, false); nextSpawn = now + rand(0.5, 1.2); }
    petals = petals.filter(function (p) { return draw(p, now, dt); });
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.globalAlpha = 1;
    raf = requestAnimationFrame(frame);
  }

  function start() { if (!raf && visible && !document.hidden) { last = 0; petals = []; raf = requestAnimationFrame(frame); } }

  resize();
  window.addEventListener('resize', resize);
  document.addEventListener('visibilitychange', start);
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) {
      visible = entries[0].isIntersecting;
      start();
    }).observe(canvas.closest('.home-hero') || canvas);
  }
  start();
  window.__homePetals = { state: function () { return { petals: petals.length, running: !!raf, visible: visible, unit: unit, size: [W, H] }; } };
})();
