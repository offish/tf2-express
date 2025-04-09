import logging
from typing import Callable

import requests
from socketio import AsyncClient

from .pricing_provider import PricingProvider

# NOTE: prices are on the format we expect, so no need to format it
# {
#     "name": "Strange Australium Minigun",
#     "sku": "202;11;australium",
#     "source": "bptf",
#     "time": 1700403492,
#     "buy": {"keys": 25, "metal": 21.33},
#     "sell": {"keys": 26, "metal": 61.77}
# }


class BPTFAutopricer(PricingProvider):
    def __init__(self, callback: Callable[[dict], None]):
        super().__init__(callback)

        self.url = "http://127.0.0.1:3456"
        self.sio = AsyncClient()

        self.sio.on("connect", self.on_connect)
        self.sio.on("price", self.on_price_update)

    def get_price(self, sku: str) -> dict:
        response = requests.get(f"{self.url}/items/{sku}")
        response.raise_for_status()

        data = response.json()
        logging.debug(f"got price for {sku=} {data=}")

        return data

    def get_multiple_prices(self, skus: list[str]) -> list[dict]:
        prices = {}

        for sku in skus:
            prices[sku] = self.get_price(sku)

        return prices

    async def on_connect(self) -> None:
        logging.info(f"Connected to {self.url} Socket.IO Server")

    async def on_price_update(self, data: dict) -> None:
        logging.debug(f"got data: {data}")
        self.callback(data)

    async def listen(self) -> None:
        await self.sio.wait()
