from datetime import date, datetime

from .config import DEBUG

from colorama import Fore as f
from colorama import init

init()

logs = []


def write_to_txt_file(strings: list):
    to_write = ""

    for string in strings:
        to_write += "\n" + string

    with open("express/files/logs.txt", "a") as f:
        f.write(to_write)


def log(color: int, sort: str, bot: str, text: str, offer_id: str = ""):
    name = f" {f.WHITE}[{f.GREEN}{bot}{f.WHITE}]" if bot else ""
    text = f"({f.YELLOW}{offer_id}{f.WHITE}) {text}" if offer_id else text
    time = datetime.now().time().strftime("%H:%M:%S")
    string = "{}tf2-express | {}" + time + " - {}" + sort + "{}{}: " + text + "{}"

    if DEBUG:
        logs.append(
            f"{date.today().strftime('%d/%m/%Y')} @ {time} | {sort} {bot}: {text}"
        )

        if len(logs) >= 10:
            write_to_txt_file(logs)
            logs.clear()

    print(string.format(f.GREEN, f.WHITE, color, name, f.WHITE, f.WHITE))


class Log:
    def __init__(self, bot: str = "", offer_id: str = ""):
        self.bot = bot
        self.offer_id = offer_id

    def info(self, text: str):
        log(f.GREEN, "info", self.bot, text)

    def error(self, text: str):
        log(f.RED, "error", self.bot, text)

    def trade(self, text: str, offer_id: str = ""):
        log(f.MAGENTA, "trade", self.bot, text, self.offer_id or offer_id)

    def debug(self, text: str, offer_id: str = ""):
        log(f.CYAN, "debug", self.bot, text, self.offer_id or offer_id)

    def close(self):
        write_to_txt_file(logs)
