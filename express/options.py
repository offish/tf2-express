from dataclasses import dataclass, field


@dataclass
class Options:
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
    poll_interval: int = 30
    database: str = "express"
    owners: list[str] = field(default_factory=list)


@dataclass
class GlobalOptions:
    bots: list[dict]
    name: str = "express user"  # nickname for gui
    check_versions_on_startup: bool = True
    listen_to_pricer: bool = True
