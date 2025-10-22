import pytest

from express.pricers.pricedb import PriceDB
from express.pricers.prices_tf import PricesTF
from express.pricers.pricing_providers import get_pricing_provider
from express.utils import has_correct_price_format


def callback(data: dict) -> None:
    del data


provider = get_pricing_provider("pricedb", callback)


def test_pricing_provider() -> None:
    assert isinstance(provider, PriceDB)
    assert isinstance(get_pricing_provider("PriceDB", callback), PriceDB)
    assert isinstance(get_pricing_provider("PricesTF", callback), PricesTF)

    with pytest.raises(ValueError):
        get_pricing_provider("invalid_provider", callback)


async def test_get_price() -> None:
    price = await provider.get_price("5021;6")
    assert has_correct_price_format(price)


async def test_get_multiple_prices() -> None:
    skus = ["5021;6", "725;6;uncraftable", "233;6"]
    prices = await provider.get_multiple_prices(skus)
    assert len(prices) == 3

    for sku in prices:
        assert has_correct_price_format(prices[sku])
