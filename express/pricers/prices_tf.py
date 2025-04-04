import json
import logging
from typing import Callable

from tf2_utils import PricesTF as PricesTFUtils
from websockets import connect
from websockets.asyncio.connection import Connection

from .pricing_provider import PricingProvider


class PricesTF(PricesTFUtils, PricingProvider):
    def __init__(self, callback: Callable[[dict], None]) -> None:
        super().__init__()

        self.callback = callback

    def format_data(self, data: dict) -> dict:
        return self.format_price(data) | {"sku": data["sku"]}

    def format_websocket_data(self, message: dict) -> dict | None:
        # {
        #     "type": "PRICE_UPDATED",
        #     "data": {
        #         "sku": "31291;6",
        #         "buyHalfScrap": 18,
        #         "buyKeys": 1,
        #         "buyKeyHalfScrap": 1206,
        #         "sellHalfScrap": 72,
        #         "sellKeys": 1,
        #         "sellKeyHalfScrap": 1208,
        #         "createdAt": "2025-04-01T14:15:01.515Z",
        #         "updatedAt": "2025-04-01T14:15:01.515Z"
        #     }
        # }

        if message.get("type") not in ["PRICE_UPDATED", "PRICE_CHANGED"]:
            return

        return self.format_data(message["data"])

    def get_price(self, sku: str) -> dict:
        if not self.access_token:
            self.request_access_token()

        data = super().get_price(sku)
        logging.debug(f"got price for {sku=} {data=}")

        return self.format_data(data)

    def get_multiple_prices(self, skus: list[str]) -> dict:
        # fetch 10 pages (500 prices), hopefully every sku is there
        prices = self.get_prices_till_page(10)

        for sku in prices.copy():
            if sku not in skus:
                del prices[sku]

        # fetch missing prices one by one
        for sku in skus:
            if sku not in prices:
                prices[sku] = self.get_price(sku)

        return prices

    async def process_message(self, ws: Connection, message: dict) -> None:
        if message.get("type") != "AUTH_REQUIRED":
            data = self.format_websocket_data(message)

            if data is None:
                return

            self.callback(data)
            return

        # our auths are only valid for 10 minutes at a time
        # pricestf requests us to authenticate again
        self.request_access_token()

        payload = {
            "type": "AUTH",
            "data": {"accessToken": self.access_token},
        }

        await ws.send(json.dumps(payload))

    async def listen(self) -> None:
        # get and set headers
        self.request_access_token()

        async with connect(
            "wss://ws.prices.tf", additional_headers=self.headers
        ) as websocket:
            logging.info("Connected to PricesTF WebSocket")

            while True:
                message = await websocket.recv()
                await self.process_message(websocket, json.loads(message))
