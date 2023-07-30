# to run: python -m express.ui.panel

from flask import Flask, render_template, request, redirect, abort

from express.database import *
from express.prices import get_pricelist

import json


app = Flask(__name__)

PATH = "express/ui/"
PRICESLIST = PATH + "pricelist.json"


@app.route("/")
def overview():
    return redirect("/prices")


@app.route("/trades")
def trades():
    return render_template("trades.html", trades=get_trades())


@app.route("/prices")
def prices():
    return render_template("prices.html", items=get_database_pricelist())


@app.route("/pricelist")
def pricelist():
    with open(PRICESLIST, "w") as f:
        json.dump(get_pricelist(), f)
    return redirect("/prices")


@app.route("/price/<name>")
def price(name):
    try:
        pricelist = json.loads(open(PRICESLIST, "r").read())
        item = {}

        for i in pricelist["items"]:
            if name == i["name"]:
                item = i

        if not (item.get("buy") and item["sell"]):
            return redirect("/prices")

        update_price(name, True, item["buy"], item["sell"])
        return redirect("/prices")

    except FileNotFoundError:
        return redirect("/pricelist")


@app.route("/delete/<name>")
def delete(name):
    remove_price(name)
    return redirect("/prices")


@app.route("/edit", methods=["POST"])
def edit():
    data = dict(request.form.items())

    print(data)

    name, buy, sell = (
        data["name"],
        {"keys": int(data["buy_keys"]), "metal": float(data["buy_metal"])},
        {"keys": int(data["sell_keys"]), "metal": float(data["sell_metal"])},
    )

    update_price(name, False, buy, sell)

    return redirect("/prices")


@app.route("/add", methods=["POST"])
def add():
    data = dict(request.form.items())
    names = data["names"].split(", ")
    for name in names:
        if not name in get_items():
            add_price(name)
    return redirect("/prices")


if __name__ == "__main__":
    app.run(debug=True)
