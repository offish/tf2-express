import logging
from typing import TYPE_CHECKING

from steam import MovedItem, TradeOfferReceipt
from tf2_utils import get_sku

from .inventory import ExpressInventory
from .utils import is_same_item

if TYPE_CHECKING:
    from .express import Express


class InventoryManager(ExpressInventory):
    def __init__(self, client: "Express") -> None:
        self.client = client
        self.options = client.options

        super().__init__(
            str(client.user.id64),
            self.options.inventory_provider,
            self.options.inventory_api_key,
        )

    @staticmethod
    def _get_new_asset_id(item: dict, moved_items: list[MovedItem]) -> int:
        for moved_item in moved_items:
            if is_same_item(
                item,
                {"instanceid": moved_item.instance_id, "classid": moved_item.class_id},
            ):
                return moved_item.new_id
        return -1

    def get_inventory_instance(self) -> ExpressInventory:
        return ExpressInventory(
            str(self.client.user.id64),
            self.options.inventory_provider,
            self.options.inventory_api_key,
        )

    async def update_inventory_with_receipt(
        self, their_items: list[dict], our_items: list[dict], receipt: TradeOfferReceipt
    ) -> None:
        logging.debug(f"{receipt=}")
        updated_inventory = self.our_inventory.copy()

        for item in our_items:
            for old_item in updated_inventory.copy():
                if not is_same_item(item, old_item):
                    continue

                logging.debug(f"{old_item=}")

                index = updated_inventory.index(old_item)
                del updated_inventory[index]

                logging.debug(f"removed from inventory {index=}")
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

        logging.info("Our inventory was updated")

        # notify listing manager inventory has changed (stock needs to be updated)
        if self.options.use_backpack_tf:
            self.client.listing_manager.set_inventory_changed()
