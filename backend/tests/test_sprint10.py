"""
Sprint 10 regression tests:
- Adapter silent-failure paths now log (behaviour unchanged — still return None/False/0)
- Store name is stripped of surrounding whitespace on create and update
- Rule-application loop logs (not silently swallows) per-entity exceptions
- _get_active_integration detaches ORM object before decrypting (no flush risk)
"""
import pytest


# ── Store name stripping ────────────────────────────────────────────────────

class TestStoreNameStripping:
    def _create_store(self, client, auth_headers, name: str):
        return client.post(
            "/stores",
            json={
                "name": name,
                "platform": "custom",
                "base_url": "https://example.com",
            },
            headers=auth_headers,
        )

    def test_create_store_strips_leading_whitespace(self, client, auth_headers):
        response = self._create_store(client, auth_headers, "  My Store")
        assert response.status_code == 201
        # Fetch the created store and verify name is stripped
        store_id = response.json()["id"]
        detail = client.get(f"/stores/{store_id}", headers=auth_headers)
        assert detail.status_code == 200
        assert detail.json()["name"] == "My Store"

    def test_create_store_strips_trailing_whitespace(self, client, auth_headers):
        response = self._create_store(client, auth_headers, "My Store   ")
        assert response.status_code == 201
        store_id = response.json()["id"]
        detail = client.get(f"/stores/{store_id}", headers=auth_headers)
        assert detail.json()["name"] == "My Store"

    def test_create_store_strips_both_sides(self, client, auth_headers):
        response = self._create_store(client, auth_headers, "  Padded  ")
        assert response.status_code == 201
        store_id = response.json()["id"]
        detail = client.get(f"/stores/{store_id}", headers=auth_headers)
        assert detail.json()["name"] == "Padded"

    def test_update_store_strips_name(self, client, auth_headers):
        create_resp = self._create_store(client, auth_headers, "Original")
        store_id = create_resp.json()["id"]

        update_resp = client.put(
            f"/stores/{store_id}",
            json={"name": "  Updated  "},
            headers=auth_headers,
        )
        assert update_resp.status_code == 200

        detail = client.get(f"/stores/{store_id}", headers=auth_headers)
        assert detail.json()["name"] == "Updated"


# ── Rule application endpoint still works after logging fix ─────────────────

def test_apply_rules_returns_200(client, auth_headers):
    """POST /rules/apply should return 200 even with no entities (not 500)."""
    response = client.post("/rules/apply", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "rules_applied" in data
    assert "records_updated" in data


# ── Adapter module smoke tests (import & instantiation) ─────────────────────

class TestAdapterLoggingImports:
    """Verify each adapter module can be imported and has a logger."""

    def test_woocommerce_adapter_has_logger(self):
        from backend.adapters import woocommerce
        import logging
        assert isinstance(woocommerce.logger, logging.Logger)

    def test_shopify_adapter_has_logger(self):
        from backend.adapters import shopify
        import logging
        assert isinstance(shopify.logger, logging.Logger)

    def test_bsale_adapter_has_logger(self):
        from backend.adapters import bsale
        import logging
        assert isinstance(bsale.logger, logging.Logger)

    def test_custom_adapter_has_logger(self):
        from backend.adapters import custom
        import logging
        assert isinstance(custom.logger, logging.Logger)
