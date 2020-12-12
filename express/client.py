from json import dumps

from .logging import Log, f

from steampy.client import SteamClient
from steampy.exceptions import InvalidCredentials

class Client:
    def __init__(self, bot: dict):
        self.log = Log(bot['name'])
        self.username = bot['username']
        self.password = bot['password']
        self.secrets = bot['secrets']
        self.client = SteamClient(bot['api_key'])

    def login(self):
        try:
            self.client.login(self.username, self.password, dumps(self.secrets))

            if self.client.was_login_executed:
                self.log.info(f'Logged into Steam as {f.GREEN + self.username}')
            else:
                self.log.error('Login was not executed')
        
        except InvalidCredentials as e:
            self.log.error(e)

    def logout(self):
        self.log.info('Logging out...')
        self.client.logout()

    def get_offers(self):
        return self.client.get_trade_offers(merge=True)['response']['trade_offers_received']

    def get_offer(self, offer_id: str):
        return self.client.get_trade_offer(offer_id, merge=True)['response']['offer']

    def get_receipt(self, trade_id: str):
        return self.client.get_trade_receipt(trade_id)

    def accept(self, offer_id: str):
        self.log.trade('Trying to accept offer', offer_id)
        self.client.accept_trade_offer(offer_id)

    def decline(self, offer_id: str):
        self.log.trade('Trying to decline offer', offer_id)
        self.client.decline_trade_offer(offer_id)
