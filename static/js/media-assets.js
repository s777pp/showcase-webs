(function () {
  'use strict';
  const resumePrefix = 'sm-upload:';
  const t = function (ru, en) { const L=window.SMLang?SMLang.get():'en'; return L==='ru'?ru:(window.SMLang&&SMLang.translate?SMLang.translate(en,L):en); };
  const authHeaders = function () { return window.__smHeaders ? window.__smHeaders() : {}; };

  function resumeKey(file) { return resumePrefix + [file.name, file.size, file.lastModified].join(':'); }
  async function json(response) {
    const body = await response.json().catch(function () { return {}; });
    if (!response.ok || body.ok === false) throw new Error(body.msg || ('HTTP ' + response.status));
    return body;
  }
  async function begin(file) {
    const old = localStorage.getItem(resumeKey(file));
    if (old) {
      const status = await fetch('/api/assets/uploads/' + encodeURIComponent(old), { credentials: 'include', headers: authHeaders() });
      if (status.ok) return (await status.json()).upload;
      localStorage.removeItem(resumeKey(file));
    }
    const response = await fetch('/api/assets/uploads', {
      method: 'POST', credentials: 'include', headers: Object.assign({'Content-Type':'application/json'}, authHeaders()),
      body: JSON.stringify({name:file.name, size:file.size, type:file.type})
    });
    const body = await json(response);
    localStorage.setItem(resumeKey(file), body.upload.id);
    body.upload.chunk_size = body.chunk_size;
    return body.upload;
  }
  async function upload(file, progress) {
    if (file.__assetId) return file.__assetId;
    let state = await begin(file);
    let offset = Number(state.offset || 0);
    const chunkSize = Number(state.chunk_size || 2 * 1024 * 1024);
    while (offset < file.size) {
      const end = Math.min(file.size, offset + chunkSize);
      const response = await fetch('/api/assets/uploads/' + encodeURIComponent(state.id), {
        method: 'PATCH', credentials: 'include', headers: Object.assign({'Upload-Offset':String(offset),'Content-Type':'application/offset+octet-stream'}, authHeaders()),
        body: file.slice(offset, end)
      });
      if (response.status === 409) { offset = Number(response.headers.get('Upload-Offset') || 0); continue; }
      if (!response.ok) await json(response);
      offset = Number(response.headers.get('Upload-Offset') || end);
      if (progress) progress(offset / file.size);
    }
    const done = await json(await fetch('/api/assets/uploads/' + encodeURIComponent(state.id) + '/complete', {
      method:'POST', credentials:'include', headers:Object.assign({'Content-Type':'application/json'}, authHeaders()), body:'{}'
    }));
    localStorage.removeItem(resumeKey(file));
    try { Object.defineProperty(file, '__assetId', {value:done.asset.id, writable:true, configurable:true}); } catch (_) { file.__assetId = done.asset.id; }
    return done.asset.id;
  }
  async function ensure(files, progress) {
    const ids = [];
    for (let index = 0; index < files.length; index += 1) {
      ids.push(await upload(files[index], function (part) {
        if (progress) progress((index + part) / Math.max(1, files.length), files[index]);
      }));
    }
    return ids;
  }

  function buildDialog() {
    let overlay = document.getElementById('assetLibrary');
    if (overlay) return overlay;
    overlay = document.createElement('div'); overlay.id = 'assetLibrary'; overlay.className = 'asset-library';
    overlay.innerHTML = '<div class="asset-library__panel" role="dialog" aria-modal="true"><header><div><small>MEDIA / SHARED</small><h3>'+t('Мои файлы','My media')+'</h3></div><button type="button" data-close>×</button></header><p>'+t('Загружай один раз и используй исходник в разных инструментах. Незавершённая загрузка продолжится автоматически.','Upload once and reuse the source in different tools. Interrupted uploads resume automatically.')+'</p><div class="asset-library__list" data-list></div></div>';
    overlay.addEventListener('click', function (event) { if (event.target === overlay || event.target.closest('[data-close]')) overlay.classList.remove('is-open'); });
    document.body.appendChild(overlay); return overlay;
  }
  async function openLibrary(target) {
    const overlay = buildDialog(); const list = overlay.querySelector('[data-list]');
    overlay.classList.add('is-open'); list.innerHTML = '<span class="asset-library__empty">'+t('Загрузка…','Loading…')+'</span>';
    try {
      const body = await json(await fetch('/api/assets', {credentials:'include', cache:'no-store', headers:authHeaders()}));
      if (!body.assets.length) { list.innerHTML = '<span class="asset-library__empty">'+t('Пока нет сохранённых исходников. Добавь файл в обработке — он появится здесь.','No saved sources yet. Add a file in Process and it will appear here.')+'</span>'; return; }
      list.innerHTML = '';
      body.assets.forEach(function (asset) {
        const item = document.createElement('button'); item.type='button'; item.className='asset-library__item';
        item.innerHTML = '<span class="asset-library__thumb"></span><b></b><small></small>';
        item.querySelector('b').textContent = asset.name;
        item.querySelector('small').textContent = (asset.size/1048576).toFixed(2)+' MB';
        const thumb = item.querySelector('.asset-library__thumb');
        if ((asset.media_type || '').startsWith('image/')) thumb.style.backgroundImage='url("/api/assets/'+asset.id+'/content")';
        item.onclick = async function () {
          item.disabled=true;
          const response = await fetch('/api/assets/'+asset.id+'/content', {credentials:'include', headers:authHeaders()});
          if (!response.ok) { item.disabled=false; return; }
          const blob = await response.blob(); const file = new File([blob], asset.name, {type:asset.media_type || blob.type});
          try { Object.defineProperty(file, '__assetId', {value:asset.id, writable:true}); } catch (_) { file.__assetId=asset.id; }
          document.dispatchEvent(new CustomEvent('sm:assets-selected', {detail:{files:[file], target:target || 'process', asset:asset}}));
          overlay.classList.remove('is-open');
        };
        list.appendChild(item);
      });
    } catch (error) { list.textContent=String(error.message || error); }
  }
  window.SMMediaAssets = { upload:upload, ensure:ensure, openLibrary:openLibrary };
})();
