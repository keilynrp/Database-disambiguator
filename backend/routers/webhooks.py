"""
Webhook management and audit feed endpoints.
  POST   /webhooks
  GET    /webhooks
  GET    /webhooks/{id}
  PUT    /webhooks/{id}
  DELETE /webhooks/{id}
  POST   /webhooks/{id}/test
  GET    /audit/feed
"""
import json

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from backend import models, schemas, database
from backend.auth import get_current_user, require_role
from backend.database import get_db
from backend.routers.deps import _dispatch_webhook

router = APIRouter()


def _serialize_webhook(w: models.Webhook) -> dict:
    events: list = []
    try:
        events = json.loads(w.events or "[]")
    except Exception:
        pass
    return {
        "id": w.id,
        "url": w.url,
        "events": events,
        "is_active": w.is_active,
        "created_at": w.created_at.isoformat() if w.created_at else None,
        "last_triggered_at": w.last_triggered_at.isoformat() if w.last_triggered_at else None,
        "last_status": w.last_status,
    }


@router.post("/webhooks", status_code=201, tags=["webhooks"])
def create_webhook(
    payload: schemas.WebhookCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin")),
):
    hook = models.Webhook(
        url=payload.url,
        events=json.dumps(payload.events),
        secret=payload.secret,
        is_active=True,
    )
    db.add(hook)
    db.commit()
    db.refresh(hook)
    return _serialize_webhook(hook)


@router.get("/webhooks", tags=["webhooks"])
def list_webhooks(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin")),
):
    return [_serialize_webhook(h) for h in db.query(models.Webhook).order_by(models.Webhook.id).all()]


@router.get("/webhooks/{webhook_id}", tags=["webhooks"])
def get_webhook(
    webhook_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin")),
):
    hook = db.get(models.Webhook, webhook_id)
    if hook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return _serialize_webhook(hook)


@router.put("/webhooks/{webhook_id}", tags=["webhooks"])
def update_webhook(
    webhook_id: int = Path(..., ge=1),
    payload: schemas.WebhookUpdate = ...,
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin")),
):
    hook = db.get(models.Webhook, webhook_id)
    if hook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    if payload.url is not None:
        hook.url = payload.url
    if payload.events is not None:
        hook.events = json.dumps(payload.events)
    if payload.secret is not None:
        hook.secret = payload.secret
    if payload.is_active is not None:
        hook.is_active = payload.is_active
    db.commit()
    db.refresh(hook)
    return _serialize_webhook(hook)


@router.delete("/webhooks/{webhook_id}", tags=["webhooks"])
def delete_webhook(
    webhook_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin")),
):
    hook = db.get(models.Webhook, webhook_id)
    if hook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    db.delete(hook)
    db.commit()
    return {"deleted": webhook_id}


@router.post("/webhooks/{webhook_id}/test", tags=["webhooks"])
def test_webhook(
    webhook_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin")),
):
    """Send a synthetic ping payload to verify the endpoint is reachable."""
    hook = db.get(models.Webhook, webhook_id)
    if hook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    _dispatch_webhook("ping", {"message": "UKIP webhook test"}, database.SessionLocal)
    return {"queued": True}


# ── Audit feed ────────────────────────────────────────────────────────────────

_ACTION_ICONS: dict[str, str] = {
    "upload": "📥",
    "entity.update": "✏️",
    "entity.delete": "🗑️",
    "entity.bulk_delete": "🗑️",
    "harmonization.apply": "⚙️",
    "authority.confirm": "✅",
    "authority.reject": "❌",
}


@router.get("/audit/feed", tags=["audit"])
def get_audit_feed(
    limit: int = Query(default=50, ge=1, le=200),
    action: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """Return recent audit log entries, newest first."""
    q = db.query(models.AuditLog)
    if action:
        q = q.filter(models.AuditLog.action == action)
    entries = q.order_by(models.AuditLog.created_at.desc()).limit(limit).all()

    result = []
    for e in entries:
        result.append({
            "id": e.id,
            "action": e.action,
            "icon": _ACTION_ICONS.get(e.action, "📋"),
            "entity_type": e.entity_type,
            "entity_id": e.entity_id,
            "user_id": e.user_id,
            "details": json.loads(e.details) if e.details else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        })
    return result
