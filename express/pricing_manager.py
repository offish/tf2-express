import asyncio
import logging
import time
from typing import TYPE_CHECKING

from tf2_utils.utils import to_scrap

from .exceptions import NoKeyPrice
from .pricers.pricing_providers import get_pricing_provider

if TYPE_CHECKING:
    from .express import Express


class PricingManager:
    def __init__(self, client: "Express") -> None:
        self.client = client
        self.db = client.database
        self.options = client.options
        self.listing_manager = client.listing_manager

        self._pricelist_count = 0
        self._has_been_autopriced = set()

        self.pricing_provider = get_pricing_provider(
            self.options.pricing_provider, self._on_price_update
        )

    def _update_pricelist(self) -> None:
        self.client.are_prices_updated = False
        self._update_autopriced_items()
        self._pricelist_count = self.db.get_pricelist_count()

    def _get_key_prices(self) -> dict:
        return self.db.get_item("5021;6")

    def get_key_scrap_price(self, intent: str) -> int:
        price = self._get_key_prices().get(intent)

        if "metal" not in price:
            raise NoKeyPrice("Keys need to have a price in the database!")

        return to_scrap(price["metal"])

    def get_scrap_price(self, sku: str, intent: str) -> int:
        key_price = self.get_key_scrap_price(intent)
        keys, metal = self.db.get_price(sku, intent)
        return keys * key_price + to_scrap(metal)

    def _on_price_update(self, data: dict) -> None:
        if data.get("type") != "PRICE_CHANGED":
            return

        if "sku" not in data.get("data", {}):
            return

        sku = data["data"]["sku"]

        if sku not in self.db.get_autopriced_skus():
            return

        # update database price
        self.db.update_autoprice(data)
        self._has_been_autopriced.add(sku)

        if not self.options.use_backpack_tf:
            return

        # update listing price
        self.listing_manager.set_price_changed(sku)

    def _update_price(self, sku: str) -> None:
        price = self.pricing_provider.get_price(sku)
        self.db.update_autoprice(price)

    def _update_autopriced_items(self) -> None:
        logging.info("Updating autopriced items...")

        skus = [
            item["sku"]
            for item in self.db.get_autopriced()
            if item.get("updated", 0) + self.options.max_price_age_seconds < time.time()
        ]

        if self.options.use_backpack_tf:
            self.listing_manager.delete_inactive_listings(skus)

        for sku in self._has_been_autopriced.copy():
            if sku not in skus:
                self._has_been_autopriced.remove(sku)

        prices = self.pricing_provider.get_multiple_prices(skus)
        logging.debug(f"Got prices for {len(prices)} items")

        for sku in prices:
            if sku in self._has_been_autopriced:
                continue

            price = {"sku": sku} | prices[sku]
            self.db.update_autoprice(price)
            self._has_been_autopriced.add(sku)

            if not self.options.use_backpack_tf:
                continue

            self.listing_manager.set_price_changed(sku)

        self.client.are_prices_updated = True

        logging.info(f"Updated prices for {len(skus)} autopriced items")

    async def run(self) -> None:
        # fetches prices and checks for pricelist changes
        while True:
            await asyncio.sleep(5)

            # no change
            if self._pricelist_count == self.db.get_pricelist_count():
                continue

            # items added/removed, update prices and listings
            logging.info("Pricelist has changed, updating prices and listings...")
            self._update_pricelist()
