from typing import Callable

from .pricedb import PriceDB
from .prices_tf import PricesTF
from .pricing_provider import PricingProvider

PROVIDERS = [PriceDB, PricesTF]


def get_pricing_provider(
    provider: str, callback: Callable[[dict], None]
) -> PricingProvider:
    for i in PROVIDERS:
        if provider.lower() == i.__name__.lower():
            return i(callback)

    raise ValueError(f"Unknown provider: {provider}")
