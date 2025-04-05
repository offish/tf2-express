from typing import Callable

from .bptf_autopricer import BPTFAutopricer
from .prices_tf import PricesTF
from .pricing_provider import PricingProvider

PROVIDERS = [BPTFAutopricer, PricesTF]


def get_pricing_provider(
    provider: str, callback: Callable[[dict], None]
) -> PricingProvider:
    for i in PROVIDERS:
        if provider.lower() == i.__name__.lower():
            return i(callback)

    raise ValueError(f"Unknown provider: {provider}")
