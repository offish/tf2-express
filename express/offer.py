from .utils import get_steamid64
from .config import owners

states = {
    '2': 'active',
    '3': 'accepted',
    '7': 'declined'
}


class Offer:
    def __init__(self, offer: dict):
        self.offer = offer

    def get_state(self):
        state = str(self.offer['trade_offer_state'])
        
        if state in states:
            return states[state]
        return state

    def has_state(self, state: int) -> bool:
        return self.offer['trade_offer_state'] == state

    def is_active(self) -> bool:
        return self.has_state(2)

    def is_accepted(self) -> bool:
        return self.has_state(3)

    def is_declined(self) -> bool:
        return self.has_state(7)

    def has_escrow(self) -> bool:
        return self.offer['escrow_end_date'] == 0

    def is_our_offer(self) -> bool:
        return self.offer['is_our_offer']

    def is_gift(self) -> bool:
        return self.offer.get('items_to_receive') \
            and not self.offer.get('items_to_give')

    def is_scam(self) -> bool:
        return self.offer.get('items_to_give') \
            and not self.offer.get('items_to_receive') \

    def is_valid(self) -> bool:
        return self.offer.get('items_to_receive') \
            and self.offer.get('items_to_give') \
            and self.has_escrow()

    def get_partner(self) -> int:
        return get_steamid64(self.offer['accountid_other'])

    def is_from_owner(self) -> bool:
        return self.get_partner in owners
