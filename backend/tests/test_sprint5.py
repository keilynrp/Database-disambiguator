"""
Sprint 5 regression tests:
- Auth sweep: destructive / expensive endpoints now require a valid token
- Pagination: X-Total-Count header on /entities and /entities/grouped
- Limit cap: limit > 500 returns 422
- Upload guard: 413 on payloads > 20 MB
"""
import io
import pytest


# ── Auth sweep — 401 without token ───────────────────────────────────────────

class TestEntityMutationsRequireAuth:
    def test_update_entity_without_token(self, client):
        response = client.put("/entities/1", json={})
        assert response.status_code == 401

    def test_delete_entity_without_token(self, client):
        response = client.delete("/entities/999")
        assert response.status_code == 401

    def test_purge_all_entities_without_token(self, client):
        response = client.delete("/entities/all")
        assert response.status_code == 401

    def test_upload_without_token(self, client):
        response = client.post(
            "/upload",
            files={"file": ("data.csv", b"col1,col2\nval1,val2", "text/csv")},
        )
        assert response.status_code == 401


class TestEnrichEndpointsRequireAuth:
    def test_enrich_single_without_token(self, client):
        response = client.post("/enrich/row/1")
        assert response.status_code == 401

    def test_enrich_bulk_without_token(self, client):
        response = client.post("/enrich/bulk")
        assert response.status_code == 401


class TestHarmonizationMutationsRequireAuth:
    def test_apply_step_without_token(self, client):
        response = client.post("/harmonization/apply/clean_entity_names")
        assert response.status_code == 401

    def test_apply_all_without_token(self, client):
        response = client.post("/harmonization/apply-all")
        assert response.status_code == 401

    def test_undo_without_token(self, client):
        response = client.post("/harmonization/undo/1")
        assert response.status_code == 401

    def test_redo_without_token(self, client):
        response = client.post("/harmonization/redo/1")
        assert response.status_code == 401


class TestRuleMutationsRequireAuth:
    def test_create_rules_bulk_without_token(self, client):
        response = client.post(
            "/rules/bulk",
            json={"field_name": "brand_lower", "canonical_value": "Canon", "variations": ["canon"]},
        )
        assert response.status_code == 401

    def test_delete_rule_without_token(self, client):
        response = client.delete("/rules/1")
        assert response.status_code == 401

    def test_apply_rules_without_token(self, client):
        response = client.post("/rules/apply")
        assert response.status_code == 401


class TestRAGEndpointsRequireAuth:
    def test_rag_index_without_token(self, client):
        response = client.post("/rag/index")
        assert response.status_code == 401

    def test_rag_clear_index_without_token(self, client):
        response = client.delete("/rag/index")
        assert response.status_code == 401


class TestStoreOperationsRequireAuth:
    def test_test_connection_without_token(self, client):
        response = client.post("/stores/999/test")
        assert response.status_code == 401

    def test_pull_without_token(self, client):
        response = client.post("/stores/999/pull")
        assert response.status_code == 401

    def test_approve_queue_item_without_token(self, client):
        response = client.post("/stores/queue/1/approve")
        assert response.status_code == 401

    def test_reject_queue_item_without_token(self, client):
        response = client.post("/stores/queue/1/reject")
        assert response.status_code == 401

    def test_bulk_approve_without_token(self, client):
        response = client.post("/stores/queue/bulk-approve", params={"store_id": 1})
        assert response.status_code == 401

    def test_bulk_reject_without_token(self, client):
        response = client.post("/stores/queue/bulk-reject", params={"store_id": 1})
        assert response.status_code == 401


# ── Pagination: X-Total-Count + limit cap ─────────────────────────────────────

class TestEntitiesPagination:
    def test_entities_returns_x_total_count_header(self, client, auth_headers):
        response = client.get("/entities", headers=auth_headers)
        assert response.status_code == 200
        assert "x-total-count" in response.headers

    def test_entities_total_count_is_integer(self, client, auth_headers):
        response = client.get("/entities", headers=auth_headers)
        total = int(response.headers["x-total-count"])
        assert total >= 0

    def test_entities_limit_above_500_returns_422(self, client, auth_headers):
        response = client.get("/entities", params={"limit": 501}, headers=auth_headers)
        assert response.status_code == 422

    def test_entities_limit_zero_returns_422(self, client, auth_headers):
        response = client.get("/entities", params={"limit": 0}, headers=auth_headers)
        assert response.status_code == 422

    def test_entities_limit_500_is_valid(self, client, auth_headers):
        response = client.get("/entities", params={"limit": 500}, headers=auth_headers)
        assert response.status_code == 200

    def test_entities_grouped_returns_x_total_count_header(self, client, auth_headers):
        response = client.get("/entities/grouped", headers=auth_headers)
        assert response.status_code == 200
        assert "x-total-count" in response.headers

    def test_entities_grouped_limit_above_500_returns_422(self, client, auth_headers):
        response = client.get("/entities/grouped", params={"limit": 999}, headers=auth_headers)
        assert response.status_code == 422


# ── Upload size guard ─────────────────────────────────────────────────────────

class TestUploadSizeGuard:
    def test_upload_oversized_file_returns_413(self, client, auth_headers):
        # Build a payload just over 20 MB
        oversized = b"A" * (20 * 1024 * 1024 + 1)
        response = client.post(
            "/upload",
            files={"file": ("big.csv", oversized, "text/csv")},
            headers=auth_headers,
        )
        assert response.status_code == 413

    def test_upload_requires_auth_before_size_check(self, client):
        """Without a token, should get 401 regardless of file size."""
        oversized = b"A" * (20 * 1024 * 1024 + 1)
        response = client.post(
            "/upload",
            files={"file": ("big.csv", oversized, "text/csv")},
        )
        assert response.status_code == 401
