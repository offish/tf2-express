from dataclasses import dataclass, field
from typing import Any

from .exceptions import MissingAPIKey, MissingBackpackTFToken, OptionsError
from .utils import get_and_read_json_file


@dataclass
class GeneralOptions:
    price_provider: str = "pricedb"
    database_provider: str = "mongodb"
    check_updates: bool = True
    groups: list[int] = field(default_factory=list)
    owners: list[str] = field(default_factory=list)  # list of owner steam id64
    blacklist: list[str] = field(default_factory=list)  # list of blacklisted steam id64
    client_options: dict = field(default_factory=dict)  # client options for steam.py


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
class FriendsOptions:
    accept_friends: bool = False  # auto accept friend requests
    enable_chat: bool = False  # wheter to process chats


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
    general: GeneralOptions
    messages: Messages
    backpack_tf: BackpackTFOptions
    inventory: InventoryOptions
    offers: OffersOptions
    discord: DiscordOptions
    friends: FriendsOptions
    arbitrage: ArbitrageOptions
    copy_trade: CopyTradeOptions
    express_tf: ExpressTFOptions


def get_option(data: dict, option: Any) -> Any | None:
    annotations = option.__annotations__
    name = option.__name__

    for key in data:
        if key not in annotations:
            raise OptionsError(f'Option "{key}" does not exist in {name}')

        value = type(data[key])
        correct_type = annotations[key]

        if name != "Options" and correct_type != list[str] and value != correct_type:
            raise OptionsError(f'Option "{key}" in {name} is not a {correct_type}')

    if name == "Options":
        return

    return option(**data)


def get_options(username: str) -> Options:
    options = get_and_read_json_file("options.json", must_exist=False)
    messages = get_and_read_json_file("messages.json", must_exist=False)
    get_option(options, Options)

    options_dict = {}
    pairs = {
        "general": GeneralOptions,
        "backpack_tf": BackpackTFOptions,
        "offers": OffersOptions,
        "inventory": InventoryOptions,
        "friends": FriendsOptions,
        "discord": DiscordOptions,
        "copy_trade": CopyTradeOptions,
        "arbitrage": ArbitrageOptions,
        "express_tf": ExpressTFOptions,
    }

    for key in pairs:
        value = options.get(key, {})
        options_dict[key] = get_option(value, pairs[key])

    return Options(username=username, messages=Messages(**messages), **options_dict)


def check_options(options: Options) -> None:
    if options.backpack_tf.enable and not options.backpack_tf.access_token:
        raise MissingBackpackTFToken("Backpack.TF Access Token is required for listing")

    if options.backpack_tf.check_bans and not options.backpack_tf.api_key:
        raise MissingAPIKey("Backpack.TF API key is needed for ban checks")

    if options.discord.enable and not options.discord.owner_ids:
        raise OptionsError("Discord Bot must have at least 1 owner")

    if options.discord.enable and not options.discord.token:
        raise OptionsError("Discord Bot Token is required")

    if options.discord.enable and not options.discord.channel_id:
        raise OptionsError("Discord Channel ID is required")

    if options.arbitrage.enable and not options.arbitrage.stn_api_key:
        raise MissingAPIKey("STN.tf API key is needed for arbitrage")

    if options.copy_trade.enable and not options.copy_trade.steam_id:
        raise OptionsError("A Steam ID is required to copy trade")
