import asyncio
import logging
from dataclasses import asdict

from backpack_tf import BackpackTF
from tf2_utils import get_metal, get_sku, is_key, is_metal, is_pure, to_scrap

from ..exceptions import ListingDoesNotExist
from ..utils import has_buy_and_sell_price, has_correct_price_format
from .base_manager import BaseManager


def get_listing_key(intent: str, sku: str) -> str:
    return f"{intent}_{sku}"


def has_enough_stock(intent: str, in_stock: int) -> bool:
    if intent == "sell":
        return in_stock > 0

    return True


def surpasses_max_stock(intent: str, in_stock: int, max_stock: int) -> bool:
    if intent == "sell":
        return False

    return max_stock != -1 and in_stock >= max_stock


class ListingManager(BaseManager):
    def setup(self) -> None:
        self.can_list = False
        self._listings = {}
        self._has_updated_listings = True
        self._is_ready = False

        self._bptf = BackpackTF(
            token=self.options.backpack_tf_token,
            steam_id=self.client.steam_id,
            api_key=self.options.backpack_tf_api_key,
            user_agent=self.options.backpack_tf_user_agent,
        )
        self._bptf._library = "tf2-express"

    async def wait_until_ready(self) -> None:
        while not self._is_ready:
            await asyncio.sleep(0.1)

    def set_user_agent(self) -> bool:
        user_agent = self._bptf.register_user_agent()
        logging.debug(f"User agent: {user_agent}")

        if user_agent.get("status") != "active":
            logging.error("Could not register Backpack.TF user agent")
            return False

        logging.info("Backpack.TF user agent is now active")
        return True

    def is_banned(self, steam_id: str | int) -> bool:
        if isinstance(steam_id, int):
            steam_id = str(steam_id)

        res = self._bptf._request(
            "GET",
            "/users/info/v1",
            params={"steamids": steam_id, "key": self.options.backpack_tf_api_key},
        )
        logging.debug(f"User info: {res}")

        user = res["users"][steam_id]
        bans = user.get("bans", None)

        return bans is not None

    def _get_listing_variables(self, sku: str, currencies: dict) -> dict:
        keys = currencies["keys"]
        metal = currencies["metal"]
        formatted_sku = sku.replace(";", "_")
        max_stock = self.database.get_max_stock(sku)
        in_stock = self.inventory_manager.get_in_stock(sku)
        max_stock_string = str(max_stock)

        if max_stock == -1:
            max_stock_string = "∞"

        price = f"{metal} ref"

        if keys > 0:
            price = f"{keys} keys {metal} ref"

        variables = {
            "sku": sku,
            "in_stock": in_stock,
            "max_stock": max_stock,
            "formatted_sku": formatted_sku,
            "price": price,
            "max_stock_string": max_stock_string,
        }

        logging.debug(f"Listing variables: {variables}")
        return variables

    def _get_sell_listing_details(self, sku: str, currencies: dict) -> str:
        variables = self._get_listing_variables(sku, currencies)
        sell_details = "{price} ⚡️ I have {in_stock} ⚡️ 24/7 FAST ⚡️ "
        sell_details += "Offer (try to take it for free, I'll counter) or chat me. "
        sell_details += "(double-click Ctrl+C): buy_{formatted_sku}"

        return sell_details.format(**variables)

    def _get_buy_listing_details(self, sku: str, currencies: dict) -> str:
        variables = self._get_listing_variables(sku, currencies)
        buy_details = "{price} ⚡️ Stock {in_stock}/{max_stock_string} ⚡️ 24/7 FAST ⚡️ "
        buy_details += "Offer or chat me. "
        buy_details += "(double-click Ctrl+C): sell_{formatted_sku}"

        return buy_details.format(**variables)

    def _get_listing_details(self, sku: str, intent: str, currencies: dict) -> str:
        return (
            self._get_buy_listing_details(sku, currencies)
            if intent == "buy"
            else self._get_sell_listing_details(sku, currencies)
        )

    def _get_asset_id_for_sku(self, sku: str) -> int:
        asset_id = self.inventory_manager.get_last_item_in_our_inventory(sku)["assetid"]
        return int(asset_id)

    def _is_asset_id_in_inventory(self, asset_id: str | int) -> bool:
        if isinstance(asset_id, int):
            asset_id = str(asset_id)

        for item in self.inventory_manager.get_our_inventory():
            if item["assetid"] == asset_id:
                return True

        return False

    def _update_listing(self, listing: dict) -> None:
        logging.debug(f"Updating listing {listing=}")

        sku = listing["sku"]
        intent = listing["intent"]
        stock = self.inventory_manager.get_stock()
        in_stock = stock.get(sku, 0)
        max_stock = listing["max_stock"]

        # nothing to update
        if in_stock == listing["in_stock"]:
            return

        keys = int(listing.get("keys", 0))
        metal = float(listing.get("metal", 0.0))

        # not enough pure anymore
        if intent == "buy" and not self.has_enough_pure(keys, metal):
            self.remove_listing(sku, intent)
            return

        # we dont have the item anymore
        if not has_enough_stock(intent, in_stock):
            self.remove_listing(sku, intent)
            return

        # remove listing if max stock has been reached
        if surpasses_max_stock(intent, in_stock, max_stock):
            self.remove_listing(sku, intent)
            return

        asset_id = listing.get("asset_id", 0)

        if intent == "sell" and not self._is_asset_id_in_inventory(asset_id):
            self.remove_listing(sku, intent)
            self.create_listing(sku, intent)
            return

        # stock was most likely changed
        self.create_listing(sku, intent)

    def is_listed(self, sku: str, intent: str) -> bool:
        key = get_listing_key(intent, sku)
        return key in self._listings

    def has_enough_pure(self, keys: int, metal: float) -> bool:
        inventory = self.inventory_manager.get_our_inventory()
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

        key_scrap_price = self.client.pricing_manager.get_key_scrap_price("buy")
        scrap_total = keys_amount * key_scrap_price + scrap_amount

        return scrap_total >= keys * key_scrap_price + to_scrap(metal)

    def create_listing(self, sku: str, intent: str) -> bool:
        logging.debug(f"Creating {intent} listing for {sku}")

        # listing random craft hats and weps not supported yet
        if sku in ["-50;6", "-100;6"]:
            return False

        if self.is_listed(sku, intent):
            logging.debug(f"{intent} listing for {sku} already exists")
            return False

        item = self.database.get_item(sku)
        assert has_correct_price_format(item), f"Item has wrong price format: {item}"

        currencies = item[intent]
        keys = int(currencies.get("keys", 0))
        metal = float(currencies.get("metal", 0.0))
        currencies = {
            "keys": keys,
            "metal": metal,
        }

        listing_variables = self._get_listing_variables(sku, currencies)
        in_stock = listing_variables["in_stock"]
        max_stock = listing_variables["max_stock"]

        if not has_enough_stock(intent, in_stock):
            logging.debug(f"Not enough stock for {sku} to create a sell listing")
            return False

        if surpasses_max_stock(intent, in_stock, max_stock):
            logging.debug(f"Max stock reached for {sku} to create a buy listing")
            return False

        if intent == "buy" and not self.has_enough_pure(keys, metal):
            logging.debug(f"Not enough pure for {sku} to create a buy listing")
            return False

        asset_id = 0

        if intent == "sell":
            asset_id = self._get_asset_id_for_sku(sku)
            logging.info(f"Asset ID for {sku} is {asset_id}")

        details = self._get_listing_details(sku, intent, currencies)
        logging.debug(f"creating listing {sku=} {intent=} {currencies=} {asset_id=}")
        logging.debug(f"{details=}")

        listing = self._bptf.create_listing(sku, intent, currencies, details, asset_id)
        logging.debug(f"{asdict(listing)}")

        if listing.id:
            listing_key = get_listing_key(intent, sku)
            listing_dict = asdict(listing) | listing_variables

            if asset_id > 0:
                listing_dict["asset_id"] = asset_id

            self._listings[listing_key] = listing_dict
            logging.info(f"{intent.capitalize()} listing was created for {sku}")
            return True

        return False

    def delete_inactive_listings(self, current_skus: list[str]) -> None:
        logging.debug("Deleting inactive listings...")

        for i in self._listings:
            intent, sku = i.split("_")

            if sku in current_skus:
                continue

            logging.debug(f"Deleting inactive {intent} listing for {sku}")
            self.remove_listing(sku, intent)

    def remove_listing(self, sku: str, intent: str) -> None:
        logging.debug(f"Removing {intent} listing for {sku}")
        key = get_listing_key(intent, sku)

        if key not in self._listings:
            raise ListingDoesNotExist

        asset_id = self._listings[key].get("asset_id", 0)
        item_name = self._listings[key]["item"].get("baseName")
        assert item_name is not None, "Item name is None"

        if asset_id:
            success = self._bptf.delete_listing_by_asset_id(asset_id)
        else:
            success = self._bptf.delete_listing_by_sku(item_name)

        if success is not True:
            logging.error(f"Error when trying to delete {intent} listing for {sku}")
            logging.error(success)
            return

        del self._listings[key]
        logging.info(f"Deleted {intent} listing for {sku}")

    def set_inventory_changed(self) -> None:
        logging.debug("Inventory changed")
        self._has_updated_listings = False

    def set_price_changed(self, sku: str) -> None:
        logging.debug(f"Updating listing for {sku}...")

        for intent in ["buy", "sell"]:
            if self.is_listed(sku, intent):
                self.remove_listing(sku, intent)

            self.create_listing(sku, intent)

    def get_filtered_pricelist(self) -> list[dict]:
        pricelist = self.database.get_pricelist()
        return [item for item in pricelist if has_buy_and_sell_price(item)]

    def create_sell_listings(self) -> None:
        logging.debug("Creating sell listings...")

        listings_created = 0
        priced_skus = [item["sku"] for item in self.get_filtered_pricelist()]

        # first list the items we have in our inventory
        for item in self.inventory_manager.get_our_inventory():
            sku = get_sku(item)

            # we dont care about metal
            if is_metal(sku):
                continue

            # item has to be priced
            if sku not in priced_skus:
                logging.debug(f"{sku} does not have both buy and sell price")
                continue

            created = self.create_listing(sku, "sell")

            if created:
                listings_created += 1

        if not listings_created:
            logging.warning("No sell listings were created")
        else:
            logging.info(f"Created {listings_created} sell listings")

    def create_buy_listings(self) -> None:
        logging.debug("Creating buy listings...")

        listings_created = 0
        pricelist = self.get_filtered_pricelist()

        for item in pricelist:
            created = self.create_listing(item["sku"], "buy")

            if created:
                listings_created += 1

        if not listings_created:
            logging.warning("No buy listings were created")
        else:
            logging.info(f"Created {listings_created} buy listings")

    def create_listings(self) -> None:
        logging.info("Creating listings...")
        self.create_sell_listings()
        self.create_buy_listings()
        logging.info("Done with creating listings")

    async def run(self) -> None:
        if not self.set_user_agent():
            return

        self._bptf.delete_all_listings()
        self._is_ready = True
        logging.info("Deleted all listings")

        while True:
            if self._has_updated_listings or not self._listings:
                await asyncio.sleep(1)
                continue

            logging.info("Updating our listings...")

            for i in self._listings:
                listing = self._listings[i]
                self._update_listing(listing)

            logging.info("All listings were updated!")

            self._has_updated_listings = True

    def close(self):
        self._bptf.delete_all_listings()
        logging.info("Deleted all listings")
        self._listings.clear()
        self._bptf.stop_user_agent()
        logging.info("Stopped Backpack.TF user agent")
