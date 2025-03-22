import asyncio
import json
import logging
import time
from threading import Thread
from typing import Any

import steam
from tf2_utils import (
    CurrencyExchange,
    Item,
    PricesTFWebsocket,
    get_metal,
    get_sku,
    get_steam_id_from_trade_url,
    get_token_from_trade_url,
    is_metal,
    is_pure,
    refinedify,
    to_refined,
    to_scrap,
)
from websockets import connect
from websockets.asyncio.connection import Connection
from websockets.exceptions import ConnectionClosedError, InvalidStatus

from .command import parse_command
from .conversion import item_data_to_item_object, item_object_to_item_data
from .database import Database
from .exceptions import NoKeyPrice
from .inventory import ExpressInventory, get_first_non_pure_sku
from .listing_manager import ListingManager
from .options import (
    COUNTER_OFFER_MESSAGE,
    FRIEND_ACCEPT_MESSAGE,
    OFFER_ACCEPTED_MESSAGE,
    SEND_OFFER_MESSAGE,
    Options,
)
from .utils import is_only_taking_items, is_two_sided_offer, swap_intent


class ExpressClient(steam.Client):
    def __init__(self, options: Options):
        self._is_ready = False
        self._prices_are_updated = False
        self._options = options
        self._db = Database(options.username)
        self._ws: Connection = None

        self._pricelist_count = 0
        self._has_been_autopriced = set()
        self._pending_offer_users = set()
        self._processed_offers = {}
        self._users_in_queue = set()
        self._pending_site_offers = {}

        self._set_defaults()

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
        self._counter_offer_message = COUNTER_OFFER_MESSAGE

    def _set_pricer(self) -> None:
        self._pricer = PricesTFWebsocket(self._on_price_update)
        prices_thread = Thread(target=self._pricer.listen, daemon=True)
        prices_thread.start()

        logging.info("Listening to PricesTF")

        self._prices_tf = self._pricer._prices_tf

    def _on_price_update(self, data: dict) -> None:
        if data.get("type") != "PRICE_CHANGED":
            return

        if "sku" not in data.get("data", {}):
            return

        sku = data["data"]["sku"]

        if sku not in self._db.get_autopriced():
            return

        # update database price
        self._db.update_autoprice(data)
        self._has_been_autopriced.add(sku)

        if not self._options.use_backpack_tf:
            return

        # update listing price
        self._listing_manager.set_price_changed(sku)

    async def _send_ws_message(self, data: dict) -> None:
        message = json.dumps({"message": data})
        await self._ws.send(message)

    def _add_user_to_queue(self, steam_id: str) -> None:
        self._users_in_queue.add(steam_id)
        logging.debug(f"Added user {steam_id} to queue")

    def _remove_user_from_queue(self, steam_id: str) -> None:
        self._users_in_queue.remove(steam_id)
        logging.debug(f"Removed user {steam_id} from queue")

    async def _on_incoming_site_trade(self, data: dict) -> None:
        logging.info("Got incoming site trade")

        message = data.get("message", {})

        message_type = message.get("message_type")
        asset_ids = message.get("asset_ids")
        trade_url = message.get("trade_url")
        steam_id = message.get("steam_id")
        intent = message.get("intent")
        intent = message.get("intent")

        if message_type != "initalize_trade":
            logging.debug(f"Got {message_type=} for {message=}")
            return

        if steam_id in self._users_in_queue:
            logging.debug(f"User {steam_id} is already in queue")

            await self._send_ws_message(
                {
                    "success": False,
                    "steam_id": steam_id,
                    "message_type": "queue",
                    "message": "You are already in the queue!",
                }
            )
            return

        self._add_user_to_queue(steam_id)

        await self._send_ws_message(
            {
                "success": True,
                "steam_id": steam_id,
                "message_type": "queue",
                "message": "Please wait while we process your offer!",
            }
        )

        offer_id = await self.send_offer_by_trade_url(trade_url, intent, asset_ids)

        if not offer_id:
            logging.warning(f"Could not send offer to {steam_id}")
            self._remove_user_from_queue(steam_id)

            await self._send_ws_message(
                {
                    "success": False,
                    "steam_id": steam_id,
                    "message_type": "trade",
                    "message": "Could not send offer",
                }
            )
            return

        await self._send_ws_message(
            {
                "success": True,
                "steam_id": steam_id,
                "message_type": "trade",
                "message": "Offer was sent",
                "offer_id": offer_id,
            }
        )
        self._pending_site_offers[str(offer_id)] = steam_id

    async def _connect_to_site_ws(self, uri: str) -> None:
        async with connect(uri) as websocket:
            logging.info("Connected to websocket!")

            self._ws = websocket

            while True:
                message = await websocket.recv()
                data = json.loads(message)

                await self._on_incoming_site_trade(data)

    async def _listen_for_incoming_site_trades(self) -> None:
        token = self._options.express_tf_token
        uri = self._options.express_tf_uri + token

        while True:
            try:
                await self._connect_to_site_ws(uri)
            except (InvalidStatus, ConnectionClosedError, TimeoutError) as e:
                logging.error(f"Error connecting to websocket: {e}")

            await asyncio.sleep(5)

    def _run_site_asyncio_in_thread(self) -> None:
        asyncio.run(self._listen_for_incoming_site_trades())

    def _update_price(self, sku: str) -> None:
        price = self._prices_tf.get_price(sku)
        self._db.update_autoprice(price)

    def _update_autopriced_items(self) -> None:
        skus = self._db.get_autopriced()

        if self._options.use_backpack_tf:
            self._listing_manager.delete_inactive_listings(skus)

        self._prices_tf.request_access_token()

        for sku in self._has_been_autopriced.copy():
            if sku not in skus:
                self._has_been_autopriced.remove(sku)

        # make this more efficient, fetch x pages and check for missing
        # if missing fetch the missing ones directly
        # should probably request price updates also
        for sku in skus:
            if sku in self._has_been_autopriced:
                continue

            self._update_price(sku)
            self._has_been_autopriced.add(sku)

            if not self._options.use_backpack_tf:
                continue

            self._listing_manager.set_price_changed(sku)

        self._prices_are_updated = True

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
            item_data["sku"] = get_sku(item_data)

            updated_inventory.append(item_data)

        self._inventory.set_our_inventory(updated_inventory)

        logging.info("Our inventory was updated")

        if not self._options.use_backpack_tf:
            return

        # notify listing manager inventory has changed (stock needs to be updated)
        self._listing_manager.set_inventory_changed()

    def _get_key_prices(self) -> dict:
        data = self._db.get_item("5021;6")
        return {"buy": data["buy"], "sell": data["sell"]}

    def _get_key_scrap_price(self, intent: str) -> int:
        price = self._get_key_prices().get(intent)

        if "metal" not in price:
            raise NoKeyPrice("Keys need to have a price in the database!")

        return to_scrap(price["metal"])

    def _get_scrap_price(self, sku: str, intent: str) -> int:
        key_price = self._get_key_scrap_price(intent)
        keys, metal = self._db.get_price(sku, intent)
        return key_price * keys + to_scrap(metal)

    def _surpasses_max_stock(self, their_items: list[dict]) -> bool:
        in_offer = {"-100;6": 0}

        for i in their_items:
            item = Item(i)
            sku = get_sku(item)

            if item.is_craft_hat() and self._options.allow_craft_hats:
                in_offer["-100;6"] += 1

            if sku not in in_offer:
                in_offer[sku] = 1
                continue

            in_offer[sku] += 1

        for sku in in_offer:
            # no max stock for pure items
            if is_pure(sku):
                continue

            amount = in_offer[sku]

            if amount == 0:
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
        self, items: list[dict], intent: str, all_skus: list[str]
    ) -> tuple[int, bool]:
        has_unpriced = False
        total = 0

        key_scrap_price = self._get_key_scrap_price(intent)

        # valute one item at a time
        for i in items:
            item = Item(i)
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

            elif is_metal(sku):
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
        pricelist = self._db.get_pricelist()

        # first list the items we have in our inventory
        for item in self._inventory.get_our_inventory():
            sku = get_sku(item)

            # we dont care about metal
            if is_metal(sku):
                continue

            # item has to be priced
            if sku not in pricelist:
                continue

            self._listing_manager.create_listing(sku, "sell")

        # then list buy orders
        for item in pricelist:
            sku = item["sku"]
            self._listing_manager.create_listing(item, "buy")

    def _update_pricelist(self) -> None:
        self._prices_are_updated = False
        self._update_autopriced_items()
        self._pricelist_count = self._db.get_pricelist_count()

    def _pricelist_check(self) -> None:
        while True:
            time.sleep(3)

            # no change
            if self._pricelist_count == self._db.get_pricelist_count():
                continue

            # items added/removed, update prices and listings
            logging.info("Pricelist has changed, updating prices and listings...")
            self._update_pricelist()

    async def _create_offer_with_items(
        self,
        partner: steam.PartialUser,
        their_items: list[dict],
        our_items: list[dict],
        token: str = None,
        message: str = None,
    ) -> tuple[steam.TradeOffer, dict[str, Any]] | None:
        offer_data = {}
        their_value = 0
        our_value = 0

        logging.debug(f"{len(their_items)=} {len(our_items)=}")
        logging.debug("Checking if values for offer is equal...")

        for item in their_items:
            sku = item["sku"]
            scrap_price = self._get_scrap_price(sku, "buy")

            logging.debug(f"{sku=} has {scrap_price=}")

            their_value += scrap_price

        for item in our_items:
            sku = item["sku"]
            scrap_price = self._get_scrap_price(sku, "sell")

            logging.debug(f"{sku=} has {scrap_price=}")

            our_value += scrap_price

        if their_value != our_value:
            logging.warning("Error, values in offer did not add up!")
            await partner.send("Sorry, there was an error processing your offer")
            return

        logging.debug(f"Value for trade was equal {their_value=} {our_value=}")

        offer_data["their_value"] = their_value
        offer_data["our_value"] = our_value

        our_items = [
            item_data_to_item_object(self._state, self.user, item) for item in our_items
        ]
        their_items = [
            item_data_to_item_object(self._state, partner, item) for item in their_items
        ]

        if message is None:
            message = self._send_offer_message

        return (
            steam.TradeOffer(
                message=message,
                token=token,
                sending=our_items,
                receiving=their_items,
            ),
            offer_data,
        )

    async def _create_offer(
        self,
        partner: steam.PartialUser,
        sku: str,
        intent: str,
        token: str = None,
        message: str = None,
    ) -> tuple[steam.TradeOffer, dict[str, Any]] | None:
        partner_steam_id = partner.id64
        all_skus = self._db.get_skus()

        if sku not in all_skus:
            logging.warning(f"We are not banking {sku}!")
            await partner.send(f"Sorry, I'm not banking {sku}")
            return

        has_price = self._db.has_price(sku)

        if not has_price:
            logging.warning(f"Item {sku} does not have a price")
            await partner.send(f"Sorry, I do not have a price for {sku}")
            return

        key_price = self._get_key_scrap_price(swap_intent(intent))
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

        if not currencies.is_possible:
            logging.warning("Currencies does not add up for trade")
            await partner.send(
                "Sorry, metal did not add up for this trade. Do you have enough metal?"
            )
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

        return await self._create_offer_with_items(
            partner, their_items, our_items, token, message
        )

    async def _create_asset_ids_offer(
        self,
        partner: steam.PartialUser,
        asset_ids: list[str],
        intent: str,
        token: str = None,
        message: str = None,
    ) -> tuple[steam.TradeOffer, dict[str, Any]] | None:
        partner_steam_id = str(partner.id64)
        swapped_intent = swap_intent(intent)
        all_skus = self._db.get_skus()
        their_items = []
        our_items = []
        scrap_price = 0

        logging.debug(f"Creating offer {partner_steam_id=} {intent=} {asset_ids=}")

        inventory = self._get_inventory_instance()
        our_inventory = inventory.set_our_inventory(self._inventory.our_inventory)
        their_inventory = inventory.fetch_their_inventory(partner_steam_id)

        asset_id_inventory = their_inventory if intent == "buy" else our_inventory
        key_scrap_price = self._get_key_scrap_price(swapped_intent)

        logging.debug(f"{key_scrap_price=} with {swapped_intent=}")

        for item in asset_id_inventory:
            asset_id = item["assetid"]

            if asset_id not in asset_ids:
                continue

            logging.debug(f"Found {asset_id=} in inventory")

            sku = item["sku"]

            if sku not in all_skus:
                logging.warning(f"We are not banking {sku}!")
                return

            if not self._db.has_price(sku):
                logging.warning(f"Item {sku} does not have a price")
                return

            keys, metal = self._db.get_price(sku, intent)
            scrap_price += key_scrap_price * keys + to_scrap(metal)

            logging.debug(f"{sku=} has {intent} {scrap_price=}")

            if intent == "buy":
                their_items.append(item)
                logging.debug(f"Added {sku} {asset_id=} to their items")
            else:
                our_items.append(item)
                logging.debug(f"Added {sku} {asset_id=} to our items")

        item_length = len(their_items) if intent == "buy" else len(our_items)

        logging.debug(f"{item_length=} {asset_ids=}")

        if item_length != len(asset_ids):
            logging.warning("Not all items were added")
            return

        currencies = CurrencyExchange(
            their_inventory, our_inventory, intent, scrap_price, key_scrap_price
        )
        currencies.calculate()

        if not currencies.is_possible:
            logging.warning("Currencies does not add up for trade")
            return

        their_metal, our_metal = currencies.get_currencies()
        logging.debug(
            f"Currencies for trade adds up {len(their_metal)=} {len(our_metal)=}"
        )

        their_items += their_metal
        our_items += our_metal

        return await self._create_offer_with_items(
            partner, their_items, our_items, token, message
        )

    async def _counter_offer(
        self, trade: steam.TradeOffer, our_items: list[dict]
    ) -> None:
        # only supported counter offer for one item
        sku = get_first_non_pure_sku(our_items)

        if sku is None:
            logging.warning("Found no non-pure items to counter offer")
            await trade.decline()
            return

        logging.info(f"Counter offering {sku} to {trade.user.name}...")

        data = await self._create_offer(
            trade.user, sku, "sell", message=self._counter_offer_message
        )

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
        if trade.is_gift() and self._options.accept_donations:
            logging.info("User is trying to give items")
            await trade.accept()
            return

        # decline trade holds
        if await partner.escrow() is not None and self._options.decline_trade_hold:
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

        all_skus = self._db.get_skus()

        # we dont care about unpriced items on their side
        their_value, _ = self._valuate(their_items, "buy", all_skus)
        our_value, has_unpriced = self._valuate(our_items, "sell", all_skus)
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

        if self._options.counter_bad_offers:
            logging.info("Counter offering...")
            await self._counter_offer(trade, our_items)
            return

        logging.info("Ignoring offer as automatic decline is disabled")

    async def setup(self) -> None:
        # set steam api key
        self.http.api_key = self._api_key

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

        self._set_pricer()

        listing_manager_thread = Thread(target=self._listing_manager.run, daemon=True)
        listing_manager_thread.start()

        if self._options.fetch_prices_on_startup:
            pricelist_thread = Thread(target=self._pricelist_check, daemon=True)
            pricelist_thread.start()

        if self._options.is_express_tf_bot:
            incoming_trades_thread = Thread(
                target=self._run_site_asyncio_in_thread, daemon=True
            )
            incoming_trades_thread.start()

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
        intent = swap_intent(intent)

        await message.channel.send(f"Processing your trade for {amount}x {sku}...")

        if message.author.id64 in self._pending_offer_users:
            await message.channel.send("You appear to have a pending offer already")
            return

        offer_id = await self.send_offer(message.author, intent, sku)

        if offer_id:
            self._pending_offer_users.add(message.author.id64)

    async def process_offer(self, trade: steam.TradeOffer) -> dict[str, Any]:
        while not self._is_ready or not self._prices_are_updated:
            await asyncio.sleep(1)

        offer_data = {}
        await self._process_offer(trade, offer_data)

        return offer_data

    async def send_offer(
        self, partner: steam.PartialUser, intent: str, sku: str, token: str = None
    ) -> int:
        assert intent in ["buy", "sell"]

        while not self._is_ready or not self._prices_are_updated:
            await asyncio.sleep(1)

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

    async def send_asset_ids_offer(
        self,
        partner: steam.PartialUser,
        intent: str,
        asset_ids: list[str],
        token: str = None,
    ) -> int:
        data = await self._create_asset_ids_offer(partner, asset_ids, intent, token)

        if data is None:
            return 0

        offer, offer_data = data

        logging.info(f"Sending offer to {partner.name}...")

        await partner.send(trade=offer)

        self._processed_offers[offer.id] = offer_data

        logging.info(f"Sent offer for {asset_ids}")

        return offer.id

    async def send_offer_by_trade_url(
        self, trade_url: str, intent: str, asset_ids: list[str]
    ) -> int:
        steam_id = get_steam_id_from_trade_url(trade_url)
        token = get_token_from_trade_url(trade_url)
        partner = self.get_user(int(steam_id))

        return await self.send_asset_ids_offer(partner, intent, asset_ids, token)

    async def process_offer_state(
        self, trade: steam.TradeOffer, offer_data: dict[str, Any]
    ) -> None:
        while not self._is_ready:
            await asyncio.sleep(1)

        steam_id = str(trade.user.id64)
        offer_id = str(trade.id)
        was_accepted = trade.state == steam.TradeOfferState.Accepted

        logging.info(f"Offer #{offer_id} with {steam_id} was {trade.state.name}")

        if offer_id in self._pending_site_offers:
            self._remove_user_from_queue(steam_id)

            await self._send_ws_message(
                {
                    "success": was_accepted,
                    "steam_id": steam_id,
                    "message_type": "trade_status",
                    "message": f"Offer was {trade.state.name}!",
                }
            )

            del self._pending_site_offers[offer_id]

        if trade.user.id64 in self._pending_offer_users:
            self._pending_offer_users.remove(trade.user.id64)

        if not was_accepted:
            return

        if trade.user.is_friend():
            await trade.user.send(self._offer_accepted_message)

        offer_data |= {
            "offer_id": offer_id,
            "partner_id": str(trade.user.id64),
            "partner_name": trade.user.name,
            "message": trade.message,
            "their_items": [item_object_to_item_data(i) for i in trade.receiving],
            "our_items": [item_object_to_item_data(i) for i in trade.sending],
            "key_prices": self._get_key_prices(),
            "state": trade.state.name.lower(),
            "timestamp": time.time(),
        }

        self._db.insert_trade(offer_data)
        # await self._group.invite(trade.user)

        logging.debug("Getting receipt...")

        receipt = await trade.receipt()
        self._update_inventory_with_receipt(receipt)

        logging.debug("Inventory was updated after receipt")
