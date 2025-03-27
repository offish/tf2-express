import json
import logging
from datetime import datetime
from pathlib import Path

import requests
from tf2_utils import SchemaItemsUtils, sku_to_color

from .exceptions import NoConfigFound

schema_items_utils = SchemaItemsUtils()


def create_and_get_log_file() -> Path:
    current_date = datetime.today().strftime("%Y-%m-%d")
    file_path = Path(__file__).parent.parent / f"logs/express-{current_date}.log"

    if not file_path.exists():
        file_path.touch()

    return file_path


def is_same_item(a: dict, b: dict) -> bool:
    return int(a["instanceid"]) == int(b["instanceid"]) and int(a["classid"]) == int(
        b["classid"]
    )


def swap_intent(intent: str) -> str:
    return "buy" if intent.lower() == "sell" else "sell"


def is_only_taking_items(their_items_amount: int, our_items_amount: int) -> bool:
    return their_items_amount == 0 and our_items_amount > 0


def is_two_sided_offer(their_items_amount: int, our_items_amount: int) -> bool:
    return their_items_amount > 0 and our_items_amount > 0


def sku_to_item_data(sku: str) -> dict:
    name = schema_items_utils.sku_to_name(sku)
    color = sku_to_color(sku)
    image = schema_items_utils.sku_to_image_url(sku)
    return {"sku": sku, "name": name, "image": image, "color": color}


def encode_data(data: dict) -> bytes:
    if "_id" in data:
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
