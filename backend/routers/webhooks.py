"""
Webhook management, delivery history, and audit feed endpoints.
  POST   /webhooks
  GET    /webhooks
  GET    /webhooks/stats
  GET    /webhooks/{id}
  PUT    /webhooks/{id}
  DELETE /webhooks/{id}
  POST   /webhooks/{id}/test
  GET    /webhooks/{id}/deliveries
  GET    /audit/feed
"""
import json

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from backend import models, schemas, database
from backend.auth import get_current_user, require_role
from backend.database import get_db
from backend.routers.deps import _dispatch_webhook, _dispatch_webhook_sync

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


def _serialize_delivery(d: models.WebhookDelivery) -> dict:
    return {
        "id": d.id,
        "webhook_id": d.webhook_id,
        "event": d.event,
        "url": d.url,
        "status_code": d.status_code,
        "response_body": d.response_body,
        "latency_ms": d.latency_ms,
        "error": d.error,
        "success": d.success,
        "created_at": d.created_at.isoformat() if d.created_at else None,
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


@router.get("/webhooks/stats", tags=["webhooks"])
def webhook_stats(
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin")),
):
    """Summary stats for the webhooks management page."""
    total = db.query(models.Webhook).count()
    active = db.query(models.Webhook).filter(models.Webhook.is_active == True).count()  # noqa: E712
    # Failing = active hooks whose last_status is NOT 2xx (or null)
    failing = db.query(models.Webhook).filter(
        models.Webhook.is_active == True,  # noqa: E712
        models.Webhook.last_status != None,  # noqa: E711
        ~models.Webhook.last_status.between(200, 299),
    ).count()
    total_deliveries = db.query(models.WebhookDelivery).count()
    return {
        "total": total,
        "active": active,
        "inactive": total - active,
        "failing": failing,
        "total_deliveries": total_deliveries,
    }


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
    # Also delete deliveries for this webhook
    db.query(models.WebhookDelivery).filter(
        models.WebhookDelivery.webhook_id == webhook_id
    ).delete()
    db.delete(hook)
    db.commit()
    return {"deleted": webhook_id}


@router.post("/webhooks/{webhook_id}/test", tags=["webhooks"])
def test_webhook(
    webhook_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin")),
):
    """Send a synchronous ping to the webhook and return real delivery results."""
    hook = db.get(models.Webhook, webhook_id)
    if hook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    result = _dispatch_webhook_sync(
        "ping",
        {"message": "UKIP webhook test"},
        hook,
        db,
    )
    return result


@router.get("/webhooks/{webhook_id}/deliveries", tags=["webhooks"])
def list_deliveries(
    webhook_id: int = Path(..., ge=1),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: models.User = Depends(require_role("super_admin", "admin")),
):
    """Paginated delivery history for a single webhook, newest first."""
    hook = db.get(models.Webhook, webhook_id)
    if hook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    q = db.query(models.WebhookDelivery).filter(
        models.WebhookDelivery.webhook_id == webhook_id
    ).order_by(models.WebhookDelivery.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    return {
        "items": [_serialize_delivery(d) for d in items],
        "total": total,
        "page": page,
        "size": size,
    }


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

