import asyncio
import logging
import time
from threading import Thread
from typing import Any

import steam
from tf2_utils import (
    CurrencyExchange,
    Item,
    PricesTFSocket,
    get_metal,
    get_sku,
    is_metal,
    is_pure,
    refinedify,
    to_refined,
    to_scrap,
)

from .command import parse_command
from .conversion import item_data_to_item_object, item_object_to_item_data
from .database import Database
from .inventory import ExpressInventory, get_first_non_pure_sku
from .listing_manager import ListingManager
from .offer import is_only_taking_items, is_two_sided_offer
from .options import (
    FRIEND_ACCEPT_MESSAGE,
    OFFER_ACCEPTED_MESSAGE,
    SEND_OFFER_MESSAGE,
    Options,
)


class ExpressClient(steam.Client):
    def __init__(self, options: Options):
        self._is_ready = False
        self._options = options
        self._db = Database(options.database)

        self._processed_offers = {}
        self._set_defaults()

        if self._options.fetch_prices_on_startup:
            self._autopriced_skus = self._db.get_autopriced()
            self._set_pricer()

        super().__init__(
            app=steam.TF2,
            state=steam.PersonaState.LookingToTrade,
            language=steam.Language.English,
            **options.client_options,
        )

    def _set_defaults(self) -> None:
        self._send_offer_message = SEND_OFFER_MESSAGE
        self._friend_accept_message = FRIEND_ACCEPT_MESSAGE
        self._offer_accepted_message = OFFER_ACCEPTED_MESSAGE

    def _set_pricer(self) -> None:
        self._pricer = PricesTFSocket(self._on_price_update)
        prices_thread = Thread(target=self._pricer.listen, daemon=True)
        prices_thread.start()

        logging.info("Listening to PricesTF")

        self._prices_tf = self._pricer.prices_tf

        if not self._options.fetch_prices_on_startup:
            return

        self._update_autopriced_items()

    def _on_price_update(self, data: dict) -> None:
        if data.get("type") != "PRICE_CHANGED":
            return

        if "sku" not in data.get("data", {}):
            return

        sku = data["data"]["sku"]

        if sku not in self._autopriced_skus:
            return

        # update database price
        self._db.update_autoprice(data)
        # update listing price
        self._listing_manager.set_price_changed(sku)

    def _update_autopriced_items(self) -> None:
        skus = self._autopriced_skus
        self._prices_tf.request_access_token()

        for sku in skus:
            price = self._prices_tf.get_price(sku)
            self._db.update_autoprice(price)

        logging.info(f"Updated prices for {len(skus)} autopriced items")

    def _get_inventory_instance(self) -> ExpressInventory:
        return ExpressInventory(
            str(self.user.id64),
            self._options.inventory_provider,
            self._options.inventory_api_key,
        )

    def _update_inventory_with_receipt(self, receipt: steam.TradeOfferReceipt) -> None:
        updated_inventory = self._inventory.our_inventory.copy()

        for item in receipt.sent:
            item_data = item_object_to_item_data(item)

            for i in updated_inventory.copy():
                if (
                    i["instanceid"] != item_data["instanceid"]
                    or i["classid"] != item_data["classid"]
                    or i["market_hash_name"] != item_data["market_hash_name"]
                ):
                    continue

                del updated_inventory[i]
                break

        for item in receipt.received:
            item_data = item_object_to_item_data(item)
            updated_inventory.append(item_data)

        self._inventory.set_our_inventory(updated_inventory)

        logging.info("Our inventory was updated")

        if not self._options.use_backpack_tf:
            return

        # notify listing manager inventory has changed (stock needs to be updated)
        self._listing_manager.set_inventory_changed()

    def _get_key_price(self, intent: str) -> int:
        item = self._db.get_item("5021;6")
        return item[intent]["metal"]

    def _get_scrap_price(self, sku: str, intent: str) -> int:
        key_price = self._get_key_price(intent)
        keys, metal = self._db.get_price(sku, intent)
        return key_price * keys + to_scrap(metal)

    def _surpasses_max_stock(self, their_items: list[dict]) -> bool:
        # NOTE: we do not check limits for pure items
        random_craft_hat_sku = "-100;6"
        in_offer = {random_craft_hat_sku: 0}

        for i in their_items:
            item = Item(their_items[i])
            sku = get_sku(item)

            if item.is_craft_hat() and self._options.allow_craft_hats:
                in_offer[random_craft_hat_sku] += 1

            if sku not in in_offer:
                in_offer[sku] = 1
                continue

            in_offer[sku] += 1

        for sku in in_offer:
            # no max stock for pure items
            if is_pure(sku):
                continue

            # stock is updated every time a trade is completed
            in_stock, max_stock = self._db.get_stock(sku)

            # item does not have max_stock
            if max_stock == -1:
                continue

            if in_stock + in_offer[sku] > max_stock:
                return True

        return False

    def _is_owner(self, partner_steam_id: int) -> bool:
        return partner_steam_id in self._options.owners

    def _valuate(
        self, items: dict, intent: str, all_skus: list[str], key_prices: dict[str, Any]
    ) -> tuple[int, bool]:
        has_unpriced = False
        key_price = 0.0
        total = 0

        if key_prices:
            key_price = key_prices[intent]["metal"]
        else:
            logging.warning("No key price found, will valuate keys at 0 ref")

        key_scrap_price = to_scrap(key_price)

        # valute one item at a time
        for i in items:
            item = Item(items[i])
            sku = get_sku(item)
            keys = 0
            metal = 0.0

            # appid is not 440, means no pricing for that item
            if not item.is_tf2() and intent == "sell":
                has_unpriced = True
                break

            # we dont add any price for that item -> skip
            if not item.is_tf2() and intent == "buy":
                continue

            elif item.is_key():
                keys = 1

            elif is_metal(sku):  # should be metal
                metal = to_refined(get_metal(sku))

            # has a specifc price
            elif sku in all_skus:
                keys, metal = self._db.get_price(sku, intent)

            elif item.is_craft_hat() and self._options.allow_craft_hats:
                keys, metal = self._db.get_price("-100;6", intent)

            value = keys * key_scrap_price + to_scrap(metal)

            # dont need to process rest of offer since we cant know the total price
            if not value and intent == "sell":
                has_unpriced = True
                break

            logging.debug(f"{intent} {sku=} has {value=}")
            total += value

        # total scrap
        return total, has_unpriced

    def _create_listings(self) -> None:
        items = self._db.get_pricelist()

        for item in items:
            sku = item["sku"]
            intent = item["intent"]
            self._listing_manager.create_listing(sku, intent)

    async def _create_offer(
        self, partner: steam.PartialUser, sku: str, intent: str, token: str = None
    ) -> tuple[steam.TradeOffer, dict[str, Any]] | None:
        partner_steam_id = partner.id64
        all_skus = self._db.get_skus()
        offer_data = {}
        their_value = 0
        our_value = 0

        if sku not in all_skus:
            logging.warning(f"We are not banking {sku}!")
            await partner.send(f"Sorry, I'm not banking {sku}")
            return

        has_price = self._db.has_price(sku)

        if not has_price:
            logging.warning(f"Item {sku} does not have a price")
            await partner.send(f"Sorry, I do not have a price for {sku}")
            return

        key_price = self._get_key_price("buy" if intent == "sell" else "sell")
        keys, metal = self._db.get_price(sku, intent)
        scrap_price = key_price * keys + to_scrap(metal)

        # get fresh instance of inventory (stores both our and theirs)
        inventory = self._get_inventory_instance()
        our_inventory = inventory.set_our_inventory(self._inventory.our_inventory)
        their_inventory = inventory.fetch_their_inventory(str(partner_steam_id))

        currencies = CurrencyExchange(
            their_inventory, our_inventory, intent, scrap_price, key_price
        )
        currencies.calculate()

        if not currencies.is_possible():
            logging.warning("Currencies does not add up for trade")
            await partner.send("Sorry, metal currencies did not add up")
            return

        their_items, our_items = currencies.get_currencies()

        if intent == "buy":
            if not inventory.has_sku_in_their_inventory(sku):
                logging.info(f"User {partner.name} does not have {sku}")
                await partner.send(
                    f"Sorry, it appears you do not have this item ({sku})"
                )
                return

            item = inventory.get_last_item_in_their_inventory(sku)
            their_items.append(item)
        else:
            if not inventory.has_sku_in_our_inventory(sku):
                logging.info(f"We do not have {sku}")
                await partner.send(f"Sorry, I do not have this item ({sku})")
                return

            item = inventory.get_last_item_in_our_inventory(sku)
            our_items.append(item)

        for item in their_items:
            their_value += self._get_scrap_price(item["sku"], "buy")

        for item in our_items:
            our_value += self._get_scrap_price(item["sku"], "sell")

        if their_value != our_value:
            logging.warning("Error, values in offer did not add up!")
            await partner.send("Sorry, there was an error processing your offer")
            return

        offer_data["their_value"] = their_value
        offer_data["our_value"] = our_value

        our_items = [
            item_data_to_item_object(self._state, self.user, item) for item in our_items
        ]
        their_items = [
            item_data_to_item_object(self._state, partner, item) for item in their_items
        ]

        return (
            steam.TradeOffer(
                message=self._send_offer_message,
                token=token,
                sending=our_items,
                receiving=their_items,
            ),
            offer_data,
        )

    async def _counter_offer(
        self, trade: steam.TradeOffer, our_items: list[dict]
    ) -> None:
        # only supported counter offer for one item
        sku = get_first_non_pure_sku(our_items)

        if sku is None:
            logging.warning("Found no non-pure items to counter offer")
            return

        logging.info(f"Counter offering {sku} to {trade.user.name}...")

        data = await self._create_offer(trade.user, sku, "sell")

        if data is None:
            logging.warning("Counter offer could not be created")
            return

        offer, offer_data = data

        await trade.counter(offer)

        self._processed_offers[offer.id] = offer_data

    async def _process_offer(
        self, trade: steam.TradeOffer, offer_data: dict[str, Any]
    ) -> None:
        partner = trade.user
        their_items_amount = len(trade.receiving)
        our_items_amount = len(trade.sending)
        items_amount = their_items_amount + our_items_amount

        logging.info(f"Processing offer #{trade.id} from {partner.name}...")
        logging.info(f"Offer contains {items_amount} item(s)")

        # is owner
        if self._is_owner(partner.id64):
            logging.info("Offer is from owner")
            await trade.accept()
            return

        # nothing on our side
        if trade.is_gift():
            logging.info("User is trying to give items")
            await trade.accept()
            return

        # decline trade holds
        if await partner.escrow() is not None:
            logging.info("User has a trade hold")
            await trade.decline()
            return

        their_items = [item_object_to_item_data(i) for i in trade.receiving]
        our_items = [item_object_to_item_data(i) for i in trade.sending]

        # only items on our side
        if is_only_taking_items(their_items_amount, our_items_amount):
            logging.info("User is trying to take items")

            await self._counter_offer(trade, our_items)
            return

        # should never not be a two sided offer here
        if not is_two_sided_offer(their_items_amount, our_items_amount):
            logging.info("Error encountered when checking offer, ignoring...")
            return

        logging.info("Offer is valid, calculating...")

        if self._surpasses_max_stock(their_items):
            logging.warning("Trade would surpass our max stock, ignoring offer")
            return

        # get mann co key buy and sell price
        key_prices = self._db.get_item("5021;6")
        all_skus = self._db.get_skus()

        # we dont care about unpriced items on their side
        their_value, _ = self._valuate(their_items, "buy", all_skus, key_prices)
        our_value, has_unpriced = self._valuate(our_items, "sell", all_skus, key_prices)
        # all prices are in scrap

        offer_data["their_value"] = their_value
        offer_data["our_value"] = our_value

        difference = to_refined(their_value - our_value)
        their_value = to_refined(their_value)
        our_value = to_refined(our_value)

        summary = "Their value: {} ref, our value: {} ref, difference: {} ref".format(
            their_value,
            our_value,
            refinedify(difference),
        )

        logging.info(summary)

        if has_unpriced:
            logging.warning("Offer has unpriced items on our side, ignoring offer")
            return

        if their_value >= our_value:
            logging.info("Accepting offer...")
            await trade.accept()
            return

        if self._options.decline_bad_offers:
            logging.info("Declining offer...")
            await trade.decline()
            return

        logging.info("Ignoring offer as automatic decline is disabled")

    async def setup(self) -> None:
        # set inventory
        self._inventory = self._get_inventory_instance()
        self._inventory.fetch_our_inventory()

        # get inventory stock and update database
        stock = self._inventory.get_stock()
        self._db.update_stock(stock)

        # we are now ready (other events can now fire)
        self._is_ready = True

        if not self._options.use_backpack_tf:
            return

        self._listing_manager = ListingManager(
            backpack_tf_token=self._options.backpack_tf_token,
            steam_id=str(self.user.id64),
            database=self._db,
            inventory=self._inventory,
        )

        listing_manager_thread = Thread(target=self._listing_manager.run, daemon=True)
        listing_manager_thread.start()

        self._create_listings()

    async def join_groups(self) -> None:
        group_id = 103582791463210868
        groups = [group_id, 103582791463210863, *self._options.groups]

        for i in groups:
            group = await self.fetch_clan(i)

            if group is None:
                continue

            if group.id64 == group_id:
                self._group = group

            await group.join()

    async def process_message(self, message: steam.Message, msg: str) -> None:
        data = parse_command(msg)

        if data is None:
            await message.channel.send("Could not parse your message")
            return

        # parse message
        intent = data["intent"]
        amount = 1  # amounts other than 1 are not supported yet
        sku = data["sku"]

        logging.info(f"{message.author.name} wants to {intent} {amount}x of {sku}")

        # swap intents
        intent = "buy" if intent == "sell" else "sell"

        await message.channel.send(f"Processing your trade for {amount}x {sku}...")
        await self.send_offer(message.author, intent, sku)

    async def process_offer(self, trade: steam.TradeOffer) -> dict[str, Any]:
        # wait for on_ready to finish
        while not self._is_ready:
            await asyncio.sleep(1)

        offer_data = {}
        await self._process_offer(trade, offer_data)

        return offer_data

    async def send_offer(
        self, partner: steam.PartialUser, intent: str, sku: str, token: str = None
    ) -> int:
        assert intent in ["buy", "sell"]

        data = await self._create_offer(partner, sku, intent, token)

        if data is None:
            return 0

        offer, offer_data = data

        logging.info(f"Sending offer to {partner.name}...")

        await partner.send("Sending offer...")
        await partner.send(trade=offer)

        self._processed_offers[offer.id] = offer_data

        logging.info(f"Sent offer for {sku}")

        return offer.id

    async def process_offer_state(
        self, trade: steam.TradeOffer, offer_data: dict[str, Any]
    ) -> None:
        # wait for on_ready to finish
        while not self._is_ready:
            await asyncio.sleep(1)

        logging.info(f"Offer #{trade.id} was {trade.state.name}")

        if trade.state != steam.TradeOfferState.Accepted:
            return

        if trade.user.is_friend():
            await trade.user.send(self._offer_accepted_message)

        offer_data |= {
            "offer_id": trade.id,
            "partner_id": trade.user.id64,
            "partner_name": trade.user.name,
            "message": trade.message,
            "their_items": [item_object_to_item_data(i) for i in trade.receiving],
            "our_items": [item_object_to_item_data(i) for i in trade.sending],
            "key_prices": self._db.get_item("5021;6"),
            "state": trade.state.name.lower(),
            "timestamp": time.time(),
        }

        self._db.insert_trade(offer_data)
        await self._group.invite(trade.user)

        receipt = await trade.receipt()
        self._update_inventory_with_receipt(receipt)
