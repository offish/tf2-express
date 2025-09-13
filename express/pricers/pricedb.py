import logging
from typing import Callable

import requests
from socketio import AsyncClient

from .pricing_provider import PricingProvider

# NOTE: prices are on the format we expect, so no need to format it
# {
#     "sku": "5021;6",
#     "name": "Mann Co. Supply Crate Key",
#     "buy": {"keys": 0, "metal": 67.33},
#     "sell": {"keys": 0, "metal": 68.11},
#     "time": 1640995200,
#     "source": "bptf",
# }


class PriceDB(PricingProvider):
    def __init__(self, callback: Callable[[dict], None]):
        super().__init__(callback)

        self.socket_url = "ws://ws.pricedb.io:5500/"
        self.api_url = "https://pricedb.io/api"
        self.sio = AsyncClient()

        self.sio.on("connect", self.on_connect)
        self.sio.on("price", self.on_price_update)

    def get_price(self, sku: str) -> dict:
        response = requests.get(f"{self.api_url}/item/{sku}")
        response.raise_for_status()

        data = response.json()
        logging.debug(f"got price for {sku=} {data=}")

        return data

    def get_multiple_prices(self, skus: list[str]) -> dict:
        prices = {}

        response = requests.post(f"{self.api_url}/items-bulk", json={"skus": skus})
        response.raise_for_status()
        data = response.json()

        for price in data:
            sku = price["sku"]
            prices[sku] = price

        return prices

    async def on_connect(self) -> None:
        logging.info(f"Connected to {self.url} Socket.IO Server")

    async def on_price_update(self, data: dict) -> None:
        logging.debug(f"got data: {data}")
        self.callback(data)

    async def listen(self) -> None:
        await self.sio.wait()
