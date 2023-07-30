from .settings import DECLINE_TRADE_HOLD
from .prices import get_price, get_key_price
from .config import OWNERS
from .utils import to_scrap
from .items import Item

from steampy.models import TradeOfferState
from steampy.utils import account_id_to_steam_id


def valuate(items: dict, intent: str, item_list: list) -> tuple[int, bool]:
    has_unpriced = False
    total = 0

    for i in items:
        # valute one item at a time
        item = Item(items[i])
        name = item.name
        value = 0.00

        if not item.is_tf2():
            # we dont add any price for that item -> skip
            continue

        if item.is_pure():  # should be metal / add keys to pure
            value = item.get_pure()

        elif item.is_key():
            # handle keys equal, at this time, but we maybe dont want to
            value = get_key_price()

        elif item.is_craftable():
            if name in item_list:
                value = get_price(name, intent)

            elif item.is_craft_weapon():
                value = get_price("Craftable Weapon", intent)

            elif item.is_craft_hat():
                value = get_price("Random Craft Hat", intent)

        elif not item.is_craftable():
            name = "Non-Craftable " + name

            if name in item_list:
                value = get_price(name, intent)

        if not value and intent == "sell":
            has_unpriced = True
            # dont need to process rest of offer since we cant know the total price
            break

        # gets prices in ref, and converts to scrap
        # if price is less than 0.11 ref, it's a craft weapon
        total += to_scrap(value) if value >= 0.11 else 0.50

    # total scrap
    return total, has_unpriced


class Offer:
    def __init__(self, offer: dict) -> None:
        self.offer = offer
        self.state = offer["trade_offer_state"]

    def get_state(self) -> str:
        return TradeOfferState(self.state).name

    def has_state(self, state: int) -> bool:
        return self.state == state

    def is_active(self) -> bool:
        return self.has_state(2)

    def is_accepted(self) -> bool:
        return self.has_state(3)

    def is_declined(self) -> bool:
        return self.has_state(7)

    def has_trade_hold(self) -> bool:
        return self.offer["escrow_end_date"] != 0

    def is_our_offer(self) -> bool:
        return self.offer["is_our_offer"]

    def is_gift(self) -> bool:
        return self.offer.get("items_to_receive") and not self.offer.get(
            "items_to_give"
        )

    def is_scam(self) -> bool:
        return self.offer.get("items_to_give") and not self.offer.get(
            "items_to_receive"
        )

    def is_valid(self) -> bool:
        if self.has_trade_hold() and DECLINE_TRADE_HOLD:
            return False

        if self.offer.get("items_to_receive") and self.offer.get("items_to_give"):
            return True

        return False

    def get_partner(self) -> str:
        return account_id_to_steam_id(self.offer["accountid_other"])

    def is_from_owner(self) -> bool:
        return self.get_partner() in OWNERS
