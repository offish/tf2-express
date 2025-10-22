import logging

import discord
from steam import TradeOffer

from .base_manager import BaseManager


class DiscordManager(BaseManager, discord.Client):
    def setup(self) -> None:
        if not self.options.enable_discord:
            return

        intents = discord.Intents.default()
        intents.message_content = True

        self.token = self.options.discord_token
        self.channel = None
        self.owner_ids = [int(owner) for owner in self.options.discord_owner_ids]

        discord.Client.__init__(self, intents=intents)

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

    async def send_offer_state_changed(
        self, trade: TradeOffer, their_items: list[dict], our_items: list[dict]
    ) -> None:
        del their_items, our_items

        message = f"Trade offer {trade.id} changed state to {trade.state}."
        await self.channel.send(message)

    async def run(self) -> None:
        channel_id = self.options.discord_channel_id
        self.channel = await self.fetch_channel(channel_id)

        if self.channel is None:
            raise ValueError(f"Discord channel with ID {channel_id} not found.")

        await self.start(self.token)
