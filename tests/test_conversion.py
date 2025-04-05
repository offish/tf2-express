from typing import Any

from express.conversion import item_data_to_item_object


def test_item_data_to_item_object(inventory_item_data: dict[str, Any]) -> None:
    item = item_data_to_item_object(None, None, inventory_item_data)

    assert item is not None
    assert item.id == 13751702840
    assert item._app_id == 440
    assert item.class_id == 67503
    assert item.instance_id == 11042697
    assert item.market_hash_name == "Honcho's Headgear"
