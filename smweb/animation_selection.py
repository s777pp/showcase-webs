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
    "hair": "A steady breeze visibly sways the existing hair strands, with smooth continuous motion and natural inertia.",
    "breathing": "Natural rhythmic breathing gently lifts and lowers the chest and shoulders, without changing anatomy or exaggerating body movement.",
    "eyes": "One or two natural blinks, with a subtle lifelike eye movement; preserve the eye shape and facial expression.",
    "cloth": "The existing loose fabric softly flutters in a breeze, with continuous flowing folds.",
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
    amplitudes = {"gentle": "Small but visible", "normal": "Clearly visible moderate", "strong": "Expressive but controlled"}
    prompt = "Animate this exact source image with a locked static camera; no pan, zoom or cuts. "
    prompt += SUBJECTS[selection.subject] + " " + amplitudes[intensity] + " movement throughout the clip. "
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
    prompt += "Keep all other regions stationary. Preserve the original pose and facial expression except for the explicitly requested local motion."
    negative = "no motion, static selected region, camera movement, zoom, cuts, flicker, face distortion, deformed anatomy, extra limbs, new objects, text, watermark"
    if "eyes" not in selection.targets:
        negative += ", blinking, changing eyes"
    if "breathing" not in selection.targets:
        negative += ", moving torso, breathing motion"
    if not ("eyes" in selection.targets or "breathing" in selection.targets):
        negative += ", head rotation, changing facial expression"
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
