import time
from datetime import datetime

from flask import Request, render_template
from tf2_data import COLORS
from tf2_utils import Item, SchemaItemsUtils, is_sku, to_refined

from .database import Database
from .utils import get_config, get_versions, sku_to_item_data


class Panel:
    def __init__(self) -> None:
        self._config = get_config()
        self._schema = SchemaItemsUtils()
        self._database_names = []
        self._set_database_names()

        database_name = self._get_first_database_name()
        self._database = Database(database_name)

    def _set_database_names(self) -> None:
        for bot in self._config["bots"]:
            database_name = bot["username"]
            self._database_names.append(database_name)

    def _get_first_database_name(self) -> str:
        return self._database_names[0]

    def _get_database(self, request: Request) -> str:
        default = self._get_first_database_name()
        database_name = request.args.get("db", default)

        if database_name != self._database.name:
            self._database = Database(database_name)

        return database_name

    def _get_item_data(self, item: str, skus: list[str]) -> dict | None:
        # check if first char is whitespace
        if item.find(" ") == 0:
            item = item[1:]

        sku = item

        if not is_sku(sku):
            sku = self._schema.name_to_sku(item)

        item_data = sku_to_item_data(sku)

        if sku in skus:
            print(f"{sku=} already exists in the database")
            return

        if not item_data["name"]:
            print(f"could not get name for {sku=}, ignoring...")
            return

        return item_data

    def _add_items_to_database(self, items: list[str]) -> None:
        skus = self._database.get_skus()

        for item in items:
            item_data = self._get_item_data(item, skus)

            if item_data is None:
                continue

            self._database.add_item(**item_data)

    def _render(self, page: str, db_name: str, **kwargs) -> str:
        return render_template(
            f"{page}.html",
            db_name=db_name,
            database_names=self._database_names,
            current_year=datetime.now().year,
            **kwargs,
        )

    def get_overview(self, request: Request) -> str:
        database_name = self._get_database(request)

        return self._render(
            "home",
            database_name,
            name=database_name,
            **get_versions(),
        )

    def get_trades(self, request: Request) -> str:
        database_name = self._get_database(request)

        start = request.args.get("start", 0)
        amount = request.args.get("amount", 25)

        if not isinstance(start, int):
            start = int(start)

        if not isinstance(amount, int):
            amount = int(amount)

        data = self._database.get_trades(start, amount)
        summarized_trades = summarize_trades(data["trades"])

        return self._render(
            "trades",
            database_name,
            trades=summarized_trades,
            total_trades=data["total_trades"],
            start=start,
            amount=amount,
            start_index=data["start_index"],
            end_index=data["end_index"],
        )

    def get_item_info(self, request: Request, sku: str) -> str:
        database_name = self._get_database(request)
        item = self._database.get_item(sku)

        time_updated = item.get("updated", 0)
        updated = datetime.fromtimestamp(time_updated).strftime("%c")
        passed_time = int((time.time() - time_updated) / 60)

        return self._render(
            "item", database_name, item=item, updated=updated, passed_time=passed_time
        )

    def get_items(self, request: Request) -> str:
        database_name = self._get_database(request)
        items = self._database.get_pricelist()

        return self._render("items", database_name, items=items)

    def autoprice_item(self, request: Request, sku: str) -> str:
        database_name = self._get_database(request)
        self._database.update_price(sku, {}, {}, True)

        return database_name

    def add_item(self, request: Request) -> str:
        database_name = self._get_database(request)
        data = dict(request.form.items())
        items = data["items"].split(",")
        self._add_items_to_database(items)

        return database_name

    def edit_item(self, request: Request) -> str:
        database_name = self._get_database(request)
        data = dict(request.form.items())

        buy_keys = data.get("buy_keys", 0)
        buy_metal = data.get("buy_metal", 0.0)
        sell_keys = data.get("sell_keys", 0)
        sell_metal = data.get("sell_metal", 0.0)
        max_stock = data.get("max_stock", -1)

        self._database.update_price(
            data["sku"],
            buy={"keys": int(buy_keys), "metal": float(buy_metal)},
            sell={"keys": int(sell_keys), "metal": float(sell_metal)},
            max_stock=int(max_stock),
        )

        return database_name

    def delete_item(self, request: Request, sku: str) -> str:
        database_name = self._get_database(request)
        self._database.delete_price(sku)

        return database_name


def summarize_items(items: list[dict]) -> dict:
    summary = {}

    for item in items:
        item_name = item["market_hash_name"]

        if item_name in summary:
            summary[item_name]["count"] += 1
            continue

        quality = Item(item).get_quality()
        color = COLORS[quality]

        summary[item_name] = {
            "count": 1,
            "image": item["icon_url"],
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
