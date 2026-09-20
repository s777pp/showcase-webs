/* Presentation only: existing inputs, editor state and processing APIs remain authoritative. */
(function () {
  'use strict';
  const t = window.WorkspaceEditorCopy;
  const el = id => document.getElementById(id);
  const paths = {
    upload: '<path d="M12 16V3m-5 5 5-5 5 5M4 15v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5"/>',
    cut: '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="m8 8 12 12M8 16 20 4"/>',
    layers: '<path d="m12 3 10 5-10 5L2 8Zm-10 9 10 5 10-5M2 16l10 5 10-5"/>',
    background: '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="8" r="1.5"/><path d="m3 17 5-5 4 4 4-6 5 7"/>',
    character: '<circle cx="12" cy="7" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2"/>',
    text: '<path d="M4 6V3h16v3M12 3v18m-4 0h8"/>',
    frame: '<path d="M3 9V3h6m6 0h6v6m0 6v6h-6m-6 0H3v-6"/><rect x="7" y="7" width="10" height="10" rx="1"/>',
    effect: '<path d="m12 3 2.4 6.6L21 12l-6.6 2.4L12 21l-2.4-6.6L3 12l6.6-2.4Z"/><path d="M20 2v4m-2-2h4"/>',
    sliders: '<path d="M4 6h7m4 0h5M4 18h3m4 0h9"/><circle cx="13" cy="6" r="2"/><circle cx="9" cy="18" r="2"/>',
    pointer: '<path d="m5 3 14 9-7 2-3 7Z"/>',
    visible: '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
    hidden: '<path d="m3 3 18 18M10 5h2c6 0 10 7 10 7a18 18 0 0 1-3 4M6 6a19 19 0 0 0-4 6s4 7 10 7c1 0 3 0 4-1"/>',
    lock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V6a4 4 0 0 1 8 0v4m-4 5v2"/>',
    unlock: '<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V6a4 4 0 0 1 8 0m-4 9v2"/>',
    duplicate: '<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
    up: '<path d="M12 20V4m-6 6 6-6 6 6"/>',
    down: '<path d="M12 4v16m-6-6 6 6 6-6"/>',
    delete: '<path d="M4 6h16M9 6V3h6v3m-9 0 1 15h10l1-15M10 10v7m4-7v7"/>'
  };
  function icon(name) {
    return '<svg class="editor-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' + (paths[name] || paths.layers) + '</svg>';
  }
  function text(node, value) { if (node && node.textContent !== value) node.textContent = value; }
  function language() {
    document.querySelectorAll('[data-editor-copy]').forEach(node => text(node, t(node.dataset.editorCopy)));
    document.querySelectorAll('[data-editor-icon]').forEach(node => { if (!node.firstElementChild) node.innerHTML = icon(node.dataset.editorIcon); });
    el('builderProjectName').setAttribute('aria-label', t('projectName'));
    el('drop').setAttribute('aria-label', t('chooseFile'));
    el('builderCatalogSearch').placeholder = t('searchBackgrounds');
    el('builderCatalogSearch').setAttribute('aria-label', t('searchBackgrounds'));
    el('btnClear').removeAttribute('data-i');
    text(el('btnClear'), t('clear'));
    text(el('btnCancelProcess'), t('cancel'));
    navigation();
    processState();
  }
  function navigation() {
    const name = document.querySelector('#nav .active')?.dataset.tab || 'process';
    const workspace = ['process', 'builder', 'projects', 'dna'].includes(name);
    document.body.classList.toggle('is-showcase-workspace', workspace);
    document.body.dataset.workspaceTool = name;
    document.querySelector('.workspace-switch').hidden = !workspace;
    document.querySelectorAll('.workspace-switch [data-open-tool]').forEach(button => {
      button.classList.toggle('active', button.dataset.openTool === name);
      if (button.dataset.openTool === name) button.setAttribute('aria-current', 'page');
      else button.removeAttribute('aria-current');
    });
    if (name === 'process' || name === 'builder') {
      text(el('pageTitle'), t(name + 'Title'));
      text(el('pageSub'), t(name + 'Sub'));
    }
  }
  function processState() {
    const count = window.state?.files?.length || 0;
    const mode = window.state?.mode || 'workshop';
    const key = {workshop:'ws', featured:'ft', split:'sp'}[mode] || 'ws';
    el('tab-process').classList.toggle('has-files', count > 0);
    text(el('processNextHint'), t(count ? 'ready' : 'needFile'));
    text(el('processLayoutCaption'), t('mode_' + key) + ' · ' + t('mode_' + key + '_hint'));
    document.querySelector('.editor-preview-sample').dataset.previewMode = mode;
    document.querySelectorAll('#processModeCard [data-mode]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.mode === mode)));
    el('btnClear').hidden = count === 0;
  }
  function builderState(detail) {
    el('builderStart').hidden = detail.count > 0;
    el('builderInspectorEmpty').hidden = !!detail.selected;
    text(el('builderElementCount'), String(detail.count));
    if (!el('showcaseBuilder').classList.contains('is-exporting')) el('builderExport').disabled = !detail.exportable;
    el('showcaseBuilder').classList.toggle('has-elements', detail.count > 0);
    document.querySelector('[data-editor-jump="edit"]').disabled = !detail.selected;
  }
  function disclosure(content, key, className) {
    if (!content || content.parentElement.classList.contains(className)) return;
    const details = document.createElement('details'), summary = document.createElement('summary');
    details.className = className;
    summary.dataset.editorCopy = key;
    summary.textContent = t(key);
    content.before(details);
    details.append(summary, content);
  }
  function builderReady() {
    disclosure(document.querySelector('.builder-canvas-toolbar'), 'canvasTools', 'editor-canvas-options');
    disclosure(el('builderEffectControls').querySelector('.builder-motion-body'), 'effectAdvanced', 'editor-effect-options');
    // Scene-wide settings need the width of the stage. In the tools rail long
    // translated labels collapse to one character per line.
    const motion = document.querySelector('.builder-stage > .builder-motion-panel');
    const canvas = document.querySelector('.builder-canvas-wrap');
    if (motion && canvas) canvas.before(motion);
    document.querySelectorAll('[data-add-layer]').forEach(button => button.addEventListener('click', () => {
      if (['text','frame','effect'].includes(button.dataset.addLayer) && matchMedia('(max-width:760px)').matches) {
        requestAnimationFrame(() => jump('edit'));
      }
    }));
    language();
  }
  function catalogOpened(reset) {
    if (!reset) return;
    el('builderCatalog').scrollIntoView({block:'start', behavior:'instant'});
    el('builderCatalogSearch').focus({preventScroll:true});
  }
  function catalogClosed() {
    document.querySelector('.builder-canvas-wrap').scrollIntoView({block:'nearest', behavior:'instant'});
    el('builderSteamBackgrounds').focus({preventScroll:true});
  }
  el('builderCatalog').addEventListener('keydown', event => {
    if (event.key === 'Escape') { event.preventDefault(); el('builderCatalogClose').click(); }
  });
  window.WorkspaceEditor = {icon, builderState, builderReady, language, catalogOpened, catalogClosed};
  function jump(name) {
    const target = name === 'edit' ? el('builderInspector') : document.querySelector(name === 'add' ? '.builder-tools' : '.builder-canvas-wrap');
    target.scrollIntoView({block:'start', behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'instant':'smooth'});
  }
  document.querySelectorAll('[data-editor-jump]').forEach(button => button.addEventListener('click', () => jump(button.dataset.editorJump)));
  window.addEventListener('sm:processchange', processState);
  window.addEventListener('sm:langchange', () => queueMicrotask(language));
  document.querySelectorAll('#nav [data-tab]').forEach(button => button.addEventListener('click', () => queueMicrotask(navigation)));
  // Bind navigation before the lazy Builder loads and supplies its own handlers.
  document.querySelectorAll('[data-open-tool]').forEach(button => button.addEventListener('click', () => {
    if (!window.ShowcaseBuilder) document.querySelector('#nav [data-tab="' + button.dataset.openTool + '"]')?.click();
    button.closest('.workspace-more')?.removeAttribute('open');
  }));
  el('drop').addEventListener('keydown', event => {
    if (event.target === el('drop') && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault(); el('fileInput').click();
    }
  });
  document.querySelectorAll('[data-editor-upload]').forEach(button => button.addEventListener('click', () => el('fileInput').click()));
  document.querySelectorAll('[data-editor-start]').forEach(button => button.addEventListener('click', () => {
    if (button.dataset.editorStart === 'steam') {
      el('builderSteamBackgrounds').click();
      el('builderCatalog').scrollIntoView({block:'nearest', behavior:'instant'});
      el('builderCatalogSearch').focus({preventScroll:true});
    } else document.querySelector('[data-add-layer="background"]').click();
  }));
  language();
})();
