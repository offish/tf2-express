from express.sku import parse_command


def test_parse_command() -> None:
    assert parse_command("bu") is None
    assert parse_command("bu_12") is None
    assert parse_command("buy_12_5") == {
        "intent": "buy",
        "amount": 1,
        "sku": "12;5",
    }
    assert parse_command("buy_1x_5021_6") == {
        "intent": "buy",
        "amount": 1,
        "sku": "5021;6",
    }
    assert parse_command("BUY_5X_5021_6") == {
        "intent": "buy",
        "amount": 5,
        "sku": "5021;6",
    }
    assert parse_command("buy_5021_6") == {
        "intent": "buy",
        "amount": 1,
        "sku": "5021;6",
    }
    assert parse_command("sell_1x_5021_6") == {
        "intent": "sell",
        "amount": 1,
        "sku": "5021;6",
    }
    assert parse_command("sell_5x_5021_6") == {
        "intent": "sell",
        "amount": 5,
        "sku": "5021;6",
    }
    assert parse_command("SELL_5021_6") == {
        "intent": "sell",
        "amount": 1,
        "sku": "5021;6",
    }
    assert parse_command("buy_30917_5_u3147") == {
        "intent": "buy",
        "amount": 1,
        "sku": "30917;5;u3147",
    }
    assert parse_command("buy_5x_30917_5_u3147") == {
        "intent": "buy",
        "amount": 5,
        "sku": "30917;5;u3147",
    }
    assert parse_command("sell_1943x_1071_11_kt-3") == {
        "intent": "sell",
        "amount": 1943,
        "sku": "1071;11;kt-3",
    }
    assert parse_command("sell_sdfsx_1071_11_kt-3") == {
        "intent": "sell",
        "amount": 1,
        "sku": "sdfsx;1071;11;kt-3",
    }
