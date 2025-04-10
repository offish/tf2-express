import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from tf2_utils.utils import to_scrap

from ..exceptions import NoKeyPrice
from ..pricers.pricing_providers import get_pricing_provider

if TYPE_CHECKING:
    from ..express import Express


class PricingManager:
    def __init__(self, client: "Express") -> None:
        self.client = client
        self.db = client.database
        self.options = client.options
        self.listing_manager = client.listing_manager

        self._last_autopriced_items = []

        self.pricer = get_pricing_provider(
            self.options.pricing_provider, self._on_price_update
        )

    @staticmethod
    def _get_items(item_list: list[dict]) -> dict:
        # must be autopriced items
        return {item["sku"]: item for item in item_list if item.get("autoprice", False)}

    def _get_key_prices(self) -> dict:
        return self.db.get_item("5021;6")

    def get_key_scrap_price(self, intent: str) -> int:
        price = self._get_key_prices().get(intent)

        if "metal" not in price:
            raise NoKeyPrice("Keys need to have a price in the database!")

        return to_scrap(price["metal"])

    def get_item(self, sku: str) -> dict[str, Any]:
        return self.db.get_item(sku)

    def get_scrap_price(self, sku: str, intent: str) -> int:
        key_price = self.get_key_scrap_price(intent)
        keys, metal = self.db.get_price(sku, intent)
        return keys * key_price + to_scrap(metal)

    def _update_price(
        self, sku: str, price: dict, notify_listing_manager: bool = True
    ) -> None:
        data = {"sku": sku} | price
        self.db.update_autoprice(data)

        if self.options.use_backpack_tf and notify_listing_manager:
            self.listing_manager.set_price_changed(sku)

    def _on_price_update(self, data: dict) -> None:
        if data.get("type") != "PRICE_CHANGED":
            return

        if "sku" not in data.get("data", {}):
            return

        sku = data["data"]["sku"]

        if sku not in self.db.get_autopriced_skus():
            return

        self._update_price(sku, data)

    def _update_all_autopriced_items(self) -> None:
        logging.info("Updating autopriced items...")

        skus = [
            item["sku"]
            for item in self.db.get_autopriced()
            if item.get("updated", 0) + self.options.max_price_age_seconds < time.time()
            or item["buy"] == {}
            or item["sell"] == {}
        ]

        prices = self.pricer.get_multiple_prices(skus)
        logging.debug(f"Got prices for {len(prices)} items")

        for sku in prices:
            price = prices[sku]
            self._update_price(sku, price, notify_listing_manager=False)

        logging.info(f"Updated prices for {len(skus)} autopriced items")

    def _get_and_update_price(self, sku: str) -> None:
        price = self.pricer.get_price(sku)
        self._update_price(sku, price)

    def _update_entire_pricelist(self) -> None:
        self._update_all_autopriced_items()
        self._last_autopriced_items = self.db.get_autopriced()
        self.client.are_prices_updated = True

    def _get_skus_changed(self) -> list[str]:
        old_pricelist = self._get_items(self._last_autopriced_items)
        new_pricelist = self._get_items(self.db.get_autopriced())
        changed_skus = set()

        for sku in new_pricelist:
            # item was added
            if sku not in old_pricelist:
                changed_skus.add(sku)
                continue

            buy_price = new_pricelist[sku]["buy"]
            sell_price = new_pricelist[sku]["sell"]

            # price have been changed and then reset with autoprice button
            if not buy_price or not sell_price:
                changed_skus.add(sku)

        return list(changed_skus)

    async def run(self) -> None:
        if self.options.use_backpack_tf:
            await self.listing_manager.wait_until_ready()

        self._update_entire_pricelist()
        self.listing_manager.create_listings()

        # fetches prices and checks for pricelist changes
        while True:
            await asyncio.sleep(5)

            skus = self._get_skus_changed()

            # no changes to pricelist
            if not skus:
                logging.debug("No changes to pricelist")
                continue

            logging.info("Pricelist has changed, updating prices and listings...")

            for sku in skus:
                self._get_and_update_price(sku)

            self._last_autopriced_items = self.db.get_autopriced()
