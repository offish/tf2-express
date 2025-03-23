import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

import steam
from tf2_utils import (
    CurrencyExchange,
    Item,
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

from .conversion import item_data_to_item_object, item_object_to_item_data
from .inventory import get_first_non_pure_sku
from .options import COUNTER_OFFER_MESSAGE, OFFER_ACCEPTED_MESSAGE, SEND_OFFER_MESSAGE
from .utils import is_only_taking_items, is_two_sided_offer, swap_intent

if TYPE_CHECKING:
    from .express import Express


class TradeManager:
    def __init__(self, client: "Express") -> None:
        self.client = client
        self.pricing = client.pricing_manager
        self.inventory_manager = client.inventory_manager
        self.db = client.database
        self.options = client.options

    def _valuate(
        self, items: list[dict], intent: str, all_skus: list[str]
    ) -> tuple[int, bool]:
        has_unpriced = False
        total = 0

        key_scrap_price = self.pricing.get_key_scrap_price(intent)

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
                keys, metal = self.db.get_price(sku, intent)

            elif item.is_craft_hat() and self.options.allow_craft_hats:
                keys, metal = self.db.get_price("-100;6", intent)

            value = keys * key_scrap_price + to_scrap(metal)

            # dont need to process rest of offer since we cant know the total price
            if not value and intent == "sell":
                has_unpriced = True
                break

            logging.debug(f"{intent} {sku=} has {value=}")
            total += value

        # total scrap
        return total, has_unpriced

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
            scrap_price = self.pricing.get_scrap_price(sku, "buy")

            logging.debug(f"{sku=} has {scrap_price=}")

            their_value += scrap_price

        for item in our_items:
            sku = item["sku"]
            scrap_price = self.pricing.get_scrap_price(sku, "sell")

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
            item_data_to_item_object(self.client._state, self.client.user, item)
            for item in our_items
        ]
        their_items = [
            item_data_to_item_object(self.client._state, partner, item)
            for item in their_items
        ]

        if message is None:
            message = SEND_OFFER_MESSAGE

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
        all_skus = self.db.get_skus()

        if sku not in all_skus:
            logging.warning(f"We are not banking {sku}!")
            await partner.send(f"Sorry, I'm not banking {sku}")
            return

        has_price = self.db.has_price(sku)

        if not has_price:
            logging.warning(f"Item {sku} does not have a price")
            await partner.send(f"Sorry, I do not have a price for {sku}")
            return

        key_price = self.pricing.get_key_scrap_price(swap_intent(intent))
        keys, metal = self.db.get_price(sku, intent)
        scrap_price = key_price * keys + to_scrap(metal)

        # get fresh instance of inventory (stores both our and theirs)
        inventory = self.inventory_manager.get_inventory_instance()
        our_inventory = self.inventory_manager.our_inventory
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
        all_skus = self.db.get_skus()
        their_items = []
        our_items = []
        scrap_price = 0

        logging.debug(f"Creating offer {partner_steam_id=} {intent=} {asset_ids=}")

        inventory = self.inventory_manager.get_inventory_instance()
        our_inventory = self.inventory_manager.our_inventory
        their_inventory = inventory.fetch_their_inventory(partner_steam_id)

        asset_id_inventory = their_inventory if intent == "buy" else our_inventory
        key_scrap_price = self.pricing.get_key_scrap_price(swapped_intent)

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

            if not self.db.has_price(sku):
                logging.warning(f"Item {sku} does not have a price")
                return

            keys, metal = self.db.get_price(sku, intent)
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
            trade.user, sku, "sell", message=COUNTER_OFFER_MESSAGE
        )

        if data is None:
            logging.warning("Counter offer could not be created")
            return

        offer, offer_data = data

        await trade.counter(offer)

        self.client.processed_offers[offer.id] = offer_data

    def _is_owner(self, partner_steam_id: int) -> bool:
        return partner_steam_id in self.options.owners

    def _surpasses_max_stock(self, their_items: list[dict]) -> bool:
        in_offer = {"-100;6": 0}

        for i in their_items:
            item = Item(i)
            sku = get_sku(item)

            if item.is_craft_hat() and self.options.allow_craft_hats:
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
            in_stock, max_stock = self.db.get_stock(sku)

            # item does not have max_stock
            if max_stock == -1:
                continue

            if in_stock + in_offer[sku] > max_stock:
                return True

        return False

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
        if trade.is_gift() and self.options.accept_donations:
            logging.info("User is trying to give items")
            await trade.accept()
            return

        # decline trade holds
        if await partner.escrow() is not None and self.options.decline_trade_hold:
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

        all_skus = self.db.get_skus()

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

        if self.options.counter_bad_offers:
            logging.info("Counter offering...")
            await self._counter_offer(trade, our_items)
            return

        logging.info("Ignoring offer as automatic decline is disabled")

    async def process_offer(self, trade: steam.TradeOffer) -> dict[str, Any]:
        while not self.client.bot_is_ready or not self.client.are_prices_updated:
            await asyncio.sleep(1)

        offer_data = {}
        await self._process_offer(trade, offer_data)

        return offer_data

    async def send_offer(
        self, partner: steam.User, intent: str, sku: str, token: str = None
    ) -> int:
        assert intent in ["buy", "sell"]

        while not self.client.bot_is_ready or not self.client.are_prices_updated:
            await asyncio.sleep(1)

        data = await self._create_offer(partner, sku, intent, token)

        if data is None:
            return 0

        offer, offer_data = data

        logging.info(f"Sending offer to {partner.name}...")

        await partner.send("Sending offer...")
        await partner.send(trade=offer)

        self.client.processed_offers[offer.id] = offer_data

        logging.info(f"Sent offer for {sku}")

        return offer.id

    async def send_asset_ids_offer(
        self,
        partner: steam.User,
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

        self.client.processed_offers[offer.id] = offer_data

        logging.info(f"Sent offer for {asset_ids}")

        return offer.id

    async def send_offer_by_trade_url(
        self, trade_url: str, intent: str, asset_ids: list[str]
    ) -> int:
        steam_id = get_steam_id_from_trade_url(trade_url)
        token = get_token_from_trade_url(trade_url)
        partner = self.client.get_user(int(steam_id))

        logging.debug(f"{partner.name} has {steam_id=} {token=}")

        return await self.send_asset_ids_offer(partner, intent, asset_ids, token)

    async def process_offer_state(
        self, trade: steam.TradeOffer, offer_data: dict[str, Any]
    ) -> None:
        while not self.client.bot_is_ready:
            await asyncio.sleep(1)

        steam_id = str(trade.user.id64)
        offer_id = str(trade.id)
        was_accepted = trade.state == steam.TradeOfferState.Accepted

        logging.info(f"Offer #{offer_id} with {steam_id} was {trade.state.name}")

        if offer_id in self.client.pending_site_offers:
            self.client.ws_manager.remove_user_from_queue(steam_id)

            await self.client.ws_manager._send_ws_message(
                {
                    "success": was_accepted,
                    "steam_id": steam_id,
                    "message_type": "trade_status",
                    "message": f"Offer was {trade.state.name}!",
                }
            )

            del self.client.pending_site_offers[offer_id]

        if trade.user.id64 in self.client.pending_offer_users:
            self.client.pending_offer_users.remove(trade.user.id64)

        if not was_accepted:
            return

        if trade.user.is_friend():
            await trade.user.send(OFFER_ACCEPTED_MESSAGE)

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

        self.db.insert_trade(offer_data)
        # await self._group.invite(trade.user)

        logging.debug("Getting receipt...")

        receipt = await trade.receipt()
        self.client.inventory_manager.update_inventory_with_receipt(receipt)

        logging.debug("Inventory was updated after receipt")
