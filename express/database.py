from .logging import Log

from pymongo import MongoClient


client = MongoClient('localhost', 27017)
database = client['express']

trades = database['trades']
prices = database['prices']

log = Log()


def add_trade(data: dict) -> None:
    trades.insert(data)
    log.info(f'Offer was added to the database')


def get_items() -> list:
    data = prices.find()
    names = []
    for i in data:
        names.append(i['name'])
    return names


def get_item(name: str) -> dict:
    search = {'name': name}
    return prices.find_one(search)


def _get_price(name: str) -> dict:
    search = {'name': name}
    return prices.find_one(search)


def _get_pricelist() -> dict:
    return prices.find()


def add_price(name: str, buy: float, sell: float) -> None:
    data = {
        'name': name,
        'buy': buy,
        'sell': sell
    }
    prices.insert(data)
    log.info(f'Added {name} to the database')


def update_price(name: str, buy: float, sell: float) -> None:
    search = {'name': name}
    data = prices.find_one(search)

    data['buy'] = buy
    data['sell'] = sell

    prices.replace_one(search, data)
    log.info(f'Updated price for {name}')


def remove_price(name: str) -> None:
    search = {'name': name}
    prices.delete_one(search)
    log.info(f'Removed {name} from the database')
