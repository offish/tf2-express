from .database import Database
from .options import Options
from .offer import valuate

from json import dumps
import logging
import time

from steampy.exceptions import InvalidCredentials
from steampy.client import SteamClient
from tf2_utils import Offer, to_refined, refinedify


class Express:
    def __init__(self, bot: dict, options: Options) -> None:
        self.name = bot["name"]
        self.username = bot["username"]
        self.password = bot["password"]
        self.secrets = bot["secrets"]
        self.steam_id = self.secrets["steamid"]
        self.client = SteamClient(bot["api_key"])
        self.db = Database(options.database)

        self.values = {}
        self.processed = []
        self.last_offer_fetch = 0
        self.options = options

        self.is_enabled = True
        # TODO: add processed_offers, accepted_offers, active_offers for status

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
            logging.error(f"Did not get wanted response when getting offers: {e}")
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
        offer_id = offer["tradeofferid"]

        self.__log_trade("Processing offer", offer_id)

        if offer_id in self.processed:
            logging.debug(f"{offer_id} has already been processed")
            return

        # we assume we wont crash, add to processed now
        # so if we return early, we wont process again
        self.processed.append(offer_id)
        logging.debug(f"Added offer {offer_id} to processed list")

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

        self.values[offer_id] = {
            "their_items": their_items,
            "our_items": our_items,
        }

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
                "User value: {} ref, our value: {} ref, difference: {} ref".format(
                    their_value,
                    our_value,
                    refinedify(difference),
                )
            )

            self.values[offer_id]["our_value"] = our_value
            self.values[offer_id]["their_value"] = their_value

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
        logging.info(f"Processing {len(offers)} offers")
        logging.info(
            "{} offer with values {} processed".format(
                len(self.values), len(self.processed)
            )
        )

        for offer in offers:
            self.__process_offer(offer)

    def __update_offer_states(self) -> None:
        for offer_id in self.processed:
            offer = self.__get_offer(offer_id)
            trade = Offer(offer)

            if trade.is_active():
                self.__log_trade(f"Offer is still active", offer_id)
                continue

            if not trade.is_active():
                self.__log_trade(
                    f"Offer state changed to {trade.get_state()}", offer_id
                )
                # we have processed the offer if its not active anymore
                self.processed.remove(offer_id)

            if trade.is_accepted():
                if self.options.save_trades:
                    logging.info("Saving offer data...")

                    if offer_id in self.values:
                        offer["their_items"] = self.values[offer_id]["their_items"]
                        offer["our_items"] = self.values[offer_id]["our_items"]
                        offer["our_value"] = self.values[offer_id].get("our_value", 0.0)
                        offer["their_value"] = self.values[offer_id].get(
                            "their_value", 0.0
                        )

                    if offer.get("tradeid") and self.options.save_receipt:
                        offer["receipt"] = self.__get_receipt(offer["tradeid"])

                    self.db.insert_trade(offer)
                    logging.info("Offer was added to the database")

            if offer_id in self.values:
                self.values.pop(offer_id)

    def run(self) -> None:
        logging.info(f"Fetching offers every {self.options.poll_interval} seconds")

        # TODO: update prices on startup

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

            try:
                logging.debug(f"Currently in processed: {self.processed}")
                self.__process_offers()
                self.__update_offer_states()
            except Exception as e:
                logging.error(e)
