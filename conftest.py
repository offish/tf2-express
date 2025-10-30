from typing import Any

import pytest

from express.options import Messages, Options
from express.utils import get_config, read_json_file
from tests.mock.express import Express

INVENTORY_ITEM = read_json_file("./tests/jsons/inventory_item.json")
RECEIPT_ITEM = read_json_file("./tests/jsons/receipt_item.json")

bot_steam_id = "76561198828172881"  # replace with your own for testing
config = get_config()
messages = Messages(**config["messages"])
bot_options = Options(
    username=config["username"], messages=messages, **config["options"]
)
express = Express(bot_steam_id, bot_options)


@pytest.fixture
def inventory_item_data() -> dict[str, Any]:
    return INVENTORY_ITEM


@pytest.fixture
def receipt_item_data() -> dict[str, Any]:
    return RECEIPT_ITEM


@pytest.fixture
def steam_id() -> str:
    return bot_steam_id


@pytest.fixture
def options() -> Options:
    return bot_options


@pytest.fixture
def client() -> Express:
    return express
