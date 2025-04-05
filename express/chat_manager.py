import logging
from typing import TYPE_CHECKING

from steam import Message

from .command import parse_command
from .utils import swap_intent

if TYPE_CHECKING:
    from .express import Express


class ChatManager:
    def __init__(self, client: "Express") -> None:
        self.client = client

    async def process_message(self, message: Message, msg: str) -> None:
        data = parse_command(msg)

        if data is None:
            await message.channel.send("Could not parse your message")
            return

        # parse message
        intent = data["intent"]
        amount = 1  # amounts other than 1 are not supported yet
        sku = data["sku"]

        logging.info(f"{message.author.name} wants to {intent} {amount} of {sku}")

        # swap intents
        intent = swap_intent(intent)

        await message.channel.send(f"Processing your trade for {amount} of {sku}...")

        if message.author.id64 in self.client.pending_offer_users:
            await message.channel.send("You appear to have a pending offer already")
            return

        offer_id = await self.client.trade_manager.send_offer(
            message.author, intent, [sku], "sku"
        )

        if offer_id:
            self.client.pending_offer_users.add(message.author.id64)
