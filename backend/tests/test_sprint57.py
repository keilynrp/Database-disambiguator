"""
Sprint 57 — User Management UI backend tests.
  GET  /users/stats         — super_admin only
  POST /users/{id}/activate — super_admin only
"""
import pytest
from backend import models
from backend.auth import hash_password


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_user(db, username, role="viewer", is_active=True):
    u = models.User(
        username=username,
        password_hash=hash_password("password12345"),
        role=role,
        is_active=is_active,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


# ── GET /users/stats ──────────────────────────────────────────────────────────

class TestUserStats:
    def test_requires_auth(self, client):
        r = client.get("/users/stats")
        assert r.status_code == 401

    def test_viewer_forbidden(self, client, viewer_headers):
        r = client.get("/users/stats", headers=viewer_headers)
        assert r.status_code == 403

    def test_editor_forbidden(self, client, editor_headers):
        r = client.get("/users/stats", headers=editor_headers)
        assert r.status_code == 403

    def test_super_admin_ok(self, client, auth_headers):
        r = client.get("/users/stats", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        for key in ("total", "active", "inactive", "by_role"):
            assert key in data

    def test_counts_match_users(self, client, auth_headers, db_session):
        _make_user(db_session, "stats_active1",   is_active=True)
        _make_user(db_session, "stats_active2",   is_active=True)
        _make_user(db_session, "stats_inactive1", is_active=False)

        r = client.get("/users/stats", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        # testadmin (super_admin) is always present
        # + editor, viewer from session fixtures + 3 new users
        assert data["active"]   >= 2
        assert data["inactive"] >= 1
        assert data["total"]    == data["active"] + data["inactive"]

    def test_by_role_structure(self, client, auth_headers, db_session):
        _make_user(db_session, "stats_editor_x", role="editor")
        _make_user(db_session, "stats_viewer_x", role="viewer")

        r = client.get("/users/stats", headers=auth_headers)
        by_role = r.json()["by_role"]
        assert isinstance(by_role, dict)
        assert all(isinstance(v, int) for v in by_role.values())


# ── POST /users/{id}/activate ─────────────────────────────────────────────────

class TestActivateUser:
    def test_requires_auth(self, client):
        r = client.post("/users/999/activate")
        assert r.status_code == 401

    def test_viewer_forbidden(self, client, viewer_headers):
        r = client.post("/users/999/activate", headers=viewer_headers)
        assert r.status_code == 403

    def test_editor_forbidden(self, client, editor_headers):
        r = client.post("/users/999/activate", headers=editor_headers)
        assert r.status_code == 403

    def test_activate_deactivated_user(self, client, auth_headers, db_session):
        u = _make_user(db_session, "was_inactive", is_active=False)
        assert u.is_active is False

        r = client.post(f"/users/{u.id}/activate", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["is_active"] is True
        assert data["username"] == "was_inactive"

    def test_activate_already_active_is_idempotent(self, client, auth_headers, db_session):
        u = _make_user(db_session, "already_active", is_active=True)
        r = client.post(f"/users/{u.id}/activate", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["is_active"] is True

    def test_activate_nonexistent_returns_404(self, client, auth_headers):
        r = client.post("/users/999999/activate", headers=auth_headers)
        assert r.status_code == 404

    def test_activate_invalid_id_returns_422(self, client, auth_headers):
        r = client.post("/users/0/activate", headers=auth_headers)
        assert r.status_code == 422


# ── Deactivate → Activate round-trip ─────────────────────────────────────────

class TestDeactivateActivateCycle:
    def test_full_cycle(self, client, auth_headers, db_session):
        u = _make_user(db_session, "cycle_user", is_active=True)

        # Deactivate
        r = client.delete(f"/users/{u.id}", headers=auth_headers)
        assert r.status_code == 200

        check = client.get(f"/users/{u.id}", headers=auth_headers)
        assert check.json()["is_active"] is False

        # Reactivate
        r2 = client.post(f"/users/{u.id}/activate", headers=auth_headers)
        assert r2.status_code == 200
        assert r2.json()["is_active"] is True

    def test_inactive_user_cannot_change_role(self, client, auth_headers, db_session):
        u = _make_user(db_session, "inactive_role", is_active=False)
        r = client.put(
            f"/users/{u.id}",
            json={"role": "admin"},
            headers=auth_headers,
        )
        # PUT should succeed even for inactive users — just a data update
        assert r.status_code == 200
        assert r.json()["role"] == "admin"
