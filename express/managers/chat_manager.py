import logging

from steam import Message

from ..command import parse_command, try_parse_sku
from ..options import HELP_COMMAND, PRICE_COMMAND
from ..utils import swap_intent
from .ai_manager import AIManager
from .base_manager import BaseManager


class ChatManager(BaseManager):
    def setup(self) -> None:
        if not self.options.use_ai_chat_responses:
            return

        api_key = self.options.groq_api_key
        self.ai_manager = AIManager(api_key)

    async def process_message(self, message: Message, msg: str) -> None:
        if msg == "help":
            await self.handle_help_command(message)
            return

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

        if not self.options.use_ai_chat_responses:
            await message.channel.send("Invalid command")
            return

        response = self.ai_manager.prompt(msg)
        await message.channel.send(response)

    async def handle_help_command(self, message: Message) -> None:
        await message.channel.send(HELP_COMMAND)

    async def handle_buy_sell_command(self, message: Message, msg: str) -> None:
        data = parse_command(msg)

        if data is None:
            await message.channel.send("Error. Could not parse your message")
            return

        # parse message
        intent = data["intent"]
        amount = data["amount"]
        identifier = data["sku"] if data["is_sku"] else data["item_name"]
        sku = ""

        if data["is_sku"]:
            sku = data["sku"]
        else:
            item_name = data["item_name"]
            item = self.database.find_item_by_name(item_name)

            if item is None:
                await message.channel.send(f"Error. No item with name '{item_name}'")
                return

            sku = item["sku"]

        logging.info(
            f"{message.author.name} wants to {intent} {amount} of {identifier}"
        )

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
        sku = ""
        parts = msg.split("_")
        sku_parts = parts[1:]
        is_sku = try_parse_sku(sku_parts)

        if is_sku:
            sku = ";".join(sku_parts)
        else:
            item_name = "_".join(sku_parts)
            item = self.database.find_item_by_name(item_name)

            if item is None:
                await message.channel.send(f"Error. No item with name '{item_name}'")
                return

            sku = item["sku"]

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

        text = PRICE_COMMAND.format(
            sku=sku,
            buy_keys=buy_keys,
            buy_metal=buy_metal,
            sell_keys=sell_keys,
            sell_metal=sell_metal,
            in_stock=in_stock,
            max_stock=max_stock,
        )

        await message.channel.send(text)
