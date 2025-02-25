from typing import Any

import pytest

from express.utils import read_json_file

INVENTORY_ITEM = read_json_file("./tests/jsons/inventory_item.json")
RECEIPT_ITEM = read_json_file("./tests/jsons/receipt_item.json")


@pytest.fixture
def inventory_item_data() -> dict[str, Any]:
    return INVENTORY_ITEM


@pytest.fixture
def receipt_item_data() -> dict[str, Any]:
    return RECEIPT_ITEM
