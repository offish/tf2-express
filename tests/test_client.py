from express.client import ExpressClient
from express.options import Options


def test_is_owner() -> None:
    options = Options(owners=[1, 2, 3], fetch_prices_on_startup=False)
    client = ExpressClient(options)

    assert client._is_owner(1) is True
    assert client._is_owner(4) is False
