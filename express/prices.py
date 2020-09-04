#import requests
import json

from .methods import read, write
#from .utils import get_defindex

PATH = 'express/json/prices.json'

def add(name: str, buy: float, sell: float) -> None:
    data = read(PATH)

    data[name] = {
        'buy': buy,
        'sell': sell
    }
    write(PATH, data)


def update(name: str, buy: float = 0.00,
    sell: float = 0.00) -> None:
    data = read(PATH)

    if name in data and (buy or sell):
        if buy:
            data[name]['buy'] = buy
        if sell:
            data[name]['sell'] = sell
        write(PATH, data)


def remove(name: str) -> None:
    data = read(PATH)
    
    if name in data:
        data.pop(name)
        write(PATH, data)


def get_pricelist() -> dict:
    return read(PATH)


def get_price(name: str, intent: str) -> float:
    prices = get_prices(name)

    if not prices == {} \
        and intent in prices:
        return prices[intent]
    return 0.00


def get_prices(name: str) -> dict:
    data = read(PATH)

    if name in data \
        and 'buy' in data[name] \
        and 'sell' in data[name]:
        return data[name]
    return {}
