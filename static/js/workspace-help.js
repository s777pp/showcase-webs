(function () {
  'use strict';
  let active, count = 0;
  const text = window.WorkspaceCopy;
  function close() { if (!active) return; active.popup.hidden = true; active.button.setAttribute('aria-expanded','false'); active = null; }
  function attach(content, anchor) {
    if (!content || !anchor || content.dataset.smHelp) return;
    content.dataset.smHelp = '1';
    const wrap = document.createElement('span'), button = document.createElement('button'), popup = document.createElement('div');
    wrap.className = 'sm-help'; button.type = 'button'; button.className = 'sm-help__button'; button.textContent = '?';
    button.setAttribute('aria-label',text('help')); button.setAttribute('aria-expanded','false');
    popup.className = 'sm-help__popup'; popup.id = 'workspaceHelp' + (++count); popup.hidden = true; popup.setAttribute('role','tooltip');
    button.setAttribute('aria-controls',popup.id); button.setAttribute('aria-describedby',popup.id);
    if(anchor.matches('[data-i],[data-builder-i]')){
      const heading=document.createElement('div');heading.className='sm-help-heading';anchor.replaceWith(heading);heading.append(anchor,wrap);
    }else anchor.appendChild(wrap);
    wrap.appendChild(button); document.body.appendChild(popup); popup.appendChild(content);
    function open() {
      if (active?.button !== button) close();
      popup.hidden = false; button.setAttribute('aria-expanded','true'); active = {button,popup};
      const r = button.getBoundingClientRect();
      popup.style.left = Math.max(12,Math.min(r.left,innerWidth-popup.offsetWidth-12))+'px';
      popup.style.top = Math.max(12, r.bottom+8+popup.offsetHeight < innerHeight ? r.bottom+8 : r.top-popup.offsetHeight-8)+'px';
    }
    let timer;
    button.addEventListener('pointerenter', e => {if(e.pointerType==='mouse')open()});
    button.addEventListener('focus',open);
    button.addEventListener('click',() => {open()});
    function later(){clearTimeout(timer);timer=setTimeout(()=>{if(!popup.matches(':hover')&&!button.matches(':hover')&&document.activeElement!==button&&active?.button===button)close()},160)}
    button.addEventListener('pointerleave',later); button.addEventListener('blur',later); popup.addEventListener('pointerleave',later); popup.addEventListener('pointerenter',()=>clearTimeout(timer));
  }
  // Move only explanatory copy, preserving its existing translation binding.
  const choices = [
    ['[data-i="wm_hint"]','#wmPreviewCard h2'],
    ['[data-i="smart_compress_hint"]','.steam-opt-copy strong'],
    ['[data-i="outline_hint"]','.workshop-outline'],
    ['.compose-help','#tab-compose h2'],
    ['[data-i="compose_final_hint"]','#tab-compose .compose-preview-panel'],
    ['[data-i="convert_body"]','#tab-convert h2'],
    ['[data-i="hex_body"]','#tab-hex h2'],
    ['[data-builder-i="source-hint"]','#showcaseBuilder .builder-panel-title'],
    ['[data-builder-i="stage-help"]','.builder-stage-head']
  ];
  choices.forEach(([source,target])=>attach(document.querySelector(source),document.querySelector(target)));
  window.WorkspaceHelp = {attach};
  document.addEventListener('pointerdown',e=>{if(active&&!active.button.contains(e.target)&&!active.popup.contains(e.target))close()});
  document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});
  window.addEventListener('resize',close); document.addEventListener('scroll',e=>{if(active&&!active.popup.contains(e.target))close()},true);
})();
