import asyncio
import logging

from aiohttp import ClientSession
from tf2_utils import InvalidInventory, Item, get_keys_and_scrap, map_inventory
from tf2_utils.providers.providers import PROVIDERS
from tf2_utils.providers.steamcommunity import SteamCommunity

from .base_manager import BaseManager


class InventoryManager(BaseManager):
    async def setup(self):
        inventory_provider = self.options.inventory.provider
        api_key = self.options.inventory.api_key

        self.steam_id = self.client.steam_id
        self.our_inventory: list[dict] = []
        self.their_inventory: list[dict] = []
        self.session = ClientSession()

        # default to steamcommunity
        self.provider = SteamCommunity()

        # default to steam if no api_key is given
        if not api_key:
            return

        provider_name = inventory_provider.lower()

        # loop through providers create object
        for i in PROVIDERS:
            if provider_name == i.__name__.lower():
                # set the first found provider and then stop
                self.provider = i(api_key)
                return

    def set_inventory_changed(self) -> None:
        # notify listing manager inventory has changed (stock needs to be updated)
        if self.options.backpack_tf.enable:
            self.client.listing_manager.set_inventory_changed()

    async def fetch(self, steam_id: str) -> dict:
        url, params = self.provider.get_url_and_params(steam_id, 440, 2)

        try:
            async with self.session.get(
                url, params=params, headers=self.provider.headers
            ) as resp:
                resp.raise_for_status()
                return await resp.json()
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def fetch_inventory(self, steam_id: str) -> list[dict] | None:
        for i in range(5):
            try:
                inventory = await self.fetch(steam_id)
                return map_inventory(inventory, add_skus=True, skip_untradable=True)
            except InvalidInventory:
                logging.debug(f"Failed to fetch inventory for {steam_id}. Retrying...")
                await asyncio.sleep(2**i)

        logging.warning(f"Failed to fetch inventory for {steam_id}")

    async def fetch_our_inventory(self) -> list[dict]:
        inventory = await self.fetch_inventory(self.steam_id)
        assert inventory is not None, "Inventory could not be loaded"
        self.our_inventory = inventory
        logging.info("Fetched our inventory")
        return self.our_inventory

    def get_our_inventory(self) -> list[dict]:
        return self.our_inventory.copy()

    async def fetch_their_inventory(self, steam_id: str) -> list[dict]:
        return await self.fetch_inventory(steam_id)

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

    def get_in_stock(self, sku: str) -> int:
        stock = self.get_stock()
        return stock.get(sku, 0)

    def get_keys_scrap_in_inventory(self) -> tuple[int, int]:
        inventory = self.our_inventory
        return get_keys_and_scrap(inventory)

    def has_sku_in_our_inventory(self, sku: str) -> bool:
        return any(item["sku"] == sku for item in self.our_inventory)

    def get_last_item_in_our_inventory(self, sku: str) -> dict | None:
        inventory = self.get_our_inventory()
        inventory.reverse()

        for item in inventory:
            if item["sku"] == sku:
                return item

    async def close(self) -> None:
        await self.session.close()
