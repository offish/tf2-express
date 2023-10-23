# from .options import Options

# from threading import Thread
import logging

# from tf2_utils import PricesTFSocket
import requests


def get_version(repository: str, folder: str) -> str:
    url = f"https://raw.githubusercontent.com/offish/{repository}/master/{folder}/__init__.py"

    r = requests.get(url)
    data = r.text

    version_index = data.index("__version__")
    start_quotation_mark = data.index('"', version_index)
    end_quotation_mark = data.index('"', start_quotation_mark + 1)

    # get rid of first "
    return data[start_quotation_mark + 1 : end_quotation_mark]


# class GlobalPricing:
#     def __init__(self, bots: list) -> None:
#         self.bots = bots
#         prices_tf_socket = PricesTFSocket(self.on_price_receive)
#         self.thread = Thread(prices_tf_socket)
#         self.thread.start()
#         self.default_options = Options()

#     def __get_database_names(self) -> list[str]:
#         db_names = []

#         for bot in self.bots:
#             db_name = self.default_options.database

#             specified_name = bot["options"].get("database")

#             if specified_name:
#                 db_name = specified_name

#             db_names.append(db_name)

#         return db_names

#


class ExpressFormatter(logging.Formatter):
    _format = "tf2-express | %(asctime)s - [%(levelname)s]: %(message)s"

    FORMATS = {
        logging.DEBUG: _format,
        logging.INFO: _format,
        logging.WARNING: _format,
        logging.ERROR: _format + "(%(filename)s:%(lineno)d)",
        logging.CRITICAL: _format + "(%(filename)s:%(lineno)d)",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)


class ExpressFileFormatter(logging.Formatter):
    _format = "%(filename)s %(asctime)s - [%(levelname)s]: %(message)s"

    FORMATS = {
        logging.DEBUG: _format,
        logging.INFO: _format,
        logging.WARNING: _format,
        logging.ERROR: _format + "(%(filename)s:%(lineno)d)",
        logging.CRITICAL: _format + "(%(filename)s:%(lineno)d)",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%d/%m/%Y %H:%M:%S")
        return formatter.format(record)
