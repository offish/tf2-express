import logging
from typing import Callable

import aiohttp
from socketio import AsyncClient
from socketio.exceptions import ConnectionError

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
        self.session = aiohttp.ClientSession()

    async def request(self, method: str, endpoint: str, **kwargs) -> dict:
        url = f"{self.api_url}/{endpoint}"

        logging.debug(f"requesting {method} {url} with {kwargs}")

        async with self.session.request(method.upper(), url, **kwargs) as resp:
            resp.raise_for_status()
            data = await resp.json()
            logging.debug(f"got data for {url} {str(data)[:50]}")

        return data

    async def get_price(self, sku: str) -> dict:
        return await self.request("GET", f"item/{sku}")

    async def get_schema(self) -> list[dict]:
        items = await self.request("GET", "autob/items")
        return items.get("items", [])

    async def get_items_bulk(self, skus: list[str]) -> list[dict]:
        # remove duplicates
        skus = list(set(skus))
        return await self.request("POST", "items-bulk", json={"skus": skus})

    async def get_prices_by_schema(self, skus: list[str]) -> list[dict]:
        schema = await self.get_schema()
        return [item for item in schema if item["sku"] in skus]

    async def get_multiple_prices(self, skus: list[str]) -> dict:
        # remove duplicates
        skus = list(set(skus))
        prices = {}
        data = []

        if len(skus) <= 50:
            data = await self.get_items_bulk(skus)
        else:
            data = await self.get_prices_by_schema(skus)

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
        self.sio.on("disconnect", self.on_disconnect)
        self.sio.on("price", self.on_price_update)
        self.sio.on("connect_error", self.on_connect_error)

    async def on_connect(self) -> None:
        logging.info("Connected to PriceDB socket")

    async def on_disconnect(self) -> None:
        logging.warning("Disconnected from PriceDB socket")

    async def on_connect_error(self, data) -> None:
        logging.warning(f"Connection error: {data}")

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
        # logging.debug(f"got data: {data}")

        if data.get("success") is not True:
            return

        self.callback(data)

    async def listen(self) -> None:
        logging.info("Connecting to PriceDB socket...")

        while True:
            try:
                await self.sio.connect("ws://ws.pricedb.io/")
                break
            except ConnectionError:
                logging.warning("Failed to connect to PriceDB socket - retrying in 5s")
                await self.sio.sleep(5)
                continue

        await self.sio.wait()

    async def close(self) -> None:
        await self.sio.disconnect()
        await self.session.close()
