from abc import ABC, abstractmethod


class PricingProvider(ABC):
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
    async def listen(self) -> None:
        pass
