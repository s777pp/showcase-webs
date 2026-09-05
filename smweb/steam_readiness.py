"""Steam showcase readiness analysis.

This module deliberately contains no HTTP or UI code.  The same report can be
used by the standalone checker today and by the Process pipeline/fixer later.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from PIL import Image


STEAM_FILE_LIMIT = 5 * 1024 * 1024
STEAM_ANIMATION_LIMIT_SECONDS = 8.0
SUPPORTED_FORMATS = {"PNG", "JPEG", "GIF"}
_AUXILIARY = re.compile(r"(?:^|/)(?:full_(?:original|with_bars|with_watermark)|preview)(?:\.|$)", re.I)


@dataclass(frozen=True)
class Candidate:
    name: str
    data: bytes


def _display_name(name: str) -> str:
    return str(PurePosixPath((name or "file").replace("\\", "/")))[:240]


def _repair_hex_trailer(data: bytes) -> bytes:
    """Restore a standard trailer in a copy so Pillow can inspect HEX21 files."""
    if not data or data[-1] != 0x21:
        return data
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return data[:-1] + b"\x82"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return data[:-1] + b"\x3b"
    if data.startswith(b"\xff\xd8"):
        return data[:-1] + b"\xd9"
    return data


def inspect_file(candidate: Candidate) -> dict:
    name = _display_name(candidate.name)
    raw = candidate.data
    result = {
        "name": name,
        "size": len(raw),
        "format": "",
        "width": 0,
        "height": 0,
        "animated": False,
        "frames": 1,
        "duration_ms": 0,
        "fps": 0.0,
        "hex21": bool(raw and raw[-1] == 0x21),
        "issues": [],
    }
    if not raw:
        result["issues"].append({"code": "empty", "severity": "fail"})
        return result
    if len(raw) > STEAM_FILE_LIMIT:
        result["issues"].append({
            "code": "file_too_large", "severity": "fail",
            "actual": len(raw), "limit": STEAM_FILE_LIMIT,
        })
    try:
        with Image.open(io.BytesIO(_repair_hex_trailer(raw))) as image:
            result["format"] = str(image.format or "").upper()
            result["width"], result["height"] = map(int, image.size)
            frames = int(getattr(image, "n_frames", 1) or 1)
            result["frames"] = frames
            result["animated"] = frames > 1
            if result["format"] == "GIF" and frames > 1:
                total_ms = 0
                # Steam-ready animations are short; this cap prevents malformed
                # files from keeping a web worker busy indefinitely.
                for index in range(min(frames, 1200)):
                    image.seek(index)
                    total_ms += max(10, int(image.info.get("duration", 100) or 100))
                result["duration_ms"] = total_ms
                result["fps"] = round(frames / (total_ms / 1000), 2) if total_ms else 0.0
                if frames > 1200:
                    result["issues"].append({"code": "too_many_frames", "severity": "fail", "actual": frames})
                if total_ms > int(STEAM_ANIMATION_LIMIT_SECONDS * 1000) + 50:
                    result["issues"].append({
                        "code": "animation_too_long", "severity": "fail",
                        "actual": total_ms, "limit": int(STEAM_ANIMATION_LIMIT_SECONDS * 1000),
                    })
    except Exception:
        result["issues"].append({"code": "unreadable", "severity": "fail"})
        return result

    if result["format"] not in SUPPORTED_FORMATS:
        result["issues"].append({"code": "unsupported_format", "severity": "fail"})
    if result["format"] in SUPPORTED_FORMATS and not result["hex21"]:
        result["issues"].append({"code": "hex21_missing", "severity": "warn"})
    return result


def _mode_from_files(files: list[dict], requested: str) -> str:
    if requested in {"workshop", "featured", "split"}:
        return requested
    names = [PurePosixPath(item["name"]).name.lower() for item in files]
    widths = sorted(int(item.get("width") or 0) for item in files)
    if len(files) == 5 and (
        all(re.search(r"(?:part[_ -]?)?[1-5]", name) for name in names)
        or len(set(widths)) == 1
    ):
        return "workshop"
    if len(files) == 2 and (widths == [100, 506] or any("center_506" in n for n in names)):
        return "split"
    if len(files) == 1 and (widths == [630] or "featured" in names[0]):
        return "featured"
    return "unknown"


def _check(check_id: str, state: str, **details) -> dict:
    return {"id": check_id, "state": state, **details}


def analyze_group(name: str, candidates: list[Candidate], requested_mode: str = "auto") -> dict:
    inspected = [inspect_file(item) for item in candidates]
    for item in inspected:
        item["auxiliary"] = bool(_AUXILIARY.search(item["name"]))
        if item["auxiliary"]:
            item["issues"] = [issue for issue in item["issues"] if issue["code"] != "hex21_missing"]
    primary = [item for item in inspected if not _AUXILIARY.search(item["name"])]
    mode = _mode_from_files(primary, requested_mode)
    checks = []
    format_ok = bool(primary) and all(item["format"] in SUPPORTED_FORMATS for item in primary)
    checks.append(_check("format", "pass" if format_ok else "fail"))
    size_ok = bool(primary) and all(item["size"] <= STEAM_FILE_LIMIT for item in primary)
    checks.append(_check("weight", "pass" if size_ok else "fail", limit=STEAM_FILE_LIMIT))

    geometry_state = "fail"
    set_state = "fail"
    naming_state = "warn"
    if mode == "workshop":
        set_state = "pass" if len(primary) == 5 else "fail"
        same_height = len({item["height"] for item in primary}) == 1 if primary else False
        same_width = len({item["width"] for item in primary}) == 1 if primary else False
        geometry_state = "pass" if len(primary) == 5 and same_height and same_width else "fail"
        part_numbers = sorted(
            int(match.group(1)) for item in primary
            if (match := re.search(r"part[_ -]?([1-5])", PurePosixPath(item["name"]).name, re.I))
        )
        naming_state = "pass" if part_numbers == [1, 2, 3, 4, 5] else "warn"
    elif mode == "featured":
        set_state = "pass" if len(primary) == 1 else "fail"
        geometry_state = "pass" if len(primary) == 1 and primary[0]["width"] == 630 else "fail"
        naming_state = "pass" if len(primary) == 1 and "featured" in primary[0]["name"].lower() else "warn"
    elif mode == "split":
        set_state = "pass" if len(primary) == 2 else "fail"
        widths = sorted(item["width"] for item in primary)
        same_height = len({item["height"] for item in primary}) == 1 if primary else False
        geometry_state = "pass" if len(primary) == 2 and widths == [100, 506] and same_height else "fail"
        names = " ".join(item["name"].lower() for item in primary)
        naming_state = "pass" if "center_506" in names and "side_100" in names else "warn"
    checks.append(_check("geometry", geometry_state, mode=mode))
    checks.append(_check("set", set_state, mode=mode, count=len(primary)))
    checks.append(_check("naming", naming_state, mode=mode))

    gifs = [item for item in primary if item["format"] == "GIF" and item["animated"]]
    animation_state = "pass"
    if any(item["duration_ms"] > int(STEAM_ANIMATION_LIMIT_SECONDS * 1000) + 50 for item in gifs):
        animation_state = "fail"
    checks.append(_check("animation", animation_state, animated=len(gifs)))

    sync_state = "pass"
    if len(gifs) > 1:
        durations = [item["duration_ms"] for item in gifs]
        frames = [item["frames"] for item in gifs]
        fps = [item["fps"] for item in gifs]
        if max(durations) - min(durations) > 60 or len(set(frames)) > 1 or max(fps) - min(fps) > 0.15:
            sync_state = "fail"
    checks.append(_check("sync", sync_state, animated=len(gifs)))

    hex_state = "pass" if primary and all(item["hex21"] for item in primary) else "warn"
    checks.append(_check("hex21", hex_state))

    # Summary counters describe failed preflight stages.  Individual file
    # issues are details of those stages and must not be counted twice.
    failures = sum(check["state"] == "fail" for check in checks)
    warnings = sum(check["state"] == "warn" for check in checks)
    status = "fail" if failures else ("warn" if warnings else "ready")
    return {
        "name": _display_name(name), "mode": mode, "status": status,
        "files": inspected, "primary_count": len(primary), "checks": checks,
        "failures": failures, "warnings": warnings,
    }


def analyze_groups(groups: dict[str, list[Candidate]], requested_mode: str = "auto") -> dict:
    reports = [analyze_group(name, items, requested_mode) for name, items in sorted(groups.items()) if items]
    failures = sum(report["failures"] for report in reports)
    warnings = sum(report["warnings"] for report in reports)
    status = "fail" if failures else ("warn" if warnings else "ready")
    return {
        "status": status, "groups": reports, "group_count": len(reports),
        "file_count": sum(len(report["files"]) for report in reports),
        "failures": failures, "warnings": warnings,
        "limits": {"file_bytes": STEAM_FILE_LIMIT, "animation_ms": int(STEAM_ANIMATION_LIMIT_SECONDS * 1000)},
    }
