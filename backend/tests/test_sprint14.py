"""
Sprint 14 regression tests:
- Auth on previously-public GET endpoints (14A)
- Account lockout after 5 failed attempts (14B)
- POST /users/me/password endpoint (14C)
- /health remains public
"""
import pytest
from datetime import datetime, timedelta, timezone

from backend.tests.conftest import TestingSessionLocal
from backend import models


# ── 14A: Previously public endpoints now require auth ─────────────────────────

def test_entities_without_auth_returns_401(client):
    assert client.get("/entities").status_code == 401


def test_entities_with_viewer_returns_200(client, viewer_headers):
    assert client.get("/entities", headers=viewer_headers).status_code == 200


def test_stats_without_auth_returns_401(client):
    assert client.get("/stats").status_code == 401


def test_stats_with_viewer_returns_200(client, viewer_headers):
    assert client.get("/stats", headers=viewer_headers).status_code == 200


def test_brands_without_auth_returns_401(client):
    assert client.get("/brands").status_code == 401


def test_domains_without_auth_returns_401(client):
    assert client.get("/domains").status_code == 401


def test_domains_with_auth_returns_200(client, auth_headers):
    assert client.get("/domains", headers=auth_headers).status_code == 200


def test_rules_without_auth_returns_401(client):
    assert client.get("/rules").status_code == 401


def test_enrich_stats_without_auth_returns_401(client):
    assert client.get("/enrich/stats").status_code == 401


def test_rag_stats_without_auth_returns_401(client):
    assert client.get("/rag/stats").status_code == 401


def test_health_remains_public(client):
    """GET /health must never require authentication (liveness probe)."""
    assert client.get("/health").status_code == 200


# ── 14B: Account lockout ──────────────────────────────────────────────────────

def _do_failed_login(client, username: str, n: int):
    """Perform n failed login attempts for the given username."""
    for _ in range(n):
        client.post(
            "/auth/token",
            data={"username": username, "password": "WRONG_PASSWORD"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )


def test_unknown_user_login_returns_401(client):
    resp = client.post(
        "/auth/token",
        data={"username": "does_not_exist", "password": "whatever"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 401


def test_lockout_after_five_failed_attempts(client, auth_headers, db_session):
    """After 5 consecutive failures the 6th attempt must return 423."""
    # Create a dedicated user so we don't pollute testadmin
    resp = client.post(
        "/users",
        json={"username": "lockout_test_user", "password": "ValidPass1!", "role": "viewer"},
        headers=auth_headers,
    )
    assert resp.status_code == 201

    # 5 wrong-password attempts (rate-limiter is per-IP, tests share 127.0.0.1
    # but the limiter allows 5/min on /auth/token so we call directly via DB)
    with TestingSessionLocal() as db:
        from backend.auth import authenticate_user, _MAX_FAILED_ATTEMPTS
        for _ in range(_MAX_FAILED_ATTEMPTS):
            try:
                authenticate_user(db, "lockout_test_user", "WRONG")
            except Exception:
                pass  # ignore 423 raised mid-loop

        # 6th attempt must raise 423
        import pytest as _pytest
        from fastapi import HTTPException
        with _pytest.raises(HTTPException) as exc_info:
            authenticate_user(db, "lockout_test_user", "WRONG")
        assert exc_info.value.status_code == 423


def test_lockout_blocks_correct_password(client, auth_headers, db_session):
    """While locked out, even the correct password must return 423."""
    resp = client.post(
        "/users",
        json={"username": "lockout_correct_pw", "password": "ValidPass1!", "role": "viewer"},
        headers=auth_headers,
    )
    assert resp.status_code == 201

    with TestingSessionLocal() as db:
        from backend.auth import authenticate_user, _MAX_FAILED_ATTEMPTS
        from fastapi import HTTPException

        # Exhaust attempts
        for _ in range(_MAX_FAILED_ATTEMPTS):
            try:
                authenticate_user(db, "lockout_correct_pw", "WRONG")
            except HTTPException:
                pass

        # Correct password still blocked
        with pytest.raises(HTTPException) as exc_info:
            authenticate_user(db, "lockout_correct_pw", "ValidPass1!")
        assert exc_info.value.status_code == 423


def test_lockout_expires_after_timeout(auth_headers, db_session):
    """After the lock expires, a correct login succeeds again."""
    with TestingSessionLocal() as db:
        from backend.auth import authenticate_user, hash_password
        from backend import models

        # Insert a pre-locked user with an already-expired lock
        expired_lock = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
        user = models.User(
            username="lockout_expired_user",
            password_hash=hash_password("ValidPass1!"),
            role="viewer",
            is_active=True,
            failed_attempts=5,
            locked_until=expired_lock,
        )
        db.add(user)
        db.commit()

        result = authenticate_user(db, "lockout_expired_user", "ValidPass1!")
        assert result is not None
        assert result.username == "lockout_expired_user"


def test_successful_login_resets_failed_attempts(auth_headers, db_session):
    """A successful login resets failed_attempts to 0."""
    with TestingSessionLocal() as db:
        from backend.auth import authenticate_user, hash_password
        from backend import models

        user = models.User(
            username="lockout_reset_user",
            password_hash=hash_password("ValidPass1!"),
            role="viewer",
            is_active=True,
            failed_attempts=3,
            locked_until=None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    with TestingSessionLocal() as db:
        from backend.auth import authenticate_user
        result = authenticate_user(db, "lockout_reset_user", "ValidPass1!")
        assert result is not None
        db.refresh(result)
        assert result.failed_attempts == 0


# ── 14C: Password change endpoint ────────────────────────────────────────────

def test_change_password_without_auth_returns_401(client):
    resp = client.post(
        "/users/me/password",
        json={"current_password": "testpassword", "new_password": "NewSecure1!"},
    )
    assert resp.status_code == 401


def test_change_password_wrong_current_returns_400(client, auth_headers):
    resp = client.post(
        "/users/me/password",
        json={"current_password": "WRONG_PASSWORD", "new_password": "NewSecure1!"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_change_password_too_short_new_returns_422(client, auth_headers):
    resp = client.post(
        "/users/me/password",
        json={"current_password": "testpassword", "new_password": "short"},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_change_password_success_returns_200(client, auth_headers):
    """Change and restore testadmin password so other tests are not affected."""
    original = "testpassword"
    new_pw = "NewSecurePass1!"

    # Change
    resp = client.post(
        "/users/me/password",
        json={"current_password": original, "new_password": new_pw},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Password updated successfully"

    # Restore so the rest of the test session works
    restore = client.post(
        "/users/me/password",
        json={"current_password": new_pw, "new_password": original},
        headers=auth_headers,
    )
    assert restore.status_code == 200
