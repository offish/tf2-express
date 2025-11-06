from typing import Any


class DatabaseProvider:
    def __init__(self, username: str) -> None:
        raise NotImplementedError

    def has_price(self, sku: str) -> bool:
        raise NotImplementedError

    def find_item_by_name(self, normalized_name: str) -> dict | None:
        raise NotImplementedError

    def get_normalized_item_name(self, sku: str) -> str | None:
        raise NotImplementedError

    def insert_trade(self, data: dict) -> None:
        raise NotImplementedError

    def get_trades(self, start_index: int, amount: int) -> dict[str, Any]:
        raise NotImplementedError

    def get_price(self, sku: str, intent: str) -> tuple[int, float]:
        raise NotImplementedError

    def get_skus(self) -> list[str]:
        raise NotImplementedError

    def get_autopriced(self) -> list[dict]:
        raise NotImplementedError

    def get_autopriced_skus(self) -> list[str]:
        raise NotImplementedError

    def get_item(self, sku: str) -> dict[str, Any]:
        raise NotImplementedError

    def get_pricelist(self) -> list[dict]:
        raise NotImplementedError

    def get_stock(self, sku: str) -> tuple[int, int]:
        raise NotImplementedError

    def get_max_stock(self, sku: str) -> int:
        raise NotImplementedError

    def replace_item(self, data: dict) -> None:
        raise NotImplementedError

    def update_stock(self, stock: dict) -> None:
        raise NotImplementedError

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
        raise NotImplementedError

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
