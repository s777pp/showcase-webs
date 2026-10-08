"""Depth effects for still pictures ("Depth", Process tab; owner 2026-10-08): one picture + its depth map
(smweb/depth.py) -> a seamless loop. Everything is a function of the loop position u in [0, 1) with whole cycles per
loop, so frame(0) == frame(1) and the GIF never jumps.

Effects (any combination):
  camera      orbit | sway | float | dolly | none  (parallax: near and far parts move differently)
  particles   snow | sakura | rain | sparks | stars, drawn BETWEEN depth layers (hidden behind nearer pixels)
  atmosphere  fog (drifting haze on the far plane) | light (a light band sweeping across the background)
  focuspull   the sharp plane travels far -> near -> far, the rest is blurred
  breath      the user's body region breathes; `chest` adds a soft follow-through bounce of the upper part
  hair        strokes the user painted over the hair sway, more at the tips than at the roots

The same code renders the browser preview (small size, /api/process/depth-preview) and the final clip
(processor.parallax_source), so the preview is exactly what the files will look like. Particles use a fixed seed.
"""
from __future__ import annotations

import math

import numpy as np

CAMERA = ("none", "orbit", "sway", "float", "dolly")
PARTICLES = ("none", "snow", "sakura", "rain", "sparks", "stars")
ATMOSPHERE = ("none", "fog", "light")
SECONDS = 4.0
AMP = 0.012          # camera shift per strength unit, share of the width
ZOOM = 0.06          # dolly zoom per strength unit
MAX_STROKES = 600


def _num(value, default, low, high):
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    if not math.isfinite(number):
        number = default
    return max(low, min(high, number))


def normalize(raw) -> dict | None:
    """Clean options; None when nothing would move. Accepts the first version ({motion, strength, focus}) too."""
    if not isinstance(raw, dict) or raw.get("on") is False:
        return None
    camera = raw.get("camera") if isinstance(raw.get("camera"), dict) else {}
    motion = camera.get("motion", raw.get("motion", "orbit"))
    out = {
        "camera": {"motion": motion if motion in CAMERA else "orbit",
                   "strength": round(_num(camera.get("strength", raw.get("strength")), 1.5, 0.5, 3.0), 2)},
        "focus": round(_num(raw.get("focus"), 0.5, 0.0, 1.0), 2),
        "particles": None, "atmosphere": "none", "focuspull": bool(raw.get("focuspull")), "breath": None, "hair": None,
    }
    particles = raw.get("particles") if isinstance(raw.get("particles"), dict) else {}
    if particles.get("kind") in PARTICLES and particles.get("kind") != "none":
        out["particles"] = {"kind": particles["kind"], "amount": int(round(_num(particles.get("amount"), 2, 1, 3)))}
    if raw.get("atmosphere") in ATMOSPHERE:
        out["atmosphere"] = raw["atmosphere"]
    def strokes_of(block):
        out_strokes = []
        for item in (block.get("strokes") or [])[:MAX_STROKES] if isinstance(block.get("strokes"), list) else []:
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                out_strokes.append([round(_num(item[0], 0, 0, 1), 4), round(_num(item[1], 0, 0, 1), 4),
                                    round(_num(item[2], 0.02, 0.004, 0.2), 4)])
        return out_strokes

    breath = raw.get("breath") if isinstance(raw.get("breath"), dict) else {}
    if breath.get("on"):
        region = breath.get("region") if isinstance(breath.get("region"), dict) else {}
        out["breath"] = {
            "strength": round(_num(breath.get("strength"), 1.5, 0.5, 3.0), 2),
            "chest": round(_num(breath.get("chest"), 0.0, 0.0, 3.0), 2),
            "region": {"cx": round(_num(region.get("cx"), 0.5, 0, 1), 4), "cy": round(_num(region.get("cy"), 0.55, 0, 1), 4),
                       "rx": round(_num(region.get("rx"), 0.16, 0.03, 0.6), 4), "ry": round(_num(region.get("ry"), 0.14, 0.03, 0.6), 4)},
        }
        # Painted body (owner, 2026-10-08: a box was clumsy). When present it replaces the region.
        body_strokes = strokes_of(breath)
        if body_strokes:
            out["breath"]["strokes"] = body_strokes
    hair = raw.get("hair") if isinstance(raw.get("hair"), dict) else {}
    strokes = strokes_of(hair)
    if hair.get("on") and strokes:
        out["hair"] = {"strength": round(_num(hair.get("strength"), 1.5, 0.5, 3.0), 2), "strokes": strokes}
    if (out["camera"]["motion"] == "none" and not out["particles"] and out["atmosphere"] == "none"
            and not out["focuspull"] and not out["breath"] and not out["hair"]):
        return None
    return out


# ---------------------------------------------------------------- precomputed maps
def _smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _periodic_noise(h: int, w: int, rng: np.random.Generator) -> np.ndarray:
    """Soft noise that tiles horizontally (so it can scroll one full width per loop), 0..1."""
    field = np.zeros((h, w), np.float32)
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    for _ in range(9):
        fx = int(rng.integers(1, 5))
        fy = float(rng.uniform(0.5, 3.0))
        phase = float(rng.uniform(0, 2 * math.pi))
        field += np.sin(2 * math.pi * (fx * xs / w) + 2 * math.pi * fy * ys / h + phase).astype(np.float32) / (fx + 1)
    field -= field.min()
    return field / max(1e-6, field.max())


def _sprite_disc(radius: float) -> np.ndarray:
    size = int(math.ceil(radius * 2 + 3))
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32)
    c = (size - 1) / 2
    d = np.sqrt((xs - c) ** 2 + (ys - c) ** 2) / max(0.5, radius)
    return np.clip(1 - d, 0, 1) ** 1.6


def _sprite_petal(length: float, angle: float) -> np.ndarray:
    size = int(math.ceil(length * 2 + 3))
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32)
    c = (size - 1) / 2
    ca, sa = math.cos(angle), math.sin(angle)
    u = ((xs - c) * ca + (ys - c) * sa) / max(1.0, length)
    v = (-(xs - c) * sa + (ys - c) * ca) / max(1.0, length * 0.55)
    return np.clip(1 - (u * u + v * v), 0, 1) ** 0.8


def _sprite_streak(length: float, width: float) -> np.ndarray:
    # Rain falls slightly to the right; the streak is drawn along that direction.
    h = int(math.ceil(length + 4)); w = int(math.ceil(length * 0.1 + width * 2 + 4))
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    line_x = 2 + width + ys * 0.08
    d = np.abs(xs - line_x) / max(0.6, width)
    fade = np.clip(ys / max(1.0, length), 0, 1)
    return np.clip(1 - d, 0, 1) * fade


PARTICLE_STYLE = {
    #           count, colour (RGB), size (share of width), fall cycles, drift, glow
    "snow":   (90, (255, 255, 255), 0.0075, (1, 2), 0.012, 0.0),
    "sakura": (42, (255, 183, 214), 0.013, (1, 1), 0.05, 0.0),
    "rain":   (140, (210, 228, 255), 0.04, (3, 5), 0.0, 0.0),
    "sparks": (55, (255, 196, 110), 0.0055, (1, 2), 0.01, 0.6),
    "stars":  (70, (225, 240, 255), 0.0045, (0, 0), 0.0, 0.5),
}
BUCKETS = (0.28, 0.5, 0.72, 0.95)


class Scene:
    """Everything that does not change between frames, for one picture + options + output size."""

    def __init__(self, pixels: np.ndarray, depth: np.ndarray, options: dict):
        import cv2
        self.cv2 = cv2
        self.options = options
        self.pixels = pixels if pixels.shape[2] == 4 else np.dstack([pixels, np.full(pixels.shape[:2], 255, np.uint8)])
        # A cut-out (the Builder's Character layer) is warped premultiplied, or the colour hidden under transparent
        # pixels bleeds into the edge as a dark fringe; frame() divides it back out. Opaque pictures are unchanged.
        self.premultiplied = bool((self.pixels[..., 3] < 255).any())
        if self.premultiplied:
            alpha = self.pixels[..., 3:4].astype(np.float32) / 255.0
            self.pixels = np.dstack([np.clip(self.pixels[..., :3] * alpha + 0.5, 0, 255).astype(np.uint8), self.pixels[..., 3]])
        self.h, self.w = depth.shape[:2]
        from processor import depth_displacement
        self.disp = depth_displacement(depth)
        self.depth = cv2.GaussianBlur(depth.astype(np.float32), (0, 0), max(1.0, self.w * 0.002))
        self.xs, self.ys = np.meshgrid(np.arange(self.w, dtype=np.float32), np.arange(self.h, dtype=np.float32))
        self.cx, self.cy = (self.w - 1) / 2, (self.h - 1) / 2
        rng = np.random.default_rng(20261008)
        self.blurred = None
        if options["focuspull"]:
            self.blurred = cv2.GaussianBlur(self.pixels, (0, 0), max(1.5, self.w * 0.007))
        self.fog = None
        if options["atmosphere"] == "fog":
            small = _periodic_noise(48, 96, rng)
            self.fog = cv2.resize(small, (self.w, self.h), interpolation=cv2.INTER_CUBIC)
        self.diag = (self.xs * 0.8 + self.ys * 0.6) / (self.w * 0.8 + self.h * 0.6)
        self._breath_maps()
        self._hair_maps()
        self._particles(rng)

    # ---- body region: whole-region breathing weight and the upper part for the chest follow-through
    def _breath_maps(self):
        self.breath = None
        b = self.options["breath"]
        if not b:
            return
        if b.get("strokes"):
            self._breath_from_strokes(b["strokes"])
            return
        r = b["region"]
        cx, cy = r["cx"] * self.w, r["cy"] * self.h
        rx, ry = max(4.0, r["rx"] * self.w), max(4.0, r["ry"] * self.h)
        dist = np.sqrt(((self.xs - cx) / rx) ** 2 + ((self.ys - cy) / ry) ** 2)
        body = _smooth((1.25 - dist) / 0.6)
        cdist = np.sqrt(((self.xs - cx) / (rx * 0.8)) ** 2 + ((self.ys - (cy - ry * 0.18)) / (ry * 0.55)) ** 2)
        chest = _smooth((1.1 - cdist) / 0.55)
        self.breath = {"cx": cx, "cy": cy, "ry": ry, "body": body.astype(np.float32), "chest": chest.astype(np.float32)}

    def _breath_from_strokes(self, strokes):
        """Painted body: a soft mask breathes around its centroid; the chest bounce takes its upper part."""
        cv2 = self.cv2
        mask = np.zeros((self.h, self.w), np.float32)
        for x, y, r in strokes:
            cv2.circle(mask, (int(round(x * self.w)), int(round(y * self.h))), max(1, int(round(r * self.w))), 1.0, -1)
        on = mask > 0.5
        if not on.any():
            return
        ys, xs = np.nonzero(on)
        cx, cy = float(xs.mean()), float(ys.mean())
        top, bottom = float(np.percentile(ys, 2)), float(np.percentile(ys, 98))
        ry = max(4.0, (bottom - top) / 2)
        # A wide feather: the stretch fades out smoothly instead of tearing at the edge of the painting.
        body = cv2.GaussianBlur(mask, (0, 0), max(2.0, self.w * 0.018))
        body = _smooth(np.clip(body / max(1e-6, float(body.max())), 0, 1) * 1.4 - 0.1)
        t = (self.ys - top) / max(1.0, bottom - top)
        chest = body * _smooth((t - 0.05) / 0.2) * _smooth((0.7 - t) / 0.2)
        self.breath = {"cx": cx, "cy": cy, "ry": ry, "body": body.astype(np.float32), "chest": chest.astype(np.float32)}

    # ---- hair: painted mask and how far each pixel is from the roots (top of the mask in its column)
    def _hair_maps(self):
        self.hair = None
        hair = self.options["hair"]
        if not hair:
            return
        cv2 = self.cv2
        mask = np.zeros((self.h, self.w), np.float32)
        for x, y, r in hair["strokes"]:
            cv2.circle(mask, (int(round(x * self.w)), int(round(y * self.h))), max(1, int(round(r * self.w))), 1.0, -1)
        mask = cv2.GaussianBlur(mask, (0, 0), max(1.0, self.w * 0.006))
        # Roots = the top of the whole painted hair, not of each column: strands painted across the face then belong
        # to the still upper part, so the eyes and the fringe never warp (a per-column top let a strand over the
        # face count as a "tip" and dragged the eye beside it; owner sample, 2026-10-08).
        ys_on = np.nonzero(mask > 0.25)[0]
        if ys_on.size:
            top, bottom = float(np.percentile(ys_on, 2)), float(np.percentile(ys_on, 99.5))
        else:
            top, bottom = 0.0, float(self.h)
        tip = np.clip((self.ys - top) / max(self.h * 0.05, bottom - top), 0, 1)
        self.hair = {"mask": np.clip(mask, 0, 1), "tip": tip.astype(np.float32)}

    def _particles(self, rng):
        self.parts = []
        p = self.options["particles"]
        if not p:
            return
        count, color, size, cycles, drift, glow = PARTICLE_STYLE[p["kind"]]
        self.glow = glow
        count = int(count * (0.55, 1.0, 1.7)[p["amount"] - 1])
        for _ in range(count):
            z = float(rng.uniform(0.3, 1.0) ** 0.7) if p["kind"] != "stars" else float(rng.uniform(0.05, 0.35))
            bucket = min(BUCKETS, key=lambda b: abs(b - z))
            scale = 0.55 + 0.9 * z
            self.parts.append({
                "x": float(rng.uniform(0, 1)), "y": float(rng.uniform(0, 1)), "bucket": bucket,
                "size": max(0.6, size * self.w * scale), "fall": int(rng.integers(cycles[0], cycles[1] + 1)) if cycles[1] else 0,
                "drift": drift * float(rng.uniform(0.4, 1.0)), "sway": int(rng.integers(1, 3)), "phase": float(rng.uniform(0, 1)),
                "spin": int(rng.choice([-2, -1, 1, 2])), "alpha": float(rng.uniform(0.75, 1.0)) * (0.7 + 0.3 * z),
            })
        self.color = np.array(color, np.float32) / 255.0
        self.kind = p["kind"]
        self.sprites = {}

    def _sprite(self, key, maker):
        sprite = self.sprites.get(key)
        if sprite is None:
            sprite = self.sprites[key] = maker()
        return sprite

    # ---------------------------------------------------------------- one frame
    def frame(self, u: float) -> np.ndarray:
        cv2 = self.cv2
        o = self.options
        cam = o["camera"]
        motion, strength, focus = cam["motion"], cam["strength"], o["focus"]
        s2, c2 = math.sin(2 * math.pi * u), math.cos(2 * math.pi * u)
        ox, oy, zoom = {"none": (0, 0, 0), "orbit": (c2, 0.55 * s2, 0), "sway": (s2, 0, 0), "float": (0.3 * s2, c2, 0),
                        "dolly": (0, 0, (1 - c2) / 2)}[motion]
        amp = AMP * strength * self.w
        overscan = 1.0 if motion in ("none", "dolly") else 1.0 + 2.4 * AMP * strength
        bx = self.cx + (self.xs - self.cx) / overscan
        by = self.cy + (self.ys - self.cy) / overscan
        k = ZOOM * strength * zoom

        # Body and hair move the picture before the camera looks at it (backward map: subtract the movement).
        ex = np.zeros_like(bx); ey = np.zeros_like(by)
        if self.breath:
            b = o["breath"]
            inhale = math.sin(2 * math.pi * u)
            sy = 1 + 0.010 * b["strength"] * inhale
            sx = 1 + 0.004 * b["strength"] * inhale
            ex += (bx - self.breath["cx"]) * (1 - 1 / sx) * self.breath["body"]
            ey += (by - self.breath["cy"]) * (1 - 1 / sy) * self.breath["body"]
            if b["chest"] > 0:
                # A soft follow-through that lags the breath (whole harmonics, so it loops).
                bounce = 0.7 * math.sin(2 * math.pi * u - 0.9) + 0.3 * math.sin(4 * math.pi * u - 1.7)
                ey += 0.012 * b["chest"] * self.breath["ry"] * bounce * self.breath["chest"]
        if self.hair:
            hs = o["hair"]["strength"]
            tip = self.hair["tip"]
            wave = np.sin(2 * math.pi * (u - 0.35 * tip)).astype(np.float32)
            # The upper part of a strand (fringe over the face, the crown) stays put; only the lower part sways.
            # tip ** 1.5 moved the fringe a few pixels and the eyes under it warped with it (owner sample, 2026-10-08).
            weight = self.hair["mask"] * _smooth((tip - 0.35) / 0.5)
            ex += 0.012 * hs * self.w * weight * wave
            ey += 0.002 * hs * self.w * weight * np.abs(wave)
        bx = bx - ex
        by = by - ey

        def moved(depth_here):
            if motion == "dolly":
                return bx - (bx - self.cx) * k * depth_here, by - (by - self.cy) * k * depth_here
            if motion == "none":
                return bx, by
            shift = (depth_here - focus) * 2
            return bx - ox * amp * shift, by - oy * amp * shift

        sx_, sy_ = moved(cv2.remap(self.disp, bx, by, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE))
        sx_, sy_ = moved(cv2.remap(self.disp, sx_, sy_, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE))
        sx_ = sx_.astype(np.float32); sy_ = sy_.astype(np.float32)
        out = cv2.remap(self.pixels, sx_, sy_, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101).astype(np.float32) / 255.0
        depth_here = cv2.remap(self.depth, sx_, sy_, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

        if self.blurred is not None:
            target = 0.5 + 0.38 * c2
            soft = cv2.remap(self.blurred, sx_, sy_, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101).astype(np.float32) / 255.0
            mix = np.clip(np.abs(depth_here - target) * 2.4 - 0.15, 0, 1)[..., None]
            out = out * (1 - mix) + soft * mix
        far = np.clip(1 - depth_here, 0, 1)
        if self.fog is not None:
            haze = np.roll(self.fog, int(round(u * self.w)), axis=1)
            alpha = (0.42 * haze * far ** 1.6)[..., None]
            out[..., :3] = out[..., :3] * (1 - alpha) + np.array([0.78, 0.84, 0.95], np.float32) * alpha * out[..., 3:4]
        if o["atmosphere"] == "light":
            centre = -0.35 + 1.7 * u
            band = np.exp(-((self.diag - centre) / 0.07) ** 2) * far ** 1.2
            out[..., :3] = np.clip(out[..., :3] + (band * 0.38)[..., None] * np.array([1.0, 0.94, 0.86], np.float32) * out[..., 3:4], 0, 1)
        if self.parts:
            out = self._draw_particles(out, depth_here, u)
        if self.premultiplied:
            cover = out[..., 3:4]
            out[..., :3] = np.where(cover > 1e-4, np.minimum(out[..., :3], cover) / np.maximum(cover, 1e-4), 0)
        return np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8)

    def _draw_particles(self, out, depth_here, u):
        layers = {b: np.zeros((self.h, self.w), np.float32) for b in BUCKETS}
        for p in self.parts:
            kind = self.kind
            alpha = p["alpha"]
            if kind == "stars":
                x, y = p["x"], p["y"]
                alpha *= 0.45 + 0.55 * (0.5 + 0.5 * math.sin(2 * math.pi * (p["sway"] * u + p["phase"])))
                sprite = self._sprite(("disc", round(p["size"], 1)), lambda: _sprite_disc(p["size"]))
            elif kind == "sparks":
                y = (p["y"] - p["fall"] * u) % 1.0
                x = (p["x"] + p["drift"] * math.sin(2 * math.pi * (p["sway"] * u + p["phase"]))) % 1.0
                alpha *= 0.4 + 0.6 * abs(math.sin(2 * math.pi * (2 * p["sway"] * u + p["phase"])))
                sprite = self._sprite(("disc", round(p["size"], 1)), lambda: _sprite_disc(p["size"]))
            elif kind == "rain":
                y = (p["y"] + p["fall"] * u) % 1.0
                x = p["x"]
                sprite = self._sprite(("streak", round(p["size"])), lambda: _sprite_streak(p["size"], max(0.7, p["size"] * 0.05)))
                alpha *= 0.55
            elif kind == "sakura":
                y = (p["y"] + p["fall"] * u) % 1.0
                x = (p["x"] + p["drift"] * math.sin(2 * math.pi * (p["sway"] * u + p["phase"]))) % 1.0
                turn = round(((p["spin"] * u + p["phase"]) % 1.0) * 16) % 16
                sprite = self._sprite(("petal", round(p["size"], 1), turn), lambda: _sprite_petal(p["size"], turn * math.pi / 8))
            else:  # snow
                y = (p["y"] + p["fall"] * u) % 1.0
                x = (p["x"] + p["drift"] * math.sin(2 * math.pi * (p["sway"] * u + p["phase"]))) % 1.0
                sprite = self._sprite(("disc", round(p["size"], 1)), lambda: _sprite_disc(p["size"]))
            self._stamp(layers[p["bucket"]], sprite, x * self.w, y * self.h, alpha)
        for bucket, layer in layers.items():
            if not layer.any():
                continue
            # A particle at depth `bucket` hides behind every pixel nearer than it.
            visible = np.clip((bucket - depth_here) * 14 + 0.5, 0, 1)
            a = np.clip(layer, 0, 1) * visible
            if self.glow:
                # Glowing particles also light up what is around them.
                halo = self.cv2.GaussianBlur(a, (0, 0), max(1.5, self.w * 0.006)) * self.glow * 2.5
                out[..., :3] = np.minimum(1, out[..., :3] + halo[..., None] * self.color * out[..., 3:4])
            # "Over" in premultiplied terms; for an opaque picture alpha stays 1 and the colour maths is the same.
            out[..., :3] = out[..., :3] * (1 - a[..., None]) + self.color * a[..., None]
            out[..., 3] = out[..., 3] * (1 - a) + a
        return out

    def _stamp(self, layer, sprite, x, y, alpha):
        sh, sw = sprite.shape
        x0, y0 = int(round(x - sw / 2)), int(round(y - sh / 2))
        for dx in (0, -self.w, self.w):           # particles wrap around the edges
            for dy in (0, -self.h, self.h):
                ax, ay = x0 + dx, y0 + dy
                l, t = max(0, ax), max(0, ay)
                r, b = min(self.w, ax + sw), min(self.h, ay + sh)
                if r <= l or b <= t:
                    continue
                piece = sprite[t - ay:b - ay, l - ax:r - ax]
                np.maximum(layer[t:b, l:r], piece * alpha, out=layer[t:b, l:r])


def body_guess(depth: np.ndarray) -> dict:
    """A starting body region from the depth map: the nearest blob's upper middle (fractions of the picture)."""
    h, w = depth.shape[:2]
    near = depth > max(0.55, float(np.percentile(depth, 70)))
    if near.sum() < 0.02 * w * h:
        return {"cx": 0.5, "cy": 0.6, "rx": 0.16, "ry": 0.14}
    ys, xs = np.nonzero(near)
    top, bottom = np.percentile(ys, 3), np.percentile(ys, 97)
    left, right = np.percentile(xs, 5), np.percentile(xs, 95)
    band = (ys > top + 0.35 * (bottom - top)) & (ys < top + 0.65 * (bottom - top))
    cx = float(np.median(xs[band])) if band.any() else (left + right) / 2
    return {"cx": round(float(cx) / w, 4), "cy": round(float(top + 0.5 * (bottom - top)) / h, 4),
            "rx": round(float(max(0.06, min(0.3, 0.24 * (right - left) / w))), 4),
            "ry": round(float(max(0.06, min(0.3, 0.17 * (bottom - top) / h))), 4)}
