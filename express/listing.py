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
) -> Listing | None:
    for listing in listings:
        if listing.status != "active":
            continue

        if listing.intent != listing_construct.intent:
            continue

        sku = listing_construct.sku
        defindex = listing.item.get("defindex")
        quality_id = listing.item.get("quality", {}).get("id")

        if defindex != sku_to_defindex(sku):
            continue

        if quality_id != sku_to_quality(sku):
            continue

        return listing
