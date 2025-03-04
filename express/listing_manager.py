import logging
import time
from dataclasses import asdict

from backpack_tf import BackpackTF
from tf2_utils import get_metal, get_sku, is_pure, to_scrap

from .database import Database
from .exceptions import ListingDoesNotExist, MissingBackpackTFToken
from .inventory import ExpressInventory


def is_key(sku: str) -> bool:
    return sku == "5021;6"


class ListingManager:
    def __init__(
        self,
        backpack_tf_token: str,
        steam_id: str,
        database: Database,
        inventory: ExpressInventory,
    ) -> None:
        self._inventory = inventory
        self._db = database

        if not backpack_tf_token:
            raise MissingBackpackTFToken

        self._bptf = BackpackTF(
            token=backpack_tf_token,
            steam_id=steam_id,
            user_agent="A tf2-express bot",
        )
        self._listings = {}
        self._has_updated_listings = False

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

    def _get_asset_id_for_sku(self, sku: str) -> int:
        asset_id = self._inventory.get_last_item_in_our_inventory(sku)["assetid"]
        return int(asset_id)

    def _is_asset_id_in_inventory(self, asset_id: str | int) -> bool:
        if isinstance(asset_id, int):
            asset_id = str(asset_id)

        for item in self._inventory.get_our_inventory():
            if item["assetid"] == asset_id:
                return True

        return False

    def _has_enough_pure(self, keys: int, metal: int) -> bool:
        inventory = self._inventory.get_our_inventory()
        keys_amount = 0
        scrap_amount = 0

        for i in inventory:
            sku = get_sku(i)

            if is_key(sku):
                keys_amount += 1
                continue

            if is_pure(sku):
                scrap_amount += get_metal(sku)
                continue

        _, metal_price = self._db.get_price("5021;6", "buy")
        key_scrap_price = to_scrap(metal_price)
        scrap_total = keys_amount * key_scrap_price + scrap_amount >= metal

        return scrap_total >= keys * key_scrap_price + to_scrap(metal)

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

        if intent == "buy" and not self._has_enough_pure(
            currencies["keys"], currencies["metal"]
        ):
            return

        asset_id = 0

        if intent == "sell":
            asset_id = self._get_asset_id_for_sku(sku)

        details = self._get_listing_details(sku, intent, currencies)
        listing = self._bptf.create_listing(
            sku=sku,
            intent=intent,
            currencies=currencies,
            details=details,
            asset_id=asset_id,
        )

        if listing.id > 0:
            listing_key = self._get_listing_key(intent, sku)
            self._listings[listing_key] = asdict(listing) | listing_variables

    def remove_listing(self, sku: str, intent: str) -> None:
        key = self._get_listing_key(intent, sku)

        if key not in self._listings:
            raise ListingDoesNotExist

        success = self._bptf.delete_listing(self._listings[key].id)

        if success is not True:
            logging.error(f"Error when trying to delete {intent} listing for {sku}")
            logging.error(success)
            return

        del self._listings[key]
        logging.info(f"Deleted {intent} listing for {sku}")

    def set_inventory_changed(self) -> None:
        self._has_updated_listings = False

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

        # not enough pure anymore
        if intent == "buy" and not self._has_enough_pure(
            listing["keys"], listing["metal"]
        ):
            self.remove_listing(sku, intent)
            return

        # we dont have the item anymore
        if intent == "sell" and in_stock == 0:
            self.remove_listing(sku, intent)
            return

        # remove listing if max stock has been reached
        if (
            intent == "buy"
            and listing["max_stock"] != -1
            and in_stock >= listing["max_stock"]
        ):
            self.remove_listing(sku, intent)
            return

        if intent == "sell":
            asset_id = listing["asset_id"]

            # asset id used for sell listing was traded away
            if not self._is_asset_id_in_inventory(asset_id):
                self.remove_listing(sku, intent)
                self.create_listing(sku, intent)
                return

        # stock was most likely changed
        self.create_listing(sku, intent)

    def run(self) -> None:
        user_agent = self._bptf.register_user_agent()

        if user_agent["status"] == "active":
            logging.info("Backpack.TF user agent is now active")
        else:
            logging.error("Could not register Backpack.TF user agent")
            logging.error(user_agent)
            return

        self._bptf.delete_all_listings()
        logging.info("Deleted all listings")

        while True:
            # TODO: bump listings
            # TODO: create flow for creating multiple listings at once

            if self._has_updated_listings:
                time.sleep(0.1)
                continue

            logging.info("Updating our listings...")

            for i in self._listings:
                listing = self._listings[i]
                self._update_listing(listing)

            logging.info("All listings were updated!")

            self._has_updated_listings = True

    def __del__(self):
        self._bptf.delete_all_listings()
        self._listings.clear()
        self._bptf.stop_user_agent()
