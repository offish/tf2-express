from .database import Database

from tf2_utils import Item, Inventory, map_inventory


class ExpressInventory(Inventory):
    def __init__(
        self,
        db: Database,
        steam_id: str,
        provider_name: str = "steamcommunity",
        api_key: str = "",
    ) -> None:
        self.db = db
        self.steam_id = steam_id
        self.stock = {"-100;6": 0}
        super().__init__(provider_name, api_key)

    def __fetch_inventory(self, steam_id: str) -> list[dict]:
        return map_inventory(self.fetch(steam_id), True)

    def fetch_our_inventory(self) -> list[dict]:
        self.our_inventory = self.__fetch_inventory(self.steam_id)
        return self.our_inventory

    def fetch_their_inventory(self, steam_id: str) -> list[dict]:
        self.their_inventory = self.__fetch_inventory(steam_id)
        return self.their_inventory

    def get_our_inventory(self) -> list[dict]:
        return self.our_inventory.copy()

    def get_their_inventory(self) -> list[dict]:
        return self.their_inventory.copy()

    def get_stock(self) -> dict:
        return self.stock.copy()

    def update_stock(self) -> None:
        self.stock = {"-100;6": 0}

        for item in self.our_inventory:
            item_util = Item(item)
            sku = item["sku"]

            if item["tradable"] is not True:
                continue

            if item_util.is_craft_hat():
                self.stock["-100;6"] += 1

            if sku not in self.stock:
                self.stock[sku] = 1
            else:
                self.stock[sku] += 1

        self.db.update_stocks(self.stock)

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


def format_items_list_to_dict(items: list[dict]) -> dict:
    return {item["assetid"]: item for item in items}


def receipt_item_to_inventory_item(receipt_item: dict) -> dict:
    """receipt items are formatted differently than inventory items"""
    defindex = receipt_item["app_data"]["def_index"]
    asset_id = receipt_item["id"]
    context_id = str(receipt_item["contextid"])

    wiki_link = "http://wiki.teamfortress.com/scripts/itemredirect.php?id={}&lang=en_US"

    tags = []

    for tag in receipt_item["tags"]:
        color = tag.get("color", "")
        tag_data = {
            "color": color,
            "category": tag["category"],
            "internal_name": tag["internal_name"],
            "localized_tag_name": tag["name"],
            "localized_category_name": tag["category_name"],
        }
        tags.append(tag_data)

    del receipt_item["tags"]
    del receipt_item["id"]
    del receipt_item["app_data"]
    del receipt_item["pos"]
    del receipt_item["contextid"]

    return {
        **receipt_item,
        # add keys which are missing
        "assetid": asset_id,
        "actions": [
            {
                "link": wiki_link.format(defindex),
                "name": "Item Wiki Page...",
            }
        ],
        "tags": tags,
        "contextid": context_id,
    }
