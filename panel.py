from express.database import Database
from express.utils import (
    summarize_trades,
    get_config,
    sku_to_item_data,
)

from datetime import datetime
import time

from flask import Flask, render_template, request, redirect
from tf2_utils import SchemaItemsUtils, refinedify, is_sku
from tf2_utils import __version__ as tf2_utils_version
from tf2_data import __version__ as tf2_data_version
from tf2_sku import __version__ as tf2_sku_version
from express import __version__ as tf2_express_version


app = Flask(__name__)
name = ""

databases: dict = {}
schema_items_utils = SchemaItemsUtils()
first_database = ""


def items_to_data(items: list, skus: list) -> list:
    data = []

    for item in items:
        # check if first char is whitespace
        if item.find(" ") == 0:
            item = item[1:]

        sku = item

        if not is_sku(sku):
            sku = schema_items_utils.name_to_sku(item)

        item_data = sku_to_item_data(sku)

        if sku in skus:
            print(f"{sku=} already exists in the database")
            continue

        if not item_data["name"]:
            print(f"could not get name for {sku=}, ignoring...")
            continue

        data.append(item_data)

    return data


def add_items_to_database(db, data: list) -> None:
    for item in data:
        db.add_item(**item)

    return


def get_database(request) -> tuple[Database, str]:
    default = first_database
    db_name = request.args.get("db", default)

    if not db_name:
        db_name = default

    return databases[db_name], db_name


def render(page: str, db_name: str, **kwargs) -> str:
    return render_template(
        f"{page}.html",
        db_name=db_name,
        database_names=list(databases.keys()),
        tf2_express_version=tf2_express_version,
        **kwargs,
    )


@app.route("/")
def overview():
    _, db_name = get_database(request)

    return render(
        "home",
        db_name,
        name=name,
        tf2_utils_version=tf2_utils_version,
        tf2_data_version=tf2_data_version,
        tf2_sku_version=tf2_sku_version,
    )


@app.route("/trades")
def trades():
    db, db_name = get_database(request)

    start = request.args.get("start", 0)
    amount = request.args.get("amount", 25)

    if not isinstance(start, int):
        start = int(start)

    if not isinstance(amount, int):
        amount = int(amount)

    selected_trades, total_trades, start_index, end_index = db.get_trades(start, amount)

    summarized_trades = summarize_trades(selected_trades)

    return render(
        "trades",
        db_name,
        trades=summarized_trades,
        total_trades=total_trades,
        start=start,
        amount=amount,
        start_index=start_index,
        end_index=end_index,
    )


@app.route("/item/<sku>")
def item_info(sku):
    db, db_name = get_database(request)
    item = db.get_item(sku)

    time_updated = item.get("updated", 0)
    updated = datetime.fromtimestamp(time_updated).strftime("%c")
    passed_time = int((time.time() - time_updated) / 60)

    return render("item", db_name, item=item, updated=updated, passed_time=passed_time)


@app.route("/items")
def items():
    db, db_name = get_database(request)

    return render("items", db_name, items=db.get_pricelist())


@app.route("/autoprice/<sku>")
def autoprice(sku):
    db, db_name = get_database(request)
    db.update_price(sku, {}, {}, True)

    return redirect(f"/items?db={db_name}")


@app.route("/delete/<sku>")
def delete(sku):
    db, db_name = get_database(request)
    db.delete_price(sku)

    return redirect(f"/items?db={db_name}")


@app.route("/edit", methods=["POST"])
def edit():
    db, db_name = get_database(request)
    data = dict(request.form.items())

    buy_keys = data["buy_keys"]
    buy_metal = data["buy_metal"]
    sell_keys = data["sell_keys"]
    sell_metal = data["sell_metal"]
    max_stock = data["max_stock"]

    if not buy_keys:
        buy_keys = 0

    if not sell_keys:
        sell_keys = 0

    if not buy_metal:
        buy_metal = 0.0

    if not sell_metal:
        sell_metal = 0.0

    if not max_stock or int(max_stock) <= 0:
        max_stock = -1

    db.update_price(
        sku=data["sku"],
        buy={
            "keys": int(buy_keys),
            "metal": refinedify(float(buy_metal)),
        },
        sell={
            "keys": int(sell_keys),
            "metal": refinedify(float(sell_metal)),
        },
        autoprice=False,
        max_stock=int(max_stock),
    )

    return redirect(f"/items?db={db_name}")


@app.route("/add", methods=["POST"])
def add():
    db, db_name = get_database(request)
    data = dict(request.form.items())
    items = data["items"].split(",")
    skus = db.get_skus()
    data = items_to_data(items, skus)
    add_items_to_database(db, data)

    return redirect(f"/items?db={db_name}")


if __name__ == "__main__":
    config = get_config()

    for bot in config["bots"]:
        options = bot.get("options", {})
        db = options.get("database", "express")
        host = options.get("host", "localhost")
        port = options.get("port", 27017)

        if not first_database:
            first_database = db

        databases[db] = Database(db, host, port)

    name = config.get("name", "express user")

    app.run(debug=True)
