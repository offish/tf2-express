from dataclasses import dataclass, field

FRIEND_ACCEPT_MESSAGE = """Hello {username}, thanks for adding me!
Get started by sending a command like "buy_ellis_cap" or write "help"
"""

SEND_OFFER_MESSAGE = "Thank you!"

COUNTER_OFFER_MESSAGE = "Your offer contained wrong values, here is a corrected one!"

PRICE_COMMAND = """I'm buying {sku} for {buy_keys} keys and {buy_metal} ref
and selling for {sell_keys} keys and {sell_metal} ref
I currently have {in_stock} in stock, my max is {max_stock}
"""

HELP_COMMAND = """Available commands:

- help - Shows this message
- buy_ellis_cap - Buy items from the bot
- sell_ellis_cap - Sell items to the bot
- price_ellis_cap - Check the buy and sell price and its stock for an item

You can use the item name or SKU, e.g. "buy_5021_6" or "buy_mann_co_supply_crate_key"
You can also specify amount to buy/sell multiple items at once, e.g. "buy_10x_5021_6"
"""

SELL_LISTING_DETAILS = (
    "{price} ⚡️ I have {in_stock} ⚡️ 24/7 FAST ⚡️ "
    + "Offer (try to take it for free, I'll counter) or chat me. "
    + "(double-click Ctrl+C): buy_{formatted_identifier}"
)

BUY_LISTING_DETAILS = (
    "{price} ⚡️ Stock {in_stock}/{max_stock_string} ⚡️ 24/7 FAST ⚡️ "
    + "Offer or chat me. (double-click Ctrl+C): sell_{formatted_identifier}"
)


@dataclass
class Options:
    username: str
    use_backpack_tf: bool
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
    llm_chat_responses: bool = False  #  for chat commands which are not recognized
    llm_model: str = "groq/llama-3.3-70b-versatile"  # model to use for llm responses
    llm_api_key: str = ""  # api key for to llm provider
    groups: list[int] = field(default_factory=list)
    owners: list[str] = field(default_factory=list)  # list of owner steam id64
    blacklist: list[str] = field(default_factory=list)  # list of blacklisted steam id64
    client_options: dict = field(default_factory=dict)  # client options for steam.py
    enable_arbitrage: bool = False
    stn_api_key: str = ""  # api key for stn.tf
    is_express_tf_bot: bool = False  # is this bot an express.tf bot
    express_tf_uri: str = ""
    express_tf_token: str = ""
