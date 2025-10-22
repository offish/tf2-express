from express.command import parse_command


def test_parse_sku_command() -> None:
    assert parse_command("bu") is None
    assert parse_command("bu_12") is None
    assert parse_command("buy_12_5") == {
        "intent": "buy",
        "amount": 1,
        "is_sku": True,
        "sku": "12;5",
    }
    assert parse_command("buy_1x_5021_6") == {
        "intent": "buy",
        "amount": 1,
        "is_sku": True,
        "sku": "5021;6",
    }
    assert parse_command("BUY_5X_5021_6") == {
        "intent": "buy",
        "amount": 5,
        "is_sku": True,
        "sku": "5021;6",
    }
    assert parse_command("buy_5021_6") == {
        "intent": "buy",
        "amount": 1,
        "is_sku": True,
        "sku": "5021;6",
    }
    assert parse_command("sell_1x_5021_6") == {
        "intent": "sell",
        "amount": 1,
        "is_sku": True,
        "sku": "5021;6",
    }
    assert parse_command("sell_5x_5021_6") == {
        "intent": "sell",
        "amount": 5,
        "is_sku": True,
        "sku": "5021;6",
    }
    assert parse_command("SELL_5021_6") == {
        "intent": "sell",
        "amount": 1,
        "is_sku": True,
        "sku": "5021;6",
    }
    assert parse_command("buy_30917_5_u3147") == {
        "intent": "buy",
        "amount": 1,
        "is_sku": True,
        "sku": "30917;5;u3147",
    }
    assert parse_command("buy_5x_30917_5_u3147") == {
        "intent": "buy",
        "amount": 5,
        "is_sku": True,
        "sku": "30917;5;u3147",
    }
    assert parse_command("sell_1943x_1071_11_kt-3") == {
        "intent": "sell",
        "amount": 1943,
        "is_sku": True,
        "sku": "1071;11;kt-3",
    }


def test_parse_item_name_command() -> None:
    assert parse_command("buy_mann_co_supply_crate_key") == {
        "intent": "buy",
        "amount": 1,
        "item_name": "mann_co_supply_crate_key",
        "is_sku": False,
    }
    assert parse_command("buy_5x_mann_co_supply_crate_key") == {
        "intent": "buy",
        "amount": 5,
        "item_name": "mann_co_supply_crate_key",
        "is_sku": False,
    }
    assert parse_command("sell_mann_co_supply_crate_key") == {
        "intent": "sell",
        "amount": 1,
        "item_name": "mann_co_supply_crate_key",
        "is_sku": False,
    }
    assert parse_command("sell_3x_mann_co_supply_crate_key") == {
        "intent": "sell",
        "amount": 3,
        "item_name": "mann_co_supply_crate_key",
        "is_sku": False,
    }
    assert parse_command("sell_3x_mann_co_supply_crate_key_with_strange_part") == {
        "intent": "sell",
        "amount": 3,
        "item_name": "mann_co_supply_crate_key_with_strange_part",
        "is_sku": False,
    }
