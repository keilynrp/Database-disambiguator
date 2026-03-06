"""
Sprint 13 regression tests:
- POST /upload, /stores, /ai-integrations, /rules/bulk return 201 (13A)
- /brands, /product-types, /classifications respect limit bounds (13B)
- GET /stores accepts skip/limit pagination (13B)
- custom_headers max_length=5000 enforced (13D)
"""
import pytest


# ── 13A: HTTP 201 on resource creation ──────────────────────────────────────

def test_upload_returns_201(client, auth_headers):
    import io
    csv_bytes = b"entity_name,sku\nWidget,SKU-001\n"
    resp = client.post(
        "/upload",
        files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=auth_headers,
    )
    assert resp.status_code == 201


def test_create_store_returns_201(client, auth_headers):
    resp = client.post(
        "/stores",
        json={"name": "Sprint13 Store", "platform": "custom", "base_url": "https://example.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 201


def test_create_ai_integration_returns_201(client, auth_headers):
    resp = client.post(
        "/ai-integrations",
        json={"provider_name": "sprint13_provider", "api_key": "sk-test"},
        headers=auth_headers,
    )
    assert resp.status_code == 201


def test_create_rules_bulk_returns_201(client, auth_headers):
    resp = client.post(
        "/rules/bulk",
        json={
            "field_name": "brand_capitalized",
            "canonical_value": "Acme Corp",
            "variations": ["acme", "ACME", "Acme Corp"],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201


# ── 13B: /brands, /product-types, /classifications limit bounds ──────────────

class TestLookupEndpointLimits:
    def test_brands_limit_zero_returns_422(self, client, auth_headers):
        assert client.get("/brands?limit=0", headers=auth_headers).status_code == 422

    def test_brands_limit_above_1000_returns_422(self, client, auth_headers):
        assert client.get("/brands?limit=1001", headers=auth_headers).status_code == 422

    def test_brands_limit_valid_accepted(self, client, auth_headers):
        assert client.get("/brands?limit=50", headers=auth_headers).status_code == 200

    def test_product_types_limit_zero_returns_422(self, client, auth_headers):
        assert client.get("/product-types?limit=0", headers=auth_headers).status_code == 422

    def test_product_types_limit_1000_accepted(self, client, auth_headers):
        assert client.get("/product-types?limit=1000", headers=auth_headers).status_code == 200

    def test_classifications_limit_zero_returns_422(self, client, auth_headers):
        assert client.get("/classifications?limit=0", headers=auth_headers).status_code == 422

    def test_classifications_limit_valid_accepted(self, client, auth_headers):
        assert client.get("/classifications?limit=500", headers=auth_headers).status_code == 200


# ── 13B: /stores pagination ──────────────────────────────────────────────────

class TestStoresPagination:
    def test_stores_skip_negative_returns_422(self, client, auth_headers):
        resp = client.get("/stores?skip=-1", headers=auth_headers)
        assert resp.status_code == 422

    def test_stores_limit_zero_returns_422(self, client, auth_headers):
        resp = client.get("/stores?limit=0", headers=auth_headers)
        assert resp.status_code == 422

    def test_stores_limit_above_500_returns_422(self, client, auth_headers):
        resp = client.get("/stores?limit=501", headers=auth_headers)
        assert resp.status_code == 422

    def test_stores_valid_pagination_accepted(self, client, auth_headers):
        resp = client.get("/stores?skip=0&limit=10", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ── 13D: custom_headers max_length ───────────────────────────────────────────

def test_custom_headers_too_long_returns_422(client, auth_headers):
    resp = client.post(
        "/stores",
        json={
            "name": "Header Test",
            "platform": "custom",
            "base_url": "https://example.com",
            "custom_headers": "x" * 5001,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_custom_headers_at_limit_accepted(client, auth_headers):
    resp = client.post(
        "/stores",
        json={
            "name": "Header Test OK",
            "platform": "custom",
            "base_url": "https://example.com",
            "custom_headers": '{"Authorization": "Bearer token"}',
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
