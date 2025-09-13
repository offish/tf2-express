import asyncio
import json
import logging

from websockets import connect
from websockets.exceptions import ConnectionClosedError, InvalidStatus

from ..utils import sku_to_item_data
from .base_manager import BaseManager


class ArbitrageManager(BaseManager):
    def setup(self) -> None:
        self.ws = None

    def add_deal(self, deal: dict) -> None:
        self.db.add_deal(deal)

    def update_deal(self, deal: dict) -> None:
        self.db.update_deal(deal)

    def delete_deal(self, sku: str) -> None:
        self.db.delete_deal(sku)

    def get_deal(self, sku: str) -> dict:
        return self.db.get_deal(sku)

    def get_deals(self) -> list[dict]:
        return self.db.get_deals().copy()

    def update_deal_state(self, sku: str, intent: str) -> None:
        for deal in self.get_deals():
            if sku != deal["sku"]:
                continue

            deal[intent] = True
            self.update_deal(deal)

            intent_text = "bought" if intent == "is_bought" else "sold"
            logging.info(sku + " was {}".format(intent_text))

        if intent == "is_sold" and self.db.is_temporarily_priced(sku):
            logging.info(f"Deleting temporary price for {sku}")
            self.db.delete_price(sku)

    def process_deals(self) -> None:
        for deal in self.get_deals():
            sell_requested = (
                deal.get("sell_requested", False) and "pricestf" != deal["sell_site"]
            )
            buy_requested = (
                deal.get("buy_requested", False) and "pricestf" != deal["buy_site"]
            )
            is_bought = deal.get("is_bought", False)
            is_sold = deal.get("is_sold", False)
            sku = deal["sku"]

            logging.info(
                f"{sku} {sell_requested=} {buy_requested=} {is_bought=} {is_sold=}"
            )

            # deal is completed
            if is_sold:
                logging.info(f"{sku} deal successfully completed!")
                self.delete_deal(deal["sku"])
                continue

            # NOTE: request tf2-arbitrage to buy/sell an item
            if not buy_requested:
                deal["request_buy"] = True
                logging.info(f"Requesting to buy {sku}")
                self.send(deal)

                deal["buy_requested"] = True
                self.update_deal(deal)
                continue

            if is_bought and not sell_requested and "sell_data" not in deal:
                deal["request_sell"] = True
                logging.info(f"Requesting to sell {sku}")

                asset_id = self.inventory.get_last_item_in_our_inventory(sku)["assetid"]
                deal["our_item"] = asset_id
                self.send(deal)

                deal["sell_requested"] = True
                self.update_deal(deal)
                continue

            # send offer to buy order
            if "buy_data" in deal:
                logging.info(f"Sending offer to buy {sku}")
                buy_data = deal["buy_data"]
                trade_url = buy_data["trade_url"]
                response = self.client.trade_manager.send_offer(trade_url, "buy", sku)

                if response.get("success"):
                    deal["buy_offer_sent"] = True
                    self.update_deal(deal)

            if "sell_data" in deal:
                if not is_bought:
                    logging.info(f"{sku} still not bought")
                    continue

                logging.info(f"Sending offer to sell {sku}")
                sell_data = deal["sell_data"]
                trade_url = sell_data["trade_url"]
                response = self.client.trade_manager.send_offer(trade_url, "sell", sku)

                if response.get("success"):
                    deal["sell_offer_sent"] = True
                    self.update_deal(deal)

                # response =
                # if response.get("success") set true to is_sold

    async def _send_ws_message(self, data: dict) -> None:
        message = json.dumps({"message": data})
        await self._ws.send(message)

    async def _on_incoming_site_trade(self, data: dict) -> None:
        for deal in data:
            # can be other types of messages
            if not deal.get("is_deal"):
                continue

            sku = deal["sku"]
            logging.info(f"Got a deal for {sku=}")

            self.db.add_price(
                **sku_to_item_data(sku),
                buy=deal["buy_price"],
                sell=deal["sell_price"],
            )

            self.add_deal(deal)

    async def _connect_to_site_ws(self, uri: str) -> None:
        async with connect(uri) as websocket:
            logging.info("Connected to tf2-arbitrage")

            self._ws = websocket

            while True:
                message = await websocket.recv()
                data = json.loads(message)

                await self._on_incoming_site_trade(data)

    async def listen(self) -> None:
        uri = self.options.arbitrage_url

        while True:
            try:
                await self._connect_to_site_ws(uri)
            except (
                InvalidStatus,
                ConnectionRefusedError,
                ConnectionClosedError,
                TimeoutError,
            ) as e:
                logging.error(f"Error connecting to websocket: {e}")

            await asyncio.sleep(60)
