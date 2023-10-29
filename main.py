from express.express import Express
from express.options import Options, GlobalOptions
from express.utils import (
    ExpressFormatter,
    ExpressFileFormatter,
    get_version,
    get_config,
)

from threading import Thread
import logging
import sys
import os

from tf2_utils import PricesTFSocket
from tf2_utils import __version__ as tf2_utils_version
from express import __version__ as tf2_express_version
from tf2_sku import __version__ as tf2_sku_version


bots: list[Express] = []

packages = [
    (tf2_express_version, "tf2-express", "express"),
    (tf2_utils_version, "tf2-utils", "src/tf2_utils"),
    (tf2_sku_version, "tf2-sku", "src/tf2_sku"),
]

formatter = ExpressFormatter()
stream_handler = logging.StreamHandler(sys.stdout)

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


def create_bot_instance(bot: dict) -> Express:
    options = Options(**bot["options"])
    logging.debug(f"using options {options=}")
    client = Express(bot, options)

    logging.info(f"Created instance for {bot['username']}")
    return client


# callback to tf2-utils' pricestf
def on_price_change(data: dict) -> None:
    if data.get("type") != "PRICE_CHANGED":
        return

    if not data.get("data", {}).get("sku"):
        return

    logging.debug(f"Got new price change from Prices.tf {data=}")

    for bot in bots:
        bot.append_new_price(data.get("data", {}))


if __name__ == "__main__":
    logging.info("Started tf2-express")

    config = get_config()
    options = GlobalOptions(**config)

    prices_tf_socket = PricesTFSocket(on_price_change)
    prices_thread = Thread(target=prices_tf_socket.listen, daemon=True)

    logging.info("Listening to Prices.tf for price updates")

    if options.check_versions_on_startup:
        for i in packages:
            current_version, repo, folder = i
            latest_version = get_version(repo, folder)

            if current_version == latest_version:
                continue

            logging.warning(
                "{} is at version {} while {} is available".format(
                    repo, current_version, latest_version
                )
            )

    prices_thread.start()
    bot_threads: list[Thread] = []

    for bot in options.bots:
        bot_instance = create_bot_instance(bot)
        bot_instance.login()
        bot_thread = Thread(target=bot_instance.run, daemon=True)
        bot_thread.start()

        bots.append(bot_instance)
        bot_threads.append(bot_thread)

    for thread in bot_threads:
        thread.join()

    prices_thread.join()
