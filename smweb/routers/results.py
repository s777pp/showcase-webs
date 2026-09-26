"""'My results': finished ZIPs kept for signed-in users (see smweb.saved_results)."""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

import auth_db
from smweb import analytics, object_store, saved_results
from smweb.core import _auth_user

router = APIRouter(prefix="/api/results", tags=["results"])

_PRIVATE = {"Cache-Control": "private, no-store"}


def _user(request: Request):
    user = _auth_user(request)
    if not user:
        return None, JSONResponse({"ok": False, "msg": "Login required"}, status_code=401)
    return user, None


def _row(request: Request, result_id: str):
    user, error = _user(request)
    if error:
        return None, error
    if not saved_results.RESULT_ID.fullmatch(result_id or ""):
        return None, JSONResponse({"ok": False, "msg": "Not found"}, status_code=404)
    row = auth_db.saved_result_get(int(user["id"]), result_id)
    if not row:
        return None, JSONResponse({"ok": False, "msg": "Not found"}, status_code=404)
    return row, None


def _download_name(row: dict) -> str:
    stem = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(row.get("title") or ""))[:40].strip("_")
    return f"showcase_{stem or row['id'][:8]}.zip"


@router.get("")
def list_results(request: Request):
    user, error = _user(request)
    if error:
        return error
    rows = auth_db.saved_results_for_user(int(user["id"]))
    return JSONResponse(
        {"ok": True, "keep_days": saved_results.KEEP_DAYS, "max_items": saved_results.MAX_PER_USER,
         "items": [saved_results.public_row(row) for row in rows]},
        headers=_PRIVATE,
    )


@router.get("/{result_id}/download")
def download_result(result_id: str, request: Request):
    row, error = _row(request, result_id)
    if error:
        return error
    name = _download_name(row)
    analytics.record("zip_download", request=request, user_id=int(row["user_id"]),
                     properties={"mode": str(row.get("mode") or ""), "value": int(row.get("size") or 0)})
    if row.get("storage") == "r2":
        try:
            url = object_store.presigned_get_url(str(row["zip_ref"]), expires=600, download_name=name,
                                                 media_type="application/zip")
        except Exception:
            return JSONResponse({"ok": False, "msg": "Storage unavailable. Try again later."}, status_code=503)
        return RedirectResponse(url, status_code=302, headers=_PRIVATE)
    path = saved_results.local_zip_path(row)
    if not path:
        return JSONResponse({"ok": False, "msg": "Result file is missing"}, status_code=410)
    return FileResponse(path, media_type="application/zip", filename=name, headers=_PRIVATE)


@router.get("/{result_id}/thumb")
def result_thumb(result_id: str, request: Request):
    row, error = _row(request, result_id)
    if error:
        return error
    path = saved_results.thumb_path(int(row["user_id"]), result_id)
    if not path:
        return JSONResponse({"ok": False, "msg": "No preview"}, status_code=404)
    return FileResponse(path, media_type="image/webp", headers={"Cache-Control": "private, max-age=86400"})


@router.delete("/{result_id}")
def delete_result(result_id: str, request: Request):
    user, error = _user(request)
    if error:
        return error
    if not saved_results.RESULT_ID.fullmatch(result_id or "") or not saved_results.delete_result(int(user["id"]), result_id):
        return JSONResponse({"ok": False, "msg": "Not found"}, status_code=404)
    return {"ok": True}
