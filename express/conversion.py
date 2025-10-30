from typing import Any

from steam.protobufs.econ import Asset, ItemDescription
from steam.state import ConnectionState
from steam.trade import Item, MovedItem
from steam.user import User


def item_data_to_item_object(
    state: ConnectionState, owner: User, item_data: dict[str, Any]
) -> Item:
    # logging.debug(f"{item_data=}")
    asset_item_data = {
        "assetid": int(item_data["assetid"]),
        "appid": int(item_data["appid"]),
        "classid": int(item_data["classid"]),
        "instanceid": int(item_data["instanceid"]),
        "amount": int(item_data["amount"]),
        "contextid": int(item_data["contextid"]),
    }
    description_item_data = {
        "appid": int(item_data["appid"]),
        "classid": int(item_data["classid"]),
        "instanceid": int(item_data["instanceid"]),
        "icon_url": item_data["icon_url"],
        "descriptions": [i["value"] for i in item_data.get("descriptions", [])],
        "tradable": item_data["tradable"],
        "actions": item_data["actions"],
        "name": item_data["name"],
        "name_color": item_data["name_color"],
        "market_name": item_data["market_name"],
        "market_hash_name": item_data["market_hash_name"],
    }

    asset = Asset(**asset_item_data)
    description = ItemDescription(**description_item_data)

    return Item(state=state, asset=asset, description=description, owner=owner)


def item_object_to_item_data(item: Item) -> dict[str, Any]:
    # these are not always present
    is_tradable = item._is_tradable if getattr(item, "_is_tradable", None) else True
    icon = item.icon if getattr(item, "icon", None) else None
    icon_url = icon.url if getattr(icon, "url", None) else ""

    actions = []

    for i in item.actions:
        link = i.link if getattr(i, "link", None) else i["link"]
        name = i.name if getattr(i, "name", None) else i["name"]
        actions.append({"link": link, "name": name})

    return item.to_dict() | {
        "appid": int(item._app_id),
        "classid": item.class_id,
        "instanceid": item.instance_id,
        "icon_url": icon_url,
        "tradable": is_tradable,
        "actions": actions,
        "name": item.name,
        "market_hash_name": item.market_hash_name,
        "type": item.type,
        "marketable": item._is_marketable,
        "descriptions": [
            {
                "type": i.type,
                "value": i.value,
                "color": i.color,
                "label": i.label,
            }
            for i in item.descriptions
        ],
        "tags": [
            {
                "category": i.category,
                "internal_name": i.internal_name,
                "localized_category_name": i.localized_category_name,
                "localized_tag_name": i.localized_tag_name,
                "color": i.color,
            }
            for i in item.tags
        ],
    }


def receipt_object_to_item_data(item: MovedItem) -> dict[str, Any]:
    return item_object_to_item_data(item) | {"assetid": str(item.new_id)}
