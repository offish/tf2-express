import pytest

from express.databases.database_providers import get_database_provider
from express.exceptions import SKUNotFound

database = get_database_provider("json", "express")
path = database.items_file
database._write_json(path, [])  # clear database


def test_get_price() -> None:
    assert database.get_price("5000;6", "buy") == (0, 0.11)
    assert database.get_price("5001;6", "buy") == (0, 0.33)
    assert database.get_price("5002;6", "buy") == (0, 1.0)
    assert database.get_price("5000;6", "sell") == (0, 0.11)
    assert database.get_price("5001;6", "sell") == (0, 0.33)
    assert database.get_price("5002;6", "sell") == (0, 1.0)
    assert database.get_price("not;in;db", "buy") == (0, 0.0)
    assert database.get_price("not;in;db", "sell") == (0, 0.0)


def test_add_key_for_first_time() -> None:
    assert database.get_skus() == []
    assert database.get_item("5021;6") == {}

    database._add_key_for_first_time()

    assert database.get_skus() == ["5021;6"]
    assert database.has_price("5021;6") is False
    assert database.get_price("5021;6", "buy") == (0, 0.0)
    assert database.get_price("5021;6", "sell") == (0, 0.0)
    assert database.get_item("5021;6") == {
        "autoprice": True,
        "buy": {},
        "color": "7D6D00",
        "image": "http://media.steampowered.com/apps/440/icons/key.be0a5e2cda3a039132c35b67319829d785e50352.png",
        "in_stock": 0,
        "max_stock": -1,
        "name": "Mann Co. Supply Crate Key",
        "sell": {},
        "sku": "5021;6",
    }


def test_update_price() -> None:
    database.update_price(
        "5021;6", {"keys": 0, "metal": 60.11}, {"keys": 0, "metal": 60.22}
    )

    assert database.has_price("5021;6") is True
    assert database.get_price("5021;6", "buy") == (0, 60.11)
    assert database.get_price("5021;6", "sell") == (0, 60.22)

    with pytest.raises(SKUNotFound):
        database.update_price(
            "not;in;db", {"keys": 0, "metal": 60.11}, {"keys": 0, "metal": 60.22}
        )


def test_update_stock() -> None:
    assert database.get_stock("5021;6") == (0, -1)

    stock = {"5021;6": 10, "not;a;sku": 20}
    database.update_stock(stock)

    assert database.get_stock("5021;6") == (10, -1)
