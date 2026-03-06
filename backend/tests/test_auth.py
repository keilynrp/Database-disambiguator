"""
Tests for backend/auth.py — JWT creation, validation, and login endpoint.
"""
import os
import pytest
from datetime import timedelta
from jose import jwt

# Ensure env vars are set before import (conftest.py handles this,
# but be explicit for isolated runs)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ADMIN_USERNAME", "testadmin")
os.environ.setdefault("ADMIN_PASSWORD", "testpassword")

from backend.auth import (
    authenticate_user,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
)

# Use the same TestingSessionLocal from conftest (shared in-memory DB)
from backend.tests.conftest import TestingSessionLocal


# ── Unit: token creation ─────────────────────────────────────────────────────

def test_create_access_token_contains_subject():
    token = create_access_token(subject="testadmin", role="super_admin")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "testadmin"


def test_create_access_token_has_expiry():
    token = create_access_token(subject="testadmin", role="super_admin")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert "exp" in payload


def test_create_access_token_custom_expiry():
    token = create_access_token(subject="testadmin", role="super_admin", expires_delta=timedelta(minutes=1))
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "testadmin"


# ── Unit: authentication logic ───────────────────────────────────────────────

def test_authenticate_user_correct_credentials():
    with TestingSessionLocal() as db:
        assert authenticate_user(db, "testadmin", "testpassword") is not None


def test_authenticate_user_wrong_password():
    with TestingSessionLocal() as db:
        assert authenticate_user(db, "testadmin", "wrongpassword") is None


def test_authenticate_user_wrong_username():
    with TestingSessionLocal() as db:
        assert authenticate_user(db, "notauser", "testpassword") is None


def test_authenticate_user_empty_credentials():
    with TestingSessionLocal() as db:
        assert authenticate_user(db, "", "") is None


# ── Integration: /auth/token endpoint ───────────────────────────────────────

def test_login_success(client):
    response = client.post(
        "/auth/token",
        data={"username": "testadmin", "password": "testpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client):
    response = client.post(
        "/auth/token",
        data={"username": "testadmin", "password": "wrongpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401


def test_login_wrong_username(client):
    response = client.post(
        "/auth/token",
        data={"username": "nobody", "password": "testpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401


def test_login_missing_fields(client):
    response = client.post("/auth/token", data={})
    assert response.status_code == 422  # Unprocessable entity
