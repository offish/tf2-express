from tf2_utils import map_inventory


def get_inventory_stock(inventory: dict) -> dict:
    # {sku: amount}
    stock = {}

    for item in map_inventory(inventory, True):
        sku = item["sku"]

        if item["tradable"] != True:
            continue

        if sku not in stock:
            stock[sku] = 1
        else:
            stock[sku] += 1

    return stock
