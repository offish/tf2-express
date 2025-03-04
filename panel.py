from flask import Flask, redirect, request

from express.gui import Panel

app = Flask(__name__)
panel = Panel()


@app.route("/")
def overview():
    return panel.get_overview(request)


@app.route("/trades")
def trades():
    return panel.get_trades(request)


@app.route("/item/<sku>")
def item_info(sku):
    return panel.get_item_info(request, sku)


@app.route("/items")
def items():
    return panel.get_items(request)


@app.route("/autoprice/<sku>")
def autoprice(sku):
    database_name = panel.autoprice_item(request, sku)
    return redirect(f"/items?db={database_name}")


@app.route("/add", methods=["POST"])
def add():
    database_name = panel.add_item(request)
    return redirect(f"/items?db={database_name}")


@app.route("/edit", methods=["POST"])
def edit():
    database_name = panel.edit_item(request)
    return redirect(f"/items?db={database_name}")


@app.route("/delete/<sku>")
def delete(sku):
    database_name = panel.delete_item(request, sku)
    return redirect(f"/items?db={database_name}")


if __name__ == "__main__":
    app.run(debug=True)
