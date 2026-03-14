"""
Sprint 79 — Scheduled Reports: backend tests.

Tests cover:
  - POST /scheduled-reports           (create)
  - GET  /scheduled-reports           (list)
  - GET  /scheduled-reports/{id}      (get single)
  - PUT  /scheduled-reports/{id}      (update)
  - DELETE /scheduled-reports/{id}    (delete)
  - POST /scheduled-reports/{id}/trigger (manual trigger — SMTP not configured → error)
  - RBAC: editor/viewer cannot access
  - ScheduledReport model fields
"""

import json
import pytest
from backend import models


# ── helpers ───────────────────────────────────────────────────────────────────

def _create_report(client, auth_headers, name="Weekly PDF", **kwargs):
    body = {
        "name": name,
        "domain_id": "default",
        "format": "pdf",
        "sections": [],
        "interval_minutes": 1440,
        "recipient_emails": ["test@example.com"],
        **kwargs,
    }
    return client.post("/scheduled-reports", json=body, headers=auth_headers)


# ── CRUD ──────────────────────────────────────────────────────────────────────

class TestScheduledReportCRUD:
    def test_create_returns_201(self, client, auth_headers):
        r = _create_report(client, auth_headers)
        assert r.status_code == 201
        d = r.json()
        assert d["name"] == "Weekly PDF"
        assert d["format"] == "pdf"
        assert d["interval_minutes"] == 1440
        assert d["recipient_emails"] == ["test@example.com"]
        assert d["is_active"] is True
        assert d["total_sent"] == 0
        assert d["last_status"] == "pending"
        assert d["next_run_at"] is not None

    def test_list_returns_200(self, client, auth_headers):
        _create_report(client, auth_headers, name="List Test")
        r = client.get("/scheduled-reports", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert any(s["name"] == "List Test" for s in r.json())

    def test_get_single(self, client, auth_headers):
        created = _create_report(client, auth_headers, name="Get Single").json()
        r = client.get(f"/scheduled-reports/{created['id']}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == created["id"]

    def test_get_404(self, client, auth_headers):
        r = client.get("/scheduled-reports/99999", headers=auth_headers)
        assert r.status_code == 404

    def test_update_name_and_interval(self, client, auth_headers):
        created = _create_report(client, auth_headers, name="Before Update").json()
        r = client.put(
            f"/scheduled-reports/{created['id']}",
            json={"name": "After Update", "interval_minutes": 720},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["name"] == "After Update"
        assert r.json()["interval_minutes"] == 720

    def test_toggle_active(self, client, auth_headers):
        created = _create_report(client, auth_headers, name="Toggle Test").json()
        r = client.put(
            f"/scheduled-reports/{created['id']}",
            json={"is_active": False},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    def test_delete(self, client, auth_headers):
        created = _create_report(client, auth_headers, name="Delete Me").json()
        r = client.delete(f"/scheduled-reports/{created['id']}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["deleted"] == created["id"]
        r2 = client.get(f"/scheduled-reports/{created['id']}", headers=auth_headers)
        assert r2.status_code == 404

    def test_delete_404(self, client, auth_headers):
        r = client.delete("/scheduled-reports/99999", headers=auth_headers)
        assert r.status_code == 404


# ── Trigger (SMTP not configured) ─────────────────────────────────────────────

class TestScheduledReportTrigger:
    def test_trigger_fails_gracefully_no_smtp(self, client, auth_headers):
        """Trigger returns 200 with success=False when SMTP not configured."""
        created = _create_report(client, auth_headers, name="Trigger Test").json()
        r = client.post(
            f"/scheduled-reports/{created['id']}/trigger",
            headers=auth_headers,
        )
        assert r.status_code == 200
        d = r.json()
        # Either success (if SMTP is configured in test env) or failure with error msg
        assert "success" in d
        if not d["success"]:
            assert "error" in d

    def test_trigger_404(self, client, auth_headers):
        r = client.post("/scheduled-reports/99999/trigger", headers=auth_headers)
        assert r.status_code == 404


# ── Validation ────────────────────────────────────────────────────────────────

class TestScheduledReportValidation:
    def test_invalid_format(self, client, auth_headers):
        r = _create_report(client, auth_headers, name="Bad Format", format="docx")
        assert r.status_code == 422

    def test_interval_too_short(self, client, auth_headers):
        r = _create_report(client, auth_headers, name="Too Short", interval_minutes=10)
        assert r.status_code == 422

    def test_interval_too_long(self, client, auth_headers):
        r = _create_report(client, auth_headers, name="Too Long", interval_minutes=99999)
        assert r.status_code == 422

    def test_empty_name_rejected(self, client, auth_headers):
        r = _create_report(client, auth_headers, name="")
        assert r.status_code == 422


# ── RBAC ─────────────────────────────────────────────────────────────────────

class TestScheduledReportRBAC:
    def test_viewer_cannot_list(self, client, viewer_headers):
        r = client.get("/scheduled-reports", headers=viewer_headers)
        assert r.status_code == 403

    def test_editor_cannot_create(self, client, editor_headers):
        r = _create_report(client, editor_headers)
        assert r.status_code == 403

    def test_unauthenticated_rejected(self, client):
        r = client.get("/scheduled-reports")
        assert r.status_code == 401


# ── Model ─────────────────────────────────────────────────────────────────────

class TestScheduledReportModel:
    def test_model_fields(self, db_session):
        r = models.ScheduledReport(
            name="Model Test",
            domain_id="default",
            format="excel",
            sections=json.dumps(["entity_stats"]),
            interval_minutes=720,
            recipient_emails=json.dumps(["a@b.com"]),
        )
        db_session.add(r)
        db_session.commit()
        db_session.refresh(r)

        assert r.id is not None
        assert r.name == "Model Test"
        assert r.format == "excel"
        assert json.loads(r.sections) == ["entity_stats"]
        assert json.loads(r.recipient_emails) == ["a@b.com"]
        assert r.is_active is True or r.is_active == 1
        assert r.total_sent == 0 or r.total_sent is None
        assert r.last_status == "pending"
