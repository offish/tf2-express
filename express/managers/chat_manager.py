import logging
import os

from litellm import completion
from steam import Channel, Message, User

from ..command import parse_command, try_parse_sku
from ..utils import swap_intent
from .base_manager import BaseManager


class LLM:
    def __init__(self, api_key: str, model: str) -> None:
        provider = model.split("/")[0]
        provider_key = f"{provider}_API_KEY".upper()
        os.environ[provider_key] = api_key
        self.model = model

    def prompt(self, system_prompt: str, text: str) -> str:
        response = completion(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
        )
        return response.choices[0].message.content


class ChatManager(BaseManager):
    async def setup(self) -> None:
        self.arbitrage = self.client.arbitrage_manager
        self.trade = self.client.trade_manager

        if not self.options.chat.llm_responses:
            return

        api_key = self.options.chat.llm_api_key
        model = self.options.chat.llm_model

        self.system_prompt = self.options.messages.system_prompt
        self.llm = LLM(api_key, model)

    def is_owner(self, message: Message) -> bool:
        return str(message.author.id64) in self.options.owners

    def get_items(self, message: str, command: str) -> list[str]:
        items = message.replace(command, "").split(",")
        return [item.strip() for item in items]

    async def send_message(self, recipient: User | Channel, message: str) -> None:
        if not self.options.chat.send_messages:
            logging.debug(f"sending messages is disabled, not sending {message}")
            return

        await recipient.send(message)

    async def process_message(self, message: Message, msg: str) -> None:
        if msg == "help":
            return await self.handle_help_command(message)

        if msg.startswith("buy") or msg.startswith("sell"):
            return await self.handle_buy_sell_command(message, msg)

        if (
            msg.startswith("price")
            or msg.startswith("check")
            or msg.startswith("stock")
        ):
            return await self.handle_price_command(message, msg)

        if msg.startswith("quickbuy") and self.is_owner(message):
            items = self.get_items(msg, "quickbuy")
            content = f"Processing quickbuy for items: {items}"
            await self.send_message(message.channel, content)
            return await self.arbitrage.quickbuy(items)

        if msg.startswith("quicksell") and self.is_owner(message):
            content = "Going to quicksell all items"
            await self.send_message(message.channel, content)
            return await self.arbitrage.quicksell([])

        if not self.options.chat.llm_responses:
            return await self.send_message(
                message.channel, self.options.messages.invalid_command
            )

        response = self.llm.prompt(self.system_prompt, msg)
        await self.send_message(message.channel, response)

    async def handle_help_command(self, message: Message) -> None:
        content = self.options.messages.help_command
        await self.send_message(message.channel, content)

    async def handle_buy_sell_command(self, message: Message, msg: str) -> None:
        data = parse_command(msg)

        if data is None:
            content = self.options.messages.invalid_command
            return await self.send_message(message.channel, content)

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
                content = f"Error. No item with name '{item_name}'"
                return await self.send_message(message.channel, content)

            sku = item["sku"]

        logging.info(
            f"{message.author.name} wants to {intent} {amount} of {identifier}"
        )

        if amount < 1:
            content = "You must trade at least 1 item"
            await self.send_message(message.channel, content)
            return

        if amount > 10:
            content = "You can only trade up to 10 items at a time"
            await self.send_message(message.channel, content)
            amount = 10

        # swap intents
        intent = swap_intent(intent)

        content = f"Processing your trade for {amount} of {sku}..."
        await self.send_message(message.channel, content)

        if message.author.id64 in self.client.pending_offer_users:
            content = self.options.messages.user_pending_offer
            return await self.send_message(message.channel, content)

        items = [sku] * amount
        offer_id = await self.trade.send_offer(message.author, intent, items, "sku")

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
                content = f"Error. No item with name '{item_name}'"
                return await self.send_message(message.channel, content)

            sku = item["sku"]

        logging.info(f"{message.author.name} wants to check price for {sku}")

        data = self.client.pricing_manager.get_item(sku)

        if not data:
            content = "Could not find information for this item"
            return await self.send_message(message.channel, content)

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

        content = self.options.messages.price_command.format(
            sku=sku,
            buy_keys=buy_keys,
            buy_metal=buy_metal,
            sell_keys=sell_keys,
            sell_metal=sell_metal,
            in_stock=in_stock,
            max_stock=max_stock,
        )
        await self.send_message(message.channel, content)
