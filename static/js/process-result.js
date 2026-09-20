(function () {
  'use strict';
  const t = window.WorkspaceCopy;
  const editorText = key => window.WorkspaceEditorCopy ? WorkspaceEditorCopy(key) : key;
  let urls = [], generation = 0, modal = null, previousFocus = null;
  const automaticallyDownloaded = new Set();

  function node(tag, text, className) {
    const element = document.createElement(tag);
    if (text) element.textContent = text;
    if (className) element.className = className;
    return element;
  }
  function releaseUrls() { urls.forEach(URL.revokeObjectURL); urls = []; }
  function close() {
    if (!modal) return;
    generation += 1;
    releaseUrls();
    window.SteamCheckResult?.release?.();
    modal.remove();
    modal = null;
    document.body.classList.remove('has-workspace-result');
    if (previousFocus?.isConnected) previousFocus.focus({preventScroll:true});
    previousFocus = null;
  }
  function createModal() {
    previousFocus = document.activeElement;
    const overlay = node('div', null, 'workspace-result-modal');
    const backdrop = node('button', null, 'workspace-result-modal__backdrop');
    backdrop.type = 'button'; backdrop.tabIndex = -1;
    backdrop.setAttribute('aria-label', editorText('closeResult'));
    const dialog = node('section', null, 'workspace-result-modal__dialog');
    dialog.setAttribute('role', 'dialog'); dialog.setAttribute('aria-modal', 'true');
    dialog.setAttribute('aria-labelledby', 'workspaceResultTitle');
    const header = node('header', null, 'workspace-result-modal__header');
    const heading = node('div');
    heading.append(node('span', 'STEAM / RESULT', 'workspace-result-modal__eyebrow'));
    const title = node('h2', editorText('resultDialogTitle')); title.id = 'workspaceResultTitle'; heading.append(title);
    const closeButton = node('button', '×', 'workspace-result-modal__close');
    closeButton.type = 'button'; closeButton.setAttribute('aria-label', editorText('closeResult'));
    header.append(heading, closeButton);
    const body = node('div', null, 'workspace-result-modal__body');
    dialog.append(header, body); overlay.append(backdrop, dialog);
    backdrop.onclick = close; closeButton.onclick = close;
    overlay.addEventListener('keydown', event => {
      if (event.key === 'Escape') { event.preventDefault(); close(); return; }
      if (event.key !== 'Tab') return;
      const focusable = [...dialog.querySelectorAll('button,a[href],select,[tabindex]:not([tabindex="-1"])')].filter(item => !item.disabled && !item.hidden);
      if (!focusable.length) return;
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    });
    document.body.append(overlay); document.body.classList.add('has-workspace-result'); modal = overlay;
    requestAnimationFrame(() => closeButton.focus({preventScroll:true}));
    return body;
  }

  window.ProcessResult = {
    close,
    async open(job, id, originals) {
      close();
      const token = ++generation;
      const download = job.download || '/api/process/download/' + encodeURIComponent(id);
      const body = createModal();
      const panel = node('section', null, 'workspace-result'); panel.id = 'workspaceResult'; panel.setAttribute('data-no-translate', '');
      panel.append(node('h3', editorText('previewSummary')), node('p', editorText('resultHint'), 'editor-note'));
      const toolbar = node('div', null, 'workspace-result__toolbar'), select = node('select'); select.setAttribute('aria-label', t('result'));
      const tabs = ['result','original','compare'].map(key => {
        const button = node('button', t(key)); button.type = 'button'; button.onclick = () => { view = key; paint(); };
        toolbar.append(button); return button;
      });
      const zoom = node('button', t('fit')); zoom.type = 'button'; let actual = false;
      zoom.onclick = () => { actual = !actual; zoom.textContent = actual ? '100%' : t('fit'); paint(); };
      toolbar.append(zoom, select); panel.append(toolbar);
      const viewport = node('div', null, 'workspace-result__viewport'); panel.append(viewport);
      const files = node('div', null, 'workspace-result__files'); panel.append(files);
      const downloadButton = node('a', editorText('downloadAgain'), 'btn workspace-result__download');
      downloadButton.href = download; downloadButton.download = 'showcase_' + String(job.mode || 'out') + '.zip'; panel.append(downloadButton);
      body.append(panel);

      const readiness = node('section', null, 'workspace-result__readiness steam-check');
      readiness.append(node('h3', editorText('readinessTitle'), 'workspace-result__section-title'));
      const reportMount = node('div', null, 'workspace-result__readiness-report'); readiness.append(reportMount); body.append(readiness);
      const integrated = !!(job.readiness && window.SteamCheckResult?.open(job.readiness, download, reportMount, {jobId:id}));
      if (integrated) readiness.dataset.status = job.readiness.status || 'ready';
      else {
        const notice = node('div', null, 'workspace-result__readiness-empty');
        notice.append(node('span', 'i'), node('p', editorText('readinessUnavailable'))); reportMount.append(notice);
      }
      if (!automaticallyDownloaded.has(String(id))) {
        automaticallyDownloaded.add(String(id));
        requestAnimationFrame(() => { if (token === generation && downloadButton.isConnected) downloadButton.click(); });
      }

      let groups = [], view = 'result', previousGroup = null;
      viewport.textContent = t('loading'); toolbar.hidden = true;
      function paint() {
        if (!groups.length) return;
        const group = groups[+select.value || 0], stem = group.name.replace(/_(workshop|featured|split)$/,'');
        if (previousGroup && previousGroup !== group) previousGroup.files.forEach(file => { if (file.image) { file.image.src = ''; file.image = null; } });
        previousGroup = group;
        const matches = originals.filter(file => file.name.replace(/\.[^.]+$/,'').slice(0,40) === stem);
        const source = matches.length === 1 ? matches[0] : (originals.length === 1 ? originals[0] : null);
        tabs[1].disabled = tabs[2].disabled = !source;
        if (!source) view = 'result';
        tabs.forEach((button,index) => button.setAttribute('aria-pressed', String(['result','original','compare'][index] === view)));
        releaseUrls(); viewport.replaceChildren(); files.replaceChildren();
        const columns = node('div', null, 'workspace-result__columns' + (view === 'compare' ? ' is-compare' : '')); viewport.append(columns);
        if (view !== 'result' && source) {
          const figure = node('figure', null, 'workspace-result__original'); figure.append(node('figcaption', t('original')));
          const media = node(source.type.startsWith('video/') ? 'video' : 'img'), url = URL.createObjectURL(source);
          urls.push(url); media.src = url; media.alt = source.name;
          if (media.tagName === 'VIDEO') { media.muted = true; media.loop = true; media.autoplay = true; media.controls = true; media.playsInline = true; }
          figure.append(media); columns.append(figure);
        }
        if (view !== 'original') {
          const figure = node('figure'); figure.append(node('figcaption', t('result')));
          const parts = node('div', null, 'workspace-result__parts'); figure.append(parts); columns.append(figure);
          const widths = new Map();
          group.files.forEach(file => {
            const cell = node('div', null, 'workspace-result__part'), image = file.image || node('img'); image.alt = file.name;
            if (!file.image) { image.src = file.url; file.image = image; }
            image.onload = () => {
              widths.set(file.name, image.naturalWidth); cell.style.flex = image.naturalWidth + ' 0 0px';
              if (file.detail) file.detail.textContent = ' · ' + image.naturalWidth + '×' + image.naturalHeight;
              if (actual && widths.size === group.files.length) parts.style.width = Array.from(widths.values()).reduce((a,b) => a + b, 0) + 'px';
            };
            image.onerror = () => { image.alt = t('previewError'); }; cell.append(image); parts.append(cell);
            if (image.complete && image.naturalWidth) image.onload();
          });
        }
        group.files.forEach(file => {
          const row = node('div'), link = node('a', file.name.split('/').pop()); link.href = file.url; link.download = file.name.split('/').pop();
          file.detail = node('span'); if (file.image?.naturalWidth) file.detail.textContent = ' · ' + file.image.naturalWidth + '×' + file.image.naturalHeight;
          row.append(link, document.createTextNode(' · ' + (file.size / 1024 / 1024).toFixed(2) + ' MB'), file.detail); files.append(row);
        });
      }
      try {
        const response = await fetch('/api/process/preview/' + encodeURIComponent(id), {credentials:'include',cache:'no-store'}), data = await response.json();
        if (token !== generation) return true;
        if (!response.ok || !data.ok || !data.files.length) throw Error('preview');
        const grouped = new Map();
        data.files.forEach(file => { const key = file.name.split('/').slice(0,-1).join('/'); if (!grouped.has(key)) grouped.set(key,[]); grouped.get(key).push(file); });
        groups = Array.from(grouped, ([name,entries]) => ({name,files:entries.sort((a,b) => a.name.localeCompare(b.name,undefined,{numeric:true}))}));
        groups.forEach((group,index) => { const option = node('option', group.name); option.value = index; select.append(option); });
        select.onchange = paint; select.hidden = groups.length < 2; toolbar.hidden = false; paint();
      } catch (_) { if (token === generation) viewport.textContent = t('previewError'); }
      return true;
    }
  };
})();
