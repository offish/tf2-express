from dataclasses import dataclass, field

FRIEND_ACCEPT_MESSAGE = """Hello {username}, thanks for adding me!
Get started by sending a command like "buy_1x_5021_6" or check out my listings!
"""
SEND_OFFER_MESSAGE = "Thank you!"
COUNTER_OFFER_MESSAGE = "Your offer contained wrong values, here is a corrected one!"


@dataclass
class Options:
    username: str
    use_backpack_tf: bool
    backpack_tf_token: str = ""
    pricing_provider: str = "pricestf"  # pricestf or bptfautopricer
    inventory_provider: str = "steamcommunity"  # steamsupply, expressload, etc.
    inventory_api_key: str = ""  # api key for the inventory provider
    backpack_tf_user_agent: str = "Listing goin' up!"
    accept_donations: bool = True
    auto_counter_bad_offers: bool = True  # counter offers with wrong values
    decline_trade_hold: bool = True
    auto_cancel_sent_offers: bool = True  # cancel offers sent by us after some time
    cancel_sent_offers_after_seconds: int = 300  # auto cancel has to be enabled
    max_price_age_seconds: int = 3600  # if over the threshold, has to fetch price
    enable_arbitrage: bool = False  # used by tf2-arbitrage
    enable_craft_hats: bool = False  # enable random craft hats
    save_trade_offers: bool = True  # save trade offers in database
    groups: list[int] = field(default_factory=list)
    owners: list[str] = field(default_factory=list)  # list of owner steam id64
    client_options: dict = field(default_factory=dict)  # client options for steam.py
    arbitrage_url: str = ""  # url to websocket hosted by tf2-arbitrage
    is_express_tf_bot: bool = False  # is this bot an express.tf bot
    express_tf_uri: str = ""
    express_tf_token: str = ""
