from dataclasses import dataclass, field


@dataclass
class Messages:
    send_offer: str = ""
    counter_offer: str = ""


@dataclass
class BackpackTFOptions:
    enable: bool = False
    access_token: str = ""
    api_key: str = ""
    user_agent: str = "Listing goin' up!"
    check_bans: bool = False
    use_item_name: bool = True  # false for sku instead


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
    cancel_sent: bool = False  # cancel offers sent by us after some time
    cancel_sent_after_seconds: int = 300  # auto cancel has to be enabled
    save_trades: bool = True  # save trade offers in database


@dataclass
class ChatOptions:
    enable: bool = False  # wheter to process chats
    accept_friends: bool = False  # auto accept friend requests


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
    stn_api_key: str = ""
    look_for_deals: bool = False


@dataclass
class CopyTradeOptions:
    enable: bool = False
    steam_id: str = ""  # steam id to copy trade


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
    chat: ChatOptions
    arbitrage: ArbitrageOptions
    copy_trade: CopyTradeOptions
    express_tf: ExpressTFOptions
    price_provider: str = "pricedb"
    database_provider: str = "mongodb"
    check_updates: bool = True
    groups: list[int] = field(default_factory=list)
    owners: list[str] = field(default_factory=list)  # list of owner steam id64
    blacklist: list[str] = field(default_factory=list)  # list of blacklisted steam id64
    client_options: dict = field(default_factory=dict)  # client options for steam.py
