from express.command import parse_command


def get_command(intent: str, sku: str, amount: int = 1) -> dict:
    is_sku = ";" in sku

    data = {"intent": intent, "amount": amount, "is_sku": is_sku}

    if is_sku:
        data["sku"] = sku
    else:
        data["item_name"] = sku

    return data


def test_parse_sku_command() -> None:
    assert parse_command("bu") is None
    assert parse_command("bu_12") is None
    assert parse_command("buy_12_5") == get_command("buy", "12;5")
    assert parse_command("buy_1x_5021_6") == get_command("buy", "5021;6")
    assert parse_command("BUY_5X_5021_6") == get_command("buy", "5021;6", 5)
    assert parse_command("buy_5021_6") == get_command("buy", "5021;6")
    assert parse_command("sell_1x_5021_6") == get_command("sell", "5021;6")
    assert parse_command("sell_5x_5021_6") == get_command("sell", "5021;6", 5)
    assert parse_command("SELL_5021_6") == get_command("sell", "5021;6")
    assert parse_command("buy_30917_5_u3147") == get_command("buy", "30917;5;u3147")
    assert parse_command("buy_5x_30917_5_u3147") == get_command(
        "buy", "30917;5;u3147", 5
    )
    assert parse_command("sell_1943x_1071_11_kt-3") == get_command(
        "sell", "1071;11;kt-3", 1943
    )


def test_parse_item_name_command() -> None:
    assert parse_command("buy_mann_co_supply_crate_key") == get_command(
        "buy", "mann_co_supply_crate_key"
    )
    assert parse_command("buy_5x_mann_co_supply_crate_key") == get_command(
        "buy", "mann_co_supply_crate_key", 5
    )
    assert parse_command("sell_mann_co_supply_crate_key") == get_command(
        "sell", "mann_co_supply_crate_key"
    )
    assert parse_command("sell_3x_mann_co_supply_crate_key") == get_command(
        "sell", "mann_co_supply_crate_key", 3
    )
    assert parse_command("sell_3x_ellis_cap") == get_command("sell", "ellis_cap", 3)
