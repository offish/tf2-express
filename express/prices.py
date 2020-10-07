from .methods import request, read, write
import json

PATH = 'express/json/prices.json'


def get_pricelist():
    uri = 'https://api.prices.tf/items'
    payload = {'src': 'bptf'}
    return request(uri, payload)


def get_price(item: str, intent: str, prices: dict):
    if item in prices \
        and intent in prices[item]:
        return prices[item][intent]['metal']
    return None


def get_prices(items: list, pricelist: dict) -> dict:
    pricelist = pricelist['items'] \
        if 'items' in pricelist else pricelist

    prices = {}

    for item in items:
        for i in pricelist:
            if i['name'] == item:
                prices[i['name']] = {
                    'buy': i['buy'],
                    'sell': i['sell']
                }
    return prices


def add(name: str, buy: float, sell: float) -> None:
    data = read(PATH)

    data[name] = {
        'buy': buy,
        'sell': sell
    }
    write(PATH, data)


def update(name, buy, sell) -> None:
    try:
        data = read(PATH)
        data[name]['buy'] = buy
        data[name]['sell'] = sell
        write(PATH, data)
    except json.decoder.JSONDecodeError:
        pass


def remove(name: str) -> None:
    data = read(PATH)
    
    if name in data:
        data.pop(name)
        write(PATH, data)
