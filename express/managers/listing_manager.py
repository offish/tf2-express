import asyncio
import logging
from dataclasses import asdict

from backpack_tf import BackpackTF
from tf2_utils import get_metal, get_sku, is_key, is_metal, is_pure, to_scrap

from ..exceptions import ListingDoesNotExist, MissingBackpackTFToken
from ..utils import has_buy_and_sell_price
from .base_manager import BaseManager


class ListingManager(BaseManager):
    def setup(self) -> None:
        backpack_tf_token = self.options.backpack_tf_token

        self.can_list = False
        self._listings = {}
        self._has_updated_listings = True
        self._is_ready = False

        if not backpack_tf_token:
            raise MissingBackpackTFToken

        self._bptf = BackpackTF(
            token=backpack_tf_token,
            steam_id=self.client.steam_id,
            user_agent=self.options.backpack_tf_user_agent,
        )
        self._bptf._library = "tf2-express"

    @staticmethod
    def _get_listing_key(intent: str, sku: str) -> str:
        return f"{intent}_{sku}"

    def _get_listing_variables(self, sku: str, currencies: dict) -> dict:
        keys = currencies["keys"]
        metal = currencies["metal"]
        formatted_sku = sku.replace(";", "_")
        max_stock = self.db.get_max_stock(sku)
        in_stock = self.inventory.get_in_stock(sku)
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
        sell_details = "{price} I have {in_stock} 24/7 FAST "
        sell_details += "Offer (try to take it for free, I'll counter) or chat me. "
        sell_details += "(double-click Ctrl+C): buy_1x_{formatted_sku}"

        return sell_details.format(**variables)

    def _get_buy_listing_details(self, sku: str, currencies: dict) -> str:
        variables = self._get_listing_variables(sku, currencies)
        buy_details = "{price} Stock {in_stock}/{max_stock_string} 24/7 FAST "
        buy_details += "Offer or chat me. "
        buy_details += "(double-click Ctrl+C): sell_1x_{formatted_sku}"

        return buy_details.format(**variables)

    def _get_listing_details(self, sku: str, intent: str, currencies: dict) -> str:
        return (
            self._get_buy_listing_details(sku, currencies)
            if intent == "buy"
            else self._get_sell_listing_details(sku, currencies)
        )

    def _get_asset_id_for_sku(self, sku: str) -> int:
        asset_id = self.inventory.get_last_item_in_our_inventory(sku)["assetid"]
        return int(asset_id)

    def _is_asset_id_in_inventory(self, asset_id: str | int) -> bool:
        if isinstance(asset_id, int):
            asset_id = str(asset_id)

        for item in self.inventory.get_our_inventory():
            if item["assetid"] == asset_id:
                return True

        return False

    def _has_enough_pure(self, keys: int, metal: int) -> bool:
        inventory = self.inventory.get_our_inventory()
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
        scrap_total = keys_amount * key_scrap_price + scrap_amount >= metal

        return scrap_total >= keys * key_scrap_price + to_scrap(metal)

    def _update_listing(self, listing: dict) -> None:
        logging.debug(f"Updating listing {listing=}")

        sku = listing["sku"]
        intent = listing["intent"]
        in_stock = self.inventory.get_stock().get(sku, 0)

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

    def is_listed(self, sku: str, intent: str) -> bool:
        key = self._get_listing_key(intent, sku)
        return key in self._listings

    def create_listing(self, sku: str, intent: str) -> None:
        logging.debug(f"Creating {intent} listing for {sku}")
        
        # Check if listing already exists
        if self.is_listed(sku, intent):
            logging.debug(f"{intent} listing for {sku} already exists")
            return
            
        currencies = self.db.get_item(sku)[intent]
        
        # Debug: Log the exact currency format being passed
        logging.info(f"Currency format for {sku} ({intent}): {currencies}")
        
        # Fix currency format - convert keys to int and remove 0 keys
        if isinstance(currencies, dict):
            fixed_currencies = {}
            
            # Handle metal
            if "metal" in currencies:
                fixed_currencies["metal"] = float(currencies["metal"])
            
            # Handle keys - convert to int and omit if 0
            if "keys" in currencies:
                keys_value = int(currencies["keys"])
                if keys_value > 0:
                    fixed_currencies["keys"] = keys_value
            
            currencies = fixed_currencies
            logging.info(f"Fixed currency format: {currencies}")
        
        # Validate currencies format
        if not isinstance(currencies, dict) or ("keys" not in currencies and "metal" not in currencies):
            logging.error(f"Invalid currencies format for {sku}: {currencies}")
            return
            
        listing_variables = self._get_listing_variables(sku, currencies)
        in_stock = listing_variables["in_stock"]

        if in_stock == 0 and intent == "sell":
            logging.debug(f"Not enough stock for {sku} to create a sell listing")
            return

        if (
            listing_variables["max_stock"] != -1
            and in_stock >= listing_variables["max_stock"]
            and intent == "buy"
        ):
            logging.debug(f"Max stock reached for {sku} to create a buy listing")
            return

        if intent == "buy" and not self._has_enough_pure(
            currencies["keys"], currencies["metal"]
        ):
            logging.debug(f"Not enough pure for {sku} to create a buy listing")
            return

        asset_id = 0

        if intent == "sell":
            try:
                asset_id = self._get_asset_id_for_sku(sku)
                logging.info(f"Asset id for {sku} is {asset_id}")
            except Exception as e:
                logging.error(f"Failed to get asset ID for {sku}: {e}")
                return

        details = self._get_listing_details(sku, intent, currencies)
        
        # Log listing parameters for debugging
        logging.debug(f"Creating listing - SKU: {sku}, Intent: {intent}, Currencies: {currencies}, Asset ID: {asset_id}")
        
        # Create listing using positional arguments as per library specification
        try:
            if asset_id > 0:
                listing = self._bptf.create_listing(sku, intent, currencies, details, asset_id)
            else:
                listing = self._bptf.create_listing(sku, intent, currencies, details)
        except TypeError as e:
            error_msg = str(e)
            if "unexpected keyword argument" in error_msg:
                # Extract the problematic field name
                import re
                field_match = re.search(r"unexpected keyword argument '(\w+)'", error_msg)
                field_name = field_match.group(1) if field_match else "unknown"
                
                logging.error(f"Failed to create listing for {sku}: Library version mismatch")
                logging.error(f"API returned field '{field_name}' not supported by Listing class")
                logging.error(f"This indicates the backpack_tf library needs updating")
                return
            else:
                raise
        except Exception as e:
            logging.error(f"Failed to create listing for {sku}: {e}")
            return
            
        logging.debug(f"Listing created: {asdict(listing)}")

        if listing.id:
            listing_key = self._get_listing_key(intent, sku)
            listing_dict = asdict(listing) | listing_variables
            
            # Store asset_id for deletion purposes
            if asset_id > 0:
                listing_dict["asset_id"] = asset_id
                
            self._listings[listing_key] = listing_dict
            logging.info(f"Listing for {intent}ing {sku} was created")

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
        key = self._get_listing_key(intent, sku)

        if key not in self._listings:
            raise ListingDoesNotExist

        # Use the appropriate deletion method based on listing type
        listing_data = self._listings[key]
        if "asset_id" in listing_data and listing_data["asset_id"] > 0:
            success = self._bptf.delete_listing_by_asset_id(listing_data["asset_id"])
        else:
            success = self._bptf.delete_listing_by_sku(sku)

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
        
        # Remove existing listings first to force recreation with new prices
        try:
            if self.is_listed(sku, "buy"):
                self.remove_listing(sku, "buy")
        except ListingDoesNotExist:
            pass
            
        try:
            if self.is_listed(sku, "sell"):
                self.remove_listing(sku, "sell")
        except ListingDoesNotExist:
            pass
            
        # Create new listings with updated prices
        self.create_listing(sku, "buy")
        self.create_listing(sku, "sell")

    def create_listings(self) -> None:
        logging.info("Creating listings...")
        logging.debug("Creating sell listings...")

        pricelist = self.db.get_pricelist()
        pricelist_skus = [
            item["sku"] for item in pricelist if has_buy_and_sell_price(item)
        ]

        # first list the items we have in our inventory
        for item in self.inventory.get_our_inventory():
            sku = get_sku(item)

            # we dont care about metal
            if is_metal(sku):
                continue

            # item has to be priced
            if sku not in pricelist_skus:
                logging.debug(f"{sku} is not priced")
                continue

            self.create_listing(sku, "sell")

        logging.debug("Created sell listings")
        logging.debug("Creating buy listings...")

        # then list buy orders
        for item in pricelist:
            self.create_listing(item["sku"], "buy")

        logging.info("Listings were created!")

    async def wait_until_ready(self) -> None:
        while not self._is_ready:
            await asyncio.sleep(0.1)

    async def run(self) -> None:
        user_agent = self._bptf.register_user_agent()
        logging.debug(f"User agent: {user_agent}")

        if user_agent.get("status") == "active":
            logging.info("Backpack.TF user agent is now active")
        else:
            logging.error("Could not register Backpack.TF user agent")
            logging.error(user_agent)
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

    def __del__(self):
        self._bptf.delete_all_listings()
        logging.info("Deleted all listings")
        self._listings.clear()
        self._bptf.stop_user_agent()
        logging.info("Stopped Backpack.TF user agent")
