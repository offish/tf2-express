from backpack_tf import Listing
from tf2_utils import sku_to_defindex, sku_to_quality


def get_listing_key(intent: str, sku: str) -> str:
    assert intent in ["buy", "sell"]
    assert ";" in sku

    return f"{intent}_{sku}"


def has_enough_stock(intent: str, in_stock: int) -> bool:
    if intent == "sell":
        return in_stock > 0

    return True


def surpasses_max_stock(intent: str, in_stock: int, max_stock: int) -> bool:
    if intent == "sell":
        return False

    return max_stock != -1 and in_stock >= max_stock


def format_sell_listing_details(variables: dict) -> str:
    sell_details = (
        "{price} ⚡️ I have {in_stock} ⚡️ 24/7 FAST ⚡️ "
        + "Offer (try to take it for free, I'll counter) or chat me. "
        + "(double-click Ctrl+C): buy_1x_{formatted_sku}"
    )
    return sell_details.format(**variables)


def format_buy_listing_details(variables: dict) -> str:
    buy_details = (
        "{price} ⚡️ Stock {in_stock}/{max_stock_string} ⚡️ 24/7 FAST ⚡️ "
        + "Offer or chat me. (double-click Ctrl+C): sell_1x_{formatted_sku}"
    )
    return buy_details.format(**variables)


class ListingConstruct:
    def __init__(
        self,
        sku: str,
        intent: str,
        currencies: dict,
        details: str,
        asset_id: int,
        listing_variables: dict,
    ) -> None:
        self.sku = sku
        self.intent = intent
        self.currencies = currencies
        self.details = details
        self.asset_id = asset_id
        self.listings_variables = listing_variables

    @property
    def listing(self) -> dict:
        return {
            "sku": self.sku,
            "intent": self.intent,
            "currencies": self.currencies,
            "details": self.details,
            "asset_id": self.asset_id,
        }


def get_matching_listing(
    listing_construct: ListingConstruct, listings: list[Listing]
) -> Listing:
    for listing in listings:
        if listing.status != "active":
            continue

        sku = listing_construct.sku

        if listing.item.get("defindex") != sku_to_defindex(sku):
            continue

        if listing.item.get("quality", {}).get("id") != sku_to_quality(sku):
            continue

        if listing.intent != listing_construct.intent:
            continue

        return listing

    return None
