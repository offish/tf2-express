from express.utils import (
    get_version,
    sku_to_item_data,
    encode_data,
    decode_data,
)
from express import __version__

from unittest import TestCase


class TestUtils(TestCase):
    def test_sku_to_item_data(self):
        self.assertEqual(
            sku_to_item_data("30469;1"),
            {
                "color": "4D7455",
                "image": "http://media.steampowered.com/apps/440/icons/horace.1fa7eb3b1b04da8888d5ee3979916d96d851a53e.png",  # noqa
                "name": "Horace",
                "sku": "30469;1",
            },
        )
        self.assertEqual(
            sku_to_item_data("233;6"),
            {
                "color": "7D6D00",
                "image": "http://media.steampowered.com/apps/440/icons/gift_single.efd5979a6b289dbab280920a9a123d1db3f4780b.png",  # noqa
                "name": "Secret Saxton",
                "sku": "233;6",
            },
        )

    def test_data(self):
        data = {"test": "data"}
        encoded = encode_data(data)
        decoded = decode_data(encoded)

        self.assertEqual(encoded, b'{"test": "data"}NEW_DATA')
        self.assertEqual(decoded, [data])

    def test_version(self):
        version = get_version("tf2-express", "express")
        self.assertNotEqual(version, __version__)
