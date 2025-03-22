import logging
import sys

from express.express import Express
from express.options import Options
from express.utils import (
    ExpressFileFormatter,
    ExpressFormatter,
    create_and_get_log_file,
    get_config,
)

formatter = ExpressFormatter()
stream_handler = logging.StreamHandler(sys.stdout)

log_file = create_and_get_log_file()
file_handler = logging.FileHandler(log_file, encoding="utf-8")

logging.getLogger("steam").setLevel(logging.WARNING)
logging.getLogger("pymongo").setLevel(logging.INFO)
logging.getLogger("websockets").setLevel(logging.INFO)
logging.basicConfig(level=logging.DEBUG, handlers=[stream_handler, file_handler])

# only want to see info and above in console
stream_handler.setLevel(logging.INFO)
# stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(ExpressFormatter())

# want to have everything in the log file
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(ExpressFileFormatter())


def main() -> None:
    config = get_config()["bots"][0]
    options = Options(username=config["username"], **config["options"])
    express = Express(options)
    express.start(**config)


if __name__ == "__main__":
    main()
