friend_accept = """Hello {username}, thanks for adding me!
Get started by sending a command like "buy_ellis_cap" or write "help"
"""

price_command = """I'm buying {sku} for {buy_keys} keys and {buy_metal} ref
and selling for {sell_keys} keys and {sell_metal} ref
I currently have {in_stock} in stock, my max is {max_stock}
"""

help_command = """Available commands:

- help - Shows this message
- buy_ellis_cap - Buy items from the bot
- sell_ellis_cap - Sell items to the bot
- price_ellis_cap - Check the buy and sell price and its stock for an item

You can use the item name or SKU, e.g. "buy_5021_6" or "buy_mann_co_supply_crate_key"
You can also specify amount to buy/sell multiple items at once, e.g. "buy_10x_5021_6"
"""

sell_listing_details = (
    "{price} ⚡️ I have {in_stock} ⚡️ 24/7 FAST ⚡️ "
    + "Offer (try to take it for free, I'll counter) or chat me. "
    + "(double-click Ctrl+C): buy_{formatted_identifier}"
)

buy_listing_details = (
    "{price} ⚡️ Stock {in_stock}/{max_stock_string} ⚡️ 24/7 FAST ⚡️ "
    + "Offer or chat me. (double-click Ctrl+C): sell_{formatted_identifier}"
)

user_banned = "Aborted. You are banned on Backpack.TF"
user_blacklisted = "Aborted. You are blacklisted from trading with this bot."
invalid_command = "Invalid command, use 'help' to see available commands."
user_pending_offer = "You appear to have a pending offer already."
sending_offer = "Sending offer..."
sending_offer_error = (
    "There was an error while sending your trade offer. Please try again later."
)
send_offer = "Thank you!"
counter_offer = "Your offer contained wrong values. Here is a corrected one!"
offer_accepted = "Your offer has been accepted! Thank you for the trade!"
