import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Callable

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

from ..conversion import item_data_to_item_object, item_object_to_item_data
from ..inventory import get_non_pure_skus
from ..utils import is_only_taking_items, is_two_sided_offer, swap_intent
from .base_manager import BaseManager


class TradeManager(BaseManager):
    async def setup(self) -> None:
        self.arbitrage = self.client.arbitrage_manager
        self.owners = [str(steam_id) for steam_id in self.options.owners]
        self.blacklist = [str(steam_id) for steam_id in self.options.blacklist]

    @staticmethod
    def _is_offer_active(trade: steam.TradeOffer) -> bool:
        try:
            trade._check_active()
            return True
        except ValueError:
            return False

    @staticmethod
    async def _retry_action(
        trade: steam.TradeOffer, action_name: str, action_func: Callable
    ) -> None:
        logging.info(f"{action_name.capitalize()} offer #{trade.id}...")
        tries = 5

        for i in range(tries):
            try:
                return await action_func()
            except steam.errors.HTTPException as e:
                logging.debug(f"Error {action_name.lower()}: {e}")
                await asyncio.sleep(2**i)

        logging.warning(
            f"Failed when {action_name.lower()} offer #{trade.id} after {tries} attempts"
        )

    async def send_message(self, user: steam.User, message: str) -> None:
        if not self.options.send_messages:
            return

        if not user.is_friend():
            return

        await user.send(message)

    def is_owner(self, steam_id: str | int) -> bool:
        return str(steam_id) in self.owners

    def is_blacklisted(self, steam_id: str | int) -> bool:
        return str(steam_id) in self.blacklist

    async def accept(self, trade: steam.TradeOffer) -> None:
        await self._retry_action(trade, "accepting", trade.accept)

    async def cancel(self, trade: steam.TradeOffer) -> None:
        await self._retry_action(trade, "cancelling", trade.cancel)

    async def decline(self, trade: steam.TradeOffer) -> None:
        await self._retry_action(trade, "declining", trade.decline)

    def _get_sku(self, item: dict[str, Any]) -> str:
        sku = item["sku"]

        # if item does not have a price, but is a craft hat
        # use the craft hat sku instead
        if (
            not self.database.has_price(sku)
            and Item(item).is_craft_hat()
            and self.options.enable_craft_hats
        ):
            sku = "-100;6"

        return sku

    def _surpasses_max_stock(self, their_items: list[dict]) -> bool:
        in_offer = {"-100;6": 0}

        for i in their_items:
            item = Item(i)
            sku = get_sku(item)

            if item.is_craft_hat() and self.options.enable_craft_hats:
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
            in_stock, max_stock = self.database.get_stock(sku)

            # item does not have max_stock
            if max_stock == -1:
                continue

            if in_stock + in_offer[sku] > max_stock:
                return True

        return False

    def _valuate_items(
        self, items: list[dict], intent: str, all_skus: list[str]
    ) -> tuple[int, bool]:
        has_unpriced = False
        total = 0
        key_scrap_price = self.pricing_manager.get_key_scrap_price(intent)

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
                keys, metal = self.database.get_price(sku, intent)

            elif item.is_craft_hat() and self.options.enable_craft_hats:
                keys, metal = self.database.get_price("-100;6", intent)

            value = keys * key_scrap_price + to_scrap(metal)

            # dont need to process rest of offer since we cant know the total price
            if not value and intent == "sell":
                has_unpriced = True
                break

            logging.debug(f"{intent} {sku=} has {value=}")
            total += value

        # total scrap
        return total, has_unpriced

    def _item_values_adds_up(
        self,
        their_items: list[dict],
        our_items: list[dict],
        intent: str,
        scrap_value: int = None,
    ) -> tuple[bool, int, int]:
        logging.debug("checking if values for offer is equal...")
        their_value = 0
        our_value = 0

        for item in their_items:
            scrap_price = 0

            if intent == "buy" and scrap_value:
                scrap_price = scrap_value
            else:
                sku = self._get_sku(item)
                scrap_price = self.pricing_manager.get_scrap_price(sku, "buy")

            their_value += scrap_price

        for item in our_items:
            scrap_price = 0

            if intent == "sell" and scrap_value:
                scrap_price = scrap_value
            else:
                sku = self._get_sku(item)
                scrap_price = self.pricing_manager.get_scrap_price(sku, "sell")

            our_value += scrap_price

        return (their_value == our_value, their_value, our_value)

    async def _get_selected_items(
        self,
        partner: steam.User,
        intent: str,
        items: list[str],
        item_type: str,
        selected_inventory: list[dict],
        scrap_value: int = None,
    ) -> tuple[bool, list[dict], int] | None:
        swapped_intent = swap_intent(intent)
        key_scrap_price = self.pricing_manager.get_key_scrap_price(swapped_intent)
        all_skus = self.database.get_skus()

        item_list = items.copy()
        selected_items = []
        total_scrap_value = 0
        message = ""

        logging.debug(f"{key_scrap_price=} with {swapped_intent=} ({scrap_value=})")

        selected_inventory.reverse()

        for item in selected_inventory:
            if len(item_list) == 0:
                logging.debug("Found all items for offer")
                break

            asset_id = item["assetid"]

            if int(asset_id) == 0:
                logging.warning(f"Item {item} has no asset id, skipping")
                continue

            item_identifier = item["sku"] if item_type == "sku" else asset_id

            if item_identifier not in item_list:
                continue

            sku = self._get_sku(item)
            logging.debug(f"{item_identifier=} as {sku=} {asset_id=}")

            if not scrap_value and sku not in all_skus:
                logging.warning(f"We are not banking {sku}!")
                message = f"Sorry, I'm not banking {sku}"
                break

            if not scrap_value and not self.database.has_price(sku):
                logging.warning(f"Item {sku} does not have a price")
                message = f"Sorry, I do not have a price for {sku}"
                break

            scrap = 0

            if scrap_value:
                scrap = scrap_value
            else:
                keys, metal = self.database.get_price(sku, intent)
                scrap = key_scrap_price * keys + to_scrap(metal)

            logging.debug(f"{sku=} has {intent} {scrap=}")

            total_scrap_value += scrap
            selected_items.append(item)
            item_list.remove(item_identifier)

        logging.debug(f"{len(selected_items)=} {len(items)=}")

        if not message and len(selected_items) != len(items):
            logging.warning("Not all items were found")

            if intent == "buy":
                message = "Sorry, one or more items you requested was not found in your inventory"
            else:
                message = "Sorry, one or more items you requested has already been traded away"

        logging.debug(f"{message=}")

        # if a message was set, an error occured
        if not message:
            return (selected_items, total_scrap_value)

        await self.send_message(partner, message)

    async def _get_offer_items(
        self,
        partner: steam.User,
        intent: str,
        items: list[str],
        item_type: str,
        their_inventory: list[dict],
        our_inventory: list[dict],
        scrap_value: int = None,
    ) -> tuple[list[dict], list[dict]] | None:
        swapped_intent = swap_intent(intent)
        selected_inventory = their_inventory if intent == "buy" else our_inventory

        data = await self._get_selected_items(
            partner, intent, items, item_type, selected_inventory, scrap_value
        )

        if data is None:
            return

        items_selected, total_scrap_price = data

        if intent == "buy":
            their_items = items_selected
            our_items = []
        else:
            our_items = items_selected
            their_items = []

        key_scrap_price = self.pricing_manager.get_key_scrap_price(swapped_intent)
        currencies = CurrencyExchange(
            their_inventory, our_inventory, intent, total_scrap_price, key_scrap_price
        )
        currencies.calculate()

        if not currencies.is_possible:
            logging.warning("Currencies does not add up for trade")
            await self.send_message(
                partner,
                "Sorry, metal did not add up for this trade. Do you have enough metal?",
            )
            return

        their_metal, our_metal = currencies.get_currencies()
        logging.debug(f"currencies adds up {len(their_metal)=} {len(our_metal)=}")
        their_items += their_metal
        our_items += our_metal

        return (their_items, our_items)

    async def _create_offer(
        self,
        partner: steam.User,
        items: list[str],
        item_type: str,
        intent: str,
        token: str = None,
        message: str = None,
        scrap_value: int = None,
    ) -> tuple[steam.TradeOffer, dict[str, Any]] | None:
        partner_steam_id = str(partner.id64)
        offer_data = {}

        # get fresh instance of inventory (stores both our and theirs)
        inventory = self.inventory_manager.get_inventory_instance()
        our_inventory = self.inventory_manager.our_inventory
        their_inventory = inventory.fetch_their_inventory(partner_steam_id)
        data = await self._get_offer_items(
            partner,
            intent,
            items,
            item_type,
            their_inventory,
            our_inventory,
            scrap_value,
        )

        if data is None:
            logging.warning("Error, could not get items for offer")
            await self.send_message(partner, self.options.messages.sending_offer_error)
            return

        their_items, our_items = data
        logging.debug(f"{len(their_items)=} {len(our_items)=}")
        is_adding_up, their_value, our_value = self._item_values_adds_up(
            their_items, our_items, intent, scrap_value
        )

        if not is_adding_up:
            logging.warning("Error, values in offer did not add up!")
            await self.send_message(partner, self.options.messages.sending_offer_error)
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
            message = self.options.messages.send_offer

        return (
            steam.TradeOffer(
                message=message,
                token=token,
                sending=our_items,
                receiving=their_items,
            ),
            offer_data,
        )

    async def counter_offer(
        self,
        trade: steam.TradeOffer,
        our_items: list[dict],
        their_items: list[dict],
    ) -> None:
        our_non_pure_skus = get_non_pure_skus(our_items)
        their_non_pure_skus = get_non_pure_skus(their_items)
        intent = "sell"

        if not our_non_pure_skus and not their_non_pure_skus:
            logging.info("No non-pure items to counter offer, declining...")
            await self.decline(trade)
            return

        if our_non_pure_skus and their_non_pure_skus:
            logging.info(
                "Both sides have non-pure items, cannot counter offer, declining..."
            )
            await self.decline(trade)
            return

        if their_non_pure_skus:
            intent = "buy"

        if our_non_pure_skus:
            intent = "sell"

        skus = our_non_pure_skus + their_non_pure_skus

        logging.info(f"Counter offering {skus} to {trade.user.name}...")
        data = await self._create_offer(
            trade.user, skus, "sku", intent, message=self.options.messages.counter_offer
        )

        if data is None:
            logging.warning("Counter offer could not be created")
            return

        offer, offer_data = data
        await trade.counter(offer)
        self.client.add_offer_data(offer.id, offer_data)

    async def counter_taking_offer(
        self, trade: steam.TradeOffer, our_items: list[dict]
    ) -> None:
        await self.counter_offer(trade, our_items, [])

    async def _process_offer(
        self, trade: steam.TradeOffer, offer_data: dict[str, Any]
    ) -> None:
        partner = trade.user
        partner_id = str(partner.id64)
        their_items_amount = len(trade.receiving)
        our_items_amount = len(trade.sending)
        items_amount = their_items_amount + our_items_amount

        logging.info(f"Processing offer #{trade.id} from {partner.name}...")
        logging.info(f"Offer contains {items_amount} item(s)")

        if self.is_blacklisted(partner_id):
            logging.info(f"Offer is from blacklisted user ({partner.name})")
            await self.decline(trade)
            return

        if self.is_owner(partner_id):
            logging.info(f"Offer is from owner ({partner.name})")
            await self.accept(trade)
            return

        if self.listing_manager.is_backpack_tf_banned(partner_id):
            logging.info("User is banned on Backpack.TF")
            await self.decline(trade)
            return

        # nothing on our side
        if trade.is_gift():
            logging.info("User is trying to give items")

            if self.options.accept_gift:
                await self.accept(trade)
            else:
                logging.info("Ignoring gift offer")
            return

        # decline trade holds
        if await partner.escrow() is not None and self.options.decline_trade_hold:
            logging.info("User has a trade hold")
            await self.decline(trade)
            return

        their_items = [item_object_to_item_data(i) for i in trade.receiving]
        our_items = [item_object_to_item_data(i) for i in trade.sending]

        if self.is_arbitrage_offer(their_items, our_items):
            logging.info("Offer is an arbitrage offer")
            await self.arbitrage.process_offer(trade, their_items, our_items)
            return

        # only items on our side
        if is_only_taking_items(their_items_amount, our_items_amount):
            logging.info("User is trying to take items")
            await self.counter_taking_offer(trade, our_items)
            return

        # should never not be a two sided offer here
        if not is_two_sided_offer(their_items_amount, our_items_amount):
            logging.info("Error encountered when checking offer, ignoring...")
            return

        logging.info("Offer is valid, calculating...")

        if self._surpasses_max_stock(their_items):
            logging.warning("Trade would surpass our max stock, ignoring offer")
            return

        all_skus = self.database.get_skus()

        # we dont care about unpriced items on their side
        their_value, _ = self._valuate_items(their_items, "buy", all_skus)
        our_value, has_unpriced = self._valuate_items(our_items, "sell", all_skus)

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
            await self.accept(trade)
            return

        if self.options.counter_bad_offers:
            logging.info("Counter offering...")
            await self.counter_offer(trade, our_items, their_items)
            return

        logging.info("Ignoring offer as automatic decline is disabled")

    async def _check_stale_offer(self, trade: steam.TradeOffer) -> None:
        if not trade.is_our_offer():
            return

        if not self._is_offer_active(trade):
            return

        updated = trade.updated_at

        if updated is None:
            return

        delta = datetime.now(timezone.utc) - updated
        delta_seconds = round(delta.total_seconds(), 1)
        expire_time = self.options.cancel_sent_offers_after_seconds
        logging.debug(f"{trade.id=} updated {delta_seconds=} ago {expire_time=}")

        if delta_seconds < expire_time:
            logging.debug(f"{trade.id=} not stale")
            return

        logging.info(
            f"Offer #{trade.id} is stale, no action past {delta_seconds} seconds"
        )
        await self.cancel(trade)

    async def process_offer(self, trade: steam.TradeOffer) -> dict[str, Any]:
        offer_data = {}
        await self._process_offer(trade, offer_data)

        return offer_data

    def is_arbitrage_offer(
        self, their_items: list[dict], our_items: list[dict]
    ) -> bool:
        if not self.options.enable_arbitrage:
            return False

        return self.arbitrage.is_arbitrage_offer(their_items, our_items)

    async def send_offer(
        self,
        partner: steam.User,
        intent: str,
        items: list[str],
        item_type: str,
        token: str = None,
        scrap_value: int = None,
    ) -> int:
        assert intent in ["buy", "sell"]
        assert item_type in ["sku", "asset_id"]

        logging.debug(
            f"Sending offer to {partner.name} {intent=} {items=} {item_type=}"
        )
        steam_id = str(partner.id64)

        if self.is_blacklisted(steam_id):
            logging.info("User is blacklisted, not sending offer")
            await self.send_message(partner, self.options.messages.user_blacklisted)
            return 0

        if self.listing_manager.is_backpack_tf_banned(steam_id):
            logging.info("User is banned on Backpack.TF, not sending offer")
            await self.send_message(partner, self.options.messages.user_banned)
            return 0

        await self.client.bot_is_ready_and_prices_updated()
        data = await self._create_offer(
            partner, items, item_type, intent, token=token, scrap_value=scrap_value
        )

        if data is None:
            return 0

        offer, offer_data = data
        logging.info(f"Sending offer to {partner.name}...")

        await self.send_message(partner, self.options.messages.sending_offer)

        try:
            await partner.send(trade=offer)
        except steam.errors.HTTPException:
            logging.warning(f"There was an error while sending offer to {partner.name}")
            await self.send_message(partner, self.options.messages.sending_offer_error)
            return 0

        self.client.add_offer_data(offer.id, offer_data)
        logging.info(f"Sent offer for {items} to {partner.name}")

        return offer.id

    async def send_offer_by_trade_url(
        self,
        trade_url: str,
        intent: str,
        items: list[str],
        item_type: str,
        scrap_value: int = None,
    ) -> int:
        steam_id = get_steam_id_from_trade_url(trade_url)
        token = get_token_from_trade_url(trade_url)
        partner = await self.client.fetch_user(int(steam_id))

        if not partner:
            logging.warning(f"Could not find user {steam_id}")
            return -1

        logging.debug(f"{partner.name} {intent=} has {steam_id=} {token=}")

        return await self.send_offer(
            partner, intent, items, item_type, token, scrap_value
        )

    async def process_offer_state(
        self, trade: steam.TradeOffer, offer_data: dict[str, Any]
    ) -> None:
        steam_id = str(trade.user.id64)
        offer_id = str(trade.id)
        state_name = trade.state.name.lower()
        was_accepted = trade.state == steam.TradeOfferState.Accepted

        logging.info(f"Offer #{offer_id} with {trade.user.name} was {state_name}")

        if trade.state == steam.TradeOfferState.Active:
            return

        if trade.state != steam.TradeOfferState.Accepted:
            await self.send_message(trade.user, f"Your offer was {state_name}")

        if offer_id in self.client.pending_site_offers:
            self.client.ws_manager.remove_user_from_queue(steam_id)
            await self.client.ws_manager._send_ws_message(
                {
                    "success": was_accepted,
                    "steam_id": steam_id,
                    "message_type": "trade_status",
                    "offer_state": state_name,
                    "message": f"Offer was {state_name}!",
                }
            )
            del self.client.pending_site_offers[offer_id]

        if trade.user.id64 in self.client.pending_offer_users:
            self.client.pending_offer_users.remove(trade.user.id64)

        if self.options.enable_discord:
            await self.discord_manager.send_offer_state_changed(
                trade, trade.receiving, trade.sending
            )

        if self.options.enable_arbitrage:
            await self.arbitrage.process_offer_state(
                trade, trade.receiving, trade.sending
            )

        if not was_accepted:
            return

        their_items = [item_object_to_item_data(i) for i in trade.receiving]
        our_items = [item_object_to_item_data(i) for i in trade.sending]

        await self.send_message(trade.user, self.options.messages.offer_accepted)

        offer_data |= {
            "offer_id": offer_id,
            "partner_id": str(trade.user.id64),
            "partner_name": trade.user.name,
            "message": trade.message,
            "their_items": their_items,
            "our_items": our_items,
            "key_prices": self.pricing_manager.get_key_prices(),
            "state": trade.state.name.lower(),
            "timestamp": time.time(),
        }

        self.database.insert_trade(offer_data)

        # error, need to refetch inventory
        if None in their_items or None in our_items:
            logging.warning("Error converting items after offer was accepted")
            self.inventory_manager.fetch_our_inventory()
            self.inventory_manager.set_inventory_changed()
            return

        logging.debug("Getting receipt...")

        receipt = await trade.receipt()
        await self.client.inventory_manager.update_inventory_with_receipt(
            their_items, our_items, receipt
        )

        logging.debug("Inventory was updated after receipt")

    async def run(self) -> None:
        # checks for stale offers
        while True:
            logging.debug("Checking for stale offers...")

            for trade in self.client.trades:
                await self._check_stale_offer(trade)

            await asyncio.sleep(15)
