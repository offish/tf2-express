from express import __version__
from express.utils import (
    get_version,
    has_buy_and_sell_price,
    is_only_taking_items,
    is_two_sided_offer,
    sku_to_item_data,
    swap_intent,
)


def test_has_buy_and_sell_price() -> None:
    assert has_buy_and_sell_price({"buy": {}, "sell": {}}) is False
    assert has_buy_and_sell_price({"buy": {"keys": 0, "metal": 0}, "sell": {}}) is False
    assert (
        has_buy_and_sell_price(
            {"buy": {"keys": 0, "metal": 0}, "sell": {"keys": 0, "metal": 0}}
        )
        is True
    )


def test_swap_intent() -> None:
    assert swap_intent("sell") == "buy"
    assert swap_intent("buy") == "sell"
    assert swap_intent("Sell") == "buy"
    assert swap_intent("Buy") == "sell"


def test_is_only_taking_items() -> None:
    assert is_only_taking_items(0, 1) is True
    assert is_only_taking_items(1, 0) is False


def test_is_two_sided_offer() -> None:
    assert is_two_sided_offer(1, 1) is True
    assert is_two_sided_offer(0, 1) is False
    assert is_two_sided_offer(1, 0) is False


def test_sku_to_item_data():
    assert sku_to_item_data("30469;1") == {
        "color": "4D7455",
        "image": "http://media.steampowered.com/apps/440/icons/horace.1fa7eb3b1b04da8888d5ee3979916d96d851a53e.png",
        "name": "Genuine Horace",
        "sku": "30469;1",
    }

    assert sku_to_item_data("233;6") == {
        "color": "7D6D00",
        "image": "http://media.steampowered.com/apps/440/icons/gift_single.efd5979a6b289dbab280920a9a123d1db3f4780b.png",
        "name": "Secret Saxton",
        "sku": "233;6",
    }


def test_version() -> None:
    version = get_version("tf2-express", "express")
    assert version != __version__
