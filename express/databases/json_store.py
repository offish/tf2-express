import json
import logging
import time
from pathlib import Path
from typing import Any

from tf2_utils import is_metal

from ..exceptions import SKUNotFound
from .database_provider import DatabaseProvider


class JSON(DatabaseProvider):
    def __init__(self, username: str) -> None:
        self.name = username

        self.data_dir = Path(__file__).parent.parent.parent / "files" / username
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.trades_file = self.data_dir / "trades.json"
        self.items_file = self.data_dir / "items.json"
        self.arbitrage_file = self.data_dir / "arbitrage.json"

        self._init_file(self.trades_file, [])
        self._init_file(self.items_file, [])
        self._init_file(self.arbitrage_file, [])

        # bot needs key price to work
        if not self.get_item("5021;6"):
            self._add_key_for_first_time()

    def _init_file(self, filepath: Path, default_data: Any) -> None:
        if not filepath.exists():
            self._write_json(filepath, default_data)

    def _read_json(self, filepath: Path) -> Any:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_json(self, filepath: Path, data: Any) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def insert_trade(self, data: dict) -> None:
        trades = self._read_json(self.trades_file)
        trades.append(data)
        self._write_json(self.trades_file, trades)
        logging.info("Offer was added to the database")

    def get_trades_sorted(self):
        return self._read_json(self.trades_file)

    def get_items(self) -> list[dict]:
        return self._read_json(self.items_file)

    def replace_item(self, data: dict) -> None:
        sku = data["sku"]

        logging.debug(f"Updating {sku} with {data=}")
        items = self.get_items()

        for i, item in enumerate(items):
            if item["sku"] == sku:
                items[i] = data
                break

        self._write_json(self.items_file, items)

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

        items = self.get_items()
        items.append(document)
        self._write_json(self.items_file, items)
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

        self.replace_item(data)
        logging.info(f"Updated price for {sku}")

    def delete_all_items(self) -> None:
        self._write_json(self.items_file, [])

    def delete_item(self, sku: str) -> None:
        items = self.get_items()
        items = [item for item in items if item["sku"] != sku]
        self._write_json(self.items_file, items)
        logging.info(f"Removed {sku} from the database")

    def insert_arbitrage(self, data: dict) -> None:
        arbitrages = self._read_json(self.arbitrage_file)
        arbitrages.append(data)
        self._write_json(self.arbitrage_file, arbitrages)

    def update_arbitrage(self, sku: str, data: dict) -> None:
        arbitrages = self._read_json(self.arbitrage_file)

        for i, arb in enumerate(arbitrages):
            if arb["sku"] == sku:
                arbitrages[i] = data
                break

        self._write_json(self.arbitrage_file, arbitrages)

    def delete_arbitrage(self, sku: str) -> None:
        arbitrages = self._read_json(self.arbitrage_file)
        arbitrages = [arb for arb in arbitrages if arb["sku"] != sku]
        self._write_json(self.arbitrage_file, arbitrages)

    def get_arbitrages(self) -> list[dict]:
        return self._read_json(self.arbitrage_file)
