"""
Sprint 62 — Bulk Entity Editor: backend tests.

Tests cover:
  - POST /entities/bulk-update  (batch field updates)
  - Field validation (rejects unknown fields)
  - RBAC: viewer cannot bulk-update
  - Integration with existing bulk delete endpoint
"""

import pytest
from backend import models


# ── helpers ───────────────────────────────────────────────────────────────────

def _seed_entities(db_session, count=5):
    ids = []
    for i in range(count):
        e = models.RawEntity(
            primary_label=f"Test Entity {i}",
            validation_status="pending",
        )
        db_session.add(e)
        db_session.flush()
        ids.append(e.id)
    db_session.commit()
    return ids


# ── Bulk Update ──────────────────────────────────────────────────────────────

class TestBulkUpdate:
    def test_bulk_update_status(self, client, auth_headers, db_session):
        ids = _seed_entities(db_session, 3)
        r = client.post(
            "/entities/bulk-update",
            json={"ids": ids, "updates": {"validation_status": "valid"}},
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["updated"] == 3
        assert "validation_status" in data["fields"]
        # Verify in DB
        for eid in ids:
            e = db_session.get(models.RawEntity, eid)
            db_session.refresh(e)
            assert e.validation_status == "valid"

    def test_bulk_update_multiple_fields(self, client, auth_headers, db_session):
        ids = _seed_entities(db_session, 2)
        r = client.post(
            "/entities/bulk-update",
            json={
                "ids": ids,
                "updates": {
                    "entity_type": "product",
                    "validation_status": "invalid",
                },
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["updated"] == 2
        for eid in ids:
            e = db_session.get(models.RawEntity, eid)
            db_session.refresh(e)
            assert e.entity_type == "product"
            assert e.validation_status == "invalid"

    def test_bulk_update_rejects_unknown_fields(self, client, auth_headers, db_session):
        ids = _seed_entities(db_session, 1)
        r = client.post(
            "/entities/bulk-update",
            json={"ids": ids, "updates": {"nonexistent_field": "value"}},
            headers=auth_headers,
        )
        assert r.status_code == 422
        assert "Invalid fields" in r.json()["detail"]

    def test_bulk_update_partial_ids(self, client, auth_headers, db_session):
        """Only matching IDs get updated, non-existent IDs are silently skipped."""
        ids = _seed_entities(db_session, 2)
        r = client.post(
            "/entities/bulk-update",
            json={"ids": ids + [99999], "updates": {"validation_status": "archived"}},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["updated"] == 2  # only 2 real entities


# ── Bulk Delete (existing — verify still works) ─────────────────────────────

class TestBulkDelete:
    def test_bulk_delete(self, client, auth_headers, db_session):
        ids = _seed_entities(db_session, 4)
        r = client.request(
            "DELETE",
            "/entities/bulk",
            json={"ids": ids[:2]},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["deleted"] == 2
        # Remaining entities still exist
        remaining = db_session.query(models.RawEntity).filter(
            models.RawEntity.id.in_(ids)
        ).count()
        assert remaining == 2


# ── RBAC ──────────────────────────────────────────────────────────────────────

class TestBulkUpdateRBAC:
    def test_viewer_cannot_bulk_update(self, client, viewer_headers, db_session):
        r = client.post(
            "/entities/bulk-update",
            json={"ids": [1], "updates": {"status": "x"}},
            headers=viewer_headers,
        )
        assert r.status_code == 403

    def test_editor_can_bulk_update(self, client, editor_headers, db_session):
        ids = _seed_entities(db_session, 1)
        r = client.post(
            "/entities/bulk-update",
            json={"ids": ids, "updates": {"validation_status": "reviewed"}},
            headers=editor_headers,
        )
        assert r.status_code == 200
        assert r.json()["updated"] == 1
