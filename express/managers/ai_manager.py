from groq import Groq

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


class AIManager:
    def __init__(self, api_key: str) -> None:
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"

    def prompt(self, text: str) -> str:
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": text,
                },
            ],
            model=self.model,
        )
        return response.choices[0].message.content
