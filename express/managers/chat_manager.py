import logging

from steam import Message
from tf2_utils import swap_intent

from ..command import clamp_amount, parse_command
from .base_manager import BaseManager


class ChatManager(BaseManager):
    async def setup(self) -> None:
        self.trade = self.client.trade_manager

    def get_sku(self, data: dict) -> str | None:
        if data["is_sku"]:
            return data["sku"]

        item_name = data["item_name"]
        item = self.database.find_item_by_name(item_name)

        if item:
            return item["sku"]

    async def handle_buy_sell_command(self, message: Message, msg: str) -> None:
        steam_id = message.author.id64

        # offer already pending
        if steam_id in self.client.pending_offer_users:
            return

        data = parse_command(msg)

        if data is None:
            return

        sku = self.get_sku(data)

        if sku is None:
            return

        intent = data["intent"]
        amount = data["amount"]
        identifier = data["sku"] if data["is_sku"] else data["item_name"]
        logging.info(f"{steam_id} wants to {intent} {amount} of {identifier}")

        # swap intents
        intent = swap_intent(intent)
        amount = clamp_amount(amount)

        items = [sku] * amount
        offer_id = await self.trade.send_offer(message.author, intent, items, "sku")

        if offer_id:
            self.client.pending_offer_users.add(steam_id)

    async def process_message(self, message: Message, msg: str) -> None:
        if msg.startswith("buy") or msg.startswith("sell"):
            await self.handle_buy_sell_command(message, msg)
