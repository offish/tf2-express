import asyncio
import atexit
import logging
import time

import steam
from tf2_utils import to_scrap

from .databases.database_providers import get_database_provider
from .exceptions import MissingAPIKey, MissingBackpackTFToken, OptionsError
from .managers.api_manager import APIManager
from .managers.arbitrage_manager import ArbitrageManager
from .managers.base_manager import BaseManager
from .managers.chat_manager import ChatManager
from .managers.copy_trade_manager import CopyTradeManager
from .managers.discord_manager import DiscordManager
from .managers.inventory_manager import InventoryManager
from .managers.listing_manager import ListingManager
from .managers.pricing_manager import PricingManager
from .managers.site_manager import SiteManager
from .managers.trade_manager import TradeManager
from .options import Options


class Express(steam.Client):
    def __init__(self, options: Options) -> None:
        self.started_at = time.time()

        self.options = options
        self.options_check()
        self.are_prices_updated = False
        self.pending_offer_users = set()
        self.pending_site_offers = {}
        self.processed_offers = {}
        self.is_bot_ready = False

        # managers
        self.copy_trade_manager = None
        self.inventory_manager = None
        self.arbitrage_manager = None
        self.listing_manager = None
        self.pricing_manager = None
        self.discord_manager = None
        self.trade_manager = None
        self.chat_manager = None
        self.site_manager = None
        self.api_manager = None

        super().__init__(
            app=steam.TF2,
            state=steam.PersonaState.LookingToTrade,
            language=steam.Language.English,
            **options.client_options,
        )

        self.database = get_database_provider(
            options.database_provider, options.username
        )

    async def setup(self) -> None:
        # set managers
        self.inventory_manager = InventoryManager(self)
        self.pricing_manager = PricingManager(self)
        self.trade_manager = TradeManager(self)
        self.chat_manager = ChatManager(self)
        self.api_manager = APIManager(self)

        self.managers: list[BaseManager] = [
            self.inventory_manager,
            self.pricing_manager,
            self.trade_manager,
            self.chat_manager,
            self.api_manager,
        ]

        # add additional managers based on options
        self.append_additional_managers()

        for manager in self.managers:
            await manager.setup()

        # delete listings on exit and disconnect from websocket
        atexit.register(self.cleanup)

        # set inventory
        await self.inventory_manager.fetch_our_inventory()

        # get inventory stock and update database
        stock = self.inventory_manager.get_stock()
        self.database.update_stock(stock)

        # bot is now ready (other events can fire)
        self.is_bot_ready = True

        # we dont want to listen for price updates when copy trading
        if not self.options.copy_trade.enable:
            asyncio.create_task(self.pricing_manager.provider.listen())

        # start managers
        for manager in self.managers:
            if self.should_start_task(manager.name):
                asyncio.create_task(manager.run())

    def should_start_task(self, name: str) -> bool:
        if name == "trademanager" and not self.options.offers.cancel_sent:
            return False

        if name == "arbitragemanager" and not self.options.arbitrage.look_for_deals:
            return False

        return True

    def options_check(self) -> None:
        if (
            self.options.backpack_tf.enable
            and not self.options.backpack_tf.access_token
        ):
            raise MissingBackpackTFToken("Backpack.TF token is required for listing")

        if self.options.backpack_tf.check_bans and not self.options.backpack_tf.api_key:
            raise MissingAPIKey("Backpack.TF API key is needed for ban checks")

        if self.options.discord.enable and not self.options.discord.owner_ids:
            raise OptionsError("Discord bot must have at least 1 owner")

        if self.options.discord.enable and not self.options.discord.token:
            raise OptionsError("Discord bot token is required")

        if self.options.discord.enable and not self.options.discord.channel_id:
            raise OptionsError("Discord channel ID is required")

        if self.options.arbitrage.enable and not self.options.arbitrage.stn_api_key:
            raise MissingAPIKey("STN.tf API key is needed for arbitrage")

        if self.options.copy_trade.enable and not self.options.copy_trade.steam_id:
            raise OptionsError("A Steam ID is required to copy trade")

    def append_additional_managers(self) -> None:
        if self.options.backpack_tf.enable:
            self.listing_manager = ListingManager(self)
            self.managers.append(self.listing_manager)

        if self.options.discord.enable:
            self.discord_manager = DiscordManager(self)
            self.managers.append(self.discord_manager)

        if self.options.arbitrage.enable:
            self.arbitrage_manager = ArbitrageManager(self)
            self.managers.append(self.arbitrage_manager)

        if self.options.copy_trade.enable:
            self.copy_trade_manager = CopyTradeManager(self)
            self.managers.append(self.copy_trade_manager)

        if self.options.express_tf.enable:
            self.site_manager = SiteManager(self)
            self.managers.append(self.site_manager)

    async def bot_is_ready(self) -> None:
        while not self.is_bot_ready:
            await asyncio.sleep(1)

    async def bot_is_ready_and_prices_updated(self) -> None:
        await self.bot_is_ready()

        while not self.are_prices_updated:
            await asyncio.sleep(1)

    async def on_ready(self) -> None:
        logging.info(f"Logged into Steam as {self.username}")

        await self.join_groups()
        await self.setup()

    async def on_message(self, message: steam.Message) -> None:
        # dont process messages if chat is disabled
        if not self.options.chat.enable:
            return

        # ignore our own messages
        if message.author == self.user:
            return

        # ignore trade offer messages
        if "tradeoffer" in message.content:
            return

        await self.bot_is_ready_and_prices_updated()
        msg = message.content.lower()
        logging.info(f"{message.author.name} sent: {msg}")

        await self.chat_manager.process_message(message, msg)

    async def on_invite(self, invite: steam.Invite) -> None:
        if not isinstance(invite, steam.UserInvite):
            return

        if not self.options.chat.accept_friends:
            logging.info(f"Ignoring friend invite from {invite.author.name}")
            return

        # accept the friend invite
        await invite.accept()

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

    def get_key_price(self, intent: str) -> int:
        item = self.database.get_item("5021;6")
        metal = item[intent]["metal"]
        return to_scrap(metal)

    def add_offer_data(self, offer_id: int | str, offer_data: dict) -> None:
        self.processed_offers[str(offer_id)] = offer_data

    async def join_groups(self) -> None:
        groups = [103582791463210863, *self.options.groups]

        for i in groups:
            group = await self.fetch_clan(i)

            if group:
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

    def cleanup(self) -> None:
        for manager in self.managers:
            asyncio.run(manager.close())

    @property
    def steam_id(self) -> str:
        return str(self.user.id64)
