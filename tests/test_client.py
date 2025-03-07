from express.client import ExpressClient
from express.options import Options

options = Options(
    owners=[1, 2, 3], use_backpack_tf=False, fetch_prices_on_startup=False
)
client = ExpressClient(options)


def test_is_owner() -> None:
    assert client._is_owner(1) is True
    assert client._is_owner(4) is False


def test_check_if_ready() -> None:
    assert client._is_ready is False
    assert client._prices_are_updated is False

    assert client._check_if_ready(False) is False
    assert client._check_if_ready(True) is False

    client._is_ready = True

    assert client._check_if_ready(False) is True
    assert client._check_if_ready(True) is False

    client._is_ready = False
    client._prices_are_updated = True

    assert client._check_if_ready(False) is False
    assert client._check_if_ready(True) is False

    client._is_ready = True
    client._prices_are_updated = True

    assert client._check_if_ready(False) is True
    assert client._check_if_ready(True) is True
