"""Upscale model registry and the HuggingFace call.

Moved out of main.py unchanged; see docs/STRUCTURE.md.
"""


from __future__ import annotations

import hashlib
import hmac
import html
import io
import ipaddress
import json
import logging
import os
import re
import socket
import secrets
import tempfile
import shutil
import time
import uuid
import warnings
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

import processor as proc
import redis_store as rs

import auth_db


# ====================== Public gallery (test) ======================



# ====================== Image Upscale (Hugging Face Space via gradio_client) ======================
# Uses public Space: https://huggingface.co/spaces/Phips/Upscaler
# Caveats: queue / cold start / rate limits on free ZeroGPU — not for production-critical path.

# Labels are UI-facing; keys must match Space dropdown values.
_UPSCALE_MODELS = [
    # Faster / illustration-friendly first
    "4xBHI_dat2_real",
    "4xNomosWebPhoto_RealPLKSR",
    "4xNomos2_hq_drct-l",
    "4xRealWebPhoto_v4_dat2",
    "4xNomosUni_rgt_multijpg",
    "4xLSDIRDAT",
    "4xNomos8kHAT-L_otf",
    "4xNomosUniDAT_otf",
]


_UPSCALE_MODEL_META = {
    "4xBHI_dat2_real": {"label": "Anime / art · fast", "group": "anime"},
    "4xNomosWebPhoto_RealPLKSR": {"label": "Photo · balanced", "group": "photo"},
    "4xNomos2_hq_drct-l": {"label": "General HQ", "group": "general"},
    "4xRealWebPhoto_v4_dat2": {"label": "Photo v4", "group": "photo"},
    "4xNomosUni_rgt_multijpg": {"label": "Universal / jpg", "group": "general"},
    "4xLSDIRDAT": {"label": "Detail (slower)", "group": "general"},
    "4xNomos8kHAT-L_otf": {"label": "8k HAT (slow)", "group": "slow"},
    "4xNomosUniDAT_otf": {"label": "Uni DAT (slow)", "group": "slow"},
}


def _run_hf_upscale(src_path: Path, model: str) -> Path:
    """Blocking call — run inside a threadpool."""
    from gradio_client import Client, handle_file

    model = model if model in _UPSCALE_MODELS else _UPSCALE_MODELS[0]
    client = Client("Phips/Upscaler")
    # API docs: /upscale_image(image, model_selection) -> (slider tuple, filepath)
    result = client.predict(
        handle_file(str(src_path)),
        model,
        api_name="/upscale_image",
    )
    out = None
    if isinstance(result, (list, tuple)):
        # prefer last filepath-like element (full-quality PNG)
        for item in reversed(result):
            if isinstance(item, str) and Path(item).is_file():
                out = Path(item)
                break
            if isinstance(item, dict) and item.get("path"):
                cand = Path(item["path"])
                if cand.is_file():
                    out = cand
                    break
            if isinstance(item, (list, tuple)):
                for sub in reversed(item):
                    if isinstance(sub, str) and Path(sub).is_file():
                        out = Path(sub)
                        break
    elif isinstance(result, str) and Path(result).is_file():
        out = Path(result)
    if out is None or not out.is_file():
        raise RuntimeError(f"Upscaler returned no file: {type(result)} {result!r}"[:300])
    return out
