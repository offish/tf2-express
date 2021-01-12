from .settings import decline_trade_hold
from .prices import get_price, get_key_price
from .config import owners
from .utils import Item, to_scrap

from steampy.models import TradeOfferState
from steampy.utils import account_id_to_steam_id


def valuate(items: dict, intent: str, item_list: list) -> int:
    total = 0
    high = float(10 ** 5)

    for i in items:
        item = Item(items[i])
        name = item.name
        value = 0.00

        if item.is_tf2():

            if item.is_pure():
                value = item.get_pure()

            elif item.is_key():
                value = get_key_price()

            elif item.is_craftable():

                if name in item_list:
                    value = get_price(name, intent)

                elif item.is_craft_hat():
                    value = get_price("Random Craft Hat", intent)

            elif not item.is_craftable():
                name = "Non-Craftable " + name

                if name in item_list:
                    value = get_price(name, intent)

        if not value:
            value = high if intent == "sell" else 0.00

        total += to_scrap(value)

    return total


class Offer:
    def __init__(self, offer: dict):
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

    def has_escrow(self) -> bool:
        return self.offer["escrow_end_date"] == 0

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
        return (
            True
            if self.offer.get("items_to_receive")
            and self.offer.get("items_to_give")
            and (self.has_escrow() or self.has_escrow() == decline_trade_hold)
            else False
        )

    def get_partner(self) -> str:
        return account_id_to_steam_id(self.offer["accountid_other"])

    def is_from_owner(self) -> bool:
        return self.get_partner() in owners
