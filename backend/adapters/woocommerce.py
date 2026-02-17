"""
WooCommerce REST API v3 adapter.
Docs: https://woocommerce.github.io/woocommerce-rest-api-docs/
"""
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Optional

from .base import BaseStoreAdapter, RemoteProduct, ConnectionTestResult


class WooCommerceAdapter(BaseStoreAdapter):

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_base = f"{self.base_url}/wp-json/wc/v3"
        self.auth = HTTPBasicAuth(self.api_key or "", self.api_secret or "")

    def _request(self, method: str, endpoint: str, params: dict = None, json_data: dict = None, timeout: int = 30):
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        try:
            resp = requests.request(
                method, url,
                auth=self.auth,
                params=params,
                json=json_data,
                timeout=timeout,
                verify=True,
            )
            resp.raise_for_status()
            return resp
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Cannot connect to {self.base_url}: {e}")
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"WooCommerce API error ({resp.status_code}): {resp.text[:300]}")
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Request to {url} timed out after {timeout}s")

    def test_connection(self) -> ConnectionTestResult:
        try:
            resp = self._request("GET", "system_status")
            data = resp.json()
            env = data.get("environment", {})
            return ConnectionTestResult(
                success=True,
                message="Connected successfully to WooCommerce",
                store_name=env.get("site_title", self.base_url),
                product_count=None,
                api_version=f"WC {data.get('settings', {}).get('version', 'unknown')}",
            )
        except Exception as e:
            return ConnectionTestResult(success=False, message=str(e))

    def _parse_product(self, p: dict) -> RemoteProduct:
        images = [img.get("src", "") for img in p.get("images", []) if img.get("src")]
        tags = [tag.get("name", "") for tag in p.get("tags", [])]
        categories = [cat.get("name", "") for cat in p.get("categories", [])]
        variants = []
        for v in p.get("variations", []):
            variants.append({
                "id": str(v.get("id", "")),
                "sku": v.get("sku", ""),
                "price": v.get("price", ""),
                "stock": str(v.get("stock_quantity", "")),
            })

        return RemoteProduct(
            remote_id=str(p["id"]),
            name=p.get("name", ""),
            canonical_url=p.get("permalink", "") or f"{self.base_url}/?p={p['id']}",
            sku=p.get("sku", ""),
            barcode=p.get("barcode", "") or p.get("global_unique_id", ""),
            price=p.get("price", ""),
            compare_at_price=p.get("regular_price", ""),
            stock=str(p.get("stock_quantity", "")) if p.get("stock_quantity") is not None else None,
            status=p.get("status", ""),
            description=p.get("description", ""),
            short_description=p.get("short_description", ""),
            brand=next((attr["options"][0] for attr in p.get("attributes", []) if attr.get("name", "").lower() in ("marca", "brand") and attr.get("options")), None),
            category=", ".join(categories),
            tags=tags,
            images=images,
            weight=p.get("weight", ""),
            dimensions=f"{p.get('dimensions', {}).get('length', '')}x{p.get('dimensions', {}).get('width', '')}x{p.get('dimensions', {}).get('height', '')}",
            variants=variants,
            raw_data=p,
        )

    def fetch_products(self, page: int = 1, per_page: int = 50) -> List[RemoteProduct]:
        resp = self._request("GET", "products", params={"page": page, "per_page": per_page, "status": "any"})
        products = resp.json()
        return [self._parse_product(p) for p in products]

    def fetch_product_by_id(self, remote_id: str) -> Optional[RemoteProduct]:
        try:
            resp = self._request("GET", f"products/{remote_id}")
            return self._parse_product(resp.json())
        except Exception:
            return None

    def fetch_product_count(self) -> int:
        resp = self._request("GET", "reports/products/totals")
        totals = resp.json()
        return sum(t.get("total", 0) for t in totals)

    def push_product_update(self, remote_id: str, updates: dict) -> bool:
        """Push updates to a WooCommerce product.
        Supported update fields: name, sku, regular_price, sale_price, 
        description, short_description, status, stock_quantity, manage_stock, tags.
        """
        wc_payload = {}
        field_map = {
            "name": "name",
            "sku": "sku",
            "price": "regular_price",
            "description": "description",
            "short_description": "short_description",
            "status": "status",
            "stock": "stock_quantity",
        }
        for local_field, wc_field in field_map.items():
            if local_field in updates:
                wc_payload[wc_field] = updates[local_field]

        if "stock" in updates:
            wc_payload["manage_stock"] = True

        if "tags" in updates and isinstance(updates["tags"], list):
            wc_payload["tags"] = [{"name": t} for t in updates["tags"]]

        try:
            self._request("PUT", f"products/{remote_id}", json_data=wc_payload)
            return True
        except Exception:
            return False
