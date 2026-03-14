"""
Custom Branding Settings endpoints (Sprint 44 / Sprint 76).
  GET    /branding/settings  — PUBLIC (needed at app load before login)
  PUT    /branding/settings  — admin+
  POST   /branding/logo      — admin+  (drag-and-drop logo upload)
  DELETE /branding/logo      — admin+  (remove logo, revert to default icon)
"""
from __future__ import annotations

import logging
import pathlib
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend import models, schemas
from backend.auth import require_role
from backend.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

_STATIC_DIR = pathlib.Path("static")
_MAX_LOGO_BYTES = 2 * 1024 * 1024   # 2 MB
_ALLOWED_MIME: dict[str, str] = {
    "image/png":     "png",
    "image/jpeg":    "jpg",
    "image/jpg":     "jpg",
    "image/svg+xml": "svg",
    "image/webp":    "webp",
    "image/gif":     "gif",
}


def _get_or_create_settings(db: Session) -> models.BrandingSettings:
    s = db.get(models.BrandingSettings, 1)
    if not s:
        s = models.BrandingSettings(id=1)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def _delete_current_logo(settings: models.BrandingSettings) -> None:
    """Remove the previously uploaded logo file from disk (if any)."""
    url = settings.logo_url or ""
    if url.startswith("/static/logo"):
        path = pathlib.Path(url.lstrip("/"))
        if path.exists():
            path.unlink(missing_ok=True)


# ── GET /branding/settings ────────────────────────────────────────────────────

@router.get("/branding/settings", tags=["branding"])
def get_branding_settings(db: Session = Depends(get_db)):
    """Public — returns current branding configuration. No auth required."""
    s = _get_or_create_settings(db)
    return schemas.BrandingSettingsResponse.model_validate(s)


# ── PUT /branding/settings ────────────────────────────────────────────────────

@router.put("/branding/settings", tags=["branding"])
def update_branding_settings(
    payload: schemas.BrandingSettingsUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin")),
):
    s = _get_or_create_settings(db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(s, field, value)
    db.commit()
    db.refresh(s)
    logger.info("Branding settings updated")
    return schemas.BrandingSettingsResponse.model_validate(s)


# ── POST /branding/logo ───────────────────────────────────────────────────────

@router.post("/branding/logo", tags=["branding"])
async def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin")),
):
    """
    Sprint 76 — Upload a logo image via drag & drop.
    Accepts PNG, JPG, SVG, WebP, GIF up to 2 MB.
    Saves to static/logo.<ext>, updates branding_settings.logo_url,
    and returns the public URL path.
    """
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in _ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported image type '{content_type}'. "
                   f"Allowed: {', '.join(_ALLOWED_MIME)}",
        )

    contents = await file.read()
    if len(contents) > _MAX_LOGO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({len(contents) // 1024} KB). Maximum is 2 MB.",
        )

    ext = _ALLOWED_MIME[content_type]
    # Use a stable filename so old files are overwritten on re-upload of same type,
    # but add a short token so browser caches are busted on format change.
    token = uuid.uuid4().hex[:8]
    filename = f"logo_{token}.{ext}"

    _STATIC_DIR.mkdir(parents=True, exist_ok=True)

    dest = _STATIC_DIR / filename
    dest.write_bytes(contents)

    # Remove old uploaded logo (avoid accumulating files)
    s = _get_or_create_settings(db)
    _delete_current_logo(s)

    logo_url = f"/static/{filename}"
    s.logo_url = logo_url
    db.commit()

    logger.info("Logo uploaded: %s (%d bytes)", filename, len(contents))
    return {"logo_url": logo_url, "filename": filename, "size_bytes": len(contents)}


# ── DELETE /branding/logo ─────────────────────────────────────────────────────

@router.delete("/branding/logo", tags=["branding"])
def delete_logo(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin")),
):
    """Remove the uploaded logo and revert to the default icon."""
    s = _get_or_create_settings(db)
    _delete_current_logo(s)
    s.logo_url = ""
    db.commit()
    logger.info("Logo removed — reverted to default icon")
    return {"logo_url": ""}
