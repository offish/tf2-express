import asyncio
import logging
from dataclasses import asdict

from backpack_tf import BackpackTF, Listing
from tf2_utils import (
    get_metal,
    get_sku,
    is_key,
    is_metal,
    is_pure,
    to_scrap,
)

from ..exceptions import ListingDoesNotExist
from ..listing import (
    ListingConstruct,
    get_listing_key,
    get_matching_listing,
    has_enough_stock,
    surpasses_max_stock,
)
from ..utils import has_buy_and_sell_price, has_correct_price_format
from .base_manager import BaseManager


class ListingManager(BaseManager):
    def setup(self) -> None:
        self.can_list = False
        self._listings = {}
        self._has_updated_listings = True
        self._is_ready = False

        self.backpack_tf = BackpackTF(
            token=self.options.backpack_tf_token,
            steam_id=self.client.steam_id,
            api_key=self.options.backpack_tf_api_key,
            user_agent=self.options.backpack_tf_user_agent,
        )
        self.backpack_tf._library = "tf2-express"

    async def wait_until_ready(self) -> None:
        while not self._is_ready:
            await asyncio.sleep(0.1)

    def set_user_agent(self) -> bool:
        user_agent = self.backpack_tf.register_user_agent()
        logging.debug(f"User agent: {user_agent}")

        if user_agent.get("status") != "active":
            logging.error("Could not register Backpack.TF user agent")
            return False

        logging.info("Backpack.TF user agent is now active")
        return True

    def set_inventory_changed(self) -> None:
        logging.debug("Inventory changed")
        self._has_updated_listings = False

    def set_price_changed(self, sku: str) -> None:
        logging.debug(f"Updating listing for {sku}...")

        for intent in ["buy", "sell"]:
            if self.is_listed(sku, intent):
                self.delete_listing(sku, intent)

            self.create_listing(sku, intent)

    def set_listing(self, listing: Listing, construct: ListingConstruct) -> None:
        listing_key = get_listing_key(construct.intent, construct.sku)
        listing_data = (
            asdict(listing) | construct.listing | construct.listings_variables
        )

        if construct.asset_id > 0:
            listing_data["asset_id"] = construct.asset_id

        logging.debug(f"Setting listing {listing_key=} {listing_data=}")
        self._listings[listing_key] = listing_data

        intent = construct.intent.capitalize()
        logging.info(f"{intent} listing was created for {construct.sku}")

    def is_backpack_tf_banned(self, steam_id: str | int) -> bool:
        return self.options.check_backpack_tf_bans and self.backpack_tf.is_banned(
            steam_id
        )

    def _get_listing_variables(self, sku: str, currencies: dict) -> dict:
        formatted_identifier = sku.replace(";", "_")

        if not self.options.sku_in_listing_details:
            formatted_identifier = self.database.get_normalized_item_name(sku)

        keys = currencies["keys"]
        metal = currencies["metal"]
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
            "formatted_identifier": formatted_identifier,
            "price": price,
            "max_stock_string": max_stock_string,
        }

        logging.debug(f"Listing variables: {variables}")
        return variables

    def get_listing_details(self, sku: str, intent: str, currencies: dict) -> str:
        variables = self._get_listing_variables(sku, currencies)

        return (
            self.options.messages.buy_listing_details.format(**variables)
            if intent == "buy"
            else self.options.messages.sell_listing_details.format(**variables)
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
            self.delete_listing(sku, intent)
            return

        # we dont have the item anymore
        if not has_enough_stock(intent, in_stock):
            self.delete_listing(sku, intent)
            return

        # remove listing if max stock has been reached
        if surpasses_max_stock(intent, in_stock, max_stock):
            self.delete_listing(sku, intent)
            return

        asset_id = listing.get("asset_id", 0)

        if intent == "sell" and not self._is_asset_id_in_inventory(asset_id):
            self.delete_listing(sku, intent)
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

    def get_priced_skus(self) -> list[str]:
        pricelist = self.database.get_pricelist()
        return [item["sku"] for item in pricelist if has_buy_and_sell_price(item)]

    def create_listing_construct(
        self, sku: str, intent: str
    ) -> ListingConstruct | None:
        logging.debug(f"Creating construct for listing {intent=} {sku=}")

        # listing random craft hats and weps not supported yet
        if sku in ["-50;6", "-100;6"]:
            return

        if self.is_listed(sku, intent):
            logging.debug(f"{intent} listing for {sku} already exists")
            return

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
            return

        if surpasses_max_stock(intent, in_stock, max_stock):
            logging.debug(f"Max stock reached for {sku} to create a buy listing")
            return

        if intent == "buy" and not self.has_enough_pure(keys, metal):
            logging.debug(f"Not enough pure for {sku} to create a buy listing")
            return

        asset_id = 0

        if intent == "sell":
            asset_id = self._get_asset_id_for_sku(sku)
            logging.debug(f"Asset ID for {sku} is {asset_id}")

        details = self.get_listing_details(sku, intent, currencies)
        logging.debug(f"creating listing {sku=} {intent=} {currencies=} {asset_id=}")
        logging.debug(f"{details=}")

        return ListingConstruct(
            sku, intent, currencies, details, asset_id, listing_variables
        )

    def create_sell_constructs(self) -> list[ListingConstruct]:
        logging.debug("Collecting data for sell listings...")

        listings = []
        skus = self.get_priced_skus()

        # first list the items we have in our inventory
        for item in self.inventory_manager.get_our_inventory():
            sku = get_sku(item)

            # we dont care about metal
            if is_metal(sku):
                continue

            # item has to be priced
            if sku not in skus:
                logging.debug(f"{sku} does not have both buy and sell price")
                continue

            data = self.create_listing_construct(sku, "sell")

            if data is None:
                continue

            listings.append(data)

        return listings

    def create_buy_constructs(self) -> list[ListingConstruct]:
        logging.debug("Collecting data for buy listings...")

        skus = self.get_priced_skus()
        listings = []

        for sku in skus:
            data = self.create_listing_construct(sku, "buy")

            if data is None:
                continue

            listings.append(data)

        return listings

    def create_listing(self, sku: str, intent: str) -> bool:
        data = self.create_listing_construct(sku, intent)

        if data is None:
            return False

        listing = self.backpack_tf.create_listing(**data.listing)
        logging.debug(f"{asdict(listing)}")

        if listing.id:
            self.set_listing(listing, data)

            logging.info(f"{intent.capitalize()} listing was created for {sku}")
            return True

        return False

    def create_listings(self) -> None:
        logging.info("Creating listings...")

        created_listings = 0
        listings = self.create_sell_constructs() + self.create_buy_constructs()

        listings_created = self.backpack_tf.create_listings(
            [i.listing for i in listings]
        )
        logging.debug(f"{[asdict(i) for i in listings_created]}")

        for construct in listings:
            sku = construct.sku
            intent = construct.intent
            listing = get_matching_listing(construct, listings_created)

            # probably not enough pure, so listing is not active
            if listing is None:
                logging.debug(f"No matching listing found for {intent} {sku}")
                continue

            self.set_listing(listing, construct)
            created_listings += 1

        if not created_listings:
            logging.warning("No listings were created")
        else:
            logging.info(f"Created {created_listings} listings")

        logging.info("Done with creating listings")

    def delete_listing(self, sku: str, intent: str) -> None:
        logging.debug(f"Removing {intent} listing for {sku}")

        if not self.is_listed(sku, intent):
            raise ListingDoesNotExist

        key = get_listing_key(intent, sku)
        listing = self._listings[key]
        asset_id = listing.get("asset_id", 0)
        item_name = listing["item"].get("baseName")
        assert item_name is not None, "Item name is None"

        if asset_id:
            success = self.backpack_tf.delete_listing_by_asset_id(asset_id)
        else:
            success = self.backpack_tf.delete_listing_by_sku(item_name)

        if success is not True:
            logging.error(f"Error when trying to delete {intent} listing for {sku}")
            logging.error(success)
            return

        del self._listings[key]
        logging.info(f"Deleted {intent} listing for {sku}")

    async def run(self) -> None:
        if not self.set_user_agent():
            return

        self.backpack_tf.delete_all_listings()
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
        self.backpack_tf.delete_all_listings()
        logging.info("Deleted all listings")
        self._listings.clear()
        self.backpack_tf.stop_user_agent()
        logging.info("Stopped Backpack.TF user agent")
