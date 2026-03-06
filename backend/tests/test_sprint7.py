"""
Sprint 7 regression tests:
- /export requires auth (401 without token)
- /analyze requires auth (401 without token)
- /rag/query requires auth (401 without token)
- 500 responses do NOT leak raw exception strings
- DELETE /entities/all accepts bool query param for include_rules
"""
import pytest


# ── Auth guards on newly-protected endpoints ─────────────────────────────────

def test_export_requires_auth(client):
    response = client.get("/export")
    assert response.status_code == 401


def test_analyze_requires_auth(client):
    response = client.post(
        "/analyze",
        files={"file": ("test.csv", b"a,b\n1,2", "text/csv")},
    )
    assert response.status_code == 401


def test_rag_query_requires_auth(client):
    response = client.post("/rag/query", json={"question": "test"})
    assert response.status_code == 401


def test_export_accessible_with_auth(client, auth_headers):
    """Authenticated request should NOT return 401 (may return 200 or other)."""
    response = client.get("/export", headers=auth_headers)
    assert response.status_code != 401


def test_analyze_accessible_with_auth(client, auth_headers):
    """Authenticated request should NOT return 401."""
    import io
    csv_bytes = b"col_a,col_b\nval1,val2\n"
    response = client.post(
        "/analyze",
        files={"file": ("sample.csv", io.BytesIO(csv_bytes), "text/csv")},
        headers=auth_headers,
    )
    assert response.status_code != 401


# ── 500 responses do not leak internal exception strings ─────────────────────

def test_olap_500_does_not_leak_traceback(client, auth_headers):
    """An unknown domain_id triggers a ValueError from the OLAP engine (404),
    not a raw exception in the body."""
    response = client.get("/olap/nonexistent_domain_xyz", headers=auth_headers)
    # Should be 404 (ValueError path) — crucially, no raw traceback in body
    assert response.status_code in (404, 500)
    body = response.text
    assert "Traceback" not in body
    assert "File \"" not in body


# ── include_rules bool query param ───────────────────────────────────────────

class TestPurgeIncludeRulesBool:
    def test_include_rules_false_is_default(self, client, auth_headers):
        """DELETE /entities/all?include_rules=false should be accepted (not 422)."""
        response = client.delete("/entities/all?include_rules=false", headers=auth_headers)
        assert response.status_code != 422

    def test_include_rules_true_is_accepted(self, client, auth_headers):
        """DELETE /entities/all?include_rules=true should be accepted (not 422)."""
        response = client.delete("/entities/all?include_rules=true", headers=auth_headers)
        assert response.status_code != 422

    def test_include_rules_invalid_returns_422(self, client, auth_headers):
        """Non-boolean value for include_rules should return 422."""
        response = client.delete("/entities/all?include_rules=maybe", headers=auth_headers)
        assert response.status_code == 422
