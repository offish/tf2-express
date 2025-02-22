import logging
import os
import sys

from express.express import Express
from express.options import Options
from express.utils import ExpressFileFormatter, ExpressFormatter, get_config

formatter = ExpressFormatter()
stream_handler = logging.StreamHandler(sys.stdout)

LOG_PATH = os.getcwd() + "/logs/"
LOG_FILE = LOG_PATH + "express.log"

# create folder and empty log file
if not os.path.isfile(LOG_FILE):
    os.makedirs(LOG_PATH)
    open(LOG_FILE, "x")

file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")

logging.getLogger("steam").setLevel(logging.WARNING)
logging.basicConfig(level=logging.DEBUG, handlers=[stream_handler, file_handler])

# only want to see info and above in console
stream_handler.setLevel(logging.INFO)
# stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(ExpressFormatter())

# want to have everything in the log file
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(ExpressFileFormatter())


def main() -> None:
    options = Options()
    express = Express(options)
    bot_config = get_config()["bots"][0]
    config = {
        "username": bot_config["username"],
        "password": bot_config["password"],
        "shared_secret": bot_config["shared_secret"],
        "identity_secret": bot_config["identity_secret"],
    }
    express.run(**config)


if __name__ == "__main__":
    main()
