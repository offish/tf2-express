from datetime import datetime

from colorama import Fore as f
from colorama import init

init()


def log(color: int, sort: str, bot: str, text: str, offer_id: str = ''):
    name = f' {f.GREEN}[{bot}]' if bot else ''
    text = f'({f.YELLOW}{offer_id}{f.WHITE}) {text}' \
        if offer_id else text
    time = datetime.now().time().strftime('%H:%M:%S')
    print(f'{f.GREEN}tf2-express | {f.WHITE}{time} - {color + sort}{name}{f.WHITE}: {text}{f.WHITE}')


class Log:
    def __init__(self, bot: str = '', offer_id: str = ''):
        self.bot = bot
        self.offer_id = offer_id
    
    def info(self, text: str):
        log(f.GREEN, 'info', self.bot, text)

    def error(self, text: str):
        log(f.RED, 'error', self.bot, text)
    
    def trade(self, text: str, offer_id: str = ''):
        log(f.MAGENTA, 'trade', self.bot, text, self.offer_id or offer_id)

