from unittest import TestCase

from express.express import Express
from express.options import Options
from express.utils import sku_to_item_data, get_config


class TestDatabase(TestCase):
    def test_database(self):
        config = get_config()
        options = config["bots"][0]["options"]

        options["database"] = "express_test"
        options["enable_deals"] = False

        options = Options(**options)
        bot = Express(config["bots"][0], options)

        db = bot.db

        self.assertNotEqual(db.get_item("5021;6"), {})

        db.add_price(
            **sku_to_item_data("30469;1"),
            buy={"keys": 0, "metal": 0.11},
            sell={"keys": 0, "metal": 0.22},
        )

        db.add_price(
            **sku_to_item_data("5020;6"),
            buy={"keys": 0, "metal": 0.11},
            sell={"keys": 0, "metal": 0.22},
        )

        self.assertEqual(db.get_price("30469;1", "buy"), (0, 0.11))

        db.update_stocks({"30469;1": 1, "5020;6": 5})

        for sku in db.get_skus():
            db.delete_price(sku)

        self.assertEqual(db.get_price("30469;1", "sell"), (0, 0.0))
        self.assertEqual(db.get_price("5002;6", "buy"), (0, 1.0))
        self.assertEqual(db.get_price("5002;6", "sell"), (0, 1.0))
