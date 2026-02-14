import logging
import time
from os import getenv

from pymongo import DESCENDING, MongoClient
from tf2_utils import is_metal

from ..exceptions import SKUNotFound
from .database_provider import DatabaseProvider


class MongoDB(DatabaseProvider):
    def __init__(self, username: str) -> None:
        host = getenv("MONGO_HOST", "localhost")
        client = MongoClient(host, 27017)
        db = client[username]

        self.name = username
        self.trades = db["trades"]
        self.items = db["items"]
        self.arbitrage = db["arbitrage"]

        # bot needs key price to work
        if not self.get_item("5021;6"):
            self._add_key_for_first_time()

    def get_items(self) -> list[dict]:
        return list(self.get_items())

    def insert_trade(self, data: dict) -> None:
        self.trades.insert_one(data)
        logging.info("Offer was added to the database")

    def get_trades_sorted(self) -> list[dict]:
        return list(self.trades.find().sort("timestamp", DESCENDING))

    def replace_item(self, data: dict) -> None:
        sku = data["sku"]

        logging.debug(f"Updating {sku} with {data=}")
        self.items.replace_one({"sku": sku}, data)

    def add_item(
        self,
        sku: str,
        color: str,
        image: str,
        name: str,
        autoprice: bool = True,
        in_stock: int = 0,
        max_stock: int = -1,
        buy: dict = None,
        sell: dict = None,
    ) -> None:
        if is_metal(sku):
            logging.warning(f"Cannot add metal {sku} to database")
            return

        if sku in self.get_skus():
            logging.warning(f"{sku} already exists in database")
            return

        if in_stock < 0:
            logging.warning(f"{in_stock} cannot be less than zero")
            return

        if max_stock == 0:
            logging.warning(f"{max_stock} cannot be zero")
            return

        document = {
            "sku": sku,
            "name": name,
            "buy": buy or {},
            "sell": sell or {},
            "autoprice": autoprice,
            "in_stock": in_stock,
            "max_stock": max_stock,
            "color": color,
            "image": image,
        }

        self.items.insert_one(document)
        logging.info(f"Added {sku} to database")

    def update_price(
        self,
        sku: str,
        buy: dict,
        sell: dict,
        override_autoprice: bool = None,
        override_max_stock: int = None,
    ) -> None:
        data = self.get_item(sku)

        if not data:
            raise SKUNotFound(f"{sku} does not exist in database!")

        autoprice = data["autoprice"]
        max_stock = data["max_stock"]

        if override_autoprice is not None:
            autoprice = override_autoprice

        if override_max_stock is not None:
            max_stock = override_max_stock

        data["buy"] = buy
        data["sell"] = sell
        data["autoprice"] = autoprice
        data["max_stock"] = max_stock
        data["updated"] = time.time()

        self.items.replace_one({"sku": sku}, data)
        logging.info(f"Updated price for {sku}")

    def delete_all_items(self) -> None:
        self.items.delete_many({})

    def delete_item(self, sku: str) -> None:
        self.items.delete_one({"sku": sku})
        logging.info(f"Removed {sku} from the database")

    def insert_arbitrage(self, data: dict) -> None:
        self.arbitrage.insert_one(data)

    def update_arbitrage(self, sku: str, data: dict) -> None:
        self.arbitrage.replace_one({"sku": sku}, data)

    def delete_arbitrage(self, sku: str) -> None:
        self.arbitrage.delete_one({"sku": sku})

    def get_arbitrages(self) -> list[dict]:
        return list(self.arbitrage.find())
