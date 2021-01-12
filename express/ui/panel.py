# to run: python -m express.ui.panel

from flask import Flask, render_template, request, redirect, abort

from .. import database


app = Flask(__name__)


@app.route("/")
def overview():
    return redirect("/prices")


@app.route("/trades")
def trades():
    return render_template("trades.html", trades=database.get_trades())


@app.route("/prices")
def prices():
    return render_template("prices.html", items=database._get_pricelist())


@app.route("/delete/<name>")
def delete(name):
    database.remove_price(name)
    return redirect("/prices")


@app.route("/add", methods=["POST"])
def add():
    data = dict(request.form.items())
    names = data["names"].split(", ")
    for name in names:
        database.add_price(name)
    return redirect("/prices")


if __name__ == "__main__":
    app.run(debug=True)
