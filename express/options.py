from dataclasses import dataclass, field

from .messages import Messages


@dataclass
class BackpackTFOptions:
    enable: bool = False
    access_token: str = ""
    api_key: str = ""
    user_agent: str = "Listing goin' up!"
    check_bans: bool = False
    sku_in_listing_details: bool = False  # disable for item name instead


@dataclass
class InventoryOptions:
    provider: str = "steamcommunity"  # steamsupply, expressload, etc.
    api_key: str = ""  # api key for the inventory provider
    retries: int = 5


@dataclass
class OffersOptions:
    enable_craft_hats: bool = False  # enable random craft hats
    accept_donations: bool = False
    counter_wrong_values: bool = False  # counter offers with wrong values
    decline_trade_hold: bool = True
    cancel_old_sent: bool = False  # cancel offers sent by us after some time
    cancel_sent_after_seconds: int = 300  # auto cancel has to be enabled
    save_trades: bool = True  # save trade offers in database


@dataclass
class ChatOptions:
    enable: bool = True
    llm_responses: bool = False  #  for chat commands which are not recognized
    llm_model: str = "groq/llama-3.3-70b-versatile"
    llm_api_key: str = ""


@dataclass
class DiscordOptions:
    enable: bool = False
    token: str = ""
    channel_id: str = ""
    owner_ids: list[str] = field(default_factory=list)


@dataclass
class ArbitrageOptions:
    enable: bool = False
    minimum_profit: float = 0.11
    check_interval_seconds: int = 300
    stn_api_key: str = ""
    quicksell: bool = False
    quickbuy: bool = False
    quicksell_on_startup: bool = False


@dataclass
class ExpressTFOptions:
    enable: bool = False
    uri: str = ""
    token: str = ""


@dataclass
class Options:
    username: str
    messages: Messages
    backpack_tf: BackpackTFOptions
    inventory: InventoryOptions
    offers: OffersOptions
    discord: DiscordOptions
    arbitrage: ArbitrageOptions
    chat: ChatOptions
    express_tf: ExpressTFOptions
    price_provider: str = "pricedb"
    database_provider: str = "mongodb"
    check_updates: bool = True
    groups: list[int] = field(default_factory=list)
    owners: list[str] = field(default_factory=list)  # list of owner steam id64
    blacklist: list[str] = field(default_factory=list)  # list of blacklisted steam id64
    client_options: dict = field(default_factory=dict)  # client options for steam.py
