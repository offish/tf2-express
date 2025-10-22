from dataclasses import dataclass, field

from .messages import (
    buy_listing_details,
    counter_offer,
    friend_accept,
    help_command,
    invalid_command,
    offer_accepted,
    price_command,
    sell_listing_details,
    send_offer,
    sending_offer,
    sending_offer_error,
    user_banned,
    user_blacklisted,
    user_pending_offer,
)


@dataclass
class Messages:
    friend_accept: str = friend_accept
    send_offer: str = send_offer
    counter_offer: str = counter_offer
    price_command: str = price_command
    help_command: str = help_command
    sell_listing_details: str = sell_listing_details
    buy_listing_details: str = buy_listing_details
    invalid_command: str = invalid_command
    offer_accepted: str = offer_accepted
    sending_offer: str = sending_offer
    sending_offer_error: str = sending_offer_error
    user_banned: str = user_banned
    user_blacklisted: str = user_blacklisted
    user_pending_offer: str = user_pending_offer


@dataclass
class Options:
    username: str
    use_backpack_tf: bool
    messages: Messages
    backpack_tf_token: str = ""
    pricing_provider: str = "pricedb"  # pricedb
    inventory_provider: str = "steamcommunity"  # steamsupply, expressload, etc.
    inventory_api_key: str = ""  # api key for the inventory provider
    backpack_tf_user_agent: str = "Listing goin' up!"
    check_backpack_tf_bans: bool = False
    backpack_tf_api_key: str = ""  # api key for backpack.tf
    accept_donations: bool = True
    counter_bad_offers: bool = False  # counter offers with wrong values
    decline_trade_hold: bool = True
    cancel_old_sent_offers: bool = False  # cancel offers sent by us after some time
    cancel_sent_offers_after_seconds: int = 300  # auto cancel has to be enabled
    enable_craft_hats: bool = False  # enable random craft hats
    save_trade_offers: bool = True  # save trade offers in database
    sku_in_listing_details: bool = False  # disable for item name instead
    enable_discord: bool = False
    discord_token: str = ""  # discord bot token
    discord_channel_id: int = 0
    discord_owner_ids: list[int] = field(default_factory=list)
    llm_chat_responses: bool = False  #  for chat commands which are not recognized
    llm_model: str = "groq/llama-3.3-70b-versatile"  # model to use for llm responses
    llm_api_key: str = ""  # api key for to llm provider
    groups: list[int] = field(default_factory=list)
    owners: list[str] = field(default_factory=list)  # list of owner steam id64
    blacklist: list[str] = field(default_factory=list)  # list of blacklisted steam id64
    client_options: dict = field(default_factory=dict)  # client options for steam.py
    enable_arbitrage: bool = False
    quicksell_on_startup: bool = False
    stn_api_key: str = ""  # api key for stn.tf
    is_express_tf_bot: bool = False  # is this bot an express.tf bot
    express_tf_uri: str = ""
    express_tf_token: str = ""
