(function () {
  'use strict';
  let active, dismissed, count = 0;
  const text = window.WorkspaceCopy;
  function close() { if (!active) return; active.unpin?.(); active.popup.hidden = true; active.button.setAttribute('aria-expanded','false'); active = null; }
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
      popup.hidden = false; button.setAttribute('aria-expanded','true'); active = {button,popup,isPinned:()=>pinned,unpin:()=>{pinned=false}};
      const r = button.getBoundingClientRect();
      // Long explanations must scroll on one side of their trigger rather
      // than covering it (which can make hover/click repeatedly reopen).
      const below = Math.max(0, innerHeight - r.bottom - 20);
      const above = Math.max(0, r.top - 20);
      const placeBelow = below >= Math.min(popup.scrollHeight, 320) || below >= above;
      popup.style.maxHeight = Math.max(40, placeBelow ? below : above) + 'px';
      popup.style.overflowY = 'auto';
      popup.style.left = Math.max(12,Math.min(r.left,innerWidth-popup.offsetWidth-12))+'px';
      popup.style.top = Math.max(12, placeBelow ? r.bottom+8 : r.top-popup.offsetHeight-8)+'px';
    }
    let timer, pinned = false;
    button.addEventListener('pointerenter', e => {if(e.pointerType==='mouse'&&dismissed!==button)open()});
    button.addEventListener('focus',() => {if(dismissed!==button)open()});
    button.addEventListener('click',event => {event.preventDefault();if(active?.button===button&&pinned){pinned=false;close();return}pinned=true;dismissed=null;open()});
    function later(){if(pinned)return;clearTimeout(timer);timer=setTimeout(()=>{if(!pinned&&!popup.matches(':hover')&&!button.matches(':hover')&&document.activeElement!==button&&active?.button===button)close()},160)}
    button.addEventListener('pointerleave',()=>{if(dismissed===button)dismissed=null;later()}); button.addEventListener('blur',()=>{if(dismissed===button)dismissed=null;later()}); popup.addEventListener('pointerleave',later); popup.addEventListener('pointerenter',()=>clearTimeout(timer));
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
  document.addEventListener('keydown',e=>{if(e.key==='Escape'){dismissed=active?.button;close()}},true);
  window.addEventListener('resize',close); document.addEventListener('scroll',e=>{if(active&&!active.isPinned?.()&&!active.popup.contains(e.target))close()},true);
})();
