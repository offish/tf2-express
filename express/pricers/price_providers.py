from typing import Callable

from aiohttp import ClientSession

from .price_provider import PriceProvider
from .pricedb import PriceDB

PROVIDERS: list[PriceProvider] = [PriceDB]


def get_price_provider(
    provider: str, session: ClientSession, callback: Callable[[dict], None]
) -> PriceProvider:
    for i in PROVIDERS:
        if provider.lower() == i.__name__.lower():
            return i(session, callback)

    raise ValueError(f"Unknown provider: {provider}")
