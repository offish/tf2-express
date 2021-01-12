from .database import update_price, get_item
from .database import _get_price
from .methods import request
from .logging import Log
from .utils import to_scrap, to_refined
from .settings import craft_hat_buy, craft_hat_sell

log = Log()


def get_key_price() -> float:
    return _get_price("Mann Co. Supply Crate Key")["buy"]["metal"]


def get_pricelist() -> dict:
    log.info("Trying to get prices...")
    return request("https://api.prices.tf/items", {"src": "bptf"})


def get_price(name: str, intent: str) -> float:
    if name == "Random Craft Hat":
        return craft_hat_sell if intent == "sell" else craft_hat_buy

    price = _get_price(name)[intent]
    metal = to_scrap(price["metal"])
    keys = price.get("keys")

    if keys:
        metal += to_scrap(keys * get_key_price())

    return to_refined(metal)


def update_pricelist(items: list) -> None:
    pricelist = get_pricelist()

    if not pricelist.get("items"):
        log.error("Could not get pricelist")
        return

    for i in pricelist["items"]:
        name = i["name"]

        if name in items:
            item = get_item(name)

            if not (item["buy"] or item["sell"]):
                update_price(name, i["buy"], i["sell"])

            elif not (i["buy"] == item["buy"]) or not (i["sell"] == item["sell"]):
                update_price(name, i["buy"], i["sell"])

    # Does not warn the user if an item in the database
    # can't be found in Prices.TF's pricelist
