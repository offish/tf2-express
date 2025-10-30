class Express:
    def __init__(self, steam_id: str, options) -> None:
        self.steam_id = steam_id
        self.options = options
        self.database = None

        self.inventory_manager = None
        self.arbitrage_manager = None
        self.listing_manager = None
        self.pricing_manager = None
        self.discord_manager = None
        self.trade_manager = None
        self.chat_manager = None
        self.ws_manager = None
