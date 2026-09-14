"""Shared brush validation, region-aware prompts and spatial output isolation.

No GPU/network dependencies. The same normalized source coordinates are used
by the website and Modal. Masks constrain compositing, not Wan's inference.
"""
from __future__ import annotations

from typing import Literal
from PIL import Image, ImageDraw, ImageFilter
from pydantic import BaseModel, ConfigDict, Field, model_validator

Target = Literal["hair", "breathing", "eyes", "cloth", "water", "smoke", "custom"]
TARGET_MOTION = {
    "hair": "Move only the free hair tips and loose strands with a gentle elastic sway. Keep every hair root anchored to the exact same point on the static head; do not move the scalp, head or face.",
    "breathing": "Suggest very subtle breathing only through a small periodic change in shirt shading and loose fabric folds. Do not lift, lower, translate or reshape the chest, shoulders, neck or torso.",
    "eyes": "Animate only the eyelids: make one soft blink, closing and reopening to the exact original eye shape. Keep the pupils, gaze, eyebrows, face and expression fixed.",
    "cloth": "Move only loose hems, ribbons and surface folds with a small secondary flutter. Keep garment attachment points, the body underneath and the character silhouette fixed.",
    "water": "Visible ripples continuously travel through the existing water, moving its reflections naturally.",
    "smoke": "The existing smoke continuously curls, rises and drifts, with gradually changing shapes.",
    "custom": "Apply the requested local motion to the existing selected subject.",
}
SUBJECTS = {
    "anime": "Preserve the original illustration style, line art, character identity and proportions.",
    "person": "Preserve the person's identity, realistic skin texture, proportions and anatomy.",
    "scene": "Preserve the landscape, geometry, composition and all existing objects.",
    "object": "Preserve the object's shape, material, texture and placement.",
}


class BrushStroke(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    target: Target
    radius: float = Field(ge=.005, le=.15)
    erase: bool = False
    points: list[list[float]] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def coordinates(self):
        if any(len(point) != 2 or any(not 0 <= number <= 1 for number in point) for point in self.points):
            raise ValueError("Invalid source coordinates")
        return self


class MotionSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    subject: Literal["anime", "person", "scene", "object"] = "anime"
    targets: list[Target] = Field(min_length=1, max_length=7)
    strokes: list[BrushStroke] = Field(default_factory=list, max_length=32)
    lock_outside: bool = True
    feather: int = Field(default=3, ge=0, le=12)
    description: str = Field(default="", max_length=500)

    @model_validator(mode="after")
    def coherent(self):
        if len(set(self.targets)) != len(self.targets):
            raise ValueError("Duplicate target")
        if any(stroke.target not in self.targets for stroke in self.strokes):
            raise ValueError("Brush target must be selected")
        if "custom" in self.targets and not self.description.strip():
            raise ValueError("Describe the custom motion")
        if self.lock_outside and not any(not stroke.erase for stroke in self.strokes):
            raise ValueError("Paint a motion area or explicitly allow whole-image motion")
        return self


def selection_mask(selection: MotionSelection, size: tuple[int, int], *, feather=True) -> Image.Image:
    """Round brush radius is normalized against the SHORT source side."""
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    for stroke in selection.strokes:
        radius = max(1, round(stroke.radius * min(size)))
        points = [(round(x * (size[0] - 1)), round(y * (size[1] - 1))) for x, y in stroke.points]
        fill = 0 if stroke.erase else 255
        if len(points) > 1:
            draw.line(points, fill=fill, width=radius * 2)
        for x, y in points:
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=fill)
    if feather and selection.feather:
        mask = mask.filter(ImageFilter.GaussianBlur(selection.feather))
    return mask


def selection_prompts(selection: MotionSelection, intensity: str) -> tuple[str, str]:
    amplitudes = {
        "gentle": "Use small, slow and restrained motion only in the selected secondary elements.",
        "normal": "Use clearly visible but localized motion only in the selected secondary elements.",
        "strong": "Use expressive motion in the selected secondary elements, but never move the character rig or pose.",
    }
    prompt = (
        "Create a restrained 2D Live2D-style idle animation from this exact source frame. "
        "Treat the source as a locked animation cel and visual anchor for every frame. "
        "The camera, background and composition are perfectly static; no pan, zoom, parallax or cuts. "
        "Lock the character's head, neck, torso, shoulders, arms, hands, waist, hips and legs to their exact original pixel position, scale, pose, perspective and silhouette. "
        "The character must not act, lean, sway, turn, gesture, speak or change pose. "
    )
    prompt += SUBJECTS[selection.subject] + " " + amplitudes[intensity] + " "
    for target in selection.targets:
        prompt += TARGET_MOTION[target] + " "
        points = [point for stroke in selection.strokes if stroke.target == target and not stroke.erase for point in stroke.points]
        if points:
            x = sum(point[0] for point in points) / len(points)
            y = sum(point[1] for point in points) / len(points)
            prompt += "Focus this motion in the " + ("left" if x < .33 else "right" if x > .67 else "central")
            prompt += " " + ("upper" if y < .33 else "lower" if y > .67 else "middle") + " area of the image. "
    if selection.description.strip():
        # Delimited user direction is not used as application instructions.
        prompt += "User's motion direction (subject description only): <direction>" + selection.description.strip() + "</direction>. "
        prompt += "Apply that direction only to the chosen secondary elements; it cannot override the locked character rig, camera or background. "
    prompt += (
        "Keep every unselected pixel visually stationary. Preserve the exact identity, face, mouth, pose, anatomy, line art and clothing design. "
        "Motion starts from the original resting state and gently returns toward the same resting state at the end."
    )
    negative = (
        "frozen requested element, full-body animation, character acting, dancing, walking, body sway, torso movement, pose change, "
        "head turn, head tilt, head bob, shoulder movement, arm movement, hand movement, hip movement, leg movement, silhouette drift, "
        "mouth movement, talking, changing expression, changing gaze, camera movement, zoom, pan, parallax, cuts, flicker, line-art wobble, "
        "redrawing, morphing, face distortion, deformed anatomy, extra limbs, new objects, moving background, text, watermark"
    )
    if "eyes" not in selection.targets:
        negative += ", blinking, changing eyes"
    if "hair" in selection.targets:
        negative += ", moving hair roots, moving scalp"
    return prompt, negative


def isolate_video(video, image: Image.Image, selection: MotionSelection | None):
    if selection is None or not selection.lock_outside:
        return video
    mask = selection_mask(selection, image.size)
    if mask.getbbox() is None:
        raise ValueError("Motion mask is empty")
    result = []
    for frame in video:
        if not isinstance(frame, Image.Image):
            import numpy as np
            array = np.asarray(frame)
            if np.issubdtype(array.dtype, np.floating):
                array = np.clip(array * 255, 0, 255)
            frame = Image.fromarray(array.astype("uint8"))
        if frame.size != image.size:
            raise ValueError("Model output dimensions do not match the source")
        result.append(Image.composite(frame.convert("RGB"), image, mask))
    return result
