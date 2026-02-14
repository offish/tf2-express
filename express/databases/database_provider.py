import logging
from typing import Any

from tf2_utils import normalize_item_name

from ..utils import has_buy_and_sell_price, sku_to_item_data


class DatabaseProvider:
    def __init__(self, username: str) -> None:
        raise NotImplementedError

    def _add_key_for_first_time(self) -> None:
        self.add_item(**sku_to_item_data("5021;6"))

    def has_price(self, sku: str) -> bool:
        data = self.get_item(sku)

        if not data:
            return False

        return has_buy_and_sell_price(data)

    def find_item_by_name(self, normalized_name: str) -> dict | None:
        for item in self.get_items():
            if normalize_item_name(item["name"]) != normalized_name:
                continue

            if "_id" in item:
                del item["_id"]

            return item

    def get_normalized_item_name(self, sku: str) -> str | None:
        item = self.get_item(sku)

        if item:
            return normalize_item_name(item["name"])

    def insert_trade(self, data: dict) -> None:
        raise NotImplementedError

    def get_trades_sorted(self) -> list[dict]:
        raise NotImplementedError

    def get_trades(self, start_index: int, amount: int) -> dict[str, Any]:
        # sort newest trades first
        sorted_trades = self.get_trades_sorted()
        total_trades = len(sorted_trades)
        intended_end_index = start_index + amount
        trades = sorted_trades[start_index:intended_end_index]
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
        return [item["sku"] for item in self.get_items()]

    def get_autopriced(self) -> list[dict]:
        items = self.get_items()
        return [
            item
            for item in items
            if item.get("autoprice", False) and item["sku"] != "-100;6"
        ]

    def get_autopriced_skus(self) -> list[str]:
        return [item["sku"] for item in self.get_autopriced()]

    def get_items(self) -> list[dict]:
        raise NotImplementedError

    def get_item(self, sku: str) -> dict[str, Any]:
        items = self.get_items()

        for item in items.copy():
            if item["sku"] != sku:
                continue

            if "_id" in item:
                del item["_id"]

            return item

        return {}

    def get_stock(self, sku: str) -> tuple[int, int]:
        """returns in_stock, max_stock"""
        data = self.get_item(sku)
        return (data.get("in_stock", 0), data.get("max_stock", -1))

    def get_max_stock(self, sku: str) -> int:
        return self.get_item(sku).get("max_stock", -1)

    def replace_item(self, data: dict) -> None:
        raise NotImplementedError

    def update_stock(self, stock: dict) -> None:
        all_items = self.get_items()

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
        raise NotImplementedError

    def add_price(
        self,
        sku: str,
        buy: dict = None,
        sell: dict = None,
        max_stock: int = 1,
    ) -> None:
        item_data = sku_to_item_data(sku)
        self.add_item(
            **item_data,
            autoprice=False,
            max_stock=max_stock,
            buy=buy,
            sell=sell,
        )

    def update_price(
        self,
        sku: str,
        buy: dict,
        sell: dict,
        override_autoprice: bool = None,
        override_max_stock: int = None,
    ) -> None:
        raise NotImplementedError

    def update_autoprice(self, data: dict) -> None:
        self.update_price(data["sku"], data["buy"], data["sell"])

    def delete_all_items(self) -> None:
        raise NotImplementedError

    def delete_items(self) -> None:
        key = self.get_item("5021;6")

        if "_id" in key:
            del key["_id"]

        self.delete_all_items()
        self.add_item(**key)

    def delete_item(self, sku: str) -> None:
        raise NotImplementedError

    def insert_arbitrage(self, data: dict) -> None:
        raise NotImplementedError

    def update_arbitrage(self, sku: str, data: dict) -> None:
        raise NotImplementedError

    def delete_arbitrage(self, sku: str) -> None:
        raise NotImplementedError

    def get_arbitrages(self) -> list[dict]:
        raise NotImplementedError
