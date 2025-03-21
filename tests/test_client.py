from express.client import ExpressClient
from express.options import Options

options = Options(
    username="express",
    owners=[1, 2, 3],
    use_backpack_tf=False,
    fetch_prices_on_startup=False,
)
client = ExpressClient(options)


def test_is_owner() -> None:
    assert client._is_owner(1) is True
    assert client._is_owner(4) is False


def test_items_count() -> None:
    assert client._db.get_pricelist_count() == 2
