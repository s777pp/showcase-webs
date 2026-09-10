(function () {
  'use strict';
  const t = window.WorkspaceCopy;
  let urls = [], generation = 0;
  function node(tag, text, className) {const n=document.createElement(tag);if(text)n.textContent=text;if(className)n.className=className;return n}
  window.ProcessResult = {
    async open(job, id, originals) {
      const token = ++generation;
      const download = job.download || '/api/process/download/'+encodeURIComponent(id);
      const integrated = job.readiness && window.SteamCheckResult?.open(job.readiness, download);
      const parent = integrated ? document.getElementById('steamCheckResults') : document.getElementById('tab-process');
      if (!parent) return false;
      document.getElementById('workspaceResult')?.remove(); urls.forEach(URL.revokeObjectURL); urls=[];
      const panel=node('section',null,'workspace-result');panel.id='workspaceResult';panel.setAttribute('data-no-translate','');
      const title=node('h2',t('result'));panel.append(title);
      const help=node('p',t('previewHelp'));window.WorkspaceHelp?.attach(help,title);
      const toolbar=node('div',null,'workspace-result__toolbar'), select=node('select'); select.setAttribute('aria-label',t('result'));
      const tabs=['result','original','compare'].map(key=>{const b=node('button',t(key));b.type='button';b.onclick=()=>{view=key;paint()};toolbar.append(b);return b});
      const zoom=node('button',t('fit'));zoom.type='button';let actual=false;zoom.onclick=()=>{actual=!actual;zoom.textContent=actual?'100%':t('fit');paint()};toolbar.append(zoom,select);
      panel.append(toolbar);const viewport=node('div',null,'workspace-result__viewport');panel.append(viewport);
      const files=node('div',null,'workspace-result__files');panel.append(files);
      if(!integrated){const a=node('a',t('download'),'btn');a.href=download;panel.append(a)}
      if(integrated)parent.prepend(panel);else parent.append(panel);
      let groups=[],view='result',previousGroup=null;viewport.textContent=t('loading');toolbar.hidden=true;
      function paint(){
        if(!groups.length)return;
        const group=groups[+select.value||0],stem=group.name.replace(/_(workshop|featured|split)$/,'');
        if(previousGroup&&previousGroup!==group)previousGroup.files.forEach(file=>{if(file.image){file.image.src='';file.image=null}});
        previousGroup=group;
        const matches=originals.filter(f=>f.name.replace(/\.[^.]+$/,'').slice(0,40)===stem);
        const source=matches.length===1?matches[0]:(originals.length===1?originals[0]:null);
        tabs[1].disabled=tabs[2].disabled=!source;
        if(!source)view='result';tabs.forEach((b,i)=>b.setAttribute('aria-pressed',String(['result','original','compare'][i]===view)));
        urls.forEach(URL.revokeObjectURL);urls=[];viewport.replaceChildren();files.replaceChildren();
        const columns=node('div',null,'workspace-result__columns'+(view==='compare'?' is-compare':''));viewport.append(columns);
        if(view!=='result'&&source){
          const figure=node('figure',null,'workspace-result__original');figure.append(node('figcaption',t('original')));
          const m=node(source.type.startsWith('video/')?'video':'img');const url=URL.createObjectURL(source);urls.push(url);m.src=url;m.alt=source.name;
          if(m.tagName==='VIDEO'){m.muted=true;m.loop=true;m.autoplay=true;m.controls=true;m.playsInline=true}
          figure.append(m);columns.append(figure);
        }
        if(view!=='original'){
          const figure=node('figure');figure.append(node('figcaption',t('result')));const parts=node('div',null,'workspace-result__parts');figure.append(parts);columns.append(figure);
          let widths=new Map();
          group.files.forEach(file=>{const cell=node('div',null,'workspace-result__part'),img=file.image||node('img');img.alt=file.name;if(!file.image){img.src=file.url;file.image=img}
            img.onload=()=>{widths.set(file.name,img.naturalWidth);cell.style.flex=img.naturalWidth+' 0 0px';if(file.detail)file.detail.textContent=' · '+img.naturalWidth+'×'+img.naturalHeight;if(actual&&widths.size===group.files.length){parts.style.width=Array.from(widths.values()).reduce((a,b)=>a+b,0)+'px'}};
            img.onerror=()=>{img.alt=t('previewError')};cell.append(img);parts.append(cell);
            if(img.complete&&img.naturalWidth)img.onload();
          });
        }
        group.files.forEach(file=>{const row=node('div'),link=node('a',file.name.split('/').pop());link.href=file.url;link.download=file.name.split('/').pop();file.detail=node('span');if(file.image?.naturalWidth)file.detail.textContent=' · '+file.image.naturalWidth+'×'+file.image.naturalHeight;row.append(link,document.createTextNode(' · '+(file.size/1024/1024).toFixed(2)+' MB'),file.detail);files.append(row)});
      }
      try{
        const response=await fetch('/api/process/preview/'+encodeURIComponent(id),{credentials:'include',cache:'no-store'}),data=await response.json();
        if(token!==generation)return true;
        if(!response.ok||!data.ok||!data.files.length)throw Error('preview');
        const grouped=new Map();data.files.forEach(file=>{const key=file.name.split('/').slice(0,-1).join('/');if(!grouped.has(key))grouped.set(key,[]);grouped.get(key).push(file)});
        groups=Array.from(grouped,([name,entries])=>({name,files:entries.sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true}))}));
        groups.forEach((g,i)=>{const o=node('option',g.name);o.value=i;select.append(o)});select.onchange=paint;select.hidden=groups.length<2;toolbar.hidden=false;paint();
      }catch(_){if(token===generation)viewport.textContent=t('previewError')}
      panel.scrollIntoView({behavior:'smooth',block:'start'});return true;
    }
  };
})();
