import pytest

from express.pricers.bliss_autopricer import BlissAutopricer
from express.pricers.prices_tf import PricesTF
from express.pricers.pricing_providers import get_pricing_provider


def dummy_callback(data: dict) -> None:
    del data


def test_pricing_provider() -> None:
    assert isinstance(get_pricing_provider("pricestf", dummy_callback), PricesTF)
    assert isinstance(get_pricing_provider("PricesTF", dummy_callback), PricesTF)
    assert isinstance(
        get_pricing_provider("blissautopricer", dummy_callback), BlissAutopricer
    )

    with pytest.raises(ValueError):
        get_pricing_provider("invalid_provider", dummy_callback)
