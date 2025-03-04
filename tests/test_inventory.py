# from typing import Any

# from tf2_utils import Item, get_sku

# from express.conversion import receipt_data_to_item


# def test_receipt_item(
#     receipt_item_data: dict[str, Any], inventory_item_data: dict[str, Any]
# ) -> None:
#     receipt_to_inventory_item = receipt_data_to_item(receipt_item_data)

#     receipt_item = Item(receipt_to_inventory_item)
#     inventory_item = Item(inventory_item_data)

#     assert receipt_item.name == inventory_item.name
#     assert receipt_item.is_craft_hat() == inventory_item.is_craft_hat()
#     assert receipt_item.get_defindex() == inventory_item.get_defindex()
#     assert get_sku(receipt_item) == get_sku(inventory_item)
