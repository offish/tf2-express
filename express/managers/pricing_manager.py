import asyncio
import logging
from typing import Any

from tf2_utils.utils import to_scrap

from ..exceptions import NoKeyPrice, WrongPriceFormat
from ..pricers.pricing_providers import get_pricing_provider
from ..utils import filter_skus, has_invalid_price_format
from .base_manager import BaseManager


class PricingManager(BaseManager):
    def setup(self) -> None:
        self.autopriced_skus: list[str] = []
        self.autopriced_items: list[dict] = []

        self.provider = get_pricing_provider(
            self.options.pricing_provider, self.on_price_update
        )

    @staticmethod
    def filter_items(item_list: list[dict]) -> dict:
        # must be autopriced items
        return {item["sku"]: item for item in item_list if item.get("autoprice", False)}

    def on_price_update(self, data: dict) -> None:
        sku = data.get("sku")

        if not sku:
            raise WrongPriceFormat(f"Price update has no SKU: {data}")

        if sku not in self.autopriced_skus:
            return

        self.update_price(sku, data, notify_listing_manager=True)

    def set_prices_updated(self) -> None:
        assert self.client.are_prices_updated is False
        self.client.are_prices_updated = True

    def get_item(self, sku: str) -> dict[str, Any]:
        return self.database.get_item(sku)

    def get_key_prices(self) -> dict:
        return self.database.get_item("5021;6")

    def get_key_scrap_price(self, intent: str) -> int:
        price = self.get_key_prices().get(intent)

        if "metal" not in price:
            raise NoKeyPrice("Keys need to have a price in the database!")

        return to_scrap(price["metal"])

    def get_scrap_price(self, sku: str, intent: str) -> int:
        key_price = self.get_key_scrap_price(intent)
        keys, metal = self.database.get_price(sku, intent)
        return keys * key_price + to_scrap(metal)

    def update_price(self, sku: str, data: dict, notify_listing_manager: bool) -> None:
        price = {"sku": sku} | data

        if has_invalid_price_format(price):
            raise WrongPriceFormat(f"Price update has invalid format: {price}")

        buy = price["buy"]
        sell = price["sell"]

        self.database.update_price(sku, buy, sell)

        if self.options.use_backpack_tf and notify_listing_manager:
            self.listing_manager.set_price_changed(sku)

    def update_prices(
        self, prices: dict[str, dict], notify_listing_manager: bool = True
    ) -> None:
        for sku in prices:
            price = prices[sku]
            self.update_price(sku, price, notify_listing_manager)

        logging.info(f"Updated prices for {len(prices)} items")

    def get_and_update_price(self, sku: str) -> None:
        price = self.provider.get_price(sku)
        self.update_price(sku, price, notify_listing_manager=True)

    def get_and_update_prices(self, skus: list[str]) -> None:
        if len(skus) == 1:
            self.get_and_update_price(skus[0])
            return

        prices = self.provider.get_multiple_prices(skus)

        if not prices:
            logging.warning(f"No price data received for {skus} ({prices})")
            return

        self.update_prices(prices)

    def update_pricelist(self) -> None:
        logging.info("Updating autopriced items...")

        autopriced_items = self.database.get_autopriced()
        skus = filter_skus(autopriced_items)

        if not skus:
            logging.info("No autopriced items to update")
            return

        prices = self.provider.get_multiple_prices(skus)
        logging.debug(f"Got prices for {len(prices)} out of {len(skus)} items")
        # dont notify listing manager, we will create listings after this
        self.update_prices(prices, notify_listing_manager=False)

        self.autopriced_items = autopriced_items
        self.autopriced_skus = skus

    def get_skus_changed(self) -> list[str]:
        current_autopriced = self.database.get_autopriced()
        changed_skus = set()

        old_pricelist = self.filter_items(self.autopriced_items)
        new_pricelist = self.filter_items(current_autopriced)

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

        self.update_pricelist()
        self.set_prices_updated()

        if self.options.use_backpack_tf:
            self.listing_manager.create_listings()

        # fetches prices and checks for pricelist changes
        while True:
            await asyncio.sleep(5)

            skus = self.get_skus_changed()

            # no changes to pricelist
            if not skus:
                logging.debug("No changes to pricelist")
                continue

            logging.info("Pricelist has changed, updating prices and listings...")
            self.get_and_update_prices(skus)

            autopriced_items = self.database.get_autopriced()
            self.autopriced_items = autopriced_items
            self.autopriced_skus = filter_skus(autopriced_items)
