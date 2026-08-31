(() => {
  const root = document.documentElement;
  const section = document.querySelector(".cinema-scroll");
  const stage = document.querySelector(".stage");
  if (!section || !stage) return;

  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  let raf = 0;
  let targetScroll = 0;
  let smoothScroll = 0;
  let targetMX = 0, targetMY = 0;
  let mx = 0, my = 0;
  let initialized = false;

  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const smoothstep = (a, b, v) => {
    const x = clamp((v - a) / (b - a));
    return x * x * (3 - 2 * x);
  };
  const lerp = (a, b, t) => a + (b - a) * t;

  const getScrollDistance = () => {
    const r = section.getBoundingClientRect();
    return clamp(-r.top, 0, Math.max(0, section.offsetHeight - window.innerHeight));
  };

  const setVar = (name, value) => root.style.setProperty(name, value);

  function update() {
    raf = 0;
    targetScroll = getScrollDistance();

    if (reduce.matches || !initialized) {
      smoothScroll = targetScroll;
      initialized = true;
    } else {
      smoothScroll = lerp(smoothScroll, targetScroll, 0.12);
      if (Math.abs(smoothScroll - targetScroll) < 0.05) smoothScroll = targetScroll;
    }

    if (reduce.matches) {
      mx = my = targetMX = targetMY = 0;
    } else {
      mx = lerp(mx, targetMX, 0.11);
      my = lerp(my, targetMY, 0.11);
    }

    const p = clamp(smoothScroll / Math.max(1, section.offsetHeight - window.innerHeight));
    const heroOut = smoothstep(0.03, 0.16, smoothScroll / 1000);

    // Scene 1: hero -> tools
    const toolsT = smoothstep(650, 1500, smoothScroll);
    const toolsOut = smoothstep(1650, 2250, smoothScroll);
    const toolsOpacity = toolsT * (1 - toolsOut);

    // Scene 2: profile
    const profileIn = smoothstep(1950, 2750, smoothScroll);
    const profileOut = smoothstep(2950, 3500, smoothScroll);
    const profileOpacity = profileIn * (1 - profileOut);

    // Scene 3: gallery
    const galleryIn = smoothstep(3300, 4100, smoothScroll);
    const galleryOut = smoothstep(4300, 4850, smoothScroll);
    const galleryOpacity = galleryIn * (1 - galleryOut);

    // Scene 4: CTA
    const ctaIn = smoothstep(4650, 5000, smoothScroll);
    const ctaOpacity = ctaIn;

    setVar("--progress", p.toFixed(4));
    setVar("--mx", reduce.matches ? "0" : mx.toFixed(4));
    setVar("--my", reduce.matches ? "0" : my.toFixed(4));

    setVar("--hero-y", `${-heroOut * 180}`);
    setVar("--hero-scale", `${1 - heroOut * .09}`);
    setVar("--hero-opacity", `${1 - heroOut}`);

    setVar("--tools-opacity", toolsOpacity);
    setVar("--tools-x", `${(1 - toolsT) * 100 - toolsOut * 70}px`);
    setVar("--scene-opacity", 0);
    setVar("--scene-y", "60px");

    const toolScene = document.querySelector(".scene-tools");
    const profileScene = document.querySelector(".scene-profile");
    const galleryScene = document.querySelector(".scene-gallery");
    const ctaScene = document.querySelector(".scene-cta");

    if (toolScene) {
      toolScene.style.setProperty("--scene-opacity", toolsOpacity);
      toolScene.style.setProperty("--scene-y", `${(1-toolsT)*60 - toolsOut*50}px`);
    }
    if (profileScene) {
      profileScene.style.setProperty("--scene-opacity", profileOpacity);
      profileScene.style.setProperty("--scene-y", `${(1-profileIn)*70 - profileOut*55}px`);
      profileScene.style.setProperty("--profile-scale", `${.91 + profileIn*.09 - profileOut*.04}`);
      profileScene.style.setProperty("--profile-x", `${(1-profileIn)*80}px`);
    }
    if (galleryScene) {
      galleryScene.style.setProperty("--scene-opacity", galleryOpacity);
      galleryScene.style.setProperty("--scene-y", `${(1-galleryIn)*70 - galleryOut*55}px`);
    }
    if (ctaScene) {
      ctaScene.style.setProperty("--scene-opacity", ctaOpacity);
      ctaScene.style.setProperty("--scene-y", `${(1-ctaIn)*65}px`);
    }

    const floaters = [
      [".card-process", 1, -28, 1],
      [".card-character", 1, 42, 1],
      [".card-steam", 1, -44, 1],
      [".card-da", 1, 70, 1],
      [".card-converter", 1, 96, 1],
    ];
    for (const [sel, , extra, ] of floaters) {
      const el = document.querySelector(sel);
      if (!el) continue;
      const base = el.dataset.baseTransform || getComputedStyle(el).transform;
      el.dataset.baseTransform = base;
      const drift = (p * extra) + (smoothScroll > 500 ? -p * extra * .65 : 0);
      el.style.transform = `translate3d(calc(var(--mx) * 14px), calc(var(--my) * 10px + ${drift}px), 0) ${base === "none" ? "" : ""}`;
      el.style.opacity = String(Math.max(.08, 1 - heroOut * .82));
    }

    if (Math.abs(smoothScroll - targetScroll) > .05 || Math.abs(mx-targetMX) > .001 || Math.abs(my-targetMY) > .001) {
      requestTick();
    }
  }

  function requestTick() {
    if (raf) return;
    raf = requestAnimationFrame(update);
  }

  window.addEventListener("scroll", requestTick, { passive: true });
  window.addEventListener("resize", requestTick);
  window.addEventListener("pointermove", e => {
    if (reduce.matches) return;
    targetMX = e.clientX / Math.max(1, window.innerWidth) - .5;
    targetMY = e.clientY / Math.max(1, window.innerHeight) - .5;
    requestTick();
  }, { passive: true });

  reduce.addEventListener?.("change", requestTick);

  // Ensure internal navigation from the cinematic page feels instant.
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener("click", e => {
      const id = a.getAttribute("href");
      const el = document.querySelector(id);
      if (!el) return;
      e.preventDefault();
      window.scrollTo({ top: el.offsetTop, behavior: reduce.matches ? "auto" : "smooth" });
    });
  });

  requestTick();
})();
