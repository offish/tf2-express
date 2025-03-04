import logging

import steam
from tf2_utils import get_steam_id_from_trade_url, get_token_from_trade_url

from .client import ExpressClient
from .options import Options


class Express(ExpressClient):
    def __init__(self, options: Options) -> None:
        super().__init__(options)

    async def on_ready(self) -> None:
        logging.info(f"Logged into Steam as {self.username}")

        logging.info("Fetched our inventory")

        await self.join_groups()
        await self.setup()

    async def on_message(self, message: steam.Message) -> None:
        # ignore our own messages
        if message.author == self.user:
            return

        # user has sent a trade offer
        if "tradeoffer" in message.content:
            return

        msg = message.content.lower()

        logging.info(f"{message.author.name} sent: {msg}")

        # only care about buy and sell messages
        if not msg.startswith("buy") and not msg.startswith("sell"):
            await message.channel.send("Invalid command")
            return

        await self.process_message(message, msg)

    async def on_invite(self, invite: steam.Invite) -> None:
        if not isinstance(invite, steam.UserInvite):
            return

        # accept the friend invite
        await invite.accept()

    async def on_friend_add(self, friend: steam.Friend) -> None:
        message = self._friend_accept_message.format(username=friend.name)
        await friend.send(message)

    async def on_trade(self, trade: steam.TradeOffer) -> None:
        if trade.is_our_offer():
            return

        offer_data = await self.process_offer(trade)

        if not offer_data:
            return

        self._processed_offers[trade.id] = offer_data

    async def on_trade_update(self, _, trade: steam.TradeOffer) -> None:
        offer_id = trade.id
        offer_data = self._processed_offers.get(offer_id, {})

        await self.process_offer_state(trade, offer_data)

        if offer_id in self._processed_offers:
            del self._processed_offers[offer_id]

    async def send_offer_by_trade_url(
        self, trade_url: str, intent: str, sku: str
    ) -> int:
        steam_id = get_steam_id_from_trade_url(trade_url)
        token = get_token_from_trade_url(trade_url)
        partner = self.get_user(int(steam_id))

        return await self.send_offer(partner, intent, sku, token)

    def start(
        self,
        username: str,
        password: str,
        identity_secret: str,
        shared_secret: str,
        **kwargs,
    ) -> None:
        del kwargs

        self.run(
            username=username,
            password=password,
            identity_secret=identity_secret,
            shared_secret=shared_secret,
            debug=False,
        )
