"""
Shopify Admin REST API adapter.
Docs: https://shopify.dev/docs/api/admin-rest
"""
import requests
from typing import List, Optional

from .base import BaseStoreAdapter, RemoteProduct, ConnectionTestResult


class ShopifyAdapter(BaseStoreAdapter):

    def __init__(self, config: dict):
        super().__init__(config)
        # Shopify uses access token in header
        self.api_version = "2024-01"
        self.api_base = f"{self.base_url}/admin/api/{self.api_version}"
        self.headers = {
            "X-Shopify-Access-Token": self.access_token or "",
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
            raise RuntimeError(f"Shopify API error ({resp.status_code}): {resp.text[:300]}")
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Request to {url} timed out after {timeout}s")

    def test_connection(self) -> ConnectionTestResult:
        try:
            resp = self._request("GET", "shop.json")
            data = resp.json()
            shop = data.get("shop", {})
            return ConnectionTestResult(
                success=True,
                message="Connected successfully to Shopify",
                store_name=shop.get("name", self.base_url),
                product_count=None,
                api_version=f"Shopify {self.api_version}",
            )
        except Exception as e:
            return ConnectionTestResult(success=False, message=str(e))

    def _parse_product(self, p: dict) -> RemoteProduct:
        images = [img.get("src", "") for img in p.get("images", []) if img.get("src")]
        tags = [t.strip() for t in (p.get("tags", "") or "").split(",") if t.strip()]

        # Get first variant data
        first_variant = p.get("variants", [{}])[0] if p.get("variants") else {}
        variants = [{
            "id": str(v.get("id", "")),
            "sku": v.get("sku", ""),
            "price": v.get("price", ""),
            "stock": str(v.get("inventory_quantity", "")),
            "title": v.get("title", ""),
        } for v in p.get("variants", [])]

        handle = p.get("handle", "")
        canonical = f"{self.base_url}/products/{handle}" if handle else ""

        return RemoteProduct(
            remote_id=str(p["id"]),
            name=p.get("title", ""),
            canonical_url=canonical,
            sku=first_variant.get("sku", ""),
            barcode=first_variant.get("barcode", ""),
            price=first_variant.get("price", ""),
            compare_at_price=first_variant.get("compare_at_price", ""),
            stock=str(first_variant.get("inventory_quantity", "")) if first_variant.get("inventory_quantity") is not None else None,
            status=p.get("status", ""),
            description=p.get("body_html", ""),
            short_description=None,
            brand=p.get("vendor", ""),
            category=p.get("product_type", ""),
            tags=tags,
            images=images,
            weight=str(first_variant.get("weight", "")),
            dimensions=None,
            variants=variants,
            raw_data=p,
        )

    def fetch_products(self, page: int = 1, per_page: int = 50) -> List[RemoteProduct]:
        # Shopify uses cursor-based pagination; for simplicity we use limit+page
        resp = self._request("GET", "products.json", params={"limit": per_page})
        data = resp.json()
        products = data.get("products", [])
        return [self._parse_product(p) for p in products]

    def fetch_product_by_id(self, remote_id: str) -> Optional[RemoteProduct]:
        try:
            resp = self._request("GET", f"products/{remote_id}.json")
            data = resp.json()
            return self._parse_product(data.get("product", {}))
        except Exception:
            return None

    def fetch_product_count(self) -> int:
        try:
            resp = self._request("GET", "products/count.json")
            return resp.json().get("count", 0)
        except Exception:
            return 0

    def push_product_update(self, remote_id: str, updates: dict) -> bool:
        shopify_product: dict = {}
        if "name" in updates:
            shopify_product["title"] = updates["name"]
        if "description" in updates:
            shopify_product["body_html"] = updates["description"]
        if "status" in updates:
            shopify_product["status"] = updates["status"]
        if "brand" in updates:
            shopify_product["vendor"] = updates["brand"]
        if "category" in updates:
            shopify_product["product_type"] = updates["category"]
        if "tags" in updates:
            shopify_product["tags"] = ", ".join(updates["tags"]) if isinstance(updates["tags"], list) else updates["tags"]

        # Variant-level updates
        variant_updates: dict = {}
        if "sku" in updates:
            variant_updates["sku"] = updates["sku"]
        if "price" in updates:
            variant_updates["price"] = updates["price"]
        if "barcode" in updates:
            variant_updates["barcode"] = updates["barcode"]

        try:
            if shopify_product:
                self._request("PUT", f"products/{remote_id}.json", json_data={"product": shopify_product})
            if variant_updates:
                # Get first variant ID
                product_resp = self._request("GET", f"products/{remote_id}.json")
                product_data = product_resp.json().get("product", {})
                first_variant = (product_data.get("variants") or [{}])[0]
                variant_id = first_variant.get("id")
                if variant_id:
                    self._request("PUT", f"variants/{variant_id}.json", json_data={"variant": variant_updates})
            return True
        except Exception:
            return False
