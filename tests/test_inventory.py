from express.inventory import receipt_item_to_inventory_item, format_items_list_to_dict
from express.utils import read_json_file

from unittest import TestCase

from tf2_utils import Item, get_sku, map_inventory


class TestInventory(TestCase):
    def test_receipt_item(self):
        receipt_item_raw = read_json_file("./tests/jsons/receipt_item.json")
        _inventory_item = read_json_file("./tests/jsons/inventory_item.json")

        _receipt_item = receipt_item_to_inventory_item(receipt_item_raw)

        receipt_item = Item(_receipt_item)
        inventory_item = Item(_inventory_item)

        self.assertEqual(receipt_item.name, inventory_item.name)
        self.assertEqual(receipt_item.is_craft_hat(), inventory_item.is_craft_hat())
        self.assertEqual(receipt_item.get_defindex(), inventory_item.get_defindex())
        self.assertEqual(get_sku(receipt_item), get_sku(inventory_item))
        self.assertEqual(_receipt_item["assetid"], _inventory_item["assetid"])

    def test_format_items_list_to_dict(self):
        inventory = map_inventory(read_json_file("./tests/jsons/raw_inventory.json"))

        self.assertTrue(isinstance(format_items_list_to_dict(inventory), dict))
