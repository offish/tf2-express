from multiprocessing import Process, Pool
from time import sleep

from express.database import *
from express.settings import *
from express.logging import Log, f
from express.prices import get_price, update_pricelist
from express.config import bots, timeout
from express.client import Client
from express.offer import Offer
from express.utils import Items, to_scrap, to_refined

import socketio


def run(bot: dict) -> None:
    client = Client(bot)
    client.login()

    log = Log(bot['name'])

    processed = []
    values = {}

    while True:
        offers = client.get_offers()

        for offer in offers:
            offer_id = offer['tradeofferid']

            if offer_id not in processed:
                log = Log(bot['name'], offer_id)

                trade = Offer(offer)
                steam_id = trade.get_partner()

                if trade.is_active() and not trade.is_our_offer():
                    log.trade(f'Received a new offer from {f.YELLOW + str(steam_id)}')

                    if trade.is_from_owner():
                        log.trade('Offer is from owner')
                        client.accept(offer_id)

                    elif trade.is_gift() and accept_donations:
                        log.trade('User is trying to give items')
                        client.accept(offer_id)

                    elif trade.is_scam() and decline_scam_offers:
                        log.trade('User is trying to take items')
                        client.decline(offer_id)

                    elif trade.is_valid():
                        log.trade('Processing offer...')
                        
                        their_value = 0
                        their_items = offer['items_to_receive']

                        our_value = 0
                        our_items = offer['items_to_give']

                        items = get_items()

                        # Their items
                        for _item in their_items:
                            item = Items(their_items[_item])
                            name = item.name
                            value = 0.00

                            if item.is_tf2():
                                
                                if item.is_pure():
                                    value = item.get_pure()

                                elif item.is_craftable():

                                    if name in items:
                                        value = get_price(name, 'buy')

                                    elif item.is_craft_hat():
                                        value = craft_hat_buy
                                    
                                elif not item.is_craftable():
                                    name = 'Non-Craftable ' + name
                                    
                                    if name in items:
                                        value = get_price(name, 'buy')
                            
                            value = value if value else 0.00
                            their_value += to_scrap(value)

                        # Our items
                        for _item in our_items:
                            item = Items(our_items[_item])
                            name = item.name
                            value = 0.00
                            high = float(10**5)

                            if item.is_tf2():
                                
                                if item.is_pure():
                                    value = item.get_pure()

                                elif item.is_craftable():
                                
                                    if name in items:
                                        value = get_price(name, 'sell')

                                    elif item.is_craft_hat():
                                        value = craft_hat_sell
                                    
                                elif not item.is_craftable():
                                    name = 'Non-Craftable ' + name

                                    if name in items:
                                        value = get_price(name, 'sell')
                        
                            value = value if value else high
                            our_value += to_scrap(value)
                        
                        item_amount = len(their_items) + len(our_items)
                        log.trade(f'Offer contains {item_amount} items')

                        difference = to_refined(their_value - our_value)
                        their_value = to_refined(their_value)
                        our_value = to_refined(our_value)
                        summary = 'User value: {} ref, our value: {} ref, difference: {} ref'

                        log.trade(summary.format(their_value, our_value, difference))

                        if to_scrap(their_value) >= to_scrap(our_value):
                            values[offer_id] = {
                                'our_value': our_value,
                                'their_value': their_value
                            }
                            client.accept(offer_id)

                        else:
                            client.decline(offer_id)

                    else:
                        log.trade('Offer is invalid')

                else:
                    log.trade('Offer is not active')
            
                processed.append(offer_id)
        
        del offers

        for offer_id in processed:
            offer = client.get_offer(offer_id)
            trade = Offer(offer)

            log = Log(bot['name'], offer_id)

            if not trade.is_active():
                state = trade.get_state()
                log.trade(f'Offer state changed to {f.YELLOW + state}')

                if trade.is_accepted() and 'tradeid' in offer:
                    if save_trades:
                        Log().info('Saving offer data...')
                        _values = {}

                        if offer_id in values:
                            _values = values[offer_id]

                        trade_id = offer['tradeid']
                        receipt = client.get_receipt(trade_id)

                        offer['receipt'] = receipt
                        offer['our_value'] = _values['our_value']
                        offer['their_value'] = _values['their_value']

                        add_trade(offer)

                    values.pop(offer_id)
                    processed.remove(offer_id)

                else:
                    if offer_id in values:
                        values.pop(offer_id)
                    
                    if offer_id in processed:
                        processed.remove(offer_id)

        sleep(timeout)


def detect_database_changes() -> None:
    items = get_items()
    log = Log()

    while True:
        if not items == get_items():
            log.info('Item(s) were added or removed from the database')
            items = get_items()
            update_pricelist(items)
            log.info('Successfully updated all prices')
        sleep(10)


if __name__ == '__main__':
    log = Log()
    socket = socketio.Client()

    items = get_items() 
    update_pricelist(items)
    log.info('Successfully updated all prices')

    @socket.event
    def connect():
        socket.emit('authentication')
        log.info('Successfully connected to Prices.tf socket server')

    @socket.event
    def authenticated(data):
        pass

    @socket.event
    def price(data):
        if data['name'] in get_items():
            update_price(data['name'], data['buy'], data['sell'])

    @socket.event
    def unauthorized(sid):
        pass

    socket.connect('https://api.prices.tf')
    log.info('Listening to Prices.tf for price updates')

    Process(target=detect_database_changes).start()

    with Pool(len(bots)) as p:
        p.map(run, bots)
