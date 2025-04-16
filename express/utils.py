import json
import logging
from datetime import datetime
from pathlib import Path

import requests
from backpack_tf import __version__ as backpack_tf_version
from steam import __version__ as steam_py_version
from tf2_data import __version__ as tf2_data_version
from tf2_sku import __version__ as tf2_sku_version
from tf2_utils import SchemaItemsUtils, sku_to_color
from tf2_utils import __version__ as tf2_utils_version

from . import __version__ as tf2_express_version
from .exceptions import NoConfigFound

schema_items_utils = SchemaItemsUtils()


def has_buy_and_sell_price(data: dict) -> bool:
    return data.get("buy", {}) != {} and data.get("sell", {}) != {}


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


def read_json_file(filename: str | Path) -> dict:
    content = {}

    with open(filename, "r") as f:
        content = json.loads(f.read())

    return content


def get_config() -> dict:
    path = Path(__file__).parent.parent / "config.json"

    if not path.exists():
        raise NoConfigFound("No config.json file found!")

    return read_json_file(path)


def get_bot_config() -> dict:
    # only one bot is supported for now
    return get_config().get("bots", [])[0]


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


def get_versions() -> dict[str, str]:
    return {
        "tf2_express_version": tf2_express_version,
        "tf2_data_version": tf2_data_version,
        "tf2_sku_version": tf2_sku_version,
        "tf2_utils_version": tf2_utils_version,
        "backpack_tf_version": backpack_tf_version,
        "steam_py_version": steam_py_version,
    }


def get_newest_versions() -> dict[str, str]:
    return {
        "tf2_express_version": get_version("tf2-express", "express"),
        "tf2_data_version": get_version("tf2-data", "src/tf2_data"),
        "tf2_sku_version": get_version("tf2-sku", "src/tf2_sku"),
        "tf2_utils_version": get_version("tf2-utils", "src/tf2_utils"),
        "backpack_tf_version": get_version("backpack-tf", "src/backpack_tf"),
    }


def check_for_updates() -> None:
    logging.info("Checking for updates...")

    current_versions = get_versions()
    newest_versions = get_newest_versions()
    has_outdated = False

    for key in current_versions:
        if key not in newest_versions:
            continue

        current_version = current_versions[key]
        newest_version = newest_versions[key]

        if current_version != newest_version:
            has_outdated = True
            name = key.replace("_version", "").replace("_", "-")

            logging.warning(f"{name} has a new version. You should probably upgrade.")
            logging.warning(
                f"Installed version: {current_version}, available: {newest_version}"
            )

    if not has_outdated:
        logging.info("All packages are up to date!")


def create_and_get_log_file() -> Path:
    current_date = datetime.today().strftime("%Y-%m-%d")
    file_path = Path(__file__).parent.parent / f"logs/express-{current_date}.log"

    if not file_path.exists():
        file_path.touch()

    return file_path


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
