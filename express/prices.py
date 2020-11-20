from .database import update_price, get_item
from .database import _get_price
from .methods import request
from .logging import Log


log = Log()


def get_pricelist():
    uri = 'https://api.prices.tf/items'
    payload = {'src': 'bptf'}
    log.info('Trying to get prices...')
    return request(uri, payload)


def get_price(item: str, intent: str):
    return _get_price(item)[intent]['metal']


def update_pricelist(items: list) -> None:
    pricelist = get_pricelist()

    if not 'items' in pricelist:
        log.error('Could not get pricelist')
        return

    for i in pricelist['items']:
        name = i['name']
        
        if name in items:
            item = get_item(name)

            if not (item['buy'] or item['sell']):
                update_price(name, i['buy'], i['sell'])

            elif not (i['buy'] == item['buy']) \
                or not (i['sell'] == item['sell']):
                update_price(name, i['buy'], i['sell'])

    # Does not warn the user if an item in the database
    # can't be found in Prices.TF's pricelist
