import logging
from typing import TYPE_CHECKING

from steam import TradeOfferReceipt
from tf2_utils import get_sku

from .conversion import item_object_to_item_data
from .inventory import ExpressInventory

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

    def get_inventory_instance(self) -> ExpressInventory:
        return ExpressInventory(
            str(self.client.user.id64),
            self.options.inventory_provider,
            self.options.inventory_api_key,
        )

    def update_inventory_with_receipt(self, receipt: TradeOfferReceipt) -> None:
        updated_inventory = self.our_inventory.copy()

        for item in receipt.sent:
            item_data = item_object_to_item_data(item)

            for i in updated_inventory.copy():
                if (
                    i["instanceid"] != item_data["instanceid"]
                    or i["classid"] != item_data["classid"]
                    or i["market_hash_name"] != item_data["market_hash_name"]
                ):
                    continue

                del updated_inventory[i]
                break

        for item in receipt.received:
            item_data = item_object_to_item_data(item)
            item_data["sku"] = get_sku(item_data)

            updated_inventory.append(item_data)

        self.set_our_inventory(updated_inventory)

        logging.info("Our inventory was updated")

        if not self.options.use_backpack_tf:
            return

        # notify listing manager inventory has changed (stock needs to be updated)
        self.client.listing_manager.set_inventory_changed()
