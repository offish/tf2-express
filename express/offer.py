def is_only_taking_items(their_items_amount: int, our_items_amount: int) -> bool:
    return their_items_amount == 0 and our_items_amount > 0


def is_two_sided_offer(their_items_amount: int, our_items_amount: int) -> bool:
    return their_items_amount > 0 and our_items_amount > 0
