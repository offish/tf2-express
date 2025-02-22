from tf2_utils import Item, get_sku

from express.inventory import receipt_item_to_inventory_item
from express.utils import read_json_file


def test_receipt_item() -> None:
    receipt_item_raw = read_json_file("./tests/jsons/receipt_item.json")
    _inventory_item = read_json_file("./tests/jsons/inventory_item.json")

    _receipt_item = receipt_item_to_inventory_item(receipt_item_raw)

    receipt_item = Item(_receipt_item)
    inventory_item = Item(_inventory_item)

    assert receipt_item.name == inventory_item.name
    assert receipt_item.is_craft_hat() == inventory_item.is_craft_hat()
    assert receipt_item.get_defindex() == inventory_item.get_defindex()
    assert get_sku(receipt_item) == get_sku(inventory_item)
    assert _receipt_item["assetid"] == _inventory_item["assetid"]
