import asyncio
import logging

import steam

from .database import Database
from .managers.chat_manager import ChatManager
from .managers.inventory_manager import InventoryManager
from .managers.listing_manager import ListingManager
from .managers.pricing_manager import PricingManager
from .managers.trade_manager import TradeManager
from .managers.websocket_manager import WebSocketManager
from .options import FRIEND_ACCEPT_MESSAGE, Options


class Express(steam.Client):
    def __init__(self, options: Options) -> None:
        self.group = None
        self.options = options
        self.are_prices_updated = False
        self.pending_offer_users = set()
        self.pending_site_offers = {}
        self.processed_offers = {}
        self._bot_is_ready = False

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
        self._bot_is_ready = True

        asyncio.create_task(self.pricing_manager.pricer.listen())
        asyncio.create_task(self.pricing_manager.run())

        if self.options.use_backpack_tf:
            asyncio.create_task(self.listing_manager.run())

        if self.options.is_express_tf_bot:
            asyncio.create_task(self.ws_manager.listen())

        if self.options.auto_cancel_sent_offers:
            asyncio.create_task(self.trade_manager.run())

    async def bot_is_ready(self) -> None:
        while not self._bot_is_ready:
            await asyncio.sleep(1)

    async def bot_is_ready_and_prices_updated(self) -> None:
        await self.bot_is_ready()

        while not self.are_prices_updated:
            await asyncio.sleep(1)

    def add_offer_data(self, offer_id: int | str, offer_data: dict) -> None:
        if isinstance(offer_id, int):
            offer_id = str(offer_id)

        self.processed_offers[offer_id] = offer_data

    async def on_ready(self) -> None:
        logging.info(f"Logged into Steam as {self.username}")

        await self.join_groups()
        await self.setup()

    async def on_message(self, message: steam.Message) -> None:
        # ignore our own messages
        if message.author == self.user:
            return

        # user has sent a trade offer
        if "tradeoffer" in message.content:
            return

        await self.bot_is_ready_and_prices_updated()
        msg = message.content.lower()
        logging.info(f"{message.author.name} sent: {msg}")

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

        await self.bot_is_ready_and_prices_updated()
        offer_data = await self.trade_manager.process_offer(trade)

        if not offer_data:
            return

        self.add_offer_data(trade.id, offer_data)

    async def on_trade_update(self, _, trade: steam.TradeOffer) -> None:
        await self.bot_is_ready()

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
