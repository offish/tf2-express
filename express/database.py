from .logging import Log

from pymongo import MongoClient


client = MongoClient("localhost", 27017)
database = client["express"]

trades = database["trades"]
prices = database["prices"]

log = Log()


def add_trade(data: dict) -> None:
    trades.insert(data)
    log.info(f"Offer was added to the database")


def get_trades() -> dict:
    return trades.find()


def get_items() -> list:
    return [item["name"] for item in prices.find()]


def get_autopriced_items() -> list:
    return [item["name"] for item in prices.find() if item.get("autoprice")]


def get_item(name: str) -> dict:
    return prices.find_one({"name": name})


def _get_price(name: str) -> dict:
    return prices.find_one({"name": name})


def get_database_pricelist() -> dict:
    return prices.find()


def add_price(name: str) -> None:
    prices.insert({"name": name, "autoprice": True, "buy": None, "sell": None})
    log.info(f"Added {name} to the database")


def update_price(name: str, autoprice: bool, buy: dict, sell: dict) -> None:
    prices.replace_one(
        {"name": name}, {"name": name, "autoprice": autoprice, "buy": buy, "sell": sell}
    )
    log.info(f"Updated price for {name}")


def remove_price(name: str) -> None:
    prices.delete_one({"name": name})
    log.info(f"Removed {name} from the database")
