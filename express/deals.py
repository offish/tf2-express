from .inventory import ExpressInventory
from .database import Database
from .utils import decode_data, encode_data, sku_to_item_data

from dataclasses import dataclass, asdict
from threading import Thread
import logging
import socket
import time


@dataclass
class Deal:
    is_deal: bool
    sku: str
    name: str
    profit: float
    sites: list[str]
    buy_site: str
    buy_price: dict
    sell_site: str
    sell_price: dict
    stock: dict
    request_buy: bool = False
    buy_requested: bool = False
    is_bought: bool = False
    buy_data: dict = {}
    buy_offer_sent: bool = False
    request_sell: bool = False
    sell_requested: bool = False
    sell_data: dict = {}
    sell_offer_sent: bool = False
    our_item: str = ""
    is_sold: bool = False
    time: float = 0.0
    tries: int = 5


class Deals:
    def __init__(self, express, enabled: bool = False) -> None:
        self.enabled = enabled

        if not enabled:
            return

        self.express = express
        self.inventory: ExpressInventory = self.express.inventory
        self.db: Database = self.express.db

    def begin(self) -> None:
        if not self.enabled:
            return

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Connect to the server
        server_address = ("localhost", 12345)

        try:
            self.socket.connect(server_address)
            logging.info("Connected to socket server")
        except ConnectionRefusedError:
            raise SystemExit("Server socket is not running")

        self.socket_thread = Thread(target=self.listen, daemon=True)
        self.socket_thread.start()

    def listen(self) -> None:
        logging.info("Listening for deals...")

        while True:
            data = self.socket.recv(1024)
            deals = decode_data(data)

            for deal in deals:
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

    def add_deal(self, deal: dict) -> None:
        deal["time"] = time.time()
        self.db.add_deal(deal)

    def update_deal(self, deal: Deal) -> None:
        self.db.update_deal(asdict(deal))

    def delete_deal(self, sku: str) -> None:
        self.db.delete_deal(sku)

    def get_deal(self, sku: str) -> Deal:
        return Deal(**self.db.get_deal(sku))

    def get_deals(self) -> list[Deal]:
        return [Deal(**deal) for deal in self.db.get_deals()]

    def update_deal_value(self, sku: str, **kwargs) -> None:
        deal = self.get_deal(sku)

        for key, value in kwargs.items():
            setattr(deal, key, value)

            intent_text = "bought" if key == "is_bought" else "sold"
            logging.info(f"{sku} was {intent_text}")

            if key == "is_sold":
                self.db.delete_price(sku)
                logging.info(f"Deleting temporary price for {sku}")

        self.update_deal(deal)

    @staticmethod
    def is_outdated(deal: Deal) -> bool:
        return (
            time.time() > deal.time + 5 * 60
            and deal.buy_requested
            and not deal.is_bought
            and deal.buy_site != "pricestf"
        )

    @staticmethod
    def is_going_to_buy(deal: Deal) -> bool:
        return not deal.buy_requested and not deal.is_bought and deal.buy_data

    @staticmethod
    def is_going_to_sell(deal: Deal) -> bool:
        return not deal.sell_requested and deal.is_bought and deal.sell_data

    @staticmethod
    def is_going_to_buy_offer(deal: Deal) -> bool:
        return deal.buy_data and not deal.buy_offer_sent

    @staticmethod
    def is_going_to_sell_offer(deal: Deal) -> bool:
        return deal.sell_data and not deal.sell_offer_sent and deal.is_bought

    def process_deal(self, deal: Deal) -> None:
        sku = deal.sku

        if self.is_outdated(deal):
            logging.info(f"{sku} buy request old, deleting deal")
            self.delete_deal(sku)
            self.db.delete_price(sku)
            return

        # TODO: if bought but failed to sell, find another buyer

        # deal is completed
        if deal.is_sold:
            logging.info(f"{sku} deal successfully completed!")
            self.delete_deal(sku)
            return

        # NOTE: request tf2-arbitrage to buy/sell an item
        if self.is_going_to_buy(deal):
            deal.request_buy = True

            logging.info(f"Requesting to buy {sku}")
            self.send(deal)

            deal.buy_requested = True
            self.update_deal(deal)
            return

        if self.is_going_to_sell(deal):
            deal.request_sell = True
            logging.info(f"Requesting to sell {sku}")

            asset_id = self.inventory.get_our_last_item(sku)["assetid"]
            deal.our_item = asset_id
            self.send(deal)

            deal.sell_requested = True
            self.update_deal(deal)
            return

        # send offer to buy order
        if self.is_going_to_buy_offer(deal):
            logging.info(f"Sending offer to buy {sku}")
            buy_data = deal.buy_data
            trade_url = buy_data["trade_url"]
            response = self.express.send_offer(trade_url, "buy", sku)

            if response.get("success"):
                deal.buy_offer_sent = True
                self.update_deal(deal)

        if self.is_going_to_sell_offer(deal):
            logging.info(f"Sending offer to sell {sku}")
            sell_data = deal.sell_data
            trade_url = sell_data["trade_url"]
            response = self.express.send_offer(trade_url, "sell", sku)

            if response.get("success"):
                deal.sell_offer_sent = True
                self.update_deal(deal)

    def process_deals(self) -> None:
        if not self.enabled:
            return

        for deal in self.get_deals().copy():
            self.process_deal(deal)

    def send(self, data: Deal | dict) -> None:
        if not self.socket:
            logging.warning("Socket empty, could not send data")
            return

        if isinstance(data, Deal):
            data = asdict(data)

        logging.info(f"Sending data {data=}")

        self.socket.sendall(encode_data(data))
