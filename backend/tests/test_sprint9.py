"""
Sprint 9 regression tests:
- Auth required on store read endpoints (9A)
- Auth required on harmonization read endpoints (9A)
- GET /rules pagination bounds (9B)
- Invalid field names return 400 on /disambiguate and /authority (9C)
- Valid field names accepted (9C)
"""
import pytest


# ── 9A: Store read endpoints require auth ────────────────────────────────────

def test_get_stores_requires_auth(client):
    response = client.get("/stores")
    assert response.status_code == 401


def test_get_store_by_id_requires_auth(client):
    response = client.get("/stores/1")
    assert response.status_code == 401


def test_get_stores_summary_requires_auth(client):
    response = client.get("/stores/stats/summary")
    assert response.status_code == 401


def test_get_store_mappings_requires_auth(client):
    response = client.get("/stores/1/mappings")
    assert response.status_code == 401


def test_get_store_queue_requires_auth(client):
    response = client.get("/stores/1/queue")
    assert response.status_code == 401


def test_get_store_logs_requires_auth(client):
    response = client.get("/stores/1/logs")
    assert response.status_code == 401


# ── 9A: Harmonization read endpoints require auth ────────────────────────────

def test_get_harmonization_steps_requires_auth(client):
    response = client.get("/harmonization/steps")
    assert response.status_code == 401


def test_get_harmonization_logs_requires_auth(client):
    response = client.get("/harmonization/logs")
    assert response.status_code == 401


# ── 9A: Auth users can access protected endpoints ────────────────────────────

def test_get_stores_accessible_with_auth(client, auth_headers):
    response = client.get("/stores", headers=auth_headers)
    assert response.status_code != 401


def test_get_harmonization_steps_accessible_with_auth(client, auth_headers):
    response = client.get("/harmonization/steps", headers=auth_headers)
    assert response.status_code != 401


# ── 9B: GET /rules pagination bounds ────────────────────────────────────────

class TestRulesPagination:
    def test_limit_above_500_returns_422(self, client, auth_headers):
        response = client.get("/rules?limit=501", headers=auth_headers)
        assert response.status_code == 422

    def test_limit_zero_returns_422(self, client, auth_headers):
        response = client.get("/rules?limit=0", headers=auth_headers)
        assert response.status_code == 422

    def test_skip_negative_returns_422(self, client, auth_headers):
        response = client.get("/rules?skip=-1", headers=auth_headers)
        assert response.status_code == 422

    def test_valid_pagination_accepted(self, client, auth_headers):
        response = client.get("/rules?skip=0&limit=50", headers=auth_headers)
        assert response.status_code != 422

    def test_limit_500_accepted(self, client, auth_headers):
        response = client.get("/rules?limit=500", headers=auth_headers)
        assert response.status_code != 422


# ── 9C: Field name validation on /disambiguate and /authority ────────────────

class TestDisambiguateFieldValidation:
    def test_invalid_field_with_spaces_returns_400(self, client, auth_headers):
        response = client.get("/disambiguate/invalid field", headers=auth_headers)
        assert response.status_code == 400

    def test_invalid_field_starts_with_number_returns_400(self, client, auth_headers):
        response = client.get("/disambiguate/1invalid", headers=auth_headers)
        assert response.status_code == 400

    def test_invalid_field_with_special_chars_returns_400(self, client, auth_headers):
        response = client.get("/disambiguate/field;drop--", headers=auth_headers)
        assert response.status_code == 400

    def test_valid_field_accepted(self, client, auth_headers):
        response = client.get("/disambiguate/brand_capitalized", headers=auth_headers)
        assert response.status_code != 400

    def test_valid_field_with_underscores_accepted(self, client, auth_headers):
        response = client.get("/disambiguate/some_field_name", headers=auth_headers)
        assert response.status_code != 400


class TestAuthorityFieldValidation:
    def test_invalid_field_with_special_chars_returns_400(self, client, auth_headers):
        response = client.get("/authority/bad$field", headers=auth_headers)
        assert response.status_code == 400

    def test_invalid_field_starts_with_number_returns_400(self, client, auth_headers):
        response = client.get("/authority/9field", headers=auth_headers)
        assert response.status_code == 400

    def test_valid_field_accepted(self, client, auth_headers):
        response = client.get("/authority/brand_capitalized", headers=auth_headers)
        assert response.status_code != 400
