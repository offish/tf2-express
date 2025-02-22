from express import __version__
from express.utils import (
    decode_data,
    encode_data,
    get_version,
    sku_to_item_data,
)


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


def test_data() -> None:
    data = {"test": "data"}
    encoded = encode_data(data)
    decoded = decode_data(encoded)

    assert encoded == b'{"test": "data"}NEW_DATA'
    assert decoded == [data]


def test_version() -> None:
    version = get_version("tf2-express", "express")
    assert version != __version__
