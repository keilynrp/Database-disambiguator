"""
Sprint 6 regression tests:
- /health endpoint returns DB status
- Store schema: invalid platform/sync_direction → 422
- Rate-limit enforced on /auth/token (429 after exceeding 5/min)
"""
import pytest


# ── /health ───────────────────────────────────────────────────────────────────

def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_contains_status_field(client):
    body = client.get("/health").json()
    assert "status" in body
    assert body["status"] in ("ok", "degraded")


def test_health_contains_database_field(client):
    body = client.get("/health").json()
    assert "database" in body
    assert body["database"] in ("ok", "error")


def test_health_database_is_ok_with_in_memory_db(client):
    """The in-memory SQLite DB used in tests should always be reachable."""
    body = client.get("/health").json()
    assert body["database"] == "ok"
    assert body["status"] == "ok"


# ── Store schema validation ───────────────────────────────────────────────────

class TestStoreSchemaValidation:
    def test_invalid_platform_returns_422(self, client, auth_headers):
        response = client.post(
            "/stores",
            json={"name": "Test", "platform": "magento", "base_url": "https://x.com"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_valid_platform_accepted(self, client, auth_headers):
        response = client.post(
            "/stores",
            json={"name": "Test WC", "platform": "woocommerce", "base_url": "https://x.com"},
            headers=auth_headers,
        )
        # 200 (created) or 400 (platform check) — NOT 422
        assert response.status_code != 422

    def test_invalid_sync_direction_returns_422(self, client, auth_headers):
        response = client.post(
            "/stores",
            json={
                "name": "Test",
                "platform": "woocommerce",
                "base_url": "https://x.com",
                "sync_direction": "sideways",
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_valid_sync_directions_accepted(self, client, auth_headers):
        for direction in ("pull", "push", "bidirectional"):
            response = client.post(
                "/stores",
                json={
                    "name": f"Test {direction}",
                    "platform": "woocommerce",
                    "base_url": "https://x.com",
                    "sync_direction": direction,
                },
                headers=auth_headers,
            )
            assert response.status_code != 422, f"sync_direction='{direction}' should be valid"

    def test_update_store_invalid_platform_returns_422(self, client, auth_headers):
        response = client.put(
            "/stores/1",
            json={"platform": "unknown_platform"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_update_store_invalid_sync_direction_returns_422(self, client, auth_headers):
        response = client.put(
            "/stores/1",
            json={"sync_direction": "both"},
            headers=auth_headers,
        )
        assert response.status_code == 422


# ── Rate-limit enforcement on /auth/token ────────────────────────────────────

def test_auth_token_rate_limit_enforced(client):
    """After exceeding 5 req/min, /auth/token returns 429.

    SlowAPIMiddleware does not inject X-RateLimit-* headers in TestClient
    (ASGI transport doesn't propagate them), but the @limiter.limit decorator
    still enforces the limit and raises HTTP 429.  We fire 10 rapid requests
    and assert at least one is rejected.
    """
    statuses = []
    for _ in range(10):
        r = client.post(
            "/auth/token",
            data={"username": "testadmin", "password": "testpassword"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        statuses.append(r.status_code)
    assert 429 in statuses, (
        f"Expected at least one 429 after exceeding rate limit, got: {statuses}"
    )
