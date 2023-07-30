from json import dumps
import time

from .database import add_trade, get_items
from .settings import *
from .logging import Log, f
from .prices import update_pricelist
from .config import TIMEOUT
from .utils import to_refined, refinedify
from .offer import Offer, valuate

from steampy.client import SteamClient
from steampy.exceptions import InvalidCredentials


class Express:
    def __init__(self, bot: dict) -> None:
        self.name = bot["name"]
        self.log = Log(self.name)
        self.username = bot["username"]
        self.password = bot["password"]
        self.secrets = bot["secrets"]
        self.client = SteamClient(bot["api_key"])
        self.values = {}
        self.processed = []
        self.last_offer_fetch = 0

    def login(self) -> None:
        try:
            self.client.login(self.username, self.password, dumps(self.secrets))

            if self.client.was_login_executed:
                self.log.info(f"Logged into Steam as {f.GREEN + self.username}")
            else:
                self.log.error("Login was not executed")

        except InvalidCredentials as e:
            self.log.error(e)

    def logout(self) -> None:
        self.log.info("Logging out...")
        self.client.logout()

    def get_offers(self) -> dict:
        self.log.info("Fetching offers...")
        self.last_offer_fetch = time.time()
        try:
            response = self.client.get_trade_offers(merge=True).get("response")

            return response["trade_offers_received"]
        except:
            return {}

    def get_offer(self, offer_id: str) -> dict:
        response = self.client.get_trade_offer(offer_id, merge=True).get("response")

        if response and "offer" in response:
            return response["offer"]
        return {}

    def get_receipt(self, trade_id: str) -> dict:
        return self.client.get_trade_receipt(trade_id)

    def accept(self, offer_id: str) -> None:
        self.log.trade("Trying to accept offer", offer_id)

        try:
            self.client.accept_trade_offer(offer_id)
        except Exception as e:
            self.log.error(f"Error when confirming offer {e}")

    def decline(self, offer_id: str) -> None:
        self.log.trade("Trying to decline offer", offer_id)
        self.client.decline_trade_offer(offer_id)

    def _process_offer(self, offer: dict) -> None:
        offer_id = offer["tradeofferid"]

        if not offer_id in self.processed:
            log = Log(self.name, offer_id)

            trade = Offer(offer)
            steam_id = trade.get_partner()

            if trade.is_active() and not trade.is_our_offer():
                log.trade(f"Received a new offer from {f.YELLOW + steam_id}")

                if trade.is_from_owner():
                    log.trade("Offer is from owner")
                    self.accept(offer_id)

                elif trade.is_gift() and ACCEPT_DONATIONS:
                    log.trade("User is trying to give items")
                    self.accept(offer_id)

                elif trade.is_scam() and DECLINE_SCAM_OFFERS:
                    log.trade("User is trying to take items")
                    self.decline(offer_id)

                elif trade.is_valid():
                    log.trade("Processing offer...")

                    their_items = offer["items_to_receive"]
                    our_items = offer["items_to_give"]

                    # all item names in our database
                    all_item_names = get_items()

                    # we dont care about unpriced items on their side
                    their_value, _ = valuate(their_items, "buy", all_item_names)
                    our_value, has_unpriced = valuate(our_items, "sell", all_item_names)

                    item_amount = len(their_items) + len(our_items)
                    log.trade(f"Offer contains {item_amount} items")

                    difference = to_refined(their_value - our_value)
                    summary = (
                        "User value: {} ref, our value: {} ref, difference: {} ref"
                    )

                    log.trade(
                        summary.format(
                            to_refined(their_value),
                            to_refined(our_value),
                            refinedify(difference),
                        )
                    )

                    if has_unpriced:
                        log.trade("Offer contains unpriced items on our side")

                    if not has_unpriced and their_value >= our_value:
                        self.values[offer_id] = {
                            "our_value": to_refined(our_value),
                            "their_value": to_refined(their_value),
                        }
                        self.accept(offer_id)

                    else:
                        if DECLINE_BAD_TRADE:
                            self.decline(offer_id)
                        else:
                            log.trade("Ignoring offer as automatic decline is disabled")

                else:
                    log.trade("Offer is invalid")

            else:
                log.trade("Offer is not active")

            self.processed.append(offer_id)

    def _process_offers(self) -> None:
        for offer in self.get_offers():
            self._process_offer(offer)

    def _update_offer_states(self) -> None:
        for offer_id in self.processed:
            offer = self.get_offer(offer_id)
            trade = Offer(offer)

            log = Log(self.name, offer_id)

            if not trade.is_active():
                log.trade(f"Offer state changed to {f.YELLOW + trade.get_state()}")

                if trade.is_accepted() and "tradeid" in offer:
                    if SAVE_TRADES:
                        self.log.info("Saving offer data...")

                        if offer_id in self.values:
                            offer["our_value"] = self.values[offer_id]["our_value"]
                            offer["their_value"] = self.values[offer_id]["their_value"]

                        offer["receipt"] = self.get_receipt(offer["tradeid"])
                        add_trade(offer)
                        self.log.info("Offer was added to the database")

                if offer_id in self.values:
                    self.values.pop(offer_id)

                self.processed.remove(offer_id)

    def run(self) -> None:
        self.log.info(f"Fetching offers every {TIMEOUT} seconds")

        while True:
            # we want to wait for TIMEOUT seconds before fetching again
            if self.last_offer_fetch + TIMEOUT > time.time():
                # sleep 100 ms to limit cpu usage
                time.sleep(0.1)
                continue

            try:
                self._process_offers()
                self._update_offer_states()
            except Exception as e:
                self.log.error(e)
