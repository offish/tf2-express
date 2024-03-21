from .database import Database
from .options import Options
from .offer import valuate, OfferData
from .inventory import (
    ExpressInventory,
    receipt_item_to_inventory_item,
    format_items_list_to_dict,
)
from .deals import Deals

from dataclasses import asdict
from json import dumps
import logging
import time

from steampy.exceptions import InvalidCredentials
from steampy.client import SteamClient, Asset
from steampy.utils import GameOptions
from tf2_utils import (
    Item,
    CurrencyExchange,
    Offer,
    PricesTF,
    is_pure,
    get_sku,
    to_scrap,
    to_refined,
    refinedify,
    account_id_to_steam_id,
    get_steam_id_from_trade_url,
)


GAME = GameOptions.TF2


class Express:
    def __init__(self, bot: dict, options: Options) -> None:
        self.name = bot["name"]
        self.username = bot["username"]
        self.__password = bot["password"]
        self.__secrets = bot["secrets"]
        self.steam_id = self.__secrets["steamid"]
        self.client = SteamClient(bot["api_key"])
        self.db = Database(options.database)
        self.pricer = PricesTF()
        self.inventory = ExpressInventory(
            self.db,
            self.steam_id,
            options.inventory_provider,
            options.inventory_api_key,
        )
        self.deals = Deals(self, options.enable_deals)

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
            self.client.login(self.username, self.__password, dumps(self.__secrets))

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

    def __get_receipt(self, trade_id: str) -> list[dict]:
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

    def __get_scrap_price(self, sku: str, intent: str) -> int:
        key_price = self.__get_key_price()
        keys, metal = self.db.get_price(sku, intent)
        return key_price * keys + to_scrap(metal)

    def __passed_item_check(
        self, their_items: list[dict], our_items: list[dict]
    ) -> bool:
        their_value = 0
        our_value = 0

        for item in their_items:
            their_value += self.__get_scrap_price(item["sku"], "buy")

        for item in our_items:
            our_value += self.__get_scrap_price(item["sku"], "sell")

        # NOTE: make sure tf2-arbitrage actually sendes the lowest price
        return their_value == our_value

    def __get_key_price(self) -> int:
        # TODO: use stn key prices, which we keep updated every 10 minutes
        return to_scrap(self.db.get_item("5021;6")["buy"]["metal"])

    def send_offer(self, trade_url: str, intent: str, sku: str) -> dict:
        """only used for deals"""
        # NOTE: only works for buying/selling one item at a time
        scrap_price = 0

        key_price = self.__get_key_price()

        keys, metal = self.db.get_price(sku, intent)
        scrap_price += key_price * keys + to_scrap(metal)

        steam_id = get_steam_id_from_trade_url(trade_url)
        our_inventory = self.inventory.get_our_inventory()
        their_inventory = self.inventory.fetch_their_inventory(steam_id)

        currencies = CurrencyExchange(
            their_inventory, our_inventory, intent, scrap_price, key_price
        )
        currencies.calculate()

        if not currencies.is_possible():
            logging.warning("Currencies could not add up")
            return {}

        their_items, our_items = currencies.get_currencies()

        logging.debug(f"{their_items=}")
        logging.debug(f"{our_items=}")

        # print(f"{their_items=} {our_items=}")

        if intent == "buy":
            if not self.inventory.has_sku_in_their_inventory(sku):
                logging.warning(f"{steam_id} does not have {sku} in their inventory")
                return {}

            their_items.append(self.inventory.get_their_last_item(sku))

        else:
            if not self.inventory.has_sku_in_our_inventory(sku):
                logging.warning(f"We do not have {sku} in our inventory")
                return {}

            our_items.append(self.inventory.get_our_last_item(sku))

        if not self.__passed_item_check(their_items, our_items):
            logging.warning("Offer did not pass the offer item check")
            return {}

        our_assets = [Asset(item["assetid"], GAME) for item in our_items]
        their_assets = [Asset(item["assetid"], GAME) for item in their_items]

        offer = self.client.make_offer_with_url(our_assets, their_assets, trade_url)

        logging.info(f"{offer=}")

        if not offer.get("success"):
            return offer

        their_items = format_items_list_to_dict(their_items)
        our_items = format_items_list_to_dict(our_items)

        logging.debug(f"{their_items=}")
        logging.debug(f"{our_items=}")

        offer_data = OfferData(
            offer_id=offer["tradeofferid"],
            steam_id_other=steam_id,
            message="",
            time_created=time.time(),
            their_items=their_items,
            our_items=our_items,
        )
        self.processed.append(offer_data)
        self.active_offers += 1

        logging.info(f"Offer for {sku} was sent to {steam_id}")

        return offer

    def __surpasses_max_stock(self, their_items: list[dict]) -> bool:
        in_offer = {}

        for i in their_items:
            item = Item(their_items[i])
            sku = get_sku(item)

            if sku not in in_offer:
                in_offer[sku] = 1
            else:
                in_offer[sku] += 1

        for sku in in_offer:
            logging.debug(f"getting in_stock and max_stock for {sku} {in_offer[sku]=}")

            # no max stock for pure items
            if is_pure(sku):
                continue

            # stock is updated every time a trade is completed
            # NOTE: rename to limits
            in_stock, max_stock = self.db.get_stock(sku)

            logging.debug(f"{sku} {in_stock=} {max_stock=}")

            # item does not have max_stock
            if max_stock == -1:
                continue

            if in_stock + in_offer[sku] > max_stock:
                return True

        return False

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

            if self.__surpasses_max_stock(their_items):
                self.__log_trade(
                    "Trade would surpass our max stock, ignoring offer", level="WARNING"
                )
                return

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

            # NOTE: add is_declined, is_cancelled (assetid might have change
            #  according to tf2autobot members)

            if trade.is_accepted():
                self.accepted_offers += 1

                # TODO: this offer might have been sent by us, interesting to see if we
                # set offer_data correctly and it works

                our_items = offer_data.our_items

                # these items were traded away
                for t in our_items:
                    traded_item = our_items[t]

                    # this is a copy of our inventory
                    for i in self.inventory.get_our_inventory():
                        if (
                            traded_item["classid"] != i["classid"]
                            or traded_item["instanceid"] != i["instanceid"]
                        ):
                            continue

                        item = Item(i)
                        sku = get_sku(item)

                        self.deals.update_deal_value(sku, is_sold=True)
                        self.inventory.remove_item(i)
                        break

                if self.options.save_trades:
                    logging.info("Saving offer data...")

                    if offer.get("tradeid"):
                        receipt = self.__get_receipt(offer["tradeid"])

                        if self.options.save_receipt:
                            offer_data.receipt = receipt

                        # items in receipt are items received
                        for i in receipt:
                            # NOTE: this must be parsed to be a normal item
                            # receipt item != inventory item
                            inventory_item = receipt_item_to_inventory_item(i)

                            item = Item(inventory_item)
                            sku = get_sku(item)

                            self.deals.update_deal_value(sku, is_bought=True)
                            inventory_item["sku"] = sku
                            self.inventory.add_item(inventory_item)

                    self.db.insert_trade(asdict(offer_data))

                self.inventory.update_stock()

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

        self.deals.begin()

        if self.options.fetch_prices_on_startup:
            self.__append_autopriced_items()
            self.__update_prices()

        self.inventory.fetch_our_inventory()
        self.inventory.update_stock()

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

            logging.debug(f"Currently in processed: {len(self.processed)}")

            self.__process_offers()
            self.__update_offer_states()
            self.deals.process_deals()
