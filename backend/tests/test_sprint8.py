"""
Sprint 8 regression tests:
- X-Total-Count header is returned (and accessible via CORS expose_headers)
- Unbounded query params now validate correctly (422 on out-of-range values)
- threshold, per_page, page bounds enforced
"""
import pytest


# ── X-Total-Count header ─────────────────────────────────────────────────────

def test_entities_returns_x_total_count(client, auth_headers):
    response = client.get("/entities", headers=auth_headers)
    assert response.status_code == 200
    assert "x-total-count" in response.headers


def test_entities_grouped_returns_x_total_count(client, auth_headers):
    response = client.get("/entities/grouped", headers=auth_headers)
    assert response.status_code == 200
    assert "x-total-count" in response.headers


# ── threshold validation on /disambiguate ────────────────────────────────────

class TestDisambiguateThreshold:
    def test_threshold_below_zero_returns_422(self, client, auth_headers):
        response = client.get("/disambiguate/brand_capitalized?threshold=-1", headers=auth_headers)
        assert response.status_code == 422

    def test_threshold_above_100_returns_422(self, client, auth_headers):
        response = client.get("/disambiguate/brand_capitalized?threshold=101", headers=auth_headers)
        assert response.status_code == 422

    def test_threshold_zero_accepted(self, client, auth_headers):
        response = client.get("/disambiguate/brand_capitalized?threshold=0", headers=auth_headers)
        assert response.status_code != 422

    def test_threshold_100_accepted(self, client, auth_headers):
        response = client.get("/disambiguate/brand_capitalized?threshold=100", headers=auth_headers)
        assert response.status_code != 422

    def test_threshold_default_accepted(self, client, auth_headers):
        response = client.get("/disambiguate/brand_capitalized", headers=auth_headers)
        assert response.status_code != 422


# ── threshold validation on /authority ───────────────────────────────────────

class TestAuthorityThreshold:
    def test_threshold_below_zero_returns_422(self, client, auth_headers):
        response = client.get("/authority/brand_capitalized?threshold=-5", headers=auth_headers)
        assert response.status_code == 422

    def test_threshold_above_100_returns_422(self, client, auth_headers):
        response = client.get("/authority/brand_capitalized?threshold=200", headers=auth_headers)
        assert response.status_code == 422

    def test_threshold_valid_accepted(self, client, auth_headers):
        response = client.get("/authority/brand_capitalized?threshold=75", headers=auth_headers)
        assert response.status_code != 422


# ── per_page and page validation on /stores/{id}/pull ────────────────────────

class TestStorePullParams:
    def test_per_page_above_200_returns_422(self, client, auth_headers):
        response = client.post(
            "/stores/99/pull?per_page=201",
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_per_page_zero_returns_422(self, client, auth_headers):
        response = client.post(
            "/stores/99/pull?per_page=0",
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_page_zero_returns_422(self, client, auth_headers):
        response = client.post(
            "/stores/99/pull?page=0",
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_valid_params_accepted(self, client, auth_headers):
        """Valid params pass validation (may 404 on missing store — not 422)."""
        response = client.post(
            "/stores/99/pull?page=1&per_page=50",
            headers=auth_headers,
        )
        assert response.status_code != 422
