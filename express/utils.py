import json
import logging
import re
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
from .options import (
    ArbitrageOptions,
    BackpackTFOptions,
    ChatOptions,
    DiscordOptions,
    ExpressTFOptions,
    InventoryOptions,
    Messages,
    OffersOptions,
    Options,
)

schema_items_utils = SchemaItemsUtils()


def has_correct_price_format(data: dict) -> bool:
    if not isinstance(data, dict):
        return False

    for key in ["sku", "buy", "sell"]:
        if key not in data:
            return False

    if not isinstance(data["buy"], dict) or not isinstance(data["sell"], dict):
        return False

    for price in [data["buy"], data["sell"]]:
        if len(price) < 1 or len(price) > 2:
            return False

        if "keys" not in price and "metal" not in price:
            return False

        keys = price.get("keys", 0)
        metal = price.get("metal", 0.0)

        if not (isinstance(keys, int) and keys >= 0):
            return False

        if not (isinstance(metal, (int, float)) and metal >= 0):
            return False

    return True


def has_invalid_price_format(data: dict) -> bool:
    return not has_correct_price_format(data)


def has_buy_and_sell_price(data: dict) -> bool:
    return data.get("buy", {}) != {} and data.get("sell", {}) != {}


def is_same_item(a: dict, b: dict) -> bool:
    return int(a["instanceid"]) == int(b["instanceid"]) and int(a["classid"]) == int(
        b["classid"]
    )


def filter_skus(item_list: list[dict]) -> list[str]:
    return [item["sku"] for item in item_list]


def swap_intent(intent: str) -> str:
    return "buy" if intent.lower() == "sell" else "sell"


def normalize_item_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", "_", name)
    return name


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


def get_and_read_json_file(filename: str, must_exist: bool = True) -> dict:
    path = Path(__file__).parent.parent / filename

    if not path.exists() and not must_exist:
        logging.info(f"File {filename} does not exist, using default...")
        return {}

    if not path.exists() and must_exist:
        raise FileNotFoundError(f"No file found at path: {path}")

    return read_json_file(path)


def get_mafile() -> Path | None:
    path = Path(__file__).parent.parent

    for file in path.iterdir():
        if file.suffix == ".maFile":
            logging.debug(f"Found maFile: {file.name}")
            return file


def get_config() -> dict:
    config = get_and_read_json_file("config.json")

    assert "password" in config, "Password is missing in config"
    assert config["password"], "Password cannot be empty"

    username = config.get("username")
    identity_secret = config.get("identity_secret")
    shared_secret = config.get("shared_secret")
    mafile = get_mafile()

    if mafile:
        logging.info("Using maFile for authentication")
        content = json.loads(mafile.read_text())
        username = content["account_name"]
        identity_secret = content["identity_secret"]
        shared_secret = content["shared_secret"]
    else:
        logging.info("Using config for authentication")

    assert username, "username is missing"
    assert identity_secret, "identity_secret is missing"
    assert shared_secret, "shared_secret is missing"

    return {
        "username": username,
        "password": config["password"],
        "identity_secret": identity_secret,
        "shared_secret": shared_secret,
    }


def get_options(username: str) -> Options:
    options = get_and_read_json_file("options.json", must_exist=False)
    messages = get_and_read_json_file("messages.json", must_exist=False)
    backpack_tf = options.get("backpack_tf", {})
    offers = options.get("offers", {})
    inventory = options.get("inventory", {})
    chat = options.get("chat", {})
    discord = options.get("discord", {})
    arbitrage = options.get("arbitrage", {})
    express_tf = options.get("express_tf", {})

    # remove all keys that are not part of Options
    for key in options.copy():
        if key in [
            "username",
            "messages",
            "backpack_tf",
            "offers",
            "inventory",
            "chat",
            "discord",
            "arbitrage",
            "express_tf",
        ]:
            del options[key]

    return Options(
        username=username,
        **options,
        messages=Messages(**messages),
        backpack_tf=BackpackTFOptions(**backpack_tf),
        offers=OffersOptions(**offers),
        inventory=InventoryOptions(**inventory),
        chat=ChatOptions(**chat),
        discord=DiscordOptions(**discord),
        arbitrage=ArbitrageOptions(**arbitrage),
        express_tf=ExpressTFOptions(**express_tf),
    )


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
