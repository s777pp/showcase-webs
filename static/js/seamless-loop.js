(function(){
  'use strict';
  const $=id=>document.getElementById(id), tool=$('tab-loop');
  if(!tool)return;
  const text={
    en:{kicker:'MOTION / SEAM',heading:'Seamless loop',copy:'Turn a short GIF or video into an animation whose ending flows back into its beginning.',proTitle:'Pro only',proBody:'Activate Pro to create seamless animations.',dropTitle:'Choose an animation',dropHint:'GIF, MP4, WebM or AVI · best with 2–4 seconds',modeLabel:'Loop method',modeBlend:'Smooth transition',modePingpong:'Forward and backward',blendLabel:'Transition length',formatLabel:'Result format',fpsLabel:'Frame rate',run:'Create loop',emptyKicker:'END → BEGINNING',emptyTitle:'Your seamless animation will appear here',emptyBody:'The original is not changed. Check the transition, then download the result.',ready:'Loop ready',download:'Download result',toProcess:'Continue in Process',processHint:'Download the result first, then add it in Process for Steam slicing.',pick:'Choose a GIF or video',upload:'Uploading…',wait:'Building the transition: ',done:'Done. Play it several times and check the seam.',failed:'Could not create the loop.'},
    ru:{kicker:'ДВИЖЕНИЕ / СТЫК',heading:'Бесшовный цикл',copy:'Преврати короткую GIF или видео в анимацию, где конец плавно возвращается к началу.',proTitle:'Только для Pro',proBody:'Активируй Pro, чтобы создавать бесшовные анимации.',dropTitle:'Выбрать анимацию',dropHint:'GIF, MP4, WebM или AVI · лучше всего 2–4 секунды',modeLabel:'Способ зацикливания',modeBlend:'Плавный переход',modePingpong:'Вперёд и обратно',blendLabel:'Длина перехода',formatLabel:'Формат результата',fpsLabel:'Частота кадров',run:'Создать цикл',emptyKicker:'КОНЕЦ → НАЧАЛО',emptyTitle:'Здесь появится бесшовная анимация',emptyBody:'Исходник не изменяется. Проверь переход и скачай готовый файл.',ready:'Цикл готов',download:'Скачать результат',toProcess:'Перейти в Обработку',processHint:'Сначала скачай результат, затем добавь его в «Обработку» для нарезки под Steam.',pick:'Выбери GIF или видео',upload:'Загружаем файл…',wait:'Собираем переход: ',done:'Готово. Просмотри несколько повторов и проверь место стыка.',failed:'Не удалось создать цикл.'}
  };
  const words=()=>{try{return SMLang.isRu()?text.ru:text.en}catch(_){return text.en}};
  function localize(){const w=words();tool.querySelectorAll('[data-loop]').forEach(node=>{const key=node.dataset.loop;if(w[key])node.textContent=w[key]})}
  localize();window.addEventListener('sm:languagechange',localize);document.addEventListener('sm:languagechange',localize);
  const input=$('loopFile'),drop=$('loopDrop'),run=$('loopRun'),status=$('loopStatus'),progress=$('loopProgress'),mode=$('loopMode'),lock=$('loopLock'),panel=$('loopPanel');let selected=null;
  const isPro=()=>{const b=$('planBadge'),v=(b?.textContent||'').toLowerCase();return v==='pro'||v==='trial'||!!b?.classList.contains('pro')};
  function syncLock(){const ok=isPro();lock.hidden=ok;panel.hidden=!ok}
  setTimeout(syncLock,350);setInterval(syncLock,4000);
  function choose(file){selected=file||null;$('loopFileName').textContent=selected?selected.name:'';run.disabled=!selected}
  drop.addEventListener('click',()=>input.click());input.addEventListener('change',()=>choose(input.files?.[0]));
  ['dragenter','dragover'].forEach(type=>drop.addEventListener(type,e=>{e.preventDefault();drop.classList.add('over')}));
  ['dragleave','drop'].forEach(type=>drop.addEventListener(type,e=>{e.preventDefault();drop.classList.remove('over');if(type==='drop')choose(e.dataTransfer?.files?.[0])}));
  mode.addEventListener('change',()=>{$('loopBlendField').hidden=mode.value!=='blend'});
  $('loopToProcess').addEventListener('click',()=>document.querySelector('#nav button[data-tab="process"]')?.click());
  const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
  async function json(response){const data=await response.json().catch(()=>({}));if(!response.ok||!data.ok){const error=new Error(data.msg||words().failed);error.code=data.code;throw error}return data}
  run.addEventListener('click',async()=>{
    if(!selected){status.textContent=words().pick;return}run.disabled=true;tool.querySelector('.loop-tool').dataset.busy='1';status.className='status';status.textContent=words().upload;progress.firstElementChild.style.width='3%';$('loopResult').hidden=true;$('loopEmpty').hidden=false;
    try{
      const form=new FormData();form.append('file',selected);form.append('mode',mode.value);form.append('output_format',$('loopFormat').value);form.append('fps',$('loopFps').value);form.append('blend',$('loopBlend').value);
      const queued=await json(await fetch('/api/loop/start',{method:'POST',body:form,credentials:'include'}));let result,deadline=Date.now()+20*60*1000;
      while(Date.now()<deadline){await sleep(1400);result=await json(await fetch('/api/loop/status/'+encodeURIComponent(queued.job_id),{credentials:'include',cache:'no-store'}));const pct=Math.max(0,Math.min(100,Number(result.pct)||0));progress.firstElementChild.style.width=pct+'%';status.textContent=words().wait+pct+'%';if(result.status==='done')break;if(result.status==='error')throw Error(result.error||words().failed)}
      if(!result||result.status!=='done')throw Error(words().failed);
      const isGif=(result.media_type||'').includes('gif'),video=$('loopVideo'),img=$('loopGif');video.hidden=isGif;img.hidden=!isGif;if(isGif){img.src=result.preview_url}else{video.src=result.preview_url;video.load();video.play().catch(()=>{})}$('loopDownload').href=result.download_url;$('loopEmpty').hidden=true;$('loopResult').hidden=false;status.className='status ok';status.textContent=words().done;
    }catch(error){status.className='status err';status.textContent=error.message||words().failed;if(error.code==='pro')syncLock()}finally{run.disabled=!selected;delete tool.querySelector('.loop-tool').dataset.busy}
  });
})();
