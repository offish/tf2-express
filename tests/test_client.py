from express.client import ExpressClient
from express.options import Options

options = Options(owners=[1, 2, 3])
client = ExpressClient(options)


def test_is_owner() -> None:
    assert client._is_owner(1) is True
    assert client._is_owner(4) is False
