"""Background keying for characters on a solid backdrop (any colour).

Server twin of static/js/chroma-matte.js (Builder layers, Character preview): keep
the formulas identical, tests/test_chroma_matte.py compares the two.

Why it is built this way (owner report 2026-10-05: GIF/video cut-outs flickered,
white highlights vanished on white backdrops, black outlines broke on black):

* The backdrop colour is estimated ONCE per clip from the border of several frames
  (`estimate`), not per frame. Per-frame sampling made the key drift = flicker.
* Distance is measured in YCbCr. For a saturated key (green, blue, pink...) the
  brightness counts little, so shading on the backdrop still keys; for neutral keys
  (white, grey, black) brightness is the whole difference.
* Only backdrop CONNECTED TO THE FRAME BORDER is removed (a flood fill, like a magic
  wand), so white eyes / black outlines inside the character survive. Enclosed
  backdrop pockets (between an arm and the body) are removed too when they are
  large enough (`holes`); small ones (eyes, highlights) stay.
* The decision uses a 3x3-averaged distance, which ignores GIF dithering and video
  compression noise.
* Soft edge pixels get the backdrop colour un-mixed out of them (no halo), saturated
  keys also lose their colour spill on the rim.
* In clips, alpha of pixels whose colour did not change since the previous frame is
  averaged with that frame (removes the shimmer of noisy edges on still parts).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# The same constants live in static/js/chroma-matte.js.
RING = 2                 # border ring width sampled for the backdrop colour
CLUSTER = 36.0           # RGB radius of the backdrop cluster around the histogram peak
MIN_COVERAGE = 0.30      # auto mode: share of the border that must be backdrop
HOLE_SHARE = 0.0008      # enclosed pockets (between hair strands, arms) at least this share of the
                         # image are removed for white/grey/black keys (smaller ones = eyes and
                         # highlights stay); a saturated key colour (green screen) is never part
                         # of the figure, so its pockets go down to POCKET_MIN pixels.
POCKET_MIN = 8
POCKET_EXACT = 0.5       # ... and only when this share of the pocket IS the backdrop colour
                         # (skin on white, a black suit on dark green are not)
SPECK_SHARE = 0.00005    # tiny islands of almost-backdrop colour left in the backdrop
STATIC_DIFF = 10         # max channel change for "this pixel did not move"
FOREIGN = 0.3            # a frame whose border matches the clip backdrop less than this ...
OWN_BACKDROP = 0.45      # ... but is this solid in another colour gets its own model (intro/flash frames)
OWN_SPREAD = 12.0        # "solid": the frame's own backdrop varies less than this
PRESETS = {"green": (0, 177, 64), "blue": (0, 71, 187), "red": (210, 30, 40),
           "white": (255, 255, 255), "black": (0, 0, 0)}


@dataclass
class Model:
    key: tuple[float, float, float]
    spread: float = 0.0
    coverage: float = 1.0
    onset: float = 0.0   # distance where the figure's colours start (p3 beyond the backdrop); 0 = unknown


def _ycc(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    y = 0.299 * r + 0.587 * g + 0.114 * b
    cb = -0.168736 * r - 0.331264 * g + 0.5 * b
    cr = 0.5 * r - 0.418688 * g - 0.081312 * b
    return y, cb, cr


def _key_saturation(key) -> float:
    _, cb, cr = _ycc(np.asarray(key, dtype=np.float64))
    return float(np.hypot(cb, cr))


def _luma_weight(key) -> float:
    _, cb, cr = _ycc(np.asarray(key, dtype=np.float64))
    saturation = float(np.hypot(cb, cr))
    return 1.0 - 0.65 * min(1.0, max(0.0, (saturation - 20.0) / 40.0))


def distance(rgb, key) -> np.ndarray:
    """Colour distance to the key: brightness counts fully only for neutral keys."""
    rgb = np.asarray(rgb, dtype=np.float32)
    y, cb, cr = _ycc(rgb)
    ky, kcb, kcr = (float(v) for v in _ycc(np.asarray(key, dtype=np.float64)))
    weight = _luma_weight(key)
    return np.sqrt(weight * (y - ky) ** 2 + (cb - kcb) ** 2 + (cr - kcr) ** 2)


def _ring(array: np.ndarray) -> np.ndarray:
    h, w = array.shape[:2]
    band = min(RING, max(1, h // 2), max(1, w // 2))
    parts = [array[:band].reshape(-1, array.shape[2]), array[h - band:].reshape(-1, array.shape[2]),
             array[band:h - band, :band].reshape(-1, array.shape[2]),
             array[band:h - band, w - band:].reshape(-1, array.shape[2])]
    return np.concatenate(parts)


def estimate(frames, max_frames: int = 12) -> Model | None:
    """Backdrop colour from the border ring of up to ``max_frames`` frames (RGBA arrays)."""
    frames = list(frames)
    if not frames:
        return None
    step = max(1, len(frames) // max_frames)
    samples = []
    for frame in frames[::step][:max_frames]:
        ring = _ring(np.asarray(frame))
        samples.append(ring[ring[:, 3] >= 128, :3])
    samples = np.concatenate(samples).astype(np.int32) if samples else np.empty((0, 3), np.int32)
    if not len(samples):
        return None
    q = samples >> 3
    codes = q[:, 0] * 1024 + q[:, 1] * 32 + q[:, 2]
    peak = int(np.bincount(codes, minlength=32768).argmax())
    centre = np.array([(peak >> 10) * 8 + 4, ((peak >> 5) & 31) * 8 + 4, (peak & 31) * 8 + 4], dtype=np.float64)
    near = np.sqrt(((samples - centre) ** 2).sum(axis=1)) < CLUSTER
    cluster = samples[near]
    key = tuple(float(v) for v in cluster.mean(axis=0))
    spread = float(np.percentile(distance(cluster, key), 90)) if len(cluster) else 0.0
    model = Model(key=key, spread=spread, coverage=float(len(cluster)) / len(samples))
    model.onset = _onset(frames[::step][:max_frames], model)
    return model


def _onset(frames, model: Model) -> float:
    """Where the figure's colours begin: the first 4-unit distance bin beyond the backdrop
    itself holding at least a quarter of the fullest bin (every 4th pixel). A thin tail of
    anti-aliased edge pixels does not count, a real colour mass (dark clothes next to a muted
    dark-green or grey backdrop) does; the tolerance is capped below it (`_thresholds`)."""
    limit = max(12.0, _exact_limit(model))
    values = []
    for frame in frames:
        array = np.asarray(frame)
        pixels = array.reshape(-1, array.shape[-1])[::4]
        pixels = pixels[pixels[:, 3] >= 128, :3]
        far = distance(pixels, model.key)
        values.append(far[far > limit])
    values = np.concatenate(values) if values else np.empty(0)
    if len(values) < 50:
        return 0.0
    counts = np.bincount(((values - limit) // 4).astype(np.int64))
    first = int(np.argmax(counts >= 0.25 * counts.max()))
    return float(limit + first * 4)


def resolve(mode: str, model: Model | None) -> Model | None:
    """Turn the user's choice into the model to key with (None = leave the picture alone)."""
    mode = (mode or "auto").strip().lower()
    if mode in ("none", "0", "off", ""):
        return None
    wanted = None
    if mode in PRESETS:
        wanted = PRESETS[mode]
    elif mode.startswith("#") and len(mode) == 7:
        try:
            wanted = tuple(int(mode[i:i + 2], 16) for i in (1, 3, 5))
        except ValueError:
            wanted = None
    if wanted is None:
        # auto / "color": trust the border, but only when it really is one colour.
        return model if model and model.coverage >= MIN_COVERAGE else None
    # An explicit colour: use the measured backdrop when it is that colour (exact shade
    # and noise level), otherwise the colour as given.
    if model and float(distance(np.array([model.key]), wanted)[0]) < 40:
        return model
    return Model(key=tuple(float(v) for v in wanted), spread=0.0, coverage=0.0)


def _thresholds(model: Model, tolerance: float, softness: float) -> tuple[float, float]:
    tolerance = max(10.0, min(120.0, float(tolerance if tolerance is not None else 45)))
    softness = max(0.0, min(40.0, float(softness if softness is not None else 16)))
    floor = model.spread * 1.25 + 4.0
    inner = max(6.0 + (tolerance - 10.0) * 0.75, floor)
    if model.onset > 0:
        inner = min(inner, max(floor, 0.75 * model.onset))  # auto: stay below the figure's colours
    return inner, inner + (4.0 + softness * 1.2 if softness > 0 else 0.0)


def _exact_limit(model: Model) -> float:
    """Distance under which a pixel is the backdrop colour itself (noise included)."""
    return max(model.spread * 2.5 + 4.0, 10.0)


def _blur3(values: np.ndarray) -> np.ndarray:
    padded = np.pad(values, 1, mode="edge")
    total = np.zeros_like(values)
    for dy in range(3):
        for dx in range(3):
            total += padded[dy:dy + values.shape[0], dx:dx + values.shape[1]]
    return total / 9.0


def _components(mask: np.ndarray) -> tuple[int, np.ndarray]:
    import cv2
    count, labels = cv2.connectedComponents(mask.astype(np.uint8), connectivity=4)
    return count, labels


def apply(frame, model: Model | None, tolerance: float = 45, softness: float = 16,
          holes: bool = True, previous=None):
    """Key one RGBA frame. Returns (RGBA uint8 array, state for the next frame of a clip)."""
    rgba = np.asarray(frame, dtype=np.uint8)
    if model is None:
        return rgba.copy(), None
    h, w = rgba.shape[:2]
    total = h * w
    rgb = rgba[..., :3].astype(np.float32)
    src_alpha = rgba[..., 3].astype(np.float32)
    inner, outer = _thresholds(model, tolerance, softness)
    raw = distance(rgb, model.key)
    near = _blur3(raw)
    near[src_alpha < 8] = 0.0  # already transparent pixels count as backdrop
    # The smaller of the raw and the 3x3-averaged distance: averaging ignores noise on the
    # backdrop, the raw value keeps 1-3 px gaps between hair strands (averaging filled them).
    level = np.minimum(raw, near)
    candidate = level < max(outer, inner + 1e-3)
    core = level < inner

    count, labels = _components(candidate)
    border = np.zeros((h, w), dtype=bool)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    seeds = np.unique(labels[border & core])
    chosen = np.zeros(count, dtype=bool)
    chosen[seeds] = True
    chosen[0] = False
    if holes and count > 1:
        pocket = np.bincount(labels[core], minlength=count)
        area = np.bincount(labels.ravel(), minlength=count)
        exact = np.bincount(labels[raw < _exact_limit(model)], minlength=count)
        saturated = _key_saturation(model.key) >= 40
        # A saturated key colour is never part of the figure: any pocket of it goes. For
        # neutral/muted keys the pocket must also BE the backdrop colour (not skin, not a suit).
        chosen |= ((pocket >= (POCKET_MIN if saturated else max(48, HOLE_SHARE * total)))
                   & (saturated | (exact >= POCKET_EXACT * area)))
        chosen[0] = False
    backdrop = chosen[labels]

    # Opacity inside the removed area from the same level: pure backdrop next to the figure
    # is clear and lone noisy pixels stay clear too.
    if outer > inner:
        t = np.clip((level - inner) / (outer - inner), 0.0, 1.0)
        soft = t * t * (3.0 - 2.0 * t)
    else:
        soft = (level >= inner).astype(np.float32)
    alpha = np.where(backdrop, soft, 1.0).astype(np.float32)
    _rim_alpha(alpha, raw, backdrop)

    # Specks: tiny islands of near-backdrop colour standing alone in the removed area.
    island_count, islands = _components(~backdrop)
    if island_count > 1:
        sizes = np.bincount(islands.ravel(), minlength=island_count)
        closeness = np.bincount(islands.ravel(), weights=near.ravel(), minlength=island_count)
        mean_near = closeness / np.maximum(1, sizes)
        drop = (sizes < max(8, SPECK_SHARE * total)) & (mean_near < outer * 2)
        drop[0] = False
        alpha[drop[islands]] = 0.0

    if previous is not None and previous[0].shape == rgb.shape:
        prev_rgb, prev_alpha = previous
        still = np.abs(rgb - prev_rgb).max(axis=2) < STATIC_DIFF
        alpha = np.where(still, (alpha + prev_alpha) * 0.5, alpha)
    state = (rgb, alpha)

    out = rgb.copy()
    key = np.array(model.key, dtype=np.float32)
    partial = (alpha > 0.0) & (alpha < 1.0)
    if partial.any():
        a = alpha[partial][:, None]
        out[partial] = np.clip((rgb[partial] - (1.0 - a) * key) / np.maximum(a, 0.05), 0.0, 255.0)
    _despill(out, alpha, backdrop, model.key)
    result = np.empty_like(rgba)
    result[..., :3] = np.clip(np.rint(out), 0, 255).astype(np.uint8)
    result[..., 3] = np.clip(np.rint(alpha * src_alpha), 0, 255).astype(np.uint8)
    if np.count_nonzero(result[..., 3] > 16) < max(16, int(total * 0.004)):
        return rgba.copy(), previous  # keyed everything away: the guess was wrong
    return result, state


def _rim_alpha(alpha: np.ndarray, raw: np.ndarray, backdrop: np.ndarray) -> None:
    """Anti-aliased rim: a pixel touching the removed backdrop is a mix of the backdrop and
    its most different neighbour, so its opacity is how far it got towards that neighbour
    (a grey pixel between a black outline and a white backdrop = half-transparent black)."""
    import cv2
    kernel = np.ones((3, 3), np.uint8)
    rim = cv2.dilate(backdrop.astype(np.uint8), kernel).astype(bool) & ~backdrop
    if not rim.any():
        return
    farthest = cv2.dilate(raw.astype(np.float32), kernel)
    share = np.clip(raw / np.maximum(farthest, 1.0), 0.0, 1.0)
    share = np.where(share > 0.92, 1.0, share)
    alpha[rim] = np.minimum(alpha[rim], share[rim])
    # The soft band inside the removed area: the same mixing share, measured against the most
    # different colour within 2 px (a 30 % red / 70 % green pixel is 0.3 opaque, not 0.8).
    band = backdrop & (alpha > 0)
    if band.any():
        farthest = cv2.dilate(raw.astype(np.float32), np.ones((5, 5), np.uint8))
        share = np.clip(raw / np.maximum(farthest, 1.0), 0.0, 1.0)
        share = np.where(share > 0.92, 1.0, share)
        alpha[band] = np.minimum(alpha[band], share[band])


def _despill(out: np.ndarray, alpha: np.ndarray, backdrop: np.ndarray, key) -> None:
    """Pull the key's colour out of the rim (2 px next to the removed backdrop)."""
    ky, kcb, kcr = (float(v) for v in _ycc(np.asarray(key, dtype=np.float64)))
    saturation = float(np.hypot(kcb, kcr))
    if saturation < 40:
        return
    import cv2
    near_backdrop = cv2.dilate(backdrop.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    rim = near_backdrop & (alpha > 0)
    if not rim.any():
        return
    ux, uy = kcb / saturation, kcr / saturation
    y, cb, cr = _ycc(out[rim])
    toward = np.maximum(0.0, cb * ux + cr * uy) * 0.6
    cb = cb - ux * toward
    cr = cr - uy * toward
    out[rim] = np.stack([y + 1.402 * cr, y - 0.344136 * cb - 0.714136 * cr, y + 1.772 * cb], axis=1)


def key_frames(frames, mode: str = "auto", tolerance: float = 45, softness: float = 16,
               holes: bool = True) -> list[np.ndarray]:
    """Key a whole clip with one backdrop model and temporal smoothing (RGBA arrays in, out)."""
    arrays = [np.asarray(frame.convert("RGBA") if hasattr(frame, "convert") else frame, dtype=np.uint8)
              for frame in frames]
    if not arrays:
        return []
    transparent = np.mean([float(np.mean(_ring(a)[:, 3] < 250)) for a in arrays[:4]])
    if (mode or "auto").lower() in ("auto", "a", "color") and transparent > 0.5:
        return [a.copy() for a in arrays]  # a cut-out already: nothing to remove
    model = resolve(mode, estimate(arrays))
    state = None
    keyed = []
    for array in arrays:
        frame_model = model
        if model is not None and len(arrays) > 1 and border_match(array, model) < FOREIGN:
            # An intro/flash frame on another solid colour: key it with its own backdrop.
            own = estimate([array])
            if own is not None and own.coverage >= OWN_BACKDROP and own.spread <= OWN_SPREAD:
                frame_model = resolve(mode, own) or model
        out, state = apply(array, frame_model, tolerance, softness, holes,
                           state if frame_model is model else None)
        keyed.append(out)
    return keyed


def border_match(frame, model: Model) -> float:
    """Share of the frame border (opaque pixels) that is the model's backdrop colour."""
    ring = _ring(np.asarray(frame))
    ring = ring[ring[:, 3] >= 128, :3]
    if not len(ring):
        return 1.0
    return float(np.mean(distance(ring, model.key) < CLUSTER))
