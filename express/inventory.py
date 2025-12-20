import logging
import time

from tf2_utils import (
    InvalidInventory,
    Inventory,
    get_metal,
    get_sku,
    is_key,
    is_pure,
    map_inventory,
)


class ExpressInventory(Inventory):
    def __init__(
        self,
        our_steam_id: str,
        provider_name: str = "steamcommunity",
        api_key: str = "",
    ) -> None:
        self.steam_id = our_steam_id
        self.our_inventory: list[dict] = []
        self.their_inventory: list[dict] = []

        super().__init__(provider_name, api_key)

    def _fetch_inventory(self, steam_id: str) -> list[dict] | None:
        for i in range(5):
            try:
                inventory = self.fetch(steam_id)
                return map_inventory(inventory, add_skus=True, skip_untradable=True)
            except InvalidInventory:
                logging.debug(f"Failed to fetch inventory for {steam_id}. Retrying...")
                time.sleep(2**i)

        logging.warning(f"Failed to fetch inventory for {steam_id}")

    def set_our_inventory(self, inventory: list[dict]) -> list[dict]:
        self.our_inventory = inventory
        return self.our_inventory

    def fetch_our_inventory(self) -> list[dict]:
        inventory = self._fetch_inventory(self.steam_id)

        assert inventory is not None, "Inventory could not be loaded"
        self.our_inventory = inventory
        logging.info("Fetched our inventory")

        return self.our_inventory

    def fetch_their_inventory(self, steam_id: str) -> list[dict]:
        self.their_inventory = self._fetch_inventory(steam_id)
        return self.their_inventory

    def get_our_inventory(self) -> list[dict]:
        return self.our_inventory.copy()

    def get_their_inventory(self) -> list[dict]:
        return self.their_inventory.copy()


def get_non_pure_skus(items: list[dict]) -> list[str]:
    skus = []

    for i in items:
        sku = get_sku(i)

        if not is_pure(sku):
            skus.append(sku)

    return skus


def get_keys_and_scrap(inventory: list[dict]) -> tuple[int, int]:
    keys = 0
    scrap = 0

    for i in inventory:
        sku = i["sku"]

        if is_key(sku):
            keys += 1
            continue

        if is_pure(sku):
            scrap += get_metal(sku)
            continue

    return keys, scrap
