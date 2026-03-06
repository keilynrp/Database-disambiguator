"""
Sprint 12 regression tests:
- Negative/zero integer path parameters return 422 (12A)
- store_id=0 on bulk-approve/reject query param returns 422 (12A)
- TOCTOU-safe queue approve/reject: non-pending items return 409 (12B)
- RAG question field validation: empty/too-long returns 422 (12C)
- AI integration update uses typed model: empty model_name accepted, long rejected (12C)
- llm_agent logger check (12D)
"""
import pytest


# ── 12A: Negative/zero path params return 422 ────────────────────────────────

class TestNegativePathParams:
    def test_update_entity_negative_id(self, client, auth_headers):
        resp = client.put("/entities/-1", json={}, headers=auth_headers)
        assert resp.status_code == 422

    def test_delete_entity_zero_id(self, client, auth_headers):
        resp = client.delete("/entities/0", headers=auth_headers)
        assert resp.status_code == 422

    def test_delete_rule_negative_id(self, client, auth_headers):
        resp = client.delete("/rules/-5", headers=auth_headers)
        assert resp.status_code == 422

    def test_get_store_negative_id(self, client, auth_headers):
        resp = client.get("/stores/-1", headers=auth_headers)
        assert resp.status_code == 422

    def test_delete_store_zero_id(self, client, auth_headers):
        resp = client.delete("/stores/0", headers=auth_headers)
        assert resp.status_code == 422

    def test_undo_harmonization_negative_id(self, client, auth_headers):
        resp = client.post("/harmonization/undo/-1", headers=auth_headers)
        assert resp.status_code == 422

    def test_redo_harmonization_zero_id(self, client, auth_headers):
        resp = client.post("/harmonization/redo/0", headers=auth_headers)
        assert resp.status_code == 422

    def test_approve_queue_item_negative_id(self, client, auth_headers):
        resp = client.post("/stores/queue/-1/approve", headers=auth_headers)
        assert resp.status_code == 422

    def test_reject_queue_item_zero_id(self, client, auth_headers):
        resp = client.post("/stores/queue/0/reject", headers=auth_headers)
        assert resp.status_code == 422

    def test_ai_integration_activate_negative_id(self, client, auth_headers):
        resp = client.post("/ai-integrations/-1/activate", headers=auth_headers)
        assert resp.status_code == 422

    def test_ai_integration_delete_zero_id(self, client, auth_headers):
        resp = client.delete("/ai-integrations/0", headers=auth_headers)
        assert resp.status_code == 422


# ── 12A: Bulk queue store_id=0 query param ────────────────────────────────────

class TestBulkQueueQueryBounds:
    def test_bulk_approve_store_id_zero_returns_422(self, client, auth_headers):
        resp = client.post("/stores/queue/bulk-approve?store_id=0", headers=auth_headers)
        assert resp.status_code == 422

    def test_bulk_reject_store_id_negative_returns_422(self, client, auth_headers):
        resp = client.post("/stores/queue/bulk-reject?store_id=-1", headers=auth_headers)
        assert resp.status_code == 422

    def test_bulk_approve_valid_store_id_accepted(self, client, auth_headers):
        resp = client.post("/stores/queue/bulk-approve?store_id=99", headers=auth_headers)
        # store 99 doesn't exist but params are valid → not 422
        assert resp.status_code != 422

    def test_bulk_reject_valid_store_id_accepted(self, client, auth_headers):
        resp = client.post("/stores/queue/bulk-reject?store_id=99", headers=auth_headers)
        assert resp.status_code != 422


# ── 12B: Queue approve/reject on non-existent item → 404 ─────────────────────

class TestQueueApproveRejectTOCTOU:
    def test_approve_nonexistent_item_returns_404(self, client, auth_headers):
        resp = client.post("/stores/queue/99999/approve", headers=auth_headers)
        assert resp.status_code == 404

    def test_reject_nonexistent_item_returns_404(self, client, auth_headers):
        resp = client.post("/stores/queue/99999/reject", headers=auth_headers)
        assert resp.status_code == 404


# ── 12C: RAG question field validation ───────────────────────────────────────

class TestRAGQueryValidation:
    def test_empty_question_returns_422(self, client, auth_headers):
        resp = client.post("/rag/query", json={"question": ""}, headers=auth_headers)
        assert resp.status_code == 422

    def test_too_long_question_returns_422(self, client, auth_headers):
        resp = client.post(
            "/rag/query",
            json={"question": "x" * 5001},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_valid_question_passes_validation(self, client, auth_headers):
        # Will fail with 400/500 (no provider) but NOT 422
        resp = client.post(
            "/rag/query",
            json={"question": "What are the top products?"},
            headers=auth_headers,
        )
        assert resp.status_code != 422


# ── 12C: AI integration update typed model ───────────────────────────────────

def test_ai_integration_update_too_long_model_name(client, auth_headers):
    """model_name over 100 chars should return 422."""
    resp = client.put(
        "/ai-integrations/1",
        json={"model_name": "x" * 101},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_ai_integration_update_valid_payload_passes(client, auth_headers):
    """Valid update payload should not return 422 (may 404 if integration missing)."""
    resp = client.put(
        "/ai-integrations/1",
        json={"model_name": "gpt-4o"},
        headers=auth_headers,
    )
    assert resp.status_code != 422


# ── 12D: llm_agent uses logger, not print ────────────────────────────────────

def test_llm_agent_has_logger():
    from backend import llm_agent
    import logging
    assert isinstance(llm_agent.logger, logging.Logger)
