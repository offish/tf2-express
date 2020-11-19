from json import dumps

from .logging import Log, f
from .config import api_key, username, password, secrets

from steampy.client import SteamClient
from steampy.exceptions import ConfirmationExpected


log = Log()


class Client:
    def __init__(self):
        self.client = SteamClient(api_key)

    def login(self):
        self.client.login(username, password, dumps(secrets))

        if self.client.was_login_executed:
            log.info(f'Logged into Steam as {f.GREEN + username}')
        else:
            log.error('Login was not executed')

    def logout(self):
        log.info('Logging out...')
        self.client.logout()

    def get_offers(self):
        return self.client.get_trade_offers(merge=True)['response']['trade_offers_received']

    def get_offer(self, offer_id):
        return self.client.get_trade_offer(offer_id, merge=True)['response']['offer']

    def get_receipt(self, trade_id):
        return self.client.get_trade_receipt(trade_id)

    def accept(self, offer_id: str):
        log.trade('Trying to accept offer', offer_id)
        self.client.accept_trade_offer(offer_id)

    def decline(self, offer_id: str):
        log.trade('Trying to decline offer', offer_id)
        self.client.decline_trade_offer(offer_id)
