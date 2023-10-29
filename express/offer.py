from .database import Database
from .options import Options
from .items import Item

import logging

from tf2_utils import get_sku, to_scrap


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

        elif item.is_pure():  # should be metal / add keys to pure
            metal = item.get_pure()

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

        # handle craft weapons
        # total += value if value >= 1 else 0.50
        total += value

    # total scrap
    return total, has_unpriced
