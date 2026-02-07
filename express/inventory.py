import asyncio
import logging

from aiohttp import ClientSession
from tf2_utils import get_metal, get_sku, is_key, is_pure, map_inventory
from tf2_utils.exceptions import InvalidInventory
from tf2_utils.providers.providers import PROVIDERS
from tf2_utils.providers.steamcommunity import SteamCommunity


class Inventory:
    def __init__(
        self,
        our_steam_id: str,
        provider_name: str = "steamcommunity",
        api_key: str = "",
    ) -> None:
        self.steam_id = our_steam_id
        self.our_inventory: list[dict] = []
        self.their_inventory: list[dict] = []
        self.session = ClientSession()

        # default to steamcommunity
        self.provider = SteamCommunity()

        # default to steam if no api_key is given
        if not api_key:
            return

        provider_name = provider_name.lower()

        # loop through providers create object
        for i in PROVIDERS:
            if provider_name == i.__name__.lower():
                # set the first found provider and then stop
                self.provider = i(api_key)
                break

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

    def set_our_inventory(self, inventory: list[dict]) -> list[dict]:
        self.our_inventory = inventory
        return self.our_inventory

    async def fetch_our_inventory(self) -> list[dict]:
        inventory = await self.fetch_inventory(self.steam_id)

        assert inventory is not None, "Inventory could not be loaded"
        self.our_inventory = inventory
        logging.info("Fetched our inventory")

        return self.our_inventory

    async def fetch_their_inventory(self, steam_id: str) -> list[dict]:
        self.their_inventory = await self.fetch_inventory(steam_id)
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
