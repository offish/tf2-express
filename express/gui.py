import time
from datetime import datetime
from typing import Any
from urllib.parse import unquote

import requests
from flask import Request, render_template
from tf2_data import COLORS
from tf2_utils import Item, is_metal, is_sku, to_refined
from tf2_utils.instances import schema

from .databases.database_providers import get_database_provider
from .utils import get_config, get_options, get_versions, sku_to_item_data


class Panel:
    def __init__(self) -> None:
        config = get_config()
        username = config["username"]

        self.username = username
        self.options = get_options(username)
        self.database = get_database_provider(self.options.database_provider, username)

    def request(self, method: str, endpoint: str, **kwargs) -> Any:
        url = "http://127.0.0.1:8010/api/v1/" + endpoint
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def get_item_data(item: str, skus: list[str]) -> dict | None:
        # check if first char is whitespace
        if item.find(" ") == 0:
            item = item[1:]

        sku = item

        if not is_sku(sku):
            sku = schema.name_to_sku(item)

        item_data = sku_to_item_data(sku)

        if sku in skus:
            print(f"{sku=} already exists in the database")
            return

        if not item_data["name"]:
            print(f"could not get name for {sku=}, ignoring...")
            return

        return item_data

    def add_items_to_database(self, items: list[str]) -> None:
        skus = self.database.get_skus()

        for item in items:
            item_data = self.get_item_data(item, skus)

            if item_data is None:
                continue

            self.database.add_item(**item_data)

    def render(self, page: str, **kwargs) -> str:
        return render_template(
            f"{page}.html", current_year=datetime.now().year, **kwargs
        )

    def get_overview(self) -> str:
        return self.render("home", name=self.username, **get_versions())

    def get_trades(self, request: Request) -> str:
        start = request.args.get("start", 0)
        amount = request.args.get("amount", 25)

        if not isinstance(start, int):
            start = int(start)

        if not isinstance(amount, int):
            amount = int(amount)

        data = self.database.get_trades(start, amount)
        summarized_trades = summarize_trades(data["trades"])

        return self.render(
            "trades",
            trades=summarized_trades,
            total_trades=data["total_trades"],
            start=start,
            amount=amount,
            start_index=data["start_index"],
            end_index=data["end_index"],
        )

    def get_item_info(self, sku: str) -> str:
        item = self.database.get_item(sku)

        time_updated = item.get("updated", 0)
        updated = datetime.fromtimestamp(time_updated).strftime("%c")
        passed_time = int((time.time() - time_updated) / 60)

        return self.render("item", item=item, updated=updated, passed_time=passed_time)

    def get_items(self) -> str:
        items = self.database.get_items()
        return self.render("items", items=items)

    def autoprice_item(self, sku: str) -> str:
        if sku in ["-50;6", "-100;6"]:
            print(f"Autopricing {sku} is not possible!")
            return

        self.database.update_price(sku, {}, {}, override_autoprice=True)

    def add_item(self, request: Request) -> str:
        data = dict(request.form.items())
        items = data["items"].split(",")
        self.add_items_to_database(items)

    def edit_item(self, request: Request) -> None:
        data = dict(request.form.items())
        sku = data["sku"]

        buy_keys = data.get("buy_keys", 0)
        buy_metal = data.get("buy_metal", 0.0)
        sell_keys = data.get("sell_keys", 0)
        sell_metal = data.get("sell_metal", 0.0)
        max_stock = data.get("max_stock", -1)

        # they can still be empty strings
        if not buy_keys:
            buy_keys = 0

        if not buy_metal:
            buy_metal = 0.0

        if not sell_keys:
            sell_keys = 0

        if not sell_metal:
            sell_metal = 0.0

        buy_price = {"keys": int(buy_keys), "metal": float(buy_metal)}
        sell_price = {"keys": int(sell_keys), "metal": float(sell_metal)}

        item = self.database.get_item(sku)
        autoprice = item["autoprice"]

        if item["buy"] != buy_price or item["sell"] != sell_price:
            autoprice = False

        self.database.update_price(
            sku=sku,
            buy=buy_price,
            sell=sell_price,
            override_autoprice=autoprice,
            override_max_stock=int(max_stock),
        )

    def get_filtered_inventory(self) -> dict:
        inventory = self.request("GET", "inventory")
        filtered_inventory = {"inventory": []}

        for item in inventory["inventory"]:
            sku = item["sku"]

            if not is_metal(sku):
                filtered_inventory["inventory"].append(item)

        return filtered_inventory

    def get_inventory(self) -> str:
        filtered_inventory = self.get_filtered_inventory()
        return self.render("inventory", inventory=filtered_inventory)

    def get_prices(self, sku: str) -> str:
        sku = unquote(sku)
        prices = self.request("GET", "prices", params={"sku": sku})
        return self.render("prices", sku=sku, prices=prices)

    def get_dump(self) -> str:
        filtered_inventory = self.get_filtered_inventory()
        return self.render("dump", inventory=filtered_inventory)

    def get_wishlist(self) -> str:
        filtered_inventory = self.get_filtered_inventory()
        return self.render("wishlist", inventory=filtered_inventory)


def summarize_items(items: list[dict]) -> dict:
    summary = {}

    for item in items:
        if not item:
            continue

        item_name = item["market_hash_name"]

        if item_name in summary:
            summary[item_name]["count"] += 1
            continue

        quality = Item(item).get_quality()

        if quality:
            color = COLORS[quality]
        else:
            color = "808080"

        summary[item_name] = {
            "count": 1,
            "image": item.get("icon_url", ""),
            "color": color,
        }

    return summary


def summarize_trades(trades: list[dict]) -> list[dict]:
    summary = []

    for trade in trades:
        timestamp = trade["timestamp"]
        accepted = datetime.fromtimestamp(timestamp).strftime("%c")
        passed_time = (time.time() - timestamp) / 3600
        our_value = to_refined(trade.get("our_value", 0))
        their_value = to_refined(trade.get("their_value", 0))

        summary.append(
            trade
            | {
                "our_summary": summarize_items(trade.get("our_items", [])),
                "their_summary": summarize_items(trade.get("their_items", [])),
                "accepted": accepted,
                "passed_time": int(passed_time),
                "our_value": our_value,
                "their_value": their_value,
            }
        )

    return summary
