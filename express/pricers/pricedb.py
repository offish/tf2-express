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


class BasePriceDB:
    def __init__(self):
        self.api_url = "https://pricedb.io/api"

    def request(self, method: str, endpoint: str, **kwargs) -> dict:
        url = f"{self.api_url}/{endpoint}"
        response = requests.request(method.upper(), url, **kwargs)
        response.raise_for_status()
        logging.debug(f"got data for {url} {response.text[:50]}")

        return response.json()

    def get_price(self, sku: str) -> dict:
        return self.request("GET", f"item/{sku}")

    def get_schema(self) -> dict:
        return self.request("GET", "autob/items").get("items", [])

    def get_multiple_prices(self, skus: list[str]) -> dict:
        data = self.request("POST", "items-bulk", json={"skus": skus})
        prices = {}

        for price in data:
            sku = price["sku"]
            prices[sku] = price

        return prices


class PriceDB(BasePriceDB, PricingProvider):
    def __init__(self, callback: Callable[[dict], None]):
        super().__init__()
        PricingProvider.__init__(self, callback)

        self.socket_url = "ws://ws.pricedb.io:5500/"
        self.sio = AsyncClient()

        self.sio.on("connect", self.on_connect)
        self.sio.on("price", self.on_price_update)

    async def on_connect(self) -> None:
        logging.info("Connected to PriceDB Socket.IO Server")

    async def on_price_update(self, data: dict) -> None:
        logging.debug(f"got data: {data}")
        self.callback(data)

    async def listen(self) -> None:
        await self.sio.connect(self.socket_url)
        await self.sio.wait()
