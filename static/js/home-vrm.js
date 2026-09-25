/* Landing VRM: SABA_0.1 sitting on the desk of the hero painting.
   Procedural motion only (breathing, sway, blinking, cursor gaze, a short
   happy reaction on click). The pose is authored in the model's normalized
   humanoid space; see POSE. On failure the painting simply stays without the
   character and the loader is released. */
import {
  THREE,
  GLTFLoader,
  VRMLoaderPlugin,
  VRMUtils,
} from '/static/vendor/vrm-runtime.module.js?v=20260915-saba2';

const host = document.getElementById('heroVrm');
const canvas = document.getElementById('heroVrmCanvas');
const hitZone = document.getElementById('heroVrmHit') || canvas;
const sceneRoot = host?.closest('.creator-scene');
const stage = host?.closest('.home-hero');

const REACTION_SOUND_URL = '/static/audio/hero-cute-reaction.mp3?v=20260918-2';
const REACTION_SOUND_VOLUME = 0.05;
const REACTION_SOUND_COOLDOWN = 520;
const REACTION_MS = 1700;
const HEART_COLORS = ['#55d9ff', '#7be7ff', '#35b9f2', '#9e8cff'];

/* Euler XYZ radians per normalized bone (VRM 0.x rig: faces -Z, left = -X). */
const POSE = {
  hips: [0.12, 0.18, -0.06],
  spine: [-0.10, 0.05, -0.10],
  chest: [-0.12, 0.02, -0.08],
  rightShoulder: [0, 0, 0],
  upperChest: [0, 0, 0],
  neck: [0.04, 0, -0.02],
  head: [0.08, -0.10, 0.06],
  rightUpperLeg: [2.25, -0.30, 0.12],
  rightLowerLeg: [-2.45, 0, 0],
  rightFoot: [0.35, 0, 0],
  leftUpperLeg: [1.60, 0.25, -0.50],
  leftLowerLeg: [-1.50, 0.10, -0.45],
  leftFoot: [0.20, 0, 0],
  rightUpperArm: [0.35, -0.35, -1.02], // slightly behind the hip, leaning on the desk
  rightLowerArm: [0, 0.10, 0],
  rightHand: [0.30, -0.20, 1.10], // palm flat on the desk, fingers outward
  leftUpperArm: [0.30, -0.80, 1.15],
  leftLowerArm: [0, -0.90, 0.10],
  leftHand: [-0.20, 0, 0.30],    // resting on top of the thigh
  leftIndexProximal: [0, 0, 0.14], leftIndexIntermediate: [0, 0, 0.18], leftIndexDistal: [0, 0, 0.12],
  leftMiddleProximal: [0, 0, 0.14], leftMiddleIntermediate: [0, 0, 0.18], leftMiddleDistal: [0, 0, 0.12],
  leftRingProximal: [0, 0, 0.14], leftRingIntermediate: [0, 0, 0.18], leftRingDistal: [0, 0, 0.12],
  leftLittleProximal: [0, 0, 0.14], leftLittleIntermediate: [0, 0, 0.18], leftLittleDistal: [0, 0, 0.12],
  leftThumbProximal: [0, 0.5, 0], leftThumbIntermediate: [0, 0.4, 0], leftThumbDistal: [0, 0.3, 0],
  rightIndexProximal: [0, 0, -0.10], rightIndexIntermediate: [0, 0, -0.12], rightIndexDistal: [0, 0, -0.07],
  rightMiddleProximal: [0, 0, -0.10], rightMiddleIntermediate: [0, 0, -0.12], rightMiddleDistal: [0, 0, -0.07],
  rightRingProximal: [0, 0, -0.10], rightRingIntermediate: [0, 0, -0.12], rightRingDistal: [0, 0, -0.07],
  rightLittleProximal: [0, 0, -0.10], rightLittleIntermediate: [0, 0, -0.12], rightLittleDistal: [0, 0, -0.07],
  rightThumbProximal: [0, -0.25, 0], rightThumbIntermediate: [0, -0.2, 0],
};
/* Hands are placed with an analytic two-bone IK every frame (world metres,
   the model faces +Z, so her right is -X and "back" is -Z). Each arm has a
   hand target and a pole that chooses where the elbow points (IMAGE/ii.png):
   - support arm (model right / viewer left): upper arm hangs down and a little
     back, elbow bent near the desk, forearm towards the surface, palm flat on
     the desk beside her;
   - other arm: upper arm along the body, elbow slightly back, forearm towards
     the horizontal leg, hand on top of the thigh near the knee, fingers down. */
const HANDS = {
  deskSide: 0.28,      // hand outward from the hip
  deskBack: 0.10,      // hand behind the hip
  deskDown: 0.11,      // hand below the hip joint (desk surface)
  deskYaw: 0.15,       // fingers pointing outward, slightly forward
  supportPole: [-0.05, -0.50, -0.60], // elbow direction from the shoulder: out, down, back
  kneeUp: 0.09,        // wrist above the knee joint
  kneeBack: 0.19,      // wrist back along the thigh (hand on the thigh near the knee)
  kneePitch: 0.25,     // fingers following the leg downward
  kneePole: [0.20, -0.50, -0.60],     // elbow out, down and back
};
/* Where the character sits in the painting, in 1672×941 design pixels and
   relative to the .home-vrm box (which starts at 24% of the art width). */
const FRAME = { boxLeft: 0.24, boxWidth: 0.56, seatX: 806, seatY: 648, headTopY: 56 };

const CONTROLLED_EXPRESSIONS = ['happy', 'relaxed', 'surprised', 'sad'];
const IDLE_FACE = { relaxed: 0.08 };
const REACTION_FACE = { happy: 0.38, relaxed: 0.18 };

let heroLoadSettled = false;
let reactionSound = null;
let lastReactionSoundAt = -Infinity;

function settleHeroLoad(status) {
  if (heroLoadSettled) return;
  heroLoadSettled = true;
  document.dispatchEvent(new CustomEvent('showcasemaker:hero-ready', { detail: { status } }));
}

function showFallback() {
  sceneRoot?.classList.add('is-vrm-fallback');
  settleHeroLoad('fallback');
}

if (host && canvas && sceneRoot && stage) {
  initHomeVrm().catch(() => showFallback());
} else {
  settleHeroLoad('unavailable');
}

async function initHomeVrm() {
  const saveData = Boolean(navigator.connection?.saveData);
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (saveData || !hasWebGL()) {
    showFallback();
    return;
  }

  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: 'high-performance' });
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, window.innerWidth < 820 ? 1.25 : 1.5));

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(22, 1, 0.01, 100);
  // Cool ambient from the room, a soft key from the left and a strong cyan
  // rim from the monitor on the right, matching the painting's light.
  scene.add(new THREE.HemisphereLight(0xc8d8ff, 0x1a1f3a, 1.35));
  const keyLight = new THREE.DirectionalLight(0xf2f0ff, 1.9);
  keyLight.position.set(-1.8, 2.4, 3.2);
  scene.add(keyLight);
  const monitorLight = new THREE.DirectionalLight(0x5fc8ff, 1.1);
  monitorLight.position.set(3.2, 1.4, 1.2);
  scene.add(monitorLight);
  const rimLight = new THREE.DirectionalLight(0x8a7dff, 0.55);
  rimLight.position.set(-2.4, 1.8, -2.4);
  scene.add(rimLight);

  const loader = new GLTFLoader();
  loader.register(parser => new VRMLoaderPlugin(parser));
  const gltf = await loadModel(loader);
  const vrm = gltf.userData.vrm;
  if (!vrm) throw new Error('The model does not contain VRM data');

  VRMUtils.rotateVRM0(vrm);
  scene.add(vrm.scene);
  vrm.scene.traverse(object => { object.frustumCulled = false; });

  const humanoid = vrm.humanoid;
  const bones = {};
  for (const name of Object.keys(POSE)) bones[name] = humanoid?.getNormalizedBoneNode(name) || null;
  const pose = JSON.parse(JSON.stringify(POSE));

  const tmpEuler = new THREE.Euler(0, 0, 0, 'XYZ');
  function setBone(name, x, y, z) {
    if (!(name in bones)) bones[name] = humanoid?.getNormalizedBoneNode(name) || null;
    const bone = bones[name];
    if (!bone) return;
    tmpEuler.set(x, y, z, 'XYZ');
    bone.quaternion.setFromEuler(tmpEuler);
  }

  const node = name => {
    if (!(name in bones)) bones[name] = humanoid?.getNormalizedBoneNode(name) || null;
    return bones[name];
  };
  const ikA = new THREE.Vector3(), ikB = new THREE.Vector3(), ikC = new THREE.Vector3();
  const ikTarget = new THREE.Vector3(), ikUp = new THREE.Vector3(0, 1, 0);
  const qa = new THREE.Quaternion(), qb = new THREE.Quaternion(), qc = new THREE.Quaternion();

  const ikE = new THREE.Vector3(), ikDir = new THREE.Vector3(), ikPole = new THREE.Vector3();
  // Rotate `bone` (in world space) so that `child` ends up on the line to target.
  function aim(bone, child, target) {
    bone.getWorldPosition(ikA);
    child.getWorldPosition(ikB);
    ikB.sub(ikA).normalize();
    ikC.copy(target).sub(ikA).normalize();
    if (ikB.dot(ikC) > 0.999999) return;
    qa.setFromUnitVectors(ikB, ikC);
    bone.getWorldQuaternion(qb);
    bone.parent.getWorldQuaternion(qc);
    bone.quaternion.copy(qc.invert().multiply(qa.multiply(qb)));
  }
  // Analytic two-bone IK: the elbow lies in the plane of shoulder, target and pole.
  function reach(upperName, lowerName, handName, target, poleOffset) {
    const upper = node(upperName), lower = node(lowerName), hand = node(handName);
    if (!upper || !lower || !hand) return;
    const S = upper.getWorldPosition(new THREE.Vector3());
    const lenA = S.distanceTo(lower.getWorldPosition(ikA));
    const lenB = ikA.distanceTo(hand.getWorldPosition(ikB));
    ikDir.copy(target).sub(S);
    const d = THREE.MathUtils.clamp(ikDir.length(), 1e-4, (lenA + lenB) * 0.999);
    ikDir.normalize();
    const along = (lenA * lenA - lenB * lenB + d * d) / (2 * d);
    const height = Math.sqrt(Math.max(0, lenA * lenA - along * along));
    ikPole.set(poleOffset[0], poleOffset[1], poleOffset[2]);
    ikPole.addScaledVector(ikDir, -ikPole.dot(ikDir)).normalize();
    ikE.copy(S).addScaledVector(ikDir, along).addScaledVector(ikPole, height);
    aim(upper, lower, ikE);
    aim(lower, hand, target);
  }

  // Orient a hand in world space: palm down (as in the T-pose), then yaw/pitch.
  function orientHand(handName, yaw, pitchAxis, pitch) {
    const hand = node(handName);
    if (!hand) return;
    node('hips').parent.getWorldQuaternion(qb);          // rig root: palms face down
    qa.setFromAxisAngle(ikUp, yaw).multiply(qb);
    if (pitchAxis && pitch) qa.premultiply(qc.setFromAxisAngle(pitchAxis, pitch));
    hand.parent.getWorldQuaternion(qb);
    hand.quaternion.copy(qb.invert().multiply(qa));
  }

  function placeHands() {
    const h = HANDS;
    // Supporting hand on the desk (the model faces +Z, so her right is -X).
    node('hips').getWorldPosition(ikTarget);
    ikTarget.x -= h.deskSide; ikTarget.z -= h.deskBack; ikTarget.y -= h.deskDown;
    reach('rightUpperArm', 'rightLowerArm', 'rightHand', ikTarget, h.supportPole);
    orientHand('rightHand', h.deskYaw);
    // Other hand on the knee of the horizontal leg.
    const hip = node('leftUpperLeg').getWorldPosition(new THREE.Vector3());
    const knee = node('leftLowerLeg').getWorldPosition(new THREE.Vector3());
    const thigh = knee.clone().sub(hip).normalize();
    ikTarget.copy(knee).addScaledVector(ikUp, h.kneeUp).addScaledVector(thigh, -h.kneeBack);
    reach('leftUpperArm', 'leftLowerArm', 'leftHand', ikTarget, h.kneePole);
    const flat = new THREE.Vector3(thigh.x, 0, thigh.z).normalize();
    const drape = new THREE.Vector3().crossVectors(flat, ikUp).normalize();
    orientHand('leftHand', Math.atan2(-flat.z, flat.x), drape, -h.kneePitch);
  }

  function applyPose(now, gaze, reactAmount) {
    const t = now / 1000;
    const breath = Math.sin(t * 1.55);
    const sway = Math.sin(t * 0.42);
    for (const [name, [x, y, z]] of Object.entries(pose)) {
      let dx = 0, dy = 0, dz = 0;
      if (name === 'spine') { dx = breath * 0.012; dz = sway * 0.012; }
      if (name === 'chest') { dx = breath * 0.018; dy = gaze.x * 0.05; }
      if (name === 'upperChest') { dx = breath * 0.01; }
      if (name === 'neck') { dx = gaze.y * 0.06; dy = gaze.x * 0.12; dz = reactAmount * 0.04; }
      if (name === 'head') { dx = gaze.y * 0.16 - reactAmount * 0.03; dy = gaze.x * 0.26; dz = sway * 0.015 - reactAmount * 0.16; }
      setBone(name, x + dx, y + dy, z + dz);
    }
    placeHands();
  }

  const faceValues = Object.fromEntries(CONTROLLED_EXPRESSIONS.map(name => [name, 0]));
  function updateFace(target, delta) {
    const k = Math.min(1, delta * 5);
    for (const name of CONTROLLED_EXPRESSIONS) {
      faceValues[name] += ((target[name] || 0) - faceValues[name]) * k;
      setExpression(vrm, name, faceValues[name]);
    }
  }

  const lookTarget = new THREE.Object3D();
  scene.add(lookTarget);
  if (vrm.lookAt) vrm.lookAt.target = lookTarget;

  const zero = new THREE.Vector2(0, 0);
  applyPose(0, zero, 0);
  vrm.update(0);

  // Seat the model: hips at the origin, head height measured from the posed rig.
  const hipsWorld = new THREE.Vector3();
  const headWorld = new THREE.Vector3();
  function measure() {
    vrm.scene.updateMatrixWorld(true);
    humanoid.getNormalizedBoneNode('hips').getWorldPosition(hipsWorld);
    humanoid.getNormalizedBoneNode('head').getWorldPosition(headWorld);
  }
  measure();
  vrm.scene.position.sub(hipsWorld);
  measure();
  const headTop = headWorld.y + 0.25; // crown + hair above the head bone

  function resize() {
    const rect = host.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    renderer.setSize(rect.width, rect.height, false);
    camera.aspect = rect.width / rect.height;
    // Map design pixels to world units so the seat and the crown land where
    // the painting expects them, whatever the viewport size.
    const boxWidthPx = FRAME.boxWidth * 1672;
    const unitsPerPx = headTop / (FRAME.seatY - FRAME.headTopY);
    const visibleHeight = 941 * unitsPerPx;
    const distance = visibleHeight / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov * 0.5)));
    const seatInBoxX = FRAME.seatX - FRAME.boxLeft * 1672;
    const cx = (boxWidthPx / 2 - seatInBoxX) * unitsPerPx;
    const cy = (FRAME.seatY - 941 / 2) * unitsPerPx;
    camera.position.set(cx, cy, distance);
    camera.lookAt(cx, cy, 0);
    camera.updateProjectionMatrix();
  }

  const pointer = new THREE.Vector2(0, 0);
  const gaze = new THREE.Vector2(0, 0);
  let reactingUntil = 0;
  let reactAmount = 0;
  let nextBlink = performance.now() + randomBlinkDelay();
  let blinkStarted = 0;
  let active = true;
  let disposed = false;
  let firstFrame = true;
  let frameId = 0;
  const clock = new THREE.Clock();

  function setPointer(event) {
    const rect = canvas.getBoundingClientRect();
    // Eye line of the character inside the canvas box.
    const cx = rect.left + rect.width * ((FRAME.seatX - FRAME.boxLeft * 1672) / (FRAME.boxWidth * 1672));
    const cy = rect.top + rect.height * (170 / 941);
    const rangeX = event.clientX < cx ? cx : window.innerWidth - cx;
    const rangeY = event.clientY < cy ? cy : window.innerHeight - cy;
    pointer.x = THREE.MathUtils.clamp((event.clientX - cx) / Math.max(rangeX, 1), -1, 1);
    pointer.y = THREE.MathUtils.clamp((cy - event.clientY) / Math.max(rangeY, 1), -1, 1);
  }
  function resetPointer(event) {
    if (!event.relatedTarget) pointer.set(0, 0);
  }

  function react(event) {
    burstReactionHearts(event);
    if (reducedMotion) return;
    reactingUntil = performance.now() + REACTION_MS;
  }
  function playReactionAudio() {
    playReactionSound(performance.now());
  }

  window.addEventListener('pointermove', setPointer, { passive: true });
  document.addEventListener('pointerout', resetPointer, { passive: true });
  // A plain rectangle over the character receives clicks: no per-move 3D
  // hit testing, which stalled frames on skinned meshes.
  hitZone.addEventListener('pointerdown', react, { passive: true });
  hitZone.addEventListener('click', playReactionAudio);

  function frame() {
    if (disposed) return;
    frameId = requestAnimationFrame(frame);
    if (!active || document.hidden) return;
    const delta = Math.min(clock.getDelta(), 0.05);
    const now = performance.now();
    const reacting = now < reactingUntil;
    reactAmount += ((reacting ? 1 : 0) - reactAmount) * Math.min(1, delta * (reacting ? 7 : 3));

    if (!reducedMotion) {
      gaze.lerp(pointer, 0.06);
      applyPose(now, gaze, reactAmount);
      lookTarget.position.set(gaze.x * 1.2, headWorld.y + gaze.y * 0.5, 2.5);
      if (!blinkStarted && now >= nextBlink) blinkStarted = now;
      let blink = 0;
      if (blinkStarted) {
        const progress = (now - blinkStarted) / 170;
        blink = progress < 0.5 ? progress * 2 : Math.max(0, (1 - progress) * 2);
        if (progress >= 1) { blinkStarted = 0; nextBlink = now + randomBlinkDelay(); }
      }
      setExpression(vrm, 'blink', blink);
      updateFace(reacting ? REACTION_FACE : IDLE_FACE, delta);
    } else {
      applyPose(0, zero, 0);
    }

    vrm.update(delta);
    renderer.render(scene, camera);
    if (firstFrame) {
      firstFrame = false;
      sceneRoot.classList.add('is-vrm-ready');
      settleHeroLoad('ready');
      prepareReactionSound();
    }
  }

  const resizeObserver = new ResizeObserver(resize);
  resizeObserver.observe(host);
  const visibilityObserver = new IntersectionObserver(entries => {
    active = entries[0]?.isIntersecting !== false;
    if (active) clock.getDelta();
  }, { rootMargin: '120px' });
  visibilityObserver.observe(stage);

  canvas.addEventListener('webglcontextlost', event => {
    event.preventDefault();
    sceneRoot.classList.remove('is-vrm-ready');
    active = false;
    showFallback();
  });

  window.addEventListener('pagehide', () => {
    disposed = true;
    cancelAnimationFrame(frameId);
    resizeObserver.disconnect();
    visibilityObserver.disconnect();
    window.removeEventListener('pointermove', setPointer);
    document.removeEventListener('pointerout', resetPointer);
    hitZone.removeEventListener('click', playReactionAudio);
    reactionSound?.pause();
    VRMUtils.deepDispose(vrm.scene);
    renderer.dispose();
  }, { once: true });

  // Local-only tuning hook: lets a QA script adjust the pose without reloads.
  if (isLocalPreview()) {
    window.__homeVrm = {
      pose, frame: FRAME, hands: HANDS,
      setPose(values) { Object.assign(pose, values); },
      setFrame(values) { Object.assign(FRAME, values); resize(); },
      react() { reactingUntil = performance.now() + REACTION_MS; },
    };
  }

  resize();
  frame();
}

async function loadModel(loader) {
  const primaryUrl = host.dataset.model;
  const fallbackUrl = host.dataset.modelFallback;
  try {
    return await loader.loadAsync(primaryUrl);
  } catch (primaryError) {
    if (!fallbackUrl || fallbackUrl === primaryUrl) throw primaryError;
    return loader.loadAsync(fallbackUrl);
  }
}

function setExpression(vrm, name, value) {
  if (!name) return;
  try {
    if (vrm.expressionManager?.getExpression(name)) vrm.expressionManager.setValue(name, value);
  } catch (_) {
    // Models may omit optional expressions.
  }
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
    reactionSound.volume = REACTION_SOUND_VOLUME;
    reactionSound.currentTime = 0;
    const playback = reactionSound.play();
    if (playback?.catch) playback.catch(() => { reactionSound = null; lastReactionSoundAt = -Infinity; });
  } catch (_) {
    // Audio is decorative and must never block the reaction.
  }
}

function prepareReactionSound() {
  if (reactionSound) return reactionSound;
  reactionSound = new Audio(REACTION_SOUND_URL);
  reactionSound.preload = 'auto';
  reactionSound.volume = REACTION_SOUND_VOLUME;
  return reactionSound;
}

function burstReactionHearts(event) {
  if (!sceneRoot || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  let layer = stage.querySelector('.home-reaction');
  if (!layer) {
    layer = document.createElement('div');
    layer.className = 'home-reaction';
    layer.setAttribute('aria-hidden', 'true');
    stage.appendChild(layer);
  }
  const rect = stage.getBoundingClientRect();
  const originX = (event?.clientX ?? rect.left + rect.width * 0.5) - rect.left;
  const originY = (event?.clientY ?? rect.top + rect.height * 0.4) - rect.top;
  for (let index = 0; index < 8; index += 1) {
    const heart = document.createElement('i');
    const angle = (index / 7 - 0.5) * Math.PI * 0.82;
    const distance = 28 + Math.random() * 52;
    heart.style.setProperty('--heart-x', `${originX}px`);
    heart.style.setProperty('--heart-y', `${originY}px`);
    heart.style.setProperty('--heart-drift', `${(Math.sin(angle) * distance).toFixed(1)}px`);
    heart.style.setProperty('--heart-rise', `${(74 + Math.cos(angle) * 35 + Math.random() * 24).toFixed(1)}px`);
    heart.style.setProperty('--heart-delay', `${(index * 18 + Math.random() * 35).toFixed(0)}ms`);
    heart.style.setProperty('--heart-scale', (0.55 + Math.random() * 0.55).toFixed(2));
    heart.style.setProperty('--heart-color', HEART_COLORS[index % HEART_COLORS.length]);
    heart.addEventListener('animationend', () => heart.remove(), { once: true });
    layer.appendChild(heart);
  }
}
