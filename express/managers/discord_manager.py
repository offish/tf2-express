import logging

import discord
from steam import TradeOffer

from .base_manager import BaseManager


class DiscordManager(BaseManager, discord.Client):
    async def setup(self) -> None:
        if not self.options.discord.enable:
            return

        intents = discord.Intents.default()
        intents.message_content = True

        self.token = self.options.discord.token
        self.channel = None
        self.owner_ids = [int(owner) for owner in self.options.discord.owner_ids]

        discord.Client.__init__(
            self, intents=intents, activity=discord.Game(name="tf2-express")
        )

    def is_owner(self, user_id: int) -> bool:
        return user_id in self.owner_ids

    async def on_ready(self):
        logging.info(f"Logged on as {self.user}!")

    async def on_message(self, message):
        if message.author == self.user:
            return

        if not self.is_owner(message.author.id):
            return

        logging.info(f"Message from {message.author}: {message.content}")

        if message.content.startswith("quicksell") and self.options.arbitrage.quicksell:
            await message.channel.send("Going to quicksell all items")
            await self.client.arbitrage_manager.quicksell([])
            return

        await message.channel.send("Invalid command")

    async def send_offer_state_changed(
        self, trade: TradeOffer, their_items: list[dict], our_items: list[dict]
    ) -> None:
        del their_items, our_items

        if not self.channel:
            channel_id = self.options.discord.channel_id
            self.channel = self.get_channel(channel_id)

        message = f"Trade offer {trade.id} changed state to {trade.state}."
        await self.channel.send(message)

    async def run(self) -> None:
        await self.start(self.token)
