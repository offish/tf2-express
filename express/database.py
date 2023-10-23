import logging
import time

from tf2_utils import to_refined, to_scrap
from pymongo import MongoClient


# TODO: change database to use SKUs instead
class Database:
    def __init__(self, name: str, host: str = "localhost", port: int = 27017) -> None:
        client = MongoClient(host, port)
        db = client[name]

        self.trades = db["trades"]
        self.prices = db["prices"]
        # TODO: cache prices? faster access but more mem

    def insert_trade(self, data: dict) -> None:
        logging.debug("Adding new trade to database")
        self.trades.insert_one(data)

    def get_trades(
        self, start_index: int, amount: int
    ) -> tuple[list[dict], int, int, int]:
        all_trades = list(self.trades.find())
        total = len(all_trades)
        intended_end_index = start_index + amount
        result = all_trades[start_index:intended_end_index]
        actual_end_index = start_index + len(result)

        return (result, total, start_index, actual_end_index)

    def __get_data(self, sku: str) -> dict | None:
        return self.prices.find_one({"sku": sku})

    def get_price(self, sku: str, intent: str) -> tuple[int, float]:
        item_price = self.__get_data(sku)

        if item_price is None:
            return (0, 0.0)

        price = item_price[intent]

        keys = price.get("keys", 0)
        metal = price.get("metal", 0.0)

        return (keys, metal)

        # metal = to_scrap(price["metal"])
        # keys = price.get("keys", 0)

        # if keys:
        #     # TODO: find a better solution to this
        #     # hardcoded to 63 refined per key
        #     metal += to_scrap(keys * 63)

        # return to_refined(metal)

    def get_skus(self) -> list[str]:
        return [item["sku"] for item in self.prices.find()]

    # TODO: rename all "name" to "sku"

    # def get_item_names(self) -> list[dict]:
    #     return [item["name"] for item in self.prices.find()]

    def get_autopriced(self) -> list[dict]:
        return [item["sku"] for item in self.prices.find({"autoprice": True})]

    def get_item(self, sku: str) -> dict:
        return self.prices.find_one({"sku": sku})

    def get_pricelist(self) -> list[dict]:
        return self.prices.find()

    # def create_price(self, name: str) -> None:
    #     self.prices.insert_one({"name": name, "autoprice": True, "buy": {}, "sell": {}})
    #     logging.info(f"Added {name} to the database")

    def add_price(self, sku: str, color: str, image: str, name: str) -> None:
        self.prices.insert_one(
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

        self.prices.replace_one(
            {"sku": sku},
            data,
        )
        logging.info(f"Updated price for {sku}")

    def update_autoprice(self, data: dict) -> None:
        sku = data["sku"]
        buy_keys = data["buy"].get("keys", 0)
        buy_metal = data["buy"].get("metal", 0.0)
        sell_keys = data["sell"].get("keys", 0)
        sell_metal = data["sell"].get("metal", 0.0)

        self.update_price(
            sku,
            {"metal": buy_metal, "keys": buy_keys},
            {"metal": sell_metal, "keys": sell_keys},
            True,
        )

    def delete_price(self, sku: str) -> None:
        self.prices.delete_one({"sku": sku})
        logging.info(f"Removed {sku} from the database")
