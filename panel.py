from flask import Flask, redirect, request

from express.gui import Panel

app = Flask(__name__)
panel = Panel()


@app.route("/")
def overview():
    return panel.get_overview()


@app.route("/items")
def items():
    return panel.get_items()


@app.route("/item/<sku>")
def item_info(sku: str):
    return panel.get_item_info(sku)


@app.route("/add", methods=["POST"])
def add():
    panel.add_item(request)
    return redirect("/items")


@app.route("/autoprice/<sku>")
def autoprice(sku: str):
    panel.autoprice_item(sku)
    return redirect("/items")


@app.route("/edit", methods=["POST"])
def edit():
    panel.edit_item(request)
    return redirect("/items")


@app.route("/delete/<sku>")
def delete(sku: str):
    panel.database.delete_item(sku)
    return redirect("/items")


@app.route("/trades")
def trades():
    return panel.get_trades(request)


@app.route("/inventory")
def get_inventory():
    return panel.get_inventory()


@app.route("/prices/<sku>")
def get_prices(sku: str):
    return panel.get_prices(sku)


@app.route("/dump")
def dump():
    return panel.get_dump()


@app.route("/wishlist")
def wishlist():
    return panel.get_wishlist()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
