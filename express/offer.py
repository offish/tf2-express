from .database import Database
from .options import Options

from dataclasses import dataclass, field
import logging

from tf2_utils import Item, get_sku, to_scrap, is_metal, get_metal, to_refined


@dataclass
class OfferData:
    offer_id: str
    steam_id_other: str = ""
    message: str = ""
    time_created: int = 0
    time_updated: int = 0
    their_items: dict = field(default_factory=dict)
    our_items: dict = field(default_factory=dict)
    our_value: float = 0.0
    their_value: float = 0.0
    state: str = "Processed"
    has_unpriced: bool = True
    receipt: dict = field(default_factory=dict)


def valuate(
    db: Database,
    items: dict,
    intent: str,
    all_skus: list,
    key_prices: dict | None,
    options: Options,
) -> tuple[int, bool]:
    has_unpriced = False
    total = 0

    key_price = 0.0

    if key_prices:
        key_price = key_prices[intent]["metal"]
    else:
        logging.warning("No key price found, will valuate keys at 0 ref")

    for i in items:
        # valute one item at a time
        item = Item(items[i])
        sku = get_sku(item)
        keys = 0
        metal = 0.00

        # TODO: what if intent is sell and the item is "fake"?
        if not item.is_tf2() and intent == "buy":
            # we dont add any price for that item -> skip
            continue

        elif item.is_key():
            keys = 1

        elif is_metal(sku):  # should be metal
            metal = to_refined(get_metal(sku))

        # has a specifc price
        elif sku in all_skus:
            keys, metal = db.get_price(sku, intent)

        # TODO: AND ALLOW CRAFT WEPS
        # elif item.is_craft_weapon():
        #     keys, metal = db.get_price("-50;6", intent)

        elif item.is_craft_hat() and options.allow_craft_hats:
            keys, metal = db.get_price("-100;6", intent)

        value = keys * to_scrap(key_price) + to_scrap(metal)

        if not value and intent == "sell":
            # dont need to process rest of offer since we cant know the total price
            has_unpriced = True
            break

        logging.debug(f"{intent} {sku=} has {value=}")
        # handle craft weapons
        # total += value if value >= 1 else 0.50
        total += value

    # total scrap
    return total, has_unpriced
