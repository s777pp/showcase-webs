/* History snapshots contain only editor state. Media blobs live once in the browser draft. */
(function () {
  'use strict';
  window.createBuilderHistory = function (root, read, apply) {
    const t=window.WorkspaceCopy, copy=v=>JSON.parse(JSON.stringify(v));
    let history=[copy(read())],cursor=0,timer,saveTimer,pendingDraft=null,ready=false,revision=0,writing=false,failed=false;
    const cachedAssets=new Map();
    const toolbar=document.createElement('div');toolbar.className='builder-history';toolbar.setAttribute('data-no-translate','');
    function button(label,fn){const b=document.createElement('button');b.type='button';b.textContent=t(label);b.onclick=fn;toolbar.append(b);return b}
    const undo=button('undo',()=>move(-1)),redo=button('redo',()=>move(1));
    undo.title=t('undo')+' (Ctrl/⌘+Z)';redo.title=t('redo')+' (Ctrl/⌘+Shift+Z)';
    const note=document.createElement('span');note.className='builder-draft-status';note.setAttribute('role','status');toolbar.append(note);
    const help=document.createElement('p');help.textContent=t('localHelp');
    root.querySelector('.builder-stage-head').after(toolbar);
    // Help is initialized after the editor script.
    window.addEventListener('load',()=>window.WorkspaceHelp?.attach(help,toolbar),{once:true});
    const recovery=document.createElement('div');recovery.className='workspace-draft';recovery.hidden=true;recovery.setAttribute('data-no-translate','');toolbar.after(recovery);
    const message=document.createElement('span');message.textContent=t('draft');recovery.append(message);
    function recoveryButton(key,fn){const b=document.createElement('button');b.type='button';b.className='btn ghost';b.textContent=t(key);b.onclick=fn;recovery.append(b)}
    function paint(){undo.disabled=cursor===0;redo.disabled=cursor===history.length-1}
    function stateKey(v){return JSON.stringify([v.project,v.name,v.id])}
    function changed(){clearTimeout(timer);timer=setTimeout(commit,400);note.textContent=t('saving')}
    function commit(){clearTimeout(timer);timer=null;const next=copy(read());if(stateKey(next)===stateKey(history[cursor])){paint();return}history=history.slice(0,cursor+1);history.push(next);if(history.length>60)history.shift();cursor=history.length-1;revision++;paint();scheduleSave()}
    function move(delta){commit();const index=cursor+delta;if(index<0||index>=history.length)return;cursor=index;apply(copy(history[cursor]));revision++;paint();scheduleSave()}
    const dbPromise=new Promise((resolve,reject)=>{const req=indexedDB.open('showcase-builder-draft',1);req.onupgradeneeded=()=>req.result.createObjectStore('draft');req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error)});
    async function store(mode,value){const db=await dbPromise;return new Promise((resolve,reject)=>{const tx=db.transaction('draft',mode),s=tx.objectStore('draft');let req;if(mode==='readonly')req=s.get('current');else if(value===null)req=s.delete('current');else req=s.put(value,'current');tx.oncomplete=()=>resolve(req.result);tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error)})}
    function scheduleSave(){if(!ready||pendingDraft)return;clearTimeout(saveTimer);saveTimer=setTimeout(save,650)}
    async function save(){
      if(writing||!ready||pendingDraft)return;
      clearTimeout(saveTimer);saveTimer=null;writing=true;const rev=revision;note.textContent=t('saving');
      try{
        const value=copy(read()),assets={};let bytes=0;
        for(const layer of value.project.layers){
          if(!layer.src?.startsWith('blob:')&&!layer.src?.startsWith('/api/builder/assets/')&&!cachedAssets.has(layer.src))continue;
          if(!assets[layer.src]){let blob=cachedAssets.get(layer.src);if(!blob){const response=await fetch(layer.src);if(!response.ok)throw Error('media');blob=await response.blob();cachedAssets.set(layer.src,blob)}bytes+=blob.size;if(bytes>100*1024*1024)throw Error('size');assets[layer.src]=blob}
        }
        // One atomic IndexedDB write preserves the previous complete draft if storage is full.
        await store('readwrite',{version:1,state:value,assets,updated:Date.now()});
        failed=false;note.textContent=t('local');note.classList.remove('is-error');
      }catch(_){failed=true;note.textContent=t('draftError');note.classList.add('is-error')}
      finally{writing=false;if(rev!==revision)scheduleSave()}
    }
    recoveryButton('restore',()=>{
      const value=copy(pendingDraft.state);const replacements={};
      Object.entries(pendingDraft.assets||{}).forEach(([key,blob])=>{replacements[key]=URL.createObjectURL(blob)});
      value.project.layers.forEach(layer=>{if(replacements[layer.src])layer.src=replacements[layer.src]});
      // Restored local drafts are copies: never overwrite a different signed-in account's server project.
      value.id='';apply(value);pendingDraft=null;recovery.hidden=true;commit();scheduleSave();
    });
    recoveryButton('discard',async()=>{try{await store('readwrite',null);pendingDraft=null;recovery.hidden=true;note.textContent='';if(read().project.layers.length)scheduleSave()}catch(_){note.textContent=t('draftError')}});
    store('readonly').then(value=>{ready=true;if(value?.version===1&&Array.isArray(value.state?.project?.layers)&&value.state.project.layers.length){pendingDraft=value;recovery.hidden=false}else if(revision)scheduleSave()}).catch(()=>{ready=true;failed=true;note.textContent=t('draftError')});
    document.addEventListener('keydown',e=>{
      if(!root.closest('.tab')?.classList.contains('active')||e.target.closest('input,textarea,select,[contenteditable=true]'))return;
      if((e.ctrlKey||e.metaKey)&&!e.altKey&&(e.key.toLowerCase()==='z'||e.key.toLowerCase()==='y')){e.preventDefault();move(e.shiftKey||e.key.toLowerCase()==='y'?1:-1)}
    });
    root.addEventListener('input',changed);root.addEventListener('change',()=>queueMicrotask(commit));
    document.addEventListener('visibilitychange',()=>{if(document.hidden){commit();if(revision)save()}});
    window.addEventListener('beforeunload',e=>{commit();if(failed||writing||timer||saveTimer){e.preventDefault();e.returnValue=''}});
    root.addEventListener('click',()=>queueMicrotask(commit));
    document.getElementById('tab-projects')?.addEventListener('click',()=>queueMicrotask(commit));
    paint();return {changed,commit,remember:(url,file)=>cachedAssets.set(url,file)};
  };
})();
