"""
Bsale API adapter.
Docs: https://www.bsale.com.pe/docs/api/
"""
import requests
from typing import List, Optional

from .base import BaseStoreAdapter, RemoteProduct, ConnectionTestResult


class BsaleAdapter(BaseStoreAdapter):

    def __init__(self, config: dict):
        super().__init__(config)
        # Bsale uses access_token in header
        self.api_base = f"{self.base_url}/v1" if "/v1" not in self.base_url else self.base_url
        self.headers = {
            "access_token": self.access_token or "",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, endpoint: str, params: dict = None, json_data: dict = None, timeout: int = 30):
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        try:
            resp = requests.request(
                method, url,
                headers=self.headers,
                params=params,
                json=json_data,
                timeout=timeout,
            )
            resp.raise_for_status()
            return resp
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Cannot connect to {self.base_url}: {e}")
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Bsale API error ({resp.status_code}): {resp.text[:300]}")
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Request to {url} timed out after {timeout}s")

    def test_connection(self) -> ConnectionTestResult:
        try:
            resp = self._request("GET", "products.json", params={"limit": 1})
            data = resp.json()
            count = data.get("count", 0)
            return ConnectionTestResult(
                success=True,
                message="Connected successfully to Bsale",
                store_name="Bsale Store",
                product_count=count,
                api_version="Bsale v1",
            )
        except Exception as e:
            return ConnectionTestResult(success=False, message=str(e))

    def _parse_product(self, p: dict) -> RemoteProduct:
        variants = []
        for v in p.get("variants", {}).get("items", []):
            variants.append({
                "id": str(v.get("id", "")),
                "sku": v.get("code", ""),
                "barcode": v.get("barCode", ""),
                "price": str(v.get("finalPrice", "")),
                "stock": "",
            })

        first_variant = variants[0] if variants else {}
        product_type = p.get("product_type", {})

        return RemoteProduct(
            remote_id=str(p.get("id", "")),
            name=p.get("name", ""),
            canonical_url=p.get("urlSlug", "") or f"{self.base_url}/product/{p.get('id', '')}",
            sku=first_variant.get("sku", ""),
            barcode=first_variant.get("barcode", ""),
            price=first_variant.get("price", ""),
            compare_at_price=None,
            stock=None,
            status="active" if p.get("state") == 0 else "inactive",
            description=p.get("description", ""),
            short_description=None,
            brand=None,
            category=product_type.get("name", "") if isinstance(product_type, dict) else "",
            tags=[],
            images=[],
            weight=None,
            dimensions=None,
            variants=variants,
            raw_data=p,
        )

    def fetch_products(self, page: int = 1, per_page: int = 50) -> List[RemoteProduct]:
        offset = (page - 1) * per_page
        resp = self._request("GET", "products.json", params={"limit": per_page, "offset": offset, "expand": "[variants]"})
        data = resp.json()
        items = data.get("items", [])
        return [self._parse_product(p) for p in items]

    def fetch_product_by_id(self, remote_id: str) -> Optional[RemoteProduct]:
        try:
            resp = self._request("GET", f"products/{remote_id}.json", params={"expand": "[variants]"})
            return self._parse_product(resp.json())
        except Exception:
            return None

    def fetch_product_count(self) -> int:
        try:
            resp = self._request("GET", "products.json", params={"limit": 1})
            return resp.json().get("count", 0)
        except Exception:
            return 0

    def push_product_update(self, remote_id: str, updates: dict) -> bool:
        bsale_payload: dict = {}
        if "name" in updates:
            bsale_payload["name"] = updates["name"]
        if "description" in updates:
            bsale_payload["description"] = updates["description"]

        try:
            if bsale_payload:
                self._request("PUT", f"products/{remote_id}.json", json_data=bsale_payload)
            return True
        except Exception:
            return False
