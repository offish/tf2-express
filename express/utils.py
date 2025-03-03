import json
import logging
from pathlib import Path

import requests
from tf2_utils import SchemaItemsUtils, sku_to_color

from .exceptions import NoConfigFound

schema_items_utils = SchemaItemsUtils()


def sku_to_item_data(sku: str) -> dict:
    name = schema_items_utils.sku_to_name(sku)
    color = sku_to_color(sku)
    image = schema_items_utils.sku_to_image_url(sku)
    return {"sku": sku, "name": name, "image": image, "color": color}


def encode_data(data: dict) -> bytes:
    if data.get("_id"):
        del data["_id"]

    return (json.dumps(data) + "NEW_DATA").encode()


def decode_data(data: bytes) -> list[dict]:
    return [json.loads(doc) for doc in data.decode().split("NEW_DATA") if doc]


def read_json_file(filename: str | Path) -> dict:
    content = {}

    with open(filename, "r") as f:
        content = json.loads(f.read())

    return content


def get_config() -> dict:
    path = Path(__file__).parent / "config.json"

    if not path.exists():
        raise NoConfigFound("No config.json file in the express directory!")

    return read_json_file(path)


def summarize_items(items: list[dict]) -> dict:
    summary = {}

    for item in items:
        item_name = items[item]["market_hash_name"]

        if item_name in summary:
            summary[item_name]["count"] += 1
            continue

        summary[item_name] = {
            "count": 1,
            "image": items[item]["icon_url"],
            "color": items[item]["name_color"],
        }

    return summary


def summarize_trades(trades: list[dict]) -> list[dict]:
    return [
        {
            **trade,
            "our_summary": summarize_items(trade.get("our_items", [])),
            "their_summary": summarize_items(trade.get("their_items", [])),
        }
        for trade in trades
    ]


def get_version(repository: str, folder: str) -> str:
    url = "https://raw.githubusercontent.com/offish/{}/master/{}/__init__.py".format(
        repository, folder
    )

    r = requests.get(url)
    data = r.text

    version_index = data.index("__version__")
    start_quotation_mark = data.index('"', version_index) + 1
    end_quotation_mark = data.index('"', start_quotation_mark)

    # get rid of first "
    return data[start_quotation_mark:end_quotation_mark]


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
