// gallery.html L386-845
(function () {
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));

  /* ---- i18n ---- */
  const GDICT = {
    en: {
      gal_carousel: 'Carousel',
      gal_feed: 'Feed',
      gal_loading: 'Loading the gallery…',
      gal_hint: 'Click a card · scroll or drag · hover to pause',
      gal_ph_comment: 'Write a comment…',
      gal_send: 'Send',
      c_loading: 'Loading…',
      c_empty: 'No comments yet',
      c_fail: 'Could not load comments',
      c_need_login: 'Sign in to leave a comment',
      c_send_fail: 'Could not send the comment',
      gal_fail: 'Could not load the gallery',
      untitled: 'Untitled', anonymous: 'anonymous', by: 'by', showcase: 'Showcase'
    },
    ru: {
      gal_carousel: 'Карусель',
      gal_feed: 'Лента',
      gal_loading: 'Загрузка галереи…',
      gal_hint: 'Кликни по карточке · колёсико или перетаскивание · пауза при наведении',
      gal_ph_comment: 'Написать комментарий…',
      gal_send: 'Отправить',
      c_loading: 'Загрузка…',
      c_empty: 'Пока нет комментариев',
      c_fail: 'Не удалось загрузить',
      c_need_login: 'Войдите, чтобы комментировать',
      c_send_fail: 'Ошибка отправки',
      gal_fail: 'Не удалось загрузить галерею',
      untitled: 'Без названия', anonymous: 'аноним', by: 'автор:', showcase: 'Витрина'
    }
  };
  function gLang() { try { return window.SMLang ? SMLang.get() : 'en'; } catch (e) { return 'en'; } }
  function gT(k) { const p = GDICT[gLang()] || GDICT.en; return p[k] != null ? p[k] : (GDICT.en[k] || ''); }
  function applyGalleryLang() {
    const pack = GDICT[gLang()] || GDICT.en;
    if (window.SMLang && SMLang.apply) { SMLang.apply(pack); return; }
    $$('[data-i]').forEach((el) => { const v = pack[el.getAttribute('data-i')]; if (v != null) el.textContent = v; });
    $$('[data-i-ph]').forEach((el) => { const v = pack[el.getAttribute('data-i-ph')]; if (v != null) el.placeholder = v; });
  }
  applyGalleryLang();
  window.addEventListener('sm:langchange', () => {
    applyGalleryLang();
    if (items.length) { buildCarousel(); buildFeed(); }
  });

  // mobile menu
  const menuBtn = $('#logoMenuBtn');
  const mobileMenu = $('#mobileMenu');
  if (menuBtn && mobileMenu) {
    menuBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      mobileMenu.classList.toggle('open');
    });
    document.addEventListener('click', () => mobileMenu.classList.remove('open'));
  }

  // header transparency on scroll (feed mode)
  const header = $('#siteHeader');
  window.addEventListener('scroll', () => {
    header.classList.toggle('scrolled', window.scrollY > 20);
  }, { passive: true });

  // view toggle
  let viewMode = 'carousel';
  $$('#viewBar button').forEach((b) => {
    b.addEventListener('click', () => {
      $$('#viewBar button').forEach((x) => x.classList.remove('active'));
      b.classList.add('active');
      viewMode = b.dataset.view;
      document.body.classList.toggle('carousel-mode', viewMode === 'carousel');
      document.body.classList.toggle('feed-mode', viewMode === 'feed');
      if (viewMode === 'carousel') startLoop();
      else stopLoop();
    });
  });

  let items = [];
  let cardCount = 0;
  let cards = [];
  let metrics = { cardW: 280, cardH: 380 };
  let progress = 0;
  let paused = false;
  let dragging = false;
  let dragStartX = 0;
  let dragStartProgress = 0;
  const mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
  let raf = 0;
  let currentItem = null;

  const stage = $('#stage');
  const stageInner = $('#stageInner');
  const feedGrid = $('#feedGrid');
  const loadingEl = $('#loading');

  function escapeHtml(s) {
    return String(s || '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function resize() {
    const w = window.innerWidth;
    const h = window.innerHeight;
    let cardW = Math.round(Math.min(300, Math.max(160, w * 0.18)));
    const hf = Math.min(1, Math.max(0.7, h / 900));
    cardW = Math.round(cardW * hf);
    metrics = { cardW, cardH: Math.round(cardW * 1.35) };
    const root = stageInner.querySelector('.card-root');
    if (root) {
      root.style.width = metrics.cardW + 'px';
      root.style.height = metrics.cardH + 'px';
    }
    cards.forEach((c) => {
      if (!c) return;
      c.style.width = metrics.cardW + 'px';
      c.style.height = metrics.cardH + 'px';
    });
  }

  function buildCarousel() {
    stageInner.innerHTML = '';
    cards = [];
    const root = document.createElement('div');
    root.className = 'card-root';
    root.style.width = metrics.cardW + 'px';
    root.style.height = metrics.cardH + 'px';
    root.style.transformStyle = 'preserve-3d';

    const thickness = [-1.3, -0.65, 0, 0.65, 1.3];

    items.forEach((item, i) => {
      const card = document.createElement('div');
      card.className = 'card';
      card.dataset.idx = i;
      card.style.width = metrics.cardW + 'px';
      card.style.height = metrics.cardH + 'px';
      card.style.transformStyle = 'preserve-3d';

      thickness.forEach((zOff, li) => {
        const isFront = li === thickness.length - 1;
        const isBack = li === 0;
        const layer = document.createElement('div');
        layer.className = 'layer';

        if (!isFront && !isBack) {
          layer.classList.add('layer-mid');
          layer.style.transform = `translateZ(${zOff}px)`;
        } else if (isFront) {
          layer.classList.add('layer-face');
          layer.style.transform = `translateZ(${zOff}px)`;
          layer.innerHTML = `
            <img src="${item.url}" alt="${escapeHtml(item.title)}" draggable="false" loading="lazy"/>
            <div class="face-grad"></div>
            <div class="face-logo">S</div>
            <div class="face-badge">${escapeHtml(item.mode || gT('showcase'))}</div>
            <div class="face-meta">
              <div class="face-title">${escapeHtml(item.title || gT('untitled'))}</div>
              <div class="face-author">${escapeHtml(gT('by'))} ${escapeHtml(item.author || gT('anonymous'))}</div>
            </div>`;
        } else {
          layer.classList.add('layer-face');
          layer.style.transform = `translateZ(${zOff}px) rotateY(180deg)`;
          layer.innerHTML = `
            <div class="back-blur"><img src="${item.url}" alt="" draggable="false"/></div>
            <div class="back-dim"></div>
            <div class="back-stripe"></div>
            <div class="back-info">
              <div class="face-title">${escapeHtml(item.title || gT('untitled'))}</div>
              <div class="face-author">@${escapeHtml(item.author || gT('anonymous'))}</div>
              <div class="back-tags">
                <span>${escapeHtml(item.mode || gT('showcase'))}</span>
                <span>Steam</span>
                ${item.likes ? `<span>♥ ${item.likes}</span>` : ''}
              </div>
            </div>`;
        }
        card.appendChild(layer);
      });

      // Invisible hit layer — 3D cards with pointer-events:none children don't receive clicks otherwise
      const hit = document.createElement('div');
      hit.className = 'card-hit';
      hit.style.cssText = 'position:absolute;inset:0;z-index:20;border-radius:16px;cursor:pointer;pointer-events:auto;background:transparent;transform:translateZ(2px);';
      card.appendChild(hit);

      hit.addEventListener('mouseenter', () => { paused = true; });
      hit.addEventListener('mouseleave', () => { if (!dragging) paused = false; });
      hit.addEventListener('pointerup', (e) => {
        if (e.button != null && e.button !== 0) return;
        const moved = Math.hypot((e.clientX || 0) - dragStartX, (e.clientY || 0) - (window._dragStartY || 0));
        if (moved > 10) return;
        e.preventDefault();
        e.stopPropagation();
        openModal(item);
      });
      // also click as fallback
      hit.addEventListener('click', (e) => {
        const moved = Math.hypot((e.clientX || 0) - dragStartX, (e.clientY || 0) - (window._dragStartY || 0));
        if (moved > 10) return;
        e.preventDefault();
        e.stopPropagation();
        openModal(item);
      });

      root.appendChild(card);
      cards.push(card);
    });

    stageInner.appendChild(root);
  }

  function buildFeed() {
    feedGrid.innerHTML = items.map((item) => `
      <article class="feed-card" data-id="${item.id}">
        <img src="${item.url}" alt="${escapeHtml(item.title)}" loading="lazy"/>
        <div class="info">
          <div class="t">${escapeHtml(item.title || gT('untitled'))}</div>
          <div class="a">${escapeHtml(gT('by'))} ${escapeHtml(item.author || gT('anonymous'))}</div>
          <div class="stats">
            <span>♥ ${item.likes || 0}</span>
            <span>${escapeHtml(item.mode || '')}</span>
          </div>
        </div>
      </article>
    `).join('');
    $$('.feed-card', feedGrid).forEach((el) => {
      el.addEventListener('click', () => {
        const it = items.find((x) => String(x.id) === el.dataset.id);
        if (it) openModal(it);
      });
    });
  }

  // HORIZONTAL cylinder math
  function renderLoop() {
    if (!paused && !dragging && viewMode === 'carousel') {
      progress += 0.0014;
    }

    const w = window.innerWidth;
    const { cardW } = metrics;
    const roundedIndex = Math.round(progress);
    const diffFromRound = progress - roundedIndex;
    const easedDiff = Math.sign(diffFromRound) * Math.pow(Math.abs(diffFromRound) * 2, 4.0) / 2;
    const virtualActiveIndex = roundedIndex + easedDiff;
    const halfCount = Math.max(cardCount / 2, 1);
    const gap = 36;
    const peekAmount = -40;
    const D = 1400;

    for (let i = 0; i < cardCount; i++) {
      const card = cards[i];
      if (!card) continue;

      let offset = i - virtualActiveIndex;
      while (offset > halfCount) offset -= cardCount;
      while (offset < -halfCount) offset += cardCount;

      const absOffset = Math.abs(offset);
      const sign = Math.sign(offset) || 1;

      if (absOffset > 3) {
        card.style.visibility = 'hidden';
        continue;
      }
      card.style.visibility = 'visible';

      let x = 0, z = 0, rot = 0;

      if (absOffset <= 1) {
        const t = absOffset;
        const e = t * t * (3 - 2 * t);
        x = sign * (e * (cardW + gap));
        z = 380 + e * (200 - 380);
        rot = e * 55; // yaw for horizontal feel
      } else if (absOffset <= 2) {
        const t = absOffset - 1;
        const e = t * t * (3 - 2 * t);
        const xStart = cardW + gap, zStart = 200, rotStart = 55;
        const zEnd = -40, rotEnd = 75;
        const sEnd = D / (D - zEnd);
        const xEnd = (w / 2 - peekAmount) / sEnd - cardW / 2;
        x = sign * (xStart + e * (xEnd - xStart));
        z = zStart + e * (zEnd - zStart);
        rot = rotStart + e * (rotEnd - rotStart);
      } else {
        const t = Math.min(absOffset - 2, 1);
        const e = t * t * (3 - 2 * t);
        const zStart = -40, rotStart = 75, zEnd3 = -220, rotEnd3 = 90;
        const s2 = D / (D - zStart);
        const x2 = (w / 2 - peekAmount) / s2 - cardW / 2;
        const s3 = D / (D - zEnd3);
        const x3 = (w / 2 + 80) / s3 + cardW / 2;
        x = sign * (x2 + e * (x3 - x2));
        z = zStart + e * (zEnd3 - zStart);
        rot = rotStart + e * (rotEnd3 - rotStart);
      }

      card.style.zIndex = String(Math.round(z));
      card.style.transform =
        `translateX(${x.toFixed(2)}px) translateZ(${z.toFixed(2)}px) ` +
        `rotateY(${(-sign * rot).toFixed(2)}deg)`;
    }

    raf = requestAnimationFrame(renderLoop);
  }

  function startLoop() {
    if (!raf && viewMode === 'carousel' && cardCount) {
      raf = requestAnimationFrame(renderLoop);
    }
  }
  function stopLoop() {
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
  }


  // wheel → horizontal progress
  stage.addEventListener('wheel', (e) => {
    if (viewMode !== 'carousel') return;
    e.preventDefault();
    progress += e.deltaY * 0.0018 + e.deltaX * 0.0018;
  }, { passive: false });

  // drag
  let dragMoved = false;
  window._dragStartY = 0;
  stage.addEventListener('pointerdown', (e) => {
    if (viewMode !== 'carousel') return;
    dragging = true;
    dragMoved = false;
    paused = true;
    dragStartX = e.clientX;
    window._dragStartY = e.clientY;
    dragStartProgress = progress;
    // do NOT capture pointer immediately — otherwise card click never fires
  });
  stage.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    const dx = e.clientX - dragStartX;
    const dy = e.clientY - (window._dragStartY || 0);
    if (Math.hypot(dx, dy) > 6) {
      dragMoved = true;
      try { stage.setPointerCapture(e.pointerId); } catch (_) {}
    }
    progress = dragStartProgress - dx * 0.0045;
  });
  stage.addEventListener('pointerup', () => {
    dragging = false;
    paused = false;
  });
  stage.addEventListener('pointercancel', () => {
    dragging = false;
    paused = false;
  });

  window.addEventListener('resize', resize);

  // ===== Modal =====
  const modalBg = $('#modalBg');
  function openModal(item) {
    currentItem = item;
    $('#mImg').src = item.url;
    $('#mTitle').textContent = item.title || gT('untitled');
    $('#mMode').textContent = item.mode || gT('showcase');
    $('#mLikes').textContent = item.likes || 0;
    $('#mLike').classList.toggle('liked', !!item.liked);

    const author = item.author || gT('anonymous');
    const profileUrl = item.profile_url || (item.username ? '/profile/' + encodeURIComponent(item.username) : '#');
    $('#mAuthor').textContent = author;
    $('#mAuthor').href = profileUrl;
    $('#mSub').textContent = item.username ? '@' + item.username : '';
    const av = $('#mAv');
    av.href = profileUrl;
    if (item.avatar_url) {
      av.innerHTML = `<img src="${item.avatar_url}" alt=""/>`;
    } else {
      av.textContent = (author[0] || '?').toUpperCase();
    }

    loadComments(item.id);
    modalBg.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
  function closeModal() {
    modalBg.classList.remove('open');
    document.body.style.overflow = '';
    currentItem = null;
  }
  $('#mClose').addEventListener('click', closeModal);
  modalBg.addEventListener('click', (e) => { if (e.target === modalBg) closeModal(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });

  async function loadComments(id) {
    const box = $('#mComments');
    box.innerHTML = '<div class="comment-empty">' + escapeHtml(gT('c_loading')) + '</div>';
    try {
      const r = await fetch(`/api/gallery/${id}/comments`, { credentials: 'include' });
      const d = await r.json();
      const list = d.comments || d.items || [];
      if (!list.length) {
        box.innerHTML = '<div class="comment-empty">' + escapeHtml(gT('c_empty')) + '</div>';
        return;
      }
      box.innerHTML = list.map((c) => `
        <div class="comment">
          <div class="c-author">${escapeHtml(c.author || c.display_name || gT('anonymous'))}</div>
          <div class="c-text">${escapeHtml(c.text || c.body || '')}</div>
        </div>
      `).join('');
    } catch {
      box.innerHTML = '<div class="comment-empty">' + escapeHtml(gT('c_fail')) + '</div>';
    }
  }

  $('#mLike').addEventListener('click', async () => {
    if (!currentItem) return;
    try {
      const r = await fetch(`/api/gallery/${currentItem.id}/like`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });
      const d = await r.json();
      if (d.ok || d.likes != null) {
        currentItem.likes = d.likes != null ? d.likes : (currentItem.likes || 0) + (d.liked ? 1 : -1);
        currentItem.liked = !!d.liked;
        $('#mLikes').textContent = currentItem.likes;
        $('#mLike').classList.toggle('liked', currentItem.liked);
      }
    } catch {}
  });

  $('#mCommentSend').addEventListener('click', async () => {
    if (!currentItem) return;
    const input = $('#mCommentInput');
    const text = (input.value || '').trim();
    if (!text) return;
    try {
      const r = await fetch(`/api/gallery/${currentItem.id}/comments`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      const d = await r.json();
      if (d.ok !== false) {
        input.value = '';
        loadComments(currentItem.id);
      } else {
        alert(d.msg || gT('c_need_login'));
      }
    } catch {
      alert(gT('c_send_fail'));
    }
  });

  async function load() {
    try {
      const r = await fetch('/api/gallery/list?status=approved&limit=40', { credentials: 'include' });
      const d = await r.json();
      const list = d.items || d.gallery || [];
      items = list.map((it) => ({
        id: it.id,
        title: it.title || gT('untitled'),
        author: it.author || it.username || gT('anonymous'),
        username: it.username || '',
        profile_url: it.profile_url || (it.username ? '/profile/' + encodeURIComponent(it.username) : '#'),
        avatar_url: it.avatar_url || '',
        mode: it.mode || gT('showcase'),
        url: it.url || (it.id ? '/api/gallery/image/' + it.id : ''),
        likes: it.likes || 0,
        liked: !!it.liked,
      })).filter((x) => x.url);

      if (!items.length) {
        items = [
          { id: 1, title: 'Neon Dreams', author: 'n1t1337', username: 'n1t1337', mode: 'Workshop', url: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&q=80', likes: 12, profile_url: '#' },
          { id: 2, title: 'Cherry Soft', author: 'momo', username: 'momo', mode: 'Featured', url: 'https://images.unsplash.com/photo-1579783902614-a3fb3927b6a5?w=800&q=80', likes: 8, profile_url: '#' },
          { id: 3, title: 'Cyber Alley', author: 'void', username: 'void', mode: 'Workshop', url: 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800&q=80', likes: 21, profile_url: '#' },
          { id: 4, title: 'Soft Light', author: 'pixel', username: 'pixel', mode: 'Artwork Split', url: 'https://images.unsplash.com/photo-1614850523459-c2f4c699c52e?w=800&q=80', likes: 5, profile_url: '#' },
          { id: 5, title: 'Rainy Night', author: 'frame', username: 'frame', mode: 'Workshop', url: 'https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=800&q=80', likes: 14, profile_url: '#' },
        ];
      }

      cardCount = items.length;
      loadingEl.style.display = 'none';
      resize();
      buildCarousel();
      buildFeed();
      startLoop();
    } catch (e) {
      console.error(e);
      loadingEl.innerHTML = '<div>' + escapeHtml(gT('gal_fail')) + '</div>';
    }
  }

  load();
})();
