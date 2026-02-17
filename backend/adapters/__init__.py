from .base import BaseStoreAdapter
from .woocommerce import WooCommerceAdapter
from .shopify import ShopifyAdapter
from .bsale import BsaleAdapter
from .custom import CustomAPIAdapter


def get_adapter(platform: str, config: dict) -> BaseStoreAdapter:
    """Factory function to get the right adapter for a platform."""
    adapters = {
        "woocommerce": WooCommerceAdapter,
        "shopify": ShopifyAdapter,
        "bsale": BsaleAdapter,
        "custom": CustomAPIAdapter,
    }
    adapter_class = adapters.get(platform)
    if not adapter_class:
        raise ValueError(f"Unsupported platform: {platform}")
    return adapter_class(config)
