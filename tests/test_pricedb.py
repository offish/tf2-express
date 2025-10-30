import pytest

from express.pricers.pricedb import BasePriceDB
from express.utils import has_correct_price_format


@pytest.mark.asyncio
async def test_get_items_bulk():
    price_db = BasePriceDB()

    skus = ["5021;6", "725;6;uncraftable", "233;6"]
    prices = await price_db.get_items_bulk(skus)

    assert isinstance(prices, list)
    assert len(prices) == 3

    for price in prices:
        assert has_correct_price_format(price)


@pytest.mark.asyncio
async def test_get_prices_by_schema():
    price_db = BasePriceDB()

    skus = ["5021;6", "725;6;uncraftable", "233;6"]
    prices = await price_db.get_prices_by_schema(skus)

    assert isinstance(prices, list)
    assert len(prices) == 3

    for price in prices:
        assert has_correct_price_format(price)
