"""
Shared pytest fixtures for UKIP backend tests.
Uses an isolated in-memory SQLite database so tests never touch sql_app.db.
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ── Use a clean in-memory DB for every test session ────────────────────────
# StaticPool ensures all sessions/connections share the SAME in-memory database.
# Without it, each new connection creates an isolated empty SQLite database.
TEST_DATABASE_URL = "sqlite:///:memory:"

# Patch the database URL before importing app modules.
# ADMIN_PASSWORD is the plain-text password used to bootstrap the super_admin
# on first startup. ADMIN_USERNAME identifies the account.
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ADMIN_USERNAME", "testadmin")
os.environ.setdefault("ADMIN_PASSWORD", "testpassword")


from sqlalchemy import text  # noqa: E402
from backend import models, database  # noqa: E402 — env vars must be set first
from backend.main import app  # noqa: E402

# Override the database engine with the in-memory one
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # All sessions share the same in-memory connection
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create tables in the in-memory DB
models.Base.metadata.create_all(bind=test_engine)

# Override dependency — imported from database to match auth.py's import
from backend.database import get_db  # noqa: E402
app.dependency_overrides[get_db] = override_get_db

# Seed the super_admin in the in-memory test DB so the login fixture works.
# (The lifespan bootstrap uses database.SessionLocal which hits the real DB;
#  this seeds the in-memory DB that test requests use via override_get_db.)
from backend.auth import hash_password as _hash_pw  # noqa: E402
with TestingSessionLocal() as _seed_db:
    if _seed_db.query(models.User).count() == 0:
        _seed_db.add(models.User(
            username=os.environ["ADMIN_USERNAME"],
            password_hash=_hash_pw(os.environ["ADMIN_PASSWORD"]),
            role="super_admin",
            is_active=True,
        ))
        _seed_db.commit()


@pytest.fixture(scope="session")
def client():
    """FastAPI test client with in-memory DB."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="session")
def auth_token(client):
    """Obtain a valid JWT token for the super_admin test account."""
    response = client.post(
        "/auth/token",
        data={"username": "testadmin", "password": "testpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200, f"Auth failed: {response.text}"
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# ── RBAC test users ────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def editor_headers(client, auth_headers):
    """Create an editor user and return its auth headers (session-scoped).
    Token is generated directly (bypasses rate-limited /auth/token endpoint)."""
    from backend.auth import create_access_token as _cat
    resp = client.post(
        "/users",
        json={"username": "test_editor", "password": "editor1234", "role": "editor"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, f"Editor creation failed: {resp.text}"
    token = _cat(subject="test_editor", role="editor")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def viewer_headers(client, auth_headers):
    """Create a viewer user and return its auth headers (session-scoped).
    Token is generated directly (bypasses rate-limited /auth/token endpoint)."""
    from backend.auth import create_access_token as _cat
    resp = client.post(
        "/users",
        json={"username": "test_viewer", "password": "viewer1234", "role": "viewer"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, f"Viewer creation failed: {resp.text}"
    token = _cat(subject="test_viewer", role="viewer")
    return {"Authorization": f"Bearer {token}"}


# ── DB cleanup (function-scoped) ────────────────────────────────────────────

_TABLES_TO_CLEAN = [
    "raw_entities",
    "store_connections",
    "store_sync_mappings",
    "sync_logs",
    "sync_queue",
    "ai_integrations",
    "normalization_rules",
    "harmonization_logs",
    "harmonization_change_records",
    "authority_records",
    # Note: "users" is intentionally excluded — the super_admin/editor/viewer
    # test accounts must persist across the entire test session.
]


@pytest.fixture()
def db_session():
    """
    Provide a DB session for each test, with full table cleanup after the test.

    Because enrichment worker functions call db.commit() internally, nested
    transactions / savepoints are unreliable for isolation on SQLite. Instead
    we truncate the relevant tables after every test.
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Wipe all test data so the next test starts clean
        cleanup_db = TestingSessionLocal()
        try:
            for table in _TABLES_TO_CLEAN:
                cleanup_db.execute(text(f"DELETE FROM {table}"))
            cleanup_db.commit()
        finally:
            cleanup_db.close()
