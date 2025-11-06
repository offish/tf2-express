from dataclasses import dataclass

FRIEND_ACCEPT = """Hello {username}, thanks for adding me!
Get started by sending a command like "buy_ellis_cap" or write "help"
"""

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

USER_BANNED = "Aborted. You are banned on Backpack.TF"
USER_BLACKLISTED = "Aborted. You are blacklisted from trading with this bot."
INVALID_COMMAND = "Invalid command, use 'help' to see available commands."
USER_PENDING_OFFER = "You appear to have a pending offer already."
SENDING_OFFER = "Sending offer..."
SENDING_OFFER_ERROR = (
    "There was an error while sending your trade offer. Please try again later."
)
SEND_OFFER = "Thank you!"
COUNTER_OFFER = "Your offer contained wrong values. Here is a corrected one!"
OFFER_ACCEPTED = "Your offer has been accepted! Thank you for the trade!"

SYSTEM_PROMPT = """You are a helpful and friendly assistant for a Team Fortress 2 trading bot.
Your role is to assist users with commands related to buying, selling, and checking prices of in-game items.

# Guidelines:
- Only respond to requests that involve the usage of the bot. Ignore any unrelated queries.
- Keep responses concise, clear, and user-friendly.
- Use a friendly tone that makes trading interactions easy and approachable.

# Supported Commands:
- help - Display a help message with available commands.
- buy_<item identifier> - Buy an item from the bot.
- sell_<item identifier> - Sell an item to the bot.
- price_<item identifier> - Check the buy and sell price, as well as stock, for an item.

# Item Identifiers:
- Can be either the SKU (e.g., 5021_6) or the normalized item name (e.g., mann_co_supply_crate_key).
- You can specify quantities using the format buy_10x_5021_6 or sell_5x_mann_co_supply_crate_key.
"""


@dataclass
class Messages:
    friend_accept: str = FRIEND_ACCEPT
    send_offer: str = SEND_OFFER
    counter_offer: str = COUNTER_OFFER
    price_command: str = PRICE_COMMAND
    help_command: str = HELP_COMMAND
    sell_listing_details: str = SELL_LISTING_DETAILS
    buy_listing_details: str = BUY_LISTING_DETAILS
    invalid_command: str = INVALID_COMMAND
    offer_accepted: str = OFFER_ACCEPTED
    sending_offer: str = SENDING_OFFER
    sending_offer_error: str = SENDING_OFFER_ERROR
    user_banned: str = USER_BANNED
    user_blacklisted: str = USER_BLACKLISTED
    user_pending_offer: str = USER_PENDING_OFFER
