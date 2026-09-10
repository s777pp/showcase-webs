/* Process guidance and local source inspection. No file bytes leave the browser here. */
(function () {
  'use strict';

  var root = document.getElementById('tab-process');
  var panel = document.getElementById('processPreflight');
  if (!root || !panel) return;

  var allowed = /\.(png|jpe?g|gif|webp|mp4|mov|webm|avi)$/i;
  var generation = 0;
  var latest = { blocked:false, pending:false, items:[] };
  var processStartedAt = 0;

  function copy(key, vars) { return window.WorkspaceCopy ? WorkspaceCopy(key, vars) : key; }
  function escape(value) { return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) { return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c]; }); }
  function size(value) { return value >= 1048576 ? (value / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(value / 1024)) + ' KB'; }
  function rotatedDimensions(meta, angle) {
    return Math.abs(Number(angle) || 0) % 180 === 90 ? { width:meta.height, height:meta.width } : meta;
  }
  function probeImage(file) {
    return new Promise(function (resolve, reject) {
      var url = URL.createObjectURL(file), image = new Image();
      image.onload = function () { URL.revokeObjectURL(url); resolve({ width:image.naturalWidth, height:image.naturalHeight, duration:0 }); };
      image.onerror = function () { URL.revokeObjectURL(url); reject(Error(copy('fileUnsupported'))); };
      image.src = url;
    });
  }
  function probeVideo(file) {
    return new Promise(function (resolve, reject) {
      var url = URL.createObjectURL(file), video = document.createElement('video');
      video.preload = 'metadata'; video.muted = true;
      video.onloadedmetadata = function () { var meta={ width:video.videoWidth, height:video.videoHeight, duration:Number(video.duration)||0 }; video.src=''; URL.revokeObjectURL(url); resolve(meta); };
      video.onerror = function () { video.src=''; URL.revokeObjectURL(url); reject(Error(copy('fileUnsupported'))); };
      video.src = url;
    });
  }
  function isVideo(file) { return String(file.type || '').indexOf('video/') === 0 || /\.(mp4|mov|webm|avi)$/i.test(file.name || ''); }
  async function probe(file, rotation, targetWidth) {
    var errors=[], warnings=[], meta={ width:0,height:0,duration:0 };
    if (!file.size) errors.push(copy('fileEmpty'));
    if (file.size > 40 * 1024 * 1024) errors.push(copy('fileTooLarge'));
    if (!allowed.test(file.name || '') && !/^(image|video)\//.test(file.type || '')) errors.push(copy('fileUnsupported'));
    if (!errors.length) {
      try { meta = await (isVideo(file) ? probeVideo(file) : probeImage(file)); }
      catch (error) { errors.push(error.message || copy('fileUnsupported')); }
    }
    meta = rotatedDimensions(meta, rotation);
    if (meta.duration > 8.05) warnings.push(copy('fileLong'));
    if (meta.width && meta.width < targetWidth * .82) warnings.push(copy('fileSmall'));
    return { name:file.name, size:file.size, meta:meta, errors:errors, warnings:warnings };
  }
  function paint(result, elapsed) {
    latest = result;
    var run=document.getElementById('btnRun');
    if (!result.items.length) {
      if(run)run.disabled=true;
      panel.className='process-preflight';
      panel.innerHTML='<div class="process-preflight__empty"><span>✓</span><p><b>'+escape(copy('preflightTitle'))+'</b><small>'+escape(copy('preflightEmpty'))+'</small></p></div>';
      return;
    }
    var problems=result.items.reduce(function (n,item) { return n+item.errors.length; },0);
    var warnings=result.items.reduce(function (n,item) { return n+item.warnings.length; },0);
    panel.className='process-preflight '+(problems?'is-blocked':'is-ready');
    if(run)run.disabled=problems>0;
    var title=problems?copy('preflightBlocked'):copy('preflightReady');
    var glyph=problems?'!':'✓';
    var html='<header><span>'+glyph+'</span><div><b>'+escape(title)+'</b><small>'+escape(copy('localCheck',{ms:Math.max(1,Math.round(elapsed))}))+'</small></div><em>'+result.items.length+' · '+warnings+'</em></header><div class="process-preflight__list">';
    result.items.forEach(function(item){
      var dimensions=item.meta.width?item.meta.width+'×'+item.meta.height:'';
      var duration=item.meta.duration?item.meta.duration.toFixed(1)+' s':'';
      var issue=item.errors[0]||item.warnings[0]||'';
      html+='<article class="'+(item.errors.length?'is-error':item.warnings.length?'is-warning':'is-ok')+'"><i></i><p><b>'+escape(item.name)+'</b><small>'+escape([size(item.size),dimensions,duration].filter(Boolean).join(' · '))+'</small></p><span>'+escape(issue||'OK')+'</span></article>';
    });
    panel.innerHTML=html+'</div>';
  }
  async function inspect(files, rotations) {
    var token=++generation, started=performance.now(), target=Number(document.getElementById('size')?.value)||750;
    if (!files.length) { paint({blocked:false,pending:false,items:[]},0); updateRoute('mode'); return latest; }
    panel.className='process-preflight is-checking';
    var run=document.getElementById('btnRun');if(run)run.disabled=true;
    panel.innerHTML='<div class="process-preflight__empty"><span class="is-spin">◌</span><p><b>'+escape(copy('preflightChecking'))+'</b></p></div>';
    var items=await Promise.all(files.map(function(file,index){return probe(file,rotations[index]||0,target);}));
    if(token!==generation)return latest;
    paint({blocked:items.some(function(x){return x.errors.length;}),pending:false,items:items},performance.now()-started);
    updateRoute('files');
    return latest;
  }
  function updateRoute(active) {
    root.querySelectorAll('[data-process-step]').forEach(function(button){
      var name=button.dataset.processStep;
      button.classList.toggle('is-active',name===active);
      var complete=(name==='mode')||(name==='settings')||(name==='files'&&latest.items.length&&!latest.blocked)||(name==='result'&&active==='result');
      button.classList.toggle('is-complete',!!complete&&name!==active);
    });
  }
  root.querySelectorAll('[data-process-step]').forEach(function(button){
    button.addEventListener('click',function(){
      var name=button.dataset.processStep, target=name==='result'?root.querySelector('.workspace-result'):document.querySelector('[data-process-card="'+(name==='settings'?'settings':name)+'"]');
      if(target)target.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'center'});
    });
  });
  function applyLanguage(){ if(WorkspaceCopy.apply)WorkspaceCopy.apply(root); paint(latest,0); }
  window.addEventListener('sm:langchange',applyLanguage);
  applyLanguage();

  window.ProcessGuide = {
    filesChanged:function(files,rotations){ return inspect(Array.from(files||[]),Array.from(rotations||[])); },
    modeChanged:function(){ return inspect(Array.from(window.state?.files||[]),Array.from(window.state?.fileRotations||[])); },
    beforeRun:async function(files,rotations){ var result=await inspect(Array.from(files||[]),Array.from(rotations||[])); if(result.blocked){panel.scrollIntoView({behavior:'smooth',block:'center'});return false;} return true; },
    running:function(){processStartedAt=performance.now();updateRoute('result');root.classList.add('is-processing');},
    complete:function(){root.classList.remove('is-processing');updateRoute('result');if(processStartedAt)console.info('[Showcase Maker] process UI elapsed:',Math.round(performance.now()-processStartedAt),'ms');},
    failed:function(){root.classList.remove('is-processing');updateRoute('files');},
    message:function(error){var raw=String(error&&error.message?error.message:error||'').trim();return raw||copy('processingFailed');}
  };
})();
