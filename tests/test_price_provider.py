import pytest
from aiohttp import ClientSession

from express.pricers.price_providers import get_price_provider
from express.pricers.pricedb import PriceDB
from express.utils import has_correct_price_format


def callback(data: dict) -> None:
    del data


async def test_pricing_provider(aiohttp_session: ClientSession) -> None:
    provider = get_price_provider("pricedb", aiohttp_session, callback)

    assert isinstance(provider, PriceDB)
    assert isinstance(get_price_provider("PriceDB", aiohttp_session, callback), PriceDB)

    with pytest.raises(ValueError):
        get_price_provider("invalid_provider", aiohttp_session, callback)


async def test_get_price(aiohttp_session: ClientSession) -> None:
    provider = get_price_provider("pricedb", aiohttp_session, callback)

    price = await provider.get_price("5021;6")
    assert has_correct_price_format(price)


async def test_get_multiple_prices(aiohttp_session: ClientSession) -> None:
    provider = get_price_provider("pricedb", aiohttp_session, callback)

    skus = ["5021;6", "725;6;uncraftable", "233;6"]
    prices = await provider.get_multiple_prices(skus)
    assert len(prices) == 3

    for sku in prices:
        assert has_correct_price_format(prices[sku])
