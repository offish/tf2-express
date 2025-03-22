import logging
import time
from threading import Thread
from typing import TYPE_CHECKING

from tf2_utils.prices_tf_websocket import PricesTFWebsocket
from tf2_utils.utils import to_scrap

from .exceptions import NoKeyPrice

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

    def _update_pricelist(self) -> None:
        self.client.are_prices_updated = False
        self._update_autopriced_items()
        self._pricelist_count = self.db.get_pricelist_count()

    def _get_key_prices(self) -> dict:
        data = self.db.get_item("5021;6")
        return {"buy": data["buy"], "sell": data["sell"]}

    def get_key_scrap_price(self, intent: str) -> int:
        price = self._get_key_prices().get(intent)

        if "metal" not in price:
            raise NoKeyPrice("Keys need to have a price in the database!")

        return to_scrap(price["metal"])

    def get_scrap_price(self, sku: str, intent: str) -> int:
        key_price = self.get_key_scrap_price(intent)
        keys, metal = self.db.get_price(sku, intent)
        return key_price * keys + to_scrap(metal)

    def _on_price_update(self, data: dict) -> None:
        if data.get("type") != "PRICE_CHANGED":
            return

        if "sku" not in data.get("data", {}):
            return

        sku = data["data"]["sku"]

        if sku not in self.db.get_autopriced():
            return

        # update database price
        self.db.update_autoprice(data)
        self._has_been_autopriced.add(sku)

        if not self.options.use_backpack_tf:
            return

        # update listing price
        self.listing_manager.set_price_changed(sku)

    def _update_price(self, sku: str) -> None:
        price = self._prices_tf.get_price(sku)
        self.db.update_autoprice(price)

    def _update_autopriced_items(self) -> None:
        skus = self.db.get_autopriced()

        if self.options.use_backpack_tf:
            self.listing_manager.delete_inactive_listings(skus)

        self._prices_tf.request_access_token()

        for sku in self._has_been_autopriced.copy():
            if sku not in skus:
                self._has_been_autopriced.remove(sku)

        # make this more efficient, fetch x pages and check for missing
        # if missing fetch the missing ones directly
        # should probably request price updates also
        for sku in skus:
            if sku in self._has_been_autopriced:
                continue

            self._update_price(sku)
            self._has_been_autopriced.add(sku)

            if not self.options.use_backpack_tf:
                continue

            self.listing_manager.set_price_changed(sku)

        self.client.are_prices_updated = True

        logging.info(f"Updated prices for {len(skus)} autopriced items")

    def _pricelist_check(self) -> None:
        while True:
            time.sleep(3)

            # no change
            if self._pricelist_count == self.db.get_pricelist_count():
                continue

            # items added/removed, update prices and listings
            logging.info("Pricelist has changed, updating prices and listings...")
            self._update_pricelist()

    def listen(self) -> None:
        self._pricer = PricesTFWebsocket(self._on_price_update)
        prices_thread = Thread(target=self._pricer.listen, daemon=True)
        prices_thread.start()

        logging.info("Listening to PricesTF")

        self._prices_tf = self._pricer._prices_tf

    def listen_for_pricelist_changes(self) -> None:
        pricelist_thread = Thread(target=self._pricelist_check, daemon=True)
        pricelist_thread.start()
