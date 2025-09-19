import logging

from steam import Message

from ..command import parse_command
from ..utils import swap_intent
from .base_manager import BaseManager


class ChatManager(BaseManager):
    async def process_message(self, message: Message, msg: str) -> None:
        if msg.startswith("buy") or msg.startswith("sell"):
            await self.handle_buy_sell_command(message, msg)
            return

        if (
            msg.startswith("price")
            or msg.startswith("check")
            or msg.startswith("stock")
        ):
            await self.handle_price_command(message, msg)
            return

        await message.channel.send("Invalid command")

    async def handle_buy_sell_command(self, message: Message, msg: str) -> None:
        data = parse_command(msg)

        if data is None:
            await message.channel.send("Could not parse your message")
            return

        # parse message
        intent = data["intent"]
        amount = data["amount"]
        sku = data["sku"]

        logging.info(f"{message.author.name} wants to {intent} {amount} of {sku}")

        if amount < 1:
            await message.channel.send("You must trade at least 1 item")
            return

        if amount > 10:
            await message.channel.send("You can only trade up to 10 items at a time")
            amount = 10

        # swap intents
        intent = swap_intent(intent)

        await message.channel.send(f"Processing your trade for {amount} of {sku}...")

        if message.author.id64 in self.client.pending_offer_users:
            await message.channel.send("You appear to have a pending offer already")
            return

        offer_id = await self.client.trade_manager.send_offer(
            message.author, intent, [sku] * amount, "sku"
        )

        if offer_id:
            self.client.pending_offer_users.add(message.author.id64)

    async def handle_price_command(self, message: Message, msg: str) -> None:
        parts = msg.split("_")

        sku_parts = parts[1:]
        sku = ";".join(sku_parts)

        logging.info(f"{message.author.name} wants to check price for {sku}")

        data = self.client.pricing_manager.get_item(sku)

        if not data:
            await message.channel.send("Could not find information for this item")
            return

        buy_price: dict = data["buy"]
        sell_price: dict = data["sell"]
        buy_keys = buy_price.get("keys", 0)
        buy_metal = buy_price.get("metal", 0.0)
        sell_keys = sell_price.get("keys", 0)
        sell_metal = sell_price.get("metal", 0.0)
        in_stock = data.get("in_stock", 0)
        max_stock = data.get("max_stock", -1)

        if max_stock == -1:
            max_stock = "∞"

        text = (
            f"I'm buying {sku} for {buy_keys} keys and {buy_metal} ref\n"
            + f"and selling for {sell_keys} keys and {sell_metal} ref\n"
            + f"I currently have {in_stock} in stock, my max is {max_stock}\n"
        )

        await message.channel.send(text)
