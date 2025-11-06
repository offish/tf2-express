import logging

from steam import MovedItem, TradeOfferReceipt
from tf2_utils import get_sku

from ..inventory import ExpressInventory
from ..utils import is_same_item
from .base_manager import BaseManager


class InventoryManager(BaseManager, ExpressInventory):
    async def setup(self):
        ExpressInventory.__init__(
            self,
            self.client.steam_id,
            self.options.inventory.provider,
            self.options.inventory.api_key,
        )

    @staticmethod
    def _get_new_asset_id(item: dict, moved_items: list[MovedItem]) -> int:
        for moved_item in moved_items:
            moved = {
                "instanceid": moved_item.instance_id,
                "classid": moved_item.class_id,
            }

            if is_same_item(item, moved):
                return int(moved_item.new_id)

        return -1

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

    async def update_inventory_with_receipt(
        self, their_items: list[dict], our_items: list[dict], receipt: TradeOfferReceipt
    ) -> None:
        logging.debug(f"{receipt=}")
        updated_inventory = self.our_inventory.copy()

        for item in our_items:
            for old_item in updated_inventory.copy():
                if not is_same_item(item, old_item):
                    continue

                index = updated_inventory.index(old_item)
                del updated_inventory[index]
                break

        for item in their_items:
            asset_id = self._get_new_asset_id(item, receipt.received)
            sku = get_sku(item)

            logging.debug(f"{item=}")
            logging.debug(f"{sku=}")
            logging.debug(f"{asset_id=}")

            item["sku"] = get_sku(item)
            item["assetid"] = str(asset_id)

            updated_inventory.append(item)

        self.set_our_inventory(updated_inventory)

        logging.info("Inventory was updated")
        self.set_inventory_changed()
