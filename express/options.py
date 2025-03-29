from dataclasses import dataclass, field

FRIEND_ACCEPT_MESSAGE = """Hi {username}, thanks for adding me!
Get started by sending a command like "buy_1x_5021_6" or check out my listings!
"""
SEND_OFFER_MESSAGE = "Thank you!"
OFFER_ACCEPTED_MESSAGE = "Success, offer was accepted. Thank you for the trade!"
COUNTER_OFFER_MESSAGE = "Your offer contained wrong values, here is a corrected one!"


@dataclass
class Options:
    username: str
    use_backpack_tf: bool
    backpack_tf_token: str = ""
    inventory_provider: str = "steamcommunity"  # steamsupply, expressload, etc.
    inventory_api_key: str = ""  # api key for the inventory provider
    fetch_prices_on_startup: bool = True
    accept_donations: bool = True
    counter_bad_offers: bool = True  # counter offers with wrong values
    decline_trade_hold: bool = True
    expire_sent_offers: bool = True  # cancel offers sent by us after some time
    expire_sent_offers_after: int = 300  # time in seconds which must pass to cancel
    enable_deals: bool = False  # used by tf2-arbitrage
    allow_craft_hats: bool = False
    save_trades: bool = True  # save trade offers in database
    save_receipt: bool = True  # save trade offer receipts in database
    groups: list[int] = field(default_factory=list)
    owners: list[int] = field(default_factory=list)  # list of owner steam id64
    client_options: dict = field(default_factory=dict)  # client options for steam.py
    is_express_tf_bot: bool = False  # is this bot an express.tf bot
    express_tf_uri: str = ""
    express_tf_token: str = ""
