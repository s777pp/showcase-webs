"""Shared source-media endpoints with resumable chunk uploads."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, Response

import redis_store as rs
from smweb import media_assets


router = APIRouter()


@router.post("/api/assets/uploads")
async def create_upload(request: Request):
    try:
        body = await request.json()
        owner = media_assets.owner_key(request)
        allowed, _ = rs.rate_limit(f"asset-create:{owner}", 40, 3600)
        if not allowed:
            return JSONResponse({"ok": False, "msg": "Too many uploads. Try again later."}, status_code=429)
        asset = media_assets.create_upload(
            owner,
            name=str(body.get("name") or "media"),
            size=int(body.get("size") or 0),
            media_type=str(body.get("type") or ""),
        )
        return JSONResponse({"ok": True, "upload": asset, "chunk_size": media_assets.CHUNK_SIZE}, status_code=201)
    except (TypeError, ValueError) as exc:
        return JSONResponse({"ok": False, "msg": str(exc)}, status_code=400)


@router.get("/api/assets/uploads/{upload_id}")
def upload_status(upload_id: str, request: Request):
    item = media_assets.upload_status(upload_id, media_assets.owner_key(request))
    return {"ok": True, "upload": item} if item else JSONResponse({"ok": False, "msg": "Upload not found"}, status_code=404)


@router.head("/api/assets/uploads/{upload_id}")
def upload_head(upload_id: str, request: Request):
    item = media_assets.upload_status(upload_id, media_assets.owner_key(request))
    if not item:
        return Response(status_code=404)
    return Response(status_code=204, headers={"Upload-Offset": str(item.get("offset") or 0), "Upload-Length": str(item.get("size") or 0)})


@router.patch("/api/assets/uploads/{upload_id}")
async def append_upload(upload_id: str, request: Request):
    try:
        offset = int(request.headers.get("upload-offset") or 0)
        item = await media_assets.append_async(upload_id, media_assets.owner_key(request), offset, request.stream())
        return Response(status_code=204, headers={"Upload-Offset": str(item.get("offset") or 0)})
    except media_assets.OffsetError as exc:
        return JSONResponse({"ok": False, "msg": str(exc), "offset": exc.offset}, status_code=409, headers={"Upload-Offset": str(exc.offset)})
    except FileNotFoundError:
        return JSONResponse({"ok": False, "msg": "Upload not found"}, status_code=404)
    except ValueError as exc:
        return JSONResponse({"ok": False, "msg": str(exc)}, status_code=400)


@router.post("/api/assets/uploads/{upload_id}/complete")
async def complete_upload(upload_id: str, request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        asset = media_assets.complete(upload_id, media_assets.owner_key(request), str(body.get("sha256") or ""))
        return {"ok": True, "asset": asset}
    except FileNotFoundError:
        return JSONResponse({"ok": False, "msg": "Upload not found"}, status_code=404)
    except ValueError as exc:
        return JSONResponse({"ok": False, "msg": str(exc)}, status_code=400)


@router.get("/api/assets")
def assets(request: Request):
    return {"ok": True, "assets": media_assets.list_assets(media_assets.owner_key(request))}


@router.get("/api/assets/{asset_id}/content")
def asset_content(asset_id: str, request: Request, download: bool = False):
    item = media_assets.resolve(asset_id, media_assets.owner_key(request))
    if not item:
        return JSONResponse({"ok": False, "msg": "Asset not found"}, status_code=404)
    meta, path = item
    return FileResponse(
        path,
        media_type=str(meta.get("media_type") or "application/octet-stream"),
        filename=str(meta.get("name") or Path(path).name) if download else None,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.delete("/api/assets/{asset_id}")
def delete_asset(asset_id: str, request: Request):
    if not media_assets.delete_asset(asset_id, media_assets.owner_key(request)):
        return JSONResponse({"ok": False, "msg": "Asset not found"}, status_code=404)
    return {"ok": True}
