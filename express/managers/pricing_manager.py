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
        self._failed_skus = []  # Track SKUs that failed to get prices
        self._last_retry_time = 0  # Track when we last retried failed SKUs

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

        prices = self.pricer.get_multiple_prices(skus)
        logging.debug(f"Got prices for {len(prices)} out of {len(skus)} items")

        # Update prices for items we got data for
        updated_count = 0
        for sku in prices:
            price = prices[sku]
            self._update_price(sku, price, notify_listing_manager=False)
            updated_count += 1

        # Track failed SKUs for retry later
        self._failed_skus = [sku for sku in skus if sku not in prices]
        
        if self._failed_skus:
            logging.info(f"Updated prices for {updated_count} items, {len(self._failed_skus)} items still waiting for prices")
        else:
            logging.info(f"Updated prices for {updated_count} autopriced items")

    def _retry_failed_skus(self) -> None:
        """Retry getting prices for previously failed SKUs"""
        if not self._failed_skus:
            return
            
        current_time = time.time()
        # Only retry every 15 seconds
        if current_time - self._last_retry_time < 15:
            return
            
        self._last_retry_time = current_time
        logging.info(f"Retrying prices for {len(self._failed_skus)} failed items...")
        
        prices = self.pricer.get_multiple_prices(self._failed_skus.copy())
        
        # Update prices for items we now have data for
        updated_count = 0
        for sku in prices:
            price = prices[sku]
            self._update_price(sku, price, notify_listing_manager=True)  # Notify listing manager for retries
            updated_count += 1
            
        # Remove successfully updated SKUs from failed list
        self._failed_skus = [sku for sku in self._failed_skus if sku not in prices]
        
        if updated_count > 0:
            logging.info(f"Successfully got prices for {updated_count} previously failed items")
        if self._failed_skus:
            logging.debug(f"Still waiting for prices for {len(self._failed_skus)} items")

    def _get_and_update_price(self, sku: str) -> None:
        price = self.pricer.get_price(sku)
        if price is not None:
            self._update_price(sku, price)
        else:
            logging.debug(f"Price not yet available for {sku}, will retry later")
            if sku not in self._failed_skus:
                self._failed_skus.append(sku)

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

        # Connect to pricer websocket for real-time updates
        try:
            await self.pricer.connect_websocket()
            # Start websocket listener task
            asyncio.create_task(self.pricer.listen())
            logging.info("Connected to pricer websocket for real-time price updates")
            
            # Subscribe to all autopriced items
            autopriced_skus = self.db.get_autopriced_skus()
            if autopriced_skus:
                await self.pricer.subscribe_to_items(autopriced_skus)
                logging.info(f"Subscribed to {len(autopriced_skus)} autopriced items for real-time updates")
            
        except Exception as e:
            logging.error(f"Failed to connect to pricer websocket: {e}")

        self._update_entire_pricelist()
        self.listing_manager.create_listings()

        # fetches prices and checks for pricelist changes
        while True:
            await asyncio.sleep(5)

            # Try to retry failed SKUs every cycle
            self._retry_failed_skus()

            skus = self._get_skus_changed()

            # no changes to pricelist
            if not skus:
                logging.debug("No changes to pricelist")
                continue

            logging.info("Pricelist has changed, updating prices and listings...")

            for sku in skus:
                self._get_and_update_price(sku)

            self._last_autopriced_items = self.db.get_autopriced()
