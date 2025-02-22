from express.offer import is_only_taking_items, is_two_sided_offer


def test_is_only_taking_items() -> None:
    assert is_only_taking_items(0, 1) is True
    assert is_only_taking_items(1, 0) is False


def test_is_two_sided_offer() -> None:
    assert is_two_sided_offer(1, 1) is True
    assert is_two_sided_offer(0, 1) is False
    assert is_two_sided_offer(1, 0) is False
