import logging
import time

from tf2_utils import refinedify
from pymongo import MongoClient


class Database:
    def __init__(self, name: str, host: str = "localhost", port: int = 27017) -> None:
        client = MongoClient(host, port)
        db = client[name]

        self.trades = db["trades"]
        self.items = db["items"]

    @staticmethod
    def has_price(data: dict) -> bool:
        return data.get("buy", {}) != {} and data.get("sell", {}) != {}

    def insert_trade(self, data: dict) -> None:
        logging.debug("Adding new trade to database")
        self.trades.insert_one(data)

    def get_trades(
        self, start_index: int, amount: int
    ) -> tuple[list[dict], int, int, int]:
        all_trades = list(self.trades.find().sort("time_updated", -1))
        total = len(all_trades)
        intended_end_index = start_index + amount
        result = all_trades[start_index:intended_end_index]
        actual_end_index = start_index + len(result)

        return (result, total, start_index, actual_end_index)

    def __get_data(self, sku: str) -> dict | None:
        return self.items.find_one({"sku": sku})

    def get_price(self, sku: str, intent: str) -> tuple[int, float]:
        item_price = self.__get_data(sku)

        # item does not exist in db or does not have a price
        if item_price is None or not self.has_price(item_price):
            return (0, 0.0)

        price = item_price[intent]

        keys = price.get("keys", 0)
        metal = price.get("metal", 0.0)

        return (keys, metal)

    def get_skus(self) -> list[str]:
        return [item["sku"] for item in self.items.find()]

    def get_autopriced(self) -> list[str]:
        return [
            item["sku"]
            for item in self.items.find({"autoprice": True})
            if item["sku"] != "-100;6"
        ]

    def get_item(self, sku: str) -> dict | None:
        return self.items.find_one({"sku": sku})

    def get_pricelist(self) -> list[dict]:
        return self.items.find()

    def add_price(self, sku: str, color: str, image: str, name: str) -> None:
        self.items.insert_one(
            {
                "sku": sku,
                "name": name,
                "color": color,
                "image": image,
                "autoprice": True,  # default to autoprice
                "buy": {},
                "sell": {},
            }
        )
        logging.info(f"Added {sku} to the database")

    def update_price(
        self, sku: str, buy: dict, sell: dict, autoprice: bool = False
    ) -> None:
        data = self.__get_data(sku)

        data["buy"] = buy
        data["sell"] = sell
        data["autoprice"] = autoprice
        data["updated"] = time.time()

        self.items.replace_one(
            {"sku": sku},
            data,
        )
        logging.info(f"Updated price for {sku}")

    def update_autoprice(self, data: dict) -> None:
        sku = data["sku"]
        buy_keys = data.get("buyKeys", 0)
        # will have many decimals e.g. 2.2222223 if we dont refinedify
        buy_metal = refinedify(data.get("buyHalfScrap", 0.0) / 18)
        sell_keys = data.get("sellKeys", 0)
        sell_metal = refinedify(data.get("sellHalfScrap", 0.0) / 18)

        self.update_price(
            sku,
            {"metal": buy_metal, "keys": buy_keys},
            {"metal": sell_metal, "keys": sell_keys},
            True,
        )

    def delete_price(self, sku: str) -> None:
        self.items.delete_one({"sku": sku})
        logging.info(f"Removed {sku} from the database")
