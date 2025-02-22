# import time

# from express.express import Express
# from express.options import Options

# express = Express(
#     {
#         "name": "",
#         "username": "",
#         "password": "",
#         "api_key": "",
#         "secrets": {
#             "steamid": "",
#         },
#     },
#     Options(enable_deals=True, database="express_test"),
# )
# deals = express.deals


# def test_deals(self):
#     assert deals.get_deals(), []

#     deal = {
#         "is_deal": True,
#         "sku": "978;6",
#         "name": "Der Wintermantel",
#         "profit": 0.11,
#         "sites": ["stn", "pricestf"],
#         "buy_site": "stn",
#         "buy_price": {"keys": 0, "metal": 2.55},
#         "sell_site": "pricestf",
#         "sell_sell": {"keys": 0, "metal": 2.66},
#         "sell_data": {
#             "steamid": "76561199127484024",
#             "trade_url": "https://steamcommunity.com/tradeoffer/new/?partner=1378878827&token=N5dlFlVT",  # noqa
#         },
#         "stock": {"level": 25, "limit": 25},
#     }

#     deals.add_deal(deal)

#     assert deals.get_deals() == [deal]
#     assert deals.get_deal("978;6") == deal

#     deals.add_deal(deal)
#     assert deals.get_deals() == [deal]

#     data = deals.get_deal("978;6")
#     data["updated"] = time.time() - 3 * 60
#     deals.update_deal(data)

#     assert deals.get_deal("978;6") == data

#     deals.update_deal_state("978;6", "is_bought")

#     data["is_bought"] = True

#     assert deals.get_deal("978;6") == data

#     deals.update_deal_state("978;6", "is_sold")

#     data["is_sold"] = True
#     assert deals.get_deal("978;6") == data

#     for deal in deals.get_deals():
#         deals.delete_deal(deal["sku"])

#     assert deals.get_deals() == []
