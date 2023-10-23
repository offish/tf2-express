# from multiprocessing import Process, Pool
import time
import logging
import sys
import json

# from express.database import get_items
from express.express import Express
from express.options import Options

# from express.prices import update_pricelist

from express.utils import ExpressFormatter, ExpressFileFormatter, get_version
from express import __version__ as tf2_express_version

from tf2_utils import __version__ as tf2_utils_version
from tf2_sku import __version__ as tf2_sku_version

from tf2_utils import PricesTFSocket
from threading import Thread
from express.options import GlobalOptions


formatter = ExpressFormatter()
stream_handler = logging.StreamHandler(sys.stdout)


import os

LOG_PATH = os.getcwd() + "/logs/"
LOG_FILE = LOG_PATH + "express.log"

# create folder and empty log file
if not os.path.isfile(LOG_FILE):
    os.makedirs(LOG_PATH)
    open(LOG_FILE, "x")

file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[
        stream_handler,
        file_handler,
    ],
)

# only want to see info and above in console
stream_handler.setLevel(logging.INFO)
# stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(ExpressFormatter())

# want to have everything in the log file
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(ExpressFileFormatter())


packages = [
    (tf2_express_version, "tf2-express", "express"),
    (tf2_utils_version, "tf2-utils", "src/tf2_utils"),
    (tf2_sku_version, "tf2-sku", "src/tf2_sku"),
]


def create_bot_instance(bot: dict) -> Express:
    options = Options(**bot["options"])
    logging.debug(f"using options {options=}")
    client = Express(bot, options)

    logging.info(f"Created instance for {bot['username']}")
    return client

    # try:
    # client.login()
    # client.start()
    # client.run()

    # except BaseException as e:
    #     logging.info(f"Caught {type(e).__name__}")
    #     logging.error(e)

    #     client.logout()

    #     logging.info(f"Stopped")


# def on_database_change() -> None:
#     try:
#         items_in_database = get_items()
#         # log = Log()

#         while True:
#             if not items_in_database == get_items():
#                 logging.info("Item(s) were added or removed from the database")
#                 items_in_database = get_items()
#                 update_pricelist(items_in_database)
#                 logging.info("Successfully updated all prices")
#             sleep(10)

#     except BaseException:
#         pass


# check which database which should be used

# def start(self):


bots: list[Express] = []


def get_config() -> dict:
    config = {}

    with open("./express/config.json", "r") as f:
        config = json.loads(f.read())

    return config


def on_price_change(data: dict) -> None:
    if data.get("type") != "PRICE_CHANGED":
        return

    if not data.get("data", {}).get("sku"):
        return

    logging.debug(f"Got new price change from prices.tf {data=}")

    for bot in bots:
        bot.append_new_price(data)


if __name__ == "__main__":
    # t1 = time.time()

    logging.info("Started tf2-express")

    config = get_config()

    prices_tf_socket = PricesTFSocket(on_price_change)
    prices_thread = Thread(target=prices_tf_socket.listen)

    # bot_configs = []

    options = GlobalOptions(**config)

    if options.check_versions_on_startup:
        for i in packages:
            current_version, repo, folder = i
            latest_version = get_version(repo, folder)

            if current_version == latest_version:
                continue

            logging.warning(
                f"{repo} is at version {current_version} while {latest_version} is available"
            )

    prices_thread.start()
    bot_threads: list[Thread] = []

    for bot in options.bots:
        bot_instance = create_bot_instance(bot)
        bot_instance.login()
        bot_thread = Thread(target=bot_instance.run)
        bot_thread.start()

        bots.append(bot_instance)
        bot_threads.append(bot_thread)

    for thread in bot_threads:
        thread.join()

    prices_thread.join()

    # run(bots[0])
    # with Pool(len(bots)) as p:
    #     p.map(run, bots)
