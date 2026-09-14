(function (host) {
  'use strict';
  // Shared calculations are independent of DOM, media decoding and the encoder.
  const bounded = (v, lo, hi, fallback) => Number.isFinite(Number(v)) ? Math.max(lo, Math.min(hi, Number(v))) : fallback;
  const cuts = mode => mode === 'workshop' ? [.2, .4, .6, .8] : mode === 'split' ? [506 / 606] : [];
  function effectiveLayer(layer, intensity) {
    if (layer.intensityLinked === false) return Object.assign({}, layer);
    const power = bounded(intensity, 0, 100, 50) / 50;
    const result = Object.assign({}, layer);
    if (layer.type === 'effect') {
      result.effectSpeed = bounded(layer.effectSpeed, 25, 250, 100) * (.35 + power * .65);
      result.effectDensity = bounded(layer.effectDensity, 25, 200, 100) * (.3 + power * .7);
      result.lightStrength = bounded(layer.lightStrength, 0, 100, 40) * power;
    }
    result.motionPower = power;
    return result;
  }
  function lightPulse(layer, ms) {
    const seconds = ms / 1000, speed = bounded(layer.effectSpeed, 1, 500, 100) / 100;
    if (layer.effect === 'lightning') {
      const p = (seconds * speed) % 3.7;
      return p < .12 ? 1 : p < .22 ? .38 : p > .36 && p < .43 ? .68 : 0;
    }
    return .45 + .15 * Math.sin(seconds * speed * 3) + .1 * Math.sin(seconds * speed * 7);
  }
  function loopClock(seconds, duration, mode) {
    const phase = ((seconds % duration) + duration) % duration;
    return mode === 'pingpong' ? (phase <= duration / 2 ? phase : duration - phase) : phase;
  }
  function motionOffset(region, ms, period, power) {
    const angle = bounded(region.direction, -180, 180, 0) * Math.PI / 180;
    const amount = bounded(region.strength, 0, 30, 8) * power * Math.sin(ms / 1000 * Math.PI * 2 / period);
    return {x: Math.cos(angle) * amount, y: Math.sin(angle) * amount};
  }
  function brushPoint(px, py, geometry) {
    const a = -geometry.rotation, dx = px - geometry.x, dy = py - geometry.y;
    return {x: (dx * Math.cos(a) - dy * Math.sin(a)) / geometry.w + .5,
      y: (dx * Math.sin(a) + dy * Math.cos(a)) / geometry.h + .5};
  }
  const api = {bounded, cuts, effectiveLayer, lightPulse, loopClock, motionOffset, brushPoint};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  host.BuilderMotion = api;

  api.create = function (root, adapter) {
    const canvas = adapter.canvas, byId = id => root.querySelector('#' + id);
    const translate = key => host.BuilderMotionCopy.get(key);
    const surface = () => {const c = document.createElement('canvas'); c.width = canvas.width; c.height = canvas.height; return c;};
    const fxCanvas = surface(), lightCanvas = surface(), joinCanvas = surface();
    const regionCache = new Map();
    let paintMode = '', painting = null, paintedLayer = '', protection = null;
    let previewStart = performance.now();
    let recording = false;

    // Compact controls inherit the existing switches, rail and action geometry.
    const panel = document.createElement('details'); panel.className = 'builder-motion-panel';
    panel.innerHTML = '<summary data-motion-i="scene"></summary><div class="builder-motion-body">' +
      '<label><span data-motion-i="intensity"></span><input id="bmIntensity" type="range" min="0" max="100" value="50"/></label>' +
      '<label class="builder-toggle"><input id="bmSeams" type="checkbox"/><i></i><span data-motion-i="seams"></span></label>' +
      '<label><span data-motion-i="cycle"></span><select id="bmLoop"><option value="none" data-motion-i="no-loop"></option><option value="blend" data-motion-i="blend"></option><option value="pingpong" data-motion-i="pingpong"></option></select></label>' +
      '<div class="builder-two"><label><span data-motion-i="duration"></span><select id="bmDuration"><option value="4">4 s</option><option value="6">6 s</option><option value="8">8 s</option></select></label><label id="bmFadeRow"><span data-motion-i="fade"></span><select id="bmFade"><option value="0.25">0.25 s</option><option value="0.5">0.5 s</option><option value="0.75">0.75 s</option></select></label></div>' +
      '<button type="button" class="btn ghost" id="bmSeamPreview" data-motion-i="preview-seam"></button><p data-motion-i="cycle-note"></p></div>';
    root.querySelector('.builder-stage-head').after(panel);

    const effectPanel = document.createElement('div'); effectPanel.className = 'builder-motion-body';
    effectPanel.innerHTML = '<label><span data-motion-i="depth"></span><select id="bmDepth"><option value="flat" data-motion-i="as-layer"></option><option value="back" data-motion-i="behind"></option><option value="front" data-motion-i="in-front"></option><option value="mixed" data-motion-i="mixed"></option></select></label>' +
      '<label><span data-motion-i="depth-strength"></span><input id="bmDepthAmount" type="range" min="0" max="100" value="60"/></label>' +
      '<div class="builder-motion-buttons"><button type="button" class="btn ghost" id="bmProtect" data-motion-i="protect"></button><button type="button" class="btn ghost" id="bmClearProtect" data-motion-i="clear"></button></div>' +
      '<label class="builder-toggle"><input id="bmLight" type="checkbox"/><i></i><span data-motion-i="light"></span></label>' +
      '<div id="bmLightSettings"><div class="builder-two"><label><span data-motion-i="light-color"></span><input id="bmLightColor" type="color" value="#83dfff"/></label><label><span data-motion-i="radius"></span><input id="bmLightRadius" type="range" min="10" max="150" value="80"/></label></div><label><span data-motion-i="light-strength"></span><input id="bmLightStrength" type="range" min="0" max="100" value="40"/></label></div>' +
      '<p data-motion-i="light-note"></p>';
    byId('builderEffectControls').append(effectPanel);

    const localPanel = document.createElement('details'); localPanel.id = 'bmLocalPanel'; localPanel.className = 'builder-motion-panel';
    localPanel.innerHTML = '<summary data-motion-i="local-motion"></summary><div class="builder-motion-body"><p data-motion-i="paint-help"></p>' +
      '<div class="builder-motion-buttons"><button type="button" class="btn ghost" data-paint="paint" data-motion-i="paint"></button><button type="button" class="btn ghost" data-paint="pin" data-motion-i="pin"></button><button type="button" class="btn ghost" data-paint="erase" data-motion-i="erase"></button><button type="button" class="btn ghost" data-paint="" data-motion-i="finish"></button></div>' +
      '<label><span data-motion-i="brush"></span><input id="bmBrush" type="range" min="1" max="20" value="5"/></label>' +
      '<div class="builder-two"><label><span data-motion-i="direction"></span><input id="bmDirection" type="range" min="-180" max="180" value="0"/></label><label><span data-motion-i="amplitude"></span><input id="bmAmplitude" type="range" min="0" max="30" value="8"/></label></div>' +
      '<button type="button" class="btn ghost" id="bmClearMotion" data-motion-i="clear-motion"></button></div>';
    byId('builderMediaControls').append(localPanel);
    const linked = document.createElement('label'); linked.className = 'builder-toggle';
    linked.innerHTML = '<input id="bmLinked" type="checkbox" checked/><i></i><span data-motion-i="linked"></span>';
    byId('builderInspector').append(linked);
    const hint = document.createElement('p'); hint.className = 'builder-motion-hint'; hint.hidden = true; hint.setAttribute('aria-live', 'polite');
    root.querySelector('.builder-canvas-wrap').after(hint);

    const current = () => adapter.layer();
    function stopPainting() {paintMode = ''; painting = null; protection = null; hint.hidden = true; canvas.classList.remove('is-painting'); root.querySelectorAll('[data-paint]').forEach(b => b.classList.remove('active'));}
    function edit(fn) {const layer = current(); if (!layer || layer.locked || recording) return; fn(layer); regionCache.clear(); adapter.commit();}
    function sceneSettings() {
      const p = adapter.project(); p.motion = p.motion || {};
      return p.motion;
    }
    function slider(id, key, fallback) {byId(id).addEventListener('input', e => edit(l => {l[key] = Number(e.target.value) || fallback;}));}
    slider('bmDepthAmount', 'depthAmount', 0); slider('bmLightRadius', 'lightRadius', 10); slider('bmLightStrength', 'lightStrength', 0);
    ['bmDepth', 'bmLightColor'].forEach(id => byId(id).addEventListener('change', e => edit(l => {l[id === 'bmDepth' ? 'depth' : 'lightColor'] = e.target.value;})));
    byId('bmLight').addEventListener('change', e => {edit(l => {l.sceneLight = e.target.checked;}); sync();});
    byId('bmLinked').addEventListener('change', e => edit(l => {l.intensityLinked = e.target.checked;}));
    ['bmDirection', 'bmAmplitude'].forEach(id => byId(id).addEventListener('input', e => edit(l => {l.localMotion = l.localMotion || {strokes: [], pins: []}; l.localMotion[id === 'bmDirection' ? 'direction' : 'strength'] = Number(e.target.value);}))); 
    byId('bmIntensity').addEventListener('input', e => {sceneSettings().intensity = Number(e.target.value); adapter.commit();});
    ['bmLoop', 'bmDuration', 'bmFade', 'bmSeams'].forEach(id => byId(id).addEventListener('change', e => {
      const key = {bmLoop: 'loop', bmDuration: 'duration', bmFade: 'fade', bmSeams: 'seams'}[id];
      sceneSettings()[key] = id === 'bmSeams' ? e.target.checked : id === 'bmLoop' ? e.target.value : Number(e.target.value);
      previewStart = performance.now(); adapter.commit(); sync(); adapter.guides();
    }));
    byId('bmSeamPreview').onclick = () => adapter.previewLoop();
    byId('bmProtect').onclick = () => {stopPainting(); paintMode = 'protect'; paintedLayer = current()?.id; hint.hidden = false; hint.textContent = translate('protect-help'); canvas.classList.add('is-painting');};
    byId('bmClearProtect').onclick = () => edit(l => {delete l.protectedArea;});
    byId('bmClearMotion').onclick = () => {edit(l => {delete l.localMotion;}); stopPainting();};
    localPanel.querySelectorAll('[data-paint]').forEach(button => {button.onclick = () => {
      stopPainting(); paintMode = button.dataset.paint; paintedLayer = current()?.id;
      if (paintMode) {button.classList.add('active'); hint.hidden = false; hint.textContent = translate('paint-help'); canvas.classList.add('is-painting');}
    };});
    const projectPoint = e => {const r = canvas.getBoundingClientRect(); return {x: (e.clientX - r.left) / r.width, y: (e.clientY - r.top) / r.height};};
    function addPoint(e) {
      const l = current(), point = projectPoint(e); if (!l || l.locked || l.id !== paintedLayer) {stopPainting(); return;}
      if (paintMode === 'protect') {protection.end = point; return;}
      const geometry = adapter.geometry(l), p = brushPoint(point.x * canvas.width, point.y * canvas.height, geometry);
      if (p.x < 0 || p.x > 1 || p.y < 0 || p.y > 1) return;
      const region = l.localMotion || (l.localMotion = {strokes: [], pins: [], direction: 0, strength: 8});
      region.strokes = region.strokes || []; region.pins = region.pins || [];
      if (paintMode === 'pin') {if (region.pins.length < 32) region.pins.push({x: p.x, y: p.y, radius: Number(byId('bmBrush').value) / 100});}
      else if (painting && painting.points.length < 400) painting.points.push([p.x, p.y]);
      regionCache.delete(l.id);
    }
    canvas.addEventListener('pointerdown', e => {
      if (!paintMode || recording) return;
      e.preventDefault(); e.stopImmediatePropagation(); const l = current(); if (!l || l.locked) return;
      const point = projectPoint(e);
      if (paintMode === 'protect') protection = {start: point, end: point};
      else if (paintMode !== 'pin') {
        const region = l.localMotion || (l.localMotion = {strokes: [], pins: [], direction: 0, strength: 8});
        if ((region.strokes || []).length >= 80) return;
        painting = {radius: Number(byId('bmBrush').value) / 100, erase: paintMode === 'erase', points: []};
        (region.strokes || (region.strokes = [])).push(painting);
      }
      canvas.setPointerCapture(e.pointerId); addPoint(e);
    }, true);
    canvas.addEventListener('pointermove', e => {if (!paintMode) return; e.stopImmediatePropagation(); if (e.buttons && (painting || protection || paintMode === 'pin')) addPoint(e);}, true);
    function finishStroke(e) {
      if (!paintMode) return; e.stopImmediatePropagation();
      if (protection) {
        const a = protection.start, b = protection.end;
        edit(l => {l.protectedArea = {x: Math.min(a.x, b.x), y: Math.min(a.y, b.y), w: Math.abs(b.x - a.x), h: Math.abs(b.y - a.y)};});
        stopPainting();
      }
      painting = null; adapter.commit();
    }
    canvas.addEventListener('pointerup', finishStroke, true); canvas.addEventListener('pointercancel', finishStroke, true);
    canvas.addEventListener('keydown', e => {if (e.key === 'Escape') stopPainting();});

    function sync() {
      const p = adapter.project(), s = p.motion || {}, l = current();
      byId('bmIntensity').value = s.intensity == null ? 50 : s.intensity;
      byId('bmLoop').value = s.loop || 'none'; byId('bmDuration').value = s.duration || 8;
      byId('bmFade').value = s.fade || .5; byId('bmSeams').checked = !!s.seams;
      byId('bmFadeRow').hidden = s.loop !== 'blend'; byId('bmSeamPreview').disabled = !s.loop || s.loop === 'none';
      if (paintMode && (!l || l.id !== paintedLayer || l.locked)) stopPainting();
      if (l) {
        byId('bmDepth').value = l.depth || 'flat'; byId('bmDepthAmount').value = l.depthAmount == null ? 60 : l.depthAmount;
        byId('bmLight').checked = !!l.sceneLight; byId('bmLightSettings').hidden = !l.sceneLight;
        byId('bmLightColor').value = l.lightColor || l.color || '#83dfff'; byId('bmLightRadius').value = l.lightRadius || 80;
        byId('bmLightStrength').value = l.lightStrength == null ? 40 : l.lightStrength;
        byId('bmLinked').checked = l.intensityLinked !== false;
        const isStatic = !/^(video\/|image\/gif)/.test(l.mediaType || '') && !/\.(?:gif|mp4|webm|mov)(?:\?|$)/i.test(l.src || '');
        localPanel.hidden = !isStatic;
        byId('bmDirection').value = l.localMotion?.direction || 0; byId('bmAmplitude').value = l.localMotion?.strength == null ? 8 : l.localMotion.strength;
        [effectPanel, localPanel, linked].forEach(n => n.querySelectorAll('input,select,button').forEach(c => {c.disabled = !!l.locked || recording;}));
      }
      root.querySelectorAll('[data-motion-i]').forEach(n => {n.textContent = translate(n.dataset.motionI);});
      root.querySelectorAll('.builder-motion-panel input[type="range"],.builder-motion-body input[type="range"]').forEach(n => n.style.setProperty('--range-progress', ((n.value - n.min) / (n.max - n.min) * 100) + '%'));
    }
    host.addEventListener('sm:langchange', sync);

    function sized(c) {if (c.width !== canvas.width || c.height !== canvas.height) {c.width = canvas.width; c.height = canvas.height;} return c.getContext('2d');}
    function drawLight(l, ms, output, drawLayer) {
      if (!l.sceneLight) return;
      const amount = lightPulse(l, ms) * bounded(l.lightStrength, 0, 200, 40) / 100 * bounded(l.opacity, 0, 1, 1);
      if (amount <= 0) return;
      const lc = sized(lightCanvas); lc.clearRect(0, 0, canvas.width, canvas.height);
      adapter.project().layers.filter(c => c.visible !== false && c.type === 'character').forEach(c => drawLayer(c, ms, lc));
      lc.globalCompositeOperation = 'source-in'; lc.fillStyle = l.lightColor || l.color || '#83dfff'; lc.fillRect(0, 0, canvas.width, canvas.height); lc.globalCompositeOperation = 'source-over';
      const x = bounded(l.x, 0, 1, .5) * canvas.width, y = bounded(l.y, 0, 1, .5) * canvas.height;
      const radius = Math.max(1, Math.max(canvas.width, canvas.height) * bounded(l.lightRadius, 10, 150, 80) / 100);
      output.save(); output.globalCompositeOperation = 'screen'; output.globalAlpha = amount * .24;
      const gradient = output.createRadialGradient(x, y, 0, x, y, radius);
      gradient.addColorStop(0, l.lightColor || l.color || '#83dfff'); gradient.addColorStop(1, '#00000000');
      output.fillStyle = gradient; output.fillRect(0, 0, canvas.width, canvas.height);
      output.globalAlpha = amount * .28; output.shadowColor = l.lightColor || l.color || '#83dfff'; output.shadowBlur = 12;
      output.drawImage(lightCanvas, 0, 0); output.restore();
    }
    function drawEffectPass(l, ms, output, drawLayer, far) {
      const fc = sized(fxCanvas); fc.clearRect(0, 0, canvas.width, canvas.height);
      const amount = bounded(l.depthAmount, 0, 100, 60) / 100, c = Object.assign({}, l);
      if (l.depth === 'mixed') {
        c.opacity = bounded(c.opacity, 0, 1, 1) * (far ? .62 : .38);
        c.scale = (c.scale || 1) * (far ? 1 - amount * .45 : 1 + amount * .4);
        c.effectSpeed *= far ? 1 - amount * .4 : 1 + amount * .3;
        fc.filter = far ? 'blur(' + (amount * 1.5).toFixed(1) + 'px)' : 'none';
      }
      drawLayer(c, ms + (far && l.effect !== 'lightning' ? 1700 : 0), fc); fc.filter = 'none';
      if (!far && l.protectedArea) {
        const r = l.protectedArea;
        fc.save(); fc.globalCompositeOperation = 'destination-out'; fc.filter = 'blur(12px)';
        fc.fillStyle = '#000'; fc.fillRect(r.x * canvas.width, r.y * canvas.height, r.w * canvas.width, r.h * canvas.height); fc.restore();
      }
      output.drawImage(fxCanvas, 0, 0);
    }
    function renderScene(p, ms, output, drawLayer, diagnostic) {
      const layers = p.layers.filter(l => l.visible !== false && !(diagnostic && l.type === 'background'));
      const intensity = (p.motion || {}).intensity;
      const elevated = layers.some(l => l.type === 'effect' && ['front', 'mixed'].includes(l.depth));
      const layered = layers.some(l => l.type === 'effect' && ['back', 'front', 'mixed'].includes(l.depth));
      // Only depth-enabled effects leave the user's ordinary layer order.
      const back = layers.filter(l => l.type === 'effect' && ['back', 'mixed'].includes(l.depth));
      let inserted = false;
      function behind() {if (inserted) return; inserted = true; back.forEach(l => drawEffectPass(effectiveLayer(l, intensity), ms, output, drawLayer, true));}
      if (layered) {layers.filter(l => l.type === 'background').forEach(l => drawLayer(effectiveLayer(l, intensity), ms, output)); behind();}
      layers.forEach(l => {
        if (layered && l.type === 'background') return;
        if (l.type !== 'background') behind();
        const c = effectiveLayer(l, intensity);
        if (elevated && ['text', 'frame'].includes(l.type)) return;
        if (l.type === 'effect' && l.depth === 'back') return;
        if (l.type === 'effect' && ['front', 'mixed'].includes(l.depth)) return;
        if (l.type === 'effect') drawEffectPass(c, ms, output, drawLayer, false); else drawLayer(c, ms, output);
      });
      behind();
      layers.filter(l => l.type === 'effect' && ['front', 'mixed'].includes(l.depth)).forEach(l => drawEffectPass(effectiveLayer(l, intensity), ms, output, drawLayer, false));
      layers.filter(l => l.type === 'effect' && l.sceneLight).forEach(l => drawLight(effectiveLayer(l, intensity), ms, output, drawLayer));
      // Foreground weather never obscures the title or panel borders.
      if (elevated) layers.filter(l => ['text', 'frame'].includes(l.type)).forEach(l => drawLayer(effectiveLayer(l, intensity), ms, output));
    }

    function regionMask(layer, w, h) {
      const r = layer.localMotion, key = [w, h, JSON.stringify(r.strokes || []), JSON.stringify(r.pins || [])].join('|');
      const previous = regionCache.get(layer.id); if (previous && previous.key === key) return previous;
      const mask = document.createElement('canvas'); mask.width = w; mask.height = h; const mc = mask.getContext('2d');
      (r.strokes || []).forEach(stroke => {
        mc.globalCompositeOperation = stroke.erase ? 'destination-out' : 'source-over';
        const radius = Math.max(1, stroke.radius * w), points = stroke.points || [];
        points.forEach((point, i) => {
          const previous = points[i - 1] || point, dx = (point[0] - previous[0]) * w, dy = (point[1] - previous[1]) * h;
          const count = Math.max(1, Math.ceil(Math.hypot(dx, dy) / Math.max(1, radius * .4)));
          for (let step = 1; step <= count; step++) {
            const x = previous[0] * w + dx * step / count, y = previous[1] * h + dy * step / count;
            const gradient = mc.createRadialGradient(x, y, 0, x, y, radius); gradient.addColorStop(0, '#ffffff'); gradient.addColorStop(.65, '#ffffff'); gradient.addColorStop(1, '#ffffff00');
            mc.fillStyle = gradient; mc.fillRect(x - radius, y - radius, radius * 2, radius * 2);
          }
        });
      });
      mc.globalCompositeOperation = 'destination-out';
      (r.pins || []).forEach(pin => {const rad = Math.max(2, pin.radius * w), x = pin.x * w, y = pin.y * h, g = mc.createRadialGradient(x, y, 0, x, y, rad); g.addColorStop(0, '#fff'); g.addColorStop(.6, '#fff'); g.addColorStop(1, '#ffffff00'); mc.fillStyle = g; mc.fillRect(x - rad, y - rad, rad * 2, rad * 2);});
      const moving = document.createElement('canvas'), result = document.createElement('canvas'); moving.width = result.width = w; moving.height = result.height = h;
      const entry = {key, mask, moving, result}; if (regionCache.size > 24) regionCache.clear(); regionCache.set(layer.id, entry); return entry;
    }
    function animateMedia(source, layer, ms) {
      const r = layer.localMotion;
      if (paintMode || !r || !(r.strokes || []).length || /^video\//.test(layer.mediaType || '') || layer.mediaType === 'image/gif' || /\.(?:gif|mp4|webm|mov)(?:\?|$)/i.test(layer.src || '')) return source;
      const sw = source.width || source.naturalWidth, sh = source.height || source.naturalHeight; if (!sw || !sh) return source;
      const scale = Math.min(1, 1024 / Math.max(sw, sh)), w = Math.max(1, Math.round(sw * scale)), h = Math.max(1, Math.round(sh * scale));
      const entry = regionMask(layer, w, h), moving = entry.moving.getContext('2d'), out = entry.result.getContext('2d');
      const offset = motionOffset(r, paintMode ? 0 : ms, bounded(adapter.project().motion?.duration, 4, 8, 8), layer.motionPower == null ? 1 : layer.motionPower);
      moving.clearRect(0, 0, w, h);
      for (let y = 0; y < h; y += 4) {
        const height = Math.min(4, h - y), ripple = .65 + .35 * Math.sin(y / h * Math.PI * 2);
        moving.drawImage(source, 0, y / scale, sw, height / scale, offset.x * ripple * w / canvas.width, y + offset.y * ripple * h / canvas.height, w, height);
      }
      moving.globalCompositeOperation = 'destination-in'; moving.drawImage(entry.mask, 0, 0); moving.globalCompositeOperation = 'source-over';
      out.clearRect(0, 0, w, h); out.drawImage(source, 0, 0, w, h); out.globalCompositeOperation = 'destination-out'; out.drawImage(entry.mask, 0, 0); out.globalCompositeOperation = 'source-over'; out.drawImage(entry.moving, 0, 0);
      // Keep uncovered image detail at the region edge; no transparent holes.
      out.globalCompositeOperation = 'destination-over'; out.drawImage(source, 0, 0, w, h); out.globalCompositeOperation = 'source-over';
      return entry.result;
    }
    function overlays(output) {
      if (recording) return;
      const l = current(); output.save(); output.strokeStyle = '#52d5ff'; output.lineWidth = 2;
      if (paintMode && l?.localMotion) {
        const g = adapter.geometry(l), r = l.localMotion;
        output.translate(g.x, g.y); output.rotate(g.rotation);
        const scale = Math.min(1, 1024 / Math.max(g.w, g.h));
        const entry = regionMask(l, Math.max(1, Math.round(g.w * scale)), Math.max(1, Math.round(g.h * scale)));
        const mc = entry.mask.getContext('2d'); mc.globalCompositeOperation = 'source-in'; mc.fillStyle = '#52d5ff'; mc.fillRect(0, 0, entry.mask.width, entry.mask.height); mc.globalCompositeOperation = 'source-over';
        output.globalAlpha = .25; output.drawImage(entry.mask, -g.w / 2, -g.h / 2, g.w, g.h); output.globalAlpha = 1;
        (r.pins || []).forEach(p => {const x = (p.x - .5) * g.w, y = (p.y - .5) * g.h; output.beginPath(); output.arc(x, y, 5, 0, Math.PI * 2); output.stroke();});
      }
      output.restore();
      const area = protection ? {x: Math.min(protection.start.x, protection.end.x), y: Math.min(protection.start.y, protection.end.y), w: Math.abs(protection.start.x - protection.end.x), h: Math.abs(protection.start.y - protection.end.y)} : paintMode === 'protect' ? l?.protectedArea : null;
      if (area) {output.save(); output.strokeStyle = '#52d5ff'; output.setLineDash([6, 4]); output.strokeRect(area.x * canvas.width, area.y * canvas.height, area.w * canvas.width, area.h * canvas.height); output.restore();}
      if (adapter.project().motion?.seams) {
        output.save(); output.fillStyle = '#061019'; cuts(adapter.project().mode).forEach(x => output.fillRect(x * canvas.width - 4, 0, 8, canvas.height)); output.restore();
      }
    }
    function clock(now) {
      if (recording || paintMode) return paintMode ? 0 : now;
      const s = adapter.project().motion || {}, seconds = (now - previewStart) / 1000;
      if (!s.loop || s.loop === 'none') return seconds * 1000;
      const duration = bounded(s.duration, 4, 8, 8), fade = bounded(s.fade, .25, .75, .5);
      const phase = s.loop === 'blend' ? seconds % (duration - fade) + fade : loopClock(seconds, duration, s.loop);
      return phase * 1000;
    }
    function blendPreview(ms, output, drawLayer, diagnostic) {
      const p = adapter.project(), s = p.motion || {}; if (recording || paintMode || s.loop !== 'blend') return;
      const fade = bounded(s.fade, .25, .75, .5), duration = bounded(s.duration, 4, 8, 8), seconds = ms / 1000;
      // Procedural/local motion previews share the exact overlap ordering of the worker.
      // GIF/video seek/reversal is verified through the rendered join preview, not this live view.
      if (seconds >= duration - fade) {
        const offset = seconds - (duration - fade), jc = sized(joinCanvas);
        jc.fillStyle = diagnostic ? '#061019' : p.background || '#061019'; jc.fillRect(0, 0, canvas.width, canvas.height);
        renderScene(p, offset * 1000, jc, drawLayer, diagnostic);
        output.save(); output.globalAlpha = bounded(offset / fade, 0, 1, 0); output.drawImage(joinCanvas, 0, 0); output.restore();
      }
    }
    sync();
    return {sync, effectiveLayer, clock, renderScene, animateMedia, overlays, blendPreview,
      invalidate: () => {regionCache.clear();},
      recording: value => {recording = value; stopPainting(); sync();},
      hasAnimation: () => adapter.project().layers.some(l => l.visible !== false && l.localMotion?.strokes?.length),
      seams: () => cuts(adapter.project().mode)};
  };
})(typeof window !== 'undefined' ? window : globalThis);
