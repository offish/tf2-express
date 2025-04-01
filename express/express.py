import asyncio
import logging

import steam

from .chat_manager import ChatManager
from .database import Database
from .inventory_manager import InventoryManager
from .listing_manager import ListingManager
from .options import (
    FRIEND_ACCEPT_MESSAGE,
    Options,
)
from .pricing_manager import PricingManager
from .trade_manager import TradeManager
from .websocket_manager import WebSocketManager


class Express(steam.Client):
    def __init__(self, options: Options) -> None:
        self.group = None
        self.options = options
        self.bot_is_ready = False
        self.are_prices_updated = False
        self.pending_offer_users = set()
        self.pending_site_offers = {}
        self.processed_offers = {}

        self.inventory_manager = None
        self.listing_manager = None
        self.pricing_manager = None
        self.trade_manager = None
        self.chat_manager = None
        self.ws_manager = None

        super().__init__(
            app=steam.TF2,
            state=steam.PersonaState.LookingToTrade,
            language=steam.Language.English,
            **options.client_options,
        )

        self.database = Database(options.username)

    async def setup(self) -> None:
        # set steam api key
        self.http.api_key = self._api_key

        # set inventory
        self.inventory_manager = InventoryManager(self)
        self.inventory_manager.get_inventory_instance()
        self.inventory_manager.fetch_our_inventory()

        # set managers
        self.listing_manager = ListingManager(
            self, self.options.backpack_tf_token, str(self.user.id64)
        )
        self.pricing_manager = PricingManager(self)
        self.trade_manager = TradeManager(self)
        self.chat_manager = ChatManager(self)
        self.ws_manager = WebSocketManager(self)

        # get inventory stock and update database
        stock = self.inventory_manager.get_stock()
        self.database.update_stock(stock)

        # we are now ready (other events can now fire)
        self.bot_is_ready = True
        asyncio.create_task(self.pricing_manager.pricing_provider.listen())

        if self.options.use_backpack_tf:
            self.listing_manager.listen()

        if self.options.fetch_prices_on_startup:
            asyncio.create_task(self.pricing_manager.listen_for_pricelist_changes())

        if self.options.is_express_tf_bot:
            asyncio.create_task(self.ws_manager.listen())

        if self.options.expire_sent_offers:
            asyncio.create_task(self.trade_manager.decline_our_stale_offers())

        # after prices are updated we can create listings
        # if self.options.use_backpack_tf:
        #     self.listing_manager.create_listings()

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

        await self.chat_manager.process_message(message, msg)

    async def on_invite(self, invite: steam.Invite) -> None:
        if not isinstance(invite, steam.UserInvite):
            return

        # accept the friend invite
        await invite.accept()

    async def on_friend_add(self, friend: steam.Friend) -> None:
        message = FRIEND_ACCEPT_MESSAGE.format(username=friend.name)
        await friend.send(message)

    async def on_trade(self, trade: steam.TradeOffer) -> None:
        if trade.is_our_offer():
            return

        offer_data = await self.trade_manager.process_offer(trade)

        if not offer_data:
            return

        self.processed_offers[trade.id] = offer_data

    async def on_trade_update(self, _, trade: steam.TradeOffer) -> None:
        offer_id = str(trade.id)
        offer_data = self.processed_offers.get(offer_id, {})

        await self.trade_manager.process_offer_state(trade, offer_data)

        if offer_id in self.processed_offers:
            del self.processed_offers[offer_id]

    async def join_groups(self) -> None:
        group_id = 103582791463210868
        groups = [group_id, 103582791463210863, *self.options.groups]

        for i in groups:
            group = await self.fetch_clan(i)

            if group is None:
                continue

            if group.id64 == group_id:
                self.group = group

            await group.join()

    def start(
        self,
        username: str,
        password: str,
        identity_secret: str,
        shared_secret: str,
        api_key: str,
        **kwargs,
    ) -> None:
        del kwargs

        self._api_key = api_key

        self.run(
            username=username,
            password=password,
            identity_secret=identity_secret,
            shared_secret=shared_secret,
            debug=False,
        )
