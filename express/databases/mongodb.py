import logging
import time
from os import getenv
from typing import Any

from pymongo import DESCENDING, MongoClient
from tf2_utils import is_metal

from ..exceptions import SKUNotFound
from ..utils import has_buy_and_sell_price, normalize_item_name, sku_to_item_data
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
        self.quicksell = db["quicksell"]

        # bot needs key price to work
        if not self.get_item("5021;6"):
            self._add_key_for_first_time()

    def _add_key_for_first_time(self) -> None:
        self.add_item(**sku_to_item_data("5021;6"))

    def has_price(self, sku: str) -> bool:
        data = self.get_item(sku)

        if not data:
            return False

        return has_buy_and_sell_price(data)

    def find_item_by_name(self, normalized_name: str) -> dict | None:
        for item in self.items.find():
            if normalized_name == normalize_item_name(item["name"]):
                del item["_id"]
                return item

    def get_normalized_item_name(self, sku: str) -> str | None:
        item = self.get_item(sku)

        if item:
            return normalize_item_name(item["name"])

    def insert_trade(self, data: dict) -> None:
        self.trades.insert_one(data)
        logging.info("Offer was added to the database")

    def get_trades(self, start_index: int, amount: int) -> dict[str, Any]:
        # sort newest trades first
        all_trades = list(self.trades.find().sort("timestamp", DESCENDING))
        total_trades = len(all_trades)
        intended_end_index = start_index + amount
        trades = all_trades[start_index:intended_end_index]
        end_index = start_index + len(trades)

        return {
            "trades": trades,
            "total_trades": total_trades,
            "start_index": start_index,
            "end_index": end_index,
        }

    def get_price(self, sku: str, intent: str) -> tuple[int, float]:
        # metals does not exist in the database, but has value
        if sku == "5002;6":
            return 0, 1.0

        if sku == "5001;6":
            return 0, 0.33

        if sku == "5000;6":
            return 0, 0.11

        item_price = self.get_item(sku)

        # item does not exist in db or does not have a price
        if not item_price or not has_buy_and_sell_price(item_price):
            return 0, 0.0

        price = item_price[intent]
        keys = price.get("keys", 0)
        metal = price.get("metal", 0.0)

        return keys, metal

    def get_skus(self) -> list[str]:
        return [item["sku"] for item in self.items.find()]

    def get_autopriced(self) -> list[dict]:
        return [
            item
            for item in self.items.find({"autoprice": True})
            if item["sku"] != "-100;6"
        ]

    def get_autopriced_skus(self) -> list[str]:
        return [item["sku"] for item in self.get_autopriced()]

    def get_item(self, sku: str) -> dict[str, Any]:
        item = self.items.find_one({"sku": sku})

        if item is None:
            # logging.debug(f"{sku} not found in database")
            return {}

        del item["_id"]
        return item

    def get_pricelist(self) -> list[dict]:
        return list(self.items.find())

    def get_stock(self, sku: str) -> tuple[int, int]:
        """returns in_stock, max_stock"""
        data = self.get_item(sku)
        return (data.get("in_stock", 0), data.get("max_stock", -1))

    def get_max_stock(self, sku: str) -> int:
        return self.get_item(sku).get("max_stock", -1)

    def replace_item(self, data: dict) -> None:
        sku = data["sku"]

        logging.debug(f"Updating {sku} with {data=}")
        self.items.replace_one({"sku": sku}, data)

    def update_stock(self, stock: dict) -> None:
        all_items = self.items.find()

        for item in all_items:
            sku = item["sku"]

            if sku not in stock:
                continue

            in_stock = stock[sku]

            # in_stock is the same, no need to update
            if in_stock == item.get("in_stock", 0):
                continue

            item["in_stock"] = in_stock
            self.replace_item(item)

        logging.info("Updated stock for all items")

    def add_item(
        self,
        sku: str,
        color: str,
        image: str,
        name: str,
        autoprice: bool = True,
        in_stock: int = 0,
        max_stock: int = -1,
        buy: dict = {},
        sell: dict = {},
    ) -> None:
        if is_metal(sku):
            logging.warning(f"Cannot add metal {sku} to database")
            return

        if sku in self.get_skus():
            logging.warning(f"{sku} already exists in database")
            return

        document = {
            "sku": sku,
            "name": name,
            "buy": buy,
            "sell": sell,
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

    def update_autoprice(self, data: dict) -> None:
        self.update_price(data["sku"], data["buy"], data["sell"])

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
