/* Scroll-driven landing for computers (2026-10-07, owner: "scrolling the home page should feel like an
   animation, not an ordinary page"; reference: motionsites' Obsidian template).

   Phones keep the page exactly as it was: nothing runs below 1100 x 560 px or in portrait. Touch screens and
   "reduce motion" no longer switch it off (2026-10-09, owner saw the plain landing on a Surface and on work laptops,
   where Windows animations are often off by policy): every scene moves only while the visitor scrolls; with
   "reduce motion" the wheel steps do not glide and the follower is quicker. Roll back = remove home-scroll.css and home-scroll.js from
   index.html; the small hooks in home.js (window.__homeCut) and home-vrm.js (window.__homeLook,
   __homeEyes, __homeVrmSync, the close-up view) are inert without this file.

   The script only measures and writes numbers into CSS variables; home-scroll.css (scoped to html.hs-on)
   turns them into motion. Every number follows a smoothed copy of the scroll position (`sy`), so wheel
   steps, the scrollbar and keys all become one continuous movement. Scenes:
   1 Hero, pinned for 1.5 screens: the camera dives into the character's eyes. The painting is scaled at
     most 2.4x (bigger layers left unpainted tiles), the character box takes the rest of the zoom and
     home-vrm.js re-renders it sharp; she looks into the camera and holds still, the room darkens, then she
     dissolves into the dark.
   1b Brand moment: after a hyperspace jump, ~1300 stars (and a few meteors) fly in on bent paths and gather into
     the outline of "Showcase Maker"; the letters light up out of them from the centre outwards, a few stars keep
     twinkling on them, a highlight runs over the word, the tagline and the facts strip appear.
   2 "One artwork. Three showcases" (#features): on the way to it the stage grows out of the dark from the
     middle of the screen to its place while the copy slides in; pinned, scrolling walks Workshop ->
     Featured -> Split and the picture physically comes apart into the Steam parts (five pieces, one, 506+100).
   3 Steps: they light up one by one along a filling line while the list crosses the screen.
   4 Tools: pinned; the title, a counter and a progress bar stay on the left, the cards glide by in one
     continuous ride (each card's look is a function of its distance to the focus), the current name is
     written huge in outline behind; the ride ends on an "All tools" card.
   5 Everything below enters on its own with one-off CSS transitions (compositor only, never tied to the scroll
     frame by frame): facts rise and count up, heads rise out of a mask, steps light up along a line, the
     extension screenshots fly in, the price cards fan in, questions slide in, the final card zooms.
   Smoothness rules: per frame only transform / opacity are written, straight to the elements (no inherited
   custom properties on big sections, no animated shadows, filters or clip-paths); mouse-wheel steps glide. */
(function () {
  'use strict';
  var root = document.documentElement;
  var desk = window.matchMedia('(min-width: 1100px) and (min-height: 560px) and (orientation: landscape)');
  var still = window.matchMedia('(prefers-reduced-motion: reduce)');
  var hero = document.querySelector('.home-hero');
  if (!hero || !desk.matches) return;
  root.classList.add('hs-on');
  // Crossing the breakpoint (window resized to tablet size, motion setting changed): rebuild cleanly.
  [desk, still].forEach(function (mq) {
    var onChange = function () { location.reload(); };
    if (mq.addEventListener) mq.addEventListener('change', onChange); else if (mq.addListener) mq.addListener(onChange);
  });

  // Lite mode for weak visitor computers (everything here runs in the visitor's browser; the server only serves
  // files). On from the start for software-rendered WebGL (no usable GPU), <= 4 GB memory or <= 4 CPU threads, and
  // switched on at run time when frames keep coming late. Lite: no WebGL vortex, about half the stars / particles.
  var lite = false;
  (function () {
    var mem = navigator.deviceMemory, cpu = navigator.hardwareConcurrency;
    if ((mem && mem <= 4) || (cpu && cpu <= 4)) lite = true;
    try {
      var probe = document.createElement('canvas').getContext('webgl');
      if (!probe) { lite = true; return; }
      var info = probe.getExtension('WEBGL_debug_renderer_info');
      var name = String(probe.getParameter(info ? info.UNMASKED_RENDERER_WEBGL : probe.RENDERER) || '');
      if (/swiftshader|llvmpipe|softpipe|software|basic render/i.test(name)) lite = true;
      var lose = probe.getExtension('WEBGL_lose_context');
      if (lose) lose.loseContext();
    } catch (_) { lite = true; }
  })();
  if (lite) root.classList.add('hs-lite');            // visible marker for testing
  function amount(n) { return Math.round(n * (lite ? 0.5 : 1)); }
  var ART_W = 1672, ART_H = 941;
  // Scroll length of every pinned scene, in windows, is multiplied by this (owner, 2026-10-08: "everything is far too
  // fast at a normal scroll"). The track overlaps in home-scroll.css (hero / brand margin-bottom) assume 1.6.
  var PACE = 1.6;
  var ART_ZOOM_MAX = 2.4;
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function seg(p, a, b) { return clamp((p - a) / (b - a), 0, 1); }
  function ease(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }
  function easeOut(t) { return 1 - Math.pow(1 - t, 3); }
  function smooth(t) { return t * t * (3 - 2 * t); }
  function setVar(el, name, value) {
    var text = typeof value === 'number' ? value.toFixed(4) : value;
    if (el['__hs' + name] !== text) { el['__hs' + name] = text; el.style.setProperty(name, text); }
  }
  function wrap(el, kind) {
    var track = document.createElement('div');
    track.className = 'hs-track hs-track--' + kind;
    el.parentNode.insertBefore(track, el);
    track.appendChild(el);
    return track;
  }
  function make(tag, cls, parent) {
    var el = document.createElement(tag);
    if (cls) el.className = cls;
    if (parent) parent.appendChild(el);
    return el;
  }
  function docTop(el) {          // layout position, untouched by the transforms this file applies
    var y = 0;
    for (; el; el = el.offsetParent) y += el.offsetTop;
    return y;
  }

  // This file animates the blocks itself; home.js's one-off fade-in would fight it.
  Array.prototype.forEach.call(document.querySelectorAll('.home-blocks [data-hb-reveal]'), function (el) { el.removeAttribute('data-hb-reveal'); });
  root.classList.add('hs-own-reveal');

  // ---------------------------------------------------------------- build the tracks
  var scenes = [];
  var art = hero.querySelector('.home-art');
  var vrmBox = hero.querySelector('.home-vrm');
  var dim = make('div', 'hs-dim');
  dim.setAttribute('aria-hidden', 'true');
  if (art && vrmBox) art.insertBefore(dim, vrmBox);
  var heroScene = { kind: 'hero', track: wrap(hero, 'hero'), el: hero, pin: function () { return innerHeight * 1.5 * PACE; } };
  scenes.push(heroScene);

  // Black hole (owner, 2026-10-07: "as if the character herself is a black hole that pulls everything in"; still the
  // same dive into her eyes). Owner, 2026-10-08: "too much" -> off; EYE_LIGHT below replaced it.
  // Turning BLACK_HOLE back on needs EYE_LIGHT = false.
  var BLACK_HOLE = false;
  // Eye light (2026-10-08): the same dive, calmer. A glint lights up in each pupil, she dissolves, the two glints
  // drift together into one point of light, and the stars of "Showcase Maker" burst out of that point.
  var EYE_LIGHT = !BLACK_HOLE;
  // The VRM eye bones sit inside the head: the pupils are about this many bone distances apart on screen.
  var PUPIL_SPAN = 3;
  var PUPIL_DROP = 0.035;           // pupils below the bone line, as a share of the pupil distance
  var glints = EYE_LIGHT ? [make('i', 'hs-glint', hero), make('i', 'hs-glint', hero)] : [];
  glints.forEach(function (g) { g.setAttribute('aria-hidden', 'true'); });
  // a) The painting is redrawn by a small WebGL shader over itself: a vortex around her eyes that twists the room and
  //    pulls it inwards, with a dark core and a spinning accretion ring. It lives inside .home-art, so the CSS zoom
  //    applies to it too.
  var hole = null;
  function buildHole() {
    var bg = art && art.querySelector('.home-art__bg');
    if (!BLACK_HOLE || !bg || lite) return null;
    var cv = document.createElement('canvas');
    cv.className = 'hs-hole';
    cv.setAttribute('aria-hidden', 'true');
    var gl = cv.getContext('webgl', { alpha: false, antialias: false, premultipliedAlpha: false });
    if (!gl) return null;
    function shader(type, src) {
      var sh = gl.createShader(type); gl.shaderSource(sh, src); gl.compileShader(sh);
      return gl.getShaderParameter(sh, gl.COMPILE_STATUS) ? sh : null;
    }
    var vs = shader(gl.VERTEX_SHADER, 'attribute vec2 p;varying vec2 uv;void main(){uv=p*0.5+0.5;gl_Position=vec4(p,0.,1.);}');
    var fs = shader(gl.FRAGMENT_SHADER, [
      // highp where available: `t` keeps growing, mediump would make the spin stutter after a while
      '#ifdef GL_FRAGMENT_PRECISION_HIGH', 'precision highp float;', '#else', 'precision mediump float;', '#endif',
      'uniform sampler2D tex;uniform vec2 c;uniform float asp;uniform float s;uniform float t;varying vec2 uv;',
      'void main(){',
      '  vec2 d=uv-c; d.x*=asp; float r=length(d); float a=atan(d.y,d.x);',
      // sample further out near the centre (the room is pulled in) and twist more the closer to the core
      '  float rs=r*(1.+s*2.4*exp(-r*3.5))+s*0.015;',
      '  float tw=s*(5.5*exp(-r*3.2)+0.5)+t*0.9*s*exp(-r*1.8);',
      '  vec3 col=vec3(0.);',
      '  for(int i=0;i<4;i++){float aa=a+tw+float(i)*0.045*s; vec2 q=vec2(cos(aa),sin(aa))*rs; q.x/=asp; col+=texture2D(tex,clamp(c+q,0.001,0.999)).rgb;}',
      '  col*=0.25;',
      '  float hz=0.035+0.09*s;',
      '  col*=mix(1.,smoothstep(hz*0.5,hz*1.7,r),s);',
      '  float ring=exp(-pow((r-hz*1.9)/(0.012+0.035*s),2.));',
      '  float fl=0.55+0.45*sin(a*5.-t*3.2+r*40.);',
      '  col+=ring*s*(fl*vec3(.45,.88,1.)+(1.-fl)*vec3(.62,.52,1.))*1.25;',
      '  col+=s*0.18*exp(-r*6.)*vec3(.3,.6,1.);',
      '  gl_FragColor=vec4(col,1.);',
      '}'].join('\n'));
    if (!vs || !fs) return null;
    var prog = gl.createProgram();
    gl.attachShader(prog, vs); gl.attachShader(prog, fs); gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return null;
    gl.useProgram(prog);
    var buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    var loc = gl.getAttribLocation(prog, 'p');
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    var tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, tex);
    [gl.TEXTURE_WRAP_S, gl.TEXTURE_WRAP_T].forEach(function (k) { gl.texParameteri(gl.TEXTURE_2D, k, gl.CLAMP_TO_EDGE); });
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    var u = { c: gl.getUniformLocation(prog, 'c'), asp: gl.getUniformLocation(prog, 'asp'), s: gl.getUniformLocation(prog, 's'), t: gl.getUniformLocation(prog, 't') };
    var state = { cv: cv, ready: false, shown: false };
    var maxTex = gl.getParameter(gl.MAX_TEXTURE_SIZE) || 4096;
    function upload() {
      // The <picture> may swap to another size on resize: every load re-uploads. Too big for the GPU = no vortex.
      if (!bg.naturalWidth || bg.naturalWidth > maxTex || bg.naturalHeight > maxTex || gl.isContextLost()) { state.ready = false; return; }
      try {
        gl.bindTexture(gl.TEXTURE_2D, tex);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGB, gl.RGB, gl.UNSIGNED_BYTE, bg);
        state.ready = true;
      } catch (_) { state.ready = false; }
    }
    if (bg.complete && bg.naturalWidth) upload();
    bg.addEventListener('load', upload);
    // A lost GPU context only switches the vortex off; the plain painting stays underneath.
    cv.addEventListener('webglcontextlost', function (event) { event.preventDefault(); state.ready = false; cv.style.display = ''; state.shown = false; });
    var picture = art.querySelector('picture');
    art.insertBefore(cv, picture ? picture.nextSibling : art.firstChild);
    state.off = function () { state.ready = false; state.shown = false; cv.style.display = ''; };
    state.draw = function (cx, cy, strength, now) {
      var on = strength > 0.002 && state.ready && !gl.isContextLost();
      if (on !== state.shown) { state.shown = on; cv.style.display = on ? 'block' : ''; }
      if (!on) return;
      var w = Math.round(art.offsetWidth * Math.min(window.devicePixelRatio || 1, 1)), h = Math.round(art.offsetHeight * Math.min(window.devicePixelRatio || 1, 1));
      if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; gl.viewport(0, 0, w, h); }
      gl.uniform2f(u.c, cx, 1 - cy);
      gl.uniform1f(u.asp, art.offsetWidth / art.offsetHeight);
      gl.uniform1f(u.s, strength);
      gl.uniform1f(u.t, now / 1000);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    };
    return state;
  }
  hole = buildHole();
  // b) The hero copy is pulled into the same point one piece after another, spinning and shrinking.
  var pulled = BLACK_HOLE ? Array.prototype.slice.call(hero.querySelectorAll('.home-hero__content > *, .home-scroll')) : [];
  if (pulled.length) root.classList.add('hs-hole-on');

  // Brand moment between the hero and the facts (owner: "first a beautiful title, then the information").
  // Stars gather into the outline of "Showcase Maker" (sampleWord / drawStarWord), a light line draws under it and
  // the letters rise out of it one by one (centre first, with a small turn), a highlight runs over the letters,
  // the tagline and the facts strip appear. Built here, so phones never get it.
  var BRAND = 'Showcase Maker';
  var blocks = document.querySelector('.home-blocks');
  var brandScene = null;
  function letterRow(parent, cls) {
    var row = make('div', 'hs-brand__row ' + cls, parent);
    return BRAND.split('').map(function (ch) {
      var cell = make('span', 'hs-brand__cell', row);
      var letter = make('span', 'hs-brand__ch', cell);
      letter.textContent = ch === ' ' ? '\u00a0' : ch;
      return letter;
    });
  }
  if (blocks) {
    var brand = make('section', 'hs-brand');
    brand.setAttribute('aria-label', BRAND);
    var glow = make('div', 'hs-brand__glow', brand);
    var word = make('div', 'hs-brand__word', brand);
    word.setAttribute('aria-hidden', 'true');
    var letters = letterRow(word, 'hs-brand__letters');
    // The highlight is a second, identical row whose fill is a bright band; it only fades and slides its fill.
    var shineRow = make('div', '', word);
    var shine = letterRow(shineRow, 'hs-brand__shine');
    shineRow.className = 'hs-brand__shinewrap';
    var line = make('i', 'hs-brand__line', word);
    var tag = make('p', 'hs-brand__tag', brand);
    // The tagline is the hero's script line ("Your Profile / Your Story", owner 2026-10-07), joined by a dash and
    // re-read every frame, so it always matches the hero in the visitor's language.
    var heroScript = hero.querySelectorAll('.home-script [data-i]');
    var tagText = make('span', '', tag);
    function tagline() {
      var a = heroScript[0] ? heroScript[0].textContent : 'Your Profile';
      var b = heroScript[1] ? heroScript[1].textContent : 'Your Story';
      return a.replace(/\s*[—–-]\s*$/, '') + ' — ' + b;
    }
    tagText.textContent = tagline();
    // Copy text can be re-translated by home.js; the brand line follows the hero's script line.
    var anchor = blocks.querySelector('.hb-aurora');
    blocks.insertBefore(brand, anchor ? anchor.nextSibling : blocks.firstChild);
    // The facts (3 types, 5 MB, HEX 21, 50+) are an aside, not a screen of their own (owner): they slide in as a
    // thin strip at the bottom of the brand scene and leave with it.
    var factsBlock = blocks.querySelector('.hb-facts');
    var factItems = [];
    if (factsBlock) {
      brand.appendChild(factsBlock);
      factItems = Array.prototype.slice.call(factsBlock.querySelectorAll('.hb-facts__list > li'));
    }
    var factsPanel = factsBlock && factsBlock.querySelector('.hb-facts__list');
    brandScene = {
      kind: 'brand', track: wrap(brand, 'brand'), el: brand, glow: glow, word: word, letters: letters, shine: shine,
      shineWrap: shineRow, line: line, tag: tag, tagText: tagText, tagline: tagline, key: '', facts: factItems, factsPanel: factsPanel, counted: false,
      pin: function () { return innerHeight * 1.15 * PACE; },
      // One gradient across the whole word: every letter shows its own window of it.
      layout: function () {
        var width = word.offsetWidth;
        [letters, shine].forEach(function (row) {
          row.forEach(function (letter) {
            var x = letter.parentNode.offsetLeft;
            letter.style.backgroundSize = (row === shine ? width * 0.22 : width) + 'px 100%';
            letter.style.backgroundPosition = -x + 'px 0';
            letter.__x = x;
          });
        });
        brandScene.width = width;
        sampleWord();
      }
    };
    // Star targets: the word is drawn letter by letter on a scratch canvas at its exact on-screen place (offsets
    // inside the pinned section, which sits at the window's top-left while pinned) and its pixels are sampled.
    var GRADIENT = [[0, [233, 251, 255]], [0.34, [111, 227, 255]], [0.58, [138, 180, 255]], [0.8, [169, 157, 255]], [1, [240, 236, 255]]];
    function gradientAt(f) {
      for (var g = 1; g < GRADIENT.length; g++) {
        if (f <= GRADIENT[g][0]) {
          var a = GRADIENT[g - 1], b = GRADIENT[g], k = (f - a[0]) / (b[0] - a[0]);
          return a[1].map(function (v, i) { return Math.round(v + (b[1][i] - v) * k); }).join(',');
        }
      }
      return GRADIENT[GRADIENT.length - 1][1].join(',');
    }
    function sampleWord() {
      var fs = parseFloat(getComputedStyle(word).fontSize) || 120;
      var ox = word.offsetLeft, oy = word.offsetTop, ww = word.offsetWidth;
      var pad = Math.round(fs * 0.3);
      var cw = Math.ceil(ww + pad * 2), ch = Math.ceil(fs * 1.6);
      var scratch = document.createElement('canvas');
      scratch.width = cw; scratch.height = ch;
      var sc = scratch.getContext('2d', { willReadFrequently: true });
      sc.font = '900 ' + fs + 'px Montserrat, "Segoe UI", Arial, sans-serif';
      var m = sc.measureText('Hg');
      var asc = m.fontBoundingBoxAscent || fs * 0.97, desc = m.fontBoundingBoxDescent || fs * 0.25;
      sc.fillStyle = '#fff';
      sc.textBaseline = 'alphabetic';
      letters.forEach(function (letter) {
        var cell = letter.parentNode;
        var top = cell.offsetTop + letter.offsetTop;                 // letter box top inside the word
        var baseline = top + (fs - (asc + desc)) / 2 + asc;
        sc.fillText(letter.textContent, cell.offsetLeft + pad, baseline + pad * 0.5);
      });
      var data = sc.getImageData(0, 0, cw, ch).data;
      var step = Math.max(3, Math.round(fs / 34)), pts = [];
      for (var yy = 0; yy < ch; yy += step) {
        for (var xx = (yy / step) % 2 ? step >> 1 : 0; xx < cw; xx += step) {
          if (data[(yy * cw + xx) * 4 + 3] > 140) pts.push([ox + xx - pad, oy + yy - pad * 0.5]);
        }
      }
      for (var i = pts.length - 1; i > 0; i--) { var j = (Math.random() * (i + 1)) | 0, tmp = pts[i]; pts[i] = pts[j]; pts[j] = tmp; }
      pts = pts.slice(0, amount(1300));
      var cx = ox + ww / 2, cy = oy + fs * 0.55, far = Math.max(innerWidth, innerHeight);
      brandScene.stars = pts.map(function (pt, i) {
        var meteor = !EYE_LIGHT && i < 9;
        var sx, sy;
        if (EYE_LIGHT) {                                // burst out of the point where the eye glints met
          var ja = Math.random() * Math.PI * 2, jr = Math.random() * 6;
          sx = innerWidth / 2 + Math.cos(ja) * jr; sy = innerHeight * 0.48 + Math.sin(ja) * jr;
        } else if (meteor) {                                   // a few meteors come in from the upper left, long tails
          sx = -innerWidth * (0.15 + Math.random() * 0.4); sy = -innerHeight * (0.2 + Math.random() * 0.5);
        } else if (Math.random() < 0.55) {              // pulled in from beyond the edges
          var ang = Math.random() * Math.PI * 2, r = far * (0.65 + Math.random() * 0.6);
          sx = cx + Math.cos(ang) * r; sy = cy + Math.sin(ang) * r * 0.75;
        } else {                                        // or from the sky around
          sx = Math.random() * innerWidth; sy = Math.random() * innerHeight;
        }
        var rank = Math.abs(pt[0] - cx) / (ww / 2);
        return {
          tx: pt[0], ty: pt[1], sx: sx, sy: sy, meteor: meteor,
          d: (meteor ? 0.01 : EYE_LIGHT ? rank * 0.06 + Math.random() * 0.04 : rank * 0.1 + Math.random() * 0.05),
          bend: (Math.random() - 0.5) * (meteor ? 60 : EYE_LIGHT ? 380 : 150),
          r: meteor ? 2.6 : 0.7 + Math.random() * 1.4,
          tw: 1 + Math.random() * 3, ph: Math.random() * 6.28,
          rgb: gradientAt(clamp((pt[0] - ox) / ww, 0, 1)), keep: Math.random() < 0.18
        };
      });
    }
    var mid = (BRAND.length - 1) / 2;
    letters.forEach(function (letter, i) { letter.__rank = Math.abs(i - mid) / mid; letter.__side = i < mid ? -1 : 1; });
    scenes.push(brandScene);
  }

  var demo = document.querySelector('.home-blocks .hb-demo');
  var stage = document.getElementById('cutStage');
  var stageArt = stage && stage.querySelector('.hb-stage__art');
  var demoScene = null;
  if (demo && stage && stageArt) {
    var bar = document.createElement('div');
    bar.className = 'hs-cutbar';
    bar.setAttribute('aria-hidden', 'true');
    bar.innerHTML = '<i></i>';
    var seg_ = demo.querySelector('.hb-seg');
    if (seg_) seg_.after(bar);
    // Five pieces of the same picture; CSS places them for the current showcase type (data-cut on the stage).
    var img = stageArt.querySelector('img');
    var src = img ? (img.currentSrc || img.src) : '';
    var pieces = make('div', 'hs-pieces', stageArt);
    pieces.setAttribute('aria-hidden', 'true');
    for (var pi = 0; pi < 5; pi++) {
      var piece = make('i', 'hs-piece', pieces);
      make('b', '', piece).style.backgroundImage = 'url("' + src + '")';
    }
    if (img) img.addEventListener('load', function () {
      Array.prototype.forEach.call(pieces.querySelectorAll('b'), function (b) { b.style.backgroundImage = 'url("' + (img.currentSrc || img.src) + '")'; });
    });
    demoScene = {
      kind: 'demo', track: wrap(demo, 'demo'), el: demo, last: '',
      copy: Array.prototype.slice.call(demo.querySelectorAll('.hb-demo__copy > *')),
      pin: function () { return innerHeight * 1.8 * PACE; }
    };
    demoScene.bar = bar.firstChild;
    scenes.push(demoScene);
  }

  var tools = document.querySelector('.home-blocks .hb-tools');
  var grid = tools && tools.querySelector('.hb-tools__grid');
  var toolsScene = null;
  if (tools && grid) toolsScene = buildTools();

  // ---------------------------------------------------------------- entrances of the blocks below
  // Smoothness rule (owner, 2026-10-07: "everything below looks jerky"): nothing below the tools scene is tied
  // to the scroll frame by frame. An element gets .hs-in when it comes into view and plays a CSS transition of
  // transform / opacity only (the compositor runs those, independent of the scroll and the main thread).
  // It is reset once it is entirely below the window again, so scrolling back down replays it.
  var entering = [];
  function enter(selector, kind, step) {
    Array.prototype.forEach.call(document.querySelectorAll(selector), function (el, i) {
      el.setAttribute('data-hs-in', kind);
      el.style.setProperty('--hs-delay', Math.round((step || 0) * i) + 'ms');
      entering.push(el);
    });
  }
  enter('.home-blocks .hb-steps .hb-head, .home-blocks .hb-pricing .hb-head, .home-blocks .hb-faq .hb-head', 'head');
  enter('.home-blocks .hb-steps__list', 'steps');
  enter('.home-blocks .hb-ext', 'ext');
  enter('.home-blocks .hb-plans', 'plans');
  Array.prototype.forEach.call(document.querySelectorAll('.home-blocks .hb-plan'), function (plan, i) {
    plan.style.setProperty('--hs-k', i);
    make('i', '', make('span', 'hs-plan-shine', plan)).setAttribute('aria-hidden', 'true');
  });
  enter('.home-blocks .hb-trial', 'trial');
  enter('.home-blocks .hb-faq__list', 'faq');
  enter('.home-blocks .hb-final__card', 'final');
  // Children that play one after another get their order once.
  Array.prototype.forEach.call(document.querySelectorAll('.home-blocks .hb-steps__list > li, .home-blocks .hb-faq__list > *, .home-blocks .hb-ext__copy > *'), function (el) {
    el.style.setProperty('--hs-k', Array.prototype.indexOf.call(el.parentNode.children, el));
  });
  // Facts count up while they rise (values that are not translated text only).
  var counts = [];
  Array.prototype.forEach.call(document.querySelectorAll('.home-blocks .hb-facts__list > li > b'), function (b, i) {
    var m = /(\d+)/.exec(b.textContent);
    if (m && !b.hasAttribute('data-i')) counts.push({ node: b, text: b.textContent, value: parseInt(m[1], 10), delay: i * 110 });
  });
  function countUp() {
    var start = performance.now();
    counts.forEach(function (c) { c.node.textContent = c.text.replace(/\d+/, '0'); });
    (function tick(now) {
      var busy = false;
      counts.forEach(function (c) {
        var t = clamp((now - start - c.delay) / 1600, 0, 1);
        c.node.textContent = t >= 1 ? c.text : c.text.replace(/\d+/, String(Math.round(c.value * easeOut(t))));
        if (t < 1) busy = true;
      });
      if (busy) requestAnimationFrame(tick);
    })(start);
  }
  if ('IntersectionObserver' in window) {
    var seen = new IntersectionObserver(function (list) {
      list.forEach(function (entry) {
        var el = entry.target;
        if (entry.isIntersecting) {
          if (!el.classList.contains('hs-in')) {
            el.classList.add('hs-in');
          }
        } else if (entry.boundingClientRect.top > 0) {
          el.classList.remove('hs-in');                 // wholly below the window: ready to play again
        }
      });
    }, { rootMargin: '0px 0px -12% 0px', threshold: 0 });
    entering.forEach(function (el) { seen.observe(el); });
  } else {
    entering.forEach(function (el) { el.classList.add('hs-in'); });
  }

  // ---------------------------------------------------------------- tools: side column + rail of cards
  function buildTools() {
    tools.classList.add('hs-tools');
    var side = make('div', 'hs-tools__side');
    var head = tools.querySelector('.hb-head');
    var link = tools.querySelector('.hb-link');
    tools.insertBefore(side, tools.firstChild);
    if (head) side.appendChild(head);
    var meta = make('div', 'hs-tools__meta', side);
    var count = make('p', 'hs-count', meta);
    count.innerHTML = '<b>01</b><span></span>';
    var tbar = make('div', 'hs-tbar', meta);
    make('i', '', tbar);
    if (link) side.appendChild(link);
    var ghost = make('div', 'hs-ghost');
    ghost.setAttribute('aria-hidden', 'true');
    tools.insertBefore(ghost, tools.firstChild);
    var rail = make('div', 'hs-tools__rail');
    grid.parentNode.insertBefore(rail, grid);
    rail.appendChild(grid);
    var items = Array.prototype.slice.call(grid.children);
    items.forEach(function (li, i) {
      li.style.setProperty('--hs-n', '"' + String(i + 1).padStart(2, '0') + '"');
      var card = li.querySelector('.hb-tool'), icon = li.querySelector('.hb-tool__icon');
      if (card && icon) card.style.setProperty('--hs-icon', icon.style.getPropertyValue('--hb-icon'));
    });
    // Last stop: every tool at once.
    var all = make('li', 'hs-all', grid);
    all.innerHTML = '<a class="hb-tool hb-tool--all" href="/app"><span class="hs-all__n">' + items.length + '</span>' +
      '<b data-i="tools_all"></b><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M8 12h7m-3-3 3 3-3 3"/></svg></a>';
    all.querySelector('b').textContent = link ? link.textContent : 'Open all tools';
    // The focus look (lit border, glow, tint) is drawn once in a layer whose opacity is the only thing that changes.
    Array.prototype.forEach.call(grid.querySelectorAll('.hb-tool'), function (card) { make('span', 'hs-glow', card).setAttribute('aria-hidden', 'true'); });
    count.querySelector('span').textContent = '/ ' + String(items.length).padStart(2, '0');
    var scene = {
      kind: 'tools', track: wrap(tools, 'tools'), el: tools, grid: grid, items: items.concat(all), total: items.length,
      count: count.querySelector('b'), bar: tbar.firstChild, ghost: ghost, cur: -1, shown: -1, ghostText: '',
      pin: function (s) { return ((s.items.length - 1) * innerHeight * 0.17 + innerHeight * 0.15) * PACE; }
    };
    scenes.push(scene);
    // Keyboard users: a focused card brings its stop of the ride into view.
    grid.addEventListener('focusin', function (event) {
      var li = event.target.closest('li');
      var index = scene.items.indexOf(li);
      if (index < 0 || !scene.length) return;
      var want = 0.04 + (index / (scene.items.length - 1)) * 0.92;
      window.scrollTo({ top: scene.top + want * scene.length, behavior: 'instant' });
    });
    return scene;
  }

  // ---------------------------------------------------------------- space backdrop (owner: "the blocks after the
  // hero sit on a plain black; make it space: falling stars, animated gradients"). A fixed layer behind the
  // (now transparent) blocks: drifting nebulae (CSS, transform / opacity only) and one canvas with three depths
  // of twinkling stars that lag behind the scroll, plus shooting stars. It only runs while the blocks are on
  // screen and the tab is visible; the hero covers it before that.
  var space = make('div', 'hs-space');
  space.setAttribute('aria-hidden', 'true');
  ['a', 'b', 'c', 'd'].forEach(function (k) { make('i', 'hs-space__neb hs-space__neb--' + k, space); });
  var sky = make('canvas', 'hs-space__sky', space);
  document.body.insertBefore(space, document.body.firstChild);
  var skyCtx = sky.getContext('2d');
  var stars = [], meteors = [], skyW = 0, skyH = 0, skyDpr = 1, skyOn = false, skyRaf = 0, nextMeteor = 0, lastSky = 0;
  var STAR_COLORS = ['255,255,255', '200,240,255', '170,220,255', '210,200,255', '255,236,250'];
  var sprite = document.createElement('canvas');
  (function () {
    sprite.width = sprite.height = 32;
    var c = sprite.getContext('2d'), g = c.createRadialGradient(16, 16, 0, 16, 16, 16);
    g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(0.18, 'rgba(210,240,255,.85)');
    g.addColorStop(0.45, 'rgba(111,227,255,.18)'); g.addColorStop(1, 'rgba(111,227,255,0)');
    c.fillStyle = g; c.fillRect(0, 0, 32, 32);
  })();
  function seedSky() {
    skyDpr = Math.min(window.devicePixelRatio || 1, 1.5);
    skyW = innerWidth; skyH = innerHeight;
    sky.width = Math.round(skyW * skyDpr); sky.height = Math.round(skyH * skyDpr);
    var area = (skyW * skyH) / (1920 * 1080);
    stars = [];
    [[190, 0.5, 1.0, 0.04], [90, 0.9, 1.5, 0.1], [26, 1.4, 2.4, 0.2]].forEach(function (layer, depth) {
      for (var i = 0; i < amount(layer[0] * area); i++) {
        stars.push({
          x: Math.random() * skyW, y: Math.random() * skyH, r: layer[1] + Math.random() * (layer[2] - layer[1]),
          par: layer[3], depth: depth, a: 0.35 + Math.random() * 0.6, tw: 0.6 + Math.random() * 2.2, ph: Math.random() * 6.28,
          c: STAR_COLORS[(Math.random() * STAR_COLORS.length) | 0]
        });
      }
    });
  }
  function spawnMeteor(now) {
    var ang = (20 + Math.random() * 12) * Math.PI / 180;      // upper left -> lower right, like on the hero
    var speed = 900 + Math.random() * 700;
    meteors.push({
      x: Math.random() * skyW * 0.8 - skyW * 0.1, y: Math.random() * skyH * 0.45 - 40,
      vx: Math.cos(ang) * speed, vy: Math.sin(ang) * speed, len: 120 + Math.random() * 180,
      born: now, life: 700 + Math.random() * 700, w: 1 + Math.random() * 1.2
    });
    nextMeteor = now + 900 + Math.random() * 2600;
  }
  // Hyperspace jump between the eyes and the title (owner: "a cool effect between the eyes and Showcase Maker"):
  // a 3D field of particles rushes from the centre towards the viewer as streaks, with a soft bloom in the middle.
  // `warpTarget` comes from the scroll (render), `warp` follows it smoothly, the flight itself runs in real time.
  var warp = 0, warpTarget = 0, warpField = [];
  function warpParticle(p, far) {
    var ang = Math.random() * Math.PI * 2, rad = 0.08 + Math.pow(Math.random(), 0.7) * 1.25;
    p.x = Math.cos(ang) * rad; p.y = Math.sin(ang) * rad;
    p.z = far ? 0.6 + Math.random() * 0.4 : 0.05 + Math.random() * 0.95;
    p.hue = Math.random() < 0.7 ? '200,240,255' : (Math.random() < 0.5 ? '111,227,255' : '190,175,255');
    return p;
  }
  function drawWarp(c, dt) {
    if (!warpField.length) for (var n = 0; n < amount(420); n++) warpField.push(warpParticle({}, false));
    var cx = skyW / 2, cy = skyH * 0.48, half = Math.max(skyW, skyH) * 0.5;
    var speed = 0.25 + 2.6 * warp;
    // Soft bloom where everything comes from.
    var bloom = c.createRadialGradient(cx, cy, 0, cx, cy, Math.min(skyW, skyH) * 0.42);
    bloom.addColorStop(0, 'rgba(190,240,255,' + (0.26 * warp).toFixed(3) + ')');
    bloom.addColorStop(0.35, 'rgba(111,200,255,' + (0.1 * warp).toFixed(3) + ')');
    bloom.addColorStop(1, 'rgba(111,200,255,0)');
    c.globalAlpha = 1;
    c.fillStyle = bloom;
    c.fillRect(0, 0, skyW, skyH);
    c.lineCap = 'round';
    for (var i = 0; i < warpField.length; i++) {
      var p = warpField[i];
      var z0 = p.z;
      p.z -= dt * speed * 0.45;
      if (p.z <= 0.04) { warpParticle(p, true); continue; }
      // The streak runs from where the particle was a moment ago (longer when faster) to where it is now.
      var tail = Math.min(0.9, p.z + 0.02 + warp * 0.16);
      var k1 = 0.12 / p.z, k0 = 0.12 / Math.max(z0, tail);
      var x1 = cx + p.x * half * k1, y1 = cy + p.y * half * k1;
      if (x1 < -50 || x1 > skyW + 50 || y1 < -50 || y1 > skyH + 50) { warpParticle(p, true); continue; }
      var x0 = cx + p.x * half * k0, y0 = cy + p.y * half * k0;
      var near = 1 - p.z;
      c.globalAlpha = Math.min(1, near * 1.3) * warp;
      c.strokeStyle = 'rgb(' + p.hue + ')';
      c.lineWidth = 0.6 + near * 2.2;
      c.beginPath(); c.moveTo(x0, y0); c.lineTo(x1, y1); c.stroke();
    }
    c.globalAlpha = 1;
  }
  // The title assembling from stars: each star flies from its start to its point of the word along a bent path
  // (progress from the scroll, so scrolling back scatters them again), leaving a short tail; once the letters
  // light up most of them fade, a few stay twinkling on the letters until the scene leaves.
  var starQ = 0, holePull = 0, slowFrames = 0, eyeLight = 0;
  function goLite() {
    lite = true;
    root.classList.add('hs-lite');
    if (hole) { hole.off(); hole = null; }
    stars = stars.filter(function (_, i) { return i % 2 === 0; });
    warpField.length = Math.min(warpField.length, amount(420));
    if (brandScene && brandScene.stars) brandScene.stars = brandScene.stars.filter(function (_, i) { return i % 2 === 0; });
  }
  function drawStarWord(c, t) {
    var q = starQ, list = brandScene.stars;
    var appear = seg(q, 0, 0.03), leave = 1 - seg(q, 0.88, 1);
    c.lineCap = 'round';
    for (var i = 0; i < list.length; i++) {
      var st = list[i];
      var k = ease(seg(q, st.d, st.d + (st.meteor ? 0.12 : 0.2)));
      var fade = seg(q, 0.3 + st.d * 1.0, 0.44 + st.d * 1.0);
      var alpha = appear * leave * (1 - fade * (st.keep ? 0.55 : 0.97));
      if (alpha <= 0.01) continue;
      var tw = 0.65 + 0.35 * Math.sin(t * st.tw + st.ph);
      var dx = st.tx - st.sx, dy = st.ty - st.sy, len = Math.hypot(dx, dy) || 1;
      var nx = -dy / len, ny = dx / len, arc = Math.sin(Math.PI * k) * st.bend;
      var x = st.sx + dx * k + nx * arc, y = st.sy + dy * k + ny * arc;
      if (k > 0.001 && k < 0.999) {
        var kb = Math.max(0, k - (st.meteor ? 0.16 : 0.025)), arcb = Math.sin(Math.PI * kb) * st.bend;
        var bx = st.sx + dx * kb + nx * arcb, by = st.sy + dy * kb + ny * arcb;
        c.globalAlpha = alpha * (st.meteor ? 0.9 : 0.35);
        c.strokeStyle = 'rgb(' + st.rgb + ')';
        c.lineWidth = st.r * (st.meteor ? 1.1 : 0.6);
        c.beginPath(); c.moveTo(bx, by); c.lineTo(x, y); c.stroke();
      }
      var size = st.r * (k >= 0.999 ? 4.6 : 4) * (st.keep && fade > 0.5 ? tw : 1);
      c.globalAlpha = alpha * (k >= 0.999 ? tw : 1);
      c.drawImage(sprite, x - size / 2, y - size / 2, size, size);
    }
    c.globalAlpha = 1;
  }
  // The point of light the two eye glints became: a soft core with a long horizontal flare, breathing a little.
  function drawEyeLight(c, t) {
    var cx = skyW / 2, cy = skyH * 0.48, k = eyeLight * (0.92 + 0.08 * Math.sin(t * 3.1));
    c.save();
    c.globalCompositeOperation = 'lighter';
    var r = 70 + 50 * k;
    var halo = c.createRadialGradient(cx, cy, 0, cx, cy, r * 2.2);
    halo.addColorStop(0, 'rgba(200,245,255,' + (0.5 * k).toFixed(3) + ')');
    halo.addColorStop(0.25, 'rgba(111,210,255,' + (0.18 * k).toFixed(3) + ')');
    halo.addColorStop(1, 'rgba(111,200,255,0)');
    c.fillStyle = halo;
    c.fillRect(cx - r * 2.2, cy - r * 2.2, r * 4.4, r * 4.4);
    var fw = Math.min(skyW * 0.42, 520) * k;
    var flare = c.createLinearGradient(cx - fw, 0, cx + fw, 0);
    flare.addColorStop(0, 'rgba(111,227,255,0)');
    flare.addColorStop(0.5, 'rgba(225,248,255,' + (0.85 * k).toFixed(3) + ')');
    flare.addColorStop(1, 'rgba(160,150,255,0)');
    c.fillStyle = flare;
    c.fillRect(cx - fw, cy - 1.2, fw * 2, 2.4);
    c.globalAlpha = k;
    var core = 26 + 14 * k;
    c.drawImage(sprite, cx - core / 2, cy - core / 2, core, core);
    c.restore();
  }
  function drawSky(now) {
    skyRaf = 0;
    if (!skyOn || document.hidden) return;
    skyRaf = requestAnimationFrame(drawSky);
    var raw = lastSky ? (now - lastSky) / 1000 : 0.016;
    var dt = Math.min(0.05, raw);
    // Frames keep arriving late (under 30 fps for ~2 s of animation): switch to lite once.
    if (!lite && lastSky) {
      slowFrames = raw > 0.034 && raw < 0.5 ? slowFrames + 1 : Math.max(0, slowFrames - 0.25);
      if (slowFrames > 60) goLite();
    }
    lastSky = now;
    var c = skyCtx, t = now / 1000, scroll = scrollY;
    c.setTransform(skyDpr, 0, 0, skyDpr, 0, 0);
    c.clearRect(0, 0, skyW, skyH);
    for (var i = 0; i < stars.length; i++) {
      var st = stars[i];
      var y = ((st.y - scroll * st.par) % skyH + skyH) % skyH;
      var a = st.a * (0.55 + 0.45 * Math.sin(t * st.tw + st.ph));
      if (holePull > 0.001) {
        // Spiral towards the black hole: closer in and turning, faster near the centre.
        var hx = skyW / 2, hy = skyH * 0.48, ddx = st.x - hx, ddy = y - hy;
        var rr = Math.hypot(ddx, ddy), an = Math.atan2(ddy, ddx);
        var turn = holePull * (2.2 * Math.exp(-rr / 420) + 0.25) + t * 0.6 * holePull * Math.exp(-rr / 600);
        var r2 = rr * (1 - 0.6 * holePull * Math.exp(-rr / 900));
        var px = hx + Math.cos(an + turn) * r2, py = hy + Math.sin(an + turn) * r2;
        if (holePull > 0.15) {
          var tl = 0.12 * holePull;
          c.globalAlpha = a * 0.6;
          c.strokeStyle = 'rgb(' + st.c + ')';
          c.lineWidth = st.r * 0.9;
          c.beginPath(); c.moveTo(hx + Math.cos(an + turn - tl) * r2 * 1.02, hy + Math.sin(an + turn - tl) * r2 * 1.02); c.lineTo(px, py); c.stroke();
        }
        c.globalAlpha = a;
        if (st.depth === 2) { var sz = st.r * 7; c.drawImage(sprite, px - sz / 2, py - sz / 2, sz, sz); }
        else { c.fillStyle = 'rgb(' + st.c + ')'; c.fillRect(px, py, st.r, st.r); }
        continue;
      }
      if (st.depth === 2) {
        var size = st.r * 7;
        c.globalAlpha = a;
        c.drawImage(sprite, st.x - size / 2, y - size / 2, size, size);
      } else {
        c.globalAlpha = a;
        c.fillStyle = 'rgb(' + st.c + ')';
        c.fillRect(st.x, y, st.r, st.r);
      }
    }
    warp += (warpTarget - warp) * Math.min(1, dt * 6);
    if (warp < 0.004 && warpTarget === 0) warp = 0;
    if (warp > 0) drawWarp(c, dt);
    if (brandScene && starQ > 0 && starQ < 1 && brandScene.stars) drawStarWord(c, t);
    if (eyeLight > 0.003) drawEyeLight(c, t);
    if (now >= nextMeteor && warp < 0.2 && !(starQ > 0 && starQ < 0.5)) spawnMeteor(now);
    c.lineCap = 'round';
    for (var m = meteors.length - 1; m >= 0; m--) {
      var mt = meteors[m], age = (now - mt.born) / mt.life;
      if (age >= 1) { meteors.splice(m, 1); continue; }
      mt.x += mt.vx * dt; mt.y += mt.vy * dt;
      var fade = Math.sin(Math.PI * age);
      var nx = mt.vx / Math.hypot(mt.vx, mt.vy), ny = mt.vy / Math.hypot(mt.vx, mt.vy);
      var tx = mt.x - nx * mt.len, ty = mt.y - ny * mt.len;
      var grad = c.createLinearGradient(tx, ty, mt.x, mt.y);
      grad.addColorStop(0, 'rgba(111,227,255,0)');
      grad.addColorStop(0.7, 'rgba(150,210,255,' + (0.35 * fade).toFixed(3) + ')');
      grad.addColorStop(1, 'rgba(255,255,255,' + (0.95 * fade).toFixed(3) + ')');
      c.globalAlpha = 1;
      c.strokeStyle = grad; c.lineWidth = mt.w;
      c.beginPath(); c.moveTo(tx, ty); c.lineTo(mt.x, mt.y); c.stroke();
      c.globalAlpha = fade;
      c.drawImage(sprite, mt.x - 7, mt.y - 7, 14, 14);
    }
    c.globalAlpha = 1;
  }
  function setSky(on) {
    if (on === skyOn) return;
    skyOn = on;
    space.classList.toggle('is-on', on);
    if (on && !skyRaf) { lastSky = 0; nextMeteor = performance.now() + 600; skyRaf = requestAnimationFrame(drawSky); }
  }
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden && skyOn && !skyRaf) { lastSky = 0; skyRaf = requestAnimationFrame(drawSky); }
  });
  seedSky();

  // ---------------------------------------------------------------- geometry
  function measure() {
    if (brandScene) brandScene.layout();
    if (innerWidth !== skyW || innerHeight !== skyH) seedSky();
    scenes.forEach(function (scene) {
      if (scene.kind === 'tools') {
        var a = scene.items[0], b = scene.items[1];
        scene.step = a && b ? b.offsetLeft - a.offsetLeft : 0;
      }
      var pinned = scene.el.offsetHeight;
      scene.length = Math.round(scene.pin(scene));
      if (scene.kind === 'demo') {
        // Pin only when the whole block fits under the header; on short screens it scrolls as before.
        var fits = pinned <= innerHeight - 100;
        scene.track.classList.toggle('hs-nopin', !fits);
        scene.el.style.setProperty('--hs-h', pinned + 'px');
        if (!fits) scene.length = 0;
        scene.pinned = pinned;
      }
      scene.track.style.height = (pinned + scene.length) + 'px';
      scene.top = docTop(scene.track);
    });
    if (demoScene) {
      // Scroll position where "One artwork" pins: the approach (stage growing into place) ends there.
      var stickTop = demoScene.track.classList.contains('hs-nopin')
        ? Math.max(80, (innerHeight - demoScene.pinned) / 2)
        : parseFloat(getComputedStyle(demoScene.el).top) || 80;
      demoScene.land = demoScene.top - stickTop;
      // The block arrives with a small stage and stays pinned while it grows (first 0.6 window of the pin).
      demoScene.from = demoScene.land - innerHeight * 0.85 * PACE;
      demoScene.grown = demoScene.land + innerHeight * 0.4 * PACE;
      // How far the stage centre is from the window centre once landed (it grows out of the middle).
      demoScene.shiftX = innerWidth / 2 - (stage.offsetLeft + docLeft(demoScene.el) + stage.offsetWidth / 2);
    }
  }
  function docLeft(el) {
    var x = 0;
    for (; el; el = el.offsetParent) x += el.offsetLeft;
    return x;
  }

  // ---------------------------------------------------------------- hero: dive into the eyes
  var eye = null;                     // smoothed eye point, so breathing and head turns never shake the camera
  function renderHero(p) {
    var W = art.offsetWidth, H = art.offsetHeight;
    var live = window.__homeEyes, ex, ey, span;
    if (live && vrmBox && vrmBox.offsetWidth) {
      ex = vrmBox.offsetLeft + live.x * vrmBox.offsetWidth;
      ey = vrmBox.offsetTop + live.y * vrmBox.offsetHeight;
      span = Math.max(4, live.span * vrmBox.offsetWidth);
      var hx = (live.dx || 0) * vrmBox.offsetWidth, hy = (live.dy || 0) * vrmBox.offsetHeight;
    } else {            // no character (WebGL off): dive into the painted face
      ex = W * (806 / ART_W); ey = H * (170 / ART_H); span = W * 0.014;
    }
    if (hx === undefined) { hx = span / 2; hy = 0; }
    if (!eye || p < 0.001) eye = { x: ex, y: ey, span: span, hx: hx, hy: hy };
    else { eye.x += (ex - eye.x) * 0.06; eye.y += (ey - eye.y) * 0.06; eye.hx += (hx - eye.hx) * 0.06; eye.hy += (hy - eye.hy) * 0.06; }
    var vw = innerWidth, vh = innerHeight;
    // The VRM eye bones sit inside the head, about a third of the visible distance between the pupils
    // apart; end with the pupils ~40% of the window apart, both eyes on screen.
    var zmax = clamp(0.4 * vw / (eye.span * PUPIL_SPAN), 4, 16);
    // Eye light: the camera arrives earlier, so the glints have time to meet before the title pins (~0.73).
    var zoom = Math.exp(Math.log(zmax) * ease(seg(p, 0, EYE_LIGHT ? 0.6 : 0.8)));
    var zArt = Math.min(zoom, ART_ZOOM_MAX);
    var pull = ease(seg(p, 0, 0.55));
    // Eye point before the transform (the art is centred on the pinned hero), pulled to the screen centre.
    var x0 = hero.clientWidth / 2 - W / 2 + eye.x, y0 = hero.clientHeight / 2 - H / 2 + eye.y;
    setVar(hero, '--hs-ox', eye.x.toFixed(2) + 'px');
    setVar(hero, '--hs-oy', eye.y.toFixed(2) + 'px');
    setVar(hero, '--hs-vox', (eye.x - vrmBox.offsetLeft).toFixed(2) + 'px');
    setVar(hero, '--hs-voy', (eye.y - vrmBox.offsetTop).toFixed(2) + 'px');
    setVar(hero, '--hs-tx', ((vw / 2 - x0) * pull).toFixed(2) + 'px');
    setVar(hero, '--hs-ty', ((vh * 0.48 - y0) * pull).toFixed(2) + 'px');
    setVar(hero, '--hs-zoom', zArt);
    setVar(hero, '--hs-vzoom', zoom / zArt);
    setVar(hero, '--hs-copy', 1 - seg(p, 0.02, 0.16));
    setVar(hero, '--hs-lift', seg(p, 0, 0.2) * 90);
    setVar(hero, '--hs-hint', 1 - seg(p, 0, 0.04));
    // With the black hole the room stays longer, so the vortex can be seen before it fades into space.
    setVar(hero, '--hs-dim', BLACK_HOLE ? ease(seg(p, 0.22, 0.62)) : EYE_LIGHT ? ease(seg(p, 0.12, 0.5)) : ease(seg(p, 0.05, 0.45)));
    // She dissolves into the dark at the end of the dive.
    setVar(hero, '--hs-vrm', 1 - (EYE_LIGHT ? ease(seg(p, 0.5, 0.66)) : ease(seg(p, 0.62, 0.82))));
    hero.classList.toggle('hs-moving', p > 0);
    hero.classList.toggle('hs-dark', p > 0.84);
    // Where the eyes are on screen now.
    var eyeX = x0 + (vw / 2 - x0) * pull, eyeY = y0 + (vh * 0.48 - y0) * pull;
    if (glints.length) {
      // One glint per pupil; they light up once the eyes are big, then drift together into one point at the centre
      // (the sky canvas takes the point over, see eyeLight) while she dissolves.
      var on = ease(seg(p, 0.3, 0.42)), meet = ease(seg(p, 0.5, 0.68)), out = seg(p, 0.7, 0.75);
      // Half the pupil-to-pupil vector on screen (head tilt included); the pupils sit a little below the bones.
      var k = PUPIL_SPAN * zoom * (1 - meet);
      var vx = eye.hx * k, vy = eye.hy * k, drop = PUPIL_DROP * eye.span * PUPIL_SPAN * zoom * (1 - meet);
      var cx = eyeX + (vw / 2 - eyeX) * meet, cy = eyeY + drop + (vh * 0.48 - eyeY) * meet;
      glints.forEach(function (g, i) {
        if (on <= 0) { if (g.style.opacity !== '0') g.style.opacity = '0'; return; }
        var s = i ? 1 : -1;
        g.style.opacity = (on * (1 - out)).toFixed(3);
        g.style.transform = 'translate3d(' + (cx + s * vx).toFixed(1) + 'px,' + (cy + s * vy).toFixed(1) + 'px,0) scale(' + (0.45 + 0.55 * on + 0.5 * meet).toFixed(3) + ')';
      });
    }
    var strength = BLACK_HOLE ? ease(seg(p, 0.02, 0.6)) : 0;
    holePull = BLACK_HOLE ? ease(seg(p, 0.08, 0.62)) * (1 - ease(seg(p, 0.66, 0.8))) : 0;
    if (hole) hole.draw(eye.x / W, eye.y / H, strength, performance.now());
    if (pulled.length) {
      // Individual translate / rotate / scale properties: they add to each element's own CSS transform (the script
      // line is tilted by its stylesheet) instead of replacing it.
      if (p < 0.001 || !pulled[0].__hs) pulled.forEach(function (el) {
        el.style.translate = el.style.rotate = el.style.scale = '';
        var r = el.getBoundingClientRect();
        el.__hs = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
      });
      pulled.forEach(function (el, i) {
        var k = ease(seg(p, 0.01 + i * 0.025, 0.24 + i * 0.03));
        if (k <= 0) { if (el.style.translate) { el.style.translate = el.style.rotate = el.style.scale = el.style.opacity = ''; } return; }
        var c0 = el.__hs, side = c0.x < eyeX ? 1 : -1;
        el.style.translate = ((eyeX - c0.x) * k).toFixed(1) + 'px ' + ((eyeY - c0.y) * k).toFixed(1) + 'px';
        el.style.rotate = (side * k * k * 70).toFixed(2) + 'deg';
        el.style.scale = Math.max(0.02, 1 - k * 0.97).toFixed(4);
        el.style.opacity = (1 - seg(k, 0.55, 1)).toFixed(3);
      });
    }
    // She looks into the camera (and holds still) as it comes closer.
    window.__homeLook = { x: 0, y: 0.02, w: seg(p, 0.01, 0.2) };
    if (window.__homeVrmSync) window.__homeVrmSync();
  }

  // ---------------------------------------------------------------- brand moment
  function renderBrand(scene, y) {
    var vh = innerHeight;
    // 0 when the scene pins (the hero's last dissolve, see the track overlap in CSS), 1 when it unpins.
    var q = clamp((y - scene.top) / scene.length, 0, 1);
    var key = q.toFixed(4);
    if (key === scene.key) return;
    scene.key = key;
    var leave = ease(seg(q, 0.9, 1));
    // The stars (drawn on the space canvas, see drawStarWord) gather into the outline; then a light line draws
    // under it and the letters rise out of the line one by one, centre first, with a small turn (owner: keep the
    // gathering stars and bring the rise from below back). The word box itself never moves while they gather.
    var drawn = ease(seg(q, 0.2, 0.32));
    scene.line.style.transform = 'scaleX(' + drawn.toFixed(4) + ')';
    scene.line.style.opacity = (drawn * (1 - seg(q, 0.5, 0.62))).toFixed(3);
    scene.letters.forEach(function (letter) {
      var start = 0.28 + letter.__rank * 0.12;
      var t = seg(q, start, start + 0.16);
      var e = easeOut(t), back = 1 - e;
      letter.style.opacity = clamp(t * 2.2, 0, 1).toFixed(3);
      letter.style.transform = t >= 1 ? '' : 'translate3d(0,' + (back * 108).toFixed(2) + '%,0) rotate(' + (back * 9 * letter.__side).toFixed(2) + 'deg) scale(' + (1 - back * 0.12).toFixed(4) + ')';
    });
    var settle = ease(seg(q, 0.25, 0.5));
    scene.word.style.transform = leave > 0 ? 'translate3d(0,' + (-leave * 30).toFixed(2) + 'px,0)' : '';
    scene.word.style.opacity = (1 - leave).toFixed(3);
    scene.glow.style.opacity = (seg(q, 0.25, 0.5) * (1 - leave)).toFixed(3);
    scene.glow.style.transform = 'scale(' + (0.7 + 0.3 * settle).toFixed(4) + ')';
    // A highlight runs over the letters once they all stand.
    var sw = seg(q, 0.54, 0.72);
    scene.shineWrap.style.opacity = Math.sin(Math.PI * sw).toFixed(3);
    var band = (-0.3 + 1.6 * sw) * (scene.width || 0);
    scene.shine.forEach(function (letter) { letter.style.backgroundPosition = (band - letter.__x).toFixed(1) + 'px 0'; });
    var line2 = scene.tagline();
    if (scene.tagText.textContent !== line2) scene.tagText.textContent = line2;
    var tg = ease(seg(q, 0.52, 0.64));
    scene.tag.style.opacity = (tg * (1 - leave)).toFixed(3);
    scene.tag.style.transform = 'translate3d(0,' + ((1 - tg) * 24 - leave * 20).toFixed(2) + 'px,0)';
    scene.facts.forEach(function (li, i) {
      var t = easeOut(seg(q, 0.5 + i * 0.04, 0.66 + i * 0.04));
      li.style.opacity = (t * (1 - leave)).toFixed(3);
      li.style.transform = 'translate3d(' + ((1 - t) * 40).toFixed(2) + 'px,' + (-leave * 16).toFixed(2) + 'px,0)';
    });
    if (scene.factsPanel) {
      scene.factsPanel.style.opacity = (seg(q, 0.46, 0.54) * (1 - leave)).toFixed(3);
      scene.factsPanel.style.transform = 'translate3d(0,' + ((1 - seg(q, 0.46, 0.56)) * 24).toFixed(2) + 'px,0)';
    }
    if (q >= 0.52 && !scene.counted) { scene.counted = true; countUp(); }
    else if (q < 0.3) scene.counted = false;
  }

  // ---------------------------------------------------------------- "One artwork": approach + type walk
  function renderDemo(scene, y, p) {
    var a = scene.length ? clamp((y - scene.from) / (scene.grown - scene.from), 0, 1) : 1;
    // The type walk uses the rest of the pin.
    var intro = innerHeight * 0.4 * PACE / Math.max(1, scene.length);
    p = scene.length ? seg(p, intro, 1) : p;
    var key = a.toFixed(4) + '|' + p.toFixed(4);
    if (key !== scene.key) {
      scene.key = key;
      var ea = easeOut(a), g = ease(seg(a, 0.05, 1)), ng = 1 - g;
      var st = stage.style;
      st.opacity = clamp(ea * 3, 0, 1).toFixed(3);
      st.transform = 'translate3d(' + (scene.shiftX * ng).toFixed(2) + 'px,' + (ng * innerHeight * 0.06).toFixed(2) + 'px,0) ' +
        'perspective(1600px) rotateY(' + (p * -6).toFixed(3) + 'deg) rotateX(' + (ng * 14).toFixed(3) + 'deg) scale(' + (0.32 + 0.68 * g).toFixed(4) + ')';
      scene.copy.forEach(function (el, i) {
        var c = clamp((ea - 0.45) * 2.6 - i * 0.12, 0, 1);
        el.style.opacity = c.toFixed(3);
        el.style.transform = c >= 1 ? '' : 'translate3d(' + ((1 - c) * -70).toFixed(2) + 'px,0,0)';
      });
      scene.bar.style.transform = 'scaleX(' + p.toFixed(4) + ')';
    }
    var order = (window.__homeCut && window.__homeCut.order) || ['workshop', 'featured', 'split'];
    var kind = order[Math.min(order.length - 1, Math.floor(p * order.length * 0.999))];
    if (kind !== scene.last && window.__homeCut) {
      if (!scene.stopped) { window.__homeCut.stop(); scene.stopped = true; }
      scene.last = kind;
      window.__homeCut.show(kind);
    }
  }

  // ---------------------------------------------------------------- tools: one continuous ride
  function renderTools(scene, p) {
    var n = scene.items.length;
    var k = seg(p, 0.04, 0.96) * (n - 1);
    var i0 = Math.min(n - 2, Math.floor(k));
    var pos = i0 + smooth(clamp(k - i0, 0, 1));     // a soft slow-down at each card, never a stop
    if (Math.abs(pos - scene.shown) < 0.0005) return;
    scene.shown = pos;
    // Only transform and opacity change per frame, written straight to the elements (no inherited variables,
    // so no style recalculation of whole sections and no repaint of shadows).
    scene.grid.style.transform = 'translate3d(' + (-pos * scene.step).toFixed(2) + 'px,0,0)';
    scene.bar.style.transform = 'scaleX(' + (pos / (n - 1)).toFixed(4) + ')';
    scene.items.forEach(function (li, i) {
      var d = i - pos;
      var past = clamp(-d * 1.4, 0, 1), focus = clamp(1 - Math.abs(d), 0, 1);
      var opacity = clamp(1 - Math.max(0, d) * 0.3, 0.38, 1) * (1 - past);
      var scale = 1 - (1 - focus) * 0.07 - past * 0.05;
      li.style.opacity = opacity.toFixed(3);
      li.style.transform = 'translate3d(' + (-past * 60).toFixed(2) + 'px,0,0) scale(' + scale.toFixed(4) + ')';
      if (li.__glow === undefined) li.__glow = li.querySelector('.hs-glow');
      if (li.__glow) li.__glow.style.opacity = focus.toFixed(3);
    });
    var cur = clamp(Math.round(pos), 0, n - 1);
    var name = scene.items[cur].querySelector('b');
    var text = name ? name.textContent : '';         // re-read: translations can arrive after the first paint
    if (text !== scene.ghostText) {
      scene.ghostText = text;
      scene.ghost.textContent = text;
      scene.ghost.classList.remove('is-new');
      void scene.ghost.offsetWidth;
      scene.ghost.classList.add('is-new');
    }
    if (cur !== scene.cur) {
      scene.cur = cur;
      scene.count.textContent = String(Math.min(cur + 1, scene.total)).padStart(2, '0');
    }
  }

  // ---------------------------------------------------------------- frame
  var sy = scrollY, lastFrame = 0, ticking = false;
  function render(now) {
    ticking = false;
    var y = scrollY, vh = innerHeight;
    // Follow the real scroll with a short glide; big jumps (anchor links) are not animated.
    var dt = lastFrame ? Math.min(48, now - lastFrame) : 16;
    lastFrame = now;
    if (Math.abs(y - sy) > vh * 2.5) sy = y;
    else sy += (y - sy) * (1 - Math.pow(1 - (still.matches ? 0.35 : 0.1), dt / 16.7));
    if (Math.abs(y - sy) < 0.3) sy = y;
    var moving = sy !== y;

    // Space shows once the hero is mostly gone.
    setSky(y > heroScene.top + heroScene.length * 0.02);   // the room fades into it during the dive
    var heroP = 0, brandP = 0;
    scenes.forEach(function (scene) {
      var p = scene.length ? clamp((sy - scene.top) / scene.length, 0, 1) : 0;
      if (scene.kind === 'hero') heroP = p;
      if (scene.kind === 'brand') brandP = p;
      if (scene.kind === 'hero') {
        renderHero(p);
        // While the camera is in the dive, keep following the (smoothed) eyes.
        if (p > 0.001 && p < 0.9) moving = true;
      } else if (scene.kind === 'brand') renderBrand(scene, sy);
      else if (scene.kind === 'demo') renderDemo(scene, sy, p);
      else if (scene.kind === 'tools') renderTools(scene, p);
    });
    // Hyperspace: builds up while she dissolves, peaks as the title pins, calms down while its line draws.
    warpTarget = EYE_LIGHT ? 0 : ease(seg(heroP, 0.55, 0.8)) * (1 - ease(seg(brandP, 0.03, 0.2)));
    // The point where the two glints met: lit on the sky canvas from the hand-over until the stars burst out of it.
    eyeLight = EYE_LIGHT ? seg(heroP, 0.67, 0.72) * (1 - ease(seg(brandP, 0.04, 0.16))) : 0;
    starQ = brandP;
    if (brandScene && sy > brandScene.top + brandScene.length) warpTarget = 0;
    if (moving) schedule(); else lastFrame = 0;
  }
  function schedule() { if (!ticking) { ticking = true; requestAnimationFrame(render); } }

  measure();
  render(performance.now());
  window.addEventListener('scroll', schedule, { passive: true });
  window.addEventListener('resize', function () { measure(); schedule(); });
  if ('ResizeObserver' in window) {
    var resizeTimer = 0;
    new ResizeObserver(function () { clearTimeout(resizeTimer); resizeTimer = setTimeout(function () { measure(); schedule(); }, 120); })
      .observe(document.querySelector('.home-blocks') || document.body);
  }
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { measure(); schedule(); });
  window.addEventListener('load', function () { measure(); schedule(); });
  // The character appears after the first paint; the dive needs its eye position.
  document.addEventListener('showcasemaker:hero-ready', schedule);

  // ---------------------------------------------------------------- mouse-wheel inertia
  // A notched mouse wheel jumps 100 px per step; here each step glides. Small fractional deltas are a
  // trackpad (it has its own inertia) and stay native, as do Ctrl+wheel (zoom), scrollable panels inside
  // the page and open dialogs that lock the page.
  var target = scrollY, current = scrollY, gliding = false, lastTime = 0, own = false;
  function canScroll(el, dy) {
    for (; el && el !== document.body && el !== root; el = el.parentElement) {
      var cs = getComputedStyle(el);
      if (/(auto|scroll)/.test(cs.overflowY) && el.scrollHeight > el.clientHeight + 1) {
        if (dy > 0 ? el.scrollTop + el.clientHeight < el.scrollHeight - 1 : el.scrollTop > 0) return true;
      }
    }
    return false;
  }
  function pageLocked() {
    return getComputedStyle(document.body).overflowY === 'hidden' || getComputedStyle(root).overflowY === 'hidden';
  }
  function glide(now) {
    var dt = lastTime ? Math.min(48, now - lastTime) : 16;
    lastTime = now;
    current += (target - current) * (1 - Math.pow(1 - 0.16, dt / 16.7));
    if (Math.abs(target - current) < 0.5) current = target;
    own = true;
    window.scrollTo({ top: current, behavior: 'instant' });
    if (current !== target) requestAnimationFrame(glide); else { gliding = false; lastTime = 0; }
  }
  window.addEventListener('wheel', function (event) {
    if (event.ctrlKey || event.defaultPrevented) return;
    var dy = event.deltaMode === 1 ? event.deltaY * 40 : event.deltaMode === 2 ? event.deltaY * innerHeight : event.deltaY;
    var notched = event.deltaMode !== 0 || Math.abs(event.deltaY) >= 50;
    if (still.matches || !notched || Math.abs(event.deltaX) > Math.abs(event.deltaY) || pageLocked() || canScroll(event.target, dy)) return;
    event.preventDefault();
    if (!gliding) { current = scrollY; target = scrollY; }
    var max = document.documentElement.scrollHeight - innerHeight;
    target = clamp(target + dy, 0, max);
    if (!gliding) { gliding = true; requestAnimationFrame(glide); }
  }, { passive: false });
  // Anything else that scrolls (scrollbar, keys, anchor links) wins over a glide in progress.
  window.addEventListener('scroll', function () {
    if (own) { own = false; return; }
    if (gliding && Math.abs(scrollY - current) > 2) { gliding = false; lastTime = 0; }
    target = current = scrollY;
  }, { passive: true });
})();
