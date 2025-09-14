import asyncio
import logging
import time
from typing import Any

from tf2_utils.utils import to_scrap

from ..exceptions import NoKeyPrice
from ..pricers.pricing_providers import get_pricing_provider
from .base_manager import BaseManager


class PricingManager(BaseManager):
    def setup(self) -> None:
        self._last_autopriced_items = []
        self._failed_skus = set()
        self._last_failed_time = 0

        self.provider = get_pricing_provider(
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

        updated_count = 0
        prices = self.provider.get_multiple_prices(skus)
        logging.debug(f"Got prices for {len(prices)} out of {len(skus)} items")

        for sku in prices:
            price = prices[sku]
            self._update_price(sku, price, notify_listing_manager=False)
            updated_count += 1

        self._failed_skus = {sku for sku in skus if sku not in prices}

        if self._failed_skus:
            logging.info(
                f"Updated prices for {updated_count} items, {len(self._failed_skus)} items still waiting for prices"
            )
        else:
            logging.info(f"Updated prices for {updated_count} autopriced items")

    def _retry_failed_skus(self) -> None:
        if not self._failed_skus:
            return

        current_time = time.time()

        if current_time - self._last_failed_time < 15:
            return

        logging.info(f"Retrying prices for {len(self._failed_skus)} failed items...")

        skus = list(self._failed_skus)
        prices = self.provider.get_multiple_prices(skus)
        updated_count = 0

        for sku in prices:
            price = prices[sku]
            self._update_price(sku, price, notify_listing_manager=True)
            updated_count += 1

        self._failed_skus = {sku for sku in self._failed_skus if sku not in prices}
        self._last_failed_time = current_time

        if updated_count > 0:
            logging.info(
                f"Successfully got prices for {updated_count} previously failed items"
            )

        if self._failed_skus:
            logging.debug(
                f"Still waiting for prices for {len(self._failed_skus)} items"
            )

    def _get_and_update_price(self, sku: str) -> None:
        price = self.pricer.get_price(sku)

        if not price:
            logging.debug(f"No price data received for {sku} ({price})")
            self._failed_skus.append(sku)
            return

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

            # TODO: something wrong with this, says there are failed, but non are sent to api
            # self._retry_failed_skus()
            skus = self._get_skus_changed()

            # no changes to pricelist
            if not skus:
                logging.debug("No changes to pricelist")
                continue

            logging.info("Pricelist has changed, updating prices and listings...")

            for sku in skus:
                self._get_and_update_price(sku)

            self._last_autopriced_items = self.db.get_autopriced()
