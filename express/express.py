from .inventory import get_inventory_stock
from .database import Database
from .options import Options
from .offer import valuate, OfferData

from dataclasses import asdict
from json import dumps
import logging
import time

from steampy.exceptions import InvalidCredentials
from steampy.client import SteamClient
from tf2_utils import (
    Offer,
    Inventory,
    PricesTF,
    to_refined,
    refinedify,
    account_id_to_steam_id,
)


class Express:
    def __init__(self, bot: dict, options: Options) -> None:
        self.name = bot["name"]
        self.username = bot["username"]
        self.password = bot["password"]
        self.secrets = bot["secrets"]
        self.steam_id = self.secrets["steamid"]
        self.client = SteamClient(bot["api_key"])
        self.db = Database(options.database)
        self.pricer = PricesTF()
        self.inventory = Inventory("steamcommunity")  # use apikey?

        self.stock = {}
        self.processed: list[OfferData] = []
        self.last_offer_fetch = 0
        self.options = options

        self.is_enabled = True
        self.active_offers = 0
        self.processed_offers = 0
        self.accepted_offers = 0

        self.prices_to_check = []

        self.last_logged_offer = ""

    def login(self) -> None:
        logging.debug("Trying to login to Steam")

        try:
            self.client.login(self.username, self.password, dumps(self.secrets))

            if not self.client.was_login_executed:
                logging.critical("Login was not executed")
                return

            logging.info(f"Logged into Steam as {self.username}")

        except InvalidCredentials as e:
            logging.error(e)

    def logout(self) -> None:
        logging.info("Logging out...")
        self.client.logout()

    def append_new_price(self, data: dict) -> None:
        self.prices_to_check.append(data)

    def __log_trade(
        self, message: str, offer_id: str = "", level: str = "INFO"
    ) -> None:
        if offer_id and offer_id != self.last_logged_offer:
            self.last_logged_offer = offer_id

        if not offer_id:
            offer_id = self.last_logged_offer

        numeric_level = logging.getLevelName(level)
        logging.log(numeric_level, f"({offer_id}) {message}")

    def __update_prices(self) -> None:
        skus = self.db.get_autopriced()

        for price in self.prices_to_check.copy():
            self.prices_to_check.remove(price)

            if price["sku"] not in skus:
                logging.debug(f"SKU: {price['sku']} does not exist in our pricelist")
                continue

            self.db.update_autoprice(price)

    def __get_offers(self) -> list[dict]:
        logging.info("Fetching offers...")
        self.last_offer_fetch = time.time()

        try:
            return self.client.get_trade_offers(merge=True)["response"][
                "trade_offers_received"
            ]
        except Exception as e:
            logging.error(f"{e}")
            return [{}]

    def __get_offer(self, offer_id: str) -> dict:
        response = self.client.get_trade_offer(offer_id, merge=True).get("response", {})
        trade_offer = response.get("offer", {})

        if not trade_offer:
            self.__log_trade(
                "Did not get wanted response when getting offer", offer_id, "ERROR"
            )
            return {}

        return trade_offer

    def __get_receipt(self, trade_id: str) -> list:
        return self.client.get_trade_receipt(trade_id)

    def __accept(self, offer_id: str) -> None:
        self.__log_trade("Trying to accept offer", offer_id)

        try:
            self.client.accept_trade_offer(offer_id)
        except Exception as e:
            self.__log_trade(f"Error when confirming offer {e}", level="ERROR")

    def __decline(self, offer_id: str) -> None:
        self.__log_trade("Trying to decline offer", offer_id)
        self.client.decline_trade_offer(offer_id)

    def __process_offer(self, offer: dict) -> None:
        offer_id = offer.get("tradeofferid", "")

        if not offer_id:
            return

        for offer_data in self.processed:
            if offer_id != offer_data.offer_id:
                continue

            logging.debug(f"({offer_id}) has already been processed")
            return

        self.__log_trade("Processing offer", offer_id)

        # we assume we wont crash, add to processed now
        # so if we return early, we wont process again
        offer_data = OfferData(offer_id)
        self.processed.append(offer_data)
        logging.debug(f"Added offer {offer_id} to processed list")

        self.active_offers += 1
        self.processed_offers += 1

        trade = Offer(offer)

        if not trade.is_active():
            self.__log_trade("Offer is not active")
            return

        if trade.is_our_offer():
            self.__log_trade("Offer is ours, skipping")
            return

        partner_steam_id = trade.get_partner()
        self.__log_trade(f"Received a new offer from {partner_steam_id}")

        their_items = offer["items_to_receive"]
        our_items = offer["items_to_give"]

        # add offer data
        offer_data.message = offer["message"]
        offer_data.steam_id_other = account_id_to_steam_id(offer["accountid_other"])
        offer_data.time_created = offer["time_created"]
        offer_data.time_updated = offer["time_updated"]
        offer_data.their_items = their_items
        offer_data.our_items = our_items

        # is owner
        if partner_steam_id in self.options.owners:
            self.__log_trade("Offer is from owner")
            self.__accept(offer_id)

        # nothing on our side
        elif trade.is_gift() and self.options.accept_donations:
            self.__log_trade("User is trying to give items")
            self.__accept(offer_id)

        # only items on our side
        elif trade.is_scam() and self.options.decline_scam_offers:
            self.__log_trade("User is trying to take items")
            self.__decline(offer_id)

        # trade hold/escrow
        elif trade.has_trade_hold() and self.options.decline_trade_hold:
            self.__log_trade("User has trade hold")
            self.__decline(offer_id)

        # two sided offer -> valuate
        elif trade.is_two_sided():
            self.__log_trade("Offer is valid, calculating...")

            # all skus in our database
            all_skus = self.db.get_skus()

            # get mann co key buy and sell price
            key_prices = self.db.get_item("5021;6")

            # TODO: handle if in_stock + new items would
            # surpass max_stock. -100;6 is edge case
            # max_stock = -1 is unlimited

            # we dont care about unpriced items on their side
            their_value, _ = valuate(
                self.db, their_items, "buy", all_skus, key_prices, self.options
            )
            our_value, has_unpriced = valuate(
                self.db, our_items, "sell", all_skus, key_prices, self.options
            )
            # all prices are in scrap

            item_amount = len(their_items) + len(our_items)
            self.__log_trade(f"Offer contains {item_amount} items")

            difference = to_refined(their_value - our_value)

            their_value = to_refined(their_value)
            our_value = to_refined(our_value)

            summary = (
                "Their value: {} ref, our value: {} ref, difference: {} ref".format(
                    their_value,
                    our_value,
                    refinedify(difference),
                )
            )

            offer_data.their_value = their_value
            offer_data.our_value = our_value
            offer_data.has_unpriced = has_unpriced

            self.__log_trade(summary)

            if has_unpriced:
                self.__log_trade(
                    "Offer contains unpriced items on our side, ignoring offer"
                )

            elif their_value >= our_value:
                self.__accept(offer_id)

            # their_value < our_value
            elif self.options.decline_bad_offers:
                self.__decline(offer_id)

            else:
                self.__log_trade("Ignoring offer as automatic decline is disabled")

        else:
            self.__log_trade("Offer is invalid, ignoring...")

    def __process_offers(self) -> None:
        offers = self.__get_offers()
        amount = len(offers)

        if not amount:
            logging.info("No new offers available")
            return

        # logging.info(f"Processing {amount} offers")

        for offer in offers:
            self.__process_offer(offer)

    def __update_offer_states(self) -> None:
        if self.active_offers:
            logging.info(f"{self.active_offers} offer(s) are still active")

        for offer_data in self.processed.copy():
            offer = self.__get_offer(offer_data.offer_id)
            trade = Offer(offer)

            offer_data.state = trade.get_state()

            if trade.is_active():
                continue

            self.active_offers -= 1

            self.__log_trade(
                f"Offer state changed to {trade.get_state()}", offer_data.offer_id
            )

            if trade.is_accepted():
                self.accepted_offers += 1

                # TODO: increment in_stock, -100;6 edge case

                if self.options.save_trades:
                    logging.info("Saving offer data...")

                    if offer.get("tradeid") and self.options.save_receipt:
                        offer_data.receipt = self.__get_receipt(offer["tradeid"])

                    self.db.insert_trade(asdict(offer_data))
                    logging.info("Offer was added to the database")

            self.processed.remove(offer_data)

    def __append_autopriced_items(self) -> None:
        autopriced_items = self.db.get_autopriced()

        self.pricer.request_access_token()

        for sku in autopriced_items:
            # get price
            price = self.pricer.get_price(sku)
            self.prices_to_check.append(price)
            time.sleep(2)

    def run(self) -> None:
        logging.info(f"Fetching offers every {self.options.poll_interval} seconds")

        if self.options.fetch_prices_on_startup:
            self.__append_autopriced_items()
            self.__update_prices()

        inventory = self.inventory.fetch(self.steam_id)
        self.stock = get_inventory_stock(inventory)

        self.db.update_stocks(self.stock)

        del inventory

        while True:
            # bot is disabled
            if not self.is_enabled:
                time.sleep(1)
                continue

            # we want to wait for TIMEOUT seconds before fetching again
            if self.last_offer_fetch + self.options.poll_interval > time.time():
                # sleep 100 ms to limit cpu usage
                time.sleep(0.1)
                continue

            self.__update_prices()

            logging.debug(f"Currently in processed: {self.processed}")
            self.__process_offers()
            self.__update_offer_states()
