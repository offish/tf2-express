import logging

from tf2_utils import Item, is_pure

from ..inventory import Inventory, get_keys_and_scrap
from .base_manager import BaseManager


class InventoryManager(BaseManager, Inventory):
    async def setup(self):
        Inventory.__init__(
            self,
            self.client.steam_id,
            self.options.inventory.provider,
            self.options.inventory.api_key,
        )

    def get_in_stock(self, sku: str) -> int:
        stock = self.get_stock()
        return stock.get(sku, 0)

    def get_inventory_instance(self) -> Inventory:
        return Inventory(
            str(self.client.user.id64),
            self.options.inventory.provider,
            self.options.inventory.api_key,
        )

    def set_inventory_changed(self) -> None:
        # notify listing manager inventory has changed (stock needs to be updated)
        if self.options.backpack_tf.enable:
            self.client.listing_manager.set_inventory_changed()

    def get_stock(self) -> dict[str, int]:
        stock = {"-100;6": 0}

        if self.our_inventory is None:
            logging.warning("Inventory was not fetched")
            return stock

        for item in self.our_inventory:
            item_util = Item(item)
            sku = item["sku"]

            if item_util.is_craft_hat():
                stock["-100;6"] += 1

            if sku not in stock:
                stock[sku] = 1
            else:
                stock[sku] += 1

        logging.debug(f"Stock: {stock}")

        return stock

    def get_keys_scrap_in_inventory(self) -> tuple[int, int]:
        inventory = self.our_inventory
        return get_keys_and_scrap(inventory)

    def get_non_pure_items(self) -> list[str]:
        non_pure_items = []

        if self.our_inventory is None:
            logging.warning("Inventory was not fetched")
            return non_pure_items

        for item in self.our_inventory:
            sku = item["sku"]

            if not is_pure(sku):
                non_pure_items.append(sku)

        logging.debug(f"Non-pure items: {non_pure_items}")

        return non_pure_items

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
