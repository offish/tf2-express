import json
import logging
from typing import Callable

from tf2_utils import PricesTF as PricesTFUtils
from tf2_utils import refinedify
from websockets import connect
from websockets.asyncio.connection import Connection

from .pricing_provider import PricingProvider


class PricesTF(PricesTFUtils, PricingProvider):
    def __init__(self, callback: Callable[[dict], None]) -> None:
        super().__init__()

        self.callback = callback

    @staticmethod
    def format_data(data: dict) -> dict:
        buy_keys = data.get("buyKeys", 0)
        buy_metal = refinedify(data.get("buyHalfScrap", 0.0) / 18)
        sell_keys = data.get("sellKeys", 0)
        sell_metal = refinedify(data.get("sellHalfScrap", 0.0) / 18)

        return {
            "sku": data["sku"],
            "buy": {
                "keys": buy_keys,
                "metal": buy_metal,
            },
            "sell": {
                "keys": sell_keys,
                "metal": sell_metal,
            },
        }

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
