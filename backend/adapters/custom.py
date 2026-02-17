"""
Custom / Generic REST API adapter.
Designed for APIs that return JSON product data with configurable field mapping.
"""
import json
import requests
from typing import List, Optional

from .base import BaseStoreAdapter, RemoteProduct, ConnectionTestResult


class CustomAPIAdapter(BaseStoreAdapter):
    """
    Generic adapter for custom REST APIs.
    Expects the API to expose endpoints like:
      GET /products         -> list of products
      GET /products/{id}    -> single product
      PUT /products/{id}    -> update product
    
    Custom headers can be passed as JSON string in the store config.
    Field mapping can be customized via the `custom_headers` JSON config:
    {
        "headers": {"Authorization": "Bearer <token>"},
        "products_endpoint": "/api/products",
        "field_map": {
            "id": "product_id",
            "name": "title",
            "url": "permalink",
            "sku": "sku",
            "price": "price",
            "stock": "quantity",
            "status": "status",
            "description": "body"
        }
    }
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.extra_config = {}
        if self.custom_headers:
            try:
                self.extra_config = json.loads(self.custom_headers)
            except json.JSONDecodeError:
                pass

        self.extra_headers = self.extra_config.get("headers", {})
        self.products_endpoint = self.extra_config.get("products_endpoint", "/products")
        self.field_map = self.extra_config.get("field_map", {
            "id": "id",
            "name": "name",
            "url": "url",
            "sku": "sku",
            "price": "price",
            "stock": "stock",
            "status": "status",
            "description": "description",
        })

        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["X-API-Key"] = self.api_key
        if self.access_token:
            self.headers["Authorization"] = f"Bearer {self.access_token}"
        self.headers.update(self.extra_headers)

    def _request(self, method: str, endpoint: str, params: dict = None, json_data: dict = None, timeout: int = 30):
        url = f"{self.base_url}{endpoint}"
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
            raise RuntimeError(f"API error ({resp.status_code}): {resp.text[:300]}")
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Request to {url} timed out after {timeout}s")

    def test_connection(self) -> ConnectionTestResult:
        try:
            resp = self._request("GET", self.products_endpoint, params={"limit": 1, "per_page": 1})
            data = resp.json()
            # Try to determine count
            count = None
            if isinstance(data, dict):
                count = data.get("total") or data.get("count") or len(data.get("items", data.get("products", data.get("data", []))))
            elif isinstance(data, list):
                count = len(data)
            return ConnectionTestResult(
                success=True,
                message="Connected successfully to custom API",
                store_name=self.base_url,
                product_count=count,
                api_version="Custom REST",
            )
        except Exception as e:
            return ConnectionTestResult(success=False, message=str(e))

    def _get(self, data: dict, field_key: str, default=""):
        """Get a value using the field map."""
        mapped = self.field_map.get(field_key, field_key)
        return data.get(mapped, default)

    def _parse_product(self, p: dict) -> RemoteProduct:
        return RemoteProduct(
            remote_id=str(self._get(p, "id", "")),
            name=self._get(p, "name", ""),
            canonical_url=self._get(p, "url", "") or f"{self.base_url}/product/{self._get(p, 'id', '')}",
            sku=self._get(p, "sku"),
            barcode=self._get(p, "barcode"),
            price=str(self._get(p, "price", "")),
            compare_at_price=str(self._get(p, "compare_at_price", "")),
            stock=str(self._get(p, "stock", "")),
            status=self._get(p, "status", ""),
            description=self._get(p, "description", ""),
            short_description=self._get(p, "short_description", ""),
            brand=self._get(p, "brand", ""),
            category=self._get(p, "category", ""),
            tags=[],
            images=[],
            variants=[],
            raw_data=p,
        )

    def fetch_products(self, page: int = 1, per_page: int = 50) -> List[RemoteProduct]:
        resp = self._request("GET", self.products_endpoint, params={"page": page, "per_page": per_page, "limit": per_page})
        data = resp.json()

        # Handle different response shapes
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("items") or data.get("products") or data.get("data") or data.get("results") or []

        return [self._parse_product(p) for p in items]

    def fetch_product_by_id(self, remote_id: str) -> Optional[RemoteProduct]:
        try:
            resp = self._request("GET", f"{self.products_endpoint}/{remote_id}")
            data = resp.json()
            product_data = data.get("product") or data.get("item") or data if isinstance(data, dict) else data
            return self._parse_product(product_data)
        except Exception:
            return None

    def fetch_product_count(self) -> int:
        try:
            resp = self._request("GET", self.products_endpoint, params={"limit": 1, "per_page": 1})
            data = resp.json()
            if isinstance(data, dict):
                return data.get("total") or data.get("count") or 0
            return 0
        except Exception:
            return 0

    def push_product_update(self, remote_id: str, updates: dict) -> bool:
        # Reverse-map field names for the remote API
        reverse_map = {v: k for k, v in self.field_map.items()}
        payload = {}
        for field, value in updates.items():
            remote_field = self.field_map.get(field, field)
            payload[remote_field] = value

        try:
            self._request("PUT", f"{self.products_endpoint}/{remote_id}", json_data=payload)
            return True
        except Exception:
            return False
