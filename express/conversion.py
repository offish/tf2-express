from typing import Any

from steam.protobufs import econ
from steam.state import ConnectionState
from steam.trade import Item
from steam.user import User


def item_data_to_item_object(
    state: ConnectionState, owner: User, item_data: dict[str, Any]
) -> Item:
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
        "currency": item_data["currency"],
        "icon_url": item_data["icon_url"],
        "icon_url_large": item_data["icon_url_large"],
        "descriptions": [i["value"] for i in item_data.get("descriptions", [])],
        "tradable": item_data["tradable"],
        "actions": item_data["actions"],
        "name": item_data["name"],
        "name_color": item_data["name_color"],
        "market_name": item_data["market_name"],
        "market_hash_name": item_data["market_hash_name"],
        "commodity": item_data["commodity"],
        "marketable": item_data["marketable"],
    }

    asset = econ.Asset(**asset_item_data)
    description = econ.ItemDescription(**description_item_data)

    return Item(state=state, asset=asset, description=description, owner=owner)


def item_object_to_item_data(item: Item) -> dict[str, Any]:
    return {
        "assetid": item.id,
        "appid": item._app_id,
        "classid": item.class_id,
        "instanceid": item.instance_id,
        "contextid": item.context_id,
        "icon_url": item.icon,
        "tradable": item._is_tradable,
        "actions": [{"link": i.link, "name": i.name} for i in item.actions],
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
