import logging

from tf2_utils import Item, is_pure

from ..inventory import ExpressInventory, get_keys_and_scrap
from .base_manager import BaseManager


class InventoryManager(BaseManager, ExpressInventory):
    async def setup(self):
        ExpressInventory.__init__(
            self,
            self.client.steam_id,
            self.options.inventory.provider,
            self.options.inventory.api_key,
        )

    def get_in_stock(self, sku: str) -> int:
        stock = self.get_stock()
        return stock.get(sku, 0)

    def get_inventory_instance(self) -> ExpressInventory:
        return ExpressInventory(
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

    # @staticmethod
    # def _get_new_asset_id(item: dict, moved_items: list[MovedItem]) -> int:
    #     for moved_item in moved_items:
    #         moved = {
    #             "instanceid": moved_item.instance_id,
    #             "classid": moved_item.class_id,
    #         }

    #         if is_same_item(item, moved):
    #             return int(moved_item.new_id)

    #     return -1

    # NOTE: this fails randomly due to keys missing. steam.py or steam issue
    # async def update_inventory_with_receipt(
    #     self, their_items: list[dict], our_items: list[dict], receipt: TradeOfferReceipt
    # ) -> None:
    #     logging.debug(f"{receipt=}")
    #     updated_inventory = self.our_inventory.copy()

    #     for item in our_items:
    #         for old_item in updated_inventory.copy():
    #             if not is_same_item(item, old_item):
    #                 continue

    #             index = updated_inventory.index(old_item)
    #             del updated_inventory[index]
    #             break

    #     for item in their_items:
    #         asset_id = self._get_new_asset_id(item, receipt.received)
    #         sku = get_sku(item)

    #         logging.debug(f"{item=}")
    #         logging.debug(f"{sku=}")
    #         logging.debug(f"{asset_id=}")

    #         item["sku"] = get_sku(item)
    #         item["assetid"] = str(asset_id)

    #         updated_inventory.append(item)

    #     self.set_our_inventory(updated_inventory)

    #     logging.info("Inventory was updated")
    #     self.set_inventory_changed()
