from dataclasses import dataclass, field

FRIEND_ACCEPT_MESSAGE = """Hi {username}, thanks for adding me!
Get started by sending a command like "buy_1x_5021_6" or check out my listings!
"""
SEND_OFFER_MESSAGE = "Thank you!"
OFFER_ACCEPTED_MESSAGE = "Success, offer was accepted. Thank you for the trade!"
COUNTER_OFFER_MESSAGE = "Your offer contained wrong values, here is a corrected one!"


@dataclass
class Options:
    use_backpack_tf: bool
    backpack_tf_token: str
    enable_deals: bool = False
    inventory_provider: str = "steamcommunity"
    inventory_api_key: str = ""
    fetch_prices_on_startup: bool = True
    accept_donations: bool = False
    decline_bad_offers: bool = False
    decline_trade_hold: bool = False
    decline_scam_offers: bool = False
    allow_craft_hats: bool = False
    save_trades: bool = True
    save_receipt: bool = True
    database: str = "express"
    groups: list[int] = field(default_factory=list)
    owners: list[int] = field(default_factory=list)
    client_options: dict = field(default_factory=dict)


@dataclass
class GlobalOptions:
    bots: list[dict]
    name: str = "express user"  # nickname for gui
    check_versions_on_startup: bool = True
    listen_to_pricer: bool = True
