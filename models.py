"""Pydantic models for request/response bodies."""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class RegisterBody(BaseModel):
    email: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=6, max_length=128)


class LoginBody(BaseModel):
    email: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=1, max_length=128)


class UnlockBody(BaseModel):
    code: str = Field(..., min_length=4, max_length=64)


class ProfileBody(BaseModel):
    display_name: Optional[str] = Field(None, max_length=40)


class PreviewWmBody(BaseModel):
    """Optional JSON body if used; mostly Form for file."""
    wm_text: str = "n1t1337"
    wm_font: str = "lap"
    wm_opacity: int = 22
    wm_corner: str = "bl"
    wm_scale: float = 1.0
    wm_color: str = "#ffffff"
    auto_contrast: bool = False


class GallerySubmitBody(BaseModel):
    title: str = Field("", max_length=80)
    mode: str = "workshop"
    job_folder: str = ""  # relative path inside job if needed


class GalleryModBody(BaseModel):
    status: str  # approved | rejected
