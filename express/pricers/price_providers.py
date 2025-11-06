from typing import Callable

from .price_provider import PriceProvider
from .pricedb import PriceDB

PROVIDERS = [PriceDB]


def get_price_provider(
    provider: str, callback: Callable[[dict], None]
) -> PriceProvider:
    for i in PROVIDERS:
        if provider.lower() == i.__name__.lower():
            return i(callback)

    raise ValueError(f"Unknown provider: {provider}")
