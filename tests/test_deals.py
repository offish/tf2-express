from unittest import TestCase
import time

from express.options import Options
from express.express import Express


class TestDatabase(TestCase):
    @classmethod
    def setUpClass(cls):
        express = Express(
            {
                "name": "",
                "username": "",
                "password": "",
                "api_key": "",
                "secrets": {
                    "steamid": "",
                },
            },
            Options(enable_deals=True, database="express_test"),
        )

        # database = Database("express_test")
        cls.deals = express.deals

    def test_deals(self):
        self.assertEqual(self.deals.get_deals(), [])

        deal = {
            "is_deal": True,
            "sku": "978;6",
            "name": "Der Wintermantel",
            "profit": 0.11,
            "sites": ["stn", "pricestf"],
            "buy_site": "stn",
            "buy_price": {"keys": 0, "metal": 2.55},
            "sell_site": "pricestf",
            "sell_sell": {"keys": 0, "metal": 2.66},
            "sell_data": {
                "steamid": "76561199127484024",
                "trade_url": "https://steamcommunity.com/tradeoffer/new/?partner=1378878827&token=N5dlFlVT",  # noqa
            },
            "stock": {"level": 25, "limit": 25},
        }

        self.deals.add_deal(deal)

        self.assertEqual(self.deals.get_deals(), [deal])
        self.assertEqual(self.deals.get_deal("978;6"), deal)

        self.deals.add_deal(deal)
        self.assertEqual(self.deals.get_deals(), [deal])

        data = self.deals.get_deal("978;6")
        data["updated"] = time.time() - 3 * 60
        self.deals.update_deal(data)

        self.assertEqual(self.deals.get_deal("978;6"), data)

        self.deals.update_deal_state("978;6", "is_bought")

        data["is_bought"] = True
        self.assertEqual(self.deals.get_deal("978;6"), data)

        self.deals.update_deal_state("978;6", "is_sold")

        data["is_sold"] = True
        self.assertEqual(self.deals.get_deal("978;6"), data)

        for deal in self.deals.get_deals():
            self.deals.delete_deal(deal["sku"])

        self.assertEqual(self.deals.get_deals(), [])
