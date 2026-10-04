/* High-quality Builder export (2026-09-30).
   Animated designs are rendered frame by frame at exact times (showcase-builder.js seeks
   videos, steps GIFs and draws each frame), encoded with WebCodecs (VP9, high bitrate) and
   packed into a small WebM file by the muxer below. Nothing depends on the machine being
   fast enough to record in real time: no dropped frames, exact scene length, exact loop.
   SMBuilderExport.supported() tells whether this path is available; otherwise
   showcase-builder.js falls back to MediaRecorder. */
(function () {
  'use strict';

  // ------------------------------------------------------------ WebM writer
  var enc = new TextEncoder();
  function concat(parts) {
    var size = 0; parts.forEach(function (p) { size += p.length; });
    var out = new Uint8Array(size), at = 0;
    parts.forEach(function (p) { out.set(p, at); at += p.length; });
    return out;
  }
  function uint(value) {
    var bytes = []; value = Math.max(0, Math.floor(value));
    do { bytes.unshift(value % 256); value = Math.floor(value / 256); } while (value > 0);
    return new Uint8Array(bytes);
  }
  function float64(value) { var b = new Uint8Array(8); new DataView(b.buffer).setFloat64(0, value); return b; }
  function size8(n) { // EBML data size, always 8 bytes: 0x01 + 7-byte big-endian length
    var b = new Uint8Array(8); b[0] = 1;
    for (var i = 7; i >= 1; i--) { b[i] = n % 256; n = Math.floor(n / 256); }
    return b;
  }
  function id(hex) { var b = []; for (var i = 0; i < hex.length; i += 2) b.push(parseInt(hex.slice(i, i + 2), 16)); return new Uint8Array(b); }
  function el(hex, data) { data = data instanceof Uint8Array ? data : concat(data); return concat([id(hex), size8(data.length), data]); }

  function webm(o) {
    // o: {codecId, width, height, fps, durationMs, chunks:[{data, ms, key}], codecPrivate}
    var header = el('1A45DFA3', [el('4286', uint(1)), el('42F7', uint(1)), el('42F2', uint(4)), el('42F3', uint(8)),
      el('4282', enc.encode('webm')), el('4287', uint(4)), el('4285', uint(2))]);
    var info = el('1549A966', [el('2AD7B1', uint(1000000)), el('4D80', enc.encode('ShowcaseMaker')), el('5741', enc.encode('ShowcaseMaker')), el('4489', float64(o.durationMs))]);
    var video = el('E0', [el('B0', uint(o.width)), el('BA', uint(o.height))]);
    var entry = [el('D7', uint(1)), el('73C5', uint(1)), el('83', uint(1)), el('9C', uint(0)), el('86', enc.encode(o.codecId)),
      el('23E383', uint(Math.round(1e9 / o.fps))), video];
    if (o.codecPrivate && o.codecPrivate.length) entry.push(el('63A2', o.codecPrivate));
    var tracks = el('1654AE6B', [el('AE', entry)]);
    var clusters = [], current = null, clusterStart = 0;
    function flush() { if (current) clusters.push(el('1F43B675', current)); current = null; }
    o.chunks.forEach(function (c) {
      if (!current || c.key || c.ms - clusterStart > 30000) { flush(); clusterStart = c.ms; current = [el('E7', uint(c.ms))]; }
      var rel = c.ms - clusterStart, head = new Uint8Array(4);
      head[0] = 0x81; head[1] = (rel >> 8) & 0xff; head[2] = rel & 0xff; head[3] = c.key ? 0x80 : 0;
      current.push(el('A3', concat([head, c.data])));
    });
    flush();
    var segment = el('18538067', [info, tracks].concat(clusters));
    return new Blob([header, segment], { type: 'video/webm' });
  }

  // ------------------------------------------------------------ encoder
  var CODECS = [
    { codec: 'vp09.00.41.08', id: 'V_VP9' },
    { codec: 'vp09.00.10.08', id: 'V_VP9' },
    { codec: 'vp8', id: 'V_VP8' }
  ];
  function supported() { return typeof window.VideoEncoder === 'function' && typeof window.VideoFrame === 'function'; }

  async function pickCodec(width, height, fps, bitrate) {
    for (var i = 0; i < CODECS.length; i++) {
      var config = { codec: CODECS[i].codec, width: width, height: height, bitrate: bitrate, framerate: fps, bitrateMode: 'variable', latencyMode: 'quality' };
      try { var r = await VideoEncoder.isConfigSupported(config); if (r && r.supported) return { config: r.config || config, id: CODECS[i].id }; } catch (e) {}
    }
    return null;
  }

  /* Encode `count` frames. render(i, ms) must draw frame i on `canvas` (it may be async).
     Returns a WebM Blob. onProgress(done, total). */
  async function encode(canvas, opts) {
    if (!supported()) throw Object.assign(new Error('webcodecs_unavailable'), { code: 'unsupported' });
    var fps = opts.fps, count = opts.count, width = canvas.width, height = canvas.height;
    if (width % 2 || height % 2) throw new Error('Canvas size must be even');
    var seconds = count / fps, bitrate = Math.round(Math.min(opts.maxBitrate || 20e6, (opts.maxBytes || 30e6) * 8 / seconds));
    var picked = await pickCodec(width, height, fps, bitrate);
    if (!picked) throw Object.assign(new Error('no_codec'), { code: 'unsupported' });
    var chunks = [], failure = null, codecPrivate = null;
    var encoder = new VideoEncoder({
      output: function (chunk, meta) {
        var data = new Uint8Array(chunk.byteLength); chunk.copyTo(data);
        chunks.push({ data: data, ms: Math.round(chunk.timestamp / 1000), key: chunk.type === 'key' });
        if (meta && meta.decoderConfig && meta.decoderConfig.description && !codecPrivate) codecPrivate = new Uint8Array(meta.decoderConfig.description);
      },
      error: function (e) { failure = e; }
    });
    encoder.configure(picked.config);
    var step = 1e6 / fps, keyEvery = Math.max(1, Math.round(fps * 2));
    for (var i = 0; i < count; i++) {
      if (failure) throw failure;
      if (opts.cancelled && opts.cancelled()) { encoder.close(); throw Object.assign(new Error('cancelled'), { code: 'cancelled' }); }
      await opts.render(i, i * 1000 / fps);
      var frame = new VideoFrame(canvas, { timestamp: Math.round(i * step), duration: Math.round(step) });
      encoder.encode(frame, { keyFrame: i % keyEvery === 0 });
      frame.close();
      while (encoder.encodeQueueSize > 6) await new Promise(function (r) { setTimeout(r, 4); });
      if (opts.onProgress) opts.onProgress(i + 1, count);
    }
    await encoder.flush();
    encoder.close();
    if (failure) throw failure;
    chunks.sort(function (a, b) { return a.ms - b.ms; });
    return webm({ codecId: picked.id, width: width, height: height, fps: fps, durationMs: seconds * 1000, chunks: chunks, codecPrivate: codecPrivate });
  }

  // ------------------------------------------------------------ GIF frames
  /* Frame-accurate GIF playback for the export (ImageDecoder). Returns null when the
     browser cannot decode GIFs this way; the caller then uses the live <img>. */
  async function gifTrack(url) {
    if (typeof window.ImageDecoder !== 'function') return null;
    var buffer = await fetch(url, { credentials: 'same-origin' }).then(function (r) { if (!r.ok) throw new Error('gif ' + r.status); return r.arrayBuffer(); });
    var decoder = new ImageDecoder({ data: buffer, type: 'image/gif' });
    await decoder.tracks.ready;
    var count = decoder.tracks.selectedTrack ? decoder.tracks.selectedTrack.frameCount : 1, starts = [], total = 0;
    for (var i = 0; i < count; i++) {
      var r = await decoder.decode({ frameIndex: i });
      starts.push(total); total += Math.max(20000, r.image.duration || 100000); r.image.close();
    }
    var current = null, currentIndex = -1;
    return {
      async frameAt(ms) {
        var t = ((ms * 1000) % total + total) % total, index = 0;
        while (index + 1 < starts.length && starts[index + 1] <= t) index++;
        if (index !== currentIndex) {
          var next = (await decoder.decode({ frameIndex: index })).image;
          if (current) current.close();
          current = next; currentIndex = index;
        }
        return current;
      },
      close: function () { if (current) current.close(); current = null; try { decoder.close(); } catch (e) {} }
    };
  }

  // ------------------------------------------------------------ direct download
  /* Send an exported design straight to the Steam pipeline (/api/process/start: cuts, GIF
     fit under 5 MB, Steam byte fix, ZIP) and wait for the result. The same checks and quota
     as the Prepare tab apply on the server. */
  function upload(form, onProgress) {
    return new Promise(function (resolve, reject) {
      var xhr = new XMLHttpRequest();
      xhr.open('POST', '/api/process/start'); xhr.responseType = 'json'; xhr.withCredentials = true;
      try { var token = localStorage.getItem('sm_token'); if (token) xhr.setRequestHeader('X-Access-Token', token); } catch (e) {}
      try { var extra = window.SMAnalytics ? SMAnalytics.headers() : {}; Object.keys(extra || {}).forEach(function (k) { xhr.setRequestHeader(k, extra[k]); }); } catch (e) {}
      xhr.upload.onprogress = function (e) { if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total); };
      xhr.onload = function () {
        var body = xhr.response || {};
        if (xhr.status >= 200 && xhr.status < 300 && body.ok && body.job_id) resolve(body);
        else reject(Object.assign(new Error(body.msg || ('HTTP ' + xhr.status)), { status: xhr.status, body: body }));
      };
      xhr.onerror = function () { reject(new Error('Network error')); };
      xhr.send(form);
    });
  }
  async function processForSteam(file, o) {
    var form = new FormData();
    form.append('mode', o.mode); form.append('fps', String(o.fps || 15)); form.append('size', String(o.size || 750));
    form.append('gif_encoder', 'gifski'); form.append('workshop_outline', '0'); form.append('auto_contrast', '0');
    form.append('all_modes', '0'); form.append('rotations', '[0]'); form.append('asset_ids', '[]');
    Object.keys(o.watermark || {}).forEach(function (k) { form.append(k, o.watermark[k]); });
    // Same ZIP rule as every tool: only the Steam files (extras off), chosen encode speed.
    form.append('encode_profile', o.encodeProfile || 'standard');
    form.append('files', file);
    var started = await upload(form, function (p) { o.onProgress && o.onProgress('upload', p); });
    var id = started.job_id, deadline = Date.now() + 15 * 60 * 1000, job = null;
    while (Date.now() < deadline) {
      await new Promise(function (r) { setTimeout(r, 900); });
      var headers = {}; try { var token = localStorage.getItem('sm_token'); if (token) headers['X-Access-Token'] = token; } catch (e) {}
      var res = await fetch('/api/process/status/' + encodeURIComponent(id), { credentials: 'include', cache: 'no-store', headers: headers });
      job = await res.json();
      if (!res.ok || !job.ok) throw new Error(job.msg || ('HTTP ' + res.status));
      if (job.status === 'error' || job.status === 'cancelled') throw new Error(job.error || (job.errors || []).join('; ') || job.status);
      if (job.status === 'done') return { id: id, job: job };
      o.onProgress && o.onProgress(job.status === 'queued' ? 'queued' : 'processing', Math.max(0, Math.min(99, Number(job.pct) || 0)) / 100, job);
    }
    throw new Error('timeout');
  }

  window.SMBuilderExport = { supported: supported, encode: encode, gifTrack: gifTrack, processForSteam: processForSteam, _webm: webm };
})();
