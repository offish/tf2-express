from datetime import datetime

from colorama import init
from colorama import Fore as f

init()

def log(color, sort, text, offer_id = ''):
    if offer_id:
        text = f'({f.YELLOW}{offer_id}{f.WHITE}) {text}'
    time = datetime.now().time().strftime('%H:%M:%S')
    print(f'{f.GREEN}tf2-express | {f.WHITE}{time} - {color + sort}{f.WHITE}: {text}{f.WHITE}')


class Log:
    def __init__(self, offer_id: str = ''):
        self.offer_id = offer_id
    
    def info(self, text: str):
        log(f.GREEN, 'info', text)

    def error(self, text: str):
        log(f.RED, 'error', text)
    
    def trade(self, text: str, offer_id: str = ''):
        log(f.MAGENTA, 'trade', text, self.offer_id or offer_id)

