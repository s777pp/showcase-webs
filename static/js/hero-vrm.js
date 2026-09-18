import {
  THREE,
  createVRMAnimationClip,
  GLTFLoader,
  VRMAnimationLoaderPlugin,
  VRMLoaderPlugin,
  VRMUtils,
} from '/static/vendor/vrm-runtime.module.js?v=20260915-saba2';

const host = document.getElementById('heroVrm');
const canvas = document.getElementById('heroVrmCanvas');
const sceneRoot = host?.closest('.creator-scene');
const studio = host?.closest('.hero-studio');
let heroLoadSettled = false;

const REACTION_SOUND_URL = '/static/audio/hero-cute-reaction.mp3?v=20260918-2';
const REACTION_SOUND_VOLUME = 0.05;
const REACTION_SOUND_COOLDOWN = 520;
const HEART_COLORS = ['#55d9ff', '#7be7ff', '#35b9f2', '#9e8cff'];
let reactionSound = null;
let lastReactionSoundAt = -Infinity;

function settleHeroLoad(status) {
  if (heroLoadSettled) return;
  heroLoadSettled = true;
  document.dispatchEvent(new CustomEvent('showcasemaker:hero-ready', { detail: { status } }));
}

const MOTION_PACK_URL = '/static/animations/saba/opensourceavatars.motionpack.json.gz?v=20260915-saba3';
const REACTION_MOTION_URL = '/static/animations/saba/Goodbye.vrma?v=20260915-saba2';
const DEFAULT_BLEND_SECONDS = 1.55;
const AMBIENT_MOTION_KEYS = new Set([
  'bored',
  'looking',
]);
const INTRO_MOTION_SEQUENCE = [
  'bored',
  'looking',
  'bored',
];
const MOTION_BEHAVIOR = {
  bored: { repeats: 6, holdSeconds: 32, timeScale: .96, blendSeconds: 1.9 },
  looking: { repeats: 4, holdSeconds: 30, timeScale: .96, blendSeconds: 1.85 },
};
const FACE_CUES = {
  relax: { relaxed: .12 },
  reaction: { happy: .85 },
  bored: { sad: .11, relaxed: .1 },
  looking: { relaxed: .18 },
};
const CONTROLLED_EXPRESSIONS = ['happy', 'joy', 'relaxed', 'surprised', 'angry', 'sad', 'sorrow', 'fun'];
const MICRO_MOODS = [
  {},
  { relaxed: .11 },
  { happy: .07 },
  { relaxed: .07, happy: .04 },
  { surprised: .035 },
];

if (host && canvas && sceneRoot && studio) {
  initHeroVrm().catch(() => {
    sceneRoot.classList.add('is-vrm-fallback');
    settleHeroLoad('fallback');
  });
} else {
  settleHeroLoad('unavailable');
}

async function initHeroVrm() {
  const saveData = Boolean(navigator.connection?.saveData);
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (saveData || !hasWebGL()) {
    sceneRoot.classList.add('is-vrm-fallback');
    settleHeroLoad('fallback');
    return;
  }

  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: 'high-performance' });
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, window.innerWidth < 820 ? 1.25 : 1.5));

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(25, 1, .01, 100);
  // Keep the avatar's original palette readable. The surrounding hero already
  // supplies plenty of cyan, so the character itself uses mostly neutral light.
  scene.add(new THREE.HemisphereLight(0xffffff, 0x2b303d, 1.45));
  const keyLight = new THREE.DirectionalLight(0xfff7ed, 2.35);
  keyLight.position.set(-1.7, 2.8, 3.5);
  scene.add(keyLight);
  const fillLight = new THREE.DirectionalLight(0xffffff, .72);
  fillLight.position.set(2.2, 1.5, 2.8);
  scene.add(fillLight);
  const rimLight = new THREE.DirectionalLight(0x8ea8ff, .38);
  rimLight.position.set(2.7, 1.7, -2.2);
  scene.add(rimLight);

  const loader = new GLTFLoader();
  loader.register(parser => new VRMLoaderPlugin(parser));
  loader.register(parser => new VRMAnimationLoaderPlugin(parser));
  // The pack is much smaller than the VRM and downloads in parallel, so the
  // requested Bored intro is ready when the character appears.
  const ambientPackPromise = reducedMotion
    ? Promise.resolve(null)
    : fetchAmbientMotionPack().catch(() => null);
  const gltf = await loadHeroModel(loader);
  const vrm = gltf.userData.vrm;
  if (!vrm) throw new Error('The model does not contain VRM data');

  VRMUtils.rotateVRM0(vrm);
  scene.add(vrm.scene);
  vrm.scene.traverse(object => {
    object.frustumCulled = false;
  });

  // Head and eyes are intentionally removed from imported body motions below.
  // This makes pointer tracking readable even while the body is moving.
  const head = vrm.humanoid?.getNormalizedBoneNode('head');
  const neck = vrm.humanoid?.getNormalizedBoneNode('neck');
  const chest = vrm.humanoid?.getNormalizedBoneNode('chest');
  const leftEye = vrm.humanoid?.getNormalizedBoneNode('leftEye');
  const rightEye = vrm.humanoid?.getNormalizedBoneNode('rightEye');
  const baseHead = head?.quaternion.clone();
  const baseNeck = neck?.quaternion.clone();
  const gazeBoneNames = new Set([head?.name, neck?.name, leftEye?.name, rightEye?.name].filter(Boolean));
  const mixer = new THREE.AnimationMixer(vrm.scene);
  const ambientPack = await ambientPackPromise;
  const packedAmbientMotions = ambientPack
    ? createAmbientMotionActions(ambientPack, mixer, vrm, gazeBoneNames)
    : [];
  const ambientMotions = packedAmbientMotions;
  let reactionMotion = null;
  let reactionMotionLoad = null;
  const faceState = createFaceState(vrm);
  let activeMotion = null;
  let activeMotionKey = 'relax';
  let nextMotionAt = 0;
  let ambientBag = buildAmbientBag(ambientMotions);

  function playMotion(
    action,
    loopMode,
    key = 'relax',
    timeScale = 1,
    blendSeconds = DEFAULT_BLEND_SECONDS,
  ) {
    if (!action || action === activeMotion) return;
    const previousMotion = activeMotion;
    action.reset();
    action.enabled = true;
    action.clampWhenFinished = loopMode === 'once';
    const loop = loopMode === 'pingpong'
      ? THREE.LoopPingPong
      : loopMode === 'repeat'
        ? THREE.LoopRepeat
        : THREE.LoopOnce;
    action.setLoop(loop, loopMode === 'once' ? 1 : Infinity);
    action.setEffectiveTimeScale(loopMode === 'pingpong' ? .82 : timeScale);
    action.setEffectiveWeight(1);
    action.play();
    if (previousMotion) previousMotion.crossFadeTo(action, blendSeconds, true);
    activeMotion = action;
    activeMotionKey = key;
    sceneRoot.dataset.heroMotion = key;
  }

  function playAmbient(now) {
    if (!ambientMotions.length) {
      applyIdlePose(vrm);
      nextMotionAt = 0;
      return;
    }
    if (!ambientBag.length) ambientBag = buildAmbientBag(ambientMotions, activeMotionKey);
    if (ambientBag[0]?.key === activeMotionKey) {
      const replacement = ambientBag.findIndex(entry => entry.key !== activeMotionKey);
      if (replacement > 0) [ambientBag[0], ambientBag[replacement]] = [ambientBag[replacement], ambientBag[0]];
    }
    const entry = ambientBag.shift();
    if (!entry) return;
    const timeScale = entry.timeScale || 1;
    const blendSeconds = entry.blendSeconds || DEFAULT_BLEND_SECONDS;
    playMotion(entry.action, 'repeat', entry.key, timeScale, blendSeconds);
    const holdSeconds = entry.holdSeconds || 30;
    nextMotionAt = now + Math.max(1800, (holdSeconds - blendSeconds) * 1000);
    setFaceCue(entry.key, now, holdSeconds * 1000);
  }

  mixer.addEventListener('finished', event => {
    if (event.action === activeMotion) playAmbient(performance.now());
  });

  if (!reducedMotion) {
    const requestedPreview = isLocalPreview()
      ? new URLSearchParams(window.location.search).get('heroMotion')
      : null;
    const introMotion = selectIntroMotion(ambientMotions, requestedPreview);
    if (introMotion) {
      const introIndex = ambientBag.indexOf(introMotion);
      if (introIndex >= 0) ambientBag.splice(introIndex, 1);
      ambientBag.unshift(introMotion);
      playAmbient(performance.now());
    } else {
      applyIdlePose(vrm);
    }
    mixer.update(0);
  } else {
    // The manual pose is also the fallback when animations are unavailable.
    applyIdlePose(vrm);
    vrm.update(0);
  }

  const bounds = new THREE.Box3().setFromObject(vrm.scene);
  const size = bounds.getSize(new THREE.Vector3());
  const center = bounds.getCenter(new THREE.Vector3());
  vrm.scene.position.x -= center.x;
  vrm.scene.position.y -= bounds.min.y;

  const lookTarget = new THREE.Object3D();
  scene.add(lookTarget);
  if (vrm.lookAt) vrm.lookAt.target = lookTarget;

  const pointer = new THREE.Vector2(0, 0);
  const smoothPointer = new THREE.Vector2(0, 0);
  let reactingUntil = 0;
  let nextBlink = performance.now() + randomBlinkDelay();
  let blinkStarted = 0;
  let winkStarted = 0;
  let nextWink = performance.now() + 14000 + Math.random() * 11000;
  let active = true;
  let disposed = false;
  let firstFrame = true;
  let frameId = 0;
  const clock = new THREE.Clock();

  function resize() {
    const rect = host.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    renderer.setSize(rect.width, rect.height, false);
    camera.aspect = rect.width / rect.height;
    // The canvas extends farther above the studio than before. These values
    // preserve the character's apparent scale and lower crop while giving
    // raised-head motions enough real render space at the top.
    const targetY = size.y * .687;
    const visibleHeight = size.y * .741;
    const distance = visibleHeight / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov * .5)));
    camera.position.set(0, targetY, distance);
    camera.lookAt(0, targetY, 0);
    camera.updateProjectionMatrix();
  }

  function setPointer(event) {
    const rect = canvas.getBoundingClientRect();
    const centerX = rect.left + rect.width * .5;
    const centerY = rect.top + rect.height * .32;
    const rangeX = event.clientX < centerX ? centerX : window.innerWidth - centerX;
    const rangeY = event.clientY < centerY ? centerY : window.innerHeight - centerY;
    pointer.x = THREE.MathUtils.clamp((event.clientX - centerX) / Math.max(rangeX, 1), -1, 1);
    pointer.y = THREE.MathUtils.clamp((centerY - event.clientY) / Math.max(rangeY, 1), -1, 1);
  }

  function resetPointer() {
    pointer.set(0, 0);
  }

  function react(event) {
    const now = performance.now();
    burstReactionHearts(event);
    if (reducedMotion) return;
    setFaceCue('reaction', now, 1800);
    reactingUntil = now + 1800;
    ensureReactionMotion().then(action => {
      if (action) playReaction(action, performance.now());
    });
  }

  function playReactionAudio() {
    playReactionSound(performance.now());
  }

  function playReaction(action, now) {
    const blendSeconds = 1.05;
    const reactionDuration = action.getClip().duration || 1.5;
    const reactionDurationMs = Math.max(1500, reactionDuration * 1000);
    reactingUntil = now + reactionDurationMs;
    setFaceCue('reaction', now, reactionDurationMs);
    if (action === activeMotion) {
      action.reset().play();
    } else {
      playMotion(action, 'once', 'goodbye', 1, blendSeconds);
    }
    nextMotionAt = now + Math.max(1300, (reactionDuration - blendSeconds) * 1000);
  }

  function ensureReactionMotion() {
    if (reactionMotion) return Promise.resolve(reactionMotion);
    if (!reactionMotionLoad) {
      reactionMotionLoad = loader.loadAsync(REACTION_MOTION_URL)
        .then(reactionGltf => {
          const reactionAnimation = reactionGltf?.userData?.vrmAnimations?.[0];
          reactionMotion = reactionAnimation
            ? createBodyMotionAction(reactionAnimation, mixer, vrm, gazeBoneNames, 'goodbye-body')
            : null;
          return reactionMotion;
        })
        .catch(() => null);
    }
    return reactionMotionLoad;
  }

  function setFaceCue(key, now, duration) {
    const cue = FACE_CUES[key] || FACE_CUES.relax;
    faceState.cue = cue;
    faceState.cueUntil = now + duration;
  }

  function handlePointerOut(event) {
    if (!event.relatedTarget) resetPointer();
  }

  window.addEventListener('pointermove', setPointer, { passive: true });
  document.addEventListener('pointerout', handlePointerOut, { passive: true });
  canvas.addEventListener('pointerdown', react, { passive: true });
  canvas.addEventListener('click', playReactionAudio);

  function render() {
    if (disposed) return;
    frameId = requestAnimationFrame(render);
    if (!active || document.hidden) return;

    const delta = Math.min(clock.getDelta(), .05);
    const now = performance.now();
    const reacting = now < reactingUntil;

    if (!reducedMotion) {
      mixer.update(delta);
      if (nextMotionAt && now >= nextMotionAt) playAmbient(now);
      smoothPointer.lerp(pointer, .07);
      lookTarget.position.set(smoothPointer.x * .7, size.y * (.62 + smoothPointer.y * .06), 2.8);

      // Positive viewport X must produce a positive head yaw for this VRM0
      // model. The previous negative sign made her look away from the cursor.
      const yaw = smoothPointer.x * .24;
      const pitch = smoothPointer.y * .14;
      const tilt = reacting ? .12 : 0;
      applyBoneRotation(neck, baseNeck, pitch * .42, yaw * .46, tilt * .3, .1);
      applyBoneRotation(head, baseHead, pitch, yaw, tilt, .14);
      if (chest) applyBoneOffset(chest, Math.sin(now * .0018) * .012, yaw * .06, 0);
      if (!blinkStarted && now >= nextBlink) blinkStarted = now;
      let blink = 0;
      if (blinkStarted) {
        const progress = (now - blinkStarted) / 170;
        blink = progress < .5 ? progress * 2 : Math.max(0, (1 - progress) * 2);
        if (progress >= 1) {
          blinkStarted = 0;
          nextBlink = now + randomBlinkDelay();
        }
      }
      setExpression(vrm, 'blink', blink);

      if (!winkStarted && now >= nextWink && !blinkStarted) winkStarted = now;
      let wink = 0;
      if (winkStarted) {
        const progress = (now - winkStarted) / 260;
        wink = progress < .5 ? progress * 2 : Math.max(0, (1 - progress) * 2);
        if (progress >= 1) {
          winkStarted = 0;
          nextWink = now + 14000 + Math.random() * 13000;
        }
      }
      setExpression(vrm, faceState.winkExpression, wink);
      updateFace(vrm, faceState, now, delta);
    }

    vrm.update(delta);
    renderer.render(scene, camera);
    if (firstFrame) {
      firstFrame = false;
      sceneRoot.classList.add('is-vrm-ready');
      settleHeroLoad('ready');
      prepareReactionSound();
      const warmReaction = () => ensureReactionMotion();
      if ('requestIdleCallback' in window) {
        window.requestIdleCallback(warmReaction, { timeout: 2500 });
      } else {
        window.setTimeout(warmReaction, 800);
      }
    }
  }

  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(host);
  const visibilityObserver = new IntersectionObserver(entries => {
    active = entries[0]?.isIntersecting !== false;
    if (active) clock.getDelta();
  }, { rootMargin: '150px' });
  visibilityObserver.observe(studio);

  canvas.addEventListener('webglcontextlost', event => {
    event.preventDefault();
    sceneRoot.classList.remove('is-vrm-ready');
    sceneRoot.classList.add('is-vrm-fallback');
    active = false;
  });

  window.addEventListener('pagehide', () => {
    disposed = true;
    cancelAnimationFrame(frameId);
    resizeObserver.disconnect();
    visibilityObserver.disconnect();
    window.removeEventListener('pointermove', setPointer);
    document.removeEventListener('pointerout', handlePointerOut);
    canvas.removeEventListener('click', playReactionAudio);
    reactionSound?.pause();
    mixer.stopAllAction();
    mixer.uncacheRoot(vrm.scene);
    VRMUtils.deepDispose(vrm.scene);
    renderer.dispose();
  }, { once: true });

  resize();
  render();
}

async function loadHeroModel(loader) {
  const primaryUrl = host.dataset.model;
  const fallbackUrl = host.dataset.modelFallback;
  try {
    return await loader.loadAsync(primaryUrl);
  } catch (primaryError) {
    if (!fallbackUrl || fallbackUrl === primaryUrl) throw primaryError;
    return loader.loadAsync(fallbackUrl);
  }
}

function applyBoneRotation(bone, base, x, y, z, smoothing) {
  if (!bone || !base) return;
  const offset = new THREE.Quaternion().setFromEuler(new THREE.Euler(x, y, z, 'YXZ'));
  const target = base.clone().multiply(offset);
  bone.quaternion.slerp(target, smoothing);
}

function applyBoneOffset(bone, x, y, z) {
  if (!bone) return;
  bone.quaternion.multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(x, y, z, 'YXZ')));
}

function applyIdlePose(vrm) {
  const humanoid = vrm.humanoid;
  if (!humanoid) return;
  setBonePose(humanoid.getNormalizedBoneNode('leftUpperArm'), .08, 0, 1.13);
  setBonePose(humanoid.getNormalizedBoneNode('rightUpperArm'), .08, 0, -1.13);
  setBonePose(humanoid.getNormalizedBoneNode('leftLowerArm'), 0, -.08, .10);
  setBonePose(humanoid.getNormalizedBoneNode('rightLowerArm'), 0, .08, -.10);
  setBonePose(humanoid.getNormalizedBoneNode('leftHand'), 0, 0, .08);
  setBonePose(humanoid.getNormalizedBoneNode('rightHand'), 0, 0, -.08);
  setBonePose(humanoid.getNormalizedBoneNode('spine'), 0, -.035, 0);
}

function setBonePose(bone, x, y, z) {
  if (!bone) return;
  bone.quaternion.multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(x, y, z, 'XYZ')));
}

function setExpression(vrm, name, value) {
  if (!name) return;
  try {
    if (vrm.expressionManager?.getExpression(name)) vrm.expressionManager.setValue(name, value);
  } catch (_) {
    // Models are allowed to omit optional expressions.
  }
}

function createBodyMotionAction(animation, mixer, vrm, blockedBoneNames, name) {
  const clip = createVRMAnimationClip(animation, vrm);
  const bodyClip = new THREE.AnimationClip(
    name,
    clip.duration,
    clip.tracks.filter(track => !isBoneTrack(track.name, blockedBoneNames)),
  );
  return mixer.clipAction(bodyClip);
}

function isBoneTrack(trackName, boneNames) {
  for (const boneName of boneNames) {
    if (trackName === `${boneName}.quaternion` || trackName === `${boneName}.position`) return true;
  }
  return false;
}

async function fetchAmbientMotionPack() {
  if (typeof DecompressionStream === 'undefined') return null;
  const response = await fetch(MOTION_PACK_URL, { cache: 'force-cache' });
  if (!response.ok || !response.body) throw new Error('Motion pack could not be loaded');
  const stream = response.body.pipeThrough(new DecompressionStream('gzip'));
  const pack = JSON.parse(await new Response(stream).text());
  if (pack.version !== 1 || !Array.isArray(pack.clips)) throw new Error('Unsupported motion pack');
  return pack;
}

function createAmbientMotionActions(pack, mixer, vrm, blockedBoneNames) {
  const isVrm0 = vrm.meta?.metaVersion === '0';
  return pack.clips.flatMap(sourceClip => {
    if (!AMBIENT_MOTION_KEYS.has(sourceClip.key)) return [];
    const times = Float32Array.from(sourceClip.times);
    const tracks = sourceClip.tracks.flatMap(sourceTrack => {
      const bone = vrm.humanoid?.getNormalizedBoneNode(sourceTrack.bone);
      if (!bone || blockedBoneNames.has(bone.name)) return [];
      const values = Float32Array.from(sourceTrack.values, (value, index) => (
        isVrm0 && index % 4 % 2 === 0 ? -value : value
      ));
      return [new THREE.QuaternionKeyframeTrack(`${bone.name}.quaternion`, times, values)];
    });
    if (!tracks.length) return [];
    const clip = new THREE.AnimationClip(`ambient-${sourceClip.key}`, sourceClip.duration, tracks);
    const action = mixer.clipAction(clip);
    return [{
      action,
      key: sourceClip.key,
      name: sourceClip.name,
      ...(MOTION_BEHAVIOR[sourceClip.key] || { repeats: 1, maxSeconds: 3.5, timeScale: 1 }),
    }];
  });
}

function selectIntroMotion(entries, requestedKey = '') {
  const requested = entries.find(entry => entry.key === requestedKey);
  if (requested) return requested;

  let sequenceIndex = 0;
  try {
    const storedIndex = Number.parseInt(sessionStorage.getItem('showcaseHeroMotionIndex') || '0', 10);
    sequenceIndex = Number.isFinite(storedIndex) ? storedIndex : 0;
    sessionStorage.setItem('showcaseHeroMotionIndex', String(sequenceIndex + 1));
  } catch (_) {
    // Storage can be disabled; Bored remains the deterministic first motion.
  }
  const selectedKey = INTRO_MOTION_SEQUENCE[sequenceIndex % INTRO_MOTION_SEQUENCE.length];
  return entries.find(entry => entry.key === selectedKey)
    || entries.find(entry => entry.key === 'bored')
    || entries[0]
    || null;
}

function buildAmbientBag(entries, avoidKey = '') {
  const bag = entries.flatMap(entry => Array.from({ length: entry.repeats || 1 }, () => entry));
  for (let index = bag.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1));
    [bag[index], bag[swapIndex]] = [bag[swapIndex], bag[index]];
  }
  if (bag[0]?.key === avoidKey) {
    const replacement = bag.findIndex(entry => entry.key !== avoidKey);
    if (replacement > 0) [bag[0], bag[replacement]] = [bag[replacement], bag[0]];
  }
  return bag;
}

function createFaceState(vrm) {
  return {
    values: Object.fromEntries(CONTROLLED_EXPRESSIONS.map(name => [name, 0])),
    mood: MICRO_MOODS[0],
    moodIndex: 0,
    nextMoodAt: performance.now() + 3500 + Math.random() * 3500,
    cue: null,
    cueUntil: 0,
    winkExpression: firstExpression(vrm, ['blinkRight', 'blink_r', 'winkRight', 'wink']),
  };
}

function updateFace(vrm, state, now, delta) {
  if (now >= state.nextMoodAt) {
    let nextIndex = state.moodIndex;
    while (nextIndex === state.moodIndex) nextIndex = Math.floor(Math.random() * MICRO_MOODS.length);
    state.moodIndex = nextIndex;
    state.mood = MICRO_MOODS[nextIndex];
    state.nextMoodAt = now + 4500 + Math.random() * 5000;
  }
  if (state.cueUntil && now >= state.cueUntil) {
    state.cue = null;
    state.cueUntil = 0;
  }
  const target = state.cue || state.mood;
  const smoothing = Math.min(1, delta * 4.8);
  for (const name of CONTROLLED_EXPRESSIONS) {
    state.values[name] += ((target[name] || 0) - state.values[name]) * smoothing;
    setExpression(vrm, name, state.values[name]);
  }
}

function firstExpression(vrm, names) {
  for (const name of names) {
    try {
      if (vrm.expressionManager?.getExpression(name)) return name;
    } catch (_) {
      // Keep looking for a compatible optional expression.
    }
  }
  return null;
}

function isLocalPreview() {
  return window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost';
}

function randomBlinkDelay() {
  return 2600 + Math.random() * 3400;
}

function hasWebGL() {
  try {
    const probe = document.createElement('canvas');
    return Boolean(window.WebGLRenderingContext && (probe.getContext('webgl2') || probe.getContext('webgl')));
  } catch (_) {
    return false;
  }
}

function playReactionSound(now) {
  if (now - lastReactionSoundAt < REACTION_SOUND_COOLDOWN) return;
  lastReactionSoundAt = now;
  prepareReactionSound();
  try {
    reactionSound.muted = false;
    reactionSound.volume = REACTION_SOUND_VOLUME;
    reactionSound.currentTime = 0;
    const playback = reactionSound.play();
    if (playback?.catch) {
      playback.catch(() => {
        reactionSound = null;
        lastReactionSoundAt = -Infinity;
      });
    }
  } catch (_) {
    // Audio is a decorative enhancement and must never block the reaction.
  }
}

function prepareReactionSound() {
  if (reactionSound) return reactionSound;
  reactionSound = new Audio(REACTION_SOUND_URL);
  reactionSound.preload = 'auto';
  reactionSound.volume = REACTION_SOUND_VOLUME;
  reactionSound.load();
  return reactionSound;
}

function burstReactionHearts(event) {
  if (!sceneRoot || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  let layer = sceneRoot.querySelector('.creator-scene__reaction-hearts');
  if (!layer) {
    layer = document.createElement('div');
    layer.className = 'creator-scene__reaction-hearts';
    layer.setAttribute('aria-hidden', 'true');
    sceneRoot.appendChild(layer);
  }

  const rect = sceneRoot.getBoundingClientRect();
  const originX = THREE.MathUtils.clamp((event?.clientX ?? rect.left + rect.width * .5) - rect.left, 24, rect.width - 24);
  const originY = THREE.MathUtils.clamp((event?.clientY ?? rect.top + rect.height * .56) - rect.top, 34, rect.height - 18);
  for (let index = 0; index < 8; index += 1) {
    const heart = document.createElement('i');
    const angle = (index / 7 - .5) * Math.PI * .82;
    const distance = 28 + Math.random() * 52;
    const drift = Math.sin(angle) * distance;
    heart.style.setProperty('--heart-x', `${originX}px`);
    heart.style.setProperty('--heart-y', `${originY}px`);
    heart.style.setProperty('--heart-drift', `${drift.toFixed(1)}px`);
    heart.style.setProperty('--heart-rise', `${(74 + Math.cos(angle) * 35 + Math.random() * 24).toFixed(1)}px`);
    heart.style.setProperty('--heart-delay', `${(index * 18 + Math.random() * 35).toFixed(0)}ms`);
    heart.style.setProperty('--heart-scale', (.62 + Math.random() * .62).toFixed(2));
    heart.style.setProperty('--heart-color', HEART_COLORS[index % HEART_COLORS.length]);
    heart.addEventListener('animationend', () => heart.remove(), { once: true });
    layer.appendChild(heart);
  }
}
