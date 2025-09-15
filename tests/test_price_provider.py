import pytest

from express.pricers.pricedb import PriceDB
from express.pricers.prices_tf import PricesTF
from express.pricers.pricing_providers import get_pricing_provider


def callback(data: dict) -> None:
    del data


def test_pricing_provider() -> None:
    assert isinstance(get_pricing_provider("pricedb", callback), PriceDB)
    assert isinstance(get_pricing_provider("PriceDB", callback), PriceDB)
    assert isinstance(get_pricing_provider("PricesTF", callback), PricesTF)

    with pytest.raises(ValueError):
        get_pricing_provider("invalid_provider", callback)
