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

    def get_schema(self) -> list[dict]:
        items = self.request("GET", "autob/items")
        return items.get("items", [])

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

        self.sio = AsyncClient()
        self.sio.on("connect", self.on_connect)
        self.sio.on("price", self.on_price_update)

    async def on_connect(self) -> None:
        logging.info("Connected to PriceDB socket")

    async def on_price_update(self, data: dict) -> None:
        # Data recevied looks like this (the format we expect)
        # we only care about the sku, buy and sell
        # {
        #     "success": True,
        #     "sku": "30371;11",
        #     "name": "Strange Archer's Groundings",
        #     "currency": "metal",
        #     "source": "bptf",
        #     "time": 1757771632,
        #     "buy": {"keys": 1, "metal": 5.66},
        #     "sell": {"keys": 1, "metal": 14.88},
        # }
        logging.debug(f"got data: {data}")

        if data.get("success") is not True:
            return

        self.callback(data)

    async def listen(self) -> None:
        await self.sio.connect("ws://ws.pricedb.io:5500/")
        await self.sio.wait()
