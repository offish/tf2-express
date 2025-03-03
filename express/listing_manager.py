import time
from dataclasses import asdict

from backpack_tf import BackpackTF

from .database import Database
from .exceptions import ListingDoesNotExist
from .inventory import ExpressInventory


class ListingManager:
    def __init__(
        self,
        backpack_tf_token: str,
        steam_id: str,
        database: Database,
        inventory: ExpressInventory = None,
    ) -> None:
        self._use_internal_inventory = False

        if inventory is None:
            inventory = ExpressInventory(steam_id)
            self._use_internal_inventory = True

        self._inventory = inventory
        self._db = database
        self._bptf = BackpackTF(
            token=backpack_tf_token,
            steam_id=steam_id,
            user_agent="A tf2-express bot",
        )
        self._listings = {}

    @staticmethod
    def _get_listing_key(intent: str, sku: str) -> str:
        return f"{intent}_{sku}"

    def _get_currencies(self, sku: str, intent: str) -> dict:
        keys, metal = self._db.get_price(sku, intent)
        return {"keys": keys, "metal": metal}

    def _get_listing_variables(self, sku: str, currencies: dict) -> dict:
        keys = currencies["keys"]
        metal = currencies["metal"]
        formatted_sku = sku.replace(";", "_")
        _, max_stock = self._db.get_stock(sku)
        in_stock = self._inventory.get_stock().get(sku, 0)

        if max_stock == -1:
            max_stock = "∞"

        price = f"{metal} ref"

        if keys > 0:
            price = f"{keys} keys {metal} ref"

        return {
            "in_stock": in_stock,
            "max_stock": max_stock,
            "formatted_sku": formatted_sku,
            "price": price,
        }

    def _get_buy_listing_details(self, sku: str, currencies: dict) -> str:
        variables = self._get_listing_variables(sku, currencies)
        del variables["max_stock"]

        buy_details = "{price} ⚡️ I have {in_stock} ⚡️ 24/7 FAST ⚡️ "
        buy_details += "Offer (try to take it for free, I'll counter) or chat me. "
        buy_details += "(double-click Ctrl+C): buy_1x_{formatted_sku}"
        return buy_details.format(**variables)

    def _get_sell_listing_details(self, sku: str, currencies: dict) -> str:
        variables = self._get_listing_variables(sku, currencies)

        sell_details = "{price} ⚡️ Stock {in_stock}/{max_stock} ⚡️ 24/7 FAST ⚡️ "
        sell_details += "Offer or chat me. "
        sell_details += "(double-click Ctrl+C): sell_1x_{formatted_sku}"
        return sell_details.format(**variables)

    def _get_listing_details(self, sku: str, intent: str, currencies: dict) -> str:
        return (
            self._get_buy_listing_details(sku, currencies)
            if intent == "buy"
            else self._get_sell_listing_details(sku, currencies)
        )

    def create_listing(self, sku: str, intent: str) -> None:
        currencies = self._get_currencies(sku, intent)
        listing_variables = self._get_listing_variables(sku, currencies)

        in_stock = listing_variables["in_stock"]

        if in_stock == 0 and intent == "sell":
            return

        if (
            listing_variables["max_stock"] != -1
            and in_stock >= listing_variables["max_stock"]
        ):
            return

        details = self._get_listing_details(sku, intent, currencies)
        listing = self._bptf.create_listing(
            sku=sku, intent=intent, currencies=currencies, details=details
        )

        if listing.id > 0:
            listing_key = self._get_listing_key(intent, sku)
            self._listings[listing_key] = asdict(listing) | listing_variables

    def remove_listing(self, sku: str, intent: str) -> None:
        key = self._get_listing_key(intent, sku)

        if key not in self._listings:
            raise ListingDoesNotExist

        success = self._bptf.delete_listing(self._listings[key].id)

        if success:
            del self._listings[key]

    def set_inventory_changed(self) -> None:
        self._has_updated_listings = False

        if self._use_internal_inventory:
            self._inventory.fetch_our_inventory()

    def set_price_changed(self, sku: str) -> None:
        self.create_listing(sku, "buy")
        self.create_listing(sku, "sell")

    def _update_listing(self, listing: dict) -> None:
        sku = listing["sku"]
        intent = listing["intent"]
        in_stock = self._inventory.get_stock().get(sku, 0)

        # nothing to update
        if in_stock == listing["in_stock"]:
            return

        if intent == "sell" and in_stock == 0:
            self.remove_listing(sku, intent)
            return

        # cannot buy more than max stock
        if (
            intent == "buy"
            and listing["max_stock"] != -1
            and in_stock >= listing["max_stock"]
        ):
            self.remove_listing(sku, intent)
            return

        # stock was changed
        self.create_listing(sku, intent)

    def run(self) -> None:
        self._bptf.register_user_agent()

        while True:
            # TODO: bump listings

            if self._has_updated_listings:
                time.sleep(0.1)
                continue

            for i in self._listings:
                listing = self._listings[i]
                self._update_listing(listing)

            self._has_updated_listings = True

    def __del__(self):
        self._bptf.stop_user_agent()
