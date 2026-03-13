"""
Sprint 56 — Notification Center tests.
  GET    /notifications/center             (any auth)
  GET    /notifications/center/unread-count (any auth)
  POST   /notifications/center/read-all    (any auth)
"""
import pytest
from sqlalchemy import text

from backend import models


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_audit(db, action="upload", entity_type="entity", entity_id=None):
    from datetime import datetime, timezone
    e = models.AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        username="testadmin",
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


# ── Auth guards ───────────────────────────────────────────────────────────────

class TestNotificationCenterAuth:
    def test_center_requires_auth(self, client):
        r = client.get("/notifications/center")
        assert r.status_code == 401

    def test_unread_count_requires_auth(self, client):
        r = client.get("/notifications/center/unread-count")
        assert r.status_code == 401

    def test_read_all_requires_auth(self, client):
        r = client.post("/notifications/center/read-all")
        assert r.status_code == 401

    def test_viewer_can_read_center(self, client, viewer_headers):
        r = client.get("/notifications/center", headers=viewer_headers)
        assert r.status_code == 200

    def test_viewer_can_mark_all_read(self, client, viewer_headers):
        r = client.post("/notifications/center/read-all", headers=viewer_headers)
        assert r.status_code == 200


# ── Pagination & shape ────────────────────────────────────────────────────────

class TestNotificationCenterShape:
    def test_empty_feed_returns_valid_structure(self, client, auth_headers, db_session):
        r = client.get("/notifications/center", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "unread_count" in data
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_items_have_required_fields(self, client, auth_headers, db_session):
        _make_audit(db_session, action="upload")
        r = client.get("/notifications/center", headers=auth_headers)
        assert r.status_code == 200
        items = r.json()["items"]
        assert len(items) >= 1
        item = items[0]
        for field in ("id", "action", "label", "icon", "is_read", "created_at"):
            assert field in item, f"Missing field: {field}"

    def test_pagination_skip_limit(self, client, auth_headers, db_session):
        for _ in range(5):
            _make_audit(db_session)
        r1 = client.get("/notifications/center?limit=2&skip=0", headers=auth_headers)
        r2 = client.get("/notifications/center?limit=2&skip=2", headers=auth_headers)
        assert r1.status_code == r2.status_code == 200
        assert len(r1.json()["items"]) == 2
        ids1 = {i["id"] for i in r1.json()["items"]}
        ids2 = {i["id"] for i in r2.json()["items"]}
        assert ids1.isdisjoint(ids2), "Pages must not overlap"

    def test_action_filter(self, client, auth_headers, db_session):
        _make_audit(db_session, action="upload")
        _make_audit(db_session, action="entity.delete")
        r = client.get("/notifications/center?action=upload", headers=auth_headers)
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["action"] == "upload"


# ── Read/unread state ─────────────────────────────────────────────────────────

class TestReadUnreadState:
    def test_new_entries_are_unread(self, client, auth_headers, db_session):
        _make_audit(db_session)
        r = client.get("/notifications/center", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["unread_count"] >= 1
        assert data["items"][0]["is_read"] is False

    def test_mark_all_read_sets_last_read_at(self, client, auth_headers, db_session):
        _make_audit(db_session)
        r = client.post("/notifications/center/read-all", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert body["last_read_at"] is not None

    def test_after_mark_all_read_entries_are_read(self, client, auth_headers, db_session):
        _make_audit(db_session)
        client.post("/notifications/center/read-all", headers=auth_headers)
        r = client.get("/notifications/center", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["unread_count"] == 0
        for item in data["items"]:
            assert item["is_read"] is True

    def test_unread_count_endpoint(self, client, auth_headers, db_session):
        # Reset read state by posting read-all, then add new entry
        client.post("/notifications/center/read-all", headers=auth_headers)
        _make_audit(db_session)
        r = client.get("/notifications/center/unread-count", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["unread_count"] >= 1


# ── Action links ──────────────────────────────────────────────────────────────

class TestActionLinks:
    def test_upload_action_has_href(self, client, auth_headers, db_session):
        _make_audit(db_session, action="upload")
        r = client.get("/notifications/center?action=upload", headers=auth_headers)
        items = r.json()["items"]
        assert items[0]["href"] == "/import-export"

    def test_entity_update_with_id_has_href(self, client, auth_headers, db_session):
        _make_audit(db_session, action="entity.update", entity_id=42)
        r = client.get("/notifications/center?action=entity.update", headers=auth_headers)
        items = r.json()["items"]
        assert items[0]["href"] == "/entities/42"

    def test_entity_delete_has_no_href(self, client, auth_headers, db_session):
        _make_audit(db_session, action="entity.delete")
        r = client.get("/notifications/center?action=entity.delete", headers=auth_headers)
        items = r.json()["items"]
        assert items[0]["href"] is None
