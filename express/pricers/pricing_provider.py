from abc import ABC, abstractmethod
from typing import Callable


class PricingProvider(ABC):
    def __init__(self, callback: Callable[[dict], None]) -> None:
        """Callback has to get a dict with the following format:

        .. code-block:: json
            {
                "sku": "5021;6",
                "buy": {
                    "keys": 0,
                    "metal": 60.44,
                },
                "sell": {
                    "keys": 0,
                    "metal": 60.55,
                }
            }
        """
        self.callback = callback

    @abstractmethod
    def get_price(self, sku: str) -> dict:
        """Has to return a dict with the following format:

        .. code-block:: json
            {
                "sku": "5021;6",
                "buy": {
                    "keys": 0,
                    "metal": 60.44,
                },
                "sell": {
                    "keys": 0,
                    "metal": 60.55,
                }
            }
        """
        pass

    @abstractmethod
    def get_multiple_prices(self, skus: list[str]) -> dict:
        """Has to return a list of dicts with the following format:

        .. code-block:: json

            {
                "5021;6": {
                    "buy": {
                        "keys": 0,
                        "metal": 60.44,
                    },
                    "sell": {
                        "keys": 0,
                        "metal": 60.55,
                    }
                },
                "263;6": {
                    "buy": {
                        "keys": 0,
                        "metal": 1.44,
                    },
                    "sell": {
                        "keys": 0,
                        "metal": 1.55,
                    }
                }
            }

        """
        pass

    @abstractmethod
    async def listen(self) -> None:
        pass
