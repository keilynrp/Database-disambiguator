"""
Shared dependencies and utility functions used across multiple routers.
"""
import hashlib
import hmac
import json
import logging
import re
import threading
import urllib.request as _urllib_req
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session
from thefuzz import fuzz, process

from backend import database, models
from backend.adapters import get_adapter
from backend.encryption import decrypt

logger = logging.getLogger(__name__)

# Field-name validation regex (reused by disambiguation and authority routers)
_FIELD_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


# ── Audit helper ──────────────────────────────────────────────────────────────

def _audit(
    db: Session,
    action: str,
    user_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    details: dict | None = None,
) -> None:
    """Append a row to audit_logs (does not commit — caller must commit)."""
    entry = models.AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        details=json.dumps(details) if details else None,
    )
    db.add(entry)


# ── Disambiguation helper ─────────────────────────────────────────────────────

def _build_disambig_groups(field: str, threshold: int, db: Session):
    """Shared disambiguation logic reused by /disambiguate and /authority."""
    if not _FIELD_RE.match(field):
        raise ValueError(
            f"Invalid field name '{field}'. Must be 1–64 lowercase alphanumeric/underscore "
            "characters starting with a letter."
        )
    if hasattr(models.RawEntity, field):
        column = getattr(models.RawEntity, field)
        entries = db.query(column).distinct().filter(column != None).all()
        values = [v[0] for v in entries if v[0] and str(v[0]).strip()]
    else:
        # Fallback to normalized JSON data using SQLite JSON extraction function
        json_col = func.json_extract(models.RawEntity.normalized_json, f"$.{field}")
        entries = db.query(json_col).distinct().filter(
            models.RawEntity.normalized_json != None,
            json_col != None,
        ).all()
        values = [v[0] for v in entries if v[0] and str(v[0]).strip()]

    values.sort(key=len, reverse=True)

    groups = []
    processed = set()

    for val in values:
        if val in processed:
            continue
        matches = process.extract(val, values, scorer=fuzz.token_sort_ratio, limit=50)
        group_members = [m[0] for m in matches if m[1] >= threshold]

        if len(group_members) > 1:
            groups.append({
                "main": val,
                "variations": group_members,
                "count": len(group_members),
            })
            for g in group_members:
                processed.add(g)
        else:
            processed.add(val)

    return groups


# ── Webhook dispatcher ────────────────────────────────────────────────────────

def _dispatch_webhook(action: str, payload: dict, db_factory) -> None:
    """Fire-and-forget: send POST to every active webhook subscribed to *action*.
    Runs in a daemon thread so it never blocks the request path.
    """
    def _worker():
        with db_factory() as db:
            hooks = db.query(models.Webhook).filter(
                models.Webhook.is_active == True  # noqa: E712
            ).all()
            body = json.dumps({"event": action, "data": payload}).encode()
            for hook in hooks:
                try:
                    events = json.loads(hook.events or "[]")
                except Exception:
                    events = []
                if action not in events:
                    continue
                headers = {"Content-Type": "application/json", "X-UKIP-Event": action}
                if hook.secret:
                    sig = hmac.new(hook.secret.encode(), body, hashlib.sha256).hexdigest()
                    headers["X-UKIP-Signature"] = f"sha256={sig}"
                req = _urllib_req.Request(hook.url, data=body, headers=headers, method="POST")
                status = 0
                try:
                    with _urllib_req.urlopen(req, timeout=10) as resp:
                        status = resp.status
                except Exception as exc:
                    logger.warning("Webhook %s delivery failed: %s", hook.url, exc)
                hook.last_triggered_at = datetime.now(timezone.utc)
                hook.last_status = status
            db.commit()

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


# ── Store adapter helper ──────────────────────────────────────────────────────

def _get_store_adapter(store: models.StoreConnection):
    """Build adapter from store connection model, decrypting credentials."""
    config = {
        "platform": store.platform,
        "base_url": store.base_url,
        "api_key": decrypt(store.api_key),
        "api_secret": decrypt(store.api_secret),
        "access_token": decrypt(store.access_token),
        "custom_headers": store.custom_headers,
    }
    return get_adapter(store.platform, config)


# ── AI integration helper ─────────────────────────────────────────────────────

def _get_active_integration(db: Session):
    """Return the active AI integration with its api_key decrypted for use.

    The object is expunged from the session before the api_key is overwritten so
    SQLAlchemy cannot flush the plaintext key back to the database.
    """
    integration = (
        db.query(models.AIIntegration)
        .filter(models.AIIntegration.is_active == True)  # noqa: E712
        .first()
    )
    if not integration:
        return None
    db.expunge(integration)  # detach — mutations below are not tracked
    if integration.api_key:
        integration.api_key = decrypt(integration.api_key)
    return integration


# ── Authority record serializer ───────────────────────────────────────────────

def _serialize_authority_record(r: models.AuthorityRecord) -> dict:
    """Convert ORM record to dict, deserializing all JSON fields."""
    return {
        "id":               r.id,
        "field_name":       r.field_name,
        "original_value":   r.original_value,
        "authority_source": r.authority_source,
        "authority_id":     r.authority_id,
        "canonical_label":  r.canonical_label,
        "aliases":          json.loads(r.aliases or "[]"),
        "description":      r.description,
        "confidence":       r.confidence,
        "uri":              r.uri,
        "status":           r.status,
        "created_at":       r.created_at,
        "confirmed_at":     r.confirmed_at,
        # Sprint 16
        "resolution_status": r.resolution_status or "unresolved",
        "score_breakdown":   json.loads(r.score_breakdown or "{}"),
        "evidence":          json.loads(r.evidence or "[]"),
        "merged_sources":    json.loads(r.merged_sources or "[]"),
    }
