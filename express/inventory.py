from typing import Any

from tf2_utils import Inventory, Item, get_sku, is_pure, map_inventory


class ExpressInventory(Inventory):
    def __init__(
        self,
        our_steam_id: str,
        provider_name: str = "steamcommunity",
        api_key: str = "",
    ) -> None:
        self.steam_id = our_steam_id
        self.stock = {"-100;6": 0}
        super().__init__(provider_name, api_key)

    def _fetch_inventory(self, steam_id: str) -> list[dict]:
        return map_inventory(self.fetch(steam_id), True)

    def set_our_inventory(self, inventory: list[dict]) -> list[dict]:
        self.our_inventory = inventory
        return self.our_inventory

    def fetch_our_inventory(self) -> list[dict]:
        self.our_inventory = self._fetch_inventory(self.steam_id)
        return self.our_inventory

    def fetch_their_inventory(self, steam_id: str) -> list[dict]:
        self.their_inventory = self._fetch_inventory(steam_id)
        return self.their_inventory

    def get_our_inventory(self) -> list[dict]:
        return self.our_inventory.copy()

    def get_their_inventory(self) -> list[dict]:
        return self.their_inventory.copy()

    def get_stock(self) -> dict[str, int]:
        stock = {"-100;6": 0}

        for item in self.our_inventory:
            item_util = Item(item)
            sku = item["sku"]

            if item["tradable"] is not True:
                continue

            if item_util.is_craft_hat():
                stock["-100;6"] += 1

            if sku not in self.stock:
                stock[sku] = 1
            else:
                stock[sku] += 1

        return stock

    def has_sku_in_inventory(self, sku: str, who: str = "us") -> bool:
        inventory = self.our_inventory if who == "us" else self.their_inventory

        for item in inventory:
            if item["sku"] == sku:
                return True

        return False

    def has_sku_in_their_inventory(self, sku: str) -> bool:
        return self.has_sku_in_inventory(sku, "them")

    def has_sku_in_our_inventory(self, sku: str) -> bool:
        return self.has_sku_in_inventory(sku, "us")

    def get_last_item(self, sku: str, who: str = "us") -> dict:
        inventory = self.our_inventory if who == "us" else self.their_inventory
        last_item = {}

        for item in inventory:
            if item["sku"] == sku:
                last_item = item

        return last_item

    def get_last_item_in_their_inventory(self, sku: str) -> dict:
        return self.get_last_item(sku, "them")

    def get_last_item_in_our_inventory(self, sku: str) -> dict:
        return self.get_last_item(sku, "us")

    def remove_item(self, item: dict) -> None:
        self.our_inventory.remove(item)

    def add_item(self, item: dict) -> None:
        self.our_inventory.append(item)


def get_first_non_pure_sku(items: list[dict]) -> str | None:
    for i in items:
        sku = get_sku(i)

        if not is_pure(sku):
            return sku


def receipt_item_to_inventory_item(receipt_item: dict[str, Any]) -> dict[str, Any]:
    """receipt items are formatted differently than inventory items"""
    defindex = receipt_item["app_data"]["def_index"]
    asset_id = receipt_item["id"]

    wiki_link = "http://wiki.teamfortress.com/scripts/itemredirect.php?id={}&lang=en_US"

    tags = [
        {
            "color": tag.get("color", ""),
            "category": tag["category"],
            "internal_name": tag["internal_name"],
            "localized_tag_name": tag["name"],
            "localized_category_name": tag["category_name"],
        }
        for tag in receipt_item["tags"]
    ]

    del receipt_item["tags"]
    del receipt_item["id"]
    del receipt_item["app_data"]
    del receipt_item["pos"]

    return receipt_item | {
        # add keys which are missing
        "assetid": asset_id,
        "actions": [
            {
                "link": wiki_link.format(defindex),
                "name": "Item Wiki Page...",
            }
        ],
        "tags": tags,
    }
